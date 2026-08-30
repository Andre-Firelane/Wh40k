"""Who the AI leaves standing on its own home objective (rules 14.01-14.02).

User: "die ki soll fernkampfeinheiten stark bevorzugen, wenn es darum geht das
home objective zu halten. sie hat im letzten spiel dafuer die lychguard
benutzt, was voelliger quatsch ist. die immortals waeren perfekt. starke
fernkaempfer mit hoher reichweite."

REPRODUCED FIRST, on the reported game (logs/game_20260826_234856.log):

  line  19  [deploy] 2 Lychguard 1 + Overlord (assault) deployed at (30.0,8.1)
  line 124  [plan problem] ... 2 Lychguard 1 + Overlord (170 pts) holds it
            exactly as well and can reach it this turn
  line 125  turn plan corrected - Necron Warriors: role 'hold' -> 'advance' ...
            2 Lychguard 1 + Overlord is cheaper

so the army's melee anvil was put on the home objective at deployment AND
confirmed there by the turn-plan pass, on both occasions because it happens to
be the cheapest unit in that list at 170 points.

BOTH HALVES OF THE USER SENTENCE ARE SEPARATE TERMS, and that is the finding
this file is mostly about. "Fernkaempfer" and "hohe Reichweite" do not select
the same units: the Aeldari Wraithguard read as a shooting unit (ratio 2.00) on
a 12" gun, and from a home objective the nearest ground anybody fights over is
15-17" away, so they contribute exactly as little as the Lychguard would.

Every claim that the change did something runs A/B against the pre-fix world.
"""

import io
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")

from testkit import Checks, GameState, TurnTracker, build_squad

from ai import agent_driver, deployment_ai, observation
from game import army_lists, combat_focus, config, deployment, maps, pregame
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import aeldari
from game.setup import SetupController
from game import attached_units

c = Checks("home-objective garrison (rules 14.01-14.02)")

OWNER = "Player 2"
HOME = "P2 Home Objective"


# ===========================================================================
# 1. the band itself - combat_focus.home_garrison_rank()
# ===========================================================================

necrons = {sq.name: sq for sq in army_lists.preview_squads("necrons", OWNER)}
aeldari_list = {sq.name: sq for sq in army_lists.preview_squads("aeldari", OWNER)}
orks = {sq.name: sq for sq in army_lists.preview_squads("orks", OWNER)}

lychguard = necrons["2 Lychguard 1 + Overlord"]
immortals_gauss = necrons["2 Immortals 1 + Plasmancer"]
immortals_tesla = necrons["2 Immortals 2 + Plasmancer"]
warriors = necrons["2 Necron Warriors 1 + Technomancer"]
wraithguard = aeldari_list["2 Wraithguard 1"]
gretchin = orks["2 Gretchin 1"]

BANDS = (combat_focus.GARRISON_BAND_SHOOTER,
         combat_focus.GARRISON_BAND_NEUTRAL,
         combat_focus.GARRISON_BAND_ASSAULT)
c.eq("the three bands are ordered best-first", list(BANDS), [0, 1, 2])

# The reported unit and the one the user named, side by side.
c.eq("the Lychguard are in the worst band for this job",
     combat_focus.home_garrison_rank(lychguard, 14.8),
     combat_focus.GARRISON_BAND_ASSAULT)
c.eq("the Immortals are in the best one",
     combat_focus.home_garrison_rank(immortals_gauss, 14.8),
     combat_focus.GARRISON_BAND_SHOOTER)
c.true("...and the Lychguard really are the CHEAPER of the two, which is the trap",
       lychguard.points < immortals_gauss.points)

# A unit that leans neither way is neither - it is not sent forward and not
# preferred for the job.
c.eq("the Necron Warriors lean neither way and land in the middle band",
     combat_focus.home_garrison_rank(warriors, 14.8),
     combat_focus.GARRISON_BAND_NEUTRAL)

# THE RANGE HALF IS A TERM OF ITS OWN. Measured on the one unit in any list
# where the two halves disagree.
c.true("the Wraithguard DO read as a shooting unit by ratio alone",
       combat_focus.is_shooting_specialist(wraithguard))
c.eq("...but their gun is 12\"", combat_focus.best_ranged_reach_in(wraithguard), 12)
c.eq("...so from a home objective they are not in the top band",
     combat_focus.home_garrison_rank(wraithguard, 14.8),
     combat_focus.GARRISON_BAND_NEUTRAL)
c.eq("...and with the range half switched off they would be",
     combat_focus.home_garrison_rank(wraithguard, None),
     combat_focus.GARRISON_BAND_SHOOTER)
