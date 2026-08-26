"""The battlefield floor is ONE picture covering the whole map, not a tile.

User: "aendere die bodentextur zu wueste-boden. aber wueste-boden ist keine
wiederholbare kachel. das sprite soll die gesamte map ausfuellen."

Two separate claims, and they need separate checks:

  * WHICH art - sprites.GROUND_TEXTURE_NAME now resolves to the desert
    file, not the old seamless Sprites/Ground.jpg (which is still in the
    folder, so "it renders something" would pass either way).
  * HOW it is drawn - Renderer._ground_image() scales a SINGLE copy to
    cover the board, so (a) every pixel of the board is painted, on a
    board of any aspect ratio, and (b) the picture appears exactly once.

(b) is what makes this a non-tile: the old path repeated a 12" tile, which
for this art would have shown its own frame and its large-scale features
several times over. It is checked with a synthetic source image carrying a
single marker patch - if anything tiled, that marker would show up in more
than one place. The same synthetic image also pins that this is a CROP and
not a stretch, i.e. that a square in the source is still square on a board
whose aspect ratio doesn't match it (map1 is portrait, the art is
landscape).

The two COVER textures went desert in the same pass and are checked here
too, but they are the opposite case: they still tile, and what needed
fixing there was that a tile was forced square. Every cover texture used to
be square so that was free; Dense_Cover-Desert.jpg is 1024x748.

Purely cosmetic; no rule reads the floor or the cover art.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from testkit import Checks

from game import sprites

c = Checks("ground texture")

pygame.init()
screen = pygame.display.set_mode((600, 400))

from game.board import Board          # noqa: E402  (needs a display)
from game import renderer as rmod     # noqa: E402
from game.renderer import Renderer    # noqa: E402

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


# --- which art -------------------------------------------------------------

path = sprites.ground_texture_path()
c.true("the ground art resolves", path is not None)
c.true("...to the desert floor the user asked for",
       path is not None and "boden" in os.path.basename(path).lower())
c.true("...and NOT to the old seamless tile, which is still in the folder",
       path is not None and os.path.basename(path) != "Ground.jpg")
c.true("PRE-CHANGE: that old tile is still present, so this check is not "
       "passing just because the file went away",
       sprites._resolve_path("Ground") is not None)


# --- how it is drawn: the real art, on both boards -------------------------

# map2 (60x44 landscape) is the configured board; map1 (44x60) is the one
# whose aspect ratio fights the art's own, so it is the interesting case.
for label, (w_in, h_in) in (("map2 60x44", (60.0, 44.0)), ("map1 44x60", (44.0, 60.0))):
    board = Board(w_in, h_in, 12.0)
    size = (board.width_px, board.height_px)
    image = Renderer._ground_image(path, size)
    c.eq(f"{label}: the floor is drawn at exactly the board's size", image.get_size(), size)

# It follows the zoom/render resolution like everything else on the board.
big = Renderer._ground_image(path, (Board(60.0, 44.0, 30.0).width_px,
                                    Board(60.0, 44.0, 30.0).height_px))
c.eq("a higher render resolution gets a correspondingly larger floor",
     big.get_size(), (1800, 1320))


# --- how it is drawn: one copy, aspect preserved ---------------------------

def marker_bbox(surface, color=(255, 255, 255)):
    """Bounding box of every pixel of `color` on `surface`, as
    (min_x, min_y, max_x, max_y), or None if there are none."""
    mask = pygame.mask.from_threshold(surface, color, (12, 12, 12, 255))
    rects = mask.get_bounding_rects()
    if not rects:
        return None
    box = rects[0].unionall(rects[1:]) if len(rects) > 1 else rects[0]
    return box, len(rects)


# A landscape source (same 1024x748-ish shape as the real art) carrying one
# square white marker, on a background that is never black - so an unpainted
# pixel of the destination Surface is detectable as black.
source = pygame.Surface((200, 100))
source.fill((180, 40, 40))
pygame.draw.rect(source, (255, 255, 255), pygame.Rect(90, 40, 20, 20))
source_path = os.path.join(SCRATCH, "_test_ground_probe.png")
os.makedirs(SCRATCH, exist_ok=True)
pygame.image.save(source, source_path)

# A PORTRAIT board, i.e. the aspect ratio that a plain stretch would smear.
board_size = (300, 400)
probe = Renderer._ground_image(source_path, board_size)
c.eq("the probe floor is exactly the board's size", probe.get_size(), board_size)

box, patch_count = marker_bbox(probe)
c.true("the marker survives the scale", box is not None)
c.eq("...exactly once - nothing is tiled", patch_count, 1)
if box is not None:
    ratio = box.width / box.height
    c.true(f"...and it is still square, not stretched (w/h = {ratio:.2f})",
           0.9 < ratio < 1.1)
    # Cover-scaling a 2:1 source onto a 3:4 board scales by height
    # (400/100 = 4x, against 300/200 = 1.5x), so the 20px marker lands at
    # ~80px. A stretch-to-fit would have given 30x80 instead. The few
    # pixels of slack are the smoothscale's soft edges: the colour
    # threshold below stops matching a pixel or two in from each side.
    c.true(f"...at the cover scale, not the fit scale (got {box.width}px)",
           abs(box.width - 80) <= 5)

# Every pixel painted: no black (= untouched Surface) anywhere, including the
# corners, on a board whose aspect ratio does not match the art's.
corners = [probe.get_at((0, 0)), probe.get_at((board_size[0] - 1, 0)),
           probe.get_at((0, board_size[1] - 1)),
           probe.get_at((board_size[0] - 1, board_size[1] - 1))]
c.true("every corner of the board is painted", all(tuple(px)[:3] != (0, 0, 0) for px in corners))
darkest = min(min(tuple(probe.get_at((x, y)))[:3])
              for x in range(0, board_size[0], 7)
              for y in range(0, board_size[1], 7))
c.true("...and so is everything in between (no unpainted strip along an edge)", darkest > 0)


# --- the two cover textures, which DO still tile ---------------------------

# User: "ersetze das bodensprite für dense cover mit dem neuen
# Dense_Cover-Desert.jpg" / "und light cover durch Light_Cover-Desert".
# "Light cover" is NORMAL_COVER_TEXTURE_NAME - the renderer's split is
# "footprint with a wall on it" vs "footprint without", not the terrain
# CATEGORY, so the constant keeps its name and only the file changes.
for label, path_of in (("dense cover", sprites.dense_cover_texture_path),
                       ("light cover", sprites.normal_cover_texture_path)):
    resolved = path_of()
    c.true(f"the {label} art resolves", resolved is not None)
    c.true(f"...to the desert version ({os.path.basename(resolved or '')})",
           resolved is not None and "Desert" in os.path.basename(resolved))

# Unlike the floor these are still tiles, each sized by its OWN constant -
# the two are pictures of different things at different real-world scales.
board = Board(60.0, 44.0, 12.0)
for label, path_of, size_in in (
    ("dense cover", sprites.dense_cover_texture_path, rmod.DENSE_COVER_TILE_SIZE_IN),
    ("light cover", sprites.normal_cover_texture_path, rmod.NORMAL_COVER_TILE_SIZE_IN),
):
    tile = Renderer()._cached_tile(path_of(), board, size_in)
    raw = pygame.image.load(path_of())
    c.eq(f'the {label} tile is {size_in}" wide',
         tile.get_width(), round(board.in_to_px_len(size_in)))
    c.true(f"...and keeps the art's own aspect ratio (tile {tile.get_size()}, "
           f"source {raw.get_size()})",
           abs(tile.get_width() / tile.get_height()
               - raw.get_width() / raw.get_height()) < 0.02)

# User: "dense cover kachel ist jetzt quadratisch. mach sie etwas größer auf
# der map." They squared the art themselves (778x748, so the aspect rule
# above is a no-op for it now); the size is this side of it. At the shared
# 3.0 its flagstones came out ~0.6" across, under one infantry base.
c.true(f'the dense tile is the larger of the two ({rmod.DENSE_COVER_TILE_SIZE_IN}" '
       f'vs {rmod.NORMAL_COVER_TILE_SIZE_IN}")',
       rmod.DENSE_COVER_TILE_SIZE_IN > rmod.NORMAL_COVER_TILE_SIZE_IN)
c.true('...but only "etwas" larger - not doubled',
       rmod.DENSE_COVER_TILE_SIZE_IN < 2 * rmod.NORMAL_COVER_TILE_SIZE_IN)

# Both live cover textures happen to be (near enough) square again after the
# user redrew them, so the aspect rule is currently a no-op on the real art -
# which would make the two checks above pass whatever _cached_tile() did with
# a non-square source. Pinned on a synthetic 2:1 one instead, so the rule
# stays honest for the next texture that isn't square.
wide = pygame.Surface((200, 100))
wide.fill((90, 120, 60))
wide_path = os.path.join(SCRATCH, "_test_cover_probe.png")
pygame.image.save(wide, wide_path)
wide_tile = Renderer()._cached_tile(wide_path, board, rmod.NORMAL_COVER_TILE_SIZE_IN)
c.eq("a 2:1 cover texture keeps its 2:1 shape as a tile",
     (wide_tile.get_width(), wide_tile.get_height()),
     (round(board.in_to_px_len(rmod.NORMAL_COVER_TILE_SIZE_IN)),
      round(board.in_to_px_len(rmod.NORMAL_COVER_TILE_SIZE_IN) / 2)))
c.true("PRE-CHANGE: it would have been squeezed into a square instead",
       wide_tile.get_width() != wide_tile.get_height())
os.remove(wide_path)

# A square source is unaffected by any of it - it tiled correctly before and
# still does, which is why this could change without touching the old art.
square = Renderer()._cached_tile(sprites._resolve_path("Normal_Cover"), board,
                                 rmod.NORMAL_COVER_TILE_SIZE_IN)
c.eq("a square cover texture still gives a square tile",
     square.get_width(), square.get_height())


# --- A/B: what the tiling path would have done -----------------------------

# The pre-change draw tiled a 12" square. On the configured 60x44 board that
# is 5x4 copies of the picture - the thing the user reported.
old_tile_size_in = 12.0
board = Board(60.0, 44.0, 12.0)
copies = ((board.width_in / old_tile_size_in) * (board.height_in / old_tile_size_in))
c.true(f"PRE-CHANGE: the old path repeated the art ~{copies:.0f}x across the board",
       copies > 15)
c.true("...whereas the floor is now a single copy",
       marker_bbox(probe)[1] == 1)

os.remove(source_path)
c.finish()
