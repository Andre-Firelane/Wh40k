"""Rules 14.01-14.02: the plan may not park several units on an objective
nobody is contesting.

Reported three times. The first answer was a paragraph in the planner prompt,
the second added the two numbers the decision turns on
("your_units_here"/"enemy_units_within_12in") plus a hard rule phrased in terms
of them - and it was reported again, from logs/game_20260813_223111.log:

    P2 Home Objective  your_units_here = [Boyz 1 + Warboss, Gretchin 2, Kill Rig]
                       enemy_units_within_12in = []
                       oc = {Player 2: 35}

    [turn plan] 2 Boyz 1 + Warboss: hold @(26,6) (Already on P2 Home Objective
      with no enemies within 12"; one cheap-ish garrison unit isn't needed here
      since Tankbustas/Gretchin also sit on it, but keep this strong unit ready
      and only shift if threatened - hold position.)

The board state below is that log's own [move detail] coordinates, so this is
the reported turn and not an illustration of it.

Every check that claims the fix did something runs A/B against the pre-fix
behaviour, because "nothing was reported" is also what a wrong scene looks
like.
"""

import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")

from testkit import Checks, Log, build_squad, GameState, TurnTracker

from ai import agent_driver, observation
from game import config, maps
from game import combat_focus
from game import army_lists
from game.objective_control import effective_oc
from game.factions import orks, tau_empire

c = Checks("over-garrison (rules 14.01-14.02)")


# --------------------------------------------------------------- the scene

# Round-3 positions from logs/game_20260813_223111.log's [move detail] lines.
P2_UNITS = {
    "2 Boyz 1 + Warboss": (orks.BOYZ, [
        (24.54, 4.74), (28.06, 5.30), (22.93, 5.67), (27.95, 7.28), (25.40, 7.15),
        (26.86, 8.19), (29.02, 4.48), (21.32, 4.74), (28.94, 6.50), (28.58, 8.37)]),
    "2 Gretchin 2": (orks.GRETCHIN, [
        (25.9, 10.4), (24.5, 10.0), (27.2, 10.8), (24.0, 11.2), (27.9, 9.6),
        (23.3, 9.8), (28.6, 11.0), (26.5, 11.6), (25.2, 8.9), (29.2, 10.2), (22.6, 10.6)]),
    "2 Kill Rig 1": (orks.KILL_RIG, [(32.30, 6.42)]),
    "2 Tankbustas 1": (orks.TANKBUSTAS, [
        (32.24, 17.62), (32.88, 12.57), (31.58, 13.32), (30.94, 18.37),
        (32.24, 14.62), (32.56, 11.34)]),
    "2 Battlewagon 1": (orks.BATTLEWAGON, [(16.00, 14.00)]),
    "2 Deff Dread 1": (orks.DEFF_DREAD, [(12.77, 9.14)]),
}
P1_UNITS = {
    "1 Riptide Battlesuit 1": (tau_empire.RIPTIDE_BATTLESUIT, [(29.43, 28.63)]),
    "1 Stealth Battlesuits 1": (tau_empire.STEALTH_BATTLESUITS, [
        (26.06, 27.43), (27.21, 30.77), (27.48, 25.95), (26.27, 29.45), (24.17, 26.56)]),
    "1 Ghostkeel Battlesuit 1": (tau_empire.GHOSTKEEL_BATTLESUIT, [(17.75, 26.50)]),
}


def scene(extra_p1=()):
    """The reported board. `extra_p1` adds enemy units, for the counter-checks
    that need the objective threatened or contested."""
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
    for name, sheet, positions in extra_p1:
        squad = build_squad(sheet, "Player 1", unit_index=1)
        squad.name = name
        squad.models = squad.models[:len(positions)]
        for model, (x, y) in zip(squad.models, positions):
            model.x_in, model.y_in = x, y
            state.tokens.append(model)
        squads[name] = squad

    turn = TurnTracker(first_player="Player 2")
    turn.battle_round = 3
    return state, turn, squads


HOME = "P2 Home Objective"


