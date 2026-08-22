from game import config  # imports nothing itself, so this cannot cycle


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
    """A rectangular piece of terrain. Its `category` (rule 13.02) decides
    whether it blocks movement and/or line of sight - see
    `blocks_movement_for(model)`/`blocks_line_of_sight`. Cover-save benefits
    (rule 13.08, not given yet) aren't modeled."""

    def __init__(self, x_in, y_in, width_in, height_in, category=DENSE):
        self.x_in = x_in
        self.y_in = y_in
        self.width_in = width_in
        self.height_in = height_in
        self.category = category
        # An Obstacle is immutable once built (nothing in the codebase ever
        # reassigns x_in/y_in/width_in/height_in), so its edges are computed
        # once here rather than recomputed by four property calls on every
        # overlaps_circle() - which the placement overlay, movement clamping,
        # line of sight and the AI's candidate sweeps all call in tight loops
        # over every obstacle on the board. The min_x/max_x/min_y/max_y
        # properties below stay as the public reading interface.
        self._min_x = x_in - width_in / 2
        self._max_x = x_in + width_in / 2
        self._min_y = y_in - height_in / 2
        self._max_y = y_in + height_in / 2

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
        x0, x1 = self._min_x, self._max_x
        y0, y1 = self._min_y, self._max_y
        dx = cx - (x0 if cx < x0 else x1 if cx > x1 else cx)
        dy = cy - (y0 if cy < y0 else y1 if cy > y1 else cy)
        return dx * dx + dy * dy < radius * radius


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
        return any(f.min_x <= x_in <= f.max_x and f.min_y <= y_in <= f.max_y for f in self.features)

    def overlaps_model(self, model):
        return any(f.overlaps_circle(model.x_in, model.y_in, model.radius_in) for f in self.features)

    def crosses_segment(self, p1, p2):
        from game.geometry import segment_intersects_rect
        return any(segment_intersects_rect(p1, p2, f.min_x, f.min_y, f.max_x, f.max_y) for f in self.features)

    def distance_to_point(self, x_in, y_in):
        """Edge distance from (x_in, y_in) to the nearest point of any
        feature in this area - 0 if inside one. Used by rule 12.08's
        Objective Consolidation ("within 3\" of ... objectives")."""
        best = None
        for f in self.features:
            closest_x = max(f.min_x, min(x_in, f.max_x))
            closest_y = max(f.min_y, min(y_in, f.max_y))
            dx = x_in - closest_x
            dy = y_in - closest_y
            dist = (dx * dx + dy * dy) ** 0.5
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
        marker), since our terrain areas are made of axis-aligned rects."""
        return (
            min(f.min_x for f in self.features), min(f.min_y for f in self.features),
            max(f.max_x for f in self.features), max(f.max_y for f in self.features),
        )


ALL_RUIN_CORNERS = ("nw", "ne", "sw", "se")


def ruin_walls(x_in, y_in, width_in, height_in, wall_thickness=0.6, door_width=3.0, category=DENSE, corners=ALL_RUIN_CORNERS):
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


def ruin(x_in, y_in, width_in, height_in, wall_thickness=0.6, door_width=3.0, wall_category=DENSE, floor_category=LIGHT, corners=ALL_RUIN_CORNERS):
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


def l_walls(x_in, y_in, width_in, height_in, facing_x, facing_y, wall_thickness=0.6, category=DENSE, wall_fraction=2 / 3, h_wall_fraction=None, v_wall_fraction=None):
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
    half_w, half_h = width_in / 2, height_in / 2
    x0, x1 = x_in - half_w, x_in + half_w
    y0, y1 = y_in - half_h, y_in + half_h
    near_x1 = facing_x >= x_in
    near_y1 = facing_y >= y_in
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
        walls.append(Obstacle(x_in=h_center_x, y_in=y_wall_center, width_in=h_length, height_in=wall_thickness, category=category))
    if v_length > 0:
        walls.append(Obstacle(x_in=x_wall_center, y_in=v_center_y, width_in=wall_thickness, height_in=v_length, category=category))
    return walls


def ruin_l(x_in, y_in, width_in, height_in, facing_x, facing_y, wall_thickness=0.6, wall_category=DENSE, floor_category=LIGHT, wall_fraction=2 / 3, h_wall_fraction=None, v_wall_fraction=None):
    """Like ruin(), but with l_walls() instead of ruin_walls() for the wall
    features: an L of two partial walls (see l_walls()) facing
    (facing_x, facing_y) instead of doored walls on all four sides.
    Returns [footprint, *wall_segments]."""
    footprint = Obstacle(x_in=x_in, y_in=y_in, width_in=width_in, height_in=height_in, category=floor_category)
    return [footprint] + l_walls(x_in, y_in, width_in, height_in, facing_x, facing_y, wall_thickness, wall_category, wall_fraction, h_wall_fraction, v_wall_fraction)
