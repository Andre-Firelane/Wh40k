"""Beast Snagga Boyz (Orks), 2026-09 codex - datasheet, weapons and wargear.

Run: python test_beast_snagga.py

Pinned against rules/orks/Beast Snagga Boyz.md: both printed builds, both
profile rows, the weapon rows (the Choppa is TWO profiles now, the second a
Hunter profile - rule 04.01.03), the Thump Gun as an ADDITION per 10 models,
the points - and the retirement of what the codex no longer prints (Feel No
Pain 6+, Monster Hunters). The mechanisms behind the Choppa's profiles are
pinned with synthetic weapons in test_weapon_profiles.py; this suite pins that
THIS datasheet carries them as printed.
"""
from collections import Counter

import testkit as tk
from game import weapon_profiles
from game.factions.orks import BEAST_SNAGGA_BOYZ, BEAST_SNAGGA_BOYZ_THUMP_GUN, BOYZ
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM
from game.keyword_condition import MONSTER_OR_VEHICLE_TARGETS
from game.units import UnitProfile
from game.weapons import printed_keywords

c = tk.Checks("Beast Snagga Boyz (2026-09 codex)")


def build(choices=None, composition_index=0):
    return tk.build(BEAST_SNAGGA_BOYZ, "Player 2", choices=choices, composition_index=composition_index)


def counts(squad):
    return dict(Counter(m.profile.name for m in squad.models))


def weapon(model, name):
    return next((w for w in model.weapons if w.name == name), None)


def carriers(squad, name):
    return [m for m in squad.models if weapon(m, name) is not None]


print("--- 1. the two printed builds ---")
small, big = build(), build(composition_index=1)
c.eq("10 models: 1 Nob + 9 Beast Snagga Boys", counts(small), {"Beast Snagga Nob": 1, "Beast Snagga Boy": 9})
c.eq("20 models: 2 Nobs + 18 Beast Snagga Boys", counts(big), {"Beast Snagga Nob": 2, "Beast Snagga Boy": 18})
c.eq("points for a 1st-3rd unit: 85 / 170", (small.points, big.points), (85, 170))
c.eq("the Nob line is printed as 'Nob'", [line.name for line in BEAST_SNAGGA_BOYZ.composition_options[0]],
     ["Nob", "Beast Snagga Boy"])
c.eq("datasheet keywords", set(BEAST_SNAGGA_BOYZ.keywords), {"INFANTRY", "BATTLELINE", "BEAST SNAGGA", "MOB"})

print("--- 2. the two profile rows ---")
nob, boy = small.models[0], small.models[1]
c.true("the Nob is the leader model", nob.profile.squad_leader)
for label, p, wounds in (("Nob", nob.profile, 3), ("Beast Snagga Boy", boy.profile, 1)):
    c.eq(f"{label}: M/T/Sv/W/Ld/OC", (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc),
         (6, 5, "5+", wounds, "7+", 2))
    c.eq(f"{label}: WS/BS off the weapon rows", (p.weapon_skill, p.ballistic_skill), ("3+", "5+"))
    c.eq(f"{label}: 32mm base", round(p.base_radius_in, 2), 0.63)
    c.true(f"{label}: INFANTRY", p.infantry)
    c.true(f"{label}: BEAST SNAGGA (what a Kill Rig carries)", p.beast_snagga)
    c.eq(f"{label}: no Feel No Pain any more", p.feel_no_pain, UnitProfile.feel_no_pain)
    c.eq(f"{label}: no Monster Hunters any more", getattr(p, "monster_hunters", False), False)
c.eq("the Nob prints a 6+ invulnerable save", nob.profile.invulnerable_save, "6+")
c.eq("...a Beast Snagga Boy none", boy.profile.invulnerable_save, UnitProfile.invulnerable_save)

print("--- 3. the weapon rows ---")
snappa = weapon(nob, "Power Snappa")
c.eq("Power Snappa A/S/AP/D", (snappa.attacks, snappa.strength, snappa.ap, snappa.damage) if snappa else None,
     (3, 8, -2, 2))