def reported_plan():
    """The orders that log actually contained for the three units on the home
    objective, plus one unit correctly sent elsewhere as a control."""
    return {
        "turn_intent": "reported turn",
        "unit_plans": {
            "2 Boyz 1 + Warboss": {"role": "hold", "target": None, "position": (26.0, 6.0),
                                   "priority": 5, "reason": "hold position"},
            "2 Gretchin 2": {"role": "hold", "target": None, "position": (25.0, 9.0),
                             "priority": 5, "reason": "cheap garrison"},
            # Role "advance", position inside the objective footprint - the
            # order that no amount of role-reading would have caught.
            "2 Kill Rig 1": {"role": "advance", "target": "1 Riptide Battlesuit 1",
                             "position": (27.0, 9.0), "priority": 3, "reason": "advance"},
            "2 Tankbustas 1": {"role": "hold", "target": None, "position": (32.0, 18.0),
                               "priority": 4, "reason": "Central Objective"},
        },
    }


def problems_for(state, turn, plan, player="Player 2"):
    return agent_driver._unreachable_position_problems(plan, player, state)


def validate(state, turn, plan, player="Player 2"):
    log = Log()
    agent_driver._validate_turn_plan(plan, player, state, turn, log)
    return plan, log


# ------------------------------------- 1. the scene really is the reported one

state, turn, squads = scene()
obs = observation.build_planning_observation(
    list(squads.values()), [], turn, "Player 2", objectives=state.objectives,
    embarked_squads=[], obstacles=state.obstacles, terrain_areas=state.terrain_areas)
home = next(o for o in obs["objectives"] if o["name"] == HOME)

c.eq("observation lists all three units on the home objective",
     sorted(home["your_units_here"]),
     ["2 Boyz 1 + Warboss", "2 Gretchin 2", "2 Kill Rig 1"])
c.eq("no enemy within 12\" of the home objective", home["enemy_units_within_12in"], [])
c.true("we hold it on Objective Control", home["oc_present"].get("Player 2", 0) > 0)
c.true("Gretchin really is the cheapest of the three",
       squads["2 Gretchin 2"].points < min(squads["2 Boyz 1 + Warboss"].points,
                                           squads["2 Kill Rig 1"].points))


# ------------------------------------------ 2. it is reported to the planner

state, turn, squads = scene()
problems = problems_for(state, turn, reported_plan())
garrison_problems = [p for p in problems if HOME in p]
c.eq("exactly one over-garrison problem is reported", len(garrison_problems), 1)
if garrison_problems:
    text = garrison_problems[0]
    c.true("it names all three units", all(
        n in text for n in ("2 Boyz 1 + Warboss", "2 Gretchin 2", "2 Kill Rig 1")))
    c.true("it says which one keeps it (the cheapest)",
           "2 Gretchin 2 already out-controls" in text and "Leave that there" in text)
    c.true("it does not ask for the Tankbustas", "2 Tankbustas 1" not in text)
c.eq("the contested Central Objective is not reported",
     [p for p in problems if "Central Objective" in p], [])


# ---------------------------- 3. A/B: without the check, nothing is reported

state, turn, squads = scene()
saved = agent_driver._over_garrison_problems
agent_driver._over_garrison_problems = lambda *a, **k: []
try:
    before = problems_for(state, turn, reported_plan())
finally:
    agent_driver._over_garrison_problems = saved
c.eq("A/B: pre-fix, the reported turn produced no over-garrison problem",
     [p for p in before if HOME in p], [])


# --------------------------------- 4. the deterministic backstop rewrites it

state, turn, squads = scene()
plan, log = validate(state, turn, reported_plan())
entries = plan["unit_plans"]

c.eq("the cheapest unit keeps its hold", entries["2 Gretchin 2"]["role"], "hold")
c.eq("...and keeps its position", entries["2 Gretchin 2"]["position"], (25.0, 9.0))
c.eq("the Boyz are freed to advance", entries["2 Boyz 1 + Warboss"]["role"], "advance")
c.eq("...and their garrison spot is dropped", entries["2 Boyz 1 + Warboss"]["position"], None)
c.eq("the Kill Rig is freed too, despite already saying 'advance'",
     entries["2 Kill Rig 1"]["position"], None)
c.eq("...and keeps its shooting/charge target",
     entries["2 Kill Rig 1"]["target"], "1 Riptide Battlesuit 1")
c.eq("the Tankbustas on the contested objective are untouched",
     (entries["2 Tankbustas 1"]["role"], entries["2 Tankbustas 1"]["position"]),
     ("hold", (32.0, 18.0)))
