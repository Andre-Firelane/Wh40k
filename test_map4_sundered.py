"""map 4 - "Sundered", the first board with DIAGONAL deployment zones.

User: "map4 anlegen. sprite liegt im ordner. schraege deployment zones. die
territory grenze ist eine parallele zu den deplyment zones in der mitte
zwischen ihnen."

Three things were asked for and each has its own section: the board itself,
zones cut off by a slanted edge, and a territory boundary that is a third line
PARALLEL to those two, halfway between them. The third is the one that needed a
change outside this file - see game/mission_context.py's in_own_territory() -
so section 3 measures it against the ideal line rather than against the code
that produces it.

  1. the board and the scale it was measured at
  2. the deployment zones - two parallel diagonals, and an army that fits
  3. THE TERRITORY LINE - the parallel midline, measured against the ideal
  4. the terrain - rotated, one clean rectangle each, symmetric on the BUILT board
  5. the objectives - five, correctly classified, compass names checked
  6. what the rest of the engine reads off it
  7. pieces that touch, touch - and the pair the art leaves open stays open
  8. the objective outline, measured in PIXELS
"""

import math

import testkit as tk
from testkit import Checks

from game import config, deployment, maps, shapes
from game.game_state import GameState
from game import secondary_missions as sm
from game import primary_missions as pm
from game import mission_context as mc
from ai import deployment_ai, observation

c = Checks("map4 - Sundered (diagonal deployment)")

BM = maps.get("map4")
maps.apply_to_config(BM)
ST = GameState()
BM.build(ST)
CX, CY = BM.center
BOARD_BOX = (0.0, 0.0, BM.width_in, BM.height_in)


def approx(got, want, tol=1e-6):
    return abs(got - want) <= tol


def mirror(x, y):
    return BM.width_in - x, BM.height_in - y


# A PROBE MUST TURN THIS SUITE RED, NOT CRASH IT - the lesson this repo has
# now paid for nineteen times. Every lookup below that a probe can empty goes
# through one of these, so a broken board reports WHICH assurance broke instead
# of a traceback that reports nothing.
def first(iterable, default=None):
    return next(iter(iterable), default)


def safe_min(iterable, default=float("inf")):
    values = list(iterable)
    return min(values) if values else default


class _Flat:
    """Stand-in for "this area has no upright footprint at all", so a probe
    that removes one reads as angle 0 rather than raising."""
    angle_deg = 0.0


_FLAT = _Flat()


# The construction the zones are built to, written out once here so every
# check below measures against the GEOMETRY rather than against the same
# constants game/maps.py used. P1's edge runs (0,0)-(30,44); P2's is its
# 180-degree mirror, (30,0)-(60,44).
RUN, RISE = 30.0, 44.0
EDGE_LEN = math.hypot(RUN, RISE)


def p1_side(x, y):
    """Signed: negative on Player 1's side of Player 1's own zone edge."""
    return (RISE * x - RUN * y) / EDGE_LEN


def p2_side(x, y):
    """Signed: positive on Player 2's side of Player 2's own zone edge."""
    return (RISE * x - RUN * y - RISE * RUN) / EDGE_LEN


# --------------------------------------------------------------------------
print("--- 1. the board ---")

c.eq("60 inches wide", BM.width_in, 60.0)
c.eq("44 inches deep", BM.height_in, 44.0)
c.true("the source image is exactly 40 px per inch, which is why the numbers "
       "come out on clean fractions",
       approx(2400 / BM.width_in, 40.0) and approx(1760 / BM.height_in, 40.0))
c.eq("the board centre", (CX, CY), (30.0, 22.0))
c.true("the name says what it is",
       "60" in BM.name and "diagonal" in BM.name.lower())
c.eq("it is registered under map4", maps.get("map4").key, "map4")
c.eq("...and the bare number resolves to it too", maps.get("4").key, "map4")
c.true("it does not become the default map by existing",
       maps.DEFAULT_MAP_KEY != "map4")
