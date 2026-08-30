"""Deployment zones as SHAPES (game/shapes.py) instead of rectangle lists, and
the diagonal territory split that follows from it.

Stage 1 of the map-geometry work. What it has to establish, in order:

  1. the primitives measure what they claim
  2. the three zone questions really are one signed distance
  3. nothing the three shipped maps do changes - INCLUDING at the exact
     boundary, which is where the first version of this work broke
  4. the seam weakness the old contains_circle() documented is gone
  5. a corner zone shaped like the layout the user supplied actually works
  6. the territory split turns with the zones and is unchanged where it used
     to apply
"""

import math

import testkit as tk
from testkit import Checks

from game import config, maps, shapes
from game.deployment import DeploymentZone, PLACEMENT_TOLERANCE_IN
from game.game_state import GameState
from game import secondary_missions as sm

c = Checks("deployment zone shapes + diagonal territory")


def approx(got, want, tol=1e-9):
    return abs(got - want) <= tol


# --------------------------------------------------------------------------
print("--- 1. the primitives ---")

r = shapes.Rect(10.0, 10.0, 8.0, 4.0)
c.true("Rect: centre is half the SHORT side from the boundary", approx(r.signed_distance(10, 10), 2.0))
c.true("Rect: a point on the edge is at distance 0", approx(r.signed_distance(14, 10), 0.0))
c.true("Rect: outside is negative", approx(r.signed_distance(15, 10), -1.0))
c.true("Rect: outside a corner measures diagonally to the corner",
       approx(r.signed_distance(17, 15), -math.hypot(3.0, 3.0)))
c.eq("Rect: bounding box", r.bounding_box(), (6.0, 8.0, 14.0, 12.0))

rot = shapes.Rect(0.0, 0.0, 8.0, 4.0, angle_deg=90.0)
c.true("Rect rotated 90 degrees: the long side is now vertical",
       approx(rot.signed_distance(0, 3), 1.0) and approx(rot.signed_distance(3, 0), -1.0))
c.true("Rect rotated 90 degrees: bounding box swaps",
       all(approx(a, b) for a, b in zip(rot.bounding_box(), (-2.0, -4.0, 2.0, 4.0))))
diag = shapes.Rect(0.0, 0.0, 8.0, 4.0, angle_deg=45.0)
c.true("Rect rotated 45 degrees: still 2 inches deep from its own centre",
       approx(diag.signed_distance(0, 0), 2.0))
c.true("...and a point 2 inches along its own short axis is on the boundary",
       approx(diag.signed_distance(-math.sqrt(2), math.sqrt(2)), 0.0))

# A rotated rectangle IS four half-planes - the two spellings must agree.
quad = shapes.Intersection([
    shapes.HalfPlane.through(-2, -2, 2, -2, 0, 0),
    shapes.HalfPlane.through(2, -2, 2, 2, 0, 0),
    shapes.HalfPlane.through(2, 2, -2, 2, 0, 0),
    shapes.HalfPlane.through(-2, 2, -2, -2, 0, 0),
])
square = shapes.Rect(0.0, 0.0, 4.0, 4.0)
pts = [(x / 4, y / 4) for x in range(-12, 13) for y in range(-12, 13)]
c.true("four half-planes and a Rect agree everywhere on WHICH points are inside",
       all((quad.signed_distance(*p) >= 0) == (square.signed_distance(*p) >= 0) for p in pts))
c.true("...and on the distance itself wherever the point is inside",
       all(approx(quad.signed_distance(*p), square.signed_distance(*p))
           for p in pts if square.signed_distance(*p) >= 0))
# Outside a CORNER the two part company, and the direction matters: an
# intersection reports the distance to the nearest EDGE LINE, which beyond a
# corner is nearer than the true distance to the corner point. So it
# UNDERSTATES how far outside you are - and every consumer reads that as "you
# are closer to that zone than you really are", which refuses an INFILTRATORS
# placement (24.20's 8") rather than allowing an illegal one. Same safe
# direction the rest of this vocabulary errs in.
outside_corner = (3.0, 3.0)
c.true("outside a corner an intersection is conservative, never permissive",
       quad.signed_distance(*outside_corner) >= square.signed_distance(*outside_corner))