c.eq("two corrections logged", sum(1 for line in log.lines if "14.01-14.02" in line), 2)
c.true("the log names the rule and the keeper",
       any("14.01-14.02" in line and "2 Gretchin 2 already out-controls" in line
           for line in log.lines))
# The Kill Rig's role was ALREADY "advance", so a line claiming it rewrote the
# role would be false on the one order whose rewrite mattered most.
rig_line = next(l for l in log.lines if "2 Kill Rig 1" in l)
c.true("the Kill Rig's line says the coordinate was dropped, not the role changed",
       "garrison spot (27,9) dropped" in rig_line and "role" not in rig_line)
boyz_line = next(l for l in log.lines if "2 Boyz 1 + Warboss" in l)
c.true("the Boyz' line reports both changes",
       "role 'hold' -> 'advance'" in boyz_line and "(26,6) dropped" in boyz_line)


# ------------------------- 5. A/B: without the backstop, the orders stand

state, turn, squads = scene()
# Patches _held_objectives, not _uncontested_objectives: the over-garrison
# pass reads the former (it needs the threat's Objective Control, not just
# whether anyone is near), and the latter now serves only _lone_garrison_swaps.
saved = agent_driver._held_objectives
agent_driver._held_objectives = lambda *a, **k: []
try:
    plan, log = validate(state, turn, reported_plan())
finally:
    agent_driver._held_objectives = saved
c.eq("A/B: pre-fix, the Boyz keep their hold order",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "hold")
c.eq("A/B: pre-fix, the Kill Rig keeps its garrison coordinate",
     plan["unit_plans"]["2 Kill Rig 1"]["position"], (27.0, 9.0))


# ------------------------------------------- 6. counter-checks: when NOT to fire

# One unit is enough - and is left alone.
state, turn, squads = scene()
solo = reported_plan()
del solo["unit_plans"]["2 Boyz 1 + Warboss"]
del solo["unit_plans"]["2 Kill Rig 1"]
c.eq("a single garrison unit is not a problem",
     [p for p in problems_for(state, turn, solo) if HOME in p], [])
plan, log = validate(state, turn, solo)
c.eq("...and is not rewritten", plan["unit_plans"]["2 Gretchin 2"]["role"], "hold")

# A THREAT SETS THE BAR, IT DOES NOT SWITCH THE PASS OFF. This used to assert
# the opposite - an enemy anywhere within 12" exempted the objective entirely,
# so any number of units could sit on it for the rest of the battle. Reported
# as "die necrons kommen immer nicht so richtig von ihrem home objective weg.
# sowohl necron warriors als auch immortals klumpen auf dem home objective":
# in that game an Avatar of Khaine stood about 12" off P2 Home from turn 2 on,
# and a 270-point Necron Warriors blob spent four turns parked behind an
# objective an Immortals unit was already holding.
#
# Rule 14.02 says how big a garrison a threat justifies: control is the higher
# Objective Control total, so the bar is the enemy's OC, not their presence.
state, turn, squads = scene(extra_p1=[
    ("1 Kroot Carnivores 1", tau_empire.KROOT_CARNIVORES, [(30.0, 18.0)])])
threatened = next(
    o for o in observation.build_planning_observation(
        list(squads.values()), [], turn, "Player 2", objectives=state.objectives,
        embarked_squads=[], obstacles=state.obstacles,
        terrain_areas=state.terrain_areas)["objectives"] if o["name"] == HOME)
c.true("scene check: the enemy really is within 12\" now",
       threatened["enemy_units_within_12in"] != [])
home = next(o for o in state.objectives if o.name == HOME)
threat_oc = dict((o.name, t) for o, t in agent_driver._held_objectives(state, "Player 2"))[HOME]
c.eq("scene check: one Kroot model is worth 2 OC", threat_oc, 2)
c.true("the keeper alone already out-controls it",
       sum(effective_oc(m) for m in squads["2 Gretchin 2"].models) > threat_oc)
c.eq("a threatened objective is still trimmed to what holds it",
     len([p for p in problems_for(state, turn, reported_plan()) if HOME in p]), 1)
plan, log = validate(state, turn, reported_plan())
c.eq("...and the surplus is freed", plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "advance")
c.eq("...while the keeper stays", plan["unit_plans"]["2 Gretchin 2"]["role"], "hold")

