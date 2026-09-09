"""The reported movement failures, rebuilt from the game logs and re-run at the
SOURCE - the AI's own placement code against the board it actually saw.

WHY THIS EXISTS. Every movement report in this repo has been reproduced by
hand from `[move detail]` coordinates, and that systematically leaves out the
other fourteen units in the way - the dominant blocker, worth ~20 points of
movement quality (see measure_crowded_movement.py). This script parses the
log for the LAST logged position of EVERY unit before the reported event, puts
the whole board back - terrain included (measure_fly_penalty.py builds no
terrain at all: GameState() starts with no obstacles, so its +0.93" figure was
measured on an open field) - and drives the real _advance_toward() /
_run_charge_attempts() over it.

THE CASES (2026-09-07/08, Necrons as the AI):

  A   2 Lychguard 1 + Overlord charge 2 Krootox Rampagers on a 12" roll and
      fail from all 13 approaches (logs/game_20260907_224519.log:966, map3).
      Brute force over a 0.2" grid: 55 legal engaged end spots within 12" of
      the first model. The charge was possible.
  B   The C'tan (r1.57") charges Dire Avengers + Asurmen on a 6" roll and
      fails: 9 of its OWN Necron Warriors stand within 3" of the target
      (logs/game_20260908_204854.log:1187, map2). Brute force: 5 legal spots.
  C   The 21-model Necron Warriors + Technomancer blob moves toward the
      Central Objective and gains 2.71" of a 5" move (same log, line 326).
      The friendly clamp truncated 535 model targets; in 445 of those a free
      landing spot lay within 2" of the intended one.
  S1  Skorpekh Destroyers + Skorpekh Lord, the unit that split 3+1 at line 134
      (from deployment positions the log does not carry) - measured on its
      next move, line 313, over the same crowded board.
  S2  Lychguard + Overlord split 5+1 (same log, line 330).

WHAT IS PRINTED, per case: the real code's result (progress or engaged
models), the segment rejections by class, the friendly-clamp truncations and -
for every truncation - whether a FREE landing spot existed within 2" of the
intended point, and for a charge the brute-force feasibility (an upper bound:
straight-line reach, transit ignored). The RESULTS block at the end is one line
per case, for diffing a before/after pair.

RECONSTRUCTION ARTEFACTS, named rather than hidden: a unit that moved or died
AFTER its last logged line stands at a stale position here. Where such a token
overlaps the unit under test at its origin (case B: two Canoptek Wraiths on
the C'tan's start), it is removed and reported - the real game had it
somewhere else.

--neutralize=<name>[,<name>] replaces the named ai/agent_driver.py helper with
its "as if it did not exist" stand-in (see NEUTRAL) so a fix can be measured
against the world it replaced. An unknown name is an error, not a no-op.

Run:  python measure_reported_moves.py [A B C S1 S2] [--neutralize=...]
"""
import collections
import math
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import config, formation_layout, maps  # noqa: E402
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance, model_terrain_violation  # noqa: E402

LOG_0907 = "logs/game_20260907_224519.log"
LOG_0908 = "logs/game_20260908_204854.log"

CASES = {
    "A": dict(kind="charge", map="map3", p1="tau_recon", p2="necrons", log=LOG_0907, before=966,
              squad="2 Lychguard 1 + Overlord", target="1 Krootox Rampagers 1", roll=12),
    "B": dict(kind="charge", map="map2", p1="aeldari", p2="necrons", log=LOG_0908, before=1187,
              squad="2 C'tan Shard of the Void Dragon 1", target="1 Dire Avengers 1 + Asurmen", roll=6),
    "C": dict(kind="move", map="map2", p1="aeldari", p2="necrons", log=LOG_0908, before=326,
              squad="2 Necron Warriors 1 + Technomancer", goal=(30.0, 22.0)),
    # The reported 3+1 split (line 134-138) started from DEPLOYMENT positions,
    # which the log carries only as an anchor point - so the fixture is this
    # unit's next move on the same crowded board (line 313, positions from 142).
    "S1": dict(kind="move", map="map2", p1="aeldari", p2="necrons", log=LOG_0908, before=313,
               squad="2 Skorpekh Destroyers 1 + Skorpekh Lord", goal=(40.0, 20.0)),
    "S2": dict(kind="move", map="map2", p1="aeldari", p2="necrons", log=LOG_0908, before=330,
               squad="2 Lychguard 1 + Overlord", goal=(11.8, 26.4)),
}

# "As if the helper did not exist" stand-ins for --neutralize. A helper that
# is not listed here cannot be neutralised, on purpose: the pre-fix world of a
# helper is a decision about what it returns, not a generic None.
NEUTRAL = {
    "_free_landing_near": lambda *a, **k: None,
    "_repair_split_by_leash": lambda *a, **k: False,
    "_charge_slot_first": lambda *a, **k: False,
}