# The other side of the same line: a gun long enough clears it.
c.eq("a 24\" gun clears the same bar", combat_focus.best_ranged_reach_in(immortals_gauss), 24)

# Measured at the boundary rather than at a comfortable distance, because a
# threshold only shows itself there.
c.eq("exactly AT the needed reach still counts",
     combat_focus.home_garrison_rank(wraithguard, 12.0),
     combat_focus.GARRISON_BAND_SHOOTER)
c.eq("...and a hair beyond it does not",
     combat_focus.home_garrison_rank(wraithguard, 12.1),
     combat_focus.GARRISON_BAND_NEUTRAL)

# The assault side is tested BEFORE the range half, so a melee unit that
# happens to carry a long gun is still a melee unit. Named because reading the
# two tests in the other order looks equivalent and is not.
skorpekh = necrons["2 Skorpekh Destroyers 1 + Skorpekh Lord"]
c.true("the Skorpekh Destroyers carry a ranged weapon at all",
       combat_focus.best_ranged_reach_in(skorpekh) > 0)
c.eq("...and are still in the assault band, whatever its range",
     combat_focus.home_garrison_rank(skorpekh, 0.0),
     combat_focus.GARRISON_BAND_ASSAULT)

# A KNOWN CONSEQUENCE, pinned rather than tuned away: the 1.4 ratio threshold
# (measured in game/combat_focus.py, and shared with the charge block and the
# deployment `assault` role) falls between this list's two Immortals units,
# which are the same datasheet with different guns. It costs nothing here - the
# Gauss unit is picked first anyway - but a future reader should not discover
# it as a surprise.
c.eq("the two Immortals units cost the same", immortals_gauss.points, immortals_tesla.points)
c.true("...but the tesla one falls just below the shooting-specialist ratio",
       combat_focus.ranged_to_melee_ratio(immortals_tesla)
       < combat_focus.SHOOTING_SPECIALIST_RATIO
       <= combat_focus.ranged_to_melee_ratio(immortals_gauss))
c.eq("...and lands one band lower",
     combat_focus.home_garrison_rank(immortals_tesla, 14.8),
     combat_focus.GARRISON_BAND_NEUTRAL)


# ===========================================================================
# 2. best_ranged_reach_in() reads the LIVE range, not the printed one
# ===========================================================================
# game/weapon_range.py is this repo's one definition of "how far does this
# weapon reach right now", and two abilities extend it live. Measured through
# Fuegan's Burning Lance (+6" to Melta weapons in the unit he leads) rather
# than asserted from the import, because an import proves nothing about which
# number comes out.

dragons = build_squad(aeldari.FIRE_DRAGONS, OWNER, unit_index=1)
printed = combat_focus.best_ranged_reach_in(dragons)
fuegan = build_squad(aeldari.FUEGAN, OWNER, unit_index=1)
led = attached_units.attach(fuegan, build_squad(aeldari.FIRE_DRAGONS, OWNER, unit_index=2))
c.true("Fire Dragons alone report their printed range", printed > 0)
c.eq("...and led by Fuegan the same unit reports 6\" more (Burning Lance)",
     combat_focus.best_ranged_reach_in(led), printed + 6)

# Dead models do not carry a gun anywhere.
corpse = build_squad(aeldari.FIRE_DRAGONS, OWNER, unit_index=3)
for model in corpse.models:
    model.current_wounds = 0
c.eq("a wiped unit has no reach at all", combat_focus.best_ranged_reach_in(corpse), 0)


# ===========================================================================
# 3. garrison_reach_needed_in() is measured off the board
# ===========================================================================

def board(map_key):
    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    return state


for map_key, want in (("map1", 17.1), ("map2", 14.8), ("map3", 15.9)):
    state = board(map_key)
    zones = getattr(state, "deployment_zones", ())
    for owner in ("Player 1", "Player 2"):
        own = deployment.zone_for(zones, owner)
        home = deployment_ai._home_objective(owner, state.objectives, own)
        c.true(f"{map_key}: {owner} has a home objective", home is not None)
        need = observation.garrison_reach_needed_in(home, state.objectives)
        c.true(f"{map_key}: {owner} needs a real, positive reach", need > 0)
        if want is not None:
            c.eq(f"{map_key}: {owner} needs {want}\" of reach", round(need, 1), want)
        # It is the distance to the NEAREST OTHER objective, not to No Man's
        # Land - that is only 3.8-5.2" away on these maps and would have let
        # every 12" gun through.
        hx, hy = observation._objective_centre_point(home)
        nearest = min(
            (observation._objective_centre_point(o)
             for o in state.objectives if o is not home),
            key=lambda p: (p[0] - hx) ** 2 + (p[1] - hy) ** 2)
        c.eq(f"{map_key}: {owner} - it is the distance to the nearest other objective",
             round(need, 3), round(((nearest[0] - hx) ** 2 + (nearest[1] - hy) ** 2) ** 0.5, 3))
        # A 12" gun falls short on every shipped board.
        c.eq(f"{map_key}: {owner} - a 12\" gun cannot reach the fight from home",
             need <= 12, False)

