"""Board regions, given as SIGNED DISTANCES - the shape vocabulary that
deployment zones (rule 03.01) are built from.

WHY A SIGNED DISTANCE AND NOT A POLYGON. A deployment zone is asked exactly
three questions, and all three are the same question about a distance:

    contains_point(p)        -> is p inside?                sd(p) >= 0
    contains_circle(p, r)    -> is the whole BASE inside?   sd(p) >= r   (03.01
                                "wholly within")
    distance_to_point(p)     -> how far outside is p?       max(0, -sd(p))
                                (rule 24.20 INFILTRATORS' 8")

So one function per primitive answers the whole API, for any shape, and the
"wholly within" test is EXACT rather than approximated - which is the thing a
polygon representation would have made hard and a list of axis-aligned
rectangles could not do at all.

WHY NOT KEEP APPROXIMATING WITH RECTANGLES. Measured on a diagonal corner zone
(44"x44", cut on x+y >= 30 with a 9" circular hole around the board centre),
comparing the legally deployable area of a staircase of axis-aligned strips
against the exact shape:

      strips        25mm base     50mm base     grav tank
       4              101 %          96 %          84 %
       8               95 %          76 %          33 %
      16               71 %          22 %           0 %
      32               10 %           0 %           0 %

Refining makes it STRICTLY WORSE, because DeploymentZone.contains_circle()
needs ONE SINGLE rectangle to hold the whole base - thinner strips hold none.
There is no "just use more rectangles" fallback here the way there was for
terrain (game/maps.py's map 2 note), and a circular hole cannot be expressed
at all. Hence real shapes.

EXACTNESS, stated per combinator rather than assumed:

  * Intersection uses min(). INSIDE the shape that is exact, and it is the
    only place the deployment rules read a magnitude that has to be right
    (03.01's "wholly within"). OUTSIDE, past a CORNER where two constraints
    meet, min() reports the distance to the nearer edge LINE rather than to
    the corner point, so it understates how far outside a point is. Every
    consumer reads that as "closer to that zone than it really is", which
    refuses an INFILTRATORS placement (24.20's 8") rather than allowing an
    illegal one - the same safe direction the old
    DeploymentZone.contains_circle() docstring already argued for. Measured
    against a brute-force 720-sample rim test over 60000 random (base,
    position) pairs on exactly the shape above: 60000 identical, 0 wrongly
    allowed.

  * Union uses max(). For a union of rectangles that reproduces the previous
    behaviour BIT FOR BIT: max_i sd_i(p) >= r  <=>  some single rectangle
    contains the whole base, which is what the old code tested. So the three
    shipped maps keep the answers they had, including the seam conservatism
    the old docstring documented.
"""

import math


class Shape:
    """A region of the board. Positive inside, negative outside, magnitude in
    inches from the boundary."""

    def signed_distance(self, x_in, y_in):
        raise NotImplementedError

    def bounding_box(self):
        """(min_x, min_y, max_x, max_y) in inches, or None when the shape is
        unbounded (a bare HalfPlane is). Callers that need to SAMPLE a shape
        (the renderer's outline, the deployment AI's candidate grid) fall back
        to the board rectangle when this is None, which is always safe: the
        board is the only place anything can stand anyway."""
        return None

    # -- conveniences shared by every shape ---------------------------------

    def contains_point(self, x_in, y_in):
        return self.signed_distance(x_in, y_in) >= 0.0

    def contains_circle(self, x_in, y_in, radius_in):
        return self.signed_distance(x_in, y_in) >= radius_in

    def distance_to_point(self, x_in, y_in):
        return max(0.0, -self.signed_distance(x_in, y_in))

    def sampling_boxes(self, inset_in=0.0, fallback_box=None):
        """The rectangle(s) a caller should lay a candidate grid over so that
        every point where a base of `inset_in` fits is inside one of them.

        Shrinking the bounding box by the inset is always valid, and the proof
        is one line: if signed_distance(p) >= inset then the whole disc of that
        radius around p is inside the shape, hence inside its bounding box,
        hence p is at least `inset` from every side of that box. So nothing
        legal is ever cut away - the grid may only cover some ground the caller
        then rejects.

        For an axis-aligned rectangle the shrunk box IS the legal region, so a
        grid laid over it is exactly the grid the rectangle-only code laid
        before this existed - which is what keeps the AI's deployment
        measurements comparable. Union hands back one box PER PART for the same
        reason: a two-rectangle zone keeps being gridded per rectangle."""
        box = self.bounding_box() or fallback_box
        if box is None:
            return []
        min_x, min_y, max_x, max_y = box
        min_x, min_y = min_x + inset_in, min_y + inset_in
        max_x, max_y = max_x - inset_in, max_y - inset_in
        if max_x < min_x or max_y < min_y:
            return []
        return [(min_x, min_y, max_x, max_y)]

    def centroid(self, board_box=None, samples=64):
        """A representative interior point, sampled rather than derived, so it
        works for every shape including intersections with holes.

        Cached: it is read per frame by the AI's forward axis and by the
        territory split, and the shape never changes once built."""
        cached = getattr(self, "_centroid_cache", None)
        if cached is not None:
            return cached
        box = self.bounding_box() or board_box
        if box is None:
            return None
        min_x, min_y, max_x, max_y = box
        sx = sy = 0.0
        hits = 0
        for i in range(samples):
            x = min_x + (max_x - min_x) * (i + 0.5) / samples
            for j in range(samples):
                y = min_y + (max_y - min_y) * (j + 0.5) / samples
                if self.signed_distance(x, y) >= 0.0:
                    sx += x
                    sy += y
                    hits += 1
        result = (sx / hits, sy / hits) if hits else ((min_x + max_x) / 2, (min_y + max_y) / 2)
        self._centroid_cache = result
        return result


