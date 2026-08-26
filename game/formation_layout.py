"""Packing a squad's models onto legal ground around a point.

Lifted out of ai/agent_driver.py's _ingress_pack_positions(), which is where
this geometry grew up - but it is engine geometry, not an AI judgement, and it
now has two callers on either side of that line:

  * the AI, arriving from Strategic Reserves (20.04) or deploying in the
    pre-game (03.01), which wants the block packed AWAY from the enemy;
  * the human, dropping a whole unit at once with "Place as Block" on
    (game/setup.py), which wants exactly the same shape without any of the
    threat reasoning.

Duplicating it would have meant two ring generators drifting apart, and having
game/setup.py import ai/ would invert this project's dependency direction. So
the pure part lives here and takes `base_angle` as a plain argument; deciding
WHICH way to face stays with the caller."""

import math

from game import config, front_rank
from game.squad import COHERENCY_RANGE_IN, max_model_radius

# Lateral spacing between packed models - matches the deployment scene's own
# spacing, and the floor under the base-derived step below.
MODEL_GAP_IN = 1.5
PACK_RINGS = 4


def packed_spread(squad):
    """How wide this unit is when squeezed as tightly as the rules allow, as an
    edge-to-edge span - i.e. the SMALLEST footprint it can have, not the one it
    happens to have now.

    Needed because hiding a big unit behind terrain usually means compressing
    it (user: "um groessere einheiten hinter gelaende zu verstecken, muss man
    sie manchmal richtig quetschen und den footprint minimieren"). Judging a
    piece of cover against the unit's CURRENT sprawl answers the wrong
    question: measured on map 2, testing the live footprint left every one of
    fourteen units with no usable cover at all, while several of them fit
    easily once packed.

    Derived rather than searched, so it costs nothing to ask: n bases at the
    smallest legal pitch, hex-packed, expressed as the edge span of a circle of
    the same area. Checked against what pack_positions() actually produces -
    for the 20-strong mob this gives 5.44", which is exactly the figure the
    packer lands on for it on clear ground."""
    models = squad.models
    if len(models) < 2:
        return 0.0
    smallest = min(m.radius_in for m in models)
    pitch = 2 * smallest + 0.05  # the overlap bound _first_legal_slot() enforces
    radius = math.sqrt(len(models) * pitch * pitch * 0.866 / math.pi)
    return max(0.0, 2 * radius - 2 * smallest)


def packed_radius(squad):
    """The radius of the disc a tightly packed `squad` occupies, bases
    included - what a piece of cover has to be able to hide."""
    if not squad.models:
        return 0.0
    return 0.5 * packed_spread(squad) + max(m.radius_in for m in squad.models)


def on_board(x_in, y_in, radius_in):
    return (
        radius_in <= x_in <= config.BOARD_WIDTH_IN - radius_in
        and radius_in <= y_in <= config.BOARD_HEIGHT_IN - radius_in
    )


def ring_candidates(origin_x, origin_y, step, base_angle, rings=PACK_RINGS,
                    inner_radius=None):
    """The drop point, then concentric rings outwards, each ring's angles
    ordered by how close they are to `base_angle` - so the block grows on the
    chosen side first and stays as near the drop point as the ground allows.

    `inner_radius` ADDS one more ring at that distance, keeping every ring the
    plain grid already had. It exists because `step` is derived from the
    SMALLEST base in the unit while the model that ends up standing on the drop
    point is the WIDEST one, so the first ring can sit closer than those two
    bases can legally stand - see pack_positions().

    Added rather than substituted, and that is deliberate: moving the first
    ring out instead was built and measured first, and it takes slots AWAY
    from the pairs of models that DID fit on the original ring - within one
    unit the required clearance differs per pair, so one radius cannot serve
    all of them. An extra ring cannot lose anyone: every slot that was legal
    before is still offered, in the same order, and the new one is only ever
    reached by a model that found nothing closer.

    It does NOT follow that the change is free. A denser block is a different
    block, and measure_crowded_movement.py's per-unit numbers move either way
    on it - on the Ork army, Boyz + Warboss + Painboy gained 6 points of
    crowded progress on map 1 while Gretchin 2, squeezed at gap_in 1.05, lost
    10 on map 2. Medians across the three maps: 64->65, 62->59, 29->28. What
    the additive form buys is that no model can be refused a slot it used to
    have; it does not promise every unit a better route."""
    radii = [step * k for k in range(1, rings + 1)]
    # Only when it is FURTHER OUT than the first ring, i.e. only when that
    # ring is the unusable one this exists for. An inner_radius inside the
    # grid would be a second, tighter ring for every unit in the game - which
    # a homogeneous one has (2r + 0.05 against a 2r + 0.1 pitch) and does not
    # want: nothing was refusing it a slot.
    if inner_radius is not None and inner_radius > step + 1e-9:
        radii.append(inner_radius)
        radii.sort()  # nearest first, so a model still prefers the closest slot
    candidates = [(origin_x, origin_y)]
    for ring_radius in radii:
        capacity = max(1, int((2 * math.pi * ring_radius) / step))
        astep = 2 * math.pi / capacity
        angles = sorted(
            (base_angle + k * astep for k in range(capacity)),
            key=lambda a: abs((a - base_angle + math.pi) % (2 * math.pi) - math.pi),
        )
        candidates.extend(
            (origin_x + ring_radius * math.cos(a), origin_y + ring_radius * math.sin(a))
            for a in angles
        )
    return candidates


