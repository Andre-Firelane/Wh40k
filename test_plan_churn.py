"""The two cheap plan problems no longer cost a re-plan.

Reported as "der Trukk mit den Boyz hat sich kaum bewegt" and "im waagh zug
haetten alle nach vorne stuermen muessen, aber die orks waren insgesamt sehr
zurueckhaltend", from logs/game_20260815_203850.log. Diagnosed there and not
guessed at: the WAAAGH turn's FIRST plan was the push - Warbikers to (30,35)
deep in the enemy half, four squads ordered out of their transports - and the
engine sent it back with 18 problems, of which THIRTEEN were "these two of your
own units are ordered 0"-4" apart" and three more were reach overshoots of 1"-2".
The revision, which is the plan that actually ran, pulled the army back into its
own deployment zone and turned every disembark order into "stay_embarked".

So both families are now handled where they are cheap:

  * a reach overshoot never reaches the planner at all - it is clamped along
    its own line (since 2026-09-09 for ANY size of overshoot, not only the
    ones a 3" tolerance absorbed: sending the big ones back handed the planner
    the same open question it had answered badly, and the measured revision
    was a reachable order 2" further from its own goal - see
    test_plan_first_leg.py);
  * a collision is separated deterministically in plan-priority order
    (_separate_colliding_positions()) instead of being reported.

Every check that claims a fix did something runs A/B against the pre-fix
behaviour, because "nothing was reported" is also what a wrong scene looks
like.
"""

import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")

from testkit import Checks, Log, build_squad, GameState, TurnTracker

from ai import agent_driver, observation
from game import maps
from game.squad import min_model_movement
from game.factions import orks, tau_empire

c = Checks("plan churn (reach tolerance + collision separation)")


# --------------------------------------------------------------- the scene
#
# Player 2's positions at the START of the reported WAAAGH turn - i.e. the
# round-1 [move detail] centroids the planner was actually looking at.
P2_UNITS = {
    "2 Trukk 1": (orks.TRUKK, [(48.07, 14.02)]),
    "2 Trukk 2": (orks.TRUKK, [(15.74, 15.86)]),
    "2 Battlewagon 1": (orks.BATTLEWAGON, [(12.50, 8.30)]),
    "2 Kill Rig 1": (orks.KILL_RIG, [(43.31, 13.03)]),
    "2 Deff Dread 1": (orks.DEFF_DREAD, [(14.27, 5.19)]),
    "2 Warbikers 1": (orks.WARBIKERS, [(52.51, 18.50), (52.51, 16.44), (54.29, 17.47)]),
    "2 Warbikers 2": (orks.WARBIKERS, [(56.33, 18.67), (56.33, 16.61), (58.11, 17.64)]),
    "2 Tankbustas 1": (orks.TANKBUSTAS, [
        (38.34, 10.20), (38.34, 8.70), (39.64, 9.45), (37.04, 9.45), (38.34, 11.70), (38.34, 13.20)]),
    "2 Gretchin 2": (orks.GRETCHIN, [
        (30.00, 6.69), (31.30, 7.44), (28.70, 7.44), (31.15, 12.53), (30.00, 5.19), (28.50, 5.59),
        (31.35, 9.18), (32.60, 6.69), (32.85, 11.78), (30.00, 3.69), (29.85, 11.78)]),
}
# One enemy unit, only so the observation-side helpers have something to look
# at; nothing under test reads it.
P1_UNITS = {
    "1 Kroot Carnivores 1": (tau_empire.KROOT_CARNIVORES, [
        (29.16, 27.36), (28.92, 28.85), (27.76, 27.90), (30.32, 28.31), (28.69, 30.33)]),
}


def scene():
    battle_map = maps.get("map2")
    maps.apply_to_config(battle_map)
    state = GameState()
    battle_map.build(state)
    squads = {}
    for owner, table in (("Player 2", P2_UNITS), ("Player 1", P1_UNITS)):
        for name, (sheet, positions) in table.items():
            squad = build_squad(sheet, owner, unit_index=1)
            squad.name = name
            squad.models = squad.models[:len(positions)]
            for model, (x, y) in zip(squad.models, positions):
                model.x_in, model.y_in = x, y
                state.tokens.append(model)
            squads[name] = squad
    turn = TurnTracker(first_player="Player 2")
    turn.battle_round = 2
    return state, turn, squads


