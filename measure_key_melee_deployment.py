"""Where does a melee CHARACTER deploy, and is its conditional Lone Operative on?

A/B over all four maps for the two armies that field such a unit, with the whole
pre-fix world restored for the BEFORE column:

  * ai/deployment_ai._deployment_role() sent every CHARACTER/VEHICLE/MONSTER to
    "key" - "hide it" - before the assault test at the bottom could see it.
  * deployment_score() had no term for a CONDITIONAL Lone Operative (rule 24.24,
    game/conditional_lone_operative.py), so nothing preferred a spot where the
    ability is actually ON.

Exists because the report was a position on a board and the fix is a sort-order
change, so the only way to know whether it did anything is to deploy the real
lists and measure the finished table (user: "warum ist ghakhull so weit hinten
platziert wurden? starke nahkampf einheit. der muss nach vorne." and "Ghazkhull
hat eigentlich Lone Op durch seine Fähigkeit").

Both carriers are measured, not only the reported one: Ghazghkull Thraka (Da
Grand Warlord's Ladz, role "key" before) and the Daemon Prince of Nurgle (Death
Guard Defenders, role "heavy" both before and after - he is in here as the
control, because a term that moved HIM would be a regression, not a fix).

Run: python measure_key_melee_deployment.py
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from ai import deployment_ai
from game import (army_io, army_roster, combat_focus, conditional_lone_operative, config,
                  deployment, maps, pregame, status_effects)
from game.decision import DecisionManager
from game.dice import DiceManager
from game.game_state import GameState
from game.setup import SetupController
from game.turn import TurnTracker

ARMIES = "armies"
ENEMY_LIST = "tau_montka"
#: The lists that field a unit with a conditional Lone Operative source.
CASES = (("orks", "Ghazghkull"), ("death_guard", "Daemon Prince"))
MAPS = ("map1", "map2", "map3", "map4")


def _legacy_role(squad):
    """_deployment_role() as it stood before the melee-threat exception: every
    CHARACTER/VEHICLE/MONSTER is "key", whatever its fists are worth."""
    if deployment_ai.is_heavy(squad):
        return "heavy"
    profile = squad.models[0].profile if squad.models else None
    if profile is not None and (profile.vehicle or profile.character
                                or getattr(profile, "monster", False)):
        return "key"
    points = squad.points or 0
    if points >= 100 and len(squad.models) <= 3:
        return "key"
    if deployment_ai._bulk_ranged_range(squad) >= deployment_ai.SHOOTER_RANGE_IN:
        return "shooter"
    if combat_focus.is_assault_unit(squad):
        return "assault"
    return "screen"


def _build(state, ctrl, owner, list_key):
    af = army_io.load(os.path.join(ARMIES, list_key + ".json"))
    built = []

    def register(squad, destination=pregame.DEPLOY, transport=None):
        built.append((squad, destination, transport))

    army_roster.build(af.roster, owner, register, list_name=list_key, state=state)
    return built


def deploy(map_key, p2_list, fixed):
    """Run rule 03.01's alternating deployment for both armies. `fixed=False`
    restores the pre-fix world - BOTH halves at once, so "BEFORE" really is the
    old behaviour rather than the old role plus the new scorer term."""
    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    setup = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN)
    tracker = TurnTracker(deferred_start=True)
    ctrl = pregame.PregameController(
        state, setup, DiceManager(), DecisionManager(), turn_tracker=tracker)

    armies, declarations = {}, {}
    for owner, list_key in (("Player 1", ENEMY_LIST), ("Player 2", p2_list)):
        built = _build(state, ctrl, owner, list_key)
        armies[owner] = [squad for squad, _, _ in built]
        declarations[owner] = built

    ctrl.start(armies)
    for owner, built in declarations.items():
        for squad, destination, transport in built:
            if transport is not None:
                ctrl.declare(squad, destination, transport_token=transport)
            else:
                ctrl.declare(squad, destination)
        ctrl.finish_formations_for(owner)
    ctrl.state = pregame.DEPLOYING

    original_role = deployment_ai._deployment_role
    original_grant = conditional_lone_operative.would_grant_at
    if not fixed:
        deployment_ai._deployment_role = _legacy_role
        conditional_lone_operative.would_grant_at = lambda *a, **k: False
    try:
        guard = 0
        while ctrl.state == pregame.DEPLOYING and guard < 80:
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
    finally:
        deployment_ai._deployment_role = original_role
        conditional_lone_operative.would_grant_at = original_grant

    own_zone = deployment.zone_for(state.deployment_zones, "Player 2")
    fx, fy = deployment_ai._forward_axis(own_zone, config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
    ox, oy = deployment_ai._zone_centroid(own_zone, config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
    enemies = [s for s in armies["Player 1"] if any(m in state.tokens for m in s.models)]

    rows = []
    for squad in armies["Player 2"]:
        if not any(m in state.tokens for m in squad.models):
            continue
        cx = sum(m.x_in for m in squad.models) / len(squad.models)
        cy = sum(m.y_in for m in squad.models) / len(squad.models)
        rows.append({
            "name": squad.name,
            "forward": (cx - ox) * fx + (cy - oy) * fy,
            "pos": (round(cx, 1), round(cy, 1)),
            "lone": status_effects.lone_operative_range(squad, state.tokens),
            "enemy": min((squad.min_distance_to(e) for e in enemies), default=float("nan")),
        })
    rows.sort(key=lambda r: -r["forward"])
    for i, row in enumerate(rows, 1):
        row["rank"] = "%d/%d" % (i, len(rows))
    return rows


def main():
    forward_gain, lone_gained, regressions, traded = [], 0, [], []
    for p2_list, carrier in CASES:
        for map_key in MAPS:
            after = deploy(map_key, p2_list, True)
            before = deploy(map_key, p2_list, False)
            for row in after:
                if carrier not in row["name"]:
                    continue
                was = next(r for r in before if r["name"] == row["name"])
                gain = row["forward"] - was["forward"]
                forward_gain.append(gain)
                lone_gained += bool(row["lone"]) and not was["lone"]
                # A lost Lone Operative is only a REGRESSION when the unit did
                # not get anything for it. The trade is deliberate and was
                # measured before it was taken: the pre-fix Lone Operative on
                # map3 came from the back corner, where standing beside the
                # home garrison switched the ability on by accident - and the
                # user's requirement is the other thing ("auf jeden fall muss
                # der vorne stehen"). Ranking the ability ABOVE forward
                # progress was tried and rejected: it kept the ability on all
                # four maps and left him at rank 7/9 and 8/9 on two of them,
                # which is the reported problem again.
                if bool(was["lone"]) and not row["lone"]:
                    if gain > 0.5:
                        traded.append("%s %s traded its rear-corner Lone Operative for "
                                      "%+.2f\" of ground" % (p2_list, map_key, gain))
                    else:
                        regressions.append("%s %s lost its Lone Operative for nothing"
                                           % (p2_list, map_key))
                if gain < -0.5:
                    regressions.append("%s %s went %.2f\" BACKWARD" % (p2_list, map_key, gain))
                print("%-11s %s  %s" % (p2_list, map_key, row["name"]))
                print("    before: %-14s rank %-6s forward %6.2f\"  enemy %5.1f\"  lone %s"
                      % (was["pos"], was["rank"], was["forward"], was["enemy"], was["lone"]))
                print("    after : %-14s rank %-6s forward %6.2f\"  enemy %5.1f\"  lone %s"
                      % (row["pos"], row["rank"], row["forward"], row["enemy"], row["lone"]))

    print("\n%d placements measured" % len(forward_gain))
    print("forward progress: %+.2f\" on average, best %+.2f\", worst %+.2f\""
          % (sum(forward_gain) / len(forward_gain), max(forward_gain), min(forward_gain)))
    print("conditional Lone Operative switched ON that was off before: %d" % lone_gained)
    for line in traded:
        print("traded: " + line)
    if regressions:
        print("\nREGRESSIONS:")
        for line in regressions:
            print("  " + line)
        return 1
    print("no placement moved backward, and no Lone Operative was lost without "
          "ground bought for it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
