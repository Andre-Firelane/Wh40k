"""Falcon: the first Aeldari VEHICLE and TRANSPORT, and Fire Support.

Fire Support is the only genuinely new mechanic, and it is a chain of three
facts that each live somewhere else - the unit hit, the transport ridden, the
wound re-roll offered. So it is driven through the REAL controllers at every
link: the mark is set by ShootingController's own after-shooting hook, the
provenance by TransportController.confirm_disembark(), and the effect is read
back out of _wound_reroll_reason() rather than off the controller.
"""

import testkit as tk
from testkit import Checks, script

from game import fire_support as fs
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Falcon")
LINE = "Falcon"


def falcon(choices=None, owner="Player 1"):
    return tk.build(ae.FALCON, owner, name="1 Falcon 1", choices=choices)


def weapon_names(squad):
    return sorted(w.name for w in squad.models[0].weapons)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

sq = falcon()
p = sq.models[0].profile
checks.eq("one model", len(sq.models), 1)
checks.eq("130 points", sq.points, 130)
checks.eq("no army-copy tiering", ae.FALCON.points_for(0, unit_index=4), 130)
checks.eq("M14\"", p.movement_in, 14)
checks.eq("T9", p.toughness, 9)
checks.eq("Sv3+", p.armor_save, "3+")
checks.eq("W12", p.wounds, 12)
checks.eq("Ld7+", p.leadership, "7+")
checks.eq("OC3", p.oc, 3)
checks.eq("no invulnerable save", p.invulnerable_save, "-")
checks.eq("60 mm base", round(p.base_radius_in, 3), round(60 / 2 / 25.4, 3))
checks.true("VEHICLE", p.vehicle)
checks.true("FLY", p.fly)
checks.true("TRANSPORT", p.transport)
checks.true("Deep Strike (24.09), from its CORE line", p.deep_strike)
checks.eq("Deadly Demise D3 (24.08)", p.deadly_demise_notation.sides, 3)
checks.eq("Damaged at 1-4 wounds remaining", p.damaged_threshold, 4)
checks.true("Battle Focus", p.battle_focus)
checks.true("Fire Support", p.fire_support)
for kw in ("VEHICLE", "TRANSPORT", "FLY", "FRAME", "FALCON"):
    checks.true(f"keyword {kw}", kw in ae.FALCON.keywords)


# --- 2. weapons and wargear ------------------------------------------------
print("--- 2. weapons and wargear ---")

checks.eq("default loadout", weapon_names(sq),
          ["Pulse Laser", "Scatter Laser", "Twin Shuriken Catapult", "Wraithbone Hull"])

laser = next(w for w in sq.models[0].weapons if w.name == "Pulse Laser")
checks.eq("Pulse Laser 48\"/A3/S9/AP-2",
          (laser.range_in, laser.attacks, laser.strength, laser.ap), (48, 3, 9, -2))
checks.eq("...with a rolled D6 Damage", laser.damage_notation.sides, 6)
scatter = next(w for w in sq.models[0].weapons if w.name == "Scatter Laser")
checks.eq("Scatter Laser 36\"/A6/S5/AP0/D1",
          (scatter.range_in, scatter.attacks, scatter.strength, scatter.ap, scatter.damage), (36, 6, 5, 0, 1))
checks.eq("...[SUSTAINED HITS 1]", scatter.sustained_hits, 1)
twin = next(w for w in sq.models[0].weapons if w.name == "Twin Shuriken Catapult")
checks.true("Twin Shuriken Catapult is [TWIN-LINKED]", twin.twin_linked)
checks.true("...and [ASSAULT]", twin.assault)
hull = next(w for w in sq.models[0].weapons if w.weapon_type == MELEE)
checks.eq("Wraithbone Hull A3/S6/AP0/D1", (hull.attacks, hull.strength, hull.ap, hull.damage), (3, 6, 0, 1))
checks.eq("...and prints its own WS4+", hull.weapon_skill, "4+")

for option, gained, lost in (
    (ae.FALCON_SCATTER_TO_MISSILE, "Missile Launcher - Starshot", "Scatter Laser"),
    (ae.FALCON_SCATTER_TO_BRIGHT_LANCE, "Bright Lance", "Scatter Laser"),
    (ae.FALCON_SCATTER_TO_SHURIKEN_CANNON, "Shuriken Cannon", "Scatter Laser"),
    (ae.FALCON_SCATTER_TO_STARCANNON, "Starcannon", "Scatter Laser"),
    (ae.FALCON_CATAPULT_TO_SHURIKEN_CANNON, "Shuriken Cannon", "Twin Shuriken Catapult"),
):
    names = weapon_names(falcon(choices={LINE: {option: 1}}))
    checks.true(f"{option}", gained in names and lost not in names)

