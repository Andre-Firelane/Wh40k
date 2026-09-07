"""The ARENA biome: a battlefield that is PAINTED, not photographed.

User: "ich bin unzufrieden mit dem aussehen der maps. versuchen wir mal einen
anderen weg. neben den 3 biomen soll es noch eine 4. option geben. dort besteht
die map nicht aus sprites, sondern du renderst sie. sie soll aussehen, wie eine
simulations arena. aehnlicher look wie das interface. eventuell mit leichten
farbverlaeufen oder ein ganz subtiles kariertes muster. natuerlich dann
unterschiedlich: boden, dense cover, light cover"

The other three biomes are three PICTURES on disk (game/biomes.py). This one
has no folder at all - it answers the same three roles with drawing code, so
`Biome.folder is None` is what marks it and biomes.is_procedural() is how the
renderer asks.

WHY THAT IS WORTH A MODULE RATHER THAN A FOURTH FOLDER OF ART:

  * It is resolution-independent. Every measurement below is in INCHES and goes
    through board.in_to_px_len(), so the grid is the same grid on the
    map-select preview (~11 px/inch) and on the real board (~62 px/inch) - a
    photo has one resolution and is stretched to whatever it is asked for.
  * It matches the HUD, and can keep matching it: the palette here is derived
    from game/ui/button_style.py's panel colours rather than eyeballed beside
    them, so the board reads as part of the same instrument the panels are.
  * The grid IS the ruler. Minor lines sit one inch apart and major ones every
    six, which are two distances this game actually measures in (coherency and
    the Engagement Range band; the 6" centre circle and the board-quarter lines
    the renderer already draws). On a sand photo that information does not
    exist.

THE THREE ROLES ARE SEPARATED BY PATTERN FIRST, BRIGHTNESS SECOND - not by
hue. The renderer's split is "footprint with a wall on it" against "without"
(see game/sprites.py), and a player has to read that at a glance across a whole
board:

  ground        flat grid, darkest, no pattern of its own beyond the checker
  dense cover   a LATTICE of plates - orthogonal, brightest, reads as a floor
                you can walk into with walls rising out of it
  light cover   DIAGONAL hatching, dimmer and sparser - reads as a marked-off
                patch of rubble rather than a structure

Two orthogonal cues, so the split survives both a colour-blind player and the
TERRAIN_TILE_ALPHA blend the renderer puts these through.

THE TILES ARE SEAMLESS, and that is a constraint on how they are drawn rather
than a claim: game/renderer.py tiles them grid-aligned to the board's own
(0,0), so a pattern that did not wrap would show a visible break at every tile
boundary and two adjacent footprints would not line up. Every line below is
drawn at the tile's TOP/LEFT edge only (its partner comes from the neighbouring
tile) or at an offset that repeats modulo the tile size. Pinned in
test_arena_biome.py by wrapping a tile against itself.

NO FILESYSTEM AND NO CONFIG here, same as game/biomes.py: this module answers
"what does the arena look like", nothing else. It is handed a Board and returns
Surfaces.
"""

import math

import pygame

from game import biomes

# ---------------------------------------------------------------------------
# Palette. Every value is anchored to the HUD rather than picked beside it, so
# "aehnlicher look wie das interface" stays true if the interface is retuned.
#
# game/ui/button_style.py is deliberately NOT imported: it lives under game/ui/
# and pulls the panel stack in with it, while this module runs on the render
# path and is imported by game/renderer.py. The four values it would supply are
# restated here WITH the name of their source, and test_arena_biome.py pins
# each one against button_style itself - so the two cannot drift apart
# silently, which is the only thing the import would have bought.
# ---------------------------------------------------------------------------

#: button_style.BOX_BG_COLOR (10, 18, 28) - the darkest thing the HUD draws,
#: and the floor of the arena is the same surface as the back of a panel.
GROUND_BASE = (10, 18, 28)
#: How much brighter the middle of the board is than its corners: a floor lit
#: from above. It gives the flat fill somewhere to go without introducing a
#: second colour. ADDED, so nothing can come out darker than GROUND_BASE.
GROUND_CENTRE_LIFT = (10, 16, 24)
#: The alternating 6" cells ("ein ganz subtiles kariertes muster"). Deliberately
#: tiny - at +5 per channel it is a texture you notice only once you look for
#: it, which is what "subtil" asks for, and it keeps the gradient from banding.
GROUND_CHECKER_LIFT = 5

#: button_style.BORDER_NORMAL (60, 150, 205) - the cyan every panel edge and
#: every button outline is already drawn in.
GRID_COLOR = (60, 150, 205)
GRID_MINOR_ALPHA = 30
GRID_MAJOR_ALPHA = 62
#: The board's outer edge, in button_style.BORDER_HOVER (110, 210, 255) - the
#: brightest line on the table, so the play area reads as a bounded arena
#: rather than as a texture that happens to stop.
EDGE_COLOR = (110, 210, 255)
EDGE_ALPHA = 90

