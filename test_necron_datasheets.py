"""The thirteen Necron datasheets: statlines, weapons, wargear and points.

ONE SUITE FOR THIRTEEN SHEETS rather than thirteen suites, deliberately. The
repo's usual shape is one file per datasheet, and that earns its keep when a
sheet arrives alone with an ability to drive end to end. These thirteen arrived
as one transcription batch, and what needs guarding about them is uniform:
did the numbers come across, do the wargear options build the loadout the
user's army list actually names, and do the points match what was transcribed.
The ABILITIES are not here - they get their own suite, where they can be driven
through real controllers instead of asserted as flags.

WHAT THIS IS REALLY PROTECTING: a transcription. Every number below was read
off Wahapedia once, and the failure mode is a digit, not a design. So the
checks are dense and literal, with two exceptions that are pinned RELATIVELY
because a literal would not survive a future edit meaningfully:

  * base sizes are checked as the mm -> inch arithmetic, not as a rounded
    literal, so a changed convention shows up as arithmetic rather than noise;
  * the two Staff of Light pairs and the three Close Combat Weapon rows are
    checked AGAINST EACH OTHER, because the thing worth guarding is that they
    are DIFFERENT - that is the "same name, different numbers" trap the recipe
    warns about, and a literal check on each would pass even if someone later
    merged them.
"""

from testkit import Checks, build_squad
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game import attached_units, sprites
from game import weapons as w

c = Checks("Necron datasheets")


def build(sheet, name=None, **kw):
    kw.setdefault("name", name or f"2 {sheet.name} 1")
    return build_squad(sheet, "Player 2", **kw)


def loadout(squad):
    out = {}
    for m in squad.models:
        for weapon in m.weapons:
            out[weapon.name] = out.get(weapon.name, 0) + 1
    return out


def mm(size):
    return round(size / 2 / 25.4, 3)


# --- 1. statlines -----------------------------------------------------------
print("--- 1. statlines ---")

STATS = [
    # sheet, M, T, Sv, W, Ld, OC, Inv, base mm
    (nec.NECRON_WARRIORS, 5, 4, "4+", 1, "7+", 2, "-", 32),
    (nec.IMMORTALS, 5, 5, "3+", 1, "7+", 2, "-", 32),
    (nec.LYCHGUARD, 5, 5, "3+", 2, "7+", 1, "-", 32),
    (nec.OVERLORD, 5, 5, "2+", 6, "6+", 1, "4+", 40),
    (nec.PLASMANCER, 5, 4, "4+", 4, "6+", 1, "-", 32),
    (nec.TECHNOMANCER, 10, 4, "4+", 4, "6+", 1, "-", 50),
    (nec.ILLUMINOR_SZERAS, 8, 8, "2+", 9, "6+", 3, "4+", 80),
    (nec.CANOPTEK_WRAITHS, 10, 6, "3+", 4, "8+", 2, "4+", 50),
    (nec.SKORPEKH_DESTROYERS, 8, 6, "3+", 3, "7+", 2, "-", 50),
    # base=None: these three do NOT use their printed size on the table, so
    # they are checked below against the thing they were matched TO instead.
    (nec.LOKHUST_DESTROYERS, 8, 6, "3+", 3, "7+", 2, "-", None),
    (nec.LOKHUST_HEAVY_DESTROYERS, 8, 6, "3+", 4, "7+", 2, "-", None),
    (nec.DOOMSDAY_ARK, 10, 9, "3+", 14, "7+", 5, "4+", None),
    (nec.CTAN_SHARD_OF_THE_VOID_DRAGON, 10, 11, "3+", 16, "6+", 4, "4+", 80),
]
for sheet, move, tough, sv, wounds, ld, oc, inv, base in STATS:
    p = build(sheet).models[0].profile
    c.eq(f"{sheet.name}: M/T/Sv/W/Ld/OC",
         (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc),
         (move, tough, sv, wounds, ld, oc))
    c.eq(f"{sheet.name}: invulnerable save", p.invulnerable_save, inv)
    if base is not None:
        c.eq(f"{sheet.name}: base is {base}mm", round(p.base_radius_in, 3), mm(base))