# THE BAR IS REAL, not a formality: a threat big enough to out-control the
# keeper keeps a SECOND unit there. Without this the rule above would be
# indistinguishable from "always keep exactly one".
state, turn, squads = scene(extra_p1=[
    ("1 Kroot Carnivores 1", tau_empire.KROOT_CARNIVORES,
     [(26.0 + 0.9 * i, 18.0) for i in range(10)]),
    ("1 Kroot Carnivores 2", tau_empire.KROOT_CARNIVORES,
     [(26.0 + 0.9 * i, 19.5) for i in range(10)])])
threat_oc = dict((o.name, t) for o, t in agent_driver._held_objectives(state, "Player 2"))[HOME]
gretchin_oc = sum(effective_oc(m) for m in squads["2 Gretchin 2"].models)
c.true("scene check: the threat now out-controls the keeper alone",
       threat_oc > gretchin_oc)
plan, log = validate(state, turn, reported_plan())
c.eq("a bigger threat keeps a second unit on the objective",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "hold")
c.eq("...and still frees the rest", plan["unit_plans"]["2 Kill Rig 1"]["position"], None)

# An objective the enemy out-controls is not ours to over-garrison.
state, turn, squads = scene()
contested = [o for o in state.objectives if o.name == "Central Objective"]
c.eq("the Central Objective is not treated as safely ours",
     [o.name for o in agent_driver._uncontested_objectives(state, "Player 2")
      if o.name == "Central Objective"], [])
c.true("...while the home objective is",
       HOME in [o.name for o in agent_driver._uncontested_objectives(state, "Player 2")])


# --------------------------------- 7. an active role with no position is left be

state, turn, squads = scene()
moving = reported_plan()
moving["unit_plans"]["2 Boyz 1 + Warboss"] = {
    "role": "advance", "target": "1 Riptide Battlesuit 1", "position": None,
    "priority": 5, "reason": "go"}
moving["unit_plans"]["2 Kill Rig 1"]["position"] = None
garrisons = agent_driver._planned_garrisons(
    moving, {s.name: s for s in squads.values()}, state, "Player 2")
c.eq("a unit told to advance with no coordinate is not counted as a garrison",
     sorted(s.name for s in garrisons.get(HOME, [])), ["2 Gretchin 2"])
c.eq("...so nothing is reported", [p for p in problems_for(state, turn, moving) if HOME in p], [])


# ------------------------------ 8. an embarked unit is never ordered out by this

state, turn, squads = scene()
passenger = build_squad(orks.BEAST_SNAGGA_BOYZ, "Player 2", unit_index=1)
passenger.name = "2 Beast Snagga Boyz 1"
rig = squads["2 Kill Rig 1"].models[0]
for model in passenger.models:
    model.x_in, model.y_in = rig.x_in, rig.y_in
passenger.embarked_in = rig
state.embarked_squads.append(passenger)
riding = reported_plan()
riding["unit_plans"]["2 Beast Snagga Boyz 1"] = {
    "role": "stay_embarked", "target": None, "position": None,
    "priority": 5, "reason": "stay aboard"}
plan, log = validate(state, turn, riding)
c.eq("rule 18.02: a passenger stands on nothing, so it is not a garrison unit",
     plan["unit_plans"]["2 Beast Snagga Boyz 1"]["role"], "stay_embarked")


# ----------------------------------- 9. unknown points are freed, not parked
#
# CHANGED SHAPE, and the change is the point. "Unknown points may not be read
# as cheap" is still the rule, but points are now the SECOND term - role band
# first (see agent_driver._garrison_fitness()). So the principle has to be
# measured where it still decides, which is between two units in the SAME
# band, and the case where it no longer decides is worth pinning too.

# (a) the band beats an unknown price, and that is the reported outcome:
#     Gretchin hold, Boyz go forward. User, on this very board: "die 20 boyz
#     wurden gerade auf dem home objective geparkt, obwohl die KI auch 2
#     gretchin trupps hat ... die boyz sollen nach vorne und gretchins das
#     homeobjective halten."
state, turn, squads = scene()
squads["2 Gretchin 2"].points = None
unpriced = reported_plan()
plan, log = validate(state, turn, unpriced)
c.eq("an unpriced unit still keeps the objective when it is better suited to it",
     plan["unit_plans"]["2 Gretchin 2"]["role"], "hold")
