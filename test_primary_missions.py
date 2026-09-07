"""Force Disposition Primary Missions (game/primary_missions.py).

What this suite pins, and why some of it looks surprising:

- A Primary is NOT a Secondary card. It has several scoring boxes, each with
  its own instant and its own battle-round band, and each pays EVERY time its
  instant comes round. Section 8 drives all three instants and both ends of
  every band, because a box whose band is off by one still passes any test that
  only ever scores it in round 3.
- Two cards print rows that look alike and are not. Reconnaissance Sweep's two
  spread tiers are ALTERNATIVES (3 or 6, never 9); Secure Asset's two
  end-of-Command-phase rows STACK (4 + 4). Sections 3 and 5 pin both, because
  reading either one the other way passes every single-row test.
- Secure Asset's second objective row has NO "(excluding your home objective)"
  where the row directly above it does. One parenthesis, its own check.
- Three boxes read a TURN-START SNAPSHOT rather than the board, because they
  ask about units that are dead and control that has changed by the time they
  score. Section 4/5/6 each check the box against a board that has moved on,
  which is the only arrangement where the snapshot does any work.
- "Central objective" is geometry, not the name "Central": map3 has no
  objective called that. Section 7 measures all three shipped maps.
- Nothing here prompts. A Primary offers no choice, which is why the headless
  harnesses need no opt-out - section 10 asserts that absence rather than
  leaving it to be discovered.
"""

import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from game import config  # noqa: E402
from game import force_dispositions as fd  # noqa: E402
from game import maps  # noqa: E402
from game import mission_context as mc  # noqa: E402
from game import primary_missions as pm  # noqa: E402
from game.actions import ActionController  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game import missions  # noqa: E402
from game.missions import MissionController  # noqa: E402
from game.turn import PHASES, PHASE_SHOOTING, TurnTracker  # noqa: E402
from game.factions import aeldari as ae  # noqa: E402

checks = tk.Checks("Primary Missions")

config.PRIMARY_MISSION_CARD_PLAYERS = ("Player 1",)

# The real map2, for the same reason test_secondary_missions.py uses it: the
# classifications under test (what is No Man's Land, which objective is whose
# home, where the quarters fall) are properties the shipped maps actually
# produce, and hand-made rectangles would only test the arithmetic.
_map = maps.MAPS["map2"]
maps.apply_to_config(_map)
board = GameState()
_map.build(board)

CENTRE_X, CENTRE_Y = mc.board_centre()
OBJ = {o.name: o for o in board.objectives}


def clear_control():
    for objective in board.objectives:
        objective.controlled_by = None


def ctx(player="Player 1", tokens=(), **kw):
    return mc.MissionContext(
        player, tokens=list(tokens), objectives=board.objectives,
        deployment_zones=board.deployment_zones,
        terrain_areas=board.terrain_areas, **kw)


def unit(owner="Player 1", x=10.0, y=10.0, models=3, name=None):
    """A plain infantry unit at a known spot.

    DIRE AVENGERS rather than Guardian Defenders, and that is not arbitrary:
    rule 16.01's start_eligibility() refuses a unit whose models[0] has OC 0,
    and a Guardian Defenders squad leads with its Heavy Weapon Platform, which
    does. Every Objective Action here would have been silently ineligible."""
    squad = tk.build(ae.DIRE_AVENGERS, owner=owner,
                     name=name or f"{owner[-1]} test unit")
    del squad.models[models:]
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + i * 1.4, y
    return squad


def tokens_of(*squads):
    out = []
    for squad in squads:
        out.extend(squad.models)
    return out


# ============================================================ 1. the registry
print("--- 1. registry and dispositions ---")

checks.eq("five missions, one per Force Disposition", len(pm.ALL_MISSIONS), 5)
checks.eq("keyed on the disposition, all five covered",
          sorted(pm.BY_DISPOSITION), sorted(fd.ALL))
for mission in pm.ALL_MISSIONS:
    checks.true(f"{mission.name} names a valid disposition",
                fd.is_valid(mission.force_disposition))
    checks.true(f"{mission.name} has at least one scoring box", bool(mission.boxes))
    for box in mission.boxes:
        checks.true(f"{mission.name}/{box.key} has a known timing",
                    box.timing in pm.TIMING_LABELS)
checks.eq("mission_for() on an unknown disposition is None",
          pm.mission_for("no such disposition"), None)

# Exactly the two cards whose printed reverse is an Objective Action.
with_action = sorted(m.name for m in pm.ALL_MISSIONS if m.action is not None)
checks.eq("two missions carry an Objective Action", with_action,
          ["Death Trap", "Secure Asset"])
checks.true("Booby Trap completes immediately",
            pm.BOOBY_TRAP_ACTION.completes_immediately)
checks.eq("Secure Asset's action does NOT complete immediately",
          pm.SECURE_ASSET_ACTION.completes_immediately, False)
for action in (pm.BOOBY_TRAP_ACTION, pm.SECURE_ASSET_ACTION):
    checks.eq(f"{action.name} starts in the Shooting phase",
              action.starts, PHASE_SHOOTING)


# ================================================== 2. Battlefield Dominance
print("--- 2. Battlefield Dominance (Take and Hold) ---")

clear_control()
checks.eq("nobody holds anything: no VP", pm._dominance_more_objectives(ctx()), 0)
OBJ["Central Objective"].controlled_by = "Player 1"
checks.eq("1 v 0 is MORE: 2 VP", pm._dominance_more_objectives(ctx()),
          pm.BATTLEFIELD_DOMINANCE_MORE_VP)
OBJ["Objective West"].controlled_by = "Player 2"
checks.eq("1 v 1 is a TIE, and a tie is not more: 0 VP",
          pm._dominance_more_objectives(ctx()), 0)
OBJ["Objective East"].controlled_by = "Player 1"
checks.eq("2 v 1: 2 VP", pm._dominance_more_objectives(ctx()),
          pm.BATTLEFIELD_DOMINANCE_MORE_VP)

# The cumulative home bonus. 3 VP per objective INCLUDING your home, then +2
# per objective EXCLUDING it - so the home itself stays worth 3 while every
# forward objective becomes worth 5.
clear_control()
OBJ["Objective East"].controlled_by = "Player 1"
checks.eq("one forward objective, home not held: 3 VP",
          pm._dominance_control(ctx()), 3)
OBJ["P1 Home Objective"].controlled_by = "Player 1"
checks.eq("home + one forward: 3+3 base, +2 for the forward one = 8 VP",
          pm._dominance_control(ctx()), 8)
OBJ["Central Objective"].controlled_by = "Player 1"
checks.eq("home + two forward: 9 base + 4 bonus = 13 VP",
          pm._dominance_control(ctx()), 13)
clear_control()
OBJ["Objective East"].controlled_by = "Player 1"
OBJ["Central Objective"].controlled_by = "Player 1"
checks.eq("two forward, home NOT held: 6 VP and no bonus at all",
          pm._dominance_control(ctx()), 6)
# Holding ONLY your home pays the 3 and nothing else - the bonus counts the
# objectives other than it, and there are none.
clear_control()
OBJ["P1 Home Objective"].controlled_by = "Player 1"
checks.eq("home alone: 3 VP, no bonus", pm._dominance_control(ctx()), 3)

box_more = next(b for b in pm.BATTLEFIELD_DOMINANCE.boxes if b.key == "more_objectives")
box_ctrl = next(b for b in pm.BATTLEFIELD_DOMINANCE.boxes if b.key == "control")
checks.eq("the MORE box is rounds 1-2", (box_more.min_round, box_more.max_round), (None, 2))
checks.true("...and is out of band in round 3", not box_more.in_round_band(3))
checks.true("...and in band in rounds 1 and 2",
            box_more.in_round_band(1) and box_more.in_round_band(2))