# --- the three bases that deviate from their printed size, on purpose -------
# All three are user table-size decisions, so each is pinned to WHAT IT WAS
# MATCHED TO rather than to a literal - a literal here says nothing about
# whether the intent still holds.
from game.units import DevilfishProfile, FalconProfile, WaveSerpentProfile

destroyer = build(nec.LOKHUST_DESTROYERS, composition_index=0).models[0].profile
heavy = build(nec.LOKHUST_HEAVY_DESTROYERS, composition_index=0).models[0].profile
skorpekh = build(nec.SKORPEKH_DESTROYERS).models[0].profile
# ALL THREE Destroyer datasheets share one table size, so all three are pinned
# against the one they were matched TO rather than against three literals -
# three copies of a shared number drift apart the next time one is touched.
c.eq("all three Destroyer datasheets are the same size on the table",
     [destroyer.base_radius_in, heavy.base_radius_in],
     [skorpekh.base_radius_in, skorpekh.base_radius_in])
c.eq("...and that size is the Skorpekh Destroyers' printed 50mm",
     round(skorpekh.base_radius_in, 3), mm(50))
c.true("...so the two Lokhust sheets really are smaller than their own "
       "printed 60mm, not larger",
       destroyer.base_radius_in < mm(60) and heavy.base_radius_in < mm(60))

ark_profile = build(nec.DOOMSDAY_ARK).models[0].profile
c.eq("the Doomsday Ark matches the other grav tanks, not its printed 60mm",
     [ark_profile.base_radius_in == FalconProfile.base_radius_in,
      ark_profile.base_radius_in == DevilfishProfile.base_radius_in,
      ark_profile.base_radius_in == WaveSerpentProfile.base_radius_in],
     [True, True, True])
c.true("...and it is the one unit here that GREW - every other size request "
       "so far made something smaller",
       ark_profile.base_radius_in > mm(60))

# the two statlines with something extra printed on them
ark = build(nec.DOOMSDAY_ARK).models[0].profile
c.eq("Doomsday Ark: Damaged 1-5 wounds remaining", ark.damaged_threshold, 5)
c.eq("Doomsday Ark: Deadly Demise D3", ark.deadly_demise_notation.sides, 3)
c.true("Doomsday Ark is a VEHICLE that FLYs", ark.vehicle and ark.fly)

vd = build(nec.CTAN_SHARD_OF_THE_VOID_DRAGON).models[0].profile
c.eq("Void Dragon: Deadly Demise D6", vd.deadly_demise_notation.sides, 6)
c.eq("Void Dragon: Feel No Pain 5+", vd.feel_no_pain, "5+")
c.true("Void Dragon has Deep Strike", vd.deep_strike)
c.true("Void Dragon is a MONSTER CHARACTER EPIC HERO", vd.monster and vd.character and vd.epic_hero)
c.eq("Illuminor Szeras: Feel No Pain 4+",
     build(nec.ILLUMINOR_SZERAS).models[0].profile.feel_no_pain, "4+")
c.true("Technomancer has FLY", build(nec.TECHNOMANCER).models[0].profile.fly)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")


def profile_tuple(weapon):
    return (weapon.range_in, weapon.attacks, weapon.strength, weapon.ap, weapon.damage)


c.eq("Gauss Flayer 24in A1 S4 AP0 D1", profile_tuple(w.GaussFlayerProfile()), (24, 1, 4, 0, 1))
c.true("Gauss Flayer is [LETHAL HITS] [RAPID FIRE 1]",
       w.GaussFlayerProfile().lethal_hits and w.GaussFlayerProfile().rapid_fire == 1)