c.true("...and it really is a different number there, not an accident of this point",
       not approx(quad.signed_distance(*outside_corner), square.signed_distance(*outside_corner)))

hp = shapes.HalfPlane.through(0.0, 10.0, 10.0, 0.0, 0.0, 0.0)
c.true("HalfPlane.through keeps the side the given point is on", hp.signed_distance(0, 0) > 0)
c.true("...and the line itself is distance 0", approx(hp.signed_distance(5, 5), 0.0))
c.true("...distance is perpendicular, not along an axis",
       approx(hp.signed_distance(0, 0), -10.0 / math.sqrt(2) * -1))
c.eq("HalfPlane is unbounded, so it reports no box", hp.bounding_box(), None)

d = shapes.Disc(10.0, 10.0, 6.0)
c.true("Disc: centre is the radius from the boundary", approx(d.signed_distance(10, 10), 6.0))
c.true("Disc: outside", approx(d.signed_distance(20, 10), -4.0))
c.true("Outside(Disc) flips the sign", approx(shapes.Outside(d).signed_distance(10, 10), -6.0))

c.true("Intersection takes the nearest constraint",
       approx(shapes.Intersection([shapes.Rect(0, 0, 10, 10), shapes.Disc(0, 0, 3)]).signed_distance(0, 0), 3.0))
c.true("Union takes the furthest",
       approx(shapes.Union([shapes.Rect(0, 0, 10, 10), shapes.Disc(0, 0, 3)]).signed_distance(0, 0), 5.0))
c.eq("an empty Union contains nothing", shapes.Union([]).signed_distance(0, 0), float("-inf"))
c.eq("an empty Intersection constrains nothing", shapes.Intersection([]).signed_distance(0, 0), float("inf"))


# --------------------------------------------------------------------------
print("--- 2. one distance answers all three zone questions ---")

zone = DeploymentZone("Player 1", [(10.0, 10.0, 8.0, 4.0)])
c.true("contains_point is sd >= 0", zone.contains_point(10, 10) and not zone.contains_point(10, 13))
c.true("contains_circle is sd >= r (a 1.5in base fits in a 2in half-depth)",
       zone.contains_circle(10, 10, 1.5))
c.true("...and a 2.5in base does not", not zone.contains_circle(10, 10, 2.5))
c.true("a base exactly as deep as the zone still counts as wholly within",
       zone.contains_circle(10, 10, 2.0))
c.true("distance_to_point is 0 inside", approx(zone.distance_to_point(10, 10), 0.0))
c.true("...and the perpendicular distance outside", approx(zone.distance_to_point(10, 15), 3.0))

def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


c.true("a zone with neither rects nor shape is refused loudly",
       raises(lambda: DeploymentZone("P")))
c.true("...and so is a zone given both, which would have two sources of truth",
       raises(lambda: DeploymentZone("P", [(0, 0, 1, 1)], shapes.Disc(0, 0, 1))))


# --------------------------------------------------------------------------
print("--- 3. the three shipped maps are unchanged, boundary included ---")


def old_contains_point(rects, x, y):
    return any(cx - w / 2 <= x <= cx + w / 2 and cy - h / 2 <= y <= cy + h / 2
               for cx, cy, w, h in rects)


def old_contains_circle(rects, x, y, r):
    return any(cx - w / 2 <= x - r and x + r <= cx + w / 2
               and cy - h / 2 <= y - r and y + r <= cy + h / 2
               for cx, cy, w, h in rects)


def old_distance(rects, x, y):
    best = None
    for cx, cy, w, h in rects:
        dx = max(cx - w / 2 - x, 0.0, x - (cx + w / 2))
        dy = max(cy - h / 2 - y, 0.0, y - (cy + h / 2))
        dist = math.hypot(dx, dy)
        if best is None or dist < best:
            best = dist
    return 0.0 if best is None else best


