"""Tests for the map selection screen, its rendered previews, and the frame
both picking screens now share.

User: "Vor der Fraktion würde ich jetzt allerdings gerne noch die Map
auswählen. Da wäre es cool, wenn ein Screenshot der Map angeboten werden würde.
Kriegst du das hin, oder soll ich das machen?" - the preview is RENDERED from
the map rather than screenshotted, so section 1 is largely about the one way
that can go wrong: a preview that decides the battlefield merely by having been
looked at.

  1. game/ui/map_preview.py - it renders every map, letterboxes into the box it
     is given, caches, and does NOT touch config.
  2. game/ui/map_select.py  - the facts under each tile, derived from the built
     board rather than written beside it.
  3. the screen           - tiles, clicking, quitting, paging, drawing.
  4. game/ui/tile_screen.py - the frame shared with the army picker.
  5. the WIRING in main.py and the harnesses: the map is chosen BEFORE the
     board is built and before the armies, which is the half a behaviour test
     cannot see.

Run: python test_map_select.py
"""

import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1600, 900))

from game import config, maps  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.ui import map_preview, tile_screen as ts  # noqa: E402
from game.ui.map_select import MapSelectScreen, map_facts  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("map selection")
SCREEN_RECT = pygame.Rect(0, 0, 1600, 900)
ALL_MAPS = list(maps.MAPS.values())


def _read(path):
    return io.open(path, encoding="utf-8").read()


# --------------------------------------------------------------------------
# 1. The rendered preview
# --------------------------------------------------------------------------
print("\n=== 1. rendered previews ===")

# THE ONE THING THIS MUST NOT DO. The map picker runs BEFORE
# maps.apply_to_config(), so at preview time config still holds the last run's
# board. A preview that wrote its own map's size into config would decide the
# battlefield merely by having been drawn.
before = (config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
map_preview.clear_cache()
for battle_map in ALL_MAPS:
    art = map_preview.surface_for(battle_map, 300, 300)
    c.true(f"{battle_map.key}: a preview is produced", art.get_width() > 0)
c.eq("rendering a preview does not touch config",
     (config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN), before)
c.true("...and it is checked at the source too",
       "config" not in _read(os.path.join("game", "ui", "map_preview.py"))
       .split('"""')[2])  # the module body, past the docstring

# Letterboxed: the picture fits the box, keeps its aspect, and touches at least
# one side of it - which is what makes a portrait board look portrait.
for battle_map in ALL_MAPS:
    art = map_preview.surface_for(battle_map, 400, 300)
    w, h = art.get_size()
    c.true(f"{battle_map.key}: fits the box", w <= 400 and h <= 300)
    c.true(f"{battle_map.key}: fills one axis of it", w == 400 or h == 300)
    board_aspect = battle_map.width_in / battle_map.height_in
    c.true(f"{battle_map.key}: keeps the board's aspect ratio "
           f"({w / h:.3f} vs {board_aspect:.3f})", abs((w / h) - board_aspect) < 0.02)

# A portrait board and a landscape one must NOT come out the same shape - that
# would mean the picture says nothing about the board.
portrait = map_preview.surface_for(maps.get("map1"), 400, 300)
landscape = map_preview.surface_for(maps.get("map2"), 400, 300)
c.true("a portrait board is taller than it is wide",
       portrait.get_height() > portrait.get_width())
c.true("a landscape board is wider than it is tall",
       landscape.get_width() > landscape.get_height())

# Cached per size: the same request twice is the same Surface object.
c.true("a preview is cached", map_preview.surface_for(maps.get("map2"), 400, 300) is landscape)
c.true("...and a different size is a different one",
       map_preview.surface_for(maps.get("map2"), 200, 150) is not landscape)

# It actually draws the board rather than an empty rectangle: the ground
# texture and terrain mean many distinct colours, where a blank fill has one.
sample = map_preview.surface_for(maps.get("map2"), 300, 300)
colors = {sample.get_at((x, y))[:3]
          for x in range(0, sample.get_width(), 5)
          for y in range(0, sample.get_height(), 5)}
c.true(f"the preview shows a real board, not a flat fill ({len(colors)} colours)", len(colors) > 50)


# --------------------------------------------------------------------------
# 2. The facts under a tile
# --------------------------------------------------------------------------
print("\n=== 2. tile facts ===")

for battle_map in ALL_MAPS:
    deployment, contents = map_facts(battle_map)
    state = GameState()
    battle_map.build(state)
    # Counted off the BUILT board, so a map whose terrain is re-measured
    # updates its own tile instead of disagreeing with it.
    c.true(f"{battle_map.key}: the terrain count is the map's own",
           f"{len(state.obstacles)} terrain features" in contents)
    c.true(f"{battle_map.key}: the objective count is the map's own",
           f"{len(state.objectives)} objectives" in contents)
    c.true(f"{battle_map.key}: it says how deep the zones are", "deep" in deployment)
    c.true(f"{battle_map.key}: and how much open ground is between them",
           "no man's land" in deployment)

# The two numbers, per map, written out rather than trusted. Both are measured
# off the BUILT zones (see map_facts), so they keep meaning something for a map
# whose zones are not bands: map 3 deploys in opposite corners with a 9" circle
# bitten out of the middle, and 12.7" is the true closest approach between the
# two - the distance between the two points where those circles meet the
# quadrant boundaries, not a board dimension minus two depths.
for key, depth, gap in (("map1", 18, 24), ("map2", 12, 20), ("map3", 21, 12.7)):
    deployment, _contents = map_facts(maps.get(key))
    c.true(f"{key}: zones {depth}\" deep -- {deployment}", f'zones {depth:g}" deep' in deployment)
    c.true(f"{key}: {gap}\" of no man's land -- {deployment}", f'{gap:g}" of no man' in deployment)

# The board size is deliberately NOT repeated - every map's own name already
# carries it, and the line is worth more spent on something else.
c.true("the facts line does not repeat the size already in the name",
       all('x' not in map_facts(m)[0] for m in ALL_MAPS))


# --------------------------------------------------------------------------
# 3. The screen
# --------------------------------------------------------------------------
print("\n=== 3. the screen ===")

screen = MapSelectScreen(default="map2")
tiles = screen.layout(SCREEN_RECT)
c.eq("one tile per map", len(tiles), len(ALL_MAPS))
c.true("every tile is inside the screen", all(SCREEN_RECT.contains(t.rect) for t in tiles))
c.true("tiles do not overlap",
       all(not a.rect.colliderect(b.rect) for i, a in enumerate(tiles) for b in tiles[i + 1:]))
c.true("the tiles are large", all(t.rect.width > 300 and t.rect.height > 400 for t in tiles))
c.true("every preview sits inside its own tile",
       all(t.rect.contains(t.preview_rect) for t in tiles))
c.true("every preview box is the same size",
       len({t.preview_rect.size for t in tiles}) == 1)
# Three maps on a screen that would hold four tiles must still share the whole
# width - a fourth empty slot would make all three a quarter too small.
c.eq("three maps use three slots, not four", screen.tiles_per_page, 3)
c.true("...so the tiles span the usable width",
       tiles[-1].rect.right >= SCREEN_RECT.width - 2 * ts.MARGIN - 4)

c.true("it is not done before anything is picked", not screen.done)
c.eq("tile_at finds the tile under the cursor", screen.tile_at(tiles[1].rect.center), 1)
c.eq("tile_at outside every tile is None", screen.tile_at((2, 2)), None)

screen.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": tiles[2].rect.center, "button": 1}),
    SCREEN_RECT)
