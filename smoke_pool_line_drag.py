"""Place a unit straight out of the pool AND form it up - one gesture, through
main()'s REAL loop.

THE REPORT this exists for: "wenn ich in der aufstellungsphase oder bei reserven
meine einheiten platzieren will, dann muss ich sie erstmal auf der map
platzieren und kann dann im 2ten schritt erst die drag-formation benutzen ...
kann das direkt aus der reserve heraus funktionieren? ohne zwischen step?"

WHY A SMOKE AND NOT A SUITE. The three moving parts are a click on a real card
in the Reserves strip, a right-press that main() turns into a placement via
_place_picked_unit(), and the polled continuation that lays the block out. The
first two live in main.py's ~48-branch event chain, and that chain is where
every earlier version of this gesture was swallowed. A unit test can drive
InputManager.begin_line_drag(start_placement=...) perfectly and still say
nothing about whether a press in a real frame ever reaches it - this repo has
six "built but never FED" cases on record.

THE LOAD-BEARING CHECK is the pair "nothing placed yet" / "placed AND dragging":
before the press the card is picked and setup_controller is IDLE, so nothing is
on the board; after the press the unit is PLACING and the line drag is live.
That pair IS the difference between one gesture and two, which is the only
thing the report was about.

The pre-game half is what gets driven here because it is reachable in a few
dozen frames. The Reserves half (rule 20.04) goes through the SAME main.py
helper - one function, whose reserve branch is source-guarded in
test_line_drag.py section 5 and exercised against a real IngressController in
section 4.

--neutralize removes the new route only (start_placement) and MUST fail: the
press then falls through to the Movement-phase branch, which refuses during the
pre-game, so nothing is placed and nothing forms up.

Uses MockAgent - no API calls.

Run: python smoke_pool_line_drag.py [map] [--neutralize]
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

args = [a for a in sys.argv[1:] if not a.startswith("--")]
NEUTRALIZE = "--neutralize" in sys.argv
MAP_KEY = args[0] if args else "map2"
MAX_FRAMES = 4000

pygame.init()

from game import config  # noqa: E402

state = {"frames": 0, "armed": False, "stage": "pick", "rec": {}, "error": None,
         "rmb": False, "card": None, "drop": None, "far": None}


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
    """Answer whatever modal is in front, so the gesture is measured against an
    open board rather than against a notice."""
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


def _card_pixel(loc, low=4, high=12):
    """A screen pixel over a pool card whose unit is a workable size, asked of
    main()'s own ReservesPanel - so the strip under test is the real one and the
    hit test is the production one.

    Size-bounded on purpose: the drag below draws a short line, and a 21-model
    blob breaches rule 09.02's 9 inch spread at every frontage a short line can
    produce. That would be a finding about the drag length, not the wiring."""
    panel = loc.get("reserves_panel")
    rect = loc.get("reserves_panel_rect")
    if panel is None or rect is None:
        return None, None
    for gx in range(2, 100):
        for gy in range(20, 100, 20):
            pos = (rect.x + rect.width * gx // 100, rect.y + rect.height * gy // 100)
            squad = panel.squad_at(pos)
            if squad is not None and low <= len(squad.models) <= high:
                return pos, squad
    return None, None


def _legal_drop_pixel(loc, squad):
    """A screen pixel whose board position every model of `squad` may legally
    occupy, found by asking PregameController's own predicate.

    Screen to inches goes through camera.to_native_px() + board.to_in(), which
    is literally the pair main()'s own board branch uses - so a pixel that
    works here is a pixel that works there."""
    board = loc["board"]
    camera = loc["camera"]
    rect = loc["board_rect_screen"]
    pre = loc["pregame_controller"]
    token = max(squad.models, key=lambda m: m.radius_in)
    for gy in range(10, 95, 3):
        for gx in range(10, 95, 3):
            pos = (rect.x + rect.width * gx // 100, rect.y + rect.height * gy // 100)
            local = camera.to_native_px((pos[0] - rect.x, pos[1] - rect.y))
            x_in, y_in = board.to_in(*local)
            if pre.position_valid(squad, token, x_in, y_in):
                return pos, (x_in, y_in)
    return None, None


def fake_events():
    state["frames"] += 1
    if state["frames"] >= MAX_FRAMES:
        state["error"] = f"never finished within {MAX_FRAMES} frames (stage {state['stage']})"
        raise SystemExit(0)
    loc = _main_locals()

    if not state["armed"]:
        # Auto-play ON so the AI deploys its own half of rule 03.01's
        # alternation; the human's units are still left to us.
        state["armed"] = True
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]

    im = loc.get("input_manager")
    pre = loc.get("pregame_controller")
    sc = loc.get("setup_controller")
    if im is None or pre is None or sc is None or loc.get("board_rect_screen") is None:
        return []

    rec = state["rec"]
    stage = state["stage"]

    if stage == "pick":
        clearing = _clear_the_way(loc)
        if clearing is not None:
            return clearing
        if pre.state != "deploying":
            if not pre.is_active:
                state["error"] = "the pre-game ended before a card could be picked"
                raise SystemExit(0)
            # Declare Battle Formations (03.01) comes first and is answered from
            # the left panel - the same way smoke_line_drag.py walks it. Only
            # ever clicked OUTSIDE the deploying state: in it, the panel's first
            # button is the AI auto-placer, which would put the unit down for us
            # and make the whole measurement meaningless.
            buttons = getattr(loc.get("action_panel"), "_buttons", [])
            return _click(buttons[0][0].center) if buttons else []
        if pre.active_player != pre.human_player:
            return []
        pos, squad = _card_pixel(loc)
        if pos is None:
            state["error"] = "no pool card of a workable size in the strip"
            raise SystemExit(0)
        state["card"] = squad
        state["stage"] = "after_pick"
        return _click(pos)

    if stage == "after_pick":
        # The click really picked a unit out of the strip, and NOTHING is on the
        # board yet - the "no intermediate step" half of the report.
        rec["picked"] = getattr(pre.selected_unit, "name", None)
        rec["awaiting_drop"] = pre.awaiting_drop
        rec["idle_before_press"] = sc.state
        if not pre.awaiting_drop:
            state["error"] = "clicking a pool card did not pick it"
            raise SystemExit(0)
        pos, at_in = _legal_drop_pixel(loc, pre.selected_unit)
        if pos is None:
            state["error"] = "no legal drop position found in the deployment zone"
            raise SystemExit(0)
        state["drop"] = pos
        rec["drop_in"] = (round(at_in[0], 2), round(at_in[1], 2))
        state["stage"] = "press"
        return []

    if stage == "press":
        state["rmb"] = True
        state["stage"] = "drag"
        return _press(state["drop"], button=3)

    if stage == "drag":
        # The press alone must have done BOTH: set the unit down and open the
        # gesture. Either one missing is the two-step this removes.
        rec["placing_after_press"] = sc.state
        rec["placed_squad"] = getattr(sc.setting_up_squad, "name", None)
        rec["opened"] = im.line_drag_active
        rec["drag_squad"] = getattr(im.line_drag_squad, "name", None)
        rec["on_board"] = (
            None if sc.setting_up_squad is None
            else all(m in loc["state"].tokens for m in sc.setting_up_squad.models))
        if sc.setting_up_squad is not None:
            rec["before"] = [(round(m.x_in, 3), round(m.y_in, 3))
                             for m in sc.setting_up_squad.models]
        # A SHORT line sideways: long enough to ask for more than one file,
        # short enough to stay inside rule 09.02's spread limit at the frontage
        # it produces - so the block it forms is one Confirm would accept.
        far = (state["drop"][0] + int(loc["board_rect_screen"].width * 0.06),
               state["drop"][1])
        state["far"] = far
        state["stage"] = "after_drag"
        return _motion(far)

    if stage == "after_drag":
        info = im.line_drag_info
        rec["info"] = None if info is None else {
            "frontage": info.frontage, "ranks": info.ranks, "short": info.short,
            "groups": info.groups, "widest": round(info.widest_in, 2),
            "limit": info.limit_in, "over": info.over_limit, "split": info.split,
            "legal": info.legal_frontages,
        }
        if sc.setting_up_squad is not None:
            rec["after"] = [(round(m.x_in, 3), round(m.y_in, 3))
                            for m in sc.setting_up_squad.models]
        state["stage"] = "release"
        return []

    if stage == "release":
        state["rmb"] = False
        state["stage"] = "after_release"
        return _release(state["far"], button=3)

    if stage == "after_release":
        rec["closed_on_release"] = not im.line_drag_active
        # A Set Up commits nothing on release - the placement stays open for
        # Confirm, exactly as a hand-dragged one does.
        rec["still_placing"] = sc.state
        rec["kept_formation"] = (
            None if sc.setting_up_squad is None
            else [(round(m.x_in, 3), round(m.y_in, 3)) for m in sc.setting_up_squad.models])
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
    # The pre-fix world: the gesture exists, but has no route to a unit that is
    # still in the pool. Everything else is untouched, so what falls is exactly
    # what the new route buys.
    _real_begin = InputManager.begin_line_drag

    def _no_placement_route(self, *a, **k):
        k.pop("start_placement", None)
        return _real_begin(self, *a, **k)

    InputManager.begin_line_drag = _no_placement_route

try:
    main.main(MAP_KEY)
except SystemExit:
    pass
finally:
    pygame.mouse.get_pressed = _real_get_pressed

print(f"\npool line-drag smoke ({MAP_KEY}), {state['frames']} frames"
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
    check("clicking a pool card picks the unit", rec.get("awaiting_drop") is True,
          str(rec.get("picked")))
    check("...and nothing is placed yet - no intermediate step",
          rec.get("idle_before_press") == "idle", str(rec.get("idle_before_press")))
    check("the right-press alone sets the unit down",
          rec.get("placing_after_press") == "placing",
          f"{rec.get('placed_squad')} at {rec.get('drop_in')}")
    check("...with its models really on the board", rec.get("on_board") is True)
    check("...and opens the line drag in the same press", rec.get("opened") is True)
    check("...on the unit that was just placed",
          rec.get("drag_squad") is not None and rec.get("drag_squad") == rec.get("placed_squad"),
          f"{rec.get('drag_squad')} / {rec.get('placed_squad')}")
    info = rec.get("info")
    check("the polled continuation really ran", info is not None, str(info))
    if info:
        check("...asking for a real frontage", info["frontage"] >= 1, str(info["frontage"]))
        check("...with the ranks that follow from it",
              info["ranks"] == -(-len(rec.get("before") or [1]) // info["frontage"]),
              str(info["ranks"]))
        check("...and a legal-frontage window swept up front",
              isinstance(info["legal"], tuple) and len(info["legal"]) > 0, str(info["legal"]))
        check("...the block it formed is one Confirm would accept",
              info["groups"] == 1 and not info["over"] and not info["split"],
              f"groups {info['groups']}, widest {info['widest']} of {info['limit']}")
    before, after = rec.get("before"), rec.get("after")
    check("the unit formed up along the line",
          before is not None and after is not None and before != after,
          f"{None if not before else before[:2]} -> {None if not after else after[:2]}")
    check("releasing closes the drag", rec.get("closed_on_release") is True)
    check("...and commits nothing - the placement waits for Confirm",
          rec.get("still_placing") == "placing", str(rec.get("still_placing")))
    check("...keeping the formation it drew", rec.get("kept_formation") == after)
    check("...without taking the game down with it", rec.get("still_running") is True)

print(f"\n{'OK' if not failures else 'FAILED: ' + ', '.join(f.strip() for f in failures)}")
sys.exit(1 if failures else 0)
