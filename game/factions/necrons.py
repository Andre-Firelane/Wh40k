"""Necron faction data - the fourth faction in this engine, after T'au Empire,
Orks and Aeldari.

The army rule is NOT here: Reanimation Protocols lives in
game/reanimation_protocols.py, because it applies regardless of detachment and
is engine behaviour rather than datasheet data. Same split the other three
factions use - this module holds datasheet-level data only. The Awakened
Dynasty detachment's own rule (Command Protocols) is likewise its own module.

The AWAKENED_DYNASTY record at the bottom is descriptive: nothing reads its
`stratagems`, exactly as with the Ork War Horde and the T'au Retaliation Cadre.
A live Stratagem needs a controller to own its effect, and those are built in
main.py.

TRANSCRIPTION PROVENANCE: Wahapedia, 11th edition. Every weapon row on every
one of these datasheets came back with an EMPTY keyword column and its keywords
in the weapon NAME instead - the ~15th occurrence of the artefact CLAUDE.md
records - so game/weapons.py follows the name column throughout.
"""

from game import force_dispositions, macrocyte_wargear, spyder_wargear
from game.factions.datasheet import Datasheet, Gear, ModelLine, WargearOption
from game.factions.faction import Faction, register_faction
from game.factions.detachment import Detachment, Enhancement
from game.factions.necrons_points import NECRONS_POINTS
from game.units import (
    CanoptekWraithProfile,
    CtanShardOfTheVoidDragonProfile,
    CtanShardOfTheNightbringerProfile,
    CtanShardOfTheDeceiverProfile,
    TranscendentCtanProfile,
    DoomsdayArkProfile,
    IlluminorSzerasProfile,
    ImmortalProfile,
    LokhustDestroyerProfile,
    LokhustHeavyDestroyerProfile,
    LokhustLordProfile,
    LychguardProfile,
    NecronWarriorProfile,
    OverlordProfile,
    PlasmancerProfile,
    SkorpekhDestroyerProfile,
    SkorpekhLordProfile,
    TechnomancerProfile,
    ChronomancerProfile,
    PsychomancerProfile,
    OrikanTheDivinerProfile,
    DeathmarkProfile,
    FlayedOneProfile,
    CryptothrallProfile,
    TombBladeProfile,
    HexmarkDestroyerProfile,
    OphydianDestroyerProfile,
    NekrosorAmmentarProfile,
    TriarchPraetorianProfile,
    TriarchStalkerProfile,
    CanoptekScarabSwarmProfile,
    CanoptekSpyderProfile,
    CanoptekDoomstalkerProfile,
    CanoptekReanimatorProfile,
    CanoptekMacrocyteProfile,
    CanoptekTombCrawlerProfile,
    GeomancerProfile,
)
from game.weapons import (
    ArmouredBulkProfile,
    CanoptekTailBladesProfile,
    DoomsdayCannonProfile,
    EldritchLanceMeleeProfile,
    EldritchLanceRangedProfile,
    EnmiticAnnihilatorProfile,
    EnmiticExterminatorProfile,
    GaussBlasterProfile,
    GaussCannonProfile,
    GaussDestructorProfile,
    GaussFlayerArrayProfile,
    GaussFlayerProfile,
    FlensingClawProfile,
    GaussReaperProfile,
    HyperphaseHarvesterProfile,
    HyperphaseSwordProfile,
    ImpalingLegsProfile,
    NecronCloseCombatWeaponA1Profile,
    NecronCloseCombatWeaponA2Profile,
    LordStaffOfLightMeleeProfile,
    LordsBladeProfile,
    LordStaffOfLightRangedProfile,
    OverlordsBladeProfile,
    AtomiserBeamA1Profile,
    AtomiserBeamA3Profile,
    AutomatonClawsProfile,
    ClawsA2S4Profile,
    ClawsA4S6Profile,
    DoomsdayBlasterProfile,
    DoomstalkerLimbsProfile,
    FeederMandiblesProfile,
    GaussScalpelProfile,
    HeatRayDispersedProfile,
    ParticleBeamerS6Profile,
    ReanimatorsClawsProfile,
    TeslaCasterProfile,
    TransdimensionalIsolatorProfile,
    TremorglaiveMeleeProfile,
    TremorglaiveReverberatingBeamProfile,
    TwinGaussFlayerProfile,
    TwinGaussReaperProfile,
    HeavyGaussCannonArrayProfile,
    ParticleCasterProfile,
    ParticleShredderProfile,
    RodOfCovenantMeleeProfile,
    RodOfCovenantRangedProfile,
    StalkersForelimbsProfile,
    VoidbladeProfile,
    PlasmicLanceMeleeProfile,
    PlasmicLanceRangedProfile,
    SkorpekhHyperphaseWeaponsProfile,
    SpearOfTheVoidDragonAntiVehicleProfile,
    GazeOfDeathProfile,
    ScytheOfTheNightbringerStrikeProfile,
    ScytheOfTheNightbringerSweepProfile,
    CosmicInsanityProfile,
    GoldenFistsProfile,
    SeismicAssaultProfile,
    CracklingTendrilsProfile,
    SpearOfTheVoidDragonStrikeProfile,
    TachyonArrowProfile,
    TeslaCarbineProfile,
    TechnomancerStaffOfLightMeleeProfile,
    TechnomancerStaffOfLightRangedProfile,
    TransdimensionalBeamerProfile,
    ViciousClawsProfile,
    VoidscytheProfile,
    VoltaicStormProfile,
    WarscytheProfile,
    WhipCoilsProfile,
    AeonstaveRangedProfile,
    AeonstaveMeleeProfile,
    AbyssalLanceRangedProfile,
    AbyssalLanceMeleeProfile,
    StaffOfTomorrowProfile,
    SynapticDisintegratorProfile,
    FlayerClawsProfile,
    ScouringEyeProfile,
    ScythedLimbsProfile,
    ParticleBeamerS5Profile,
    TwinGaussBlasterProfile,
    TwinTeslaCarbineProfile,
    NecronCloseCombatWeaponA4S5Profile,
    EnmiticDisintegratorPistolsProfile,
    OphydianHyperphaseWeaponsProfile,
    EnmiticDisintegratorsProfile,
    BladeTailAndWhipCoilsProfile,
    UnmakerGauntletProfile,
)

from game import tomb_blade_wargear

NECRONS = register_faction(Faction("Necrons", "NECRONS"))

#: The army rule's own text, printed once here so every datasheet's
#: abilities_text can cite it without thirteen copies drifting apart.
_REANIMATION_PROTOCOLS_TEXT = (
    "Reanimation Protocols (Faction): at the end of your Command phase, each friendly "
    "unit with this ability that is on the battlefield activates its Reanimation "
    "Protocols: when a unit's Reanimation Protocols activate, that unit heals D3 "
    "wounds - see game/reanimation_protocols.py, which also implements the core-rule "
    "half (02.02.04/01.02.03) that turns surplus healing into revived models."
)


# ===========================================================================
# Battleline
# ===========================================================================

_NECRON_WARRIOR_LINE = "Necron Warrior"
_NECRON_WARRIOR_LOADOUT = [GaussFlayerProfile, NecronCloseCombatWeaponA1Profile]
NECRON_WARRIORS_TO_GAUSS_REAPER = "Gauss Flayer -> Gauss Reaper"

NECRON_WARRIORS = NECRONS.add_datasheet(Datasheet(
    "Necron Warriors",
    keywords=("INFANTRY", "BATTLELINE", "NECRON WARRIORS", "NECRONS"),
    composition_options=[
        [ModelLine(NecronWarriorProfile, 10, _NECRON_WARRIOR_LOADOUT, name=_NECRON_WARRIOR_LINE)],
        [ModelLine(NecronWarriorProfile, 20, _NECRON_WARRIOR_LOADOUT, name=_NECRON_WARRIOR_LINE)],
    ],
    wargear_options=[
        WargearOption(_NECRON_WARRIOR_LINE, replaces=GaussFlayerProfile,
                      with_weapons=[GaussReaperProfile],
                      name=NECRON_WARRIORS_TO_GAUSS_REAPER),
    ],
    points=NECRONS_POINTS["Necron Warriors"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Their Number Is Legion: \"Each time this unit's Reanimation Protocols activate, "
        "you can re-roll the dice to see how many wounds are reanimated.\" Optional, so "
        "the AI answers it deterministically and a human is asked - see "
        "game/reanimation_protocols.py's should_reroll(). NOTE: the printed ABILITY NAME "
        "was not captured by the transcription (Wahapedia returned the text without its "
        "heading); the rule itself is verbatim.",
    ],
))


_IMMORTAL_LINE = "Immortal"
_IMMORTAL_LOADOUT = [GaussBlasterProfile, NecronCloseCombatWeaponA2Profile]
IMMORTALS_TO_TESLA_CARBINE = "Gauss Blaster -> Tesla Carbine"

IMMORTALS = NECRONS.add_datasheet(Datasheet(
    "Immortals",
    keywords=("INFANTRY", "BATTLELINE", "IMMORTALS", "NECRONS"),
    composition_options=[
        [ModelLine(ImmortalProfile, 5, _IMMORTAL_LOADOUT, name=_IMMORTAL_LINE)],
        [ModelLine(ImmortalProfile, 10, _IMMORTAL_LOADOUT, name=_IMMORTAL_LINE)],
    ],
    wargear_options=[
        WargearOption(_IMMORTAL_LINE, replaces=GaussBlasterProfile,
                      with_weapons=[TeslaCarbineProfile],
                      name=IMMORTALS_TO_TESLA_CARBINE),
    ],
    points=NECRONS_POINTS["Immortals"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Implacable Eradication: \"Each time a model in this unit makes an attack, "
        "re-roll a Wound roll of 1. If the target of that attack is an enemy unit within "
        "range of an objective marker, you can re-roll the Wound roll instead.\" - see "
        "game/implacable_eradication.py.",
    ],
))


# ===========================================================================
# Infantry
# ===========================================================================

_LYCHGUARD_LINE = "Lychguard"
_LYCHGUARD_LOADOUT = [WarscytheProfile]
LYCHGUARD_TO_HYPERPHASE_SWORD = "Warscythe -> Hyperphase Sword"
LYCHGUARD_DISPERSION_SHIELD = "Dispersion Shield"


def _equip_dispersion_shield(token):
    """"All models in this unit can each have their warscythe replaced with 1
    hyperphase sword AND 1 dispersion shield."

    ONE printed option, but half of it is a weapon swap and half is a defensive
    item, so it arrives as a WargearOption plus this Gear - the same split the
    Shining Spear Exarch's star lance and shimmershield already use.

    The two halves are inseparable in the printed text, and build_squad() runs
    gear AFTER every weapon swap, so this simply declines to attach to a model
    that did not take the sword. The pairing enforces itself that way rather
    than needing a validation rule nobody would remember to call - the same
    trick the Dire Avenger Exarch's conditional shimmershield uses."""
    if not any(isinstance(w, HyperphaseSwordProfile) for w in token.weapons):
        return
    token.dispersion_shield = True   # read by game/invulnerable_save.py


