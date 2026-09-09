"""How often the AI completes a charge that is physically possible - measured
over many synthetic scenes on real map2 terrain, through the real charge
ladder (ai/agent_driver._run_charge_attempts), and A/B against one mechanism
switched off.

WHY THIS EXISTS. The two reported charges (measure_reported_moves.py A/B)
turned out to be one that the engine's own transit rules make unreachable by
a hair (case A: shortest legal path 12.05" on a 12" roll) and one the sweep
already completes (case B) - neither can measure an extra approach. This
harness can: it scatters a charging unit, a target and bystander enemy units
over the map, rolls a fixed set of distances, and counts the charges that
COMPLETE and the models that end engaged. A scene is only kept when brute
force says it is possible: some legal engaged end spot lies within the roll
of some model in a straight line - a lower bound, as case A shows, so the
completion rate is never expected to be 100%.

Two worlds: the default scatters freely (mostly open ground, gaps 4-10");
`--hard` is the world the reports come from - the gap within 3" of the roll,
one to three bystanders within 6" of the target, and in every other scene a
Dense wall dropped between charger and target.

Deterministic (seeded), so a run is repeatable and an A/B compares the same
scenes.

Run:  python measure_charge_scenes.py [scenes] [--hard]
          [--neutralize=_charge_slot_first | --neutralize=old_ring]
"""
import math
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from ai import agent_driver as ad  # noqa: E402
from game import config, maps  # noqa: E402
from game.factions import build_squad  # noqa: E402
from game.factions.orks import BOYZ, MEGANOBZ, WARBIKERS  # noqa: E402
from game.factions.necrons import LYCHGUARD, SKORPEKH_DESTROYERS  # noqa: E402
from game.factions.tau_empire import KROOT_CARNIVORES, STRIKE_TEAM, VESPID_STINGWINGS  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance, model_terrain_violation  # noqa: E402
from game.terrain import DENSE, Obstacle  # noqa: E402
from game.turn import PHASES, PHASE_CHARGE, TurnTracker  # noqa: E402

battle_map = maps.apply_to_config(maps.get("map2"))
CHARGERS = [(BOYZ, 10), (MEGANOBZ, 5), (WARBIKERS, 3), (LYCHGUARD, 5), (SKORPEKH_DESTROYERS, 3)]
TARGETS = [(STRIKE_TEAM, 5), (KROOT_CARNIVORES, 10), (VESPID_STINGWINGS, 5)]
ROLLS = (7.0, 9.0, 12.0)
COUNTS = {"slot_first_calls": 0, "slot_first_landed": 0}