c.eq("Gauss Reaper 12in A2 S4 AP-1 D1", profile_tuple(w.GaussReaperProfile()), (12, 2, 4, -1, 1))
c.eq("Gauss Blaster 24in A2 S5 AP-1 D1", profile_tuple(w.GaussBlasterProfile()), (24, 2, 5, -1, 1))
c.true("Tesla Carbine is [ASSAULT] [SUSTAINED HITS 2]",
       w.TeslaCarbineProfile().assault and w.TeslaCarbineProfile().sustained_hits == 2)
c.eq("Warscythe A2 S8 AP-3 D2", profile_tuple(w.WarscytheProfile()), (2, 2, 8, -3, 2))
c.true("Warscythe is [DEVASTATING WOUNDS]", w.WarscytheProfile().devastating_wounds)
c.eq("Hyperphase Sword A3 S6 AP-2 D1", profile_tuple(w.HyperphaseSwordProfile()), (2, 3, 6, -2, 1))
c.eq("Hyperphase Sword prints NO keywords",
     (w.HyperphaseSwordProfile().devastating_wounds, w.HyperphaseSwordProfile().lethal_hits), (False, False))
c.eq("Skorpekh Hyperphase Weapons A4 S7 AP-2 D2",
     profile_tuple(w.SkorpekhHyperphaseWeaponsProfile()), (2, 4, 7, -2, 2))
c.eq("Gauss Cannon 24in A3 S5 AP-2 D2", profile_tuple(w.GaussCannonProfile()), (24, 3, 5, -2, 2))
c.eq("Gauss Destructor 48in A1 S14 AP-4 D6", profile_tuple(w.GaussDestructorProfile()), (48, 1, 14, -4, 6))
c.true("Gauss Destructor is [HEAVY] [LETHAL HITS]",
       w.GaussDestructorProfile().heavy and w.GaussDestructorProfile().lethal_hits)
c.eq("Enmitic Exterminator 36in A6 S6 AP-1 D1",
     profile_tuple(w.EnmiticExterminatorProfile()), (36, 6, 6, -1, 1))
c.true("Enmitic Exterminator is [HEAVY] [RAPID FIRE 6] [SUSTAINED HITS 1]",
       w.EnmiticExterminatorProfile().heavy and w.EnmiticExterminatorProfile().rapid_fire == 6
       and w.EnmiticExterminatorProfile().sustained_hits == 1)
c.eq("Doomsday Cannon 72in S18 AP-4 D4", (w.DoomsdayCannonProfile().range_in,
     w.DoomsdayCannonProfile().strength, w.DoomsdayCannonProfile().ap,
     w.DoomsdayCannonProfile().damage), (72, 18, -4, 4))
c.eq("Doomsday Cannon Attacks are D6+1",
     (w.DoomsdayCannonProfile().attacks_notation.sides, w.DoomsdayCannonProfile().attacks_notation.bonus), (6, 1))
c.eq("Gauss Flayer Array is [RAPID FIRE 5]", w.GaussFlayerArrayProfile().rapid_fire, 5)
c.eq("Voidscythe A3 S12 AP-3 D3", profile_tuple(w.VoidscytheProfile()), (2, 3, 12, -3, 3))
c.eq("Voidscythe prints its OWN worse WS", w.VoidscytheProfile().weapon_skill, "3+")
c.eq("Tachyon Arrow 72in S16 AP-5, damage D6+2",
     (w.TachyonArrowProfile().range_in, w.TachyonArrowProfile().strength,
      w.TachyonArrowProfile().ap, w.TachyonArrowProfile().damage_notation.bonus), (72, 16, -5, 2))
c.true("Tachyon Arrow is [ONE SHOT]", w.TachyonArrowProfile().one_shot)
c.true("Particle Caster is [DEVASTATING WOUNDS] and a [PISTOL]",
       w.ParticleCasterProfile().devastating_wounds and w.ParticleCasterProfile().pistol)