def pack_positions(squad, origin_x, origin_y, base_angle=-math.pi / 2, position_valid=None,
                   rings=PACK_RINGS, gap_in=MODEL_GAP_IN):
    """One (x, y) per model of `squad`, in squad order, packing them onto
    concentric rings around (origin_x, origin_y).

    Three guarantees, and they are why rings are used rather than a line:
      * every slot is checked for THAT SPECIFIC model (base sizes differ within
        one unit since 19.01 attached units exist);
      * squadmates never overlap each other;
      * each new model lands in coherency range of one already placed, so rule
        09.02's single connected group is built by construction rather than
        hoped for.

    A line fails wholesale by comparison - six models at a 1.5" pitch is a 7.5"
    bar that has to be clear along its whole length, and the spots worth
    standing on are exactly the ones with a wall or a board edge nearby. Rings
    degrade gracefully: a blocked slot costs one slot, not the placement.

    Any model that finds no legal slot is left stacked on the drop point, so
    the caller's own confirm check fails and it can try another facing rather
    than this quietly returning a broken formation."""
    n = len(squad.models)
    if n == 0:
        return []
    # Candidate PITCH comes from the SMALLEST base, not the largest - the same
    # correction game/agent_driver.py's disembark rings needed, and for the
    # same reason. A 19.01 attached unit is not homogeneous: pitching 21 Boyz
    # (0.63") apart as if they were all a 0.98" Warboss blows the 22-model mob
    # out from 6.24" to 9.00" across.
    #
    # That used to be stated here as "rule 09.02's 9" span limit then rejects
    # it at every facing, i.e. the unit cannot be deployed". Only half true
    # now: config.SPREAD_LIMIT_PLAYERS lifted that half of 09.02 for the AI,
    # so measured on the real mob the wide pitch is REJECTED for Player 1 -
    # who reaches this through game/setup.py's "Place as Block" - and LEGAL
    # for the AI. The pitch stays where it is for both of them either way,
    # because a 2.76" wider block is worth nothing to anyone: a small
    # footprint is the design goal (13.09 needs EVERY model in the dense area,
    # and units in a column block each other less).
    #
    # Each slot is still checked against the CONCRETE model that would stand
    # on it (see _first_legal_slot), and the widest models pick first, so
    # nothing overlaps; only the grid gets denser. For a homogeneous unit min
    # and max are the same number, so this changes nothing at all for one.
    step = max(gap_in, 2 * min(m.radius_in for m in squad.models) + 0.1)
    # ...but the INNERMOST ring has to clear the model standing on the drop
    # point, and by the widest-first order in _fill() that is the WIDEST model
    # in the unit. With a pitch off the smallest base the two disagree, and the
    # whole first ring then fails _first_legal_slot()'s overlap bound at every
    # angle - it does not cost one slot, it costs the entire ring.
    #
    # User report on the Necron Warriors: "welcher Mechanismus sorgt eigentlich
    # dafuer, dass hier die Nekonkrieger so viel Abstand zu ihrem Character
    # halten, der angeschlossen ist? Das sorgt nur dafuer, dass der Footprint
    # unnoetig gross wird." Measured on that unit (21 models, a 0.98"
    # Technomancer among 0.63" Warriors): ring 1 seated ZERO models, the
    # Technomancer sat alone in a 1.39" moat while his Warriors stood 0.29"
    # apart, and the block spread to 7.20". Offering a ring at the distance
    # those two bases actually need: moat 0.05", spread 6.24", and the first
    # ring seats six.
    #
    # The ring is ADDED to the grid, never swapped in for it - see
    # ring_candidates(). So this can be asked for unconditionally: a unit that
    # was already packing fine keeps every slot it had, and only a model with
    # nowhere legal to stand closer ever lands on the new ring. A homogeneous
    # unit does not even get one, since max + min + 0.05 is below `step`
    # whenever `step` is 2*r + 0.1.
    candidates = ring_candidates(origin_x, origin_y, step, base_angle, rings,
                                 inner_radius=_inner_radius(squad.models))

    plain = _fill(squad, candidates, position_valid)

    # Melee characters to the FRONT of the block (game/front_rank.py). Skipped
    # outright - not just cheaply, but with no second fill at all - for any unit
    # that has none, which is every unit that is not a 19.01 attached one.
    fighters = front_rank.front_rank_models(squad)
    if not fighters:
        return _stack_leftovers(squad, plain, origin_x, origin_y)

    # Why they are PLACED first rather than swapped forward afterwards, which
    # was tried and measured first: a swap cannot work for a character with a
    # bigger base than the rank and file. The grid is pitched off the SMALLEST
    # base (1.5" here), and a 0.98" Warboss beside a 0.63" Boy needs 1.66", so
    # the only slot in the finished block he fits in is the one the packer
    # already cleared around him. Measured on the reported mob, every forward
    # swap was rejected and he stayed rank 7 of 22. Placing him first is what
    # makes the hole form at the front instead of in the middle.
    #
    # The forward limit comes from the plain fill above: it is the front edge
    # of the block this unit actually forms, so a character is put at the front
    # of his own formation rather than flung out to the edge of the candidate
    # disc, where the rest of the squad could not chain onto him.
    fx, fy = math.cos(base_angle + math.pi), math.sin(base_angle + math.pi)  # toward the enemy
    if not plain:
        return _stack_leftovers(squad, plain, origin_x, origin_y)
    front_limit = max(x * fx + y * fy for (x, y) in plain.values()) + 1e-9
    front_first = sorted(
        (c for c in candidates if c[0] * fx + c[1] * fy <= front_limit),
        key=lambda c: -(c[0] * fx + c[1] * fy),
    )
    led = _fill(squad, candidates, position_valid,
                first=fighters, first_candidates=front_first)

    # Never trade a working placement for a better-looking one - see
    # no_worse_than() for both halves of what "working" means here.
    keep = led if no_worse_than(
        led, plain, lambda i: squad.models[i].radius_in) else plain
    return _stack_leftovers(squad, keep, origin_x, origin_y)


