"""Step 0 of the placements plan: is there any headroom to chase?

THE QUESTION. CLAUDE.md's deferred entry proposes replacing "move toward a
point, then check whether the formation is still legal" with "build a legal
target FORMATION first, then walk into it", and offering the tactical layer a
handful of scored placements instead of a destination. That is a large rebuild,
and the user's own objection to it is the reason this script exists: the option
archetypes would themselves need designing and tuning, so the rebuild is only
worth it if the ceiling is meaningfully above what the AI already reaches.

So this measures the CEILING, not another heuristic. For each unit, on the same
crowded board measure_crowded_movement.py uses, it brute-forces reachable
placements - anchor grid x facings, models poured in with
formation_layout.pack_positions(), every model's line of sight checked
individually - and reports the best achievable against what the AI's real
movement path actually delivers on the same turn from the same start.

WHY REAL MODEL POSITIONS AND NOT packed_radius(). The measurement this replaces
approximated a unit as a DISC of packed_radius() and concluded there were zero
spots on map 2 that both hide a unit and gain ground. The user rejected that
("es gibt keine platz? sicher?", then, with staging spots drawn on the map, "ich
kann mir nicht vorstellen, dass da keine squads dahinterpassen. man muss die
modelle halt nur gut anordnen"), and he was right: a 3.08"-radius disc fits
behind almost nothing, so the number said "my circle approximation fits nowhere",
not "there is no cover". A squad is a deformable mass - it can be a line hugging
a wall or a column in a corridor - so the only honest test is to lay the models
out and look.

WHAT MAKES THIS AN UPPER BOUND, stated plainly so the verdict is not overread:
  * reachability is judged per model - every model matched to its own slot,
    nobody walking further than its own move - but transit blocking is NOT
    simulated, so a placement counted as reachable might still be unreachable
    in one move;
  * hiding is judged against enemies where they STAND, not after they move,
    which is the stricter test observation._spot_stays_hidden() applies.
Both biases inflate the ceiling. That is the safe direction for a go/no-go: if
even the inflated ceiling is close to what the AI already gets, the rebuild is
not worth it.

WHY THE LINE-OF-SIGHT CACHE IS EXACT, not an approximation. Measured here, one
has_line_of_sight() call costs 3.6 ms, and confirming a 22-model placement is
fully hidden costs 924 of them - 3.3 s. The cache turns that into a lookup, and
it is sound because of rule 06.01 plus this project's own house rule: a blocker
must be neither in the observer's unit nor in the TARGET's unit, and no model of
the observer's army blocks at all. For an enemy looking at one of our models,
the rest of that model's own squad therefore never blocks - so the answer for
(enemy, point, base size) does not depend on where the rest of the squad is
standing, and slots repeat heavily across anchors and facings.

Run:  python measure_placement_headroom.py [map_key] [--units=N] [--step=0.5]
"""

import math
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import measure_crowded_movement as H
from ai import agent_driver
from ai import observation as O
from game import config, formation_layout, front_rank, line_of_sight, maps
from game.game_state import GameState
from game.squad import min_model_movement, model_terrain_violation

# Anchor grid step for the LEGALITY pass. Fine, because the gaps between
# friendly units are often narrower than a base: see headroom()'s docstring for
# what a 1.5" grid measured.
DEFAULT_STEP_IN = 0.5
# Grid for the visibility pass, which costs 3.6 ms a probe rather than pure
# arithmetic. Hidden ground comes in regions, so a coarse hunt plus a refine
# around the hits finds the same places for a fraction of the probes.
COARSE_PROBE_STEP_IN = 1.5
# Facings tried per anchor. The block grows away from `base_angle`, so which way
# it faces decides whether it hugs the cover or spills past it.
FACINGS = 6
# How many anchors get a full pack-and-check per objective. The point probe
# below is what makes this affordable: it is a NECESSARY condition for a fully
# hidden placement (pack_positions puts a model on the anchor itself), so
# anchors that fail it cannot possibly qualify and cost one probe instead of a
# whole placement.
FULL_EVALS_PER_OBJECTIVE = 8
# How many anchors an objective may try before giving up on finding that
# many. Bounds the cost when most of the good-looking ground is out of
# reach - see pursue() for why a fixed top-N does not work here.
MAX_ANCHOR_ATTEMPTS = 80


