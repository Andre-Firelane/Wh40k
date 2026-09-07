"""The ARENA biome - the one that is DRAWN instead of photographed.

User: "ich bin unzufrieden mit dem aussehen der maps. versuchen wir mal einen
anderen weg. neben den 3 biomen soll es noch eine 4. option geben. dort besteht
die map nicht aus sprites, sondern du renderst sie. sie soll aussehen, wie eine
simulations arena. aehnlicher look wie das interface. eventuell mit leichten
farbverlaeufen oder ein ganz subtiles kariertes muster. natuerlich dann
unterschiedlich: boden, dense cover, light cover"

test_biomes.py already asks that it IS a biome - a fourth button, a fourth
distinct board, and no art on disk. This file asks the four things that are
only true of a drawn one, each of which is a way the request can be met on
paper and missed on screen:

  1. IT LOOKS LIKE THE INTERFACE. game/arena_biome.py restates four
     button_style colours by value rather than importing that module (it lives
     under game/ui/ and this runs on the render path), so the numbers are
     pinned AGAINST button_style here - which is the only thing the import
     would have bought.
  2. THE THREE ROLES ARE TOLD APART. "natuerlich dann unterschiedlich" is the
     load-bearing half of the request: measured as mean colour distance on a
     real board, and separately as PATTERN, since two patterns can differ
     while their means do not.
  3. THE TILES WRAP. The renderer tiles them grid-aligned to the board origin,
     so a pattern that does not repeat cleanly shows a break at every tile
     boundary. Checked across a real seam, not asserted.
  4. THE RENDERER ACTUALLY GOES THERE. Three seams branch on
     biomes.is_procedural() - ground, cover and walls - and a drawn biome that
     is never reached renders as a flat fill. Checked end to end through a real
     Renderer, not only as a source guard: this repo has found five controllers
     that were built and never fed.

Run: python test_arena_biome.py
"""


import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((400, 300))

from game import arena_biome, biomes, config, maps, renderer as rmod  # noqa: E402
from game.board import Board  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.renderer import Renderer  # noqa: E402
from game.terrain import DENSE  # noqa: E402
from game.ui import button_style  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("arena biome")

_ORIGINAL_BIOME = config.BIOME
RENDERER_SRC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "game", "renderer.py"), encoding="utf-8").read()


def mean_rgb(surface, rect):
    total = [0, 0, 0]
    count = 0
    for y in range(rect.top, rect.bottom):
        for x in range(rect.left, rect.right):
            pixel = surface.get_at((x, y))
            total[0] += pixel[0]
            total[1] += pixel[1]
            total[2] += pixel[2]
            count += 1
    return tuple(v / count for v in total)


def colour_distance(a, b):
    """Mean absolute per-channel difference - the same coarse readability
    proxy game/renderer.py's biome work has used throughout. Coarse on
    purpose, and its limit is recorded there: a pattern can read clearly at a
    distance of 6 (the forest light cover does), which is why section 3 below
    measures pattern separately rather than leaning on this alone."""
    return sum(abs(x - y) for x, y in zip(a, b)) / 3.0


def scene(map_key="map2", ppi=30.0):
    battle_map = maps.get(map_key)
    state = GameState()
    battle_map.build(state)
    board = Board(battle_map.width_in, battle_map.height_in, ppi)
    return battle_map, state, board


def render(state, board):
    surface = pygame.Surface((board.width_px, board.height_px))
    Renderer().draw(surface, board, (), obstacles=state.obstacles,
                    deployment_zones=state.deployment_zones,
                    terrain_areas=state.terrain_areas)
    return surface


def patch(board, x_in, y_in, size_in):
    px, py = board.to_px(x_in, y_in)
    side = max(2, round(board.in_to_px_len(size_in)))
    return pygame.Rect(round(px), round(py), side, side)


# --- 1. it is built out of the interface's own colours ---------------------