c.true("it fields the whole army, like the three boards before it",
       BM.army_roster is None)


# --------------------------------------------------------------------------
print("--- 2. the deployment zones ---")

p1 = deployment.zone_for(ST.deployment_zones, "Player 1")
p2 = deployment.zone_for(ST.deployment_zones, "Player 2")
c.true("both players have a zone", p1 is not None and p2 is not None)
c.eq("neither is written as rectangles - a slanted edge cannot be", (p1.rects, p2.rects), ([], []))

c.true("Player 2 keeps the low-y corner, as on all three other maps",
       p2.centroid(board_box=BOARD_BOX)[1] < CY < p1.centroid(board_box=BOARD_BOX)[1])
c.true("...and they are diagonally opposite, not banded",
       (p2.centroid(board_box=BOARD_BOX)[0] - CX) * (p1.centroid(board_box=BOARD_BOX)[0] - CX) < 0)

# WHICH corners each triangle owns - and it is ONE each, not two. A diagonal
# from a corner to the midpoint of the opposite long edge cuts a triangle whose
# other two board corners are the deep one and the APEX: Player 1's triangle
# has vertices (0,0), (0,44) and (30,44), so (0,0) is only its point. The two
# corners nobody owns outright are exactly where the band meets the short
# edges.
c.true("Player 1 owns the low-x HIGH-y corner", p1.contains_point(1.0, 43.0))
c.true("...but not the low-x low-y one - that is where its triangle comes to a point",
       not p1.contains_point(1.0, 1.0))
c.true("...and neither high-x corner",
       not p1.contains_point(59.0, 1.0) and not p1.contains_point(59.0, 43.0))
c.true("Player 2 owns the high-x LOW-y corner", p2.contains_point(59.0, 1.0))
c.true("...but not the high-x high-y one, which is its own apex",
       not p2.contains_point(59.0, 43.0))
c.true("...and neither low-x corner",
       not p2.contains_point(1.0, 1.0) and not p2.contains_point(1.0, 43.0))
c.true("the band between them belongs to nobody",
       not any(z.contains_point(CX, CY) for z in ST.deployment_zones))
c.true("...including the two board corners the band runs out through",
       not any(z.contains_point(x, y) for z in ST.deployment_zones
               for x, y in ((1.0, 1.0), (59.0, 43.0))))

# THE EDGES ARE THE CONSTRUCTION. Measured off the source image the pink edge
# passes through (0.094, 0) and (30.039, 44) - a board CORNER and the MIDPOINT
# of the opposite long edge, to 0.09" and 0.04" - and the two drawn edges are
# parallel to 0.0008 degrees. The board is built to the exact construction,
# which is what these check.
for x, y in ((0.0, 0.0), (RUN, RISE), (RUN / 2, RISE / 2)):
    c.true(f"Player 1's edge passes through ({x:g}, {y:g})",
           approx(p1.distance_to_point(x, y), 0.0, 1e-9) and p1.contains_point(x, y))
for x, y in ((RUN, 0.0), (BM.width_in, RISE), (RUN + RUN / 2, RISE / 2)):
    c.true(f"Player 2's edge passes through ({x:g}, {y:g})",
           approx(p2.distance_to_point(x, y), 0.0, 1e-9) and p2.contains_point(x, y))

# PARALLEL, not merely both slanted - which is what makes the open ground a
# BAND of constant width instead of a wedge, and what lets the territory line
# be parallel to both of them at once.
widths = [p1.distance_to_point(x, y) + p2.distance_to_point(x, y)
          for x, y in ((0.5, 0.0), (15.0, 22.0), (30.0, 22.0), (45.0, 43.9), (30.5, 44.0))]
c.true("the open ground is a BAND of constant width, so the edges are parallel",
       max(widths) - min(widths) < 1e-6)