class Rect(Shape):
    """An axis-aligned or ROTATED rectangle, centre-based - the same
    (x_in, y_in, width_in, height_in) shape game/terrain.py's Obstacle uses,
    plus an angle. `angle_deg` turns it counter-clockwise about its centre;
    0.0 is exactly the old axis-aligned rectangle and takes the same fast
    path, so every zone the three shipped maps define is unchanged."""

    def __init__(self, x_in, y_in, width_in, height_in, angle_deg=0.0):
        self.x_in = x_in
        self.y_in = y_in
        self.width_in = width_in
        self.height_in = height_in
        self.angle_deg = angle_deg
        self._hw = width_in / 2.0
        self._hh = height_in / 2.0
        # cos/sin cached here, not recomputed per query: signed_distance() is
        # on the deployment overlay's per-frame path and the AI's candidate
        # sweeps, the same reason Obstacle caches its four edges.
        radians = math.radians(angle_deg)
        self._cos = math.cos(radians)
        self._sin = math.sin(radians)
        self._axis_aligned = abs(angle_deg) < 1e-9

    def signed_distance(self, x_in, y_in):
        dx = x_in - self.x_in
        dy = y_in - self.y_in
        if not self._axis_aligned:
            # Into the rectangle's own frame, where it IS axis-aligned again -
            # so rotation costs a 6-flop transform and reuses the same maths
            # below rather than needing any new geometry.
            dx, dy = dx * self._cos + dy * self._sin, -dx * self._sin + dy * self._cos
        ax = abs(dx) - self._hw
        ay = abs(dy) - self._hh
        # Exact box distance, one expression for both cases: inside, the hypot
        # term is 0 and min(max(ax,ay),0) is the (negative) distance to the
        # nearest edge; outside, the min term is 0.
        return -(math.hypot(max(ax, 0.0), max(ay, 0.0)) + min(max(ax, ay), 0.0))

    def bounding_box(self):
        if self._axis_aligned:
            return (self.x_in - self._hw, self.y_in - self._hh,
                    self.x_in + self._hw, self.y_in + self._hh)
        ex = abs(self._cos) * self._hw + abs(self._sin) * self._hh
        ey = abs(self._sin) * self._hw + abs(self._cos) * self._hh
        return (self.x_in - ex, self.y_in - ey, self.x_in + ex, self.y_in + ey)


class HalfPlane(Shape):
    """Everything on one side of a straight line: nx*x + ny*y >= offset, with
    (nx, ny) a unit normal pointing INTO the region.

    This is the primitive that makes a diagonal or corner deployment zone
    possible at all, and it also subsumes rotation - four half-planes are a
    rotated rectangle. Prefer `through()` for map authoring: naming the two
    points the edge runs between and one point on the keeping side is
    traceable back to a measurement, where a bare normal vector is not."""

    def __init__(self, nx, ny, offset):
        length = math.hypot(nx, ny)
        if length < 1e-12:
            raise ValueError("HalfPlane needs a non-zero normal")
        self.nx = nx / length
        self.ny = ny / length
        self.offset = offset / length

    @classmethod
    def through(cls, x0_in, y0_in, x1_in, y1_in, inside_x_in, inside_y_in):
        """The half-plane whose edge runs through (x0,y0)-(x1,y1), keeping
        whichever side (inside_x, inside_y) is on."""
        dx, dy = x1_in - x0_in, y1_in - y0_in
        nx, ny = -dy, dx
        if nx * (inside_x_in - x0_in) + ny * (inside_y_in - y0_in) < 0:
            nx, ny = -nx, -ny
        return cls(nx, ny, nx * x0_in + ny * y0_in)

    def signed_distance(self, x_in, y_in):
        return self.nx * x_in + self.ny * y_in - self.offset

    def bounding_box(self):
        """Half-infinite when the edge is axis-aligned, None otherwise.

        A half-plane is unbounded, so reporting None would be honest - but
        FOUR of them are a rectangle, and an Intersection can only see that if
        each one says which side it closes. Without this, a zone written as
        quadrant-plus-board-edges reported no box at all and every caller that
        SAMPLES it fell back to the whole board: the deployment AI's exposure
        probe then found zero points inside it and silently measured nothing.
        A slanted edge still returns None - it bounds the region in a direction
        no axis-aligned box can express, and a larger box is always safe."""
        inf = float("inf")
        if abs(self.ny) < 1e-12:
            return (self.offset / self.nx, -inf, inf, inf) if self.nx > 0                 else (-inf, -inf, self.offset / self.nx, inf)
        if abs(self.nx) < 1e-12:
            return (-inf, self.offset / self.ny, inf, inf) if self.ny > 0                 else (-inf, -inf, inf, self.offset / self.ny)
        return None