c.eq("...and the 20-model melee mob is freed, which is what was reported",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "advance")
c.true("the Gretchin are in a better garrison band than the Boyz, price aside",
       combat_focus.home_garrison_rank(squads["2 Gretchin 2"])
       < combat_focus.home_garrison_rank(squads["2 Boyz 1 + Warboss"]))

# (b) WITHIN one band, unknown points still sort LAST - the original rule,
#     measured between two units that tie on the band so only price can decide.
state, turn, squads = scene()
home_obj = next(o for o in state.objectives if o.name == HOME)
boyz, rig = squads["2 Boyz 1 + Warboss"], squads["2 Kill Rig 1"]
c.eq("the two melee units really do tie on the band, so this measures price alone",
     combat_focus.home_garrison_rank(boyz, 14.8),
     combat_focus.home_garrison_rank(rig, 14.8))
c.true("...and the Boyz are the cheaper of the two while both are priced",
       boyz.points < rig.points)
c.true("...so with prices known the Boyz would win on price",
       agent_driver._garrison_fitness(boyz, home_obj, state)
       < agent_driver._garrison_fitness(rig, home_obj, state))
# Take the price off the one that was winning: it has to LOSE now, which is
# the whole content of the rule. Reading it the other way round would pass
# even if unknown sorted first.
boyz.points = None
c.true("a unit whose cost is unknown is not claimed to be the cheapest",
       agent_driver._garrison_fitness(rig, home_obj, state)
       < agent_driver._garrison_fitness(boyz, home_obj, state))


# ============================================================================
# 10. ONE unit on the objective, but the wrong one
# ============================================================================
# Reported separately, and the count test above cannot see it: "die 20 boyz
# wurden gerade auf dem home objective geparkt, obwohl die KI auch 2 gretchin
# trupps hat. das geht gar nicht, die boyz sollen nach vorne und gretchins das
# homeobjective halten." One unit is present, so len(squads) is never >= 2, and
# a 170-point mob spends the game holding ground a 45-point one holds exactly
# as well (rule 14.02: control is the higher OC total).


def lone_plan(gretchin_role="advance", gretchin_spot=(30.0, 15.0)):
    """The Boyz alone on the home objective, with the Gretchin given a job of
    their own somewhere off it."""
    return {
        "turn_intent": "reported turn",
        "unit_plans": {
            "2 Boyz 1 + Warboss": {"role": "hold", "target": None, "position": (26.0, 6.0),
                                   "priority": 5, "reason": "hold position"},
            "2 Gretchin 2": {"role": gretchin_role, "target": None, "position": gretchin_spot,
                             "priority": 5, "reason": "move up"},
            "2 Tankbustas 1": {"role": "hold", "target": None, "position": (32.0, 18.0),
                               "priority": 4, "reason": "Central Objective"},
        },
    }


state, turn, squads = scene()
plan = lone_plan()
garrisons = agent_driver._planned_garrisons(plan, squads, state, "Player 2")
c.eq("the scene really is the single-unit case the count test misses",
     len(garrisons.get(HOME, [])), 1)
c.true("...and the mob is far dearer than the Gretchin",
       squads["2 Boyz 1 + Warboss"].points > squads["2 Gretchin 2"].points)

problems = problems_for(state, turn, lone_plan())
c.true("a lone over-priced garrison is reported to the planner",
       any("2 Boyz 1 + Warboss" in p and "2 Gretchin 2" in p for p in problems))

plan, log = validate(state, turn, lone_plan())
c.eq("the mob is freed to fight", plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "advance")
c.eq("...and loses the garrison coordinate that parked it",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["position"], None)
c.eq("the Gretchin take the garrison job", plan["unit_plans"]["2 Gretchin 2"]["role"], "hold")
c.true("...and are sent onto the objective itself",
       state.objectives and any(
           o.name == HOME and o.terrain_area.contains_point(
               *plan["unit_plans"]["2 Gretchin 2"]["position"])
           for o in state.objectives))
c.true("the rewrite says what it did and why",
       any("garrison job goes to it" in line for line in log.lines))