def line_up(squad, x, y, cols=5, pitch=1.4):
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + (i % cols) * pitch, y + (i // cols) * pitch


def legal_position(state, squad, others):
    for m in squad.models:
        if not (m.radius_in < m.x_in < config.BOARD_WIDTH_IN - m.radius_in
                and m.radius_in < m.y_in < config.BOARD_HEIGHT_IN - m.radius_in):
            return False
        if model_terrain_violation(m, state.obstacles):
            return False
        for o in others:
            if math.dist((m.x_in, m.y_in), (o.x_in, o.y_in)) < m.radius_in + o.radius_in + 0.1:
                return False
    return True


def brute_force_possible(squad, target, roll, tokens, obstacles, keep_out):
    """Some legal engaged end spot within `roll` (straight line) of some
    model: on the board, off Dense terrain, no overlap, within Engagement
    Range of the target and outside every bystander's."""
    others = [t for t in tokens if t.squad is not squad]
    for m in squad.models:
        r = m.radius_in
        for e in target.models:
            for ring in (0.2, 0.7, 1.2, 1.7):
                dist = ring + r + e.radius_in
                for k in range(24):
                    a = 2 * math.pi * k / 24
                    x, y = e.x_in + dist * math.cos(a), e.y_in + dist * math.sin(a)
                    if math.dist((x, y), (m.x_in, m.y_in)) > roll:
                        continue
                    if not (r < x < config.BOARD_WIDTH_IN - r and r < y < config.BOARD_HEIGHT_IN - r):
                        continue
                    if model_terrain_violation(m, obstacles, x, y):
                        continue
                    if any(math.dist((x, y), (o.x_in, o.y_in)) < r + o.radius_in for o in others):
                        continue
                    if any(math.dist((x, y), (o.x_in, o.y_in)) - r - o.radius_in <= ENGAGEMENT_RANGE_IN
                           for o in others if o.squad in keep_out):
                        continue
                    return True
    return False


def scene(seed, hard, roll):
    rng = random.Random(seed)
    state = GameState()
    battle_map.build(state)
    sheet, n = rng.choice(CHARGERS)
    charger = build_squad(sheet, "Player 2", name="2 Charger 1")
    charger.models = charger.models[:n]
    tsheet, tn = rng.choice(TARGETS)
    target = build_squad(tsheet, "Player 1", name="1 Target 1")
    target.models = target.models[:tn]
    bystanders = []
    for i in range(rng.randint(1, 3) if hard else rng.randint(0, 2)):
        bsheet, bn = rng.choice(TARGETS)
        b = build_squad(bsheet, "Player 1", name=f"1 Bystander {i + 1}")
        b.models = b.models[:min(bn, 5)]
        bystanders.append(b)
    for _attempt in range(200):
        tx, ty = rng.uniform(6.0, config.BOARD_WIDTH_IN - 6.0), rng.uniform(8.0, config.BOARD_HEIGHT_IN - 8.0)
        line_up(target, tx, ty)
        if not legal_position(state, target, []):
            continue
        angle = rng.uniform(0, 2 * math.pi)
        gap = rng.uniform(max(3.0, roll - 3.0), roll - 0.5) if hard else rng.uniform(4.0, 10.0)
        cx, cy = tx + gap * math.cos(angle), ty + gap * math.sin(angle)
        line_up(charger, cx, cy)
        placed = list(target.models)
        if not legal_position(state, charger, placed):
            continue
        placed += list(charger.models)
        ok = True
        for b in bystanders:
            for _t in range(30):
                reach = 6.0 if hard else 8.0
                bx = tx + rng.uniform(-reach, reach)
                by = ty + rng.uniform(-reach, reach)
                line_up(b, bx, by)
                if legal_position(state, b, placed):
                    placed += list(b.models)
                    break
            else:
                ok = False
        if not ok:
            continue
        # Rule 11.01: a unit within Engagement Range of ANY enemy cannot declare
        # a charge - and a model left standing beside a bystander keeps the
        # whole unit illegally engaged with it, whatever the rest do.
        if charger.min_distance_to(target) < ENGAGEMENT_RANGE_IN + 0.5:
            continue
        if any(charger.min_distance_to(b) < ENGAGEMENT_RANGE_IN + 0.5 for b in bystanders):
            continue
        wall = None
        if hard and seed % 2 == 0:
            # A Dense wall across the line, a third of the way to the target,
            # as long as the gap and 1" thick, with its ends open.
            mx, my = cx + 0.35 * (tx - cx), cy + 0.35 * (ty - cy)
            wall = Obstacle(mx, my, max(3.0, gap * 0.9), 1.0, DENSE,
                            angle_deg=math.degrees(angle) + 90.0)
            state.obstacles.append(wall)
            if not legal_position(state, charger, []) or not legal_position(state, target, []) \
                    or any(not legal_position(state, b, []) for b in bystanders):
                state.obstacles.remove(wall)
                continue
        state.tokens = list(charger.models) + list(target.models) + [m for b in bystanders for m in b.models]
        return state, charger, target, bystanders
    return None


def run_scene(state, charger, target, roll):
    tracker = TurnTracker(first_player="Player 2")
    tracker.phase_index = PHASES.index(PHASE_CHARGE)
    mc = MovementController(obstacles=state.obstacles, player_name="Player 2", turn_tracker=tracker,
                            all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)

    def reopen():
        mc.select(charger.models[0])
        if mc.selected_squad is not charger:
            mc.selected_squad = charger
        mc.start_charge_move(roll, [target])

    reopen()
    ok, _errors = ad._run_charge_attempts(mc, charger, target, roll, reopen=reopen, confirm=mc.confirm_move)
    engaged = sum(1 for m in charger.models if any(edge_distance(m, e) <= ENGAGEMENT_RANGE_IN for e in target.models))
    return ok, engaged


def path_feasible(state, charger, target, bystanders, roll):
    """The CEILING: is there a legal engaged slot some model can reach by a
    legal PATH (enemy bases block transit, 03.01) within the roll? Brute
    force above measures straight lines; this is what the ladder is really
    up against (case A: a 12.05" path on a 12" roll)."""
    from game import pathfinding
    tracker = TurnTracker(first_player="Player 2")
    tracker.phase_index = PHASES.index(PHASE_CHARGE)
    mc = MovementController(obstacles=state.obstacles, player_name="Player 2", turn_tracker=tracker,
                            all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    mc.select(charger.models[0])
    if mc.selected_squad is not charger:
        mc.selected_squad = charger
    mc.start_charge_move(roll, [target])
    keep_out = ad._charge_keep_out(charger, target, state.tokens)
    slots = ad._engagement_slots(target, ad.max_model_radius(charger), ad.PILE_IN_CLEARANCE_IN,
                                 legal=ad._engagement_slot_filter(charger, mc, keep_out))
    for m in charger.models:
        hard_obstacles = pathfinding.blocking_obstacles_for(m, mc.obstacles)
        hard_models = pathfinding.enemy_models_for(m, mc.all_tokens)
        start = (m.x_in, m.y_in)
        for s in slots:
            goal = (s[0], s[1])
            if math.dist(start, goal) > roll:
                continue
            if pathfinding._direct_line_clear(start, goal, hard_obstacles, hard_models, m.radius_in):
                return True
            route = pathfinding.find_route(start, goal, m.radius_in, roll, hard_obstacles, hard_models,
                                           mc.board_width_in, mc.board_height_in)
            if route and math.dist(route[-1], goal) <= 0.35:
                return True
    return False


def install(neutralize):
    """The A/B switches. `_charge_slot_first`: the approach never lands.
    `old_ring`: the engagement ring sampled one base apart in arc AND depth,
    as before 2026-09-09 (the legal filter and the de-dupe stay)."""
    real_slot_first = ad._charge_slot_first
    real_slots = ad._engagement_slots
    real_ring_step = ad._ENGAGEMENT_RING_STEP_IN

    def counted_slot_first(*a, **k):
        COUNTS["slot_first_calls"] += 1
        landed = False if "_charge_slot_first" in neutralize else real_slot_first(*a, **k)
        COUNTS["slot_first_landed"] += 1 if landed else 0
        return landed

    ad._charge_slot_first = counted_slot_first
    if "old_ring" in neutralize:
        def old_slots(target_squad, own_radius, clearance, *, arc_step_in=None, legal=None):
            ad._ENGAGEMENT_RING_STEP_IN = max(0.5, 2 * own_radius + 0.1)
            try:
                return real_slots(target_squad, own_radius, clearance,
                                  arc_step_in=max(0.5, 2 * own_radius + 0.1), legal=legal)
            finally:
                ad._ENGAGEMENT_RING_STEP_IN = real_ring_step
        ad._engagement_slots = old_slots


def main():
    scenes = 60
    hard = False
    diagnose = False
    neutralize = []
    for arg in sys.argv[1:]:
        if arg.startswith("--neutralize="):
            neutralize = [n for n in arg.split("=", 1)[1].split(",") if n]
        elif arg.startswith("--lead-tries="):
            ad._SLOT_FIRST_LEAD_TRIES = int(arg.split("=", 1)[1])
        elif arg.startswith("--ring-edge="):
            # The charge ring built from this edge distance (shipped: base
            # contact, ai/agent_driver._CHARGE_RING_INNER_EDGE_IN; 1.0 is the
            # pre-2026-09-09 ring at CHARGE_TARGET_CLEARANCE_IN).
            ad._CHARGE_RING_INNER_EDGE_IN = float(arg.split("=", 1)[1])
        elif arg == "--hard":
            hard = True
        elif arg == "--diagnose":
            diagnose = True
        else:
            scenes = int(arg)
    install(neutralize)
    possible = completed = engaged_total = 0
    failed_feasible = failed_infeasible = 0
    seed = 0
    while possible < scenes and seed < scenes * 20:
        roll = ROLLS[seed % len(ROLLS)]
        built = scene(seed, hard, roll)
        seed += 1
        if built is None:
            continue
        state, charger, target, bystanders = built
        keep_out = {b for b in bystanders}
        if not brute_force_possible(charger, target, roll, state.tokens, state.obstacles, keep_out):
            continue
        possible += 1
        home = [(m.x_in, m.y_in) for m in charger.models]
        ok, engaged = run_scene(state, charger, target, roll)
        completed += 1 if ok else 0
        engaged_total += engaged if ok else 0
        if diagnose and not ok:
            for m, (x, y) in zip(charger.models, home):
                m.x_in, m.y_in = x, y
            if path_feasible(state, charger, target, bystanders, roll):
                failed_feasible += 1
                print(f"  failed but PATH-feasible: seed {seed - 1}, {charger.name[2:]} "
                      f"{charger.models[0].profile.name} x{len(charger.models)} -> {target.models[0].profile.name} "
                      f"x{len(target.models)}, roll {roll}, gap {charger.min_distance_to(target):.1f}\", "
                      f"{len(bystanders)} bystanders, wall {'yes' if (hard and (seed - 1) % 2 == 0) else 'no'}")
            else:
                failed_infeasible += 1
    label = (f"neutralized {','.join(neutralize)}" if neutralize else "as shipped") + (", HARD" if hard else "")
    print(f"charge scenes ({label}): {possible} possible by brute force, {completed} completed "
          f"({100.0 * completed / max(1, possible):.0f}%), engaged models on completed charges {engaged_total}; "
          f"slot-first landed {COUNTS['slot_first_landed']} of {COUNTS['slot_first_calls']} ladders")
    if diagnose:
        print(f"  of the {possible - completed} failures: {failed_feasible} reachable by a legal PATH (the ladder's "
              f"ceiling), {failed_infeasible} not (straight-line possible only)")


if __name__ == "__main__":
    main()
