import math

from game.geometry import segment_circle_entry_fraction

SAMPLE_POINTS = 24


def _circle_points(cx, cy, radius, num_points=SAMPLE_POINTS):
    return [
        (
            cx + radius * math.cos(2 * math.pi * i / num_points),
            cy + radius * math.sin(2 * math.pi * i / num_points),
        )
        for i in range(num_points)
    ]


def _blocked_by_obstacle(p1, p2, obstacle):
    if not obstacle.blocks_line_of_sight:
        return False  # rule 13.03/13.04: Exposed/Light terrain doesn't block sight
    return obstacle.blocks_segment(p1, p2)


def _blocked_by_model(p1, p2, model):
    return segment_circle_entry_fraction(p1, p2, (model.x_in, model.y_in), model.radius_in) < 1.0


def _bounding_box(token_a, token_b):
    """The rectangle that contains EVERY possible sample point on either
    token's base rim - any p1 on token_a's rim satisfies token_a.x_in -
    token_a.radius_in <= p1.x <= token_a.x_in + token_a.radius_in (and
    likewise for y), so this is a safe superset of the bounding box of any
    single p1-p2 segment used below."""
    min_x = min(token_a.x_in - token_a.radius_in, token_b.x_in - token_b.radius_in)
    max_x = max(token_a.x_in + token_a.radius_in, token_b.x_in + token_b.radius_in)
    min_y = min(token_a.y_in - token_a.radius_in, token_b.y_in - token_b.radius_in)
    max_y = max(token_a.y_in + token_a.radius_in, token_b.y_in + token_b.radius_in)
    return min_x, min_y, max_x, max_y


def _obstacle_relevant(obstacle, box):
    """A conservative PREFILTER, and it stays correct for a rotated obstacle
    without changing: min_x..max_y is that piece's axis-aligned bounding box
    (see game/terrain.py's Obstacle), so anything this rejects cannot touch
    the rectangle inside it either. It may keep a piece the exact test then
    discards, which costs a little time and no correctness."""
    min_x, min_y, max_x, max_y = box
    return not (obstacle.max_x < min_x or obstacle.min_x > max_x or obstacle.max_y < min_y or obstacle.min_y > max_y)


def _model_relevant(model, box):
    min_x, min_y, max_x, max_y = box
    r = model.radius_in
    return not (model.x_in + r < min_x or model.x_in - r > max_x or model.y_in + r < min_y or model.y_in - r > max_y)


def _relevant_obstacles(obstacles, box):
    """Rule 13.05/13.11 perf: a real Dense-terrain-heavy, ~130-model board
    made has_line_of_sight() itself the bottleneck (user report: the game
    still hangs for several seconds when choosing a shooting target) - every
    one of its O(sample_points^2) point pairs re-tested EVERY obstacle/
    blocking model on the whole board, even ones nowhere near the two
    tokens actually being checked. Any obstacle/model entirely outside
    _bounding_box() (computed once per call, not once per point pair)
    cannot possibly intersect ANY p1-p2 segment this call will ever test -
    see _bounding_box()'s docstring - so filtering here first is a pure,
    lossless optimization, not an approximation: it changes which
    candidates the O(sample_points^2) loop below even considers, never
    the actual blocked/not-blocked outcome for any of them."""
    return [o for o in obstacles if _obstacle_relevant(o, box)]


def _relevant_models(models, box):
    return [m for m in models if _model_relevant(m, box)]


def _obscuring_areas_between(terrain_areas, token_a, token_b):
    """Rule 13.10: which terrain areas can possibly obscure the sightline
    between these two specific models - i.e. areas with a Light or Dense
    feature that neither model is standing within. This only depends on
    token_a/token_b (not on any particular sample point pair), so it's
    computed once per has_line_of_sight()/model_fully_visible() call rather
    than redundantly inside the O(sample_points^2) point-pair loop - that
    used to make every single LoS check re-run overlaps_model() (itself a
    loop over every feature in the area) for every one of the ~24*24 sample
    pairs, which is where nearly all the cost of a Benefit-of-Cover-heavy
    scene like this one's terrain-covered board was going."""
    return [
        area for area in terrain_areas
        if area.is_obscuring and not area.overlaps_model(token_a) and not area.overlaps_model(token_b)
    ]


