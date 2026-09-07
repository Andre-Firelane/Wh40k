"""The DEATH GUARD faction: eleven datasheets and the Death Lord's Chosen
detachment record.

WHERE THE RULES LIVE, and it is not here: this module is DATA. The army rule
Nurgle's Gift is game/nurgles_gift.py (with its three Plagues in
game/plagues.py), the detachment rule Deadly Vectors is
game/deadly_vectors.py, and each datasheet ability is its own module named in
the profile flag's comment - the same split game/factions/necrons.py records.
The Detachment object below carries the rule TEXT and the four Enhancements as
description only; nothing reads Detachment.stratagems, because a live Stratagem
needs a controller and those are built in main.py.

EVERY PROFILE HERE CARRIES nurgles_gift = True (asserted in the suite): the
army rule is printed on every Death Guard datasheet, so the flag doubles as
this engine's "is this a DEATH GUARD model" test.

WEAPON NAMING: several of these weapons print names a loyalist Space Marine
faction also prints with DIFFERENT numbers (boltgun, meltagun, plasma gun,
power fist, multi-melta). Death Guard is currently the only faction here that
prints them at all, so they take the plain names - see game/weapons.py's own
Death Guard section header for what has to happen if that changes.
"""

from game import force_dispositions
from game.factions.datasheet import Datasheet, Gear, ModelLine, WargearOption
from game.factions.death_guard_points import DEATH_GUARD_POINTS
from game.factions.detachment import Detachment, Enhancement
from game.factions.faction import Faction, register_faction
from game.icon_of_despair import equip as _equip_icon_of_despair
from game.units import (ChaosSpawnProfile, DaemonPrinceOfNurgleProfile,
                        DeathshroudChampionProfile, DeathshroudTerminatorProfile,
                        DefilerProfile, FoetidBloatDroneProfile,
                        MalignantPlaguecasterProfile, MyphiticBlightHaulerProfile,
                        PlagueburstCrawlerProfile, PlagueChampionProfile,
                        PlagueMarineProfile, PoxwalkerProfile, TyphusProfile)
from game.weapons import (ArmouredTracksProfile, BileSpurtProfile,
                          BlightLauncherProfile, BoltgunProfile, BoltPistolProfile,
                          BuboticWeaponsProfile, CorruptedStaffProfile,
                          DefilerHeavyMissileLauncherFragProfile,
                          DefilerHeavyMissileLauncherKrakProfile,
                          EctoplasmaDestructorProfile, ElectroscourgeProfile,
                          EntropyCannonProfile, ExcruciatorCannonProfile,
                          FleshmowerProfile, GnashingMawProfile,
                          HadesBattleCannonProfile, HadesLascannonProfile,
                          HeavyBaleflamerProfile, HeavyPlagueWeaponProfile,
                          HeavyReaperAutocannonProfile, HeavySluggerProfile,
                          HellforgedWeaponsStrikeProfile, HideousMutationsProfile,
                          ImprovisedWeaponProfile, InfernalCannonProfile,
                          LakrimaeStrikeProfile, MagmaCuttersProfile,
                          ManreaperStrikeProfile, MeltagunProfile,
                          MissileLauncherFragProfile, MissileLauncherKrakProfile,
                          MultiMeltaProfile, PlagueBelcherProfile,
                          PlagueburstMortarProfile, PlagueKnivesProfile,
                          PlagueProbeProfile, PlagueSpewerProfile,
                          PlaguespitterProfile, PlaguespurtGauntletProfile,
                          PlagueWindProfile, PlasmaGunProfile, PlasmaPistolProfile,
                          PowerFistProfile, RothailVolleyGunProfile,
                          ShearingClawsStrikeProfile)

DEATH_GUARD = register_faction(Faction("Death Guard", "DEATH GUARD"))


# --- Plague Marines ---------------------------------------------------------

_PM_CHAMPION_LINE = "Plague Champion"
_PM_LINE = "Plague Marine"
_PM_LOADOUT = [BoltgunProfile, PlagueKnivesProfile]

