"""The log panel's filter click and wheel scroll actually reach it from main().

test_log_panel.py drives LogPanel directly, which proves the panel works and
proves nothing about the six lines of wiring in main()'s event chain - and a
view control that sits in the wrong branch of that chain fails silently, which
is the exact failure the wheel-zoom branch already carries a comment about.

So this drives main()'s REAL loop the way selfplay.py does, waits until the
game is running, and then feeds it a wheel event and a chip click positioned
from main()'s own `log_rect`. Both are only ever asserted through the panel's
public state, so this cannot pass by calling the handlers itself.

Usage:  python smoke_log_input.py [map_key]
Uses MockAgent - no API calls.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

MAP_KEY = sys.argv[1] if len(sys.argv) > 1 else "map2"
MAX_FRAMES = 4000

pygame.init()

from game.game_log import FAILED_ORDER  # noqa: E402
from game.ui.log_panel import ALL_FILTER  # noqa: E402

state = {"frames": 0, "armed": False, "stage": "wait", "results": {}, "seeded": False}


def _click(pos):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


def _main_locals():
    frame = sys._getframe(2)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


def fake_events():
    state["frames"] += 1
    if state["frames"] >= MAX_FRAMES:
        raise SystemExit(0)
    loc = _main_locals()

    if not state["armed"]:
        state["armed"] = True
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]

    panel = loc.get("log_panel")
    log_rect = loc.get("log_rect")
    game_log = loc.get("game_log")
    if panel is None or log_rect is None or game_log is None:
        return []

    # Enough entries that scrolling has somewhere to go, and at least one under
    # each filter. Seeded rather than waited for: what is being tested is the
    # wiring, not how long the AI takes to fail an order.
    if not state["seeded"]:
        for i in range(40):
            game_log.add(f"seeded log line {i}")
        game_log.add("seeded: a unit could not carry out its order", category=FAILED_ORDER)
        state["seeded"] = True
        return []

    results = state["results"]
    stage = state["stage"]

    if stage == "wait":
        # One frame with nothing injected, so the panel has drawn once and its
        # chip rects exist.
        #
        # The log must not reach the "Next Phase" button. A first version of the
        # taller log derived its height from a measurement of the Game Status
        # panel taken WITHOUT a mission controller, so in the real game - where
        # that panel is taller - the log covered the button and there was no way
        # to advance the phase at all. Measured here, in the running game, so
        # that cannot come back silently.
        status = loc.get("game_status_panel")
        button = getattr(status, "_button_rect", None)
        if button is not None:
            state["results"]["button_gap"] = log_rect.top - button.bottom
        state["stage"] = "scroll"
        return []

    if stage == "scroll":
        results["scroll_before"] = panel.scroll
        state["stage"] = "check_scroll"
        return [pygame.event.Event(pygame.MOUSEWHEEL, {"x": 0, "y": 1, "flipped": False,
                                                       "precise_x": 0.0, "precise_y": 1.0,
                                                       "touch": False, "which": 0})]

    if stage == "check_scroll":
        results["scroll_after"] = panel.scroll
        chips = dict(panel._chips)
        results["filter_before"] = panel.filter
        target = chips.get(FAILED_ORDER)
        if target is None:
            results["error"] = "no Failed chip was drawn"
            raise SystemExit(0)
        results["chip_rect"] = tuple(target)
        results["chip_inside_panel"] = bool(log_rect.contains(target))
        state["stage"] = "check_click"
        return _click(target.center)

    if stage == "check_click":
        results["filter_after"] = panel.filter
        results["visible_under_filter"] = panel._visible_count
        raise SystemExit(0)

    return []


# The wheel event must be delivered while the cursor is OVER the log panel:
# main() reads pygame.mouse.get_pos() for it, not event.pos.
def _mouse_pos():
    loc = _main_locals()
    rect = loc.get("log_rect")
    return rect.center if rect is not None else (0, 0)


pygame.event.get = lambda *a, **k: fake_events()
pygame.mouse.get_pos = _mouse_pos
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

main.ClaudeAgent = lambda *a, **k: MockAgent()

try:
    main.main(MAP_KEY)
except SystemExit:
    pass

r = state["results"]
print(f"\nlog input smoke ({MAP_KEY}), {state['frames']} frames")
failures = []


def check(label, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{'   ' + detail if detail else ''}")
    if not condition:
        failures.append(label)


if "error" in r:
    check(r["error"], False)
else:
    check("the wheel over the log scrolls it", r.get("scroll_after", 0) > r.get("scroll_before", 0),
          f"{r.get('scroll_before')} -> {r.get('scroll_after')}")
    check("the Failed chip is drawn inside the log panel", r.get("chip_inside_panel", False),
          str(r.get("chip_rect")))
    check("the panel starts unfiltered", r.get("filter_before", "?") is ALL_FILTER)
    check("clicking the chip selects that filter", r.get("filter_after") == FAILED_ORDER,
          f"{r.get('filter_before')} -> {r.get('filter_after')}")
    check("the filtered view is smaller than the whole log",
          0 < r.get("visible_under_filter", 0) < 41, f"{r.get('visible_under_filter')} entries")
    check("the log does not cover the Next Phase button",
          r.get("button_gap", -1) > 0, f"gap {r.get('button_gap')} px")

print(f"\n{'OK' if not failures else 'FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
