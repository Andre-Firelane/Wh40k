"""The "you can still fight" warning, through main()'s REAL event chain.

User: "gib mal bitte ine warnung aus, die ich wegklicken muss, wenn ich auf
end turn klicke, obwohl ich noch mit einheiten im nahkampf kaempfen koennte."

test_fight_end_turn_warning.py proves the question and the overlay in
isolation, and reads main.py as text. Neither can prove the click actually
reaches the warning: main()'s event chain is a long if/elif over CONTROLLER
STATE and has swallowed an input five times (CLAUDE.md error class 15), and
this repo has three recorded cases of a controller that was built and never
fed. So this drives the real loop, the way smoke_measure_tool.py does, and
reads only what main()'s own live objects say.

The sequence under test is the whole point and cannot be checked one half at
a time:

    click End Turn  -> the turn does NOT end, the warning is up
    click anywhere  -> the warning is gone, the turn STILL has not ended
    click End Turn  -> now it ends

A/B: run with `--neutralize` to put the pre-fix world back (the warning never
intercepts, which is exactly what main.py did before). That must FAIL.

Usage:  python smoke_end_turn_warning.py [map_key] [--neutralize]
Uses MockAgent - no API calls.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

args = [a for a in sys.argv[1:] if not a.startswith("--")]
NEUTRALIZE = "--neutralize" in sys.argv
MAP_KEY = args[0] if args else "map2"
MAX_FRAMES = 8000

pygame.init()

from game.turn import PHASES, PHASE_FIGHT  # noqa: E402

HUMAN = "Player 1"
AI = "Player 2"

state = {"frames": 0, "stage": "auto_on", "error": None, "rec": {}, "settle": 0}


def _main_locals():
    frame = sys._getframe(2)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


def _click(pos):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


def _shift_a():
    return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                "unicode": "A", "scancode": 4})]


def _drive_pregame(loc):
    """Get to battle round 1 - the human's waiting rooms only; main()'s own
    auto-play drives Player 2's side of rule 03.01. Same shape as
    smoke_measure_tool.py's own copy."""
    for name in ("fight_warning_overlay", "turn_start_overlay", "turn_plan_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay"):
        overlay = loc.get(name)
        if overlay is not None and getattr(overlay, "is_pending", False):
            return _click((10, 10))

    dice_manager = loc.get("dice_manager")
    if dice_manager is not None and dice_manager.is_pending:
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        return _click((w - 8, h - 8))

    pregame_ctrl = loc.get("pregame_controller")
    if pregame_ctrl is None or not getattr(pregame_ctrl, "is_active", False):
        return None

    decisions = loc.get("decision_manager")
    if decisions is not None and decisions.is_pending:
        decisions.choose(0)
        return []
    if (pregame_ctrl.state == "deploying"
            and pregame_ctrl.active_player == pregame_ctrl.human_player
            and pregame_ctrl.selected_unit is None):
        pending = pregame_ctrl.pending_units(pregame_ctrl.human_player)
        if pending:
            pregame_ctrl.select_unit(pending[0])
            return []
    buttons = getattr(loc.get("action_panel"), "_buttons", [])
    if buttons:
        return _click(buttons[0][0].center)
    return []


def _clear_blockers(loc):
    """Answer whatever currently outranks the End Turn button in main()'s
    event chain. Returns the events to send, or None once nothing is left.

    Deliberately does NOT special-case fight_warning_overlay away: at this
    point in the run it can never be up (nothing has clicked End Turn yet),
    and skipping it here would hide a warning raised too early."""
    notice = loc["_front_notice"]()
    if notice is not None:
        return _click((10, 10))
    if loc["decision_manager"].is_pending:
        loc["decision_manager"].choose(0)
        return []
    if loc["dice_manager"].is_pending:
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        return _click((w - 8, h - 8))
    return None


def _squads_on_board(loc, owner):
    seen = {}
    for token in loc["state"].tokens:
        if token.squad is not None and token.squad.owner == owner:
            seen.setdefault(id(token.squad), token.squad)
    return list(seen.values())