# Symmetric: both players face the same problem on these boards.
for map_key in ("map1", "map2", "map3"):
    state = board(map_key)
    zones = getattr(state, "deployment_zones", ())
    needs = []
    for owner in ("Player 1", "Player 2"):
        own = deployment.zone_for(zones, owner)
        home = deployment_ai._home_objective(owner, state.objectives, own)
        needs.append(round(observation.garrison_reach_needed_in(home, state.objectives), 1))
    c.eq(f"{map_key}: both players need the same reach", needs[0], needs[1])


# THE NUMBER IS NOT A CONSTANT, and this is the check that shows it. It used to
# ride on the old 30"x30" test board, which was the one shipped map where the
# two players needed DIFFERENT reach (11.6" against 13.8") - written down as a
# fixed threshold, that case would have been silently wrong. That board is gone
# (its key now carries the 60"x44" corner-deployment layout, which is
# symmetric), so the case is built here instead of borrowed from whichever map
# happens to have it: an asymmetric objective layout, and the two players
# needing different reach, with a 12" gun clearing the bar for exactly one.
_asym = board("map2")
_home1 = deployment_ai._home_objective(
    "Player 1", _asym.objectives, deployment.zone_for(_asym.deployment_zones, "Player 1"))
_home2 = deployment_ai._home_objective(
    "Player 2", _asym.objectives, deployment.zone_for(_asym.deployment_zones, "Player 2"))
_h1 = observation._objective_centre_point(_home1)
_h2 = observation._objective_centre_point(_home2)


class _FakeObjective:
    """An objective at a chosen point - enough for garrison_reach_needed_in(),
    which only ever asks for centres."""

    def __init__(self, x_in, y_in):
        self.terrain_area = type("A", (), {"bounding_box": (x_in, y_in, x_in, y_in)})()
        self.name = "probe"


_near = _FakeObjective(_h1[0], _h1[1] - 10.0)      # 10" from Player 1's home
_far = _FakeObjective(_h2[0], _h2[1] + 14.0)       # 14" from Player 2's home
_layout = [_home1, _home2, _near, _far]
_need1 = observation.garrison_reach_needed_in(_home1, _layout)
_need2 = observation.garrison_reach_needed_in(_home2, _layout)
c.eq("an asymmetric layout gives Player 1 a nearer fight", round(_need1, 1), 10.0)
c.eq("...and Player 2 a further one", round(_need2, 1), 14.0)
c.true("so the two players do NOT need the same reach", _need1 != _need2)
c.eq("a 12\" gun clears the bar for exactly one of them",
     (_need1 <= 12, _need2 <= 12), (True, False))

# One objective on the board means nothing to compare against.
state = board("map2")
c.eq("with no other objective there is nothing to reach and the term is dropped",
     observation.garrison_reach_needed_in(state.objectives[0], [state.objectives[0]]), None)


# ===========================================================================
# 4. deployment: who is designated to hold home
# ===========================================================================

def pregame_for(map_key, army_key):
    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    setup = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN)
    ctrl = pregame.PregameController(state, setup, DiceManager(), DecisionManager(),
                                     turn_tracker=TurnTracker(first_player=OWNER))
    squads, decls = [], []

    def register(squad, destination=pregame.DEPLOY, transport=None):
        squads.append(squad)
        decls.append((squad, destination, transport))
        return squad

    army_lists.get(army_key).build(OWNER, register, state=state)
    ctrl.start({OWNER: squads})
    for squad, destination, transport in decls:
        ctrl.declare(squad, destination, transport_token=transport)
    own = deployment.zone_for(getattr(state, "deployment_zones", ()), OWNER)
    return ctrl, state, own


def home_pick(map_key, army_key):
    ctrl, state, own = pregame_for(map_key, army_key)
    return deployment_ai.home_garrison_squad(ctrl, OWNER, state.objectives, own)