PM_CHAMPION_TO_BOLT_PISTOL = "Champion Boltgun -> Bolt Pistol"
PM_CHAMPION_TO_PLASMA_GUN = "Champion Boltgun -> Plasma Gun"
PM_CHAMPION_TO_PLASMA_PISTOL = "Champion Boltgun -> Plasma Pistol"
PM_CHAMPION_TO_BUBOTIC = "Champion Plague Knives -> Bubotic Weapons"
PM_CHAMPION_TO_POWER_FIST = "Champion Plague Knives -> Power Fist"
PM_TO_BLIGHT_LAUNCHER = "Boltgun -> Blight Launcher"
PM_TO_PLAGUE_SPEWER = "Boltgun -> Plague Spewer"
PM_TO_MELTAGUN = "Boltgun -> Meltagun"
PM_TO_PLAGUE_BELCHER = "Boltgun -> Plague Belcher"
PM_TO_PLASMA_GUN = "Boltgun -> Plasma Gun"
PM_TO_BUBOTIC = "Boltgun -> Bubotic Weapons"
PM_TO_HEAVY_PLAGUE_WEAPON = "Boltgun -> Heavy Plague Weapon"
PM_ICON_OF_DESPAIR = "Icon of Despair"

PLAGUE_MARINES = DEATH_GUARD.add_datasheet(Datasheet(
    "Plague Marines",
    keywords=("INFANTRY", "BATTLELINE", "GRENADES", "CHAOS", "NURGLE",
              "PLAGUE MARINES", "DEATH GUARD"),
    composition_options=[
        [ModelLine(PlagueChampionProfile, 1, _PM_LOADOUT, name=_PM_CHAMPION_LINE),
         ModelLine(PlagueMarineProfile, n - 1, _PM_LOADOUT, name=_PM_LINE)]
        for n in (5, 7, 10)
    ],
    wargear_options=[
        # The Champion's two menus. Each is "one of the following", so all
        # three boltgun swaps share a replaced set and therefore a cursor -
        # which is exactly what stops two of them landing on him at once.
        WargearOption(_PM_CHAMPION_LINE, replaces=BoltgunProfile,
                      with_weapons=[BoltPistolProfile], max_models=1,
                      name=PM_CHAMPION_TO_BOLT_PISTOL),
        WargearOption(_PM_CHAMPION_LINE, replaces=BoltgunProfile,
                      with_weapons=[PlasmaGunProfile], max_models=1,
                      name=PM_CHAMPION_TO_PLASMA_GUN),
        WargearOption(_PM_CHAMPION_LINE, replaces=BoltgunProfile,
                      with_weapons=[PlasmaPistolProfile], max_models=1,
                      name=PM_CHAMPION_TO_PLASMA_PISTOL),
        WargearOption(_PM_CHAMPION_LINE, replaces=PlagueKnivesProfile,
                      with_weapons=[BuboticWeaponsProfile], max_models=1,
                      name=PM_CHAMPION_TO_BUBOTIC),
        WargearOption(_PM_CHAMPION_LINE, replaces=PlagueKnivesProfile,
                      with_weapons=[PowerFistProfile], max_models=1,
                      name=PM_CHAMPION_TO_POWER_FIST),
        # "For every 5 models in this unit, 1 Plague Marine's boltgun can be
        # replaced with..." - per_models is the ratio, computed against the
        # WHOLE unit (Champion included), which is what the printed text says.
        WargearOption(_PM_LINE, replaces=BoltgunProfile,
                      with_weapons=[BlightLauncherProfile], per_models=5,
                      name=PM_TO_BLIGHT_LAUNCHER),
        WargearOption(_PM_LINE, replaces=BoltgunProfile,
                      with_weapons=[PlagueSpewerProfile], per_models=5,
                      name=PM_TO_PLAGUE_SPEWER),
        WargearOption(_PM_LINE, replaces=BoltgunProfile,
                      with_weapons=[MeltagunProfile], per_models=5,
                      name=PM_TO_MELTAGUN),
        WargearOption(_PM_LINE, replaces=BoltgunProfile,
                      with_weapons=[PlagueBelcherProfile], per_models=5,
                      name=PM_TO_PLAGUE_BELCHER),
        WargearOption(_PM_LINE, replaces=BoltgunProfile,
                      with_weapons=[PlasmaGunProfile], per_models=5,
                      name=PM_TO_PLASMA_GUN),
        # "For every 5 models in this unit, UP TO 2 Plague Marines can each
        # have their boltgun replaced" - a 2-per-5 ratio, which WargearOption
        # has no field for: per_models expresses 1-per-N only, and max_for()
        # computes `unit_size // per_models`. So it is written as 2.5, which
        # gives the printed answer for every size this datasheet can be built
        # at: 5 -> 2, 7 -> 2, 10 -> 4.
        #
        # NOT exact in general, and that is why it is said out loud rather
        # than left to be discovered: at 9 models it would allow 3 where the
        # printed rule allows 2. Nine is not one of the three points tiers, so
        # this engine cannot build it - the test pins the cap at all three
        # sizes so a future tier cannot slip past this quietly.
        WargearOption(_PM_LINE, replaces=BoltgunProfile,
                      with_weapons=[BuboticWeaponsProfile], per_models=2.5,
                      name=PM_TO_BUBOTIC),
        WargearOption(_PM_LINE, replaces=BoltgunProfile,
                      with_weapons=[HeavyPlagueWeaponProfile], per_models=2.5,
                      name=PM_TO_HEAVY_PLAGUE_WEAPON),
    ],
    gear_options=[Gear(_PM_LINE, PM_ICON_OF_DESPAIR, _equip_icon_of_despair)],
    gear_slots={_PM_LINE: 1},
    points=DEATH_GUARD_POINTS["Plague Marines"],
    abilities_text=[
        "Nurgle's Gift (Aura): an enemy unit within Contagion Range is Afflicted - "
        "see game/nurgles_gift.py and game/plagues.py.",
        "Icon of Despair (Aura): while an enemy unit is within 6\" of the bearer, "
        "worsen the Leadership characteristic of models in that unit by 1 - "
        "see game/icon_of_despair.py.",
    ],
))