checks.eq("the CONTROL box is second round onward",
          (box_ctrl.min_round, box_ctrl.max_round), (2, None))
checks.true("...and is out of band in round 1", not box_ctrl.in_round_band(1))
checks.eq("the two boxes score at DIFFERENT instants",
          (box_more.timing, box_ctrl.timing),
          (pm.TIMING_END_OF_YOUR_TURN, pm.TIMING_END_OF_COMMAND_PHASE))


# ================================================= 3. Reconnaissance Sweep
print("--- 3. Reconnaissance Sweep (Reconnaissance) ---")

# map2's quarters are NW/NE/SW/SE split at (30, 22). Each unit below sits well
# inside one and well clear of the 6" centre exclusion.
nw = unit("Player 1", 8.0, 8.0)
ne = unit("Player 1", 46.0, 8.0)
sw = unit("Player 1", 8.0, 34.0)
se = unit("Player 1", 46.0, 34.0)

three = ctx(tokens=tokens_of(nw, ne, sw))
four = ctx(tokens=tokens_of(nw, ne, sw, se))
checks.eq("three quarters have presence", len(mc.quarters_with_presence(three)), 3)
checks.eq("four quarters have presence", len(mc.quarters_with_presence(four)), 4)
checks.eq("three quarters: 3 VP", pm._recon_quarters(three), pm.RECON_THREE_QUARTERS_VP)
checks.eq("four quarters: 6 VP", pm._recon_quarters(four), pm.RECON_FOUR_QUARTERS_VP)
# OR, not cumulative - the whole point of the two rows being alternatives.
checks.eq("four quarters is 6, NOT 3+6=9", pm._recon_quarters(four), 6)
checks.eq("two quarters: nothing",
          pm._recon_quarters(ctx(tokens=tokens_of(nw, ne))), 0)

# Three units in the SAME quarter are not three quarters - and the card asks
# for three DIFFERENT ones. Presence is per quarter, so this cannot pay.
crowd = [unit("Player 1", 4.0 + i * 6.0, 6.0) for i in range(3)]
checks.eq("three units all in one quarter: nothing",
          pm._recon_quarters(ctx(tokens=tokens_of(*crowd))), 0)

# The 6"-from-centre clause is what makes the card hard: a unit inside its
# quarter but hugging the middle gives no presence.
near_centre = unit("Player 1", 26.0, 19.0)
checks.true("the near-centre unit IS wholly inside its quarter",
            all(mc._model_wholly_in_rect(m, mc.table_quarters()[0])
                for m in near_centre.models))
checks.eq("...but within 6\" of the centre, so no presence",
          len(mc.quarters_with_presence(ctx(tokens=tokens_of(near_centre)))), 0)
checks.eq("so three quarters plus a hugger is still only three",
          pm._recon_quarters(ctx(tokens=tokens_of(nw, ne, sw, near_centre))),
          pm.RECON_THREE_QUARTERS_VP)


class DeadSquad:
    def __init__(self, owner):
        self.owner = owner
        self.models = []


def killed(*owners):
    return [DeadSquad(o) for o in owners]


checks.eq("one enemy unit killed: 1 VP",
          pm._recon_kills(ctx(destroyed_squads_this_turn=killed("Player 2"))),
          pm.RECON_PER_KILL_VP)
checks.eq("three enemy units killed: 3 VP, uncapped",
          pm._recon_kills(ctx(destroyed_squads_this_turn=killed(*(["Player 2"] * 3)))), 3)
checks.eq("MY OWN losses pay nothing",
          pm._recon_kills(ctx(destroyed_squads_this_turn=killed("Player 1", "Player 1"))), 0)

clear_control()
checks.eq("no objective held: nothing", pm._recon_objective(ctx()), 0)
OBJ["P1 Home Objective"].controlled_by = "Player 1"
checks.eq("holding ONLY my home objective pays nothing - it is excluded",
          pm._recon_objective(ctx()), 0)
OBJ["Central Objective"].controlled_by = "Player 1"
checks.eq("a non-home objective: 3 VP", pm._recon_objective(ctx()), pm.RECON_OBJECTIVE_VP)
# "excluding your home objective" is singular and possessive: the ENEMY's home
# objective is not excluded.
clear_control()
OBJ["P2 Home Objective"].controlled_by = "Player 1"
checks.eq("taking the ENEMY's home objective counts",
          pm._recon_objective(ctx()), pm.RECON_OBJECTIVE_VP)


# ==================================================== 4. Unstoppable Force
print("--- 4. Unstoppable Force (Purge the Foe) ---")

checks.eq("no kills: nothing", pm._unstoppable_kills(ctx()), 0)
checks.eq("one kill: 3 VP",
          pm._unstoppable_kills(ctx(destroyed_squads_this_turn=killed("Player 2"))),
          pm.UNSTOPPABLE_KILL_VP)
checks.eq("three kills: still 3 VP - this box is a yes/no, not a count",
          pm._unstoppable_kills(
              ctx(destroyed_squads_this_turn=killed(*(["Player 2"] * 3)))),
          pm.UNSTOPPABLE_KILL_VP)

clear_control()
checks.eq("no objectives: nothing", pm._unstoppable_objectives(ctx()), 0)
OBJ["Central Objective"].controlled_by = "Player 1"
OBJ["Objective East"].controlled_by = "Player 1"
checks.eq("two non-home objectives: 8 VP", pm._unstoppable_objectives(ctx()), 8)
OBJ["P1 Home Objective"].controlled_by = "Player 1"
checks.eq("my home objective adds nothing - it is excluded",
          pm._unstoppable_objectives(ctx()), 8)

# "objectives you did not control at the START of the turn" - read from the
# snapshot, so a board that has moved on since is exactly the interesting case.
clear_control()
OBJ["Central Objective"].controlled_by = "Player 1"
held_all_along = {id(OBJ["Central Objective"])}
checks.eq("held throughout, nothing gained: 0 VP",
          pm._unstoppable_gained(ctx(objectives_controlled_at_turn_start=held_all_along)), 0)
OBJ["Objective East"].controlled_by = "Player 1"
checks.eq("one taken this turn: 3 VP",
          pm._unstoppable_gained(ctx(objectives_controlled_at_turn_start=held_all_along)),
          pm.UNSTOPPABLE_GAINED_VP)
checks.eq("with an EMPTY snapshot everything counts as newly taken",
          pm._unstoppable_gained(ctx(objectives_controlled_at_turn_start=set())),
          pm.UNSTOPPABLE_GAINED_VP)
# Taking your own home objective is not taking ground: it is excluded.
clear_control()
OBJ["P1 Home Objective"].controlled_by = "Player 1"
checks.eq("gaining only my own home objective pays nothing",
          pm._unstoppable_gained(ctx(objectives_controlled_at_turn_start=set())), 0)

clear_control()
central = mc.central_objectives(ctx())
checks.eq("map2 has exactly one central objective", len(central), 1)
checks.eq("...and it is the Central Objective", central[0].name, "Central Objective")
checks.eq("nobody holds it: nothing", pm._unstoppable_central(ctx()), 0)
OBJ["Objective East"].controlled_by = "Player 1"
checks.eq("holding a NON-central objective pays nothing",
          pm._unstoppable_central(ctx()), 0)
central[0].controlled_by = "Player 1"
checks.eq("holding the central objective: 5 VP",
          pm._unstoppable_central(ctx()), pm.UNSTOPPABLE_CENTRAL_VP)
central[0].controlled_by = "Player 2"
checks.eq("the AI holding it pays me nothing", pm._unstoppable_central(ctx()), 0)

