"""Player 1's army list, checked unit by unit against the list the user
supplied - every model line, every weapon, the five attached units and the
points each one comes to.

Builds the roster the same way main() does (same datasheets, same choices,
same attachment ORDER) rather than driving main() itself: that keeps the check
about WHAT the army is, independent of deployment, which the Pre-game Sequence
(03.01) now owns.

REWRITTEN when the roster went from T'au Empire to Aeldari, and REVISED again
when the Aeldari list itself changed (the Avatar of Khaine and the Fire Dragons
out; Dark Reapers, Rangers, Shining Spears, Shroud Runners and a Warlock
Skyrunner in). Both times the old file kept passing while it validated an army
that no longer existed - the same stale-test trap test_player2_army.py hit when
the Ork list was replaced. That is twice now for this one file, which is why the
totals below are written as the LIST's own numbers rather than as whatever the
engine happened to produce: a stale expectation that merely disagrees is caught,
one that was copied from the previous run is not.
"""

from game import attached_units, loadout
from game.factions import build_squad
from game.factions.aeldari import (
    ASURMEN, BANSHEE_BLADE_TO_EXECUTIONER, DARK_REAPERS, DIRE_AVENGERS,
    DIRE_AVENGER_SECOND_CATAPULT, ELDRAD_ULTHRAN, FALCON,
    FALCON_CATAPULT_TO_SHURIKEN_CANNON, FALCON_SCATTER_TO_BRIGHT_LANCE, FARSEER,
    FARSEER_WITCHBLADE_TO_SPEAR, GUARDIAN_DEFENDERS, HOWLING_BANSHEES,
    JAIN_ZAR, LHYKHIS, RANGERS, SHINING_SPEARS, SHINING_SPEAR_SHIMMERSHIELD,
    SHINING_SPEAR_TO_SHURIKEN_CANNON, SHINING_SPEAR_TO_STAR_LANCE, SHROUD_RUNNERS,
    STORM_GUARDIANS, STORM_GUARDIAN_CCW_TO_POWER_SWORD,
    STORM_GUARDIAN_PISTOL_TO_FLAMER, STORM_GUARDIAN_PISTOL_TO_FUSION,
    STRIKING_SCORPIONS, WARLOCK_CONCLAVE, WARLOCK_SKYRUNNERS,
    WARLOCK_WITCHBLADE_TO_SPEAR, WARP_SPIDERS,
    WARP_SPIDER_TO_POWERBLADE_ARRAY, WRAITHGUARD, WRAITHGUARD_TO_D_SCYTHE,
)

PASS = []
FAIL = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))


def build(datasheet, **kw):
    kw.setdefault("name", datasheet.name)
    return build_squad(datasheet, "Player 1", x_in=20, y_in=20, **kw)


def lines(squad):
    """{model line name: [(count, sorted weapon names)]} - the shape the list
    itself is written in ("10x Guardian Defender: 10 with Close Combat Weapon,
    Shuriken Catapult")."""
    out = {}
    for model in squad.models:
        key = model.profile.name
        weps = tuple(sorted(w.name for w in model.weapons))
        bucket = out.setdefault(key, {})
        bucket[weps] = bucket.get(weps, 0) + 1
    return out


def has_line(squad, line_name, count, *weapon_names):
    """`count` models of `line_name` carry EXACTLY `weapon_names`.

    Exact rather than a subset on purpose: the whole point of checking a list
    is that a weapon which should have been REPLACED is gone, and a subset
    test cannot see a leftover."""
    want = tuple(sorted(weapon_names))
    got = lines(squad).get(line_name, {})
    return got.get(want, 0) == count, f"{line_name}: {dict(got)}"


print("1. Units with no attached character")

