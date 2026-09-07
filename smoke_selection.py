"""Unit selection through main()'s REAL loop: click a model, does the unit
actually end up picked AND drawn - and do the two ways of letting go work.

WHY A SMOKE AND NOT ONLY A SUITE. test_unit_selection.py proves each link on
its own: the renderer draws a unit outline (pixels), main.py contains the call
(source guard), InputManager selects and deselects (real events). What no suite
can reach is the CHAIN - that a real click in a real frame reaches
MovementController, and that main.py then hands that live selection to the
renderer. This repo has been bitten six times by a controller that was built,
unit-tested, and never fed (VengefulStarsController, the mark wiring, Path of
the Outcast's dice acknowledgement, move_exceptions' turn sweep, the overflight
controller, KrootPackmatesController), and a source guard only says the call is
written, not that it runs.

Driven the way smoke_measure_tool.py and smoke_log_input.py drive it: real
events into main()'s own event chain, positions found by asking main()'s own
input_manager so the screen -> camera -> board -> inches mapping under test is
the production one.

--neutralize restores the pre-fix world - the press deselects immediately again
and the renderer is handed nothing - and MUST fail: 6 of the 9 checks survive,
3 fall, and the three that fall are exactly what the fix buys (the renderer
being handed the live selection, it being the same unit, and a camera pan not
letting go).

The six survivors are honest, not slack. Four describe behaviour that was
already correct before this work (a click picks a unit, it is anchored on one
of its models, a click into the void lets go, a unit can be picked up again).
The other two are the ESC rung, which is a BRANCH in main.py's source rather
than a callable and so cannot be stubbed from out here - test_unit_selection.py
carries an A/B probe for it instead ("ESC back to fullscreen quit only"), which
does bite.

Uses MockAgent - no API calls.

Run: python smoke_selection.py [map] [--neutralize]
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
         "draw_calls": [], "on_model": None, "empty": None}


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
                               {"pos": pos, "rel": (1, 1), "buttons": (1, 0, 0), "touch": False})]


def _click(pos):
    return _press(pos) + _release(pos)


def _esc():
    return [pygame.event.Event(pygame.KEYDOWN,
                               {"key": pygame.K_ESCAPE, "mod": 0, "unicode": "", "scancode": 41})]


def _drive_pregame(loc):
    """Get to battle round 1 - the same short way smoke_measure_tool.py does.
    Only the waiting rooms that belong to the HUMAN; Player 2's own side of
    rule 03.01 is driven by main()'s auto-play."""
    for name in ("turn_start_overlay", "turn_plan_overlay",
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


def _clear_the_way(loc):
    """Events that dismiss whatever modal owns the board's clicks right now, or
    None once nothing does.

    Needed because battle round 1 opens with the turn-start banner still up:
    the very first gesture after the pre-game was being spent dismissing that
    instead of selecting, so the first click silently did nothing while a later
    one worked. Exactly the state-gated-chain hazard this whole feature is
    about, met in the harness rather than in the code."""
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


def _positions(loc):
    """A screen pixel over one of the HUMAN's own models, and one over empty
    ground. Asked of main()'s own input_manager for the reason
    smoke_measure_tool.py gives: a re-derivation could agree with itself while
    both are wrong."""
    im = loc["input_manager"]
    board = loc["board"]
    rect = loc["board_rect_screen"]
    tokens = loc["state"].tokens
    human = loc["movement_controller"].turn_tracker.active_player
    on_model = None
    empty = None
    for gy in range(3, 100, 2):
        for gx in range(3, 100, 2):
            pos = (rect.x + rect.width * gx // 100, rect.y + rect.height * gy // 100)
            hit = im.token_at_event(tokens, board, pos)
            if hit is not None and on_model is None:
                if hit.squad is not None and hit.squad.owner == human:
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
        # Auto-play for Player 2, exactly as the other smokes arm it.
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
        # Round 1 opens with the turn banner up; clear it before spending the
        # first gesture on it. Re-checked before every later gesture too.
        clearing = _clear_the_way(loc)
        if clearing is not None:
            return clearing
        on_model, empty = _positions(loc)
        if on_model is None or empty is None:
            state["error"] = f"no usable board positions found (model={on_model}, empty={empty})"
            raise SystemExit(0)
        state["on_model"] = on_model
        state["empty"] = empty
        state["stage"] = "select"
        # Auto-play OFF again now that the pre-game is done (Shift+A toggles
        # it). It was only ever needed to get Player 2 deployed; leaving it on
        # means the AI keeps advancing phases underneath the gestures below,
        # and main.py's own advance paths call select(None) - which silently
        # cleared the pick between recording it and using it. That made this
        # smoke pass standalone and fail inside run_tests.py --smoke.
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]

    # Every stage past settle: never spend a gesture on a modal that owns the
    # board's clicks. One guard rather than one per stage, because the AI's own
    # turn can raise a banner or a roll between any two of them.
    clearing = _clear_the_way(loc)
    if clearing is not None:
        return clearing

    if stage == "select":
        state["stage"] = "after_select"
        return _click(state["on_model"])

    if stage == "reselect_for_esc":
        # Re-found rather than reusing the cached pixel: turns flip while this
        # runs, and can_select() refuses a unit that is not the active
        # player's, so the model that was selectable ten frames ago need not
        # be now. The first version cached it, the re-click silently selected
        # nothing, and ESC then fell through to its fullscreen-quit rung and
        # ended the run - which the checks reported as ESC "working".
        on_model, _ = _positions(loc)
        if on_model is None:
            return []
        state["stage"] = "after_reselect"
        return _click(on_model)

    if stage == "after_select":
        rec["selected_squad"] = getattr(mc.selected_squad, "name", None)
        rec["anchor_is_a_model"] = (
            mc.selected_model is not None
            and mc.selected_squad is not None
            and mc.selected_model in mc.selected_squad.models
        )
        # Whether main.py actually handed that live selection to the renderer
        # during a frame - the link no source guard can prove.
        state["draw_calls"] = []
        state["stage"] = "watch_draw"
        return []

    if stage == "watch_draw":
        rec["drawn_squad"] = state["draw_calls"][-1] if state["draw_calls"] else None
        state["stage"] = "pan"
        return []

    if stage == "pan":
        # THE REPORTED ANNOYANCE: a press on empty ground that travels is a
        # camera pan, and it used to throw the selection away.
        state["stage"] = "after_pan"
        far = (state["empty"][0] + 60, state["empty"][1] + 35)
        return _press(state["empty"]) + _motion(far) + _release(far)

    if stage == "after_pan":
        rec["squad_after_pan"] = getattr(mc.selected_squad, "name", None)
        state["stage"] = "void_click"
        return []

    if stage == "void_click":
        state["stage"] = "after_void_click"
        return _click(state["empty"])

    if stage == "after_void_click":
        rec["squad_after_void_click"] = getattr(mc.selected_squad, "name", None)
        state["stage"] = "reselect_for_esc"
        return []

    if stage == "after_reselect":
        # Record and press ESC in the SAME call, leaving no frame in between.
        # With auto-play armed the AI advances phases, and main.py's own
        # advance paths call select(None) - so a one-frame gap here let the
        # pick be cleared by somebody else, ESC then fell through to its
        # fullscreen-quit rung, and the run ended before this stage. It passed
        # standalone and failed inside run_tests.py --smoke: a flake, not a
        # difference in the code.
        picked = getattr(mc.selected_squad, "name", None)
        if picked is None:
            state["stage"] = "reselect_for_esc"
            return []
        rec["squad_before_esc"] = picked
        state["stage"] = "after_esc"
        return _esc()

    if stage == "after_esc":
        rec["squad_after_esc"] = getattr(mc.selected_squad, "name", None)
        rec["still_running"] = True
        raise SystemExit(0)

    return []


pygame.event.get = lambda *a, **k: fake_events()

config.ARMY_SELECT = False
config.MAP_SELECT = False
# This harness answers no prompt that belongs to the human outside the pre-game
# - the same reason every other smoke turns the deck off, and there is a source
# guard in test_secondary_missions.py requiring it.
config.SECONDARY_MISSION_CARD_PLAYERS = ()

import main  # noqa: E402
from ai.mock_agent import MockAgent  # noqa: E402
from game.input_handler import InputManager  # noqa: E402
from game.renderer import Renderer  # noqa: E402

main.ClaudeAgent = lambda *a, **k: MockAgent()

# Spy on the renderer rather than on main.py, so what is recorded is what the
# renderer was really handed on a real frame.
_real_draw_selection = Renderer.draw_selection


def _spy_draw_selection(self, surface, board, selection):
    squad = getattr(selection, "squad", None)
    if squad is not None:
        state["draw_calls"].append(squad.name)
    return _real_draw_selection(self, surface, board, selection)


Renderer.draw_selection = _spy_draw_selection

if NEUTRALIZE:
    # The pre-fix world, whole: the press deselects immediately (so a pan loses
    # the pick), ESC has no deselect rung, and the renderer is handed nothing.
    _real_handle = InputManager.handle_event

    def _pre_fix_handle(self, event, tokens, board, movement_controller, setup_controller=None):
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and setup_controller is not None
                and getattr(setup_controller, "state", None) != "placing"
                and getattr(movement_controller, "state", None) != "moving"):
            if self._find_token_at(tokens, *board.to_in(*self._local_pos(event.pos))) is None:
                movement_controller.select(None)
        return _real_handle(self, event, tokens, board, movement_controller, setup_controller)

    InputManager.handle_event = _pre_fix_handle
    Renderer.draw_selection = lambda self, surface, board, selection: None

