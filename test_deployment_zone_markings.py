"""HOW the deployment zones are MARKED - colour and thickness.

User: "nur die aufstelllungszonen muessen sichtbarer sein. mach die
markierungen dicker. gegener: rot / spieler: gruen"

There was no test for any of this, and that is the reason the report exists.
game/renderer.py draws two things per zone - the traced boundary and a thicker
highlight along the stretch of board edge that zone owns - and BOTH widths were
handed to pygame.draw.line() raw, on a surface main.py renders at several times
the on-screen resolution. So the numbers in the source described a line nobody
had ever seen: measured at default zoom on a 1920x1080 window, the "2 pixel"
outline landed on 0.70 of a screen pixel on map2 and 0.37 on map1.

That is the same defect that produced TOKEN_INNER_RING_WIDTH, and
Renderer._ring_width() is the correction that already existed for it. So the
checks here are in ON-SCREEN pixels throughout - the only unit in which "make
it thicker" means anything - and section 3 pins the pre-change numbers so the
fix cannot quietly be undone.

test_deployment_shapes.py owns the zone SHAPES (what is inside, which board
edges are whose). This file owns what they LOOK like.

Run: python test_deployment_zone_markings.py
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((400, 300))

from game import config, maps, render_resolution, renderer as rmod  # noqa: E402
from game.board import Board  # noqa: E402
from game.deployment import DeploymentZone  # noqa: E402
from game.renderer import Renderer  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("deployment zone markings")

BW, BH = 60.0, 44.0
ZONE_DEPTH = 12.0


def zones():
    """The shipped arrangement: Player 2 along the north edge, Player 1 along
    the south - the same way round every shipped map has them."""
    return [
        DeploymentZone("Player 2", [(BW / 2, ZONE_DEPTH / 2, BW, ZONE_DEPTH)]),
        DeploymentZone("Player 1", [(BW / 2, BH - ZONE_DEPTH / 2, BW, ZONE_DEPTH)]),
    ]


def zone_layer(render_scale=1.0, ppi=30.0):
    """Just the zone overlay, on black.

    Drawn on its own rather than measured off a finished board, so the ground
    art and the terrain cannot contribute a pixel to a width measurement - and
    so the answer is the same in every biome."""
    board = Board(BW, BH, ppi)
    surface = pygame.Surface((board.width_px, board.height_px))
    surface.fill((0, 0, 0))
    Renderer(render_scale=render_scale)._draw_deployment_zones(surface, board, zones())
    return surface, board


def runs(surface, x, dominant):
    """Lengths of the vertical runs at column `x` where `dominant` is the
    strongest channel - i.e. how many pixels thick each marking is."""
    out = []
    run = 0
    for y in range(surface.get_height()):
        r, g, b = surface.get_at((x, y))[:3]
        channels = {"r": r, "g": g, "b": b}
        hit = (max(channels, key=channels.get) == dominant
               and channels[dominant] > 40)
        if hit:
            run += 1
        elif run:
            out.append(run)
            run = 0
    if run:
        out.append(run)
    return out


# --- 1. the colours --------------------------------------------------------

player = rmod.DEPLOYMENT_ZONE_LINE_COLORS["Player 1"]
enemy = rmod.DEPLOYMENT_ZONE_LINE_COLORS["Player 2"]
c.true(f"the player's zone is GREEN {player[:3]}",
       player[1] > player[0] and player[1] > player[2])
c.true(f"the enemy's zone is RED {enemy[:3]}",
       enemy[0] > enemy[1] and enemy[0] > enemy[2])
c.true("...and neither is the blue it used to be",
       player[2] < player[1] and enemy[2] < enemy[0])

# It is keyed by OWNER, which is the only handle the renderer has: it has no
# notion of which player is the human. The same assumption the table has always
# made - Player 1 is the one being played.
c.eq("one colour per player, and nothing else in the table",
     sorted(rmod.DEPLOYMENT_ZONE_LINE_COLORS), ["Player 1", "Player 2"])
c.true("an unowned zone still draws, in a neutral grey",
       len(set(rmod.DEPLOYMENT_ZONE_FALLBACK_COLOR[:3])) == 1)

# Green and red are the two ends of the most common colour-blindness, so the
# two also have to differ in BRIGHTNESS rather than hue alone. Measured as
# luminance, not asserted.
lum = lambda rgb: 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]  # noqa: E731
c.true(f"they differ in brightness too, not only in hue "
       f"(player {lum(player):.0f} vs enemy {lum(enemy):.0f})",
       abs(lum(player) - lum(enemy)) > 40)

# ...and they really reach the board. Drawn, then read back off the surface.
surface, board = zone_layer()
north = round(board.in_to_px_len(ZONE_DEPTH))          # the enemy zone's inner edge
south = round(board.in_to_px_len(BH - ZONE_DEPTH))     # the player's
mid_x = board.width_px // 2
c.true("the enemy's boundary really is drawn red",
       max(range(3), key=lambda i: surface.get_at((mid_x, north))[i]) == 0)
c.true("the player's boundary really is drawn green",
       max(range(3), key=lambda i: surface.get_at((mid_x, south))[i]) == 1)


# --- 2. the widths are in ON-SCREEN pixels ---------------------------------

# The fix. Both constants are on-screen pixels and go through _ring_width(), so
# doubling the board's render resolution has to double the drawn line - the
# thing that was NOT true before, and the reason the markings were invisible.
plain, board = zone_layer(render_scale=1.0)
scaled, _ = zone_layer(render_scale=3.0)
plain_runs = runs(plain, mid_x, "g")
scaled_runs = runs(scaled, mid_x, "g")
c.eq("at render_scale 1 the player's zone draws its two markings",
     len(plain_runs), 2)
c.eq("...and so does the supersampled one", len(scaled_runs), 2)
# Compared against the width each scale ASKS FOR, not against 3x the scale-1
# measurement. The two differ by a sub-pixel quantisation at the board edge:
# the player's band is inset from the SOUTH edge, and at scale 1 a 5-wide band
# reads back as 4 there while the enemy's north one reads 5. Harmless in the
# game (at a real render scale of ~3.4 that is 1 row of 17, well under a screen
# pixel) but it is a whole 20% of a 5-pixel measurement, so folding it into a
# +/-1 tolerance made this check quietly depend on the constants being LARGE.
asked = [max(1, round(w * s))
         for s in (1.0, 3.0)
         for w in (rmod.DEPLOYMENT_ZONE_LINE_WIDTH, rmod.BOARD_EDGE_LINE_WIDTH)]
c.true(f"...three times as thick, because the width follows the render scale "
       f"({plain_runs} -> {scaled_runs}, asked {asked})",
       all(abs(drawn - want) <= 1
           for drawn, want in zip(plain_runs + scaled_runs, asked)))
c.true("...and 3x is really what the scale asks for, so the check above is "
       f"about the drawing and not about the arithmetic ({asked})",
       asked[2] >= 2.5 * asked[0] and asked[3] >= 2.5 * asked[1])

RENDERER_SRC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "game", "renderer.py"), encoding="utf-8").read()
c.true("the outline width goes through _ring_width()",
       "line_width = self._ring_width(DEPLOYMENT_ZONE_LINE_WIDTH)" in RENDERER_SRC)
c.true("...and so does the board-edge highlight",
       "self._ring_width(BOARD_EDGE_LINE_WIDTH))" in RENDERER_SRC)
c.true("...and neither constant is handed to pygame raw any more",
       "width=DEPLOYMENT_ZONE_LINE_WIDTH" not in RENDERER_SRC
       and "width=BOARD_EDGE_LINE_WIDTH" not in RENDERER_SRC)

# The board-edge highlight is drawn at the SAME width as the boundary. User:
# "bei den Aufstellungszonen gibt es an den spielfeldraendern sehr dicke
# Linien. koennen die genau so dick sein wie die innenliegenden Linien?"
#
# It used to be the thicker of the two, and this check used to say so.
# "Zuordnung der Spielfeldkanten" survives that: which edge belongs to whom is
# carried by the line's COLOUR and by its PRESENCE (an edge nobody owns gets no
# line at all), never by how thick it was.
#
# Read through a guard rather than by unpacking: two A/B probes (the zone drawn
# blue, and the zone drawn as a fill) make this list the wrong length, and an
# unpack THROWS where a check goes red - which hides which claim broke. Third
# time this repo has learned that; see the str.index()/find() note in CLAUDE.md.
ordered = sorted(plain_runs, reverse=True)
c.eq("the player's zone draws exactly two markings to compare", len(ordered), 2)
edge_run, outline_run = (ordered + [0, 0])[:2]
c.eq(f"the board-edge highlight is drawn exactly as thick as the boundary "
     f"({edge_run} vs {outline_run})", edge_run, outline_run)
# DERIVED, not two literals that happen to match today: equality is the whole
# request, and two numbers tuned separately is how it stops being true.
#
# Asserted at the SOURCE and not with `is`. An identity check here would be a
# TAUTOLOGY: CPython folds equal float constants in one module into one object,
# so `2.4 is 2.4` across two separate assignments is True and the check would
# pass for exactly the copy it is meant to forbid. (Measured before it shipped -
# the same trap as the palette-constant check in test_biomes.py.)
c.eq("the edge width equals the boundary width",
     rmod.BOARD_EDGE_LINE_WIDTH, rmod.DEPLOYMENT_ZONE_LINE_WIDTH)
c.true("...written as a derivation in the source, not copied",
       "BOARD_EDGE_LINE_WIDTH = DEPLOYMENT_ZONE_LINE_WIDTH" in RENDERER_SRC)
# The inset keeps the whole edge line ON the board: half of it hanging off the
# surface is exactly how a 7-pixel highlight reads as 3. Compared against the
# width actually DRAWN at this scale, not against the constant - the constant
# is a float in on-screen pixels and the measurement is whole rows.
enemy_runs = runs(plain, mid_x, "r")
c.eq("...and all of it lands on the board, none of it off the top edge",
     (enemy_runs + [0])[0],
     Renderer(render_scale=1.0)._ring_width(rmod.BOARD_EDGE_LINE_WIDTH))


# --- 3. how thick they end up on screen, and what they were -----------------

# The values that SHIPPED, drawn raw. They are what "before" has to be computed
# from - using today's constants for both sides is what this probe did first,
# and it flattered the pre-change world by half a pixel.
PRE_CHANGE_OUTLINE_WIDTH = 2
PRE_CHANGE_EDGE_WIDTH = 5


def on_screen(width_const, win_w, win_h, board_w_in, board_h_in, pre_change):
    """(what this width reaches the eye as today, what the SHIPPED raw value
    did before).

    main() renders the board at a derived resolution and the camera then shows
    it at a fit-to-area zoom, so what arrives is constant * render_scale *
    camera today, and constant * camera before - the render_scale being exactly
    the factor that used to be dropped."""
    area_w = win_w - config.LEFT_PANEL_WIDTH - config.RIGHT_PANEL_WIDTH
    area_h = win_h - config.RESERVES_PANEL_HEIGHT
    ppi = render_resolution.board_pixels_per_inch(area_w, area_h, board_w_in, board_h_in)
    brd = Board(board_w_in, board_h_in, ppi)
    camera = min(area_w / brd.width_px, area_h / brd.height_px)
    scale = ppi / config.PIXELS_PER_INCH
    return max(1, round(width_const * scale)) * camera, pre_change * camera


# THE BAR IS A RATIO, NOT AN ABSOLUTE. render_scale * camera works out to
# area_px / (board_in * config.PIXELS_PER_INCH), i.e. how much of "nominal"
# the board is being shown at - so on a small window EVERY on-screen-pixel
# measurement in this renderer shrinks together, model rims and fonts included.
# An absolute floor would therefore not be a statement about the zone markings
# at all; it would be a statement about the window. Measured at 1366x768 map1
# the whole board runs at 58% of nominal, and a boundary lands on 1.8 px there
# against 3.5 at 1920x1080.
#
# So the two claims that ARE about the markings: the fix multiplied them by the
# render scale, and they are thicker than the model rim they sit under - the
# reference the user has already accepted as readable.
#
# THE FIRST IS PHRASED AGAINST TODAY'S CONSTANT, with and without the scale,
# not against the shipped pre-change one. It used to demand "2.5x the old raw
# value", which silently mixed the FIX in with whatever the constants happened
# to be tuned to - so trimming them on request (3 -> 2.4 and 7 -> 5, User: "mach
# sie bitte etwas duenner") read as the fix regressing. The pre-change numbers
# stay, as the report they were: under a screen pixel.
for win in ((1920, 1080), (1366, 768)):
    for map_key in ("map1", "map2", "map3", "map4"):
        battle_map = maps.get(map_key)
        now, before = on_screen(rmod.DEPLOYMENT_ZONE_LINE_WIDTH, *win,
                                battle_map.width_in, battle_map.height_in,
                                PRE_CHANGE_OUTLINE_WIDTH)
        rim, _ = on_screen(rmod.TOKEN_BORDER_WIDTH + rmod.TOKEN_INNER_RING_WIDTH,
                           *win, battle_map.width_in, battle_map.height_in, 1)
        raw = on_screen(rmod.DEPLOYMENT_ZONE_LINE_WIDTH, *win, battle_map.width_in,
                        battle_map.height_in, rmod.DEPLOYMENT_ZONE_LINE_WIDTH)[1]
        c.true(f"{win[0]}x{win[1]} {map_key}: the boundary reaches the eye at "
               f"{now:.1f} screen pixels, not the {raw:.2f} it would raw",
               now >= raw * 2.0)
        c.true(f"{win[0]}x{win[1]} {map_key}: PRE-CHANGE it was under one whole "
               f"screen pixel ({before:.2f}) - the report", before < 1.0)
        c.true(f"{win[0]}x{win[1]} {map_key}: ...and it is thicker than a model's "
               f"base rim ({now:.1f} vs {rim:.1f}), which reads fine today",
               now > rim)
        now, before = on_screen(rmod.BOARD_EDGE_LINE_WIDTH, *win,
                                battle_map.width_in, battle_map.height_in,
                                PRE_CHANGE_EDGE_WIDTH)
        raw = on_screen(rmod.BOARD_EDGE_LINE_WIDTH, *win, battle_map.width_in,
                        battle_map.height_in, rmod.BOARD_EDGE_LINE_WIDTH)[1]
        c.true(f"{win[0]}x{win[1]} {map_key}: the edge highlight reaches the "
               f"eye at {now:.1f} screen pixels, not the {raw:.2f} it would raw",
               now >= raw * 2.0)
        c.true(f"{win[0]}x{win[1]} {map_key}: PRE-CHANGE it was {before:.2f} - "
               f"under two screen pixels for a five-pixel highlight",
               before < 2.0)
        # Stated for the EDGE line too, not left to follow from the two widths
        # being equal today: if they are ever separated again, this is the bar
        # the thinner one still has to clear.
        c.true(f"{win[0]}x{win[1]} {map_key}: ...and the edge line is still "
               f"thicker than a model's base rim ({now:.1f} vs {rim:.1f})",
               now > rim)


# --- 4. it did not become a wall -------------------------------------------

# "Sichtbarer" is not "covers the board". These are reference lines drawn on
# the CACHED static layer, under the terrain and every model - so the check is
# that the zone's INTERIOR is still bare, not just that the lines are bright.
surface, board = zone_layer(render_scale=3.0)
inside = surface.get_at((mid_x, round(board.in_to_px_len(BH - ZONE_DEPTH / 2))))[:3]
c.eq("the zone is an OUTLINE - its interior is not filled or tinted",
     inside, (0, 0, 0))
painted = sum(runs(surface, mid_x, "g")) + sum(runs(surface, mid_x, "r"))
# Against the sum of the four lines that column crosses (one boundary and one
# board edge per zone), not against a round percentage: this way it says the
# markings are EXACTLY the lines asked for, and anything that started filling
# or feathering them shows up as a number rather than as a judgement call. The
# tolerance is the marching-squares step - a traced boundary may wobble by a
# pixel where it crosses this column.
ring = Renderer(render_scale=3.0)._ring_width
expected = 2 * (ring(rmod.DEPLOYMENT_ZONE_LINE_WIDTH) + ring(rmod.BOARD_EDGE_LINE_WIDTH))
c.true(f"...and a column crosses exactly the four lines it should, no fill and "
       f"no bleed ({painted} px against {expected})", abs(painted - expected) <= 4)

c.finish()