LYCHGUARD = NECRONS.add_datasheet(Datasheet(
    "Lychguard",
    keywords=("INFANTRY", "LYCHGUARD", "NECRONS"),
    composition_options=[
        [ModelLine(LychguardProfile, 5, _LYCHGUARD_LOADOUT, name=_LYCHGUARD_LINE)],
        [ModelLine(LychguardProfile, 10, _LYCHGUARD_LOADOUT, name=_LYCHGUARD_LINE)],
    ],
    wargear_options=[
        WargearOption(_LYCHGUARD_LINE, replaces=WarscytheProfile,
                      with_weapons=[HyperphaseSwordProfile],
                      name=LYCHGUARD_TO_HYPERPHASE_SWORD),
    ],
    gear_options=[
        # all_models=True: the printed line dresses EVERY model, not just a
        # character. Lychguard are the first datasheet in this engine to need
        # that, which is why Gear grew the flag - see Gear's own docstring.
        Gear(_LYCHGUARD_LINE, LYCHGUARD_DISPERSION_SHIELD, _equip_dispersion_shield,
             all_models=True),
    ],
    gear_slots={_LYCHGUARD_LINE: 1},
    points=NECRONS_POINTS["Lychguard"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Guardian Protocols: \"While a NOBLE model is leading this unit, each time an "
        "attack targets this unit, if the Strength characteristic of that attack is "
        "greater than this unit's Toughness characteristic, subtract 1 from the Wound "
        "roll.\" Mechanically identical to the Wave Serpent Shield, so it reads the same "
        "_wound_modifiers(strength=) hook - see game/guardian_protocols.py.",
        "Dispersion Shield (Wargear): \"The bearer has a 4+ invulnerable save.\" - a Gear "
        "item, read by game/invulnerable_save.py.",
    ],
))


_SKORPEKH_LINE = "Skorpekh Destroyer"
_SKORPEKH_LOADOUT = [SkorpekhHyperphaseWeaponsProfile]
SKORPEKH_PLASMACYTE = "Plasmacyte"


def _equip_plasmacyte(token):
    """"For every 3 models in this unit, this unit can have 1 Plasmacyte."

    Counted on the token rather than set as a boolean because the printed
    ability is "once per battle FOR EACH Plasmacyte this unit has" - a
    six-model unit with two of them gets two uses.

    KNOWN, DELIBERATE GAP: the "for every 3 models" ratio is NOT enforced by
    the scaffold. gear_slots is a flat per-line cap and cannot see the chosen
    composition, so a 3-model unit can be handed 2 Plasmacytes here. That is a
    LIST-BUILDING constraint, and this engine has no army-building/validation
    flow at all (CLAUDE.md's Spaeter-Liste) - every other list-building limit
    is likewise trusted to the caller. Stated rather than hidden, and asserted
    in test_skorpekh_destroyers.py so it cannot be mistaken for an oversight."""
    token.plasmacyte_count = getattr(token, "plasmacyte_count", 0) + 1


SKORPEKH_DESTROYERS = NECRONS.add_datasheet(Datasheet(
    "Skorpekh Destroyers",
    keywords=("INFANTRY", "DESTROYER CULT", "SKORPEKH DESTROYERS", "NECRONS"),
    composition_options=[
        [ModelLine(SkorpekhDestroyerProfile, 3, _SKORPEKH_LOADOUT, name=_SKORPEKH_LINE)],
        [ModelLine(SkorpekhDestroyerProfile, 6, _SKORPEKH_LOADOUT, name=_SKORPEKH_LINE)],
    ],
    gear_options=[
        Gear(_SKORPEKH_LINE, SKORPEKH_PLASMACYTE, _equip_plasmacyte, max_count=2),
    ],
    gear_slots={_SKORPEKH_LINE: 2},   # the six-model unit's maximum; see _equip_plasmacyte
    points=NECRONS_POINTS["Skorpekh Destroyers"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Whirling Onslaught: \"Each time a model in this unit makes a melee attack, "
        "re-roll a Hit roll of 1. If this unit made a Charge move this turn, you can "
        "re-roll the Hit roll instead.\" - see game/destroyer_cult.py.",
        "Plasmacyte (Wargear): \"Once per battle for each Plasmacyte this unit has, when "
        "this unit is selected to fight, you can use this ability. If you do, until the "
        "end of the phase, melee weapons equipped by models in this unit have the "
        "[DEVASTATING WOUNDS] ability.\" - see game/plasmacyte.py.",
    ],
))


# ===========================================================================
# Characters
# ===========================================================================

_OVERLORD_LINE = "Overlord"
_OVERLORD_LOADOUT = [TachyonArrowProfile, OverlordsBladeProfile]
OVERLORD_TO_STAFF_OF_LIGHT = "Tachyon Arrow + Blade -> Staff of Light"
OVERLORD_TO_VOIDSCYTHE = "Tachyon Arrow + Blade -> Voidscythe"
OVERLORD_RESURRECTION_ORB = "Resurrection Orb"


def _equip_resurrection_orb_unconditional(token):
    """The Lokhust Lord's orb. Same wargear, no condition attached: his
    printed line is a plain "one of the following", where the Overlord's is
    gated on having traded away his tachyon arrow. Two functions rather than
    one with a flag, so neither datasheet can quietly acquire the other's
    condition."""
    token.resurrection_orb = True   # read by game/resurrection_orb.py


def _equip_resurrection_orb(token):
    """"If this model is not equipped with a tachyon arrow, it can be equipped
    with 1 resurrection orb."

    The condition enforces itself for the same reason the Lychguard shield's
    does: gear runs after the weapon swaps, so by the time this is called the
    tachyon arrow is either still there or has been traded away."""
    if any(isinstance(w, TachyonArrowProfile) for w in token.weapons):
        return
    token.resurrection_orb = True   # read by game/resurrection_orb.py


OVERLORD = NECRONS.add_datasheet(Datasheet(
    "Overlord",
    keywords=("INFANTRY", "CHARACTER", "NOBLE", "OVERLORD", "NECRONS"),
    model_lines=[ModelLine(OverlordProfile, 1, _OVERLORD_LOADOUT, name=_OVERLORD_LINE)],
    wargear_options=[
        # Both options give up the SAME printed pair, so build_squad()'s
        # cursor groups them and they are mutually exclusive by construction -
        # which is what the printed "OR" means.
        WargearOption(_OVERLORD_LINE,
                      replaces=(TachyonArrowProfile, OverlordsBladeProfile),
                      with_weapons=[LordStaffOfLightRangedProfile,
                                    LordStaffOfLightMeleeProfile],
                      max_models=1, name=OVERLORD_TO_STAFF_OF_LIGHT),
        WargearOption(_OVERLORD_LINE,
                      replaces=(TachyonArrowProfile, OverlordsBladeProfile),
                      with_weapons=[VoidscytheProfile],
                      max_models=1, name=OVERLORD_TO_VOIDSCYTHE),
    ],
    gear_options=[
        Gear(_OVERLORD_LINE, OVERLORD_RESURRECTION_ORB, _equip_resurrection_orb),
    ],
    gear_slots={_OVERLORD_LINE: 1},
    points=NECRONS_POINTS["Overlord"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "My Will Be Done: \"Once per battle round, one unit from your army with this "
        "ability can use it when its unit is targeted with a Stratagem. If it does, "
        "reduce the CP cost of that use of that Stratagem by 1CP.\" - a "
        "StratagemController.cost_discounts collaborator, see game/my_will_be_done.py.",
        "Implacable Resilience: \"Each time an attack is allocated to this model, "
        "subtract 1 from that attack's Damage characteristic.\" - see "
        "game/damage_reduction.py.",
        "Resurrection Orb (Wargear): \"Once per battle, per unit. At the end of any "
        "phase, you can use this ability. If you do, this unit resurrects: when a unit "
        "resurrects, that unit's Reanimation Protocols activate, but that unit heals D6 "
        "wounds (instead of D3 wounds). You cannot resurrect more than one unit per "
        "turn.\" - see game/resurrection_orb.py.",
    ],
))

_LOKHUST_LORD_LINE = "Lokhust Lord"
LOKHUST_LORD_TO_LORDS_BLADE = "Staff of Light -> Lord's Blade"
LOKHUST_LORD_NANOSCARAB_AMULET = "Nanoscarab Amulet"
LOKHUST_LORD_RESURRECTION_ORB = "Resurrection Orb"


def _equip_nanoscarab_amulet(token):
    """"The bearer has the Feel No Pain 5+ ability." - the BEARER, so this is
    a per-token flag, read by game/nanoscarab_amulet.py."""
    token.nanoscarab_amulet = True


LOKHUST_LORD = NECRONS.add_datasheet(Datasheet(
    "Lokhust Lord",
    keywords=("MOUNTED", "CHARACTER", "FLY", "DESTROYER CULT", "LOKHUST LORD", "NECRONS"),
    model_lines=[ModelLine(LokhustLordProfile, 1,
                           [LordStaffOfLightRangedProfile, LordStaffOfLightMeleeProfile],
                           name=_LOKHUST_LORD_LINE)],
    wargear_options=[
        # "This model's staff of light can be replaced with 1 Lord's blade."
        # The staff is ONE printed weapon with a ranged AND a melee row, so
        # replacing it gives up BOTH - which leaves this build with no ranged
        # weapon at all. Same shape as the Overlord's Voidscythe swap.
        WargearOption(_LOKHUST_LORD_LINE,
                      replaces=(LordStaffOfLightRangedProfile, LordStaffOfLightMeleeProfile),
                      with_weapons=[LordsBladeProfile],
                      max_models=1, name=LOKHUST_LORD_TO_LORDS_BLADE),
    ],
    gear_options=[
        Gear(_LOKHUST_LORD_LINE, LOKHUST_LORD_NANOSCARAB_AMULET, _equip_nanoscarab_amulet),
        Gear(_LOKHUST_LORD_LINE, LOKHUST_LORD_RESURRECTION_ORB, _equip_resurrection_orb_unconditional),
    ],
    # "one of the following" - a flat cap of ONE across both items is what
    # makes them mutually exclusive, rather than a condition inside either.
    gear_slots={_LOKHUST_LORD_LINE: 1},
    points=NECRONS_POINTS["Lokhust Lord"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Leader (Core).",
        "Destroyer Cult: \"While this model is leading a unit, each time a model in that "
        "unit makes a ranged attack, a successful unmodified Hit roll of 5+ scores a "
        "Critical Hit.\" - word for word the Plasmancer's Harbinger of Destruction, which "
        "is why both read one mechanic-named flag; see game/crit_hit.py.",
        "Driven by Hatred: \"Each time this model makes an attack that targets an enemy "
        "unit that is Below Half-strength, you can re-roll the Hit roll and you can "
        "re-roll the Wound roll.\" - see game/destroyer_cult.py.",
        "Nanoscarab Amulet (Wargear): \"The bearer has the Feel No Pain 5+ ability.\" - "
        "see game/nanoscarab_amulet.py.",
        "Resurrection Orb (Wargear): \"Once per battle, per unit. At the end of any "
        "phase, you can use this ability. If you do, this unit resurrects: when a unit "
        "resurrects, that unit's Reanimation Protocols activate, but that unit heals D6 "
        "wounds (instead of D3 wounds). You cannot resurrect more than one unit per "
        "turn.\" - see game/resurrection_orb.py.",
    ],
))