try:
    main.main(MAP_KEY)
except SystemExit:
    pass

print(f"\nselection smoke ({MAP_KEY}), {state['frames']} frames"
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
    picked = rec.get("selected_squad")
    check("a click on a model picks its unit", picked is not None, str(picked))
    check("...anchored on one of that unit's own models", rec.get("anchor_is_a_model") is True)
    check("main.py really hands that live selection to the renderer",
          rec.get("drawn_squad") is not None, str(rec.get("drawn_squad")))
    check("...and it is the SAME unit the controller holds",
          rec.get("drawn_squad") == picked,
          f"{rec.get('drawn_squad')!r} vs {picked!r}")
    check("a camera pan does NOT let go of it",
          rec.get("squad_after_pan") == picked, str(rec.get("squad_after_pan")))
    check("a click on empty ground DOES let go of it",
          rec.get("squad_after_void_click") is None, str(rec.get("squad_after_void_click")))
    check("it can be picked up again", rec.get("squad_before_esc") is not None,
          str(rec.get("squad_before_esc")))
    # Sentinel, not .get(None): if this stage is never reached the key is
    # absent, and a plain .get() would read that as "ESC cleared it" - the
    # check would pass precisely when the run fell over before trying.
    after_esc = rec.get("squad_after_esc", "<never reached>")
    check("ESC lets go of it too", after_esc is None, str(after_esc))
    check("...and ESC did not quit the game out from under us",
          rec.get("still_running") is True)

print(f"\n{'OK' if not failures else 'FAILED: ' + ', '.join(f.strip() for f in failures)}")
sys.exit(1 if failures else 0)
