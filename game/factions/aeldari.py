"""Aeldari faction data - the third faction in this engine, after T'au Empire
and Orks.

The army rule (Battle Focus and its six Agile Manoeuvres) is NOT here: it lives
in game/battle_focus.py, because it applies regardless of detachment and is
engine behaviour rather than datasheet data. Same split the other two factions
use - this module holds datasheet-level data only. The Seer Council
detachment's rule (Strands of Fate) is likewise in game/strands_of_fate.py.

Guardian Defenders is the first datasheet, and with it the army rule stops
being inert: its models are the first carriers of UnitProfile.battle_focus,
which is also what game/battle_focus.py's qualifying_players() reads to decide
whose army counts as ASURYANI.
"""

from game import force_dispositions
from game.factions.aeldari_points import AELDARI_POINTS
from game.factions.datasheet import Datasheet, Gear, ModelLine, WargearOption
from game.factions.detachment import Detachment, Enhancement
from game.factions.faction import Faction, register_faction
from game.units import (
    AsurmenProfile,
    AvatarOfKhaineProfile,
    EldradUlthranProfile,
    LhykhisProfile,
    FarseerProfile,
    WarlockProfile,
    JainZarProfile,
    DireAvengerExarchProfile,
    DireAvengerProfile,
    FalconProfile,
    WraithguardProfile,
    FireDragonExarchProfile,
    FireDragonProfile,
    GuardianDefenderProfile,
    HeavyWeaponPlatformProfile,
    HowlingBansheeExarchProfile,
    HowlingBansheeProfile,
    SerpentsScalePlatformProfile,
    StormGuardianProfile,
    StrikingScorpionExarchProfile,
    StrikingScorpionProfile,
    WarpSpiderExarchProfile,
    WarpSpiderProfile,
    DarkReaperExarchProfile, DarkReaperProfile, ShiningSpearExarchProfile, ShiningSpearProfile,
    FueganProfile,
    WarWalkerProfile,
    WarlockSkyrunnerProfile,
    WaveSerpentProfile, WindriderProfile,
    RangerProfile, ShroudRunnerProfile,
    BaharrothProfile, SwoopingHawkExarchProfile, SwoopingHawkProfile,
    WraithbladeProfile, WraithlordProfile,
    DCannonPlatformProfile, ShadowWeaverPlatformProfile,
    VibroCannonPlatformProfile,
    FirePrismProfile, NightSpinnerProfile, VyperProfile,
    LoneWarlockProfile, SpiritseerProfile, FarseerSkyrunnerProfile,
    AutarchProfile, AutarchWayleaperProfile, MauganRaProfile,
    DragonKnightProfile, ClanbladeProfile, LeystalkerProfile,
    StonesingerProfile,
    CorsairVoidreaverProfile, VoidreaverFelarchProfile,
    CorsairVoidscarredProfile, VoidscarredFelarchProfile,
    ShadeRunnerProfile, SoulWeaverProfile, WaySeekerProfile,
    CorsairSkyreaverProfile, SkyreaverFelarchProfile,
    KharsethProfile, PrinceYrielProfile, StarfangProfile,
    YvraineProfile, TheVisarchProfile, TheYncarneProfile,
)
from game.weapons import (
    AeldariCloseCombatWeaponA2Profile,
    AeldariCloseCombatWeaponProfile,
    AeldariFlamerProfile,
    AvengerShurikenCatapultProfile,
    BladeOfDestructionProfile,
    BloodyTwinsProfile,
    BansheeBladeProfile,
    BitingBladeProfile,
    BrightLanceProfile,
    ChainsabresMeleeProfile,
    ChainsabresRangedProfile,
    DeathSpinnerProfile,
    DeathWeaversProfile,
    DireswordProfile,
    DestructorProfile,
    EldritchStormProfile,
    BroodTwainProfile,
    MindWarProfile,
    DragonAxeProfile,
    DragonFusionGunProfile,
    DragonFusionPistolProfile,
    DragonsBreathFlamerProfile,
    ExarchsDeathSpinnerProfile,
    ExarchsDragonFusionGunProfile,
    ExecutionerProfile,
    FirepikeProfile,
    FusionGunProfile,
    MissileLauncherStarshotProfile,
    MirrorswordsProfile,
    PowerbladeArrayProfile,
    PowerbladesProfile,
    PowerGlaiveProfile,
    PowerSwordProfile,
    PulseLaserProfile,
    ScatterLaserProfile,
    DScytheProfile,
    ScorpionChainswordProfile,
    ScorpionsClawProfile,
    ShurikenCatapultProfile,
    ShurikenPistolProfile,
    SpidersFangsProfile,
    StaffOfUlthamarProfile,
    WailingDoomProfile,
    WailingDoomStrikeProfile,
    WailingDoomSweepProfile,
    WeaverenderProfile,
    ShurikenCannonProfile,
    SpinneretRifleProfile,
    SilentDeathProfile,
    SingingSpearMeleeProfile,
    SingingSpearRangedProfile,
    SwordOfAsurProfile,
    StarcannonProfile,
    TriskeleMeleeProfile,
    TriskeleRangedProfile,
    TwinShurikenCatapultProfile,
    TwinBrightLanceProfile,
    TwinMissileLauncherStarshotProfile,
    TwinScatterLaserProfile,
    TwinShurikenCannonProfile,
    TwinStarcannonProfile,
    FireAxeProfile,
    SearsongBeamProfile,
    WarWalkerFeetProfile,
    WraithboneHullProfile,
    WraithCloseCombatWeaponProfile,
    WraithcannonProfile, VoidreaverWraithcannonProfile,
    WitchbladeProfile,
    DarkReaperMissileLauncherStarshotProfile, DarkReaperShurikenCannonProfile, LaserLanceMeleeProfile, LaserLanceRangedProfile, ParagonSabreProfile, ReaperLauncherStarshotProfile, StarLanceMeleeProfile, StarLanceRangedProfile, TempestLauncherProfile,
    AeldariCloseCombatWeaponA3Profile, ScatterLaserProfile,
    RangerLongRifleProfile, RangerShurikenPistolProfile,
    ShroudRunnerLongRifleProfile, ShroudRunnerScatterLaserProfile,
    ExarchsLasblasterProfile, FuryOfTheTempestProfile, HawksTalonProfile,
    LasblasterProfile, ShiningBladeProfile, SunpistolProfile,
    SwoopingHawkPowerSwordProfile,
    GhostaxeProfile, GhostglaiveStrikeProfile, GhostswordsProfile,
    WraithboneFistsProfile,
    DCannonProfile, ShadowWeaverProfile, VibroCannonProfile,
    PrismCannonDispersedPulseProfile, DoomweaverProfile,
    WitchStaffProfile,
    AutarchBansheeBladeProfile, AutarchScorpionChainswordProfile,
    AutarchReaperLauncherStarshotProfile, StarGlaiveProfile,
    MaugetarRangedProfile, MaugetarMeleeProfile,
    DeathSpinnerProfile, DragonFusionGunProfile, DragonFusionPistolProfile,
    SolarCarbineProfile, DrakesteedFangsAndTalonsProfile,
    ExoditeLaserLanceMeleeProfile, MoonbladesProfile,
    ExoditeLongRifleProfile, HuntingBladesProfile,
    SongOfWaningProfile, VenomcrestSpitProfile, StoneStaveProfile,
    BlasterProfile, NeuroDisruptorProfile, ShredderProfile,
    ShurikenRifleProfile, BlastPistolProfile, CorsairBladeProfile,
    PairedHekatariiBladesProfile, VoidscarredExecutionerProfile,
    VoidscarredPowerSwordProfile,
    WaySeekerWitchStaffProfile, DreadOfTheDeepVoidProfile, WaystaveProfile,
    EyeOfWrathProfile, SpearOfTwilightProfile, DisintegratorCannonProfile,
    StarfangGrenadeLauncherProfile, PowerSwordProfile, FusionGunProfile,
    LaserLanceRangedProfile,
    VyperScatterLaserProfile, VyperStarcannonProfile,
    TwinShurikenCatapultProfile,
    StormOfWhispersProfile, KhaVirProfile, AsuVarQuicksilverStanceProfile,
    SwirlingSoulEnergyProfile, VilithZharStrikeProfile,
)

AELDARI = register_faction(Faction("Aeldari", "AELDARI"))

# The one Aeldari detachment modelled. Recorded here so that every faction
# answers "which detachments do you have, and which config constant says who
# is fielding them" the same way - game/detachments.py reads exactly that, and
# a faction that answered it differently would need a special case there.
# Until the T'au gained a second detachment this record did not exist at all
# and game/army_lists.py carried the setting name instead, which worked only
# while an army list and a detachment were the same choice.
SEER_COUNCIL = AELDARI.add_detachment(Detachment(
    "Seer Council",
    rule_name="Strands of Fate",
    setting="SEER_COUNCIL_PLAYERS",
    points=2,
    force_disposition=force_dispositions.PRIORITY_ASSETS,
    rule_text=(
        "Strands of Fate: at the start of the battle, roll six D6 and set them aside as "
        "Fate dice. Once per phase, you can spend one to reduce the cost of a Stratagem. "
        "See game/strands_of_fate.py."
    ),
    enhancements=(
        Enhancement("Lucid Eye", 30),
        Enhancement("Runes of Warding", 25),
        Enhancement("Stone of Eldritch Fury", 15),
        Enhancement("Torc of Morai-Heg", 20),
    ),))

# The seven further detachments whose RULES are modelled. Their `rule_text` is
# the VERBATIM printed rule from rules/aeldari/detachments/, not Seer Council's
# older paraphrase-with-a-module-pointer style.
#
# `stratagems=` stays EMPTY and `enhancements=` no longer does. A record here
# makes a detachment SELECTABLE and nothing more - making one DO something is a
# module per rule - but the Enhancement records are also what game/enhancements.py's
# registry is PINNED AGAINST (points and detachment, rather than literals), so
# they earn their place twice.
#
# Between them these seven print 36 Stratagems and 24 Enhancements, and both are
# now built; Seer Council's four bring the Enhancement total to 28. (The
# Stratagem count read 30 until it was recounted against the corpus:
# 6+6+6+6+6+3+3. The wrong figure had silently dropped Armoured Warhost's three
# and Path of the Outcast's three, i.e. exactly the two detachments that print
# fewer than six - which is how a plausible-looking 5 x 6 survived review. The
# test counts the corpus headings rather than trusting either number, and does
# the same for the Enhancements.)
#
# No `tag` on any of them: none prints an exclusion clause. Measured across all
# 15 Aeldari detachment pages - only Fateful Performance and Twilight Flickers
# carry one (ACROBATIC), and neither is in this batch.

ARMOURED_WARHOST = AELDARI.add_detachment(Detachment(
    "Armoured Warhost",
    rule_name="Skilled Crews",
    setting="ARMOURED_WARHOST_PLAYERS",
    points=1,
    force_disposition=force_dispositions.RECONNAISSANCE,
    rule_text=(
        "Skilled Crews: Friendly AELDARI VEHICLE units' ranged attacks have [ASSAULT]. "
        "Granted in the adjuster chain AND read by game/coldstar.py's "
        "weapon_has_assault(), which is what actually lets a vehicle Advance and still "
        "shoot (24.04). See game/skilled_crews.py."
    ),
    enhancements=(
        Enhancement("Spirit Stone of Raelyth", 20),
        Enhancement("Guiding Presence", 25),
    ),))

PATH_OF_THE_OUTCAST_DETACHMENT = AELDARI.add_detachment(Detachment(
    "Path of the Outcast",
    rule_name="Far-Reaching Doom",
    setting="PATH_OF_THE_OUTCAST_PLAYERS",
    points=1,
    force_disposition=force_dispositions.RECONNAISSANCE,
    rule_text=(
        "Far-Reaching Doom: when a friendly RANGERS/SHROUD RUNNERS unit is selected to "
        "shoot, enemy units have +6\" detection range until that friendly unit has shot. "
        "The engine module is named after the RULE, not the detachment - "
        "game/path_of_the_outcast.py is the RANGERS DATASHEET ability of the same name "
        "and shares none of this text. See game/far_reaching_doom.py."
    ),
    enhancements=(
        Enhancement("Camouflaged Snipers", 10),
        Enhancement("Assassins' Eye", 15),
    ),))

GUARDIAN_BATTLEHOST = AELDARI.add_detachment(Detachment(
    "Guardian Battlehost",
    rule_name="Defend at All Costs",
    setting="GUARDIAN_BATTLEHOST_PLAYERS",
    points=2,
    force_disposition=force_dispositions.TAKE_AND_HOLD,
    rule_text=(
        "Defend at All Costs: each time a DIRE AVENGER, GUARDIAN, SUPPORT WEAPON or "
        "WAR WALKER model from your army makes an attack, if that model's unit and/or "
        "the target unit are within range of one or more objective markers, add 1 to "
        "the Hit roll. The \"and/or\" is an OR - three of the four board states pay. "
        "See game/defend_at_all_costs.py."
    ),
    enhancements=(
        Enhancement("Craftworld's Champion", 25),
        Enhancement("Ethereal Pathway", 30),
        Enhancement("Protector of the Paths", 20),
        Enhancement("Breath of Vaul", 10),
    ),))

ASPECT_HOST = AELDARI.add_detachment(Detachment(
    "Aspect Host",
    rule_name="Path of the Warrior",
    setting="ASPECT_HOST_PLAYERS",
    points=3,
    force_disposition=force_dispositions.PRIORITY_ASSETS,
    rule_text=(
        "Path of the Warrior: each time an ASPECT WARRIORS or AVATAR OF KHAINE unit "
        "from your army is selected to shoot or fight, select one of the following for "
        "it to gain until the end of the phase - re-roll a Hit roll of 1, or re-roll a "
        "Wound roll of 1. A real choice between two exclusive options, so a real "
        "prompt; each clause is a plain automatic 1s re-roll rather than a "
        "failures-or-whole offer. See game/path_of_the_warrior.py."
    ),
    enhancements=(
        Enhancement("Aspect of Murder", 15),
        Enhancement("Mantle of Wisdom", 20),
        Enhancement("Shimmerstone", 10),
        Enhancement("Strategic Savant", 10),
    ),))

WARHOST = AELDARI.add_detachment(Detachment(
    "Warhost",
    rule_name="Martial Grace",
    setting="WARHOST_PLAYERS",
    points=3,
    force_disposition=force_dispositions.RECONNAISSANCE,
    rule_text=(
        "Martial Grace: at the start of the battle round you receive 1 additional "
        "Battle Focus token; each time a unit performs the Swift as the Wind Agile "
        "Manoeuvre, add an additional 1\" to the Move characteristic of models in that "
        "unit until the end of the phase; and each time a unit performs an Agile "
        "Manoeuvre that involves rolling a D6, add 1 to the result. Three clauses, all "
        "three turning dials on the army rule rather than adding a mechanism - so all "
        "three live in game/battle_focus.py's own seams. See game/martial_grace.py."
    ),
    enhancements=(
        Enhancement("Phoenix Gem", 35),
        Enhancement("Timeless Strategist", 15),
        Enhancement("Gift of Foresight", 15),
        Enhancement("Psychic Destroyer", 30),
    ),))

WINDRIDER_HOST = AELDARI.add_detachment(Detachment(
    "Windrider Host",
    rule_name="Ride the Wind",
    setting="WINDRIDER_HOST_PLAYERS",
    points=2,
    force_disposition=force_dispositions.DISRUPTION,
    rule_text=(
        "Ride the Wind: ASURYANI MOUNTED and VYPER units may be set up in Reserves and "
        "arrive as if from Strategic Reserves, and for the purposes of setting such "
        "units up the current battle round counts as one higher. In addition, at the "
        "end of your opponent's turn you may pull back up to N of them (Incursion 1, "
        "Strike Force 2, Onslaught 3) that are not within Engagement Range. WINDRIDERS "
        "gain BATTLELINE. Two of the four clauses are measured no-ops here - rule 20.01 "
        "already lets any unit start in Reserves, and no Aeldari rule reads BATTLELINE. "
        "See game/ride_the_wind.py."
    ),
    enhancements=(
        Enhancement("Firstdrawn Blade", 10),
        Enhancement("Mirage Field", 25),
        Enhancement("Seersight Strike", 15),
        Enhancement("Echoes of Ulthanesh", 20),
    ),))

SPIRIT_CONCLAVE = AELDARI.add_detachment(Detachment(
    "Spirit Conclave",
    rule_name="Shepherds of the Dead",
    setting="SPIRIT_CONCLAVE_PLAYERS",
    points=2,
    force_disposition=force_dispositions.TAKE_AND_HOLD,
    rule_text=(
        "Shepherds of the Dead: each time an ASURYANI PSYKER model from your army is "
        "destroyed by an enemy unit, that enemy unit gains a Vengeful Dead token, and "
        "WRAITH CONSTRUCT models add 1 to the Hit roll and 1 to the Wound roll against "
        "a unit carrying one or more. ASURYANI PSYKER models also have Spirit Guides "
        "(Aura): a WRAITHBLADES/WRAITHGUARD/WRAITHLORD unit within 12\" has the Battle "
        "Focus ability. WRAITHBLADES and WRAITHGUARD gain BATTLELINE (a measured no-op "
        "here). The ninth enemy mark and the first placed by a DEATH rather than a "
        "choice - cumulative, and the only one that never expires. "
        "See game/shepherds_of_the_dead.py."
    ),
    enhancements=(
        Enhancement("Light of Clarity", 30),
        Enhancement("Stave of Kurnous", 15),
        Enhancement("Rune of Mists", 10),
        Enhancement("Higher Duty", 25),
    ),))

_GUARDIAN_LOADOUT = [AeldariCloseCombatWeaponProfile, ShurikenCatapultProfile]
_PLATFORM_LOADOUT = [AeldariCloseCombatWeaponProfile, BrightLanceProfile]

GUARDIAN_DEFENDERS = AELDARI.add_datasheet(Datasheet(
    "Guardian Defenders",
    # Faction keywords (ASURYANI, AELDARI) are not repeated here - the Faction
    # itself carries AELDARI, and ASURYANI is what the army rule keys off,
    # which it reads from the ability rather than from this line.
    keywords=("BATTLELINE", "INFANTRY", "GRENADES", "GUARDIANS", "GUARDIAN DEFENDERS"),
    model_lines=[
        ModelLine(HeavyWeaponPlatformProfile, 1, _PLATFORM_LOADOUT, name="Heavy Weapon Platform"),
        ModelLine(GuardianDefenderProfile, 10, _GUARDIAN_LOADOUT, name="Guardian Defender"),
    ],
    # No wargear options modelled, deliberately. The datasheet lets the
    # platform swap its gun (Shuriken Cannon / Missile Launcher / Scatter Laser
    # / Starcannon are the alternatives), but the loadout supplied for this
    # project is the Bright Lance one and only its numbers were confirmed. The
    # others' keyword columns were not, and an unverified weapon keyword lands
    # in the engine as a wrong dice result - the same documented gap the Boyz
    # and Breacher Team datasheets carry for the same reason. Adding them later
    # is one WargearOption each.
    points=AELDARI_POINTS["Guardian Defenders"],
    abilities_text=[
        'Battle Focus (army rule): this unit can perform Agile Manoeuvres - see '
        'game/battle_focus.py for the token pool and all six manoeuvres.',
        'Fleet of Foot: performs the Fade Back Agile Manoeuvre without spending a Battle '
        'Focus token, is not blocked by another unit having done so this phase, and does '
        'not block other units from doing so either.',
        'Crewed Platform: when the last Guardian Defender model in this unit is destroyed, '
        'any remaining Heavy Weapon Platform models in this unit are destroyed too.',
    ],
))


_STORM_GUARDIAN_LOADOUT = [AeldariCloseCombatWeaponA2Profile, ShurikenPistolProfile]
# The platform carries no gun at all - its contribution is the Serpent Shield.
_SERPENT_PLATFORM_LOADOUT = [AeldariCloseCombatWeaponA2Profile]

_STORM_GUARDIAN_LINE = "Storm Guardian"