_SKORPEKH_LORD_LINE = "Skorpekh Lord"

SKORPEKH_LORD = NECRONS.add_datasheet(Datasheet(
    "Skorpekh Lord",
    keywords=("INFANTRY", "CHARACTER", "DESTROYER CULT", "SKORPEKH LORD", "NECRONS"),
    model_lines=[ModelLine(SkorpekhLordProfile, 1,
                           [EnmiticAnnihilatorProfile,
                            FlensingClawProfile,
                            HyperphaseHarvesterProfile],
                           name=_SKORPEKH_LORD_LINE)],
    # No wargear_options at all: the printed entry has none, so all three
    # weapons are simply carried. Asserted in the test rather than left
    # implicit, the same way Rangers and Shroud Runners are.
    points=NECRONS_POINTS["Skorpekh Lord"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Leader (Core).",
        "United In Destruction: \"While this model is leading a unit, melee weapons "
        "equipped by models in that unit have the [LETHAL HITS] ability.\" - see "
        "game/united_in_destruction.py.",
        "Crimson Harvest: \"Each time this model ends a Charge move, select one enemy "
        "unit within Engagement Range of this model and roll one D6: on a 2-5, that "
        "unit suffers D3 mortal wounds; on a 6, that unit suffers D3+3 mortal wounds.\" "
        "- see game/mortal_wound_abilities.py.",
    ],
))



_PLASMANCER_LINE = "Plasmancer"

PLASMANCER = NECRONS.add_datasheet(Datasheet(
    "Plasmancer",
    keywords=("INFANTRY", "CHARACTER", "CRYPTEK", "PLASMANCER", "NECRONS"),
    model_lines=[ModelLine(PlasmancerProfile, 1,
                           [PlasmicLanceRangedProfile, PlasmicLanceMeleeProfile],
                           name=_PLASMANCER_LINE)],
    points=NECRONS_POINTS["Plasmancer"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Support (Core).",
        "Harbinger of Destruction: \"While this model is leading a unit, each time a "
        "model in that unit makes a ranged attack, a successful unmodified Hit roll of "
        "5+ scores a Critical Hit.\" - see game/crit_hit.py.",
        "Living Lightning: \"In your Shooting phase, select one enemy unit within 18\" of "
        "and visible to this model (excluding units with the Lone Operative ability that "
        "are not part of an Attached unit and are not within 12\" of this model) and roll "
        "four D6: for each 4+, that enemy unit suffers 1 mortal wound.\" - see "
        "game/mortal_wound_abilities.py.",
    ],
))


_TECHNOMANCER_LINE = "Technomancer"

TECHNOMANCER = NECRONS.add_datasheet(Datasheet(
    "Technomancer",
    keywords=("INFANTRY", "CHARACTER", "CRYPTEK", "FLY", "TECHNOMANCER", "NECRONS"),
    model_lines=[ModelLine(TechnomancerProfile, 1,
                           [TechnomancerStaffOfLightRangedProfile,
                            TechnomancerStaffOfLightMeleeProfile],
                           name=_TECHNOMANCER_LINE)],
    points=NECRONS_POINTS["Technomancer"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Support (Core).",
        "Rites of Reanimation: \"While this model is leading a unit, models in that unit "
        "have the Feel No Pain 5+ ability.\" - one more fold in game/feel_no_pain.py.",
        "Technomancer: \"At the end of your Movement phase, you can select one friendly "
        "NECRONS model within 6\" of the bearer. That model regains up to D3 lost wounds. "
        "Each model can only be selected for this ability once per turn.\" - see "
        "game/technomancer.py.",
    ],
))


# ---------------------------------------------------------------------------
# Crypteks - Chronomancer, Psychomancer, Orikan The Diviner
#
# All three print CORE: Support, share the Plasmancer's chassis (M5" T4 Sv4+
# W4 Ld6+ OC1 on a 40 mm base) and attach to the same two bodyguard units. The
# GEOMANCER is the fourth Cryptek of this batch and is deliberately NOT here:
# it is the only unit the Canoptek Macrocytes can be supported by, and its
# Vanguard Protocols grant Scouts only while it is attached to one, so both of
# its printed clauses would be unreachable until that datasheet exists.
# ---------------------------------------------------------------------------

_CHRONOMANCER_LINE = "Chronomancer"

CHRONOMANCER = NECRONS.add_datasheet(Datasheet(
    "Chronomancer",
    keywords=("INFANTRY", "CHARACTER", "CRYPTEK", "CHRONOMANCER", "NECRONS"),
    model_lines=[ModelLine(ChronomancerProfile, 1,
                           [AeonstaveRangedProfile, AeonstaveMeleeProfile],
                           name=_CHRONOMANCER_LINE)],
    points=NECRONS_POINTS["Chronomancer"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Support (Core).",
        "Timesplinter Mantle: \"This unit has Stealth. Melee attacks that target this "
        "unit have -1 to hit rolls.\" Both halves in game/timesplinter_mantle.py - the "
        "Stealth half is a GRANT to the unit, so it is a second source in "
        "squad_has_stealth() rather than the every-model reading rule 24.33 gives a "
        "datasheet that prints the CORE ability.",
        "Chronometron: \"In your Shooting phase, after this model's unit has shot, if it "
        "is not within Engagement Range of any enemy units, that unit can make a Normal "
        "move of up to 5\" as if it were your Movement phase. If it does, until the end "
        "of the turn, that unit is not eligible to declare a charge.\" - see "
        "game/chronometron.py, the third twin of Asurmen's Tactical Acumen.",
    ],
))


_PSYCHOMANCER_LINE = "Psychomancer"

PSYCHOMANCER = NECRONS.add_datasheet(Datasheet(
    "Psychomancer",
    keywords=("INFANTRY", "CHARACTER", "CRYPTEK", "PSYCHOMANCER", "NECRONS"),
    model_lines=[ModelLine(PsychomancerProfile, 1,
                           [AbyssalLanceRangedProfile, AbyssalLanceMeleeProfile],
                           name=_PSYCHOMANCER_LINE)],
    points=NECRONS_POINTS["Psychomancer"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Support (Core).",
        "Nightmare Shroud (Aura): \"In the Battle-Shock step of your opponent's Command "
        "phase, if an enemy unit that is below its Starting Strength is within 6\" of "
        "this model, that enemy unit must take a Battle-Shock test, subtracting 1 from "
        "the test when it does so.\" - see game/psychomancer.py.",
        "Harbinger of Despair: \"Once per turn, at the start of your Command, Movement, "
        "Shooting, Charge or Fight phase, you can select one enemy unit within 18\" of "
        "this model. That unit must take a Battle-Shock test, subtracting 1 from the "
        "test when it does so.\" - its sibling above one trigger apart; both fold onto "
        "BattleShockController.start_forced_roll(penalty=), see game/psychomancer.py.",
    ],
))


_ORIKAN_LINE = "Orikan The Diviner"

ORIKAN_THE_DIVINER = NECRONS.add_datasheet(Datasheet(
    "Orikan The Diviner",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "CRYPTEK", "CHRONOMANCER",
              "ORIKAN THE DIVINER", "NECRONS"),
    model_lines=[ModelLine(OrikanTheDivinerProfile, 1,
                           [StaffOfTomorrowProfile], name=_ORIKAN_LINE)],
    points=NECRONS_POINTS["Orikan The Diviner"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Support (Core).",
        "Master Chronomancer: \"While this model is leading a unit, models in that unit "
        "have a 4+ invulnerable save.\" - one more _better() fold in "
        "game/invulnerable_save.py, read with attached_units.leader_ability().",
        "The Stars Are Right: \"Once per battle, at the start of the Fight phase, this "
        "model can use this ability. If it does, until the end of the phase, triple the "
        "Attacks and Strength characteristics of this model's Staff of Tomorrow and "
        "every successful Wound roll made for this model's attacks scores a Critical "
        "Wound.\" - see game/the_stars_are_right.py.",
    ],
))


# ---------------------------------------------------------------------------
# Rank and file - Deathmarks, Flayed Ones, Cryptothralls, Tomb Blades
# ---------------------------------------------------------------------------

_DEATHMARK_LINE = "Deathmark"

DEATHMARKS = NECRONS.add_datasheet(Datasheet(
    "Deathmarks",
    keywords=("INFANTRY", "DEATHMARKS", "NECRONS"),
    composition_options=[
        [ModelLine(DeathmarkProfile, n,
                   # The Necron A2 close combat weapon is EXACTLY this row
                   # (A2 S4 AP0 D1), so it is shared rather than cloned - the
                   # inverse of the "same name, other numbers" trap.
                   [SynapticDisintegratorProfile, NecronCloseCombatWeaponA2Profile],
                   name=_DEATHMARK_LINE)]
        for n in (5, 10)
    ],
    points=NECRONS_POINTS["Deathmarks"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deep Strike (Core).",
        "Hyperspace Hunters: \"Once per turn, in the Reinforcements step of your "
        "opponent's Movement phase, when an enemy unit is set up on the battlefield "
        "from Reserves within 18\\\" of and visible to this unit, this unit can shoot as "
        "if it were your Shooting phase, but must only target that enemy unit when "
        "doing so, and can only do so if that enemy unit is an eligible target.\" - see "
        "game/hyperspace_hunters.py.",
    ],
))


_FLAYED_ONE_LINE = "Flayed One"