# Two independent sentences: the catapult swap can be taken alongside any of
# the scatter-laser ones, because it gives up a different weapon.
both = weapon_names(falcon(choices={LINE: {ae.FALCON_SCATTER_TO_BRIGHT_LANCE: 1,
                                           ae.FALCON_CATAPULT_TO_SHURIKEN_CANNON: 1}}))
checks.eq("both sentences at once", both,
          ["Bright Lance", "Pulse Laser", "Shuriken Cannon", "Wraithbone Hull"])
# ...while the four scatter-laser options are "one of the following": one
# model, so whichever applies first leaves the rest with nobody to claim.
exclusive = weapon_names(falcon(choices={LINE: {ae.FALCON_SCATTER_TO_BRIGHT_LANCE: 1,
                                                ae.FALCON_SCATTER_TO_STARCANNON: 1}}))
checks.eq("two exclusive options -> only the first applies", exclusive,
          ["Bright Lance", "Pulse Laser", "Twin Shuriken Catapult", "Wraithbone Hull"])

# The missile launcher is ONE datasheet entry with two firing profiles, so the
# second is an alternate mode rather than a second weapon.
missile = next(w for w in falcon(choices={LINE: {ae.FALCON_SCATTER_TO_MISSILE: 1}}).models[0].weapons
               if w.name.startswith("Missile Launcher"))
checks.eq("only one missile launcher weapon is granted",
          sum(1 for w in falcon(choices={LINE: {ae.FALCON_SCATTER_TO_MISSILE: 1}}).models[0].weapons
              if w.name.startswith("Missile Launcher")), 1)
checks.eq("starshot is S10/AP-2 with a rolled D6 Damage",
          (missile.strength, missile.ap, missile.damage_notation.sides), (10, -2, 6))
alt = missile.overcharge_profile()
checks.eq("sunburst is its alternate mode: S4/AP-1, D6 attacks",
          (alt.strength, alt.ap, alt.attacks_notation.sides), (4, -1, 6))


# --- 3. transport ----------------------------------------------------------
print("--- 3. transport ---")

checks.eq("capacity 6", p.transport_capacity, 6)
checks.true("INFANTRY only", p.transport_requires_infantry)
checks.eq("JUMP PACK excluded", p.transport_excludes, ("jump_pack",))

from game.formations import embark_errors  # noqa: E402

carrier = falcon()
dragons5 = tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1")
spiders = tk.build(ae.WARP_SPIDERS, "Player 1", name="1 Warp Spiders 1")
dragons10 = tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 2", composition_index=1)
checks.eq("5 Fire Dragons fit", embark_errors(dragons5, carrier.models[0], []), [])
checks.true("10 do not (capacity 6)", bool(embark_errors(dragons10, carrier.models[0], [])))
# Warp Spiders are JUMP PACK - the printed exclusion, and the reason this
# datasheet's transport_excludes is not empty.
checks.true("Warp Spiders are JUMP PACK", spiders.models[0].profile.jump_pack)
checks.true("...so they cannot ride", bool(embark_errors(spiders, carrier.models[0], [])))
checks.true("a VEHICLE cannot ride either",
            bool(embark_errors(falcon(), carrier.models[0], [])))


# --- 4. Fire Support -------------------------------------------------------
print("--- 4. Fire Support ---")

ctrl = fs.FireSupportController(game_log=tk.Log())
target_a = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 1")
target_b = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 2")
rider = tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons R")
carrier = falcon()

checks.eq("nothing is marked to begin with", ctrl.marked_by(carrier.models[0]), None)
ctrl.offer_after_shooting(carrier, {target_a})
checks.eq("one unit hit -> marked without asking", ctrl.marked_by(carrier.models[0]), target_a)