STORM_GUARDIAN_PISTOL_TO_FLAMER = "Shuriken Pistol -> Flamer"
STORM_GUARDIAN_PISTOL_TO_FUSION = "Shuriken Pistol -> Fusion Gun"
STORM_GUARDIAN_CCW_TO_POWER_SWORD = "Close Combat Weapon -> Power Sword"

STORM_GUARDIANS = AELDARI.add_datasheet(Datasheet(
    "Storm Guardians",
    keywords=("BATTLELINE", "INFANTRY", "GRENADES", "GUARDIANS", "STORM GUARDIANS"),
    model_lines=[
        ModelLine(SerpentsScalePlatformProfile, 1, _SERPENT_PLATFORM_LOADOUT,
                  name="Serpent's Scale Platform"),
        ModelLine(StormGuardianProfile, 10, _STORM_GUARDIAN_LOADOUT, name=_STORM_GUARDIAN_LINE),
    ],
    # Three options, each capped at 2 models INDEPENDENTLY - so a unit can
    # field 2 flamers AND 2 fusion guns, not 2 special weapons in total. That
    # distinction was checked rather than assumed, because a shared cap would
    # need a different mechanism than max_models entirely.
    wargear_options=[
        WargearOption(_STORM_GUARDIAN_LINE, replaces=ShurikenPistolProfile,
                      with_weapons=[AeldariFlamerProfile], max_models=2,
                      name=STORM_GUARDIAN_PISTOL_TO_FLAMER),
        WargearOption(_STORM_GUARDIAN_LINE, replaces=ShurikenPistolProfile,
                      with_weapons=[FusionGunProfile], max_models=2,
                      name=STORM_GUARDIAN_PISTOL_TO_FUSION),
        WargearOption(_STORM_GUARDIAN_LINE, replaces=AeldariCloseCombatWeaponA2Profile,
                      with_weapons=[PowerSwordProfile], max_models=2,
                      name=STORM_GUARDIAN_CCW_TO_POWER_SWORD),
    ],
    points=AELDARI_POINTS["Storm Guardians"],
    abilities_text=[
        'Battle Focus (army rule): this unit can perform Agile Manoeuvres - see '
        'game/battle_focus.py. Note that it does NOT have Fleet of Foot, unlike '
        'Guardian Defenders, so its Fade Back costs a token like anyone else\'s.',
        'Crewed Platform: when the last Storm Guardian model in this unit is destroyed, '
        'any remaining Serpent\'s Scale Platform models in this unit are destroyed too.',
        'Serpent Shield: while the platform lives, every model in this unit has a 5+ '
        'invulnerable save - see game/invulnerable_save.py.',
        'Stormblades: at the end of the owner\'s phase, an objective marker they control '
        'with this unit in range stays theirs even with no models in range, until the '
        'opponent\'s Level of Control over it is greater. Mechanically the same rule Kroot '
        'Carnivores print as "Fieldcraft" and Boyz as "Get Da Good Bitz", so it shares that '
        'flag and rule 14.03\'s existing Secured mechanism - see game/fieldcraft.py.',
    ],
))


_SCORPION_LOADOUT = [ScorpionChainswordProfile, ShurikenPistolProfile]
_EXARCH_LOADOUT = [ScorpionChainswordProfile, ScorpionsClawProfile, ShurikenPistolProfile]

_EXARCH_LINE = "Striking Scorpion Exarch"
_EXARCH_PRINTED_WEAPONS = (
    ScorpionChainswordProfile, ScorpionsClawProfile, ShurikenPistolProfile,
)

EXARCH_TO_BITING_BLADE = "Exarch -> Biting Blade + Shuriken Pistol"
EXARCH_TO_CHAINSABRES = "Exarch -> Chainsabres"

STRIKING_SCORPIONS = AELDARI.add_datasheet(Datasheet(
    "Striking Scorpions",
    keywords=("INFANTRY", "ASPECT WARRIORS", "STRIKING SCORPIONS"),
    composition_options=[
        [
            ModelLine(StrikingScorpionExarchProfile, 1, _EXARCH_LOADOUT, name=_EXARCH_LINE),
            ModelLine(StrikingScorpionProfile, 4, _SCORPION_LOADOUT, name="Striking Scorpion"),
        ],
        [
            ModelLine(StrikingScorpionExarchProfile, 1, _EXARCH_LOADOUT, name=_EXARCH_LINE),
            ModelLine(StrikingScorpionProfile, 9, _SCORPION_LOADOUT, name="Striking Scorpion"),
        ],
    ],
    # The Exarch's printed three weapons go together, replaced by ONE of two
    # alternatives - so both options replace the same set. They are mutually
    # exclusive by the rule's own "one of the following", and that falls out of
    # the engine for free: the Exarch line holds a single model, so the second
    # option finds no model left to claim and is trimmed, exactly as an
    # over-eager choice always is.
    wargear_options=[
        WargearOption(_EXARCH_LINE, replaces=_EXARCH_PRINTED_WEAPONS,
                      with_weapons=[BitingBladeProfile, ShurikenPistolProfile],
                      max_models=1, name=EXARCH_TO_BITING_BLADE),
        WargearOption(_EXARCH_LINE, replaces=_EXARCH_PRINTED_WEAPONS,
                      with_weapons=[ChainsabresRangedProfile, ChainsabresMeleeProfile],
                      max_models=1, name=EXARCH_TO_CHAINSABRES),
    ],
    points=AELDARI_POINTS["Striking Scorpions"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. This datasheet has no '
        'Fleet of Foot, so its Fade Back costs a token.',
        'Infiltrators (24.20), Scouts 7" (24.31/24.32) and Stealth (24.33): all three '
        'were already implemented before this datasheet existed and needed only the '
        'flags. Stealth in particular means this unit always counts as having the '
        'benefit of cover against ranged attacks.',
        'Mandiblasters: each time a model in this unit makes a melee attack, if the unit '
        'made a Charge move this turn, an unmodified Hit roll of 5+ scores a Critical Hit '
        '- see game/crit_hit.py.',
        'Aspect Shrine token: 1 per 5 models. Once per battle each, one Hit or Wound roll made for a non-CHARACTER model in this unit can be changed to an unmodified 6 - see game/aspect_shrine.py.',
    ],
))


_BANSHEE_LOADOUT = [BansheeBladeProfile, ShurikenPistolProfile]

_BANSHEE_EXARCH_LINE = "Howling Banshee Exarch"

BANSHEE_BLADE_TO_EXECUTIONER = "Exarch -> Executioner"
BANSHEE_BLADE_TO_TRISKELE = "Exarch -> Triskele"
BANSHEE_TO_MIRRORSWORDS = "Exarch -> Mirrorswords"

HOWLING_BANSHEES = AELDARI.add_datasheet(Datasheet(
    "Howling Banshees",
    keywords=("INFANTRY", "ASPECT WARRIORS", "HOWLING BANSHEES"),
    composition_options=[
        [
            ModelLine(HowlingBansheeExarchProfile, 1, _BANSHEE_LOADOUT, name=_BANSHEE_EXARCH_LINE),
            ModelLine(HowlingBansheeProfile, 4, _BANSHEE_LOADOUT, name="Howling Banshee"),
        ],
        [
            ModelLine(HowlingBansheeExarchProfile, 1, _BANSHEE_LOADOUT, name=_BANSHEE_EXARCH_LINE),
            ModelLine(HowlingBansheeProfile, 9, _BANSHEE_LOADOUT, name="Howling Banshee"),
        ],
    ],
    # Three Exarch options, and they are the reason build_squad() groups its
    # model cursors by INTERSECTING replaced sets rather than matching ones:
    # the first two give up the Banshee Blade, the third gives up the Shuriken
    # Pistol AND the Banshee Blade. All three compete for the same single
    # model, so picking more than one applies the first and trims the rest -
    # which is what "one of the following" means.
    wargear_options=[
        WargearOption(_BANSHEE_EXARCH_LINE, replaces=BansheeBladeProfile,
                      with_weapons=[ExecutionerProfile], max_models=1,
                      name=BANSHEE_BLADE_TO_EXECUTIONER),
        WargearOption(_BANSHEE_EXARCH_LINE, replaces=BansheeBladeProfile,
                      with_weapons=[TriskeleRangedProfile, TriskeleMeleeProfile], max_models=1,
                      name=BANSHEE_BLADE_TO_TRISKELE),
        WargearOption(_BANSHEE_EXARCH_LINE,
                      replaces=(ShurikenPistolProfile, BansheeBladeProfile),
                      with_weapons=[MirrorswordsProfile], max_models=1,
                      name=BANSHEE_TO_MIRRORSWORDS),
    ],
    points=AELDARI_POINTS["Howling Banshees"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. No Fleet of Foot, so this '
        'unit\'s Fade Back costs a token.',
        'Fights First: the core ability (24.13), already implemented - only the flag was '
        'needed.',
        'Acrobatic: this unit can declare a charge in a turn in which it Advanced or Fell '
        'Back. Word for word the rule Stormboyz print as "Full Throttle", so it shares '
        'that flag and game/charge.py\'s existing exception rather than adding a second '
        'copy of it.',
        'Invulnerable Save 5+, improved to 4+ against melee attacks - the conditional half '
        'is UnitProfile.invulnerable_save_vs_melee, resolved in game/invulnerable_save.py '
        'from the weapon the Save roll is being made against.',
        'Aspect Shrine token: 1 per 5 models. Once per battle each, one Hit or Wound roll '
        'made for a non-CHARACTER model in this unit can be changed to an unmodified 6 - '
        'see game/aspect_shrine.py.',
    ],
))


_WARP_SPIDER_LOADOUT = [AeldariCloseCombatWeaponA2Profile, DeathSpinnerProfile]
_WARP_SPIDER_EXARCH_LOADOUT = [AeldariCloseCombatWeaponA2Profile, ExarchsDeathSpinnerProfile]

_WARP_SPIDER_EXARCH_LINE = "Warp Spider Exarch"

WARP_SPIDER_TO_SPINNERET = "Exarch -> Spinneret Rifle + Death Weavers"
WARP_SPIDER_TO_POWERBLADES = "Exarch -> Powerblades + Death Weavers"
WARP_SPIDER_TO_POWERBLADE_ARRAY = "Exarch -> Powerblade Array"

WARP_SPIDERS = AELDARI.add_datasheet(Datasheet(
    "Warp Spiders",
    keywords=("INFANTRY", "JUMP PACK", "FLY", "ASPECT WARRIORS", "WARP SPIDERS"),
    composition_options=[
        [
            ModelLine(WarpSpiderExarchProfile, 1, _WARP_SPIDER_EXARCH_LOADOUT, name=_WARP_SPIDER_EXARCH_LINE),
            ModelLine(WarpSpiderProfile, 4, _WARP_SPIDER_LOADOUT, name="Warp Spider"),
        ],
        [
            ModelLine(WarpSpiderExarchProfile, 1, _WARP_SPIDER_EXARCH_LOADOUT, name=_WARP_SPIDER_EXARCH_LINE),
            ModelLine(WarpSpiderProfile, 9, _WARP_SPIDER_LOADOUT, name="Warp Spider"),
        ],
    ],
    # "The Warp Spider Exarch's Exarch's death spinner can be replaced with one
    # of the following" - so all three options give up the SAME single weapon,
    # and the Exarch's close combat weapon is untouched in every one of them.
    # That last point is the literal printed reading and is taken deliberately:
    # the third option ("1 powerblade array") reads as if it might swallow the
    # close combat weapon too, but the sentence only ever offers to replace the
    # death spinner. Keeping the close combat weapon alongside a melee option
    # costs nothing anyway - rule 04.01 lets a model swing with only one melee
    # weapon per activation, so the better one is simply chosen.
    wargear_options=[
        WargearOption(_WARP_SPIDER_EXARCH_LINE, replaces=ExarchsDeathSpinnerProfile,
                      with_weapons=[SpinneretRifleProfile, DeathWeaversProfile],
                      max_models=1, name=WARP_SPIDER_TO_SPINNERET),
        WargearOption(_WARP_SPIDER_EXARCH_LINE, replaces=ExarchsDeathSpinnerProfile,
                      with_weapons=[PowerbladesProfile, DeathWeaversProfile],
                      max_models=1, name=WARP_SPIDER_TO_POWERBLADES),
        WargearOption(_WARP_SPIDER_EXARCH_LINE, replaces=ExarchsDeathSpinnerProfile,
                      with_weapons=[PowerbladeArrayProfile],
                      max_models=1, name=WARP_SPIDER_TO_POWERBLADE_ARRAY),
    ],
    points=AELDARI_POINTS["Warp Spiders"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. No Fleet of Foot, so this '
        'unit\'s Fade Back costs a token.',
        'Deep Strike (24.09): already implemented, only the flag was needed.',
        'Flickerjump: an optional upgrade to a 24" Move characteristic on a Normal move, '
        'paid for with the unit\'s charge for the turn and a D6 per model at the end of '
        'the phase (each 1 is a mortal wound) - see game/flickerjump.py.',
        'Invulnerable Save 5+.',
        'Aspect Shrine token: 1 per 5 models. Once per battle each, one Hit or Wound roll '
        'made for a non-CHARACTER model in this unit can be changed to an unmodified 6 - '
        'see game/aspect_shrine.py.',
    ],
))


_DIRE_AVENGER_LOADOUT = [AeldariCloseCombatWeaponA2Profile, AvengerShurikenCatapultProfile]

_DIRE_AVENGER_EXARCH_LINE = "Dire Avenger Exarch"

DIRE_AVENGER_SHIMMERSHIELD = "Exarch -> Shimmershield (replaces the Shuriken Pistol)"


def _equip_shimmershield(token):
    """"The Dire Avenger Exarch's shuriken pistol can be replaced with 1
    shimmershield" - and the shimmershield is not a weapon, it is a defensive
    rule ("the bearer has a 4+ invulnerable save"), so it is Gear rather than a
    WargearOption.

    Gear runs AFTER the weapon swaps on the same model, which is what makes the
    printed precondition enforce itself: the Exarch only carries a Shuriken
    Pistol if one of the two weapon options put one there, so an Exarch that
    kept its Avenger Shuriken Catapult finds nothing to give up and the item
    does nothing - silently trimmed, the same convention an over-eager choice
    always gets."""
    pistol = next((w for w in token.weapons if w.name == ShurikenPistolProfile.name), None)
    if pistol is None:
        return
    token.weapons.remove(pistol)
    token.shimmershield = True   # read by game/invulnerable_save.py


DIRE_AVENGER_TO_DIRESWORD = "Exarch -> Shuriken Pistol + Diresword"
DIRE_AVENGER_TO_POWER_GLAIVE = "Exarch -> Shuriken Pistol + Power Glaive"
DIRE_AVENGER_SECOND_CATAPULT = "Exarch -> second Avenger Shuriken Catapult"

DIRE_AVENGERS = AELDARI.add_datasheet(Datasheet(
    "Dire Avengers",
    keywords=("INFANTRY", "GRENADES", "ASPECT WARRIORS", "DIRE AVENGERS"),
    composition_options=[
        [
            ModelLine(DireAvengerExarchProfile, 1, _DIRE_AVENGER_LOADOUT, name=_DIRE_AVENGER_EXARCH_LINE),
            ModelLine(DireAvengerProfile, 4, _DIRE_AVENGER_LOADOUT, name="Dire Avenger"),
        ],
        [
            ModelLine(DireAvengerExarchProfile, 1, _DIRE_AVENGER_LOADOUT, name=_DIRE_AVENGER_EXARCH_LINE),
            ModelLine(DireAvengerProfile, 9, _DIRE_AVENGER_LOADOUT, name="Dire Avenger"),
        ],
    ],
    # Three of the datasheet's four printed sentences are modelled. The two
    # weapon swaps give up the same weapon (the Exarch's Avenger shuriken
    # catapult) and are mutually exclusive for the usual reason - one model,
    # so the second finds nobody left. The third is a pure ADDITION, which is
    # why it takes no `replaces`: its printed condition ("if this unit's Exarch
    # is equipped with 1 Avenger shuriken catapult") is exactly "no swap was
    # taken", and build_squad() applies options in order, so a swap taken first
    # leaves the addition with a weapon that is no longer there to duplicate.
    #
    # The fourth sentence - "The Dire Avenger Exarch's shuriken pistol can be
    # replaced with 1 shimmershield" - is a Gear item instead (see
    # _equip_shimmershield above): it grants a defensive rule, not a weapon.
    # Its printed precondition needs no special case either. Options are
    # applied in order against the live weapon list, and a swap whose replaced
    # weapon is not present is now skipped rather than becoming a free
    # addition, so "shimmershield without first taking a swap" simply does
    # nothing - exactly what "if this unit's Exarch is equipped with" means.
    wargear_options=[
        WargearOption(_DIRE_AVENGER_EXARCH_LINE, replaces=AvengerShurikenCatapultProfile,
                      with_weapons=[ShurikenPistolProfile, DireswordProfile],
                      max_models=1, name=DIRE_AVENGER_TO_DIRESWORD),
        WargearOption(_DIRE_AVENGER_EXARCH_LINE, replaces=AvengerShurikenCatapultProfile,
                      with_weapons=[ShurikenPistolProfile, PowerGlaiveProfile],
                      max_models=1, name=DIRE_AVENGER_TO_POWER_GLAIVE),
        WargearOption(_DIRE_AVENGER_EXARCH_LINE, replaces=None,
                      with_weapons=[AvengerShurikenCatapultProfile],
                      max_models=1, name=DIRE_AVENGER_SECOND_CATAPULT),
    ],
    gear_options=[
        Gear(_DIRE_AVENGER_EXARCH_LINE, DIRE_AVENGER_SHIMMERSHIELD, _equip_shimmershield),
    ],
    gear_slots={_DIRE_AVENGER_EXARCH_LINE: 1},
    points=AELDARI_POINTS["Dire Avengers"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. No Fleet of Foot, so this '
        'unit\'s Fade Back costs a token.',
        'Bladestorm: ranged weapons equipped by models in this unit have [SUSTAINED HITS 1] '
        'while targeting an enemy unit within half range - see game/bladestorm.py.',
        'Shimmershield: the bearer has a 4+ invulnerable save. Implemented, but currently '
        'unreachable - see the wargear note in this datasheet\'s source.',
        'Invulnerable Save 5+.',
        'Aspect Shrine token: 1 per 5 models. Once per battle each, one Hit or Wound roll '
        'made for a non-CHARACTER model in this unit can be changed to an unmodified 6 - '
        'see game/aspect_shrine.py.',
    ],
))


_FIRE_DRAGON_LOADOUT = [AeldariCloseCombatWeaponA2Profile, DragonFusionGunProfile]
_FIRE_DRAGON_EXARCH_LOADOUT = [AeldariCloseCombatWeaponA2Profile, ExarchsDragonFusionGunProfile]

_FIRE_DRAGON_EXARCH_LINE = "Fire Dragon Exarch"

FIRE_DRAGON_TO_BREATH_FLAMER = "Exarch -> Dragon's Breath Flamer"
FIRE_DRAGON_TO_PISTOL_AND_AXE = "Exarch -> Dragon Fusion Pistol + Dragon Axe"
FIRE_DRAGON_TO_FIREPIKE = "Exarch -> Firepike"

