import math

from game import config  # imports nothing itself, so this cannot cycle
from game import scuttling_walker  # imports nothing itself either


def may_cross_walls(model):
    """Whether the wall-crossing house rule covers this model's owner - see
    config.VEHICLES_CROSS_WALLS / WALL_CROSSING_PLAYERS.

    Deliberately keyed on the OWNER rather than on anything about the model:
    the rule exists to take a handicap off the AI, and the user plays under the
    printed rules unchanged ("für mich als menschlicher spieler soll alles so
    bleiben"). Anything whose owner cannot be determined gets the strict
    answer, so an unowned or duck-typed probe is never accidentally granted a
    permission the human does not have."""
    if not config.VEHICLES_CROSS_WALLS:
        return False
    squad = getattr(model, "squad", None)
    owner = getattr(squad, "owner", None)
    return owner in config.WALL_CROSSING_PLAYERS


EXPOSED = "exposed"  # rule 13.03: traversed without hindrance, only scant cover
LIGHT = "light"      # rule 13.04: provides cover, doesn't slow movement or block sight
DENSE = "dense"      # rule 13.05: blocks movement and can shelter units from sight


class Obstacle:
    """A rectangular piece of terrain, optionally ROTATED about its centre.
    Its `category` (rule 13.02) decides whether it blocks movement and/or line
    of sight - see `blocks_movement_for(model)`/`blocks_line_of_sight`.
    Cover-save benefits (rule 13.08, not given yet) aren't modeled.

    ROTATION, and the two rules that make it safe to add to a shape six
    subsystems already read:

    1. `min_x/max_x/min_y/max_y` are the AXIS-ALIGNED BOUNDING BOX of the
       rotated rectangle, not the rectangle itself. Everything that uses them
       as a cheap conservative PREFILTER (line_of_sight._obstacle_relevant,
       the A* candidate reject) therefore stays correct with no change at all,
       and anything that has not been taught the exact test yet merely blocks
       a little too much rather than answering nonsense.
    2. Every EXACT question is answered by a method here, in the obstacle's
       own frame - `overlaps_circle`, `contains_point`, `blocks_segment`,
       `segment_entry_fraction`, `distance_to_point`, `corners`. Callers ask
       the obstacle instead of passing four numbers to a free function, so
       there is one definition of "what shape is this" rather than six.

    `angle_deg=0.0` (every piece all three shipped maps build) takes a fast
    path that is the PREVIOUS ARITHMETIC VERBATIM, not the general formula
    specialised. That is deliberate: the two are equal in exact arithmetic but
    round differently at the boundary, and stage 1 of this work already lost a
    whole ring of the AI's deployment grid to exactly that (see
    game/deployment.py's PLACEMENT_TOLERANCE_IN). Terrain is measured with the
    same tolerances, so the shipped maps keep their bit-for-bit answers."""

    def __init__(self, x_in, y_in, width_in, height_in, category=DENSE, angle_deg=0.0):
        self.x_in = x_in
        self.y_in = y_in
        self.width_in = width_in
        self.height_in = height_in
        self.category = category
        self.angle_deg = angle_deg
        # An Obstacle is immutable once built (nothing in the codebase ever
        # reassigns x_in/y_in/width_in/height_in), so its edges and its
        # rotation are computed once here rather than recomputed on every
        # overlaps_circle() - which the placement overlay, movement clamping,
        # line of sight and the AI's candidate sweeps all call in tight loops
        # over every obstacle on the board. The min_x/max_x/min_y/max_y
        # properties below stay as the public reading interface.
        self._half_w = width_in / 2
        self._half_h = height_in / 2
        self._axis_aligned = abs(angle_deg) < 1e-9
        radians = math.radians(angle_deg)
        self._cos = math.cos(radians)
        self._sin = math.sin(radians)
        if self._axis_aligned:
            self._min_x = x_in - width_in / 2
            self._max_x = x_in + width_in / 2
            self._min_y = y_in - height_in / 2
            self._max_y = y_in + height_in / 2
        else:
            ex = abs(self._cos) * self._half_w + abs(self._sin) * self._half_h
            ey = abs(self._sin) * self._half_w + abs(self._cos) * self._half_h
            self._min_x, self._max_x = x_in - ex, x_in + ex
            self._min_y, self._max_y = y_in - ey, y_in + ey

    def to_local(self, x_in, y_in):
        """A board point in this obstacle's own frame, where it is axis-aligned
        again - so rotation costs a 6-flop transform and every test below
        reuses the same maths it always used."""
        dx = x_in - self.x_in
        dy = y_in - self.y_in
        return (dx * self._cos + dy * self._sin, -dx * self._sin + dy * self._cos)

    def corners(self):
        """The four corners, in board coordinates, going round the rectangle.
        For a rotated piece these are NOT the bounding box corners, which is
        why the renderer and the AI's corner routing ask for them."""
        out = []
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            lx, ly = sx * self._half_w, sy * self._half_h
            out.append((self.x_in + lx * self._cos - ly * self._sin,
                        self.y_in + lx * self._sin + ly * self._cos))
        return out

    def blocks_movement_for(self, model):
        """Rule 13.05/13.06: Dense terrain is "an obstacle to even the
        largest war machines" - except INFANTRY/BEASTS/SWARM/MOBILE models,
        which can move horizontally through it regardless. Exposed (13.03)
        and Light (13.04) terrain never block movement, for any model.

        The one seam the crossing house rule hangs on (config.
        VEHICLES_CROSS_WALLS): every consumer of "may this model pass through
        that" goes through here - MovementController.clamp_move(),
        pathfinding.blocking_obstacles_for() and the AI's two corner-routing
        helpers - so lifting it here lifts it consistently for the mover, the
        route search and the AI's own geometry at once, instead of the three
        disagreeing about what is passable. What it does NOT touch is where a
        model may END (game/squad.py's model_terrain_violation, rule 13.05)
        or line of sight (blocks_line_of_sight below), both of which stay in
        force. The cost of crossing is charged in
        MovementController._finalize_segment()."""
        if self.category != DENSE:
            return False
        profile = getattr(model, "profile", None)
        if profile is None:
            return True
        if profile.can_move_through_dense_terrain:
            return False
        # The Defiler's Scuttling Walker. Asked HERE, beside the keyword rule,
        # rather than by adding a keyword the datasheet does not print: it is a
        # VEHICLE WALKER, so can_move_through_dense_terrain (which tests
        # INFANTRY/BEASTS/SWARM/MOBILE) is false for it and always will be.
        # This seam is also the one the docstring above calls "every consumer
        # of may this model pass through that", so the mover, the route search
        # and the AI's corner routing all agree about it at once.
        if scuttling_walker.can_cross_terrain(model):
            return False
        return not may_cross_walls(model)

    @property
    def blocks_line_of_sight(self):
        """Rule 13.05: only Dense terrain can "shelter entire squads from
        enemy sight" - Exposed and Light terrain don't block sight at all,
        they only affect cover saves (rule 13.08, not given yet)."""
        return self.category == DENSE

    @property
    def min_x(self):
        return self._min_x

    @property
    def max_x(self):
        return self._max_x

    @property
    def min_y(self):
        return self._min_y

    @property
    def max_y(self):
        return self._max_y

    def overlaps_circle(self, cx, cy, radius):
        # Hot path (see __init__): reads the cached edges directly and does a
        # squared-distance compare, so no property lookups and no sqrt.
        if self._axis_aligned:
            x0, x1 = self._min_x, self._max_x
            y0, y1 = self._min_y, self._max_y
            dx = cx - (x0 if cx < x0 else x1 if cx > x1 else cx)
            dy = cy - (y0 if cy < y0 else y1 if cy > y1 else cy)
            return dx * dx + dy * dy < radius * radius
        # Rotated: the bounding box is a cheap reject first (this is the hot
        # path for the placement overlay, which asks every obstacle on the
        # board per candidate), then the exact test in the local frame.
        if (cx + radius < self._min_x or cx - radius > self._max_x
                or cy + radius < self._min_y or cy - radius > self._max_y):
            return False
        lx, ly = self.to_local(cx, cy)
        dx = lx - (-self._half_w if lx < -self._half_w else self._half_w if lx > self._half_w else lx)
        dy = ly - (-self._half_h if ly < -self._half_h else self._half_h if ly > self._half_h else ly)
        return dx * dx + dy * dy < radius * radius

    def contains_point(self, x_in, y_in, inflate=0.0):
        """Whether the point is inside the rectangle, optionally grown by
        `inflate` on every side.

        The inflation is a SQUARE-cornered grow, not a rounded one, and that is
        load-bearing rather than sloppy: pathfinding's cell test and
        blocks_segment() below have to agree about corners or an
        "individually unblocked" cell produces a segment the continuous check
        rejects (see game/pathfinding.py's own note)."""
        if self._axis_aligned:
            return (self._min_x - inflate <= x_in <= self._max_x + inflate
                    and self._min_y - inflate <= y_in <= self._max_y + inflate)
        lx, ly = self.to_local(x_in, y_in)
        return (abs(lx) <= self._half_w + inflate and abs(ly) <= self._half_h + inflate)

    def blocks_segment(self, p1, p2, inflate=0.0):
        """Whether the segment touches this obstacle, grown by `inflate`.
        Replaces passing min_x/min_y/max_x/max_y to
        geometry.segment_intersects_rect(), which could only ever describe an
        axis-aligned piece."""
        blocked, _ = self.segment_clip(p1, p2, inflate)
        return blocked

    def segment_entry_fraction(self, p1, p2, inflate=0.0):
        """How far along p1->p2 (0..1) travel gets before entering this
        obstacle; 1.0 if it never does."""
        blocked, entry_t = self.segment_clip(p1, p2, inflate)
        return entry_t if blocked else 1.0

    def segment_clip(self, p1, p2, inflate=0.0):
        """(blocked, entry_fraction) - the one place segment-vs-obstacle is
        decided, so line of sight, movement clamping and the AI's routing
        cannot drift apart about it."""
        from game.geometry import segment_rect_clip
        if self._axis_aligned:
            return segment_rect_clip(
                p1, p2,
                self._min_x - inflate, self._min_y - inflate,
                self._max_x + inflate, self._max_y + inflate,
            )
        x1, y1 = p1
        x2, y2 = p2
        # Bounding-box reject before the transform. Line of sight asks this
        # per sample-point PAIR (24x24 of them per check), so the transform is
        # on the hottest path in the renderer-facing code; rejecting a segment
        # that cannot reach this piece at all costs four comparisons instead.
        # Exact as a rejection - the rectangle lies inside its own bounding
        # box - so it can only ever save time, never change an answer.
        # Measured on a fully rotated map 2: 1.81 -> 1.38 ms per line-of-sight
        # check, against 1.30 ms for the same board axis-aligned.
        if (max(x1, x2) < self._min_x - inflate or min(x1, x2) > self._max_x + inflate
                or max(y1, y2) < self._min_y - inflate or min(y1, y2) > self._max_y + inflate):
            return False, 1.0
        # The segment in the obstacle's frame, clipped against the same
        # rectangle it always was. Rotating the SEGMENT rather than trying to
        # describe a rotated rectangle to an axis-aligned clipper is what
        # keeps this one Liang-Barsky implementation for both cases. Inlined
        # rather than calling to_local() twice: two method calls per pair is
        # measurable at this frequency.
        ox, oy, cos_a, sin_a = self.x_in, self.y_in, self._cos, self._sin
        ax, ay = x1 - ox, y1 - oy
        bx, by = x2 - ox, y2 - oy
        hw, hh = self._half_w + inflate, self._half_h + inflate
        return segment_rect_clip(
            (ax * cos_a + ay * sin_a, -ax * sin_a + ay * cos_a),
            (bx * cos_a + by * sin_a, -bx * sin_a + by * cos_a),
            -hw, -hh, hw, hh,
        )

    def route_waypoints(self, from_x, from_y, clearance):
        """Points worth trying as a way past this obstacle, for a mover at
        (from_x, from_y) needing `clearance` from it.

        Four "slide past it" points, whose straight line from the mover runs
        PARALLEL to one of this rectangle's own edges and so cannot cross it
        whichever side the mover is on, plus the four corners pushed outward.
        Both families are built in the obstacle's own frame, which is what
        makes "parallel to its own edge" mean the right thing once the piece
        is rotated - in board axes it would mean nothing.

        It lives here rather than in ai/agent_driver.py because that file
        contains the routing TWICE, in two near-identical helpers, and a
        rotation taught to only one of them is the kind of drift this repo
        keeps having to consolidate."""
        if self._axis_aligned:
            # The previous expressions verbatim, so existing routes do not
            # shift by a rounding step.
            return [
                (from_x, self._min_y - clearance),
                (from_x, self._max_y + clearance),
                (self._min_x - clearance, from_y),
                (self._max_x + clearance, from_y),
            ] + [
                (corner_x + sign_x * clearance, corner_y + sign_y * clearance)
                for corner_x, sign_x in ((self._min_x, -1), (self._max_x, 1))
                for corner_y, sign_y in ((self._min_y, -1), (self._max_y, 1))
            ]
        lx, ly = self.to_local(from_x, from_y)
        local = [
            (lx, -self._half_h - clearance),
            (lx, self._half_h + clearance),
            (-self._half_w - clearance, ly),
            (self._half_w + clearance, ly),
        ] + [
            (sx * (self._half_w + clearance), sy * (self._half_h + clearance))
            for sx in (-1, 1) for sy in (-1, 1)
        ]
        return [self.to_board(px, py) for px, py in local]

    def to_board(self, local_x, local_y):
        """The inverse of to_local()."""
        return (self.x_in + local_x * self._cos - local_y * self._sin,
                self.y_in + local_x * self._sin + local_y * self._cos)

    def distance_to_point(self, x_in, y_in):
        """Edge distance from a board point to this rectangle; 0 inside it."""
        if self._axis_aligned:
            closest_x = max(self._min_x, min(x_in, self._max_x))
            closest_y = max(self._min_y, min(y_in, self._max_y))
            return math.hypot(x_in - closest_x, y_in - closest_y)
        lx, ly = self.to_local(x_in, y_in)
        dx = max(abs(lx) - self._half_w, 0.0)
        dy = max(abs(ly) - self._half_h, 0.0)
        return math.hypot(dx, dy)