FLAYED_ONES = NECRONS.add_datasheet(Datasheet(
    "Flayed Ones",
    keywords=("INFANTRY", "FLAYED ONES", "NECRONS"),
    composition_options=[
        [ModelLine(FlayedOneProfile, n, [FlayerClawsProfile], name=_FLAYED_ONE_LINE)]
        for n in (5, 10)
    ],
    points=NECRONS_POINTS["Flayed Ones"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Infiltrators, Stealth (Core).",
        "Flesh Hunger: \"Each time a model in this unit makes a melee attack, if the "
        "target of that attack is Below Half-strength, a successful Hit roll scores a "
        "Critical Hit.\" NOT a fixed threshold - the crit threshold IS the hit "
        "threshold, the same shape as Baharroth's Cry of the Wind; see game/crit_hit.py.",
    ],
))


_CRYPTOTHRALL_LINE = "Cryptothrall"

CRYPTOTHRALLS = NECRONS.add_datasheet(Datasheet(
    "Cryptothralls",
    keywords=("INFANTRY", "CRYPTOTHRALLS", "NECRONS"),
    model_lines=[ModelLine(CryptothrallProfile, 2,
                           [ScouringEyeProfile, ScythedLimbsProfile],
                           name=_CRYPTOTHRALL_LINE)],
    points=NECRONS_POINTS["Cryptothralls"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Bound Creation: \"While this unit is in the same unit as a CRYPTEK model, that "
        "CRYPTEK model has the Feel No Pain 4+ ability.\" The SECOND bodyguard-to-leader "
        "Feel No Pain grant here, after Death Guard's Silent Bodyguard - see "
        "game/cryptothralls.py.",
        "Systematic Vigour: \"Each time a CRYPTOTHRALL model in this unit is destroyed by "
        "a melee attack, if that model has not fought this phase, roll one D6: on a 2+, "
        "do not remove it from play. The destroyed model can fight after the attacking "
        "model's unit has finished making its attacks, and it is then removed from "
        "play.\" - the third consumer of game/fight_after_death.py.",
        "Cryptek Retinue: \"At the start of the Declare Battle Formations step, this unit "
        "can join one other unit from your army that is being led by a CRYPTEK INFANTRY "
        "model (a unit cannot have more than one CRYPTOTHRALLS unit joined to it). If it "
        "does, until the end of the battle, every model in this unit counts as being "
        "part of that Bodyguard unit, and that Bodyguard unit's Starting Strength is "
        "increased accordingly.\" - the THIRD attachment role "
        "(attached_units.RETINUE), see game/cryptothralls.py.",
    ],
))


_TOMB_BLADE_LINE = "Tomb Blade"
TOMB_BLADES_TO_PARTICLE_BEAMER = "Twin Gauss Blaster -> Particle Beamer"
TOMB_BLADES_TO_TWIN_TESLA_CARBINE = "Twin Gauss Blaster -> Twin Tesla Carbine"
TOMB_BLADES_SHIELDVANES = "Shieldvanes"
TOMB_BLADES_NEBULOSCOPE = "Nebuloscope"
TOMB_BLADES_SHADOWLOOM = "Shadowloom"

TOMB_BLADES = NECRONS.add_datasheet(Datasheet(
    "Tomb Blades",
    keywords=("MOUNTED", "FLY", "TOMB BLADES", "NECRONS"),
    composition_options=[
        [ModelLine(TombBladeProfile, n,
                   # Again the shared Necron A1 close combat weapon.
                   [TwinGaussBlasterProfile, NecronCloseCombatWeaponA1Profile],
                   name=_TOMB_BLADE_LINE)]
        for n in (3, 6)
    ],
    wargear_options=[
        # "Any number of models can each have their twin gauss blaster replaced
        # with ONE OF the following" - both give up the same printed weapon, so
        # build_squad()'s cursor groups them and they are mutually exclusive per
        # model by construction, which is what the printed "one of" means.
        WargearOption(_TOMB_BLADE_LINE, replaces=TwinGaussBlasterProfile,
                      with_weapons=[ParticleBeamerS5Profile],
                      name=TOMB_BLADES_TO_PARTICLE_BEAMER),
        WargearOption(_TOMB_BLADE_LINE, replaces=TwinGaussBlasterProfile,
                      with_weapons=[TwinTeslaCarbineProfile],
                      name=TOMB_BLADES_TO_TWIN_TESLA_CARBINE),
    ],
    gear_options=[
        # Its own printed bullet, so its own slot: shieldvanes can be taken
        # ALONGSIDE a nebuloscope or a shadowloom.
        Gear(_TOMB_BLADE_LINE, TOMB_BLADES_SHIELDVANES,
             tomb_blade_wargear.equip_shieldvanes, all_models=True, group="vanes"),
        # "...one of the following", so these two SHARE a slot and a model may
        # carry only one of them.
        Gear(_TOMB_BLADE_LINE, TOMB_BLADES_NEBULOSCOPE,
             tomb_blade_wargear.equip_nebuloscope, all_models=True, group="optic"),
        Gear(_TOMB_BLADE_LINE, TOMB_BLADES_SHADOWLOOM,
             tomb_blade_wargear.equip_shadowloom, all_models=True, group="optic"),
    ],
    gear_slots={_TOMB_BLADE_LINE: {"vanes": 1, "optic": 1}},
    points=NECRONS_POINTS["Tomb Blades"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Scouts 9\\\" (Core).",
        "Evasion Engrams: \"In your Shooting phase, after this unit has shot, it can make "
        "a Normal move of up to 6\\\". If it does, until the end of the turn, this unit is "
        "not eligible to declare a charge.\" NOTE: unlike its two closest neighbours "
        "(Fire and Fade, Chronometron) it prints NO Engagement Range clause - see "
        "game/evasion_engrams.py.",
        "Nebuloscope (Wargear): \"Ranged weapons equipped by the bearer have the "
        "[IGNORES COVER] ability.\" - see game/tomb_blade_wargear.py.",
        "Shadowloom (Wargear): \"The bearer has the Stealth ability.\" Per rule 24.33 the "
        "UNIT only has Stealth if EVERY model does - see game/tomb_blade_wargear.py.",
        "Shieldvanes (Wargear): \"The bearer has a 3+ Save characteristic and a Move "
        "characteristic of 8\\\".\" A TRADE - the save improves and the move worsens - so "
        "both halves are overrides; see game/tomb_blade_wargear.py.",
    ],
))


# ---------------------------------------------------------------------------
# Destroyer Cult - Hexmark Destroyer, Ophydian Destroyers, Nekrosor Ammentar
#
# The fifth, sixth and seventh DESTROYER CULT datasheets. game/destroyer_cult.py
# already carries four re-rolls printed under that keyword; none of these three
# adds a fifth, which is worth noting rather than assumed - the keyword names a
# cult, not a mechanic.
# ---------------------------------------------------------------------------

_HEXMARK_LINE = "Hexmark Destroyer"

HEXMARK_DESTROYER = NECRONS.add_datasheet(Datasheet(
    "Hexmark Destroyer",
    keywords=("INFANTRY", "CHARACTER", "DESTROYER CULT", "HEXMARK DESTROYER", "NECRONS"),
    model_lines=[ModelLine(HexmarkDestroyerProfile, 1,
                           [EnmiticDisintegratorPistolsProfile,
                            # The THIRD set of numbers this faction prints
                            # under "Close combat weapon" (A4 S5), so its own
                            # class - the numbers here match NEITHER of the two
                            # that already exist.
                            NecronCloseCombatWeaponA4S5Profile],
                           name=_HEXMARK_LINE)],
    points=NECRONS_POINTS["Hexmark Destroyer"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deep Strike, Lone Operative (Core).",
        "Inescapable Death: \"Once per turn, one unit from your army with this ability "
        "can be targeted with the Fire Overwatch Stratagem for 0CP, even if you have "
        "already used that Stratagem on a different unit this phase. In addition, each "
        "time you target this unit with the Fire Overwatch Stratagem, while resolving "
        "that Stratagem, hits are scored on unmodified Hit rolls of 2+.\" THREE clauses "
        "and only TWO of them share an entitlement - see game/inescapable_death.py.",
        "Multi-threat Eliminator: \"Once per turn, in your opponent's Shooting phase, "
        "when an enemy unit makes a ranged attack that targets a friendly NECRONS unit "
        "within 3\\\" of a model with this ability, after that enemy unit has shot, one "
        "model with this ability that is within 3\\\" of that target can shoot as if it "
        "were your Shooting phase, but it must target only that enemy unit when doing "
        "so, and can only do so if that enemy unit is an eligible target.\" - the SECOND "
        "carrier of the Kroot Packmates shape; see game/multi_threat_eliminator.py.",
    ],
))


_OPHYDIAN_LINE = "Ophydian Destroyer"
OPHYDIAN_PLASMACYTE = "Plasmacyte"

OPHYDIAN_DESTROYERS = NECRONS.add_datasheet(Datasheet(
    "Ophydian Destroyers",
    keywords=("INFANTRY", "DESTROYER CULT", "OPHYDIAN DESTROYERS", "NECRONS"),
    composition_options=[
        [ModelLine(OphydianDestroyerProfile, n, [OphydianHyperphaseWeaponsProfile],
                   name=_OPHYDIAN_LINE)]
        for n in (3, 6)
    ],
    gear_options=[
        # The SAME printed wargear the Skorpekh Destroyers carry, word for
        # word, so it shares _equip_plasmacyte() and its documented gap: the
        # "for every 3 models" ratio is a LIST-BUILDING limit and this engine
        # has no army-building step to enforce it in.
        Gear(_OPHYDIAN_LINE, OPHYDIAN_PLASMACYTE, _equip_plasmacyte, max_count=2),
    ],
    gear_slots={_OPHYDIAN_LINE: 2},   # the six-model unit's maximum, as above
    points=NECRONS_POINTS["Ophydian Destroyers"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deep Strike (Core).",
        "Tunnelling Horrors: \"At the end of your opponent's turn, if this unit is "
        "unengaged, you can use this ability. If you do: place this unit in strategic "
        "reserves; this unit must make an ingress move in your next Movement phase "
        "(including in your first turn).\" Airborne Agility's withdrawal plus Unshrouded "
        "Truth's round-gate override, one phase apart - see "
        "game/tunnelling_horrors.py.",
        "Plasmacyte (Wargear): \"Once per battle for each Plasmacyte this unit has, when "
        "this unit is selected to fight, you can use this ability. If you do, until the "
        "end of the phase, melee weapons equipped by models in this unit have the "
        "[DEVASTATING WOUNDS] ability.\" The SECOND carrier of this exact text, and the "
        "one that revealed nothing had ever OFFERED it - see game/plasmacyte.py.",
    ],
))


_NEKROSOR_LINE = "Nekrosor Ammentar"