# --- Poxwalkers -------------------------------------------------------------

_POX_LINE = "Poxwalker"

POXWALKERS = DEATH_GUARD.add_datasheet(Datasheet(
    "Poxwalkers",
    keywords=("INFANTRY", "CHAOS", "NURGLE", "POXWALKERS", "DEATH GUARD"),
    composition_options=[
        [ModelLine(PoxwalkerProfile, n, [ImprovisedWeaponProfile], name=_POX_LINE)]
        for n in (10, 20)
    ],
    points=DEATH_GUARD_POINTS["Poxwalkers"],
    abilities_text=[
        "Core: Infiltrators, Feel No Pain 5+.",
        "Curse of the Walking Pox: each time a POXWALKER model in this unit destroys "
        "an enemy model (excluding MONSTER and VEHICLE), one destroyed Poxwalker "
        "returns after this unit resolves its attacks; while TYPHUS leads it, models "
        "killed by his Eater Plague count too - see game/curse_of_the_walking_pox.py.",
    ],
))


# --- Characters -------------------------------------------------------------

TYPHUS = DEATH_GUARD.add_datasheet(Datasheet(
    "Typhus",
    keywords=("INFANTRY", "CHARACTER", "PSYKER", "EPIC HERO", "CHAOS", "NURGLE",
              "TERMINATOR", "TYPHUS", "DEATH GUARD"),
    model_lines=[ModelLine(TyphusProfile, 1, [LakrimaeStrikeProfile], name="Typhus")],
    points=DEATH_GUARD_POINTS["Typhus"],
    abilities_text=[
        "Core: Deep Strike, Leader.",
        "The Destroyer Hive: while this model is leading a unit, each time a melee "
        "attack targets that unit, subtract 1 from the Hit roll - "
        "see game/destroyer_hive.py.",
        "Eater Plague (Psychic): in your Shooting phase, one enemy unit within 18\" "
        "and visible; on a 1 this PSYKER's own unit suffers D3 mortal wounds, on a "
        "2-5 the target suffers D6, on a 6 it suffers D3+3 - "
        "see game/mortal_wound_abilities.py.",
    ],
))