# The mark alone is not enough: the attacker must have ridden in THAT Falcon.
checks.eq("a unit that did not disembark gets nothing", ctrl.applies(rider, target_a), False)
rider.disembarked_from_this_turn = carrier.models[0]
checks.true("one that did, against the marked unit, does", ctrl.applies(rider, target_a))
checks.eq("but not against a different unit", ctrl.applies(rider, target_b), False)
other = falcon()
rider.disembarked_from_this_turn = other.models[0]
checks.eq("nor if it rode in a DIFFERENT Falcon", ctrl.applies(rider, target_a), False)
rider.disembarked_from_this_turn = carrier.models[0]

# "Until the end of the turn".
ctrl.reset_turn()
checks.eq("the mark expires at end of turn", ctrl.applies(rider, target_a), False)

# Several units hit -> the player picks.
decisions = tk.DecisionManager() if hasattr(tk, "DecisionManager") else None
from game.decision import DecisionManager  # noqa: E402

dm = DecisionManager()
ctrl2 = fs.FireSupportController(decision_manager=dm, game_log=tk.Log())
ctrl2.offer_after_shooting(carrier, {target_a, target_b})
checks.true("two units hit -> a choice is raised", dm.is_pending)
checks.eq("...listing both", sorted(o["label"] for o in dm.options),
          sorted([target_a.name, target_b.name]))
tk.pick_option(dm, target_b.name)
checks.eq("and the chosen one is marked", ctrl2.marked_by(carrier.models[0]), target_b)

# A unit without the ability never marks anything.
plain = tk.build(tau.DEVILFISH, "Player 1", name="1 Devilfish 1")
ctrl3 = fs.FireSupportController(game_log=tk.Log())
ctrl3.offer_after_shooting(plain, {target_a})
checks.eq("a non-Falcon transport marks nothing", ctrl3.marked_by(plain.models[0]), None)
# ...and neither does a hit-less activation.
ctrl4 = fs.FireSupportController(game_log=tk.Log())
ctrl4.offer_after_shooting(carrier, set())
checks.eq("hitting nothing marks nothing", ctrl4.marked_by(carrier.models[0]), None)


# --- 5. Fire Support end to end --------------------------------------------
print("--- 5. Fire Support end to end ---")

# The provenance half through the REAL TransportController, not a hand-set
# field: this is the fact the engine did not record before this datasheet.
from game.transport import TransportController  # noqa: E402
import inspect  # noqa: E402

src = inspect.getsource(TransportController.confirm_disembark)
checks.true("confirm_disembark() records which transport the unit left",
            "disembarked_from_this_turn" in src)

# The effect half through the REAL wound-reroll lookup.
scene = tk.shooting_scene(ae.FIRE_DRAGONS, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
live = fs.FireSupportController(game_log=tk.Log())
scene["shooting"].fire_support = live
scene["shooting"].active_squad = scene["attacker"]
gun = next(w for w in scene["attacker"].models[1].weapons if w.weapon_type == RANGED)

checks.eq("no mark -> no re-roll from this source",
          scene["shooting"]._wound_reroll_reason(gun, scene["target"]), None)
live.offer_after_shooting(carrier, {scene["target"]})
scene["attacker"].disembarked_from_this_turn = carrier.models[0]
checks.eq("marked, and the shooter rode in that Falcon -> the re-roll is granted",
          scene["shooting"]._wound_reroll_reason(gun, scene["target"]), fs.FIRE_SUPPORT_LABEL)
checks.true("...as a WHOLE-roll re-roll, like every other 'you can re-roll the Wound roll'",
            scene["shooting"]._wound_reroll_is_full(gun, scene["target"]))
live.reset_turn()
checks.eq("and it is gone at end of turn",
          scene["shooting"]._wound_reroll_reason(gun, scene["target"]), None)


# --- 6. sprite -------------------------------------------------------------
print("--- 6. sprite ---")

checks.eq("Falcon art", _squad_key(sq.models[0]), "Falcon Tank")


# --- 7. A/B probe ----------------------------------------------------------
print("--- 7. A/B probe ---")

original = fs.FireSupportController.applies
fs.FireSupportController.applies = lambda self, a, t: False
live2 = fs.FireSupportController(game_log=tk.Log())
scene["shooting"].fire_support = live2
live2.offer_after_shooting(carrier, {scene["target"]})
checks.eq("A/B: unwired, the marked target grants nothing",
          scene["shooting"]._wound_reroll_reason(gun, scene["target"]), None)
fs.FireSupportController.applies = original
checks.eq("A/B: restored",
          scene["shooting"]._wound_reroll_reason(gun, scene["target"]), fs.FIRE_SUPPORT_LABEL)

checks.finish()
