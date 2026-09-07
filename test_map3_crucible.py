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
    # ...and so does its whole AREA, which is the half this used to miss. The
    # centre was always in the hole; the footprint reached 12.01" out and put
    # 15.3% of the objective inside a deployment zone (user report). The
    # cross-map form of this lives in test_deployment_shapes.py section 9.
    area = objective.terrain_area
    corner_r = max(
        math.hypot(x - CX, y - CY)
        for f in area.features
        for x in (f.min_x, f.max_x) for y in (f.min_y, f.max_y))
    c.true(f"...area included: its furthest corner is {corner_r:.2f}\" out, inside the "
           f"{HOLE:.0f}\" hole", corner_r < HOLE)

# The size and position that buy it, and the THREE things they trade off. The
# pieces are scaled to 0.675 of the measured 7.48 x 10.85 and slid 1.2" toward
# the board centre: at the measured centre the piece is 6.13" out from the
# middle of a 9" circle, so nothing bigger than scale 0.508 fits there whatever
# its shape - room has to come from the position, not just the size.
east = next(o for o in ST.objectives if o.name == "Objective East")
foot = east.terrain_area.features[0]
c.true(f"the central pieces are scaled to fit the hole "
       f"({foot.width_in:.2f} x {foot.height_in:.2f} of 7.48 x 10.85)",
       abs(foot.width_in / 7.48 - 0.675) < 0.01
       and abs(foot.height_in / 10.85 - 0.675) < 0.01)
c.true("...keeping the measured aspect, so it still reads as the same piece",
       abs((foot.height_in / foot.width_in) - (10.85 / 7.48)) < 0.01)
c.true("...moved toward the board centre, not away from it",
       math.hypot(foot.x_in - CX, foot.y_in - CY) < math.hypot(35.87 - CX, 20.22 - CY))

# THE CORRIDOR between the pair, which is what stops the pieces simply being
# slid further in until they are big again (User: "es soll aber noch ein
# corridor zwischen den objectives bleiben"). The ART's own gap is 4.26"; this
# keeps at least that, and it has to stay wider than the 4.2" base of a Falcon
# or Wave Serpent - the widest thing that has to drive through the middle.
west = next(o for o in ST.objectives if o.name == "Objective West")
wfoot = west.terrain_area.features[0]
lane = abs(max(foot.min_x, wfoot.min_x) - min(foot.max_x, wfoot.max_x))
ART_CORRIDOR = 4.26          # the gap the measured pieces left, at their size
GRAV_TANK_IN = 4.2           # Falcon / Wave Serpent base, the widest in play
c.true(f"a corridor is left between the two central pieces ({lane:.2f}\")",
       lane >= ART_CORRIDOR)
c.true(f"...wide enough for the widest base in the game ({GRAV_TANK_IN}\")",
       lane > GRAV_TANK_IN)

# The pair stay a MIRROR pair, so both remain exactly as far from the board
# centre - which is what makes both of them "central" for the Primary missions
# that read that.
c.true("the two central pieces are still mirror images about the board centre",
       abs((foot.x_in + wfoot.x_in) / 2 - CX) < 0.01
       and abs((foot.y_in + wfoot.y_in) / 2 - CY) < 0.01)

# The DRAWN ring clears too, at the zoom the board is played at - without this
# the fix is correct and still looks broken, which is how it was reported.
from game import renderer as _r  # noqa: E402  (local to this check)

PLAY_PPI = 62.0                      # measured elsewhere in this repo
ring_grow = _r.OBJECTIVE_OUTLINE_INFLATE_PX / PLAY_PPI
ring_r = max(
    math.hypot(x - CX, y - CY)
    for f in east.terrain_area.features
    for x in (f.min_x - ring_grow, f.max_x + ring_grow)
    for y in (f.min_y - ring_grow, f.max_y + ring_grow))
c.true(f"the drawn outline clears the arc in play too ({ring_r:.2f}\" < {HOLE:.0f}\")",
       ring_r < HOLE)

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
# 16.8", up from 15.9" when the two central pieces sat where the art measured
# them. They were slid 1.2" toward the board centre so their footprints clear
# the deployment zones (see game/maps.py), and the nearest other objective to a
# home objective IS one of that pair - so the reach a home garrison needs grew
# with the move. The number is READ OFF THE BOARD rather than set, which is the
# whole point of garrison_reach_needed_in(); what matters is that it stays well
# past a 12" gun, so the conclusion it was written for is unchanged.
c.eq("...and it is 16.8 inches - the nearest other objective is still one of the "
     "two central pieces, which moved 1.2in in", needs[0], 16.8)
c.true("...so a 12in gun still cannot hold home usefully", needs[0] > 12.0)


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


# --------------------------------------------------------------------------
print("--- 7. pieces that touch, touch ---")

# User: "bei map 3 gibt es kleine luecken, durch die man durchschiessen kann
# zwischen den gelaendestuecken ... schiebe sie so zusammen, dass da keine
# luecken sind, wenn gelaendestuecke sich beruehren sollten."
#
# The cause was the percentile fit (see game/maps.py): trimming both pieces of
# a touching pair opened seams of 0.15" to 0.43". What is pinned here is the
# RESULT, in a form that catches a re-measurement sliding a sliver back in: a
# pair is either flush or clearly apart, never a hair's breadth from meeting.


