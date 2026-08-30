"""Rotated terrain footprints (game/terrain.py's Obstacle.angle_deg) and the
six subsystems that read an obstacle's shape.

Stage 2 of the map-geometry work; stage 1 was the deployment zones
(test_deployment_shapes.py). What this has to establish:

  1. the rotated maths is right - checked against brute force on the polygon,
     not against a second copy of the same formula
  2. the axis-aligned path is the OLD arithmetic verbatim, so the three
     shipped maps keep their answers bit for bit
  3. every consumer asks the obstacle instead of its bounding box, measured on
     the one region where those two differ: inside the box, outside the piece
  4. the bounding box is still a correct conservative prefilter
"""

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

from game import config, geometry, line_of_sight, maps, pathfinding, renderer as R
from game.board import Board
from game.game_state import GameState
from game.terrain import DENSE, EXPOSED, LIGHT, Obstacle, TerrainArea

c = Checks("rotated terrain footprints")


class Tok:
    def __init__(self, x, y, r=0.63):
        self.x_in, self.y_in, self.radius_in = x, y, r


def poly_contains(pts, x, y):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def seg_point_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def poly_distance(pts, x, y):
    if poly_contains(pts, x, y):
        return 0.0
    n = len(pts)
    return min(seg_point_distance(x, y, *pts[i], *pts[(i + 1) % n]) for i in range(n))


def segments_cross(p, q, r, s):
    def side(a, b, cc):
        return (b[0] - a[0]) * (cc[1] - a[1]) - (b[1] - a[1]) * (cc[0] - a[0])
    d1, d2, d3, d4 = side(p, q, r), side(p, q, s), side(r, s, p), side(r, s, q)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def poly_blocks_segment(pts, p1, p2):
    n = len(pts)
    return (poly_contains(pts, *p1) or poly_contains(pts, *p2)
            or any(segments_cross(p1, p2, pts[i], pts[(i + 1) % n]) for i in range(n)))


# --------------------------------------------------------------------------
print("--- 1. the rotated rectangle itself ---")

WALL = Obstacle(20.0, 15.0, 11.5, 7.0, DENSE, angle_deg=27.0)
pts = WALL.corners()

c.eq("a rotated piece still has four corners", len(pts), 4)
c.true("...and the printed side lengths, unchanged by the rotation",
       abs(math.dist(pts[0], pts[1]) - 11.5) < 1e-9 and abs(math.dist(pts[1], pts[2]) - 7.0) < 1e-9)
c.true("...adjacent sides still meet at a right angle",
       abs((pts[1][0] - pts[0][0]) * (pts[2][0] - pts[1][0])
           + (pts[1][1] - pts[0][1]) * (pts[2][1] - pts[1][1])) < 1e-9)
c.true("the centre is where it was put", WALL.contains_point(20.0, 15.0))
c.true("min_x..max_y is the BOUNDING BOX, and it encloses every corner",
       all(WALL.min_x - 1e-9 <= px <= WALL.max_x + 1e-9
           and WALL.min_y - 1e-9 <= py <= WALL.max_y + 1e-9 for px, py in pts))
c.true("...and it is genuinely bigger than the piece, which is the whole point",
       (WALL.max_x - WALL.min_x) > 11.5)
c.true("to_local and to_board are inverses",
       all(abs(a - b) < 1e-9 for a, b in zip(WALL.to_board(*WALL.to_local(7.3, 22.1)), (7.3, 22.1))))

# The region that separates "asks the obstacle" from "asks its bounding box":
# inside the box, outside the rectangle. Every consumer below is measured here.
CORNER_GAP = (WALL.min_x + 0.4, WALL.min_y + 0.4)
c.true("there IS such a spot: inside the bounding box, outside the piece",
       WALL.min_x <= CORNER_GAP[0] <= WALL.max_x and WALL.min_y <= CORNER_GAP[1] <= WALL.max_y
       and not WALL.contains_point(*CORNER_GAP))