# game/arena_biome.py names its source for each of these in a comment. The
# comment is the claim; this is the check, and it is the whole reason the
# module is allowed to restate them instead of importing button_style.
c.eq("the floor is the HUD's own box background (button_style.BOX_BG_COLOR)",
     arena_biome.GROUND_BASE, button_style.BOX_BG_COLOR)
c.eq("the grid is the HUD's own border cyan (button_style.BORDER_NORMAL)",
     arena_biome.GRID_COLOR, button_style.BORDER_NORMAL)
c.eq("the board edge is its hover cyan (button_style.BORDER_HOVER)",
     arena_biome.EDGE_COLOR, button_style.BORDER_HOVER)

# ...and it must not reach back into game/ui/. That import would work today and
# be a cycle the moment anything under game/ui/ wants a board drawn - which
# game/ui/map_preview.py already does.
ARENA_SRC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "game", "arena_biome.py"), encoding="utf-8").read()
c.true("...without importing game.ui, which would be a cycle through map_preview",
       "import" not in ARENA_SRC.split("def ")[0].replace("game.ui", "")
       or "from game.ui" not in ARENA_SRC and "import game.ui" not in ARENA_SRC)

# The grid spacings are the distances the RULES use, not decoration. Pinned
# against the engagement range the rest of the game measures with, so a later
# "let us make it 2 inches for looks" is a visible change.
from game.squad import ENGAGEMENT_RANGE_IN  # noqa: E402
c.eq("the minor grid is one inch - coherency and the engagement band",
     arena_biome.GRID_MINOR_IN, 1.0)
c.eq("...which is also the Engagement Range the rules measure in",
     arena_biome.GRID_MINOR_IN, float(ENGAGEMENT_RANGE_IN) / 2)
c.eq("the major grid is six inches - the centre circle the renderer draws",
     arena_biome.GRID_MAJOR_IN, 6.0)
c.true("...a whole number of minor cells, so the two grids never disagree",
       arena_biome.GRID_MAJOR_IN % arena_biome.GRID_MINOR_IN == 0)


# --- 2. the ground: gradient, checker, grid --------------------------------

board = Board(60.0, 44.0, 30.0)
arena_biome.clear_cache()
ground = arena_biome.ground_surface(board)

c.eq("the ground is drawn at the board's own pixel size",
     ground.get_size(), (board.width_px, board.height_px))


def cell(col, row, board=board):
    """Well inside major cell (col,row), clear of its own grid lines."""
    return pygame.Rect(
        *[round(v) for v in board.to_px(col * 6 + 1.0, row * 6 + 1.0)],
        round(board.in_to_px_len(4.0)), round(board.in_to_px_len(4.0)))


# THE GRADIENT ("leichte farbverlaeufe"). Corner against centre.
corner = mean_rgb(ground, cell(0, 0))
centre = mean_rgb(ground, cell(5, 3))
lift = sum(b - a for a, b in zip(corner, centre)) / 3.0
c.true(f"the middle of the board is lit brighter than its corner (+{lift:.1f})",
       lift > 6)
c.true("...and no channel anywhere falls below the base fill, because the lift "
       "is ADDED - a multiply would darken the corners below the panel behind them",
       all(cmin >= base - 1 for cmin, base
           in zip(corner, arena_biome.GROUND_BASE)))

# THE CHECKER ("ein ganz subtiles kariertes muster"). Two cells MIRRORED about
# the board centre: same distance from the middle, so the gradient contributes
# equally and only the checker's parity differs. Measuring two ADJACENT cells
# instead is what this probe did first, and it read 1.47 where the answer is 5
# - the gradient swamped it. The isolation is the check.
left_cell = mean_rgb(ground, cell(3, 3))
right_cell = mean_rgb(ground, cell(6, 3))
c.eq("cols 3 and 6 really are mirrored about the board centre",
     round(abs((3 * 6 + 3) - 30), 6), round(abs((6 * 6 + 3) - 30), 6))