FIRE_DRAGONS = AELDARI.add_datasheet(Datasheet(
    "Fire Dragons",
    keywords=("INFANTRY", "GRENADES", "ASPECT WARRIORS", "FIRE DRAGONS"),
    composition_options=[
        [
            ModelLine(FireDragonExarchProfile, 1, _FIRE_DRAGON_EXARCH_LOADOUT, name=_FIRE_DRAGON_EXARCH_LINE),
            ModelLine(FireDragonProfile, 4, _FIRE_DRAGON_LOADOUT, name="Fire Dragon"),
        ],
        [
            ModelLine(FireDragonExarchProfile, 1, _FIRE_DRAGON_EXARCH_LOADOUT, name=_FIRE_DRAGON_EXARCH_LINE),
            ModelLine(FireDragonProfile, 9, _FIRE_DRAGON_LOADOUT, name="Fire Dragon"),
        ],
    ],
    # "can be replaced with 1 of the following" - all three give up the same
    # single weapon, so they are mutually exclusive for the usual reason: the
    # Exarch line holds one model, and whichever option is applied first
    # leaves the others with nobody to claim. The close combat weapon is
    # untouched in every one of them, which is the literal printed reading.
    wargear_options=[
        WargearOption(_FIRE_DRAGON_EXARCH_LINE, replaces=ExarchsDragonFusionGunProfile,
                      with_weapons=[DragonsBreathFlamerProfile], max_models=1,
                      name=FIRE_DRAGON_TO_BREATH_FLAMER),
        WargearOption(_FIRE_DRAGON_EXARCH_LINE, replaces=ExarchsDragonFusionGunProfile,
                      with_weapons=[DragonFusionPistolProfile, DragonAxeProfile], max_models=1,
                      name=FIRE_DRAGON_TO_PISTOL_AND_AXE),
        WargearOption(_FIRE_DRAGON_EXARCH_LINE, replaces=ExarchsDragonFusionGunProfile,
                      with_weapons=[FirepikeProfile], max_models=1,
                      name=FIRE_DRAGON_TO_FIREPIKE),
    ],
    points=AELDARI_POINTS["Fire Dragons"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. No Fleet of Foot, so this '
        'unit\'s Fade Back costs a token.',
        'Assured Destruction: in your Shooting phase, a ranged attack from this unit '
        'against a MONSTER or VEHICLE unit may re-roll its Hit roll, its Wound roll and '
        'its Damage roll - see game/assured_destruction.py.',
        'Aspect Shrine token: 1 per 5 models. Once per battle each, one Hit or Wound roll '
        'made for a non-CHARACTER model in this unit can be changed to an unmodified 6 - '
        'see game/aspect_shrine.py.',
        'Invulnerable Save 5+.',
    ],
))


_FALCON_LOADOUT = [
    PulseLaserProfile, ScatterLaserProfile, TwinShurikenCatapultProfile, WraithboneHullProfile,
]

_FALCON_LINE = "Falcon"

FALCON_SCATTER_TO_MISSILE = "Scatter Laser -> Missile Launcher"
FALCON_SCATTER_TO_BRIGHT_LANCE = "Scatter Laser -> Bright Lance"
FALCON_SCATTER_TO_SHURIKEN_CANNON = "Scatter Laser -> Shuriken Cannon"
FALCON_SCATTER_TO_STARCANNON = "Scatter Laser -> Starcannon"
FALCON_CATAPULT_TO_SHURIKEN_CANNON = "Twin Shuriken Catapult -> Shuriken Cannon"

FALCON = AELDARI.add_datasheet(Datasheet(
    "Falcon",
    keywords=("VEHICLE", "TRANSPORT", "FLY", "FRAME", "FALCON"),
    model_lines=[ModelLine(FalconProfile, 1, _FALCON_LOADOUT, name=_FALCON_LINE)],
    # Two independent sentences, so two independent swaps: the scatter laser
    # has four mutually exclusive alternatives ("one of the following", and
    # they exclude each other for the usual reason - one model, so whichever
    # applies first leaves the rest with nobody to claim), and the twin
    # shuriken catapult has one of its own, which can be taken alongside any
    # of them because it gives up a different weapon.
    wargear_options=[
        WargearOption(_FALCON_LINE, replaces=ScatterLaserProfile,
                      with_weapons=[MissileLauncherStarshotProfile], max_models=1,
                      name=FALCON_SCATTER_TO_MISSILE),
        WargearOption(_FALCON_LINE, replaces=ScatterLaserProfile,
                      with_weapons=[BrightLanceProfile], max_models=1,
                      name=FALCON_SCATTER_TO_BRIGHT_LANCE),
        WargearOption(_FALCON_LINE, replaces=ScatterLaserProfile,
                      with_weapons=[ShurikenCannonProfile], max_models=1,
                      name=FALCON_SCATTER_TO_SHURIKEN_CANNON),
        WargearOption(_FALCON_LINE, replaces=ScatterLaserProfile,
                      with_weapons=[StarcannonProfile], max_models=1,
                      name=FALCON_SCATTER_TO_STARCANNON),
        WargearOption(_FALCON_LINE, replaces=TwinShurikenCatapultProfile,
                      with_weapons=[ShurikenCannonProfile], max_models=1,
                      name=FALCON_CATAPULT_TO_SHURIKEN_CANNON),
    ],
    points=AELDARI_POINTS["Falcon"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deep Strike (24.09) and Deadly Demise D3 (24.08): both core, already implemented, '
        'only the flags were needed.',
        'Damaged 1-4 wounds remaining: subtract 1 from this model\'s Hit rolls.',
        'Fire Support: after this model shoots, one enemy unit it hit is marked, and units '
        'that disembarked from it this turn may re-roll Wound rolls against that unit until '
        'the end of the turn - see game/fire_support.py.',
        'Transport: 6 AELDARI INFANTRY models, no JUMP PACK models. The printed YNNARI half '
        'of the exclusion is not modelled - this engine has no per-model faction tracking, '
        'the same documented gap the Devilfish carries.',
    ],
))


_WRAITHGUARD_LOADOUT = [WraithCloseCombatWeaponProfile, WraithcannonProfile]

_WRAITHGUARD_LINE = "Wraithguard"

WRAITHGUARD_TO_D_SCYTHE = "Wraithcannon -> D-scythe"

WRAITHGUARD = AELDARI.add_datasheet(Datasheet(
    "Wraithguard",
    keywords=("INFANTRY", "WRAITH CONSTRUCT", "WRAITHGUARD"),
    model_lines=[ModelLine(WraithguardProfile, 5, _WRAITHGUARD_LOADOUT, name=_WRAITHGUARD_LINE)],
    # "ALL of the models in this unit can EACH have their wraithcannon
    # replaced" - so it is all-or-nothing across the unit rather than a
    # per-model pick, and max_models is the whole line. Choosing fewer than 5
    # is not a legal build, but the engine has no way to express "all or none"
    # and trimming is its universal convention for an option taken the wrong
    # number of times; noted rather than left to be discovered.
    wargear_options=[
        WargearOption(_WRAITHGUARD_LINE, replaces=WraithcannonProfile,
                      with_weapons=[DScytheProfile], max_models=5,
                      name=WRAITHGUARD_TO_D_SCYTHE),
    ],
    points=AELDARI_POINTS["Wraithguard"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'War Construct: this unit is eligible to shoot in a turn in which it Fell Back - '
        'word for word the same 09.07 exception Crisis Starscythe Battlesuits print as '
        '"Battlesuit Support System", so it shares that exception in '
        'shooting.py\'s available_shooting_types().',
        'Psychic Guidance: while within 12" of a friendly AELDARI PSYKER model, this unit '
        'has Leadership 6+ and adds 1 to its Hit rolls - see game/psychic_guidance.py. '
        'Inert until an AELDARI PSYKER datasheet exists, but the condition is real and '
        'will start firing on its own when one does.',
        'WRAITH CONSTRUCT: each of these models takes up two slots inside a TRANSPORT '
        '(the Falcon prints that line).',
    ],
))


ASURMEN = AELDARI.add_datasheet(Datasheet(
    "Asurmen",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "GRENADES",
              "ASPECT WARRIOR", "PHOENIX LORD", "ASURMEN"),
    model_lines=[ModelLine(AsurmenProfile, 1, [BloodyTwinsProfile, SwordOfAsurProfile], name="Asurmen")],
    # No wargear options printed.
    points=AELDARI_POINTS["Asurmen"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader (24.22): attaches to Dire Avengers, and only to them - the legality is '
        'read off the points list\'s own LEADER line, like every other faction here.',
        'Tactical Acumen: while he leads a unit, that unit may make a 6" Normal move after '
        'it shoots, and cannot declare a charge this turn if it does - see '
        'game/tactical_acumen.py.',
        'Hand of Asuryan: once per battle, when he is selected to shoot, Bloody Twins gains '
        'Damage 3, [ANTI-INFANTRY 5+] and [DEVASTATING WOUNDS] until the end of the phase - '
        'see game/hand_of_asuryan.py.',
        'Invulnerable Save 4+.',
        'EPIC HERO is descriptive only: there is no army-building flow that could enforce '
        '"only one of these in your army" - the same documented gap The Twin Lance carries.',
    ],
))


JAIN_ZAR = AELDARI.add_datasheet(Datasheet(
    "Jain Zar",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "ASPECT WARRIOR",
              "PHOENIX LORD", "JAIN ZAR"),
    model_lines=[ModelLine(JainZarProfile, 1, [SilentDeathProfile, BladeOfDestructionProfile], name="Jain Zar")],
    # No wargear options printed.
    points=AELDARI_POINTS["Jain Zar"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'CORE: Fights First (24.13) and Leader (24.22) - both already implemented, only '
        'the flags were needed. She attaches to Howling Banshees, and only to them.',
        'Whirling Death: while she leads a unit, that unit does not roll its Advance - it '
        'gets a flat +6" to its Move characteristic for the phase instead. The printed '
        '"ignore any vertical distance" half is a no-op here, since this engine models no '
        'height at all - see game/whirling_death.py.',
        'Storm of Silence: her attacks may re-roll the Wound roll against a CHARACTER unit, '
        'in either phase - see game/storm_of_silence.py.',
        'Invulnerable Save 4+.',
        'EPIC HERO is descriptive only, the same documented gap Asurmen and The Twin Lance '
        'carry: there is no army-building flow that could enforce "only one".',
    ],
))


_WARLOCK_LOADOUT = [DestructorProfile, ShurikenPistolProfile, WitchbladeProfile]

_WARLOCK_LINE = "Warlock"

WARLOCK_WITCHBLADE_TO_SPEAR = "Witchblade -> Singing Spear"

WARLOCK_CONCLAVE = AELDARI.add_datasheet(Datasheet(
    "Warlock Conclave",
    keywords=("INFANTRY", "PSYKER", "WARLOCKS", "WARLOCK CONCLAVE"),
    # The printed composition is "2-4 Warlocks", but only 2 and 4 are priced -
    # so those are the two builds. A 3-model unit would resolve to an unknown
    # cost, which points.py deliberately reports as None rather than inventing
    # a number for.
    composition_options=[
        [ModelLine(WarlockProfile, 2, _WARLOCK_LOADOUT, name=_WARLOCK_LINE)],
        [ModelLine(WarlockProfile, 4, _WARLOCK_LOADOUT, name=_WARLOCK_LINE)],
    ],
    # "Any number of models can each have their witchblade replaced" - so the
    # cap is the whole line, per composition.
    wargear_options=[
        WargearOption(_WARLOCK_LINE, replaces=WitchbladeProfile,
                      with_weapons=[SingingSpearRangedProfile, SingingSpearMeleeProfile],
                      max_models=4, name=WARLOCK_WITCHBLADE_TO_SPEAR),
    ],
    points=AELDARI_POINTS["Warlock Conclave"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader (24.22): attaches to Guardian Defenders or Storm Guardians.',
        'Psychic Communion: each Warlock\'s Destructor gains +1 Attack and +1 Strength for '
        'each OTHER friendly AELDARI PSYKER model within 6" of that model, to a maximum of '
        '+2, computed when the unit is selected to shoot and held for the phase - see '
        'game/psychic_communion.py.',
        'Protect: while a FARSEER model leads this unit, attacks targeting it subtract 1 '
        'from the Wound roll - see game/protect.py. LIVE, and reachable two ways, both '
        'about ORDER: this unit\'s own LEADER ability is worded as a JOIN whose only '
        'printed limit is one Conclave per unit, so it may join a unit a plain Farseer '
        'already leads; and Eldrad Ulthran\'s LEADER line lets HIM join a unit this '
        'Conclave has already joined. What is not legal is a plain Farseer attaching '
        'AFTER this unit has joined - that is an ordinary 19.01 attachment and his '
        'datasheet carries no permission for it. Either way the merged unit has a '
        'FARSEER leading Warlocks, and the ability applies to all of it.',
        'Invulnerable Save 4+.',
    ],
))


_FARSEER_LOADOUT = [EldritchStormProfile, ShurikenPistolProfile, WitchbladeProfile]

_FARSEER_LINE = "Farseer"

FARSEER_WITCHBLADE_TO_SPEAR = "Witchblade -> Singing Spear"

FARSEER = AELDARI.add_datasheet(Datasheet(
    "Farseer",
    keywords=("INFANTRY", "CHARACTER", "PSYKER", "FARSEER"),
    model_lines=[ModelLine(FarseerProfile, 1, _FARSEER_LOADOUT, name=_FARSEER_LINE)],
    # Four of his five weapon rows are the Warlock Conclave's, unchanged - the
    # printed BS/WS differ (2+ against 3+) but those are the MODEL's, which
    # both weapons defer to, so the profiles are shared rather than copied.
    wargear_options=[
        WargearOption(_FARSEER_LINE, replaces=WitchbladeProfile,
                      with_weapons=[SingingSpearRangedProfile, SingingSpearMeleeProfile],
                      max_models=1, name=FARSEER_WITCHBLADE_TO_SPEAR),
    ],
    points=AELDARI_POINTS["Farseer"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader (24.22): attaches to Guardian Defenders or Storm Guardians - the same two '
        'the Warlock Conclave leads.',
        'Branching Fates: while he leads a unit, once per phase one Hit, Wound or Damage '
        'roll made for a model in it becomes an unmodified 6 - see '
        'game/branching_fates.py. The "excluding SUPPORT WEAPON models" clause is real but '
        'currently never excludes anything: no SUPPORT WEAPON datasheet exists here.',
        'Guide: at the end of his Movement phase he marks one enemy unit within 18" and '
        'visible; friendly AELDARI models add 1 to Hit rolls against it until the start of '
        'his next Command phase - see game/guide.py. The longest-lived effect in this '
        'engine, and the only one that deliberately spans the opponent\'s turn.',
        'PSYKER and FARSEER: this datasheet was expected to make Warlock Conclave\'s '
        'Protect live, the way the Conclave made Wraithguard\'s Psychic Guidance live. It '
        'does NOT - a Conclave is itself a leader unit, so this Farseer cannot be attached '
        'to it, and he prints no clause letting him join a unit one has already joined. '
        'ELDRAD ULTHRAN does print that clause, and he is the datasheet that makes Protect '
        'live - see game/protect.py.',
        'Invulnerable Save 4+.',
    ],
))


_ELDRAD_LOADOUT = [MindWarProfile, ShurikenPistolProfile, StaffOfUlthamarProfile]

_ELDRAD_LINE = "Eldrad Ulthran"

ELDRAD_ULTHRAN = AELDARI.add_datasheet(Datasheet(
    "Eldrad Ulthran",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "PSYKER", "FARSEER", "ELDRAD ULTHRAN"),
    model_lines=[ModelLine(EldradUlthranProfile, 1, _ELDRAD_LOADOUT, name=_ELDRAD_LINE)],
    # No wargear options: his printed wargear line is a flat "this model is
    # equipped with", with nothing to swap.
    points=AELDARI_POINTS["Eldrad Ulthran"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader (24.22): attaches to Guardian Defenders or Storm Guardians - AND, by the '
        'second sentence of his own LEADER line, he may join such a unit even if one '
        'WARLOCKS unit has already been attached to it. That clause is what finally makes '
        'Warlock Conclave\'s Protect reachable: Guardians + Warlock Conclave + Eldrad is a '
        'unit with a FARSEER leading Warlocks. See game/attached_units.py\'s '
        '_leader_allows_joining_led_unit().',
        'Diviner of Futures: +1 CP at the start of your Command phase while he is on the '
        'battlefield - see game/diviner_of_futures.py. Routed through gain_cp(), so the '
        'user\'s house rule of at most +1 bonus CP per battle round applies across ALL such '
        'abilities combined, not per ability.',
        'Doom (Psychic): at the end of his Movement phase he marks one enemy unit within '
        '18" and visible; friendly AELDARI models add 1 to WOUND rolls against it until the '
        'start of his next Command phase - see game/doom.py. Guide\'s twin one word apart, '
        'sharing game/psychic_mark.py - but unlike Guide it prints NO once-per-turn cap, so '
        'a unit already Guided this turn can still be Doomed.',
        'Invulnerable Save 4+.',
        'NOT modelled: the separate errata reportedly adds WARLOCK CONCLAVE to his printed '
        'leader list. Only the printed list is transcribed - see the note in '
        'game/factions/aeldari_points.py. It changes nothing Protect needs, since the '
        'LEADER-line clause above already reaches that shape.',
    ],
))


_LHYKHIS_LOADOUT = [BroodTwainProfile, SpidersFangsProfile, WeaverenderProfile]

_LHYKHIS_LINE = "Lhykhis"

LHYKHIS = AELDARI.add_datasheet(Datasheet(
    "Lhykhis",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "JUMP PACK", "FLY",
              "ASPECT WARRIOR", "PHOENIX LORD", "LHYKHIS"),
    model_lines=[ModelLine(LhykhisProfile, 1, _LHYKHIS_LOADOUT, name=_LHYKHIS_LINE)],
    # No wargear options: her printed wargear line is a flat "equipped with".
    points=AELDARI_POINTS["Lhykhis"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deep Strike (24.09) and Leader (24.22), her CORE line. She leads WARP SPIDERS and '
        'nothing else - the narrowest leader list in the faction, and the pairing her two '
        'abilities are written around.',
        'Empyric Ambush: while she leads a unit, that unit may still declare a charge in a '
        'turn in which it used Flickerjump - see game/empyric_ambush.py. The only ability '
        'here that cancels another one, so it is built by making Flickerjump skip its own '
        'charge lock rather than by ignoring the shared flag afterwards; a Lhykhis-led unit '
        'that ALSO disembarked still cannot charge.',
        'Whispering Web: after she shoots, one enemy unit she hit is marked until the end of '
        'the turn, and friendly AELDARI models score a Critical Hit against it on an '
        'unmodified 5+ - see game/whispering_web.py. Her own Brood Twain never benefits, '
        'because [TORRENT] means it makes no hit roll at all; the ability is army-wide and '
        'written for everyone else.',
        'Invulnerable Save 4+.',
        'No Aspect Shrine token: she is an ASPECT WARRIOR but her printed wargear line has '
        'no token entry, unlike the four ASPECT WARRIORS squads.',
    ],
))


_AVATAR_LOADOUT = [WailingDoomProfile, WailingDoomStrikeProfile, WailingDoomSweepProfile]

_AVATAR_LINE = "Avatar of Khaine"

AVATAR_OF_KHAINE = AELDARI.add_datasheet(Datasheet(
    "Avatar of Khaine",
    keywords=("MONSTER", "CHARACTER", "EPIC HERO", "DAEMON", "AVATAR OF KHAINE"),
    model_lines=[ModelLine(AvatarOfKhaineProfile, 1, _AVATAR_LOADOUT, name=_AVATAR_LINE)],
    # No wargear options: his printed wargear line is "equipped with: the
    # Wailing Doom", which is all three rows of the one weapon.
    points=AELDARI_POINTS["Avatar of Khaine"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deadly Demise D3 (24.08), his CORE line.',
        'The Wailing Doom is ONE weapon printed as three rows: a ranged one with '
        '[SUSTAINED HITS D3], and a melee Strike (A6/S16/AP-4/D6+2) and Sweep '
        '(A12/S8/AP-2/D2). Rule 04.01 already makes Strike-or-Sweep a choice - whichever '
        'swings locks the other out for the activation - so it needs no mode machinery.',
        '[SUSTAINED HITS D3] is the first weapon keyword here whose value is a DIE. One die '
        'per critical hit is rolled for real as a visible step, not approximated by the '
        'die\'s maximum or average - see shooting.py/fight.py\'s _begin_sustained_hits_roll().',
        'Molten Form: each attack allocated to him has its Damage characteristic halved, '
        'rounding up - see game/molten_form.py. The first halving in this engine; that '
        'module records the rounding convention, why it lands before Feel No Pain, and why '
        'mortal wounds are not halved.',
        'The Bloody-Handed (Aura): friendly AELDARI units within 6" add 1 to Advance and '
        'Charge rolls - see game/bloody_handed.py. It reaches his own unit too (he is 0" '
        'from himself), which is the printed wording taken literally: this aura prints no '
        '"excluding this unit" clause.',
        'Damaged: 1-5 Wounds Remaining - -1 to his own Hit rolls, the existing generic '
        'damaged_threshold field.',
        'Invulnerable Save 4+.',
        'No LEADER line, so he attaches to nothing and nothing attaches to him.',
    ],
))