OBSTACLE, MODEL, AREA = "obstacle", "model", "area"


def _first_blocker(p1, p2, obstacles, blockers, obscuring_areas, memo=None):
    """WHAT blocks the p1-p2 sightline, as a (kind, object) pair, or None if
    nothing does - the three separate any() checks this replaces only ever
    said whether something did.

    `memo` is the pair this same call returned for the PREVIOUS point pair,
    and it is tested first. That is a pure reordering: per point pair the
    answer is an OR over three side-effect-free predicates applied to a fixed
    candidate set, and an OR does not care about order, so this cannot change
    any answer - the same argument _relevant_obstacles() makes for the
    bounding-box prefilter, one layer further in. What it buys is that a wall
    standing across the sightline is found at position 1 instead of position n
    for each of the ~576 point pairs it blocks. Measured on the shipped maps
    (fuzz-compared against the pre-memo version, see test_line_of_sight.py):
    4.6x/5.0x/7.8x on map1/map2/map3 in the blocked case, 1.67x in the mixed
    case, never slower - a clear sightline returns on its very first point
    pair either way, so the extra test costs nothing there. The memo stays in
    its own list as well, so a miss tests it twice; that is cheaper than an
    `is` comparison per list element and is what keeps "never slower" true.

    DO NOT CARRY A MEMO ACROSS has_line_of_sight() CALLS. It is the obvious
    next step - eligible_targets() asks about the same wall a thousand times
    in a row - and it is wrong for two of the three kinds:

      * _blocking_models() excludes PER PAIR: both tokens' own units, and by
        house rule the whole observing ARMY. A model memoised from another
        pair may be one that is not allowed to block for this pair, which
        would silently delete the "friendly units never block" house rule.
      * _obscuring_areas_between() excludes areas either token is STANDING
        in, likewise per pair.

    Only OBSTACLEs are pair-independent (_blocked_by_obstacle reads nothing
    but the obstacle and the segment), so a cross-call memo would have to be
    restricted to those."""
    if memo is not None:
        kind, candidate = memo
        if kind == OBSTACLE:
            if _blocked_by_obstacle(p1, p2, candidate):
                return memo
        elif kind == MODEL:
            if _blocked_by_model(p1, p2, candidate):
                return memo
        elif candidate.crosses_segment(p1, p2):
            return memo
    for obstacle in obstacles:
        if _blocked_by_obstacle(p1, p2, obstacle):
            return (OBSTACLE, obstacle)
    for model in blockers:
        if _blocked_by_model(p1, p2, model):
            return (MODEL, model)
    for area in obscuring_areas:
        if area.crosses_segment(p1, p2):
            return (AREA, area)
    return None


def _owner_of(token):
    """Which player a model belongs to, or None for the duck-typed probe
    stand-ins (ai/observation.py's _ProbePoint, ai/agent_driver.py's
    _ExposureProbe) that ask "what would a model standing HERE see" - a probe
    without a squad has no army, so no model counts as friendly to it."""
    return getattr(getattr(token, "squad", None), "owner", None)


def _blocking_models(token_a, token_b, all_tokens):
    """Rule 06.01: every other model can block line of sight, except models
    in the observing model's own unit and models in the observed model's
    unit, which are ignored.

    HOUSE RULE (user request: "blockieren befreundete einheiten sichtlinie?
    das sollte nicht so sein"): models belonging to the OBSERVER'S OWN ARMY
    never block either, not just its own unit. Enemy models still block, so
    screening a target behind another unit keeps working - only your own
    army stops shooting itself in the back."""
    observer_owner = _owner_of(token_a)
    return [
        model for model in all_tokens
        if model is not token_a and model is not token_b
        and model.squad is not token_a.squad and model.squad is not token_b.squad
        and not (observer_owner is not None and _owner_of(model) == observer_owner)
    ]


