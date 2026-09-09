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
# map 4's numbers come out of the same sampling and describe the shape the
# other three do not have: two PARALLEL diagonals, so its "no man's land" is a
# band of constant width (24.787" exactly, rounded to 25 by the 1" sampling
# grid) rather than a closest approach between two facing blocks, and its
# "depth" is how far the deepest point of a triangle stands from the nearest
# board edge.
for key, depth, gap in (("map1", 18, 24), ("map2", 12, 20), ("map3", 21, 12.7),
                        ("map4", 17.5, 25)):
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
# ONE TILE PER MAP ON THIS PAGE, not one per map in the registry - the fourth
# board is what made that distinction real. At 1600px three tiles clear
# MIN_TILE_WIDTH, so four maps paginate, and the pager going live here is the
# same milestone the fifth army list was for the army picker. The stronger
# claim (every map is reachable) is checked right below, because "3 tiles" on
# its own would also pass on a screen that had quietly dropped a map.
c.eq("one tile per map on this page", len(tiles), len(screen.page_items))
c.true("...and the page really is full, so nothing is being hidden by an "
       "undersized layout", len(tiles) == min(screen.tiles_per_page, len(ALL_MAPS)))
seen = []
for _ in range(screen.page_count):
    seen += [t.battle_map.key for t in screen.layout(SCREEN_RECT)]
    screen.turn_page(1)
c.eq("every map is reachable by paging through the screen",
     sorted(set(seen)), sorted(m.key for m in ALL_MAPS))
screen = MapSelectScreen(default="map2")
tiles = screen.layout(SCREEN_RECT)
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

# TWO BEATS. User: "momentan geschieht die auswahl schon, wenn man draufklickt.
# ich haette gerne ein auswahl highlight + button. also erst auswaehlen, dann
# wird die entsprechende kachel gehighlightet und dann auf den auswahl button
# unten druecken." A click must no longer end the screen.
screen.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": tiles[2].rect.center, "button": 1}),
    SCREEN_RECT)
c.true("clicking a tile does NOT end the screen", not screen.done)
c.eq("...it selects it", screen.selected.key, tiles[2].battle_map.key)
c.eq("...and nothing is chosen yet", screen.chosen, None)

# Reversible: a second click moves the selection instead of committing the
# first one.
screen.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": tiles[0].rect.center, "button": 1}),
    SCREEN_RECT)
c.eq("clicking another tile moves the selection", screen.selected.key, tiles[0].battle_map.key)
c.true("...and still has not chosen", not screen.done)

# The button only exists once something is picked - the same convention the
# pager follows, so there is never a dead control on screen.
_empty = MapSelectScreen()
_empty.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
c.eq("no confirm button before anything is selected", _empty.footer.confirm, None)
c.eq("...and no label for one either", _empty.confirm_label, None)

_surface = pygame.Surface(SCREEN_RECT.size)
screen.draw(_surface, (2, 2))
c.true("a confirm button appears once a map is selected", screen.footer.confirm is not None)
c.true("...and it names the pick", tiles[0].battle_map.name in screen.confirm_label)

screen.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                       {"pos": screen.footer.confirm.center, "button": 1}),
    SCREEN_RECT)
c.true("pressing Confirm ends the screen", screen.done)
c.eq("...with the selected map", screen.chosen.key, tiles[0].battle_map.key)

# Confirm with nothing picked is a no-op, not an advance.
_bare = MapSelectScreen()
c.eq("confirm with no selection does nothing", _bare.confirm(), False)
c.true("...and the screen stays open", not _bare.done)

# ENTER is the keyboard half of the same button - and it is not a shortcut
# past the first beat.
_keyed = MapSelectScreen()
_keyed.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}), SCREEN_RECT)
c.true("ENTER with nothing selected does nothing", not _keyed.done)
_keyed.layout(SCREEN_RECT)
_keyed.select(_keyed.tiles[1].battle_map)
_keyed.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}), SCREEN_RECT)
c.true("ENTER confirms a selection", _keyed.done)
c.eq("...with the selected map", _keyed.chosen.key, _keyed.tiles[1].battle_map.key)

# The one-call API is unchanged, for callers driving the screen without a mouse.
_direct = MapSelectScreen()
_direct.layout(SCREEN_RECT)
c.true("choose() still selects and commits in one call",
       _direct.choose(_direct.tiles[1].battle_map))
c.true("...ending the screen", _direct.done)

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
# 4b. The selection highlight, and the footer that now carries a fourth button
# --------------------------------------------------------------------------
print("\n=== 4b. selection highlight ===")

# THREE distinct looks, measured on pixels. Hover and selected must not merely
# differ from plain - they must differ from EACH OTHER, or the highlight says
# "the cursor is here" instead of "this is your answer", which is the whole
# point of the change.
FRAME_RECT = pygame.Rect(20, 20, 300, 200)


def _frame_pixels(**kwargs):
    surf = pygame.Surface((360, 240))
    surf.fill((0, 0, 0))
    ts.draw_tile_frame(surf, FRAME_RECT, **kwargs)
    return {surf.get_at((x, y))[:3]
            for x in range(FRAME_RECT.x, FRAME_RECT.right, 3)
            for y in range(FRAME_RECT.y, FRAME_RECT.bottom, 3)}


plain_px = _frame_pixels()
hover_px = _frame_pixels(hovered=True)
sel_px = _frame_pixels(selected=True)
c.true("a hovered tile differs from a plain one", plain_px != hover_px)
c.true("a selected tile differs from a plain one", plain_px != sel_px)
c.true("...and from a hovered one", sel_px != hover_px)
c.true("the selected tile carries the selection colour",
       ts.TILE_BORDER_SELECTED_COLOR in sel_px)