c.eq("Vicious Claws A4 S6 AP-1 D2", profile_tuple(w.ViciousClawsProfile()), (2, 4, 6, -1, 2))
c.eq("Whip Coils A8 S5 AP0 D1", profile_tuple(w.WhipCoilsProfile()), (2, 8, 5, 0, 1))
c.true("Impaling Legs is [EXTRA ATTACKS]", w.ImpalingLegsProfile().extra_attacks)
c.true("Canoptek Tail Blades is [EXTRA ATTACKS]", w.CanoptekTailBladesProfile().extra_attacks)
c.eq("Eldritch Lance ranged 36in A3 S9 AP-3 D3",
     profile_tuple(w.EldritchLanceRangedProfile()), (36, 3, 9, -3, 3))

# the Spear's three profiles, and the strike/sweep MODE pair
strike, sweep = w.SpearOfTheVoidDragonStrikeProfile(), w.SpearOfTheVoidDragonSweepProfile()
c.eq("Spear - strike A5 S12 AP-4", (strike.attacks, strike.strength, strike.ap), (5, 12, -4))
c.eq("Spear - sweep A10 S8 AP-1 D2", profile_tuple(sweep), (2, 10, 8, -1, 2))
c.eq("strike and sweep are ONE datasheet entry, so a firing-mode pair",
     w.SpearOfTheVoidDragonStrikeProfile.overcharge_profile, w.SpearOfTheVoidDragonSweepProfile)
c.eq("Spear (both melee and ranged) is [ANTI-VEHICLE 2+]",
     (strike.anti, w.SpearOfTheVoidDragonAntiVehicleProfile().anti),
     (("VEHICLE", 2), ("VEHICLE", 2)))
c.true("Voltaic Storm is [BLAST] with [SUSTAINED HITS 2]",
       w.VoltaicStormProfile().blast and w.VoltaicStormProfile().sustained_hits == 2)

# the "same name, different numbers" pairs - pinned against EACH OTHER
ov_r, tm_r = w.LordStaffOfLightRangedProfile(), w.TechnomancerStaffOfLightRangedProfile()
ov_m, tm_m = w.LordStaffOfLightMeleeProfile(), w.TechnomancerStaffOfLightMeleeProfile()
c.eq("both Staffs of Light print the same NAME", (ov_r.name, tm_r.name),
     ("Staff of Light", "Staff of Light"))
c.true("...but the melee halves differ in Attacks (4 vs 2)", ov_m.attacks != tm_m.attacks)
c.eq("the Overlord swings his 4 times", ov_m.attacks, 4)
c.eq("the Technomancer swings his twice", tm_m.attacks, 2)
a1, a2 = w.NecronCloseCombatWeaponA1Profile(), w.NecronCloseCombatWeaponA2Profile()
c.eq("both Close Combat Weapons print the same NAME", (a1.name, a2.name),
     ("Close Combat Weapon", "Close Combat Weapon"))
c.true("...but differ in Attacks", a1.attacks != a2.attacks)


# --- 3. wargear and the user's loadouts -------------------------------------
print("--- 3. wargear ---")

warriors = build(nec.NECRON_WARRIORS, composition_index=1)
c.eq("20 Necron Warriors, gauss flayers by default", len(warriors.models), 20)
c.eq("...and the default really is the flayer", loadout(warriors).get("Gauss Flayer"), 20)
swapped = build(nec.NECRON_WARRIORS, composition_index=1,
                choices={"Necron Warrior": {nec.NECRON_WARRIORS_TO_GAUSS_REAPER: 5}})
c.eq("five can trade for gauss reapers", loadout(swapped).get("Gauss Reaper"), 5)
c.eq("...leaving fifteen flayers", loadout(swapped).get("Gauss Flayer"), 15)

immortals = build(nec.IMMORTALS, composition_index=1)
c.eq("10 Immortals with gauss blasters", loadout(immortals).get("Gauss Blaster"), 10)
tesla = build(nec.IMMORTALS, composition_index=1,
              choices={"Immortal": {nec.IMMORTALS_TO_TESLA_CARBINE: 10}})
c.eq("all ten can take tesla carbines instead", loadout(tesla).get("Tesla Carbine"), 10)
c.eq("...and then carry no blasters", loadout(tesla).get("Gauss Blaster"), None)