uf = {b.key: b for b in pm.UNSTOPPABLE_FORCE.boxes}
checks.eq("the central box is the only END OF BATTLE one",
          [k for k, b in uf.items() if b.timing == pm.TIMING_END_OF_BATTLE], ["central"])
checks.eq("the GAINED box is second round onward", uf["gained"].min_round, 2)
checks.eq("the KILLS box has no round band at all",
          (uf["kills"].min_round, uf["kills"].max_round), (None, None))


# ========================================================= 5. Secure Asset
print("--- 5. Secure Asset (Priority Assets) ---")

checks.eq("nothing secured: nothing", pm._secure_asset_secured(ctx(card_state={})), 0)
checks.eq("secured this turn: 4 VP",
          pm._secure_asset_secured(
              ctx(card_state={pm.SECURE_ASSET_SLOT: [OBJ["Central Objective"]]})),
          pm.SECURE_ASSET_SECURED_VP)

dead_enemy = DeadSquad("Player 2")
checks.eq("a kill that was NOT on a central objective pays nothing",
          pm._secure_asset_kill(ctx(destroyed_squads_this_turn=[dead_enemy],
                                    on_central_objective_at_turn_start=set())), 0)
checks.eq("a kill that started the turn on a central objective: 2 VP",
          pm._secure_asset_kill(ctx(destroyed_squads_this_turn=[dead_enemy],
                                    on_central_objective_at_turn_start={id(dead_enemy)})),
          pm.SECURE_ASSET_KILL_VP)
own_dead = DeadSquad("Player 1")
checks.eq("MY OWN unit dying there pays nothing",
          pm._secure_asset_kill(ctx(destroyed_squads_this_turn=[own_dead],
                                    on_central_objective_at_turn_start={id(own_dead)})), 0)

# The two end-of-Command-phase rows: one excludes my home objective and the
# other does NOT, and they STACK. Both facts are one parenthesis apart.
clear_control()
checks.eq("nothing held: neither row pays",
          (pm._secure_asset_one_objective(ctx()), pm._secure_asset_three_objectives(ctx())),
          (0, 0))
OBJ["P1 Home Objective"].controlled_by = "Player 1"
checks.eq("holding only my home: the 'one objective' row excludes it",
          pm._secure_asset_one_objective(ctx()), 0)
OBJ["Central Objective"].controlled_by = "Player 1"
OBJ["Objective East"].controlled_by = "Player 1"
checks.eq("home + two forward: the 'one objective' row pays",
          pm._secure_asset_one_objective(ctx()), pm.SECURE_ASSET_ONE_OBJECTIVE_VP)
checks.eq("...and the 'three or more' row COUNTS my home objective, so it pays too",
          pm._secure_asset_three_objectives(ctx()), pm.SECURE_ASSET_THREE_OBJECTIVES_VP)
checks.eq("the two rows STACK: 4 + 4",
          pm._secure_asset_one_objective(ctx()) + pm._secure_asset_three_objectives(ctx()), 8)
# Two forward objectives without the home is three-minus-one: the second row
# must not fire. This is the check the home-exclusion reading would fail.
OBJ["P1 Home Objective"].controlled_by = None
checks.eq("two objectives only: the 'three or more' row does not pay",
          pm._secure_asset_three_objectives(ctx()), 0)
checks.eq("...while the 'one objective' row still does",
          pm._secure_asset_one_objective(ctx()), pm.SECURE_ASSET_ONE_OBJECTIVE_VP)


# ============================================================ 6. Death Trap
print("--- 6. Death Trap (Disruption) ---")

plain_area = next(a for a in board.terrain_areas
                  if not any(o.terrain_area is a for o in board.objectives))
objective_area = OBJ["Central Objective"].terrain_area
checks.true("the plain area is not an objective",
            not pm.area_is_an_objective(ctx(), plain_area))
checks.true("the objective's area IS an objective (shared identity)",
            pm.area_is_an_objective(ctx(), objective_area))

checks.eq("nothing trapped: nothing", pm._death_trap_traps(ctx(card_state={})), 0)
checks.eq("one plain area trapped: 2 VP",
          pm._death_trap_traps(ctx(card_state={pm.DEATH_TRAP_SLOT: [plain_area]})),
          pm.DEATH_TRAP_PER_AREA_VP)
checks.eq("one OBJECTIVE area trapped: 2 + 3 cumulative = 5 VP",
          pm._death_trap_traps(ctx(card_state={pm.DEATH_TRAP_SLOT: [objective_area]})), 5)
checks.eq("one of each: 2 + 5 = 7 VP",
          pm._death_trap_traps(
              ctx(card_state={pm.DEATH_TRAP_SLOT: [plain_area, objective_area]})), 7)

# The kill clause reads WHERE the unit stood from the snapshot and WHETHER that
# area is trapped live - two different sources, deliberately.
victim = DeadSquad("Player 2")
trapped_state = {pm.DEATH_TRAP_ALL_SLOT: {id(plain_area): plain_area}}
checks.eq("a kill in an UNTRAPPED area pays nothing",
          pm._death_trap_kill(ctx(card_state={pm.DEATH_TRAP_ALL_SLOT: {}},
                                  destroyed_squads_this_turn=[victim],
                                  in_terrain_at_turn_start={id(victim): frozenset([id(plain_area)])})), 0)
checks.eq("a kill in a trapped area: 3 VP",
          pm._death_trap_kill(ctx(card_state=trapped_state,
                                  destroyed_squads_this_turn=[victim],
                                  in_terrain_at_turn_start={id(victim): frozenset([id(plain_area)])})),
          pm.DEATH_TRAP_KILL_VP)
checks.eq("a kill that started the turn in NO terrain area pays nothing",
          pm._death_trap_kill(ctx(card_state=trapped_state,
                                  destroyed_squads_this_turn=[victim],
                                  in_terrain_at_turn_start={})), 0)
checks.eq("a kill in a DIFFERENT, untrapped area pays nothing",
          pm._death_trap_kill(ctx(card_state=trapped_state,
                                  destroyed_squads_this_turn=[victim],
                                  in_terrain_at_turn_start={id(victim): frozenset([id(objective_area)])})), 0)
# The area need not have been trapped THIS turn - the clause is present tense
# with no "this turn", so a trap laid in an earlier round still counts.
checks.eq("an area trapped on an EARLIER turn still counts",
          pm._death_trap_kill(ctx(card_state={pm.DEATH_TRAP_ALL_SLOT: {id(plain_area): plain_area},
                                              pm.DEATH_TRAP_SLOT: []},
                                  destroyed_squads_this_turn=[victim],
                                  in_terrain_at_turn_start={id(victim): frozenset([id(plain_area)])})),
          pm.DEATH_TRAP_KILL_VP)

clear_control()
OBJ["Central Objective"].controlled_by = "Player 1"
checks.eq("a non-home objective held: 4 VP", pm._death_trap_objective(ctx()),
          pm.DEATH_TRAP_OBJECTIVE_VP)
clear_control()
OBJ["P1 Home Objective"].controlled_by = "Player 1"
checks.eq("only my home objective: nothing", pm._death_trap_objective(ctx()), 0)


# ================================== 7. central_objectives on all three maps
print("--- 7. central objectives, measured on all three maps ---")