IDEAL_GAP = RISE * RUN / EDGE_LEN            # 24.787"
c.true(f"...and that width is the construction's {IDEAL_GAP:.3f} inches",
       approx(widths[0], IDEAL_GAP, 1e-6))
# The art annotates 24.25". That is NOT this measurement and was checked
# rather than assumed: the white ruler carrying that label is 15.05" long end
# to end and its endpoints stand 5.06" and 4.52" from the two dashed lines, so
# it spans neither of them. Map 3's precedent (annotation minus the dashed
# line's own width) cannot explain it either - a line width makes the gap
# BIGGER, not smaller. Pinned so a later "correction" to the label has to
# argue with the ruler.
c.true("the drawn 24.25in annotation is 0.54in off the construction, and the "
       "construction is what is built", approx(IDEAL_GAP - 24.25, 0.537, 0.01))

# An army has to FIT. Same measurement that killed the rectangle approximation
# for map 3's zones (see game/shapes.py): a staircase leaves a grav tank
# nowhere to stand at all.
cell = 60 * 44 / (121 * 89)
for label, radius, floor in (("25mm", 0.63, 500), ("50mm", 1.18, 450), ("grav tank", 2.10, 350)):
    area = sum(1 for i in range(121) for j in range(89)
               if p1.contains_circle(60 * i / 120, 44 * j / 88, radius)) * cell
    c.true(f"a {label} base has room: {area:.0f} sq.in of Player 1's zone", area > floor)
sym = [sum(1 for i in range(121) for j in range(89)
           if z.contains_point(60 * i / 120, 44 * j / 88)) for z in (p1, p2)]
c.eq("both zones are the same size, as a 180-degree symmetric layout demands", sym[0], sym[1])
c.true("...and each is about a quarter of the board, as two corner triangles are",
       abs(sym[0] * cell / (60 * 44) - 0.25) < 0.02)

# The bounding box, which is what every SAMPLING consumer falls back on.
# HalfPlane.bounding_box() is None for a slanted edge - correct - so without
# the four board-edge half-planes this Intersection reports no box at all and
# the deployment AI's exposure probe silently measures nothing.
for zone in ST.deployment_zones:
    c.true(f"{zone.owner}'s zone reports a bounding box", zone.bounding_box() is not None)
    c.true(f"...and the AI's exposure probe finds points in it",
           len(deployment_ai._zone_probe_points(zone)) >= 10)
    c.true("...all of them actually inside the zone",
           all(zone.contains_point(*p) for p in deployment_ai._zone_probe_points(zone)))
    c.true(f"...and a candidate grid to deploy on", deployment_ai._shape_box(zone) is not None)
# The half-plane whose edge is SLANTED must still refuse to report a box, or
# the guard above is testing nothing: it is the four square ones that bound it.
c.true("a slanted half-plane still reports no box of its own - the board edges "
       "are what bound the zone",
       shapes.HalfPlane.through(0.0, 0.0, RUN, RISE, 0.0, RISE).bounding_box() is None)


# --------------------------------------------------------------------------
print("--- 3. the territory line is PARALLEL to the zones, halfway between ---")

# THE REQUEST: "die territory grenze ist eine parallele zu den deplyment zones
# in der mitte zwischen ihnen." The ideal line is therefore (15,0)-(45,44) -
# both edges shifted half the band's width - and this measures the shipped rule
# against that line rather than against the code that computes it.


class Ctx:
    def __init__(self, zones, player, opponent):
        self.deployment_zones = zones
        self.player = player
        self.opponent = opponent


def midline(x, y):
    """Signed distance to the ideal parallel midline; negative on P1's side."""
    return (RISE * x - RUN * y - RISE * RUN / 2) / EDGE_LEN


ctx1 = Ctx(ST.deployment_zones, "Player 1", "Player 2")
ctx2 = Ctx(ST.deployment_zones, "Player 2", "Player 1")

