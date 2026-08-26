"""Shining Spears - statline, weapons, wargear, and the three things worth
pinning rather than assuming:

  * MOUNTED, not INFANTRY. The fastest profile in the engine (M14"), and the
    consequences of NOT being infantry are real: no Dense-terrain crossing
    (13.06), no Hidden (13.09).
  * The laser lance is ONE printed weapon with a ranged row AND a melee row,
    so a wargear option that replaces it has to give up both.
  * It is the one ASPECT WARRIORS datasheet here whose wargear prints no
    Aspect Shrine token. Checked against its four sisters, because "the other
    Aspect Warriors have it" is exactly how it would get handed out by mistake.
"""

import testkit as tk
from game import aspect_shrine, invulnerable_save, status_effects
from game.factions import aeldari as ae
from game.units import ShiningSpearExarchProfile, ShiningSpearProfile

checks = tk.Checks("Shining Spears")

EXARCH = "Shining Spear Exarch"


def spears(choices=None, gear=None, composition_index=0):
    return tk.build(ae.SHINING_SPEARS, "Player 1", name="1 Shining Spears 1",
                    choices=choices, gear=gear, composition_index=composition_index)


def names(squad, model_index=0, kind=None):
    return sorted(w.name for w in squad.models[model_index].weapons
                  if kind is None or w.weapon_type == kind)


def weapon(squad, model_index, name, kind):
    return next(w for w in squad.models[model_index].weapons
                if w.name == name and w.weapon_type == kind)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

three = spears()
six = spears(composition_index=1)
checks.eq("3-model unit: 1 Exarch + 2", len(three.models), 3)
checks.eq("6-model unit: 1 Exarch + 5", len(six.models), 6)
checks.eq("...costs 100", three.points, 100)
checks.eq("...and 200", six.points, 200)

trooper = ShiningSpearProfile()
exarch = ShiningSpearExarchProfile()
checks.eq("M14\"", trooper.movement_in, 14)
checks.eq("T4", trooper.toughness, 4)
checks.eq("Sv3+", trooper.armor_save, "3+")
checks.eq("W2", trooper.wounds, 2)
checks.eq("Ld6+", trooper.leadership, "6+")
checks.eq("OC2", trooper.oc, 2)
checks.eq("BS3+ / WS3+", (trooper.ballistic_skill, trooper.weapon_skill), ("3+", "3+"))
checks.eq("5+ invulnerable save", trooper.invulnerable_save, "5+")
# ON-TABLE SIZE, not the printed base - a user call, so it is pinned as one
# rather than as arithmetic off the datasheet. The three MOUNTED jetbike units
# in the roster (Shining Spears, Shroud Runners, Warlock Skyrunners) were set to
# match EACH OTHER at 45 mm: the first two came down a quarter from 60 mm, the
# Skyrunner came up from 32 mm. Checked against the other two rather than
# against a literal, so the three cannot drift apart unnoticed.
from game.units import ShroudRunnerProfile, WarlockSkyrunnerProfile  # noqa: E402
checks.eq("45 mm on the table (printed base is 60 mm)",
          trooper.base_radius_in, round(45 / 2 / 25.4, 3))
checks.eq("...the same as the Shroud Runners",
          trooper.base_radius_in, ShroudRunnerProfile.base_radius_in)
checks.eq("...and the same as the Warlock Skyrunner",
          trooper.base_radius_in, WarlockSkyrunnerProfile.base_radius_in)
checks.eq("...the Exarch shares it", exarch.base_radius_in, trooper.base_radius_in)
# The Exarch differs in Wounds and nothing else.
checks.eq("the Exarch has W3", exarch.wounds, 3)
checks.eq("...same M", exarch.movement_in, trooper.movement_in)
checks.eq("...same BS", exarch.ballistic_skill, trooper.ballistic_skill)
checks.true("...and is highlighted as the squad leader", exarch.squad_leader)

# The fastest thing on the board - worth an explicit comparison rather than a
# bare 14, because the number is the point of the datasheet.
from game.factions import orks as ork  # noqa: E402

warbike = tk.build(ork.WARBIKERS, "Player 2", name="2 Warbikers 1").models[0]
checks.true("faster than Warbikers, the previous quickest",
            trooper.movement_in > warbike.profile.movement_in)

# MOUNTED, and what that costs.
checks.true("MOUNTED on the datasheet's keyword line", "MOUNTED" in ae.SHINING_SPEARS.keywords)
checks.true("FLY too", "FLY" in ae.SHINING_SPEARS.keywords)
checks.eq("NOT infantry", trooper.infantry, False)
checks.true("...so the FLY flag is set for rule 21.03", trooper.fly)
checks.true("Battle Focus (army rule)", trooper.battle_focus)
checks.eq("but NOT Fleet of Foot", getattr(trooper, "fleet_of_foot", False), False)
checks.eq("no LEADER ability", getattr(trooper, "leader", False), False)