NEKROSOR_AMMENTAR = NECRONS.add_datasheet(Datasheet(
    "Nekrosor Ammentar",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "DESTROYER CULT",
              "NEKROSOR AMMENTAR", "NECRONS"),
    model_lines=[ModelLine(NekrosorAmmentarProfile, 1,
                           [EnmiticDisintegratorsProfile,
                            UnmakerGauntletProfile,
                            BladeTailAndWhipCoilsProfile],
                           name=_NEKROSOR_LINE)],
    points=NECRONS_POINTS["Nekrosor Ammentar"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deep Strike, Fights First (Core).",
        "Invulnerable Save: \"This model has a 4+ invulnerable save.\"",
        "Protective Disciples: \"While this model is within 3\\\" of one or more other "
        "friendly DESTROYER CULT units, this model has the Lone Operative ability.\" "
        "Illuminor Szeras's sentence with a narrower keyword - the FIFTH conditional "
        "grant registered in game/conditional_lone_operative.py.",
        "Infectious Murder-madness (Aura): \"While a friendly NECRONS unit (excluding "
        "MONSTER and TITANIC units) is within 6\\\" of this model, each time a model in "
        "that unit makes an attack, if that model has the DESTROYER CULT keyword or that "
        "enemy unit is the closest eligible target, that attack has the [SUSTAINED HITS "
        "1] ability.\" - see game/nekrosor_ammentar.py.",
        "Prophet of Destruction: \"Each time this model destroys an enemy unit, select "
        "one other friendly DESTROYER CULT unit within 9\\\" of it. Until the end of the "
        "phase, each time a model in that unit makes an attack, re-roll a Wound roll of "
        "1.\" - a death-sweep consumer like Protocol of the Vengeful Stars; see "
        "game/nekrosor_ammentar.py.",
        "Nullstone Field Generator (Wargear, Aura): \"While a friendly NECRONS unit is "
        "within 6\\\" of the bearer, models in that unit have the Feel No Pain 5+ ability "
        "against mortal wounds and Psychic Attacks.\" The FIRST aura source in "
        "game/feel_no_pain.py's fold, so it is stamped on the Squad once per frame like "
        "Nurgle's Gift - see game/nekrosor_ammentar.py.",
        "NOTE: no printed LEADER line - none of the three datasheets in this batch has "
        "one, so all three always fight as their own unit. That is what makes "
        "\"this model destroys\" and \"his unit destroyed\" the same statement for "
        "Prophet of Destruction, the same shortcut Illuminor Szeras records.",
    ],
))


_SZERAS_LINE = "Illuminor Szeras"

ILLUMINOR_SZERAS = NECRONS.add_datasheet(Datasheet(
    "Illuminor Szeras",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "CRYPTEK", "ILLUMINOR SZERAS", "NECRONS"),
    model_lines=[ModelLine(IlluminorSzerasProfile, 1,
                           [EldritchLanceRangedProfile, EldritchLanceMeleeProfile,
                            ImpalingLegsProfile],
                           name=_SZERAS_LINE)],
    points=NECRONS_POINTS["Illuminor Szeras"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Feel No Pain 4+ (Core).",
        "Invulnerable Save: \"This model has a 4+ invulnerable save.\"",
        "Illuminor: \"While this model is within 3\" of one or more other friendly NECRONS "
        "units, this model has the Lone Operative ability.\" - a CONDITIONAL form of the "
        "core ability, resolved at read time; see game/illuminor.py.",
        "Mechanical Augmentation (Aura): \"While a friendly NECRONS BATTLELINE unit is "
        "within 3\" of this model, each time a model in that unit makes an attack, improve "
        "the Armour Penetration characteristic of that attack by 1, and each time an "
        "attack targets that unit, worsen the Armour Penetration characteristic of that "
        "attack by 1.\" - see game/mechanical_augmentation.py.",
        "Atomic Energy Manipulator: \"At the end of the Fight phase, if this model "
        "destroyed one or more models this phase, until the end of the battle, add 3\" to "
        "the range of its Mechanical Augmentation ability (to a maximum of 12\").\" - the "
        "only growing-range aura in this engine; see game/mechanical_augmentation.py.",
        "NOTE: Szeras has no printed LEADER line. He helps a unit through the Aura above, "
        "which is a range test, not an attachment - so `leader` is deliberately absent "
        "from his UnitProfile.",
    ],
))


_VOID_DRAGON_LINE = "C'tan Shard of the Void Dragon"

CTAN_SHARD_OF_THE_VOID_DRAGON = NECRONS.add_datasheet(Datasheet(
    "C'tan Shard of the Void Dragon",
    keywords=("MONSTER", "CHARACTER", "EPIC HERO", "FLY",
              "C'TAN SHARD OF THE VOID DRAGON", "NECRONS"),
    model_lines=[ModelLine(CtanShardOfTheVoidDragonProfile, 1,
                           [SpearOfTheVoidDragonAntiVehicleProfile,
                            VoltaicStormProfile,
                            SpearOfTheVoidDragonStrikeProfile,
                            CanoptekTailBladesProfile],
                           name=_VOID_DRAGON_LINE)],
    points=NECRONS_POINTS["C'tan Shard of the Void Dragon"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deadly Demise D6, Deep Strike, Feel No Pain 5+ (Core).",
        "Enslaved Star God: \"This model cannot be your WARLORD.\" A documented NO-OP - "
        "this engine has no Warlord concept at all, the same status as the "
        "\"ignore vertical distance\" abilities.",
        "Matter Absorption: \"At the start of your Shooting phase, select one enemy "
        "VEHICLE unit within 12\" of this model and roll one D6: on a 2+, that enemy unit "
        "suffers D3 mortal wounds and this model regains up to that many lost wounds.\" - "
        "see game/mortal_wound_abilities.py.",
        "Necrodermis: \"Each time an attack is allocated to this model, subtract 1 from "
        "the Damage characteristic of that attack.\" - the same flat -1 the Overlord's "
        "Implacable Resilience prints, so both read game/damage_reduction.py.",
        "NOTE: the Spear of the Void Dragon prints THREE profiles - a ranged "
        "anti-vehicle row and a melee strike/sweep pair. The melee pair is one datasheet "
        "entry, so it is modelled as a firing-mode pair (overcharge_profile); otherwise "
        "rule 04.01 would let him swing both in one activation.",
    ],
))


# --- The other three C'tan -------------------------------------------------
#
# ONE CHASSIS, THREE DATASHEETS. Measured before any of them was written: all
# four C'tan in this faction print T11, Sv3+, W16, Ld6+, OC4, a 4+ invulnerable,
# Feel No Pain 5+, Deadly Demise D6, Deep Strike, Necrodermis and Enslaved Star
# God. They differ in Move (10" for the Void Dragon and the Nightbringer, 8" for
# the other two), in base, in their weapons, and in exactly ONE ability each.
# game/units.py's CtanShardProfile holds the agreement, so a drift off any of
# those numbers has to be written down to happen.
#
# They sit with the CHARACTERS rather than under the banner below for the same
# reason the Void Dragon above them does: every one of them prints CHARACTER,
# and MONSTER is what they are, not where they belong.
#
# THE TRANSCENDENT C'TAN IS THE ODD ONE, twice over - it is the only C'tan that
# is NOT an EPIC HERO, and therefore the only one a list may field more than
# once, which is why it is also the only one with per-unit points tiers.

_NIGHTBRINGER_LINE = "C'tan Shard of the Nightbringer"

CTAN_SHARD_OF_THE_NIGHTBRINGER = NECRONS.add_datasheet(Datasheet(
    "C'tan Shard of the Nightbringer",
    keywords=("MONSTER", "CHARACTER", "EPIC HERO", "FLY",
              "C'TAN SHARD OF THE NIGHTBRINGER", "NECRONS"),
    model_lines=[ModelLine(CtanShardOfTheNightbringerProfile, 1,
                           [GazeOfDeathProfile,
                            ScytheOfTheNightbringerStrikeProfile],
                           name=_NIGHTBRINGER_LINE)],
    points=NECRONS_POINTS["C'tan Shard of the Nightbringer"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deadly Demise D6, Deep Strike, Feel No Pain 5+ (Core).",
        "Enslaved Star God: \"This model cannot be your WARLORD.\" A documented NO-OP - "
        "this engine has no Warlord concept at all, the same status as the "
        "\"ignore vertical distance\" abilities.",
        "Drain Life: \"At the end of the Fight phase, roll one D6 for each enemy unit "
        "within 6\" of this model: on a 4+, that enemy unit suffers D3 mortal wounds.\" - "
        "see game/drain_life.py.",
        "Necrodermis: \"Each time an attack is allocated to this model, subtract 1 from "
        "the Damage characteristic of that attack.\" - the same flat -1 the Void Dragon "
        "and the Overlord's Implacable Resilience print, so all three read "
        "game/damage_reduction.py.",
        "NOTE: the Scythe of the Nightbringer prints TWO melee profiles (strike and "
        "sweep) as ONE datasheet entry, so they are modelled as a firing-mode pair "
        "(overcharge_profile); otherwise rule 04.01 would let him swing both in one "
        "activation. Only the strike mode goes in the loadout.",
    ],
))


_DECEIVER_LINE = "C'tan Shard of the Deceiver"

CTAN_SHARD_OF_THE_DECEIVER = NECRONS.add_datasheet(Datasheet(
    "C'tan Shard of the Deceiver",
    keywords=("MONSTER", "CHARACTER", "EPIC HERO", "FLY",
              "C'TAN SHARD OF THE DECEIVER", "NECRONS"),
    model_lines=[ModelLine(CtanShardOfTheDeceiverProfile, 1,
                           [CosmicInsanityProfile, GoldenFistsProfile],
                           name=_DECEIVER_LINE)],
    points=NECRONS_POINTS["C'tan Shard of the Deceiver"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deadly Demise D6, Deep Strike, Feel No Pain 5+, Stealth (Core).",
        "Enslaved Star God: \"This model cannot be your WARLORD.\" A documented NO-OP - "
        "this engine has no Warlord concept at all.",
        "Grand Illusion: \"If your army includes this model, after both players have "
        "deployed their armies, select up to three NECRONS units from your army and "
        "redeploy them. When doing so, any of those units can be placed into Strategic "
        "Reserves, regardless of how many units are already in Strategic Reserves.\" - "
        "see game/grand_illusion.py.",
        "Necrodermis: \"Each time an attack is allocated to this model, subtract 1 from "
        "the Damage characteristic of that attack.\" - see game/damage_reduction.py.",
        "NOTE: the printed base is 40 mm, which is smaller than all three of its "
        "siblings' and smaller than its 16-wound MONSTER statline suggests. It plays on "
        "the Void Dragon's 80 mm by user decision - a TABLE-SIZE choice, recorded in "
        "game/units.py so it is not \"corrected\" back.",
    ],
))


_TRANSCENDENT_CTAN_LINE = "Transcendent C'tan"