wrong = 0
tested = 0
for i in range(301):
    for j in range(301):
        x, y = BM.width_in * i / 300, BM.height_in * j / 300
        if abs(midline(x, y)) < 0.02:      # points ON the line are a tie either way
            continue
        tested += 1
        if sm.in_own_territory(ctx1, x, y) != (midline(x, y) < 0):
            wrong += 1
        if sm.in_own_territory(ctx2, x, y) != (midline(x, y) > 0):
            wrong += 1
c.true("the territory sweep really covered the board", tested > 80000)
c.eq("every point on the board falls on the side of the parallel midline it should",
     wrong, 0)

# ...and it is not a vertical or horizontal line dressed up. The two points
# below sit on opposite sides of the DIAGONAL and the same side of the board's
# vertical centre line, which is exactly what the axis pick this rule grew out
# of could not express.
c.true("a point past the diagonal but left of centre is THEIRS",
       not sm.in_own_territory(ctx1, 25.0, 2.0))
c.true("...and its mirror, past the diagonal but right of centre, is MINE",
       sm.in_own_territory(ctx1, 35.0, 42.0))
c.true("my own zone is my territory", sm.in_own_territory(ctx1, 2.0, 40.0))
c.true("...their zone is not", not sm.in_own_territory(ctx1, 58.0, 4.0))
# The board centre sits ON the midline, so it is a tie - measured as one
# rather than asserted through in_own_territory(), whose <= breaks the tie on
# whichever side rounds smaller in the last bit. Which player wins a
# measure-zero line is not a fact about this map.
c.true("the board centre lies exactly on the parallel midline",
       approx(midline(CX, CY), 0.0, 1e-9))
c.true("...and it is equidistant from the two zones, which is what makes it one",
       approx(p1.distance_to_point(CX, CY), p2.distance_to_point(CX, CY), 1e-9))
c.true("...and exactly one player claims it, so nothing falls between the two",
       sm.in_own_territory(ctx1, CX, CY) != sm.in_own_territory(ctx2, CX, CY))

# THE RULE THIS REPLACED would not have delivered it. Kept as a live
# comparison rather than a remembered number: the centre bisector runs 14
# degrees off the zone edges on this board.
mine_c = mc._zone_centre(p1)
theirs_c = mc._zone_centre(p2)


def centre_rule(x, y):
    return ((x - mine_c[0]) ** 2 + (y - mine_c[1]) ** 2
            <= (x - theirs_c[0]) ** 2 + (y - theirs_c[1]) ** 2)


bisector_deg = math.degrees(math.atan2(mine_c[0] - theirs_c[0], theirs_c[1] - mine_c[1])) % 180
edge_deg = math.degrees(math.atan2(RISE, RUN)) % 180
c.true(f"the zone edges run at {edge_deg:.2f} degrees", approx(edge_deg, 55.71, 0.01))
c.true(f"...while the zone-CENTRE bisector runs at {bisector_deg:.2f}, "
       f"{abs(bisector_deg - edge_deg):.1f} degrees out - which is why the rule "
       f"had to measure to the SHAPES", abs(bisector_deg - edge_deg) > 10.0)
disagree = sum(1 for i in range(201) for j in range(201)
               for x, y in [(BM.width_in * i / 200, BM.height_in * j / 200)]
               if abs(midline(x, y)) >= 0.02 and centre_rule(x, y) != (midline(x, y) < 0))
c.true(f"...and it really lands elsewhere on {disagree} sampled points", disagree > 1000)


# --------------------------------------------------------------------------
print("--- 4. the terrain ---")

feet = [o for area in ST.terrain_areas for o in area.features if o.category != "dense"]
walls = [o for area in ST.terrain_areas for o in area.features if o.category == "dense"]
c.eq("fifteen footprints - one central piece plus seven mirror pairs", len(feet), 15)
c.true("and a wall layout on top of them", len(walls) > 0)
c.eq("every terrain area is one footprint plus its walls", len(ST.terrain_areas), 15)
c.true("every footprint is ONE clean rectangle, no composite shapes",
       all(len([o for o in area.features if o.category != "dense"]) == 1
           for area in ST.terrain_areas))