class TerrainArea:
    """Rule 13.01/13.02: the footprint/boundary that one or more terrain
    *features* occupy together (an Obstacle is one feature, e.g. one wall -
    a TerrainArea is the whole "terrain area" rules like Benefit of Cover
    (13.08), Hidden (13.09) and Obscuring (13.10) actually check against)."""

    def __init__(self, features):
        self.features = list(features)

    @property
    def has_dense_feature(self):
        return any(f.category == DENSE for f in self.features)

    @property
    def is_obscuring(self):
        """Rule 13.10: a terrain area with a Light or Dense feature in it -
        note an Exposed-only area (e.g. a lone crater) is NOT obscuring."""
        return any(f.category in (LIGHT, DENSE) for f in self.features)

    def contains_point(self, x_in, y_in):
        return any(f.contains_point(x_in, y_in) for f in self.features)

    def overlaps_model(self, model):
        return any(f.overlaps_circle(model.x_in, model.y_in, model.radius_in) for f in self.features)

    def crosses_segment(self, p1, p2):
        return any(f.blocks_segment(p1, p2) for f in self.features)

    def distance_to_point(self, x_in, y_in):
        """Edge distance from (x_in, y_in) to the nearest point of any
        feature in this area - 0 if inside one. Used by rule 12.08's
        Objective Consolidation ("within 3\" of ... objectives")."""
        best = None
        for f in self.features:
            dist = f.distance_to_point(x_in, y_in)
            if best is None or dist < best:
                best = dist
        return best if best is not None else float("inf")

    def distance_to_model(self, model):
        """Like distance_to_point(), but edge-to-edge (accounts for the
        model's own base radius) rather than center-to-edge."""
        return max(0.0, self.distance_to_point(model.x_in, model.y_in) - model.radius_in)

    @property
    def bounding_box(self):
        """(min_x, min_y, max_x, max_y) across every feature - used to draw
        a single outline around the whole area (e.g. for an objective
        marker). Each feature contributes its own bounding box, so this stays
        a correct enclosing rectangle for a rotated piece too, just a looser
        one than its four corners."""
        return (
            min(f.min_x for f in self.features), min(f.min_y for f in self.features),
            max(f.max_x for f in self.features), max(f.max_y for f in self.features),
        )