def plan_of(orders):
    """orders: {name: (role, position, priority)}"""
    return {
        "turn_intent": "WAAAGH! is active - push hard on both flanks.",
        "unit_plans": {
            name: {"role": role, "target": None, "position": spot,
                   "priority": priority, "reason": f"{name} pushes"}
            for name, (role, spot, priority) in orders.items()
        },
    }


def problems_for(state, plan, player="Player 2"):
    return agent_driver._problems_for_the_planner(plan, player, state)


def by_name(squads):
    return dict(squads)


state, turn, squads = scene()

c.eq("scene: the reported map", (round(maps.get('map2').width_in),
                                 round(maps.get('map2').height_in)), (60, 44))
c.eq("scene: Battlewagon stands where the log says",
     (round(squads["2 Battlewagon 1"].models[0].x_in, 1),
      round(squads["2 Battlewagon 1"].models[0].y_in, 1)), (12.5, 8.3))


# A/B PROBE
# ---------
# Restoring _CLAMP_TOLERANCE_IN alone is NOT the pre-fix world any more. Reach
# now counts rule 09.06's Advance (see ai/observation.py's advance_reach_in()),
# so a 2" overshoot is inside reach on its own merits and the tolerance has
# nothing left to absorb - an A/B that only put the tolerance back would report
# that this fix had never existed. Same trap this repo has now hit three times:
# a probe has to restore the WHOLE previous world, not the one line it is about.
class plain_move_reach:
    """Reach measured on the flat Move characteristic, as it was before
    Advance was counted."""

    def __enter__(self):
        self._saved = observation.advance_reach_in
        observation.advance_reach_in = min_model_movement
        return self

    def __exit__(self, *exc):
        observation.advance_reach_in = self._saved
        return False


# ---------------------------------------------------------------------------
# 1. A reach overshoot the clamp can absorb never reaches the planner
# ---------------------------------------------------------------------------
#
# The reported orders, verbatim: the Battlewagon (10" move) to (20,20) and the
# Warbikers (12") to (30,35). One is 2" too far, the other 15".

MARGINAL = plan_of({"2 Battlewagon 1": ("advance", (20.0, 20.0), 1)})
FAR = plan_of({"2 Warbikers 1": ("advance", (30.0, 35.0), 1)})

with plain_move_reach():
    gap, reach = agent_driver._reach_to_point(squads["2 Battlewagon 1"], (20.0, 20.0))
c.true("the reported Battlewagon order really IS out of a plain move", gap > reach)
c.eq("...by the 2\" the log reported", round(gap - reach), 2)
c.true("...and Advancing covers it, so the order is legal outright",
       agent_driver._reach_to_point(squads["2 Battlewagon 1"], (20.0, 20.0),
                                    allow_advance=True)[0]
       <= agent_driver._reach_to_point(squads["2 Battlewagon 1"], (20.0, 20.0),
                                       allow_advance=True)[1])

c.eq("a 2\" overshoot is not sent back to the planner", problems_for(state, MARGINAL), [])

gap_far, reach_far = agent_driver._reach_to_point(squads["2 Warbikers 1"], (30.0, 35.0),
                                                  allow_advance=True)
c.true("the reported Warbikers order overshoots by far more", gap_far - reach_far > 10)
# Since 2026-09-09 NO overshoot goes back, whatever its size: the channel handed
# the planner the same open request it had already answered badly (measured
# on logs/game_20260909_210843.log - the revision to a 17" order was a
# REACHABLE order 2" further from its own goal). The clamp answers it instead,
# deterministically, and test_plan_first_leg.py owns that case; the pin here is
# that the channel is silent on reach.
c.eq("a 15\" overshoot does not go back to the planner either", problems_for(state, FAR), [])
far_clamped = agent_driver._validate_turn_plan(
    plan_of({"2 Warbikers 1": ("advance", (30.0, 35.0), 1)}), "Player 2", state, turn, game_log=Log())
