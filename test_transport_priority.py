"""Which units the AI loads into which TRANSPORT during rule 03.01's Declare
Battle Formations step.

The reported failure: "ki soll keine gretchins in die transporter packen",
with a Gretchin unit riding in a Trukk in a real game
(logs/game_20260813_234034.log). The user asked whether something had been
FORCED aboard. Measured: no. The old _transport_affinity() had no notion of
unit type at all - it accepted any unit whose best ranged weapon reached under
18" and sorted those by reach, breaking ties by NAME. Gretchin (12" blasta) and
Boyz (12" slugga) tie on reach, so the Trukks loaded "2 Boyz 2" and then
"2 Gretchin 1" purely on alphabetical order, with room to spare.

Replaced by the user's own priority lists (TRANSPORT_PASSENGER_PRIORITY):

    prio battle wagon: 1. meganobs 2. boyz 3. flash gits
    prio kill rig:     beast boyz
    prio trukk:        1. slugga boyz mit warboss 2. slugga boyz 3. flash gits

Every check below runs against Player 2's REAL roster as main() builds it -
including the two EMBARK hints and the three attached units - because the
ordering only means anything against real capacities and real model counts.
"""

from testkit import Checks, DecisionManager, DiceManager, GameState

from ai import deployment_ai
from game import attached_units, formations, pregame
from game.factions import build_squad
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, BATTLEWAGON_ADD_ZZAP_GUN, BATTLEWAGON_ARD_CASE,
    BEAST_SNAGGA_BOYZ, BEASTBOSS, BOYZ, BOYZ_BIG_CHOPPA_TO_POWER_KLAW, DEFF_DREAD, FLASH_GITZ,
    FLASH_GITZ_AMMO_RUNT, GRETCHIN, KILL_RIG, MEGANOBZ, STORMBOYZ,
    STORMBOYZ_CHOPPA_TO_POWER_KLAW, TANKBUSTAS, TANKBUSTAS_ADD_ROKKIT_LAUNCHA,
    TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER, TRUKK, WARBIKERS, WARBIKERS_ADD_POWER_KLAW,
    WARBOSS, WARBOSS_ADD_ATTACK_SQUIG, WARBOSS_MEGA_ARMOUR,
)

c = Checks("transport passenger priority")


# ---------------------------------------------------------------------------
# Player 2's roster, exactly as main() assembles it
# ---------------------------------------------------------------------------
def ork_army():
    """Returns (pregame_controller, hints, transports_by_name, squads_by_name)."""
    state = GameState()
    army, hints, transports = [], {}, []

    def reg(squad, transport=None):
        army.append(squad)
        if transport is not None:
            hints[id(squad)] = (pregame.EMBARK, transport)
        return squad

    def mk(sheet, name, **kw):
        return build_squad(sheet, "Player 2", name=name, **kw)

    kill_rig = mk(KILL_RIG, "2 Kill Rig 1")
    transports.append(kill_rig.models[0])
    reg(kill_rig)

    bsb = attached_units.attach(
        mk(BEASTBOSS, "2 Beastboss 1"), mk(BEAST_SNAGGA_BOYZ, "2 Beast Snagga Boyz 1"),
        game_state=state,
    )
    reg(bsb, kill_rig.models[0])

    battlewagon = mk(
        BATTLEWAGON, "2 Battlewagon 1", gear={"Battlewagon": [BATTLEWAGON_ARD_CASE]},
        choices={"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1, BATTLEWAGON_ADD_ZZAP_GUN: 1}},
    )
    transports.append(battlewagon.models[0])
    reg(battlewagon)

    meganobz = attached_units.attach(
        mk(WARBOSS_MEGA_ARMOUR, "2 Warboss in Mega Armour 1"),
        mk(MEGANOBZ, "2 Meganobz 1", composition_index=1), game_state=state,
    )
    reg(meganobz, battlewagon.models[0])

    boyz1 = attached_units.attach(
        mk(WARBOSS, "2 Warboss 1", choices={"Warboss": {WARBOSS_ADD_ATTACK_SQUIG: 1}}),
        mk(BOYZ, "2 Boyz 1", choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}}),
        game_state=state,
    )
    reg(boyz1)
    reg(mk(BOYZ, "2 Boyz 2", choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}}))

    for i in (1, 2):
        trukk = mk(TRUKK, f"2 Trukk {i}")
        transports.append(trukk.models[0])
        reg(trukk)
    for i in (1, 2):
        reg(mk(GRETCHIN, f"2 Gretchin {i}"))
    for i in (1, 2):
        reg(mk(WARBIKERS, f"2 Warbikers {i}", composition_index=0,
               choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}}))
    reg(mk(STORMBOYZ, "2 Stormboyz 1", composition_index=1,
           choices={"Boss Nob": {STORMBOYZ_CHOPPA_TO_POWER_KLAW: 1}}))
    reg(mk(DEFF_DREAD, "2 Deff Dread 1"))
    reg(mk(FLASH_GITZ, "2 Flash Gitz 1", composition_index=1,
           gear={"Kaptin": [FLASH_GITZ_AMMO_RUNT]}))
    reg(mk(TANKBUSTAS, "2 Tankbustas 1",
           choices={"Boss Nob": {TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER: 1},
                    "Tankbusta": {TANKBUSTAS_ADD_ROKKIT_LAUNCHA: 1}}))

    ctrl = pregame.PregameController(
        game_state=state, setup_controller=None, dice_manager=DiceManager(),
        decision_manager=DecisionManager(),
    )
    ctrl.start({"Player 2": army}, transport_tokens=transports)
    ctrl.scene_hints = hints
    return (
        ctrl, hints,
        {formations.transport_name(t): t for t in transports},
        {s.name: s for s in army},
    )