MALIGNANT_PLAGUECASTER = DEATH_GUARD.add_datasheet(Datasheet(
    "Malignant Plaguecaster",
    keywords=("INFANTRY", "CHARACTER", "PSYKER", "CHAOS", "NURGLE",
              "MALIGNANT PLAGUECASTER", "DEATH GUARD"),
    model_lines=[ModelLine(
        MalignantPlaguecasterProfile, 1,
        [BoltPistolProfile, PlagueWindProfile, CorruptedStaffProfile],
        name="Malignant Plaguecaster")],
    points=DEATH_GUARD_POINTS["Malignant Plaguecaster"],
    abilities_text=[
        "Core: Leader.",
        "Gift of Contagion: while this model is leading a unit, that unit's attacks "
        "against an Afflicted target have [SUSTAINED HITS 1] - "
        "see game/gift_of_contagion.py.",
        "Pestilent Fallout: after this model shoots, one enemy INFANTRY unit hit by "
        "its Plague Wind is enfeebled (-2\" Move) until the end of your opponent's "
        "next turn - see game/pestilent_fallout.py.",
    ],
))

DAEMON_PRINCE_OF_NURGLE = DEATH_GUARD.add_datasheet(Datasheet(
    "Daemon Prince of Nurgle",
    keywords=("MONSTER", "CHARACTER", "CHAOS", "NURGLE", "DAEMON", "DAEMON PRINCE",
              "DEATH GUARD"),
    model_lines=[ModelLine(
        DaemonPrinceOfNurgleProfile, 1,
        [InfernalCannonProfile, HellforgedWeaponsStrikeProfile],
        name="Daemon Prince of Nurgle")],
    points=DEATH_GUARD_POINTS["Daemon Prince of Nurgle"],
    abilities_text=[
        "Core: Deadly Demise D3.",
        "Death Guard Defenders: while within 3\" of a friendly DEATH GUARD INFANTRY "
        "unit, this model has Lone Operative - see game/death_guard_defenders.py.",
        "Fevered Strategist: once per battle round, reduce by 1 the CP cost of a "
        "Stratagem targeting a friendly DEATH GUARD unit within 12\" - "
        "see game/fevered_strategist.py.",
        "Miasma of Pestilence (Aura): a friendly DEATH GUARD unit within 6\" has the "
        "Benefit of Cover against ranged attacks - see game/miasma_of_pestilence.py.",
    ],
))


# --- Chaos Spawn ------------------------------------------------------------

CHAOS_SPAWN = DEATH_GUARD.add_datasheet(Datasheet(
    "Chaos Spawn",
    keywords=("BEAST", "CHAOS", "NURGLE", "CHAOS SPAWN", "DEATH GUARD"),
    model_lines=[ModelLine(ChaosSpawnProfile, 2, [HideousMutationsProfile],
                           name="Chaos Spawn")],
    points=DEATH_GUARD_POINTS["Chaos Spawn"],
    abilities_text=[
        "Core: Deadly Demise 1, Feel No Pain 5+, Scouts 6\".",
        "Lethal Ichor: each melee attack allocated to this unit may cost the "
        "attacking unit a mortal wound on a 4+, up to six dice per attacking unit - "
        "see game/lethal_ichor.py.",
    ],
))


# --- Deathshroud Terminators ------------------------------------------------

_DS_CHAMPION_LINE = "Deathshroud Champion"
_DS_LINE = "Deathshroud Terminator"
_DS_LOADOUT = [PlaguespurtGauntletProfile, ManreaperStrikeProfile]

DS_EXTRA_GAUNTLET = "Additional Plaguespurt Gauntlet"
DS_ICON_OF_DESPAIR = "Icon of Despair"

