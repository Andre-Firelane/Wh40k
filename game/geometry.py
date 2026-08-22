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
    before entering an obstacle, inflated by inflate_radius on every side."""
    min_t = 1.0
    for obstacle in obstacles:
        blocked, entry_t = segment_rect_clip(
            p1, p2,
            obstacle.min_x - inflate_radius, obstacle.min_y - inflate_radius,
            obstacle.max_x + inflate_radius, obstacle.max_y + inflate_radius,
        )
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
