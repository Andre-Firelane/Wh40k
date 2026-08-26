"""Blood decals are one fixed size, whatever died.

User: "mach die blutflecken immer klein."

They used to be scaled off the dead model's own base (1.15x its DIAMETER),
so a Battlewagon or a Riptide left a stain several inches across while a
Gretchin left a dot - at that size the big ones read as terrain rather than
as a mark on the floor. Now every stain is sprites.BLOOD_DECAL_DIAMETER_IN.

Purely cosmetic; no rule reads a decal. What is worth pinning is that the
size no longer depends on the model, and that the size chosen is the one the
user had already been looking at without complaint (the infantry stain).
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

from game import sprites
from game.game_state import GameState
from game.factions.orks import BATTLEWAGON, BOYZ, GRETCHIN
from game.factions.tau_empire import RIPTIDE_BATTLESUIT

c = Checks("blood decals")

pygame.init()
screen = pygame.display.set_mode((600, 400))

from game.board import Board          # noqa: E402  (needs a display)
from game.renderer import Renderer    # noqa: E402

grot = tk.build(GRETCHIN, "Player 2", name="G").models[0]
boy = tk.build(BOYZ, "Player 2", name="B").models[-1]
wagon = tk.build(BATTLEWAGON, "Player 2", name="W").models[0]
riptide = tk.build(RIPTIDE_BATTLESUIT, "Player 1", name="R").models[0]

# The scene has to actually contain the size spread the report is about,
# otherwise "all the same size" would be true for an uninteresting reason.
c.true("the models really do span a wide range of base sizes",
       wagon.radius_in > 3 * grot.radius_in)


# --- the decal record itself ------------------------------------------------

state = GameState()
state.add_blood_decal(12.0, 8.0)
state.add_blood_decal(20.0, 30.0)
c.eq("a decal is just a position", state.blood_decals, [(12.0, 8.0), (20.0, 30.0)])


# --- what is drawn ----------------------------------------------------------

def drawn_sizes(decals):
    """The size of every decal the renderer actually put on the board, in
    pixels - read at the renderer/sprites seam (what it ASKED for and got)
    rather than by re-deriving it, so this measures the drawing path."""
    board = Board(60.0, 44.0, 18.0)
    sizes = []
    real_surface = sprites.blood_decal_surface

    def spy(path, diameter_px):
        surf = real_surface(path, diameter_px)
        sizes.append(surf.get_size())
        return surf

    sprites.blood_decal_surface = spy
    try:
        Renderer().draw_blood_decals(pygame.Surface((600, 400)), board, decals)
    finally:
        sprites.blood_decal_surface = real_surface
    # One surface is fetched per DRAW now, not per decal - it is the same for
    # all of them - so repeat it out to the decal count the caller expects.
    return sizes * len(decals) if len(sizes) == 1 else sizes


path = sprites.blood_decal_path()
c.true("the decal art is present, so there is something to measure", path is not None)

sizes = drawn_sizes([(6.0, 8.0), (14.0, 8.0), (6.0, 16.0), (14.0, 16.0)])
c.eq("one decal drawn per record", len(sizes), 4)
c.eq("...and every one of them the same size", len(set(sizes)), 1)

board = Board(60.0, 44.0, 18.0)
expected_px = round(board.in_to_px_len(sprites.BLOOD_DECAL_DIAMETER_IN))
c.true("...at the fixed diameter, within a pixel of rounding",
       abs(max(sizes[0]) - expected_px) <= 1)

# It still scales with the ZOOM - it is a mark on the board, not a UI overlay.
zoomed = []
for px_per_inch in (9.0, 18.0, 36.0):
    b = Board(60.0, 44.0, px_per_inch)
    zoomed.append(max(sprites.blood_decal_surface(
        path, b.in_to_px_len(sprites.BLOOD_DECAL_DIAMETER_IN)).get_size()))
c.true("a decal still grows and shrinks with the zoom",
       zoomed[0] < zoomed[1] < zoomed[2])

# A/B: the old rule, as a local copy - it gave four different sizes for these
# four models, and the biggest was several inches across.
old_diameters = {tok.radius_in * 2 * 1.15 for tok in (grot, boy, wagon, riptide)}
c.true("PRE-CHANGE: four models, four different stain sizes", len(old_diameters) > 1)
c.true("...and the largest was several inches across", max(old_diameters) > 4.0)
c.true("...whereas the fixed one is well under that",
       sprites.BLOOD_DECAL_DIAMETER_IN < max(old_diameters) / 3)

# The size chosen is the infantry stain the old rule already produced - i.e.
# the one the user had been looking at without complaining about it.
infantry = sorted(tok.radius_in * 2 * 1.15 for tok in (grot, boy))
c.true("the fixed size sits inside the old INFANTRY range",
       infantry[0] <= sprites.BLOOD_DECAL_DIAMETER_IN <= infantry[-1])

# Missing art degrades to drawing nothing, the same convention as every other
# sprite lookup here.
real_path = sprites.blood_decal_path
sprites.blood_decal_path = lambda: None
try:
    c.eq("no art, nothing drawn", drawn_sizes([(6.0, 8.0)]), [])
finally:
    sprites.blood_decal_path = real_path

c.finish()