# Not being INFANTRY has two concrete consequences, read off the rules that
# care rather than off the flag.
checks.eq("13.09: it can never be Hidden (that needs INFANTRY/BEASTS/SWARM)",
          status_effects.is_hidden(three.models[0], [], None, None), False)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("every model starts with laser lance + twin shuriken catapult",
          names(three, 0), ["Laser Lance", "Laser Lance", "Twin Shuriken Catapult"])
checks.eq("...the rank and file too", names(three, 1),
          ["Laser Lance", "Laser Lance", "Twin Shuriken Catapult"])

# ONE printed weapon, two rows.
lance_r = weapon(three, 0, "Laser Lance", "ranged")
lance_m = weapon(three, 0, "Laser Lance", "melee")
checks.eq("Laser Lance (ranged): 6\"/A1/S6/AP-2/D3",
          (lance_r.range_in, lance_r.attacks, lance_r.strength, lance_r.ap, lance_r.damage),
          (6, 1, 6, -2, 3))
checks.true("...[ASSAULT]", lance_r.assault)
checks.eq("...and no [LETHAL HITS] - the name column, not the keywords column, is the "
          "reliable one here", lance_r.lethal_hits, False)
checks.eq("Laser Lance (melee): A3/S5/AP-2/D3",
          (lance_m.attacks, lance_m.strength, lance_m.ap, lance_m.damage), (3, 5, -2, 3))
checks.true("...[LANCE] (rule 24.21)", lance_m.lance)
checks.eq("...[ANTI-MONSTER 3+] and [ANTI-VEHICLE 3+]", lance_m.anti,
          (("MONSTER", 3), ("VEHICLE", 3)))

catapult = weapon(three, 0, "Twin Shuriken Catapult", "ranged")
checks.eq("the Twin Shuriken Catapult is the shared profile",
          type(catapult).__name__, "TwinShurikenCatapultProfile")
checks.true("...[ASSAULT] + [TWIN-LINKED]", catapult.assault and catapult.twin_linked)


# --- 3. wargear options -----------------------------------------------------
print("--- 3. wargear options ---")

# Replacing the laser lance has to take BOTH its rows away, which is the whole
# reason `replaces` is a pair on that option.
sabre = spears(choices={EXARCH: {ae.SHINING_SPEAR_TO_PARAGON_SABRE: 1}})
checks.eq("-> Paragon Sabre: the Exarch keeps only the catapult and the sabre",
          names(sabre, 0), ["Paragon Sabre", "Twin Shuriken Catapult"])
checks.eq("...so NO laser lance row of either kind is left",
          [w.name for w in sabre.models[0].weapons if w.name == "Laser Lance"], [])
sabre_w = weapon(sabre, 0, "Paragon Sabre", "melee")
checks.eq("Paragon Sabre: A6/S5/AP-2/D2",
          (sabre_w.attacks, sabre_w.strength, sabre_w.ap, sabre_w.damage), (6, 5, -2, 2))
checks.eq("...no keywords at all",
          (sabre_w.lance, sabre_w.anti, sabre_w.lethal_hits), (False, None, False))
# ...and it is melee-only, so that Exarch gives up his 6" lance shot.
checks.eq("...melee only, so the Exarch loses his lance shot", names(sabre, 0, "ranged"),
          ["Twin Shuriken Catapult"])

star = spears(choices={EXARCH: {ae.SHINING_SPEAR_TO_STAR_LANCE: 1}})
checks.eq("-> Star Lance: both rows arrive", names(star, 0),
          ["Star Lance", "Star Lance", "Twin Shuriken Catapult"])
star_r = weapon(star, 0, "Star Lance", "ranged")
star_m = weapon(star, 0, "Star Lance", "melee")
checks.eq("Star Lance (ranged): 6\"/A1/S9/AP-3/D3",
          (star_r.range_in, star_r.attacks, star_r.strength, star_r.ap, star_r.damage),
          (6, 1, 9, -3, 3))
checks.true("...[ASSAULT]", star_r.assault)
checks.eq("Star Lance (melee): A4/S5/AP-3/D3",
          (star_m.attacks, star_m.strength, star_m.ap, star_m.damage), (4, 5, -3, 3))
checks.true("...[LANCE] and both [ANTI-X 3+]",
            star_m.lance and star_m.anti == (("MONSTER", 3), ("VEHICLE", 3)))

# "1 of the following" - and it falls out of the one-model line, as always.
both = spears(choices={EXARCH: {ae.SHINING_SPEAR_TO_PARAGON_SABRE: 1,
                                ae.SHINING_SPEAR_TO_STAR_LANCE: 1}})