class Disc(Shape):
    """The inside of a circle. Wrap it in `Outside` for the hole a mission
    layout punches around the board centre."""

    def __init__(self, x_in, y_in, radius_in):
        self.x_in = x_in
        self.y_in = y_in
        self.radius_in = radius_in

    def signed_distance(self, x_in, y_in):
        return self.radius_in - math.hypot(x_in - self.x_in, y_in - self.y_in)

    def bounding_box(self):
        r = self.radius_in
        return (self.x_in - r, self.y_in - r, self.x_in + r, self.y_in + r)


class Outside(Shape):
    """The complement of another shape - `Outside(Disc(cx, cy, 9.0))` is "the
    circle in the middle, cut out", written the way the layout reads.

    Deliberately its own class rather than an `inside=False` flag on Disc: a
    flag would have to be repeated on every primitive that might ever be
    subtracted, and would read as a property of the circle instead of as the
    subtraction it is."""

    def __init__(self, shape):
        self.shape = shape

    def signed_distance(self, x_in, y_in):
        return -self.shape.signed_distance(x_in, y_in)


def _combine_boxes(boxes, intersect):
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None
    if intersect:
        min_x = max(b[0] for b in boxes)
        min_y = max(b[1] for b in boxes)
        max_x = min(b[2] for b in boxes)
        max_y = min(b[3] for b in boxes)
        if max_x < min_x or max_y < min_y:
            return None
        # Half-planes contribute half-infinite boxes (see HalfPlane); if the
        # parts together still leave a side open, there is no box to report and
        # the caller falls back to the board, which is what None means here.
        box = (min_x, min_y, max_x, max_y)
        return box if all(v == v and abs(v) != float("inf") for v in box) else None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


class Intersection(Shape):
    """Every part at once - the shape a real deployment zone is written as:
    a couple of half-planes for the diagonal and the board edges, plus an
    Outside(Disc) for the centre hole. See the module docstring for why min()
    is exact for convex parts and conservative (never permissive) otherwise."""

    def __init__(self, parts):
        self.parts = list(parts)

    def signed_distance(self, x_in, y_in):
        # No parts = no constraint = everywhere, the identity for min().
        return min((p.signed_distance(x_in, y_in) for p in self.parts), default=float("inf"))

    def bounding_box(self):
        # Only the BOUNDED parts constrain the box; an unbounded half-plane
        # contributes nothing, which is right - the board clamps it.
        return _combine_boxes([p.bounding_box() for p in self.parts], intersect=True)


class Union(Shape):
    """Any part - what a list of rectangles becomes. max() reproduces the old
    "any SINGLE rectangle contains the whole base" reading exactly; see the
    module docstring."""

    def __init__(self, parts):
        self.parts = list(parts)

    def signed_distance(self, x_in, y_in):
        # No parts = nothing is inside, the identity for max(). That settles a
        # question the two previous copies of this code ANSWERED DIFFERENTLY:
        # DeploymentZone.distance_to_point() returned 0.0 for a zone with no
        # rectangles ("you are inside it"), secondary_missions.zone_distance()
        # returned inf ("it is nowhere near you"). -inf here makes it inf, the
        # honest one: an empty zone contains nothing, so nothing is in it and
        # rule 24.20's "more than 8 inches from your opponent's zone" is
        # satisfied everywhere rather than nowhere. No shipped map defines an
        # empty zone, so this cannot change a game today.
        return max((p.signed_distance(x_in, y_in) for p in self.parts), default=float("-inf"))

    def bounding_box(self):
        return _combine_boxes([p.bounding_box() for p in self.parts], intersect=False)

    def sampling_boxes(self, inset_in=0.0, fallback_box=None):
        boxes = []
        for part in self.parts:
            boxes.extend(part.sampling_boxes(inset_in, fallback_box))
        return boxes


def rects_to_shape(rects):
    """The authoring form the three shipped maps use - a list of
    (x, y, width, height) centre-based axis-aligned rectangles - as a Shape."""
    parts = [Rect(x, y, w, h) for x, y, w, h in rects]
    if len(parts) == 1:
        return parts[0]
    return Union(parts)
