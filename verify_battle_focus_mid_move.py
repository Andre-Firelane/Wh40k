"""Runtime proof through the REAL main() loop that the Agile Manoeuvre buttons
are on screen while a move is running.

THE REPORTED BUG. User, after an Aeldari game: "battle focus +2 Movement wurde
beim unteren guardian trupp nicht angeboten, obwohl ich noch tokens hatte.
diese faehigkeit kann mehrmals angewendet werden pro phase."

The RULE was right - REPEATABLE_PER_PHASE allows Swift as the Wind once per
unit per phase, exactly as printed, and test_battle_focus.py section 3 has
pinned that for a long time. The PANEL was the bug: the manoeuvre block lived
only in _draw_movement_ui()'s `else` arm, so the moment "Move" was pressed all
three buttons vanished, and after Confirm moved_squad_ids shut Swift as the
Wind for good. In logs/game_20260911_100813.log:303 the Avatar spends a token
before moving; seven units move after it in the same phase - both Guardian
Defenders squads among them - and no second token is ever spent.

WHY THIS EXISTS ON TOP OF THE SUITE. The report is literally "the button was
not on my screen". Section 14 proves the ActionPanel OBJECT draws it; only
main() proves the panel is REACHED, with a live pool, in a real frame - and
that three-stage call has a scar: action_panel.py:298-302 records a parameter
added at two stages and forgotten at the third, "which crashes every frame".

ONE STAGED FACT, named. ai/agent_driver.py runs start_move(), the sweep and
confirm_move() synchronously inside a single take_one_action(), so no frame of
a MockAgent run is ever rendered with state == MOVING - a passive counter
would truthfully report 0 and look exactly like a pass. So this selects a
Player 1 unit through the REAL MovementController and calls the REAL
start_move(), then lets main() render one frame untouched. Everything after
that is real: the real panel, the real _draw_dispatch, the real
battle_focus_pool main() built, the real token count.

Harness traps this walks into deliberately (both documented in CLAUDE.md):
importing selfplay runs nothing because of its __main__ guard, so it goes
through runpy; and selfplay REPLACES pygame.event.get at import time, so the
frame hook installs itself from the first drawn frame rather than racing it.

Usage:  python verify_battle_focus_mid_move.py [map2]
        python verify_battle_focus_mid_move.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import battle_focus as bf_mod
from game import config as game_config
from game import movement as movement_mod
from game.movement import MovementController
from game.turn import PHASE_MOVEMENT
from game.ui import button_style
from game.ui.action_panel import ActionPanel

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

MAP = next((a for a in sys.argv[1:] if not a.startswith("-")), "map2")

# SECOND STAGED FACT, named: Aeldari on BOTH sides. Measured first - with the
# shipped pairing the run spends all 2813 rendered frames in PLAYER 2's
# Movement phase, because selfplay only auto-plays Player 2 and Player 1's
# turn needs "Next Phase" clicks it does not make. So the side that actually
# reaches a Movement phase has to be the one carrying Battle Focus. The
# question asked is about the PANEL, which draws for
# movement_controller.selected_squad regardless of which player owns it.
game_config.PLAYER2_ARMY = "aeldari"

state = {
    "mover": None,          # the MovementController main() built
    "pool": None,           # the BattleFocusPool main() built
    "staged": False,
    "unit": None,
    "arms": [],             # movement state each time the block was drawn
    "labels": [],           # manoeuvre button labels drawn while MOVING
    "tokens": None,
}

_frames = {"n": 0}
_pump = {"real": None}

_real_mover_init = MovementController.__init__
_real_pool_init = bf_mod.BattleFocusPool.__init__
_real_draw_am = ActionPanel._draw_agile_manoeuvres
_real_draw_button = button_style.draw_button


def mover_init(self, *a, **kw):
    _real_mover_init(self, *a, **kw)
    if state["mover"] is None:
        state["mover"] = self


def pool_init(self, *a, **kw):
    _real_pool_init(self, *a, **kw)
    state["pool"] = self


def draw_am(self, surface, rect, button_width, button_y, squad, pool_, mover):
    """Records WHICH arm drew the block, then hands off to the real one."""
    _install_pump()
    arm = getattr(mover, "state", None)
    state["arms"].append(arm)
    if NEUTRALIZE and arm == movement_mod.MOVING:
        # THE PRE-FIX WORLD: the MOVING arm simply had no call here. The
        # `else` arm is untouched, which is exactly how it shipped.
        return button_y
    return _real_draw_am(self, surface, rect, button_width, button_y, squad, pool_, mover)


def draw_button(surface, rect, label, *a, **kw):
    accent = kw.get("accent")
    if accent == "battle_focus" and state["mover"] is not None \
            and state["mover"].state == movement_mod.MOVING:
        state["labels"].append(label)
    return _real_draw_button(surface, rect, label, *a, **kw)


MovementController.__init__ = mover_init
bf_mod.BattleFocusPool.__init__ = pool_init
ActionPanel._draw_agile_manoeuvres = draw_am
button_style.draw_button = draw_button


def _stage():
    """Put ONE Player 1 unit into a running move - the one fact a MockAgent
    run never produces. Everything after this is main()'s own code."""
    mover = state["mover"]
    pool_ = state["pool"]
    if mover is None or pool_ is None or state["staged"]:
        return
    tracker = getattr(mover, "turn_tracker", None)
    if tracker is None:
        return
    if tracker.phase != PHASE_MOVEMENT:
        return
    owner = tracker.turn_owner
    squads = []
    for token in list(getattr(mover, "all_tokens", []) or []):
        squad = getattr(token, "squad", None)
        if squad is None or squad.owner != owner:
            continue
        if squad in getattr(mover, "moved_squad_ids", set()):
            continue
        if not bf_mod.has_battle_focus(squad):
            continue
        if squad not in squads:
            squads.append(squad)
    for squad in squads:
        if not squad.models:
            continue
        mover.select(squad.models[0])
        mover.start_move()
        if mover.state == movement_mod.MOVING:
            state["staged"] = True
            state["unit"] = squad.name
            state["tokens"] = pool_.tokens.get(owner, 0)
            state["owner"] = owner
            return
    mover.select(None)