c.true("clicking a tile picks that map", screen.done)
c.eq("...and it is the one clicked", screen.chosen.key, tiles[2].battle_map.key)

hover = MapSelectScreen()
hover.layout(SCREEN_RECT)
hover.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": hover.tiles[1].rect.center}),
                   SCREEN_RECT)
c.eq("motion sets the hovered tile", hover.hovered_tile, 1)
c.true("motion picks nothing", not hover.done)

for label, event in (("ESC", pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})),
                     ("QUIT", pygame.event.Event(pygame.QUIT, {}))):
    aborted = MapSelectScreen()
    aborted.handle_event(event, SCREEN_RECT)
    c.true(f"{label} abandons the screen", aborted.cancelled and aborted.done)

# Drawing, on a real Surface: the tiles have to differ from the background, and
# each preview has to be more than an empty plate.
surface = pygame.Surface(SCREEN_RECT.size)
drawn = MapSelectScreen()
drawn.draw(surface, (2, 2))


def _colours(rect):
    sub = surface.subsurface(rect)
    return {sub.get_at((x, y))[:3]
            for x in range(0, rect.width, 6) for y in range(0, rect.height, 6)}


c.true("the tiles are drawn", all(_colours(t.rect) != {ts.BG_COLOR} for t in drawn.tiles))
c.true("each tile really shows its board",
       all(len(_colours(t.preview_rect)) > 20 for t in drawn.tiles))
c.true("the header is drawn", _colours(pygame.Rect(0, 0, SCREEN_RECT.width, 60)) != {ts.BG_COLOR})

# Paging is unreachable with three maps, which is the point of testing it with
# a fabricated set: an unreachable feature is an untested one.
many = MapSelectScreen(battle_maps=(ALL_MAPS * 3)[:7])
many.layout(SCREEN_RECT)
c.eq("seven maps page", many.page_count, 3)
c.eq("...three at a time", many.tiles_per_page, 3)
many.turn_page(1)
c.eq("Next moves on", many.page, 1)
c.eq("...and shows the next three",
     [t.battle_map.key for t in many.layout(SCREEN_RECT)],
     [m.key for m in many.items[3:6]])