c.true("...and have opposite checker parity", (3 + 3) % 2 != (6 + 3) % 2)
per_channel = [a - b for a, b in zip(left_cell, right_cell)]
# BOTH BOUNDS ARE READ OFF THE SURFACE, not off GROUND_CHECKER_LIFT. Checking
# the measurement against the constant is the only assertion here that moves
# BOTH sides at once: switching the checker off makes the drawn difference 0
# and the expected value 0 with it, and the check passes on a board with no
# checker at all. Found by the A/B probe, which is the second time this repo
# has caught that exact tautology.
c.true(f"the checker really lifts one cell of every pair - measured, not "
       f"restated (got {[round(v, 2) for v in per_channel]})",
       all(v > 3 for v in per_channel))
c.true("...and it is SUBTLE: under 8 points on the board itself, or it stops "
       "being a texture and becomes a chessboard",
       all(v < 8 for v in per_channel))
c.true("...by exactly the amount the constant claims, so the two agree",
       all(abs(v - arena_biome.GROUND_CHECKER_LIFT) < 0.5 for v in per_channel))


def bright_columns(surface, y, threshold):
    """x of every column at row `y` whose blue channel clears `threshold`,
    grouped into runs - i.e. where the vertical lines are and how wide."""
    runs = []
    run = None
    for x in range(surface.get_width()):
        if surface.get_at((x, y))[2] >= threshold:
            run = (x, 1) if run is None else (run[0], run[1] + 1)
        elif run is not None:
            runs.append(run)
            run = None
    if run is not None:
        runs.append(run)
    return runs


def line_vs_gap(surface, board, inch, y):
    """(blue on the grid line at `inch`, blue midway to the next one).

    Compared LOCALLY, against the gap right beside it, rather than against one
    threshold picked for the whole row: the centre lift makes the same line
    ~18 points brighter in the middle of the board than at its edge, so any
    fixed cut-off answers a different question at each end - measured, a
    threshold that isolates the major grid near the edge catches every minor
    line near the middle. Reading a line against its own neighbour is also the
    comparison the eye is actually making."""
    x_line = round(board.in_to_px_len(inch))
    x_gap = round(board.in_to_px_len(inch + arena_biome.GRID_MINOR_IN / 2))
    return surface.get_at((x_line, y))[2], surface.get_at((x_gap, y))[2]


# THE GRID, measured as lines on the surface rather than as constants. Sampled
# on a row inside a checker cell so the checker's own +5 cannot be mistaken for
# a line.
row = round(board.in_to_px_len(3.0))
readings = {inch: line_vs_gap(ground, board, inch, row) for inch in range(60)}
c.true("there is a grid line at EVERY inch",
       all(line > gap for line, gap in readings.values()))
majors = [line for inch, (line, _) in readings.items() if inch % 6 == 0]
minors = [line for inch, (line, _) in readings.items() if inch % 6]
c.true(f"...and every sixth one is drawn stronger (major {min(majors)}-{max(majors)} "
       f"vs minor {min(minors)}-{max(minors)})", min(majors) > max(minors))
c.true("...which is what makes a 6-inch cell readable instead of a wall of "
       "graph paper", arena_biome.GRID_MAJOR_ALPHA > arena_biome.GRID_MINOR_ALPHA)

# RESOLUTION INDEPENDENCE - the reason this is drawn rather than photographed.
# The same grid in INCHES at the map-select preview's resolution and at the
# game's. A photograph has one resolution and is stretched to whatever it is
# handed; this must not be.
for ppi in (11.0, 62.5):
    arena_biome.clear_cache()
    other = Board(60.0, 44.0, ppi)
    other_ground = arena_biome.ground_surface(other)
    other_row = round(other.in_to_px_len(3.0))
    reads = {inch: line_vs_gap(other_ground, other, inch, other_row)
             for inch in range(1, 59)}
    c.true(f"{ppi} px/inch: still a line at every INCH, not every N pixels",
           all(line > gap for line, gap in reads.values()))
    c.true(f"{ppi} px/inch: ...and still a stronger one every six",
           min(line for inch, (line, _) in reads.items() if inch % 6 == 0)
           > max(line for inch, (line, _) in reads.items() if inch % 6))
