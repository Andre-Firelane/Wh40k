"""Who does the AI leave standing on its own home objective - and does the
turn-plan garrison pass make that better or worse?

WHY THIS EXISTS
---------------
User: "die ki soll fernkampfeinheiten stark bevorzugen, wenn es darum geht das
home objective zu halten. sie hat im letzten spiel dafuer die lychguard
benutzt, was voelliger quatsch ist. die immortals waeren perfekt. starke
fernkaempfer mit hoher reichweite."

That decision is made TWICE, one phase apart, and both halves were deciding it
on points alone:

  * ai/deployment_ai.py's home_garrison_squad() - who is standing there when
    deployment ends. On the Necron list the cheapest unit in the whole army is
    the Lychguard at 170 points, which is its melee anvil with no ranged
    weapons at all, so it got the job every single game.
  * ai/agent_driver.py's _lone_garrison_swaps() - who the turn plan leaves
    there. "Strictly cheaper than the holder" was the whole definition of a
    worthwhile swap, so it could only ever move the job DOWN the points list.
    Measured on the reported game (logs/game_20260826_234856.log lines
    124-125) it took P2 Home Objective off the 270-point Necron Warriors and
    handed it to the 170-point Lychguard.

So this measures both, and the second one against the REPORTED BOARD rather
than a unit standing on its own: the reason the Immortals were not chosen in
that game is that they were deployed at (13.8,10.4) and (50.3,10.4), 16" and
20" from an objective at (30,7) - far out of reach of a 5" move. A probe that
put an Immortals unit next to the objective would have reported a fix the real
game could not have used, and would have hidden that the DEPLOYMENT half is
the one that actually decides this.

A/B: --neutralize restores the pre-fix world at BOTH sources (points-only
ordering, points-only swap gate) and must change the answer.

Run: python measure_home_garrison.py [--neutralize]
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from ai import agent_driver, deployment_ai, observation
from game import army_lists, combat_focus, config, deployment, maps, pregame
from game.decision import DecisionManager
from game.dice import DiceManager
from game.game_state import GameState
from game.setup import SetupController
from game.turn import TurnTracker

NEUTRALIZE = "--neutralize" in sys.argv
OWNER = "Player 2"

# The AI deployment from the reported game, logs/game_20260826_234856.log
# lines 13-34. Kept as coordinates rather than re-run, because what has to be
# reproduced is the board the pass actually saw - including how far the
# Immortals were from the objective.
REPORTED_DEPLOYMENT = {
    "2 Doomsday Ark 1": (47.6, 9.9),
    "2 Canoptek Wraiths 1": (26.0, 10.0),
    "2 Lychguard 1 + Overlord": (30.0, 8.1),
    "2 Skorpekh Destroyers 1 + Skorpekh Lord": (10.0, 10.0),
    "2 Necron Warriors 1 + Technomancer": (34.0, 4.0),
    "2 Immortals 1 + Plasmancer": (13.8, 10.4),
    "2 Immortals 2 + Plasmancer": (50.3, 10.4),
    "2 Lokhust Destroyers 1 + Lokhust Lord": (44.0, 8.0),
}


class _PointsOnly:
    """combat_focus with the garrison band flattened - every unit ties on the
    band, so the points term decides on its own, exactly as it did before.

    A whole stand-in rather than one patched function: the pre-fix world had
    NO band anywhere, and neutralising only the ordering while leaving the swap
    gate banded would be half a probe - the failure mode this repo has recorded
    five times."""

    @staticmethod
    def home_garrison_rank(squad, reach_needed_in=None):
        return 0

    @staticmethod
    def is_assault_unit(squad):
        return False

    @staticmethod
    def is_shooting_specialist(squad):
        return False

    @staticmethod
    def ranged_to_melee_ratio(squad):
        return combat_focus.ranged_to_melee_ratio(squad)

    @staticmethod
    def best_ranged_reach_in(squad):
        return combat_focus.best_ranged_reach_in(squad)


def _neutralize():
    deployment_ai.home_garrison_squad.__globals__["combat_focus"] = _PointsOnly
    agent_driver._cheaper_garrison_candidates.__globals__["combat_focus"] = _PointsOnly


def _pregame(map_key, army_key):
    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    setup = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN)
    ctrl = pregame.PregameController(state, setup, DiceManager(), DecisionManager(),
                                     turn_tracker=TurnTracker(deferred_start=True))
    squads, decls = [], []

    def register(squad, destination=pregame.DEPLOY, transport=None):
        squads.append(squad)
        decls.append((squad, destination, transport))
        return squad

    army_lists.get(army_key).build(OWNER, register, state=state)
    ctrl.start({OWNER: squads})
    for squad, destination, transport in decls:
        ctrl.declare(squad, destination, transport_token=transport)
    return ctrl, state, squads


def _describe(squad, reach_needed):
    if squad is None:
        return "nobody"
    band = combat_focus.home_garrison_rank(squad, reach_needed)
    tag = ("SHOOTER", "neutral", "ASSAULT")[band]
    ratio = combat_focus.ranged_to_melee_ratio(squad)
    rs = "n/a" if ratio is None else ("inf" if ratio == float("inf") else "%.2f" % ratio)
    return ("%s  [%s] %s pts, ratio %s, reach %.0f\""
            % (squad.name, tag, squad.points, rs,
               combat_focus.best_ranged_reach_in(squad)))


def part1_deployment():
    """Which unit each list designates to hold home, on each map."""
    print("=" * 78)
    print("PART 1 - deployment: who is designated to hold the home objective")
    print("=" * 78)
    for map_key in ("map1", "map2", "map3"):
        for army_key in ("necrons", "orks", "aeldari"):
            ctrl, state, _ = _pregame(map_key, army_key)
            own = deployment.zone_for(getattr(state, "deployment_zones", ()), OWNER)
            home = deployment_ai._home_objective(OWNER, state.objectives, own)
            if home is None:
                print("  %s %-9s  no home objective" % (map_key, army_key))
                continue
            reach = observation.garrison_reach_needed_in(home, state.objectives)
            pick = deployment_ai.home_garrison_squad(ctrl, OWNER, state.objectives, own)
            print("  %s %-9s  needs %5.1f\" of reach -> %s"
                  % (map_key, army_key, reach, _describe(pick, reach)))
    print()


def part2_turn_plan():
    """The reported turn: does the garrison pass hand P2 Home to the Lychguard?"""
    print("=" * 78)
    print("PART 2 - turn plan on the REPORTED board (logs/game_20260826_234856.log)")
    print("=" * 78)
    ctrl, state, squads = _pregame("map2", "necrons")
    by_name = {sq.name: sq for sq in squads}

    placed = []
    for name, (x, y) in REPORTED_DEPLOYMENT.items():
        squad = by_name.get(name)
        if squad is None:
            print("  !! roster no longer fields %s - update this probe" % name)
            continue
        for i, model in enumerate(squad.models):
            model.x_in = x + (i % 4) * 1.2
            model.y_in = y + (i // 4) * 1.2
            state.tokens.append(model)
        placed.append(squad)

    own = deployment.zone_for(getattr(state, "deployment_zones", ()), OWNER)
    home = deployment_ai._home_objective(OWNER, state.objectives, own)
    reach = observation.garrison_reach_needed_in(home, state.objectives)
    hx, hy = agent_driver._objective_centre(home)
    print("  %s @(%.1f,%.1f), needs %.1f\" of reach\n" % (home.name, hx, hy, reach))

    holder = by_name["2 Necron Warriors 1 + Technomancer"]
    plan = {"unit_plans": {holder.name: {"role": "hold", "position": [hx, hy]}}}

    print("  who can reach the objective at all this turn:")
    for squad in placed:
        gap, rch = agent_driver._reach_to_point(squad, (hx, hy))
        ok = "yes" if gap <= rch else "no "
        print("    %s  gap %5.1f\" vs move %4.1f\"   %s"
              % (ok, gap, rch, _describe(squad, reach)))
    print()

    swaps = agent_driver._lone_garrison_swaps(plan, by_name, state, OWNER)
    if not swaps:
        print("  RESULT: no swap - %s keeps the garrison" % holder.name)
    for objective, held, replacement in swaps:
        print("  RESULT: %s" % objective.name)
        print("    off:  %s" % _describe(held, reach))
        print("    onto: %s" % _describe(replacement, reach))
    print()


if __name__ == "__main__":
    if NEUTRALIZE:
        _neutralize()
        print(">>> NEUTRALIZED: points-only ordering at both sources "
              "(the pre-fix world)\n")
    part1_deployment()
    part2_turn_plan()