_DARK_REAPER_LOADOUT = [AeldariCloseCombatWeaponA2Profile, ReaperLauncherStarshotProfile]

_DARK_REAPER_EXARCH_LINE = "Dark Reaper Exarch"

DARK_REAPER_TO_MISSILE_LAUNCHER = "Exarch -> Missile Launcher"
DARK_REAPER_TO_SHURIKEN_CANNON = "Exarch -> Shuriken Cannon"
DARK_REAPER_TO_TEMPEST_LAUNCHER = "Exarch -> Tempest Launcher"

DARK_REAPERS = AELDARI.add_datasheet(Datasheet(
    "Dark Reapers",
    keywords=("INFANTRY", "AELDARI", "ASPECT WARRIORS", "DARK REAPERS"),
    composition_options=[
        [
            ModelLine(DarkReaperExarchProfile, 1, _DARK_REAPER_LOADOUT, name=_DARK_REAPER_EXARCH_LINE),
            ModelLine(DarkReaperProfile, 4, _DARK_REAPER_LOADOUT, name="Dark Reaper"),
        ],
        [
            ModelLine(DarkReaperExarchProfile, 1, _DARK_REAPER_LOADOUT, name=_DARK_REAPER_EXARCH_LINE),
            ModelLine(DarkReaperProfile, 9, _DARK_REAPER_LOADOUT, name="Dark Reaper"),
        ],
    ],
    # "The Dark Reaper Exarch's Reaper launcher can be replaced with 1 of the
    # following" - three alternatives that exclude each other for the usual
    # reason: the Exarch line holds a single model, so whichever applies first
    # leaves the others with nobody to claim and they are trimmed, exactly as
    # an over-eager choice always is.
    #
    # Both of the launchers are ONE datasheet entry with two firing modes, so
    # each is a single weapon carrying an overcharge_profile rather than two
    # weapons - see game/weapons.py.
    wargear_options=[
        WargearOption(_DARK_REAPER_EXARCH_LINE, replaces=ReaperLauncherStarshotProfile,
                      with_weapons=[DarkReaperMissileLauncherStarshotProfile],
                      max_models=1, name=DARK_REAPER_TO_MISSILE_LAUNCHER),
        WargearOption(_DARK_REAPER_EXARCH_LINE, replaces=ReaperLauncherStarshotProfile,
                      with_weapons=[DarkReaperShurikenCannonProfile],
                      max_models=1, name=DARK_REAPER_TO_SHURIKEN_CANNON),
        WargearOption(_DARK_REAPER_EXARCH_LINE, replaces=ReaperLauncherStarshotProfile,
                      with_weapons=[TempestLauncherProfile],
                      max_models=1, name=DARK_REAPER_TO_TEMPEST_LAUNCHER),
    ],
    points=AELDARI_POINTS["Dark Reapers"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. This datasheet has no '
        'Fleet of Foot, so its Fade Back costs a token.',
        'Inescapable Accuracy: each time a model in this unit makes a ranged attack, you '
        'can ignore any or all modifiers to that attack\'s Ballistic Skill characteristic '
        'and any or all modifiers to the Hit roll. Word for word the permission the '
        'Riptide prints as "Weapon Support System" and rule 24.29 gives [PSYCHIC], so it '
        'shares their flag and their automatic handling - see game/shooting.py\'s '
        '_hit_modifiers().',
        'Aspect Shrine token: 1 per 5 models. Once per battle each, one Hit or Wound roll '
        'made for a non-CHARACTER model in this unit can be changed to an unmodified 6 - '
        'see game/aspect_shrine.py.',
        'Invulnerable Save 5+.',
    ],
))


_SHINING_SPEAR_LOADOUT = [LaserLanceRangedProfile, LaserLanceMeleeProfile,
                          TwinShurikenCatapultProfile]

_SHINING_SPEAR_EXARCH_LINE = "Shining Spear Exarch"

SHINING_SPEAR_TO_PARAGON_SABRE = "Exarch -> Paragon Sabre"
SHINING_SPEAR_TO_STAR_LANCE = "Exarch -> Star Lance"
SHINING_SPEAR_TO_SHURIKEN_CANNON = "Exarch -> Shuriken Cannon"
SHINING_SPEAR_SHIMMERSHIELD = "Exarch -> Shimmershield"


def _equip_spear_shimmershield(token):
    """"The Shining Spear Exarch can be equipped with 1 shimmershield" - a pure
    ADDITION here, unlike the Dire Avenger Exarch's, which gives up his Shuriken
    Pistol for it. Same defensive rule either way (4+ invulnerable save, read by
    game/invulnerable_save.py), so it is Gear rather than a WargearOption, but
    it takes nothing away."""
    token.shimmershield = True


SHINING_SPEARS = AELDARI.add_datasheet(Datasheet(
    "Shining Spears",
    keywords=("MOUNTED", "AELDARI", "FLY", "ASPECT WARRIORS", "SHINING SPEARS"),
    composition_options=[
        [
            ModelLine(ShiningSpearExarchProfile, 1, _SHINING_SPEAR_LOADOUT, name=_SHINING_SPEAR_EXARCH_LINE),
            ModelLine(ShiningSpearProfile, 2, _SHINING_SPEAR_LOADOUT, name="Shining Spear"),
        ],
        [
            ModelLine(ShiningSpearExarchProfile, 1, _SHINING_SPEAR_LOADOUT, name=_SHINING_SPEAR_EXARCH_LINE),
            ModelLine(ShiningSpearProfile, 5, _SHINING_SPEAR_LOADOUT, name="Shining Spear"),
        ],
    ],
    # Three independent printed sentences. The first two give up DIFFERENT
    # weapons, so they can be taken together; the two alternatives within the
    # first exclude each other for the one-model reason above.
    #
    # The laser lance is one printed weapon with a ranged row AND a melee row,
    # so replacing it means giving up both - which is why `replaces` is a pair.
    # The paragon sabre is melee-only (the Exarch keeps no 6" lance shot), the
    # star lance has both rows like the weapon it replaces.
    wargear_options=[
        WargearOption(_SHINING_SPEAR_EXARCH_LINE,
                      replaces=(LaserLanceRangedProfile, LaserLanceMeleeProfile),
                      with_weapons=[ParagonSabreProfile],
                      max_models=1, name=SHINING_SPEAR_TO_PARAGON_SABRE),
        WargearOption(_SHINING_SPEAR_EXARCH_LINE,
                      replaces=(LaserLanceRangedProfile, LaserLanceMeleeProfile),
                      with_weapons=[StarLanceRangedProfile, StarLanceMeleeProfile],
                      max_models=1, name=SHINING_SPEAR_TO_STAR_LANCE),
        WargearOption(_SHINING_SPEAR_EXARCH_LINE, replaces=TwinShurikenCatapultProfile,
                      with_weapons=[ShurikenCannonProfile],
                      max_models=1, name=SHINING_SPEAR_TO_SHURIKEN_CANNON),
    ],
    gear_options=[
        Gear(_SHINING_SPEAR_EXARCH_LINE, SHINING_SPEAR_SHIMMERSHIELD, _equip_spear_shimmershield),
    ],
    gear_slots={_SHINING_SPEAR_EXARCH_LINE: 1},
    points=AELDARI_POINTS["Shining Spears"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. No Fleet of Foot, so this '
        'unit\'s Fade Back costs a token.',
        'Extreme Mobility: each time this unit makes a Normal, Advance, Fall Back or '
        'Charge move, ignore any vertical distance when determining total movement '
        'distance. A NO-OP in this engine, and demonstrably so rather than by oversight: '
        'no height is modelled at all (the same reason rule 22.05 Plunging Fire does not '
        'exist here), so there is never any vertical distance to ignore. Same status as '
        'the second half of Jain Zar\'s Whirling Death.',
        'Shimmershield (Exarch wargear): the bearer has a 4+ invulnerable save, which '
        'beats the printed 5+ - see game/invulnerable_save.py.',
        'Invulnerable Save 5+.',
        'NOT an Aspect Shrine datasheet: alone among the ASPECT WARRIORS units here, its '
        'wargear options print no token entry, so it gets none.',
    ],
))


_WINDRIDER_LOADOUT = [AeldariCloseCombatWeaponA3Profile, TwinShurikenCatapultProfile]

_WINDRIDER_LINE = "Windrider"

WINDRIDER_TO_SCATTER_LASER = "Twin Shuriken Catapult -> Scatter Laser"
WINDRIDER_TO_SHURIKEN_CANNON = "Twin Shuriken Catapult -> Shuriken Cannon"

WINDRIDERS = AELDARI.add_datasheet(Datasheet(
    "Windriders",
    keywords=("MOUNTED", "AELDARI", "FLY", "WINDRIDERS"),
    composition_options=[
        [ModelLine(WindriderProfile, 3, _WINDRIDER_LOADOUT, name=_WINDRIDER_LINE)],
        [ModelLine(WindriderProfile, 6, _WINDRIDER_LOADOUT, name=_WINDRIDER_LINE)],
    ],
    # "Any number of models can each have their twin shuriken catapult
    # replaced with one of the following" - so the cap is the whole line, and
    # the two alternatives give up the SAME weapon, which is what makes them
    # share a cursor in build_squad(): pick both and they land on different
    # models rather than stacking on one.
    wargear_options=[
        WargearOption(_WINDRIDER_LINE, replaces=TwinShurikenCatapultProfile,
                      with_weapons=[ScatterLaserProfile], max_models=6,
                      name=WINDRIDER_TO_SCATTER_LASER),
        WargearOption(_WINDRIDER_LINE, replaces=TwinShurikenCatapultProfile,
                      with_weapons=[ShurikenCannonProfile], max_models=6,
                      name=WINDRIDER_TO_SHURIKEN_CANNON),
    ],
    points=AELDARI_POINTS["Windriders"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. No Fleet of Foot, so this '
        'unit\'s Fade Back costs a token.',
        'Swift Demise: each ranged attack re-rolls a Hit roll of 1, and against the '
        'CLOSEST eligible target the whole Hit roll may be re-rolled INSTEAD - one or the '
        'other, never both. See game/swift_demise.py.',
        'MOUNTED, not INFANTRY: no Dense-terrain crossing (13.06) and no Hidden (13.09).',
        'No invulnerable save - the printed statline has a 4+ armour save and nothing else.',
    ],
))


_SKYRUNNER_LOADOUT = [DestructorProfile, ShurikenPistolProfile,
                      TwinShurikenCatapultProfile, WitchbladeProfile]

_SKYRUNNER_LINE = "Warlock Skyrunner"

SKYRUNNER_WITCHBLADE_TO_SPEAR = "Witchblade -> Singing Spear"

WARLOCK_SKYRUNNERS = AELDARI.add_datasheet(Datasheet(
    "Warlock Skyrunners",
    keywords=("MOUNTED", "AELDARI", "FLY", "PSYKER", "WARLOCKS", "WARLOCK SKYRUNNERS"),
    composition_options=[
        [ModelLine(WarlockSkyrunnerProfile, 1, _SKYRUNNER_LOADOUT, name=_SKYRUNNER_LINE)],
        [ModelLine(WarlockSkyrunnerProfile, 2, _SKYRUNNER_LOADOUT, name=_SKYRUNNER_LINE)],
    ],
    # "Any number of models can each have their witchblade replaced with 1
    # singing spear" - the whole line, exactly as the foot Warlock Conclave's
    # own identical option. The Singing Spear is one printed weapon with a
    # thrown row and a melee row, so the swap grants both.
    wargear_options=[
        WargearOption(_SKYRUNNER_LINE, replaces=WitchbladeProfile,
                      with_weapons=[SingingSpearRangedProfile, SingingSpearMeleeProfile],
                      max_models=2, name=SKYRUNNER_WITCHBLADE_TO_SPEAR),
    ],
    points=AELDARI_POINTS["Warlock Skyrunners"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader: this unit JOINS one WINDRIDERS unit, with its own limit ("a unit cannot '
        'have more than one WARLOCK SKYRUNNERS unit joined to it") rather than 19.01\'s '
        'one-leader default - word for word the Warlock Conclave\'s wording, and handled '
        'by the same code (see game/attached_units.py).',
        'Runes of Battle: weapons equipped by models in this unit have the [IGNORES COVER] '
        'ability. Same effect as the unit-level Ignores Cover rule The Twin Lance prints, '
        'so it shares that flag - see game/shooting.py\'s _cover_ignored_for_group().',
        'Psychic Communion: each Warlock\'s Destructor gains +1 Attack and +1 Strength for '
        'each OTHER friendly AELDARI PSYKER model within 6" of that model, to a maximum of '
        '+2 - see game/psychic_communion.py.',
        'NOT Protect: unlike the foot Warlock Conclave, this datasheet does not print it. '
        'Checked against the printed ability list rather than inherited from its near-twin.',
        'Invulnerable Save 4+.',
    ],
))


_RANGER_LOADOUT = [AeldariCloseCombatWeaponProfile, RangerLongRifleProfile,
                   RangerShurikenPistolProfile]

RANGERS = AELDARI.add_datasheet(Datasheet(
    "Rangers",
    keywords=("INFANTRY", "AELDARI", "RANGERS"),
    composition_options=[
        [ModelLine(RangerProfile, 5, _RANGER_LOADOUT, name="Ranger")],
        [ModelLine(RangerProfile, 10, _RANGER_LOADOUT, name="Ranger")],
    ],
    # None printed - the datasheet's wargear options section reads "None".
    points=AELDARI_POINTS["Rangers"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. No Fleet of Foot, so this '
        'unit\'s Fade Back costs a token.',
        'CORE: Infiltrators (24.20) and Stealth (24.33) - both already implemented, so '
        'they needed only the flags. Stealth means this unit always counts as having the '
        'benefit of cover against ranged attacks.',
        'Path of the Outcast: in the opponent\'s Movement phase, when an enemy unit ends a '
        'move within 8" and this unit is not within Engagement Range, it may make a D6" '
        'Normal move - see game/path_of_the_outcast.py.',
        'Invulnerable Save 5+ AGAINST RANGED ATTACKS ONLY - there is no save against melee '
        'ones. Confirmed with a second lookup before being written down.',
        'The Shuriken Pistol is printed at BS2+ while the model and its Long Rifle are 3+. '
        'That is what the datasheet says, checked twice.',
    ],
))


_SHROUD_RUNNER_LOADOUT = [AeldariCloseCombatWeaponProfile, ShroudRunnerLongRifleProfile,
                          ShroudRunnerScatterLaserProfile, ShurikenPistolProfile]

SHROUD_RUNNERS = AELDARI.add_datasheet(Datasheet(
    "Shroud Runners",
    keywords=("MOUNTED", "AELDARI", "FLY", "SHROUD RUNNERS"),
    composition_options=[
        [ModelLine(ShroudRunnerProfile, 3, _SHROUD_RUNNER_LOADOUT, name="Shroud Runner")],
        [ModelLine(ShroudRunnerProfile, 6, _SHROUD_RUNNER_LOADOUT, name="Shroud Runner")],
    ],
    # None printed. "Every model equipped identically", and the Scatter Laser
    # is part of that baseline rather than an option.
    points=AELDARI_POINTS["Shroud Runners"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'CORE: Scouts 9" (24.31/24.32) - the longest Scout move in the engine - and '
        'Stealth (24.33). Both already implemented.',
        'Target Acquisition: after this unit shoots, one enemy unit hit by a LONG RIFLE '
        'attack cannot have the Benefit of Cover until the end of the phase - see '
        'game/target_acquisition.py. Unlike every other cover-bypassing source it is a '
        'mark on the TARGET, so it applies to attacks from the whole army.',
        'Its Long Rifle is NOT the Rangers\' one: same printed name, but [PRECISION] alone '
        'at BS2+ where theirs is [HEAVY] + [PRECISION] at BS3+.',
        'Invulnerable Save 5+ against ranged attacks only.',
        'MOUNTED, not INFANTRY: no Dense-terrain crossing (13.06) and no Hidden (13.09) - '
        'and, unlike the Rangers, no Infiltrators.',
    ],
))


_SWOOPING_HAWK_LOADOUT = [AeldariCloseCombatWeaponA2Profile, LasblasterProfile]
_SWOOPING_HAWK_EXARCH_LOADOUT = [AeldariCloseCombatWeaponA2Profile, HawksTalonProfile]

_SWOOPING_HAWK_EXARCH_LINE = "Swooping Hawk Exarch"

HAWK_TALON_TO_EXARCHS_LASBLASTER = "Exarch -> Exarch's Lasblaster"
HAWK_TALON_TO_SUNPISTOL_AND_SWORD = "Exarch -> Sunpistol + Power Sword"
HAWK_TALON_TO_SCATTER_LASER = "Exarch -> Scatter Laser"

SWOOPING_HAWKS = AELDARI.add_datasheet(Datasheet(
    "Swooping Hawks",
    keywords=("INFANTRY", "AELDARI", "JUMP PACK", "FLY", "GRENADES",
              "ASPECT WARRIORS", "SWOOPING HAWKS"),
    composition_options=[
        [
            ModelLine(SwoopingHawkExarchProfile, 1, _SWOOPING_HAWK_EXARCH_LOADOUT,
                      name=_SWOOPING_HAWK_EXARCH_LINE),
            ModelLine(SwoopingHawkProfile, 4, _SWOOPING_HAWK_LOADOUT, name="Swooping Hawk"),
        ],
        [
            ModelLine(SwoopingHawkExarchProfile, 1, _SWOOPING_HAWK_EXARCH_LOADOUT,
                      name=_SWOOPING_HAWK_EXARCH_LINE),
            ModelLine(SwoopingHawkProfile, 9, _SWOOPING_HAWK_LOADOUT, name="Swooping Hawk"),
        ],
    ],
    # "The Swooping Hawk Exarch's Hawk's talon can be replaced with one of the
    # following" - three alternatives that give up the same weapon, so they
    # exclude each other for the usual reason: the Exarch line holds one model,
    # and whichever applies first leaves the others with nobody to claim.
    #
    # The middle one grants TWO weapons for one, which is why with_weapons is a
    # pair - and it is the only way this datasheet gets a melee weapon beyond
    # the shared close combat one.
    wargear_options=[
        WargearOption(_SWOOPING_HAWK_EXARCH_LINE, replaces=HawksTalonProfile,
                      with_weapons=[ExarchsLasblasterProfile], max_models=1,
                      name=HAWK_TALON_TO_EXARCHS_LASBLASTER),
        WargearOption(_SWOOPING_HAWK_EXARCH_LINE, replaces=HawksTalonProfile,
                      with_weapons=[SunpistolProfile, SwoopingHawkPowerSwordProfile],
                      max_models=1, name=HAWK_TALON_TO_SUNPISTOL_AND_SWORD),
        WargearOption(_SWOOPING_HAWK_EXARCH_LINE, replaces=HawksTalonProfile,
                      with_weapons=[ScatterLaserProfile], max_models=1,
                      name=HAWK_TALON_TO_SCATTER_LASER),
    ],
    points=AELDARI_POINTS["Swooping Hawks"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py. No Fleet of Foot, so this '
        'unit\'s Fade Back costs a token.',
        'CORE: Deep Strike (24.09) - already implemented, so it needed only the flag.',
        'Grenade Pack Flyover: once per turn, in your Movement phase, on being set up or '
        'on ending a Normal, Advance or Fall Back move, roll one D6 per SWOOPING HAWKS '
        'model against an enemy unit within 8" and visible; each 4+ is 1 mortal wound, to '
        'a maximum of 6. Using it also locks the unit out of the Explosives Stratagem for '
        'the turn - see game/grenade_pack_flyover.py.',
        'Aspect Shrine token: 1 per 5 models - see game/aspect_shrine.py.',
        'Invulnerable Save 5+.',
        'INFANTRY despite the 14" move and FLY, so unlike the Aeldari jetbikes it keeps '
        'Dense-terrain crossing (13.06) and can be Hidden (13.09).',
    ],
))


_BAHARROTH_LOADOUT = [FuryOfTheTempestProfile, ShiningBladeProfile]

BAHARROTH = AELDARI.add_datasheet(Datasheet(
    "Baharroth",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "AELDARI", "JUMP PACK", "FLY",
              "GRENADES", "ASPECT WARRIOR", "PHOENIX LORD", "BAHARROTH"),
    model_lines=[ModelLine(BaharrothProfile, 1, _BAHARROTH_LOADOUT, name="Baharroth")],
    points=AELDARI_POINTS["Baharroth"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'CORE: Deep Strike (24.09) and Leader (24.22) - he leads Swooping Hawks and '
        'nothing else, which is the pairing table can_attach() reads from the points list.',
        'Cloudstrider, in two halves and NEITHER of them new machinery: at the end of the '
        'opponent\'s turn an unengaged unit he leads may withdraw into Strategic Reserves '
        '(the same move game/strategic_reserves.py already did for the Starflare Ignition '
        'System and Unshrouded Truth), and a unit he leads arriving by Deep Strike may be '
        'set up more than 6" from every enemy model but cannot charge that turn (the same '
        'override The Shortened Blade arms). See game/cloudstrider.py.',
        'Cry of the Wind: each time he is set up on the battlefield, until the end of the '
        'turn his RANGED attacks score a Critical Hit on any successful unmodified Hit '
        'roll - not a fixed number, but whatever the attack needs to hit. See '
        'game/crit_hit.py.',
        'Invulnerable Save 4+.',
    ],
))