BASES = (0.63, 0.886, 0.984, 1.18, 1.63, 2.10, 3.10)
mismatch_grid = mismatch_edge = 0
edge_points = 0
for key in ("map1", "map2", "map3"):
    bm = maps.MAPS[key]
    maps.apply_to_config(bm)
    st = GameState()
    bm.build(st)
    for z in st.deployment_zones:
        rects = z.rects
        if not rects:
            # A zone written as a SHAPE (map 3's corner quadrants) has no
            # rectangle form and therefore no previous answer to preserve.
            # The invariant here is about rectangle-built zones wherever they
            # occur, not about every map having only those.
            c.true(f"{key}: a shape-built zone answers from its shape alone",
                   z.shape is not None and z.contains_point(*z.centroid(board_box=(0, 0, bm.width_in, bm.height_in))))
            continue
        # (a) a plain grid over the board
        for i in range(41):
            for j in range(41):
                x = bm.width_in * i / 40
                y = bm.height_in * j / 40
                if old_contains_point(rects, x, y) != z.contains_point(x, y):
                    mismatch_grid += 1
                if not approx(old_distance(rects, x, y), z.distance_to_point(x, y), 1e-9):
                    mismatch_grid += 1
                for radius in (0.63, 1.18):
                    if old_contains_circle(rects, x, y, radius) != z.contains_circle(x, y, radius):
                        mismatch_grid += 1
        # (b) the points the AI's candidate grid puts EXACTLY on the inset
        # boundary. A random sweep never lands here, and this is precisely
        # where the signed distance first disagreed with the rectangle
        # comparison - 103 of 210 of these flipped from legal to illegal,
        # taking the whole outer ring of the deployment grid with them.
        for cx, cy, w, h in rects:
            for inset in BASES:
                for x, y in ((cx - w / 2 + inset, cy), (cx + w / 2 - inset, cy),
                             (cx, cy - h / 2 + inset), (cx, cy + h / 2 - inset),
                             (cx - w / 2 + inset, cy - h / 2 + inset),
                             (cx + w / 2 - inset, cy + h / 2 - inset)):
                    edge_points += 1
                    if old_contains_circle(rects, x, y, inset) != z.contains_circle(x, y, inset):
                        mismatch_edge += 1

c.eq("no answer changes anywhere on a board-wide grid (3 maps x 2 zones)", mismatch_grid, 0)
c.true("the boundary sweep really did sample something", edge_points >= 150)
c.eq("no answer changes on the AI candidate grid's exact boundary points", mismatch_edge, 0)
c.true("the tolerance that buys that is far below anything the board means",
       PLACEMENT_TOLERANCE_IN < 1e-6)

# The grid boxes the AI lays candidates over must be the same rectangles too.
box_mismatch = 0
for key in ("map1", "map2", "map3"):
    bm = maps.MAPS[key]
    maps.apply_to_config(bm)
    st = GameState()
    bm.build(st)
    for z in st.deployment_zones:
        if not z.rects:
            continue
        for inset in BASES:
            want = sorted((cx - w / 2 + inset, cy - h / 2 + inset, cx + w / 2 - inset, cy + h / 2 - inset)
                          for cx, cy, w, h in z.rects)
            got = sorted(z.shape.sampling_boxes(inset))
            if len(got) != len(want) or not all(approx(a, b) for gg, ww in zip(got, want) for a, b in zip(gg, ww)):
                box_mismatch += 1
c.eq("sampling_boxes reproduces the rectangle-inset grid exactly", box_mismatch, 0)

# No shipped map writes a zone as more than ONE rectangle, so the shipped-map
# sweep above never exercises the union case at all. A stepped zone is exactly
# what DeploymentZone's docstring says rectangles are for, and it has to keep
# being gridded per rectangle - one box over the pair would offer candidates in
# the notch that belongs to neither half.
stepped = DeploymentZone("Player 1", [(6.0, 3.0, 12.0, 6.0), (16.0, 2.0, 8.0, 4.0)])
step_boxes = sorted(stepped.shape.sampling_boxes(0.5))
c.eq("a two-rectangle zone yields TWO grid boxes, one per rectangle", len(step_boxes), 2)
c.true("...each of them its own rectangle inset, not the pair's bounding box",
       all(approx(a, b) for a, b in zip(step_boxes[0], (0.5, 0.5, 11.5, 5.5)))
       and all(approx(a, b) for a, b in zip(step_boxes[1], (12.5, 0.5, 19.5, 3.5))))
c.true("...and the notch the bounding box would have covered is not in either box",
       not any(x0 <= 13.0 <= x1 and y0 <= 5.0 <= y1 for (x0, y0, x1, y1) in step_boxes))


