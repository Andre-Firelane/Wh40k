"""Do the AI's big models get a clear lane off the deployment line?

User report, twice: "die ki sollte sehr große fahrzeuge eher in der ersten
reihe aufstellen, nicht in der 2ten. dann kann auch nicht so viel im weg sein
beim losfahren" and, with evidence, "deffdread und battlewagon haben sich in
zug 1 kaum bewegt... dann kommen sie durch die eigenen einheiten nicht durch
und werden ständig blockiert".

Measures the finished deployment rather than arguing about the scorer:

  * forward RANK - is this model in the front row or behind its own army;
  * lane blockage - how many friendly models sit in the corridor it has to
    drive through on its first move (its own width plus a model's, out to its
    Movement characteristic);
  * and then actually moves it, so the claim is checked against inches
    travelled and not only against geometry.

Deploys both armies with the real pre-game AI on the real board, so the answer
is about the shipping scorer and not a reconstruction of it.

Run: python measure_vehicle_lanes.py [map_key]
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver, deployment_ai
from game import config, deployment, maps, pregame
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import (
    BATTLEWAGON, BEAST_SNAGGA_BOYZ, BOYZ, DEFF_DREAD, FLASH_GITZ, GRETCHIN,
    KILL_RIG, MEGANOBZ, STORMBOYZ, TANKBUSTAS, TRUKK, WARBIKERS,
    WARBIKERS_ADD_POWER_KLAW,
)
from game.factions.tau_empire import (
    BREACHER_TEAM, GHOSTKEEL_BATTLESUIT, KROOT_CARNIVORES, PATHFINDER_TEAM,
    RIPTIDE_BATTLESUIT, STEALTH_BATTLESUITS, STRIKE_TEAM,
)
from game.game_state import GameState
from game.movement import MovementController
from game.setup import SetupController
from game.squad import max_model_radius
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker

MAP_KEY = sys.argv[1] if len(sys.argv) > 1 else "map2"
# Clearance a model wants beside it to count a lane as open.
LANE_MARGIN_IN = 0.4


def army(owner):
    if owner == "Player 2":
        return [
            build_squad(KILL_RIG, owner, name="2 Kill Rig 1"),
            build_squad(BATTLEWAGON, owner, name="2 Battlewagon 1"),
            build_squad(DEFF_DREAD, owner, name="2 Deff Dread 1"),
            build_squad(TRUKK, owner, name="2 Trukk 1"),
            build_squad(TRUKK, owner, name="2 Trukk 2"),
            build_squad(WARBIKERS, owner, composition_index=0,
                        choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}},
                        name="2 Warbikers 1"),
            build_squad(WARBIKERS, owner, composition_index=0,
                        choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}},
                        name="2 Warbikers 2"),
            build_squad(GRETCHIN, owner, name="2 Gretchin 1"),
            build_squad(GRETCHIN, owner, name="2 Gretchin 2"),
            build_squad(TANKBUSTAS, owner, name="2 Tankbustas 1"),
            build_squad(FLASH_GITZ, owner, name="2 Flash Gitz 1"),
            build_squad(BOYZ, owner, name="2 Boyz 1"),
            build_squad(MEGANOBZ, owner, name="2 Meganobz 1"),
            build_squad(STORMBOYZ, owner, composition_index=1, name="2 Stormboyz 1"),
            build_squad(BEAST_SNAGGA_BOYZ, owner, name="2 Beast Snagga Boyz 1"),
        ]
    return [
        build_squad(RIPTIDE_BATTLESUIT, owner, name="1 Riptide Battlesuit 1"),
        build_squad(GHOSTKEEL_BATTLESUIT, owner, name="1 Ghostkeel Battlesuit 1"),
        build_squad(STRIKE_TEAM, owner, name="1 Strike Team 1"),
        build_squad(BREACHER_TEAM, owner, name="1 Breacher Team 1"),
        build_squad(KROOT_CARNIVORES, owner, name="1 Kroot Carnivores 1"),
        build_squad(PATHFINDER_TEAM, owner, name="1 Pathfinder Team 1"),
        build_squad(STEALTH_BATTLESUITS, owner, name="1 Stealth Battlesuits 1"),
    ]


def deploy(map_key):
    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    setup = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    tracker = TurnTracker(deferred_start=True)
    ctrl = pregame.PregameController(state, setup, DiceManager(), DecisionManager(),
                                     turn_tracker=tracker)
    armies = {o: army(o) for o in ("Player 1", "Player 2")}
    ctrl.start(armies)
    for owner in armies:
        for squad in armies[owner]:
            ctrl.declare(squad, pregame.DEPLOY)
        ctrl.finish_formations_for(owner)
    ctrl.state = pregame.DEPLOYING

    guard = 0
    while ctrl.state == pregame.DEPLOYING and guard < 120:
        guard += 1
        owner = ctrl.active_player
        pending = ctrl.pending_units(owner)
        if not pending:
            break
        squad = sorted(pending, key=deployment_ai.deployment_order_key)[0]
        if not deployment_ai.auto_deploy_squad(
                ctrl, setup, squad, config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN,
                objectives=state.objectives):
            ctrl.give_up_on(squad)
    return state, armies, tracker


def blockers_in_lane(squad, state, forward):
    """Friendly models standing in the strip this unit must drive through on
    its first move: as wide as its base plus a model's, as long as its move."""
    cx = sum(m.x_in for m in squad.models) / len(squad.models)
    cy = sum(m.y_in for m in squad.models) / len(squad.models)
    radius = max_model_radius(squad)
    length = squad.models[0].profile.movement_in
    fx, fy = forward
    count = 0
    for token in state.tokens:
        if token.squad is None or token.squad is squad or token.squad.owner != squad.owner:
            continue
        dx, dy = token.x_in - cx, token.y_in - cy
        along = dx * fx + dy * fy
        across = abs(-dx * fy + dy * fx)
        if 0.0 < along <= length and across <= radius + token.radius_in + LANE_MARGIN_IN:
            count += 1
    return count