def _inner_radius(models):
    """How far out the innermost ring has to sit for the model standing on the
    drop point to have a neighbour at all: its own base plus the smallest base
    in the unit, plus _first_legal_slot()'s own overlap bound.

    None when there is nothing to size it against, which leaves
    ring_candidates() on its plain grid."""
    if not models:
        return None
    radii = [m.radius_in for m in models]
    return max(radii) + min(radii) + 0.05 + 1e-6


def _fill(squad, candidates, position_valid, first=(), first_candidates=None):
    """{model index: (x, y)} for as many of `squad`'s models as find a legal
    slot, greedily.

    `first` is a list of models that pick before everyone else and, if
    `first_candidates` is given, pick from that ordering instead of the normal
    one. Everyone else keeps the long-standing widest-first order, so the
    hardest model to fit still chooses from the whole board of candidates
    rather than from whatever the small ones left over."""
    models = squad.models
    priority = [i for m in first for i, x in enumerate(models) if x is m]
    rest = sorted((i for i in range(len(models)) if i not in set(priority)),
                  key=lambda i: -models[i].radius_in)
    chosen = {}
    placed = []
    for index in priority + rest:
        model = models[index]
        pool = first_candidates if (index in priority and first_candidates is not None) else candidates
        spot = _first_legal_slot(model, pool, placed, position_valid)
        if spot is not None:
            chosen[index] = spot
            placed.append((spot[0], spot[1], model.radius_in))
    return chosen


def _stack_leftovers(squad, chosen, origin_x, origin_y):
    """Squad-order list of spots, with any model that found nowhere legal left
    stacked on the drop point - see pack_positions()' docstring for why that is
    better than quietly returning a smaller formation."""
    return [chosen.get(i, (origin_x, origin_y)) for i in range(len(squad.models))]