TRANSCENDENT_CTAN = NECRONS.add_datasheet(Datasheet(
    "Transcendent C'tan",
    keywords=("MONSTER", "CHARACTER", "FLY", "TRANSCENDENT C'TAN", "NECRONS"),
    model_lines=[ModelLine(TranscendentCtanProfile, 1,
                           [SeismicAssaultProfile, CracklingTendrilsProfile],
                           name=_TRANSCENDENT_CTAN_LINE)],
    points=NECRONS_POINTS["Transcendent C'tan"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deadly Demise D6, Deep Strike, Feel No Pain 5+ (Core).",
        "Enslaved Star God: \"This model cannot be your WARLORD.\" A documented NO-OP - "
        "this engine has no Warlord concept at all.",
        "C'Tan Shard: \"This model cannot be given Enhancements.\" A documented NO-OP "
        "today - game/enhancements.py's registry holds 47 specs across T'au and Aeldari "
        "detachments and not one Necron entry, so there is nothing here to refuse. "
        "Transcribed so the gap is visible rather than rediscovered.",
        "Transdimensional Displacement: \"In your Movement phase, when this unit is "
        "selected to make an advance move, you can use this ability. If you do: that "
        "advance move has no maximum distance; this unit can move through all types of "
        "model (including enemy models and MONSTER/VEHICLE models); after moving, this "
        "unit must be more than 8\" horizontally from all enemy units.\" - "
        "see game/transdimensional_displacement.py.",
        "Necrodermis: \"Each time an attack is allocated to this model, subtract 1 from "
        "the Damage characteristic of that attack.\" - see game/damage_reduction.py.",
    ],
))



# ===========================================================================
# Beasts, Mounted, Vehicles
# ===========================================================================

_WRAITH_LINE = "Canoptek Wraith"
_WRAITH_LOADOUT = [ViciousClawsProfile]
WRAITHS_ADD_PARTICLE_CASTER = "+ Particle Caster"
WRAITHS_ADD_TRANSDIMENSIONAL_BEAMER = "+ Transdimensional Beamer"
WRAITHS_TO_WHIP_COILS = "Vicious Claws -> Whip Coils"

CANOPTEK_WRAITHS = NECRONS.add_datasheet(Datasheet(
    "Canoptek Wraiths",
    keywords=("BEASTS", "FLY", "CANOPTEK", "WRAITHS", "NECRONS"),
    composition_options=[
        [ModelLine(CanoptekWraithProfile, 3, _WRAITH_LOADOUT, name=_WRAITH_LINE)],
        [ModelLine(CanoptekWraithProfile, 6, _WRAITH_LOADOUT, name=_WRAITH_LINE)],
    ],
    wargear_options=[
        # Pure ADDITIONS ("can each be equipped with one of the following"),
        # so replaces=None and both start their cursor at model 0. The printed
        # "one of the following" means a model may not take both; build_squad()
        # counts rather than excludes, so that half is trusted to the caller -
        # the same standing as every other list-building limit here.
        WargearOption(_WRAITH_LINE, replaces=None,
                      with_weapons=[ParticleCasterProfile],
                      name=WRAITHS_ADD_PARTICLE_CASTER),
        WargearOption(_WRAITH_LINE, replaces=None,
                      with_weapons=[TransdimensionalBeamerProfile],
                      name=WRAITHS_ADD_TRANSDIMENSIONAL_BEAMER),
        WargearOption(_WRAITH_LINE, replaces=ViciousClawsProfile,
                      with_weapons=[WhipCoilsProfile],
                      name=WRAITHS_TO_WHIP_COILS),
    ],
    points=NECRONS_POINTS["Canoptek Wraiths"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Wraith Form: \"Each time this unit ends a Normal move, you can select one enemy "
        "unit it moved over during that move and roll one D6 for each model in this unit: "
        "for each 4+, that enemy unit suffers 1 mortal wound.\" - see game/wraith_form.py.",
    ],
))


_LOKHUST_LINE = "Lokhust Destroyer"
_LOKHUST_LOADOUT = [GaussCannonProfile, NecronCloseCombatWeaponA2Profile]

LOKHUST_DESTROYERS = NECRONS.add_datasheet(Datasheet(
    "Lokhust Destroyers",
    keywords=("MOUNTED", "FLY", "DESTROYER CULT", "LOKHUST DESTROYERS", "NECRONS"),
    composition_options=[
        [ModelLine(LokhustDestroyerProfile, n, _LOKHUST_LOADOUT, name=_LOKHUST_LINE)]
        for n in (1, 2, 3, 6)
    ],
    points=NECRONS_POINTS["Lokhust Destroyers"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Hard-wired for Destruction: \"Each time a model in this unit makes a ranged "
        "attack that targets the closest eligible enemy unit, re-roll a Hit roll of 1. "
        "If that target is within range of an objective marker your opponent controls, "
        "you can re-roll the Hit roll instead.\" - see game/destroyer_cult.py.",
    ],
))


_LOKHUST_HEAVY_LINE = "Lokhust Heavy Destroyer"
_LOKHUST_HEAVY_LOADOUT = [GaussDestructorProfile, NecronCloseCombatWeaponA2Profile]
LOKHUST_HEAVY_TO_ENMITIC_EXTERMINATOR = "Gauss Destructor -> Enmitic Exterminator"

LOKHUST_HEAVY_DESTROYERS = NECRONS.add_datasheet(Datasheet(
    "Lokhust Heavy Destroyers",
    keywords=("MOUNTED", "FLY", "DESTROYER CULT", "LOKHUST HEAVY DESTROYERS", "NECRONS"),
    composition_options=[
        [ModelLine(LokhustHeavyDestroyerProfile, n, _LOKHUST_HEAVY_LOADOUT,
                   name=_LOKHUST_HEAVY_LINE)]
        for n in (1, 2, 3)
    ],
    wargear_options=[
        WargearOption(_LOKHUST_HEAVY_LINE, replaces=GaussDestructorProfile,
                      with_weapons=[EnmiticExterminatorProfile],
                      name=LOKHUST_HEAVY_TO_ENMITIC_EXTERMINATOR),
    ],
    points=NECRONS_POINTS["Lokhust Heavy Destroyers"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Optimised for Slaughter: \"Each time a model in this unit makes an attack with "
        "an enmitic exterminator that targets a unit (excluding MONSTERS and VEHICLES), "
        "re-roll a Wound roll of 1. Each time a model in this unit makes an attack with a "
        "gauss destructor that targets a MONSTER or VEHICLE, re-roll a Wound roll of 1.\" "
        "- a per-WEAPON condition, unlike the other Destroyer Cult re-rolls; see "
        "game/destroyer_cult.py.",
    ],
))


_DOOMSDAY_ARK_LINE = "Doomsday Ark"

DOOMSDAY_ARK = NECRONS.add_datasheet(Datasheet(
    "Doomsday Ark",
    keywords=("VEHICLE", "FLY", "FRAME", "DOOMSDAY ARK", "NECRONS"),
    model_lines=[ModelLine(DoomsdayArkProfile, 1,
                           # "equipped with: doomsday cannon; 2 gauss flayer
                           # arrays; armoured bulk" - the array really is
                           # printed twice, so it is listed twice.
                           [DoomsdayCannonProfile,
                            GaussFlayerArrayProfile, GaussFlayerArrayProfile,
                            ArmouredBulkProfile],
                           name=_DOOMSDAY_ARK_LINE)],
    points=NECRONS_POINTS["Doomsday Ark"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deadly Demise D3 (Core).",
        "Damaged: 1-5 Wounds Remaining - \"Each time this model makes an attack, subtract "
        "1 from the Hit roll.\" - the existing damaged_threshold field.",
        "Overwhelming Obliteration: \"In your Movement phase, if this model Remains "
        "Stationary, until the end of the turn, its doomsday cannon has the "
        "[DEVASTATING WOUNDS] ability.\" - see game/overwhelming_obliteration.py.",
    ],
))


# ---------------------------------------------------------------------------
# Triarch - Praetorians, Stalker
#
# ONE BATCH BY KEYWORD, and it straddles this file's section banners: the
# Praetorians are INFANTRY and the Stalker is a VEHICLE. They are kept together
# because TRIARCH is what makes them one batch, the same way the Deathmarks
# batch above sits under the Characters banner - the sub-banner is the unit of
# organisation here, not the keyword the section above happens to name.
#
# NEITHER ONE ATTACHES TO ANYTHING. Neither prints a LEADER line and neither
# appears in any LED BY block on this faction's page (six of those exist,
# none names a Triarch datasheet) - measured, not inferred from the absence of
# a pairing in necrons_points.py.
# ---------------------------------------------------------------------------

_PRAETORIAN_LINE = "Triarch Praetorian"
PRAETORIANS_TO_CASTER_AND_VOIDBLADE = "Rod of Covenant -> Particle Caster + Voidblade"

TRIARCH_PRAETORIANS = NECRONS.add_datasheet(Datasheet(
    "Triarch Praetorians",
    keywords=("INFANTRY", "FLY", "TRIARCH", "PRAETORIANS", "NECRONS"),
    composition_options=[
        [ModelLine(TriarchPraetorianProfile, n,
                   # The rod of covenant is ONE printed entry with a ranged
                   # and a melee row, so both travel together - the Aeonstave
                   # and Eldritch Lance arrangement, not the Void Dragon
                   # spear's exclusive strike/sweep pair.
                   [RodOfCovenantRangedProfile, RodOfCovenantMeleeProfile],
                   name=_PRAETORIAN_LINE)]
        for n in (5, 10)
    ],
    wargear_options=[
        # "All models in this unit can each have their rod of covenant
        # replaced with 1 particle caster and 1 voidblade" - so the swap gives
        # up BOTH rows of that one printed entry and takes two weapons back,
        # which is what the multi-weapon `replaces` form is for. max_models is
        # None because "all models ... can each" really is unlimited.
        #
        # THE PARTICLE CASTER IS THE CANOPTEK WRAITHS' CLASS, SHARED. Its
        # printed row here is byte-for-byte theirs down to the keywords; only
        # BS differs (3+ against their 4+), and BS lives on the model profile,
        # so one class gives each wielder its own printed skill. See the
        # collision sweep at the head of that block in game/weapons.py.
        WargearOption(_PRAETORIAN_LINE,
                      replaces=(RodOfCovenantRangedProfile, RodOfCovenantMeleeProfile),
                      with_weapons=[ParticleCasterProfile, VoidbladeProfile],
                      name=PRAETORIANS_TO_CASTER_AND_VOIDBLADE),
    ],
    points=NECRONS_POINTS["Triarch Praetorians"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deep Strike (Core).",
        "Relentless Combatants: \"You can re-roll Charge rolls made for this unit, and "
        "this unit is eligible to declare a charge in a turn in which it Fell Back.\" - "
        "one sentence at TWO seams: the re-roll is offered the instant the Charge roll "
        "lands (game/relentless_combatants.py), and the Fall Back exemption registers in "
        "game/move_exceptions.py, which owns rule 09.07's charge ban.",
    ],
))


