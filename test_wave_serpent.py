"""Wave Serpent: statline, the twin-linked gun rack, the wargear, the
transport, the Wave Serpent Shield, and the sprite.

The shield is the reason this suite exists. It is the only defender-side wound
modifier in the engine whose condition is about the ATTACK rather than about who
is shooting - "if the Strength characteristic of that attack is greater than the
Toughness characteristic of this model" - so it is the first thing that needed
the attack's Strength threaded into _wound_modifiers(). It is therefore measured
through the REAL controller, on both sides of the S>T line, rather than off the
predicate: a modifier that is computed and never reaches the roll is exactly the
failure a predicate-only test cannot see.
"""

import testkit as tk
from game import sprites, strength_over_toughness, wave_serpent_shield
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.weapons import (
    ShurikenCannonProfile,
    TwinBrightLanceProfile,
    TwinMissileLauncherStarshotProfile,
    TwinMissileLauncherSunburstProfile,
    TwinScatterLaserProfile,
    TwinShurikenCannonProfile,
    TwinShurikenCatapultProfile,
    TwinStarcannonProfile,
    WraithboneHullProfile,
)

checks = tk.Checks("Wave Serpent")

LINE = "Wave Serpent"


def serpent(choices=None, owner="Player 1", name="1 Wave Serpent 1"):
    return tk.build(ae.WAVE_SERPENT, owner, name=name,
                    choices={LINE: choices} if choices else None)


def weapon_names(squad):
    return sorted(w.name for w in squad.models[0].weapons)


# --- 1. statline ------------------------------------------------------------
print("--- 1. statline ---")

one = serpent()
p = one.models[0].profile

checks.eq("M14\"", p.movement_in, 14)
checks.eq("T9", p.toughness, 9)
checks.eq("Sv3+", p.armor_save, "3+")
checks.eq("W13", p.wounds, 13)
checks.eq("Ld7+", p.leadership, "7+")
checks.eq("OC2", p.oc, 2)
checks.eq("BS3+", p.ballistic_skill, "3+")
checks.eq("Invulnerable Save 5+", p.invulnerable_save, "5+")
checks.eq("VEHICLE", p.vehicle, True)
checks.eq("FLY", p.fly, True)
checks.eq("Deadly Demise D3 (24.08)", p.deadly_demise_notation.sides, 3)
checks.eq("Damaged 1-4 wounds remaining", p.damaged_threshold, 4)
checks.eq("Battle Focus (army rule)", p.battle_focus, True)
checks.eq("Wave Serpent Shield flag", p.wave_serpent_shield, True)
checks.eq("no Deep Strike printed - unlike the Falcon",
          getattr(p, "deep_strike", False), False)

# Not the printed 60 mm: the Falcon was enlarged to match the Devilfish on user
# request, and these two are the same hull - having them sit on the table at
# wildly different sizes would be the odd result. Pinned against the Falcon
# rather than a literal so the pair cannot drift apart unnoticed.
checks.eq("base radius matched to the Falcon, not the printed 60 mm",
          p.base_radius_in, ae.FALCON.model_lines[0].profile_cls.base_radius_in)

# WS is not on the printed statline; the hull prints its own 4+, and that is the
# only melee this model has, so the profile is set to agree rather than left on
# the class default.
checks.eq("WS4+ agrees with the Wraithbone hull's printed WS",
          p.weapon_skill, WraithboneHullProfile().weapon_skill)

checks.eq("one model", len(one.models), 1)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("default loadout",
          weapon_names(one),
          ["Twin Shuriken Cannon", "Twin Shuriken Catapult", "Wraithbone Hull"])

# Every gun on this datasheet is a gun that already existed plus [TWIN-LINKED],
# which is why they SUBCLASS rather than repeat the numbers: a change to the
# shared statline has to reach the twin version. Checked pair by pair, since a
# copy-pasted class would pass a "does it have the keyword" test just as well.
for twin_cls, base_name in (
    (TwinBrightLanceProfile, "Bright Lance"),
    (TwinScatterLaserProfile, "Scatter Laser"),
    (TwinShurikenCannonProfile, "Shuriken Cannon"),
    (TwinStarcannonProfile, "Starcannon"),
    (TwinMissileLauncherStarshotProfile, "Missile Launcher - Starshot"),
    (TwinMissileLauncherSunburstProfile, "Missile Launcher - Sunburst Blast"),
):
    twin = twin_cls()
    base = twin_cls.__bases__[0]()
    checks.eq("%s is [TWIN-LINKED]" % twin.name, twin.twin_linked, True)
    checks.eq("...and the plain %s is not" % base_name, base.twin_linked, False)
    checks.eq("...same S/AP/D as the gun it subclasses",
              (twin.strength, twin.ap, twin.damage),
              (base.strength, base.ap, base.damage))
    checks.eq("...same range", twin.range_in, base.range_in)