reapers = build(DARK_REAPERS)
check("Dark Reapers: 5 models", len(reapers.models) == 5)
# The list gives Exarch and troopers the same Reaper Launcher, which IS the
# printed default - checked rather than assumed, because all three of this
# datasheet's options replace exactly the Exarch's launcher, so getting it wrong
# would have meant taking one of them.
check("...Exarch on a Reaper Launcher, with no option taken",
      *has_line(reapers, "Dark Reaper Exarch", 1, "Close Combat Weapon",
                "Reaper Launcher - Starshot"))
check("...4 on Reaper Launchers",
      *has_line(reapers, "Dark Reaper", 4, "Close Combat Weapon",
                "Reaper Launcher - Starshot"))

falcon = build(FALCON, choices={"Falcon": {FALCON_SCATTER_TO_BRIGHT_LANCE: 1,
                                          FALCON_CATAPULT_TO_SHURIKEN_CANNON: 1}})
# "Pulse Laser, Wraithbone hull, Bright Lance, Shuriken Cannon" - and the two
# swapped-away weapons have to be GONE, which is what makes this an exact test.
check("Falcon: Pulse Laser + Wraithbone Hull + Bright Lance + Shuriken Cannon",
      *has_line(falcon, "Falcon", 1, "Pulse Laser", "Wraithbone Hull",
                "Bright Lance", "Shuriken Cannon"))
check("...so the Scatter Laser it traded is gone",
      not any(w.name == "Scatter Laser" for m in falcon.models for w in m.weapons))
check("...and so is the Twin Shuriken Catapult",
      not any(w.name == "Twin Shuriken Catapult" for m in falcon.models for w in m.weapons))
check("Falcon costs 130", falcon.points == 130, str(falcon.points))

rangers = build(RANGERS)
check("Rangers: 5 models", len(rangers.models) == 5)
check("...all 5 on Long Rifle + Pistol + CCW (the datasheet has no options at all)",
      *has_line(rangers, "Ranger", 5, "Close Combat Weapon", "Long Rifle",
                "Shuriken Pistol"))
check("...and the datasheet really has none", len(RANGERS.wargear_options) == 0)

# "Shimmershield, Shuriken Cannon, Star Lance" is three printed sentences of two
# different kinds: two weapon swaps, and one pure ADDITION modelled as Gear. The
# only entry in this roster that uses the gear columns at all.
spears = build(SHINING_SPEARS,
               choices={"Shining Spear Exarch": {SHINING_SPEAR_TO_STAR_LANCE: 1,
                                                 SHINING_SPEAR_TO_SHURIKEN_CANNON: 1}},
               gear={"Shining Spear Exarch": [SHINING_SPEAR_SHIMMERSHIELD]})
check("Shining Spears: 3 models", len(spears.models) == 3)
# The lance is one printed weapon with a ranged row AND a melee row, so it is
# named twice - exactly like the laser lance it replaced.
check("...Exarch on Star Lance (2 profiles) + Shuriken Cannon",
      *has_line(spears, "Shining Spear Exarch", 1, "Star Lance", "Star Lance",
                "Shuriken Cannon"))
check("...so his Laser Lance is gone",
      not any(w.name == "Laser Lance" for m in spears.models
              if m.profile.name == "Shining Spear Exarch" for w in m.weapons))
check("...and so is his Twin Shuriken Catapult",
      not any(w.name == "Twin Shuriken Catapult" for m in spears.models
              if m.profile.name == "Shining Spear Exarch" for w in m.weapons))
# The shimmershield is Gear, so it is checked on the MODEL, not in the weapons.
check("...and the shimmershield is on him (Gear, not a weapon swap)",
      sum(1 for m in spears.models if getattr(m, "shimmershield", False)) == 1)
check("...2 Spears on Laser Lance + Twin Shuriken Catapult",
      *has_line(spears, "Shining Spear", 2, "Laser Lance", "Laser Lance",
                "Twin Shuriken Catapult"))