# A/B. Without the pass the same orders come out untouched, so none of the
# checks above are passing because the scene happens to be easy.
saved = agent_driver._lone_garrison_swaps
agent_driver._lone_garrison_swaps = lambda *a, **k: []
state, turn, squads = scene()
c.eq("A/B: pre-fix, nothing at all was reported",
     [p for p in problems_for(state, turn, lone_plan()) if "2 Gretchin 2" in p], [])
pre, _ = validate(state, turn, lone_plan())
c.eq("A/B: pre-fix, the mob kept the objective",
     (pre["unit_plans"]["2 Boyz 1 + Warboss"]["role"],
      pre["unit_plans"]["2 Gretchin 2"]["role"]), ("hold", "advance"))
agent_driver._lone_garrison_swaps = saved

# ---- and each condition that must switch it OFF, isolated

state, turn, squads = scene()
no_cheaper = lone_plan()
del no_cheaper["unit_plans"]["2 Gretchin 2"]
squads.pop("2 Gretchin 2")
for model in list(state.tokens):
    if model.squad is not None and model.squad.name == "2 Gretchin 2":
        state.tokens.remove(model)
plan, log = validate(state, turn, no_cheaper)
c.eq("no cheaper unit on the board -> the mob keeps the job",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "hold")

state, turn, squads = scene()
squads["2 Gretchin 2"].battle_shocked = True
plan, log = validate(state, turn, lone_plan())
c.eq("rule 01.07: a battle-shocked unit has no OC, so it cannot take over",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "hold")

state, turn, squads = scene()
for model in squads["2 Gretchin 2"].models:
    model.y_in = 55.0  # right across the board, far beyond a 6" move
plan, log = validate(state, turn, lone_plan())
c.eq("a replacement that cannot reach the objective this turn is not used",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "hold")

# Tested at the level the guard lives at rather than through a whole plan: a
# second uncontested objective the same unit could also reach is not something
# this board offers, and building one would test the scene instead of the rule.
state, turn, squads = scene()
home_obj = next(o for o in state.objectives if o.name == HOME)
free = agent_driver._cheaper_garrison_candidates(
    home_obj, squads["2 Boyz 1 + Warboss"], squads, state, "Player 2", busy=set())
taken = agent_driver._cheaper_garrison_candidates(
    home_obj, squads["2 Boyz 1 + Warboss"], squads, state, "Player 2",
    busy={id(squads["2 Gretchin 2"])})
c.true("the Gretchin are a candidate when they have no objective of their own",
       any(sq.name == "2 Gretchin 2" for sq in free))
c.true("...and are not one when they are already holding something",
       not any(sq.name == "2 Gretchin 2" for sq in taken))

state, turn, squads = scene([
    ("1 Kroot Carnivores 1", tau_empire.KROOT_CARNIVORES, [(26.0, 14.0)])])
plan, log = validate(state, turn, lone_plan())
c.eq("an objective the enemy is contesting is not a garrison at all",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "hold")

# A loaded transport has a delivery to make (rule 18.02) and is not offered up
# as cheap garrison labour, even when it is the cheapest thing that can reach.
state, turn, squads = scene()
for model in squads["2 Gretchin 2"].models:
    model.y_in = 55.0
trukk = build_squad(orks.TRUKK, "Player 2", unit_index=1)
trukk.name = "2 Trukk 1"
trukk.models[0].x_in, trukk.models[0].y_in = 28.0, 13.0
state.tokens.append(trukk.models[0])
squads["2 Trukk 1"] = trukk
cargo = build_squad(orks.BOYZ, "Player 2", unit_index=2)
cargo.name = "2 Boyz 2"
cargo.embarked_in = trukk.models[0]
state.embarked_squads.append(cargo)
c.true("the Trukk really would be the cheapest thing in reach",
       trukk.points < squads["2 Boyz 1 + Warboss"].points)
plan, log = validate(state, turn, lone_plan())
c.eq("a loaded transport is not parked on garrison duty",
     plan["unit_plans"]["2 Boyz 1 + Warboss"]["role"], "hold")