arena_biome.clear_cache()
ground = arena_biome.ground_surface(board)


# --- 3. the three roles are told apart -------------------------------------

config.BIOME = "arena"
arena_biome.clear_cache()
_, state, board = scene("map2")
surface = render(state, board)


def open_ground_patch():
    for gx in range(2, 58, 2):
        for gy in range(2, 42, 2):
            if not any(o.contains_point(gx, gy, inflate=2.0) for o in state.obstacles):
                return patch(board, gx, gy, 1.0)
    raise AssertionError("map2 has no open ground, which cannot be")


def cover_patch(with_wall):
    for area in state.terrain_areas:
        if area.has_dense_feature != with_wall:
            continue
        for obstacle in area.features:
            if obstacle.category == DENSE:
                continue
            if min(obstacle.max_x - obstacle.min_x,
                   obstacle.max_y - obstacle.min_y) < 2.5:
                continue
            return patch(board, (obstacle.min_x + obstacle.max_x) / 2 - 0.75,
                         (obstacle.min_y + obstacle.max_y) / 2 - 0.75, 1.5)
    raise AssertionError(f"map2 has no {'dense' if with_wall else 'light'} cover area")


def wall_patch():
    wall = max((o for o in state.obstacles if o.category == DENSE),
               key=lambda o: min(o.max_x - o.min_x, o.max_y - o.min_y))
    return patch(board, (wall.min_x + wall.max_x) / 2 - 0.2,
                 (wall.min_y + wall.max_y) / 2 - 0.2, 0.4)


arena = {
    "ground": mean_rgb(surface, open_ground_patch()),
    "dense": mean_rgb(surface, cover_patch(True)),
    "light": mean_rgb(surface, cover_patch(False)),
    "wall": mean_rgb(surface, wall_patch()),
}

# Every pair has to be told apart, and the ORDER is part of the design: dense
# cover is the brightest of the three surfaces (a floor you walk into), light
# cover sits between it and the bare ground.
c.true(f"dense cover reads against the ground "
       f"({colour_distance(arena['dense'], arena['ground']):.1f})",
       colour_distance(arena["dense"], arena["ground"]) > 20)
c.true(f"light cover reads against the ground "
       f"({colour_distance(arena['light'], arena['ground']):.1f})",
       colour_distance(arena["light"], arena["ground"]) > 10)
c.true(f"...and against dense cover "
       f"({colour_distance(arena['light'], arena['dense']):.1f})",
       colour_distance(arena["light"], arena["dense"]) > 10)
c.true("dense cover is the brighter of the two, light cover sits between it "
       "and the bare floor",
       sum(arena["dense"]) > sum(arena["light"]) > sum(arena["ground"]))

# THE WALLS. This is the measurement that bought arena_biome.WALL_FILL: the
# shared flat OBSTACLE_COLOR was picked against three LIGHT photographed
# grounds and is near-invisible on a dark one. The bar is not a magic number -
# it is the WORST the shipped photographed biomes manage, computed here, so the
# claim is "no harder to read than the biomes we already ship" and it stays
# honest if that art is replaced.
photo_wall_contrast = {}
photo_ground = {}  # also kept for the base-rim bar further down
for key in ("city", "desert", "forest"):
    config.BIOME = key
    _, photo_state, photo_board = scene("map2")
    photo_surface = render(photo_state, photo_board)
    state, board = photo_state, photo_board  # for the patch helpers
    photo_ground[key] = mean_rgb(photo_surface, open_ground_patch())
    photo_wall_contrast[key] = colour_distance(
        mean_rgb(photo_surface, wall_patch()),
        mean_rgb(photo_surface, open_ground_patch()))