def cargo_names(ctrl, transport):
    return sorted(s.name for s in ctrl.squads_assigned_to(transport))


# ---------------------------------------------------------------------------
# 1. The scene itself, so a later failure is attributable
# ---------------------------------------------------------------------------
ctrl, hints, transports, squads = ork_army()

c.eq("four transports on this roster", sorted(transports),
     ["2 Battlewagon 1", "2 Kill Rig 1", "2 Trukk 1", "2 Trukk 2"])
c.eq("Trukk capacity", transports["2 Trukk 1"].profile.transport_capacity, 12)
c.eq("Battlewagon capacity", transports["2 Battlewagon 1"].profile.transport_capacity, 22)
c.eq("Gretchin is 11 models", len(squads["2 Gretchin 1"].models), 11)
c.eq("Boyz 1 carries the Warboss (19.01)",
     bool(attached_units.leader_components(squads["2 Boyz 1 + Warboss"])), True)
c.eq("Boyz 2 carries no character",
     bool(attached_units.leader_components(squads["2 Boyz 2"])), False)

# The two facts that make the old reach heuristic the wrong tool, measured
# rather than asserted from memory: both units the user wants carried report a
# reach at or above the old 18" cut-off, so a priority list that merely
# reordered candidates inside that filter would still never load them.
c.eq("Flash Gitz reach", deployment_ai._max_ranged_range(squads["2 Flash Gitz 1"]), 24.0)
c.eq("Boyz-with-Warboss reach", deployment_ai._max_ranged_range(squads["2 Boyz 1 + Warboss"]), 24.0)
c.true("...and both are at/over the old passenger cut-off",
       min(deployment_ai._max_ranged_range(squads["2 Flash Gitz 1"]),
           deployment_ai._max_ranged_range(squads["2 Boyz 1 + Warboss"]))
       >= deployment_ai.TRANSPORT_PASSENGER_MAX_RANGE_IN)
c.eq("Gretchin reach is under it, which is why they used to qualify",
     deployment_ai._max_ranged_range(squads["2 Gretchin 1"]) < deployment_ai.TRANSPORT_PASSENGER_MAX_RANGE_IN,
     True)


# ---------------------------------------------------------------------------
# 2. The reported bug: Gretchin never ride
# ---------------------------------------------------------------------------
for name in ("2 Trukk 1", "2 Trukk 2", "2 Battlewagon 1", "2 Kill Rig 1"):
    for gretchin in ("2 Gretchin 1", "2 Gretchin 2"):
        c.eq(f"{gretchin} refused by {name}",
             deployment_ai._transport_affinity(squads[gretchin], transports[name], hints), None)

# A/B against the pre-fix behaviour, so "refused" is attributable to this fix
# and not to the scene: with the priority table and the exclusion both taken
# out of the picture, the same Gretchin unit is accepted again.
_saved_table = deployment_ai.TRANSPORT_PASSENGER_PRIORITY
_saved_never = deployment_ai.TRANSPORT_NEVER_EMBARK
deployment_ai.TRANSPORT_PASSENGER_PRIORITY = {}
deployment_ai.TRANSPORT_NEVER_EMBARK = ()
c.true("A/B: without the table+exclusion a Trukk would accept Gretchin again",
       deployment_ai._transport_affinity(
           squads["2 Gretchin 1"], transports["2 Trukk 1"], hints) is not None)