DEATHSHROUD_TERMINATORS = DEATH_GUARD.add_datasheet(Datasheet(
    "Deathshroud Terminators",
    keywords=("INFANTRY", "CHAOS", "NURGLE", "TERMINATOR",
              "DEATHSHROUD TERMINATORS", "DEATH GUARD"),
    composition_options=[
        [ModelLine(DeathshroudChampionProfile, 1, _DS_LOADOUT, name=_DS_CHAMPION_LINE),
         ModelLine(DeathshroudTerminatorProfile, n - 1, _DS_LOADOUT, name=_DS_LINE)]
        for n in (3, 6)
    ],
    wargear_options=[
        # A pure ADDITION (replaces=None), so it starts at model 0 and uses no
        # cursor - the Champion simply carries a second gauntlet.
        WargearOption(_DS_CHAMPION_LINE, replaces=None,
                      with_weapons=[PlaguespurtGauntletProfile], max_models=1,
                      name=DS_EXTRA_GAUNTLET),
    ],
    gear_options=[Gear(_DS_CHAMPION_LINE, DS_ICON_OF_DESPAIR, _equip_icon_of_despair)],
    gear_slots={_DS_CHAMPION_LINE: 1},
    points=DEATH_GUARD_POINTS["Deathshroud Terminators"],
    abilities_text=[
        "Core: Deep Strike.",
        "Silent Bodyguard: while a CHARACTER model is leading this unit, that "
        "CHARACTER has Feel No Pain 4+ - see game/silent_bodyguard.py.",
        "Death Approaches: when set up by Deep Strike, this unit can be more than "
        "6\" from an Afflicted enemy unit and more than 8\" from any other, instead "
        "of the usual 9\" - see game/death_approaches.py.",
        "Icon of Despair (Aura): see game/icon_of_despair.py.",
    ],
))


# --- Vehicles ---------------------------------------------------------------

_DEFILER_LINE = "Defiler"
_DEFILER_LOADOUT = [
    HadesBattleCannonProfile,
    ExcruciatorCannonProfile, ExcruciatorCannonProfile,   # "2 excruciator cannons"
    HeavyBaleflamerProfile,
    DefilerHeavyMissileLauncherKrakProfile,
    ShearingClawsStrikeProfile,
]

DEFILER_TO_ECTOPLASMA = "Hades Battle Cannon -> Ectoplasma Destructor"
DEFILER_TO_MAGMA_CUTTERS = "Excruciator Cannons -> 2 Magma Cutters"
DEFILER_BALEFLAMER_TO_LASCANNON = "Heavy Baleflamer -> Hades Lascannon"
DEFILER_BALEFLAMER_TO_REAPER = "Heavy Baleflamer -> Heavy Reaper Autocannon"
DEFILER_BALEFLAMER_TO_ELECTROSCOURGE = "Heavy Baleflamer -> Electroscourge"
DEFILER_MISSILES_TO_LASCANNON = "Heavy Missile Launcher -> Hades Lascannon"
DEFILER_MISSILES_TO_REAPER = "Heavy Missile Launcher -> Heavy Reaper Autocannon"
DEFILER_MISSILES_TO_ELECTROSCOURGE = "Heavy Missile Launcher -> Electroscourge"