#: How far apart the two grids sit, in inches. Not decoration: these are
#: distances the rules measure in - 1" is unit coherency and the Engagement
#: Range band, 6" is the centre circle the renderer already draws and the step
#: its board-quarter lines fall on.
GRID_MINOR_IN = 1.0
GRID_MAJOR_IN = 6.0
#: Line widths in INCHES, so they hold their weight at any board resolution
#: (~11 px/inch on the map-select preview, ~62 in the game). Clamped to at
#: least one pixel below, or the minor grid would vanish from the preview.
GRID_MINOR_WIDTH_IN = 0.03
GRID_MAJOR_WIDTH_IN = 0.06
EDGE_WIDTH_IN = 0.10

#: The resolution the centre lift is computed at before being scaled up to the
#: board. 96x96 costs ~9k Python iterations once per board size; scaling it is
#: C. Any finer is invisible after a smoothscale over several megapixels.
GRADIENT_SAMPLES = 96

# --- cover -----------------------------------------------------------------
#: One tile's width in inches, per role. The arena declares its own rather than
#: reusing the renderer's DENSE_COVER_TILE_SIZE_IN/NORMAL_COVER_TILE_SIZE_IN:
#: those were picked so a PHOTOGRAPH's flagstones and boulders came out at a
#: believable real-world size, and a drawn lattice has no such scale to match.
#: 3" is a whole number of minor grid cells, so a plate boundary always lands
#: ON a grid line instead of half a cell off it.
COVER_TILE_SIZE_IN = {biomes.DENSE_COVER: 3.0, biomes.LIGHT_COVER: 3.0}

#: Dense cover - a footprint with a wall standing on it. The brightest and most
#: solid of the three: a plate, one interior subdivision, and a corner bracket.
DENSE_FILL = (36, 62, 88)
DENSE_PLATE_EDGE = (95, 175, 220)
DENSE_SUBDIVISION = (52, 88, 118)
DENSE_SUBDIVISION_IN = 1.0
DENSE_CORNER_IN = 0.55        # bracket length at the plate corner
DENSE_SUBDIVISION_WIDTH_IN = 0.025
DENSE_EDGE_WIDTH_IN = 0.05
DENSE_BRACKET_WIDTH_IN = 0.09

#: Light cover - a footprint with no wall. Diagonal hatching over a fill only a
#: little above the ground, so it reads as a marked-off patch rather than a
#: structure. The stripe pitch divides the tile size, which is what makes the
#: 45-degree pattern wrap.
LIGHT_FILL = (20, 34, 48)
LIGHT_HATCH = (66, 122, 162)
LIGHT_HATCH_PITCH_IN = 0.5
LIGHT_HATCH_WIDTH_IN = 0.08

# --- walls -----------------------------------------------------------------
# A FOURTH thing, and it needs saying why: DENSE terrain is not one of the
# three roles a biome answers - game/renderer.py draws it as one flat
# OBSTACLE_COLOR block whichever biome is playing, and that works for the three
# photographed ones because all three of their grounds are LIGHT (sand, grey
# concrete, brown forest floor), so a near-black block stands out on all of
# them.
#
# This ground is dark, so it does not. MEASURED on map2 as mean colour distance
# from the open ground beside it: desert 137, forest 30, city 22 - and the
# arena, with the shared colour, 11.8, the worst of the four by half. Walls are
# the terrain that blocks line of sight, i.e. the single most important thing
# on the table to be able to read at a glance, so the arena supplies its own
# rather than inheriting one chosen against a different floor.
#
# Drawn the way the HUD draws a solid thing - a mid-tone body with a bright
# edge on it, exactly like a panel - rather than as a brighter flat block,
# which at this size read as a light-coloured hole in the floor.
WALL_FILL = (58, 84, 112)
WALL_EDGE = (150, 205, 240)
WALL_EDGE_WIDTH_IN = 0.09

_ground_cache = {}   # (width_px, height_px) -> Surface
_tile_cache = {}     # (role, tile_px) -> Surface


def clear_cache():
    """Drop both caches - for tests that render at many resolutions in one run,
    and for anything that retunes the palette between renders."""
    _ground_cache.clear()
    _tile_cache.clear()


def _px(board_or_ppi, length_in, minimum=1):
    """`length_in` inches in whole pixels, never less than `minimum`.

    Takes either a Board or a bare pixels-per-inch float, because the cover
    tiles are drawn from their own resolved tile size rather than from the
    board directly - see cover_tile()."""
    ppi = getattr(board_or_ppi, "px_per_inch", board_or_ppi)
    return max(minimum, round(length_in * ppi))