EXPECTED_CENTRAL = {
    "map1": ["Central Objective"],
    "map2": ["Central Objective"],
    # map3 has NO objective named "Central" at all - its middle is a 9"
    # no-man's-land disc holding two, and they are a point-symmetric mirror
    # pair. A name-based reading would leave two scoring boxes dead here.
    "map3": ["Objective East", "Objective West"],
}
for key, expected in EXPECTED_CENTRAL.items():
    other = maps.MAPS[key]
    maps.apply_to_config(other)
    other_board = GameState()
    other.build(other_board)
    other_ctx = mc.MissionContext("Player 1", objectives=other_board.objectives,
                                  deployment_zones=other_board.deployment_zones)
    found = mc.central_objectives(other_ctx)
    checks.eq(f"{key}: central objectives", sorted(o.name for o in found), expected)
    # ...and every one that did NOT win is meaningfully further out, so the
    # answer is not a knife-edge.
    cx, cy = mc.board_centre()

    def dist(objective):
        ox, oy = mc.objective_centre(objective)
        return ((ox - cx) ** 2 + (oy - cy) ** 2) ** 0.5

    won = max(dist(o) for o in found)
    rest = [dist(o) for o in mc.no_mans_land_objectives(other_ctx) if o not in found]
    if rest:
        checks.true(f"{key}: the next nearest is well clear ({min(rest):.1f}\" vs {won:.1f}\")",
                    min(rest) > won + 5.0)
    checks.true(f"{key}: no home objective is ever central",
                all(o in mc.no_mans_land_objectives(other_ctx) for o in found))

# THE TOLERANCE IS NO LONGER INERT, and that is worth recording rather than
# quietly relaxing: it used to be a net for "a future map whose mirroring runs
# through different arithmetic", and map3 became that map. Shrinking its two
# central pieces so they clear the deployment zones changed the wall positions
# the centre is averaged from, and the mirrored pair now differ in the last
# bit - about 7e-15, the same order that once turned a rectangle into a
# pentagon. Well inside CENTRAL_OBJECTIVE_TIE_IN, which is what
# central_objectives() actually compares with.
checks.true("map3's two central objectives are still a tie for the rule "
            "that reads them", True)
maps.apply_to_config(maps.MAPS["map3"])
m3 = GameState()
maps.MAPS["map3"].build(m3)
m3_ctx = mc.MissionContext("Player 1", objectives=m3.objectives,
                           deployment_zones=m3.deployment_zones)
_cx, _cy = mc.board_centre()
_d = sorted(((ox - _cx) ** 2 + (oy - _cy) ** 2) ** 0.5
            for ox, oy in (mc.objective_centre(o) for o in mc.central_objectives(m3_ctx)))
checks.true(f"the two distances tie within the tolerance the rule uses "
            f"({abs(_d[-1] - _d[0]):.2e}\" apart, tolerance "
            f"{mc.CENTRAL_OBJECTIVE_TIE_IN})",
            abs(_d[-1] - _d[0]) < mc.CENTRAL_OBJECTIVE_TIE_IN)
# ...and BOTH are still returned, which is the thing that actually matters:
# the tie is what makes map3's middle pair No Man's Land for Secure Asset and
# Unstoppable Force. A tolerance that stopped covering the gap would silently
# drop one of them.
checks.eq("...so both are still central", len(mc.central_objectives(m3_ctx)), 2)

# The strongest statement available about map3, and the one the map's design
# actually makes: its deployment zones are quadrants MINUS a 9" disc around the
# board centre, and the two objectives sitting in that hole are the whole point
# of the board. "Nearest to the centre" must pick out exactly those two.
#
# Their NAMES are no help and would mislead: on map3 the two middle objectives
# are called "Objective East" and "Objective West", while "Northwest" and
# "Southeast" are the big diagonal ruins 22.8" out.
_in_hole = sorted(o.name for o in m3.objectives
                  if (lambda p: ((p[0] - _cx) ** 2 + (p[1] - _cy) ** 2) ** 0.5 <= 9.0)(
                      mc.objective_centre(o)))
checks.eq("map3: exactly two objectives sit inside the 9\" central disc",
          _in_hole, ["Objective East", "Objective West"])
checks.eq("...and those are precisely the central objectives",
          sorted(o.name for o in mc.central_objectives(m3_ctx)), _in_hole)
checks.true("...and neither of them is in anybody's deployment zone",
            all(not any(z.contains_point(*mc.objective_centre(o))
                        for z in m3.deployment_zones)
                for o in mc.central_objectives(m3_ctx)))

# The home-objective exclusion is a documented NO-OP on all three shipped maps
# (every home objective is further out than the winner anyway), so an A/B probe
# that deletes it changes nothing there - a finding about the maps, not proof
# the clause is idle. It is measured on a board built to need it: a deployment
# zone pushed against the middle, with its home objective nearer the centre
# than anything in No Man's Land.


class FakeZone:
    def __init__(self, owner, box):
        self.owner = owner
        self.box = box

    def contains_point(self, x, y):
        x0, y0, x1, y1 = self.box
        return x0 <= x <= x1 and y0 <= y <= y1


class FakeArea:
    def __init__(self, x, y):
        self.bounding_box = (x - 1.0, y - 1.0, x + 1.0, y + 1.0)


class FakeObjective:
    def __init__(self, name, x, y):
        self.name = name
        self.terrain_area = FakeArea(x, y)
        self.controlled_by = None


maps.apply_to_config(_map)   # 60x44, centre (30, 22)
crowded = mc.MissionContext(
    "Player 1",
    objectives=[FakeObjective("Greedy Home", 30.0, 24.0),      # 2" from centre
                FakeObjective("Far Home", 30.0, 2.0),
                FakeObjective("Middle Ground", 30.0, 16.0)],   # 6" from centre, no zone
    deployment_zones=[FakeZone("Player 1", (20.0, 23.0, 40.0, 44.0)),
                      FakeZone("Player 2", (20.0, 0.0, 40.0, 4.0))])
checks.eq("the greedy home objective IS the nearest thing to the centre",
          min((o for o in crowded.objectives),
              key=lambda o: abs(mc.objective_centre(o)[1] - 22.0)).name, "Greedy Home")
checks.eq("...and is still not a central objective, because it is a home one",
          [o.name for o in mc.central_objectives(crowded)], ["Middle Ground"])

# Put map2 back - everything after this point measures against it.
maps.apply_to_config(_map)


# =============================================== 8. the actions, end to end
print("--- 8. the two Objective Actions through the real ActionController ---")


def controller(mission, tokens=(), phase=PHASE_SHOOTING, owner="Player 1", started=True):
    """A PrimaryMissionController wired to the REAL MissionController ledger
    and the REAL ActionController - half of what this section checks is that
    it defers to them rather than keeping a second opinion."""
    log = tk.Log()
    ledger = MissionController(game_log=log)
    turn = TurnTracker(game_log=tk.Log())
    if started:
        turn.start_battle(owner) if hasattr(turn, "start_battle") else None
    turn.phase_index = PHASES.index(phase)
    turn.turn_owner = owner
    turn.set_active(owner)
    box = list(tokens)
    actions = ActionController(tokens_source=lambda: box, game_log=log)
    ctrl = pm.PrimaryMissionController(
        player="Player 1", mission_controller=ledger, turn_tracker=turn,
        game_log=log, mission=mission, action_controller=actions)
    ctrl.set_tokens_source(lambda: box)
    ctrl.set_objectives_source(lambda: board.objectives)
    ctrl.set_zones_source(lambda: board.deployment_zones)
    ctrl.set_terrain_source(lambda: board.terrain_areas)
    return ctrl, ledger, actions, turn, log, box


# --- Secure Asset -----------------------------------------------------------
clear_control()
central_obj = OBJ["Central Objective"]
ccx, ccy = mc.objective_centre(central_obj)
holder = unit("Player 1", ccx, ccy, models=3, name="1 Holders 1")
ctrl, ledger, actions, turn, log, box = controller(pm.SECURE_ASSET, tokens_of(holder))

offers = ctrl.available_actions_for(holder)
checks.true("Secure Asset is offered to a unit on an objective", bool(offers))
checks.true("...naming the objective as its target",
            any(t is central_obj for _l, _a, t in offers))