DEFILER = DEATH_GUARD.add_datasheet(Datasheet(
    "Defiler",
    keywords=("VEHICLE", "WALKER", "CHAOS", "NURGLE", "DAEMON", "DEFILER",
              "DEATH GUARD"),
    model_lines=[ModelLine(DefilerProfile, 1, _DEFILER_LOADOUT, name=_DEFILER_LINE)],
    wargear_options=[
        WargearOption(_DEFILER_LINE, replaces=HadesBattleCannonProfile,
                      with_weapons=[EctoplasmaDestructorProfile], max_models=1,
                      name=DEFILER_TO_ECTOPLASMA),
        # "2 excruciator cannons can be replaced with 2 magma cutters" - a
        # matched pair, so both copies go and both replacements arrive. A swap
        # gives up EVERY copy of the named weapon (see build_squad()'s own
        # note), which is exactly the all-or-nothing the printed text wants.
        WargearOption(_DEFILER_LINE, replaces=ExcruciatorCannonProfile,
                      with_weapons=[MagmaCuttersProfile, MagmaCuttersProfile],
                      max_models=1, name=DEFILER_TO_MAGMA_CUTTERS),
        # The two "one of the following" menus. Note both offer the SAME three
        # weapons but replace DIFFERENT ones, so build_squad() gives them
        # separate cursors and a Defiler can legally take two lascannons.
        WargearOption(_DEFILER_LINE, replaces=HeavyBaleflamerProfile,
                      with_weapons=[HadesLascannonProfile], max_models=1,
                      points=DEATH_GUARD_POINTS["Defiler"].wargear.get("Hades lascannon", 0),
                      name=DEFILER_BALEFLAMER_TO_LASCANNON),
        WargearOption(_DEFILER_LINE, replaces=HeavyBaleflamerProfile,
                      with_weapons=[HeavyReaperAutocannonProfile], max_models=1,
                      points=DEATH_GUARD_POINTS["Defiler"].wargear.get("heavy reaper autocannon", 0),
                      name=DEFILER_BALEFLAMER_TO_REAPER),
        WargearOption(_DEFILER_LINE, replaces=HeavyBaleflamerProfile,
                      with_weapons=[ElectroscourgeProfile], max_models=1,
                      name=DEFILER_BALEFLAMER_TO_ELECTROSCOURGE),
        WargearOption(_DEFILER_LINE, replaces=DefilerHeavyMissileLauncherKrakProfile,
                      with_weapons=[HadesLascannonProfile], max_models=1,
                      points=DEATH_GUARD_POINTS["Defiler"].wargear.get("Hades lascannon", 0),
                      name=DEFILER_MISSILES_TO_LASCANNON),
        WargearOption(_DEFILER_LINE, replaces=DefilerHeavyMissileLauncherKrakProfile,
                      with_weapons=[HeavyReaperAutocannonProfile], max_models=1,
                      points=DEATH_GUARD_POINTS["Defiler"].wargear.get("heavy reaper autocannon", 0),
                      name=DEFILER_MISSILES_TO_REAPER),
        WargearOption(_DEFILER_LINE, replaces=DefilerHeavyMissileLauncherKrakProfile,
                      with_weapons=[ElectroscourgeProfile], max_models=1,
                      name=DEFILER_MISSILES_TO_ELECTROSCOURGE),
    ],
    points=DEATH_GUARD_POINTS["Defiler"],
    abilities_text=[
        "Core: Deadly Demise D6.",
        "Scuttling Walker: moves through models and terrain, may pass through "
        "Engagement Range without ending there - see game/scuttling_walker.py.",
        "Barrage of Filth: after this model shoots, one enemy unit it hit cannot "
        "have the Benefit of Cover until the end of the phase - "
        "see game/barrage_of_filth.py.",
    ],
))


_BLOAT_LINE = "Foetid Bloat-drone"
BLOAT_DRONE_TO_PLAGUESPITTERS = "Fleshmower -> 2 Plaguespitters"

FOETID_BLOAT_DRONE = DEATH_GUARD.add_datasheet(Datasheet(
    "Foetid Bloat-drone",
    keywords=("VEHICLE", "FLY", "CHAOS", "NURGLE", "DAEMON", "FOETID BLOAT-DRONE",
              "CONTAGION ENGINE", "DEATH GUARD"),
    model_lines=[ModelLine(FoetidBloatDroneProfile, 1,
                           [PlagueProbeProfile, FleshmowerProfile], name=_BLOAT_LINE)],
    wargear_options=[
        WargearOption(_BLOAT_LINE, replaces=FleshmowerProfile,
                      with_weapons=[PlaguespitterProfile, PlaguespitterProfile],
                      max_models=1, name=BLOAT_DRONE_TO_PLAGUESPITTERS),
    ],
    points=DEATH_GUARD_POINTS["Foetid Bloat-drone"],
    abilities_text=[
        "Core: Deadly Demise D3.",
        "Hovering Death: eligible to shoot and declare a charge in a turn in which "
        "it Fell Back - see game/hovering_death.py.",
    ],
))


_HAULER_LINE = "Myphitic Blight-hauler"