def ground_surface(board):
    """The whole arena floor at this board's resolution.

    Cached by PIXEL SIZE rather than by Board identity: game/ui/map_preview.py
    builds a throwaway Board per render, and this is expensive enough (a
    gradient plus a few hundred blits over a multi-megapixel surface) to be
    worth reusing when the same map is rendered again after a trip through
    another biome."""
    size = (board.width_px, board.height_px)
    cached = _ground_cache.get(size)
    if cached is not None:
        return cached
    surface = pygame.Surface(size)
    surface.fill(GROUND_BASE)
    _draw_centre_lift(surface, size)
    _draw_checker(surface, board)
    _draw_grid(surface, board)
    _draw_edge(surface, board)
    _ground_cache[size] = surface
    return surface


def _draw_centre_lift(surface, size):
    """A soft radial lift toward the middle of the board.

    Computed on a GRADIENT_SAMPLES square and smoothscaled up rather than drawn
    as concentric shapes: the scale-up is what makes the falloff smooth at any
    board size, where circles band. Added (BLEND_RGB_ADD), so the corners keep
    exactly GROUND_BASE and the picture only ever GAINS light in the middle -
    a multiply would have made the corners darker than the panel behind them."""
    small = pygame.Surface((GRADIENT_SAMPLES, GRADIENT_SAMPLES))
    half = (GRADIENT_SAMPLES - 1) / 2.0
    lift_r, lift_g, lift_b = GROUND_CENTRE_LIFT
    for y in range(GRADIENT_SAMPLES):
        dy = (y - half) / half
        for x in range(GRADIENT_SAMPLES):
            dx = (x - half) / half
            # 1 at the centre, 0 at the edge midpoints and clamped to 0 in the
            # corners; squared so the bright core stays small and the falloff
            # is gentle rather than a visible disc.
            t = max(0.0, 1.0 - math.hypot(dx, dy))
            t *= t
            small.set_at((x, y),
                         (round(lift_r * t), round(lift_g * t), round(lift_b * t)))
    surface.blit(pygame.transform.smoothscale(small, size), (0, 0),
                 special_flags=pygame.BLEND_RGB_ADD)


def _draw_checker(surface, board):
    """The "ganz subtiles kariertes muster": every other GRID_MAJOR_IN cell
    lifted by GROUND_CHECKER_LIFT.

    Stepped in board INCHES, so the checker lines up with the major grid
    exactly - the two are the same cell, one filled and one outlined, rather
    than two patterns that nearly agree."""
    cell = board.in_to_px_len(GRID_MAJOR_IN)
    cols = int(math.ceil(board.width_in / GRID_MAJOR_IN))
    rows = int(math.ceil(board.height_in / GRID_MAJOR_IN))
    patch = pygame.Surface((math.ceil(cell) + 1, math.ceil(cell) + 1))
    patch.fill((GROUND_CHECKER_LIFT,) * 3)
    for row in range(rows):
        for col in range(cols):
            if (row + col) % 2:
                continue
            surface.blit(patch, (round(col * cell), round(row * cell)),
                         special_flags=pygame.BLEND_RGB_ADD)


def _draw_grid(surface, board):
    """Minor grid then major, in that order, so a major line always wins where
    the two coincide - every sixth one does."""
    for step_in, alpha, width_in in (
        (GRID_MINOR_IN, GRID_MINOR_ALPHA, GRID_MINOR_WIDTH_IN),
        (GRID_MAJOR_IN, GRID_MAJOR_ALPHA, GRID_MAJOR_WIDTH_IN),
    ):
        width = _px(board, width_in)
        vertical = pygame.Surface((width, board.height_px), pygame.SRCALPHA)
        vertical.fill((*GRID_COLOR, alpha))
        horizontal = pygame.Surface((board.width_px, width), pygame.SRCALPHA)
        horizontal.fill((*GRID_COLOR, alpha))
        for i in range(int(board.width_in / step_in) + 1):
            x = round(board.in_to_px_len(i * step_in))
            if x < board.width_px:
                surface.blit(vertical, (x, 0))
        for i in range(int(board.height_in / step_in) + 1):
            y = round(board.in_to_px_len(i * step_in))
            if y < board.height_px:
                surface.blit(horizontal, (0, y))


def _draw_edge(surface, board):
    """The bright boundary of the play area, stroked INSIDE the board so the
    whole line is on screen - a rect stroked ON the edge would lose its outer
    half to the surface bounds and read half as bright as it should."""
    width = _px(board, EDGE_WIDTH_IN)
    frame = pygame.Surface((board.width_px, board.height_px), pygame.SRCALPHA)
    pygame.draw.rect(frame, (*EDGE_COLOR, EDGE_ALPHA), frame.get_rect(), width=width)
    surface.blit(frame, (0, 0))


