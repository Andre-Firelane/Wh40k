"""The line-formation drag through main()'s REAL loop.

WHY A SMOKE. test_line_drag.py proves each link: the geometry (an overlap audit
over 39k pairs), the two controller halves, the InputManager gesture, and source
guards over main.py. What none of them can reach is the CHAIN - that a real
right-press in a real frame opens the drag, that the polled continuation
actually runs, and that the release commits. And the chain is precisely where
this feature's risk lives: main.py's event loop is ~48 if/elif branches, forty
of which gate on controller state with no event.type term, so a button-3 press
placed anywhere inside it is swallowed in exactly the states a player would use
it in.

WHAT IT DRIVES, in order:
  1. a right-drag over one of the human's own units - does it form up along the
     line, and does the readout describe what really happened
  2. the same gesture with a modal pending - the START must be refused
  3. a live drag whose button goes up with no MOUSEBUTTONUP ever arriving (the
     ALT+TAB shape) - the poll must end it rather than leave a gesture
     rewriting model positions forever

--neutralize restores the pre-fix world - the press and the poll become no-ops,
which is what "no route to this gesture from here" looked like - and MUST fail:
6 of the 13 checks fall. The survivors are honest - they describe a drag that
never opened, so "refuses while blocked", "releasing closes it" and "the poll
ends it" are all trivially true.

Uses MockAgent - no API calls.

Run: python smoke_line_drag.py [map] [--neutralize]
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

from game import config  # noqa: E402

state = {"frames": 0, "armed": False, "stage": "settle", "rec": {}, "error": None,
         "on_model": None, "line_a": None, "line_b": None, "rmb": False}


def _main_locals():
    frame = sys._getframe(2)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


def _press(pos, button=1):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": button})]


def _release(pos, button=1):
    return [pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": button})]


def _motion(pos):
    return [pygame.event.Event(pygame.MOUSEMOTION,
                               {"pos": pos, "rel": (1, 1), "buttons": (0, 0, 1), "touch": False})]


def _click(pos):
    return _press(pos) + _release(pos)


def _clear_the_way(loc):
    for name in ("turn_start_overlay", "turn_plan_overlay", "mission_draw_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay",
                 "fight_warning_overlay"):
        overlay = loc.get(name)
        if overlay is not None and getattr(overlay, "is_pending", False):
            return _click((10, 10))
    decisions = loc.get("decision_manager")
    if decisions is not None and decisions.is_pending:
        decisions.choose(0)
        return []
    dice_manager = loc.get("dice_manager")
    if dice_manager is not None and dice_manager.is_pending:
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        return _click((w - 8, h - 8))
    return None


def _drive_pregame(loc):
    pending = _clear_the_way(loc)
    if pending:
        return pending
    pregame_ctrl = loc.get("pregame_controller")
    if pregame_ctrl is None or not getattr(pregame_ctrl, "is_active", False):
        return None
    if (pregame_ctrl.state == "deploying"
            and pregame_ctrl.active_player == pregame_ctrl.human_player
            and pregame_ctrl.selected_unit is None):
        units = pregame_ctrl.pending_units(pregame_ctrl.human_player)
        if units:
            pregame_ctrl.select_unit(units[0])
            return []
    buttons = getattr(loc.get("action_panel"), "_buttons", [])
    if buttons:
        return _click(buttons[0][0].center)
    return []


def _own_model_pos(loc):
    """A screen pixel over a model of the unit whose turn it is - asked of
    main()'s own input_manager, so the screen -> camera -> board mapping under
    test is the production one."""
    im = loc["input_manager"]
    board = loc["board"]
    rect = loc["board_rect_screen"]
    tokens = loc["state"].tokens
    active = loc["movement_controller"].turn_tracker.active_player
    for gy in range(3, 100, 2):
        for gx in range(3, 100, 2):
            pos = (rect.x + rect.width * gx // 100, rect.y + rect.height * gy // 100)
            hit = im.token_at_event(tokens, board, pos)
            if hit is not None and hit.squad is not None and hit.squad.owner == active:
                if len(hit.squad.models) >= 4:
                    return pos
    return None


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
    mc = loc.get("movement_controller")
    if im is None or mc is None or loc.get("board_rect_screen") is None:
        return []

    rec = state["rec"]
    stage = state["stage"]

    if stage == "settle":
        if not loc["turn_tracker"].started:
            pending = _drive_pregame(loc)
            return pending if pending is not None else []
        clearing = _clear_the_way(loc)
        if clearing is not None:
            return clearing
        pos = _own_model_pos(loc)
        if pos is None:
            state["error"] = "no usable own model found on the board"
            raise SystemExit(0)
        state["on_model"] = pos
        state["stage"] = "to_movement"
        # Auto-play OFF: the AI advancing phases underneath would clear the
        # selection and the move between stages. Same reason smoke_selection.py
        # turns it off here.
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]

    if stage == "to_movement":
        # Into the Movement phase through main()'s own "Next Phase" button.
        # The gesture promotes a unit via can_make_move(), which is rule 09.05
        # and therefore phase-gated - left in the Command phase every press
        # would be refused and the whole run would look like a wiring failure.
        clearing = _clear_the_way(loc)
        if clearing is not None:
            return clearing
        if loc["turn_tracker"].phase == "Movement":
            # Re-find: advancing the phase can have moved things.
            pos = _own_model_pos(loc)
            if pos is None:
                state["error"] = "no usable own model once the Movement phase began"
                raise SystemExit(0)
            state["on_model"] = pos
            state["stage"] = "blocked_press"
            return []
        rect = getattr(loc.get("game_status_panel"), "_button_rect", None)
        if rect is None:
            state["error"] = "no Next Phase button to click"
            raise SystemExit(0)
        return _click(rect.center)

    if stage == "blocked_press":
        # A modal owns the board's clicks: the START must be refused. Raised
        # through main()'s own decision_manager so the gate is the real one.
        decisions = loc.get("decision_manager")
        if decisions is not None and not decisions.is_pending:
            decisions.request("Player 1", "smoke", [("a", lambda: None), ("b", lambda: None)])
        state["rmb"] = True
        state["stage"] = "after_blocked_press"
        return _press(state["on_model"], button=3)

    if stage == "after_blocked_press":
        rec["blocked_opened_a_drag"] = im.line_drag_active
        state["rmb"] = False
        decisions = loc.get("decision_manager")
        if decisions is not None and decisions.is_pending:
            decisions.choose(0)
        state["stage"] = "settle2"
        return _release(state["on_model"], button=3)

    if stage == "settle2":
        clearing = _clear_the_way(loc)
        if clearing is not None:
            return clearing
        state["stage"] = "press"
        return []

    if stage == "press":
        state["rmb"] = True
        state["stage"] = "drag"
        return _press(state["on_model"], button=3)

    if stage == "drag":
        rec["opened"] = im.line_drag_active
        rec["squad"] = getattr(im.line_drag_squad, "name", None)
        if im.line_drag_squad is not None:
            rec["before"] = [(m.x_in, m.y_in) for m in im.line_drag_squad.models]
        # Drag sideways along the board, which is what asks for a wide front.
        far = (state["on_model"][0] + 180, state["on_model"][1])
        state["line_a"] = state["on_model"]
        state["line_b"] = far
        state["stage"] = "after_drag"
        return _motion(far)

    if stage == "drag_under_modal":
        # A modal appearing MID-drag must not freeze the gesture. This is the
        # check that makes the poll's placement load-bearing: inside the event
        # chain the continuation would be swallowed by the first pending state,
        # which is exactly where a player is most likely to be mid-gesture.
        decisions = loc.get("decision_manager")
        if decisions is not None and not decisions.is_pending:
            decisions.request("Player 1", "smoke2",
                              [("a", lambda: None), ("b", lambda: None)])
        rec["mid_drag_still_open"] = im.line_drag_active
        # Straight back toward the anchor: a much shorter line asks for a
        # narrower front, so the block has to visibly re-form.
        nearer = (state["line_a"][0] + 20, state["line_a"][1] + 90)
        state["line_b"] = nearer
        state["stage"] = "after_modal_drag"
        return _motion(nearer)

    if stage == "after_modal_drag":
        info = im.line_drag_info
        rec["mid_drag_frontage"] = None if info is None else info.frontage
        rec["mid_drag_positions"] = (
            None if im.line_drag_squad is None
            else [(m.x_in, m.y_in) for m in im.line_drag_squad.models])
        decisions = loc.get("decision_manager")
        if decisions is not None and decisions.is_pending:
            decisions.choose(0)
        state["stage"] = "release"
        return []

    if stage == "after_drag":
        info = im.line_drag_info
        rec["info"] = None if info is None else {
            "frontage": info.frontage, "ranks": info.ranks, "short": info.short,
            "groups": info.groups, "widest": round(info.widest_in, 2),
            "legal": info.legal_frontages,
        }
        if im.line_drag_squad is not None:
            rec["after"] = [(m.x_in, m.y_in) for m in im.line_drag_squad.models]
        rec["squad_ref"] = im.line_drag_squad
        rec["frontage_before_modal"] = None if info is None else info.frontage
        state["stage"] = "drag_under_modal"
        return []

    if stage == "release":
        state["rmb"] = False
        state["stage"] = "after_release"
        return _release(state["line_b"], button=3)

    if stage == "after_release":
        rec["closed_on_release"] = not im.line_drag_active
        state["stage"] = "failsafe_press"
        return []

    if stage == "failsafe_press":
        clearing = _clear_the_way(loc)
        if clearing is not None:
            return clearing
        pos = _own_model_pos(loc)
        if pos is None:
            rec["failsafe_ended"] = "no second unit available"
            raise SystemExit(0)
        state["on_model"] = pos
        state["rmb"] = True
        state["stage"] = "failsafe_drop"
        return _press(pos, button=3)

    if stage == "failsafe_drop":
        rec["failsafe_opened"] = im.line_drag_active
        # The ALT+TAB shape: the button is no longer held, and NO MOUSEBUTTONUP
        # ever arrives. Only the poll can notice.
        state["rmb"] = False
        state["stage"] = "after_failsafe"
        return []

    if stage == "after_failsafe":
        rec["failsafe_ended"] = not im.line_drag_active
        rec["still_running"] = True
        raise SystemExit(0)

    return []


pygame.event.get = lambda *a, **k: fake_events()
_real_get_pressed = pygame.mouse.get_pressed
pygame.mouse.get_pressed = lambda *a, **k: (False, False, state["rmb"])

config.ARMY_SELECT = False
config.MAP_SELECT = False
config.SECONDARY_MISSION_CARD_PLAYERS = ()

import main  # noqa: E402
from ai.mock_agent import MockAgent  # noqa: E402
from game.input_handler import InputManager  # noqa: E402

main.ClaudeAgent = lambda *a, **k: MockAgent()

if NEUTRALIZE:
    # The pre-fix world, whole: no route to the gesture at all. Both entry
    # points stubbed, which is what a button-3 press swallowed by the chain and
    # a continuation that never ran would look like from out here.
    InputManager.begin_line_drag = lambda self, *a, **k: False
    InputManager.update_line_drag = lambda self, right_held: None

try:
    main.main(MAP_KEY)
except SystemExit:
    pass
finally:
    pygame.mouse.get_pressed = _real_get_pressed

print(f"\nline drag smoke ({MAP_KEY}), {state['frames']} frames"
      + ("   [NEUTRALIZED - expected to fail]" if NEUTRALIZE else ""))
failures = []


def check(label, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{'   ' + detail if detail else ''}")
    if not condition:
        failures.append(label)


rec = state["rec"]
if state["error"]:
    check(state["error"], False)
else:
    check("a modal pending refuses to OPEN a drag", rec.get("blocked_opened_a_drag") is False,
          str(rec.get("blocked_opened_a_drag")))
    check("a right-press on an own unit opens one", rec.get("opened") is True,
          str(rec.get("squad")))
    info = rec.get("info")
    check("the polled continuation really ran", info is not None, str(info))
    if info:
        check("...asking for a real frontage", info["frontage"] >= 1, str(info["frontage"]))
        check("...with the ranks that follow from it", info["ranks"] >= 1, str(info["ranks"]))
        check("...and a legal-frontage window swept up front",
              isinstance(info["legal"], tuple), str(info["legal"]))
    before, after = rec.get("before"), rec.get("after")
    check("the unit actually moved", before is not None and after is not None and before != after,
          f"{None if not before else before[:2]} -> {None if not after else after[:2]}")
    check("a modal raised MID-drag does not close it",
          rec.get("mid_drag_still_open") is True)
    # Positions, not the frontage: with a small unit the frontage is capped at
    # its own size, so it can be unchanged while the block really did re-form.
    check("...and the drag keeps re-laying the block under it",
          rec.get("mid_drag_positions") is not None
          and rec.get("mid_drag_positions") != rec.get("after"),
          f"frontage {rec.get('frontage_before_modal')} -> {rec.get('mid_drag_frontage')}")
    check("releasing closes the drag", rec.get("closed_on_release") is True)
    check("a second drag opens", rec.get("failsafe_opened") is True)
    check("...and the poll ends it when the button goes up with no event",
          rec.get("failsafe_ended") is True, str(rec.get("failsafe_ended")))
    check("...without taking the game down with it", rec.get("still_running") is True)

print(f"\n{'OK' if not failures else 'FAILED: ' + ', '.join(f.strip() for f in failures)}")
sys.exit(1 if failures else 0)