# --- War Walkers ------------------------------------------------------------

# Two shuriken cannons, not one - "Every model is equipped with: 2 shuriken
# cannons; War Walker feet".
_WAR_WALKER_LOADOUT = [
    ShurikenCannonProfile, ShurikenCannonProfile, WarWalkerFeetProfile,
]

_WAR_WALKER_LINE = "War Walker"

WAR_WALKER_TO_MISSILE = "2x Shuriken Cannon -> 2x Missile Launcher"
WAR_WALKER_TO_BRIGHT_LANCE = "2x Shuriken Cannon -> 2x Bright Lance"
WAR_WALKER_TO_SCATTER_LASER = "2x Shuriken Cannon -> 2x Scatter Laser"
WAR_WALKER_TO_STARCANNON = "2x Shuriken Cannon -> 2x Starcannon"

WAR_WALKERS = AELDARI.add_datasheet(Datasheet(
    "War Walkers",
    keywords=("VEHICLE", "AELDARI", "WALKER", "WAR WALKERS"),
    composition_options=[
        [ModelLine(WarWalkerProfile, 1, _WAR_WALKER_LOADOUT, name=_WAR_WALKER_LINE)],
        [ModelLine(WarWalkerProfile, 2, _WAR_WALKER_LOADOUT, name=_WAR_WALKER_LINE)],
    ],
    # The printed text is per-CANNON: "each model can have EACH shuriken cannon
    # it is equipped with replaced with one of the following". A War Walker may
    # therefore end up with a MIXED pair (say one bright lance and one scatter
    # laser), and that is the one build shape this scaffold cannot express -
    # build_squad() addresses models, not individual weapon copies, and a swap
    # gives up every copy of the weapon it names.
    #
    # So the four options are written as MATCHED PAIRS: both cannons for two of
    # the same gun. All four results are legal printed builds, the default (two
    # cannons) is legal, and the symmetric loadouts are the ones actually taken
    # in play - what is lost is only the mixed pair. Deliberate and documented,
    # the same call Wraithguard's all-or-nothing note records; the alternative
    # was per-weapon-copy addressing in the scaffold, measured as reaching all
    # 55 datasheets for one build shape.
    wargear_options=[
        WargearOption(_WAR_WALKER_LINE, replaces=ShurikenCannonProfile,
                      with_weapons=[MissileLauncherStarshotProfile,
                                    MissileLauncherStarshotProfile],
                      max_models=2, name=WAR_WALKER_TO_MISSILE),
        WargearOption(_WAR_WALKER_LINE, replaces=ShurikenCannonProfile,
                      with_weapons=[BrightLanceProfile, BrightLanceProfile],
                      max_models=2, name=WAR_WALKER_TO_BRIGHT_LANCE),
        WargearOption(_WAR_WALKER_LINE, replaces=ShurikenCannonProfile,
                      with_weapons=[ScatterLaserProfile, ScatterLaserProfile],
                      max_models=2, name=WAR_WALKER_TO_SCATTER_LASER),
        WargearOption(_WAR_WALKER_LINE, replaces=ShurikenCannonProfile,
                      with_weapons=[StarcannonProfile, StarcannonProfile],
                      max_models=2, name=WAR_WALKER_TO_STARCANNON),
    ],
    points=AELDARI_POINTS["War Walkers"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Scouts 9" (24.31/24.32): core, already implemented - only the flag was needed.',
        'Crystalline Targeting: after this unit shoots, one enemy unit it hit is marked, '
        'and every friendly AELDARI attack against that unit improves its AP by 1 until '
        'the end of the phase. Each unit can only be selected once per turn - a limit on '
        'the TARGET, not on the War Walkers. See game/crystalline_targeting.py.',
        'Invulnerable Save 5+.',
    ],
))


# --- Wave Serpent -----------------------------------------------------------

_WAVE_SERPENT_LOADOUT = [
    TwinShurikenCannonProfile, TwinShurikenCatapultProfile, WraithboneHullProfile,
]

_WAVE_SERPENT_LINE = "Wave Serpent"

WAVE_SERPENT_CANNON_TO_MISSILE = "Twin Shuriken Cannon -> Twin Missile Launcher"
WAVE_SERPENT_CANNON_TO_BRIGHT_LANCE = "Twin Shuriken Cannon -> Twin Bright Lance"
WAVE_SERPENT_CANNON_TO_SCATTER_LASER = "Twin Shuriken Cannon -> Twin Scatter Laser"
WAVE_SERPENT_CANNON_TO_STARCANNON = "Twin Shuriken Cannon -> Twin Starcannon"
WAVE_SERPENT_CATAPULT_TO_SHURIKEN_CANNON = "Twin Shuriken Catapult -> Shuriken Cannon"

WAVE_SERPENT = AELDARI.add_datasheet(Datasheet(
    "Wave Serpent",
    keywords=("VEHICLE", "AELDARI", "TRANSPORT", "DEDICATED TRANSPORT",
              "FLY", "FRAME", "WAVE SERPENT"),
    model_lines=[ModelLine(WaveSerpentProfile, 1, _WAVE_SERPENT_LOADOUT,
                           name=_WAVE_SERPENT_LINE)],
    # Two independent printed sentences, so two independent swaps - the same
    # shape as the Falcon's: the turret gun has four mutually exclusive
    # alternatives (one model, so whichever lands first leaves the rest with
    # nobody to claim), and the hull gun has one of its own, takeable alongside
    # any of them because it gives up a different weapon.
    wargear_options=[
        WargearOption(_WAVE_SERPENT_LINE, replaces=TwinShurikenCannonProfile,
                      with_weapons=[TwinMissileLauncherStarshotProfile], max_models=1,
                      name=WAVE_SERPENT_CANNON_TO_MISSILE),
        WargearOption(_WAVE_SERPENT_LINE, replaces=TwinShurikenCannonProfile,
                      with_weapons=[TwinBrightLanceProfile], max_models=1,
                      name=WAVE_SERPENT_CANNON_TO_BRIGHT_LANCE),
        WargearOption(_WAVE_SERPENT_LINE, replaces=TwinShurikenCannonProfile,
                      with_weapons=[TwinScatterLaserProfile], max_models=1,
                      name=WAVE_SERPENT_CANNON_TO_SCATTER_LASER),
        WargearOption(_WAVE_SERPENT_LINE, replaces=TwinShurikenCannonProfile,
                      with_weapons=[TwinStarcannonProfile], max_models=1,
                      name=WAVE_SERPENT_CANNON_TO_STARCANNON),
        WargearOption(_WAVE_SERPENT_LINE, replaces=TwinShurikenCatapultProfile,
                      with_weapons=[ShurikenCannonProfile], max_models=1,
                      name=WAVE_SERPENT_CATAPULT_TO_SHURIKEN_CANNON),
    ],
    points=AELDARI_POINTS["Wave Serpent"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deadly Demise D3 (24.08): core, already implemented - only the flag was needed.',
        "Damaged 1-4 wounds remaining: subtract 1 from this model's Hit rolls.",
        'Wave Serpent Shield: each time a RANGED attack targets this model, if that '
        "attack's Strength is greater than this model's Toughness, subtract 1 from the "
        'Wound roll - see game/wave_serpent_shield.py. The only defender-side wound '
        'modifier here whose condition is about the attack rather than the attacker.',
        'Transport: 12 ASURYANI INFANTRY models, each WRAITH CONSTRUCT model taking the '
        'space of 2, no JUMP PACK models. The printed YNNARI half of the exclusion is not '
        'modelled - this engine has no per-model faction tracking, the same documented gap '
        'the Falcon and the Devilfish carry.',
        'Invulnerable Save 5+.',
    ],
))


# --- Fuegan -----------------------------------------------------------------

# Searsong plus the Fire Axe, and nothing to choose - the datasheet prints no
# wargear options at all, like every other Phoenix Lord here. Only the beam is
# listed: the lance is its alternate FIRING MODE (overcharge_profile), not a
# second weapon, so granting both would give him two guns.
_FUEGAN_LOADOUT = [SearsongBeamProfile, FireAxeProfile]

FUEGAN = AELDARI.add_datasheet(Datasheet(
    "Fuegan",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "AELDARI", "GRENADES",
              "ASPECT WARRIOR", "PHOENIX LORD", "FUEGAN"),
    model_lines=[ModelLine(FueganProfile, 1, _FUEGAN_LOADOUT)],
    points=AELDARI_POINTS["Fuegan"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader (24.22): this model can be attached to a Fire Dragons unit. The pairing '
        'is read off the points list\'s own LEADER line (UnitPoints.leads), like every '
        'other Phoenix Lord here.',
        'Burning Lance: while this model is leading a unit, add 6" to the Range '
        'characteristic of Melta weapons equipped by models in that unit - see '
        'game/burning_lance.py. It reaches HALF range too ([MELTA X], [RAPID FIRE X]), '
        'because half of a characteristic that has been added to is half of the new '
        'number; game/weapon_range.py is the one definition all three sites read.',
        'Unquenchable Resolve: the first time this model is destroyed, at the end of the '
        'phase roll one D6 - on a 2+ he is set back up as close as possible to where he '
        'fell, outside Engagement Range, with full wounds. See '
        'game/unquenchable_resolve.py.',
        'Invulnerable Save 4+.',
    ],
))


# --- Wraithblades -----------------------------------------------------------

_WRAITHBLADE_LOADOUT = [GhostswordsProfile]

_WRAITHBLADE_LINE = "Wraithblade"

WRAITHBLADE_TO_GHOSTAXE = "Ghostswords -> Ghostaxe + Forceshield"


def _equip_forceshield(token):
    """"All of the models in this unit can each have their ghostswords replaced
    with 1 ghostaxe AND 1 forceshield."

    ONE printed option, but half of it is a weapon swap and half is a defensive
    item, so it arrives as a WargearOption plus this Gear - exactly the split
    the Lychguard's dispersion shield and the Dire Avenger Exarch's
    shimmershield already use.

    build_squad() runs gear AFTER every weapon swap, so this simply declines to
    attach to a model that kept its ghostswords. The pairing enforces itself
    that way rather than needing a validation rule nobody would remember to
    call."""
    if not any(isinstance(w, GhostaxeProfile) for w in token.weapons):
        return
    token.forceshield = True   # read by game/invulnerable_save.py


WRAITHBLADES = AELDARI.add_datasheet(Datasheet(
    "Wraithblades",
    keywords=("INFANTRY", "AELDARI", "WRAITH CONSTRUCT", "WRAITHBLADES"),
    model_lines=[ModelLine(WraithbladeProfile, 5, _WRAITHBLADE_LOADOUT,
                           name=_WRAITHBLADE_LINE)],
    wargear_options=[
        WargearOption(_WRAITHBLADE_LINE, replaces=GhostswordsProfile,
                      with_weapons=[GhostaxeProfile],
                      max_models=5, name=WRAITHBLADE_TO_GHOSTAXE),
    ],
    gear_options=[
        # all_models=True: the printed line dresses EVERY model, not a
        # character - the same reason the Lychguard's shield needed the flag.
        Gear(_WRAITHBLADE_LINE, WRAITHBLADE_TO_GHOSTAXE, _equip_forceshield,
             all_models=True),
    ],
    gear_slots={_WRAITHBLADE_LINE: 1},
    points=AELDARI_POINTS["Wraithblades"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Malevolent Souls: each time a model in this unit is destroyed by a melee attack, '
        'if that model has not fought this phase, roll one D6. On a 3+ it is not removed - '
        'it fights after the attacking unit has finished its attacks and is then removed '
        'from play. See game/malevolent_souls.py, which shares the "dead model strikes '
        'back" ledger with Undying Spite via game/fight_after_death.py.',
        'Psychic Guidance: while this unit is within 12" of one or more friendly AELDARI '
        'PSYKER models, models in this unit have Leadership 6+ and add 1 to their Hit '
        'rolls - see game/psychic_guidance.py. The same printed ability the Wraithguard '
        'carry, and the same flag.',
        'Forceshield (wargear): the bearer has a 4+ invulnerable save. Bundled with the '
        'ghostaxe in ONE printed option - see _equip_forceshield above.',
        'WRAITH CONSTRUCT: a TRANSPORT counts each of these models as two.',
        'Led by: BONESINGER. NOT modelled - the Bonesinger is a Legends datasheet and is '
        'deliberately not built, so no leader in this engine names this unit. That '
        'direction of the pairing would live on the Bonesinger\'s own points entry '
        '(UnitPoints.leads), not here.',
    ],
))


# --- Wraithlord -------------------------------------------------------------

_WRAITHLORD_LOADOUT = [
    ShurikenCatapultProfile, ShurikenCatapultProfile, WraithboneFistsProfile,
]

_WRAITHLORD_LINE = "Wraithlord"

WRAITHLORD_CATAPULTS_TO_FLAMERS = "2x Shuriken Catapult -> 2x Flamer"
WRAITHLORD_GHOSTGLAIVE = "Add Ghostglaive"
WRAITHLORD_ADD_MISSILE = "Add Missile Launcher"
WRAITHLORD_ADD_BRIGHT_LANCE = "Add Bright Lance"
WRAITHLORD_ADD_SCATTER_LASER = "Add Scatter Laser"
WRAITHLORD_ADD_SHURIKEN_CANNON = "Add Shuriken Cannon"
WRAITHLORD_ADD_STARCANNON = "Add Starcannon"

# Three separate printed sentences, so three groups of options:
#   1. "Each of this model's shuriken catapults can be replaced with 1 flamer"
#      - per catapult, and it carries two. build_squad() addresses MODELS
#      rather than weapon copies, so this is written as the both-at-once swap,
#      the same call War Walkers records for its paired shuriken cannons.
#   2. "This model can be equipped with 1 ghostglaive" - a pure ADDITION
#      (replaces=None), and only the STRIKE profile is granted: sweep is its
#      alternate firing mode, so handing out both would be two glaives.
#   3. "up to two of the following" - five heavy weapons, each a pure addition.
#      NAMED LIMITATION: gear_slots caps Gear, not WargearOptions, so "up to
#      TWO" is not expressible here and a build can currently take all five.
#      The printed cap is recorded in abilities_text and pinned in the test as
#      a known limitation, the same treatment the Kroot Farstalkers' "one of
#      the following" and the Broadsides' "not both" already carry.
WRAITHLORD = AELDARI.add_datasheet(Datasheet(
    "Wraithlord",
    keywords=("MONSTER", "AELDARI", "WALKER", "WRAITH CONSTRUCT", "WRAITHLORD"),
    model_lines=[ModelLine(WraithlordProfile, 1, _WRAITHLORD_LOADOUT,
                           name=_WRAITHLORD_LINE)],
    wargear_options=[
        WargearOption(_WRAITHLORD_LINE, replaces=ShurikenCatapultProfile,
                      with_weapons=[AeldariFlamerProfile, AeldariFlamerProfile],
                      max_models=1, name=WRAITHLORD_CATAPULTS_TO_FLAMERS),
        WargearOption(_WRAITHLORD_LINE, replaces=None,
                      with_weapons=[GhostglaiveStrikeProfile],
                      max_models=1, name=WRAITHLORD_GHOSTGLAIVE),
        WargearOption(_WRAITHLORD_LINE, replaces=None,
                      with_weapons=[MissileLauncherStarshotProfile],
                      max_models=1, name=WRAITHLORD_ADD_MISSILE),
        WargearOption(_WRAITHLORD_LINE, replaces=None,
                      with_weapons=[BrightLanceProfile],
                      max_models=1, name=WRAITHLORD_ADD_BRIGHT_LANCE),
        WargearOption(_WRAITHLORD_LINE, replaces=None,
                      with_weapons=[ScatterLaserProfile],
                      max_models=1, name=WRAITHLORD_ADD_SCATTER_LASER),
        WargearOption(_WRAITHLORD_LINE, replaces=None,
                      with_weapons=[ShurikenCannonProfile],
                      max_models=1, name=WRAITHLORD_ADD_SHURIKEN_CANNON),
        WargearOption(_WRAITHLORD_LINE, replaces=None,
                      with_weapons=[StarcannonProfile],
                      max_models=1, name=WRAITHLORD_ADD_STARCANNON),
    ],
    points=AELDARI_POINTS["Wraithlord"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deadly Demise 1 (24.08): core, already implemented - only the value was needed.',
        'Fated Hero: at the start of the battle, select one of INFANTRY, MONSTER, MOUNTED '
        'or VEHICLE. Each time this model makes an attack against a unit with the selected '
        'keyword, re-roll a Hit roll of 1 and a Wound roll of 1 - see game/fated_hero.py.',
        'Psychic Guidance: while this model is within 12" of one or more friendly AELDARI '
        'PSYKER models, the Ballistic Skill and Weapon Skill characteristics of its weapons '
        'improve by 1 and it has Leadership 6+ - see game/psychic_guidance.py. NOTE this is '
        'the Wraithlord\'s VARIANT of the printed name: the Wraithguard/Wraithblades version '
        'adds 1 to the Hit ROLL instead, and the two are separate flags.',
        'Wargear limitation, NOT modelled: "up to two of the following" heavy weapons is a '
        'list-building cap, and a WargearOption cannot express mutual exclusivity across a '
        'group - a build can currently take more than two. Named rather than silently '
        'dropped, the same way the Kroot Farstalkers\' "one of the following" is.',
        'WRAITH CONSTRUCT: a TRANSPORT counts this model as two.',
        'Led by: BONESINGER. NOT modelled - a Legends datasheet, deliberately not built.',
    ],
))


# --- Support Weapon Platforms -----------------------------------------------
#
# Three datasheets off one chassis (SupportWeaponPlatformProfile in
# game/units.py), and the two abilities they SHARE are declared once each in
# the shared strings below - a per-datasheet copy is exactly how three sheets
# that must agree start disagreeing.