def bridge_count(placed):
    """How many coherency edges this placement has whose loss would split the
    unit - i.e. how many single points of failure rule 09.02 is resting on.

    `placed` is [(x, y, radius), ...]. None if the points are not one group to
    begin with.

    Used to judge one candidate layout against another. Seating the same number
    of models is not enough on its own: measured on the reported Kill Rig
    disembark, putting a 0.98" Beastboss at the tip of a block of 0.63" Beast
    Snagga Boyz seats all eleven and still turns a solid clump into a chain,
    because a bigger base at the front edge has fewer neighbours close enough
    to hold on to. That is exactly the fragility test_disembark_clump.py was
    written to keep out, so the front-rank packing has to be measured against
    it rather than assumed harmless."""
    n = len(placed)
    if n <= 1:
        return 0
    adjacency = [[] for _ in range(n)]
    for i in range(n):
        xi, yi, ri = placed[i]
        for j in range(i + 1, n):
            xj, yj, rj = placed[j]
            if ((xi - xj) ** 2 + (yi - yj) ** 2) ** 0.5 <= COHERENCY_RANGE_IN + ri + rj:
                adjacency[i].append(j)
                adjacency[j].append(i)

    def connected(skip):
        seen, stack = {0}, [0]
        while stack:
            cur = stack.pop()
            for nxt in adjacency[cur]:
                if nxt in seen or (min(cur, nxt), max(cur, nxt)) == skip:
                    continue
                seen.add(nxt)
                stack.append(nxt)
        return len(seen) == n

    if not connected((-1, -1)):
        return None
    edges = {(min(i, j), max(i, j)) for i in range(n) for j in adjacency[i]}
    return sum(1 for edge in edges if not connected(edge))


def no_worse_than(candidate, baseline, radius_of):
    """Whether `candidate` may replace `baseline` as a placement.

    Both are {model index: (x, y)}. Two conditions, and the second one was
    added because the first alone is not enough (see bridge_count()):
      * it seats at least as many models - a failed placement is expensive
        everywhere this is used, and an Emergency Disembark (18.05) destroys
        the unit outright;
      * it is no more fragile - no more coherency edges that a single step
        could break.

    A candidate that cannot be measured at all (not one connected group) is
    refused outright."""
    if len(candidate) < len(baseline):
        return False
    theirs = bridge_count([(x, y, radius_of(i)) for i, (x, y) in baseline.items()])
    ours = bridge_count([(x, y, radius_of(i)) for i, (x, y) in candidate.items()])
    if ours is None:
        return False
    if theirs is None:
        return True
    return ours <= theirs


def _first_legal_slot(model, candidates, placed, position_valid):
    """The first candidate point this specific model may stand on: on the
    board for its own base, allowed by the caller's own validity rule, clear
    of everything in `placed`, and - once anything IS placed - within rule
    09.02's coherency range of at least one of them, measured edge to edge.

    Shared by pack_positions() (which seeds `placed` empty, so the block is
    built from scratch) and returning_positions() (which seeds it with the
    unit's surviving models, so returning models join the group that is
    already standing there). One implementation, because "which slot may this
    model take" is the same question in both and two copies would drift."""
    for (x, y) in candidates:
        if not on_board(x, y, model.radius_in):
            continue
        if position_valid is not None and not position_valid(model, x, y):
            continue
        if any(((x - px) ** 2 + (y - py) ** 2) ** 0.5 < model.radius_in + pr + 0.05
               for px, py, pr in placed):
            continue
        if placed and not any(
            ((x - px) ** 2 + (y - py) ** 2) ** 0.5 <= COHERENCY_RANGE_IN + model.radius_in + pr
            for px, py, pr in placed
        ):
            continue
        return (x, y)
    return None


