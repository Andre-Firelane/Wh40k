"""Runtime proof through the REAL main() loop that the three Necron Stratagem
buttons reach the screen, and only in a phase their printed WHEN names.

test_necron_stratagem_ui.py draws the real ActionPanel, but it builds the panel
and the controllers itself. What it cannot show is that MAIN'S controllers,
built by MAIN'S constructors, reach MAIN'S panel - "built but never FED" has hit
this repo six times, and these three are the worst-guarded buttons in the game:
they are bespoke keyword arguments rather than registry members, so section 14
of test_event_chain_wiring.py cannot see them, and the only standing proof was
the substring "hungry_void_controller=hungry_void_controller" in main.py.

So this spies on game/ui/button_style.py's draw_button() - the one chokepoint
every button in the game goes through - and reports which of the three were
drawn, in which phases, and whether any appeared outside its WHEN.

THE NECRONS ARE THE AI'S DEFAULT ARMY, and that is the one thing this probe
must get right that its T'au and Aeldari siblings did not have to: config
ships PLAYER2_ARMY = "necrons". A probe about the HUMAN's buttons that does not
field them as PLAYER 1 measures the AI's army and reports a truthful-looking
zero.

THREE MORE THINGS ARE STAGED, each named rather than quietly faked:
  * THE DETACHMENT. Wrapped rather than pre-set: apply_to_config() writes every
    detachment setting from scratch, so a flag set before it runs is erased.
  * A SELECTED UNIT, every frame. _draw_movement_ui() opens with
    movement_controller.selected_squad and draws no unit UI without one, and a
    phase or turn change clears the pick.
  * THE PHASE. A MockAgent run does not visit all five reliably.

The phase is READ LIVE at draw time, not from a snapshot: main() can advance
the phase mid-frame, and a phase recorded a flip ago attributes the button to
the wrong one.

HUNGRY VOID GETS AN EXTRA COLUMN no T'au button could give. Its printed WHEN is
"Fight phase." with no "Your", so it must be drawn in BOTH players' Fight
phases - and MovementController.can_select() admits both players there
(12.02/12.04), so the real loop can show it.

Usage:  python verify_necron_stratagem_buttons.py [map2] [frames]
        python verify_necron_stratagem_buttons.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import config, detachments
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND, PHASE_FIGHT,
                       PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker)
from game.renderer import Renderer
from game.ui import action_panel as _panel_mod
from game.ui import button_style

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
FOE = "Player 2"
MIN_FRAMES = 1200      # below this, "undrawn" means "not yet", not "never"

# TRANSCRIBED from rules/necrons/detachments/Awakened Dynasty.md, deliberately
# not imported: the probe and the suite are then two independent statements of
# one table. `owner` is whether the printed WHEN says "Your".
WHEN = {
    "Hungry Void": ({PHASE_FIGHT}, False),
    "Sudden Storm": ({PHASE_MOVEMENT}, True),
    "Conquering Tyrant": ({PHASE_SHOOTING}, True),
}

SETTING = "AWAKENED_DYNASTY_PLAYERS"

state = {"frames": 0, "selected": 0, "seen": {}, "off_when": [],
         "phases": set(), "tracker": None, "rotate": False,
         "foreign_fight": set(), "units": set()}

_real_draw_button = button_style.draw_button


def draw_button(surface, rect, label, font, hovered=False, pressed=False,
                accent=None):
    if accent == "stratagem":
        name = label.split(" (")[0].strip()
        if name in WHEN:
            tracker = state.get("tracker")
            phase = tracker.phase if tracker is not None else None
            owner = tracker.turn_owner if tracker is not None else None
            first = state["seen"].setdefault(
                name, {"frame": state["frames"], "phases": set()})
            if phase is not None:
                first["phases"].add(phase)
                if phase not in WHEN[name][0]:
                    state["off_when"].append((name, phase, state["frames"]))
                if owner == FOE:
                    state["foreign_fight"].add((name, phase))
    return _real_draw_button(surface, rect, label, font, hovered=hovered,
                             pressed=pressed, accent=accent)


button_style.draw_button = draw_button

if NEUTRALIZE:
    # THE BESPOKE KEYWORDS NEVER REACH THE PANEL - the "built but never fed"
    # shape, and the one the substring proof cannot tell from a working wire.
    # Everything else is untouched, so a report of 0 here is the panel path and
    # nothing else.
    _real_panel_draw = _panel_mod.ActionPanel.draw

    def _blind_draw(self, *a, **kw):
        for _name in ("hungry_void_controller", "sudden_storm_controller",
                      "conquering_tyrant_controller"):
            kw.pop(_name, None)
        return _real_panel_draw(self, *a, **kw)

    _panel_mod.ActionPanel.draw = _blind_draw

_real_apply = detachments.apply_to_config


def apply_to_config(*args, **kwargs):
    """WRAPPED, not pre-set: this writes every detachment setting from
    scratch, so a flag set before it runs would simply be erased."""
    out = _real_apply(*args, **kwargs)
    setattr(config, SETTING, (HUMAN,))
    return out


detachments.apply_to_config = apply_to_config

_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

_ORDER = (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE,
          PHASE_FIGHT)
_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    tracker = state.get("tracker")
    if tracker is not None and getattr(tracker, "started", True):
        phase = _ORDER[(state["frames"] // 40) % len(_ORDER)]
        tracker.phase_index = PHASES.index(phase)
        # EVERY THIRD PASS THROUGH THE FIGHT PHASE IS THE OPPONENT'S, which is
        # the column only this faction can produce: Hungry Void prints "Fight
        # phase." with no "Your", so it must still be drawn there.
        foreign = phase == PHASE_FIGHT and (state["frames"] // 200) % 2 == 1
        owner = FOE if foreign else HUMAN
        tracker.turn_owner = owner
        tracker.set_active(owner)
        tracker.battle_round = 2
        state["phases"].add(phase)
    # A DIFFERENT, COPRIME PERIOD from the phase rotation. Sharing one modulus
    # pairs unit i with phase i%5 for ever, so a unit whose WHEN names a phase
    # it is never selected in reports "not drawn" - a truthful-looking zero
    # produced entirely by the probe.
    if state["frames"] % 17 == 0:
        state["rotate"] = True
    state["frames"] += 1
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

_real_move_range = Renderer.draw_move_range


def draw_move_range(self, surface, board, movement_controller):
    """RE-SELECTED every frame, ROTATED every seventeen. A phase or turn change
    clears the pick and the panel draws no unit UI without one, so a single
    select() would give a handful of frames and a truthful-looking zero."""
    squads = []
    for token in movement_controller.all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is not None and squad.owner == HUMAN and squad not in squads:
            squads.append(squad)
    if squads and (state.pop("rotate", False)
                   or movement_controller.selected_squad is None):
        index = (state["frames"] // 17) % len(squads)
        movement_controller.select(squads[index].models[0])
    if movement_controller.selected_squad is not None:
        state["selected"] += 1
        state["units"].add(movement_controller.selected_squad.name)
    return _real_move_range(self, surface, board, movement_controller)


Renderer.draw_move_range = draw_move_range

# WHY an undrawn name was refused, MEASURED rather than guessed. An UNREACHED
# entry nobody checked is a story about the harness - the T'au probe's first
# two guesses turned out to be wrong.
from game import protocol_conquering_tyrant as _tyrant   # noqa: E402
from game import protocol_hungry_void as _void           # noqa: E402
from game import protocol_sudden_storm as _storm         # noqa: E402

_WATCH = {"Hungry Void": (_void.HungryVoidController, PHASE_FIGHT, False),
          "Sudden Storm": (_storm.SuddenStormController, PHASE_MOVEMENT, True),
          "Conquering Tyrant": (_tyrant.ConqueringTyrantController,
                                PHASE_SHOOTING, True)}


def _watch(name, cls, phase, owned):
    real = cls.can_use

    def can_use(self, squad):
        out = real(self, squad)
        if not out and squad is not None:
            tr = getattr(self, "turn_tracker", None)
            why = "target/ledger or CP clause"
            if tr is not None and tr.phase != phase:
                why = "phase"
            elif owned and tr is not None and squad.owner != tr.turn_owner:
                why = "owner"
            state.setdefault("why", {}).setdefault(name, set()).add(why)
        return out

    cls.can_use = can_use


for _n, (_c, _p, _o) in _WATCH.items():
    _watch(_n, _c, _p, _o)

_argv = sys.argv[1:] or ["map2", "2500"]
sys.argv = ["selfplay.py"] + _argv
# THE NECRONS AS PLAYER 1. config ships PLAYER2_ARMY = "necrons", so without
# this the probe measures the AI's army and reports a truthful zero for a
# question about the human's buttons.
config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "aeldari"
config.ARMY_SELECT = False

runpy.run_module("selfplay", run_name="__main__")

drawn = sorted(state["seen"])
missing = sorted(n for n in WHEN if n not in state["seen"])

print()
print("--- Necron Stratagem buttons"
      + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames / with a selection : %d / %d" % (state["frames"], state["selected"]))
print("  phases staged             : %s" % ", ".join(sorted(state["phases"])))
print("  units selected            : %d" % len(state["units"]))
print("  DRAWN %d/%d" % (len(drawn), len(WHEN)))
for name in drawn:
    info = state["seen"][name]
    print("     %-22s f%-6d %s" % (name, info["frame"],
                                   ",".join(sorted(info["phases"]))))
for name in missing:
    print("     %-22s NOT DRAWN  (measured refusal: %s)"
          % (name, ", ".join(sorted(state.get("why", {}).get(name, ["-"])))))
print("  off-WHEN sightings        : %d" % len(state["off_when"]))
for name, phase, frame in state["off_when"][:5]:
    print("     %s in %s at f%d" % (name, phase, frame))
print("  drawn in the OPPONENT's turn: %s"
      % (", ".join("%s/%s" % p for p in sorted(state["foreign_fight"])) or "none"))

ok = True
if state["frames"] < MIN_FRAMES or not state["selected"]:
    print("  INCONCLUSIVE - too few frames or no unit was ever selected")
    raise SystemExit(2)
if state["off_when"]:
    print("  FAIL - a button appeared outside its printed WHEN")
    ok = False
if not NEUTRALIZE:
    if missing:
        print("  FAIL - a button never reached the screen")
        ok = False
    # The Hungry Void column: it prints no "Your", so it MUST appear in the
    # opponent's Fight phase too. Absent that, the owner-blindness this suite
    # exists to prove is unmeasured.
    if not any(n == "Hungry Void" for n, _p in state["foreign_fight"]):
        print("  FAIL - Hungry Void never appeared in the opponent's Fight phase")
        ok = False
elif drawn:
    print("  FAIL - neutralized, but buttons still reached the panel")
    ok = False

print("  VERDICT: %s" % ("OK" if ok else "FAILED"))
raise SystemExit(0 if ok else 1)