# --------------------------------------------------------------------------
print("--- 4. the seam the old contains_circle gave up on ---")

# Two rectangles meeting edge to edge: one 12x4 zone written as two 6x4 halves.
seam = DeploymentZone("Player 1", [(3.0, 2.0, 6.0, 4.0), (9.0, 2.0, 6.0, 4.0)])
c.true("a base straddling the seam is refused, as before - Union keeps that reading",
       not seam.contains_circle(6.0, 2.0, 1.0))
c.true("...while the same ground written as ONE rectangle accepts it",
       DeploymentZone("Player 1", [(6.0, 2.0, 12.0, 4.0)]).contains_circle(6.0, 2.0, 1.0))
whole = shapes.Intersection([
    shapes.HalfPlane(1, 0, 0.0), shapes.HalfPlane(-1, 0, -12.0),
    shapes.HalfPlane(0, 1, 0.0), shapes.HalfPlane(0, -1, -4.0),
])
c.true("...and written as half-planes there is no seam to be refused at",
       DeploymentZone("Player 1", shape=whole).contains_circle(6.0, 2.0, 1.0))


# --------------------------------------------------------------------------
print("--- 5. a corner zone like the supplied layout ---")

BOARD = 44.0
CUT, HOLE = 30.0, 9.0
corner = shapes.Intersection([
    shapes.HalfPlane.through(CUT, 0.0, 0.0, CUT, BOARD, BOARD),   # diagonal, keep the far corner
    shapes.Outside(shapes.Disc(BOARD / 2, BOARD / 2, HOLE)),      # the circle in the middle
    shapes.HalfPlane(1, 0, 0.0), shapes.HalfPlane(-1, 0, -BOARD),
    shapes.HalfPlane(0, 1, 0.0), shapes.HalfPlane(0, -1, -BOARD),
])
cz = DeploymentZone("Player 1", shape=corner)

c.true("the far corner is in the zone", cz.contains_point(42.0, 42.0))
c.true("the near corner is not", not cz.contains_point(2.0, 2.0))
c.true("a point past the diagonal but inside the centre hole is excluded",
       cz.contains_point(30.0, 8.0) and not cz.contains_point(BOARD / 2 + 4, BOARD / 2 + 4))
c.true("the hole is exactly the printed radius",
       not cz.contains_point(BOARD / 2 + HOLE - 0.1, BOARD / 2)
       and cz.contains_point(BOARD / 2 + HOLE + 0.1, BOARD / 2))

# "Wholly within" against a curve, checked against a brute-force rim test -
# min() over an intersection is only exact for CONVEX parts, and this shape
# has a concave one (the hole), so the claim needs measuring rather than
# asserting.
def brute_within(shape, x, y, r, n=360):
    if shape.signed_distance(x, y) < 0:
        return False
    return all(shape.signed_distance(x + r * math.cos(2 * math.pi * k / n),
                                     y + r * math.sin(2 * math.pi * k / n)) >= 0
               for k in range(n))


wrong_allow = conservative = 0
for i in range(60):
    for j in range(60):
        x, y = BOARD * (i + 0.5) / 60, BOARD * (j + 0.5) / 60
        for radius in (0.63, 1.18, 2.10):
            fast = cz.contains_circle(x, y, radius)
            exact = brute_within(corner, x, y, radius)
            if fast and not exact:
                wrong_allow += 1
            elif exact and not fast:
                conservative += 1
c.eq("a corner zone never allows a base that is not wholly within it", wrong_allow, 0)
c.eq("...and on this shape it is not merely conservative either, it is exact", conservative, 0)

c.true("INFILTRATORS' 24.20 distance is measured perpendicular to the diagonal",
       approx(cz.distance_to_point(0.0, 0.0), CUT / math.sqrt(2), 1e-9))
c.true("a rotated rectangle zone works the same way",
       DeploymentZone("P", shape=shapes.Rect(20, 20, 12, 6, angle_deg=30.0)).contains_circle(20, 20, 2.9))