_STALKER_LINE = "Triarch Stalker"
STALKER_TO_PARTICLE_SHREDDER = "Heat Ray -> Particle Shredder"
STALKER_TO_HEAVY_GAUSS_CANNON_ARRAY = "Heat Ray -> Heavy Gauss Cannon Array"

TRIARCH_STALKER = NECRONS.add_datasheet(Datasheet(
    "Triarch Stalker",
    keywords=("VEHICLE", "WALKER", "TRIARCH", "FRAME", "STALKER", "NECRONS"),
    model_lines=[ModelLine(TriarchStalkerProfile, 1,
                           # Only the DISPERSED heat ray is carried: the
                           # focused row is its firing MODE
                           # (overcharge_profile), not a second gun, because
                           # the two are one printed datasheet entry.
                           [HeatRayDispersedProfile, StalkersForelimbsProfile],
                           name=_STALKER_LINE)],
    wargear_options=[
        # "This model's heat ray can be replaced with ONE OF the following".
        # Both options give up the same weapon, so build_squad() hands them the
        # same cursor and they cannot both land - and on a one-model line that
        # makes the exclusivity exact rather than merely non-overlapping, which
        # is the same coincidence the Enforcer Commander's six-item menu relies
        # on. A multi-model carrier would need the real exclusion this engine
        # does not have.
        WargearOption(_STALKER_LINE, replaces=HeatRayDispersedProfile,
                      with_weapons=[ParticleShredderProfile],
                      name=STALKER_TO_PARTICLE_SHREDDER),
        WargearOption(_STALKER_LINE, replaces=HeatRayDispersedProfile,
                      with_weapons=[HeavyGaussCannonArrayProfile],
                      name=STALKER_TO_HEAVY_GAUSS_CANNON_ARRAY),
    ],
    points=NECRONS_POINTS["Triarch Stalker"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deadly Demise D3, Scouts 8\" (Core).",
        "Invulnerable Save: \"This model has a 4+ invulnerable save.\"",
        "Targeting Relay: \"In your Shooting phase, each time this model is selected to "
        "shoot, after resolving its attacks, select one enemy unit that was hit by one or "
        "more of those attacks. Until the end of the phase, that unit cannot have the "
        "Benefit of Cover.\" - the Defiler's Barrage of Filth prints the same sentence, so "
        "both are subclasses of game/cover_denial.py; see game/targeting_relay.py.",
        "NOTE: this datasheet prints NO base size (\"Use model\", the FRAME keyword). The "
        "1.575\" radius on its UnitProfile is a TABLE SIZE decision, not a transcription - "
        "the reasoning is on the profile itself.",
    ],
))


# ---------------------------------------------------------------------------
# Canoptek - Scarab Swarms, Spyders, Doomstalker, Reanimator, Macrocytes,
#            Tomb Crawlers, Geomancer
#
# ONE CLOSED SUB-FACTION, and the GEOMANCER belongs to it rather than to the
# Cryptek batch three blocks up - measured, not filed by keyword: he is the only
# entry on the Canoptek Macrocytes' SUPPORTED BY line, and his Vanguard
# Protocols grant Scouts only while he is attached to one. In the Cryptek batch
# half his datasheet would have had nothing to attach to.
#
# TWO PRINTED OPTIONS ARE NOT EXPRESSIBLE, both on the Macrocytes and both the
# same known limitation: a WargearOption swaps WEAPONS for weapons, and these
# two trade a weapon away for a piece of non-weapon wargear. Named on the
# datasheet and pinned in the suite rather than quietly half-built - see the
# note on that entry.
# ---------------------------------------------------------------------------

_SCARAB_LINE = "Canoptek Scarab Swarm"

CANOPTEK_SCARAB_SWARMS = NECRONS.add_datasheet(Datasheet(
    "Canoptek Scarab Swarms",
    keywords=("SWARM", "FLY", "CANOPTEK", "SCARAB SWARMS", "NECRONS"),
    composition_options=[
        [ModelLine(CanoptekScarabSwarmProfile, n, [FeederMandiblesProfile],
                   name=_SCARAB_LINE)]
        for n in (3, 6)
    ],
    points=NECRONS_POINTS["Canoptek Scarab Swarms"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Self-destruction: \"At the start of the Fight phase, if this unit is within "
        "Engagement Range of one or more enemy units, you can select one model in this "
        "unit to destroy. If you do, select one enemy unit within Engagement Range of "
        "that model and roll one D6, adding 1 to the result if that unit is a VEHICLE. "
        "On a 2-5, that unit suffers D3 mortal wounds; on a 6+, that unit suffers 3 "
        "mortal wounds.\" - the only ability here that spends one of your OWN models; "
        "see game/scarab_self_destruction.py.",
        "Chittering swarm: \"While an enemy unit is within Engagement Range of this "
        "unit, subtract 1 from the Objective Control characteristic of models in that "
        "enemy unit (to a minimum of 1). While this unit is within 6\" of one or more "
        "friendly CRYPTEK models, the Objective Control characteristic of models in this "
        "unit is 1.\" - two clauses pointing in OPPOSITE directions, and they are the two "
        "forms game/objective_control.py already folds; see game/chittering_swarm.py.",
        "NOTE: printed OC 0, the only one in this faction - which is what makes the "
        "second half of Chittering swarm worth anything at all.",
    ],
))


_SPYDER_LINE = "Canoptek Spyder"
SPYDERS_ADD_TWO_PARTICLE_BEAMERS = "+ 2x Particle Beamer"
SPYDER_FABRICATOR_CLAW_ARRAY = "Fabricator Claw Array"
SPYDER_GLOOM_PRISM = "Gloom Prism"


def _equip_fabricator_claw_array(token):
    spyder_wargear.equip_fabricator_claw_array(token)


def _equip_gloom_prism(token):
    spyder_wargear.equip_gloom_prism(token)


CANOPTEK_SPYDERS = NECRONS.add_datasheet(Datasheet(
    "Canoptek Spyders",
    keywords=("VEHICLE", "FLY", "CANOPTEK", "SPYDERS", "NECRONS"),
    composition_options=[
        [ModelLine(CanoptekSpyderProfile, n, [AutomatonClawsProfile],
                   name=_SPYDER_LINE)]
        for n in (1, 2)
    ],
    wargear_options=[
        # "Any number of models can each be equipped with 2 particle beamers" -
        # a pure ADDITION of TWO guns, so replaces=None and both are listed.
        # This is the S6 beamer, NOT the Tomb Blades' S5 one under the same
        # printed name; see the collision sweep in game/weapons.py.
        WargearOption(_SPYDER_LINE, replaces=None,
                      with_weapons=[ParticleBeamerS6Profile, ParticleBeamerS6Profile],
                      name=SPYDERS_ADD_TWO_PARTICLE_BEAMERS),
    ],
    gear_options=[
        # THE TWO AURAS ARE GEAR, not weapons - they grant a rule rather than
        # replacing a gun. all_models=True because the printed text is "any
        # number of models can EACH be equipped"; and that choice is MEASURED
        # INERT for these two, because both auras are answered per SQUAD (does
        # any living bearer stand within 6"), so one carrier and two produce
        # the same board. Said out loud rather than left as a coincidence.
        Gear(_SPYDER_LINE, SPYDER_FABRICATOR_CLAW_ARRAY,
             _equip_fabricator_claw_array, all_models=True),
        Gear(_SPYDER_LINE, SPYDER_GLOOM_PRISM, _equip_gloom_prism,
             all_models=True),
    ],
    gear_slots={_SPYDER_LINE: 2},
    points=NECRONS_POINTS["Canoptek Spyders"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deadly Demise 1 (Core).",
        "Canoptek Swarm: \"In your Command phase, select one friendly CANOPTEK SCARAB "
        "SWARM unit within 6\" of this unit. One destroyed model is returned to that "
        "CANOPTEK SCARAB SWARM unit for each SPYDER model in this unit.\" - the seventh "
        "model-return ability, and the first that returns models to ANOTHER unit; see "
        "game/canoptek_swarm.py.",
        "Fabricator Claw Array (Aura): \"While a friendly NECRONS VEHICLE unit is within "
        "6\" of the bearer, that unit has the Feel No Pain 6+ ability.\" - see "
        "game/spyder_wargear.py.",
        "Gloom Prism (Aura): \"While a friendly NECRONS unit is within 6\" of the bearer, "
        "models in that unit have the Feel No Pain 5+ ability against mortal wounds and "
        "Psychic Attacks.\" - Nekrosor Ammentar's Nullstone Field Generator word for "
        "word, so both are game/fnp_aura.py instances.",
    ],
))


_DOOMSTALKER_LINE = "Canoptek Doomstalker"

CANOPTEK_DOOMSTALKER = NECRONS.add_datasheet(Datasheet(
    "Canoptek Doomstalker",
    keywords=("VEHICLE", "WALKER", "CANOPTEK", "DOOMSTALKER", "NECRONS"),
    model_lines=[ModelLine(CanoptekDoomstalkerProfile, 1,
                           [DoomsdayBlasterProfile, TwinGaussFlayerProfile,
                            DoomstalkerLimbsProfile],
                           name=_DOOMSTALKER_LINE)],
    points=NECRONS_POINTS["Canoptek Doomstalker"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Deadly Demise D3 (Core).",
        "Invulnerable Save: \"This model has a 4+ invulnerable save.\"",
        "Damaged: 1-4 Wounds Remaining: \"each time this model makes an attack, subtract "
        "1 from the Hit roll.\"",
        "Sentinel Construct: \"Each time you target this unit with the Fire Overwatch "
        "Stratagem, while resolving that Stratagem, hits are scored on unmodified Hit "
        "rolls of 5+.\" - the Hexmark Destroyer prints the same clause with a 2+, so both "
        "fold at the one seam that overrides rule 15.09's flat 6; see "
        "game/sentinel_construct.py.",
    ],
))


_REANIMATOR_LINE = "Canoptek Reanimator"