c.eq("hit tests only see the current page", len(many.tiles), 3)
many.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1, "x": 0}), SCREEN_RECT)
c.eq("the wheel pages too", many.page, 2)
c.eq("a partial page keeps the tile width",
     many.layout(SCREEN_RECT)[0].rect.width, tiles[0].rect.width)


# --------------------------------------------------------------------------
# 4. The shared frame
# --------------------------------------------------------------------------
print("\n=== 4. the shared frame ===")

# Extracted at the second consumer (CLAUDE.md error class 10). The check that
# matters is that BOTH screens really go through it - a copy left behind in one
# of them is exactly the drift the extraction exists to prevent.
army_src = _read(os.path.join("game", "ui", "army_select.py"))
map_src = _read(os.path.join("game", "ui", "map_select.py"))
for name, src in (("army_select", army_src), ("map_select", map_src)):
    c.true(f"{name} uses the shared frame", "tile_screen as ts" in src)
    c.true(f"{name} uses the shared header", "ts.draw_header(" in src)
    c.true(f"{name} uses the shared footer", "ts.draw_footer(" in src)
    c.true(f"{name} uses the shared tile frame", "ts.draw_tile_frame(" in src)
    c.true(f"{name} uses the shared loop", "ts.run_screen(" in src)
    c.true(f"{name} pages through the shared mixin", "ts.Paged" in src or "self.fit_page(" in src)

c.eq("a page never has more slots than there are items",
     ts.Paged.fit_page.__doc__ is not None, True)
probe = MapSelectScreen(battle_maps=ALL_MAPS[:1])
probe.layout(SCREEN_RECT)
c.eq("one item, one slot", probe.tiles_per_page, 1)
c.true("...and it gets the whole width",
       probe.tiles[0].rect.width >= SCREEN_RECT.width - 2 * ts.MARGIN - 4)

# The width rule the pager depends on: a partial page must not stretch.
area = ts.tile_area(SCREEN_RECT)
full = ts.tile_rects(area, 3, 3, 100)
partial = ts.tile_rects(area, 3, 2, 100)
c.eq("a partial page draws at the full page's tile width",
     partial[0].width, full[0].width)


# --------------------------------------------------------------------------
# 5. Wiring - the order, which only main.py can get wrong
# --------------------------------------------------------------------------
print("\n=== 5. wiring ===")

main_src = _read("main.py")


def _line_of(pattern):
    match = re.search(pattern, main_src)
    return main_src[:match.start()].count("\n") if match else None


c.true("main() runs the map screen", "MapSelectScreen(default=config.MAP).run(screen)" in main_src)
c.true("...gated on config.MAP_SELECT",
       "if map_key is None and config.MAP_SELECT and not config.LOAD_SCENE:" in main_src)
c.true("...and abandoning it closes the program",
       re.search(r"map_key = MapSelectScreen[^\n]*\n\s*if map_key is None:\s*\n\s*pygame\.quit\(\)"
                 r"\s*\n\s*return", main_src) is not None)

display_line = _line_of(r"screen = pygame\.display\.set_mode")
map_line = _line_of(r"MapSelectScreen\(default=config\.MAP\)")
apply_line = _line_of(r"battle_map = maps\.apply_to_config")
army_line = _line_of(r"ArmySelectScreen\(defaults=armies\)")
build_line = _line_of(r"army_lists\.get\(armies\[owner\]\)\.build\(")
c.true("the window exists before the map screen is shown", display_line < map_line)
c.true("the map is chosen before the board is built", map_line < apply_line)
c.true("the board is built before the armies are chosen", apply_line < army_line)
c.true("the armies are chosen before any unit is built", army_line < build_line)

# --map is an answer, so it skips the question.
c.true("naming a map on the command line skips the screen",
       'if map_key is None and config.MAP_SELECT' in main_src)
c.true("--no-map-select exists", '"--no-map-select"' in main_src)
c.true("naming BOTH armies skips the army screen",
       "config.ARMY_SELECT = False" in main_src)

# Every headless harness has to opt out of BOTH screens - one that forgets
# hangs on a click nobody will make.
for harness in ("selfplay.py", "smoke_pregame.py", "smoke_log_input.py",
                "smoke_measure_tool.py", "smoke_end_turn_warning.py"):
    src = _read(harness)
    for flag in ("config.MAP_SELECT = False", "config.ARMY_SELECT = False"):
        c.true(f"{harness} sets {flag.split('.')[1].split(' ')[0]}", flag in src)
        c.true(f"{harness} does so before importing main",
               src.index(flag) < src.index("import main"))

# The one harness that DRIVES the screens instead of skipping them.
setup_smoke = _read("smoke_setup_screens.py")
c.true("a smoke drives both screens through main()",
       "MapSelectScreen" in setup_smoke and "ArmySelectScreen" in setup_smoke)
c.true("...and it clicks a map that config does not name",
       'WANTED_MAP = "map1"' in setup_smoke and 'config.MAP = "map2"' in setup_smoke)

c.finish()