def event_get(*args, **kwargs):
    _frames["n"] += 1
    if not state["staged"]:
        _stage()
    if state["staged"] and state["labels"]:
        # One rendered frame with the move running is all this measures.
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    return _pump["real"](*args, **kwargs)


def _install_pump():
    if _pump["real"] is None:
        _pump["real"] = pygame.event.get
        pygame.event.get = event_get


def report():
    print()
    print("=" * 68)
    print("VERIFY: Agile Manoeuvre buttons during a running move  (%s%s)"
          % (MAP, ", NEUTRALIZED" if NEUTRALIZE else ""))
    print("=" * 68)
    print("  frames run                     %d" % _frames["n"])
    print("  unit put into a running move   %s  (%s)"
          % (state["unit"] or "NONE - nothing staged", state.get("owner", "-")))
    print("  Battle Focus tokens in hand    %s" % state["tokens"])
    moving = sum(1 for a in state["arms"] if a == movement_mod.MOVING)
    other = len(state["arms"]) - moving
    print("  manoeuvre block drawn: %d time(s) while MOVING, %d from the other arm"
          % (moving, other))
    print("  manoeuvre buttons while MOVING %d" % len(state["labels"]))
    for label in state["labels"]:
        print("      %s" % label)
    print()
    if not state["staged"]:
        print("  INCONCLUSIVE - no Battle Focus unit reached a running move.")
        return 1
    if NEUTRALIZE:
        ok = not state["labels"]
        print("  PRE-FIX WORLD: %d button(s) while MOVING - the reported bug is %s"
              % (len(state["labels"]), "reproduced" if ok else "NOT reproduced"))
        return 0 if ok else 1
    ok = len(state["labels"]) >= 1 and any("Swift as the Wind" in s for s in state["labels"])
    print("  %s" % ("PASS - the buttons are on screen mid-move"
                    if ok else "FAIL - no Swift as the Wind button while MOVING"))
    return 0 if ok else 1


sys.argv = [sys.argv[0], MAP, "8000"]
try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass
except Exception as exc:  # noqa: BLE001 - a crash is a result, and is reported
    print("CRASHED OUT OF main(): %s: %s" % (type(exc).__name__, exc))

raise SystemExit(report())