checks.eq("Twin Scatter Laser keeps [SUSTAINED HITS 1]",
          TwinScatterLaserProfile().sustained_hits, 1)
checks.eq("Twin Shuriken Cannon keeps [LETHAL HITS]",
          TwinShurikenCannonProfile().lethal_hits, True)
checks.eq("the twin missile launcher is ONE entry with two firing modes",
          TwinMissileLauncherStarshotProfile.overcharge_profile,
          TwinMissileLauncherSunburstProfile)
checks.eq("...and its sunburst mode carries [BLAST]",
          TwinMissileLauncherSunburstProfile().blast, 1)

hull = WraithboneHullProfile()
checks.eq("Wraithbone hull A3/WS4+/S6/AP0/D1",
          (hull.attacks, hull.weapon_skill, hull.strength, hull.ap, hull.damage),
          (3, "4+", 6, 0, 1))


# --- 3. wargear -------------------------------------------------------------
print("--- 3. wargear ---")

# Two independent printed sentences, so two independent swaps - the Falcon's
# exact shape. The turret's four alternatives are mutually exclusive (one model,
# so whichever lands first leaves the rest with nobody to claim); the hull gun's
# own swap gives up a DIFFERENT weapon and can be taken alongside any of them.
for option, expected in (
    (ae.WAVE_SERPENT_CANNON_TO_BRIGHT_LANCE, "Twin Bright Lance"),
    (ae.WAVE_SERPENT_CANNON_TO_SCATTER_LASER, "Twin Scatter Laser"),
    (ae.WAVE_SERPENT_CANNON_TO_STARCANNON, "Twin Starcannon"),
    (ae.WAVE_SERPENT_CANNON_TO_MISSILE, "Twin Missile Launcher - Starshot"),
):
    got = weapon_names(serpent({option: 1}))
    checks.true("%s arms the turret" % option, expected in got)
    checks.true("...and gives up the twin shuriken cannon",
                "Twin Shuriken Cannon" not in got)
    checks.true("...the hull gun is untouched", "Twin Shuriken Catapult" in got)

hull_swap = weapon_names(serpent({ae.WAVE_SERPENT_CATAPULT_TO_SHURIKEN_CANNON: 1}))
checks.true("the hull swap gives a single (NOT twin) shuriken cannon",
            "Shuriken Cannon" in hull_swap)
checks.true("...and gives up the catapult", "Twin Shuriken Catapult" not in hull_swap)
checks.true("...leaving the turret alone", "Twin Shuriken Cannon" in hull_swap)

both = weapon_names(serpent({ae.WAVE_SERPENT_CANNON_TO_BRIGHT_LANCE: 1,
                             ae.WAVE_SERPENT_CATAPULT_TO_SHURIKEN_CANNON: 1}))
checks.eq("the two sentences are independent - both can be taken",
          sorted(both), ["Shuriken Cannon", "Twin Bright Lance", "Wraithbone Hull"])

exclusive = weapon_names(serpent({ae.WAVE_SERPENT_CANNON_TO_BRIGHT_LANCE: 1,
                                  ae.WAVE_SERPENT_CANNON_TO_STARCANNON: 1}))
checks.eq("two turret swaps: only one lands",
          ("Twin Bright Lance" in exclusive, "Twin Starcannon" in exclusive),
          (True, False))


# --- 4. points --------------------------------------------------------------
print("--- 4. points ---")

entry = AELDARI_POINTS["Wave Serpent"]
checks.eq("1st unit = 115 pts", entry.cost_for(1, 1), 115)
checks.eq("3rd unit = 115 pts", entry.cost_for(1, 3), 115)
checks.eq("4th unit = 125 pts", entry.cost_for(1, 4), 125)
checks.eq("built squad carries the price", one.points, 115)
checks.eq("every wargear option is free",
          serpent({ae.WAVE_SERPENT_CANNON_TO_BRIGHT_LANCE: 1}).points, 115)