runners = build(SHROUD_RUNNERS)
check("Shroud Runners: 3 models", len(runners.models) == 3)
check("...all 3 on Long Rifle + Scatter Laser + Pistol + CCW",
      *has_line(runners, "Shroud Runner", 3, "Close Combat Weapon", "Long Rifle",
                "Scatter Laser", "Shuriken Pistol"))
check("...and this datasheet has no options either",
      len(SHROUD_RUNNERS.wargear_options) == 0)

scorpions = build(STRIKING_SCORPIONS)
check("Striking Scorpions: 5 models", len(scorpions.models) == 5)
# The list's Exarch build IS the printed default - checked rather than assumed,
# because both of this datasheet's wargear options replace exactly these three
# weapons, so getting it wrong would have meant taking one of them.
check("...Exarch on Chainsword + Scorpion's Claw + Pistol, with no option taken",
      *has_line(scorpions, "Striking Scorpion Exarch", 1, "Scorpion Chainsword",
                "Scorpion's Claw", "Shuriken Pistol"))
check("...4 on Chainsword + Pistol",
      *has_line(scorpions, "Striking Scorpion", 4, "Scorpion Chainsword", "Shuriken Pistol"))

# Listed with its printed Witchblade, NOT the Singing Spear the two foot
# Conclaves take - the one swap this datasheet has, deliberately not taken.
skyrunner = build(WARLOCK_SKYRUNNERS)
check("Warlock Skyrunners: 1 model", len(skyrunner.models) == 1)
check("...on Destructor + Pistol + Twin Shuriken Catapult + Witchblade",
      *has_line(skyrunner, "Warlock Skyrunner", 1, "Destructor", "Shuriken Pistol",
                "Twin Shuriken Catapult", "Witchblade"))
check("...so no Singing Spear was taken",
      not any(w.name == "Singing Spear" for m in skyrunner.models for w in m.weapons))
# It stands ALONE in this list, and that is legal rather than an attachment that
# failed: its LEADER line is a JOIN naming Windriders, which this roster does not
# field. Checked at the pairing table so the reason is recorded, not assumed.
check("...and it stands alone: its JOIN names Windriders, which this list has none of",
      attached_units.can_attach(build(WARLOCK_SKYRUNNERS, name="Skyrunner R"),
                                build(GUARDIAN_DEFENDERS, name="Guardians S")) != [])

wraithguard = build(WRAITHGUARD, choices={"Wraithguard": {WRAITHGUARD_TO_D_SCYTHE: 5}})
check("Wraithguard: all 5 on D-scythes",
      *has_line(wraithguard, "Wraithguard", 5, "Close Combat Weapon", "D-scythe"))
check("...so no Wraithcannon is left",
      not any(w.name == "Wraithcannon" for m in wraithguard.models for w in m.weapons))


print("\n2. Guardian Defenders + Farseer + Warlock Conclave 1")

guardians = build(GUARDIAN_DEFENDERS)
check("11 models: 10 Guardians + 1 Heavy Weapon Platform", len(guardians.models) == 11)
check("...10 Guardians on Shuriken Catapults",
      *has_line(guardians, "Guardian Defender", 10, "Close Combat Weapon", "Shuriken Catapult"))
check("...the platform on a Bright Lance",
      *has_line(guardians, "Heavy Weapon Platform", 1, "Close Combat Weapon", "Bright Lance"))

farseer = build(FARSEER, choices={"Farseer": {FARSEER_WITCHBLADE_TO_SPEAR: 1}})
# The list gives him a Singing Spear, which is the datasheet's one swap. The
# spear is one printed weapon with a thrown row and a melee row, so it shows
# up twice by name.
check("Farseer: Eldritch Storm + Shuriken Pistol + Singing Spear (2 profiles)",
      *has_line(farseer, "Farseer", 1, "Eldritch Storm", "Shuriken Pistol",
                "Singing Spear", "Singing Spear"))
check("...so his Witchblade is gone",
      not any(w.name == "Witchblade" for m in farseer.models for w in m.weapons))