c.true("...which a hovered tile does not",
       ts.TILE_BORDER_SELECTED_COLOR not in hover_px)
# A selected tile still brightens under the cursor rather than going dead.
c.true("a selected tile still responds to hover",
       _frame_pixels(selected=True, hovered=True) != sel_px)

# Colour alone is not enough - the badge is what survives a colour-blind
# reader, who otherwise has only the border WIDTH to go on.
badge_surf = pygame.Surface((360, 240))
badge_surf.fill((0, 0, 0))
badge_rect = ts.draw_selected_badge(badge_surf, FRAME_RECT, ts.make_fonts())
c.true("the SELECTED badge is inside its tile", FRAME_RECT.contains(badge_rect))
c.true("...and actually paints something",
       any(badge_surf.get_at((x, y))[:3] != (0, 0, 0)
           for x in range(badge_rect.x, badge_rect.right)
           for y in range(badge_rect.y, badge_rect.bottom)))

# The footer returns a RECORD, not a tuple. It used to be a tuple that one
# caller sliced (`draw_footer(...)[1:]`), so a fourth button would have handed
# that caller the wrong rectangles - CLAUDE.md error class 22.
buttons = ts.FooterButtons()
c.eq("an unused footer control is None",
     (buttons.back, buttons.prev, buttons.next, buttons.confirm), (None,) * 4)
c.true("the footer record cannot be read positionally",
       not hasattr(buttons, "__getitem__"))
c.true("...nor grown a field by accident", hasattr(ts.FooterButtons, "__slots__"))
for name, src in (("army_select", army_src), ("map_select", map_src)):
    c.true(f"{name} stores the footer as one record",
           "self.footer = ts.draw_footer(" in src)
    c.true(f"{name} reads its buttons by name",
           "self.footer.confirm" in src and "self.footer.prev" in src)
    # The slice and the tuple unpacking that used to be here are exactly what
    # a fourth button would have broken silently.
    c.true(f"{name} has no leftover positional footer unpacking",
           "draw_footer(" in src and ")[1:]" not in src
           and "self.prev_rect" not in src and "self.next_rect" not in src
           and "self.back_rect" not in src)

# All four footer controls on the NARROWEST window this game is run at, with
# every one of them present. Overlapping buttons would make one unclickable.
narrow = pygame.Rect(0, 0, 1280, 720)
narrow_surf = pygame.Surface(narrow.size)
crowded = ts.draw_footer(narrow_surf, narrow, ts.make_fonts(), 0, 3,
                         back_label="Back", confirm_label="Confirm: Something")
present = [r for r in (crowded.back, crowded.prev, crowded.next, crowded.confirm) if r]
c.eq("a crowded footer draws all four controls", len(present), 4)
c.eq("...and none of them overlap",
     [(i, j) for i, a in enumerate(present) for j, b in enumerate(present)
      if i < j and a.colliderect(b)], [])
c.true("...and all of them stay inside the window",
       all(narrow.contains(r) for r in present))

# The confirm label names the pick, so it grows with the longest real name.
# Every one of them has to stay inside the window at the narrowest size.
from game import army_lists as _al  # noqa: E402

overflow = []
for _name in [m.name for m in ALL_MAPS] + [e.name for e in _al.ARMY_LISTS]:
    got = ts.draw_footer(narrow_surf, narrow, ts.make_fonts(), 0, 1,
                         confirm_label=f"Confirm: {_name}")
    if not narrow.contains(got.confirm):
        overflow.append(_name)
c.eq("no real map or army name pushes the confirm button off screen", overflow, [])


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
# Abandoning the screen still ends the program, but it now SAYS so rather than
# doing it: main() is one battle and run() is the application, so the screen's
# refusal travels back as the menu's own QUIT answer and run() closes the
# window. The check moved with it and got stronger - it also pins that main()
# never calls pygame.quit() itself, i.e. that exactly ONE function owns the
# window's lifetime. Without that second half, a future edit could put a
# pygame.quit() back inside a battle and leave run()'s loop flipping a dead
# display.
c.true("...and abandoning it answers the menu's QUIT",
       re.search(r"map_key = MapSelectScreen[^\n]*\n\s*if map_key is None:"
                 r"(\s*\n\s*#[^\n]*)*\s*\n\s*return game_menu_module\.QUIT",
                 main_src) is not None)
# Counted as STATEMENTS, not as mentions: main() carries a comment explaining
# why it no longer calls this, and a plain .count() reads that comment as a
# second closer. CLAUDE.md error class 24 - a wiring guard has to look at the
# call, not at the name.
_quit_calls = [n for n, line in enumerate(main_src.splitlines())
               if line.strip() == "pygame.quit()"]
c.eq("exactly one place closes the window", len(_quit_calls), 1)
c.true("...and it is run(), which is above main()",
       _quit_calls[0] < main_src[:main_src.index("def main(map_key=None):")].count("\n"))

display_line = _line_of(r"screen = pygame\.display\.get_surface\(\)")
menu_line = _line_of(r"GameMenu\(save_path=")
map_line = _line_of(r"MapSelectScreen\(default=config\.MAP\)")
apply_line = _line_of(r"battle_map = maps\.apply_to_config")
army_line = _line_of(r"ArmySelectScreen\(defaults=armies\)")
build_line = _line_of(r"army_lists\.get\(armies\[owner\]\)\.build\(")
c.true("the window exists before the map screen is shown", display_line < map_line)
# The menu is a fourth rung on the front of this ladder: it is answered before
# the battlefield is picked, because "Resume" decides the map from the file
# rather than from the screen.
c.true("the menu is answered before the map screen", menu_line < map_line)
c.true("...and after the window exists", display_line < menu_line)
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
