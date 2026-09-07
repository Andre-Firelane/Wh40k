"""What a line-formation drag produced, measured - the half both controllers
share.

The gesture exists in two phases with genuinely different rules underneath:
MovementController charges every model's walk against its own remaining
movement, SetupController has no budget at all. But the QUESTION the player is
asking is identical in both - "how wide did that make it, and is the result
legal?" - so the measuring lives here and each controller only supplies its own
clamp.

WHY THE READOUT IS NOT OPTIONAL. The drag is deliberately NOT clamped against
rule 09.02's 9" spread (user decision: "ziehen lassen, Confirm lehnt ab"). That
is only a fair deal if the player can see the limit coming, so this reports the
spread as a NUMBER that climbs rather than as a breach that appears - and, more
useful still, the set of frontages that are legal at all, swept once when the
gesture starts.

WHY THE SPREAD IS MEASURED AFTER THE CLAMP. Requested and achieved are not the
same block: in the Movement phase clamp_move() stops a model at a wall, an
enemy base, the board edge or its own budget, so the line the player drew is
frequently not the line the unit forms. Reporting the requested spread would be
a green readout over a formation Confirm will reject - this repo's error class
6 (a success reported for work that did not happen) turned inside out.
"""

from game import formation_layout
from game.coherency import connected_groups
from game.squad import spread_headroom

# How far a model may sit from its requested slot and still count as having
# reached it. Generous enough to absorb the clamp's own OBSTACLE_PULLBACK_IN
# (0.01") and float noise, tight enough that a model held up by anything real
# is counted as short.
REACHED_TOLERANCE_IN = 0.05


class LineDragInfo:
    """One frame's answer, for the on-screen readout. Deliberately NOT put into
    MovementController.errors: a live '7.3" of 9.0", fine' is not an error, and
    mixing the two would make the error box lie."""

    __slots__ = ("frontage", "ranks", "length_in", "short", "groups",
                 "widest_in", "limit_in", "legal_frontages")

    def __init__(self, frontage, ranks, length_in, short, groups,
                 widest_in, limit_in, legal_frontages):
        self.frontage = frontage
        self.ranks = ranks
        self.length_in = length_in
        self.short = short              # models that could not reach their slot
        self.groups = groups            # connected components, i.e. 1 = coherent
        self.widest_in = widest_in      # ACHIEVED spread, not the requested one
        self.limit_in = limit_in        # MAX_SPREAD_IN, or None where the house rule lifted it
        self.legal_frontages = legal_frontages

    @property
    def over_limit(self):
        return self.limit_in is not None and self.widest_in > self.limit_in

    @property
    def split(self):
        """Rule 09.02's other half: the unit is in more than one piece. A
        GENERATED line is always one group (see line_positions()), so this can
        only become true when a clamp held someone back - which makes it the
        most direct warning available that the drawn line is not the block."""
        return self.groups > 1


def legal_frontage_window(squad, start_in, end_in, origins=None,
                          gap_in=formation_layout.LINE_GAP_IN):
    """Which frontages would keep this unit inside rule 09.02's 9" spread, as a
    tuple - or () when the limit does not apply to its owner.

    Swept ONCE when the gesture starts rather than per frame: the answer is
    invariant under the drag, because rotating and sliding a rigid block does
    not change any pairwise distance. It has to be swept against the real
    `origins` rather than read off a table, because which rank the widest model
    lands in depends on where the unit is standing (see line_positions()).

    This is the number that turns "Confirm rejects" from arbitrary into
    foreseeable: measured, a 20-model unit is legal only from 3 to 8 wide, i.e.
    across roughly 2.7" to 9.5" of drag length. Without it the player has to
    discover that by being refused."""
    headroom = spread_headroom(squad)
    if headroom is None:
        return ()
    _, limit = headroom
    n = len(squad.models)
    if n <= 1:
        return tuple(range(1, n + 1))
    saved = [(m.x_in, m.y_in) for m in squad.models]
    legal = []
    try:
        for frontage in range(1, n + 1):
            targets = formation_layout.line_positions(
                squad, start_in, end_in, depth_toward=_centroid(origins),
                origins=origins, frontage=frontage, gap_in=gap_in,
            )
            for model, target in zip(squad.models, targets):
                model.x_in, model.y_in = target
            pair = _widest(squad)
            if pair <= limit:
                legal.append(frontage)
    finally:
        # The sweep MOVES the models to measure them. Restoring in a finally is
        # not defensive tidiness: this runs on the press, before the player has
        # committed to anything, and leaving a unit in the last frontage tried
        # would silently teleport it.
        for model, (x, y) in zip(squad.models, saved):
            model.x_in, model.y_in = x, y
    return tuple(legal)


def measure(squad, targets, length_in, frontage, ranks, legal_frontages):
    """Describe the block the unit ACTUALLY formed, given what was asked for.

    `targets` are the requested slots; the models are already standing wherever
    their controller's clamp let them get to."""
    short = 0
    for model, target in zip(squad.models, targets):
        if target is None:
            continue
        dx = model.x_in - target[0]
        dy = model.y_in - target[1]
        if dx * dx + dy * dy > REACHED_TOLERANCE_IN ** 2:
            short += 1
    headroom = spread_headroom(squad)
    return LineDragInfo(
        frontage=frontage,
        ranks=ranks,
        length_in=length_in,
        short=short,
        groups=len(connected_groups(squad.models)) if squad.models else 0,
        widest_in=_widest(squad),
        limit_in=None if headroom is None else headroom[1],
        legal_frontages=legal_frontages,
    )


def _centroid(points):
    if not points:
        return None
    return (sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points))


def _widest(squad):
    from game.squad import widest_pair
    pair = widest_pair(squad.models)
    return 0.0 if pair is None else pair[0]
