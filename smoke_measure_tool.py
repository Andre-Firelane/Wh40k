"""The ALT ruler works in the states that used to swallow it.

User report: "ich kann oft keine entfernungen messen. zb bei overwatch."

Reproduced statically first: main()'s event chain is a long if/elif over
CONTROLLER STATE, and both halves of the ruler sat near its END - the
KEYDOWN/KEYUP pair for ALT at branch 43, and InputManager.handle_event() (the
only thing that updated mouse_pos_in / hovered_token, i.e. the two fields
renderer.draw_measure_tool() draws from) as the very last branch. So any
pending Fire Overwatch offer / decision prompt / dice roll matched an earlier
branch whose body only handles mouse clicks, and the keystroke AND the motion
were dropped. Exactly the moments a distance matters most.

Driving InputManager directly would prove the class works and prove nothing
about which branch of main() it is wired into - which is the entire failure.
So this drives main()'s REAL loop the way smoke_log_input.py does, forces each
blocking state in turn, and reads the ruler only through input_manager's public
state.

A/B: run with `--neutralize` to put the pre-fix world back (both new entry
points stubbed out, leaving those states with no route to the ruler at all).
That must FAIL, or this smoke is not measuring what it claims to.

Usage:  python smoke_measure_tool.py [map_key] [--neutralize]
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
MAX_FRAMES = 6000

pygame.init()

from game import overwatch  # noqa: E402

# Every state that sits BEFORE the old ALT branch in main()'s chain and whose
# body only handles mouse clicks. Each is (label, install, clear) against
# main()'s own live controllers.
def _install_overwatch(loc):
    loc["fire_overwatch_controller"].state = overwatch.CHOOSING_UNIT


def _clear_overwatch(loc):
    loc["fire_overwatch_controller"].state = overwatch.IDLE


def _install_decision(loc):
    loc["decision_manager"].request("Player 1", "smoke: ruler probe", [("OK", None)])


def _clear_decision(loc):
    loc["decision_manager"].choose(0)


def _install_dice(loc):
    loc["dice_manager"].roll(1, label="smoke: ruler probe")


def _clear_dice(loc):
    loc["dice_manager"].acknowledge()


BLOCKERS = [
    ("Fire Overwatch (the reported case)", _install_overwatch, _clear_overwatch),
    ("a pending decision prompt", _install_decision, _clear_decision),
    ("a pending dice roll", _install_dice, _clear_dice),
]

state = {"frames": 0, "armed": False, "stage": "settle", "blocker": 0,
         "alt": False, "results": {}, "probe": {}, "error": None}


def _main_locals():
    frame = sys._getframe(2)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


_real_get_mods = pygame.key.get_mods


def _get_mods():
    # Only ALT is ever faked - handle_event() reads this for SHIFT too, and a
    # blanket return would silently change the Set Up block-drag gesture.
    return (pygame.KMOD_LALT if state["alt"] else 0)


def _motion(pos):
    return [pygame.event.Event(pygame.MOUSEMOTION, {"pos": pos, "rel": (1, 1), "buttons": (0, 0, 0),
                                                    "touch": False})]


def _click(pos):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


def _drive_pregame(loc):
    """Get to battle round 1, the short way selfplay.py already documents.

    Only the waiting rooms that belong to the HUMAN - Player 2's own side of
    rule 03.01 is driven by main()'s auto-play. Returns a (possibly empty)
    event list while the pre-game still owns the game, or None once it is over.
    """
    for name in ("turn_start_overlay", "turn_plan_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay"):
        overlay = loc.get(name)
        if overlay is not None and getattr(overlay, "is_pending", False):
            return _click((10, 10))

    dice_manager = loc.get("dice_manager")
    if dice_manager is not None and dice_manager.is_pending:
        # Deliberately NOT the left panel: main()'s dice branch routes clicks
        # there to the action panel and only acknowledges the roll elsewhere.
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


def _find_screen_positions(loc):
    """A screen pixel over some model, and one over empty ground.

    Found by asking main()'s own input_manager, so the whole screen ->
    camera -> board -> inches mapping under test is the production one rather
    than a re-derivation that could agree with itself while both are wrong.
    """
    im = loc["input_manager"]
    board = loc["board"]
    rect = loc["board_rect_screen"]
    tokens = loc["state"].tokens
    on_model = None
    empty = None
    for gy in range(4, 100, 3):
        for gx in range(4, 100, 3):
            pos = (rect.x + rect.width * gx // 100, rect.y + rect.height * gy // 100)
            hit = im.token_at_event(tokens, board, pos)
            if hit is not None and on_model is None:
                on_model = pos
            elif hit is None and empty is None:
                empty = pos
            if on_model is not None and empty is not None:
                return on_model, empty
    return on_model, empty


def fake_events():
    state["frames"] += 1
    if state["frames"] >= MAX_FRAMES:
        state["error"] = f"never finished within {MAX_FRAMES} frames (stage {state['stage']})"
        raise SystemExit(0)
    loc = _main_locals()

    if not state["armed"]:
        state["armed"] = True
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]

    im = loc.get("input_manager")
    if im is None or loc.get("board_rect_screen") is None:
        return []

    stage = state["stage"]

    if stage == "settle":
        # Get through rule 03.01 first, so the probe runs on a real deployed
        # board rather than on units still sitting in the reserves strip.
        if not loc["turn_tracker"].started:
            pending = _drive_pregame(loc)
            return pending if pending is not None else []
        on_model, empty = _find_screen_positions(loc)
        if on_model is None or empty is None:
            state["error"] = "could not find both an on-model and an empty screen pixel"
            raise SystemExit(0)
        state["probe"] = {"on_model": on_model, "empty": empty}
        state["stage"] = "install"
        return []

    if state["blocker"] >= len(BLOCKERS):
        raise SystemExit(0)

    label, install, clear = BLOCKERS[state["blocker"]]
    rec = state["results"].setdefault(label, {})
    on_model = state["probe"]["on_model"]
    empty = state["probe"]["empty"]

    if stage == "install":
        install(loc)
        rec["blocked"] = True
        # Park the pointer somewhere else first, so "the origin snapped to the
        # model" cannot be true just because it already was.
        im.mouse_pos_in = (-99.0, -99.0)
        im.hovered_token = None
        state["alt"] = True
        state["stage"] = "read_press"
        return _motion(on_model)

    if stage == "read_press":
        rec["measuring"] = im.measuring
        rec["origin_token"] = im.measure_origin_token is not None
        rec["origin_in"] = im.measure_origin_in
        rec["pos_after_first_motion"] = im.mouse_pos_in
        rec["hovered"] = im.hovered_token is not None
        state["stage"] = "read_drag"
        return _motion(empty)

    if stage == "read_drag":
        rec["pos_after_second_motion"] = im.mouse_pos_in
        rec["origin_still"] = im.measure_origin_in
        rec["still_measuring"] = im.measuring
        state["alt"] = False
        state["stage"] = "read_release"
        return []

    if stage == "read_release":
        rec["measuring_after_release"] = im.measuring
        rec["origin_after_release"] = im.measure_origin_in
        clear(loc)
        state["blocker"] += 1
        state["stage"] = "install" if state["blocker"] < len(BLOCKERS) else "done"
        return []

    raise SystemExit(0)


pygame.event.get = lambda *a, **k: fake_events()
pygame.key.get_mods = _get_mods
pygame.mouse.get_pos = lambda *a, **k: (0, 0)
pygame.display.flip = lambda *a, **k: None
pygame.display.update = lambda *a, **k: None

from game import config  # noqa: E402

# The army selection screen (game/ui/army_select.py) waits for a click, and
# nothing here answers one before main()'s own loop starts - so this harness
# fields whatever config.PLAYER1_ARMY/PLAYER2_ARMY say, exactly as every run
# of it did before that screen existed. smoke_army_select.py is the one that
# drives the screen for real.
config.ARMY_SELECT = False
# The map selection screen (game/ui/map_select.py) waits for a click too -
# same reason as ARMY_SELECT above.
config.MAP_SELECT = False
# The Tactical Secondary Mission deck asks the human a question at the end of
# every one of their turns, and this harness answers no prompt that belongs to
# the human outside the pre-game - so leaving it on would stall here on a
# decision nobody is present to make. Same reason ARMY_SELECT/MAP_SELECT are
# off above. test_secondary_missions.py has a source guard requiring this of
# every harness.
config.SECONDARY_MISSION_CARD_PLAYERS = ()

import main  # noqa: E402
from ai.mock_agent import MockAgent  # noqa: E402
from game.input_handler import InputManager  # noqa: E402

main.ClaudeAgent = lambda *a, **k: MockAgent()

if NEUTRALIZE:
    # The pre-fix world, whole rather than half of it: before the fix these
    # states reached NEITHER the ALT branches (swallowed by an earlier gate)
    # NOR handle_event()'s pointer tracking (the last branch of the same
    # chain). Stubbing both entry points is what "no route to the ruler from
    # here" looked like.
    InputManager.track_pointer = lambda self, event_pos, tokens, board: (
        self.mouse_pos_in[0], self.mouse_pos_in[1]
    )
    InputManager.update_measuring = lambda self, alt_held: None

try:
    main.main(MAP_KEY)
except SystemExit:
    pass

print(f"\nmeasure tool smoke ({MAP_KEY}), {state['frames']} frames"
      + ("   [NEUTRALIZED - expected to fail]" if NEUTRALIZE else ""))
failures = []


def check(label, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{'   ' + detail if detail else ''}")
    if not condition:
        failures.append(label)


if state["error"]:
    check(state["error"], False)
else:
    for label, _install, _clear in BLOCKERS:
        rec = state["results"].get(label, {})
        print(f"\n  while {label}:")
        check("    ALT starts the ruler", rec.get("measuring") is True)
        check("    the pointer is tracked at all", rec.get("pos_after_first_motion") not in (None, (-99.0, -99.0)),
              str(rec.get("pos_after_first_motion")))
        check("    the origin snaps to the model under the cursor", rec.get("origin_token") is True)
        first = rec.get("pos_after_first_motion")
        second = rec.get("pos_after_second_motion")
        check("    the far end follows the cursor", first is not None and second is not None and first != second,
              f"{first} -> {second}")
        check("    the origin stays put while the far end moves",
              rec.get("origin_in") is not None and rec.get("origin_in") == rec.get("origin_still"))
        check("    it is still measuring while ALT is held", rec.get("still_measuring") is True)
        check("    releasing ALT ends it", rec.get("measuring_after_release") is False
              and rec.get("origin_after_release") is None)

print(f"\n{'OK' if not failures else 'FAILED: ' + ', '.join(f.strip() for f in failures)}")
sys.exit(1 if failures else 0)