c.true("every piece is inside the board", all(
    o.min_x >= -0.01 and o.max_x <= BM.width_in + 0.01
    and o.min_y >= -0.01 and o.max_y <= BM.height_in + 0.01 for o in feet))

turned = [o for o in feet if abs(o.angle_deg) > 1e-9]
c.eq("eight pieces really are rotated - this map is built on the diagonal", len(turned), 8)
c.eq("...at two angles, in four mirror pairs", sorted(round(o.angle_deg, 1) for o in turned),
     [55.0] * 6 + [63.0] * 2)
# The SIGN of the angle is a MEASUREMENT, not a convention guessed at:
# building the north-west ruin's footprint at +55 covers 92.1% of its drawn
# pixels and at -55 only 62.0%, so the engine's angle_deg IS the image-space
# angle with no flip. Pinned as "positive", which is the half of that a later
# reader can check without the sprite.
c.true("every rotated piece carries a POSITIVE angle, as measured against the art",
       all(o.angle_deg > 0 for o in turned))

ruins = [a for a in ST.terrain_areas if any(f.category == "dense" for f in a.features)]
turned_ruins = [a for a in ruins
                if abs(next(f for f in a.features if f.category != "dense").angle_deg) > 1e-9]
c.eq("the two rotated ruins are the ones carrying the No Man's Land objectives",
     len(turned_ruins), 2)
c.true("...and every wall of a rotated ruin carries the SAME angle as its footprint",
       all(all(abs(w.angle_deg - next(f for f in a.features if f.category != "dense").angle_deg) < 1e-9
               for w in a.features if w.category == "dense")
           for a in turned_ruins))
c.true("...and its walls really sit on it, not beside it",
       all(next(f for f in a.features if f.category != "dense").overlaps_circle(w.x_in, w.y_in, 0.01)
           for a in turned_ruins for w in a.features if w.category == "dense"))

# The symmetry, checked on the BUILT map rather than on the measurement, so a
# hand-edited coordinate shows up here. WALLS included: the central piece is
# its own mirror, so its wall layout has to be symmetric too - which is the
# whole reason it keeps only two diagonally opposite corner "L"s.
for label, pieces in (("footprint", feet), ("wall", walls)):
    unmatched = []
    for o in pieces:
        mx, my = mirror(o.x_in, o.y_in)
        if not any(abs(p.x_in - mx) < 0.02 and abs(p.y_in - my) < 0.02
                   and approx(p.width_in, o.width_in, 0.02) and approx(p.height_in, o.height_in, 0.02)
                   and approx(p.angle_deg, o.angle_deg, 0.02)
                   for p in pieces):
            unmatched.append((round(o.x_in, 2), round(o.y_in, 2)))
    c.eq(f"every {label} has an exact 180-degree twin", unmatched, [])

# The central piece: one rectangle standing ON the board centre, so it is its
# own mirror and is built once rather than through both().
centre_piece = first(f for f in feet if approx(f.x_in, CX, 0.01) and approx(f.y_in, CY, 0.01))
c.true("the central ruin stands exactly on the board centre", centre_piece is not None)
c.true("...upright, as measured", centre_piece is not None and approx(centre_piece.angle_deg, 0.0))
centre_area = first(a for a in ST.terrain_areas if centre_piece in a.features)
centre_walls = [f for f in centre_area.features if f.category == "dense"] if centre_area else []
# It keeps ruin()'s all-four-sides layout rather than l_walls()' L, because no
# single side of a piece ON the board centre faces "the enemy" - the same
# reading map 1's and map 2's central pieces use. And only two of the four
# corner Ls are built, diagonally opposite, so the walls mirror onto
# themselves. "sw" is the low-x/high-y corner facing Player 1, "ne" the
# high-x/low-y corner facing Player 2 - each player meets a wall coming at it.
c.eq("the central ruin keeps two of its four corner Ls, which is four segments",
     len(centre_walls), 4)