# The reported list, on every map it can be played on.
for map_key in ("map1", "map2", "map3"):
    c.eq(f"{map_key}: the Necron home garrison is the Immortals, not the Lychguard",
         home_pick(map_key, "necrons").name, "2 Immortals 1 + Plasmancer")

# THE ORK LIST IS UNCHANGED, and that matters as much as the fix: the Ork
# answer is the one an earlier report asked for by name ("gretchins das
# homeobjective halten"), and a role term that out-voted points everywhere
# would have moved it to the 160-point Battlewagon.
for map_key in ("map1", "map2", "map3"):
    c.eq(f"{map_key}: the Ork home garrison is still the Gretchin",
         home_pick(map_key, "orks").name, "2 Gretchin 1")
    # The Aeldari answer MOVED, and not because this rule changed: the Warlock
    # Skyrunner used to be the cheapest unit in the SHOOTER band at 55 pts, and
    # the Shroud Runners -> Windriders swap merged it into the Windriders, so it
    # is no longer a unit that can be designated at all. The Rangers are what is
    # left at the bottom of the same band - 60 pts, and a 36" long rifle against
    # the Skyrunner's 24", so the swap traded 5 points for 12" of reach on the
    # objective the rule exists to keep a gun on. Measured, not assumed: at
    # map2's 14.8" of needed reach both qualify for the top band, and points
    # decide within it (see combat_focus.home_garrison_rank()).
    c.eq(f"{map_key}: the Aeldari home garrison is the Rangers, the cheapest shooter left",
         home_pick(map_key, "aeldari").name, "2 Rangers 1")

# Points still decide WITHIN a band - the Gretchin are not the best band, they
# are the cheapest unit in the band the Orks have.
ctrl, state, own = pregame_for("map2", "orks")
picked = deployment_ai.home_garrison_squad(ctrl, OWNER, state.objectives, own)
home_obj = deployment_ai._home_objective(OWNER, state.objectives, own)
need = observation.garrison_reach_needed_in(home_obj, state.objectives)
c.eq("the Ork pick is a middle-band unit, not a top-band one",
     combat_focus.home_garrison_rank(picked, need), combat_focus.GARRISON_BAND_NEUTRAL)
same_band = [sq for sq in ctrl.army(OWNER)
             if sq.models and not deployment_ai.is_heavy(sq)
             and any(m.profile.oc > 0 for m in sq.models)
             and combat_focus.home_garrison_rank(sq, need)
             == combat_focus.home_garrison_rank(picked, need)]
c.true("...and it is the cheapest unit of that band",
       all(picked.points <= sq.points for sq in same_band))

# A/B: the pre-fix world at this source - points alone.
_real_rank = combat_focus.home_garrison_rank
try:
    deployment_ai.combat_focus.home_garrison_rank = lambda squad, reach_needed_in=None: 0
    pre_fix = home_pick("map2", "necrons")
finally:
    deployment_ai.combat_focus.home_garrison_rank = _real_rank
c.eq("A/B: points alone put the Lychguard on the home objective, as reported",
     pre_fix.name, "2 Lychguard 1 + Overlord")


# ===========================================================================
# 5. the turn plan, on the reported board
# ===========================================================================
# Coordinates from logs/game_20260826_234856.log lines 13-34. Reproduced rather
# than staged, because the reason the Immortals were not chosen in that game is
# that they were 12" and 20" from the objective with a 5" move - a scene that
# stood one next to it would have proved a fix the real game could not use.

REPORTED = {
    "2 Doomsday Ark 1": (47.6, 9.9),
    "2 Canoptek Wraiths 1": (26.0, 10.0),
    "2 Lychguard 1 + Overlord": (30.0, 8.1),
    "2 Skorpekh Destroyers 1 + Skorpekh Lord": (10.0, 10.0),
    "2 Necron Warriors 1 + Technomancer": (34.0, 4.0),
    "2 Immortals 1 + Plasmancer": (13.8, 10.4),
    "2 Immortals 2 + Plasmancer": (50.3, 10.4),
    "2 Lokhust Destroyers 1 + Lokhust Lord": (44.0, 8.0),
}