deployment_ai.TRANSPORT_PASSENGER_PRIORITY = _saved_table
deployment_ai.TRANSPORT_NEVER_EMBARK = _saved_never

# The exclusion stands on its own, independent of the priority lists: a
# transport with no list of its own falls through to the reach heuristic, and
# Gretchin must still be refused there.
deployment_ai.TRANSPORT_PASSENGER_PRIORITY = {}
c.eq("Gretchin still refused when a transport has no priority list",
     deployment_ai._transport_affinity(squads["2 Gretchin 1"], transports["2 Trukk 1"], hints), None)
c.true("...while the heuristic itself still works for others",
       deployment_ai._transport_affinity(
           squads["2 Stormboyz 1"], transports["2 Trukk 1"], hints) is not None)
deployment_ai.TRANSPORT_PASSENGER_PRIORITY = _saved_table


# ---------------------------------------------------------------------------
# 3. Each transport's order, entry by entry
# ---------------------------------------------------------------------------
def rank(squad_name, transport_name):
    """The priority index this transport gives that unit, or None."""
    affinity = deployment_ai._transport_affinity(
        squads[squad_name], transports[transport_name], hints)
    return None if affinity is None else affinity[1]


# Battlewagon: meganobz > boyz > flash gitz. Meganobz are also hinted here, so
# their tier is the hint's (0) - checked separately below; what matters for the
# order is that boyz outrank flash gitz and nothing else is wanted.
c.true("Battlewagon wants Meganobz",
       deployment_ai._transport_affinity(
           squads["2 Meganobz 1 + Warboss in Mega Armour"],
           transports["2 Battlewagon 1"], hints) is not None)
c.true("Battlewagon ranks Boyz above Flash Gitz",
       rank("2 Boyz 2", "2 Battlewagon 1") < rank("2 Flash Gitz 1", "2 Battlewagon 1"))
for unwanted in ("2 Stormboyz 1", "2 Tankbustas 1", "2 Warbikers 1", "2 Beast Snagga Boyz 1 + Beastboss"):
    c.eq(f"Battlewagon does not want {unwanted}",
         deployment_ai._transport_affinity(squads[unwanted], transports["2 Battlewagon 1"], hints), None)

# Kill Rig: beast boyz only.
c.true("Kill Rig wants the Beast Snagga Boyz",
       deployment_ai._transport_affinity(
           squads["2 Beast Snagga Boyz 1 + Beastboss"], transports["2 Kill Rig 1"], hints) is not None)
for unwanted in ("2 Boyz 1 + Warboss", "2 Boyz 2", "2 Flash Gitz 1", "2 Meganobz 1 + Warboss in Mega Armour"):
    c.eq(f"Kill Rig does not want {unwanted}",
         deployment_ai._transport_affinity(squads[unwanted], transports["2 Kill Rig 1"], hints), None)

# Trukk: boyz-with-warboss > boyz > flash gitz. The first two share one
# datasheet, which is the whole reason Passenger carries a `led` flag.
c.eq("Trukk ranks Boyz-with-Warboss first", rank("2 Boyz 1 + Warboss", "2 Trukk 1"), 0)
c.eq("Trukk ranks plain Boyz second", rank("2 Boyz 2", "2 Trukk 1"), 1)
c.eq("Trukk ranks Flash Gitz third", rank("2 Flash Gitz 1", "2 Trukk 1"), 2)
for unwanted in ("2 Meganobz 1 + Warboss in Mega Armour", "2 Beast Snagga Boyz 1 + Beastboss",
                 "2 Stormboyz 1", "2 Tankbustas 1", "2 Deff Dread 1"):
    c.eq(f"Trukk does not want {unwanted}",
         deployment_ai._transport_affinity(squads[unwanted], transports["2 Trukk 1"], hints), None)

# Passenger(led=...) itself: `led=None` must match both versions, otherwise
# listing the led entry first would EXCLUDE the plain unit rather than just
# outrank it.
c.true("Passenger('Boyz') matches the led unit too",
       deployment_ai.Passenger("Boyz").matches(squads["2 Boyz 1 + Warboss"]))
c.true("Passenger('Boyz') matches the plain unit",
       deployment_ai.Passenger("Boyz").matches(squads["2 Boyz 2"]))
c.eq("Passenger('Boyz', led=True) rejects the plain unit",
     deployment_ai.Passenger("Boyz", led=True).matches(squads["2 Boyz 2"]), False)
c.eq("Passenger matches on datasheet, not squad name",
     deployment_ai.Passenger("Boyz").matches(squads["2 Gretchin 1"]), False)


