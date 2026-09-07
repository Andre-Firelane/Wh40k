"""The game menu, end to end through the REAL loop - including the restart.

test_game_menu.py drives the menu object directly, which proves the menu works
and proves nothing about main() honouring it. "Built, but never fed" is a
failure class this repo has shipped six times over, and a source guard only
shows that a call is WRITTEN, not that anything reaches it.

So this drives main.run() - the only harness that does, because run() is the
one thing the others never touch - and walks the whole shape of the feature:

  1. the STARTUP menu is up before any battlefield is picked, and Resume is
     disabled when there is no save to resume.
  2. Start New Game hands off: the map screen appears, a battle begins.
  3. ESC opens the menu over the running battle, and while it is open the AI
     is PAUSED - the claim no unit test can see, because the auto-play tick
     runs outside the event loop and so is not covered by the menu's own
     `continue`.
  4. Resume closes it and the battle carries on.
  5. The MENU button in the board's corner opens it too - the pre-chain claim,
     driven by RECT rather than by literal coordinates.
  6. Start New Game from inside a battle really restarts: main() returns,
     run() comes back round, the map screen is asked AGAIN, and the second
     battle is built on a DIFFERENT board in the same process. That last part
     is what proves no cached board or renderer survived from the first.
  7. Quit ends it, and pygame.quit() runs exactly once.

  --neutralize  rebuilds the pre-fix world (ESC quits outright, no menu, no
                button) and runs the same assertions. It MUST fail.

Usage:  python smoke_game_menu.py [--neutralize]
Uses MockAgent - no API calls.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

NEUTRALIZE = "--neutralize" in sys.argv[1:]
MAX_FRAMES = 3000

# Two DIFFERENT boards, so the restart cannot pass by rebuilding the same one.
FIRST_MAP = "map1"
SECOND_MAP = "map3"

pygame.init()

from game import config  # noqa: E402

config.PREGAME_DEPLOYMENT = True
config.MAP_SELECT = True          # the restart must come back HERE
config.ARMY_SELECT = False        # not what this smoke is about; keeps it short
config.START_MENU = not NEUTRALIZE
# The Tactical Secondary deck asks the human a question at the end of every one
# of their turns and this harness answers no prompt it was not written for.
config.SECONDARY_MISSION_CARD_PLAYERS = ()

from game.ui.game_menu import GameMenu  # noqa: E402
from game.ui.map_select import MapSelectScreen  # noqa: E402

state = {
    "frames": 0,
    "steps": [],           # what the harness clicked, in order
    "boards": [],          # which battlefield each battle was built on
    "startup_resume_enabled": None,
    "ai_paused_while_open": [],
    "board_visible_behind": None,
    "menu_draws": 0,
    "opened": [],
    "opened_by": [],
    "error": None,
}
report = []


def check(label, ok, detail=""):
    report.append((bool(ok), label, detail))


def _click(pos):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


def _frame_with(predicate):
    frame = sys._getframe(2)
    while frame is not None:
        if predicate(frame.f_locals):
            return frame.f_locals
        frame = frame.f_back
    return None


def _live_screen(cls):
    """The live screen of this type, found on the call stack - its own run()
    is what is calling pygame.event.get() right now."""
    found = _frame_with(lambda loc: isinstance(loc.get("self"), cls))
    return found["self"] if found else None


def _battle_locals():
    """main()'s own frame, identified by two locals only it has."""
    return _frame_with(lambda loc: "game_menu" in loc and "running" in loc)


def _entry(menu, action, screen_rect):
    for a, rect, enabled in menu.layout(screen_rect):
        if a == action and enabled:
            return rect
    return None


def fake_events():
    state["frames"] += 1
    if state["frames"] > MAX_FRAMES:
        raise SystemExit(0)
    screen = pygame.display.get_surface()
    screen_rect = screen.get_rect()

    # --- the map screen: pick whichever board this battle wants -------------
    picker = _live_screen(MapSelectScreen)
    if picker is not None:
        wanted = FIRST_MAP if not state["boards"] else SECOND_MAP
        picker.layout(screen_rect)
        if picker.selected is None or picker.selected.key != wanted:
            for tile in picker.tiles:
                if tile.battle_map.key == wanted:
                    return _click(tile.rect.center)
            # Not on this page. The headless window is 1024x768, which fits
            # two tiles, so the second battle's board genuinely lives on page
            # two - page over rather than giving up, or this harness would
            # only ever be able to ask for the first two maps.
            return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT})]
        if picker.footer.confirm is not None:
            state["steps"].append(f"map:{wanted}")
            return _click(picker.footer.confirm.center)
        return []                      # wait for the frame that draws the button

    # --- inside a battle ---------------------------------------------------
    battle = _battle_locals()
    if battle is not None:
        board_key = battle["battle_map"].key
        if not state["boards"] or state["boards"][-1] != board_key:
            state["boards"].append(board_key)
            # Per BATTLE, not per run: the second battle has to open the menu
            # for itself, and a global "have we pressed ESC yet" would leave it
            # idling until the frame cap.
            state["opened"] = []
        menu = battle["game_menu"]

        if menu.is_pending:
            # WHICH gesture actually opened it, recorded here rather than at
            # the press: pressing ESC proves nothing, the menu coming up does.
            if state["opened"] and state["opened"][-1] not in state["opened_by"]:
                state["opened_by"].append(state["opened"][-1])
            state["ai_paused_while_open"].append(bool(battle.get("ai_action_paused_this_frame")))
            if state["board_visible_behind"] is None:
                # The board is still drawn under the scrim - a menu that
                # replaced the frame would lose the position you paused on.
                state["board_visible_behind"] = battle["board_rect_screen"].width > 0
            if "resume" not in [s.split(":")[0] for s in state["steps"]]:
                rect = _entry(menu, "resume", screen_rect)
                if rect is not None:
                    state["steps"].append("resume")
                    return _click(rect.center)
            rect = _entry(menu, "new_game", screen_rect)
            if len(state["boards"]) == 1 and rect is not None:
                state["steps"].append("menu-new-game")
                return _click(rect.center)
            rect = _entry(menu, "quit", screen_rect)
            if rect is not None:
                state["steps"].append("quit")
                return _click(rect.center)
            return []

        opened = state["opened"]
        if not opened:
            opened.append("esc")
            state["steps"].append("esc")
            return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})]
        # Only the FIRST battle bothers with Resume and the button; the second
        # exists to be quit out of.
        if opened == ["esc"] and "resume" in state["steps"] and len(state["boards"]) == 1:
            opened.append("button")
            state["steps"].append("button")
            return _click(menu.button_rect(battle["board_rect_screen"]).center)
        return []

    # --- the startup menu --------------------------------------------------
    menu = _live_screen(GameMenu)
    if menu is not None:
        if state["startup_resume_enabled"] is None:
            state["startup_resume_enabled"] = [
                e for a, _l, e in menu.entries() if a == "resume"
            ][0]
        rect = _entry(menu, "new_game", screen_rect)
        if rect is not None:
            state["steps"].append("start-new-game")
            return _click(rect.center)
    return []