lych = build(nec.LYCHGUARD, choices={"Lychguard": {nec.LYCHGUARD_TO_HYPERPHASE_SWORD: 5}},
             gear={"Lychguard": [nec.LYCHGUARD_DISPERSION_SHIELD]})
c.eq("5 Lychguard take hyperphase swords", loadout(lych).get("Hyperphase Sword"), 5)
c.eq("...and the shield reaches ALL FIVE, not just the first",
     sum(1 for m in lych.models if getattr(m, "dispersion_shield", False)), 5)
bare = build(nec.LYCHGUARD, name="2 Lychguard 2",
             gear={"Lychguard": [nec.LYCHGUARD_DISPERSION_SHIELD]})
c.eq("the shield REFUSES a model that kept its warscythe - the printed pairing "
     "enforces itself", sum(1 for m in bare.models if getattr(m, "dispersion_shield", False)), 0)
c.eq("...which leaves them with warscythes", loadout(bare).get("Warscythe"), 5)

lord = build(nec.OVERLORD, choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}},
             gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]})
c.eq("the Overlord's list build is Voidscythe only", sorted(loadout(lord)), ["Voidscythe"])
c.eq("...and he carries the resurrection orb",
     getattr(lord.models[0], "resurrection_orb", False), True)
kept_arrow = build(nec.OVERLORD, name="2 Overlord 2",
                   gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]})
c.eq("keeping the tachyon arrow REFUSES the orb - the printed precondition",
     getattr(kept_arrow.models[0], "resurrection_orb", False), False)
staff = build(nec.OVERLORD, name="2 Overlord 3",
              choices={"Overlord": {nec.OVERLORD_TO_STAFF_OF_LIGHT: 1}})
c.eq("the staff option gives BOTH its printed rows",
     sorted(staff.models[0].weapons, key=lambda x: x.weapon_type)[0].name, "Staff of Light")
c.eq("...and only the staff", sorted(loadout(staff)), ["Staff of Light"])

heavy = build(nec.LOKHUST_HEAVY_DESTROYERS, composition_index=2,
              choices={"Lokhust Heavy Destroyer": {nec.LOKHUST_HEAVY_TO_ENMITIC_EXTERMINATOR: 1}})
c.eq("the list's Lokhust Heavies: 1 exterminator, 2 destructors",
     (loadout(heavy).get("Enmitic Exterminator"), loadout(heavy).get("Gauss Destructor")), (1, 2))

wraiths = build(nec.CANOPTEK_WRAITHS, composition_index=1)
c.eq("6 Wraiths with vicious claws and nothing added",
     (loadout(wraiths).get("Vicious Claws"), loadout(wraiths).get("Particle Caster")), (6, None))
armed = build(nec.CANOPTEK_WRAITHS, composition_index=1, name="2 Canoptek Wraiths 2",
              choices={"Canoptek Wraith": {nec.WRAITHS_ADD_PARTICLE_CASTER: 2,
                                           nec.WRAITHS_TO_WHIP_COILS: 3}})
c.eq("particle casters are a pure ADDITION", loadout(armed).get("Particle Caster"), 2)
c.eq("whip coils REPLACE the claws",
     (loadout(armed).get("Whip Coils"), loadout(armed).get("Vicious Claws")), (3, 3))

ark_squad = build(nec.DOOMSDAY_ARK)
c.eq("the Doomsday Ark really does print TWO gauss flayer arrays",
     loadout(ark_squad).get("Gauss Flayer Array"), 2)
c.eq("...plus the cannon and the bulk",
     (loadout(ark_squad).get("Doomsday Cannon"), loadout(ark_squad).get("Armoured Bulk")), (1, 1))

skorpekh = build(nec.SKORPEKH_DESTROYERS, gear={"Skorpekh Destroyer": [nec.SKORPEKH_PLASMACYTE]})
c.eq("a Plasmacyte is counted, not flagged",
     getattr(skorpekh.models[0], "plasmacyte_count", 0), 1)