def has_line_of_sight(token_a, token_b, obstacles, all_tokens=(), terrain_areas=(), sample_points=SAMPLE_POINTS):
    """True if any point on token_a's base rim can see any point on token_b's
    base rim, i.e. at least one 1mm-wide connecting line avoids every
    obstacle, every blocking model (rule 06.01), and every obscuring terrain
    area (rule 13.10).

    sample_points trades accuracy for speed: this is an O(sample_points^2)
    check per call, and it's called for every pair of tokens the "currently
    visible to the selected model" board highlight considers, every frame -
    lower it there (main.py) to keep movement smooth; leave it at the
    default for anything that actually resolves a rule (shooting targeting,
    Benefit of Cover), where precision matters more than raw speed."""
    points_a = _circle_points(token_a.x_in, token_a.y_in, token_a.radius_in, sample_points)
    points_b = _circle_points(token_b.x_in, token_b.y_in, token_b.radius_in, sample_points)
    box = _bounding_box(token_a, token_b)
    obstacles = _relevant_obstacles(obstacles, box)
    blockers = _relevant_models(_blocking_models(token_a, token_b, all_tokens), box)
    obscuring_areas = _obscuring_areas_between(terrain_areas, token_a, token_b)

    memo = None
    for pa in points_a:
        for pb in points_b:
            memo = _first_blocker(pa, pb, obstacles, blockers, obscuring_areas, memo)
            if memo is None:
                return True
    return False


def _facing_points(observer, target, num_points=SAMPLE_POINTS):
    """The half of target's base rim whose outward normal faces observer -
    the only part of target for which "blocked" can mean anything other than
    target's own bulk getting in the way of itself."""
    dx = observer.x_in - target.x_in
    dy = observer.y_in - target.y_in
    points = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        nx, ny = math.cos(angle), math.sin(angle)
        if nx * dx + ny * dy >= 0:
            points.append((target.x_in + target.radius_in * nx, target.y_in + target.radius_in * ny))
    return points


def _point_reachable(point, from_points, obstacles, blockers, obscuring_areas, memo=None):
    """`memo` is a one-cell list so the last blocker survives ACROSS calls
    within one model_fully_visible() - unlike has_line_of_sight(), which walks
    its point pairs in one loop and can keep a plain local. It has to: this is
    the all() half of Benefit of Cover, whose expensive case is "one wall hides
    every facing point", and a memo that reset per facing point would be
    thrown away exactly when it is worth most. Safe for the same reason as in
    _first_blocker(): the candidate lists are computed once per
    model_fully_visible() call, so every point pair here shares one pair of
    tokens - see that docstring for why a memo must NOT cross that boundary."""
    for origin in from_points:
        blocker = _first_blocker(origin, point, obstacles, blockers, obscuring_areas,
                                 memo[0] if memo else None)
        if blocker is None:
            return True
        if memo is not None:
            memo[0] = blocker
    return False


def model_visible(observer, target, obstacles, all_tokens=(), terrain_areas=()):
    """Rule 06.01: any part of target is visible to observer."""
    return has_line_of_sight(observer, target, obstacles, all_tokens, terrain_areas)


def model_fully_visible(observer, target, obstacles, all_tokens=(), terrain_areas=()):
    """Rule 06.01: every part of target facing observer is visible - i.e. the
    only thing blocking any part of target is target itself (its own far
    side, which we never even look at here)."""
    points_a = _circle_points(observer.x_in, observer.y_in, observer.radius_in)
    facing_points = _facing_points(observer, target)
    if not facing_points:
        return False
    box = _bounding_box(observer, target)
    obstacles = _relevant_obstacles(obstacles, box)
    blockers = _relevant_models(_blocking_models(observer, target, all_tokens), box)
    obscuring_areas = _obscuring_areas_between(terrain_areas, observer, target)
    memo = [None]
    return all(
        _point_reachable(pb, points_a, obstacles, blockers, obscuring_areas, memo)
        for pb in facing_points
    )


def unit_visible(observer, target_squad, obstacles, all_tokens=(), terrain_areas=()):
    """Rule 06.01: a unit is visible if any model in it is visible."""
    return any(model_visible(observer, model, obstacles, all_tokens, terrain_areas) for model in target_squad.models)


def unit_fully_visible(observer, target_squad, obstacles, all_tokens=(), terrain_areas=()):
    """Rule 06.01: a unit is fully visible if every model in it is fully
    visible (other models of that same unit are ignored as blockers while
    checking this, per _blocking_models)."""
    return all(model_fully_visible(observer, model, obstacles, all_tokens, terrain_areas) for model in target_squad.models)