pygame.event.get = lambda *a, **k: fake_events()
pygame.mouse.get_pos = lambda *a, **k: (0, 0)
pygame.display.flip = lambda *a, **k: None
pygame.display.update = lambda *a, **k: None

_quit_calls = {"n": 0}
_real_quit = pygame.quit


def _counted_quit(*a, **k):
    _quit_calls["n"] += 1
    return _real_quit(*a, **k)


pygame.quit = _counted_quit

import main  # noqa: E402
from ai.mock_agent import MockAgent  # noqa: E402

main.ClaudeAgent = lambda *a, **k: MockAgent()

if NEUTRALIZE:
    # The pre-fix world, at the SOURCE rather than one flag of it: there was no
    # menu at all. START_MENU above takes the startup screen away; this takes
    # the in-game one, so ESC and the board button reach nothing - which is
    # what they did before this feature existed. Every check that the menu
    # earns must now fail.
    GameMenu.show = lambda self: None

_orig_draw = GameMenu.draw


def _spy_draw(self, surface, mouse_pos=None):
    state["menu_draws"] += 1
    return _orig_draw(self, surface, mouse_pos)


GameMenu.draw = _spy_draw

# There is no save in a throwaway folder, so Resume must be offered disabled -
# and pointing scene_io at one keeps this smoke from depending on whatever
# happens to be lying in scenes/.
import tempfile  # noqa: E402
from game import scene_io  # noqa: E402

_empty = tempfile.mkdtemp()
scene_io.SCENES_DIR = _empty

try:
    main.run()
except SystemExit:
    pass
except Exception as exc:  # noqa: BLE001 - reported, not raised, like the other smokes
    state["error"] = f"{type(exc).__name__}: {exc}"

print(f"\nneutralize={NEUTRALIZE} frames={state['frames']}")
print(f"steps: {state['steps']}")
print(f"boards: {state['boards']}")

if state["error"]:
    print("ERROR:", state["error"])
check("the run finished without an exception", state["error"] is None, str(state["error"]))

# 1. the startup menu
check("the startup menu was shown before any battlefield was picked",
      state["steps"][:1] == ["start-new-game"], str(state["steps"][:2]))
check("...with Resume disabled, there being no save to resume",
      state["startup_resume_enabled"] is False, str(state["startup_resume_enabled"]))

# 2. it hands off to the map screen and a battle begins
check("Start New Game reached the map screen", f"map:{FIRST_MAP}" in state["steps"])
check("...and a battle was built on it", state["boards"][:1] == [FIRST_MAP], str(state["boards"]))

# 3-4. ESC opens it over the battle, the AI stops, Resume closes it
check("ESC opened the menu during the battle", "esc" in state["opened_by"],
      str(state["opened_by"]))
check("the menu really drew over the running frame", state["menu_draws"] > 0,
      str(state["menu_draws"]))
check("the board was still there behind it", state["board_visible_behind"] is True)
check("the AI was paused on every frame the menu was open",
      bool(state["ai_paused_while_open"]) and all(state["ai_paused_while_open"]),
      str(state["ai_paused_while_open"][:8]))
check("Resume closed it and the battle carried on", "resume" in state["steps"])

# 5. the board button opens it too
check("the MENU button in the board's corner opened it", "button" in state["opened_by"],
      str(state["opened_by"]))

# 6. the restart - the part that cannot be faked
check("Start New Game was pressed inside a battle", "menu-new-game" in state["steps"])
check("...the map screen was asked a SECOND time", f"map:{SECOND_MAP}" in state["steps"])
check("...and a second battle ran in the same process", len(state["boards"]) == 2,
      str(state["boards"]))
check("...on a DIFFERENT board, so nothing cached survived",
      len(state["boards"]) == 2 and state["boards"][0] != state["boards"][1],
      str(state["boards"]))

# 7. quitting
check("Quit ended the application", "quit" in state["steps"])
check("the window was closed exactly once", _quit_calls["n"] == 1, str(_quit_calls["n"]))

passed = sum(1 for ok, _l, _d in report if ok)
print()
for ok, label, detail in report:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if not ok and detail else ""))
print(f"\n{passed}/{len(report)} checks passed  (game menu smoke)")
sys.exit(0 if passed == len(report) else 1)