c.eq("datasheets with NO wargear options really have none",
     [len(nec.LOKHUST_DESTROYERS.wargear_options), len(nec.PLASMANCER.wargear_options),
      len(nec.TECHNOMANCER.wargear_options), len(nec.ILLUMINOR_SZERAS.wargear_options),
      len(nec.CTAN_SHARD_OF_THE_VOID_DRAGON.wargear_options)], [0, 0, 0, 0, 0])


# --- 4. points --------------------------------------------------------------
print("--- 4. points ---")

POINTS = [
    (nec.NECRON_WARRIORS, 1, 1, 190),          # 20 models
    (nec.IMMORTALS, 1, 1, 140),                # 10 models
    (nec.LYCHGUARD, 0, 1, 80),                 # 5 models
    (nec.OVERLORD, 0, 1, 90),
    (nec.PLASMANCER, 0, 1, 55),
    (nec.TECHNOMANCER, 0, 1, 80),
    (nec.ILLUMINOR_SZERAS, 0, 1, 175),
    (nec.CANOPTEK_WRAITHS, 1, 1, 220),         # 6 models, 1st unit
    (nec.SKORPEKH_DESTROYERS, 0, 1, 85),       # 3 models
    (nec.LOKHUST_DESTROYERS, 3, 1, 170),       # 6 models
    (nec.LOKHUST_HEAVY_DESTROYERS, 2, 1, 160),  # 3 models
    (nec.DOOMSDAY_ARK, 0, 1, 210),
    (nec.CTAN_SHARD_OF_THE_VOID_DRAGON, 0, 1, 345),
]
for sheet, ci, ui, cost in POINTS:
    c.eq(f"{sheet.name}: {cost} pts", build(sheet, composition_index=ci, unit_index=ui).points, cost)

# the copy-tiered entries, checked at the tier BOUNDARY rather than inside it -
# an off-by-one in from_unit/to_unit is the only realistic way to get these wrong
c.eq("Technomancer is dearer from the 2nd copy on",
     build(nec.TECHNOMANCER, name="2 Technomancer 2", unit_index=2).points, 90)
c.eq("Canoptek Wraiths are dearer from the 2nd unit on",
     build(nec.CANOPTEK_WRAITHS, composition_index=1, name="2 Canoptek Wraiths 2", unit_index=2).points, 240)
c.eq("Skorpekh Destroyers are dearer from the 3rd unit on",
     build(nec.SKORPEKH_DESTROYERS, name="2 Skorpekh Destroyers 3", unit_index=3).points, 95)
c.eq("...but not the 2nd",
     build(nec.SKORPEKH_DESTROYERS, name="2 Skorpekh Destroyers 2", unit_index=2).points, 85)
c.eq("Doomsday Ark is dearer from the 3rd",
     build(nec.DOOMSDAY_ARK, name="2 Doomsday Ark 3", unit_index=3).points, 230)
c.eq("the points table is transcription-only - an unbuilt unit is a KeyError, "
     "not a free unit", "Monolith" in NECRONS_POINTS, False)


# --- 5. keywords and the LEADER table (rule 19.01) --------------------------
print("--- 5. keywords and leaders ---")

c.true("Warriors and Immortals are BATTLELINE",
       "BATTLELINE" in nec.NECRON_WARRIORS.keywords and "BATTLELINE" in nec.IMMORTALS.keywords)
c.true("the Overlord is a NOBLE", "NOBLE" in nec.OVERLORD.keywords)
c.true("the Destroyer Cult is five datasheets - both Lords joined it",
       all("DESTROYER CULT" in s.keywords for s in
           (nec.SKORPEKH_DESTROYERS, nec.LOKHUST_DESTROYERS,
            nec.LOKHUST_HEAVY_DESTROYERS, nec.SKORPEKH_LORD, nec.LOKHUST_LORD)))
c.true("every datasheet carries the NECRONS faction keyword",
       all("NECRONS" in s.keywords for s in nec.NECRONS.datasheets.values()))