conclave1 = build(WARLOCK_CONCLAVE, name="Warlock Conclave 1",
                  choices={"Warlock": {WARLOCK_WITCHBLADE_TO_SPEAR: 2}})
check("Warlock Conclave: 2 models", len(conclave1.models) == 2)
check("...both on Destructor + Pistol + Singing Spear",
      *has_line(conclave1, "Warlock", 2, "Destructor", "Shuriken Pistol",
                "Singing Spear", "Singing Spear"))
check("Warlock Conclave costs 55", conclave1.points == 55, str(conclave1.points))

# THE ORDER IS THE RULE, not a preference. A plain Farseer's LEADER line
# carries no permission to join a unit something is already attached to (only
# Eldrad's does), while the Conclave's ability is worded as a JOIN whose own
# limit is one Conclave per unit. So this order is legal and the reverse is
# not - both directions are checked here, because a test that only built the
# working order could not tell the difference.
check("a Farseer CAN be attached to plain Guardian Defenders",
      attached_units.can_attach(farseer, guardians) == [])
merged_guardians = attached_units.attach(farseer, guardians)
check("...and then the Conclave may still join (its own limit is one Conclave)",
      attached_units.can_attach(conclave1, merged_guardians) == [])
merged_guardians = attached_units.attach(conclave1, merged_guardians)
check("the merged unit has 14 models", len(merged_guardians.models) == 14)
check("...and three components", len(attached_units.components(merged_guardians)) == 3)
check("...and Protect is live on it (a FARSEER leading Warlocks)",
      any(m.profile.farseer for m in merged_guardians.models)
      and attached_units.unit_has_datasheet_keyword(merged_guardians, "WARLOCKS"))

# The reverse order, on a fresh pair.
rev_guardians = attached_units.attach(
    build(WARLOCK_CONCLAVE, name="Warlock Conclave R",
          choices={"Warlock": {WARLOCK_WITCHBLADE_TO_SPEAR: 2}}),
    build(GUARDIAN_DEFENDERS, name="Guardian Defenders R"))
check("REVERSE order is refused: a plain Farseer cannot join a Conclave-led unit",
      attached_units.can_attach(
          build(FARSEER, name="Farseer R",
                choices={"Farseer": {FARSEER_WITCHBLADE_TO_SPEAR: 1}}), rev_guardians) != [])
check("...and a SECOND Conclave is refused too (its own printed limit)",
      attached_units.can_attach(
          build(WARLOCK_CONCLAVE, name="Warlock Conclave R2"), rev_guardians) != [])


print("\n3. Storm Guardians + Eldrad Ulthran + Warlock Conclave 2")

storm = build(STORM_GUARDIANS, choices={"Storm Guardian": {
    STORM_GUARDIAN_PISTOL_TO_FLAMER: 2,
    STORM_GUARDIAN_PISTOL_TO_FUSION: 2,
    STORM_GUARDIAN_CCW_TO_POWER_SWORD: [4, 5],
}})
check("11 models: 10 Storm Guardians + Serpent's Scale Platform", len(storm.models) == 11)
# Every special weapon is on its own model. The two pistol swaps share a cursor
# and separate by themselves; the sword swap gives up a different weapon and
# would restart at model 0, putting swords on the flamer models - so its models
# are named by index in main.py. This is the check that the naming survives:
# remove it and the flamer/sword/plain lines fail together.
check("...2 with Flamer, keeping their close combat weapon",
      *has_line(storm, "Storm Guardian", 2, "Close Combat Weapon", "Flamer"))
check("...2 with Fusion Gun, keeping their close combat weapon",
      *has_line(storm, "Storm Guardian", 2, "Close Combat Weapon", "Fusion Gun"))
check("...2 OTHER models with Power Sword, keeping their pistol",
      *has_line(storm, "Storm Guardian", 2, "Power Sword", "Shuriken Pistol"))
check("...no model carries two special weapons",
      not any(len({"Flamer", "Fusion Gun", "Power Sword"} & {w.name for w in m.weapons}) > 1
              for m in storm.models))