LANDING_RADII = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


def parse_board(path, before_line):
    """Last logged position of every unit strictly before `before_line`."""
    positions = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            if number >= before_line:
                break
            if "[move detail]" in line and "final positions:" in line:
                name = line.split("[move detail] ", 1)[1].split(" mode=", 1)[0]
                coords = [(float(a), float(b)) for a, b in
                          re.findall(r"\(([-\d.]+),([-\d.]+)\)",
                                     line.split("final positions:", 1)[1])]
                if coords:
                    positions[name] = coords
    return positions


def build(case):
    """The board as the AI saw it: terrain from the map, every logged unit at
    its last logged coordinates, casualties trimmed off the end of the unit
    (the log prints models in squad order)."""
    config.MAP = case["map"]
    battle_map = maps.get(case["map"])
    maps.apply_to_config(battle_map)
    from game import army_lists
    from game.game_state import GameState
    state = GameState()
    battle_map.build(state)
    squads = []
    army_lists.get(case["p1"]).build("Player 1", squads.append, state=state)
    army_lists.get(case["p2"]).build("Player 2", squads.append, state=state)
    board = parse_board(case["log"], case["before"])
    state.tokens = []
    by_name = {}
    for squad in squads:
        coords = board.get(squad.name)
        if not coords:
            continue
        if len(coords) < len(squad.models):
            squad.models = squad.models[:len(coords)]
        for model, (x_in, y_in) in zip(squad.models, coords):
            model.x_in, model.y_in = x_in, y_in
        state.tokens.extend(squad.models)
        by_name[squad.name] = squad
    return state, by_name


def drop_stale_overlaps(state, squad):
    """Remove foreign tokens standing ON the unit under test - a position the
    real game cannot have had (see the module docstring). Returns what went."""
    gone = []
    keep = []
    for token in state.tokens:
        if token.squad is squad:
            keep.append(token)
            continue
        if any(math.dist((m.x_in, m.y_in), (token.x_in, token.y_in)) < m.radius_in + token.radius_in
               for m in squad.models):
            gone.append(f"{token.squad.name} @({token.x_in:.1f},{token.y_in:.1f})")
            continue
        keep.append(token)
    state.tokens = keep
    return gone


def controller(state, phase, player="Player 2"):
    from game.movement import MovementController
    from game.turn import PHASES, TurnTracker
    tracker = TurnTracker(first_player=player)
    tracker.phase_index = PHASES.index(phase)
    return MovementController(
        obstacles=state.obstacles, player_name=player, turn_tracker=tracker,
        all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
        board_height_in=config.BOARD_HEIGHT_IN,
    )


def instrument(mc):
    """Count segment rejections by class, and every friendly-clamp truncation
    together with the nearest FREE landing spot around the intended point (the
    headroom a landing search has). Returns (rejections, clamp, restore)."""
    from ai import agent_driver as ad
    rejections = collections.Counter()
    orig_commit = mc.try_commit_segment

    def commit(token, exclude_from_overlap=frozenset()):
        ok, errs = orig_commit(token, exclude_from_overlap)
        if not ok:
            rejections[errs[0][:48]] += 1
        return ok, errs
    mc.try_commit_segment = commit

    clamp = collections.Counter()
    orig_clamp = ad._clamp_target_against_friendly_models

    def clamped(model, tx, ty, sq, mc_, placed, *args, **kwargs):
        rx, ry = orig_clamp(model, tx, ty, sq, mc_, placed, *args, **kwargs)
        if math.dist((rx, ry), (tx, ty)) <= 1e-6:
            clamp["clear"] += 1
            return rx, ry
        clamp["truncated"] += 1
        clamp["inches lost"] += math.dist((tx, ty), (rx, ry))
        budget = mc_.remaining_range.get(model.id, 0.0)
        blockers = [t for t in mc_.all_tokens if t is not model and t.squad is not None
                    and (t.squad is not sq or t in placed)]
        for radius in LANDING_RADII:
            hit = False
            for k in range(12):
                angle = 2 * math.pi * k / 12
                x, y = tx + radius * math.cos(angle), ty + radius * math.sin(angle)
                if math.dist((x, y), (model.x_in, model.y_in)) > budget + 1e-9:
                    continue
                if not formation_layout.on_board(x, y, model.radius_in):
                    continue
                if model_terrain_violation(model, mc_.obstacles, x, y):
                    continue
                if any(math.dist((x, y), (t.x_in, t.y_in)) < model.radius_in + t.radius_in + 0.02
                       for t in blockers):
                    continue
                hit = True
                break
            if hit:
                clamp[f"free spot within {radius}"] += 1
                break
        else:
            clamp["no free spot within 2.0"] += 1
        return rx, ry
    ad._clamp_target_against_friendly_models = clamped
    return rejections, clamp, lambda: setattr(ad, "_clamp_target_against_friendly_models", orig_clamp)