def match_models_to_slots(models, slots, fixed=()):
    """Which of `slots` each model should walk to, so that the model with the
    furthest to go has as little to go as possible.

    WHY THIS EXISTS. pack_positions() returns its slots in squad order, but it
    FILLS them widest-model-first outwards from the drop point - so slot i has
    nothing to do with where model i happens to be standing. Walking model i to
    slot i, which is what every caller did, therefore hands somebody a diagonal
    across the whole formation for no reason. Measured on the real board, index
    pairing against this matching:

        Boyz mob, 4.8" forward     10.9"  vs  5.1"   (move 6")
        Meganobz, 4.0" forward      6.5"  vs  4.9"   (move 5")
        Stormboyz, 9.6" forward    12.6"  vs 10.5"   (move 12")

    Roughly double, and in each of those rows that is the difference between a
    placement the unit can reach and one it cannot - so the squeeze was being
    refused for a reason that has nothing to do with the ground.

    The MAXIMUM is minimised rather than the total, because the constraint is
    per model: a unit's move fails if any single model cannot reach its slot,
    no matter how short everyone else's walk is.

    `fixed` are indices whose slot must not be reassigned - front-rank melee
    characters (see game/front_rank.py), which pack_positions() deliberately
    seated at the front of the block. Matching them away by distance would
    quietly undo that."""
    n = len(models)
    if n == 0 or len(slots) != n:
        return list(slots)
    fixed = set(fixed)
    free_models = [i for i in range(n) if i not in fixed]
    free_slots = [i for i in range(n) if i not in fixed]
    if not free_models:
        return list(slots)

    cost = [[math.dist((models[i].x_in, models[i].y_in), slots[j]) for j in free_slots]
            for i in free_models]
    options = sorted({c for row in cost for c in row})

    def assign(limit):
        pair = [-1] * len(free_slots)

        def walk(row, seen):
            for j, c in enumerate(cost[row]):
                if c > limit or j in seen:
                    continue
                seen.add(j)
                if pair[j] == -1 or walk(pair[j], seen):
                    pair[j] = row
                    return True
            return False

        if not all(walk(i, set()) for i in range(len(free_models))):
            return None
        return pair

    low, high = 0, len(options) - 1
    if assign(options[high]) is None:
        return list(slots)  # cannot be matched at all: leave the caller's order
    while low < high:
        mid = (low + high) // 2
        if assign(options[mid]) is not None:
            high = mid
        else:
            low = mid + 1

    pair = assign(options[low])
    out = list(slots)
    for slot_pos, row in enumerate(pair):
        out[free_models[row]] = slots[free_slots[slot_pos]]
    return out


def returning_positions(squad, returning, base_angle=None, position_valid=None,
                        rings=PACK_RINGS, gap_in=MODEL_GAP_IN):
    """Where to stand each of `returning` when models are put BACK into a
    unit that is already on the battlefield (Painboy's Grot Orderly - see
    game/grot_orderly.py; rule 09.02 requires the result to still be one
    coherent group).

    Different problem from pack_positions(): the survivors are already
    standing somewhere legal and must not move, so they seed the collision/
    coherency set instead of being laid out. Each returning model therefore
    lands touching the group that is there, not a group built from scratch.

    Returns a list the same length as `returning`, with None for any model
    that found nowhere legal - which the caller is expected to honour rather
    than force, since the ability itself says "UP TO D3 models". Failing to
    place one costs one model, not the whole return."""
    survivors = [m for m in squad.models if not m.is_dead()]
    if not survivors or not returning:
        return [None] * len(returning)

    origin_x = sum(m.x_in for m in survivors) / len(survivors)
    origin_y = sum(m.y_in for m in survivors) / len(survivors)
    widest = max([m.radius_in for m in survivors] + [m.radius_in for m in returning])
    step = max(gap_in, 2 * widest + 0.1)
    if base_angle is None:
        base_angle = away_from_board_centre(origin_x, origin_y)
    candidates = ring_candidates(origin_x, origin_y, step, base_angle, rings)

    placed = [(m.x_in, m.y_in, m.radius_in) for m in survivors]
    order = sorted(range(len(returning)), key=lambda i: -returning[i].radius_in)
    out = [None] * len(returning)
    for index in order:
        model = returning[index]
        spot = _first_legal_slot(model, candidates, placed, position_valid)
        if spot is None:
            continue
        out[index] = spot
        placed.append((spot[0], spot[1], model.radius_in))
    return out


def away_from_board_centre(origin_x, origin_y):
    """A sensible default facing when there is no enemy to reason about: pack
    back toward the near edge, away from the middle of the table.

    For a unit being set up in its own deployment zone that means the block
    grows backwards into the zone rather than spilling forward out of it, which
    is both what a player does by hand and what keeps a 10-model block inside a
    12"-deep zone (game/maps.py's map 2)."""
    dx = origin_x - config.BOARD_WIDTH_IN / 2
    dy = origin_y - config.BOARD_HEIGHT_IN / 2
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return -math.pi / 2
    return math.atan2(dy, dx)
