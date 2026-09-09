"""The first leg toward a distant goal: offered by the observation, substituted
by the validator, and the reach overshoot that no longer goes back to the
planner.

The reported turn (logs/game_20260909_210843.log, map4 "Sundered"): Canoptek
Wraiths at (34,4) with a 10" move, plan "Push toward Central Objective". The
first order was (25,20) - 17" away - and went back to the planner as
unreachable; the revision ordered (44,7), which is reachable and 20.5" from
the objective where the unit stood 18.4" from it. The unit walked backwards,
exactly as ordered. Fehlerklasse 2 and 3: a point the planner has to DERIVE
it derives badly, and a retry hands the same open question back to the same
reasoner.

Three things changed, and this file pins each one against that scene:
  1. ai/observation.py attaches "first_leg_this_turn" (plain and Advance) to
     every objective and enemy entry whose centre is beyond one move - the
     furthest legal point on the line toward it, nudged off walls and the
     board edge - so the planner SELECTS a waypoint instead of inventing one.
  2. _validate_turn_plan() clamps EVERY reach overshoot along its own line
     (through the same helper) and no longer sends any of them back on the
     retry channel; a reachable position that walks AWAY from the order's own
     goal is replaced by the first leg toward that goal.
  3. The retry channel (_problems_for_the_planner) keeps only the problem
     classes a deterministic rewrite would make worse.

Real map, real datasheets, the real validator; nothing is stubbed except the
planner agent, which is a call counter.

Run: python test_plan_first_leg.py
"""
import inspect
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import testkit as tk  # noqa: E402
from testkit import Checks  # noqa: E402
from ai import agent_driver as ad, observation as obs, planner_prompt  # noqa: E402
from game import maps  # noqa: E402
from game.factions.aeldari import GUARDIAN_DEFENDERS  # noqa: E402
from game.factions.necrons import CANOPTEK_WRAITHS, NECRON_WARRIORS  # noqa: E402
from game.game_log import GameLog  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.squad import min_model_movement, model_terrain_violation  # noqa: E402
from game.terrain import DENSE, Obstacle  # noqa: E402
from game.turn import TurnTracker  # noqa: E402

c = Checks("first leg toward a distant goal")

WRAITHS = "2 Canoptek Wraiths 1"
ENEMY = "1 Guardian Defenders 1"
FRIEND = "2 Necron Warriors 1"


def centroid(squad):
    return (sum(m.x_in for m in squad.models) / len(squad.models),
            sum(m.y_in for m in squad.models) / len(squad.models))


def reported_scene(wraiths_at=(32.6, 4.0)):
    """map4, the Wraiths where the log deploys them (centroid (34,4)), one enemy
    unit deep in Player 1's corner and one friendly unit out of the way."""
    battle_map = maps.get("map4")
    maps.apply_to_config(battle_map)
    state = GameState()
    battle_map.build(state)
    wraiths = tk.build(CANOPTEK_WRAITHS, owner="Player 2", name=WRAITHS)
    tk.line_up(wraiths, x=wraiths_at[0], y=wraiths_at[1], spacing=1.4)
    enemy = tk.build(GUARDIAN_DEFENDERS, owner="Player 1", name=ENEMY)
    tk.line_up(enemy, x=8.0, y=38.0, spacing=1.4)
    friend = tk.build(NECRON_WARRIORS, owner="Player 2", name=FRIEND)
    tk.line_up(friend, x=44.0, y=2.0, spacing=1.2)
    for squad in (wraiths, enemy, friend):
        state.tokens.extend(squad.models)
    turn = TurnTracker(first_player="Player 2")
    turn.battle_round = 1
    central = next(o for o in state.objectives if o.name == "Central Objective")
    return dict(state=state, wraiths=wraiths, enemy=enemy, friend=friend, turn=turn,
                central=central, central_xy=obs.objective_centre(central))


def summary_for(sc):
    summary = {}
    obs.add_planning_distances(summary, sc["wraiths"], [sc["enemy"]], sc["state"].objectives,
                               obstacles=sc["state"].obstacles, terrain_areas=sc["state"].terrain_areas,
                               all_tokens=sc["state"].tokens)
    return summary


def plan_for(position, target="", reason="Push toward Central Objective", role="advance"):
    return {"turn_intent": "push the centre", "malformed": False,
            "unit_plans": {WRAITHS: {"role": role, "target": target, "position": position,
                                     "priority": 1, "reason": reason}}}