# ------------------------- 10. the garrison job does not go to a melee unit
# Second user report on the same behaviour, from logs/game_20260826_185516.log:
# "die lych guard waren sehr passiv. die sollten eher weiter nach vorne pushen".
# The strongest case in that log is not the reported unit but the one THIS pass
# assigned: it moved the 270-point Necron Warriors off P2 Home Objective and
# handed the job to the 85-point Skorpekh Destroyers, who have no ranged
# weapons at all and then stood on empty ground for four of five turns
# (roles per AI turn: hold, hold, hold, hold, advance).
#
# Cheapest-first is what did it, and an army's assault units are routinely its
# cheapest - so the correction that exists to stop good units being wasted was
# choosing which good unit to waste. Role now orders the candidates, and points
# only break ties within a role.
#
# THE SCENE IS BUILT FROM the shipped necrons list, not from datasheets picked
# here. The first draft of this section hand-passed composition indices and got
# a 2-model 55-point Lokhust squad where the real list fields 6 models at 170 -
# which silently inverted the very comparison being asserted. That is CLAUDE.md's
# error class 17 in miniature, and building the real roster is the fix for it.
NECRON_SPOTS = {
    # Round-2 [move detail] coordinates from that log (its lines 450/722 region),
    # i.e. the board the reported plan correction was made against.
    "2 Necron Warriors 1 + Technomancer": [
        (36.61, 4.20), (34.18, 8.89), (35.24, 3.36), (31.76, 9.33), (32.76, 8.46),
        (32.33, 11.41), (35.48, 5.16), (29.44, 3.53), (37.12, 5.90), (36.87, 7.36),
        (28.53, 4.57), (34.01, 7.33), (33.65, 5.80), (36.37, 9.88), (30.20, 11.59),
        (31.31, 4.19), (38.61, 6.64), (38.79, 8.15), (32.39, 4.86), (36.20, 8.62),
        (31.79, 12.95)],
    # Four and seven models now, not three and six: the list revision put a
    # Skorpekh Lord in one and a Lokhust Lord in the other (19.01), so these
    # are the merged units and their merged names.
    "2 Skorpekh Destroyers 1 + Skorpekh Lord": [
        (30.0, 8.0), (31.6, 8.0), (33.2, 8.0), (34.8, 8.0)],
    "2 Lokhust Destroyers 1 + Lokhust Lord": [
        (30.5, 10.0), (32.1, 10.0), (33.7, 10.0),
        (35.3, 10.0), (36.9, 10.0), (38.5, 10.0), (40.1, 10.0)],
}


def necron_scene():
    maps.apply_to_config(maps.MAPS["map2"])
    state = GameState()
    maps.MAPS["map2"].build(state)
    built = []
    army_lists.get("necrons").build("Player 2", lambda sq, *a, **kw: built.append(sq), state=state)
    squads, state.tokens = {}, []
    for squad in built:
        spots = NECRON_SPOTS.get(squad.name)
        if spots is None:
            continue
        for model, (x_in, y_in) in zip(squad.models, spots):
            model.x_in, model.y_in = x_in, y_in
        squads[squad.name] = squad
        state.tokens.extend(squad.models[:len(spots)])
    return state, squads


state, squads = necron_scene()
holder = squads["2 Necron Warriors 1 + Technomancer"]
skorpekh = squads["2 Skorpekh Destroyers 1 + Skorpekh Lord"]
lokhust = squads["2 Lokhust Destroyers 1 + Lokhust Lord"]
home_obj = next(o for o in state.objectives if o.name == HOME)

c.eq("the scene fields the real 21-model Necron Warriors + Technomancer",
     len(holder.models), 21)
# NOT "no ranged weapons at all" any more - the Skorpekh Lord brought an
# enmitic annihilator into the unit. is_assault_unit() is a RATIO, not a
# presence test, and one 18" gun on one model of four does not turn a squad of
# hyperphase blades into a gunline. Worth stating, because the previous
# revision of this list made the two readings indistinguishable here.
c.true("the Skorpekh Destroyers still read as an assault unit even with their "
       "Lord's one ranged weapon in the squad",
       combat_focus.is_assault_unit(skorpekh))
c.true("...and the Lokhust Destroyers really are not",
       not combat_focus.is_assault_unit(lokhust))
c.true("...and the melee unit really is the CHEAPER of the two, which is the trap",
       agent_driver._garrison_cost_key(skorpekh) < agent_driver._garrison_cost_key(lokhust))

order = agent_driver._cheaper_garrison_candidates(
    home_obj, holder, squads, state, "Player 2", busy=set())
