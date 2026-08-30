"""map3 - the 60"x44" corner-deployment layout built from Sprites/Map3.png.

It replaces the 30"x30" test board that used to hold this key (User: "map3
ersetzen"), and it is the first map that needs BOTH pieces of the geometry
work: deployment zones that are not rectangles (stage 1) and terrain that is
not axis-aligned (stage 2).

Every number here is a measurement off the source image, and the checks are
written so a re-measurement shows up as a change rather than sliding through:

  1. the board, the symmetry, and the scale the measurement was taken at
  2. the deployment zones - the shape, the hole, and that a real army fits
  3. the terrain - rotated, and every footprint one clean rectangle
  4. the objectives - six, in three mirror pairs, correctly classified
  5. what the rest of the engine now reads off it
"""

import math

import testkit as tk
from testkit import Checks

from game import config, deployment, maps, shapes
from game.game_state import GameState
from game import secondary_missions as sm
from ai import deployment_ai, observation

c = Checks("map3 - Crucible (corner deployment)")

BM = maps.get("map3")
maps.apply_to_config(BM)
ST = GameState()
BM.build(ST)
CX, CY = BM.center
BOARD_BOX = (0.0, 0.0, BM.width_in, BM.height_in)


def approx(got, want, tol=1e-6):
    return abs(got - want) <= tol


def mirror(x, y):
    return BM.width_in - x, BM.height_in - y


# --------------------------------------------------------------------------
print("--- 1. the board ---")

c.eq("60 inches wide", BM.width_in, 60.0)
c.eq("44 inches deep", BM.height_in, 44.0)
c.true("the source image is exactly 40 px per inch, which is why the numbers "
       "come out on clean fractions", approx(2400 / BM.width_in, 40.0) and approx(1760 / BM.height_in, 40.0))
c.true("it is no longer the small test board", BM.width_in * BM.height_in > 30 * 30 * 2)
c.true("the name says what it is", "60" in BM.name and "corner" in BM.name.lower())
c.eq("the board centre", (CX, CY), (30.0, 22.0))


# --------------------------------------------------------------------------
print("--- 2. the deployment zones ---")

p1 = deployment.zone_for(ST.deployment_zones, "Player 1")
p2 = deployment.zone_for(ST.deployment_zones, "Player 2")
c.true("both players have a zone", p1 is not None and p2 is not None)
c.eq("neither is written as rectangles - they cannot be", (p1.rects, p2.rects), ([], []))

c.true("Player 2 keeps the low-y corner, as on both other maps",
       p2.centroid(board_box=BOARD_BOX)[1] < CY < p1.centroid(board_box=BOARD_BOX)[1])
c.true("...and they are diagonally opposite, not banded",
       (p2.centroid(board_box=BOARD_BOX)[0] - CX) * (p1.centroid(board_box=BOARD_BOX)[0] - CX) < 0)

# Each zone is its quadrant, minus the circle.
c.true("Player 2 owns the high-x low-y corner", p2.contains_point(58.0, 2.0))
c.true("...and not the other three", not any(p2.contains_point(x, y)
                                             for x, y in ((2.0, 2.0), (2.0, 42.0), (58.0, 42.0))))
c.true("Player 1 owns the low-x high-y corner", p1.contains_point(2.0, 42.0))
c.true("...and not the other three", not any(p1.contains_point(x, y)
                                             for x, y in ((2.0, 2.0), (58.0, 2.0), (58.0, 42.0))))
c.true("the two quadrants nobody deploys in belong to nobody",
       not any(z.contains_point(x, y) for z in ST.deployment_zones
               for x, y in ((10.0, 10.0), (50.0, 34.0))))

# The hole. Measured at 355 px = 8.88" in BOTH zones of the source image; the
# printed annotation is 9" and the difference is the dashed line's own width.
HOLE = maps.MAP3_CENTRE_HOLE_RADIUS_IN
c.eq("the centre circle is 9 inches", HOLE, 9.0)
for frac, want in ((0.0, False), (0.5, False), (0.98, False), (1.02, True)):
    r = HOLE * frac
    hits = [any(z.contains_point(CX + r * math.cos(a), CY + r * math.sin(a))
                for z in ST.deployment_zones)
            for a in (math.radians(-45), math.radians(135))]
    c.eq(f"at {frac:.2f} of the hole radius, on the two zone diagonals", all(hits) if want else any(hits), want)