class Sight:
    """Can any enemy see one of `squad`'s models standing at (x, y)?

    Caches on (base size, point) - see the module docstring for why that is
    exact rather than an approximation."""

    def __init__(self, state, enemy_models):
        self.state = state
        self.enemies = enemy_models
        self.cache = {}
        self.calls = 0

    def seen(self, model, x_in, y_in):
        key = (round(model.radius_in, 3), round(x_in, 2), round(y_in, 2))
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        keep = (model.x_in, model.y_in)
        model.x_in, model.y_in = x_in, y_in
        out = False
        for enemy in self.enemies:
            self.calls += 1
            if line_of_sight.has_line_of_sight(enemy, model, self.state.obstacles,
                                               self.state.tokens, self.state.terrain_areas):
                out = True
                break
        model.x_in, model.y_in = keep
        self.cache[key] = out
        return out

    def shooters(self, model, x_in, y_in, reach_in):
        """Whether this model, standing there, has a live shot: an enemy inside
        its own weapon reach that it can also see.

        Cached on the same key as seen(), and sound for the same reason - our
        own army never blocks for one of our own observers (house rule), and the
        target's own unit never blocks (06.01), so no enemy squad is moving
        while this search runs."""
        key = ("shoot", round(model.radius_in, 3), round(x_in, 2), round(y_in, 2),
               round(reach_in, 1))
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        out = self._shoots(model, x_in, y_in, reach_in)
        self.cache[key] = out
        return out

    def _shoots(self, model, x_in, y_in, reach_in):
        for enemy in self.enemies:
            if math.hypot(enemy.x_in - x_in, enemy.y_in - y_in) - enemy.radius_in > reach_in:
                continue
            keep = (model.x_in, model.y_in)
            model.x_in, model.y_in = x_in, y_in
            self.calls += 1
            ok = line_of_sight.has_line_of_sight(model, enemy, self.state.obstacles,
                                                 self.state.tokens, self.state.terrain_areas)
            model.x_in, model.y_in = keep
            if ok:
                return True
        return False


def model_reach(model):
    """How far THIS model can shoot - its own longest ranged weapon.

    Per model, not per squad, and the difference is not cosmetic. Taking the
    squad maximum credited every model with the best gun in the unit: the
    22-strong mob has ONE model with a 24" weapon (the Warboss) and twenty with
    12" sluggas, so a squad-wide 24" reported models as having a shot from
    ranges where they have nothing at all. Same error class this project has
    hit before, where the AI was told about a weapon that model does not have.
    """
    ranges = [w.range_in for w in model.weapons
              if getattr(w, "weapon_type", None) == "ranged"]
    return max(ranges) if ranges else 0.0


def is_melee_unit(squad):
    """Whether a live shot is even the right yardstick for this unit.

    User, on being shown Stormboyz as a shooting example: "das ist eine
    nahkampfeinheit. kann es sein, dass sie vielleicht ausser reichweite sind?"
    - and they were, 13.9" out with a 12" slugga. Scoring a melee unit on
    shooting measures the wrong thing entirely; what it wants is a charge, so
    the report carries both columns and says which one to read.

    Reuses game/front_rank.py's own melee test rather than inventing a second
    one, applied to the rank and file rather than to characters."""
    focused = sum(1 for m in squad.models if front_rank.is_melee_focused(m))
    return focused * 2 > len(squad.models)