c.eq("the garrison job goes to the shooting unit, not the melee one",
     order[0].name, "2 Lokhust Destroyers 1 + Lokhust Lord")

# THE BAND IS NOW PART OF THE GATE, NOT JUST THE ORDER, and that is the second
# half of this same report. "Strictly cheaper than the holder" was the whole
# definition of a worthwhile swap, so with points alone deciding it, this pass
# could only ever move a garrison DOWN the points list - which is how it came
# to take P2 Home Objective off the 270-point Necron Warriors and hand it to
# the 170-point Lychguard (logs/game_20260826_234856.log lines 124-125). User:
# "die ki soll fernkampfeinheiten stark bevorzugen, wenn es darum geht das home
# objective zu halten ... sie hat im letzten spiel dafuer die lychguard
# benutzt, was voelliger quatsch ist."
c.true("a unit that would be WORSE at the job is not offered it, however cheap",
       "2 Skorpekh Destroyers 1 + Skorpekh Lord" not in {sq.name for sq in order})
c.true("...and that is the band talking, not the price - it IS the cheaper one",
       agent_driver._garrison_cost_key(skorpekh) < agent_driver._garrison_cost_key(holder))

# THE OBJECTIVE IS NEVER LEFT UNHELD BY THIS. The earlier version of this pass
# kept an assault unit as a last resort, on the argument that "a garrison that
# does not happen loses the objective". That argument does not apply here and
# never did: this is the LONE-holder case, so refusing the swap leaves the
# HOLDER standing exactly where it was. Measured rather than argued.
state, squads = necron_scene()
lone_holder = squads["2 Necron Warriors 1 + Technomancer"]
only_melee = agent_driver._cheaper_garrison_candidates(
    home_obj, lone_holder, squads, state, "Player 2",
    busy={id(squads["2 Lokhust Destroyers 1 + Lokhust Lord"])})
c.eq("with only an assault unit left, no swap is offered at all",
     [sq.name for sq in only_melee], [])
# The invariant this rests on, stated once rather than per case: whatever swap
# the pass does propose is an IMPROVEMENT on the fitness order. Refusing a swap
# therefore never costs the objective - the holder is still standing on it.
state, squads = necron_scene()
lone_plan_necron = {"unit_plans": {lone_holder.name: {
    "role": "hold", "target": None, "position": list(agent_driver._objective_centre(home_obj)),
    "priority": 5, "reason": "hold home"}}}
proposed = agent_driver._lone_garrison_swaps(lone_plan_necron, squads, state, "Player 2")
c.true("with the shooting unit free, a swap IS proposed (the scene is live)",
       len(proposed) == 1)
c.true("...and every proposed swap strictly improves the garrison fitness",
       all(agent_driver._garrison_fitness(new_sq, obj, state)
           < agent_driver._garrison_fitness(old_sq, obj, state)
           for obj, old_sq, new_sq in proposed))
c.eq("...which here means the Lokhust Destroyers take it off the Warriors",
     [(o.name, a.name, b.name) for o, a, b in proposed],
     [(HOME, "2 Necron Warriors 1 + Technomancer",
       "2 Lokhust Destroyers 1 + Lokhust Lord")])

# A/B: the whole pre-fix world, not one line of it - no band in the GATE and
# none in the ORDER. A probe that re-sorted the new candidate list would have
# been measuring a list the Skorpekh are no longer in.
_real_rank = combat_focus.home_garrison_rank
try:
    agent_driver.combat_focus.home_garrison_rank = lambda squad, reach_needed_in=None: 0
    state, squads = necron_scene()
    pre_fix = agent_driver._cheaper_garrison_candidates(
        home_obj, squads["2 Necron Warriors 1 + Technomancer"], squads, state,
        "Player 2", busy=set())
finally:
    agent_driver.combat_focus.home_garrison_rank = _real_rank
c.eq("A/B: points alone hand it to the Skorpekh Destroyers, as reported",
     pre_fix[0].name if pre_fix else None, "2 Skorpekh Destroyers 1 + Skorpekh Lord")
c.true("A/B: ...and points alone let the melee unit through the gate at all",
       "2 Skorpekh Destroyers 1 + Skorpekh Lord" in {sq.name for sq in pre_fix})

c.finish()
