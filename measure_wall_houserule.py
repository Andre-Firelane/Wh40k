"""What would the proposed wall house rule actually buy the AI's movement?

The user's proposal, before implementing anything:

    "die KI darf ihre bewegung auf mauern beenden. Fahrzeuge duerfen auch auf
     mauern, und sie duerfen sich auch durch mauern durchbewegen. allerdings
     muessen sie 3" von ihrer bewegung abziehen, wenn sie mit mauern
     kollidieren. das wuerde schonmal viele fehler ursachen beseitigen oder?"

The honest answer needs numbers, because this codebase has repeatedly guessed
wrong about which half of a movement failure is the expensive one. So: run the
SAME stress test three ways over map 2's real terrain, and tally not just how
far units get but WHICH rule rejected each attempt.

  A  current rules   - 13.05 (cannot end on Dense) + 13.06 (only INFANTRY/
                       BEASTS/SWARM may cross it)
  B  end-on-walls    - 13.05 lifted, 13.06 still in force
  C  full proposal   - both lifted, minus WALL_MOVE_PENALTY_IN off the move
                       whenever a model's path actually crosses a wall

Two seams carry the whole rule, which is itself worth knowing before deciding:
`squad.model_terrain_violation()` answers "may it END here", and
`Obstacle.blocks_movement_for()` answers "may it PASS through". Nothing else
has to be touched to try the idea out.

The tally is the point. Terrain rejections happen per model in
MovementController._instant_violations() and are never written to the game log
(only coherency and "never reached the charge target" reach the log via
confirm_move), so the logs cannot answer this question at all - which is
exactly why the log tally shows 1707 coherency rejections and zero terrain ones.

STATUS: this is the DECISION-time measurement, kept for the reasoning above.
It patches the two seams itself and charges its own crude approximation of the
toll (whenever the straight line to the goal meets a wall, whether or not the
path taken does), which is why its mode C reads as a 7% loss of progress where
the shipped rule measures ~1%. The rule has since shipped as
config.VEHICLES_CROSS_WALLS / WALL_CROSSING_COST_IN, charged against the move
BUDGET in MovementController.clamp_move(). For the live behaviour use
measure_movement_fixes.py, and for the rule itself test_wall_crossing.py.

Run: python measure_wall_houserule.py [map_key]
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver
from game import config, geometry, maps, movement as movement_module, squad as squad_module
from game.factions import build_squad
from game.factions.orks import (
    BATTLEWAGON, BOYZ, DEFF_DREAD, GRETCHIN, KILL_RIG, TRUKK,
    WARBIKERS, WARBIKERS_ADD_POWER_KLAW,
)
from game.game_state import GameState
from game.movement import MovementController
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker

MAP_KEY = sys.argv[1] if len(sys.argv) > 1 else "map2"

# The user's number: what crossing a wall costs a vehicle.
WALL_MOVE_PENALTY_IN = 3.0

# A start point counts as "stalled" below this - the same threshold the AI's
# own movement ladder uses for "this attempt achieved nothing".
STALL_IN = 0.5


def units():
    """One squad per movement problem worth telling apart. The three biggest
    bases in the game, a mid vehicle, the reported bikes, and two INFANTRY
    controls that rule 13.06 already lets walk through walls - if the house
    rule is doing what it claims, the controls must NOT move."""
    return [
        ("Kill Rig (r2.10, M10, no pass-through)", build_squad(KILL_RIG, "Player 2", name="Kill Rig")),
        ("Battlewagon (r2.10, M10)", build_squad(BATTLEWAGON, "Player 2", name="Battlewagon")),
        ("Deff Dread (r1.18, M8)", build_squad(DEFF_DREAD, "Player 2", name="Deff Dread")),
        ("Trukk (r1.40, M12)", build_squad(TRUKK, "Player 2", name="Trukk")),
        ("Warbikers x3 (r0.98, M12)", build_squad(
            WARBIKERS, "Player 2", composition_index=0,
            choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}}, name="Warbikers")),
        ("Boyz x10 (INFANTRY control)", build_squad(BOYZ, "Player 2", name="Boyz")),
        ("Gretchin x11 (INFANTRY control)", build_squad(GRETCHIN, "Player 2", name="Gretchin")),
    ]


def start_points(state, sq, step=6.0):
    """Every legal spot on a coarse grid where this squad's lead model fits.

    Deliberately the whole board and not a deployment zone: the reported
    failures (bikes in a wall bay, the Deff Dread against the central ruin)
    happen mid-board, and one deployment gives a sample of one."""
    token = sq.models[0]
    pts = []
    x = 4.0
    while x < config.BOARD_WIDTH_IN - 4.0:
        y = 4.0
        while y < config.BOARD_HEIGHT_IN - 4.0:
            if not squad_module.model_terrain_violation(token, state.obstacles, x, y):
                pts.append((x, y))
            y += step
        x += step
    return pts


def goals():
    """Four directions of travel, so a result is not an artefact of everyone
    driving the same way across the same piece of terrain."""
    w, h = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
    return [(w / 2, h - 3.0), (w / 2, 3.0), (w - 3.0, h / 2), (3.0, h / 2)]


class Tally:
    def __init__(self):
        self.rejects = {}
        self.attempts = 0
        self.moved = []
        self.progress = []
        self.stalls = 0
        self.wall_penalty_in = 0.0

    def note(self, errors):
        for e in errors:
            if "Dense terrain" in e:
                key = "13.05 ended on a wall"
            elif "another model" in e:
                key = "03.01 ended on a model"
            elif "Engagement Range" in e:
                key = "03.04 ended in Engagement Range"
            else:
                key = e[:44]
            self.rejects[key] = self.rejects.get(key, 0) + 1


def shared_starts(state, squads):
    """The identical start set for all three modes.

    Has to be computed once and shared: the whole squad is checked, not just
    its lead model, and under current rules a start where a trailing model sits
    on a wall is not a legal position at all. Letting each mode filter for
    itself gave mode A 1200 attempts against B and C's 1512 - and the 312 extra
    were exactly the hardest starts, so A's stall rate was measured on an easier
    board than the others. Same starts, or the comparison says nothing."""
    out = {}
    for label, sq in squads:
        keep = []
        for (sx, sy) in start_points(state, sq):
            place(sq, sx, sy)
            if not any(squad_module.model_terrain_violation(m, state.obstacles)
                       for m in sq.models):
                keep.append((sx, sy))
        out[label] = keep
    return out


def run(mode, state, squads, starts, log=None):
    """`mode` in {"A", "B", "C"} - see the module docstring."""
    tally = Tally()
    per_unit = {}

    real_violation = squad_module.model_terrain_violation
    real_blocks = type(state.obstacles[0]).blocks_movement_for if state.obstacles else None
    real_instant = MovementController._instant_violations

    def instrumented(self, token, exclude_from_overlap=frozenset()):
        errors = real_instant(self, token, exclude_from_overlap=exclude_from_overlap)
        tally.note(errors)
        return errors

    def no_wall_violation(model, obstacles, x_in=None, y_in=None):
        return False

    def crosses_wall(self, token, x0, y0, x1, y1):
        walls = [o for o in self.obstacles if real_blocks(o, token)]
        return geometry.max_unblocked_fraction(
            (x0, y0), (x1, y1), walls, inflate_radius=token.radius_in) < 1.0

    MovementController._instant_violations = instrumented
    if mode in ("B", "C", "C0"):
        # Seam 1: rule 13.05, "may it END here".
        squad_module.model_terrain_violation = no_wall_violation
        movement_module.model_terrain_violation = no_wall_violation
    if mode in ("C", "C0"):
        # Seam 2: rule 13.06, "may it PASS through". Charged for below.
        type(state.obstacles[0]).blocks_movement_for = lambda self, token: False

    try:
        for label, sq in squads:
            token = sq.models[0]
            base_move = token.profile.movement_in
            unit_moved, unit_stalls, unit_progress = [], 0, 0.0
            for (sx, sy) in starts[label]:
                for (gx, gy) in goals():
                    place(sq, sx, sy)
                    state.tokens = list(sq.models)
                    tt = TurnTracker(first_player="Player 2")
                    tt.phase_index = PHASES.index(PHASE_MOVEMENT)
                    mc = MovementController(
                        obstacles=state.obstacles, player_name="Player 2", turn_tracker=tt,
                        all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
                        board_height_in=config.BOARD_HEIGHT_IN,
                    )
                    before = agent_driver._centroid(sq)
                    penalty = 0.0
                    if mode == "C":
                        # The user's 3": charged when the straight line from
                        # here to the goal actually crosses a wall. Applied by
                        # shortening the move BEFORE it starts, which is what
                        # "3" von ihrer bewegung abziehen" means.
                        mc.select(token)
                        if crosses_wall(mc, token, before[0], before[1], gx, gy):
                            penalty = min(WALL_MOVE_PENALTY_IN, base_move - 0.5)
                            for m in sq.models:
                                m.profile = _shorter(m.profile, penalty)
                    mc.select(token)
                    agent_driver._advance_toward(mc, sq, (gx, gy))
                    after = agent_driver._centroid(sq)
                    if penalty:
                        tally.wall_penalty_in += penalty
                        for m in sq.models:
                            m.profile = m.profile.__wrapped_original__
                    travelled = ((after[0] - before[0]) ** 2 + (after[1] - before[1]) ** 2) ** 0.5
                    d0 = ((gx - before[0]) ** 2 + (gy - before[1]) ** 2) ** 0.5
                    d1 = ((gx - after[0]) ** 2 + (gy - after[1]) ** 2) ** 0.5
                    tally.attempts += 1
                    tally.moved.append(travelled)
                    tally.progress.append(d0 - d1)
                    unit_moved.append(travelled)
                    unit_progress += d0 - d1
                    if travelled < STALL_IN:
                        tally.stalls += 1
                        unit_stalls += 1
            per_unit[label] = {
                "attempts": len(unit_moved), "stalls": unit_stalls,
                "median": sorted(unit_moved)[len(unit_moved) // 2] if unit_moved else 0.0,
                "progress": unit_progress,
            }
    finally:
        MovementController._instant_violations = real_instant
        squad_module.model_terrain_violation = real_violation
        movement_module.model_terrain_violation = real_violation
        if real_blocks is not None:
            type(state.obstacles[0]).blocks_movement_for = real_blocks
    tally.per_unit = per_unit
    return tally


_shorter_cache = {}


def _shorter(profile, penalty):
    """A copy of `profile` with movement_in reduced - the cheapest way to
    express "minus 3 inches" without touching MovementController."""
    key = (type(profile), penalty)
    if key not in _shorter_cache:
        cls = type(profile)
        sub = type(cls.__name__ + "Penalised", (cls,), {
            "movement_in": max(0.5, cls.movement_in - penalty),
        })
        sub.__wrapped_original__ = profile
        _shorter_cache[key] = sub
    sub = _shorter_cache[key]
    sub.__wrapped_original__ = profile
    return sub()


def place(sq, x, y, spacing=1.6):
    per_row = 5
    for i, m in enumerate(sq.models):
        m.x_in = x + (i % per_row) * spacing
        m.y_in = y + (i // per_row) * spacing


def report(label, tally):
    n = max(1, tally.attempts)
    moved = sorted(tally.moved)
    median = moved[len(moved) // 2] if moved else 0.0
    print(f"\n  {label}")
    print(f"    attempts                 : {tally.attempts}")
    print(f"    stalled (<{STALL_IN}\")         : {tally.stalls} ({100.0 * tally.stalls / n:.0f}%)")
    print(f"    median distance moved    : {median:.2f}\"")
    print(f"    total goal progress      : {sum(tally.progress):.0f}\"")
    if tally.wall_penalty_in:
        print(f"    movement paid in penalty : {tally.wall_penalty_in:.0f}\" total")
    print(f"    per-model rejections:")
    for key, count in sorted(tally.rejects.items(), key=lambda kv: -kv[1]):
        print(f"      {count:6d}  {key}")
    if not tally.rejects:
        print("      (none)")
    return {"stalls": tally.stalls, "attempts": tally.attempts,
            "median": median, "progress": sum(tally.progress),
            "rejects": dict(tally.rejects)}


def main():
    battle_map = maps.apply_to_config(maps.get(MAP_KEY))
    state = GameState()
    battle_map.build(state)
    print(f"=== {MAP_KEY}: {len(state.obstacles)} terrain features, "
          f"{sum(1 for o in state.obstacles if o.blocks_movement_for(build_squad(TRUKK, 'Player 2').models[0]))}"
          f" of them Dense ===")

    squads = units()
    starts = shared_starts(state, squads)
    print("start points per unit (identical in all three modes): "
          + ", ".join(f"{lbl.split(' (')[0]}={len(pts)}" for lbl, pts in starts.items()))

    out, per_unit = {}, {}
    for mode, label in (
        ("A", "A  current rules (13.05 + 13.06)"),
        ("B", "B  may END on walls (13.05 lifted)"),
        ("C", f"C  may end AND cross walls, -{WALL_MOVE_PENALTY_IN:.0f}\" when it does"),
        ("C0", "C0 same, but with NO penalty - brackets what the 3\" costs"),
    ):
        tally = run(mode, state, squads, starts)
        out[mode] = report(label, tally)
        per_unit[mode] = tally.per_unit

    print("\n  per unit, stalled %% / median distance:")
    for label, _sq in squads:
        cells = []
        for mode in ("A", "B", "C"):
            u = per_unit[mode][label]
            cells.append(f"{100.0 * u['stalls'] / max(1, u['attempts']):3.0f}% {u['median']:5.2f}\"")
        print(f"    {label:42s} " + "  ->  ".join(cells))

    print("\n" + "=" * 70)
    a, b, c = out["A"], out["B"], out["C"]
    print(f"stalled : A {100.0 * a['stalls'] / a['attempts']:.0f}%"
          f"  ->  B {100.0 * b['stalls'] / b['attempts']:.0f}%"
          f"  ->  C {100.0 * c['stalls'] / c['attempts']:.0f}%")
    print(f"median  : A {a['median']:.2f}\"  ->  B {b['median']:.2f}\"  ->  C {c['median']:.2f}\"")
    print(f"progress: A {a['progress']:.0f}\"  ->  B {b['progress']:.0f}\"  ->  C {c['progress']:.0f}\"")
    wall_a = a["rejects"].get("13.05 ended on a wall", 0)
    other_a = sum(v for k, v in a["rejects"].items() if k != "13.05 ended on a wall")
    print(f"\nof {wall_a + other_a} per-model rejections under current rules, "
          f"{wall_a} are the wall rule and {other_a} are not "
          f"({100.0 * wall_a / max(1, wall_a + other_a):.0f}% addressable by the house rule)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