checks.eq("sabre and star lance together trim to one", names(both, 0),
          ["Paragon Sabre", "Twin Shuriken Catapult"])

# The catapult swap is a SEPARATE printed sentence giving up a different
# weapon, so it stacks with either of the above.
cannon = spears(choices={EXARCH: {ae.SHINING_SPEAR_TO_SHURIKEN_CANNON: 1}})
checks.eq("-> Shuriken Cannon replaces the catapult, lance untouched",
          names(cannon, 0), ["Laser Lance", "Laser Lance", "Shuriken Cannon"])
stacked = spears(choices={EXARCH: {ae.SHINING_SPEAR_TO_STAR_LANCE: 1,
                                   ae.SHINING_SPEAR_TO_SHURIKEN_CANNON: 1}})
checks.eq("...and the two independent swaps stack", names(stacked, 0),
          ["Shuriken Cannon", "Star Lance", "Star Lance"])
checks.eq("the shared Shuriken Cannon, not a new one",
          type(weapon(cannon, 0, "Shuriken Cannon", "ranged")).__name__,
          "ShurikenCannonProfile")

# Only the Exarch, in every case.
checks.eq("the rank and file are untouched by all of it", names(stacked, 1),
          ["Laser Lance", "Laser Lance", "Twin Shuriken Catapult"])


# --- 4. Shimmershield --------------------------------------------------------
print("--- 4. Shimmershield ---")

# A pure ADDITION here, unlike the Dire Avenger Exarch's, which gives up his
# Shuriken Pistol for it - so it takes nothing away and needs no precondition.
shielded = spears(gear={EXARCH: [ae.SHINING_SPEAR_SHIMMERSHIELD]})
checks.eq("the Exarch's invulnerable save becomes 4+",
          invulnerable_save.effective_invulnerable_save(shielded.models[0]), "4+")
checks.eq("...the rest of the unit keeps the printed 5+",
          invulnerable_save.effective_invulnerable_save(shielded.models[1]), "5+")
checks.eq("...and it costs him no weapon", names(shielded, 0),
          ["Laser Lance", "Laser Lance", "Twin Shuriken Catapult"])
checks.eq("without it the Exarch is on 5+ too",
          invulnerable_save.effective_invulnerable_save(three.models[0]), "5+")


# --- 5. no Aspect Shrine token -----------------------------------------------
print("--- 5. no Aspect Shrine token ---")

# The printed wargear has no token entry, alone among the ASPECT WARRIORS
# datasheets here. Checked against all four sisters, because inheriting it from
# a near-identical datasheet is exactly the mistake this guards.
aspect_shrine.grant_tokens(three)
aspect_shrine.grant_tokens(six)
checks.eq("3 models -> 0 tokens", aspect_shrine.tokens_for(three), 0)
checks.eq("6 models -> still 0", aspect_shrine.tokens_for(six), 0)
checks.eq("...because no model carries the ability",
          any(m.profile.aspect_shrine for m in six.models), False)
for sheet, size in ((ae.STRIKING_SCORPIONS, 5), (ae.HOWLING_BANSHEES, 5),
                    (ae.WARP_SPIDERS, 5), (ae.DIRE_AVENGERS, 5), (ae.DARK_REAPERS, 5)):
    sister = tk.build(sheet, "Player 1", name="1 %s 1" % sheet.name)
    aspect_shrine.grant_tokens(sister)
    checks.eq("...while %s does get one" % sheet.name, aspect_shrine.tokens_for(sister), 1)


# --- 6. sprite ---------------------------------------------------------------
print("--- 6. sprite ---")

from game import sprites  # noqa: E402

# Art arrived after the datasheet was built. Checked at the model, not at the
# mapping table: a key that resolves to no file on disk is exactly the failure
# this is here to catch.
checks.true("Shining Spears resolve a sprite", sprites.sprite_for(three.models[0]))
checks.true("...and it is the Shining Spears file",
            "Shining Spears" in (sprites.sprite_for(three.models[0]) or ""))
checks.eq("the Exarch shares the unit's art - no separate file was supplied",
          sprites.sprite_for(three.models[0]), sprites.sprite_for(three.models[-1]))


# --- 7. A/B probe -------------------------------------------------------------
print("--- 7. A/B probe ---")

# The shimmershield is the one thing here that a single flag switches, so it is
# the honest A/B: with the grant removed the Exarch falls back to the printed
# save, which is what proves the 4+ above came from the item and not the sheet.
shielded.models[0].shimmershield = False
checks.eq("A/B: grant removed -> back to the printed 5+",
          invulnerable_save.effective_invulnerable_save(shielded.models[0]), "5+")
shielded.models[0].shimmershield = True
checks.eq("A/B: restored", invulnerable_save.effective_invulnerable_save(shielded.models[0]), "4+")


checks.finish()
