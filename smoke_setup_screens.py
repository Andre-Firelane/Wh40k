"""What the two pre-battle screens are clicked into actually reaches the board.

test_map_select.py and test_army_select.py drive the screens directly, which
proves the screens work and proves nothing about main() honouring them - and
"built, but never fed" is a failure class this repo has shipped three times
over (the Vengeful Stars controller, the mark wiring, Path of the Outcast). A
screen whose answer is computed and then dropped looks exactly like a working
screen.

So this drives main()'s REAL loop the way the other smokes do: it clicks a
BIOME button, then a map tile, then an army tile per player, and then asks the
built battlefield what it is, what it is painted in and what is standing on it.
Every click is deliberately something NO configuration produces - forest
against config's desert, map1 against config's map2, and Player 1 the ORKS with
Player 2 the AELDARI against config's aeldari/necrons - so a pass cannot come
from the defaults happening to agree.

It also pins the ORDER, which is the part that only shows up here: the map has
to be chosen before the board is built, and both before the armies, because on
a small board the map decides which units are fielded at all.

  --neutralize  turns both screens off and runs the same assertions, i.e.
                rebuilds the pre-fix world where a click cannot reach
                anything. It MUST fail.

Usage:  python smoke_setup_screens.py [--neutralize]
Uses MockAgent - no API calls.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

NEUTRALIZE = "--neutralize" in sys.argv[1:]
MAX_FRAMES = 4000

# What the clicks ask for. The map is NOT config.MAP and the pairing is not the
# configured one, so nothing here can pass by coincidence.
WANTED_MAP = "map1"
WANTED_BIOME = "forest"   # config.BIOME below stays on the default, "desert"
WANTED = {"Player 1": "orks", "Player 2": "aeldari"}

pygame.init()

from game.factions.faction import faction_keyword_of  # noqa: E402
from game.ui.army_select import ArmySelectScreen  # noqa: E402
from game.ui.map_select import MapSelectScreen  # noqa: E402

state = {"frames": 0, "clicked": [], "results": {}}
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
    """The live picking screen of this type, found on the call stack - its own
    run() is what is calling pygame.event.get() right now."""
    found = _frame_with(lambda loc: isinstance(loc.get("self"), cls))
    return found["self"] if found else None


def fake_events():
    state["frames"] += 1
    if state["frames"] >= MAX_FRAMES:
        raise SystemExit(0)

    picker = _live_screen(MapSelectScreen)
    if picker is not None:
        if not picker.tiles:
            return []
        # The biome first, on its own frame: it is a SECOND kind of button on
        # the same screen, and clicking a map ends that screen - so a biome
        # click has to be shown to land while the screen is still up AND to
        # leave it up, which is exactly the risk of putting both there.
        if picker.biome != WANTED_BIOME and picker.biome_rects:
            state["clicked"].append(("biome", WANTED_BIOME))
            return _click(picker.biome_rects[WANTED_BIOME].center)
        tile = next((t for t in picker.tiles if t.battle_map.key == WANTED_MAP), None)
        if tile is None:
            state["results"]["error"] = f"no tile for {WANTED_MAP!r}"
            raise SystemExit(0)
        state["clicked"].append(("map", WANTED_MAP))
        return _click(tile.rect.center)

    screen = _live_screen(ArmySelectScreen)
    if screen is not None:
        # The screen lays its tiles out when it draws, so the first frame has
        # none yet - wait one rather than clicking into empty space.
        player = screen.current_player
        if not screen.tiles or player is None:
            return []
        wanted = WANTED[player]
        tile = next((t for t in screen.tiles if t.entry.key == wanted), None)
        if tile is None:
            state["results"]["error"] = f"no tile for {wanted!r}"
            raise SystemExit(0)
        # Hover a portrait on the way past, so the detail card is exercised in
        # the real loop too rather than only in the unit test.
        # Only on the first ARMY step - "clicked" already holds the map click
        # by now, so testing it for emptiness would skip this entirely.
        if tile.cells and "hover_resolved" not in state["results"]:
            state["results"]["hover_unit"] = tile.cells[0][1].label
            screen.track_pointer(tile.cells[0][0].center)
            state["results"]["hover_resolved"] = screen.hovered_entry is tile.cells[0][1]
        state["clicked"].append((player, wanted))
        return _click(tile.rect.center)

    loc = _frame_with(lambda l: "scene_units" in l and "armies" in l and "battle_map" in l)
    if loc is None:
        return []

    from game import config

    from game import maps  # noqa: F401  (imported for symmetry with the map check)

    from game import sprites

    results = state["results"]
    results["map"] = loc["battle_map"].key
    results["biome"] = config.BIOME
    # Not just the setting: where the RENDERER will actually read its ground
    # picture from. A setting that no lookup honours is the same "computed and
    # then dropped" failure this whole harness exists for.
    ground = sprites.ground_texture_path()
    results["ground_folder"] = (os.path.basename(os.path.dirname(ground))
                                if ground else None)
    results["board"] = (config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
    results["armies"] = dict(loc["armies"])
    results["seer_council"] = tuple(config.SEER_COUNCIL_PLAYERS)
    results["awakened_dynasty"] = tuple(config.AWAKENED_DYNASTY_PLAYERS)
    per_player = {}
    for entry in loc["scene_units"]:
        squad = entry["squad"]
        per_player.setdefault(squad.owner, []).append(faction_keyword_of(squad))
    results["fielded"] = {owner: sorted(set(k for k in keys if k))
                          for owner, keys in per_player.items()}
    results["unit_counts"] = {owner: len(keys) for owner, keys in per_player.items()}
    raise SystemExit(0)


pygame.event.get = lambda *a, **k: fake_events()
pygame.mouse.get_pos = lambda *a, **k: (0, 0)
pygame.display.flip = lambda *a, **k: None
pygame.display.update = lambda *a, **k: None

from game import config  # noqa: E402

config.PREGAME_DEPLOYMENT = True
# The whole point: leave the SETTINGS on the defaults, so anything the clicks
# achieve is visibly the clicks' doing.
config.MAP = "map2"
config.BIOME = "desert"
config.PLAYER1_ARMY = "aeldari"
config.PLAYER2_ARMY = "necrons"
config.SEER_COUNCIL_PLAYERS = ("Player 1",)
config.AWAKENED_DYNASTY_PLAYERS = ("Player 2",)
config.MAP_SELECT = not NEUTRALIZE
config.ARMY_SELECT = not NEUTRALIZE
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
    # No map argument: naming one would skip the very screen under test.
    main.main()
except SystemExit:
    pass

results = state["results"]
print(f"\nneutralize={NEUTRALIZE} frames={state['frames']}")
print(f"clicked: {state['clicked']}")
if "error" in results:
    print("ERROR:", results["error"])

check("every step was answered by the harness, not by an agent",
      [p for p, _k in state["clicked"]] == ["biome", "map", "Player 1", "Player 2"],
      str(state["clicked"]))
check("the biome click reached config", results.get("biome") == WANTED_BIOME,
      f"got {results.get('biome')}, want {WANTED_BIOME} (config.BIOME is desert)")
check("...and the renderer reads its ground art out of that biome's folder",
      results.get("ground_folder") == "Forest", str(results.get("ground_folder")))
check("main() plays on the map that was clicked", results.get("map") == WANTED_MAP,
      f"got {results.get('map')}, want {WANTED_MAP} (config.MAP is map2)")
# The board dimensions are the thing everything downstream reads, so the click
# has to have reached config, not just a local.
check("...and the board is that map's size", results.get("board") == (44.0, 60.0),
      str(results.get("board")))
check("hovering a portrait resolves to that unit", results.get("hover_resolved"),
      str(results.get("hover_unit")))
check("main() fielded the pairing that was clicked", results.get("armies") == WANTED,
      f"got {results.get('armies')}, want {WANTED}")
check("Player 1 is on the board as ORKS", results.get("fielded", {}).get("Player 1") == ["ORKS"],
      str(results.get("fielded", {}).get("Player 1")))
check("Player 2 is on the board as AELDARI",
      results.get("fielded", {}).get("Player 2") == ["AELDARI"],
      str(results.get("fielded", {}).get("Player 2")))
check("Player 1 fields the whole Ork list (14 units)",
      results.get("unit_counts", {}).get("Player 1") == 14,
      str(results.get("unit_counts", {}).get("Player 1")))
# 12, down from 13: the Shroud Runners -> Windriders swap merged the Warlock
# Skyrunner - which stood alone only because its JOIN names WINDRIDERS and the
# list fielded none - into the Windriders. One list entry fewer on the table is
# what an attachment LOOKS like, and is not a unit going missing (the model
# count is unchanged); see game/army_lists.py's roster docstring.
check("Player 2 fields the whole Aeldari list (12 units)",
      results.get("unit_counts", {}).get("Player 2") == 12,
      str(results.get("unit_counts", {}).get("Player 2")))
# The detachment settings have to follow the lists, not stay where config left
# them - this is the half that silently leaves a player running a detachment
# whose army is not on the table.
check("Seer Council moved to the Aeldari player", results.get("seer_council") == ("Player 2",),
      str(results.get("seer_council")))
check("nobody runs Awakened Dynasty without Necrons",
      results.get("awakened_dynasty") == (), str(results.get("awakened_dynasty")))

passed = sum(1 for ok, _l, _d in report if ok)
for ok, label, detail in report:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
print(f"\n{passed}/{len(report)} checks passed")
sys.exit(0 if passed == len(report) else 1)