def _stage_a_melee(loc):
    """Put one human and one AI unit into engagement range (03.04) in the
    middle of the board, and reach the Fight phase of the human's turn.

    Both are moved as RIGID, tightly packed rows: rule 09.02 coherency is one
    of the things main()'s End Turn gate checks first, so a sloppily scattered
    unit would block the click for the wrong reason and this smoke would pass
    while measuring nothing.

    The phase is reached by setting phase_index rather than by playing four
    phases out. That skips this turn's phase hooks, which is fine and
    deliberate: what is under test is the event chain around one button, not
    what a full turn does."""
    board = loc["board"]
    turn_tracker = loc["turn_tracker"]

    human = [s for s in _squads_on_board(loc, HUMAN) if len(s.models) <= 6]
    ai = [s for s in _squads_on_board(loc, AI) if len(s.models) <= 6]
    if not human or not ai:
        return "no small unit on the board for one of the players"
    human_squad = min(human, key=lambda s: len(s.models))
    ai_squad = min(ai, key=lambda s: len(s.models))

    cx, cy = board.width_in / 2.0, board.height_in / 2.0
    for i, model in enumerate(human_squad.models):
        model.x_in, model.y_in = cx + i * 1.1, cy
    for i, model in enumerate(ai_squad.models):
        model.x_in, model.y_in = cx + i * 1.1, cy + 1.6

    turn_tracker.turn_owner = HUMAN
    turn_tracker.set_active(HUMAN)
    turn_tracker.phase_index = PHASES.index(PHASE_FIGHT)

    # Rule 12.04: the Fight step cannot begin while any unit still owes a
    # Pile In, so without this begin_fight_step() returns straight away and
    # the controller sits in NOT_STARTED. The reported state is SELECTING -
    # "it is your turn to fight, pick a unit" - which is exactly the one
    # _has_unresolved_declaration() does not cover, so it is the one worth
    # measuring here. 12.03 makes piling in optional, and skip_pile_in() is
    # the same call the panel's own Skip button makes.
    pile_in = loc["pile_in_controller"]
    for _ in range(200):
        pending = [s for s in pile_in._all_squads() if pile_in.can_pile_in(s)]
        if not pending:
            break
        pile_in.skip_pile_in(pending[0])
    loc["fight_controller"].begin_fight_step()

    rec = state["rec"]
    rec["human_unit"] = human_squad.name
    rec["ai_unit"] = ai_squad.name
    rec["engaged"] = human_squad.is_engaged(loc["state"].tokens)
    rec["owed"] = [s.name for s in loc["fight_controller"].squads_that_could_still_fight(HUMAN)]
    rec["coherent"] = loc["coherency_enforcer"].check_end_of_turn(HUMAN)
    rec["is_last_phase"] = turn_tracker.is_last_phase
    rec["fight_state"] = loc["fight_controller"].state
    rec["fight_whose_turn"] = loc["fight_controller"].whose_turn
    return None


def _button_pos(loc):
    rect = loc["game_status_panel"]._button_rect
    return rect.center if rect is not None else None


def _turn_key(loc):
    tt = loc["turn_tracker"]
    return (tt.turn_owner, tt.phase, tt.battle_round)


def fake_events():
    state["frames"] += 1
    if state["frames"] >= MAX_FRAMES:
        state["error"] = f"never finished within {MAX_FRAMES} frames (stage {state['stage']})"
        raise SystemExit(0)
    loc = _main_locals()
    if loc.get("turn_tracker") is None:
        return []
    stage = state["stage"]
    rec = state["rec"]

    if stage == "auto_on":
        state["stage"] = "settle"
        return _shift_a()

    if stage == "settle":
        if not loc["turn_tracker"].started:
            pending = _drive_pregame(loc)
            return pending if pending is not None else []
        # Auto-play back OFF before staging anything: rule 12.04's Fight step
        # is SHARED, so an AI still allowed to act would be taking its own
        # half of the fight (and advancing phases) out from under the very
        # sequence being measured.
        state["stage"] = "auto_off"
        return _shift_a()

    if stage == "auto_off":
        err = _stage_a_melee(loc)
        if err:
            state["error"] = err
            raise SystemExit(0)
        state["stage"] = "clear"
        return []

    if stage == "clear":
        # Everything that sits ABOVE the End Turn button in main()'s chain has
        # to be answered first, or the click under test is swallowed by it and
        # this smoke would report the warning missing when the button was
        # never even reached. Measured: without this, the "Player 1 Turn 1"
        # banner was still up and every one of the three clicks below went
        # into it. Not a workaround - a human sees and dismisses that banner
        # too, long before they reach the Fight phase.
        pending = _clear_blockers(loc)
        if pending is not None:
            state["settle"] += 1
            if state["settle"] > 200:
                state["error"] = "something above the End Turn button never cleared"
                raise SystemExit(0)
            return pending
        state["stage"] = "click_1"
        return []

    if stage == "click_1":
        pos = _button_pos(loc)
        if pos is None:
            state["error"] = "the End Turn button was never drawn"
            raise SystemExit(0)
        rec["turn_before"] = _turn_key(loc)
        rec["diag"] = {
            "decision": loc["decision_manager"].is_pending,
            "dice": loc["dice_manager"].is_pending,
            "unresolved": loc["_has_unresolved_declaration"](),
            "fight_state": loc["fight_controller"].state,
            "notice": loc["_front_notice"]() is not None,
            "button_rect": loc["game_status_panel"]._button_rect,
            "right_panel": loc["right_panel_rect"],
        }
        rec["button_label_is_end_turn"] = loc["turn_tracker"].is_last_phase
        state["stage"] = "read_1"
        return _click(pos)

    if stage == "read_1":
        rec["warning_up"] = loc["fight_warning_overlay"].is_pending
        rec["turn_after_first_click"] = _turn_key(loc)
        rec["front_notice_is_warning"] = (
            loc["fight_warning_overlay"].is_pending
            and loc["_front_notice"]() is loc["fight_warning_overlay"])
        state["stage"] = "read_2"
        # Dismiss it the way a player would: a click that is NOT on the
        # button, to prove the dismissal is what cleared it.
        return _click((10, 10))

    if stage == "read_2":
        rec["warning_gone"] = not loc["fight_warning_overlay"].is_pending
        rec["turn_after_dismiss"] = _turn_key(loc)
        state["stage"] = "read_3"
        return _click(_button_pos(loc))

    if stage == "read_3":
        rec["turn_after_second_click"] = _turn_key(loc)
        rec["warning_still_gone"] = not loc["fight_warning_overlay"].is_pending
        raise SystemExit(0)

    raise SystemExit(0)