def _seg_point(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length_sq))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _inside(p, poly):
    sign = 0
    for i in range(len(poly)):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % len(poly)]
        cross = (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax)
        if abs(cross) < 1e-12:
            continue
        side = 1 if cross > 0 else -1
        if sign == 0:
            sign = side
        elif side != sign:
            return False
    return True


def _crosses(p1, p2, p3, p4):
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    return (((cross(p3, p4, p1) > 0) != (cross(p3, p4, p2) > 0))
            and ((cross(p1, p2, p3) > 0) != (cross(p1, p2, p4) > 0)))


def gap(a, b):
    """Inches between two (possibly rotated) rectangles; 0 if they meet."""
    A, B = a.corners(), b.corners()
    if any(_inside(p, B) for p in A) or any(_inside(p, A) for p in B):
        return 0.0
    for i in range(len(A)):
        for j in range(len(B)):
            if _crosses(A[i], A[(i + 1) % len(A)], B[j], B[(j + 1) % len(B)]):
                return 0.0
    best = float("inf")
    for i in range(len(A)):
        best = min(best, min(_seg_point(p, A[i], A[(i + 1) % len(A)]) for p in B))
    for j in range(len(B)):
        best = min(best, min(_seg_point(p, B[j], B[(j + 1) % len(B)]) for p in A))
    return best


# A gap narrower than this is not a lane anybody chose to leave - it is a
# leftover seam. The number has room on both sides and is not a guess: the
# nearest pair that is genuinely apart on this board stands 2.7" apart, and
# the widest base in either army is 4.2" across, so nothing legitimate lives
# in between.
SLIVER_IN = 1.0
slivers = []
touching = []
for i in range(len(feet)):
    for j in range(i + 1, len(feet)):
        d = gap(feet[i], feet[j])
        if d == 0.0:
            touching.append((i, j))
        elif d < SLIVER_IN:
            slivers.append((round(feet[i].x_in, 2), round(feet[j].x_in, 2), round(d, 3)))
c.eq(f"no pair of pieces is left within {SLIVER_IN}in of touching without touching",
     slivers, [])
# Four measured contacts, and the map is symmetric, so eight.
c.eq("the four contacts the art draws are built, on both halves", len(touching), 8)
c.true("...and each is an exact contact, not an overlap",
       all(gap(feet[i], feet[j]) == 0.0 for i, j in touching))

# The rule is "close what the art draws closed", NOT "glue every neighbour":
# the cross-braced bar and the -52.5-degree barricade stand 2.35" apart in the
# source image, and they stay apart here. Without this the check above would
# also pass on a board that simply pushed everything into one lump.
bar = next(o for o in feet if approx(o.width_in, 2.05, 0.01) and o.x_in < 30)
turned_barricade = next(o for o in feet if approx(o.angle_deg, -52.5, 0.01) and o.x_in < 30)
c.true(f"the one pair the art leaves open stays open ({gap(bar, turned_barricade):.2f}in)",
       gap(bar, turned_barricade) > 2.0)

# The contact that mattered for play. Every other piece involved is a
# barricade - Light terrain, which never blocked sight - but these two are
# ruins, and their WALLS stood 0.15" apart and facing each other, which is a
# slot a line of sight threads. Both halves of that are checked: the walls
# themselves (what stops a shooter standing INSIDE one of the two areas,
# where rule 13.10 is switched off) and the sightline (what stops everyone
# else).
row_ruins = [a for a in ST.terrain_areas
             if 27.0 < a.features[0].x_in < 33.0 and a.features[0].y_in < 12.0
             and any(f.category == "dense" for f in a.features)]
c.eq("the centre-line row is two ruins, not one", len(row_ruins), 2)
row_walls = [[f for f in a.features if f.category == "dense"] for a in row_ruins]
c.true("...and their walls meet, closing the slot a shot used to thread",
       min(gap(u, v) for u in row_walls[0] for v in row_walls[1]) == 0.0)


class _Probe:
    """A point-sized model, so the check measures the terrain and not a base.
    Duck-typed on purpose - line_of_sight.py documents this stand-in shape for
    ai/observation.py's own probes, and a probe with no squad has no army."""

    def __init__(self, x_in, y_in):
        self.x_in = x_in
        self.y_in = y_in
        self.radius_in = 0.02


from game import line_of_sight as los  # noqa: E402  (local to this section)

obstacles = [o for area in ST.terrain_areas for o in area.features]
open_lanes = [round(29.90 + 0.01 * k, 2) for k in range(21)
              if los.has_line_of_sight(_Probe(29.90 + 0.01 * k, 4.0),
                                       _Probe(29.90 + 0.01 * k, 15.0),
                                       obstacles, (), ST.terrain_areas)]
c.eq("nothing can shoot through the centre-line ruins any more", open_lanes, [])
# ...and the same check has to be able to say YES, or it would also pass on a
# board where every shot is blocked. The nearest genuinely open lane is 1" off
# the row's east edge.
c.true("...while open ground beside them is still open ground",
       los.has_line_of_sight(_Probe(34.0, 4.0), _Probe(34.0, 15.0),
                             obstacles, (), ST.terrain_areas))


c.finish()