ALL_RUIN_CORNERS = ("nw", "ne", "sw", "se")

# How thick a ruin wall is. ONE definition rather than a literal on each of
# the four builders below: they all mean the same thing, and four copies of
# a number are four chances for three of them to move and one to stay.
#
# Halved from 0.60" on the user's call ("Die Wände sind insgesamt etwas
# dick. Kannst du die Dicke um 50% reduzieren?"). The walls stay pinned to
# the SAME outer edge - ruin_walls() and l_walls() inset each wall by half
# its own thickness, so a thinner wall grows inward-facing floor rather than
# moving the footprint boundary, and two touching footprints keep touching
# walls (map3 depends on that: its mid-line pair had a 0.15" shooting slit
# closed by butting the footprints together).
WALL_THICKNESS_IN = 0.3


def ruin_walls(x_in, y_in, width_in, height_in, wall_thickness=None, door_width=3.0, category=DENSE, corners=ALL_RUIN_CORNERS):
    """Rule 13.01/13.02: a terrain *area* (the footprint/boundary) is not
    itself one solid obstacle - it's occupied by one or more terrain
    *features*. A ruin's features are its walls; the space between and
    inside them is open floor. This builds the four perimeter walls of a
    rectangular ruin footprint, each with a centered doorway gap, so the
    interior is open (any model can walk in through a doorway) while the
    walls themselves are the actual Dense terrain a model's move can be
    blocked by (or, per rule 13.06, walked straight through if it has the
    INFANTRY/BEASTS/SWARM/MOBILE keyword).

    The doorway in the middle of each edge splits it into two segments, and
    every one of the resulting eight segments runs from a doorway out to
    exactly one corner - so the layout is really four corner "L"s, and
    `corners` selects which of them get built (all four by default). Passing
    a subset is how a footprint keeps some of its walls and loses the rest
    without inventing a second wall layout with different segment lengths."""
    if wall_thickness is None:
        wall_thickness = WALL_THICKNESS_IN
    half_w, half_h = width_in / 2, height_in / 2
    x0, x1 = x_in - half_w, x_in + half_w
    y0, y1 = y_in - half_h, y_in + half_h
    gap = min(door_width, width_in - 2 * wall_thickness, height_in - 2 * wall_thickness)

    def horizontal_wall(y_center, west_corner, east_corner):
        gap_min, gap_max = x_in - gap / 2, x_in + gap / 2
        segments = []
        if west_corner in corners:
            segments.append(Obstacle(x_in=(x0 + gap_min) / 2, y_in=y_center, width_in=gap_min - x0, height_in=wall_thickness, category=category))
        if east_corner in corners:
            segments.append(Obstacle(x_in=(gap_max + x1) / 2, y_in=y_center, width_in=x1 - gap_max, height_in=wall_thickness, category=category))
        return segments

    def vertical_wall(x_center, north_corner, south_corner):
        gap_min, gap_max = y_in - gap / 2, y_in + gap / 2
        segments = []
        if north_corner in corners:
            segments.append(Obstacle(x_in=x_center, y_in=(y0 + gap_min) / 2, width_in=wall_thickness, height_in=gap_min - y0, category=category))
        if south_corner in corners:
            segments.append(Obstacle(x_in=x_center, y_in=(gap_max + y1) / 2, width_in=wall_thickness, height_in=y1 - gap_max, category=category))
        return segments

    walls = []
    walls += horizontal_wall(y0 + wall_thickness / 2, "nw", "ne")  # north wall
    walls += horizontal_wall(y1 - wall_thickness / 2, "sw", "se")  # south wall
    walls += vertical_wall(x0 + wall_thickness / 2, "nw", "sw")    # west wall
    walls += vertical_wall(x1 - wall_thickness / 2, "ne", "se")    # east wall
    return walls