c.eq("twenty-two datasheets are registered", len(nec.NECRONS.datasheets), 22)
c.eq("the faction keyword is NECRONS", nec.NECRONS.keyword, "NECRONS")

# can_attach() returns a list of REASONS - empty means legal
c.eq("the Overlord may lead Immortals",
     attached_units.can_attach(build(nec.OVERLORD), build(nec.IMMORTALS, composition_index=1)), [])
c.eq("...and Lychguard", attached_units.can_attach(build(nec.OVERLORD), build(nec.LYCHGUARD)), [])
c.true("but NOT Canoptek Wraiths - they are not on his printed LEADER line",
       attached_units.can_attach(build(nec.OVERLORD), build(nec.CANOPTEK_WRAITHS, composition_index=1)) != [])
c.eq("the Technomancer may lead Canoptek Wraiths",
     attached_units.can_attach(build(nec.TECHNOMANCER), build(nec.CANOPTEK_WRAITHS, composition_index=1)), [])
c.true("Illuminor Szeras leads NOTHING - he has no printed LEADER line",
       attached_units.can_attach(build(nec.ILLUMINOR_SZERAS), build(nec.IMMORTALS, composition_index=1)) != [])
c.true("...and neither does the Void Dragon",
       attached_units.can_attach(build(nec.CTAN_SHARD_OF_THE_VOID_DRAGON),
                                 build(nec.NECRON_WARRIORS, composition_index=1)) != [])


# --- 6. sprites -------------------------------------------------------------
print("--- 6. sprites ---")

# These pins used to assert the OPPOSITE - "no Necron art is mapped" - which is
# exactly what they were for: the day the files arrived, adding them had to be
# a visible change rather than a silent one. Turned around now, the same way
# the eight Aeldari pins were.
#
# Checked at the MODEL, not in the table: a key that maps to no file on disk is
# precisely the failure a glance at the dict cannot see, and sprite_for() is
# what the renderer actually calls.
# The batch brought datasheets whose art the user has NOT supplied, so this
# stops being "every one" and becomes a NAMED list - the Aeldari precedent.
# Both directions matter: a sheet that quietly loses its art fails the first
# line, and a name that stays on the list after art arrives fails the second,
# so the exception cannot outlive its reason.
WITHOUT_ART = ["Flayed Ones"]
missing = sorted(s.name for s in nec.NECRONS.datasheets.values()
                 if not sprites.sprite_for(build(s).models[0]))
c.eq("every Necron datasheet resolves to a real file, bar the named ones",
     missing, sorted(WITHOUT_ART))
c.eq("...which is twenty-one of the twenty-two",
     len(nec.NECRONS.datasheets) - len(missing), 22 - len(WITHOUT_ART))
c.eq("the faction badge is mapped too",
     sprites.FACTION_LOGO_KEYS.get("NECRONS"), "Necron Logo")

# The folder disagrees with the datasheet in eight places, and the FOLDER wins -
# the same decision "Warpspider" and "Warlock Sky Runner" already record.
# Spelled out so a later "tidy-up" that renames them knows it is a change.
for sheet_name, expected_file in [
    ("Necron Warriors", "Necron Warrior"),          # singular file, plural datasheet
    ("Immortals", "Necron Immortal"),
    ("Canoptek Wraiths", "Necron Wraith"),
    ("Lokhust Destroyers", "Necron Destroyer"),     # names the MODEL, not the unit
    ("Lokhust Heavy Destroyers", "Necron Heavy Destroyer"),
    ("Illuminor Szeras", "Necron IlluminorSzeras"),  # no space in the filename
    ("C'tan Shard of the Void Dragon", "Necron Shard of the Void Dragon"),
]:
    c.eq(f"{sheet_name} borrows the file named {expected_file!r}",
         sprites.SQUAD_SPRITE_KEYS.get(sheet_name), expected_file)