config.BIOME = "arena"
_, state, board = scene("map2")
surface = render(state, board)
worst_photo = min(photo_wall_contrast.values())
arena_wall_contrast = colour_distance(arena["wall"], arena["ground"])
c.true(f"a wall reads against the arena floor at least as well as it does on "
       f"the worst photographed biome ({arena_wall_contrast:.1f} vs "
       f"{worst_photo:.1f}, {min(photo_wall_contrast, key=photo_wall_contrast.get)})",
       arena_wall_contrast >= worst_photo)
c.true(f"PRE-CHANGE: the shared OBSTACLE_COLOR managed only "
       f"{colour_distance(rmod.OBSTACLE_COLOR, arena['ground']):.1f} here - "
       f"the worst of the four biomes, which is why walls are painted",
       colour_distance(rmod.OBSTACLE_COLOR, arena["ground"]) < worst_photo)
c.true("a wall is drawn brighter than the dense cover it stands on, so it "
       "reads as ON the footprint rather than as a hole in it",
       sum(arena["wall"]) > sum(arena["dense"]))

# THE MODELS still have to read on it, which is the risk a DARK floor runs that
# the three light photographed ones do not: a base is a coloured RING with
# nothing inside it (see Renderer._draw_tokens), so the floor is what it is
# seen against. Both team colours, against the arena floor and against the
# desert one that has always worked.
for label, ring in (("own army (green)", rmod.OWN_ARMY_COLOR),
                    ("enemy (red)", rmod.ENEMY_ARMY_COLOR)):
    on_arena = colour_distance(ring, arena["ground"])
    c.true(f"a {label} base ring reads on the arena floor ({on_arena:.0f})",
           on_arena > 60)

# ...AND AGAINST THE GRID LINE, which is the half the floor check cannot see
# and the one that was actually reported ("blau kann man schlecht erkennen auf
# blauem grund"). The floor is nearly black, so ANY saturated rim scores well
# against it - the old blue rim scored 115 here, better than the green that
# replaced it - while what a rim really lies among out here are the blue guide
# lines. That blue was 21.7 from GRID_COLOR with an IDENTICAL red channel: a
# same-hue collision, invisible to a mean measured against the floor.
for label, ring in (("own army", rmod.OWN_ARMY_COLOR),
                    ("enemy", rmod.ENEMY_ARMY_COLOR)):
    on_grid = colour_distance(ring, arena_biome.GRID_COLOR)
    c.true(f"...and the {label} ring is not a second shade of the grid it lies "
           f"on ({on_grid:.0f} from GRID_COLOR)", on_grid > 40)

# PATTERN, not just brightness - the half a mean colour cannot see, and the
# half that survives a colour-blind player. Dense cover is an ORTHOGONAL
# lattice, light cover is DIAGONAL hatching: so a dense tile's rows repeat down
# the tile while a diagonal one's shift sideways every row.
dense_tile = arena_biome.cover_tile(biomes.DENSE_COVER, board)
light_tile = arena_biome.cover_tile(biomes.LIGHT_COVER, board)


def row_pixels(tile, y):
    return [tile.get_at((x, y))[:3] for x in range(tile.get_width())]


mid = dense_tile.get_height() // 2
c.true("dense cover is ORTHOGONAL: two rows a few pixels apart are identical, "
       "because its lines run straight down",
       row_pixels(dense_tile, mid) == row_pixels(dense_tile, mid + 3))
c.true("light cover is DIAGONAL: the same two rows are NOT, because its lines "
       "lean", row_pixels(light_tile, mid) != row_pixels(light_tile, mid + 3))
