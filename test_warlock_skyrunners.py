"""Warlock Skyrunners - the jetbike Warlock.

Its near-twin is the foot Warlock Conclave, which is exactly why this suite is
written as a COMPARISON: the two share a psychic kit and, word for word, a
LEADER ability that is a JOIN rather than a 19.01 attachment. They differ in
three ways that all had to be read off the printed sheet rather than inherited:

  * it rides - MOUNTED/FLY, M14", so no Dense-terrain crossing (13.06) and no
    Hidden (13.09);
  * it joins WINDRIDERS, not Guardians;
  * it does NOT have Protect. Copying a near-identical datasheet is precisely
    how a free ability gets handed out by accident, so that is pinned.

Runes of Battle shares the unit-level Ignores Cover flag The Twin Lance prints
instead of getting a module - the game/fieldcraft.py precedent - so it is
checked through the real _cover_ignored_for_group(), not off the flag.
"""

import testkit as tk
from game import attached_units as au
from game import status_effects
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.units import WarlockSkyrunnerProfile, WarlockProfile

checks = tk.Checks("Warlock Skyrunners")

LINE = "Warlock Skyrunner"


def skyrunners(choices=None, composition_index=0, name="1 Warlock Skyrunners 1"):
    return tk.build(ae.WARLOCK_SKYRUNNERS, "Player 1", name=name,
                    choices=choices, composition_index=composition_index)


def windriders(name="1 Windriders 1"):
    return tk.build(ae.WINDRIDERS, "Player 1", name=name)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

one = skyrunners()
two = skyrunners(composition_index=1)
checks.eq("1-model unit", len(one.models), 1)
checks.eq("2-model unit", len(two.models), 2)
checks.eq("...costs 55", one.points, 55)
checks.eq("...and 90", two.points, 90)

p = WarlockSkyrunnerProfile()
foot = WarlockProfile()
checks.eq("M14\"", p.movement_in, 14)
checks.eq("T4", p.toughness, 4)
checks.eq("Sv6+", p.armor_save, "6+")
checks.eq("W3", p.wounds, 3)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC2", p.oc, 2)
checks.eq("BS3+ / WS3+", (p.ballistic_skill, p.weapon_skill), ("3+", "3+"))
checks.eq("4+ invulnerable save", p.invulnerable_save, "4+")
# ON-TABLE SIZE, not the printed base - a user call, so it is pinned as one
# rather than as arithmetic off the datasheet. The three MOUNTED jetbike units
# in the roster (Shining Spears, Shroud Runners, Warlock Skyrunners) were set to
# match EACH OTHER at 45 mm: the first two came down a quarter from 60 mm, the
# Skyrunner came up from 32 mm. Checked against the other two rather than
# against a literal, so the three cannot drift apart unnoticed.
from game.units import ShiningSpearProfile, ShroudRunnerProfile, WindriderProfile  # noqa: E402
checks.eq("45 mm on the table (printed base is 32 mm - this one went UP)",
          p.base_radius_in, round(45 / 2 / 25.4, 3))
checks.eq("...the same as the Shining Spears", p.base_radius_in, ShiningSpearProfile.base_radius_in)
checks.eq("...and the same as the Shroud Runners", p.base_radius_in, ShroudRunnerProfile.base_radius_in)
# The Windriders were NOT part of that call and keep their printed 32 mm, so the
# Skyrunner no longer matches the jetbike it joins. Deliberate and pinned, since
# the two shared a value until now and a later "fix" would otherwise look tidy.
#
# THE PREMISE HAS SINCE CHANGED, which is why this line is worth re-reading
# rather than trusting: when the sizes were set, the note recorded that the
# Windriders were "in no demo army", so the mismatch was theoretical. The
# Aeldari list now fields 3 Windriders WITH this Skyrunner merged into them
# (19.01), so a 45 mm base sits in a unit of 32 mm ones - the same shape the
# Skorpekh Lord's note calls "exactly where the difference would show". It is a
# GAMEPLAY number, not a cosmetic one (edge_distance() reads the radius, so
# engagement range, overlap, coherency and formation packing all move with it),
# so it is named here rather than quietly aligned. Measured to still work: the
# merged unit deploys all 4 models and holds coherency over a full self-play
# run. Aligning them is a decision for whoever asks for it.
checks.true("...but the Windriders it joins were left on their printed 32 mm",
            p.base_radius_in != WindriderProfile.base_radius_in)