c.true("...and they are the two corners facing the two players, diagonally opposite",
       all(any(abs(w.x_in - (BM.width_in - v.x_in)) < 0.02
               and abs(w.y_in - (BM.height_in - v.y_in)) < 0.02 for v in centre_walls)
           for w in centre_walls))
c.true("...one L on Player 1's side of the piece",
       any(w.x_in < centre_piece.x_in and w.y_in > centre_piece.y_in for w in centre_walls))
c.true("...and one on Player 2's",
       any(w.x_in > centre_piece.x_in and w.y_in < centre_piece.y_in for w in centre_walls))


# --------------------------------------------------------------------------
print("--- 5. the objectives ---")

names = [o.name for o in ST.objectives]
c.eq("five objectives", len(ST.objectives), 5)
c.eq("every name is unique", len(set(names)), len(names))
c.true("none of them reads like debug output",
       all("No Man's Land" not in n for n in names))

homes = [o for o in ST.objectives if "Home" in o.name]
c.eq("two home objectives", len(homes), 2)
for objective in homes:
    ox, oy = sm.objective_centre(objective)
    owner = "Player 1" if "P1" in objective.name else "Player 2"
    zone = deployment.zone_for(ST.deployment_zones, owner)
    c.true(f"{objective.name} is inside {owner}'s own zone", zone.contains_point(ox, oy))
    # And WHOLLY inside, area and all. The cross-map form of this is
    # test_deployment_shapes.py section 9; this is the map-local half, because
    # a home objective that straddles its own zone edge breaks every mission
    # that says "outside your deployment zone".
    corners = [(x, y) for f in objective.terrain_area.features for x, y in f.corners()]
    c.true(f"...every corner of it too", all(zone.contains_point(x, y) for x, y in corners))

nml = sm.no_mans_land_objectives(
    sm.MissionContext("Player 1", objectives=ST.objectives, deployment_zones=ST.deployment_zones))
c.eq("the other three are No Man's Land", len(nml), 3)
for objective in nml:
    corners = [(x, y) for f in objective.terrain_area.features for x, y in f.corners()]
    c.true(f"{objective.name} keeps its whole AREA out of both zones",
           all(not z.contains_point(x, y) for x, y in corners for z in ST.deployment_zones))

# The two rotated ruins are the tightest fit on this board - their nearest
# corner clears a zone edge by 1.41". Pinned so a re-measurement that nudges
# them cannot quietly put a corner inside somebody's zone.
tight = safe_min(min(p1.distance_to_point(x, y), p2.distance_to_point(x, y))
                 for o in nml
                 if abs(first((f for f in o.terrain_area.features
                               if f.category != "dense"), _FLAT).angle_deg) > 1e-9
                 for f in o.terrain_area.features for x, y in f.corners())
c.true(f"the rotated ruins clear the zones by {tight:.2f}in, which is not much", tight > 1.0)

# The cardinal names have to be true, or they are worse than no name at all.
for objective in ST.objectives:
    ox, oy = sm.objective_centre(objective)
    for word, axis, sign in (("North", oy, -1), ("South", oy, 1), ("West", ox, -1), ("East", ox, 1)):
        if word in objective.name:
            centre = CY if word in ("North", "South") else CX
            c.true(f"{objective.name} really is {word.lower()} of centre",
                   (axis - centre) * sign > 0)

# Four in two mirror pairs, plus the one that is its own mirror.
paired = 0
for objective in ST.objectives:
    ox, oy = sm.objective_centre(objective)
    mx, my = mirror(ox, oy)
    if any(abs(sm.objective_centre(o)[0] - mx) < 0.05
           and abs(sm.objective_centre(o)[1] - my) < 0.05
           and o is not objective for o in ST.objectives):
        paired += 1