# --- 5. transport -----------------------------------------------------------
print("--- 5. transport ---")

checks.eq("capacity 12", p.transport_capacity, 12)
checks.true("INFANTRY only", p.transport_requires_infantry)
checks.eq("JUMP PACK excluded", p.transport_excludes, ("jump_pack",))
checks.true("DEDICATED TRANSPORT", "DEDICATED TRANSPORT" in ae.WAVE_SERPENT.keywords)

from game.formations import embark_errors  # noqa: E402

carrier = serpent()
dragons = tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1")
checks.eq("5 Fire Dragons fit", embark_errors(dragons, carrier.models[0], []), [])

# WRAITH CONSTRUCT models take two slots each, which the printed transport line
# says outright - 5 Wraithguard are 10 of the 12, so they fit, and a second
# INFANTRY unit on top does not.
wraith = tk.build(ae.WRAITHGUARD, "Player 1", name="1 Wraithguard 1")
checks.eq("5 Wraithguard fit (10 of 12 slots)",
          embark_errors(wraith, carrier.models[0], []), [])
checks.true("...but not alongside 5 more Fire Dragons",
            bool(embark_errors(dragons, carrier.models[0], [wraith])))

# JUMP PACK is the printed exclusion, and Warp Spiders carry the keyword.
spiders = tk.build(ae.WARP_SPIDERS, "Player 1", name="1 Warp Spiders 1")
checks.true("JUMP PACK models cannot ride",
            bool(embark_errors(spiders, carrier.models[0], [])))
checks.true("another vehicle cannot ride (INFANTRY only)",
            bool(embark_errors(serpent(name="1 Wave Serpent 2"), carrier.models[0], [])))


# --- 6. the Wave Serpent Shield --------------------------------------------
print("--- 6. Wave Serpent Shield ---")

checks.eq("unit_has_shield() reads the flag off the models",
          wave_serpent_shield.unit_has_shield(one), True)
checks.eq("...and a unit without it is not shielded",
          wave_serpent_shield.unit_has_shield(dragons), False)

# The whole ability is the S > T comparison. T9, so:
checks.eq("S12 > T9 -> the shield applies", wave_serpent_shield.applies(one, 12), True)
checks.eq("S10 > T9 -> applies", wave_serpent_shield.applies(one, 10), True)
checks.eq("S9 is NOT greater than T9 -> no shield",
          wave_serpent_shield.applies(one, 9), False)
checks.eq("S4 -> no shield", wave_serpent_shield.applies(one, 4), False)
checks.eq("no Strength in hand -> no shield (the optional argument degrades)",
          wave_serpent_shield.applies(one, None), False)
checks.eq("a unit without the ability is never shielded",
          wave_serpent_shield.applies(dragons, 12), False)

# End to end through the real controller, on BOTH sides of the S>T line, so the
# difference is attributable to the Strength and not to the scene.
from game.modifiers import apply_modifiers  # noqa: E402
from game.shooting import _wound_threshold  # noqa: E402

scene = tk.shooting_scene(ae.FIRE_DRAGONS, ae.WAVE_SERPENT, gap=6.0)
sc = scene["shooting"]
sc.active_squad = scene["attacker"]
target = scene["target"]


def threshold(strength):
    base = _wound_threshold(strength, 9)
    return apply_modifiers(base, sc._wound_modifiers(target, strength))


checks.eq("S12 vs T9: wounds on 3+ normally, 4+ behind the shield",
          (_wound_threshold(12, 9), threshold(12)), (3, 4))
checks.eq("S9 vs T9: 4+, and the shield does NOT fire",
          (_wound_threshold(9, 9), threshold(9)), (4, 4))
checks.eq("S4 vs T9: 6+, unchanged", (_wound_threshold(4, 9), threshold(4)), (6, 6))

named = [m.source for m in sc._wound_modifiers(target, 12)]
checks.true("...and the modifier names itself, so the roll can be explained",
            "Wave Serpent Shield" in named)
checks.eq("nothing is added below the line",
          [m.source for m in sc._wound_modifiers(target, 9)], [])