def main():
    state, armies, tracker = deploy(MAP_KEY)
    tracker.start_battle("Player 2")
    tracker.phase_index = PHASES.index(PHASE_MOVEMENT)

    for owner in ("Player 2", "Player 1"):
        zone = deployment.zone_for(state.deployment_zones, owner)
        forward = deployment_ai._forward_axis(zone, config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
        mine = [s for s in armies[owner] if any(m in state.tokens for m in s.models)]
        depth = {}
        for squad in mine:
            cx = sum(m.x_in for m in squad.models) / len(squad.models)
            cy = sum(m.y_in for m in squad.models) / len(squad.models)
            depth[squad.name] = cx * forward[0] + cy * forward[1]
        order = sorted(mine, key=lambda s: -depth[s.name])

        print(f"\n=== {owner} ({MAP_KEY}) - frontmost first ===")
        print(f"{'rank':>4s} {'unit':34s} {'base':>6s} {'role':>8s} {'lane':>5s} {'turn 1':>8s}")
        lane_by_name = {}
        for rank, squad in enumerate(order, 1):
            radius = max_model_radius(squad)
            role = deployment_ai._deployment_role(squad)
            blocked = blockers_in_lane(squad, state, forward)
            lane_by_name[squad.name] = blocked
            # Every unit is measured against the DEPLOYED board, so each trial
            # move is undone afterwards. Without this each later unit is scored
            # against a board its predecessors have already cleared out of,
            # which flatters exactly the thing being measured.
            snapshot = [(m.x_in, m.y_in) for m in squad.models]
            before = agent_driver._centroid(squad)
            mc = MovementController(
                obstacles=state.obstacles, player_name=owner, turn_tracker=tracker,
                all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
                board_height_in=config.BOARD_HEIGHT_IN,
            )
            tracker.set_active(owner)
            mc.select(squad.models[0])
            goal = (before[0] + forward[0] * 40.0, before[1] + forward[1] * 40.0)
            agent_driver._advance_toward(mc, squad, goal)
            after = agent_driver._centroid(squad)
            travelled = ((after[0] - before[0]) ** 2 + (after[1] - before[1]) ** 2) ** 0.5
            for model, (x, y) in zip(squad.models, snapshot):
                model.x_in, model.y_in = x, y
            flag = "  <-- big" if radius >= 1.18 else ""
            print(f"{rank:4d} {squad.name:34s} {radius:5.2f}\" {role:>8s} {blocked:5d} "
                  f"{travelled:7.2f}\"{flag}")

        big = [s for s in mine if max_model_radius(s) >= 1.18]
        if big:
            ranks = [order.index(s) + 1 for s in big]
            lanes = [lane_by_name[s.name] for s in big]
            print(f"  big models: mean forward rank {sum(ranks)/len(ranks):.1f} of {len(order)}, "
                  f"mean blockers in lane {sum(lanes)/len(lanes):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