# ...and the lean is exactly 45 degrees, which is the claim the wrap rests on.
# The stripes run down-LEFT (x = start - y), so a row `shift` further down is
# the same row moved LEFT by `shift`, and rolling it back RIGHT restores it.
# Rolling it the other way is what this probe did first: it failed against
# perfectly good art, because a wrong DIRECTION here is indistinguishable from
# a broken pattern.
shift = 3
rolled = row_pixels(light_tile, mid + shift)
rolled = rolled[-shift:] + rolled[:-shift]
c.eq("...at 45 degrees, so rolling a lower row back right by its own offset "
     "restores the one above it", rolled, row_pixels(light_tile, mid))


# --- 4. the tiles wrap -----------------------------------------------------

# game/renderer.py tiles these grid-aligned to the board's own origin, so two
# separate footprints show one continuous pattern - which only works if the
# tile meets itself cleanly. Checked on a real 3-tile strip.
def strip_of(tile, count=3):
    out = pygame.Surface((tile.get_width() * count, tile.get_height()))
    for i in range(count):
        out.blit(tile, (i * tile.get_width(), 0))
    return out


dense_strip = strip_of(dense_tile)
runs = bright_columns(dense_strip, dense_strip.get_height() // 2,
                      arena_biome.DENSE_PLATE_EDGE[2] - 10)
c.true(f"the dense lattice draws one plate edge per tile, never a doubled one "
       f"at the seam (widths {[w for _, w in runs]})",
       len(runs) == 3 and len({w for _, w in runs}) == 1)
c.true("...evenly spaced, i.e. the seam is not visible as a gap either",
       len({runs[i + 1][0] - runs[i][0] for i in range(len(runs) - 1)}) == 1)

light_strip = strip_of(light_tile)
pitch = max(2, round(arena_biome.LIGHT_HATCH_PITCH_IN
                     * light_tile.get_width() / arena_biome.COVER_TILE_SIZE_IN[
                         biomes.LIGHT_COVER]))
seam = light_tile.get_width()
mismatches = sum(
    1
    for y in range(0, light_strip.get_height(), 3)
    for x in range(seam - pitch * 2, seam + pitch)
    if light_strip.get_at((x, y))[:3] != light_strip.get_at((x + pitch, y))[:3]
)
c.eq("the diagonal hatch repeats across the seam with no break at all "
     "(its pitch divides the tile size, which is what makes it wrap)",
     mismatches, 0)
c.true("...and that is not vacuous - the pitch really does divide the tile",
     (arena_biome.COVER_TILE_SIZE_IN[biomes.LIGHT_COVER]
      / arena_biome.LIGHT_HATCH_PITCH_IN) % 1 == 0)

# A plate boundary lands ON a grid line rather than half a cell off it - the
# reason the arena picks its own tile size instead of reusing the renderer's.
for role, size_in in arena_biome.COVER_TILE_SIZE_IN.items():
    c.true(f"{role}: its tile is a whole number of minor grid cells ({size_in}\")",
           size_in % arena_biome.GRID_MINOR_IN == 0)
c.true("...which the renderer's photographic dense size is NOT, so reusing it "
       "would have put every plate edge half a cell off the floor grid",
       rmod.DENSE_COVER_TILE_SIZE_IN % arena_biome.GRID_MINOR_IN != 0)


# --- 5. the renderer really goes there -------------------------------------

# Three seams, and a drawn biome that is never reached renders as a flat fill -
# this repo has found five controllers that were built and never fed, so the
# wiring is checked at the CALL rather than by counting a name.
for call in ("arena_biome.ground_surface(board)",
             "arena_biome.cover_tile(role, board)",
             "arena_biome.draw_wall(surface, board, points)"):
    c.true(f"main render path calls {call}", call in RENDERER_SRC)
c.eq("...each gated on biomes.is_procedural(), once per seam",
     RENDERER_SRC.count("if biomes.is_procedural():"), 3)