def cover_tile(role, board):
    """One seamless tile for `role` (biomes.DENSE_COVER / LIGHT_COVER), sized to
    COVER_TILE_SIZE_IN[role] at this board's resolution.

    Returns an OPAQUE Surface, exactly as game/renderer.py's _cached_tile()
    does for a photographed biome - the renderer blends it at
    TERRAIN_TILE_ALPHA either way, so both paths hand it the same kind of thing
    and the masked-tile blend fix applies to both without a second branch."""
    size_in = COVER_TILE_SIZE_IN[role]
    tile_px = _px(board, size_in)
    cached = _tile_cache.get((role, tile_px))
    if cached is not None:
        return cached
    # The tile's OWN pixels-per-inch, not the board's: tile_px is rounded, so
    # at low resolutions the two differ by up to half a pixel per inch, and
    # every feature inside the tile has to be laid out against the size the
    # tile actually came out at or the pattern stops meeting its own edge.
    ppi = tile_px / size_in
    tile = (_dense_tile(tile_px, ppi) if role == biomes.DENSE_COVER
            else _light_tile(tile_px, ppi))
    _tile_cache[(role, tile_px)] = tile
    return tile


def _dense_tile(tile_px, ppi):
    """A structural plate: fill, interior subdivisions, a bright edge along the
    top and left, and a bracket at that corner.

    ONLY the top and left edges are stroked. The neighbouring tile supplies the
    other half of every seam, so stroking all four would draw each interior
    line twice at double width - which is also why the brackets run from that
    corner outward rather than being centred on it."""
    tile = pygame.Surface((tile_px, tile_px))
    tile.fill(DENSE_FILL)
    sub = _px(ppi, DENSE_SUBDIVISION_IN)
    thin = _px(ppi, DENSE_SUBDIVISION_WIDTH_IN)
    for offset in range(sub, tile_px, sub):
        pygame.draw.rect(tile, DENSE_SUBDIVISION, (offset, 0, thin, tile_px))
        pygame.draw.rect(tile, DENSE_SUBDIVISION, (0, offset, tile_px, thin))
    edge = _px(ppi, DENSE_EDGE_WIDTH_IN)
    pygame.draw.rect(tile, DENSE_PLATE_EDGE, (0, 0, tile_px, edge))
    pygame.draw.rect(tile, DENSE_PLATE_EDGE, (0, 0, edge, tile_px))
    bracket = max(edge + 1, _px(ppi, DENSE_CORNER_IN))
    thick = _px(ppi, DENSE_BRACKET_WIDTH_IN)
    pygame.draw.rect(tile, DENSE_PLATE_EDGE, (0, 0, bracket, thick))
    pygame.draw.rect(tile, DENSE_PLATE_EDGE, (0, 0, thick, bracket))
    return tile


def draw_wall(surface, board, points):
    """One DENSE obstacle (a wall), as a solid body with a bright edge.

    `points` is the obstacle's four corners in pixels, already rotated - the
    renderer's own obstacle_points_px(). A POLYGON rather than a rect for the
    same reason it uses one everywhere else: for a rotated wall the bounding
    box is the shape the rules do NOT use.

    Two draws where the photographed biomes do one. See WALL_FILL above for the
    measurement that bought the second: a flat block in this palette is not
    readable against this floor, and an edge is what the rest of the interface
    puts on a solid thing anyway."""
    pygame.draw.polygon(surface, WALL_FILL, points)
    pygame.draw.polygon(surface, WALL_EDGE, points,
                        width=_px(board, WALL_EDGE_WIDTH_IN))


def _light_tile(tile_px, ppi):
    """Diagonal hatching over a near-ground fill.

    The stripes run at 45 degrees and repeat every LIGHT_HATCH_PITCH_IN, which
    divides COVER_TILE_SIZE_IN - so a stripe leaving the right edge at height h
    re-enters the next tile's left edge at that same h and the hatch is
    continuous across a whole footprint. Each stripe is drawn from the top edge
    down-LEFT; the ones starting past the right edge are what fill the
    bottom-left corner, which is why the loop runs to twice the tile width."""
    tile = pygame.Surface((tile_px, tile_px))
    tile.fill(LIGHT_FILL)
    pitch = max(2, _px(ppi, LIGHT_HATCH_PITCH_IN))
    width = _px(ppi, LIGHT_HATCH_WIDTH_IN)
    for start in range(0, tile_px * 2, pitch):
        pygame.draw.line(tile, LIGHT_HATCH,
                         (start, 0), (start - tile_px, tile_px), width)
    return tile