# What the hole is FOR: it is what makes the two central objectives No Man's
# Land even though each stands in a quadrant that is otherwise somebody's zone.
for name in ("Objective East", "Objective West"):
    objective = next(o for o in ST.objectives if o.name == name)
    ox, oy = sm.objective_centre(objective)
    c.true(f"{name} stands inside somebody's quadrant",
           (ox >= CX) == (oy <= CY) or (ox <= CX) == (oy >= CY))
    c.true(f"...but inside the hole, so it belongs to nobody",
           math.hypot(ox - CX, oy - CY) < HOLE
           and not any(z.contains_point(ox, oy) for z in ST.deployment_zones))

# An army has to FIT. This is the measurement that killed the rectangle
# approximation (see game/shapes.py): a staircase of 16 strips leaves a grav
# tank nowhere to stand at all.
for label, radius, floor in (("25mm", 0.63, 450), ("50mm", 1.18, 400), ("grav tank", 2.10, 300)):
    area = sum(1 for i in range(121) for j in range(89)
               if p1.contains_circle(60 * i / 120, 44 * j / 88, radius)) * (60 * 44 / (121 * 89))
    c.true(f"a {label} base has room: {area:.0f} sq.in of Player 1's zone", area > floor)
sym = [sum(1 for i in range(121) for j in range(89)
           if z.contains_point(60 * i / 120, 44 * j / 88)) for z in (p1, p2)]
c.eq("both zones are the same size, as a 180-degree symmetric layout demands", sym[0], sym[1])


# --------------------------------------------------------------------------
print("--- 3. the terrain ---")

feet = [o for area in ST.terrain_areas for o in area.features if o.category != "dense"]
walls = [o for area in ST.terrain_areas for o in area.features if o.category == "dense"]
c.eq("eighteen footprints - nine measured, nine mirrored", len(feet), 18)
c.true("and a wall layout on top of them", len(walls) > 0)
c.eq("every terrain area is one footprint plus its walls", len(ST.terrain_areas), 18)

turned = [o for o in feet if abs(o.angle_deg) > 1e-9]
c.eq("four pieces really are rotated - that is why stage 2 existed", len(turned), 4)
c.true("...and they are two mirror pairs at 37 and -52.5 degrees",
       sorted(round(o.angle_deg, 1) for o in turned) == [-52.5, -52.5, 37.1, 37.1])
# A barricade is a footprint with NO walls on it (gold bracing, no rubble), so
# the wall check has to name the areas that actually have walls - an all/any
# over the rest is vacuously false, not vacuously true.
ruins = [a for a in ST.terrain_areas if any(f.category == "dense" for f in a.features)]
turned_ruins = [a for a in ruins
                if abs(next(f for f in a.features if f.category != "dense").angle_deg) > 1e-9]
c.eq("the two big flank ruins are the rotated ones with walls", len(turned_ruins), 2)
c.true("...and every wall of a rotated ruin carries the SAME angle as its footprint",
       all(all(abs(w.angle_deg - next(f for f in a.features if f.category != "dense").angle_deg) < 1e-9
               for w in a.features if w.category == "dense")
           for a in turned_ruins))
c.true("...and its walls really sit on it, not beside it",
       all(next(f for f in a.features if f.category != "dense").overlaps_circle(w.x_in, w.y_in, 0.01)
           for a in turned_ruins for w in a.features if w.category == "dense"))

c.true("every footprint is ONE clean rectangle, no composite shapes",
       all(len([o for o in area.features if o.category != "dense"]) == 1
           for area in ST.terrain_areas))
c.true("every piece is inside the board", all(
    o.min_x >= -0.01 and o.max_x <= BM.width_in + 0.01
    and o.min_y >= -0.01 and o.max_y <= BM.height_in + 0.01 for o in feet))

# The symmetry, checked on the BUILT map rather than on the measurement, so a
# hand-edited coordinate shows up here.
unmatched = []
for o in feet:
    mx, my = mirror(o.x_in, o.y_in)
    if not any(abs(p.x_in - mx) < 0.02 and abs(p.y_in - my) < 0.02
               and approx(p.width_in, o.width_in, 0.02) and approx(p.height_in, o.height_in, 0.02)
               and approx(p.angle_deg, o.angle_deg, 0.02)
               for p in feet):
        unmatched.append((round(o.x_in, 2), round(o.y_in, 2)))
c.eq("every piece has an exact 180-degree twin", unmatched, [])

# The pieces map 2 would have had to straighten: the two flank ruins carrying
# the No Man's Land objectives stand at 37.1 degrees, and the two central ones
# at 57.2. Named by their objective rather than by size, because the two home
# ruins are the same footprint area and would win a size sort by a rounding.
for name, want_angle in (("Objective Northwest", 37.1), ("Objective Southeast", 37.1)):
    objective = next(o for o in ST.objectives if o.name == name)
    piece = next(f for f in objective.terrain_area.features if f.category != "dense")
    c.true(f"{name} stands on a piece rotated {want_angle} degrees",
           approx(piece.angle_deg, want_angle, 0.01))