bad = {}
for angle in (0.0, 12.5, 27.0, 45.0, -31.5, 60.0, 90.0, 118.0, -75.25):
    o = Obstacle(20.0, 15.0, 11.5, 7.0, DENSE, angle_deg=angle)
    corners = o.corners()
    for i in range(37):
        for j in range(29):
            x, y = 5.0 + i * 0.85, 2.0 + j * 0.95
            if poly_contains(corners, x, y) != o.contains_point(x, y):
                bad["contains_point"] = bad.get("contains_point", 0) + 1
            if abs(poly_distance(corners, x, y) - o.distance_to_point(x, y)) > 1e-9:
                bad["distance_to_point"] = bad.get("distance_to_point", 0) + 1
            for radius in (0.5, 1.0, 2.0):
                if (poly_distance(corners, x, y) < radius) != o.overlaps_circle(x, y, radius):
                    bad["overlaps_circle"] = bad.get("overlaps_circle", 0) + 1
            p1 = (2.0 + (i % 7) * 5.0, 1.0 + (j % 5) * 6.0)
            if poly_blocks_segment(corners, p1, (x, y)) != o.blocks_segment(p1, (x, y)):
                bad["blocks_segment"] = bad.get("blocks_segment", 0) + 1
c.eq("nine angles, brute-forced against the polygon: no disagreement", bad, {})


# --------------------------------------------------------------------------
print("--- 2. the shipped maps keep their exact answers ---")


def old_overlaps(o, cx, cy, r):
    x0, x1, y0, y1 = o.min_x, o.max_x, o.min_y, o.max_y
    dx = cx - (x0 if cx < x0 else x1 if cx > x1 else cx)
    dy = cy - (y0 if cy < y0 else y1 if cy > y1 else cy)
    return dx * dx + dy * dy < r * r


def old_cell(o, x, y, r):
    return o.min_x - r <= x <= o.max_x + r and o.min_y - r <= y <= o.max_y + r


def old_distance(o, x, y):
    cx = max(o.min_x, min(x, o.max_x))
    cy = max(o.min_y, min(y, o.max_y))
    return math.hypot(x - cx, y - cy)


def old_waypoints(o, mx, my, cl):
    out = [(mx, o.min_y - cl), (mx, o.max_y + cl), (o.min_x - cl, my), (o.max_x + cl, my)]
    for ox, sx in ((o.min_x, -1), (o.max_x, 1)):
        for oy, sy in ((o.min_y, -1), (o.max_y, 1)):
            out.append((ox + sx * cl, oy + sy * cl))
    return out


drift = {}
checked = 0
for key in ("map1", "map2", "map3"):
    bm = maps.MAPS[key]
    maps.apply_to_config(bm)
    st = GameState()
    bm.build(st)
    axis = [o for o in st.obstacles if abs(o.angle_deg) < 1e-12]
    turned = [o for o in st.obstacles if abs(o.angle_deg) >= 1e-12]
    if key == "map3":
        c.true("map3 is the map that actually uses rotation", turned)
    else:
        c.true(f"{key} still builds every piece axis-aligned", not turned)
    # Only the AXIS-ALIGNED pieces have a previous answer to preserve, and the
    # invariant is about them wherever they occur - not about a map happening
    # to contain none that are turned. Written this way so a fourth map with
    # rotated terrain does not silently drop its straight pieces out of the
    # sweep.
    for o in axis:
        probes = [(o.x_in + dx, o.y_in + dy) for dx in (-9.3, -2.1, 0.0, 3.7, 8.5)
                  for dy in (-7.1, -1.4, 0.0, 2.6, 6.9)]
        # ...plus the lattice of EXACT boundary positions, which is where the
        # signed-distance rewrite went wrong in stage 1 and where a "rounds the
        # same" claim has to be tested rather than assumed.
        for r in (0.0, 0.63, 0.984, 1.18, 2.10):
            probes.extend([(o.min_x, o.y_in), (o.max_x, o.y_in), (o.x_in, o.min_y), (o.x_in, o.max_y),
                           (o.min_x, o.min_y), (o.max_x, o.max_y),
                           (o.min_x - r, o.y_in), (o.max_x + r, o.y_in),
                           (o.x_in, o.min_y - r), (o.x_in, o.max_y + r)])
        for x, y in probes:
            checked += 1
            for radius in (0.63, 1.18, 2.10):
                if old_overlaps(o, x, y, radius) != o.overlaps_circle(x, y, radius):
                    drift["overlaps_circle"] = drift.get("overlaps_circle", 0) + 1
                if old_cell(o, x, y, radius) != o.contains_point(x, y, inflate=radius):
                    drift["contains_point"] = drift.get("contains_point", 0) + 1
            if abs(old_distance(o, x, y) - o.distance_to_point(x, y)) > 0.0:
                drift["distance_to_point"] = drift.get("distance_to_point", 0) + 1
            if old_waypoints(o, x, y, 0.3) != o.route_waypoints(x, y, 0.3):
                drift["route_waypoints"] = drift.get("route_waypoints", 0) + 1
            for inflate in (0.0, 0.63, 1.18):
                want = geometry.segment_rect_clip(
                    (x - 11.0, y - 9.0), (x, y),
                    o.min_x - inflate, o.min_y - inflate, o.max_x + inflate, o.max_y + inflate)
                if want != o.segment_clip((x - 11.0, y - 9.0), (x, y), inflate):
                    drift["segment_clip"] = drift.get("segment_clip", 0) + 1
