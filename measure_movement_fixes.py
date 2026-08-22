"""A/B for the two movement changes, over map 2's real terrain.

WHAT THIS DOES NOT MEASURE - read before quoting a number from it as evidence
that movement is working. run() sets `state.tokens = list(sq.models)`: the
board it measures has exactly ONE unit standing on it. Blockage by the AI's own
army - the single biggest disruptor of its movement - cannot occur here by
construction. Measured A/B with identical code, terrain and goals, one unit
versus a whole army on the board: median share of achievable progress 85% vs
64%, moves under 60% of achievable 0% vs 50%, and the real game logs say 67%.
So this file's world is the optimistic one, and every "300/300 without
stalling" recorded in CLAUDE.md was taken in it.

It is still the right harness for what it was built for: per-unit geometry
regressions, where the question is whether ONE squad can get out of ONE awkward
spot. For "is the AI's movement any good", use measure_crowded_movement.py.


  1. rule 03.03's 2" connectivity built into the per-model placement
     (_anchored_slot/_close_up_to_placed in ai/agent_driver.py)
  2. every model may CROSS Dense terrain for config.WALL_CROSSING_COST_IN
     (config.VEHICLES_CROSS_WALLS; ending on it is still forbidden)

Each is switchable, so all four combinations are measured rather than the two
endpoints - otherwise "it got better" cannot be attributed to either change.

Reports the thing each change is supposed to fix (coherency rejections /
stalls) AND the thing it could quietly cost (distance moved, progress toward
the goal), because a movement fix that stops units moving is not a fix.

Run: python measure_movement_fixes.py [map_key]
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver
from game import config, maps, squad as squad_module
from game.factions import build_squad
from game.factions.orks import (
    BATTLEWAGON, BOYZ, BOYZ_BIG_CHOPPA_TO_POWER_KLAW, DEFF_DREAD, FLASH_GITZ,
    GRETCHIN, KILL_RIG, MEGANOBZ, STORMBOYZ, TANKBUSTAS, TRUKK, WARBIKERS,
    WARBIKERS_ADD_POWER_KLAW, WARBOSS,
)
from game import attached_units
from game.game_state import GameState
from game.movement import MovementController
from game.squad import edge_distance
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker

MAP_KEY = sys.argv[1] if len(sys.argv) > 1 else "map2"
STALL_IN = 0.5
# Consecutive moves per start point - see the loop in run() for why more
# than one matters.
TURNS = 4


def units():
    """The real Ork roster's movers, including the one unit that alone
    accounts for 45% of every coherency rejection in the logs."""
    out = [
        ("Kill Rig", build_squad(KILL_RIG, "Player 2", name="Kill Rig")),
        ("Battlewagon", build_squad(BATTLEWAGON, "Player 2", name="Battlewagon")),
        ("Deff Dread", build_squad(DEFF_DREAD, "Player 2", name="Deff Dread")),
        ("Trukk", build_squad(TRUKK, "Player 2", name="Trukk")),
        ("Warbikers x3", build_squad(
            WARBIKERS, "Player 2", composition_index=0,
            choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}}, name="Warbikers")),
        ("Boyz x10", build_squad(
            BOYZ, "Player 2", choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}}, name="Boyz")),
        ("Gretchin x11", build_squad(GRETCHIN, "Player 2", name="Gretchin")),
        ("Tankbustas", build_squad(TANKBUSTAS, "Player 2", name="Tankbustas")),
        ("Stormboyz", build_squad(STORMBOYZ, "Player 2", composition_index=1, name="Stormboyz")),
        ("Flash Gitz", build_squad(FLASH_GITZ, "Player 2", name="Flash Gitz")),
        ("Meganobz", build_squad(MEGANOBZ, "Player 2", name="Meganobz")),
    ]
    boyz = build_squad(BOYZ, "Player 2", name="Boyz 2")
    boss = build_squad(WARBOSS, "Player 2", name="Warboss")
    attached_units.attach(boss, boyz)
    out.append(("Boyz x10 + Warboss", boyz))
    return out


def place(sq, x, y, spacing=1.6, per_row=5):
    for i, m in enumerate(sq.models):
        m.x_in = x + (i % per_row) * spacing
        m.y_in = y + (i // per_row) * spacing


def start_points(state, sq, step=11.0):
    pts = []
    x = 5.0
    while x < config.BOARD_WIDTH_IN - 5.0:
        y = 5.0
        while y < config.BOARD_HEIGHT_IN - 5.0:
            place(sq, x, y)
            if not any(squad_module.model_terrain_violation(m, state.obstacles) for m in sq.models) \
                    and not sq.check_coherency():
                pts.append((x, y))
            y += step
        x += step
    return pts


def goals():
    w, h = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
    return [(w / 2, h - 4.0), (4.0, h / 2)]


def run(state, squads, starts, anchor_on, walls_on):
    """One configuration. `anchor_on` toggles change 1 by restoring the
    pre-fix slot function; `walls_on` toggles change 2 through its own config
    flag, which is where it lives anyway."""
    real_anchor = agent_driver._anchored_slot
    real_close = agent_driver._close_up_to_placed
    real_walls = config.VEHICLES_CROSS_WALLS
    if not anchor_on:
        agent_driver._anchored_slot = lambda model, slot, placed: slot
        agent_driver._close_up_to_placed = lambda *a, **k: None
    config.VEHICLES_CROSS_WALLS = walls_on

    coherency_rejects = {"conn": 0, "spread": 0}
    real_confirm = MovementController.confirm_move

    def counting_confirm(self, *a, **k):
        ok = real_confirm(self, *a, **k)
        for e in self.errors:
            if 'within 2.0"' in e:
                coherency_rejects["conn"] += 1
            if "spread too far apart" in e:
                coherency_rejects["spread"] += 1
        return ok

    MovementController.confirm_move = counting_confirm

    moved, progress, stalls, attempts = [], 0.0, 0, 0
    spreads, broken = [], 0
    per_unit = {}
    try:
        for label, sq in squads:
            u_moved, u_stalls, u_prog, u_spread, u_broken = [], 0, 0.0, [], 0
            for (sx, sy) in starts[label]:
                for (gx, gy) in goals():
                    # CONSECUTIVE turns from one start, carrying the formation
                    # forward. Resetting to a packed block before every attempt
                    # - which the first version of this did - measures the one
                    # case rule 03.03 never fails in, and reported no effect at
                    # all for that reason: a single move out of a tight block
                    # stays coherent almost whatever happens to it. Stretch
                    # ACCUMULATES over turns in a real game (measured: one move
                    # took a 10-model block from 5.34" to 7.41" of spread), and
                    # that is the state the connectivity rule actually bites in.
                    place(sq, sx, sy)
                    for _turn in range(TURNS):
                        state.tokens = list(sq.models)
                        tt = TurnTracker(first_player="Player 2")
                        tt.phase_index = PHASES.index(PHASE_MOVEMENT)
                        mc = MovementController(
                            obstacles=state.obstacles, player_name="Player 2", turn_tracker=tt,
                            all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN,
                        )
                        before = agent_driver._centroid(sq)
                        mc.select(sq.models[0])
                        agent_driver._advance_toward(mc, sq, (gx, gy))
                        after = agent_driver._centroid(sq)
                        d = ((after[0] - before[0]) ** 2 + (after[1] - before[1]) ** 2) ** 0.5
                        p = (((gx - before[0]) ** 2 + (gy - before[1]) ** 2) ** 0.5
                             - ((gx - after[0]) ** 2 + (gy - after[1]) ** 2) ** 0.5)
                        attempts += 1
                        moved.append(d); progress += p
                        u_moved.append(d); u_prog += p
                        if d < STALL_IN:
                            stalls += 1; u_stalls += 1
                    s = max(edge_distance(a, b) for i, a in enumerate(sq.models)
                            for b in sq.models[i + 1:]) if len(sq.models) > 1 else 0.0
                    spreads.append(s); u_spread.append(s)
                    if sq.check_coherency():
                        broken += 1; u_broken += 1
            per_unit[label] = {
                "attempts": len(u_moved), "stalls": u_stalls,
                "median": sorted(u_moved)[len(u_moved) // 2] if u_moved else 0.0,
                "progress": u_prog,
                "spread": sorted(u_spread)[len(u_spread) // 2] if u_spread else 0.0,
                "broken": u_broken, "runs": len(u_spread),
            }
    finally:
        MovementController.confirm_move = real_confirm
        agent_driver._anchored_slot = real_anchor
        agent_driver._close_up_to_placed = real_close
        config.VEHICLES_CROSS_WALLS = real_walls

    return {
        "attempts": attempts, "stalls": stalls,
        "median": sorted(moved)[len(moved) // 2] if moved else 0.0,
        "progress": progress,
        "conn": coherency_rejects["conn"], "spread": coherency_rejects["spread"],
        "final_spread": sorted(spreads)[len(spreads) // 2] if spreads else 0.0,
        "broken": broken, "runs": len(spreads),
        "per_unit": per_unit,
    }


def main():
    battle_map = maps.apply_to_config(maps.get(MAP_KEY))
    state = GameState()
    battle_map.build(state)
    squads = units()
    # Start points from the STRICTEST configuration, so every run is scored on
    # exactly the same board positions.
    real_walls = config.VEHICLES_CROSS_WALLS
    config.VEHICLES_CROSS_WALLS = False
    starts = {label: start_points(state, sq) for label, sq in squads}
    config.VEHICLES_CROSS_WALLS = real_walls
    total = sum(len(v) for v in starts.values()) * len(goals())
    print(f"=== {MAP_KEY}, {len(squads)} units, {total} attempts per configuration ===\n")

    configs = [
        ("BEFORE  (neither)", False, False),
        ("2\" anchored only ", True, False),
        ("walls only       ", False, True),
        ("AFTER   (both)   ", True, True),
    ]
    results = []
    print(f"{'configuration':20s} {'stalled':>9s} {'median':>8s} {'progress':>10s} "
          f"{'2\" rej':>8s} {'9\" rej':>8s} {'spread':>8s} {'broken':>10s}")
    for label, anchor, walls in configs:
        r = run(state, squads, starts, anchor, walls)
        results.append((label, r))
        print(f"{label:20s} {r['stalls']:4d} ({100.0*r['stalls']/max(1,r['attempts']):2.0f}%) "
              f"{r['median']:7.2f}\" {r['progress']:9.0f}\" {r['conn']:8d} {r['spread']:8d} "
              f"{r['final_spread']:7.2f}\" {r['broken']:4d}/{r['runs']:<5d}")

    before = results[0][1]
    after = results[-1][1]
    print("\n  per unit, coherency rejections BEFORE -> AFTER (2\" / 9\"):")
    for label, _sq in squads:
        b = before["per_unit"][label]; a = after["per_unit"][label]
        print(f"    {label:22s} stalled {b['stalls']:3d} -> {a['stalls']:3d}   "
              f"median {b['median']:5.2f}\" -> {a['median']:5.2f}\"   "
              f"progress {b['progress']:6.0f}\" -> {a['progress']:6.0f}\"   "
              f"broken {b['broken']:3d}/{b['runs']:<3d} -> {a['broken']:3d}/{a['runs']:<3d}")

    print("\n" + "=" * 72)
    print(f"2\" connectivity rejections : {before['conn']:5d} -> {after['conn']:5d}"
          f"  ({100.0 * (after['conn'] - before['conn']) / max(1, before['conn']):+.0f}%)")
    print(f"9\" spread rejections       : {before['spread']:5d} -> {after['spread']:5d}"
          f"  ({100.0 * (after['spread'] - before['spread']) / max(1, before['spread']):+.0f}%)")
    print(f"stalled                    : {before['stalls']:5d} -> {after['stalls']:5d}")
    print(f"total progress             : {before['progress']:5.0f}\" -> {after['progress']:5.0f}\""
          f"  ({100.0 * (after['progress'] - before['progress']) / max(1, before['progress']):+.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