def legal_charge_end(model, x, y, tokens, obstacles, target, squad):
    if not formation_layout.on_board(x, y, model.radius_in):
        return False
    if model_terrain_violation(model, obstacles, x, y):
        return False
    for t in tokens:
        if t is model:
            continue
        if math.dist((x, y), (t.x_in, t.y_in)) < model.radius_in + t.radius_in:
            return False
        if (t.squad is not None and t.squad.owner != squad.owner and t.squad is not target
                and math.dist((x, y), (t.x_in, t.y_in)) - model.radius_in - t.radius_in <= ENGAGEMENT_RANGE_IN):
            return False
    return True


def brute_force_charge(squad, target, roll, tokens, obstacles, step=0.2):
    """Per own model: how many legal ENGAGED end spots lie within `roll` of it
    in a straight line (transit ignored - an upper bound), and the nearest."""
    rows = []
    cells = int(roll / step) + 1
    for model in squad.models:
        count, best = 0, None
        for i in range(-cells, cells + 1):
            for j in range(-cells, cells + 1):
                x, y = model.x_in + i * step, model.y_in + j * step
                d = math.dist((x, y), (model.x_in, model.y_in))
                if d > roll:
                    continue
                if not any(math.dist((x, y), (e.x_in, e.y_in)) - model.radius_in - e.radius_in
                           <= ENGAGEMENT_RANGE_IN for e in target.models):
                    continue
                if not legal_charge_end(model, x, y, tokens, obstacles, target, squad):
                    continue
                count += 1
                if best is None or d < best:
                    best = d
        rows.append((count, best))
    return rows


def counters_line(counter):
    return ", ".join(f"{k} {round(v, 1) if isinstance(v, float) else v}"
                     for k, v in sorted(counter.items()))


def run_charge(key, case, state, by):
    from ai import agent_driver as ad
    from game.turn import PHASE_CHARGE
    squad, target, roll = by[case["squad"]], by[case["target"]], case["roll"]
    print(f"\n=== {key}: {squad.name} ({len(squad.models)} models) charges {target.name} "
          f"({len(target.models)} models), roll {roll}\"  [{case['map']}, {case['log']}:{case['before']}]")
    gone = drop_stale_overlaps(state, squad)
    if gone:
        print(f"  reconstruction artefact removed (stale token on the origin): {gone}")
    mc = controller(state, PHASE_CHARGE)
    print(f"  straight-line gap {squad.min_distance_to(target):.2f}\"  routed gap "
          f"{ad._charge_gap(squad, target, mc):.2f}\"  blocked_by_walls={ad._blocked_by_walls(squad)}")
    feasible = brute_force_charge(squad, target, roll, state.tokens, state.obstacles)
    print("  brute force, legal engaged end spots within the roll per model: "
          + ", ".join(f"{n}" + (f" (nearest {d:.1f}\")" if d is not None else "") for n, d in feasible))
    rejections, clamp, restore = instrument(mc)
    origin = [(m.x_in, m.y_in) for m in squad.models]

    def reopen():
        mc.select(squad.models[0])
        if mc.selected_squad is not squad:
            mc.selected_squad = squad
        mc.start_charge_move(roll, [target])

    reopen()
    ok, errors = ad._run_charge_attempts(mc, squad, target, roll, reopen=reopen, confirm=mc.confirm_move)
    restore()
    engaged = sum(1 for m in squad.models if any(edge_distance(m, e) <= ENGAGEMENT_RANGE_IN
                                                 for e in target.models))
    moved = [math.dist(o, (m.x_in, m.y_in)) for o, m in zip(origin, squad.models)]
    print(f"  segment rejections: {counters_line(rejections) or 'none'}")
    print(f"  friendly clamp: {counters_line(clamp)}")
    verdict = "COMPLETED" if ok else "FAILED from every approach"
    print(f"  result: charge {verdict}; engaged {engaged}/{len(squad.models)}; closest "
          f"{squad.min_distance_to(target):.2f}\"; moved " + " ".join(f"{d:.1f}" for d in moved)
          + ("" if ok else f"; last error: {errors[0][:70] if errors else '-'}"))
    return f"{key}: charge {'completed' if ok else 'FAILED'}, engaged {engaged}/{len(squad.models)}, " \
           f"feasible spots {sum(n for n, _ in feasible)}"