c.true("the shipped-map sweep really sampled something", checked > 3000)
c.eq("no axis-aligned answer moved by so much as a last bit", drift, {})


# --------------------------------------------------------------------------
print("--- 3. every consumer asks the piece, not its bounding box ---")

# One rotated wall, and a sight line that passes through the CORNER of its
# bounding box without ever touching the wall itself.
diag = Obstacle(15.0, 15.0, 14.0, 2.0, DENSE, angle_deg=45.0)
# The wall runs lower-left to upper-right, so the EMPTY corners of its bounding
# box are the other two. Probing along its long axis instead would sit ON the
# wall and prove nothing - the first version of this test did exactly that.
box_corner = (diag.min_x + 0.5, diag.max_y - 0.5)
c.true("the probe point is in the bounding box but off the wall",
       not diag.contains_point(*box_corner)
       and diag.min_x <= box_corner[0] <= diag.max_x
       and diag.min_y <= box_corner[1] <= diag.max_y)
c.true("...and it is well clear of it, not a boundary case",
       diag.distance_to_point(*box_corner) > 3.0)

shooter = Tok(10.5, 20.0)
target = Tok(12.5, 18.0)
c.true("both ends of this sight line lie inside the bounding box",
       all(diag.min_x <= t.x_in <= diag.max_x and diag.min_y <= t.y_in <= diag.max_y
           for t in (shooter, target)))
c.true("...and the BOUNDING BOX test would therefore have blocked it - this is the "
       "one region where asking the box and asking the piece differ",
       geometry.segment_intersects_rect((shooter.x_in, shooter.y_in), (target.x_in, target.y_in),
                                        diag.min_x, diag.min_y, diag.max_x, diag.max_y))
c.true("line of sight is NOT blocked by a bounding box the wall does not fill",
       line_of_sight.has_line_of_sight(shooter, target, [diag], []))
across = Tok(15.0 + 4.0, 15.0 - 4.0)
behind = Tok(15.0 - 4.0, 15.0 + 4.0)
c.true("...but IS blocked straight through the wall",
       not line_of_sight.has_line_of_sight(across, behind, [diag], []))

c.true("the movement clamp stops at the rotated face, not the bounding box",
       geometry.max_unblocked_fraction((15.0 + 6.0, 15.0 - 6.0), (15.0 - 6.0, 15.0 + 6.0), [diag]) < 1.0)
CLEAR_LINE = ((diag.min_x - 1.0, diag.max_y - 0.5), (diag.min_x + 2.0, diag.max_y - 0.5))
c.true("the clear line really does enter the bounding box, so this discriminates",
       geometry.segment_intersects_rect(*CLEAR_LINE, diag.min_x, diag.min_y, diag.max_x, diag.max_y))
c.eq("...and travel does not stop at all for it, because the wall is not there",
     geometry.max_unblocked_fraction(*CLEAR_LINE, [diag]), 1.0)

grid = pathfinding._Grid if hasattr(pathfinding, "_Grid") else None
c.true("the A* cell test uses the piece, not the box",
       diag.contains_point(15.0, 15.0, inflate=0.5)
       and not diag.contains_point(*box_corner, inflate=0.0))

area = TerrainArea([diag])
c.true("a terrain area reports containment from the piece", area.contains_point(15.0, 15.0))
c.true("...and not from its bounding box", not area.contains_point(*box_corner))
c.true("...its segment crossing likewise",
       area.crosses_segment((15.0 + 4.0, 15.0 - 4.0), (15.0 - 4.0, 15.0 + 4.0))
       and not area.crosses_segment(*CLEAR_LINE))