far_spot = far_clamped["unit_plans"]["2 Warbikers 1"]["position"]
far_gap, far_reach = agent_driver._reach_to_point(squads["2 Warbikers 1"], far_spot, allow_advance=True)
c.true("...it is clamped into reach instead", far_gap <= far_reach + 1e-6)
c.true("...toward where the plan pointed",
       ((far_spot[0] - 30.0) ** 2 + (far_spot[1] - 35.0) ** 2) ** 0.5 < gap_far - 8)

# A/B: the reach class is GONE from the channel, not hidden behind the
# tolerance - with the tolerance at zero and reach on the flat Move (the whole
# pre-fix world of this file), still nothing about reach is reported.
saved = agent_driver._CLAMP_TOLERANCE_IN
agent_driver._CLAMP_TOLERANCE_IN = 0.0
with plain_move_reach():
    c.eq("A/B: the tolerance is no longer what keeps the 2\" overshoot quiet",
         problems_for(state, MARGINAL) + problems_for(state, FAR), [])
agent_driver._CLAMP_TOLERANCE_IN = saved

# The clamp still runs on it, so the order is still made legal - it is just made
# legal for free.
clamped = agent_driver._validate_turn_plan(
    plan_of({"2 Battlewagon 1": ("advance", (20.0, 20.0), 1)}),
    "Player 2", state, turn, game_log=Log())
spot = clamped["unit_plans"]["2 Battlewagon 1"]["position"]
gap_after, reach_after = agent_driver._reach_to_point(squads["2 Battlewagon 1"], spot,
                                                      allow_advance=True)
c.true("the clamp still makes the marginal order reachable", gap_after <= reach_after + 1e-6)
c.true("...and it still heads the way the plan pointed (forward)", spot[1] > 8.3 + 5)


# ---------------------------------------------------------------------------
# 2. Collisions are separated instead of reported
# ---------------------------------------------------------------------------
#
# The reported pairs, verbatim from the WAAAGH turn's problem list.

COLLIDING = plan_of({
    "2 Kill Rig 1": ("advance", (37.0, 16.0), 1),
    "2 Trukk 1": ("advance", (38.0, 14.0), 2),
    "2 Tankbustas 1": ("advance", (33.0, 12.0), 3),
})

pair_gap = ((37.0 - 38.0) ** 2 + (16.0 - 14.0) ** 2) ** 0.5
c.eq("scene: the reported Kill Rig/Trukk pair is 2.2\" apart", round(pair_gap, 1), 2.2)

c.eq("colliding orders are no longer sent back to the planner",
     problems_for(state, COLLIDING), [])

log = Log()
resolved = agent_driver._validate_turn_plan(dict(COLLIDING, unit_plans=dict(
    (k, dict(v)) for k, v in COLLIDING["unit_plans"].items())),
    "Player 2", state, turn, game_log=log)
spots = {name: entry["position"] for name, entry in resolved["unit_plans"].items()}
c.true("every unit still has a spot", all(s is not None for s in spots.values()))
c.eq("the higher-priority unit keeps the spot the plan gave it",
     tuple(round(v, 2) for v in spots["2 Kill Rig 1"]), (37.0, 16.0))
c.true("the later unit was shifted, not left on top of it",
       spots["2 Trukk 1"] != (38.0, 14.0))

sep = ((spots["2 Kill Rig 1"][0] - spots["2 Trukk 1"][0]) ** 2
       + (spots["2 Kill Rig 1"][1] - spots["2 Trukk 1"][1]) ** 2) ** 0.5
needed = (agent_driver.max_model_radius(squads["2 Kill Rig 1"])
          + agent_driver.max_model_radius(squads["2 Trukk 1"])
          + agent_driver._ORDER_COLLISION_MARGIN_IN)
c.true("the two spots now clear each other", sep >= needed - 1e-6)
c.true("the shift is small - a nudge, not a new plan", sep - pair_gap < 5.0)
c.true("the correction is logged", log.has("so both units fit"))

