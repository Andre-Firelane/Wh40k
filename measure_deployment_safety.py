"""How exposed is the AI's deployment, and how much of rule 13.09 does it use?

A/B: runs the whole AI deployment for both armies on both maps, once with the
current scorer and once with the scorer's safety terms disabled (the pre-fix
behaviour), and reports exposure and Hidden coverage for each.

Exists because the report that prompted the change was qualitative ("teilweise
sehr offen hingestellt") and the fix is a sort-order change - the only way to
know whether it did anything is to measure the finished board.

Run: python measure_deployment_safety.py
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from ai import deployment_ai, observation
from game import config, deployment, maps, pregame, status_effects
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import (
    BOYZ,
    BOYZ_BIG_CHOPPA_TO_POWER_KLAW,
    DEFF_DREAD,
    GRETCHIN,
    STORMBOYZ,
    STORMBOYZ_CHOPPA_TO_POWER_KLAW,
    TANKBUSTAS,
    TRUKK,
    WARBIKERS,
    WARBIKERS_ADD_POWER_KLAW,
)
from game.factions.tau_empire import (
    GHOSTKEEL_BATTLESUIT,
    KROOT_CARNIVORES,
    STEALTH_BATTLESUITS,
    STRIKE_TEAM,
)
from game.game_state import GameState
from game.setup import SetupController
from game.squad import max_model_radius
from game.turn import TurnTracker


def _army(owner):
    if owner == "Player 2":
        return [
            build_squad(GRETCHIN, owner, name="2 Gretchin 1"),
            build_squad(STORMBOYZ, owner, composition_index=1,
                        choices={"Boss Nob": {STORMBOYZ_CHOPPA_TO_POWER_KLAW: 1}}, name="2 Stormboyz 1"),
            build_squad(WARBIKERS, owner, composition_index=0,
                        choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}}, name="2 Warbikers 1"),
            build_squad(BOYZ, owner, choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}}, name="2 Boyz 1"),
            build_squad(DEFF_DREAD, owner, name="2 Deff Dread 1"),
            build_squad(TRUKK, owner, name="2 Trukk 1"),
            build_squad(TANKBUSTAS, owner, name="2 Tankbustas 1"),
        ]
    return [
        build_squad(STRIKE_TEAM, owner, name="1 Strike Team 1"),
        build_squad(STRIKE_TEAM, owner, name="1 Strike Team 2"),
        build_squad(KROOT_CARNIVORES, owner, name="1 Kroot Carnivores 1"),
        build_squad(KROOT_CARNIVORES, owner, name="1 Kroot Carnivores 2"),
        build_squad(STEALTH_BATTLESUITS, owner, name="1 Stealth Battlesuits 1"),
        build_squad(GHOSTKEEL_BATTLESUIT, owner, name="1 Ghostkeel Battlesuit 1"),
    ]


def _run(map_key, safety_on):
    """Deploy both armies and report per-unit safety. `safety_on=False`
    reproduces the pre-fix ordering by neutralising the two safety terms."""
    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    setup = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    tt = TurnTracker(deferred_start=True)
    ctrl = pregame.PregameController(
        state, setup, DiceManager(), DecisionManager(), turn_tracker=tt,
    )
    armies = {o: _army(o) for o in ("Player 1", "Player 2")}
    ctrl.start(armies)
    for owner in armies:
        for squad in armies[owner]:
            ctrl.declare(squad, pregame.DEPLOY)
        ctrl.finish_formations_for(owner)
    ctrl.state = pregame.DEPLOYING

    original_score = deployment_ai.deployment_score
    original_dense = deployment_ai._in_dense_area
    if not safety_on:
        # Blind the module to Dense areas entirely. This is what makes the
        # comparison honest: it disables BOTH the score's 13.09 term AND the
        # hidden-constrained placement pass at once, so "BEFORE" really is the
        # pre-fix behaviour rather than the old sort order plus the new pass.
        deployment_ai._in_dense_area = lambda *args, **kwargs: False
        # The pre-fix key: strict forward-first for screens, and no 13.09 term
        # anywhere. Rebuilt here rather than kept in the shipping code, so the
        # comparison is against the real old ordering.
        def legacy(point, squad, pregame_ctrl, context):
            x, y = point
            role = context["roles"][id(squad)]
            fx, fy = context["forward"]
            ox, oy = context["origin"]
            forward = (x - ox) * fx + (y - oy) * fy
            to_obj = deployment_ai._nearest_uncontrolled_objective_distance(
                point, squad, context["objectives"])
            exposure = observation.zone_visibility_from_point(
                x, y, max_model_radius(squad), squad.owner, context["enemy_probes"],
                context["obstacles"], context["terrain_areas"], context["all_tokens"])
            if role == "screen":
                return (-round(forward, 1), round(to_obj, 1), exposure)
            if role == "shooter":
                lo, hi = deployment_ai.SHOOTER_IDEAL_EXPOSURE
                return (0 if lo <= exposure <= hi else 1, exposure, -round(forward, 1), round(to_obj, 1))
            return (exposure, -round(forward, 1), round(to_obj, 1))
        deployment_ai.deployment_score = legacy

    try:
        guard = 0
        while ctrl.state == pregame.DEPLOYING and guard < 60:
            guard += 1
            owner = ctrl.active_player
            pending = ctrl.pending_units(owner)
            if not pending:
                break
            squad = sorted(pending, key=deployment_ai.deployment_order_key)[0]
            if not deployment_ai.auto_deploy_squad(
                ctrl, setup, squad, config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN,
                objectives=state.objectives,
            ):
                ctrl.give_up_on(squad)
    finally:
        deployment_ai.deployment_score = original_score
        deployment_ai._in_dense_area = original_dense

    rows = []
    for owner in armies:
        probes = []
        for zone in deployment.enemy_zones(state.deployment_zones, owner):
            probes.extend(deployment_ai._zone_probe_points(zone))
        forward_axis = deployment_ai._forward_axis(
            deployment.zone_for(state.deployment_zones, owner),
            config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN,
        )
        for squad in armies[owner]:
            if not any(m in state.tokens for m in squad.models):
                continue
            cx = sum(m.x_in for m in squad.models) / len(squad.models)
            cy = sum(m.y_in for m in squad.models) / len(squad.models)
            exposure = observation.zone_visibility_from_point(
                cx, cy, max_model_radius(squad), owner, probes,
                state.obstacles, state.terrain_areas, state.tokens,
            )
            # Verified with the ENGINE's own rule function, not the scorer's
            # proxy: _in_dense_area() is what the AI optimises against, so
            # measuring with it would only prove the AI agrees with itself.
            # status_effects.is_hidden() is what actually decides whether the
            # unit can be shot at.
            hidden_models = sum(
                1 for m in squad.models
                if status_effects.is_hidden(m, state.terrain_areas, tt, {})
            )
            rows.append({
                "owner": owner,
                "name": squad.name,
                "role": deployment_ai._deployment_role(squad),
                "exposure": exposure,
                "probes": len(probes),
                "hidden": hidden_models,
                "models": len(squad.models),
                "can_hide": deployment_ai.can_be_hidden(squad),
                "forward": cx * forward_axis[0] + cy * forward_axis[1],
            })
    return rows


def _summarise(rows, label):
    # Heavy models are scored SEPARATELY, and the pass/fail below is about the
    # rest of the army. Not a loosened threshold - a changed contract: the
    # "heavy" role deliberately puts big bases in the front row so they are not
    # boxed in by their own screens (user: "dann kommen sie durch die eigenen
    # einheiten nicht durch und werden ständig blockiert"), and forward means
    # more visible. Judging that trade as a safety regression would make this
    # guard fail every time the trade is honoured, which tells nobody anything.
    # Their exposure is still reported, and still has a ceiling of its own in
    # smoke_pregame.py.
    heavy = [r for r in rows if r["role"] == "heavy"]
    rows = [r for r in rows if r["role"] != "heavy"]
    if heavy:
        print(f"    (heavy, judged separately: {len(heavy)} units, mean exposure "
              f"{sum(r['exposure'] for r in heavy) / len(heavy):5.2f})")
    exposures = [r["exposure"] for r in rows]
    hideable = [r for r in rows if r["can_hide"]]
    fully_hidden = [r for r in hideable if r["hidden"] == r["models"]]
    any_hidden = [r for r in hideable if r["hidden"] > 0]
    total_probes = rows[0]["probes"] if rows else 1
    print(f"  {label}")
    print(f"    units deployed              : {len(rows)}")
    print(f"    mean exposure              : {sum(exposures) / len(exposures):5.2f} of {total_probes}")
    print(f"    units at exposure 0        : {sum(1 for e in exposures if e == 0)}/{len(exposures)}")
    print(f"    worst single exposure      : {max(exposures)}")
    print(f"    13.09-capable units        : {len(hideable)}")
    print(f"    ...fully Hidden            : {len(fully_hidden)}/{len(hideable)}")
    print(f"    ...at least partly Hidden  : {len(any_hidden)}/{len(hideable)}")
    return {
        "mean_exposure": sum(exposures) / len(exposures),
        "zero": sum(1 for e in exposures if e == 0),
        "worst": max(exposures),
        "fully_hidden": len(fully_hidden),
        "hideable": len(hideable),
        "mean_forward": sum(r["forward"] for r in rows) / len(rows),
    }


def main():
    verdicts = []
    for map_key in ("map1", "map2"):
        print(f"\n=== {map_key} ===")
        before = _summarise(_run(map_key, safety_on=False), "BEFORE (forward-first, no 13.09 term)")
        after = _summarise(_run(map_key, safety_on=True), "AFTER  (bucketed forward + 13.09)")
        print(f"  --> mean exposure {before['mean_exposure']:.2f} -> {after['mean_exposure']:.2f}, "
              f"fully Hidden {before['fully_hidden']}/{before['hideable']} -> "
              f"{after['fully_hidden']}/{after['hideable']}, "
              f"mean forward {before['mean_forward']:.1f} -> {after['mean_forward']:.1f}")
        verdicts.append((map_key, before, after))

    print("\n" + "=" * 66)
    ok = True
    for map_key, before, after in verdicts:
        safer = after["mean_exposure"] <= before["mean_exposure"]
        hides = after["fully_hidden"] >= before["fully_hidden"]
        # Aggression must not collapse: the whole point was to keep it.
        aggressive = after["mean_forward"] >= before["mean_forward"] - 6.0
        print(f"{map_key}: safer={safer} more_hidden={hides} still_aggressive={aggressive}")
        ok = ok and safer and hides and aggressive
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