_SUPPORT_PLATFORM_SHARED_ABILITIES = [
    'Battle Focus (army rule): see game/battle_focus.py.',
    'Support Artillery: at the start of the Declare Battle Formations step this model '
    'can join one GUARDIAN DEFENDERS unit from your army (a unit cannot have more than '
    'one SUPPORT WEAPON model joined to it); it then counts as part of that unit for '
    'the rest of the battle and increases its Starting Strength. This is the SUPPORT '
    'attachment role (24.34) - the pairing is read off the points list\'s own '
    'UnitPoints.supports, exactly like a LEADER line.',
    'Support Artillery, second sentence: this model, and any unit it is joined to, '
    'cannot embark within a TRANSPORT - see game/transport.py\'s can_embark(). Both '
    'halves fall out of one per-model test, because 19.01 merges the platform into the '
    'Guardians\' own Squad.models.',
    'Support Weapon: each time an attack targets this model\'s unit, if that unit '
    'contains one or more other models, until that attack is resolved this model has '
    'Toughness 3 - folded into game/squad.py\'s attached_unit_toughness(), beside the '
    'Gretchin Runtherd override that answers the same question. A platform standing '
    'alone keeps its printed T6, unprompted.',
]

_D_CANNON_LOADOUT = [DCannonProfile, ShurikenCatapultProfile,
                     AeldariCloseCombatWeaponA2Profile]
_SHADOW_WEAVER_LOADOUT = [ShadowWeaverProfile, ShurikenCatapultProfile,
                          AeldariCloseCombatWeaponA2Profile]
_VIBRO_CANNON_LOADOUT = [VibroCannonProfile, ShurikenCatapultProfile,
                         AeldariCloseCombatWeaponA2Profile]

D_CANNON_PLATFORM = AELDARI.add_datasheet(Datasheet(
    "D-cannon Platform",
    keywords=("INFANTRY", "AELDARI", "FRAME", "SUPPORT WEAPON", "D-CANNON PLATFORM"),
    model_lines=[ModelLine(DCannonPlatformProfile, 1, _D_CANNON_LOADOUT,
                           name="D-cannon Platform")],
    points=AELDARI_POINTS["D-cannon Platform"],
    abilities_text=_SUPPORT_PLATFORM_SHARED_ABILITIES + [
        'Structural Collapse: each time this model makes an attack with its D-cannon, '
        're-roll a Damage roll of 1 - MANDATORY (the text has no "you can"), so it is '
        'resolved without a prompt. See game/structural_collapse.py.',
        'Structural Collapse, second clause: "if that attack targets a TITANIC unit, you '
        'can re-roll the Damage roll instead" is a BELIEVED NO-OP - no built datasheet '
        'carries TITANIC. Written out rather than dropped, like rapid_ingress.py\'s '
        'AIRCRAFT carve-out.',
    ],
))

SHADOW_WEAVER_PLATFORM = AELDARI.add_datasheet(Datasheet(
    "Shadow Weaver Platform",
    keywords=("INFANTRY", "AELDARI", "FRAME", "SUPPORT WEAPON", "SHADOW WEAVER PLATFORM"),
    model_lines=[ModelLine(ShadowWeaverPlatformProfile, 1, _SHADOW_WEAVER_LOADOUT,
                           name="Shadow Weaver Platform")],
    points=AELDARI_POINTS["Shadow Weaver Platform"],
    abilities_text=_SUPPORT_PLATFORM_SHARED_ABILITIES + [
        'Monofilament Snare: in your Shooting phase, after this model has shot, select '
        'one enemy unit hit by one or more of those attacks made with its shadow weaver. '
        'Until the start of your next turn that unit is snared, and each time it makes a '
        'Normal, Advance or Fall Back move it rolls one D6 per model and suffers 1 mortal '
        'wound for each 1. See game/monofilament_snare.py.',
    ],
))

VIBRO_CANNON_PLATFORM = AELDARI.add_datasheet(Datasheet(
    "Vibro Cannon Platform",
    keywords=("INFANTRY", "AELDARI", "FRAME", "SUPPORT WEAPON", "VIBRO CANNON PLATFORM"),
    model_lines=[ModelLine(VibroCannonPlatformProfile, 1, _VIBRO_CANNON_LOADOUT,
                           name="Vibro Cannon Platform")],
    points=AELDARI_POINTS["Vibro Cannon Platform"],
    abilities_text=_SUPPORT_PLATFORM_SHARED_ABILITIES + [
        'Sonic Destruction: in your Shooting phase, each time this model attacks with its '
        'vibro cannon, improve the Strength, Armour Penetration and Damage of that attack '
        'by 1 for each OTHER friendly VIBRO CANNON PLATFORM model that attacked the same '
        'enemy unit with its vibro cannon this phase. See game/sonic_destruction.py.',
    ],
))


# --- Fire Prism / Night Spinner ---------------------------------------------
#
# One hull (AeldariGunTankProfile in game/units.py), two guns. Both print the
# same single wargear line, so that is shared too.

_FIRE_PRISM_LOADOUT = [PrismCannonDispersedPulseProfile,
                       TwinShurikenCatapultProfile, WraithboneHullProfile]
_NIGHT_SPINNER_LOADOUT = [DoomweaverProfile,
                          TwinShurikenCatapultProfile, WraithboneHullProfile]

_FIRE_PRISM_LINE = "Fire Prism"
_NIGHT_SPINNER_LINE = "Night Spinner"

FIRE_PRISM_CATAPULT_TO_CANNON = "Twin Shuriken Catapult -> Shuriken Cannon"
NIGHT_SPINNER_CATAPULT_TO_CANNON = "Twin Shuriken Catapult -> Shuriken Cannon"

FIRE_PRISM = AELDARI.add_datasheet(Datasheet(
    "Fire Prism",
    keywords=("VEHICLE", "AELDARI", "FLY", "FRAME", "FIRE PRISM"),
    model_lines=[ModelLine(FirePrismProfile, 1, _FIRE_PRISM_LOADOUT,
                           name=_FIRE_PRISM_LINE)],
    wargear_options=[
        WargearOption(_FIRE_PRISM_LINE, replaces=TwinShurikenCatapultProfile,
                      with_weapons=[ShurikenCannonProfile],
                      max_models=1, name=FIRE_PRISM_CATAPULT_TO_CANNON),
    ],
    points=AELDARI_POINTS["Fire Prism"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deadly Demise D3 (24.08): core, already implemented.',
        'Damaged 1-4 wounds remaining: -1 to this model\'s Hit rolls - the shared '
        'bracket every damaged vehicle here uses.',
        'Crystal Matrix: each time this model is selected to shoot, you can re-roll one '
        'Hit roll AND one Wound roll. One use of EACH, where the gunships\' Targeting '
        'Array is one use of EITHER - the two share game/activation_reroll.py and differ '
        'only in that word. See game/crystal_matrix.py.',
        'Prism cannon: ONE datasheet entry with two firing profiles. Only the dispersed '
        'pulse is granted; focused lances is its alternate firing mode, so handing out '
        'both would give the tank two cannons.',
        '[LINKED FIRE] on the focused lances is NOT modelled. The keyword reads: "when '
        'selecting targets for this weapon, you can measure range and determine '
        'visibility from another friendly FIRE PRISM model that is visible to the '
        'bearer; when doing so, this weapon has an Attacks characteristic of 1." That '
        're-bases range AND line of sight onto a different model, which every targeting '
        'test in game/shooting.py measures from the firing model - a targeting-layer '
        'change rather than a weapon flag, and one that needs a SECOND Fire Prism on the '
        'board before it can do anything. Named rather than silently dropped.',
    ],
))

NIGHT_SPINNER = AELDARI.add_datasheet(Datasheet(
    "Night Spinner",
    keywords=("VEHICLE", "AELDARI", "FLY", "FRAME", "NIGHT SPINNER"),
    model_lines=[ModelLine(NightSpinnerProfile, 1, _NIGHT_SPINNER_LOADOUT,
                           name=_NIGHT_SPINNER_LINE)],
    wargear_options=[
        WargearOption(_NIGHT_SPINNER_LINE, replaces=TwinShurikenCatapultProfile,
                      with_weapons=[ShurikenCannonProfile],
                      max_models=1, name=NIGHT_SPINNER_CATAPULT_TO_CANNON),
    ],
    points=AELDARI_POINTS["Night Spinner"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deadly Demise D3 (24.08): core, already implemented.',
        'Damaged 1-4 wounds remaining: -1 to this model\'s Hit rolls.',
        'Monofilament Web: in your Shooting phase, after this model has shot, any enemy '
        'unit its doomweaver hit is PINNED until the start of your next turn - subtract 2 '
        'from its Move characteristic and 2 from Charge rolls made for it. NOT from '
        'Advance rolls: that is the one clause separating "pinned" from Mont\'ka\'s '
        '"shaken", and the two stack. See game/monofilament_web.py.',
    ],
))


# --- Vypers -----------------------------------------------------------------

_VYPER_LOADOUT = [ShurikenCannonProfile, BrightLanceProfile, WraithboneHullProfile]

_VYPER_LINE = "Vyper"

VYPER_LANCE_TO_SCATTER_LASER = "Bright Lance -> Scatter Laser"
VYPER_LANCE_TO_STARCANNON = "Bright Lance -> Starcannon"
VYPER_CANNON_TO_MISSILE = "Shuriken Cannon -> Missile Launcher"

VYPERS = AELDARI.add_datasheet(Datasheet(
    "Vypers",
    keywords=("VEHICLE", "AELDARI", "FLY", "VYPERS"),
    composition_options=[
        [ModelLine(VyperProfile, 1, _VYPER_LOADOUT, name=_VYPER_LINE)],
        [ModelLine(VyperProfile, 2, _VYPER_LOADOUT, name=_VYPER_LINE)],
    ],
    # Two independent printed sentences, so two groups of options: the bright
    # lance becomes one of two guns, and the shuriken cannon independently
    # becomes a missile launcher. They replace DIFFERENT weapons, so a model
    # can take one from each - which is what "any number of models can each"
    # means twice over.
    wargear_options=[
        WargearOption(_VYPER_LINE, replaces=BrightLanceProfile,
                      with_weapons=[VyperScatterLaserProfile],
                      max_models=2, name=VYPER_LANCE_TO_SCATTER_LASER),
        WargearOption(_VYPER_LINE, replaces=BrightLanceProfile,
                      with_weapons=[VyperStarcannonProfile],
                      max_models=2, name=VYPER_LANCE_TO_STARCANNON),
        WargearOption(_VYPER_LINE, replaces=ShurikenCannonProfile,
                      with_weapons=[MissileLauncherStarshotProfile],
                      max_models=2, name=VYPER_CANNON_TO_MISSILE),
    ],
    points=AELDARI_POINTS["Vypers"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deadly Demise 1 (24.08): core, already implemented.',
        'Harassment Fire: in your Shooting phase, after this unit has shot, select one '
        'enemy unit hit by one or more of those attacks; until the start of your next '
        'turn it is SUPPRESSED and subtracts 1 from its Hit rolls. The same status the '
        'T\'au Strike Team\'s Suppression Volley applies, so it is written into the same '
        'ledger (game/suppression.py) - with two printed differences: no INFANTRY '
        'restriction, and no "while this unit is on the battlefield" clause, so it '
        'outlives the Vypers that applied it.',
        'The Vypers\' scatter laser prints [SUSTAINED HITS 2] where every other carrier '
        'of that row prints 1, and their starcannon prints BS2+ where their five other '
        'weapon rows print 3+. Both transcribed as printed and pinned, because both look '
        'like typos beside the rest of the sheet.',
    ],
))


# --- The three standalone Asuryani psykers ----------------------------------

_LONE_WARLOCK_LOADOUT = [DestructorProfile, ShurikenPistolProfile, WitchbladeProfile]
_LONE_WARLOCK_LINE = "Warlock"
LONE_WARLOCK_WITCHBLADE_TO_SPEAR = "Witchblade -> Singing Spear"

WARLOCK = AELDARI.add_datasheet(Datasheet(
    "Warlock",
    keywords=("INFANTRY", "CHARACTER", "AELDARI", "PSYKER", "WARLOCK"),
    model_lines=[ModelLine(LoneWarlockProfile, 1, _LONE_WARLOCK_LOADOUT,
                           name=_LONE_WARLOCK_LINE)],
    wargear_options=[
        WargearOption(_LONE_WARLOCK_LINE, replaces=WitchbladeProfile,
                      with_weapons=[SingingSpearRangedProfile, SingingSpearMeleeProfile],
                      max_models=1, name=LONE_WARLOCK_WITCHBLADE_TO_SPEAR),
    ],
    points=AELDARI_POINTS["Warlock"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Support (24.34): this model can be attached to a Guardian Defenders or Storm '
        'Guardians unit. The pairing is read off the points list\'s UnitPoints.supports.',
        'Runes of Fortune: each time an enemy unit declares a charge, if one or more '
        'units with this ability are among its targets, subtract 2 from the Charge roll - '
        'see game/runes_of_fortune.py. The first DEFENDER-side term in that fold; the '
        'other three (Photon Grenades, shaken, pinned) all belong to the charging unit.',
        'Psychic Communion: the same ability the Warlock Conclave prints, and the same '
        'flag - see game/psychic_communion.py.',
        'NOT the Warlock Conclave\'s model, despite the shared statline: that datasheet '
        'prints PROTECT and this one prints RUNES OF FORTUNE, and this one attaches as an '
        'ordinary SUPPORT model where the Conclave\'s line is a JOIN that occupies no '
        'leader slot. LoneWarlockProfile inherits the statline and switches those off.',
        'Invulnerable Save 4+.',
    ],
))


_SPIRITSEER_LOADOUT = [ShurikenPistolProfile, WitchStaffProfile]

SPIRITSEER = AELDARI.add_datasheet(Datasheet(
    "Spiritseer",
    keywords=("INFANTRY", "CHARACTER", "AELDARI", "PSYKER", "SPIRITSEER"),
    model_lines=[ModelLine(SpiritseerProfile, 1, _SPIRITSEER_LOADOUT,
                           name="Spiritseer")],
    points=AELDARI_POINTS["Spiritseer"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Stealth (24.33): core, already implemented - only the flag was needed.',
        'Spiritseer: while within 3" of one or more friendly WRAITH CONSTRUCT units, this '
        'model has Lone Operative (24.24) - the SECOND conditional grant of that ability, '
        'after Illuminor Szeras, and it needed no new seam because his made '
        'game/status_effects.py ask a module rather than read a printed value.',
        'Spirit Mark: once per turn in your Movement phase, when this model starts or ends '
        'a move, one friendly WRAITH CONSTRUCT unit within 6" gains [SUSTAINED HITS 1] '
        'against one visible enemy unit, until the start of your next Movement phase. A '
        'PAIR rather than a mark - see game/spiritseer.py.',
        'Tears of Isha: in your Command phase, one friendly WRAITH CONSTRUCT unit within '
        '6" either returns one destroyed model or heals D3 wounds. The two branches are '
        'NOT a free choice: "otherwise" makes the heal what happens when there is nothing '
        'to return. See game/spiritseer.py.',
        'No LEADER or SUPPORT line at all: it stands alone, and reaches wraith units by '
        'RANGE rather than by attachment.',
        'Invulnerable Save 4+.',
    ],
))


_FARSEER_SKYRUNNER_LOADOUT = [EldritchStormProfile, ShurikenPistolProfile,
                              TwinShurikenCatapultProfile, WitchbladeProfile]
_FARSEER_SKYRUNNER_LINE = "Farseer Skyrunner"
FARSEER_SKYRUNNER_WITCHBLADE_TO_SPEAR = "Witchblade -> Singing Spear"

FARSEER_SKYRUNNER = AELDARI.add_datasheet(Datasheet(
    "Farseer Skyrunner",
    keywords=("MOUNTED", "CHARACTER", "AELDARI", "FLY", "PSYKER", "FARSEER",
              "FARSEER SKYRUNNER"),
    model_lines=[ModelLine(FarseerSkyrunnerProfile, 1, _FARSEER_SKYRUNNER_LOADOUT,
                           name=_FARSEER_SKYRUNNER_LINE)],
    wargear_options=[
        WargearOption(_FARSEER_SKYRUNNER_LINE, replaces=WitchbladeProfile,
                      with_weapons=[SingingSpearRangedProfile, SingingSpearMeleeProfile],
                      max_models=1, name=FARSEER_SKYRUNNER_WITCHBLADE_TO_SPEAR),
    ],
    points=AELDARI_POINTS["Farseer Skyrunner"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader (24.22): this model can be attached to a Windriders unit - which is also '
        'the only unit the Warlock Skyrunner can join, so a Windrider squad can end up '
        'with both.',
        'Branching Fates: the same ability the foot Farseer prints, and the same flag - '
        'see game/branching_fates.py.',
        'Misfortune: at the end of your Movement phase, one enemy unit within 18" and '
        'visible subtracts 1 from ITS OWN Wound rolls until the start of your next Command '
        'phase. The THIRD psychic mark of Guide and Doom\'s shape, and the first read from '
        'the attacker\'s side rather than the target\'s - see game/misfortune.py.',
        'MOUNTED, so it takes the 45 mm table size the other three jetbike datasheets '
        'share rather than its printed 32 mm.',
        'Invulnerable Save 4+.',
    ],
))


# --- Autarchs and Maugan Ra -------------------------------------------------
#
# The two Autarchs print the SAME wargear menus, so the loadout, the option
# names and the two swap groups are shared here rather than written twice.

_AUTARCH_LOADOUT = [ShurikenPistolProfile, StarGlaiveProfile]

AUTARCH_PISTOL_TO_DEATH_SPINNER = "Shuriken Pistol -> Death Spinner"
AUTARCH_PISTOL_TO_FUSION_GUN = "Shuriken Pistol -> Dragon Fusion Gun"
AUTARCH_PISTOL_TO_FUSION_PISTOL = "Shuriken Pistol -> Dragon Fusion Pistol"
AUTARCH_PISTOL_TO_REAPER = "Shuriken Pistol -> Reaper Launcher"
AUTARCH_GLAIVE_TO_BANSHEE_BLADE = "Star Glaive -> Banshee Blade"
AUTARCH_GLAIVE_TO_CHAINSWORD = "Star Glaive -> Scorpion Chainsword"


def _autarch_wargear(line):
    """The two printed sentences, as six options. Both are "one of the
    following", and the two groups replace DIFFERENT weapons - so a model takes
    one from each, and the options within a group are mutually exclusive
    because they all give up the same weapon."""
    return [
        WargearOption(line, replaces=ShurikenPistolProfile,
                      with_weapons=[DeathSpinnerProfile],
                      max_models=1, name=AUTARCH_PISTOL_TO_DEATH_SPINNER),
        WargearOption(line, replaces=ShurikenPistolProfile,
                      with_weapons=[DragonFusionGunProfile],
                      max_models=1, name=AUTARCH_PISTOL_TO_FUSION_GUN),
        WargearOption(line, replaces=ShurikenPistolProfile,
                      with_weapons=[DragonFusionPistolProfile],
                      max_models=1, name=AUTARCH_PISTOL_TO_FUSION_PISTOL),
        WargearOption(line, replaces=ShurikenPistolProfile,
                      with_weapons=[AutarchReaperLauncherStarshotProfile],
                      max_models=1, name=AUTARCH_PISTOL_TO_REAPER),
        WargearOption(line, replaces=StarGlaiveProfile,
                      with_weapons=[AutarchBansheeBladeProfile],
                      max_models=1, name=AUTARCH_GLAIVE_TO_BANSHEE_BLADE),
        WargearOption(line, replaces=StarGlaiveProfile,
                      with_weapons=[AutarchScorpionChainswordProfile],
                      max_models=1, name=AUTARCH_GLAIVE_TO_CHAINSWORD),
    ]