c.eq("four objectives sit in two mirror pairs", paired, 4)
central = first(o for o in ST.objectives if "Central" in o.name)
c.true("...and the fifth is the central one, which is its own mirror",
       central is not None
       and all(approx(v, w, 0.05) for v, w in zip(sm.objective_centre(central), (CX, CY))))


# --------------------------------------------------------------------------
print("--- 6. what the rest of the engine reads off it ---")

ctx = sm.MissionContext("Player 1", objectives=ST.objectives, deployment_zones=ST.deployment_zones)

# Secure Asset and Unstoppable Force read this one. Unlike map 3 - whose
# middle is the hole and which has no central objective at all - this board
# has exactly one, standing on the centre.
c.eq("central_objectives() finds exactly the one on the board centre",
     [o.name for o in pm.central_objectives(ctx)], ["Central Objective"])

# Forward Position reads these: one per player, the nearest non-home objective
# to that player's own zone, and on this board they are a mirror pair.
c.eq("Player 1's expansion objective", getattr(sm.expansion_objective_for(ctx, "Player 1"), "name", None),
     "Objective Northwest")
c.eq("Player 2's", getattr(sm.expansion_objective_for(ctx, "Player 2"), "name", None),
     "Objective Southeast")
c.eq("...so Forward Position asks for both of them",
     sorted(o.name for o in sm.expansion_objectives(ctx)),
     ["Objective Northwest", "Objective Southeast"])

# Home garrison reach: READ OFF THE BOARD, not set. 24.2" here, the longest of
# the four maps - the diagonal band puts a home objective further from
# everything else than any other layout does, so a home garrison on this board
# cannot contribute at range at all. The number is pinned because the
# CONCLUSION depends on it, not because 24.2 is special.
needs = []
for owner in ("Player 1", "Player 2"):
    own = deployment.zone_for(ST.deployment_zones, owner)
    home = deployment_ai._home_objective(owner, ST.objectives, own)
    needs.append(round(observation.garrison_reach_needed_in(home, ST.objectives), 1)
                 if home is not None else None)
c.eq("both players need the same reach from home", needs[0], needs[1])
c.eq("...and it is 24.2 inches, the longest of the four boards", needs[0], 24.2)
c.true("...so nothing short of a 24in gun can hold home and still shoot forward",
       needs[0] > 24.0)

# The map picker builds its one-line description off the BUILT zones. Both
# numbers come out of sampling, so a zone that reported no bounding box would
# show up here as zeroes.
band = safe_min((math.hypot(ax - bx, ay - by)
                 for ax, ay in [(x, y) for x in (0.0, 5.0, 10.0) for y in (0.0, 20.0, 40.0)
                                if p1.contains_point(x, y)]
                 for bx, by in [(x, y) for x in (50.0, 55.0, 60.0) for y in (0.0, 20.0, 40.0)
                                if p2.contains_point(x, y)]),
                default=-1.0)
c.true(f"the two zones really are {IDEAL_GAP:.1f}in apart at their closest",
       band >= IDEAL_GAP - 0.01)


# --------------------------------------------------------------------------
print("--- 7. pieces that touch, touch ---")

# The percentile fit trims a slice off BOTH pieces of a touching pair, so a
# join the art draws closed comes out of the measurement as a slot. This is
# the same correction map 3 needed; what is pinned is the RESULT, in a form
# that catches a re-measurement sliding a sliver back in.


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


def _crosses(p1_, p2_, p3_, p4_):
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    return (((cross(p3_, p4_, p1_) > 0) != (cross(p3_, p4_, p2_) > 0))
            and ((cross(p1_, p2_, p3_) > 0) != (cross(p1_, p2_, p4_) > 0)))


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
# Two measured contacts, and the map is symmetric, so four.
c.eq("the two contacts the art draws are built, on both halves", len(touching), 4)
c.true("...and each is an exact contact, not an overlap",
       all(gap(feet[i], feet[j]) == 0.0 for i, j in touching))