pygame.event.get = lambda *a, **k: fake_events()
pygame.mouse.get_pos = lambda *a, **k: (0, 0)
pygame.display.flip = lambda *a, **k: None
pygame.display.update = lambda *a, **k: None

from game import config  # noqa: E402

# Same three as every other harness here: the two pre-game screens wait for a
# click nobody answers before main()'s loop starts, and the Tactical Secondary
# deck asks the human a question at the end of each of their turns.
config.ARMY_SELECT = False
config.MAP_SELECT = False
config.SECONDARY_MISSION_CARD_PLAYERS = ()

import main  # noqa: E402
from ai.mock_agent import MockAgent  # noqa: E402
from game.ui.fight_warning_overlay import FightWarningOverlay  # noqa: E402

main.ClaudeAgent = lambda *a, **k: MockAgent()

if NEUTRALIZE:
    # The pre-fix world: the End Turn click was never intercepted at all.
    # Stubbing warn_once() (rather than deleting one call site) is what
    # main.py looked like before - the click went straight through to
    # advance_turn_phase() and the attacks were gone.
    # *a/**k: the overlay now carries a SECOND reason (Retro-thrusters), and
    # a one-armed stub would raise TypeError instead of neutralising.
    FightWarningOverlay.warn_once = lambda self, *a, **k: False

try:
    main.main(MAP_KEY)
except SystemExit:
    pass

rec = state["rec"]
print(f"\nEnd Turn warning smoke ({MAP_KEY}), {state['frames']} frames"
      + ("   [NEUTRALIZED - expected to fail]" if NEUTRALIZE else ""))
failures = []


def check(label, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{'   ' + detail if detail else ''}")
    if not condition:
        failures.append(label)


if state["error"]:
    check(state["error"], False)
else:
    print(f"\n  staged: {rec.get('human_unit')} vs {rec.get('ai_unit')}")
    check("the two units really are engaged (03.04)", rec.get("engaged") is True)
    check("the human is owed a fight (12.04)", bool(rec.get("owed")), str(rec.get("owed")))
    check("...and nothing else blocks the click", rec.get("coherent") is True)
    check("the fight step reached SELECTING (the reported state)",
          rec.get("fight_state") == "selecting",
          f"state={rec.get('fight_state')} whose_turn={rec.get('fight_whose_turn')}")
    check("the button really is End Turn (last phase)", rec.get("button_label_is_end_turn") is True)
    print(f"  diag: {rec.get('diag')}")

    print("\n  click 1 - End Turn:")
    check("    the warning comes up", rec.get("warning_up") is True)
    check("    ...and it is the notice being drawn", rec.get("front_notice_is_warning") is True)
    check("    the turn does NOT end", rec.get("turn_after_first_click") == rec.get("turn_before"),
          f"{rec.get('turn_before')} -> {rec.get('turn_after_first_click')}")

    print("\n  click 2 - anywhere (dismiss):")
    check("    the warning is gone", rec.get("warning_gone") is True)
    check("    the turn STILL has not ended", rec.get("turn_after_dismiss") == rec.get("turn_before"),
          f"-> {rec.get('turn_after_dismiss')}")

    print("\n  click 3 - End Turn again:")
    check("    now the turn ends", rec.get("turn_after_second_click") != rec.get("turn_before"),
          f"-> {rec.get('turn_after_second_click')}")
    check("    and it is not warned about twice", rec.get("warning_still_gone") is True)

print(f"\n{'OK' if not failures else 'FAILED: ' + ', '.join(f.strip() for f in failures)}")
sys.exit(1 if failures else 0)