# ---------------------------------------------------------------------------
# 4. Scene EMBARK hints still outrank the table
# ---------------------------------------------------------------------------
c.eq("a hinted unit is tier 0 at its own transport",
     deployment_ai._transport_affinity(
         squads["2 Meganobz 1 + Warboss in Mega Armour"],
         transports["2 Battlewagon 1"], hints)[0], 0)
c.eq("a hinted unit is refused by every other transport",
     deployment_ai._transport_affinity(
         squads["2 Beast Snagga Boyz 1 + Beastboss"], transports["2 Trukk 1"], hints), None)
c.true("a hinted unit beats a table match at the same transport",
       deployment_ai._transport_affinity(
           squads["2 Meganobz 1 + Warboss in Mega Armour"],
           transports["2 Battlewagon 1"], hints)
       < deployment_ai._transport_affinity(
           squads["2 Boyz 2"], transports["2 Battlewagon 1"], hints))


# ---------------------------------------------------------------------------
# 5. End to end through plan_battle_formations()
# ---------------------------------------------------------------------------
ctrl, hints, transports, squads = ork_army()
log = type("L", (), {"lines": [], "add": lambda self, m, file_only=False: self.lines.append(m)})()
deployment_ai.plan_battle_formations(ctrl, "Player 2", enemy_squads=[], hints=hints, game_log=log)

c.eq("Kill Rig carries the Beast Snagga Boyz",
     cargo_names(ctrl, transports["2 Kill Rig 1"]), ["2 Beast Snagga Boyz 1 + Beastboss"])
c.eq("Battlewagon carries the Meganobz",
     cargo_names(ctrl, transports["2 Battlewagon 1"]),
     ["2 Meganobz 1 + Warboss in Mega Armour"])
c.eq("Trukk 1 carries the Warboss's Boyz",
     cargo_names(ctrl, transports["2 Trukk 1"]), ["2 Boyz 1 + Warboss"])
c.eq("Trukk 2 carries the other Boyz",
     cargo_names(ctrl, transports["2 Trukk 2"]), ["2 Boyz 2"])

embarked = [s for t in transports.values() for s in ctrl.squads_assigned_to(t)]
c.eq("no Gretchin embarked anywhere",
     [s.name for s in embarked if "Gretchin" in s.name], [])
c.eq("exactly four units embarked", len(embarked), 4)

# Flash Gitz are wanted third by both the Battlewagon and the Trukks and end up
# walking, which is the priority list working rather than failing: every
# transport is already loaded with something it ranks higher, and what is left
# of the Battlewagon's capacity (22 - 14 = 8) is under their 10 models.
c.eq("Flash Gitz stay on foot behind higher-priority units",
     [s.name for s in embarked if "Flash Gitz" in s.name], [])
c.true("...because no transport has room for their 10 models",
       all(
           t.profile.transport_capacity
           - formations.transport_capacity_used(t, ctrl.squads_assigned_to(t))
           < len(squads["2 Flash Gitz 1"].models)
           for t in transports.values()
       ))

# Each load is legal in its own right (rule 18.01 capacity and datasheet
# restrictions), checked against the engine rather than by eye. `embarked_in`
# is cleared for the duration: plan_battle_formations() ends with
# finish_formations_for(), which applies the declarations, so embark_errors()
# would otherwise (correctly) answer "already embarked" - and the question here
# is whether the load it just made was a legal one.
for name, transport in transports.items():
    load = ctrl.squads_assigned_to(transport)
    for squad in load:
        others = [s for s in load if s is not squad]
        was, squad.embarked_in = squad.embarked_in, None
        c.eq(f"{squad.name} legally fits in {name}",
             formations.embark_errors(squad, transport, others), [])
        squad.embarked_in = was

# The log names the loads, which is what the old counting-only line could not
# do - the reported Gretchin ride had to be reconstructed from later disembark
# messages instead.
line = next((l for l in log.lines if l.startswith("[formations]")), "")
c.true("the formations log line names each transport's cargo",
       "2 Trukk 1 11/12 [2 Boyz 1 + Warboss]" in line)
c.true("...and its capacity use", "2 Battlewagon 1 14/22" in line)


# ---------------------------------------------------------------------------
# 6. Gretchin are still deployed normally, not lost
# ---------------------------------------------------------------------------
for name in ("2 Gretchin 1", "2 Gretchin 2"):
    c.eq(f"{name} is declared to deploy on the table",
         ctrl.declaration_for(squads[name])[0], pregame.DEPLOY)
c.true("both Gretchin units are in the pending deployment pool",
       all(squads[n] in ctrl.pending_units("Player 2") for n in ("2 Gretchin 1", "2 Gretchin 2")))

c.finish()