CANOPTEK_REANIMATOR = NECRONS.add_datasheet(Datasheet(
    "Canoptek Reanimator",
    keywords=("VEHICLE", "WALKER", "CANOPTEK", "REANIMATOR", "NECRONS"),
    model_lines=[ModelLine(CanoptekReanimatorProfile, 1,
                           # "equipped with: 2 atomiser beams" - the A3 row,
                           # not the Macrocytes' A1 one under the same name.
                           [AtomiserBeamA3Profile, AtomiserBeamA3Profile,
                            ReanimatorsClawsProfile],
                           name=_REANIMATOR_LINE)],
    points=NECRONS_POINTS["Canoptek Reanimator"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Feel No Pain 4+ (Core).",
        "Nanoscarab Reanimation Beam (Aura): \"While a friendly NECRONS unit is within "
        "3\" of this model, each time that unit's Reanimation Protocols activate, that "
        "unit heals an additional D3 wounds.\" - added to the wound count BEFORE it is "
        "spent, because 01.02.03's cap and 02.02.04's order both read the total; see "
        "game/reanimation_boost.py.",
    ],
))


_MACROCYTE_LINE = "Canoptek Macrocyte"
MACROCYTES_TO_TESLA_CASTER = "Gauss Scalpel -> Tesla Caster"
MACROCYTES_TO_ATOMISER_BEAM = "Gauss Scalpel -> Atomiser Beam"
MACROCYTE_NANOSCARAB_PROJECTOR = "Nanoscarab Projector"
MACROCYTE_ACCELERATOR_MANDIBLE = "Accelerator Mandible"


def _equip_nanoscarab_projector(token):
    macrocyte_wargear.equip_nanoscarab_projector(token)


def _equip_accelerator_mandible(token):
    macrocyte_wargear.equip_accelerator_mandible(token)


CANOPTEK_MACROCYTES = NECRONS.add_datasheet(Datasheet(
    "Canoptek Macrocytes",
    keywords=("BEASTS", "FLY", "CANOPTEK", "MACROCYTES", "NECRONS"),
    model_lines=[ModelLine(CanoptekMacrocyteProfile, 5,
                           [GaussScalpelProfile, ClawsA2S4Profile],
                           name=_MACROCYTE_LINE)],
    wargear_options=[
        WargearOption(_MACROCYTE_LINE, replaces=GaussScalpelProfile,
                      with_weapons=[TeslaCasterProfile],
                      name=MACROCYTES_TO_TESLA_CASTER),
        # "1 model's gauss scalpel or tesla caster can be replaced with 1
        # atomiser beam AND 1 nanoscarab projector" - the WEAPON half only.
        # The projector is a Gear item below, and the two are NOT tied
        # together: build_squad() counts rather than excludes, the same
        # standing every other "one of the following" here has.
        WargearOption(_MACROCYTE_LINE, replaces=GaussScalpelProfile,
                      with_weapons=[AtomiserBeamA1Profile], max_models=1,
                      name=MACROCYTES_TO_ATOMISER_BEAM),
    ],
    gear_options=[
        Gear(_MACROCYTE_LINE, MACROCYTE_NANOSCARAB_PROJECTOR,
             _equip_nanoscarab_projector),
        Gear(_MACROCYTE_LINE, MACROCYTE_ACCELERATOR_MANDIBLE,
             _equip_accelerator_mandible),
    ],
    gear_slots={_MACROCYTE_LINE: 2},
    points=NECRONS_POINTS["Canoptek Macrocytes"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Scouts 8\" (Core).",
        "Harassment Swarm (Aura): \"While an enemy unit (excluding MONSTERS and VEHICLES) "
        "is within 3\" of this unit, each time a model in that unit makes an attack, "
        "subtract 1 from the Hit roll.\" - the printed noun is ATTACK, so it reaches BOTH "
        "attack steps; see game/harassment_swarm.py.",
        "Accelerator Mandible: \"At the start of the Fight phase, select one friendly "
        "CANOPTEK unit within 3\" of the bearer's unit. Until the end of the phase, "
        "improve the Weapon Skill characteristic of weapons equipped by models in that "
        "unit by 1.\" - the FIRST thing in this engine that changes a WS characteristic "
        "rather than a Hit roll; see game/macrocyte_wargear.py.",
        "Nanoscarab Projector: \"Once per battle round, when a friendly NECRONS unit "
        "within 3\" of the bearer activates its Reanimation Protocols, the bearer can use "
        "this ability. If it does, that unit reanimates 1 additional wound.\" - see "
        "game/reanimation_boost.py.",
        "KNOWN LIMITATION: the two printed options that trade a weapon away FOR WARGEAR "
        "are only half expressible - a WargearOption swaps weapons for weapons. The "
        "atomiser beam swap and the projector are modelled separately and are not tied "
        "together, and the accelerator mandible gives up no weapon at all. Same "
        "structural limit the Commander in Enforcer Battlesuit's first menu records.",
    ],
))


_TOMB_CRAWLER_LINE = "Canoptek Tomb Crawler"
TOMB_CRAWLERS_TO_ISOLATOR = "Twin Gauss Reaper -> Transdimensional Isolator"

CANOPTEK_TOMB_CRAWLERS = NECRONS.add_datasheet(Datasheet(
    "Canoptek Tomb Crawlers",
    keywords=("BEASTS", "CANOPTEK", "TOMB CRAWLERS", "NECRONS"),
    model_lines=[ModelLine(CanoptekTombCrawlerProfile, 2,
                           [TwinGaussReaperProfile, ClawsA4S6Profile],
                           name=_TOMB_CRAWLER_LINE)],
    wargear_options=[
        WargearOption(_TOMB_CRAWLER_LINE, replaces=TwinGaussReaperProfile,
                      with_weapons=[TransdimensionalIsolatorProfile], max_models=1,
                      name=TOMB_CRAWLERS_TO_ISOLATOR),
    ],
    points=NECRONS_POINTS["Canoptek Tomb Crawlers"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Canoptek Retinue: \"At the start of the Declare Battle Formations step, this "
        "unit can join one other unit from your army that is being led by a CRYPTEK model "
        "(a unit cannot have more than one TOMB CRAWLERS unit joined to it and cannot "
        "have both a TOMB CRAWLERS and a CRYPTOTHRALLS unit joined to it).\" - the SECOND "
        "carrier of rule 19.01's RETINUE role, and BOTH parentheses fall out of that "
        "role's one-unit-per-role check; see game/retinue.py.",
        "Weapon Sentinels: \"Each time a model in this unit makes a ranged attack that "
        "targets a unit within 12\", you can ignore any or all modifiers to the "
        "following: that attack's Ballistic Skill characteristic; the Hit roll; the Wound "
        "roll.\" - the third noun is new here: the first ignore-modifier filter this "
        "engine has ever put on the WOUND roll; see game/weapon_sentinels.py.",
    ],
))


_GEOMANCER_LINE = "Geomancer"

GEOMANCER = NECRONS.add_datasheet(Datasheet(
    "Geomancer",
    keywords=("INFANTRY", "CHARACTER", "CRYPTEK", "GEOMANCER", "NECRONS"),
    model_lines=[ModelLine(GeomancerProfile, 1,
                           # The tremorglaive prints THREE rows: a ranged pair
                           # (one datasheet entry, so a firing-mode pair) and a
                           # melee row, which is a separate weapon.
                           [TremorglaiveReverberatingBeamProfile,
                            TremorglaiveMeleeProfile],
                           name=_GEOMANCER_LINE)],
    points=NECRONS_POINTS["Geomancer"],
    abilities_text=[
        _REANIMATION_PROTOCOLS_TEXT,
        "Support (Core) - the sixth Cryptek, and like the other five he SUPPORTS rather "
        "than leads.",
        "Vanguard Protocols: \"If this model is attached to a CANOPTEK MACROCYTES unit "
        "during the Declare Battle Formations step, this model has the Scouts 8\" "
        "ability.\" - a LATCHED conditional, and a MEASURED no-op under this engine's "
        "rule 19.04 reading; see game/vanguard_protocols.py for the measurement.",
        "Tectonic Reverberations: \"In your Movement phase, you can select one enemy unit "
        "within 18\" of and visible to this model. Until the start of your next Movement "
        "phase that enemy unit is pinned. While a unit is pinned, subtract 2 from that "
        "unit's Move characteristic and subtract 2 from Charge rolls made for it.\" - the "
        "SECOND source of the Night Spinner's status, one phase's difference in the "
        "clock; see game/tectonic_reverberations.py and game/pinned.py.",
        "Obelisk Node Control: \"While this model is within range of an objective marker "
        "you control, enemy units that are set up on the battlefield from Reserves cannot "
        "be set up within 12\" of this model.\" - the FIRST rule in this engine that "
        "restricts where the OPPONENT may arrive; see game/obelisk_node_control.py.",
    ],
))


# ===========================================================================
# Detachment (descriptive only - see this module's docstring)
# ===========================================================================

AWAKENED_DYNASTY = NECRONS.add_detachment(Detachment(
    "Awakened Dynasty",
    rule_name="Command Protocols",
    setting="AWAKENED_DYNASTY_PLAYERS",
    points=3,
    force_disposition=force_dispositions.TAKE_AND_HOLD,
    rule_text=(
        "Command Protocols: While a NECRONS CHARACTER model is leading this unit, each "
        "time a model in this unit makes an attack, add 1 to the Hit roll."
    ),
    enhancements=[
        # RECORDED AS DATA ONLY - and the reason is no longer the one that
        # used to stand here. That said "Enhancements are not a system in this
        # engine", which went stale the moment game/enhancements.py was built:
        # forty-seven are engine-wired today across fourteen T'au and Aeldari
        # detachments, with a registry, a bearer predicate and a UnitProfile
        # field each. Same class as the Mont'ka justification that rotted while
        # its assertion stayed green.
        #
        # The real reason is a ROSTER fact: armies/necrons.json buys none of
        # these four, so wiring them would produce four rules that are dormant
        # by construction - exactly where the twenty-eight Aeldari and seven
        # T'au Enhancements sit. Naming it is the honest move; inventing roster
        # content to reach them is not. test_necron_datasheets.py pins the gap
        # from both sides, so it cannot quietly close or quietly widen.
        Enhancement("Veil of Darkness", 20, description=(
            "Once per battle, at the end of your opponent's turn, if this unit is "
            "unengaged, place it in strategic reserves with Deep Strike until the start "
            "of your next Shooting phase.")),
        Enhancement("Nether-realm Casket", 20, description=(
            "While the bearer is leading a unit, models in that unit have the Stealth "
            "ability.")),
        Enhancement("Phasal Subjugator", 35, description=(
            "Aura. While a friendly NECRONS unit (excluding CHARACTER units) is within "
            "6\" of the bearer, each time a model in that unit makes an attack, add 1 to "
            "the Hit roll.")),
        Enhancement("Enaegic Dermal Bond", 30, description=(
            "The bearer has the Feel No Pain 4+ ability.")),
    ],
    # stratagems is deliberately empty: a live Stratagem needs a controller to
    # own its effect, so the six Awakened Dynasty protocols are built in
    # main.py, exactly as the T'au Retaliation Cadre's are.
))