checks.eq("it is NOT offered to the enemy's units",
          ctrl.available_actions_for(unit("Player 2", ccx, ccy)), [])

label, action, target = next(o for o in offers if o[2] is central_obj)
checks.true("starting it succeeds", ctrl.start_action(action, holder, target) is not None)
checks.eq("16.01: the unit may no longer shoot", actions.blocks_shooting(holder), True)
checks.eq("16.01: nor declare a charge", actions.blocks_charge(holder), True)
# "USE LIMIT: Once per turn" - one action in the whole turn, not one per unit.
second = unit("Player 1", ccx + 0.5, ccy + 0.5, name="1 Holders 2")
box.extend(second.models)
checks.eq("a SECOND unit is refused - once per turn, not once per unit",
          ctrl.available_actions_for(second), [])

# COMPLETES: end of your turn, if your unit controls that objective.
central_obj.controlled_by = "Player 2"
ctrl.begin_end_of_turn("Player 1", battle_round=1)
checks.eq("not controlling it: the action does not complete, 0 VP",
          ledger.primary_points["Player 1"], 0)

clear_control()
central_obj.controlled_by = "Player 1"
ctrl, ledger, actions, turn, log, box = controller(pm.SECURE_ASSET, tokens_of(holder))
_l, action, target = next(o for o in ctrl.available_actions_for(holder) if o[2] is central_obj)
ctrl.start_action(action, holder, target)
ctrl.begin_end_of_turn("Player 1", battle_round=1)
checks.eq("controlling it: the action completes and pays 4 VP",
          ledger.primary_points["Player 1"], pm.SECURE_ASSET_SECURED_VP)
checks.true("the log names the mission and the box", log.has("Secure Asset"))
checks.eq("the per-turn slot is cleared afterwards",
          ctrl.card_state.get(pm.SECURE_ASSET_SLOT), None)

# 16.01: a unit that MOVES does not complete its action.
clear_control()
central_obj.controlled_by = "Player 1"
ctrl, ledger, actions, turn, log, box = controller(pm.SECURE_ASSET, tokens_of(holder))
_l, action, target = next(o for o in ctrl.available_actions_for(holder) if o[2] is central_obj)
ctrl.start_action(action, holder, target)
actions.notify_move(holder, None)
ctrl.begin_end_of_turn("Player 1", battle_round=1)
checks.eq("a unit that moved does not complete it: 0 VP",
          ledger.primary_points["Player 1"], 0)

# --- Booby Trap -------------------------------------------------------------
clear_control()
p1_zone = next(z for z in board.deployment_zones if z.owner == "Player 1")
outside = [a for a in board.terrain_areas
           if not any(o.terrain_area is a for o in board.objectives)
           and pm._area_outside_own_deployment_zone(
               mc.MissionContext("Player 1", objectives=board.objectives,
                                 deployment_zones=board.deployment_zones), a)]
checks.true("map2 has plain terrain areas outside my deployment zone", bool(outside))
target_area = outside[0]
amin_x, amin_y, amax_x, amax_y = target_area.bounding_box
acx, acy = (amin_x + amax_x) / 2.0, (amin_y + amax_y) / 2.0
trapper = unit("Player 1", acx, acy, models=1, name="1 Trappers 1")
ctrl, ledger, actions, turn, log, box = controller(pm.DEATH_TRAP, tokens_of(trapper))
offers = ctrl.available_actions_for(trapper)
checks.true("Booby Trap is offered to a unit standing in that area", bool(offers))
checks.true("...naming that terrain area", any(t is target_area for _l, _a, t in offers))

_l, action, area_target = next(o for o in offers if o[2] is target_area)
ctrl.start_action(action, trapper, area_target)
trap_ctx = ctrl._context()
checks.true("COMPLETES: Immediately - the area is trapped straight away",
            pm.area_is_trapped(trap_ctx, target_area))
checks.eq("...and it is recorded as trapped THIS turn",
          [id(a) for a in ctrl.card_state.get(pm.DEATH_TRAP_SLOT, [])], [id(target_area)])
checks.eq("the same unit is not offered the same area twice",
          [t for _l, _a, t in ctrl.available_actions_for(trapper) if t is target_area], [])
ctrl.begin_end_of_turn("Player 1", battle_round=1)
checks.eq("a plain trapped area pays 2 VP", ledger.primary_points["Player 1"],
          pm.DEATH_TRAP_PER_AREA_VP)
# ...and being trapped OUTLIVES the turn, while "trapped this turn" does not.
checks.eq("trapped-this-turn is cleared", ctrl.card_state.get(pm.DEATH_TRAP_SLOT), None)
checks.true("but the area is still trapped next turn",
            pm.area_is_trapped(ctrl._context(), target_area))
# 16.01's per-turn bookkeeping has to be cleared here, exactly as main.py does
# one line after begin_end_of_turn(). Without it this check passed for the
# WRONG reason: the action's own use limit ("a different terrain area each
# time") still remembered last turn's target, so the trapped-forever gate under
# test was masked by a gate that resets every turn. An A/B probe that removed
# the trapped gate altogether left this line green.
actions.reset_for_turn()
checks.eq("so it cannot be trapped again for another 2 VP - even on a fresh "
          "turn, with 16.01's own per-turn limit reset",
          ctrl.available_actions_for(trapper), [])
ctrl.begin_end_of_turn("Player 1", battle_round=2)
checks.eq("and a second turn pays nothing more for it",
          ledger.primary_points["Player 1"], pm.DEATH_TRAP_PER_AREA_VP)

# Two units may both trap, as long as they are in DIFFERENT areas.
clear_control()
ctrl, ledger, actions, turn, log, box = controller(pm.DEATH_TRAP)
areas = outside[:2]
if len(areas) >= 2:
    movers = []
    for i, area in enumerate(areas):
        bx0, by0, bx1, by1 = area.bounding_box
        u = unit("Player 1", (bx0 + bx1) / 2.0, (by0 + by1) / 2.0, models=1,
                 name=f"1 Trappers {i + 1}")
        movers.append(u)
        box.extend(u.models)
    for u, area in zip(movers, areas):
        offer = [o for o in ctrl.available_actions_for(u) if o[2] is area]
        if offer:
            ctrl.start_action(offer[0][1], u, area)
    checks.eq("two units in two different areas both trap",
              len(ctrl.card_state.get(pm.DEATH_TRAP_SLOT, [])), 2)


# ============================================= 9. the controller's instants
print("--- 9. the three instants, the round bands and the ledger ---")

clear_control()
OBJ["Central Objective"].controlled_by = "Player 1"
ctrl, ledger, actions, turn, log, box = controller(pm.BATTLEFIELD_DOMINANCE)

# END OF YOUR TURN fires only for your own turn.
checks.eq("the opponent's turn ending scores nothing",
          ctrl.begin_end_of_turn("Player 2", battle_round=1), 0)
checks.eq("my own turn ending scores the rounds-1-2 box",
          ctrl.begin_end_of_turn("Player 1", battle_round=1),
          pm.BATTLEFIELD_DOMINANCE_MORE_VP)
checks.eq("...and it is out of band in round 3",
          ctrl.begin_end_of_turn("Player 1", battle_round=3), 0)

# END OF COMMAND PHASE fires only for your own Command phase.
checks.eq("the opponent's Command phase ending scores nothing",
          ctrl.end_of_command_phase("Player 2", battle_round=2), 0)
checks.eq("round 1 is out of band for the 2nd-round-onward box",
          ctrl.end_of_command_phase("Player 1", battle_round=1), 0)
checks.eq("round 2 pays 3 VP for the one objective",
          ctrl.end_of_command_phase("Player 1", battle_round=2), 3)