# A/B, through the controller rather than the predicate: neutralise the ability
# at its source and the SAME call must go back to the unmodified threshold. A
# predicate-only probe would leave open whether the modifier ever reached the
# roll, which is the failure this section exists to rule out.
#
# THE SOURCE IS THE CARRIER, not this module's re-exported applies(). Since the
# 48th extraction the arithmetic lives in game/strength_over_toughness.py and
# the controller reads the shared SHIELDS tuple; neutralising the wrapper here
# would leave the controller untouched and this A/B would quietly stop
# measuring anything. Patching the carrier is therefore the STRONGER pin - it
# proves the shooting controller really does consult that tuple.
checks.true("the shield is one of the shared S>T carriers",
            strength_over_toughness.WAVE_SERPENT_SHIELD in strength_over_toughness.SHIELDS)
checks.true("...and this module's applies() is that carrier's, not a second copy",
            wave_serpent_shield.applies(one, 12)
            is strength_over_toughness.WAVE_SERPENT_SHIELD.applies(one, 12))
shield = strength_over_toughness.WAVE_SERPENT_SHIELD
try:
    shield.applies = lambda squad, strength: False
    checks.eq("A/B: with the ability neutralised, S12 is back to a plain 3+",
              threshold(12), 3)
    checks.eq("...and no modifier is named", sc._wound_modifiers(target, 12), [])
finally:
    del shield.applies          # back to the class's own method
checks.eq("...restored", threshold(12), 4)

# RANGED only - the printed text says so. MEASURED THROUGH THE MELEE
# CONTROLLER, not at the source: this used to assert that game/fight.py never
# mentions "wave_serpent_shield", which stopped meaning anything the day the
# S>T arithmetic was extracted - fight.py reads game/strength_over_toughness.py
# now, so the old pin passed while saying nothing about the shield. An A/B
# probe that dropped the ranged-only filter altogether found it.
from game.factions import necrons as _nec  # noqa: E402
from game.weapons import GaussDestructorProfile  # noqa: E402

_melee = tk.fight_scene(_nec.SKORPEKH_DESTROYERS, ae.WAVE_SERPENT)
_fc = _melee["fight"]
_fc.fighting_squad = _melee["attacker"]
_big = GaussDestructorProfile()          # S14, comfortably over the hull's T9
checks.true("staging: that Strength really is over the Wave Serpent's Toughness",
            _big.strength > p.toughness)
checks.true("staging: the target really carries the shield",
            wave_serpent_shield.unit_has_shield(_melee["target"]))
checks.eq("the shield does NOT reach the Fight phase - its text says 'a RANGED attack'",
          _fc._wound_modifiers(_big, _melee["target"]), [])
checks.eq("...while the SAME attack in the Shooting phase is penalised",
          [m.source for m in sc._wound_modifiers(target, 14)], ["Wave Serpent Shield"])

# 19.02: the Toughness is read through attached_unit_toughness(), the same
# source the threshold it modifies uses, so the two can never disagree. Asked
# of the CARRIER since the extraction - this module now delegates, so grepping
# its own source for the name stopped meaning anything.
import inspect  # noqa: E402

checks.true("the toughness comes from attached_unit_toughness(), not the profile",
            "attached_unit_toughness" in inspect.getsource(strength_over_toughness))
# ...and on every unit this engine can build the two give the SAME answer, so
# no behaviour test can tell them apart. Pinned as the MEASUREMENT it is, so
# the day a mixed-Toughness merge exists this line moves rather than a silent
# assumption going stale.
from game.squad import attached_unit_toughness as _aut  # noqa: E402

_differ = [sh.name for sh in ae.AELDARI.datasheets.values()
           if tk.build(sh, "Player 1", name="t").models
           and tk.build(sh, "Player 1", name="t").models[0].profile.toughness
           != _aut(tk.build(sh, "Player 1", name="t"))]
checks.eq("measured: no Aeldari unit's first model disagrees with 19.02 today",
          _differ, [])


# --- 7. sprite --------------------------------------------------------------
print("--- 7. sprite ---")

checks.true("Wave Serpent resolves a sprite", sprites.sprite_for(one.models[0]))
checks.true("...and it is its own file",
            "Wave Serpent" in (sprites.sprite_for(one.models[0]) or ""))


checks.finish()