# Where it differs from the foot Warlock, stated as a comparison so a copy of
# the wrong value shows up as a failure here.
checks.true("twice the foot Warlock's speed", p.movement_in == 2 * foot.movement_in)
checks.true("tougher than him", p.toughness > foot.toughness)
checks.true("...and more wounds", p.wounds > foot.wounds)
checks.eq("...but a worse armour save than his? no - the same",
          p.armor_save, foot.armor_save)

checks.true("MOUNTED on the keyword line", "MOUNTED" in ae.WARLOCK_SKYRUNNERS.keywords)
checks.true("FLY", "FLY" in ae.WARLOCK_SKYRUNNERS.keywords)
checks.true("PSYKER", "PSYKER" in ae.WARLOCK_SKYRUNNERS.keywords)
checks.true("WARLOCKS - the keyword Eldrad's own clause reads",
            "WARLOCKS" in ae.WARLOCK_SKYRUNNERS.keywords)
checks.eq("NOT infantry", p.infantry, False)
checks.true("...so FLY is flagged for 21.03", p.fly)
checks.true("PSYKER flagged", p.psyker)
checks.true("Battle Focus", p.battle_focus)
checks.true("Psychic Communion, like the foot Warlock", p.psychic_communion)

# THE ONE IT MUST NOT HAVE.
checks.eq("NOT Protect - the printed ability list does not have it",
          getattr(p, "protect", False), False)
checks.true("...while the foot Warlock does, which is what makes it worth pinning",
            foot.protect)

# MOUNTED has consequences, read off the rules that care rather than the flag.
checks.eq("13.09: it can never be Hidden (that needs INFANTRY/BEASTS/SWARM)",
          status_effects.is_hidden(one.models[0], [], None, None), False)


# --- 2. weapons and wargear -------------------------------------------------
print("--- 2. weapons and wargear ---")


def loadout(squad, i=0):
    return sorted(w.name + ("" if w.weapon_type == "ranged" else " (M)")
                  for w in squad.models[i].weapons)


checks.eq("default: Destructor, Shuriken Pistol, Twin Shuriken Catapult, Witchblade",
          loadout(one),
          ["Destructor", "Shuriken Pistol", "Twin Shuriken Catapult", "Witchblade (M)"])
# Every weapon is shared with datasheets already here - nothing new was needed.
for name, cls in (("Destructor", "DestructorProfile"),
                  ("Shuriken Pistol", "ShurikenPistolProfile"),
                  ("Twin Shuriken Catapult", "TwinShurikenCatapultProfile"),
                  ("Witchblade", "WitchbladeProfile")):
    got = next(w for w in one.models[0].weapons if w.name == name)
    checks.eq("%s is the shared profile" % name, type(got).__name__, cls)

# "Any number of models can each have their witchblade replaced with 1 singing
# spear" - and the Singing Spear is one printed weapon with a thrown row AND a
# melee row, so the swap grants both.
speared = skyrunners(composition_index=1, choices={LINE: {ae.SKYRUNNER_WITCHBLADE_TO_SPEAR: 2}})
checks.eq("-> Singing Spear on both models", loadout(speared),
          ["Destructor", "Shuriken Pistol", "Singing Spear", "Singing Spear (M)",
           "Twin Shuriken Catapult"])
checks.eq("...so no Witchblade is left",
          [w.name for m in speared.models for w in m.weapons if w.name == "Witchblade"], [])
one_spear = skyrunners(composition_index=1, choices={LINE: {ae.SKYRUNNER_WITCHBLADE_TO_SPEAR: 1}})
checks.true("...and taking it on only one model leaves the other on its Witchblade",
            any(w.name == "Witchblade" for w in one_spear.models[1].weapons))


# --- 3. the LEADER ability is a JOIN ----------------------------------------
print("--- 3. the JOIN ---")

# Word for word the Warlock Conclave's wording, so it takes the same route
# through can_attach() - a JOIN with its own one-per-unit limit rather than
# 19.01's one-leader default.
checks.true("the JOIN flag is set", p.joins_without_leader_slot)
checks.eq("it may join Windriders", au.can_attach(skyrunners(), windriders()), [])
joined = au.attach(skyrunners(), windriders())
checks.eq("...producing one 4-model unit", len(joined.models), 4)
checks.eq("...of two components", len(au.components(joined)), 2)
# Its own printed limit is enforced.
checks.true("a SECOND Skyrunners unit is refused",
            bool(au.can_attach(skyrunners(name="1 Warlock Skyrunners 2"), joined)))