def validated(sc, plan):
    log = GameLog()
    out = ad._validate_turn_plan(plan, "Player 2", sc["state"], sc["turn"], log)
    return out["unit_plans"][WRAITHS], [line for line in log.entries if WRAITHS in line]


def heading_error_degrees(origin, point, goal):
    a = math.atan2(point[1] - origin[1], point[0] - origin[0])
    b = math.atan2(goal[1] - origin[1], goal[0] - origin[0])
    return abs(math.degrees((a - b + math.pi) % (2 * math.pi) - math.pi))


# ---------------------------------------------------------------------------
print("1) the observation offers a first leg toward every goal beyond one move")
# ---------------------------------------------------------------------------
sc = reported_scene()
w = sc["wraiths"]
origin = centroid(w)
plain = min_model_movement(w)
advance = obs.advance_reach_in(w)
c.eq("scene: the Wraiths stand where the log deploys them", (round(origin[0], 1), round(origin[1], 1)), (34.0, 4.0))
c.eq("scene: a 10\" move, as the log says", plain, 10.0)
c.eq("scene: the Central Objective is where the log's order aimed",
     (round(sc["central_xy"][0], 1), round(sc["central_xy"][1], 1)), (30.0, 22.0))
c.true("scene: the objective is beyond one move (the case this is for)",
       math.dist(origin, sc["central_xy"]) > plain)

summary = summary_for(sc)
central_entry = summary["distance_to_objectives"]["Central Objective"]
leg = central_entry.get("first_leg_this_turn")
c.true("Central Objective carries first_leg_this_turn", leg is not None)
if leg is not None:
    point = (leg["x"], leg["y"])
    gap, reach = ad._reach_to_point(w, point)
    c.true("the leg lies inside the unit's plain-move circle (the validator would not clamp it)",
           gap <= reach)
    c.true("...and it is most of that move, not a token step",
           math.dist(origin, point) >= 0.9 * (plain - obs.FIRST_LEG_MARGIN_IN))
    c.true("it is closer to the objective than the unit stands",
           math.dist(point, sc["central_xy"]) < math.dist(origin, sc["central_xy"]) - 5)
    c.true("it lies on (or within 30 degrees of) the straight line toward the objective",
           heading_error_degrees(origin, point, sc["central_xy"]) <= 30.0 + 1e-6)
    c.true("it does not end on a wall (rule 13.05)",
           not model_terrain_violation(w.models[0], sc["state"].obstacles, *point))
    adv = leg.get("if_you_advance")
    c.true("the leg carries an Advance variant", adv is not None)
    if adv is not None:
        adv_point = (adv["x"], adv["y"])
        gap_a, reach_a = ad._reach_to_point(w, adv_point, allow_advance=True)
        c.true("the Advance variant lies inside the Advance circle", gap_a <= reach_a)
        c.true("...beyond the plain-move circle", ad._reach_to_point(w, adv_point)[0] > plain - 0.5)
        c.true("...and closer still to the objective",
               math.dist(adv_point, sc["central_xy"]) < math.dist(point, sc["central_xy"]))

# The measured reason for the sideways nudge: on this line the point at full
# length brushes a ruin's L-wall. Walking back alone shortened the leg to 5.9".
ux = (sc["central_xy"][0] - origin[0]) / math.dist(origin, sc["central_xy"])
uy = (sc["central_xy"][1] - origin[1]) / math.dist(origin, sc["central_xy"])
on_line = (origin[0] + ux * (plain - obs.FIRST_LEG_MARGIN_IN), origin[1] + uy * (plain - obs.FIRST_LEG_MARGIN_IN))
c.true("scene: the point at full length ON the line is on a Dense piece",
       model_terrain_violation(w.models[0], sc["state"].obstacles, *on_line))
c.true("the leg was swung off the wall rather than cut short (keeps >= 90% of the move)",
       leg is not None and math.dist(origin, (leg["x"], leg["y"])) >= 0.9 * (plain - obs.FIRST_LEG_MARGIN_IN))

enemy_entry = summary["distance_to_enemy_units"][ENEMY]
c.true("an enemy unit beyond one move carries a first leg too", "first_leg_this_turn" in enemy_entry)
if "first_leg_this_turn" in enemy_entry:
    e_leg = enemy_entry["first_leg_this_turn"]
    e_goal = centroid(sc["enemy"])
    c.true("...aimed at the enemy, not at the objective",
           math.dist((e_leg["x"], e_leg["y"]), e_goal) < math.dist(origin, e_goal) - 5)

c.eq("the field is deterministic", summary_for(sc)["distance_to_objectives"]["Central Objective"],
     central_entry)

