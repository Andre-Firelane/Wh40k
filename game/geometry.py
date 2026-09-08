def segment_rect_clip(p1, p2, min_x, min_y, max_x, max_y):
    """Liang-Barsky segment-vs-AABB clipping.

    Returns (blocked, entry_t): blocked is True if the segment touches or
    crosses the rectangle (including lying fully inside it); entry_t is the
    fraction along the segment (0..1) where it first enters the rectangle
    (meaningless when blocked is False).
    """
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1

    t0, t1 = 0.0, 1.0
    for p, q in (
        (-dx, x1 - min_x),
        (dx, max_x - x1),
        (-dy, y1 - min_y),
        (dy, max_y - y1),
    ):
        if p == 0:
            if q < 0:
                return False, 1.0
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False, 1.0
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return False, 1.0
                if r < t1:
                    t1 = r
    return True, t0


def segment_intersects_rect(p1, p2, min_x, min_y, max_x, max_y):
    blocked, _ = segment_rect_clip(p1, p2, min_x, min_y, max_x, max_y)
    return blocked


def max_unblocked_fraction(p1, p2, obstacles, inflate_radius=0.0):
    """How far (as a 0..1 fraction of the segment) p1->p2 can be traveled
    before entering an obstacle, inflated by inflate_radius on every side.

    The inflation is SQUARE-cornered (a rectangle grown on each side), not a
    swept circle - game/pathfinding.py's cell test grows the same way on
    purpose, because the two have to agree about corners."""
    min_t = 1.0
    for obstacle in obstacles:
        # Asked of the obstacle rather than clipped against its bounding box
        # here: a rotated piece answers in its own frame, and this stays the
        # one arithmetic every consumer of "does that block this line" shares.
        blocked, entry_t = obstacle.segment_clip(p1, p2, inflate_radius)
        if blocked and entry_t < min_t:
            min_t = entry_t
    return max(0.0, min_t)


def segment_circle_entry_fraction(p1, p2, center, radius):
    """How far along p1->p2 (as a 0..1 fraction) the segment travels before
    entering a circle of the given radius around center. Returns 1.0 if it
    never does. Used to stop a moving model's base at the edge of another
    model's base (rule 03.01: bases can't be moved through enemy models)."""
    x1, y1 = p1
    x2, y2 = p2
    cx, cy = center
    dx, dy = x2 - x1, y2 - y1
    fx, fy = x1 - cx, y1 - cy

    a = dx * dx + dy * dy
    if a == 0:
        return 0.0 if (fx * fx + fy * fy) <= radius * radius else 1.0

    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - radius * radius

    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return 1.0

    sqrt_disc = discriminant ** 0.5
    t1 = (-b - sqrt_disc) / (2 * a)
    t2 = (-b + sqrt_disc) / (2 * a)
    if t2 < 0 or t1 > 1:
        return 1.0
    return max(0.0, t1)


def max_unblocked_fraction_models(p1, p2, models, inflate_radius=0.0):
    """Same idea as max_unblocked_fraction, but the blockers are other
    models' circular bases instead of rectangular terrain."""
    min_t = 1.0
    for model in models:
        entry_t = segment_circle_entry_fraction(
            p1, p2, (model.x_in, model.y_in), model.radius_in + inflate_radius
        )
        if entry_t < min_t:
            min_t = entry_t
    return max(0.0, min_t)


def convex_hull(points):
    """Monotone chain. Returns the hull in order; a degenerate input (all
    points collinear or identical) comes back as-is so the caller still has
    something to draw.

    Lives here rather than in game/renderer.py, which had it privately while
    it was the only caller. The second caller is ai/agent_driver.py, deciding
    whether a plan has ordered a unit to a point inside its own footprint, and
    it cannot import the renderer: that module pulls pygame and runs on the
    per-frame draw path. game/renderer.py imports the name from here, so every
    pixel test of the objective outline is unchanged by construction.

    The epsilon is not decoration: a ruin's walls are inset by half their
    thickness so their outer edge lies EXACTLY on the footprint's, and after
    the same inflation those corners are collinear with it. Tested against a
    bare 0 the cross product comes out at ~1e-15 rather than 0 and the wall
    corners survive as vertices, which turns a rectangle into a six-sided
    outline that is a rectangle everywhere except in the vertex list."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    eps = 1e-9

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) \
                    - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0]) <= eps:
                out.pop()
            out.append(p)
        return out
    hull = half(pts)[:-1] + half(pts[::-1])[:-1]
    return hull or pts


def point_inside_hull(point, points):
    """Is `point` inside the convex hull of `points` - i.e. are the points
    standing AROUND it rather than off to one side?

    The question ai/agent_driver.py asks about a turn plan's coordinate: a
    unit ordered "toward" a spot in the middle of its own formation has
    nowhere to go, because the models on the far side of it would have to walk
    backwards into their own squadmates. Measured on the reported board - all
    74 models where the log leaves them - a 21-model blob ordered to a point
    1.97" away and inside itself moved 0.00", while the same blob on the same
    board ordered to points outside its formation moved 2.50" and 4.72".

    A point ON the hull boundary counts as inside: a unit whose front rank
    stands exactly on the ordered spot has arrived at it. Fewer than three
    distinct points cannot enclose anything, so a one- or two-model unit is
    never "standing around" a spot - which is right: those can always simply
    walk to it."""
    hull = convex_hull(list(points))
    if len(hull) < 3:
        return False
    eps = 1e-9
    px, py = point
    for i, (ax, ay) in enumerate(hull):
        bx, by = hull[(i + 1) % len(hull)]
        # Monotone chain returns counter-clockwise, so an interior point is
        # left of (or on) every directed edge.
        if (bx - ax) * (py - ay) - (by - ay) * (px - ax) < -eps:
            return False
    return True
