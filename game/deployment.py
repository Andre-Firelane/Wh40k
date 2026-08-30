from game import shapes

# A base sitting EXACTLY on the zone boundary is wholly within it, and the
# deployment AI's candidate grid deliberately puts points there (its rows start
# exactly one base radius inside each edge, so the frontmost offered spot is the
# frontmost legal one - see ai/deployment_ai._candidate_points). A signed
# distance reaches that same boundary by a different arithmetic route than the
# rectangle comparison it replaces, so the two disagree in the last bits, and
# 103 of 210 such points flipped from legal to illegal - the whole outer ring of
# the grid. This tolerance is a millionth of a thousandth of an inch: far below
# anything the board means, far above the rounding.
PLACEMENT_TOLERANCE_IN = 1e-9


class DeploymentZone:
    """Rule 03.01: the area within which a player sets up their army before
    the battle.

    Built either from axis-aligned rectangles (the authoring form the three
    shipped maps use) or from a `game/shapes.py` Shape - which is what lets a
    layout have a rotated, diagonal or corner zone with a circular hole around
    the board centre. All three questions below are answered by ONE signed
    distance, so a new zone form needs no new code here; see the shapes module
    docstring for why that beats approximating with a list of rectangles, and
    for the exactness of each combinator.

    Enforced by game/pregame.py's PregameController during the pre-game
    deployment sequence (a unit must be set up wholly within its owner's
    zone, unless INFILTRATORS 24.20 says otherwise) and by
    game/ingress.py's IngressController for rule 20.04's "not in your
    opponent's deployment zone before battle round 3"."""

    def __init__(self, owner, rects=None, shape=None):
        if (rects is None) == (shape is None):
            raise ValueError("DeploymentZone takes exactly one of rects= or shape=")
        self.owner = owner
        # `rects` is kept because it is how this zone was WRITTEN DOWN, and
        # tests read it to place a model at a known spot. It is NOT the shape:
        # a shape-built zone has none, so nothing outside this class may use it
        # to answer a geometry question - ask signed_distance() instead.
        # test_deployment_shapes.py guards that.
        self.rects = list(rects) if rects is not None else []
        self.shape = shapes.rects_to_shape(self.rects) if shape is None else shape

    def signed_distance(self, x_in, y_in):
        """Inches from the zone boundary: positive inside, negative outside."""
        return self.shape.signed_distance(x_in, y_in)

    def bounding_box(self):
        return self.shape.bounding_box()

    def centroid(self, board_box=None):
        return self.shape.centroid(board_box=board_box)

    def contains_point(self, x_in, y_in):
        return self.shape.signed_distance(x_in, y_in) >= -PLACEMENT_TOLERANCE_IN

    def contains_circle(self, x_in, y_in, radius_in):
        """Rule 03.01's "wholly within": the model's whole base has to be
        inside the zone, not just its centre.

        For a rectangle list this is unchanged from the hand-written version
        it replaces - "some single rectangle holds the whole base", seam
        conservatism included (shapes.Union's max() is exactly that test). For
        a zone written as an intersection of half-planes there is no seam to
        be conservative about, so the same call is simply exact."""
        return self.shape.signed_distance(x_in, y_in) >= radius_in - PLACEMENT_TOLERANCE_IN

    def distance_to_point(self, x_in, y_in):
        """0 if the point is inside the zone, otherwise the shortest distance
        to its nearest edge - what rule 24.20 (INFILTRATORS) measures when it
        says "more than 8" horizontally from your opponent's deployment
        zone".

        Outside a CORNER of a shape built as an intersection this UNDERSTATES
        the distance (see game/shapes.py): it measures to the nearest
        constraint line rather than to the corner point. Every rule that reads
        it treats a smaller number as "closer to that zone", so the error can
        only ever refuse a placement, never allow an illegal one - which is why
        this stays the answer the rules get. Anything that RANKS by distance
        instead of gating on it wants true_distance_to_point() below."""
        return max(0.0, -self.shape.signed_distance(x_in, y_in))

    def true_distance_to_point(self, x_in, y_in, board_box, step_in=0.5):
        """The real Euclidean distance to the nearest point of the zone.

        Sampled, because for an intersection with a hole in it there is no
        closed form - and deliberately NOT what distance_to_point() returns,
        which is conservative by design. The two differ only outside a corner,
        and only a corner-shaped zone has one: on map 3 the conservative answer
        makes an objective 10.6" away look 4.5" away, which is enough to pick
        the wrong expansion objective (game/secondary_missions.py).

        The sample grid is built once per zone and reused - a zone never moves
        once the map is built."""
        grid = getattr(self, "_sample_grid", None)
        if grid is None:
            min_x, min_y, max_x, max_y = self.bounding_box() or board_box
            min_x, min_y = max(min_x, board_box[0]), max(min_y, board_box[1])
            max_x, max_y = min(max_x, board_box[2]), min(max_y, board_box[3])
            steps_x = max(1, int((max_x - min_x) / step_in))
            steps_y = max(1, int((max_y - min_y) / step_in))
            grid = [(min_x + (max_x - min_x) * i / steps_x,
                     min_y + (max_y - min_y) * j / steps_y)
                    for i in range(steps_x + 1) for j in range(steps_y + 1)]
            grid = [p for p in grid if self.contains_point(*p)]
            self._sample_grid = grid
        if not grid:
            return self.distance_to_point(x_in, y_in)
        if self.contains_point(x_in, y_in):
            return 0.0
        return min((x_in - gx) ** 2 + (y_in - gy) ** 2 for gx, gy in grid) ** 0.5


def zone_for(zones, owner):
    """That player's own deployment zone, or None if the map defines none."""
    for zone in zones or ():
        if zone.owner == owner:
            return zone
    return None


def enemy_zones(zones, owner):
    """Every deployment zone that is NOT this player's. A list rather than a
    single zone because nothing guarantees a two-player board here, and rule
    24.20 says "your opponent's deployment zone" - all of them have to be
    cleared, not just the first one found."""
    return [zone for zone in zones or () if zone.owner != owner]