check("...4 on the printed Shuriken Pistol",
      *has_line(storm, "Storm Guardian", 4, "Close Combat Weapon", "Shuriken Pistol"))
check("...the platform with just a close combat weapon",
      *has_line(storm, "Serpent's Scale Platform", 1, "Close Combat Weapon"))
check("Storm Guardians cost 110", storm.points == 110, str(storm.points))

eldrad = build(ELDRAD_ULTHRAN)
check("Eldrad: Mind War + Shuriken Pistol + Staff of Ulthamar and Witchblade",
      *has_line(eldrad, "Eldrad Ulthran", 1, "Mind War", "Shuriken Pistol",
                "Staff of Ulthamar and Witchblade"))

conclave2 = build(WARLOCK_CONCLAVE, name="Warlock Conclave 2",
                  choices={"Warlock": {WARLOCK_WITCHBLADE_TO_SPEAR: 2}})
merged_storm = attached_units.attach(eldrad, storm)
check("Eldrad attaches to Storm Guardians",
      any(m.profile.name == "Eldrad Ulthran" for m in merged_storm.models))
check("...and the Conclave joins after him", attached_units.can_attach(conclave2, merged_storm) == [])
merged_storm = attached_units.attach(conclave2, merged_storm)
check("the merged unit has 14 models", len(merged_storm.models) == 14)
# Eldrad is the one datasheet that works in EITHER order, which is what his
# own LEADER line says and the reason the asymmetry above is motivated at all.
check("Eldrad also works the OTHER way round (his own LEADER line)",
      attached_units.can_attach(
          build(ELDRAD_ULTHRAN, name="Eldrad R"),
          attached_units.attach(
              build(WARLOCK_CONCLAVE, name="Warlock Conclave S"),
              build(STORM_GUARDIANS, name="Storm Guardians S"))) == [])


print("\n4. The three Phoenix Lords, each with the unit its LEADER line names")

avengers = build(DIRE_AVENGERS,
                 choices={"Dire Avenger Exarch": {DIRE_AVENGER_SECOND_CATAPULT: 1}})
check("Dire Avengers: 5 models", len(avengers.models) == 5)
check("...Exarch with TWO Avenger Shuriken Catapults (a pure addition)",
      *has_line(avengers, "Dire Avenger Exarch", 1, "Avenger Shuriken Catapult",
                "Avenger Shuriken Catapult", "Close Combat Weapon"))
check("...4 with one each",
      *has_line(avengers, "Dire Avenger", 4, "Avenger Shuriken Catapult", "Close Combat Weapon"))
asurmen = build(ASURMEN)
check("Asurmen: The Bloody Twins + The Sword of Asur",
      *has_line(asurmen, "Asurmen", 1, "Bloody Twins", "Sword of Asur"))
check("Asurmen may lead Dire Avengers", attached_units.can_attach(asurmen, avengers) == [])
merged_avengers = attached_units.attach(asurmen, avengers)
check("...merged to 6 models", len(merged_avengers.models) == 6)
check("Asurmen may NOT lead anything else in this army (his LEADER line)",
      attached_units.can_attach(build(ASURMEN, name="Asurmen X"),
                                build(HOWLING_BANSHEES, name="Banshees X")) != [])

banshees = build(HOWLING_BANSHEES,
                 choices={"Howling Banshee Exarch": {BANSHEE_BLADE_TO_EXECUTIONER: 1}})
check("Howling Banshees: Exarch on an Executioner, keeping her pistol",
      *has_line(banshees, "Howling Banshee Exarch", 1, "Executioner", "Shuriken Pistol"))
check("...4 on Banshee Blades",
      *has_line(banshees, "Howling Banshee", 4, "Banshee Blade", "Shuriken Pistol"))