# Still reachable after the shift: a separation that strands a unit is not a fix.
for name in ("2 Trukk 1", "2 Tankbustas 1"):
    g, r = agent_driver._reach_to_point(squads[name], spots[name])
    c.true(f"{name} can still reach its shifted spot", g - r <= agent_driver._CLAMP_TOLERANCE_IN)

# Only the pair that actually overlaps is touched. Tankbustas at (33,12) is
# 5.7" from the Kill Rig, so it is left where the plan put it.
changed = agent_driver._separate_colliding_positions(
    dict(unit_plans=dict((k, dict(v)) for k, v in COLLIDING["unit_plans"].items())),
    by_name(squads))
c.eq("exactly one of the three orders needed separating", len(changed), 1)
c.true("...and it is the reported Kill Rig/Trukk pair", "2 Trukk 1" in changed[0])
c.eq("the third order, 5.7\" clear, is untouched",
     tuple(round(v, 2) for v in spots["2 Tankbustas 1"]), (33.0, 12.0))


# ---------------------------------------------------------------------------
# 3. Counter-checks - the pass may not fire on a plan that is fine
# ---------------------------------------------------------------------------

SPREAD = plan_of({
    "2 Kill Rig 1": ("advance", (37.0, 16.0), 1),
    "2 Trukk 1": ("advance", (46.0, 16.0), 2),
})
before = {n: e["position"] for n, e in SPREAD["unit_plans"].items()}
agent_driver._separate_colliding_positions(SPREAD, by_name(squads))
c.eq("well-separated orders are left completely alone",
     {n: e["position"] for n, e in SPREAD["unit_plans"].items()}, before)

NO_SPOTS = plan_of({"2 Kill Rig 1": ("advance", None, 1), "2 Trukk 1": ("advance", None, 2)})
c.eq("orders with no coordinate are not touched",
     agent_driver._separate_colliding_positions(NO_SPOTS, by_name(squads)), [])

# Two units ordered to the exact same point: no direction to push along, so this
# is the case that would divide by zero or loop forever if it were not handled.
SAME = plan_of({
    "2 Warbikers 1": ("advance", (44.0, 20.0), 1),
    "2 Warbikers 2": ("advance", (44.0, 20.0), 2),
})
agent_driver._separate_colliding_positions(SAME, by_name(squads))
a = SAME["unit_plans"]["2 Warbikers 1"]["position"]
b = SAME["unit_plans"]["2 Warbikers 2"]["position"]
c.eq("identical orders: the first keeps the point", tuple(round(v, 2) for v in a), (44.0, 20.0))
c.true("identical orders: the second is moved off it",
       ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 > 1.0)

# Determinism: the same plan must produce the same turn twice running.
def run_same():
    p = plan_of({"2 Warbikers 1": ("advance", (44.0, 20.0), 1),
                 "2 Warbikers 2": ("advance", (44.0, 20.0), 2)})
    agent_driver._separate_colliding_positions(p, by_name(squads))
    return {n: e["position"] for n, e in p["unit_plans"].items()}


c.eq("the separation is deterministic", run_same(), run_same())

# Three in a row: the third has to clear BOTH of the first two, not just one.
THREE = plan_of({
    "2 Warbikers 1": ("advance", (44.0, 20.0), 1),
    "2 Warbikers 2": ("advance", (45.0, 20.0), 2),
    "2 Trukk 1": ("advance", (44.5, 20.5), 3),
})
agent_driver._separate_colliding_positions(THREE, by_name(squads))
pts = [(THREE["unit_plans"][n]["position"], agent_driver.max_model_radius(squads[n]))
       for n in ("2 Warbikers 1", "2 Warbikers 2", "2 Trukk 1")]
clear = True
for i, (pa, ra) in enumerate(pts):
    for pb, rb in pts[i + 1:]:
        d = ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5
        clear = clear and d >= ra + rb + agent_driver._ORDER_COLLISION_MARGIN_IN - 1e-6
