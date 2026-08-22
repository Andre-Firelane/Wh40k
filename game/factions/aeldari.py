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
    WraithboneHullProfile,
    WraithCloseCombatWeaponProfile,
    WraithcannonProfile,
    WitchbladeProfile,
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
        'from the Wound roll - see game/protect.py. LIVE since Eldrad Ulthran: a plain '
        'Farseer still cannot be attached to this unit (it is itself a leader unit), but '
        'Eldrad\'s own LEADER line lets him join a unit that this Conclave has already '
        'joined. So Guardian Defenders + Warlock Conclave + Eldrad is a unit with a FARSEER '
        'leading Warlocks, and this ability applies to the whole merged unit.',
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