# A goal already within a plain move carries no leg: the goal IS the point.
near = reported_scene(wraiths_at=(28.6, 17.0))   # centroid (30,17), 5" from the objective
near_summary = summary_for(near)
c.true("scene: the near Wraiths are within one move of the objective",
       math.dist(centroid(near["wraiths"]), near["central_xy"]) <= min_model_movement(near["wraiths"]))
c.true("a goal within one move carries NO first leg",
       "first_leg_this_turn" not in near_summary["distance_to_objectives"]["Central Objective"])

# A passenger is skipped, like the staging spots: its models are not where
# they appear to be.
aboard = {}
obs.add_planning_distances(aboard, w, [sc["enemy"]], sc["state"].objectives, obstacles=sc["state"].obstacles,
                           terrain_areas=sc["state"].terrain_areas, all_tokens=sc["state"].tokens,
                           from_point=(40.0, 6.0), reach_bonus_in=3.0)
c.true("a passenger's objective entries carry no first leg",
       all("first_leg_this_turn" not in e for e in aboard["distance_to_objectives"].values()))


# ---------------------------------------------------------------------------
print("\n2) first_leg_toward() by itself, one clause of 'legal' at a time")
# ---------------------------------------------------------------------------
maps.apply_to_config(maps.get("map2"))
lone = tk.build(CANOPTEK_WRAITHS, owner="Player 2", name=WRAITHS)
tk.line_up(lone, x=18.6, y=20.0, spacing=1.4)      # centroid (20,20)
r = lone.models[0].radius_in

straight = obs.first_leg_toward(lone, (20.0, 40.0), 10.0, obstacles=())
c.true("open ground: the leg is on the line", straight is not None and abs(straight["x"] - 20.0) < 1e-6)
c.true("...a margin short of the reach",
       straight is not None and abs((straight["y"] - 20.0) - (10.0 - obs.FIRST_LEG_MARGIN_IN)) < 0.06)

# A wall ACROSS the line, wider than any 30-degree swing at full length can
# clear: the leg has to come back.
across = Obstacle(20.0, 30.0, 24.0, 2.0, DENSE)     # x 8-32, y 29-31
blocked = obs.first_leg_toward(lone, (20.0, 40.0), 10.0, obstacles=[across])
c.true("a wall across the line: a leg is still found", blocked is not None)
if blocked is not None:
    b = (blocked["x"], blocked["y"])
    c.true("...it does not end on the wall", not model_terrain_violation(lone.models[0], [across], *b))
    c.true("...it is within reach", math.dist((20.0, 20.0), b) <= 10.0)
    c.true("...and it still makes progress toward the goal", b[1] > 20.0 + 5.0)
    c.true("...short of the wall (it came back, not through)", b[1] + r < 29.0 + 1e-6)

# A thin wall BESIDE the line, brushed for its whole length: the swing keeps
# the full leg where walking back would have lost most of it.
beside = Obstacle(20.6, 26.0, 0.6, 10.0, DENSE)     # x 20.3-20.9, y 21-31: right next to x=20
swung = obs.first_leg_toward(lone, (20.0, 40.0), 10.0, obstacles=[beside])
c.true("a wall beside the line: the point ON the line is illegal",
       model_terrain_violation(lone.models[0], [beside], 20.0, 29.8))
c.true("...and the leg keeps at least 90% of the move by swinging sideways",
       swung is not None and math.dist((20.0, 20.0), (swung["x"], swung["y"])) >= 0.9 * (10.0 - obs.FIRST_LEG_MARGIN_IN))
c.true("...legally", swung is not None and not model_terrain_violation(lone.models[0], [beside], swung["x"], swung["y"]))
c.true("...to the far side of the goal line, not into the wall", swung is not None and swung["x"] < 20.0)

# The board edge is a clause too.
edge_squad = tk.build(CANOPTEK_WRAITHS, owner="Player 2", name=WRAITHS)
tk.line_up(edge_squad, x=3.6, y=20.0, spacing=1.4)  # centroid (5,20)
edged = obs.first_leg_toward(edge_squad, (-30.0, 20.0), 10.0, obstacles=())
c.true("a goal off the board: the leg stops at the edge", edged is not None and edged["x"] >= r - 1e-6)

within = obs.first_leg_toward(lone, (20.0, 25.0), 10.0, obstacles=())
c.true("a goal within reach: the leg is the goal itself, a margin short",
       within is not None and abs(math.dist((20.0, 20.0), (within["x"], within["y"])) - (5.0 - obs.FIRST_LEG_MARGIN_IN)) < 0.06)