# ...and the pairing table is the points list's `leads`, so a wrong guess would
# have been refused rather than silently built.
checks.true("it may NOT join Shining Spears",
            bool(au.can_attach(skyrunners(name="1 WS 3"),
                               tk.build(ae.SHINING_SPEARS, "Player 1", name="1 Shining Spears 1"))))
checks.true("...nor Guardian Defenders, which the FOOT Warlock joins",
            bool(au.can_attach(skyrunners(name="1 WS 4"),
                               tk.build(ae.GUARDIAN_DEFENDERS, "Player 1",
                                        name="1 Guardian Defenders 1"))))


# --- 4. Runes of Battle ------------------------------------------------------
print("--- 4. Runes of Battle ---")

# "Weapons equipped by models in this unit have the [IGNORES COVER] ability."
# Measured through the REAL _cover_ignored_for_group(), because a flag nobody
# reads would pass an equality check and do nothing in play.
scene = tk.shooting_scene(ae.WARLOCK_SKYRUNNERS, tau.KROOT_CARNIVORES,
                          attacker_owner="Player 1")
sc = scene["shooting"]
sc.active_squad = scene["attacker"]
catapult = next(w for w in scene["attacker"].models[0].weapons
                if w.name == "Twin Shuriken Catapult")
checks.true("cover is bypassed for a weapon with no [IGNORES COVER] of its own",
            sc._cover_ignored_for_group(catapult, scene["target"]))
checks.eq("...and the weapon itself does NOT carry the keyword - the unit rule does",
          catapult.ignores_cover, False)

# A/B: the same weapon fired by a unit without the rule does not bypass cover.
plain = tk.shooting_scene(ae.WINDRIDERS, tau.KROOT_CARNIVORES, attacker_owner="Player 1")
plain["shooting"].active_squad = plain["attacker"]
plain_catapult = next(w for w in plain["attacker"].models[0].weapons
                      if w.name == "Twin Shuriken Catapult")
checks.eq("A/B: Windriders firing the same weapon do not bypass cover",
          plain["shooting"]._cover_ignored_for_group(plain_catapult, plain["target"]), False)

# After the JOIN (19.01) the two are ONE unit, so "models in this unit" now
# covers the Windriders' own guns too - which is the point of joining.
merged_scene = tk.shooting_scene(ae.WINDRIDERS, tau.KROOT_CARNIVORES, attacker_owner="Player 1")
merged = au.attach(skyrunners(name="1 Warlock Skyrunners J"), merged_scene["attacker"])
merged_scene["shooting"].active_squad = merged
rider_gun = next(w for w in merged.models[0].weapons if w.name == "Twin Shuriken Catapult")
checks.true("joined: the Windriders' own weapons bypass cover too",
            merged_scene["shooting"]._cover_ignored_for_group(rider_gun, merged_scene["target"]))

# A/B on the flag itself.
import copy as _copy  # noqa: E402

probe = tk.shooting_scene(ae.WARLOCK_SKYRUNNERS, tau.KROOT_CARNIVORES, attacker_owner="Player 1")
probe["shooting"].active_squad = probe["attacker"]
for model in probe["attacker"].models:
    model.profile = _copy.copy(model.profile)
    model.profile.ignores_cover = False
probe_gun = next(w for w in probe["attacker"].models[0].weapons
                 if w.name == "Twin Shuriken Catapult")
checks.eq("A/B: with Runes of Battle off, cover applies again",
          probe["shooting"]._cover_ignored_for_group(probe_gun, probe["target"]), False)
for model in probe["attacker"].models:
    model.profile.ignores_cover = True
checks.true("A/B: restored",
            probe["shooting"]._cover_ignored_for_group(probe_gun, probe["target"]))


# --- 5. sprite --------------------------------------------------------------
print("--- 5. sprite ---")

from game import sprites  # noqa: E402

# Art arrived after the datasheet was built. Checked at the model, not at the
# mapping table: a key that resolves to no file on disk is exactly the failure
# this is here to catch.
checks.true("Warlock Skyrunners resolve a sprite", sprites.sprite_for(one.models[0]))
checks.true("...and it is the file's three-word spelling, not the datasheet's one word",
            "Warlock Sky Runner" in (sprites.sprite_for(one.models[0]) or ""))


checks.finish()