MYPHITIC_BLIGHT_HAULER = DEATH_GUARD.add_datasheet(Datasheet(
    "Myphitic Blight-hauler",
    keywords=("VEHICLE", "SMOKE", "CHAOS", "NURGLE", "DAEMON",
              "MYPHITIC BLIGHT-HAULER", "DEATH GUARD"),
    composition_options=[
        [ModelLine(MyphiticBlightHaulerProfile, n,
                   [BileSpurtProfile, MissileLauncherKrakProfile, MultiMeltaProfile,
                    GnashingMawProfile], name=_HAULER_LINE)]
        for n in (1, 2)
    ],
    points=DEATH_GUARD_POINTS["Myphitic Blight-hauler"],
    abilities_text=[
        "Core: Deadly Demise D3.",
        "Tank Hunters: in your Shooting phase, +1 to the Hit roll and +1 to the "
        "Wound roll against MONSTER or VEHICLE units. NOTE the phase clause - the "
        "Ork ability of the same name has none, which is why this is a separate "
        "flag; see game/squad.py's tank_hunters_modifiers().",
    ],
))


_CRAWLER_LINE = "Plagueburst Crawler"
_CRAWLER_LOADOUT = [
    PlagueburstMortarProfile, HeavySluggerProfile,
    EntropyCannonProfile, EntropyCannonProfile,   # "2 entropy cannons"
    ArmouredTracksProfile,
]

CRAWLER_TO_PLAGUESPITTERS = "2 Entropy Cannons -> 2 Plaguespitters"
CRAWLER_TO_ROTHAIL = "Heavy Slugger -> Rothail Volley Gun"

PLAGUEBURST_CRAWLER = DEATH_GUARD.add_datasheet(Datasheet(
    "Plagueburst Crawler",
    keywords=("VEHICLE", "FRAME", "CHAOS", "NURGLE", "DAEMON",
              "PLAGUEBURST CRAWLER", "DEATH GUARD"),
    model_lines=[ModelLine(PlagueburstCrawlerProfile, 1, _CRAWLER_LOADOUT,
                           name=_CRAWLER_LINE)],
    wargear_options=[
        WargearOption(_CRAWLER_LINE, replaces=EntropyCannonProfile,
                      with_weapons=[PlaguespitterProfile, PlaguespitterProfile],
                      max_models=1, name=CRAWLER_TO_PLAGUESPITTERS),
        WargearOption(_CRAWLER_LINE, replaces=HeavySluggerProfile,
                      with_weapons=[RothailVolleyGunProfile], max_models=1,
                      name=CRAWLER_TO_ROTHAIL),
    ],
    points=DEATH_GUARD_POINTS["Plagueburst Crawler"],
    abilities_text=[
        "Core: Deadly Demise D3.",
        "Spore-laced Shock Waves: when its Plagueburst mortar picks a target, roll a "
        "D6 for that unit and every enemy unit within 3\" of it (+1 if Afflicted); "
        "on a 6+ that unit suffers D3 mortal wounds after the attacks resolve - "
        "see game/spore_laced_shock_waves.py.",
    ],
))


# --- The detachment ---------------------------------------------------------

DEATH_LORDS_CHOSEN = DEATH_GUARD.add_detachment(Detachment(
    "Death Lord's Chosen",
    rule_name="Deadly Vectors",
    setting="DEATH_LORDS_CHOSEN_PLAYERS",
    points=2,
    force_disposition=force_dispositions.PRIORITY_ASSETS,
    rule_text=(
        "Deadly Vectors: in your opponent's Command phase, roll 2D6 for each "
        "Afflicted enemy unit, subtracting 1 from the result if that unit is Below "
        "Half-strength. If the result is 6 or less, that enemy unit suffers D3 "
        "mortal wounds. See game/deadly_vectors.py; the six Stratagems are live "
        "controllers built in main.py and share the predicates in "
        "game/death_lords_chosen.py."
    ),
    enhancements=(
        # Data only - Enhancements are not a system in this engine.
        Enhancement("Face of Death", 10),
        Enhancement("Vile Vigour", 15),
        Enhancement("Helm of the Fly King", 20),
        Enhancement("Warprot Talisman", 30),
    ),
))