c.true("no reach -> None", obs.first_leg_toward(lone, (20.0, 40.0), 0.0) is None)
c.true("the goal under the unit's feet -> None", obs.first_leg_toward(lone, (20.0, 20.0), 10.0) is None)
empty = tk.build(CANOPTEK_WRAITHS, owner="Player 2", name=WRAITHS)
empty.models = []
c.true("no models -> None", obs.first_leg_toward(empty, (20.0, 40.0), 10.0) is None)


# ---------------------------------------------------------------------------
print("\n3) a reach overshoot is clamped, and no longer sent back to the planner")
# ---------------------------------------------------------------------------
sc = reported_scene()
w = sc["wraiths"]
origin = centroid(w)
first_order = plan_for((25.0, 20.0), target="Central Objective")
gap, reach = ad._reach_to_point(w, (25.0, 20.0), allow_advance=True)
c.true("scene: the reported first order really is beyond reach, even Advancing", gap > reach + 3.0)
c.eq("the overshoot is NOT a problem for the planner any more",
     ad._problems_for_the_planner(first_order, "Player 2", sc["state"]), [])

entry, lines = validated(sc, plan_for((25.0, 20.0), target="Central Objective"))
c.true("the validator still shortens it", entry["position"] is not None and entry["position"] != (25.0, 20.0))
if entry["position"] is not None:
    gap2, reach2 = ad._reach_to_point(w, entry["position"], allow_advance=True)
    c.true("...to a point inside the Advance circle", gap2 <= reach2)
    c.true("...on the way to the ordered spot",
           math.dist(entry["position"], (25.0, 20.0)) < math.dist(origin, (25.0, 20.0)) - 8)
    c.true("...off any wall", not model_terrain_violation(w.models[0], sc["state"].obstacles, *entry["position"]))
    same = obs.first_leg_toward(w, (25.0, 20.0), reach, sc["state"].obstacles)
    c.eq("...and it IS the first leg toward the ordered spot (one definition, not a second projection)",
         (round(entry["position"][0], 1), round(entry["position"][1], 1)), (same["x"], same["y"]))
c.true("the clamp is logged", any("clamped to" in line for line in lines))
c.true("the target survives the clamp", entry["target"] == "Central Objective")


class CountingPlanner:
    """Answers the same plan every time and counts how often it is asked."""
    def __init__(self, plan):
        self.plan, self.calls = plan, 0

    def plan_turn(self, observation, problems=()):
        self.calls += 1
        return self.plan


agent = CountingPlanner(plan_for((25.0, 20.0), target="Central Objective"))
out = {}
ad._run_turn_plan(agent, lambda: {"squads": []}, out,
                  recheck=lambda p: ad._problems_for_the_planner(p, "Player 2", sc["state"]),
                  coverage=lambda p: ad._planned_squad_coverage(p, "Player 2", sc["state"]))
c.eq("the planner is asked ONCE for a plan with a 17\" overshoot (was: twice)", agent.calls, 1)
c.true("nothing was reported as a problem", "problems" not in out)
c.true("the plan came through", out.get("plan") is agent.plan)

# The other three classes still go back - the channel is narrowed, not gone.
src = inspect.getsource(ad._problems_for_the_planner)
c.true("the channel still carries LONE OPERATIVE, over-garrison and lone-garrison problems",
       all(n in src for n in ("_unshootable_from_position_problems", "_over_garrison_problems",
                              "_lone_garrison_problems")))
c.true("...and no reach test at all", "_reach_to_point" not in src and "_CLAMP_TOLERANCE_IN" not in src)


# ---------------------------------------------------------------------------
print("\n4) a reachable order that walks AWAY from its goal is replaced by the first leg")
# ---------------------------------------------------------------------------
sc = reported_scene()
w = sc["wraiths"]
origin = centroid(w)
central_xy = sc["central_xy"]
stands = math.dist(origin, central_xy)
second_order = (44.0, 7.0)
c.true("scene: the reported second order is reachable (Advancing)",
       ad._reach_to_point(w, second_order, allow_advance=True)[0] <= ad._reach_to_point(w, second_order, allow_advance=True)[1])
c.true("scene: ...and FURTHER from the objective than the unit stands",
       math.dist(second_order, central_xy) > stands + 1.0)

# As the log had it: an EMPTY target field, the goal only in the reason text.
entry, lines = validated(sc, plan_for(second_order, target="",
                                      reason="Push toward Central Objective; move to a reachable point (44,7) this turn"))