jain_zar = build(JAIN_ZAR)
check("Jain Zar: Silent Death + The Blade of Destruction",
      *has_line(jain_zar, "Jain Zar", 1, "Silent Death", "Blade of Destruction"))
check("Jain Zar may lead Howling Banshees", attached_units.can_attach(jain_zar, banshees) == [])
merged_banshees = attached_units.attach(jain_zar, banshees)
check("...merged to 6 models", len(merged_banshees.models) == 6)

spiders = build(WARP_SPIDERS,
                choices={"Warp Spider Exarch": {WARP_SPIDER_TO_POWERBLADE_ARRAY: 1}})
check("Warp Spiders: Exarch on a Powerblade Array",
      *has_line(spiders, "Warp Spider Exarch", 1, "Close Combat Weapon", "Powerblade Array"))
check("...so his Exarch's Death Spinner is gone",
      not any(w.name == "Exarch's Death Spinner" for m in spiders.models for w in m.weapons))
check("...4 on Death Spinners",
      *has_line(spiders, "Warp Spider", 4, "Close Combat Weapon", "Death Spinner"))
lhykhis = build(LHYKHIS)
check("Lhykhis: Brood Twain + Spider's Fangs + Weaverender",
      *has_line(lhykhis, "Lhykhis", 1, "Brood Twain", "Spider's Fangs", "Weaverender"))
check("Lhykhis may lead Warp Spiders", attached_units.can_attach(lhykhis, spiders) == [])
merged_spiders = attached_units.attach(lhykhis, spiders)
check("...merged to 6 models", len(merged_spiders.models) == 6)


print("\n5. Army rule and totals")

units = [reapers, falcon, rangers, spears, runners, scorpions, skyrunner,
         wraithguard, merged_guardians, merged_storm, merged_avengers,
         merged_banshees, merged_spiders]
check("13 units: 8 plain + 5 attached", len(units) == 13)
check("every unit is priced (no None)", all(u.points is not None for u in units))
total = sum(u.points for u in units)
# Counted from the list rather than copied from a run, which is the whole
# point of writing it out:
#   plain    5 Reapers + 1 Falcon + 5 Rangers + 3 Spears + 3 Runners
#            + 5 Scorpions + 1 Skyrunner + 5 Wraithguard          = 28
#   attached (11 + 1 + 2) + (11 + 1 + 2) + (5 + 1) * 3            = 46
models = sum(len(u.models) for u in units)
check("74 models on the table", models == 28 + 46, str(models))

# This is what makes the whole Aeldari army rule live: it is DERIVED from the
# units rather than configured, so an army built from these datasheets turns
# it on by itself.
from game import battle_focus  # noqa: E402
check("Battle Focus derives Player 1 as an ASURYANI army",
      "Player 1" in battle_focus.qualifying_players(units))
check("...and every one of the 13 units carries the flag",
      all(any(m.profile.battle_focus for m in u.models) for u in units))

# The supplied list totals 1930 pts. 12 of its 19 distinct entries disagree with
# the transcribed official points list (see main.py's roster comment), so the
# engine total is deliberately different and the check is a sanity bound, not an
# equality - overwriting the transcribed data to force a match is exactly what
# both other armies' notes say not to do. The revision's mismatches run BOTH
# ways, so this is no longer a one-sided bound.
print(f"       engine total: {total} pts   |   the supplied list totals 1930 pts")
check("the total is within 100 pts of the list's own", abs(total - 1930) <= 100,
      f"{total} vs 1930")

# The loadout display has to survive every unit here - it is what the panels
# and the reserves cards show, and an attached unit is where it has broken
# before (two datasheets under one squad name).
for unit in units:
    groups = loadout.line_groups(unit)
    ok = bool(groups) and all(
        isinstance(g, tuple) and len(g) == 3 and isinstance(g[0], int) and g[1] and g[2]
        for g in groups)
    if not ok:
        check(f"loadout display works for {unit.name}", False, str(groups)[:80])
        break
else:
    check("the loadout display renders every unit", True)

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