AUTARCH = AELDARI.add_datasheet(Datasheet(
    "Autarch",
    keywords=("INFANTRY", "CHARACTER", "AELDARI", "GRENADES", "AUTARCH"),
    model_lines=[ModelLine(AutarchProfile, 1, _AUTARCH_LOADOUT, name="Autarch")],
    wargear_options=_autarch_wargear("Autarch"),
    points=AELDARI_POINTS["Autarch"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader (24.22): the widest LEADER line in the faction - seven datasheets. '
        'Note the printed line says "DARK REAPER" in the singular; the datasheet is '
        '"Dark Reapers", and `leads` takes datasheet names.',
        'Aspect Training: while leading HOWLING BANSHEES it has Fights First; while '
        'leading STRIKING SCORPIONS it has Infiltrators, Scouts 7" and Stealth. ALL FOUR '
        'ARE BELIEVED NO-OPS here, and that is MEASURED rather than assumed - both units '
        'already print every ability they are granted (the Scorpions\' own CORE line is '
        'Infiltrators, Scouts 7", Stealth), and this engine\'s 19.04 already stops a '
        'joining character from stripping a bodyguard component\'s abilities, which is '
        'the breakage the printed ability exists to prevent. Kept as predicates so that '
        'a future tightening is one wiring change - see game/aspect_training.py, which '
        'also names the wider Scouts reading and why the narrow one is used.',
        'Superlative Strategist: while leading a unit, you can re-roll its Advance rolls. '
        'See game/superlative_strategist.py. Its SECOND clause - re-rolling "any rolls '
        'made for that unit while it is performing an Agile Manoeuvre" - is NOT modelled: '
        'the six manoeuvres resolve without a dice step of their own, so there is no roll '
        'for it to attach to.',
        'Path of Command: once per battle round, a Stratagem used on this model\'s unit '
        'costs 1CP less - the FOURTH datasheet in this engine to print that exact '
        'sentence, and the one that paid for extracting it into game/cp_discount.py.',
        'Its Banshee Blade (A5), Scorpion Chainsword (A7) and Reaper Launcher (S4 '
        'starswarm, and [HEAVY] on both modes) print DIFFERENT numbers from the Aspect '
        'Warriors\' own rows, so each has its own class that inherits the shared one.',
        'Invulnerable Save 4+.',
    ],
))

AUTARCH_WAYLEAPER = AELDARI.add_datasheet(Datasheet(
    "Autarch Wayleaper",
    keywords=("INFANTRY", "CHARACTER", "AELDARI", "JUMP PACK", "FLY", "GRENADES",
              "AUTARCH WAYLEAPER"),
    model_lines=[ModelLine(AutarchWayleaperProfile, 1, _AUTARCH_LOADOUT,
                           name="Autarch Wayleaper")],
    wargear_options=_autarch_wargear("Autarch Wayleaper"),
    points=AELDARI_POINTS["Autarch Wayleaper"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Deep Strike (24.09) and Leader (24.22): core, already implemented.',
        'Indomitable Strength of Will: while leading a unit, each Battle Focus token '
        'SPENT to let that unit perform an Agile Manoeuvre is refunded on a 3+. Fed from '
        'game/battle_focus.py\'s own spend, on the PAID path only - a refund hung on '
        '"performed a manoeuvre" would print tokens out of Fleet of Foot\'s free ones. '
        'See game/indomitable_strength_of_will.py.',
        'Path of Command: the same ability the Autarch prints, and "one model from your '
        'army" means the two share ONE use per battle round.',
        'NOT a subclass of the Autarch\'s profile: they share a statline in everything '
        'but Movement, and all three of their named abilities differ, so inheriting '
        'would switch off more than it kept.',
        'Invulnerable Save 4+.',
    ],
))


_MAUGAN_RA_LOADOUT = [MaugetarRangedProfile, MaugetarMeleeProfile]

MAUGAN_RA = AELDARI.add_datasheet(Datasheet(
    "Maugan Ra",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "AELDARI", "ASPECT WARRIOR",
              "PHOENIX LORD", "MAUGAN RA"),
    model_lines=[ModelLine(MauganRaProfile, 1, _MAUGAN_RA_LOADOUT, name="Maugan Ra")],
    points=AELDARI_POINTS["Maugan Ra"],
    abilities_text=[
        'Battle Focus (army rule): see game/battle_focus.py.',
        'Leader (24.22): this model can be attached to a Dark Reapers unit - the reverse '
        'gap that datasheet has carried since it was built.',
        'Harvester of Souls: while leading a unit, if every one of that unit\'s attacks '
        'targets the SAME enemy unit, roll a D6 for that unit and for every other enemy '
        'unit within 3" of it; each 5+ suffers D3 mortal wounds after the attacks '
        'resolve. The printed cost is giving up Split Fire entirely. See '
        'game/harvester_of_souls.py, which also names the one timing simplification.',
        'Face of Death: after this model shoots, one enemy unit it hit must take a '
        'Battle-shock test at -1 - a FORCED test ("must take"), through the same '
        'start_forced_roll() entry Neocapacitor Shields opened. See game/face_of_death.py.',
        'Maugetar is ONE printed weapon with a ranged row and a melee row, so both are '
        'granted - the same shape as the Star Lance and the Singing Spear, and not a '
        'duplicate.',
        'No wargear options at all, like every other Phoenix Lord here.',
        'Invulnerable Save 4+.',
    ],
))


# --- Exodites ---------------------------------------------------------------
#
# Four datasheets on one drakesteed (ExoditeProfile in game/units.py). The
# Drakesteed Fangs and Talons is on all four; the Solar Carbine on three.

_EXODITE_SHARED_ABILITIES = [
    'Battle Focus (army rule): see game/battle_focus.py.',
    'MOUNTED and MOBILE, on a 75 x 42 mm oval converted to an equal-area circle - '
    'the same conversion the Ghostkeel, Riptide and Warp Spiders already use.',
    'Drakesteed Fangs and Talons is [EXTRA ATTACKS] (24.11), so it never competes '
    'with the rider\'s own weapon under 04.01.',
]

_DRAGON_KNIGHT_LOADOUT = [DrakesteedFangsAndTalonsProfile, LaserLanceRangedProfile,
                          ExoditeLaserLanceMeleeProfile, SolarCarbineProfile]

DRAGON_KNIGHTS = AELDARI.add_datasheet(Datasheet(
    "Dragon Knights",
    keywords=("MOUNTED", "AELDARI", "EXODITE", "MOBILE"),
    composition_options=[
        [ModelLine(DragonKnightProfile, 3, _DRAGON_KNIGHT_LOADOUT, name="Dragon Knight")],
        [ModelLine(DragonKnightProfile, 6, _DRAGON_KNIGHT_LOADOUT, name="Dragon Knight")],
    ],
    points=AELDARI_POINTS["Dragon Knights"],
    abilities_text=_EXODITE_SHARED_ABILITIES + [
        'On the Hunt: a Fall Back move does not stop this unit being eligible to shoot '
        'or to declare a charge - the FOURTH printed wording of that exception, after '
        'Battlesuit Support System, War Construct and Agile Combatant, and it joins them '
        'at the same two gates rather than opening a fifth.',
        'Agile Reach: when this unit is selected to fight, melee weapons on UNENGAGED '
        'models within 3" of an enemy unit the unit is already engaged with can target '
        'that enemy. It widens 12.02 for the back rank only - it cannot bring a wholly '
        'disengaged unit into a fight. See game/agile_reach.py.',
        'Drakolithe: once per battle per token, when an enemy unit ends a move within 8", '
        'roll a D6 - on a 3+ it suffers 1 mortal wound. NO move-type filter, unlike the '
        'Shadow Weaver\'s snare: the printed text names none, so a Charge counts. See '
        'game/drakolithe.py.',
        'Wargear: "for every 3 models in this unit, this unit can be equipped with 2 '
        'Drakolithe" - a per-UNIT token count rather than a weapon, so it is set on the '
        'squad at build time (Squad.drakolithe_tokens) rather than as a WargearOption.',
        'Its Laser Lance shares the Shining Spears\' RANGED row exactly, and needs its own '
        'MELEE row: S6 against their S5, and no [ANTI-MONSTER/VEHICLE].',
    ],
))


_CLANBLADE_LOADOUT = [DrakesteedFangsAndTalonsProfile, MoonbladesProfile,
                      SolarCarbineProfile]

CLANBLADE = AELDARI.add_datasheet(Datasheet(
    "Clanblade",
    keywords=("MOUNTED", "AELDARI", "CHARACTER", "EXODITE", "MOBILE"),
    model_lines=[ModelLine(ClanbladeProfile, 1, _CLANBLADE_LOADOUT, name="Clanblade")],
    points=AELDARI_POINTS["Clanblade"],
    abilities_text=_EXODITE_SHARED_ABILITIES + [
        'Leader (24.22): this model can be attached to a Dragon Knights unit.',
        'Ld6+ where the other three Exodites print 7+ - the ONE characteristic that '
        'differs from the shared chassis.',
        'Blade of the Clans: this unit\'s melee attacks have [SUSTAINED HITS 1] - the '
        'third grant of that keyword here, and the only one with no leader clause and no '
        'range. See game/blade_of_the_clans.py.',
        'Cornered Prey: an enemy engaged with this unit that falls back MUST use Desperate '
        'Escape, and takes -1 on those hazard rolls if it is battle-shocked. The two '
        'clauses stack rather than overlap - the first forces the mode on a unit that is '
        'NOT battle-shocked and would otherwise choose Ordered Retreat. See '
        'game/cornered_prey.py.',
    ],
))


_LEYSTALKER_LOADOUT = [DrakesteedFangsAndTalonsProfile, ExoditeLongRifleProfile,
                       HuntingBladesProfile]

LEYSTALKER = AELDARI.add_datasheet(Datasheet(
    "Leystalker",
    keywords=("MOUNTED", "AELDARI", "CHARACTER", "EXODITE", "MOBILE"),
    model_lines=[ModelLine(LeystalkerProfile, 1, _LEYSTALKER_LOADOUT, name="Leystalker")],
    points=AELDARI_POINTS["Leystalker"],
    abilities_text=_EXODITE_SHARED_ABILITIES + [
        'Lone Operative (24.24), Scouts 9" (24.31) and Stealth (24.33): core, already '
        'implemented - and PRINTED OUTRIGHT here, unlike the Spiritseer\'s conditional '
        'Lone Operative grant.',
        'Panicked Quarry: after this unit shoots, one non-MONSTER/VEHICLE unit it hit '
        'takes a Battle-shock test at -1. Maugan Ra\'s Face of Death prints the same '
        'sentence WITHOUT that exclusion, and the two share '
        'game/battle_shock_after_shooting.py.',
        'Drakolithe: the same ability the Dragon Knights carry, and it prints TWO tokens '
        'on its own wargear line rather than buying them.',
        'Its Long Rifle prints "DEVASTATING WOUNDS: non-MONSTER/VEHICLE" - the first '
        'CONDITIONAL grant of that keyword here, applied against the real target in the '
        'adjuster chain rather than as a flat flag, which would hand it the ability '
        'against exactly the targets the printed line excludes. See '
        'game/conditional_devastating_wounds.py.',
        'No LEADER or SUPPORT line: it stands alone.',
    ],
))


_STONESINGER_LOADOUT = [DrakesteedFangsAndTalonsProfile, SongOfWaningProfile,
                        SolarCarbineProfile, StoneStaveProfile, VenomcrestSpitProfile]

STONESINGER = AELDARI.add_datasheet(Datasheet(
    "Stonesinger",
    keywords=("MOUNTED", "AELDARI", "CHARACTER", "EXODITE", "MOBILE", "PSYKER"),
    model_lines=[ModelLine(StonesingerProfile, 1, _STONESINGER_LOADOUT,
                           name="Stonesinger")],
    points=AELDARI_POINTS["Stonesinger"],
    abilities_text=_EXODITE_SHARED_ABILITIES + [
        'Support (24.34): this model can be attached to a Dragon Knights unit - the same '
        'unit the Clanblade LEADS, so a Dragon Knight squad can end up with both.',
        'Elemental Ensnarement: at the end of your Fight phase, roll a D6 - on a 1 this '
        'unit is battle-shocked, AND one visible enemy MONSTER/VEHICLE unit within 18" is '
        'ENSNARED until the start of your next turn (-2" Move, and it cannot be pinned). '
        'The two bullets are NOT alternatives: the roll is the price, not the gate. See '
        'game/elemental_ensnarement.py.',
        '"Cannot be pinned" really bites: an ensnared unit that a Night Spinner then hits '
        'does not stack the two -2s, because the pin never lands. Enforced where the pin '
        'is APPLIED, so a unit ensnared AFTER being pinned keeps the pin it had.',
        'Its Venomcrest Spit and Stone Stave print [ANTI-non-MONSTER/VEHICLE X+] - the '
        'NEGATED form, which no keyword entry could express. See the NON_MONSTER_VEHICLE '
        'sentinel in game/weapons.py, resolved in game/shooting.py as the exact '
        'complement of is_monster_or_vehicle_unit().',
        'The Venomcrest Spit\'s printed BS is "-", which is [TORRENT] - no override '
        'needed, the same call the Aeldari flamer records.',
    ],
))


# --- Anhrathe (Corsairs) ----------------------------------------------------

_CORSAIR_SHARED_ABILITIES = [
    'Battle Focus (army rule): see game/battle_focus.py.',
    'Scouts 7" (24.31/24.32): core, already implemented - every ANHRATHE datasheet '
    'here prints it, which is what makes them a raiding force rather than a line.',
]

_VOIDREAVER_LOADOUT = [ShurikenPistolProfile, PowerSwordProfile,
                       AeldariCloseCombatWeaponA2Profile]
_VOIDREAVER_LINE = "Corsair Voidreaver"
_VOIDREAVER_FELARCH_LINE = "Voidreaver Felarch"

VOIDREAVER_PISTOL_TO_NEURO = "Felarch -> Neuro Disruptor"
VOIDREAVER_PISTOL_TO_RIFLE = "Felarch -> Shuriken Rifle"
VOIDREAVER_TO_SHURIKEN_RIFLE = "Shuriken Pistol + Power Sword -> Shuriken Rifle"
VOIDREAVER_TO_BLASTER = "-> Blaster"
VOIDREAVER_TO_SHREDDER = "-> Shredder"
VOIDREAVER_TO_SHURIKEN_CANNON = "-> Shuriken Cannon"
VOIDREAVER_TO_WRAITHCANNON = "-> Wraithcannon"


def _equip_mistshield(token):
    """"The Voidreaver Felarch can be equipped with 1 mistshield" - a defensive
    item rather than a weapon, so Gear, exactly like the Dire Avenger Exarch's
    shimmershield and the Lychguard's dispersion shield."""
    token.mistshield = True   # read by game/invulnerable_save.py


VOIDREAVER_MISTSHIELD = "Felarch -> Mistshield"

CORSAIR_VOIDREAVERS = AELDARI.add_datasheet(Datasheet(
    "Corsair Voidreavers",
    keywords=("INFANTRY", "BATTLELINE", "AELDARI", "GRENADES", "ANHRATHE",
              "CORSAIR VOIDREAVERS"),
    composition_options=[
        [ModelLine(VoidreaverFelarchProfile, 1, _VOIDREAVER_LOADOUT,
                   name=_VOIDREAVER_FELARCH_LINE),
         ModelLine(CorsairVoidreaverProfile, 4, _VOIDREAVER_LOADOUT,
                   name=_VOIDREAVER_LINE)],
        [ModelLine(VoidreaverFelarchProfile, 1, _VOIDREAVER_LOADOUT,
                   name=_VOIDREAVER_FELARCH_LINE),
         ModelLine(CorsairVoidreaverProfile, 9, _VOIDREAVER_LOADOUT,
                   name=_VOIDREAVER_LINE)],
    ],
    wargear_options=[
        WargearOption(_VOIDREAVER_FELARCH_LINE, replaces=ShurikenPistolProfile,
                      with_weapons=[NeuroDisruptorProfile],
                      max_models=1, name=VOIDREAVER_PISTOL_TO_NEURO),
        WargearOption(_VOIDREAVER_FELARCH_LINE, replaces=ShurikenPistolProfile,
                      with_weapons=[ShurikenRifleProfile],
                      max_models=1, name=VOIDREAVER_PISTOL_TO_RIFLE),
        WargearOption(_VOIDREAVER_LINE, replaces=ShurikenPistolProfile,
                      with_weapons=[ShurikenRifleProfile],
                      max_models=9, name=VOIDREAVER_TO_SHURIKEN_RIFLE),
        WargearOption(_VOIDREAVER_LINE, replaces=PowerSwordProfile,
                      with_weapons=[BlasterProfile],
                      max_models=2, name=VOIDREAVER_TO_BLASTER),
        WargearOption(_VOIDREAVER_LINE, replaces=PowerSwordProfile,
                      with_weapons=[ShredderProfile],
                      max_models=2, name=VOIDREAVER_TO_SHREDDER),
        WargearOption(_VOIDREAVER_LINE, replaces=PowerSwordProfile,
                      with_weapons=[ShurikenCannonProfile],
                      max_models=1, name=VOIDREAVER_TO_SHURIKEN_CANNON),
        WargearOption(_VOIDREAVER_LINE, replaces=PowerSwordProfile,
                      with_weapons=[VoidreaverWraithcannonProfile],
                      max_models=1, name=VOIDREAVER_TO_WRAITHCANNON),
    ],
    gear_options=[
        Gear(_VOIDREAVER_FELARCH_LINE, VOIDREAVER_MISTSHIELD, _equip_mistshield),
    ],
    gear_slots={_VOIDREAVER_FELARCH_LINE: 1},
    points=AELDARI_POINTS["Corsair Voidreavers"],
    abilities_text=_CORSAIR_SHARED_ABILITIES + [
        'Reavers of the Void: re-roll a Hit roll of 1, or re-roll the WHOLE Hit roll '
        'instead if the target is within range of an objective marker. The SEVENTH '
        '"ones or whole, never just failures" source, so it registers in '
        'game/reroll_scope.py rather than growing its own reading - and it is the first '
        'whose whole-roll half turns on the target\'s POSITION rather than on a unit '
        'state or a keyword. See game/reavers_of_the_void.py.',
        'Mistshield (wargear): the bearer has a 4+ invulnerable save - the fourth item '
        'of that exact shape, folded into game/invulnerable_save.py beside the '
        'shimmershield, the dispersion shield and the forceshield.',
        'NAMED LIMITATION: the printed per-model caps ("for every 5 models, 1 ... can be '
        'replaced", "if this unit contains 10 models, 1 ...") are expressed as '
        'max_models on each option, which is exact for the 10-model build and generous '
        'for the 5-model one - a WargearOption cannot scale its cap with the composition. '
        'Named rather than silently dropped, the same treatment the Kroot Farstalkers\' '
        '"one of the following" carries.',
        'Led by: KHARSETH, PRINCE YRIEL or YVRAINE; supported by THE VISARCH. All four '
        'are built; the pairings live on their own points entries.',
    ],
))


_SKYREAVER_LOADOUT = [ShurikenPistolProfile, CorsairBladeProfile]
_SKYREAVER_LINE = "Skyreaver"
_SKYREAVER_FELARCH_LINE = "Skyreaver Felarch"

SKYREAVER_PISTOL_TO_BLAST_PISTOL = "Felarch -> Blast Pistol"
SKYREAVER_PISTOL_TO_NEURO = "Felarch -> Neuro Disruptor"
SKYREAVER_TO_BLASTER = "Pistol + Blade -> Blaster"
SKYREAVER_TO_FLAMER = "Pistol + Blade -> Flamer"
SKYREAVER_TO_FUSION_GUN = "Pistol + Blade -> Fusion Gun"
SKYREAVER_TO_SHREDDER = "Pistol + Blade -> Shredder"