# End to end, which is the half a source guard cannot give. Same board, two
# biomes: every one of the three surfaces has to come out different.
config.BIOME = "desert"
_, desert_state, desert_board = scene("map2")
desert_surface = render(desert_state, desert_board)
state, board = desert_state, desert_board
desert = {
    "ground": mean_rgb(desert_surface, open_ground_patch()),
    "dense": mean_rgb(desert_surface, cover_patch(True)),
    "wall": mean_rgb(desert_surface, wall_patch()),
}
for role in ("ground", "dense", "wall"):
    c.true(f"{role}: the arena renders it differently from the photographed biome",
           colour_distance(arena[role], desert[role]) > 15)

# ...and the base rings are no worse off on the dark floor than on the shipped
# photographed ones - "the models vanished" is exactly what a dark floor risks.
# The bar is the WORST rim/floor pairing across the three photographed biomes,
# computed here, the same shape as the wall bar above and for the same reason.
#
# IT USED TO COMPARE AGAINST THE DESERT FLOOR ALONE, and that form was wrong in
# a way that only showed when a rim colour changed: it demanded MORE of a rim
# that happens to sit far from desert sand than of one that sits close to it.
# The green rim scores 75 on the arena floor - identical to the enemy red this
# very check accepts - and would have failed it purely for scoring 88 on sand.
worst_photo_rim = min(
    colour_distance(ring, photo_ground[key])
    for ring in (rmod.OWN_ARMY_COLOR, rmod.ENEMY_ARMY_COLOR)
    for key in photo_ground)
for label, ring in (("own army (green)", rmod.OWN_ARMY_COLOR),
                    ("enemy (red)", rmod.ENEMY_ARMY_COLOR)):
    on_arena = colour_distance(ring, arena["ground"])
    c.true(f"...a {label} ring reads on the arena floor at least as well as "
           f"the worst rim reads on a photographed one ({on_arena:.0f} vs "
           f"{worst_photo_rim:.0f})", on_arena >= worst_photo_rim)

# The flat-fill fallback is what MISSING art gets. The arena must not get it -
# that is exactly what the is_procedural() branch prevents, and it is the
# failure that would be hardest to spot: config.BACKGROUND_COLOR is itself a
# dark blue-grey, so an un-wired arena still looks like a plausible dark board.
# Which means mean colour cannot answer this (they sit a few points apart) and
# the GRID has to.
config.BIOME = "arena"
arena_biome.clear_cache()
flat = pygame.Surface((board.width_px, board.height_px))
flat.fill(config.BACKGROUND_COLOR)
painted = arena_biome.ground_surface(Board(60.0, 44.0, 30.0))
c.true("...it carries a grid, which a flat fill by definition does not",
       len(bright_columns(painted, round(painted.get_height() * 0.3), 62)) > 5
       and len(bright_columns(flat, round(flat.get_height() * 0.3), 62)) == 0)


# --- 6. the caches ---------------------------------------------------------

arena_biome.clear_cache()
big = Board(60.0, 44.0, 30.0)
first = arena_biome.ground_surface(big)
c.true("the ground is cached, so the static layer is not repainted per frame",
       arena_biome.ground_surface(Board(60.0, 44.0, 30.0)) is first)
c.true("...keyed by PIXEL SIZE, not by Board identity - map_preview builds a "
       "throwaway Board per render",
       arena_biome.ground_surface(Board(30.0, 22.0, 60.0)) is first)
c.true("a different pixel size gets its own",
       arena_biome.ground_surface(Board(60.0, 44.0, 31.0)) is not first)
tile = arena_biome.cover_tile(biomes.DENSE_COVER, big)
c.true("cover tiles are cached too", arena_biome.cover_tile(biomes.DENSE_COVER, big) is tile)
c.true("...and the two roles are two different tiles",
       arena_biome.cover_tile(biomes.LIGHT_COVER, big) is not tile)
arena_biome.clear_cache()
c.true("clear_cache() really drops them",
       arena_biome.ground_surface(big) is not first)

config.BIOME = _ORIGINAL_BIOME
c.finish()