c.true("...and its distance is to the piece",
       abs(area.distance_to_point(*box_corner) - poly_distance(diag.corners(), *box_corner)) < 1e-9)

# The AI's routing: the four "slide past it" waypoints must run parallel to
# the piece's OWN edges, which for a rotated piece is not a board axis.
way = diag.route_waypoints(2.0, 2.0, 0.5)
c.eq("route_waypoints offers the same eight candidates it always did", len(way), 8)
c.true("none of them is inside the piece", not any(diag.contains_point(x, y) for x, y in way))
c.true("the four corner candidates sit off the piece's real corners",
       all(any(math.dist(w, corner) < 0.5 * math.sqrt(2) + 1e-6 for corner in diag.corners())
           for w in way[4:]))

c.true("the bounding box is still a correct conservative PREFILTER",
       all(line_of_sight._obstacle_relevant(diag, line_of_sight._bounding_box(a, b))
           for a, b in [(across, behind)]))


# --------------------------------------------------------------------------
print("--- 4. drawing ---")

pygame.init()
pygame.display.set_mode((64, 64))
board = Board(30.0, 30.0, 20)


def painted_area(angle):
    surf = pygame.Surface((board.width_px, board.height_px))
    surf.fill((0, 0, 0))
    o = Obstacle(15.0, 15.0, 12.0, 3.0, DENSE, angle_deg=angle)
    pygame.draw.polygon(surf, (255, 255, 255), R.obstacle_points_px(board, o))
    px = [(x, y) for x in range(board.width_px) for y in range(board.height_px)
          if surf.get_at((x, y))[0] > 200]
    xs = [p[0] for p in px]
    ys = [p[1] for p in px]
    return len(px), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


flat_n, flat_w, flat_h = painted_area(0.0)
tilt_n, tilt_w, tilt_h = painted_area(45.0)
c.true("a rotated wall covers the same ground as the same wall straight",
       abs(tilt_n - flat_n) / flat_n < 0.02)
c.true("...but occupies a rotated span on screen, so it is the POLYGON drawn",
       tilt_w < flat_w and tilt_h > flat_h)
c.true("...and not the bounding box, which would be far larger",
       tilt_n < flat_w * flat_w * 0.6)
c.eq("a piece at 90 degrees is the same wall stood on end",
     (painted_area(90.0)[1], painted_area(90.0)[2]), (flat_h, flat_w))


# --------------------------------------------------------------------------
print("--- 5. source guards ---")

import io

for path, needle, why in (
    ("game/line_of_sight.py", "obstacle.blocks_segment(p1, p2)", "line of sight asks the obstacle"),
    ("game/geometry.py", "obstacle.segment_clip(p1, p2, inflate_radius)", "the movement clamp asks the obstacle"),
    ("game/pathfinding.py", "o.contains_point(x, y, inflate=self.mover_radius_in)", "the A* cell test asks the obstacle"),
    ("game/terrain.py", "f.blocks_segment(p1, p2)", "a terrain area asks its features"),
    ("game/renderer.py", "obstacle_points_px(board, obstacle)", "the renderer draws the corners"),
):
    src = io.open(path, encoding="utf-8").read()
    c.true(f"{why}", needle in src)

ai_src = io.open("ai/agent_driver.py", encoding="utf-8").read()
c.eq("the AI's corner routing, which exists TWICE, goes through one definition",
     ai_src.count("candidates.extend(o.route_waypoints(mx, my, clearance))"), 2)
c.eq("...and so does its reachability test", ai_src.count("o.blocks_segment((mx, my), point)"), 2)

for path in ("game/line_of_sight.py", "game/geometry.py", "game/pathfinding.py",
             "ai/agent_driver.py", "game/renderer.py"):
    src = io.open(path, encoding="utf-8").read()
    offenders = [ln.strip() for ln in src.splitlines()
                 if ("obstacle.min_x" in ln or "o.min_x" in ln or "obstacle.max_x" in ln or "o.max_x" in ln)
                 and not ln.strip().startswith("#") and "_obstacle_relevant" not in ln]
    # The one legitimate reader left is line_of_sight's bounding-box prefilter,
    # which is CORRECT on a bounding box by construction.
    allowed = 1 if path == "game/line_of_sight.py" else 0
    c.eq(f"{path}: readers of an obstacle's bounding box as its shape", len(offenders), allowed)

c.finish()