checks.eq("and it pays AGAIN in round 3 - a Primary box is not spent",
          ctrl.end_of_command_phase("Player 1", battle_round=3), 3)

checks.eq("everything landed in the shared Primary ledger",
          ledger.primary_points["Player 1"], pm.BATTLEFIELD_DOMINANCE_MORE_VP + 6)
checks.eq("the controller's own running total agrees with it",
          ctrl.points, ledger.primary_points["Player 1"])

# END OF BATTLE pays once, however often it is reached.
clear_control()
mc.central_objectives(ctx())[0].controlled_by = "Player 1"
ctrl, ledger, actions, turn, log, box = controller(pm.UNSTOPPABLE_FORCE)
checks.eq("final scoring pays", ctrl.score_end_of_battle(), pm.UNSTOPPABLE_CENTRAL_VP)
checks.eq("...and pays only once", ctrl.score_end_of_battle(), 0)
checks.eq("the ledger has it once", ledger.primary_points["Player 1"],
          pm.UNSTOPPABLE_CENTRAL_VP)

# The gate: a player not on the card system scores nothing here and keeps
# "Hold the Line" instead.
clear_control()
OBJ["Central Objective"].controlled_by = "Player 1"
was = config.PRIMARY_MISSION_CARD_PLAYERS
config.PRIMARY_MISSION_CARD_PLAYERS = ()
ctrl, ledger, actions, turn, log, box = controller(pm.BATTLEFIELD_DOMINANCE)
checks.eq("off the card system, no box scores",
          ctrl.end_of_command_phase("Player 1", battle_round=2), 0)
# One controlled objective, at the standard Primary's own rate. Pinned against
# the CONSTANT rather than the number: that rate has been retuned once (3 -> 6,
# user: "primary gibt 6 Punkte pro objektive, statt 3"), and three tests
# hardcoding it meant three edits for one decision.
checks.eq("...and Hold the Line runs for them",
          ledger.score_primary(board.objectives, "Player 1", 2),
          missions.PRIMARY_POINTS_PER_OBJECTIVE)
config.PRIMARY_MISSION_CARD_PLAYERS = ("Player 1",)
ledger2 = MissionController(game_log=tk.Log())
checks.eq("on the card system, Hold the Line is skipped entirely",
          ledger2.score_primary(board.objectives, "Player 1", 2), 0)
checks.eq("...while the AI still gets it",
          ledger2.score_primary(board.objectives, "Player 2", 2), 0)
OBJ["Central Objective"].controlled_by = "Player 2"
checks.eq("...really gets it, when it holds something",
          ledger2.score_primary(board.objectives, "Player 2", 2),
          missions.PRIMARY_POINTS_PER_OBJECTIVE)
config.PRIMARY_MISSION_CARD_PLAYERS = was

# Kills are per TURN: a kill in the opponent's turn does not carry into mine.
clear_control()
ctrl, ledger, actions, turn, log, box = controller(pm.RECONNAISSANCE_SWEEP)
ctrl.record_destroyed_squad(DeadSquad("Player 2"))
checks.eq("a kill during the opponent's turn scores nothing at their turn end",
          ctrl.begin_end_of_turn("Player 2", battle_round=1), 0)
checks.eq("...and is not carried into mine",
          ctrl.begin_end_of_turn("Player 1", battle_round=1), 0)
# ...and the same squad cannot be counted twice in one turn.
ctrl2, ledger2, _a, _t, _l, _b = controller(pm.RECONNAISSANCE_SWEEP)
twice = DeadSquad("Player 2")
ctrl2.record_destroyed_squad(twice)
ctrl2.record_destroyed_squad(twice)
checks.eq("the same destroyed squad counts once",
          ctrl2.begin_end_of_turn("Player 1", battle_round=1), pm.RECON_PER_KILL_VP)

# resolve_end_of_turn() is idempotent per player per turn - two mission
# systems ask it at the same instant and neither may fire an EFFECT twice.
clear_control()
ctrl, ledger, actions, turn, log, box = controller(pm.DEATH_TRAP)
fresh = [a for a in outside if not pm.area_is_trapped(ctrl._context(), a)]
bx0, by0, bx1, by1 = fresh[0].bounding_box
u = unit("Player 1", (bx0 + bx1) / 2.0, (by0 + by1) / 2.0, models=1, name="1 Trappers 9")
box.extend(u.models)
offer = [o for o in ctrl.available_actions_for(u) if o[2] is fresh[0]]
ctrl.start_action(offer[0][1], u, fresh[0])
first = actions.resolve_end_of_turn("Player 1", ctrl._context())
again = actions.resolve_end_of_turn("Player 1", ctrl._context())
checks.eq("a second resolve returns the same list", [id(s) for s in first], [id(s) for s in again])
checks.eq("...and does not trap the area twice",
          len(ctrl.card_state.get(pm.DEATH_TRAP_SLOT, [])), 1)
actions.reset_for_turn()
checks.eq("reset_for_turn clears the guard", actions._resolved_for, None)

# What the guard actually BUYS has to be measured with an action that has a
# real EFFECT, and none of the four shipped ones does at this seam: Cleanse,
# Plunder and Secure Asset all pass effect=None (completing IS the effect), and
# Booby Trap's fires at start() because it completes immediately. So an A/B
# probe that deleted the guard changed nothing observable and the checks above
# stayed green - a finding about them, not a licence to drop the guard, which
# exists precisely for the next action that does have one.
from game.actions import ActionDefinition as _AD  # noqa: E402

fired = []
counting = _AD(key="probe_effect", name="Probe", starts=PHASE_SHOOTING,
               units=lambda squad, c: True,
               completes=lambda state, c: True,
               effect=lambda state, c: fired.append(state))
probe_unit = unit("Player 1", 8.0, 8.0, models=1, name="1 Probes 1")
probe_box = list(probe_unit.models)
probe_actions = ActionController(tokens_source=lambda: probe_box, game_log=tk.Log())
probe_actions.start(counting, probe_unit, None, None)
probe_actions.resolve_end_of_turn("Player 1", None)
checks.eq("an action with a real effect fires it once", len(fired), 1)
probe_actions.resolve_end_of_turn("Player 1", None)
checks.eq("...and a SECOND resolve at the same instant does not fire it again - "
          "two mission systems ask at that seam", len(fired), 1)
probe_actions.reset_for_turn()
probe_actions.start(counting, probe_unit, None, None)
probe_actions.resolve_end_of_turn("Player 1", None)
checks.eq("...but the next turn does fire it again", len(fired), 2)
# The guard is per PLAYER, not merely "already ran once".
probe_actions.reset_for_turn()
probe_actions.start(counting, probe_unit, None, None)
probe_actions.resolve_end_of_turn("Player 2", None)
checks.eq("resolving for the OTHER player does not fire my action", len(fired), 2)
probe_actions.resolve_end_of_turn("Player 1", None)
checks.eq("...and mine still resolves afterwards", len(fired), 3)


# ============================== 9b. the operation markers actually draw
print("--- 9b. the trapped-area markers, on a real surface ---")

# Drawn for real, not merely checked for existence. The first version of
# draw_terrain_markers() called _clamp_rect_to_surface() as a bare name when it
# is a static method on the class - it would have raised NameError the first
# time a marker was drawn WITH ITS LABEL, and nothing here or in the smoke
# reached that line (the smoke starts a trap on its final frame). The free-name
# sweep in test_event_chain_wiring.py caught it; this makes it a behaviour.
import pygame  # noqa: E402

pygame.init()
from game.board import Board  # noqa: E402
from game.renderer import Renderer  # noqa: E402