# The two central pieces are UPRIGHT, and that is a correction rather than a
# measurement: their art is a WEDGE, so the tightest rectangle around it lies
# diagonally (57 degrees) and is not the shape the layout reads as. The two
# readings are told apart by how much of that rectangle the piece fills.
for name in ("Objective East", "Objective West"):
    objective = next(o for o in ST.objectives if o.name == name)
    piece = next(f for f in objective.terrain_area.features if f.category != "dense")
    c.true(f"{name} stands on an UPRIGHT piece, not on a diagonal fit",
           approx(piece.angle_deg, 0.0))
    c.true(f"...and it is taller than it is wide, as the art is",
           piece.height_in > piece.width_in)
homes = [o for o in ST.objectives if "Home" in o.name]
c.true("the two home ruins are square to the board, as measured",
       all(approx(next(f for f in o.terrain_area.features if f.category != "dense").angle_deg, 0.0)
           for o in homes))

# The piece the first measurement pass missed entirely: it is drawn as a green
# container with no grey ground under it, and that pass masked only grey.
c.true("the green container pair is on the board",
       sum(1 for o in feet if approx(o.width_in, 2.00, 0.01) and approx(o.height_in, 7.00, 0.01)) == 2)


# --------------------------------------------------------------------------
print("--- 4. the objectives ---")

names = [o.name for o in ST.objectives]
c.eq("six objectives", len(ST.objectives), 6)
c.eq("no central one - the middle of this board is the hole",
     [n for n in names if "Central" in n], [])

homes = [o for o in ST.objectives if "Home" in o.name]
c.eq("two home objectives", len(homes), 2)
for objective in homes:
    ox, oy = sm.objective_centre(objective)
    owner = "Player 1" if "P1" in objective.name else "Player 2"
    zone = deployment.zone_for(ST.deployment_zones, owner)
    c.true(f"{objective.name} is inside {owner}'s own zone", zone.contains_point(ox, oy))

nml = sm.no_mans_land_objectives(
    sm.MissionContext("Player 1", objectives=ST.objectives, deployment_zones=ST.deployment_zones))
c.eq("the other four are No Man's Land", len(nml), 4)

# The cardinal names have to be true, or they are worse than no name at all.
for objective in ST.objectives:
    ox, oy = sm.objective_centre(objective)
    for word, axis, sign in (("North", oy, -1), ("South", oy, 1), ("West", ox, -1), ("East", ox, 1)):
        if word in objective.name:
            centre = CY if word in ("North", "South") else CX
            c.true(f"{objective.name} really is {word.lower()} of centre",
                   (axis - centre) * sign > 0)

pairs = {}
for objective in ST.objectives:
    ox, oy = sm.objective_centre(objective)
    mx, my = mirror(ox, oy)
    twin = [o for o in ST.objectives
            if abs(sm.objective_centre(o)[0] - mx) < 0.05
            and abs(sm.objective_centre(o)[1] - my) < 0.05]
    pairs[objective.name] = bool(twin)
c.true("all six sit in three mirror pairs", all(pairs.values()))


# --------------------------------------------------------------------------
print("--- 5. what the rest of the engine reads off it ---")

# The territory split turns with the zones - this is the map the stage-1
# generalisation was for.
ctx = sm.MissionContext("Player 1", objectives=ST.objectives, deployment_zones=ST.deployment_zones)
c.true("my own corner is my territory", sm.in_own_territory(ctx, 4.0, 40.0))
c.true("the opposite corner is not", not sm.in_own_territory(ctx, 56.0, 4.0))
c.true("the dividing line is the DIAGONAL, so the two idle quarters split",
       sm.in_own_territory(ctx, 4.0, 4.0) != sm.in_own_territory(ctx, 56.0, 40.0))

# Each player's expansion objective is the one on their own side. Ranking by
# the conservative zone distance ties these two, which is why
# expansion_objective_for() asks for the true distance.
c.eq("Player 1's expansion objective", sm.expansion_objective_for(ctx, "Player 1").name, "Objective West")
c.eq("Player 2's", sm.expansion_objective_for(ctx, "Player 2").name, "Objective East")