def reported_board():
    battle_map = maps.apply_to_config(maps.get("map2"))
    state = GameState()
    battle_map.build(state)
    built = []
    army_lists.build_necrons(OWNER, lambda sq, *a, **kw: built.append(sq), state=state)
    squads, state.tokens = {}, []
    for squad in built:
        spot = REPORTED.get(squad.name)
        if spot is None:
            continue
        for i, model in enumerate(squad.models):
            model.x_in, model.y_in = spot[0] + (i % 4) * 1.2, spot[1] + (i // 4) * 1.2
            state.tokens.append(model)
        squads[squad.name] = squad
    return state, squads


state, squads = reported_board()
c.eq("the reported board still names every unit it places", len(squads), len(REPORTED))
home_obj = next(o for o in state.objectives if o.name == HOME)
hx, hy = agent_driver._objective_centre(home_obj)
holder = squads["2 Necron Warriors 1 + Technomancer"]
plan = {"unit_plans": {holder.name: {
    "role": "hold", "target": None, "position": [hx, hy], "priority": 5,
    "reason": "hold home"}}}

# The scene really is the hard one: the Immortals cannot get there.
gap, reach = agent_driver._reach_to_point(squads["2 Immortals 1 + Plasmancer"], (hx, hy))
c.true("on the reported board the Immortals are out of reach of the objective", gap > reach)
gap, reach = agent_driver._reach_to_point(squads["2 Lychguard 1 + Overlord"], (hx, hy))
c.true("...while the Lychguard are standing right on it", gap <= reach)

swaps = agent_driver._lone_garrison_swaps(plan, squads, state, OWNER)
c.eq("the pass no longer hands the home objective to the Lychguard", swaps, [])
c.eq("...so the plan is left alone and the holder keeps it",
     plan["unit_plans"][holder.name]["role"], "hold")

# A/B: the whole pre-fix world at this source.
_real_rank = combat_focus.home_garrison_rank
try:
    agent_driver.combat_focus.home_garrison_rank = lambda squad, reach_needed_in=None: 0
    state_ab, squads_ab = reported_board()
    plan_ab = {"unit_plans": {holder.name: {
        "role": "hold", "target": None, "position": [hx, hy], "priority": 5,
        "reason": "hold home"}}}
    pre_fix_swaps = agent_driver._lone_garrison_swaps(plan_ab, squads_ab, state_ab, OWNER)
finally:
    agent_driver.combat_focus.home_garrison_rank = _real_rank
c.eq("A/B: points alone reproduce the reported swap exactly",
     [(o.name, a.name, b.name) for o, a, b in pre_fix_swaps],
     [(HOME, "2 Necron Warriors 1 + Technomancer", "2 Lychguard 1 + Overlord")])


# ===========================================================================
# 6. one fitness definition, three readers
# ===========================================================================
# The over-garrison pass picks a keeper out of two or three units, its
# planner-facing twin reports the same keeper, and the lone pass decides
# whether one unit hands the job over. Answering that from two orderings would
# have let the first keep the very unit the third was changed to stop choosing.

src = io.open("ai/agent_driver.py", encoding="utf-8").read()
c.eq("_garrison_fitness is defined exactly once", src.count("def _garrison_fitness("), 1)
c.eq("...and read from three places", src.count("_garrison_fitness(") - 1, 3)
c.true("no garrison site sorts on points alone any more",
       "key=_garrison_cost_key" not in src)

# The three readers agree by construction, measured on a live board.
state, squads = reported_board()
keeper_order = sorted(squads.values(),
                      key=lambda sq: agent_driver._garrison_fitness(sq, home_obj, state))
c.eq("the shared ordering puts a shooting unit first",
     combat_focus.home_garrison_rank(
         keeper_order[0],
         observation.garrison_reach_needed_in(home_obj, state.objectives)),
     combat_focus.GARRISON_BAND_SHOOTER)
c.eq("...and the reported melee unit last-band",
     combat_focus.home_garrison_rank(
         keeper_order[-1],
         observation.garrison_reach_needed_in(home_obj, state.objectives)),
     combat_focus.GARRISON_BAND_ASSAULT)


# ===========================================================================
# 7. the planner is told the same rule it is measured against
# ===========================================================================
# A rule that lives only in the enforcement produces plans that are corrected
# every turn; a rule that lives only in the prompt stays optional. Both.

from ai.planner_prompt import PLANNER_SYSTEM_PROMPT as PROMPT

c.true("the prompt tells the planner to garrison its back line with a shooting unit",
       "long-ranged SHOOTING unit" in PROMPT)
c.true("...and says why, in terms of what the unit gives up",
       "keeps firing every turn it stands there" in PROMPT)
c.true("...and warns that the cheapest unit is often the melee anvil",
       "your cheapest unit is often your melee anvil" in PROMPT)
c.true("...and that a contested objective is the opposite case",
       "On a CONTESTED objective this reverses" in PROMPT)
c.true("the old points-first wording is gone",
       "Garrison with the cheapest unit that holds it" not in PROMPT)

c.finish()