boxes = cz.shape.sampling_boxes(1.0, fallback_box=(0.0, 0.0, BOARD, BOARD))
c.true("a zone with unbounded parts still yields a grid box to sample", len(boxes) == 1)
c.true("...and it is the board, inset - nothing legal falls outside it",
       all(cz.contains_circle(x, y, 1.0) is False or
           (boxes[0][0] <= x <= boxes[0][2] and boxes[0][1] <= y <= boxes[0][3])
           for x in (1.0, 22.0, 43.0) for y in (1.0, 22.0, 43.0)))


# --------------------------------------------------------------------------
print("--- 6. the territory split turns with the zones ---")


class Ctx:
    def __init__(self, zones, player, opponent):
        self.deployment_zones = zones
        self.player = player
        self.opponent = opponent


def old_territory(ctx, x, y):
    """The axis-pick this replaces: whichever of x/y separates the two zone
    centres, split the board in half there."""
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    theirs = [z for z in ctx.deployment_zones if z.owner == ctx.opponent]
    if not mine or not theirs:
        return True
    mx, my = sm._zone_centre(mine[0])
    tx, ty = sm._zone_centre(theirs[0])
    ccx, ccy = sm.board_centre()
    if abs(my - ty) >= abs(mx - tx):
        return (y >= ccy) if my >= ccy else (y <= ccy)
    return (x >= ccx) if mx >= ccx else (x <= ccx)


changed = 0
sampled = 0
for key in ("map1", "map2", "map3"):
    bm = maps.MAPS[key]
    maps.apply_to_config(bm)
    st = GameState()
    bm.build(st)
    if any(not z.rects for z in st.deployment_zones):
        # map 3's corner quadrants: the axis pick this replaced could not
        # express them at all, so there is no old answer to be neutral to.
        # That it DIFFERS there is the point, and it is measured below.
        c.true(f"{key}: a corner-zone map is where the two rules must diverge",
               any(sm.in_own_territory(Ctx(st.deployment_zones, "Player 1", "Player 2"), x, y)
                   != old_territory(Ctx(st.deployment_zones, "Player 1", "Player 2"), x, y)
                   for x in (5.0, 20.0, 40.0, 55.0) for y in (5.0, 20.0, 30.0, 40.0)))
        continue
    for me, foe in (("Player 1", "Player 2"), ("Player 2", "Player 1")):
        ctx = Ctx(st.deployment_zones, me, foe)
        for i in range(61):
            for j in range(61):
                x, y = bm.width_in * i / 60, bm.height_in * j / 60
                sampled += 1
                if sm.in_own_territory(ctx, x, y) != old_territory(ctx, x, y):
                    changed += 1
c.true("the territory sweep really covered the boards", sampled > 10000)
c.eq("no point on any shipped map changes territory", changed, 0)

# And the thing the old form could not express at all - measured on the REAL
# corner-deployment map rather than a synthetic pair of zones, so this is the
# geometry the game actually plays.
bm3 = maps.MAPS["map3"]
maps.apply_to_config(bm3)
st3 = GameState()
bm3.build(st3)
ctx = Ctx(st3.deployment_zones, "Player 1", "Player 2")
p1_zone = [z for z in st3.deployment_zones if z.owner == "Player 1"][0]
p2_zone = [z for z in st3.deployment_zones if z.owner == "Player 2"][0]
c.true("map3 really does deploy in opposite CORNERS",
       p1_zone.rects == [] and p2_zone.rects == [])
own_corner = p1_zone.centroid(board_box=(0.0, 0.0, bm3.width_in, bm3.height_in))
foe_corner = p2_zone.centroid(board_box=(0.0, 0.0, bm3.width_in, bm3.height_in))
c.true("my own corner is my territory", sm.in_own_territory(ctx, *own_corner))
c.true("...the opposite corner is not", not sm.in_own_territory(ctx, *foe_corner))
c.true("the dividing line runs through the board centre for symmetric zones",
       sm.in_own_territory(ctx, 30.0, 22.0))

# The points that actually SEPARATE a diagonal split from the axis pick it
# replaces. The four board corners do not: with symmetric corner zones the old
# rule happens to agree on all of them, so a test built from corners passes
# under both rules and proves nothing. These two lie on opposite sides of the
# diagonal but the same side of the axis the old rule would have picked.
c.true("the flank beyond the diagonal is MINE on a diagonal split",
       sm.in_own_territory(ctx, 35.0, 40.0))