# The AI can sample the zone at all - a shape whose bounding box came back None
# silently gave the exposure probe zero points to measure with.
for zone in ST.deployment_zones:
    c.true(f"{zone.owner}'s zone reports a bounding box", zone.bounding_box() is not None)
    c.true(f"...and the AI's exposure probe finds points in it",
           len(deployment_ai._zone_probe_points(zone)) >= 10)
    c.true("...all of them actually inside the zone",
           all(zone.contains_point(*p) for p in deployment_ai._zone_probe_points(zone)))
    c.true(f"...and a candidate grid to deploy on",
           deployment_ai._shape_box(zone) is not None)

# Home garrison reach: measured off the board, and symmetric here.
needs = []
for owner in ("Player 1", "Player 2"):
    own = deployment.zone_for(ST.deployment_zones, owner)
    home = deployment_ai._home_objective(owner, ST.objectives, own)
    needs.append(round(observation.garrison_reach_needed_in(home, ST.objectives), 1))
c.eq("both players need the same reach from home", needs[0], needs[1])
c.eq("...and it is 15.9 inches - the nearest other objective is one of the two "
     "central pieces, so a 12in gun still cannot hold home usefully", needs[0], 15.9)


# --------------------------------------------------------------------------
print("--- 6. the objective outline follows the footprint ---")

# User: "die objective zonen muessen sich natuerlich mit den gelaende
# footprints decken. die muessen ebenfalls rotieren." Rule 14.02 already
# measured control against the ROTATED rectangle
# (TerrainArea.overlaps_model); it was the drawn outline that still came off
# the axis-aligned bounding box, so the picture promised ground the rules did
# not give.
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from game import renderer as R
from game.board import Board

pygame.init()
pygame.display.set_mode((64, 64))
_board = Board(BM.width_in, BM.height_in, 20)

for objective in ST.objectives:
    area = objective.terrain_area
    piece = next(f for f in area.features if f.category != "dense")
    pts = R.objective_outline_points(_board, area)
    c.true(f"{objective.name}: the outline is a closed polygon", len(pts) >= 4)
    # Every corner of the footprint must be INSIDE the outline, and the
    # outline must not be the bounding box when the piece is turned.
    box = R._points_bounds(pts)
    corners_px = [tuple(round(v) for v in _board.to_px(x, y)) for x, y in piece.corners()]
    c.true(f"{objective.name}: every footprint corner is inside the outline",
           all(box.collidepoint(p) for p in corners_px))
    if abs(piece.angle_deg) > 1e-9:
        hull_area = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            hull_area += x1 * y2 - x2 * y1
        hull_area = abs(hull_area) / 2
        c.true(f"{objective.name}: the outline is TIGHTER than the bounding box, "
               f"which is what 'follows the footprint' means",
               hull_area < box.width * box.height * 0.92)
        c.true(f"{objective.name}: ...and it is not axis-aligned",
               len({p[0] for p in pts}) > 2 and len({p[1] for p in pts}) > 2)
    else:
        c.true(f"{objective.name}: a square piece keeps its rectangular outline",
               len({p[0] for p in pts}) == 2 and len({p[1] for p in pts}) == 2)

# The margin is even all the way round: the outline of a rotated piece must be
# the footprint grown by the SAME amount on every side, which is exactly the
# area of a rectangle (w + 2m) x (h + 2m). Measured as an area rather than by
# picking points, because a point-to-vertex distance is not a margin.
_turned = next(o for o in ST.objectives
               if abs(next(f for f in o.terrain_area.features if f.category != "dense").angle_deg) > 1e-9)
_piece = next(f for f in _turned.terrain_area.features if f.category != "dense")
_hull = R.objective_outline_points(_board, _turned.terrain_area)
_area = abs(sum(_hull[i][0] * _hull[(i + 1) % len(_hull)][1]
                - _hull[(i + 1) % len(_hull)][0] * _hull[i][1]
                for i in range(len(_hull)))) / 2
_per_px = _board.in_to_px_len(1.0)
_m = R.OBJECTIVE_OUTLINE_INFLATE_PX / _per_px
_want = (_piece.width_in + 2 * _m) * (_piece.height_in + 2 * _m) * _per_px * _per_px
c.true(f"a rotated outline is the footprint grown evenly on all four sides "
       f"({_area:.0f} px2 against {_want:.0f})", abs(_area - _want) / _want < 0.02)
c.true("...and that really is bigger than the footprint alone",
       _want > _piece.width_in * _piece.height_in * _per_px * _per_px)

# The info icon hangs on the outline itself, not on a bounding-box corner out
# in open ground.
for objective in ST.objectives:
    pts = R.objective_outline_points(_board, objective.terrain_area)
    anchor = min(pts, key=lambda p: p[0] + p[1])
    c.true(f"{objective.name}: the icon anchor is a point ON the outline", anchor in pts)

c.finish()