def charge_chance_from(slots, squad, enemies):
    """Best 2D6 charge chance from this placement - the yardstick a melee unit
    is actually judged on. Charges happen from where the unit ENDS, with no
    further movement, so this is a property of the placement itself."""
    best_pct = 0.0
    for enemy in enemies:
        gap = min(math.hypot(sx - enemy.x_in, sy - enemy.y_in) - m.radius_in - enemy.radius_in
                  for m, (sx, sy) in zip(squad.models, slots))
        best_pct = max(best_pct, O.charge_roll_chance(gap))
    return best_pct


def slot_validator(state, squad):
    """Movement legality for one model at one point: on the board for its own
    base, terrain it may not cross, and clear of every model that is not its
    own squadmate. Same predicate _stage_toward() packs against.

    The overlap half is bucketed into a coarse grid rather than scanned. It is
    called from inside pack_positions() for every candidate slot of every model
    of every facing of every anchor, and against a full army that is ~120 other
    models each time - measured, it was most of a 61-minute run. Exact, not
    approximate: two bases can only overlap if their centres are within the sum
    of their radii, so with a cell at least that wide the 3x3 neighbourhood
    contains every model that could possibly matter."""
    others = [t for t in state.tokens if t.squad is not squad]
    widest = max([t.radius_in for t in others] + [m.radius_in for m in squad.models],
                 default=1.0)
    cell = max(1.0, 2 * widest)
    buckets = {}
    for other in others:
        buckets.setdefault((int(other.x_in // cell), int(other.y_in // cell)),
                           []).append(other)

    def ok(model, x_in, y_in):
        if not formation_layout.on_board(x_in, y_in, model.radius_in):
            return False
        if model_terrain_violation(model, state.obstacles, x_in, y_in):
            return False
        cx, cy = int(x_in // cell), int(y_in // cell)
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for other in buckets.get((gx, gy), ()):
                    if math.hypot(x_in - other.x_in, y_in - other.y_in) < \
                            model.radius_in + other.radius_in:
                        return False
        return True

    return ok


def assignment_cost(squad, slots):
    """The smallest distance D such that every model can be matched to its own
    slot with no model walking further than D - the binding constraint on
    whether a placement is reachable in a single move.

    Solved exactly (binary search on the candidate distances, augmenting-path
    matching at each threshold) rather than by greedy nearest-pair, which was
    the first version and which OVERSTATES D: greedy commits the globally
    closest pair first and can leave two models fighting over one slot while a
    nearer one sits unused. For a ceiling measurement an overstated D is the
    wrong direction - it throws out placements that are in fact reachable. n is
    at most 22 here, so exact costs nothing."""
    n = len(squad.models)
    cost = [[math.dist((m.x_in, m.y_in), slot) for slot in slots] for m in squad.models]
    options = sorted({c for row in cost for c in row})

    def matches(limit):
        pair = [-1] * len(slots)

        def try_assign(model, seen):
            for j, c in enumerate(cost[model]):
                if c > limit or j in seen:
                    continue
                seen.add(j)
                if pair[j] == -1 or try_assign(pair[j], seen):
                    pair[j] = model
                    return True
            return False

        return all(try_assign(i, set()) for i in range(n))

    low, high = 0, len(options) - 1
    if not matches(options[high]):
        return float("inf")
    while low < high:
        mid = (low + high) // 2
        if matches(options[mid]):
            high = mid
        else:
            low = mid + 1
    return options[low]


def evaluate(state, squad, slots, sight, goal, budget, reach_in, before):
    """Full metrics for one candidate placement, models actually stood on it."""
    if len(set(slots)) != len(slots):
        return None  # the packer had to stack models: this ground does not fit
    keep = [(m.x_in, m.y_in) for m in squad.models]
    for model, (x, y) in zip(squad.models, slots):
        model.x_in, model.y_in = x, y
    coherent = not squad.check_coherency()
    spread = H.spread_of(squad)
    for model, (x, y) in zip(squad.models, keep):
        model.x_in, model.y_in = x, y

    if not coherent:
        return None
    # Reachability BEFORE any line of sight: it is pure arithmetic, and it
    # rejects most candidates, while a full visibility pass on a 22-model
    # placement costs up to 3.3 s.
    worst_step = assignment_cost(squad, slots)
    if worst_step > budget + 1e-6:
        return None
    hidden = sum(1 for m, (x, y) in zip(squad.models, slots) if not sight.seen(m, x, y))
    shooting = sum(1 for m, (x, y) in zip(squad.models, slots)
                   if sight.shooters(m, x, y, model_reach(m)))
    after = (sum(x for x, _y in slots) / len(slots), sum(y for _x, y in slots) / len(slots))
    row = H.score(before, after, goal, budget)
    row.update(hidden=hidden, shooting=shooting, spread=spread,
               charge=charge_chance_from(slots, squad, sight.enemies),
               models=len(squad.models), worst_step=worst_step, anchor=None)
    return row


def anchors_for(squad, budget, step_in, valid):
    """Grid points within one move of the centroid that the unit's WIDEST model
    could legally stand on.

    The legality filter is not tidiness, it is what makes the search work at
    all. pack_positions() seats a model on the anchor if it can and otherwise
    walks outwards through its rings - and for a 2.1"-base Kill Rig a ring step
    is 4.3", so an anchor sitting on terrain produced placements up to 17" away
    from it, which the reachability test then correctly threw out. Measured
    before this filter existed, every one of the eight highest-progress anchors
    was on terrain, so the whole shortlist was spent on placements that could
    never qualify and the reported "ceiling" came out BELOW what the AI itself
    achieves - which is impossible, and is how the bug was caught."""
    cx, cy = agent_driver._centroid(squad)
    widest = max(squad.models, key=lambda m: m.radius_in)
    # Reach further than one move, on purpose. pack_positions() grows the block
    # AWAY from the anchor, so the anchor sits at the block's edge and the
    # resulting centroid - which is what progress is scored on - lands up to
    # half a packed spread behind it. Stopping the grid at exactly `budget`
    # therefore cannot express placements the AI itself reaches: measured that
    # way, the search came in 10-49 points under the AI for three units. It
    # cannot let anything illegal through either, because reachability is
    # enforced per model afterwards, against an exact matching.
    span = budget + formation_layout.packed_radius(squad)
    out = []
    steps = int(span / step_in) + 1
    for ix in range(-steps, steps + 1):
        for iy in range(-steps, steps + 1):
            x, y = cx + ix * step_in, cy + iy * step_in
            if math.hypot(x - cx, y - cy) > span + 1e-9:
                continue
            if not formation_layout.on_board(x, y, widest.radius_in):
                continue
            if not valid(widest, x, y):
                continue
            out.append((x, y))
    return out


def headroom(state, squad, goal, sight, budget, step_in, extra_anchors=()):
    """The best reachable placement under each objective, by brute force.

    Two grids, because the two filters have wildly different costs. Legality is
    arithmetic, so it runs on a FINE grid - the legal ground between friendly
    units is often only a base-width wide, and a 1.5" grid simply misses it
    (measured: on the deployment band the coarse grid found no legal anchor at
    all for the 2.1"-base Kill Rig, while the AI's own move ends on legal
    ground 8.7" away). Visibility costs 3.6 ms a check, so the hidden-region
    hunt runs on a COARSE grid first and only then refines around the hits."""
    before = agent_driver._centroid(squad)
    reach_in = max((model_reach(m) for m in squad.models), default=0.0)
    widest = max(squad.models, key=lambda m: m.radius_in)
    valid = slot_validator(state, squad)
    smallest = min(m.radius_in for m in squad.models)
    gap_in = 2 * smallest + 0.05

    fine = anchors_for(squad, budget, step_in, valid)
    fine += [p for p in extra_anchors if valid(widest, p[0], p[1])]
    if not fine:
        return []
    progress_of = lambda p: math.dist(before, goal) - math.dist(p, goal)

    # Coarse pass for the hidden objective. A visible anchor cannot yield a
    # fully hidden placement - pack_positions() seats a model on the anchor
    # itself when it is legal - so this is a strict prerequisite, not a guess.
    coarse_step = max(step_in, COARSE_PROBE_STEP_IN)
    coarse = {}
    for (x, y) in fine:
        key = (round(x / coarse_step), round(y / coarse_step))
        coarse.setdefault(key, (x, y))
    hidden_seeds = [p for p in coarse.values() if not sight.seen(widest, *p)]
    hidden_fine = [p for p in fine
                   if any(math.dist(p, seed) <= coarse_step for seed in hidden_seeds)
                   and not sight.seen(widest, *p)]

    results, tried = [], set()

    def pursue(points, key, wanted=FULL_EVALS_PER_OBJECTIVE, attempts=MAX_ANCHOR_ATTEMPTS):
        """Walk `points` best-first and keep going until `wanted` of them have
        yielded at least one legal, reachable placement.

        Adaptive rather than "take the best N", because the two are not the
        same once the anchor grid reaches past one move: the furthest-forward
        anchors are exactly the ones whose packed block cannot be reached, so a
        fixed top-N spends itself entirely on placements that get thrown out.
        Measured that way, the single-model Kill Rig went from 44 candidates to
        zero the moment the grid was widened."""
        found = 0
        for point in sorted(points, key=key, reverse=True)[:attempts]:
            anchor = (round(point[0], 2), round(point[1], 2))
            if anchor in tried:
                continue
            tried.add(anchor)
            hit = False
            for k in range(FACINGS):
                base_angle = -math.pi / 2 + k * 2 * math.pi / FACINGS
                slots = formation_layout.pack_positions(
                    squad, point[0], point[1], base_angle=base_angle,
                    position_valid=valid, gap_in=gap_in)
                got = evaluate(state, squad, slots, sight, goal, budget, reach_in, before)
                if got is None:
                    continue
                got["anchor"] = point
                results.append(got)
                hit = True
            found += 1 if hit else 0
            if found >= wanted:
                return

    pursue(fine, progress_of)
    pursue(hidden_fine, progress_of)
    # Shooting: cheap arithmetic stand-in for "how much can I see from here" -
    # how many enemy models are inside this unit's own weapon reach.
    pursue(fine, lambda p: sum(
        1 for e in sight.enemies
        if math.hypot(e.x_in - p[0], e.y_in - p[1]) - e.radius_in <= reach_in))
    return results


def best(results, key):
    return max(results, key=key) if results else None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    map_key = args[0] if args else "map2"
    limit, step_in = None, DEFAULT_STEP_IN
    for flag in flags:
        if flag.startswith("--units="):
            limit = int(flag.split("=", 1)[1])
        if flag.startswith("--step="):
            step_in = float(flag.split("=", 1)[1])

    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    settled = []
    placed = H.lay_out(state, H.movers(state), (4.0, config.BOARD_HEIGHT_IN * 0.30), settled)
    enemy = [(sq.name, sq) for sq in H.defenders()]
    enemy_placed = H.lay_out(state, enemy,
                             (config.BOARD_HEIGHT_IN * 0.62, config.BOARD_HEIGHT_IN * 0.88),
                             settled)
    enemy_models = [m for _l, sq in enemy_placed for m in sq.models]
    state.tokens = [m for _l, sq in placed for m in sq.models] + enemy_models
    goals = H.assign_goals(placed, config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
    if limit:
        placed = placed[:limit]

    print(f"{map_key}: {len(placed)} own units, {len(enemy_models)} enemy models, "
          f"grid {step_in}\", {FACINGS} facings\n")
    header = (f"{'unit':30s} {'n':>3s} {'role':>6s} | "
              f"{'AI got':>6s} {'hid':>6s} {'shoot':>6s} {'chg':>5s} | "
              f"{'best got':>8s} | {'max hid':>7s} {'got':>5s} | "
              f"{'max shoot':>9s} {'got':>5s} | {'max chg':>7s} {'got':>5s}")
    print(header)
    print("-" * len(header))

    rows = []
    started = time.perf_counter()
    for label, squad in placed:
        goal = goals[label]
        budget = min_model_movement(squad) or 6.0
        sight = Sight(state, enemy_models)
        start = [(m.x_in, m.y_in) for m in squad.models]

        # The AI moves FIRST, and where it ends up is then fed back in as a
        # known-good anchor. Not to flatter the ceiling - a seeded anchor still
        # has to survive packing, reachability and coherency like any other -
        # but so that "the search found less than the AI" means the search is
        # blind rather than merely coarse.
        before, after = H.move_once(state, squad, goal)
        ai = H.score(before, after, goal, budget)
        ai["hidden"] = sum(1 for m in squad.models if not sight.seen(m, m.x_in, m.y_in))
        ai["shooting"] = sum(1 for m in squad.models
                             if sight.shooters(m, m.x_in, m.y_in, model_reach(m)))
        ai["charge"] = charge_chance_from([(m.x_in, m.y_in) for m in squad.models],
                                          squad, enemy_models)
        for model, (x, y) in zip(squad.models, start):
            model.x_in, model.y_in = x, y

        results = headroom(state, squad, goal, sight, budget, step_in,
                           extra_anchors=[after])

        n = len(squad.models)
        b_got = best(results, lambda r: r["got"])
        b_hid = best(results, lambda r: (r["hidden"], r["got"]))
        b_shoot = best(results, lambda r: (r["shooting"], r["got"]))
        b_charge = best(results, lambda r: (r["charge"], r["got"]))
        # The combination the user actually doubted the AI could handle
        # ("maximal vorzuruecken, gleichzeitig aber moeglichst ausserhalb der
        # LOS zu bleiben"): the best hiding and the best shooting available
        # WITHOUT giving up any ground relative to what the AI itself managed.
        # Reported separately because a ceiling reached by standing still is
        # not an answer to that question.
        kept = [r for r in results if r["got"] >= ai["got"] - 1e-9]
        b_hid_free = best(kept, lambda r: (r["hidden"], r["got"]))
        b_shoot_free = best(kept, lambda r: (r["shooting"], r["got"]))
        cell = lambda r, k: (f"{r[k]}/{n}" if r else "-")
        role = "melee" if is_melee_unit(squad) else "shoot"
        print(f"{label:30s} {n:3d} {role:>6s} | {100 * ai['got']:5.0f}% "
              f"{str(ai['hidden']) + '/' + str(n):>6s} "
              f"{str(ai['shooting']) + '/' + str(n):>6s} "
              f"{ai['charge']:4.0f}% | "
              f"{(100 * b_got['got'] if b_got else 0):7.0f}% | "
              f"{cell(b_hid, 'hidden'):>7s} "
              f"{(100 * b_hid['got'] if b_hid else 0):4.0f}% | "
              f"{cell(b_shoot, 'shooting'):>9s} "
              f"{(100 * b_shoot['got'] if b_shoot else 0):4.0f}% | "
              f"{(b_charge['charge'] if b_charge else 0):6.0f}% "
              f"{(100 * b_charge['got'] if b_charge else 0):4.0f}%")
        rows.append(dict(label=label, n=n, ai=ai, best_got=b_got, best_hidden=b_hid,
                         best_shoot=b_shoot, best_hidden_free=b_hid_free,
                         best_shoot_free=b_shoot_free, best_charge=b_charge,
                         melee=is_melee_unit(squad),
                         candidates=len(results), sight=sight))

    print()
    ai_got = H.median([r["ai"]["got"] for r in rows])
    top_got = H.median([r["best_got"]["got"] if r["best_got"] else 0.0 for r in rows])
    ai_shoot = sum(r["ai"]["shooting"] for r in rows)
    top_shoot = sum(r["best_shoot"]["shooting"] if r["best_shoot"] else 0 for r in rows)
    ai_hidden_units = sum(1 for r in rows if r["ai"]["hidden"] == r["n"])
    top_hidden_units = sum(1 for r in rows
                           if r["best_hidden"] and r["best_hidden"]["hidden"] == r["n"])
    models = sum(r["n"] for r in rows)
    print(f"median share of achievable progress   AI {100 * ai_got:.0f}%   "
          f"ceiling {100 * top_got:.0f}%")
    print(f"models with a live shot after moving  AI {ai_shoot}/{models} "
          f"({100 * ai_shoot / models:.0f}%)   ceiling {top_shoot}/{models} "
          f"({100 * top_shoot / models:.0f}%)")
    print(f"units fully out of enemy sight        AI {ai_hidden_units}/{len(rows)}   "
          f"ceiling {top_hidden_units}/{len(rows)}")

    # max(AI, available) per unit, NOT the bare candidate value. A unit whose
    # `kept` set came out empty - because the search could not match its own
    # ground, which happens for the units already sitting at 87-99% - would
    # otherwise contribute zero here and drag the total BELOW what the AI
    # manages, which reads as "placing better is impossible" when it really
    # means "this unit was not measured". First version did exactly that and
    # reported 52/103 available against 53/103 achieved.
    free_shoot = sum(max(r["ai"]["shooting"],
                         r["best_shoot_free"]["shooting"] if r["best_shoot_free"] else 0)
                     for r in rows)
    free_hidden = sum(1 for r in rows
                      if r["ai"]["hidden"] == r["n"]
                      or (r["best_hidden_free"] and r["best_hidden_free"]["hidden"] == r["n"]))
    print(f"\nsame ground as the AI, better placed - i.e. free of any trade:")
    print(f"  models with a live shot             AI {ai_shoot}/{models}   "
          f"available {free_shoot}/{models}")
    print(f"  units fully out of enemy sight      AI {ai_hidden_units}/{len(rows)}   "
          f"available {free_hidden}/{len(rows)}")
    # Search-quality guard. A ceiling is only a ceiling if the brute force can
    # at least reproduce what the AI already does; anything less means the grid
    # or the shortlist is missing the good ground, not that the good ground is
    # absent. This is how the anchor-legality bug above was caught, so it stays
    # in as a permanent check rather than a one-off.
    short = [r for r in rows
             if not r["best_got"] or r["best_got"]["got"] < r["ai"]["got"] - 0.02]
    if short:
        print(f"\nWARNING - brute force did not match the AI on {len(short)} unit(s); "
              f"the ceiling is understated for them, so widen the search before "
              f"reading the verdict:")
        for r in short:
            found = f"{100 * r['best_got']['got']:.0f}%" if r["best_got"] else "nothing"
            print(f"  {r['label']:30s} AI {100 * r['ai']['got']:.0f}%, search found {found}")

    print(f"\ncandidates evaluated per unit: {sorted(r['candidates'] for r in rows)}")
    print(f"line-of-sight calls: {sum(r['sight'].calls for r in rows)}, "
          f"elapsed {time.perf_counter() - started:.0f}s")

    print("\nbest hidden placement per unit (anchor, models hidden, ground gained):")
    for r in rows:
        b = r["best_hidden"]
        if b and b["hidden"] == r["n"]:
            print(f"  {r['label']:30s} ({b['anchor'][0]:5.1f},{b['anchor'][1]:5.1f})  "
                  f"{b['hidden']}/{r['n']} hidden, {b['progress']:+5.1f}\" "
                  f"({100 * b['got']:.0f}% of achievable), spread {b['spread']:.1f}\"")
        else:
            got = f"{b['hidden']}/{r['n']}" if b else "-"
            print(f"  {r['label']:30s} none fully hidden (best {got})")


if __name__ == "__main__":
    main()
