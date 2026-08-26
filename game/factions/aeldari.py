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

from game.factions.aeldari_points import AELDARI_POINTS
from game.factions.datasheet import Datasheet, Gear, ModelLine, WargearOption
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
    WraithcannonProfile,
    WitchbladeProfile,
    DarkReaperMissileLauncherStarshotProfile, DarkReaperShurikenCannonProfile, LaserLanceMeleeProfile, LaserLanceRangedProfile, ParagonSabreProfile, ReaperLauncherStarshotProfile, StarLanceMeleeProfile, StarLanceRangedProfile, TempestLauncherProfile,
    AeldariCloseCombatWeaponA3Profile, ScatterLaserProfile,
    RangerLongRifleProfile, RangerShurikenPistolProfile,
    ShroudRunnerLongRifleProfile, ShroudRunnerScatterLaserProfile,
    ExarchsLasblasterProfile, FuryOfTheTempestProfile, HawksTalonProfile,
    LasblasterProfile, ShiningBladeProfile, SunpistolProfile,
    SwoopingHawkPowerSwordProfile,
)

AELDARI = register_faction(Faction("Aeldari", "AELDARI"))

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