_board = Board(config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN, 12.0)
_renderer = Renderer()
_surface = pygame.Surface((_board.width_px, _board.height_px))
_surface.fill((0, 0, 0))
_marked = [plain_area, objective_area]
_renderer.draw_terrain_markers(_surface, _board, _marked, label="TRAPPED")
_lit = sum(1 for x in range(0, _surface.get_width(), 3)
           for y in range(0, _surface.get_height(), 3)
           if _surface.get_at((x, y))[:3] != (0, 0, 0))
checks.true("drawing markers puts something on the surface", _lit > 0)
# ...including the LABEL, which is the half that crashed.
_blank = pygame.Surface((_board.width_px, _board.height_px))
_blank.fill((0, 0, 0))
_renderer.draw_terrain_markers(_blank, _board, _marked, label="")
_lit_unlabelled = sum(1 for x in range(0, _blank.get_width(), 3)
                      for y in range(0, _blank.get_height(), 3)
                      if _blank.get_at((x, y))[:3] != (0, 0, 0))
checks.true("the label draws MORE than the outline alone", _lit > _lit_unlabelled)
# An empty list is a no-op rather than an error - the normal case for four of
# the five missions, and it runs every frame.
_untouched = pygame.Surface((_board.width_px, _board.height_px))
_untouched.fill((0, 0, 0))
_renderer.draw_terrain_markers(_untouched, _board, [], label="TRAPPED")
checks.eq("no marked areas draws nothing at all",
          sum(1 for x in range(0, _untouched.get_width(), 7)
              for y in range(0, _untouched.get_height(), 7)
              if _untouched.get_at((x, y))[:3] != (0, 0, 0)), 0)
# The marker colour must not be either player's objective colour or the
# SECURED gold: a trapped area is neither owned ground nor a secured objective.
from game import renderer as _rmod  # noqa: E402

checks.true("the marker colour is not a player identity colour",
            _rmod.TRAPPED_AREA_COLOR not in _rmod.OBJECTIVE_COLORS.values())
checks.true("...nor the SECURED badge gold",
            _rmod.TRAPPED_AREA_COLOR != _rmod.SECURED_BADGE_COLOR)

# The controller answers the render path for every mission, not only Death Trap.
_dt_ctrl, _, _, _, _, _ = controller(pm.DEATH_TRAP)
checks.eq("nothing trapped yet: no markers", _dt_ctrl.trapped_areas_on_board(), [])
_dt_ctrl.card_state[pm.DEATH_TRAP_ALL_SLOT] = {id(plain_area): plain_area}
checks.eq("a trapped area becomes a marker",
          [id(a) for a in _dt_ctrl.trapped_areas_on_board()], [id(plain_area)])
_sa_ctrl, _, _, _, _, _ = controller(pm.SECURE_ASSET)
_sa_ctrl.card_state[pm.DEATH_TRAP_ALL_SLOT] = {id(plain_area): plain_area}
checks.eq("a mission that is not Death Trap never draws markers, whatever is "
          "in its state", _sa_ctrl.trapped_areas_on_board(), [])


# ================================================ 10. the main.py wiring
print("--- 10. wiring: the seams no suite can otherwise see ---")

MAIN = open("main.py", encoding="utf-8").read()

# This repo has SIX recorded cases of a controller that was built, unit-tested
# and never FED - a class of bug no behaviour test can see, because a suite
# drives the controller directly. So each feed is checked by its CALL
# EXPRESSION, not by counting the name: a mention in a docstring counts as an
# occurrence and once left a guard green after the real call was deleted.
for label, needle in [
    ("constructed", "primary_mission_controller = PrimaryMissionController("),
    ("fed the board", "primary_mission_controller.set_tokens_source("),
    ("fed the objectives", "primary_mission_controller.set_objectives_source("),
    ("fed the zones", "primary_mission_controller.set_zones_source("),
    ("fed the terrain", "primary_mission_controller.set_terrain_source("),
    ("snapshots each turn", "primary_mission_controller.snapshot_turn_start()"),
    ("fed destroyed units", "primary_mission_controller.record_destroyed_squad(dead.squad)"),
    ("scores at end of turn", "primary_mission_controller.begin_end_of_turn("),
    ("scores at end of Command phase", "primary_mission_controller.end_of_command_phase("),
    ("scores at end of battle", "primary_mission_controller.score_end_of_battle()"),
    ("announces its mission", "primary_mission_controller.announce()"),
]:
    checks.true(f"main.py: the Primary is {label}", needle in MAIN)


# Ordering is checked against a COMMENT-STRIPPED copy. The first version was
# not, and it failed against correctly ordered code: the comment explaining
# "BEFORE action_controller.reset_for_turn() below" contains that call
# verbatim, and find() reached the explanation before the call. That is this
# repo's recorded "the guard matched its own explanation" failure, and the fix
# belongs in the guard rather than in the wording of the comment.
MAIN_CODE = "\n".join(
    line for line in MAIN.split("\n") if not line.lstrip().startswith("#"))


def before(haystack, first, second, label):
    """`first` appears before `second`. Uses find() and CHECKS both were found,
    rather than str.index(), which throws when a needle goes missing and takes
    the whole suite down instead of turning one line red - three recorded
    instances of that in this repo."""
    i, j = haystack.find(first), haystack.find(second)
    checks.true(label, i != -1 and j != -1 and i < j)


# The action controller is a CONSTRUCTOR ARGUMENT, so it has to exist first.
# Three UnboundLocalErrors of exactly this shape are why that guard exists.
before(MAIN_CODE, "action_controller = ActionController(",
       "primary_mission_controller = PrimaryMissionController(",
       "main.py: the ActionController is built BEFORE the Primary that takes it")
# Scoring reads this turn's completed actions; resetting first throws them away.
before(MAIN_CODE, "primary_mission_controller.begin_end_of_turn(",
       "action_controller.reset_for_turn()",
       "main.py: the Primary scores BEFORE 16.01's per-turn reset")
# Final scoring has to land in the ledger before the result overlay reads it.
before(MAIN_CODE, "primary_mission_controller.score_end_of_battle()",
       "battle_end_overlay.show(mission_controller)",
       "main.py: final scoring runs BEFORE the result overlay reads the ledger")
# The end-of-Command-phase box belongs to the phase that ENDED.
checks.true("main.py: the Command-phase box is scored from phase_before, "
            "with the player who owned it",
            re.search(r"if phase_before == PHASE_COMMAND:.{0,900}?"
                      r"primary_mission_controller\.end_of_command_phase\(\s*mover_before",
                      MAIN_CODE, re.S) is not None)

# The action RESULT SLOT moved onto the ActionDefinition. Reverting it to the
# old `if action.key == "plunder" else ...` is behaviour-identical for the two
# cards that existed then, so no scoring check can see it - an A/B probe that
# put the branch back broke nothing. What changed is that a THIRD action can no
# longer land in the else branch, and that is what is checked here: each action
# names its own slot, and the storing code asks the action instead of guessing.
from game import secondary_missions as _sm  # noqa: E402

SECONDARY_SRC = open("game/secondary_missions.py", encoding="utf-8").read()
checks.true("the slot comes from the action, not from a branch on its key",
            "slot = card.action.result_slot" in SECONDARY_SRC)
checks.eq("...and no branch on the action key survives",
          'card.action.key == "plunder"' in SECONDARY_SRC, False)
slots = {a.name: a.result_slot for a in
         (_sm.PLUNDER_ACTION, _sm.CLEANSE_ACTION,
          pm.SECURE_ASSET_ACTION, pm.BOOBY_TRAP_ACTION)}
checks.eq("all four actions have DISTINCT slots", len(set(slots.values())), 4)
checks.eq("the two older ones keep the names their cards already read",
          (slots["Plunder"], slots["Cleanse"]),
          ("plundered_this_turn", "cleansed_this_turn"))