def ruin(x_in, y_in, width_in, height_in, wall_thickness=None, door_width=3.0, wall_category=DENSE, floor_category=LIGHT, corners=ALL_RUIN_CORNERS):
    """A ruin terrain feature as a whole: its footprint isn't just implied
    by where the walls happen to be - it's the rubble-strewn floor the walls
    stand on, occupying the entire area (Light by default: walkable, gives
    cover once 13.08 exists, doesn't block movement or LoS), with the walls
    (ruin_walls(), Dense by default) rising out of it. Returns
    [footprint, *wall_segments] - add every piece to the game state.

    `corners` is passed straight through to ruin_walls(): the footprint is
    unaffected by it, only which of the four corner "L"s of wall are built."""
    footprint = Obstacle(x_in=x_in, y_in=y_in, width_in=width_in, height_in=height_in, category=floor_category)
    return [footprint] + ruin_walls(x_in, y_in, width_in, height_in, wall_thickness, door_width, wall_category, corners)


def l_walls(x_in, y_in, width_in, height_in, facing_x, facing_y, wall_thickness=None, category=DENSE, wall_fraction=2 / 3, h_wall_fraction=None, v_wall_fraction=None, angle_deg=0.0):
    """Two doorless walls on the two sides of the footprint nearest a
    given facing point (default use: the board's center, standing in for
    "faces the enemy" - both players approach from opposite edges, so the
    side of a footprint nearest the board's center is the side nearest
    whichever player is attacking from beyond it). The two walls meet at the
    corner closest to that point, forming an L; the other two sides are left
    completely open (no wall segments at all - not even a doorway), unlike
    ruin_walls()'s all-four-sides-with-a-door layout.

    Each wall only covers `wall_fraction` (default two thirds) of its edge,
    anchored at the shared corner and cut off before reaching the far
    corner - it does not run the full length of the edge.

    `h_wall_fraction`/`v_wall_fraction` override that for one arm alone
    (each falling back to `wall_fraction` when None). The horizontal one
    exists for pieces that have to butt up against a neighbouring feature:
    because each arm grows from the shared corner *toward* the far corner,
    only running it the full length of its edge (1.0) makes it actually reach
    a neighbour standing flush against that far edge - at two thirds it stops
    short and leaves a slot that looks closed on screen but that line of
    sight passes straight through.

    A fraction of 0 omits that arm entirely rather than emitting a
    zero-length obstacle, which is how a piece keeps only one of the two
    walls."""
    if wall_thickness is None:
        wall_thickness = WALL_THICKNESS_IN
    half_w, half_h = width_in / 2, height_in / 2
    # Everything below is computed in the FOOTPRINT'S OWN FRAME (centred on the
    # origin, axis-aligned) and transformed back at the end. For angle_deg=0
    # that transform is the identity plus the footprint's centre, so the walls
    # land exactly where they always did; for a rotated ruin it is what makes
    # its walls turn WITH it instead of staying square to the board.
    angle = math.radians(angle_deg)
    cos_a, sin_a = math.cos(angle), math.sin(angle)

    def to_board(local_x, local_y):
        return (x_in + local_x * cos_a - local_y * sin_a,
                y_in + local_x * sin_a + local_y * cos_a)

    fdx, fdy = facing_x - x_in, facing_y - y_in
    local_facing_x = fdx * cos_a + fdy * sin_a
    local_facing_y = -fdx * sin_a + fdy * cos_a
    x0, x1 = -half_w, half_w
    y0, y1 = -half_h, half_h
    near_x1 = local_facing_x >= 0.0
    near_y1 = local_facing_y >= 0.0
    # Inset by half the wall thickness (same as ruin_walls()) so each wall
    # sits just inside the footprint's own boundary rather than centered on
    # it - centering on the edge would have it protrude half its thickness
    # outside the footprint, which can then overlap unrelated neighboring
    # terrain that was measured to sit right up against this footprint's edge.
    y_wall_center = (y1 - wall_thickness / 2) if near_y1 else (y0 + wall_thickness / 2)
    x_wall_center = (x1 - wall_thickness / 2) if near_x1 else (x0 + wall_thickness / 2)
    # Each wall's length is only wall_fraction of the edge, anchored at the
    # shared corner (x_wall_center, y_wall_center) and cut off toward the far
    # corner - hence the horizontal wall's own center offsets from x_in
    # (and likewise the vertical wall's from y_in) rather than sitting on it.
    h_length = width_in * (wall_fraction if h_wall_fraction is None else h_wall_fraction)
    h_center_x = (x1 - h_length / 2) if near_x1 else (x0 + h_length / 2)
    v_length = height_in * (wall_fraction if v_wall_fraction is None else v_wall_fraction)
    v_center_y = (y1 - v_length / 2) if near_y1 else (y0 + v_length / 2)
    walls = []
    if h_length > 0:
        wx, wy = to_board(h_center_x, y_wall_center)
        walls.append(Obstacle(x_in=wx, y_in=wy, width_in=h_length, height_in=wall_thickness,
                              category=category, angle_deg=angle_deg))
    if v_length > 0:
        wx, wy = to_board(x_wall_center, v_center_y)
        walls.append(Obstacle(x_in=wx, y_in=wy, width_in=wall_thickness, height_in=v_length,
                              category=category, angle_deg=angle_deg))
    return walls


def ruin_l(x_in, y_in, width_in, height_in, facing_x, facing_y, wall_thickness=None, wall_category=DENSE, floor_category=LIGHT, wall_fraction=2 / 3, h_wall_fraction=None, v_wall_fraction=None, angle_deg=0.0):
    """Like ruin(), but with l_walls() instead of ruin_walls() for the wall
    features: an L of two partial walls (see l_walls()) facing
    (facing_x, facing_y) instead of doored walls on all four sides.
    Returns [footprint, *wall_segments]."""
    footprint = Obstacle(x_in=x_in, y_in=y_in, width_in=width_in, height_in=height_in,
                         category=floor_category, angle_deg=angle_deg)
    return [footprint] + l_walls(x_in, y_in, width_in, height_in, facing_x, facing_y, wall_thickness,
                                 wall_category, wall_fraction, h_wall_fraction, v_wall_fraction,
                                 angle_deg=angle_deg)