c.true("the backwards order is replaced", entry["position"] is not None and entry["position"] != second_order)
if entry["position"] is not None:
    c.true("...by a point closer to the objective than the unit stands",
           math.dist(entry["position"], central_xy) < stands - 5)
    c.true("...inside the Advance circle (the original order needed an Advance)",
           ad._reach_to_point(w, entry["position"], allow_advance=True)[0]
           <= ad._reach_to_point(w, entry["position"], allow_advance=True)[1])
    # .get() chains, not [...]: in the pre-fix world the field is absent, and a
    # probe has to turn this line RED, not crash the suite.
    offered = (summary_for(sc)["distance_to_objectives"]["Central Objective"]
               .get("first_leg_this_turn", {}).get("if_you_advance"))
    c.eq("...and it IS the point the observation offered for that goal (one definition)",
         (round(entry["position"][0], 1), round(entry["position"][1], 1)),
         (offered["x"], offered["y"]) if offered else None)
c.true("the reason is rewritten to match (Fehlerklasse 4)",
       "replaced by the first leg toward Central Objective" in (entry.get("reason") or ""))
c.true("the correction is logged as a step backwards", any("a step backwards" in line for line in lines))
c.true("...and names the Advance", any("Advancing" in line for line in lines))

entry, _ = validated(sc, plan_for(second_order, target="Central Objective", reason="hold the line"))
c.true("the target FIELD is read first: same replacement with the goal named there",
       entry["position"] is not None and math.dist(entry["position"], central_xy) < stands - 5)

enemy_xy = centroid(sc["enemy"])
entry, _ = validated(sc, plan_for(second_order, target=ENEMY, reason="close on them"))
c.true("an ENEMY unit as target is a goal too",
       entry["position"] is not None and math.dist(entry["position"], enemy_xy) < math.dist(origin, enemy_xy) - 5)

for role in ("hold", "screen", "stage"):
    entry, _ = validated(sc, plan_for(second_order, role=role))
    c.eq(f"a passive role ({role}) keeps its coordinate", entry["position"], second_order)

entry, _ = validated(sc, plan_for(second_order, target="", reason="reposition to the right flank"))
c.eq("an order with no locatable goal is left alone", entry["position"], second_order)

entry, _ = validated(sc, plan_for(second_order, target=FRIEND, reason="stay with the warriors"))
c.eq("a FRIENDLY unit as target says nothing about direction - left alone", entry["position"], second_order)

sideways = (36.5, 4.0)
c.true("scene: a sidestep 0.7\" further from the objective, under the tolerance",
       0 < math.dist(sideways, central_xy) - stands < ad._BACKWARD_ORDER_TOLERANCE_IN)
entry, _ = validated(sc, plan_for(sideways))
c.eq("a sidestep under the tolerance is not a step backwards", entry["position"], sideways)

near = reported_scene(wraiths_at=(28.6, 17.0))   # centroid (30,17): 5" from the objective
away = (30.0, 12.0)                                # 10" from it - further, but the goal is in reach
entry, _ = validated(near, plan_for(away))
c.eq("a unit already within one move of its goal may reposition away from it (fine-tuning)",
     entry["position"], away)


# ---------------------------------------------------------------------------
print("\n5) source guards: one definition, and the prompt says so")
# ---------------------------------------------------------------------------
validator_src = inspect.getsource(ad._validate_turn_plan)
c.true("the validator's clamp AND its backwards guard both read observation.first_leg_toward()",
       validator_src.count("observation.first_leg_toward(") >= 2)
c.true("the backwards guard is scoped to active roles",
       "_order_goal_point(entry, squad, state)" in validator_src)
c.true("the driver's objective centre is the observation's",
       "observation.objective_centre(" in inspect.getsource(ad._objective_centre))
c.true("the observation's own objective summary reads the same centre",
       "objective_centre(objective)" in inspect.getsource(obs.objective_summary))
c.true("add_planning_distances attaches the field", "first_leg_this_turn" in inspect.getsource(obs.add_planning_distances))
prompt = planner_prompt.PLANNER_SYSTEM_PROMPT
c.true("the planner is told the field exists", "first_leg_this_turn" in prompt)
c.true("...and what happens to an order that ignores it", "step backwards" in prompt and "shortened to the reachable part" in prompt)
c.true("the retry log line no longer calls every problem an unreachable position",
       "only the planner can fix" in inspect.getsource(ad._maybe_generate_turn_plan))

c.finish()