# The two Destroyer datasheets are the only pair that could shadow each other,
# since _key_for_name() returns on the FIRST substring match. They cannot:
# "Lokhust Heavy Destroyers" does not contain "Lokhust Destroyers".
c.eq("the two Destroyer datasheets keep their own art",
     (sprites.sprite_for(build(nec.LOKHUST_DESTROYERS, composition_index=0).models[0])
      != sprites.sprite_for(build(nec.LOKHUST_HEAVY_DESTROYERS, composition_index=0).models[0])),
     True)

# --------------------------------------------------------------------------
# the four Enhancements are DATA, and that is a roster fact - pinned both ways
# --------------------------------------------------------------------------
print("--- the Enhancement gap ---")

# Awakened Dynasty prints four Enhancements. NONE of them is engine-wired:
# game/enhancements.py's registry holds forty-seven specs across fourteen T'au
# and Aeldari detachments and not one Necron entry.
#
# THAT IS A DECISION, NOT AN OVERSIGHT, and the reason is a ROSTER fact rather
# than a mechanism one: armies/necrons.json buys none of the four, so wiring
# them would produce four rules dormant by construction - exactly where the
# twenty-eight Aeldari and seven T'au Enhancements sit. Inventing roster
# content to reach them is the move this repo does not make.
#
# PINNED FROM BOTH SIDES so it can neither close nor widen quietly: if a later
# session wires one, the count moves; if a fifth is printed, the corpus count
# moves; and if a list ever buys one, the roster check moves.

import json as _enh_json                                             # noqa: E402
import pathlib as _enh_path                                          # noqa: E402

from game import enhancements as _enh                                # noqa: E402

_PRINTED = ["Veil of Darkness", "Nether-realm Casket",
            "Phasal Subjugator", "Enaegic Dermal Bond"]

c.eq("Awakened Dynasty prints four Enhancements",
     [e.name for e in nec.AWAKENED_DYNASTY.enhancements], _PRINTED)

# The registry is LIVE - without this the difference below would pass by
# measuring an empty registry.
c.true("the Enhancement registry is live (%d wired)" % len(_enh.ENHANCEMENTS),
       len(_enh.ENHANCEMENTS) >= 40)
c.eq("...and none of the four is among them",
     [n for n in _PRINTED if n in _enh.ENHANCEMENTS], [])
c.eq("...nor is any other Necron detachment Enhancement",
     sorted({s.detachment for s in _enh.ENHANCEMENTS.values()}
            & set(nec.NECRONS.detachments)), [])

# The ROSTER half, which is the actual reason.
_roster = _enh_json.loads(
    _enh_path.Path("armies/necrons.json").read_text(encoding="utf-8"))
_bought = sorted({e["enhancement"] for e in _roster["roster"]
                  if isinstance(e, dict) and e.get("enhancement")})
c.eq("the shipped Necron list buys no Enhancement", _bought, [])
c.eq("...while it DOES field the detachment, so the six Stratagems are live",
     _roster["detachments"], ["Awakened Dynasty"])

# ...and the PRINTED corpus still names exactly these four, so a fifth
# appearing on Wahapedia turns this red rather than being silently absent.
_md = _enh_path.Path("rules/necrons/detachments/Awakened Dynasty.md").read_text(
    encoding="utf-8")
# The trailing parenthetical is stripped: the corpus prints "Phasal
# Subjugator (Aura)" where the datasheet records the bare name - the same
# "(Aura)"/"(Psychic)" suffix game/rules_text.py already carries an alias for,
# and 29 of 264 printed ability titles have it.
_headings = [line[4:].split(" - ")[0].strip().split(" (")[0].strip()
             for line in _md.splitlines() if line.startswith("### ")]
c.true("the corpus was read", len(_headings) >= 10)
c.eq("the printed Enhancements are exactly the four the datasheet records",
     [h for h in _headings if h in _PRINTED], _PRINTED)
c.eq("...and the datasheet invents none the corpus does not print",
     [n for n in _PRINTED if n not in _headings], [])

c.finish()