c.eq("...[ANTI-MONSTER/VEHICLE 4+]", printed_keywords(type(snappa)) if snappa else None,
     ["ANTI-MONSTER/VEHICLE 4+"])

choppa = weapon(boy, "Choppa - Standard")
c.true("a Beast Snagga Boy carries the Choppa under its first profile's name", choppa is not None)
chain = weapon_profiles.profiles(choppa) if choppa else []
c.eq("the Choppa has two profiles, in printed order", [p.name for p in chain],
     ["Choppa - Standard", "Choppa - Hunter"])
if len(chain) == 2:
    standard, hunter = chain
    c.eq("Standard A/S/AP/D", (standard.attacks, standard.strength, standard.ap, standard.damage), (3, 5, -1, 1))
    c.eq("Hunter A/S/AP/D", (hunter.attacks, hunter.strength, hunter.ap, hunter.damage), (3, 6, -2, 1))
    c.eq("Hunter prints HUNTER: MONSTER/VEHICLE", hunter.hunter_keywords, MONSTER_OR_VEHICLE_TARGETS)
    c.true("...so it may target a vehicle",
           weapon_profiles.hunter_allows(hunter, tk.build(DEVILFISH, "Player 1")))
    c.true("...and not infantry",
           not weapon_profiles.hunter_allows(hunter, tk.build(STRIKE_TEAM, "Player 1")))
    c.true("...while the Standard profile may target anything",
           weapon_profiles.hunter_allows(standard, tk.build(STRIKE_TEAM, "Player 1")))
boyz_choppa = weapon(tk.build(BOYZ, "Player 2").models[1], "Choppa")
c.true("the Standard profile IS the Boyz' Choppa row, renamed (a subclass, so they cannot drift)",
       choppa is not None and boyz_choppa is not None and issubclass(type(choppa), type(boyz_choppa)))

slugga = weapon(boy, "Slugga")
c.eq("Slugga range/A/S", (slugga.range_in, slugga.attacks, slugga.strength) if slugga else None, (12, 1, 4))
c.eq("Slugga keywords: CLOSE-QUARTERS and a conditional LETHAL HITS",
     printed_keywords(type(slugga)) if slugga else None, ["CLOSE-QUARTERS", "LETHAL HITS: non-MONSTER/VEHICLE"])

print("--- 4. the Thump Gun is an addition, one per 10 models ---")
THUMP = {"Beast Snagga Boy": {BEAST_SNAGGA_BOYZ_THUMP_GUN: 1}}
with_gun = build(THUMP)
gunners = carriers(with_gun, "Thump Gun")
c.eq("exactly one carrier", len(gunners), 1)
if gunners:
    c.eq("the carrier keeps its Choppa and Slugga", sorted(w.name for w in gunners[0].weapons),
         ["Choppa - Standard", "Slugga", "Thump Gun"])
    thump = weapon(gunners[0], "Thump Gun")
    c.eq("Thump Gun range/A/S/AP/D", (thump.range_in, thump.attacks, thump.strength, thump.ap, thump.damage),
         (18, 3, 6, 0, 2))
    c.eq("...no dice Attacks, no [BLAST] any more", (thump.attacks_notation, thump.blast), (None, 0))
    c.eq("...[ANTI-MONSTER/VEHICLE 4+]", printed_keywords(type(thump)), ["ANTI-MONSTER/VEHICLE 4+"])
c.eq("the Thump Gun is free", with_gun.points, 85)
c.eq("an over-eager choice is trimmed to one per 10 models",
     len(carriers(build({"Beast Snagga Boy": {BEAST_SNAGGA_BOYZ_THUMP_GUN: 5}}), "Thump Gun")), 1)
c.eq("...and the 20-model build takes two",
     len(carriers(build({"Beast Snagga Boy": {BEAST_SNAGGA_BOYZ_THUMP_GUN: 5}}, composition_index=1), "Thump Gun")), 2)
c.eq("the Nob's line cannot take it",
     len(carriers(build({"Nob": {BEAST_SNAGGA_BOYZ_THUMP_GUN: 1}}), "Thump Gun")), 0)

c.finish()