def run_move(key, case, state, by):
    from ai import agent_driver as ad
    from game import movement
    from game.turn import PHASE_MOVEMENT
    squad, goal = by[case["squad"]], case["goal"]
    print(f"\n=== {key}: {squad.name} ({len(squad.models)} models) moves toward {goal}"
          f"  [{case['map']}, {case['log']}:{case['before']}]")
    gone = drop_stale_overlaps(state, squad)
    if gone:
        print(f"  reconstruction artefact removed (stale token on the origin): {gone}")
    mc = controller(state, PHASE_MOVEMENT)
    use_fly = movement.take_to_the_skies_pays(squad)
    allow_bulk = not all(m.profile.vehicle for m in squad.models)
    origin = [(m.x_in, m.y_in) for m in squad.models]
    before = ad._centroid(squad)
    budget = min(m.profile.movement_in for m in squad.models)
    achievable = min(math.dist(before, goal), budget)
    print(f"  centroid ({before[0]:.1f},{before[1]:.1f}), gap {math.dist(before, goal):.1f}\", M={budget}, "
          f"fly={use_fly}, coherency at start: {squad.check_coherency() or 'ok'}")
    trace = []

    def wrap(name):
        orig = getattr(ad, name)

        def wrapped(*args, **kwargs):
            result = orig(*args, **kwargs)
            trace.append((name, len(squad.check_coherency())))
            return result
        setattr(ad, name, wrapped)
        return orig
    originals = {n: wrap(n) for n in ("_place_per_model_pass", "_place_packed", "_place_per_model_route",
                                       "_place_rigid_route", "_creep_toward", "_regroup_move")}
    confirms = []
    orig_confirm = mc.confirm_move

    def confirm():
        orig_confirm()
        confirms.append(list(mc.errors))
    mc.confirm_move = confirm
    rejections, clamp, restore = instrument(mc)

    def start_fn():
        mc.start_move()
        if use_fly:
            mc.take_to_the_skies()
    mc.select(squad.models[0])
    if mc.selected_squad is not squad:
        mc.selected_squad = squad
    ok = ad._advance_toward(mc, squad, goal, start_move_fn=start_fn,
                            allow_bulk_fallback=allow_bulk, flying=use_fly)
    for name, orig in originals.items():
        setattr(ad, name, orig)
    restore()
    after = ad._centroid(squad)
    progress = math.dist(before, goal) - math.dist(after, goal)
    moved = [math.dist(o, (m.x_in, m.y_in)) for o, m in zip(origin, squad.models)]
    tried = collections.Counter(n for n, _ in trace)
    split = collections.Counter(n for n, e in trace if e > 0)
    print(f"  candidates tried: {dict(tried)}; ended split: {dict(split) or 'none'}")
    print(f"  confirm_move calls {len(confirms)}, rejected {sum(1 for c in confirms if c)}"
          + (f" (first: {next(c[0][:60] for c in confirms if c)})" if any(confirms) else ""))
    print(f"  segment rejections: {counters_line(rejections) or 'none'}")
    print(f"  friendly clamp: {counters_line(clamp)}")
    print(f"  result: moved={ok}; centroid progress {progress:.2f}\" of {achievable:.2f}\" achievable "
          f"({100 * progress / achievable if achievable else 0:.0f}%); models under 1\": "
          f"{sum(1 for d in moved if d < 1.0)}/{len(moved)}; final coherency: "
          f"{squad.check_coherency() or 'ok'}")
    return (f"{key}: progress {progress:.2f}\"/{achievable:.2f}\" ({100 * progress / achievable if achievable else 0:.0f}%), "
            f"coherency {'ok' if not squad.check_coherency() else 'BROKEN'}, moved={ok}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    keys = args or list(CASES)
    unknown = [k for k in keys if k not in CASES]
    if unknown:
        sys.exit(f"unknown case(s) {unknown}; choose from {list(CASES)}")
    from ai import agent_driver as ad
    for flag in flags:
        if flag.startswith("--neutralize="):
            for name in flag.split("=", 1)[1].split(","):
                if name not in NEUTRAL:
                    sys.exit(f"cannot neutralise {name!r}: not in NEUTRAL {sorted(NEUTRAL)}")
                if not hasattr(ad, name):
                    sys.exit(f"cannot neutralise {name!r}: ai/agent_driver.py has no such helper")
                setattr(ad, name, NEUTRAL[name])
                print(f"neutralised ai/agent_driver.{name}")
        else:
            sys.exit(f"unknown flag {flag}")
    results = []
    for key in keys:
        case = CASES[key]
        state, by = build(case)
        missing = [n for n in (case["squad"], case.get("target")) if n and n not in by]
        if missing:
            sys.exit(f"{key}: {missing} not on the reconstructed board")
        runner = run_charge if case["kind"] == "charge" else run_move
        results.append(runner(key, case, state, by))
    print("\nRESULTS")
    for line in results:
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