# THE CONTROL, without which the line above would also pass on a board that
# shoved everything into one lump: the nearest pair the art leaves OPEN is
# 1.30" apart in the source image and stays open here.
nearest_open = safe_min((gap(feet[i], feet[j])
                         for i in range(len(feet)) for j in range(i + 1, len(feet))
                         if gap(feet[i], feet[j]) > 0.0), default=-1.0)
c.true(f"the nearest pair the art leaves open stays open ({nearest_open:.2f}in)",
       nearest_open > SLIVER_IN)

# NAMED DIFFERENCE FROM MAP 3. There the closed seam mattered for play: two
# RUINS whose walls stood 0.15" apart and facing each other, a slot a line of
# sight threaded. Here every seam has a BARRICADE on at least one side, and a
# barricade is a LIGHT footprint with no walls - it has never blocked sight.
# Closing these is visual, and saying so is what stops the next reader
# assuming this map inherited map 3's sight-line fix.
barricade_areas = {id(a.features[0]) for a in ST.terrain_areas
                   if not any(f.category == "dense" for f in a.features)}
c.true("every closed seam has a barricade on at least one side, so none of them "
       "was a shootable slot",
       all(id(feet[i]) in barricade_areas or id(feet[j]) in barricade_areas
           for i, j in touching))
c.eq("...and there are barricades to be found at all - eight of the fifteen "
     "pieces carry no walls", len(barricade_areas), 8)
c.eq("...leaving seven ruins, which is where every wall on this board comes from",
     len(ruins), 7)


# --------------------------------------------------------------------------
print("--- 8. the objective outline follows the footprint ---")

import os  # noqa: E402  (local to this section)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

from game import renderer as R  # noqa: E402
from game.board import Board  # noqa: E402

pygame.init()
pygame.display.set_mode((64, 64))
_board = Board(BM.width_in, BM.height_in, 20)

for objective in ST.objectives:
    area = objective.terrain_area
    piece = next(f for f in area.features if f.category != "dense")
    pts = R.objective_outline_points(_board, area)
    c.true(f"{objective.name}: the outline is a closed polygon", len(pts) >= 4)
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

# The margin has to be even all the way round - measured as an AREA, because a
# point-to-vertex distance is not a margin.
_turned = first(o for o in ST.objectives
                if abs(first((f for f in o.terrain_area.features
                              if f.category != "dense"), _FLAT).angle_deg) > 1e-9)
_piece = first((f for f in _turned.terrain_area.features if f.category != "dense")) if _turned else None
c.true("there is a rotated objective to measure the outline margin on",
       _turned is not None and _piece is not None)
_hull = R.objective_outline_points(_board, _turned.terrain_area) if _turned else [(0, 0)] * 4
_area = abs(sum(_hull[i][0] * _hull[(i + 1) % len(_hull)][1]
                - _hull[(i + 1) % len(_hull)][0] * _hull[i][1]
                for i in range(len(_hull)))) / 2
_per_px = _board.in_to_px_len(1.0)
_m = R.OBJECTIVE_OUTLINE_INFLATE_PX / _per_px
_want = (_piece.width_in + 2 * _m) * (_piece.height_in + 2 * _m) * _per_px * _per_px
c.true(f"a rotated outline is the footprint grown evenly on all four sides "
       f"({_area:.0f} px2 against {_want:.0f})", abs(_area - _want) / _want < 0.02)

# The info icon hangs on the outline itself, not on a bounding-box corner out
# in open ground.
for objective in ST.objectives:
    pts = R.objective_outline_points(_board, objective.terrain_area)
    anchor = min(pts, key=lambda p: p[0] + p[1])
    c.true(f"{objective.name}: the icon anchor is a point ON the outline", anchor in pts)


c.finish()