CORSAIR_SKYREAVERS = AELDARI.add_datasheet(Datasheet(
    "Corsair Skyreavers",
    keywords=("INFANTRY", "AELDARI", "ANHRATHE", "JUMP PACK", "FLY", "GRENADES",
              "CORSAIR SKYREAVERS"),
    composition_options=[
        [ModelLine(SkyreaverFelarchProfile, 1, _SKYREAVER_LOADOUT,
                   name=_SKYREAVER_FELARCH_LINE),
         ModelLine(CorsairSkyreaverProfile, 4, _SKYREAVER_LOADOUT, name=_SKYREAVER_LINE)],
        [ModelLine(SkyreaverFelarchProfile, 1, _SKYREAVER_LOADOUT,
                   name=_SKYREAVER_FELARCH_LINE),
         ModelLine(CorsairSkyreaverProfile, 9, _SKYREAVER_LOADOUT, name=_SKYREAVER_LINE)],
    ],
    # "up to 2 Skyreaver models can each have their shuriken pistol AND Corsair
    # blade replaced with 1 <gun> and 1 close combat weapon" - so each option
    # gives up BOTH printed weapons and returns two, which is why every one of
    # them lists the close combat weapon as well.
    wargear_options=[
        WargearOption(_SKYREAVER_FELARCH_LINE, replaces=ShurikenPistolProfile,
                      with_weapons=[BlastPistolProfile],
                      max_models=1, name=SKYREAVER_PISTOL_TO_BLAST_PISTOL),
        WargearOption(_SKYREAVER_FELARCH_LINE, replaces=ShurikenPistolProfile,
                      with_weapons=[NeuroDisruptorProfile],
                      max_models=1, name=SKYREAVER_PISTOL_TO_NEURO),
        WargearOption(_SKYREAVER_LINE, replaces=CorsairBladeProfile,
                      with_weapons=[BlasterProfile, AeldariCloseCombatWeaponA3Profile],
                      max_models=2, name=SKYREAVER_TO_BLASTER),
        WargearOption(_SKYREAVER_LINE, replaces=CorsairBladeProfile,
                      with_weapons=[AeldariFlamerProfile, AeldariCloseCombatWeaponA3Profile],
                      max_models=2, name=SKYREAVER_TO_FLAMER),
        WargearOption(_SKYREAVER_LINE, replaces=CorsairBladeProfile,
                      with_weapons=[FusionGunProfile, AeldariCloseCombatWeaponA3Profile],
                      max_models=2, name=SKYREAVER_TO_FUSION_GUN),
        WargearOption(_SKYREAVER_LINE, replaces=CorsairBladeProfile,
                      with_weapons=[ShredderProfile, AeldariCloseCombatWeaponA3Profile],
                      max_models=2, name=SKYREAVER_TO_SHREDDER),
    ],
    points=AELDARI_POINTS["Corsair Skyreavers"],
    abilities_text=_CORSAIR_SHARED_ABILITIES + [
        'Deep Strike (24.09): core, already implemented.',
        'Raid and Run: at the end of the Fight phase, a unit that was eligible to fight '
        'may make a D3+3" Normal move if it is unengaged, or a D3+3" Fall Back move if it '
        'is not. ONE gate, two moves - "otherwise" selects the move, it is not a second '
        'condition. Registered in MovementController.REACTIVE_MOVE_MODES, which is what '
        'stops the AI walking over a human\'s open move (reported twice before). See '
        'game/raid_and_run.py.',
        'NAMED LIMITATION: "you cannot select the same option more than once per unit '
        'unless it contains 10 models, in which case not more than twice" is a '
        'composition-dependent cap across a GROUP of options, which WargearOption cannot '
        'express - max_models=2 is exact for the 10-model build and generous for the '
        '5-model one.',
    ],
))


# A3 for BOTH melee rows: Corsair Voidscarred print "Power sword" and "Close
# combat weapon" one Attack better than Corsair Voidreavers do, so neither
# shares the Voidreavers' class.
_VOIDSCARRED_LOADOUT = [ShurikenPistolProfile, VoidscarredPowerSwordProfile,
                        AeldariCloseCombatWeaponA3Profile]
_VOIDSCARRED_LINE = "Corsair Voidscarred"
_VOIDSCARRED_FELARCH_LINE = "Voidscarred Felarch"
_SHADE_RUNNER_LINE = "Shade Runner"
_SOUL_WEAVER_LINE = "Soul Weaver"
_WAY_SEEKER_LINE = "Way Seeker"

CORSAIR_VOIDSCARRED = AELDARI.add_datasheet(Datasheet(
    "Corsair Voidscarred",
    keywords=("INFANTRY", "AELDARI", "GRENADES", "ANHRATHE", "CORSAIR VOIDSCARRED"),
    # FIVE model lines - the most of any datasheet in this engine. The three
    # specialists are 0-1 each, so the built composition takes all three: they
    # are what the datasheet is FOR, and a build without them would exercise
    # none of the three wargear abilities.
    composition_options=[
        [ModelLine(VoidscarredFelarchProfile, 1, _VOIDSCARRED_LOADOUT,
                   name=_VOIDSCARRED_FELARCH_LINE),
         ModelLine(CorsairVoidscarredProfile, 4, _VOIDSCARRED_LOADOUT,
                   name=_VOIDSCARRED_LINE)],
        [ModelLine(VoidscarredFelarchProfile, 1, _VOIDSCARRED_LOADOUT,
                   name=_VOIDSCARRED_FELARCH_LINE),
         ModelLine(CorsairVoidscarredProfile, 6, _VOIDSCARRED_LOADOUT,
                   name=_VOIDSCARRED_LINE),
         ModelLine(ShadeRunnerProfile, 1,
                   [ShurikenPistolProfile, PairedHekatariiBladesProfile],
                   name=_SHADE_RUNNER_LINE),
         ModelLine(SoulWeaverProfile, 1,
                   [ShurikenPistolProfile, VoidscarredPowerSwordProfile],
                   name=_SOUL_WEAVER_LINE),
         ModelLine(WaySeekerProfile, 1,
                   [ShurikenPistolProfile, VoidscarredExecutionerProfile,
                    WaySeekerWitchStaffProfile],
                   name=_WAY_SEEKER_LINE)],
    ],
    points=AELDARI_POINTS["Corsair Voidscarred"],
    abilities_text=_CORSAIR_SHARED_ABILITIES + [
        'Piratical Raiders: at the start of the battle, select one enemy unit; this '
        'unit\'s weapons have [LETHAL HITS] and [PRECISION] against it for the whole '
        'battle. Both keywords are granted in ONE copy, so neither can arrive without the '
        'other. See game/corsair_abilities.py.',
        'Channeller Stones (Soul Weaver\'s wargear): once per turn, the first failed save '
        'in this unit takes Damage 0. A per-TURN resource on the squad.',
        'Faolchu (wargear): RANGED weapons in the bearer\'s unit have [IGNORES COVER] - '
        'the "ranged" is printed and is the half easiest to drop.',
        'Mistshield (wargear): a 4+ invulnerable save.',
        'The Way Seeker\'s Executioner is NOT the Aeldari Executioner already in this '
        'engine: that is a MELEE row at A3/S6/AP-3/D3 with [ANTI-INFANTRY 3+], this is a '
        'RANGED 18" gun with [ANTI-INFANTRY 2+] and [PSYCHIC]. Same printed name, nothing '
        'else in common.',
        'FIVE model lines, which is the most of any datasheet here; the three 0-1 '
        'specialists are all taken in the 10-model build.',
    ],
))


_KHARSETH_LOADOUT = [DreadOfTheDeepVoidProfile, WaystaveProfile]

KHARSETH = AELDARI.add_datasheet(Datasheet(
    "Kharseth",
    keywords=("INFANTRY", "AELDARI", "CHARACTER", "EPIC HERO", "PSYKER",
              "ANHRATHE", "KHARSETH"),
    model_lines=[ModelLine(KharsethProfile, 1, _KHARSETH_LOADOUT, name="Kharseth")],
    points=AELDARI_POINTS["Kharseth"],
    abilities_text=_CORSAIR_SHARED_ABILITIES + [
        'Leader (24.22): Corsair Voidreavers or Corsair Voidscarred. His printed line '
        'also names CORSAIR REAVER BAND, a LEGENDS datasheet deliberately not built - so '
        'it is left out of `leads` rather than dangling, and named here instead.',
        'Aethersense: enemy units arriving from Reserves cannot be set up within 12" of '
        'this MODEL - measured to the model, as printed, not to its unit. See '
        'game/corsair_abilities.py.',
        'Fury of the Void: a unit his Dread of the Deep Void hits is RIVEN until the end '
        'of the turn, and every AELDARI attack against it adds 1 to its STRENGTH. The '
        'seventh enemy mark here and the FIRST that changes a characteristic rather than '
        'a roll - so it lands in the adjuster chain, not in _wound_modifiers(). See '
        'game/fury_of_the_void.py.',
        'Invulnerable Save 4+.',
    ],
))


_PRINCE_YRIEL_LOADOUT = [EyeOfWrathProfile, ShurikenPistolProfile,
                         SpearOfTwilightProfile]

PRINCE_YRIEL = AELDARI.add_datasheet(Datasheet(
    "Prince Yriel",
    keywords=("INFANTRY", "AELDARI", "CHARACTER", "EPIC HERO", "ANHRATHE",
              "PRINCE YRIEL"),
    model_lines=[ModelLine(PrinceYrielProfile, 1, _PRINCE_YRIEL_LOADOUT,
                           name="Prince Yriel")],
    points=AELDARI_POINTS["Prince Yriel"],
    abilities_text=_CORSAIR_SHARED_ABILITIES + [
        'Leader (24.22): Corsair Voidreavers or Corsair Voidscarred, with the same '
        'CORSAIR REAVER BAND omission Kharseth carries.',
        'Piratical Hero: while leading a unit, its attacks have [SUSTAINED HITS 1] AND '
        'add 1 to the Hit roll. Two halves at two seams - the keyword in the adjuster '
        'chain (where _crit_note() can read it at roll time) and the +1 in '
        '_hit_modifiers(). See game/corsair_abilities.py.',
        'Prince of Corsairs: after both players have deployed, redeploy up to three '
        'AELDARI units, and they may go into Strategic Reserves REGARDLESS of how many '
        'are already there. The second consumer of PregameController.redeploy_step, after '
        'Kauyon\'s Solid-image Projection Unit, and it fires at the same instant. The AI '
        'declines, for the same reason that one does. See game/prince_of_corsairs.py.',
        'Invulnerable Save 4+.',
    ],
))


_STARFANG_LOADOUT = [DisintegratorCannonProfile, StarfangGrenadeLauncherProfile,
                     WraithboneHullProfile]

STARFANGS = AELDARI.add_datasheet(Datasheet(
    "Starfangs",
    keywords=("VEHICLE", "AELDARI", "ANHRATHE", "FLY", "SMOKE", "GRENADES", "STARFANGS"),
    composition_options=[
        [ModelLine(StarfangProfile, 1, _STARFANG_LOADOUT, name="Starfang")],
        [ModelLine(StarfangProfile, 2, _STARFANG_LOADOUT, name="Starfang")],
    ],
    points=AELDARI_POINTS["Starfangs"],
    abilities_text=_CORSAIR_SHARED_ABILITIES + [
        'Deadly Demise 1 (24.08): core, already implemented.',
        'Hallucinogen Grenades: at the start of your OPPONENT\'S Shooting phase, give one '
        'friendly AELDARI INFANTRY unit within 36" the Stealth ability until the end of '
        'the phase. The FIRST temporary grant of Stealth in this engine, so '
        'game/squad.py\'s squad_has_stealth() grew a second source rather than the grant '
        'being written as a flag someone has to clear. See '
        'game/hallucinogen_grenades.py.',
        'Its 105 x 70 mm oval takes the same equal-area circle as the Vyper\'s, and is '
        'pinned against it rather than against a literal.',
    ],
))


# --- The Ynnari triumvirate --------------------------------------------------
#
# Yvraine, The Visarch and The Yncarne share one FACTION line (YNNARI) and one
# army-list restriction, so their shared text is written once here.

_YNNARI_SHARED_ABILITIES = [
    'Battle Focus: the Aeldari army rule - see game/battle_focus.py.',
    'Disparate Paths: the YNNARI army rule, printed on the datasheet as a second '
    'FACTION line. It is an ARMY rule rather than a datasheet ability - it says which '
    'detachment rules a mixed Ynnari army may use - and this engine builds army rules '
    'from the ArmyList, not from a datasheet. Not modelled, and named here rather than '
    'dropped, the same way the Falcon and the Devilfish name their YNNARI transport '
    'clause.',
    'Servant Of The Whispering God: your army cannot include non-YNNARI EPIC HERO '
    'units. A LIST-BUILDING restriction, and this engine has no army-building step - '
    'by the time a battle starts the list is fixed, so there is no moment at which it '
    'could fire and nothing for it to refuse. A documented no-op; see '
    'game/ynnari_abilities.py.',
]

_YVRAINE_LOADOUT = [StormOfWhispersProfile, KhaVirProfile]

YVRAINE = AELDARI.add_datasheet(Datasheet(
    "Yvraine",
    keywords=("INFANTRY", "AELDARI", "CHARACTER", "EPIC HERO", "PSYKER", "YNNARI",
              "YVRAINE"),
    model_lines=[ModelLine(YvraineProfile, 1, _YVRAINE_LOADOUT, name="Yvraine")],
    points=AELDARI_POINTS["Yvraine"],
    abilities_text=_YNNARI_SHARED_ABILITIES + [
        'Leader (24.22): Corsair Voidreavers, Corsair Voidscarred, Guardian Defenders '
        'or Storm Guardians. Her printed line also names CORSAIR REAVER BAND (Legends) '
        'and the Ynnari-Drukhari Incubi, Kabalite Warriors and Wyches, none of which is '
        'built - so those four are left out of the pairing table rather than pointed at '
        'nothing.',
        'Word of the Phoenix (Psychic): while leading a unit, in your Command phase roll '
        'a D6; on a 2+ return up to D3+1 destroyed BODYGUARD models (excluding SUPPORT '
        'WEAPON models) with their full wounds. Two rolls, therefore two dice windows - '
        'DiceManager holds one at a time. See game/word_of_the_phoenix.py.',
        'Herald of Ynnead: at the start of the Fight phase, mark one enemy unit within '
        'Engagement Range of her unit; until the end of the PHASE, friendly AELDARI '
        'attacks against it re-roll a Wound roll of 1. The eighth enemy mark and the '
        'shortest-lived. Resolved automatically rather than offered: a bare optional '
        're-roll of 1s has no downside, so a prompt would have exactly one right answer. '
        'See game/ynnari_abilities.py.',
        'Invulnerable Save 4+.',
        'Her 75 x 42 mm oval takes the same equal-area circle as the Exodite drakesteed, '
        'and is pinned against it rather than against a literal.',
    ],
))


_VISARCH_LOADOUT = [AsuVarQuicksilverStanceProfile]

THE_VISARCH = AELDARI.add_datasheet(Datasheet(
    "The Visarch",
    keywords=("INFANTRY", "AELDARI", "CHARACTER", "EPIC HERO", "YNNARI",
              "THE VISARCH"),
    model_lines=[ModelLine(TheVisarchProfile, 1, _VISARCH_LOADOUT,
                           name="The Visarch")],
    points=AELDARI_POINTS["The Visarch"],
    abilities_text=_YNNARI_SHARED_ABILITIES + [
        'Support (24.23): the same four built datasheets Yvraine leads, with the same '
        'four omissions. His printed line adds "even if YVRAINE has already been '
        'attached to it" - the same sentence Eldrad Ulthran prints, and the same engine '
        'question (may this model join a unit that already has a leader?), so it takes '
        'the same flag rather than a second one meaning the same thing.',
        'Asu-var: ONE printed weapon with THREE stances - quicksilver, duellist and '
        'mythic. Every other multi-profile weapon here prints two, and overcharge_profile '
        'is a single link, so the three are CHAINED (quicksilver -> duellist -> mythic) '
        'and only the first is handed out.',
        'Way of the Blade: while leading a unit, models in that unit have Fights First '
        '(24.13). The THIRD source of Fights First and the first that is neither the '
        'unit\'s own printed ability nor rule 11.04\'s post-charge grant, so it folds '
        'into squad_has_fights_first() - the one place that decides activation ORDER. '
        'See game/ynnari_abilities.py.',
        'Yvraine\'s Champion: while leading a unit, OTHER CHARACTER models attached to '
        'that unit have Feel No Pain 4+. Three words do real work - "other" excludes him, '
        '"CHARACTER" excludes the bodyguards, "leading" is 24.22. See '
        'game/ynnari_abilities.py.',
        'Invulnerable Save 4+.',
    ],
))


_YNCARNE_LOADOUT = [SwirlingSoulEnergyProfile, VilithZharStrikeProfile]

THE_YNCARNE = AELDARI.add_datasheet(Datasheet(
    "The Yncarne",
    keywords=("MONSTER", "AELDARI", "CHARACTER", "EPIC HERO", "FLY", "PSYKER",
              "DAEMON", "YNNARI", "THE YNCARNE"),
    model_lines=[ModelLine(TheYncarneProfile, 1, _YNCARNE_LOADOUT,
                           name="The Yncarne")],
    points=AELDARI_POINTS["The Yncarne"],
    abilities_text=_YNNARI_SHARED_ABILITIES + [
        'Deadly Demise D3 (24.08) and Deep Strike (24.09): core, already implemented.',
        'Vilith-zhar: one printed weapon with a strike and a sweep profile, the ordinary '
        'two-mode shape.',
        'Inevitable Death: once in EACH OPPONENT\'S turn, when another friendly AELDARI '
        'unit is destroyed, remove this model and set it up as close as possible to where '
        'one of that unit\'s models died, outside Engagement Range - and it can still '
        'move this turn. Fuegan\'s Unquenchable Resolve with the arrow reversed: it is '
        'somebody else\'s death that moves a model which was alive the whole time, so '
        'nothing goes on or off the destroyed list. See game/inevitable_death.py.',
        'Ethereal Form: regains up to D3 lost wounds each time it destroys an enemy unit. '
        '"Up to" makes the roll a ceiling, so a model at full wounds gains nothing from a '
        '3. The killer is read from whoever was attacking at the time - this engine has '
        'no other answer, the same one Szeras\' Atomic Energy Manipulator takes. See '
        'game/ynnari_abilities.py.',
        'Invulnerable Save 4+.',
        'Its 80 mm base is the Avatar of Khaine\'s, and is pinned against it rather than '
        'against a literal.',
    ],
))


# --- FACTION KEYWORDS ---------------------------------------------------------
#
# The second printed keyword line, transcribed. It is NOT one keyword per
# datasheet: most craftworld units may be taken in a Ynnari army as well, and
# print both. Measured across the 54 built datasheets, there are exactly three
# lines:
#
#   ASURYANI, YNNARI   41   the ordinary case
#   ASURYANI           10   the non-Ynnari EPIC HEROes
#   YNNARI              3   the Ynnari triumvirate
#
# THE TEN ARE NOT AN ARBITRARY LIST - they are Servant Of The Whispering God
# showing up in the data. That rule (printed on all three Ynnari datasheets)
# says a Ynnari army cannot include EPIC HEROes without the YNNARI keyword, so
# those heroes cannot carry it, and the ten ASURYANI-only sheets are precisely
# the ten that set `epic_hero`. Derived here from that flag rather than listed
# by hand, and cross-checked against the corpus in the test - a hand-kept list
# of ten names is the second copy that drifts.
#
# WHY THIS IS NOT THE battle_focus FLAG, measured: all 54 set `battle_focus`,
# but only 51 print ASURYANI. The Ynnari triumvirate prints Battle Focus as a
# faction ability while belonging to YNNARI, and two of those three are
# PSYKERs - exactly the models Spirit Conclave's "ASURYANI PSYKER" clause has
# to exclude. Using the flag as a stand-in would have been wrong in the one
# place the clause bites rather than harmlessly wide.
#
# ANHRATHE (Corsairs) and EXODITE units ARE ASURYANI - read off the corpus, not
# assumed from the sub-faction names.
_YNNARI_ONLY = frozenset({"Yvraine", "The Visarch", "The Yncarne"})

for _sheet_name, _sheet in AELDARI.datasheets.items():
    if _sheet_name in _YNNARI_ONLY:
        _sheet.faction_keywords = ("YNNARI",)
    elif any(getattr(_line.profile_cls, "epic_hero", False)
             for _option in _sheet.compositions() for _line in _option):
        _sheet.faction_keywords = ("ASURYANI",)
    else:
        _sheet.faction_keywords = ("ASURYANI", "YNNARI")