c.true("...though the axis pick it replaces would have called it theirs",
       not old_territory(ctx, 35.0, 40.0))
c.true("and the mirror point is THEIRS", not sm.in_own_territory(ctx, 25.0, 4.0))
c.true("...though the axis pick would have called it mine",
       old_territory(ctx, 25.0, 4.0))
c.true("zone_distance is the zone's own answer now, not a second copy",
       approx(sm.zone_distance(p1_zone, 30.0, 22.0), p1_zone.distance_to_point(30.0, 22.0)))
c.true("...and it is non-zero at the board centre, which no zone reaches",
       sm.zone_distance(p1_zone, 30.0, 22.0) > 0.0)


# --------------------------------------------------------------------------
print("--- 7. source guards ---")

import io
import os

PRODUCTION = []
for folder in ("game", "ai"):
    for name in sorted(os.listdir(folder)):
        if name.endswith(".py"):
            PRODUCTION.append(os.path.join(folder, name))
    for sub in ("ui",):
        d = os.path.join(folder, sub)
        if os.path.isdir(d):
            PRODUCTION.extend(os.path.join(d, n) for n in sorted(os.listdir(d)) if n.endswith(".py"))
PRODUCTION.append("main.py")

readers = []
for path in PRODUCTION:
    if path.replace("\\", "/") == "game/deployment.py":
        continue
    src = io.open(path, encoding="utf-8").read()
    for line in src.splitlines():
        if ".rects" in line and "zone" in line.lower():
            readers.append(f"{path}: {line.strip()}")
c.eq("no production module answers a geometry question from zone.rects", readers, [])
c.true("the guard can see the files it is guarding", len(PRODUCTION) > 40)

dep_src = io.open("game/deployment.py", encoding="utf-8").read()
c.true("DeploymentZone delegates every question to its shape",
       dep_src.count("self.shape.signed_distance(") >= 3)
c.true("the zone still records how it was authored, for the maps and tests that write rectangles",
       "self.rects = list(rects)" in dep_src)

ai_src = io.open("ai/deployment_ai.py", encoding="utf-8").read()
c.true("the deployment AI samples the zone SHAPE, not its rectangles",
       "own.shape.sampling_boxes(inset" in ai_src)
c.true("...and the INFILTRATORS/no-zone box goes through the same inset",
       "board_h_in).sampling_boxes(inset)" in ai_src)

rend_src = io.open("game/renderer.py", encoding="utf-8").read()
c.true("the renderer traces the zone outline from its shape",
       "_shape_outline_segments(zone.shape" in rend_src)
c.true("...and the drawing half asks own_board_edges rather than selecting itself",
       "for (sx, sy), (ex, ey) in own_board_edges(board, zone):" in rend_src)

print("--- 8. which board edges are a zone's own ---")

from game.renderer import own_board_edges
from game.board import Board

BW = BH = 30.0
brd = Board(BW, BH, 10)
NORTH = ((0.0, 0.0), (BW, 0.0))
SOUTH = ((0.0, BH), (BW, BH))
WEST = ((0.0, 0.0), (0.0, BH))
EAST = ((BW, 0.0), (BW, BH))

band = DeploymentZone("Player 2", [(BW / 2, 4.0, BW, 8.0)])
c.eq("a full-width band along the north edge owns exactly that one edge",
     own_board_edges(brd, band), [NORTH])
band_s = DeploymentZone("Player 1", [(BW / 2, BH - 4.0, BW, 8.0)])
c.eq("...and the mirrored band owns the south edge", own_board_edges(brd, band_s), [SOUTH])

nw = DeploymentZone("Player 1", shape=shapes.Disc(4.0, 4.0, 6.0))
c.eq("a corner zone owns BOTH adjacent edges, which no axis test can say",
     sorted(own_board_edges(brd, nw)), sorted([NORTH, WEST]))
se = DeploymentZone("Player 2", shape=shapes.Disc(BW - 4.0, BH - 4.0, 6.0))
c.eq("...and the opposite corner owns the other two",
     sorted(own_board_edges(brd, se)), sorted([SOUTH, EAST]))
c.true("a zone centred on the board owns none - there is no direction to face",
       own_board_edges(brd, DeploymentZone("P", [(BW / 2, BH / 2, 6.0, 6.0)])) == [])

c.finish()