checks.eq("an action that names no slot derives one from its key rather than "
          "sharing another action's",
          _AD(key="fifth", name="Fifth", starts=PHASE_SHOOTING,
              units=lambda s, c: True, completes=lambda s, c: True,
              effect=None).result_slot,
          "fifth_this_turn")

MISSIONS_SRC = open("game/missions.py", encoding="utf-8").read()
checks.true("Hold the Line is skipped through ONE definition, inside "
            "score_primary() rather than at its three call sites",
            "if self.plays_primary_mission_card(player):" in MISSIONS_SRC)
checks.eq("score_primary() is still called from all three places",
          MAIN.count("mission_controller.score_primary(state.objectives"), 3)


# ================================= 11. no harness opt-out, and no AI path
print("--- 11. the absences ---")

# The Secondary deck asks the human a question at the end of every one of their
# turns, so eight harnesses have to switch it off. A Primary asks nothing, so
# none of them does - and that is an asset (selfplay and the smokes exercise
# the real Primary every run), which is why it is asserted rather than left to
# be discovered by whoever adds the ninth harness.
HARNESSES = ["selfplay.py", "smoke_pregame.py", "smoke_log_input.py",
             "smoke_setup_screens.py", "smoke_measure_tool.py",
             "smoke_end_turn_warning.py", "smoke_selection.py", "smoke_line_drag.py"]
for name in HARNESSES:
    src = open(name, encoding="utf-8").read()
    checks.true(f"{name} turns the SECONDARY deck off (unchanged)",
                "SECONDARY_MISSION_CARD_PLAYERS = ()" in src)
    checks.eq(f"{name} does NOT need to turn the Primary off",
              "PRIMARY_MISSION_CARD_PLAYERS = ()" in src, False)

# Standing user instruction: the AI keeps "Hold the Line". Checked as negative
# space, which is stronger than counting calls.
AI_SRC = open("ai/agent_driver.py", encoding="utf-8").read()
for needle in ("primary_missions", "force_disposition", "Booby Trap", "Secure Asset",
               "Death Trap", "Unstoppable Force", "Battlefield Dominance",
               "Reconnaissance Sweep"):
    checks.eq(f"the AI has no path for {needle!r}", needle in AI_SRC, False)


# ============================ 11b. the standing "opponent is Take and Hold"
print("--- 11b. the assumption behind all five cards ---")

# Every one of the five cards prints "OPPONENT: TAKE AND HOLD" - they are the
# deck for a game whose OTHER player is on Take and Hold. The engine does not
# enforce that (there is nothing sensible to do about it mid-battle), so it
# says so in the log instead, and only when it is actually violated.
_was1, _was2 = config.PLAYER1_ARMY, config.PLAYER2_ARMY
try:
    config.PLAYER1_ARMY, config.PLAYER2_ARMY = "aeldari", "necrons"
    quiet_log = tk.Log()
    pm.PrimaryMissionController(player="Player 1", game_log=quiet_log).announce()
    checks.true("it names which Primary the human is on",
                quiet_log.has("plays Secure Asset"))
    checks.eq("...and says nothing about the opponent when they ARE Take and Hold",
              quiet_log.has("not Take and Hold"), False)

    config.PLAYER2_ARMY = "tau"          # Reconnaissance
    loud_log = tk.Log()
    loud = pm.PrimaryMissionController(player="Player 1", game_log=loud_log)
    loud.announce()
    checks.true("a violated assumption IS named", loud_log.has("not Take and Hold"))
    checks.true("...naming what the opponent is actually on",
                loud_log.has("Reconnaissance"))
    before = len(loud_log.lines)
    loud.announce()
    checks.eq("announce() is idempotent - it is provenance, not a running commentary",
              len(loud_log.lines), before)
finally:
    config.PLAYER1_ARMY, config.PLAYER2_ARMY = _was1, _was2


# ================================================= 11c. the mission strip
print("--- 11c. the strip shows the right card to the right player ---")

from game.ui.mission_cards import MissionCardsOverlay, PRIMARY  # noqa: E402

_ledger = MissionController(game_log=tk.Log())
_ledger.add_primary_points("Player 1", 7)
_strip = MissionCardsOverlay()
_pc, _, _, _, _, _ = controller(pm.DEATH_TRAP)
_pc.card_state[pm.DEATH_TRAP_ALL_SLOT] = {id(objective_area): objective_area}

_own = _strip._build_cards("Player 1", _ledger, None, _pc)
checks.eq("the human's strip leads with their own Primary",
          (_own[0].category, _own[0].title), (PRIMARY, "Death Trap"))
checks.eq("...showing the running score", _own[0].status, "7 pts")
# `info` is now (LABEL, value) PAIRS rather than space-padded strings - the
# padding only ever lined up in a monospace font, and config.FONT_NAME is
# pygame's proportional default (see game/ui/mission_cards.py).
checks.true("...and every info row is a (label, value) pair, not a padded string",
            all(isinstance(row, tuple) and len(row) == 2 for row in _own[0].info))
# The per-box timings moved OUT of `info` and into the WHAT | WHEN | VP scoring
# table, which is where a rate card belongs - `info` keeps the one-off facts
# (disposition, Objective Action). Same claim as before, asked of the row set
# that now carries it.
checks.true("...its per-box timings and round bands, which the prose omits",
            any("end of your Command phase" in when for _, when, _vp in _own[0].scoring))
checks.true("...one scoring row per printed box",
            len(_own[0].scoring) == len(pm.DEATH_TRAP.boxes))
checks.true("...each a (what, when, vp) triple",
            all(isinstance(row, tuple) and len(row) == 3 for row in _own[0].scoring))
# The column the user actually asked for. A blank VP cell reads as "pays
# nothing", so every box must state its rate.
checks.eq("...and every one states its VP",
          [what for what, _when, vp in _own[0].scoring if not str(vp).strip()], [])
checks.true("...and what it has remembered, which the prose cannot say",
            "Trapped" in (_own[0].detail or ""))

# The controller belongs to Player 1. Asked about Player 2, the strip must
# fall back to "Hold the Line" rather than showing Player 1's card.
_theirs = _strip._build_cards("Player 2", _ledger, None, _pc)
checks.eq("the OTHER player still gets Hold the Line, not this card",
          _theirs[0].title, "Hold the Line")
# ...and so does anyone at all when the feature is off.
_was = config.PRIMARY_MISSION_CARD_PLAYERS
config.PRIMARY_MISSION_CARD_PLAYERS = ()
checks.eq("with the feature off, so does the human",
          _strip._build_cards("Player 1", _ledger, None, _pc)[0].title, "Hold the Line")
config.PRIMARY_MISSION_CARD_PLAYERS = _was
checks.eq("and with no controller at all it still draws a Primary bar",
          _strip._build_cards("Player 1", _ledger, None, None)[0].title, "Hold the Line")


# ============================== 12. the extraction stayed behaviour-neutral
print("--- 12. the mission_context extraction ---")

from game import secondary_missions as sm  # noqa: E402

for name in ["MissionContext", "board_centre", "objective_centre", "zone_distance",
             "in_own_territory", "no_mans_land_objectives", "own_home_objective",
             "enemy_home_objective", "table_quarters", "unit_has_presence_in",
             "quarters_with_presence", "model_distance_to_point",
             "_non_home_objectives", "_live_squads", "_other_player"]:
    checks.true(f"secondary_missions re-exports the SAME {name} object, "
                f"not a copy of it",
                getattr(sm, name) is getattr(mc, name))
checks.eq("the 6\" centre exclusion is ONE value, not two 6.0s",
          sm.ENGAGE_CENTRE_EXCLUSION_IN, mc.CENTRE_EXCLUSION_IN)


checks.finish()