c.true("three orders on one spot all end up clear of each other", clear)


# ---------------------------------------------------------------------------
# 4. The whole reported turn, end to end
# ---------------------------------------------------------------------------
#
# Every order the WAAAGH turn's first plan carried that the engine complained
# about, at once. Before: 18 problems and a re-plan. Now: how many survive?

REPORTED = plan_of({
    "2 Battlewagon 1": ("advance", (20.0, 20.0), 1),
    "2 Warbikers 1": ("advance", (30.0, 35.0), 2),
    "2 Warbikers 2": ("advance", (30.0, 35.0), 3),
    "2 Kill Rig 1": ("advance", (37.0, 16.0), 4),
    "2 Trukk 1": ("advance", (38.0, 14.0), 5),
    "2 Trukk 2": ("advance", (24.0, 16.0), 6),
    "2 Tankbustas 1": ("advance", (33.0, 12.0), 7),
    "2 Gretchin 2": ("advance", (30.0, 15.0), 8),
})
survivors = problems_for(state, REPORTED)
c.eq("NONE of the reported orders goes back to the planner any more "
     "(until 2026-09-09: the two long-range Warbiker orders did)", survivors, [])

# A/B, naming what disappeared rather than counting: the same orders, judged
# the pre-fix way - any overshoot over the flat Move, plus overlapping pairs -
# fault the Battlewagon (2" over), both Warbiker orders and the Kill Rig/Trukk
# pair. RE-DERIVED here, because the channel no longer carries the reach rule
# at all; there is nothing left in it to switch back on.
with plain_move_reach():
    pre_fix_reach = [
        n for n, e in REPORTED["unit_plans"].items()
        if (lambda g, r: g > r)(*agent_driver._reach_to_point(squads[n], e["position"], allow_advance=True))
    ]
ordered = [(n, e["position"], agent_driver.max_model_radius(squads[n]))
           for n, e in REPORTED["unit_plans"].items()]
pre_fix_collisions = [
    (na, nb)
    for i, (na, sa, ra) in enumerate(ordered)
    for nb, sb, rb in ordered[i + 1:]
    if ((sa[0] - sb[0]) ** 2 + (sa[1] - sb[1]) ** 2) ** 0.5 < ra + rb + agent_driver._ORDER_COLLISION_MARGIN_IN
]
c.true("A/B: pre-fix, the 2\" Battlewagon overshoot was also reported",
       "2 Battlewagon 1" in pre_fix_reach)
c.true("A/B: pre-fix, both Warbiker orders were reported",
       all(f"2 Warbikers {i}" in pre_fix_reach for i in (1, 2)))
c.eq("A/B: pre-fix, the two overlapping pairs were reported as well",
     len(pre_fix_collisions), 2)
c.eq(f"A/B: same orders, 5 problems before and 0 now",
     (len(pre_fix_reach) + len(pre_fix_collisions), len(survivors)), (5, 0))

# And the whole plan still comes out legal, with every unit keeping an order.
log = Log()
final = agent_driver._validate_turn_plan(
    plan_of({n: (e["role"], e["position"], e["priority"])
             for n, e in REPORTED["unit_plans"].items()}),
    "Player 2", state, turn, game_log=log)
kept = [n for n, e in final["unit_plans"].items() if e.get("position") is not None]
c.eq("every unit still has a position after validation", len(kept), len(REPORTED["unit_plans"]))
final_pts = [(final["unit_plans"][n]["position"], agent_driver.max_model_radius(squads[n]))
             for n in kept]
clear = True
for i, (pa, ra) in enumerate(final_pts):
    for pb, rb in final_pts[i + 1:]:
        d = ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5
        clear = clear and d >= ra + rb + agent_driver._ORDER_COLLISION_MARGIN_IN - 1e-6
c.true("no two of the validated spots overlap any more", clear)
for n in kept:
    g, r = agent_driver._reach_to_point(squads[n], final["unit_plans"][n]["position"])
    c.true(f"{n}'s validated spot is reachable", g - r <= agent_driver._CLAMP_TOLERANCE_IN)

c.finish()
