"""T'au Empire faction data.

The army rule ("For The Greater Good") applies regardless of detachment
choice, so it's engine-wired directly in game/greater_good.py rather than
stored here - this module only holds datasheet/detachment-level data.

Retaliation Cadre's Bonded Heroes rule is likewise engine-wired directly
(game/retaliation_cadre.py, applied unconditionally for now since it's the
only detachment that exists - see that module's docstring); the Detachment
record below is its descriptive counterpart, same relationship
Datasheet.abilities_text has to a datasheet's engine-wired fields - and
Strike Team's own two abilities (Suppression Volley, DS8 Support Turret)
are wired the same way, in game/suppression.py and game/support_turret.py
respectively. Crisis Starscythe Battlesuits' own two abilities (Starscythe,
Battlesuit Support System) follow the same pattern again, in
game/starscythe.py and game/shooting.py's available_shooting_types()
respectively - note that Bonded Heroes and Starscythe both apply to this
unit's ranged attacks simultaneously (it's a BATTLESUIT), stacking their
independent AP boosts.

Points costs are not written here either: the whole published T'au list
lives in game/factions/tau_empire_points.py (all 43 entries, including the
36 units without a datasheet yet), and each datasheet below just points its
`points=` field - and any priced wargear option - at its own entry there, so
no number is repeated. See game/factions/points.py for the structure."""

from game import force_dispositions
from game.drones import (
    DRONE_GROUP, DRONE_SLOTS, SPECIAL_DRONE_GROUP, SPECIAL_DRONE_SLOTS,
    HOVER_DRONE_GROUP, HOVER_DRONE_SLOTS, hover_drone_gear,
    drone_options, gun_drone_gear, marker_drone_gear, special_drone_options,
)
from game.battlesuit_wargear import (
    BATTLESUIT_SUPPORT_GROUP, BATTLESUIT_SUPPORT_SLOTS, support_menu_gear,
)
from game.bounty_hunters import pechra_gear
from game.oversight_drone import oversight_drone_gear
from game.homing_beacon import homing_beacon_gear
from game.factions import Datasheet, Detachment, Enhancement, Faction, Gear, ModelLine, WargearOption, register_faction
from game.factions.tau_empire_points import TAU_EMPIRE_POINTS
from game.units import (
    BreacherFireWarriorProfile, BreacherFireWarriorShasUiProfile, CadreFirebladeProfile,
    ColdstarCommanderProfile, CommanderFarsightProfile,
    CrisisStarscytheShasUiProfile, CrisisStarscytheShasVreProfile,
    CrisisSunforgeShasUiProfile, CrisisSunforgeShasVreProfile, DevilfishProfile, FireWarriorProfile,
    FireWarriorShasUiProfile, GhostkeelProfile, KrootCarnivoreProfile, LongQuillProfile,
    HammerheadGunshipProfile, PiranhaProfile, SkyRayGunshipProfile,
    BroadsideShasUiProfile, BroadsideShasVreProfile,
    CrisisFireknifeShasUiProfile, CrisisFireknifeShasVreProfile,
    CommanderShadowsunProfile, DarkstriderProfile, EnforcerCommanderProfile, EtherealProfile,
    FarstalkerHoundProfile, KrootFarstalkerProfile, KrootHoundProfile, KrootKillBrokerProfile,
    KrootoxRampagerProfile, KrootoxRiderProfile,
    VespidStingwingProfile, VespidStrainLeaderProfile,
    FiresightMarksmanProfile,
    KrootFleshShaperProfile, KrootLoneSpearProfile, KrootTrailShaperProfile, KrootWarShaperProfile,
    PathfinderProfile, PathfinderShasUiProfile, RiLantarProfile, RiLocaiProfile, RiptideProfile,
    StealthShasUiProfile, StealthShasVreProfile,
)
from game.weapons import (
    AcceleratorBurstCannonProfile, ArmouredHullProfile, BattlesuitFistsProfile, BurstCannonProfile,
    CadreFirebladeCloseCombatWeaponProfile, CrisisBattlesuitFistsProfile, CyclicIonBlasterStandardProfile,
    CyclicIonRakerStandardProfile, DevilfishTwinPulseCarbineProfile, FirebladePulseRifleProfile,
    FusionBlasterProfile, FusionColliderProfile, GhostkeelFistsProfile, HeavyBurstCannonProfile,
    HighOutputBurstCannonProfile, IonAcceleratorStandardProfile,
    HammerheadTwinPulseCarbineProfile, IonCannonStandardProfile, PiranhaArmouredHullProfile,
    PiranhaBurstCannonProfile, PiranhaFusionBlasterProfile, RailgunProfile,
    SeekerMissileRackProfile,
    BroadsideTwinSmartMissileSystemProfile, CrushingBulkProfile, HeavyRailRifleProfile,
    HighYieldMissilePodsProfile,
    DvorgiteSkinnerProfile, FarstalkerFirearmProfile, KrootPistolAndHuntingJavelinsProfile,
    KrootoxFistsProfile, LondaxiTribalestProfile, NeutronBlasterProfile,
    NeutronGrenadeLauncherProfile, NeutronRailRifleProfile, RampagerCloseCombatWeaponProfile,
    RampagerKrootoxFistsProfile, RepeaterCannonProfile, RippingFangsProfile, RitualBladeProfile,
    StingwingClawsProfile, TanglecannonProfile, TauTechRifleProfile,
    AirburstingFragmentationProjectorProfile, FlechetteLauncherProfile,
    HighEnergyFusionBlasterProfile, LightMissilePodProfile, PlasmaRifleProfile,
    BlastJavelinProfile, DarkstriderCloseCombatWeaponProfile, FiresightCloseCombatWeaponsProfile,
    HonourStaveProfile, HuntingJavelinProfile, KalamandrasBiteProfile, KrootLongGunProfile,
    LoneSpearCloseCombatWeaponProfile, LongshotPulseRiflesProfile, ShadeProfile,
    BladestaveAndPreyHookProfile, DartBowAndTriBladeProfile, KrootScattergunProfile,
    ShapersBladeProfile, TwinRitualisticBladesProfile,
    DroneMissilePodProfile,
    KrootCloseCombatWeaponProfile, KrootPistolProfile, KrootRifleProfile, MissilePodProfile,
    PulseBlasterProfile,
    PulseCarbineProfile, PulsePistolProfile, PulsePistolBs3Profile,
    PulseRifleProfile, RiptideFistsProfile,
    SemiAutomaticGrenadeLauncherEmpProfile, SeekerMissileProfile,
    DawnBladeStrikeProfile, DawnBladeSweepProfile,
    FusionEliminatorMeleeProfile, FusionEliminatorProfile,
    HighIntensityPlasmaRifleProfile, IonRifleStandardProfile, IonScattercannonMeleeProfile,
    RailRifleProfile,
    IonScattercannonStandardProfile, ShardstormBurstSystemProfile,
    SmartMissileSystemProfile, TauCloseCombatWeaponProfile, TauFlamerProfile, TwinBurstCannonProfile,
    TwinPulseBlasterProfile, XvPulsePistolMeleeProfile, XvPulsePistolProfile,
    TwinFusionBlasterProfile, TwinPlasmaRifleProfile, TwinTauFlamerProfile,
)

TAU_EMPIRE = Faction("T'au Empire", "T'AU EMPIRE")

RETALIATION_CADRE = TAU_EMPIRE.add_detachment(Detachment(
    "Retaliation Cadre",
    rule_name="Bonded Heroes",
    setting="RETALIATION_CADRE_PLAYERS",
    points=3,
    force_disposition=force_dispositions.PURGE_THE_FOE,
    rule_text=(
        'Each time a T\'AU EMPIRE BATTLESUIT model from your army makes a '
        'ranged attack that targets a unit within 12", improve the Strength characteristic '
        'of that attack by 1. If that attack targets a unit within 9", improve the Armour '
        'Penetration characteristic of that attack by 1 as well.'
    ),
    # Unlike `rule_text` and `stratagems` above, Starflare Ignition System IS
    # engine-wired (game/starflare_ignition.py) - the record here is its
    # descriptive half, and game/starflare_ignition.py's grant() is what
    # actually puts it on a model.
    #
    # Its placement under this detachment used to be an ASSUMPTION (the user
    # supplied it as a T'au Empire Enhancement without naming a detachment).
    # rules/tau_empire/detachments/Retaliation Cadre.md now confirms it, and
    # names the other three, which are recorded bare - the same descriptive
    # shape game/factions/death_guard.py uses, with the printed text living in
    # the corpus rather than being copied here.
    enhancements=[
        Enhancement("Internal Grenade Racks", 20),
        Enhancement("Prototype Weapon System", 15),
        Enhancement("Puretide Engram Neurochip", 15),
        Enhancement(
            "Starflare Ignition System", 20,
            description=(
                'The ignition thrusters on selected battlesuits are augmented with optional '
                'feed-selectors, allowing the pilot to release a jet of enriched accelerant upon '
                "take-off and sending the pilots streaking skywards.\n"
                "T'AU EMPIRE BATTLESUIT model only. At the end of your opponent's turn, if the "
                "bearer's unit is not within Engagement Range of one or more enemy units, you can "
                'remove that unit from the battlefield and place it into Strategic Reserves.'
            ),
            restricted_to="BATTLESUIT",
        ),
    ],
    # `stratagems` is deliberately left empty: this detachment's six
    # stratagems are engine-wired one module each (game/stim_injectors.py,
    # game/arrokon_protocol.py, game/shortened_blade.py,
    # game/torchstar_gambit.py, game/grav_inhibitor_field.py,
    # game/fail_safe_detonator.py), and a real game.stratagems.Stratagem needs
    # a per-battle controller for its `effect` - so the objects are built in
    # main.py, not stored as static faction data. Same relationship the Bonded
    # Heroes rule_text above has to game/retaliation_cadre.py.
))

# --- The other T'au detachments ------------------------------------------
# Descriptive records only, exactly like the one above: `rule_text` is the
# printed rule (verbatim from rules/tau_empire/detachments/*.md, which is the
# transcription source), enhancements are recorded bare, and `stratagems` stays
# empty because a live Stratagem needs a per-battle controller.
#
# What each one DOES carry that matters to the engine is `setting`: the
# game/config.py constant naming who fields it. game/detachments.py writes
# those from the player's choice, and each detachment rule's own module reads
# only its own - which is what stops Bonded Heroes from applying to a Kauyon
# army. Adding a record here therefore makes a detachment SELECTABLE; making
# it DO something is a separate module, and until that exists the detachment
# is honestly inert rather than silently borrowing another one's rule.

KAUYON = TAU_EMPIRE.add_detachment(Detachment(
    "Kauyon",
    rule_name="Patient Hunter",
    setting="KAUYON_PLAYERS",
    points=2,
    force_disposition=force_dispositions.RECONNAISSANCE,
    rule_text=(
        "During the third, fourth and fifth battle rounds, ranged weapons equipped by "
        "T'AU EMPIRE models from your army have the [SUSTAINED HITS 1] ability. During the "
        "third, fourth and fifth battle rounds, while a unit is a Guided unit (see For the "
        "Greater Good), each time a ranged attack is made by a model in that unit that "
        "targets a Spotted unit, you can ignore any or all modifiers to that attack's "
        "Ballistic Skill characteristic and/or all modifiers to the Hit roll."
    ),
    enhancements=[
        Enhancement("Exemplar of the Kauyon", 20),
        Enhancement("Precision of the Patient Hunter", 15),
        Enhancement("Solid-image Projection Unit", 20),
        Enhancement("Through Unity, Devastation", 30),
    ],
))

MONTKA = TAU_EMPIRE.add_detachment(Detachment(
    "Mont'ka",
    rule_name="Killing Blow",
    setting="MONTKA_PLAYERS",
    points=3,
    force_disposition=force_dispositions.PRIORITY_ASSETS,
    rule_text=(
        "During the first, second and third battle rounds, ranged weapons equipped by "
        "T'AU EMPIRE models from your army have the [ASSAULT] ability. During the first, "
        "second and third battle rounds, while a unit is a Guided unit, its ranged weapons "
        "have the [LETHAL HITS] ability."
    ),
    enhancements=[
        Enhancement("Coordinated Exploitation", 30),
        Enhancement("Exemplar of the Mont'ka", 10),
        Enhancement("Strategic Conqueror", 15),
        Enhancement("Strike Swiftly", 45),
    ],
))

EXPERIMENTAL_PROTOTYPE_CADRE = TAU_EMPIRE.add_detachment(Detachment(
    "Experimental Prototype Cadre",
    rule_name="Superior Craftsmanship",
    setting="EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS",
    points=1, tag="BATTLESUIT",
    force_disposition=force_dispositions.PRIORITY_ASSETS,
    rule_text=(
        'Friendly BATTLESUIT CHARACTER units\' ranged attacks have +6" Range.\n'
        "This detachment has the BATTLESUIT tag and cannot be taken with another "
        "BATTLESUIT detachment."
    ),
    enhancements=[
        Enhancement("Thermoneutronic Projector", 15),
        Enhancement("Plasma Accelerator Rifle", 20),
        Enhancement("Supernova Launcher", 15),
    ],
))

ADVANCED_ACQUISITION_CADRE = TAU_EMPIRE.add_detachment(Detachment(
    "Advanced Acquisition Cadre",
    rule_name="Expert Fieldcraft",
    setting="ADVANCED_ACQUISITION_CADRE_PLAYERS",
    points=1,
    force_disposition=force_dispositions.RECONNAISSANCE,
    rule_text=(
        "In your Shooting phase, when a friendly PATHFINDER TEAM/STEALTH BATTLESUITS unit "
        "is selected to shoot, those ranged attacks do not prevent your unit from being "
        "hidden."
    ),
    enhancements=[
        Enhancement("Negation Emitters", 15),
        Enhancement("Unmasking Suite", 15),
    ],
))

AUXILIARY_CADRE = TAU_EMPIRE.add_detachment(Detachment(
    "Auxiliary Cadre",
    rule_name="Integrated Command Structure",
    setting="AUXILIARY_CADRE_PLAYERS",
    points=1, tag="AUXILIARIES",
    force_disposition=force_dispositions.DISRUPTION,
    rule_text=(
        "Friendly KROOT/VESPID STINGWINGS units have the following ability:\n"
        'Harnessed Alien Instincts: In your Shooting phase, this unit can select one '
        'visible enemy unit within 12". That enemy unit is prey-marked: while a unit is '
        'prey-marked, that unit has +3" detection range.\n'
        "Friendly GHOSTKEEL BATTLESUIT/STEALTH BATTLESUITS units have the following "
        "ability:\n"
        'Localised Stealth Projectors (Aura): When a friendly KROOT/VESPID STINGWINGS unit '
        'within 6" of this unit has shot, those attacks do not prevent that unit from '
        "being hidden.\n"
        "This detachment has the AUXILIARIES tag and cannot be taken with another "
        "AUXILIARIES detachment."
    ),
    enhancements=[
        Enhancement("Student of Kauyon", 20),
        Enhancement("Admired Leader", 20),
    ],
))

# Baseline loadout for both model lines - Close combat weapon, Pulse pistol,
# Pulse rifle. The Shas'ui's Support Turret is deliberately NOT listed here:
# it's not part of the baseline loadout, only ever carried while
# game/support_turret.py's DS8 Support Turret ability grants it (Remain
# Stationary in the Movement phase), so build_squad() should never hand one
# out by default.
_STRIKE_TEAM_LOADOUT = [TauCloseCombatWeaponProfile, PulsePistolProfile, PulseRifleProfile]

_STRIKE_TEAM_LEADER = "Fire Warrior Shas'ui"

STRIKE_TEAM_RIFLE_TO_CARBINE = "Pulse Rifle -> Pulse Carbine"


def _strike_team_carbine_option(line_name):
    """Real wargear text (official app, screenshot): "Any number of Fire
    Warrior models can each have their pulse rifle replaced with 1 pulse
    carbine." Applied to BOTH model lines (the rank-and-file "Fire Warrior"
    line and the "Fire Warrior Shas'ui" leader line) - the text says "Fire
    Warrior models", and the Shas'ui's own datasheet title is "Fire Warrior
    Shas'ui", so read as including the leader too; flagged since the
    screenshot doesn't spell out whether the leader is meant to be
    excluded."""
    return WargearOption(line_name, replaces=PulseRifleProfile, with_weapons=[PulseCarbineProfile], name=STRIKE_TEAM_RIFLE_TO_CARBINE)


STRIKE_TEAM = TAU_EMPIRE.add_datasheet(Datasheet(
    "Strike Team",
    keywords=("BATTLELINE", "INFANTRY", "GRENADES", "MARKERLIGHT", "FIRE WARRIOR", "STRIKE TEAM"),
    model_lines=[
        ModelLine(FireWarriorShasUiProfile, 1, _STRIKE_TEAM_LOADOUT, name=_STRIKE_TEAM_LEADER),
        ModelLine(FireWarriorProfile, 9, _STRIKE_TEAM_LOADOUT, name="Fire Warrior"),
    ],
    # Support drones - real wargear text (official app, screenshot): "The
    # Fire Warrior Shas'ui can be equipped with up to two of the following,
    # and can take duplicates: guardian drone (cannot take duplicates of
    # this piece of wargear) / gun drone / marker drone / shield drone." So
    # duplicates ARE allowed except for Guardian Drone - corrects an earlier
    # pre-screenshot guess here that assumed "never the same one twice" for
    # all four (see game/drones.py's own docstring).
    gear_options=drone_options(_STRIKE_TEAM_LEADER, allow_duplicates=True),
    gear_slots={_STRIKE_TEAM_LEADER: DRONE_SLOTS},
    # Real wargear text (official app, screenshot): pulse rifle -> pulse
    # carbine, see _strike_team_carbine_option() above. The "Unselected
    # Profiles" reference block also listed a Twin Pulse Carbine and a
    # Missile Pod, but with no wargear-swap rule text of their own - same
    # documented gap as the Boyz datasheet's Wargear Options (see CLAUDE.md's
    # Später-Liste).
    wargear_options=[
        _strike_team_carbine_option(_STRIKE_TEAM_LEADER),
        _strike_team_carbine_option("Fire Warrior"),
    ],
    points=TAU_EMPIRE_POINTS["Strike Team"],  # 10 models 70 pts, no per-copy tiering; the carbine swap and the drone gear are both free on the list
    abilities_text=[
        'Suppression Volley: In your Shooting phase, after this unit has shot, select one enemy '
        'INFANTRY unit hit by one or more of those attacks. Until the start of your next turn, '
        'while unit is on the battlefield, that enemy unit is suppressed. While a unit is '
        'suppressed, each time a model in that unit makes an attack, subtract 1 from the Hit roll.',
        'DS8 Support Turret: In your Movement phase, if this unit Remains Stationary, until the '
        'start of your next turn, its Shas\'ui model is equipped with the support turret weapon.',
    ],
))

# Same baseline-loadout-excludes-the-conditional-turret reasoning as
# Strike Team's own _STRIKE_TEAM_LOADOUT above.
_BREACHER_TEAM_LOADOUT = [TauCloseCombatWeaponProfile, PulseBlasterProfile, PulsePistolProfile]
_BREACHER_TEAM_LEADER = "Breacher Fire Warrior Shas'ui"

BREACHER_TEAM = TAU_EMPIRE.add_datasheet(Datasheet(
    "Breacher Team",
    keywords=("BATTLELINE", "INFANTRY", "GRENADES", "MARKERLIGHT", "FIRE WARRIOR", "BREACHER TEAM"),
    model_lines=[
        ModelLine(BreacherFireWarriorShasUiProfile, 1, _BREACHER_TEAM_LOADOUT, name=_BREACHER_TEAM_LEADER),
        ModelLine(BreacherFireWarriorProfile, 9, _BREACHER_TEAM_LOADOUT, name="Breacher Fire Warrior"),
    ],
    gear_options=drone_options(_BREACHER_TEAM_LEADER),
    gear_slots={_BREACHER_TEAM_LEADER: DRONE_SLOTS},
    # Same documented gap as Strike Team: "Unselected Profiles" (Twin Pulse
    # Carbine, Missile Pod - both already exist in game/weapons.py, shared
    # with Strike Team's own alternates) without the actual wargear-swap
    # rule text, so no wargear_options yet.
    points=TAU_EMPIRE_POINTS["Breacher Team"],  # 10 models 90 pts, no per-copy tiering
    abilities_text=[
        'Breach and Clear: Each time a model in this unit makes a ranged attack that targets an '
        'enemy unit within range of an objective marker, you can re-roll the Wound roll.',
        'DS8 Support Turret: In your Movement phase, if this unit Remains Stationary, until the '
        'start of your next turn, its Shas\'ui model is equipped with the support turret weapon.',
    ],
))

_LONG_QUILL_LOADOUT = [KrootCloseCombatWeaponProfile, KrootPistolProfile, KrootRifleProfile]
_KROOT_CARNIVORE_LOADOUT = [KrootCloseCombatWeaponProfile, KrootRifleProfile]

KROOT_CARNIVORES = TAU_EMPIRE.add_datasheet(Datasheet(
    "Kroot Carnivores",
    # Notably no BATTLELINE/MARKERLIGHT here (unlike Strike/Breacher Team) -
    # not listed on this datasheet's own Keywords line, matching Kroot lore
    # as T'au auxiliaries rather than "true" T'au.
    keywords=("INFANTRY", "GRENADES", "KROOT", "CARNIVORES"),
    model_lines=[
        ModelLine(LongQuillProfile, 1, _LONG_QUILL_LOADOUT, name="Long-quill"),
        ModelLine(KrootCarnivoreProfile, 9, _KROOT_CARNIVORE_LOADOUT, name="Kroot Carnivores"),
    ],
    # Same documented gap as Strike/Breacher Team: "Unselected Profiles"
    # (Tanglebomb Launcher, Kroot Carbine - see game/weapons.py) without the
    # actual wargear-swap rule text, so no wargear_options yet.
    # The list prices both of this datasheet's own composition options (10
    # models 65 pts / 20 models 130 pts) - the 20-model build isn't modeled
    # yet (composition_options is None here), so points_for() can only price
    # the 10-model one until it is.
    points=TAU_EMPIRE_POINTS["Kroot Carnivores"],
    abilities_text=[
        'Fieldcraft: At the end of the your Command phase, if this unit within range of an '
        'objective marker you control, that objective marker remains under your control, even '
        'if you have no models within range of it, until your opponent controls it at the start '
        'or end of any turn.',
        'Bodyguard: If this unit has a Starting Strength of 20, you can attach up to two Leader '
        'units to it instead of one, provided those Leaders are not duplicates (e.g. you cannot '
        'attach two WAR SHAPERS to this unit). If you do, and this unit is destroyed, the Leader '
        'units attached to it become separate units with their original Starting Strengths.',
    ],
))
# Bodyguard is NOT engine-wired: it's entirely a Muster Armies-time
# attachment decision (how many/which Leaders form this unit) plus a
# "splits back apart if destroyed" runtime behavior - both depend on the
# live attached-unit-formation flow this engine deliberately doesn't have
# yet (see CLAUDE.md's Später-Liste, Attached Units entry). "Scouts 7\""
# and "Stealth" are Rules, not Abilities - see KrootCarnivoreProfile's own
# `scouts`/`stealth` fields (Stealth is fully implemented, rule 24.33;
# Scouts is stored but still deferred, see UnitProfile.scouts).

# --- The three Kroot Shapers ---
#
# One datasheet each, but they share a stat line (KrootShaperProfile in
# game/units.py), the same four core abilities and the same LEADER line, so
# they are kept together here. None of them has a wargear option except the
# War Shaper's single weapon swap, and none has drone gear - they are Kroot.

_FLESH_SHAPER_LINE = "Kroot Flesh Shaper"
_FLESH_SHAPER_LOADOUT = [KrootScattergunProfile, TwinRitualisticBladesProfile]

KROOT_FLESH_SHAPER = TAU_EMPIRE.add_datasheet(Datasheet(
    "Kroot Flesh Shaper",
    keywords=("INFANTRY", "CHARACTER", "KROOT", "SHAPER", "FLESH SHAPER"),
    model_lines=[
        ModelLine(KrootFleshShaperProfile, 1, _FLESH_SHAPER_LOADOUT, name=_FLESH_SHAPER_LINE),
    ],
    points=TAU_EMPIRE_POINTS["Kroot Flesh Shaper"],
    abilities_text=[
        'Ritual Butchery: While this model is leading a unit, melee weapons equipped by models '
        'in that unit have the [SUSTAINED HITS 1] ability.',
        'Rites of Feasting: While this model is leading a unit, models in that unit have the '
        'Feel No Pain 6+ ability. If that unit destroys one or more enemy units in the Fight '
        'phase, until the end of the battle, models in that unit have the Feel No Pain 5+ '
        'ability instead.',
        'Core: Infiltrators, Leader, Scouts 7", Stealth.',
        'Leader: This model can be attached to the following units: Kroot Carnivores, '
        'Kroot Farstalkers.',
    ],
))
# Both abilities are engine-wired: Ritual Butchery is a FightController.
# _adjusted_weapon() chain entry (game/ritual_butchery.py), Rites of Feasting
# is a fold in game/feel_no_pain.py's current_feel_no_pain()
# (game/rites_of_feasting.py). Leader is enforced by game/attached_units.py's
# can_attach(), which reads the pairing off this list's own `leads` table -
# note that KROOT FARSTALKERS is named there but has no datasheet yet, the
# same dangling half a pairing that Crisis Fireknife already has.

_TRAIL_SHAPER_LINE = "Kroot Trail Shaper"
_TRAIL_SHAPER_LOADOUT = [KrootRifleProfile, ShapersBladeProfile]

KROOT_TRAIL_SHAPER = TAU_EMPIRE.add_datasheet(Datasheet(
    "Kroot Trail Shaper",
    keywords=("INFANTRY", "CHARACTER", "KROOT", "SHAPER", "TRAIL SHAPER"),
    model_lines=[
        ModelLine(KrootTrailShaperProfile, 1, _TRAIL_SHAPER_LOADOUT, name=_TRAIL_SHAPER_LINE),
    ],
    points=TAU_EMPIRE_POINTS["Kroot Trail Shaper"],
    abilities_text=[
        'Trail Finding: In your opponent\'s Movement phase, if an enemy unit ends a move within '
        '8" of this unit, if this unit is not within Engagement Range of one or more enemy '
        'units, this unit can make a Normal move of up to D6". '
        'NOT ENGINE-WIRED - see the note below this datasheet.',
        'Kroot Ambush: After both players have deployed their armies, you can redeploy this '
        'model\'s unit and one other friendly KROOT unit. When doing so, any of those units can '
        'be placed into Strategic Reserves, regardless of how many units are already in '
        'Strategic Reserves. NOT ENGINE-WIRED - see the note below this datasheet.',
        'Core: Infiltrators, Leader, Scouts 7", Stealth.',
        'Leader: This model can be attached to the following units: Kroot Carnivores, '
        'Kroot Farstalkers.',
    ],
))
# NEITHER ability is engine-wired, and both are recorded above and asserted in
# test_kroot_shapers.py so that adding either is a visible change:
#
# - Trail Finding is a reactive move, and this engine HAS the machinery for
#   those (MovementController.REACTIVE_MOVE_MODES, which every reactive mover
#   must register with). What it does not have is a trigger for "an enemy unit
#   just ENDED a move" - every existing reactive move hangs off an attack or a
#   charge, so the hook would be the new work, not the move.
# - Kroot Ambush is a redeployment step in the Pre-game Sequence (03.01) that
#   also overrides 20.01's Strategic Reserves cap. That is a new step in
#   game/pregame.py, not an ability on a unit.
#
# Core abilities ARE wired, on the profile: Infiltrators (24.20), Scouts 7"
# (24.31, read by game/scouts.py), Stealth (24.33) and Leader (19.01).

_WAR_SHAPER_LINE = "Kroot War Shaper"
_WAR_SHAPER_LOADOUT = [DartBowAndTriBladeProfile, KrootPistolProfile, ShapersBladeProfile]

WAR_SHAPER_DART_BOW_TO_BLADESTAVE = "Dart-bow and Tri-blade -> Bladestave and Prey-hook"

KROOT_WAR_SHAPER = TAU_EMPIRE.add_datasheet(Datasheet(
    "Kroot War Shaper",
    keywords=("INFANTRY", "CHARACTER", "KROOT", "SHAPER", "WAR SHAPER"),
    model_lines=[
        ModelLine(KrootWarShaperProfile, 1, _WAR_SHAPER_LOADOUT, name=_WAR_SHAPER_LINE),
    ],
    # "This model's dart-bow and tri-bade can be replaced with 1 bladestave and
    # prey-hook" (the printed line has that typo). A RANGED weapon traded for a
    # MELEE one, which is unusual but exactly what it says - the swap leaves him
    # with only the Kroot pistol at range.
    wargear_options=[
        WargearOption(_WAR_SHAPER_LINE, DartBowAndTriBladeProfile,
                      [BladestaveAndPreyHookProfile], max_models=1,
                      name=WAR_SHAPER_DART_BOW_TO_BLADESTAVE),
    ],
    points=TAU_EMPIRE_POINTS["Kroot War Shaper"],
    abilities_text=[
        'War Leader: Once per battle round, one unit from your army with this ability can use '
        'it when its unit is targeted with a Stratagem. If it does, reduce the CP cost of that '
        'use of that Stratagem by 1CP.',
        'Root of Honour: Once per battle, at the start of any phase, you can select one friendly '
        'KROOT unit that is Battle-shocked and within 12" of this model. That unit is no longer '
        'Battle-shocked.',
        'Core: Infiltrators, Leader, Scouts 7", Stealth.',
        'Leader: This model can be attached to the following units: Kroot Carnivores, '
        'Kroot Farstalkers.',
    ],
))
# Both abilities are engine-wired: War Leader is a StratagemController.
# cost_discounts collaborator (game/war_leader.py - the fifth, and word for
# word the Necron Overlord's My Will Be Done), Root of Honour is its own small
# controller offered at every phase boundary (game/root_of_honour.py).

# --- Ethereal ---

_ETHEREAL_LINE = "Ethereal"

ETHEREAL = TAU_EMPIRE.add_datasheet(Datasheet(
    "Ethereal",
    keywords=("INFANTRY", "CHARACTER", "ETHEREAL"),
    model_lines=[
        ModelLine(EtherealProfile, 1, [HonourStaveProfile], name=_ETHEREAL_LINE),
    ],
    # Two INDEPENDENT printed menus - "1 hover drone" on its own line, and "up
    # to two of the following, and can take duplicates" for the drone trio. So
    # two groups, the same arrangement Pathfinder Team's Shas'ui needs, rather
    # than one cap of three that would let a hover drone eat a gun drone's slot.
    gear_options=(drone_options(_ETHEREAL_LINE, include_guardian=False,
                                allow_duplicates=True)
                  + [hover_drone_gear(_ETHEREAL_LINE)]),
    gear_slots={_ETHEREAL_LINE: {DRONE_GROUP: DRONE_SLOTS,
                                 HOVER_DRONE_GROUP: HOVER_DRONE_SLOTS}},
    points=TAU_EMPIRE_POINTS["Ethereal"],
    abilities_text=[
        'Failure Is Not an Option: While this model is leading a unit, models in that unit have '
        'the Feel No Pain 5+ ability.',
        'Coordinated Leadership: At the end of your Command phase, roll one D6: on a 4+, you '
        'gain 1CP.',
        'Hover Drone (wargear): The bearer can FLY and has a Move characteristic of 10".',
        'Core: Leader.',
        'Leader: This model can be attached to the following units: Breacher Team, Strike Team.',
    ],
))
# All three are engine-wired: Failure Is Not an Option is a fold in
# game/feel_no_pain.py (game/failure_is_not_an_option.py - the THIRD datasheet
# to print that exact sentence, after Dok's Toolz and Rites of Reanimation),
# Coordinated Leadership is its own end-of-Command-phase dice queue
# (game/coordinated_leadership.py), the Hover Drone is a Gear effect
# (game/drones.py). His printed 5+ invulnerable save is on the profile.

# --- Darkstrider ---

_DARKSTRIDER_LINE = "Darkstrider"

DARKSTRIDER = TAU_EMPIRE.add_datasheet(Datasheet(
    "Darkstrider",
    keywords=("INFANTRY", "CHARACTER", "EPIC HERO", "MARKERLIGHT", "DARKSTRIDER"),
    model_lines=[
        ModelLine(DarkstriderProfile, 1,
                  [ShadeProfile, DarkstriderCloseCombatWeaponProfile],
                  name=_DARKSTRIDER_LINE),
    ],
    points=TAU_EMPIRE_POINTS["Darkstrider"],
    abilities_text=[
        'Structural Analyser: While this model is leading a unit, each time a model in that unit '
        'makes a ranged attack, add 1 to the Wound roll.',
        'Jammer Array: Enemy units that are set up on the battlefield from Reserves cannot be set '
        'up within 12" of this model. NOT ENGINE-WIRED - see the note below this datasheet.',
        'Core: Infiltrators, Leader, Scouts 7".',
        'Leader: This model can be attached to the following unit: Pathfinder Team.',
    ],
))
# Structural Analyser is engine-wired (a ShootingController._wound_modifiers()
# entry, see game/structural_analyser.py). JAMMER ARRAY IS NOT, and it is the
# only ability in this batch whose absence is not about missing machinery but
# about direction: it constrains where the OPPONENT may arrive from Reserves
# (20.04), and no ability in this engine has ever restricted the other
# player's placement. Recorded above and asserted in test_tau_characters.py so
# that adding it is a visible change.

# --- Firesight Team ---

_FIRESIGHT_LINE = "Firesight Marksman"

FIRESIGHT_TEAM = TAU_EMPIRE.add_datasheet(Datasheet(
    "Firesight Team",
    keywords=("INFANTRY", "CHARACTER", "MARKERLIGHT", "FIRESIGHT TEAM"),
    # ONE model, despite the plural datasheet name: the printed Designer's Note
    # makes the Marksman and his two sniper drones a single model for all rules
    # purposes, and says the drones "do not count as models for any rules
    # purposes". That is also why the rifle profile's name is plural.
    model_lines=[
        ModelLine(FiresightMarksmanProfile, 1,
                  [LongshotPulseRiflesProfile, PulsePistolBs3Profile,
                   FiresightCloseCombatWeaponsProfile],
                  name=_FIRESIGHT_LINE),
    ],
    # The datasheet's own Wargear Options section reads "None" - the first one
    # in this faction that says so explicitly rather than omitting the section.
    points=TAU_EMPIRE_POINTS["Firesight Team"],
    abilities_text=[
        'Precise Targeting: Each time a model in this unit makes an attack that targets a Spotted '
        'unit, you can re-roll the Hit roll.',
        "Designer's Note: The Firesight Marksman model and sniper drone models are treated as a "
        'single model for all rules purposes. All distances are measured to and from the Firesight '
        'Marksman model. The sniper drone models do not count as models for any rules purposes.',
        'Core: Infiltrators, Lone Operative, Stealth.',
    ],
))
# Precise Targeting is engine-wired as a ShootingController._hit_reroll_reason()
# entry (game/precise_targeting.py), reading the Spotted mark the T'au army rule
# already sets (game/greater_good.py). Shooting only, and that is not a
# simplification - Spotted expires at the end of the Shooting phase, so no melee
# attack can ever target a Spotted unit.

# --- Kroot Lone-Spear ---

_LONE_SPEAR_LINE = "Kroot Lone-Spear"
_LONE_SPEAR_LOADOUT = [KrootLongGunProfile, LoneSpearCloseCombatWeaponProfile,
                       KalamandrasBiteProfile]

LONE_SPEAR_LONG_GUN_TO_JAVELINS = "Kroot Long Gun -> Blast Javelin + Hunting Javelin"

KROOT_LONE_SPEAR = TAU_EMPIRE.add_datasheet(Datasheet(
    "Kroot Lone-Spear",
    keywords=("MOUNTED", "CHARACTER", "KROOT", "LONE-SPEAR"),
    model_lines=[
        ModelLine(KrootLoneSpearProfile, 1, _LONE_SPEAR_LOADOUT, name=_LONE_SPEAR_LINE),
    ],
    # "This model's Kroot long gun can be replaced with 1 blast javelin and 1
    # hunting javelin" - ONE weapon given up for TWO, one ranged and one melee.
    wargear_options=[
        WargearOption(_LONE_SPEAR_LINE, KrootLongGunProfile,
                      [BlastJavelinProfile, HuntingJavelinProfile], max_models=1,
                      name=LONE_SPEAR_LONG_GUN_TO_JAVELINS),
    ],
    points=TAU_EMPIRE_POINTS["Kroot Lone-spear"],
    abilities_text=[
        'Advanced Scouting: Each time this model makes a ranged attack that hits an enemy unit, '
        'until the end of the turn, each time another KROOT model from your army makes an attack '
        'that targets that enemy unit, you can re-roll the Hit roll.',
        'Fire and Fade: In your Shooting phase, after this model has shot, if it is not within '
        'Engagement Range of one or more enemy units, it can make a Normal move of up to 6". If '
        'it does, until the end of the turn, this model is not eligible to declare a charge.',
        'Core: Lone Operative, Scouts 7", Stealth.',
    ],
))
# Both abilities are engine-wired: Advanced Scouting is a mark on the TARGET
# placed by a hit and read by both attack steps (game/advanced_scouting.py),
# Fire and Fade is a MovementController.start_post_shooting_move() consumer -
# Asurmen's Tactical Acumen with the printed Engagement Range condition added
# (game/fire_and_fade.py). His base is the equal-area circle of the printed
# 90 x 52 mm oval, the same conversion the Ghostkeel and Riptide already use.

# --- Commander in Enforcer Battlesuit ---

_ENFORCER_LINE = "Commander in Enforcer Battlesuit"

# The first printed menu: "this model's burst cannon can be replaced with one
# of the following", nine items. Six are weapons and are modelled here - they
# all give up the SAME weapon, so build_squad()'s shared cursor already makes
# them mutually exclusive, which is exactly what "one of the following" means.
#
# The other three items in that menu (battlesuit support system, shield
# generator, weapon support system) trade a WEAPON for a non-weapon, and
# WargearOption has no way to express that - it swaps weapons for weapons. They
# are NOT offered here; all three are available in the second menu below, which
# is where a build would realistically take them. Recorded rather than silently
# dropped, and asserted in test_tau_characters.py.
ENFORCER_BURST_TO_AIRBURSTING = "Burst Cannon -> Airbursting Fragmentation Projector"
ENFORCER_BURST_TO_CYCLIC_ION = "Burst Cannon -> Cyclic Ion Blaster"
ENFORCER_BURST_TO_FUSION = "Burst Cannon -> Fusion Blaster"
ENFORCER_BURST_TO_MISSILE_POD = "Burst Cannon -> Missile Pod"
ENFORCER_BURST_TO_PLASMA = "Burst Cannon -> Plasma Rifle"
ENFORCER_BURST_TO_FLAMER = "Burst Cannon -> T'au Flamer"

_ENFORCER_BURST_SWAPS = [
    (ENFORCER_BURST_TO_AIRBURSTING, AirburstingFragmentationProjectorProfile),
    (ENFORCER_BURST_TO_CYCLIC_ION, CyclicIonBlasterStandardProfile),
    (ENFORCER_BURST_TO_FUSION, FusionBlasterProfile),
    (ENFORCER_BURST_TO_MISSILE_POD, MissilePodProfile),
    (ENFORCER_BURST_TO_PLASMA, PlasmaRifleProfile),
    (ENFORCER_BURST_TO_FLAMER, TauFlamerProfile),
]

COMMANDER_IN_ENFORCER_BATTLESUIT = TAU_EMPIRE.add_datasheet(Datasheet(
    "Commander in Enforcer Battlesuit",
    keywords=("VEHICLE", "WALKER", "FLY", "CHARACTER", "BATTLESUIT",
              "COMMANDER IN ENFORCER BATTLESUIT"),
    model_lines=[
        ModelLine(EnforcerCommanderProfile, 1,
                  [BurstCannonProfile, CrisisBattlesuitFistsProfile], name=_ENFORCER_LINE),
    ],
    wargear_options=[
        WargearOption(_ENFORCER_LINE, BurstCannonProfile, [cls], max_models=1, name=label)
        for label, cls in _ENFORCER_BURST_SWAPS
    ],
    # TWO independent printed menus again, like the Ethereal: "up to two of the
    # following [drones], and can take duplicates" and "up to three of the
    # following", the second mixing guns with the three support systems. Two
    # groups, so a support system can never eat a drone slot.
    gear_options=(drone_options(_ENFORCER_LINE, include_guardian=False, allow_duplicates=True)
                  + support_menu_gear(_ENFORCER_LINE, [
                      # The starred items cannot be duplicated; the rest can,
                      # up to the menu's own cap of three.
                      ("Airbursting Fragmentation Projector",
                       AirburstingFragmentationProjectorProfile, 1),
                      ("Burst Cannon", BurstCannonProfile, 3),
                      ("Cyclic Ion Blaster", CyclicIonBlasterStandardProfile, 1),
                      ("Fusion Blaster", FusionBlasterProfile, 3),
                      ("Missile Pod", MissilePodProfile, 3),
                      ("Plasma Rifle", PlasmaRifleProfile, 3),
                      ("T'au Flamer", TauFlamerProfile, 3),
                  ])),
    gear_slots={_ENFORCER_LINE: {DRONE_GROUP: DRONE_SLOTS,
                                 BATTLESUIT_SUPPORT_GROUP: BATTLESUIT_SUPPORT_SLOTS}},
    points=TAU_EMPIRE_POINTS["Commander in Enforcer Battlesuit"],
    abilities_text=[
        'Enforcer Commander: While this model is leading a unit, each time a ranged attack targets '
        'that unit, worsen the Armour Penetration characteristic of that attack by 1.',
        'Battlesuit Support System (wargear): The bearer\'s unit is eligible to shoot in a turn in '
        'which it Fell Back, but when doing so only models equipped with this wargear can make '
        'ranged attacks. THE SECOND CLAUSE IS NOT ENFORCED - this engine has no per-model shooting '
        'gate; see game/battlesuit_wargear.py.',
        'Shield Generator (wargear): The bearer has a 4+ invulnerable save.',
        'Weapon Support System (wargear): Each time the bearer makes a ranged attack, you can '
        'ignore any or all modifiers to the Hit roll.',
        'Core: Deep Strike, Leader.',
        'Leader: This model can be attached to the following units: Crisis Battlesuits, Crisis '
        'Fireknife Battlesuits, Crisis Starscythe Battlesuits, Crisis Sunforge Battlesuits.',
    ],
))
# Enforcer Commander is engine-wired in game/damage_resolution.py's
# save_thresholds() - the same slot as the Battlewagon's Ramshackle but Rugged,
# because both are defender-side AP adjustments and that is the one place the
# panel and the resolution agree about a save (see game/enforcer_commander.py).
# All three support systems are wired to fields other datasheets already use.

# --- Commander Shadowsun ---

_SHADOWSUN_LINE = "Commander Shadowsun"

COMMANDER_SHADOWSUN = TAU_EMPIRE.add_datasheet(Datasheet(
    "Commander Shadowsun",
    # INFANTRY, not VEHICLE, unlike every other Commander here - which is what
    # lets her have Infiltrators and Stealth at all.
    keywords=("INFANTRY", "FLY", "CHARACTER", "EPIC HERO", "BATTLESUIT",
              "COMMANDER SHADOWSUN"),
    model_lines=[
        # "2 high-energy fusion blasters" - the same listing-a-class-twice
        # technique the Devilfish's seeker missiles use.
        ModelLine(CommanderShadowsunProfile, 1,
                  [FlechetteLauncherProfile,
                   HighEnergyFusionBlasterProfile, HighEnergyFusionBlasterProfile,
                   LightMissilePodProfile, PulsePistolBs3Profile,
                   CrisisBattlesuitFistsProfile],
                  name=_SHADOWSUN_LINE),
    ],
    # No wargear options and no drone MENU: her two drones are printed as part
    # of her fixed equipment line, so their abilities are profile flags rather
    # than Gear items a build could decline.
    points=TAU_EMPIRE_POINTS["Commander Shadowsun"],
    abilities_text=[
        'Agile Combatant: This model is eligible to shoot in a turn in which it Fell Back.',
        'Hero of the Empire (Aura): While a friendly T\'AU EMPIRE unit is within 6" of this model, '
        'each time a model in that unit makes a ranged attack, re-roll a Hit roll of 1.',
        'Advanced Guardian Drone (wargear): Each time a ranged attack targets the bearer, subtract '
        '1 from the Wound roll.',
        'Command-link Drone (wargear, Aura): While a friendly T\'AU EMPIRE unit is within 6" of the '
        'bearer, each time you select that unit as the target of a Stratagem, roll one D6: on a '
        '5+, you gain 1CP. NOT ENGINE-WIRED - see the note below this datasheet.',
        'Supreme Commander: If this model is in your army, it must be your Warlord. A documented '
        'NO-OP - this engine has no Warlord concept.',
        'Core: Infiltrators, Lone Operative, Stealth.',
    ],
))
# Three of the five are engine-wired: Agile Combatant at the same Fall Back
# gate as Battlesuit Support System and War Construct (game/squad.py's
# squad_has_agile_combatant()), Hero of the Empire as one more automatic-1s
# source in the hit step - the only AURA among them - and the Advanced Guardian
# Drone as a per-MODEL wound malus (game/drones.py), which is the bearer-only
# form of the unit-wide Guardian Drone.
#
# THE COMMAND-LINK DRONE IS NOT WIRED: StratagemController has no per-use hook
# a listener could hang a D6 on, and adding one changes the Stratagem flow
# rather than this datasheet. SUPREME COMMANDER is a documented no-op - there
# is no Warlord concept here at all, the same status as the Void Dragon's
# Enslaved Star God. Both are recorded above and asserted in
# test_tau_characters.py.

# --- Kroot Hounds ---

_KROOT_HOUNDS_LINE = "Kroot Hounds"

KROOT_HOUNDS = TAU_EMPIRE.add_datasheet(Datasheet(
    "Kroot Hounds",
    keywords=("BEASTS", "KROOT", "HOUNDS"),
    # 5-10 models, both sizes priced - so both are modelled, unlike Kroot
    # Carnivores, whose 20-model build is priced but not built.
    composition_options=[
        [ModelLine(KrootHoundProfile, 5, [RippingFangsProfile], name=_KROOT_HOUNDS_LINE)],
        [ModelLine(KrootHoundProfile, 10, [RippingFangsProfile], name=_KROOT_HOUNDS_LINE)],
    ],
    points=TAU_EMPIRE_POINTS["Kroot Hounds"],
    abilities_text=[
        'Loping Pounce: At the start of your Command phase, if this unit is within 6" of one or '
        'more friendly KROOT INFANTRY units, then until the end of the turn, this unit is eligible '
        'to declare a charge in a turn in which it Advanced.',
        'Hunting Hounds: While this unit is within 12" of one or more friendly KROOT CHARACTER '
        'models, the Objective Control characteristic of models in this unit is 1.',
        'Core: Scouts 7", Stealth.',
    ],
))
# Both are engine-wired, and their DURATIONS differ by one word - Loping Pounce
# is latched at the start of the Command phase and holds all turn
# (game/loping_pounce.py, read at game/charge.py's own advance gate next to
# Waaagh! and Full Throttle), Hunting Hounds is a live "while" and is read
# through game/objective_control.py, the sixteenth extraction.

# --- Vespid Stingwings ---

_VESPID_LEADER = "Vespid Strain Leader"
_VESPID_LINE = "Vespid Stingwings"
_VESPID_LOADOUT = [NeutronBlasterProfile, StingwingClawsProfile]

VESPID_BLASTER_TO_FLAMER = "Neutron Blaster -> T'au Flamer"
VESPID_BLASTER_TO_GRENADE_LAUNCHER = "Neutron Blaster -> Neutron Grenade Launcher"
VESPID_BLASTER_TO_RAIL_RIFLE = "Neutron Blaster -> Neutron Rail Rifle"

VESPID_STINGWINGS = TAU_EMPIRE.add_datasheet(Datasheet(
    "Vespid Stingwings",
    keywords=("INFANTRY", "FLY", "VESPID STINGWINGS"),
    composition_options=[
        [ModelLine(VespidStrainLeaderProfile, 1, _VESPID_LOADOUT, name=_VESPID_LEADER),
         ModelLine(VespidStingwingProfile, 4, _VESPID_LOADOUT, name=_VESPID_LINE)],
        [ModelLine(VespidStrainLeaderProfile, 1, _VESPID_LOADOUT, name=_VESPID_LEADER),
         ModelLine(VespidStingwingProfile, 9, _VESPID_LOADOUT, name=_VESPID_LINE)],
    ],
    # Every option is printed under "If this unit contains 10 models" - which
    # `per_models=10` expresses exactly, and better than a hand-written
    # condition would: at 5 models the cap computes to 0 and the option simply
    # is not available, at 10 it is 1. The Oversight Drone is Gear and carries
    # the same ratio for the same reason.
    wargear_options=[
        WargearOption(_VESPID_LINE, NeutronBlasterProfile, [TauFlamerProfile],
                      per_models=10, name=VESPID_BLASTER_TO_FLAMER),
        WargearOption(_VESPID_LINE, NeutronBlasterProfile, [NeutronGrenadeLauncherProfile],
                      per_models=10, name=VESPID_BLASTER_TO_GRENADE_LAUNCHER),
        WargearOption(_VESPID_LINE, NeutronBlasterProfile, [NeutronRailRifleProfile],
                      per_models=10, name=VESPID_BLASTER_TO_RAIL_RIFLE),
    ],
    gear_options=[oversight_drone_gear(_VESPID_LEADER)],
    gear_slots={_VESPID_LEADER: 1},
    points=TAU_EMPIRE_POINTS["Vespid Stingwings"],
    abilities_text=[
        'Airborne Agility: At the end of your opponent\'s turn, if this unit is not within '
        'Engagement Range of one or more enemy units, you can remove it from the battlefield and '
        'place it into Strategic Reserves.',
        'Oversight Drone (wargear): Once per battle, when the bearer\'s unit is selected to shoot, '
        'until the end of the phase, ranged weapons equipped by models in this unit have the '
        '[IGNORES COVER] ability.',
        'Core: Deep Strike.',
    ],
))
# Both engine-wired: Airborne Agility through game/strategic_reserves.py's own
# withdraw_to_reserves() (game/airborne_agility.py), the Oversight Drone as a
# ShootingController collaborator offered from start_shooting() only - Nova
# Charge's shape, and for the same reason (game/oversight_drone.py).

# --- Krootox Riders ---

_KROOTOX_RIDERS_LINE = "Krootox Riders"
_KROOTOX_RIDERS_LOADOUT = [RepeaterCannonProfile, KrootCloseCombatWeaponProfile,
                           KrootoxFistsProfile]

KROOTOX_REPEATER_TO_TANGLECANNON = "Repeater Cannon -> Tanglecannon"

KROOTOX_RIDERS = TAU_EMPIRE.add_datasheet(Datasheet(
    "Krootox Riders",
    keywords=("MOUNTED", "GRENADES", "KROOT", "KROOTOX RIDERS"),
    composition_options=[
        [ModelLine(KrootoxRiderProfile, n, _KROOTOX_RIDERS_LOADOUT, name=_KROOTOX_RIDERS_LINE)]
        for n in (1, 2, 3)
    ],
    # "ANY NUMBER of models can each have..." - so no cap at all, which is what
    # leaving both max_models and per_models unset means.
    wargear_options=[
        WargearOption(_KROOTOX_RIDERS_LINE, RepeaterCannonProfile, [TanglecannonProfile],
                      name=KROOTOX_REPEATER_TO_TANGLECANNON),
    ],
    points=TAU_EMPIRE_POINTS["Krootox Riders"],
    abilities_text=[
        'Kroot Packmates: Once per turn, in your opponent\'s Shooting phase, when a friendly KROOT '
        'INFANTRY unit within 6" of this unit is selected as the target of an attack, one unit '
        'from your army with this ability can use it. If it does, after that enemy unit has '
        'finished making its attacks, that unit with this ability can shoot as if it were your '
        'Shooting phase, but when resolving those attacks it can only target that enemy unit (and '
        'only if it is an eligible target).',
        'Core: Scouts 7".',
    ],
))
# Kroot Packmates is engine-wired: word for word Awakened Dynasty's Protocol of
# the Vengeful Stars minus the CP, so it reuses
# ShootingController.start_reactive_shooting(restrict_to=...) unchanged - see
# game/kroot_packmates.py, where the four separate trigger conditions are set
# out one by one.

# --- Krootox Rampagers ---

_KROOTOX_RAMPAGERS_LINE = "Krootox Rampagers"
_KROOTOX_RAMPAGERS_LOADOUT = [KrootPistolAndHuntingJavelinsProfile,
                              RampagerCloseCombatWeaponProfile,
                              RampagerKrootoxFistsProfile]

KROOTOX_RAMPAGERS = TAU_EMPIRE.add_datasheet(Datasheet(
    "Krootox Rampagers",
    keywords=("MOUNTED", "GRENADES", "KROOT", "KROOTOX RAMPAGERS"),
    composition_options=[
        [ModelLine(KrootoxRampagerProfile, n, _KROOTOX_RAMPAGERS_LOADOUT,
                   name=_KROOTOX_RAMPAGERS_LINE)]
        for n in (3, 6)
    ],
    # No wargear options printed at all.
    points=TAU_EMPIRE_POINTS["Krootox Rampagers"],
    abilities_text=[
        'Kroot Linebreakers: Each time this unit ends a Charge move, select one enemy unit within '
        'Engagement Range of it, then roll one D6 for each model in this unit that is within '
        'Engagement Range of that enemy unit: for each 4+, that enemy unit suffers D3 mortal '
        'wounds. If one or more enemy models are destroyed as a result of these mortal wounds, '
        'that enemy unit must take a Battle-shock test.',
        'Core: Scouts 7".',
    ],
))
# Kroot Linebreakers is engine-wired as a fifth ability in
# game/mortal_wound_abilities.py, on the same ChargeController.
# on_charge_move_finished hook the Skorpekh Lord's Crimson Harvest uses. Its
# Unit Composition line names "hunting blades" and "Rampager fists" where the
# weapon TABLE says "Close combat weapon" and "Krootox fists" - the table
# carries the numbers, so the table's names are used.

# --- Kroot Farstalkers ---

_KILL_BROKER_LINE = "Kroot Kill-broker"
_FARSTALKER_LINE = "Kroot Farstalkers"
_FARSTALKER_HOUND_LINE = "Kroot Hounds"

KILL_BROKER_FIREARM_TO_TAU_TECH = "Farstalker Firearm -> T'au-tech Rifle"
FARSTALKER_FIREARM_TO_SKINNER = "Farstalker Firearm -> Dvorgite Skinner"
FARSTALKER_FIREARM_TO_TRIBALEST = "Farstalker Firearm -> Londaxi Tribalest"

KROOT_FARSTALKERS = TAU_EMPIRE.add_datasheet(Datasheet(
    "Kroot Farstalkers",
    keywords=("INFANTRY", "KROOT", "GRENADES", "FARSTALKERS"),
    # THREE model lines from TWO printed stat rows: the Kill-broker shares the
    # Farstalkers' row (differing only in base size) and the two Kroot Hounds
    # have their own - with Leadership 7+ rather than the 8+ their own
    # datasheet prints, which is why FarstalkerHoundProfile exists.
    model_lines=[
        ModelLine(KrootKillBrokerProfile, 1,
                  [FarstalkerFirearmProfile, KrootPistolProfile, RitualBladeProfile],
                  name=_KILL_BROKER_LINE),
        ModelLine(KrootFarstalkerProfile, 9,
                  [FarstalkerFirearmProfile, KrootPistolProfile,
                   KrootCloseCombatWeaponProfile],
                  name=_FARSTALKER_LINE),
        ModelLine(FarstalkerHoundProfile, 2, [RippingFangsProfile],
                  name=_FARSTALKER_HOUND_LINE),
    ],
    wargear_options=[
        WargearOption(_KILL_BROKER_LINE, FarstalkerFirearmProfile, [TauTechRifleProfile],
                      max_models=1, name=KILL_BROKER_FIREARM_TO_TAU_TECH),
        # "1 Kroot Farstalker's Farstalker firearm can be replaced with ONE OF
        # the following" - one MODEL and one WEAPON between the two options.
        #
        # KNOWN LIMITATION, measured and pinned in test_tau_kroot_and_vespid.py
        # rather than assumed away: two options that give up the same weapon
        # share build_squad()'s cursor, which makes them NON-OVERLAPPING (they
        # land on different models) rather than EXCLUSIVE - so a build can
        # currently take both, on two models. On a single-model line the two
        # readings coincide, which is why the Enforcer's six-way burst-cannon
        # menu above needs nothing extra; this line has nine models and they
        # come apart. Expressing it needs an allowance SHARED across options,
        # which WargearOption does not have.
        WargearOption(_FARSTALKER_LINE, FarstalkerFirearmProfile, [DvorgiteSkinnerProfile],
                      max_models=1, name=FARSTALKER_FIREARM_TO_SKINNER),
        WargearOption(_FARSTALKER_LINE, FarstalkerFirearmProfile, [LondaxiTribalestProfile],
                      max_models=1, name=FARSTALKER_FIREARM_TO_TRIBALEST),
    ],
    gear_options=[pechra_gear(_FARSTALKER_LINE)],
    gear_slots={_FARSTALKER_LINE: 1},
    points=TAU_EMPIRE_POINTS["Kroot Farstalkers"],
    abilities_text=[
        'Bounty Hunters: At the start of the battle, select one unit from your opponent\'s army. '
        'Each time a model in this unit makes an attack that targets that unit, that attack has '
        'the [LETHAL HITS] and [PRECISION] abilities.',
        "Pech'ra (wargear): Ranged weapons equipped by the bearer's unit have the [IGNORES COVER] "
        'ability.',
        'Core: Infiltrators, Stealth.',
        'Led By: Aun\'shi, Kroot Flesh Shaper, Kroot Trail Shaper, Kroot War Shaper.',
    ],
))
# Both engine-wired (game/bounty_hunters.py): the bounty is chosen once in the
# pre-battle sequence and read by BOTH attack steps, because its text says "an
# attack" rather than "a ranged attack"; the Pech'ra is ranged-only by its own
# wording and is chained in game/shooting.py alone.
#
# THE LED BY LINE NAMES AUN'SHI, who is a Legends datasheet and is not built -
# the three Shapers are, and their own LEADER lines name this unit, so the
# pairing works in both directions for everything on the table.

# --- Broadside Battlesuits ---


def _broadside_seeker_effect(token):
    token.weapons.append(SeekerMissileProfile())


def _broadside_twin_plasma_effect(token):
    token.weapons.append(TwinPlasmaRifleProfile())


def _broadside_twin_sms_effect(token):
    token.weapons.append(BroadsideTwinSmartMissileSystemProfile())


def _broadside_weapon_support_effect(token):
    """The same field the Riptide's identically-named wargear sets - named
    after the EFFECT, not after either datasheet, which is why three printed
    abilities under two names can share it."""
    token.profile.ignores_hit_modifiers = True


_BROADSIDE_LEADER = "Broadside Shas'vre"
_BROADSIDE_LINE = "Broadside Shas'ui"
_BROADSIDE_LOADOUT = [HeavyRailRifleProfile, CrushingBulkProfile]

BROADSIDE_RAIL_TO_MISSILE_PODS = "Heavy Rail Rifle -> High-yield Missile Pods"
_BROADSIDE_POINTS = TAU_EMPIRE_POINTS["Broadside Battlesuits"]

# "Any number of models can each be equipped with up to two of the following,
# but cannot take duplicates" - the support menu, and its own footnote adds
# "no model can be equipped with BOTH a twin plasma rifle and twin smart
# missile system". That last clause is NOT enforced: Gear has no way to say
# "these two exclude each other", the same gap the Farstalkers' one-of-two
# firearm swap runs into. Recorded and asserted rather than assumed away.
_BROADSIDE_SUPPORT = "broadside_support"
_BROADSIDE_SUPPORT_SLOTS = 2

BROADSIDE_BATTLESUITS = TAU_EMPIRE.add_datasheet(Datasheet(
    "Broadside Battlesuits",
    # No FLY, unlike every other Battlesuit here - it is not printed on this
    # datasheet's own Keywords line.
    keywords=("VEHICLE", "WALKER", "BATTLESUIT", "BROADSIDE"),
    composition_options=[
        [ModelLine(BroadsideShasVreProfile, 1, _BROADSIDE_LOADOUT, name=_BROADSIDE_LEADER)],
        [ModelLine(BroadsideShasVreProfile, 1, _BROADSIDE_LOADOUT, name=_BROADSIDE_LEADER),
         ModelLine(BroadsideShasUiProfile, 1, _BROADSIDE_LOADOUT, name=_BROADSIDE_LINE)],
        [ModelLine(BroadsideShasVreProfile, 1, _BROADSIDE_LOADOUT, name=_BROADSIDE_LEADER),
         ModelLine(BroadsideShasUiProfile, 2, _BROADSIDE_LOADOUT, name=_BROADSIDE_LINE)],
    ],
    # "Any number of models" on both lines, so no cap - and the swap IS priced,
    # which is what corroborates it as a real option rather than a guess.
    wargear_options=[
        WargearOption(line, HeavyRailRifleProfile, [HighYieldMissilePodsProfile],
                      points=_BROADSIDE_POINTS.wargear["High-yield missile pods"],
                      name=BROADSIDE_RAIL_TO_MISSILE_PODS)
        for line in (_BROADSIDE_LEADER, _BROADSIDE_LINE)
    ],
    # TWO independent printed menus again, so two groups - a support system must
    # not eat a drone slot. `all_models=True` on both, because this datasheet
    # says "ANY NUMBER OF MODELS can each be equipped", where every earlier
    # menu here was one character's.
    gear_options=[
        Gear(line, name, effect, max_count=1, group=group, all_models=True)
        for line in (_BROADSIDE_LEADER, _BROADSIDE_LINE)
        for name, effect, group in (
            ("Seeker Missile", _broadside_seeker_effect, _BROADSIDE_SUPPORT),
            ("Twin Plasma Rifle", _broadside_twin_plasma_effect, _BROADSIDE_SUPPORT),
            ("Twin Smart Missile System", _broadside_twin_sms_effect, _BROADSIDE_SUPPORT),
            ("Weapon Support System", _broadside_weapon_support_effect, _BROADSIDE_SUPPORT),
        )
    ] + [g for line in (_BROADSIDE_LEADER, _BROADSIDE_LINE)
         for g in drone_options(line, include_guardian=False, include_missile=True,
                                allow_duplicates=True, all_models=True)],
    gear_slots={line: {_BROADSIDE_SUPPORT: _BROADSIDE_SUPPORT_SLOTS,
                       DRONE_GROUP: DRONE_SLOTS}
                for line in (_BROADSIDE_LEADER, _BROADSIDE_LINE)},
    points=_BROADSIDE_POINTS,
    abilities_text=[
        'Advanced Armour: Models in this unit have the Feel No Pain 4+ ability against mortal '
        'wounds.',
        'Weapon Support System (wargear): Each time the bearer makes a ranged attack, you can '
        'ignore any or all modifiers to the Hit roll.',
        'Faction: For the Greater Good.',
    ],
))
# Advanced Armour is engine-wired as the FIRST conditional Feel No Pain source
# here - 4+ against MORTAL WOUNDS only, folded into current_feel_no_pain()
# behind its new `mortal` flag, which MortalWoundAllocationSession alone sets
# (game/advanced_armour.py). The Weapon Support System reuses
# `ignores_hit_modifiers`, the same field the Riptide's identically-named
# wargear and Dark Reapers' Inescapable Accuracy already use.

# --- Crisis Fireknife Battlesuits ---

_FIREKNIFE_LEADER = "Crisis Fireknife Shas'vre"
_FIREKNIFE_LINE = "Crisis Fireknife Shas'ui"
_FIREKNIFE_LOADOUT = [PlasmaRifleProfile, MissilePodProfile, CrisisBattlesuitFistsProfile]
_FIREKNIFE_POINTS = TAU_EMPIRE_POINTS["Crisis Fireknife Battlesuits"]

FIREKNIFE_PLASMA_TO_MISSILE_POD = "Plasma Rifle -> Missile Pod"
FIREKNIFE_MISSILE_POD_TO_PLASMA = "Missile Pod -> Plasma Rifle"

CRISIS_FIREKNIFE = TAU_EMPIRE.add_datasheet(Datasheet(
    "Crisis Fireknife Battlesuits",
    keywords=("VEHICLE", "WALKER", "FLY", "BATTLESUIT", "CRISIS", "FIREKNIFE"),
    # Three separate count=1 lines, the same arrangement Starscythe and
    # Sunforge use and for the same reason: each model has its own drone menu,
    # and build_squad() applies Gear only to a line's first model.
    model_lines=[
        ModelLine(CrisisFireknifeShasVreProfile, 1, _FIREKNIFE_LOADOUT, name=_FIREKNIFE_LEADER),
        ModelLine(CrisisFireknifeShasUiProfile, 1, _FIREKNIFE_LOADOUT, name=_FIREKNIFE_LINE + " (1)"),
        ModelLine(CrisisFireknifeShasUiProfile, 1, _FIREKNIFE_LOADOUT, name=_FIREKNIFE_LINE + " (2)"),
    ],
    # The two swaps are MIRRORS - each turns one of the model's two guns into
    # another copy of the other - so a model can end with two plasma rifles or
    # two missile pods but never lose both. NEITHER carries a cost: the missile
    # pod is priced PER WEAPON IN THE UNIT (UnitPoints.per_weapon), which counts
    # the default's own three as well, so charging the swap too would double it.
    wargear_options=[
        WargearOption(line, PlasmaRifleProfile, [MissilePodProfile], max_models=1,
                      name=FIREKNIFE_PLASMA_TO_MISSILE_POD)
        for line in (_FIREKNIFE_LEADER, _FIREKNIFE_LINE + " (1)", _FIREKNIFE_LINE + " (2)")
    ] + [
        WargearOption(line, MissilePodProfile, [PlasmaRifleProfile], max_models=1,
                      name=FIREKNIFE_MISSILE_POD_TO_PLASMA)
        for line in (_FIREKNIFE_LEADER, _FIREKNIFE_LINE + " (1)", _FIREKNIFE_LINE + " (2)")
    ],
    gear_options=[g for line in (_FIREKNIFE_LEADER, _FIREKNIFE_LINE + " (1)",
                                 _FIREKNIFE_LINE + " (2)")
                  for g in drone_options(line, include_guardian=False)],
    gear_slots={line: DRONE_SLOTS
                for line in (_FIREKNIFE_LEADER, _FIREKNIFE_LINE + " (1)",
                             _FIREKNIFE_LINE + " (2)")},
    points=_FIREKNIFE_POINTS,
    abilities_text=[
        'Fireknife: Each time a model in this unit makes a ranged attack, re-roll a Hit roll of 1. '
        'If that attack targets a unit that is at its Starting Strength, you can re-roll the Hit '
        'roll instead.',
        'Weapon Support System: Each time a model in this unit makes a ranged attack, you can '
        'ignore any or all modifiers to the Hit roll.',
        'Core: Deep Strike.',
        'Faction: For the Greater Good.',
        'Led By: Commander Farsight, Commander in Coldstar Battlesuit, Commander in Crisis '
        'Battlesuit, Commander in Enforcer Battlesuit.',
    ],
))
# THIS DATASHEET CLOSES A DANGLING REFERENCE that has been in the points list
# since the T'au were built: THREE `leads` tables (Commander Farsight,
# Commander in Coldstar, Commander in Enforcer) name Crisis Fireknife
# Battlesuits, game/attached_units.py's can_attach() reads that table, and
# until now it pointed at nothing.
#
# Both abilities are engine-wired. Fireknife is the SIXTH ones-or-whole source
# (game/reroll_scope.py) - its two clauses are alternatives, so "failures only"
# must not be offered; see game/fireknife.py. Weapon Support System is printed
# as a UNIT ability here rather than as wargear, so it is the profile's own
# `ignores_hit_modifiers` - the field named after the EFFECT precisely because
# three datasheets now print it under two different names.

# --- Hammerhead Gunship ---
#
# The seeker-missile addition is Gear rather than a WargearOption for the same
# reason the Devilfish's is not: "up to 2 seeker missiles" is a COUNT of a
# repeatable item, which Gear's max_count expresses and a weapon-for-weapon
# swap does not.

_HAMMERHEAD_LINE = "Hammerhead Gunship"
_HAMMERHEAD_LOADOUT = [RailgunProfile, HammerheadTwinPulseCarbineProfile,
                       HammerheadTwinPulseCarbineProfile, ArmouredHullProfile]

HAMMERHEAD_RAILGUN_TO_ION_CANNON = "Railgun -> Ion Cannon"
HAMMERHEAD_CARBINES_TO_BURST = "2x Twin Pulse Carbine -> 2x Accelerator Burst Cannon"
HAMMERHEAD_CARBINES_TO_SMS = "2x Twin Pulse Carbine -> 2x Smart Missile System"
_GUNSHIP_SEEKER_SLOTS = 2
_GUNSHIP_SEEKER_GROUP = "seeker_missiles"


def _seeker_missile_effect(token):
    token.weapons.append(SeekerMissileProfile())


HAMMERHEAD_GUNSHIP = TAU_EMPIRE.add_datasheet(Datasheet(
    "Hammerhead Gunship",
    keywords=("VEHICLE", "FLY", "FRAME", "HAMMERHEAD GUNSHIP"),
    model_lines=[
        ModelLine(HammerheadGunshipProfile, 1, _HAMMERHEAD_LOADOUT, name=_HAMMERHEAD_LINE),
    ],
    # The two carbine swaps give up the SAME pair, so build_squad()'s shared
    # cursor makes them exclusive - "one of the following", and on a
    # single-model line that reading is exact (see the Farstalkers' note for
    # where it is not).
    wargear_options=[
        WargearOption(_HAMMERHEAD_LINE, RailgunProfile, [IonCannonStandardProfile],
                      max_models=1, name=HAMMERHEAD_RAILGUN_TO_ION_CANNON),
        WargearOption(_HAMMERHEAD_LINE, HammerheadTwinPulseCarbineProfile,
                      [AcceleratorBurstCannonProfile, AcceleratorBurstCannonProfile],
                      max_models=1, name=HAMMERHEAD_CARBINES_TO_BURST),
        WargearOption(_HAMMERHEAD_LINE, HammerheadTwinPulseCarbineProfile,
                      [SmartMissileSystemProfile, SmartMissileSystemProfile],
                      max_models=1, name=HAMMERHEAD_CARBINES_TO_SMS),
    ],
    gear_options=[Gear(_HAMMERHEAD_LINE, "Seeker Missile", _seeker_missile_effect,
                       max_count=_GUNSHIP_SEEKER_SLOTS, group=_GUNSHIP_SEEKER_GROUP)],
    gear_slots={_HAMMERHEAD_LINE: {_GUNSHIP_SEEKER_GROUP: _GUNSHIP_SEEKER_SLOTS}},
    points=TAU_EMPIRE_POINTS["Hammerhead Gunship"],
    abilities_text=[
        'Armour Hunter: Each time this model makes an attack that targets a MONSTER or VEHICLE, '
        'add 1 to the Hit roll.',
        'Targeting Array: Each time this model is selected to shoot, you can re-roll one Hit roll '
        'or you can re-roll one Wound roll when resolving those attacks.',
        'Core: Deadly Demise D3.',
        'Faction: For the Greater Good.',
        'Damaged: 1-5 wounds remaining - while this model has 1-5 wounds remaining, each time this '
        'model makes an attack, subtract 1 from the Hit roll.',
    ],
))
# Both abilities are engine-wired. Armour Hunter is Tank Hunters with the WOUND
# half missing, so it is its own flag reading the same is_monster_or_vehicle_unit()
# helper (game/armour_hunter.py). Targeting Array is a single-die re-roll with a
# panel button - rule 15.02's Command Re-roll shape without the CP
# (game/targeting_array.py).

# --- Sky Ray Gunship ---

_SKY_RAY_LINE = "Sky Ray Gunship"
_SKY_RAY_LOADOUT = [SeekerMissileRackProfile, DevilfishTwinPulseCarbineProfile,
                    DevilfishTwinPulseCarbineProfile, ArmouredHullProfile]

SKY_RAY_CARBINES_TO_BURST = "2x Twin Pulse Carbine -> 2x Accelerator Burst Cannon"
SKY_RAY_CARBINES_TO_SMS = "2x Twin Pulse Carbine -> 2x Smart Missile System"

SKY_RAY_GUNSHIP = TAU_EMPIRE.add_datasheet(Datasheet(
    "Sky Ray Gunship",
    keywords=("VEHICLE", "FLY", "FRAME", "MARKERLIGHT", "SKY RAY GUNSHIP"),
    model_lines=[
        ModelLine(SkyRayGunshipProfile, 1, _SKY_RAY_LOADOUT, name=_SKY_RAY_LINE),
    ],
    # Its carbines DO print [ASSAULT], unlike the Hammerhead's - so it carries
    # the Devilfish's class where its sibling needed one of its own.
    wargear_options=[
        WargearOption(_SKY_RAY_LINE, DevilfishTwinPulseCarbineProfile,
                      [AcceleratorBurstCannonProfile, AcceleratorBurstCannonProfile],
                      max_models=1, name=SKY_RAY_CARBINES_TO_BURST),
        WargearOption(_SKY_RAY_LINE, DevilfishTwinPulseCarbineProfile,
                      [SmartMissileSystemProfile, SmartMissileSystemProfile],
                      max_models=1, name=SKY_RAY_CARBINES_TO_SMS),
    ],
    # No seeker-missile option: its whole armament IS a rack of them.
    points=TAU_EMPIRE_POINTS["Sky Ray Gunship"],
    abilities_text=[
        'Velocity Tracker: Each time this model makes a ranged attack that targets a unit that can '
        'FLY, you can re-roll the Hit roll.',
        'Targeting Array: Each time this unit is selected to shoot, you can re-roll one Hit roll '
        'or you can re-roll one Wound roll when resolving those attacks.',
        'Core: Deadly Demise D3.',
        'Faction: For the Greater Good.',
        'Damaged: 1-5 wounds remaining - while this model has 1-5 wounds remaining, each time this '
        'model makes an attack, subtract 1 from the Hit roll.',
    ],
))
# Both engine-wired: Velocity Tracker is an ordinary failures-or-whole
# _hit_reroll_reason() entry (game/velocity_tracker.py) and deliberately NOT a
# reroll_scope source, Targeting Array is the same controller the Hammerhead
# uses.

# --- Piranhas ---

_PIRANHA_LINE = "Piranhas"
_PIRANHA_LOADOUT = [PiranhaBurstCannonProfile, DevilfishTwinPulseCarbineProfile,
                    DevilfishTwinPulseCarbineProfile, PiranhaArmouredHullProfile]

PIRANHA_BURST_TO_FUSION = "Piranha Burst Cannon -> Piranha Fusion Blaster"

PIRANHAS = TAU_EMPIRE.add_datasheet(Datasheet(
    "Piranhas",
    keywords=("VEHICLE", "FLY", "FRAME", "PIRANHAS"),
    composition_options=[
        [ModelLine(PiranhaProfile, n, _PIRANHA_LOADOUT, name=_PIRANHA_LINE)]
        for n in (1, 2, 3)
    ],
    # "Any number of models can each have..." - so no cap on either option.
    wargear_options=[
        WargearOption(_PIRANHA_LINE, PiranhaBurstCannonProfile,
                      [PiranhaFusionBlasterProfile], name=PIRANHA_BURST_TO_FUSION),
    ],
    # "Any number of models can each be equipped with up to 2 seeker missiles",
    # hence all_models=True - the same printed wording as the Broadsides'
    # menus, and the second datasheet to need it.
    gear_options=[Gear(_PIRANHA_LINE, "Seeker Missile", _seeker_missile_effect,
                       max_count=_GUNSHIP_SEEKER_SLOTS, group=_GUNSHIP_SEEKER_GROUP,
                       all_models=True)],
    gear_slots={_PIRANHA_LINE: {_GUNSHIP_SEEKER_GROUP: _GUNSHIP_SEEKER_SLOTS}},
    points=TAU_EMPIRE_POINTS["Piranhas"],
    abilities_text=[
        'Drone Harassment Tactics: At the end of your Movement phase, select one enemy unit '
        'within 12" of this unit; that enemy unit must take a Battle-shock test.',
        'Core: Deadly Demise 1, Scouts 9".',
        'Faction: For the Greater Good.',
    ],
))
# Drone Harassment Tactics is engine-wired through
# BattleShockController.start_forced_roll() - the "a rule orders a test out of
# turn" entry point that already exists (game/drone_harassment.py). Scouts 9"
# is the longest Scout move in this engine; every other one is 7" or 8".

_STEALTH_LOADOUT = [BattlesuitFistsProfile, BurstCannonProfile]
_STEALTH_LEADER = "Stealth Shas'vre"
_STEALTH_SHAS_UI = "Stealth Shas'ui"

STEALTH_PULSE_PISTOL_OPTION = "+ Pulse Pistol"
STEALTH_BURST_TO_FUSION = "Burst Cannon -> Fusion Blaster"

STEALTH_BATTLESUITS = TAU_EMPIRE.add_datasheet(Datasheet(
    "Stealth Battlesuits",
    keywords=("INFANTRY", "FLY", "BATTLESUIT", "STEALTH", "GRENADES", "MARKERLIGHT"),
    model_lines=[
        ModelLine(StealthShasVreProfile, 1, _STEALTH_LOADOUT, name=_STEALTH_LEADER),
        ModelLine(StealthShasUiProfile, 4, _STEALTH_LOADOUT, name=_STEALTH_SHAS_UI),
    ],
    # Gear/wargear - real text (official app, screenshots), correcting two
    # things an earlier pre-screenshot guess got wrong:
    # - "The Stealth Shas'vre can be equipped with 1 gun drone" and
    #   "...1 marker drone" are each capped at 1, NOT "up to 2 Gun Drones"
    #   (the earlier guess here) - two separate single-item bullets, not one
    #   duplicate-capable menu.
    # - "1 Stealth Shas'ui can be equipped with 1 homing beacon" - the
    #   HOMING BEACON belongs on the Shas'ui line, not the Shas'vre (the
    #   earlier guess put it on the leader); build_squad() applies Gear only
    #   to a line's first model, which already matches "1 Stealth Shas'ui"
    #   (one of the four, picked as the line's first).
    # "The Stealth Shas'vre can be equipped with 1 pulse pistol" is an
    # addition (replaces=None), same pattern as Devilfish's Seeker Missile
    # wargear option, since the baseline loadout has no pistol to swap out.
    gear_options=[
        gun_drone_gear(_STEALTH_LEADER, max_count=1),
        marker_drone_gear(_STEALTH_LEADER, max_count=1),
        homing_beacon_gear(_STEALTH_SHAS_UI),
    ],
    gear_slots={_STEALTH_LEADER: 2, _STEALTH_SHAS_UI: 1},
    # "2 models can each have their burst cannon replaced with 1 fusion
    # blaster" - MODELS, so any 2 of the unit's 5, the Shas'vre included.
    # This was scoped to the Shas'ui line alone at first, flagged there as a
    # judgment call; the T'au list the user supplied on 2026-08-30 gives the
    # FUSION BLASTER TO THE SHAS'VRE, so that reading made a printed build
    # unbuildable. The option now sits on both lines, which is what "2 models"
    # says.
    #
    # KNOWN LIMITATION, measured rather than hidden: a WargearOption caps per
    # LINE, so 1 (Shas'vre) + 2 (Shas'ui) is a reachable 3 against the printed
    # 2. There is no cross-line cap to express it with - the same shape as the
    # Kroot Farstalkers' "ONE OF the following" note above. The list itself
    # takes exactly 1, so it cannot reach the gap; a test pins both facts.
    wargear_options=[
        WargearOption(_STEALTH_LEADER, replaces=None, with_weapons=[PulsePistolProfile], max_models=1, name=STEALTH_PULSE_PISTOL_OPTION),
        WargearOption(_STEALTH_LEADER, replaces=BurstCannonProfile, with_weapons=[FusionBlasterProfile], max_models=1, name=STEALTH_BURST_TO_FUSION),
        WargearOption(_STEALTH_SHAS_UI, replaces=BurstCannonProfile, with_weapons=[FusionBlasterProfile], max_models=2, name=STEALTH_BURST_TO_FUSION),
    ],
    points=TAU_EMPIRE_POINTS["Stealth Battlesuits"],  # 5 models 100 pts (1st-2nd unit) / 110 (3rd+); this datasheet's own wargear options are all free on the list
    abilities_text=[
        'Forward Observers: Each time this unit is an Observer unit, until the end of the phase, '
        'each time a ranged attack is made by a model in a Guided unit that targets their Spotted '
        'unit, re-roll a Hit roll of 1 and re-roll a Wound roll of 1.',
        'Homing Beacon (0/1): Once per battle, you can use the Rapid Ingress Stratagem for 0CP. '
        'The target must be set up within 3" of the bearer\'s unit and more than 9" away from all '
        'enemy units.',
    ],
))

_STARSCYTHE_LOADOUT = [CrisisBattlesuitFistsProfile, BurstCannonProfile, TauFlamerProfile]

# Composition is "1 Shas'vre + 2 Shas'ui", all three carrying an identical
# loadout - but unlike every other T'au datasheet so far (where drone Gear
# is a single leader-only slot), the real text here (official app,
# screenshot) is "Any number of models can be equipped with up to two of
# the following, but cannot take duplicates: gun drone / marker drone /
# shield drone" - a genuinely independent per-model choice, not a per-line
# one. build_squad()'s gear parameter only ever applies to a ModelLine's
# FIRST model (see its own docstring: "would need a per-model gear list
# instead... if a future datasheet ever let several models in the same line
# each pick their own gear" - exactly this case). Rather than extending
# that mechanism, the 2 Shas'ui are modeled as TWO separate count=1
# ModelLines with distinct internal names (never shown to the player - see
# ModelLine's own note that `.name` is purely an internal choices/gear dict
# key, not display text; the token's on-screen label still comes from
# CrisisStarscytheShasUiProfile.name for both) so each gets its own
# independent gear_slots entry.
_STARSCYTHE_SHAS_VRE = "Crisis Starscythe Shas'vre"
_STARSCYTHE_SHAS_UI_1 = "Crisis Starscythe Shas'ui (1)"
_STARSCYTHE_SHAS_UI_2 = "Crisis Starscythe Shas'ui (2)"

STARSCYTHE_BURST_TO_FLAMER = "Burst Cannon -> T'au Flamer"
STARSCYTHE_FLAMER_TO_BURST = "T'au Flamer -> Burst Cannon"

_STARSCYTHE_POINTS = TAU_EMPIRE_POINTS["Crisis Starscythe Battlesuits"]


def _starscythe_wargear(line_name):
    """Real wargear text (official app, screenshot) - corrects an earlier
    pre-screenshot guess here (a single "2x Burst Cannon -> Twin T'au
    Flamer" option, assuming the baseline loadout was 2x Burst Cannon):
    - "Any number of models can each have their burst cannon replaced with
      1 T'au flamer."
    - "Any number of models can each have their T'au flamer replaced with 1
      burst cannon."
    The real baseline (per this datasheet's own "Every model is equipped
    with" text) is 1 Burst Cannon + 1 T'au Flamer per model, not 2x Burst
    Cannon - see _STARSCYTHE_LOADOUT above - and these are two independent,
    symmetric single-weapon swaps (TauFlamerProfile, not the twin-linked
    TwinTauFlamerProfile - that class belongs to Ghostkeel Battlesuit's own
    loadout instead, see GHOSTKEEL_BATTLESUIT below), not a single
    both-cannons-at-once swap to a twin-linked weapon. main.py's own
    STARSCYTHE_CHOICES reproduces the specific "2x Burst Cannon" build the
    user separately specified for this army list by picking
    STARSCYTHE_FLAMER_TO_BURST for every model.

    Only the burst-cannon-to-flamer direction costs points ("per T'au flamer
    5 pts") - that's the SECOND flamer a model ends up with, since one is
    already part of the printed default loadout. NEITHER swap carries a cost:
    the flamer is priced PER WEAPON IN THE UNIT (UnitPoints.per_weapon), which
    counts the default's own three as well, so charging the swap too would
    double it - see game/factions/points.py for the list that settles the
    reading."""
    return [
        WargearOption(
            line_name, replaces=BurstCannonProfile, with_weapons=[TauFlamerProfile],
            name=STARSCYTHE_BURST_TO_FLAMER,
        ),
        WargearOption(line_name, replaces=TauFlamerProfile, with_weapons=[BurstCannonProfile], name=STARSCYTHE_FLAMER_TO_BURST),
    ]


CRISIS_STARSCYTHE = TAU_EMPIRE.add_datasheet(Datasheet(
    "Crisis Starscythe Battlesuits",
    # User-supplied Keywords line (given separately from the initial paste):
    # Vehicle, Walker, Fly, Battlesuit, Crisis, Starscythe, Faction: T'au
    # Empire - the last one is dropped here since it's already implicit in
    # this Datasheet being registered under TAU_EMPIRE, not a separate
    # keyword this tuple needs to repeat. This tuple itself is purely
    # descriptive (see Datasheet's own docstring - keywords drive no engine
    # logic) - the actually-consequential fields (vehicle/walker/fly/
    # battlesuit/starscythe) live on CrisisStarscytheShasUiProfile, see its
    # own docstring for what each one wires into.
    keywords=("VEHICLE", "WALKER", "FLY", "BATTLESUIT", "CRISIS", "STARSCYTHE"),
    model_lines=[
        ModelLine(CrisisStarscytheShasVreProfile, 1, _STARSCYTHE_LOADOUT, name=_STARSCYTHE_SHAS_VRE),
        ModelLine(CrisisStarscytheShasUiProfile, 1, _STARSCYTHE_LOADOUT, name=_STARSCYTHE_SHAS_UI_1),
        ModelLine(CrisisStarscytheShasUiProfile, 1, _STARSCYTHE_LOADOUT, name=_STARSCYTHE_SHAS_UI_2),
    ],
    # Drones - real text (official app, screenshot): "Any number of models
    # can be equipped with up to two of the following, but cannot take
    # duplicates: gun drone / marker drone / shield drone" - no Guardian
    # Drone on this datasheet's own menu (unlike Strike/Breacher Team),
    # hence include_guardian=False; re-scoped to each of the three line
    # names above so each model's choice is tracked independently.
    gear_options=[
        *drone_options(_STARSCYTHE_SHAS_VRE, include_guardian=False),
        *drone_options(_STARSCYTHE_SHAS_UI_1, include_guardian=False),
        *drone_options(_STARSCYTHE_SHAS_UI_2, include_guardian=False),
    ],
    gear_slots={_STARSCYTHE_SHAS_VRE: DRONE_SLOTS, _STARSCYTHE_SHAS_UI_1: DRONE_SLOTS, _STARSCYTHE_SHAS_UI_2: DRONE_SLOTS},
    # Composition/loadout: the DATASHEET's own printed default (official app,
    # screenshot, "Every model is equipped with") is burst cannon + T'au
    # flamer - see _STARSCYTHE_LOADOUT above, which now matches that exactly
    # (an earlier guess had wrongly promoted the user's separately-specified
    # ARMY LIST build, "2x Burst cannon", into the coded default itself).
    # See _starscythe_wargear() above for the real, symmetric wargear-swap
    # text. The "Unselected Profiles" reference block (a Shas'ui with a
    # Twin pulse carbine + Missile pod instead) still has no wargear-swap
    # rule text of its own - same documented gap as every other T'au
    # datasheet's own Unselected Profiles.
    wargear_options=[
        *_starscythe_wargear(_STARSCYTHE_SHAS_VRE),
        *_starscythe_wargear(_STARSCYTHE_SHAS_UI_1),
        *_starscythe_wargear(_STARSCYTHE_SHAS_UI_2),
    ],
    # Official list: 3 models 90 pts (1st-2nd unit) / 100 pts (3rd+), plus 5
    # pts per extra T'au flamer. This replaces an earlier hardcoded
    # `points={3: 110}` - a user-supplied total for one specific built
    # loadout, which the real list doesn't reproduce: main.py's demo build
    # swaps every flamer AWAY for a burst cannon (free) and its drones are
    # free too, so that same unit is 90 pts as the army's first Crisis
    # Starscythe unit.
    points=_STARSCYTHE_POINTS,
    abilities_text=[
        'Starscythe: Each time a model in this unit makes a ranged attack (excluding attacks that '
        'target MONSTERS and VEHICLES), improve the Armour Penetration characteristic of that attack '
        'by 1.',
        'Battlesuit Support System: The unit is eligible to shoot in a turn in which it Fell Back.',
    ],
))

_DEVILFISH_LOADOUT = [ArmouredHullProfile, AcceleratorBurstCannonProfile, DevilfishTwinPulseCarbineProfile, DevilfishTwinPulseCarbineProfile]

DEVILFISH_SEEKER_MISSILE_OPTION = "+ 2x Seeker Missile"
DEVILFISH_CARBINES_TO_SMS = "2x Twin Pulse Carbine -> 2x Smart Missile System"

DEVILFISH = TAU_EMPIRE.add_datasheet(Datasheet(
    "Devilfish",
    keywords=("DEDICATED TRANSPORT", "VEHICLE", "FLY", "TRANSPORT", "DEVILFISH"),
    model_lines=[
        ModelLine(DevilfishProfile, 1, _DEVILFISH_LOADOUT, name="Devilfish"),
    ],
    # User-supplied build (separately from the initial paste): "1x Devilfish
    # (85 pts): Accelerator burst cannon, Armoured hull, 2x Seeker missile,
    # 2x Twin pulse carbine" - an ADDITION on top of the baseline loadout
    # (_DEVILFISH_LOADOUT already has the Accelerator burst cannon/Armoured
    # hull/2x Twin pulse carbine), not a replacement, hence replaces=None.
    # max_models=1 since this is a single-model unit.
    #
    # Real wargear text (official app, screenshot): "This model's 2 twin
    # pulse carbines can be replaced with 2 smart missile systems." -
    # `replaces` removes EVERY matching weapon on the model at once (see
    # WargearOption's own docstring), so this one option correctly swaps
    # both Twin Pulse Carbines for both Smart Missile Systems together.
    # Not selected by main.py's demo scene (which keeps the Twin Pulse
    # Carbines and only adds the Seeker Missiles above), so it's here as a
    # real, available option but currently unused in the actual battle.
    wargear_options=[
        WargearOption(
            "Devilfish", replaces=None, with_weapons=[SeekerMissileProfile, SeekerMissileProfile],
            max_models=1, name=DEVILFISH_SEEKER_MISSILE_OPTION,
        ),
        WargearOption(
            "Devilfish", replaces=DevilfishTwinPulseCarbineProfile,
            with_weapons=[SmartMissileSystemProfile, SmartMissileSystemProfile],
            max_models=1, name=DEVILFISH_CARBINES_TO_SMS,
        ),
    ],
    # Official list: 1 model 75 pts for your 1st to 3rd Devilfish, 85 pts
    # from the 4th on. This replaces an earlier hardcoded `points={1: 85}` -
    # taken from the user's own list entry ("1x Devilfish (85 pts)"), which
    # is the 4th+ price; as the demo scene's only Devilfish it costs 75, and
    # its Seeker Missiles are free on the list.
    points=TAU_EMPIRE_POINTS["Devilfish"],
    abilities_text=[
        'Rapid Deployment: Units can disembark from this TRANSPORT after it has Advanced. Units '
        'that do so count as having made a Normal move that phase, and cannot declare a charge in '
        'the same turn, but can otherwise act normally in the remainder of the turn.',
        'Transport: This model has a transport capacity of 12 T\'AU EMPIRE INFANTRY models. It '
        'cannot transport BATTLESUIT, KROOT or VESPID STINGWINGS models.',
    ],
))

# Real datasheet default (official app, screenshot, "This model is equipped
# with"): Fusion Collider, Twin T'au Flamer, Ghostkeel Fists - this
# corrects an earlier guess that had promoted the user's separately-given
# ARMY LIST build ("Battlesuit support system, Ghostkeel fists, Cyclic ion
# raker, Twin fusion blaster") into the coded default itself; that specific
# build is a real, legal one (see the wargear options below) but isn't the
# datasheet's own baseline. main.py's demo scene now reproduces it
# explicitly via `choices` (GHOSTKEEL_FUSION_TO_ION_RAKER +
# GHOSTKEEL_FLAMER_TO_FUSION_BLASTER) instead of it being hardcoded here as
# the default.
#
# Real wargear text (official app, screenshot):
# - "This model's fusion collider can be replaced with 1 cyclic ion raker."
# - "This model's twin T'au flamer can be replaced with one of the
#   following: 1 twin fusion blaster / 1 twin burst cannon."
# - "This model can be equipped with one battlesuit support system." - NOT
#   wired in: the screenshot's Wargear Options section was scrolled past
#   the point of listing what the actual support-system choices are (unlike
#   every other bullet here, no item names are visible), so there's nothing
#   concrete to encode yet - same kind of documented gap as every other T'au
#   datasheet's own "Unselected Profiles" text without swap rules. Note this
#   is a WARGEAR item, distinct from the "Battlesuit Support System"
#   ABILITY text below (eligible to shoot after Falling Back), which is
#   already wired in and unaffected by this gap.
#
# Cyclic Ion Raker itself is a single weapon with two selectable FIRING
# MODES (Standard/Overcharge, see CyclicIonRakerStandardProfile's own
# docstring - real 40k choice made at the point of shooting, like a Plasma
# weapon's supercharge), not a wargear swap - only the Standard profile is
# ever placed in this model's loadout list; Overcharge is offered as a
# second button when actually choosing this weapon to fire
# (ShootingController.weapon_eligibility()/choose_weapon(overcharge=True)),
# via CyclicIonRakerStandardProfile.overcharge_profile, not by giving the
# model a second weapon instance (which would incorrectly let it fire twice
# in one Shooting activation).
_GHOSTKEEL_LOADOUT = [GhostkeelFistsProfile, FusionColliderProfile, TwinTauFlamerProfile]
_GHOSTKEEL_LINE = "Ghostkeel Battlesuit"

GHOSTKEEL_FUSION_TO_ION_RAKER = "Fusion Collider -> Cyclic Ion Raker"
GHOSTKEEL_FLAMER_TO_FUSION_BLASTER = "Twin T'au Flamer -> Twin Fusion Blaster"
GHOSTKEEL_FLAMER_TO_BURST_CANNON = "Twin T'au Flamer -> Twin Burst Cannon"

_GHOSTKEEL_POINTS = TAU_EMPIRE_POINTS["Ghostkeel Battlesuit"]

GHOSTKEEL_BATTLESUIT = TAU_EMPIRE.add_datasheet(Datasheet(
    "Ghostkeel Battlesuit",
    keywords=("VEHICLE", "WALKER", "FLY", "SMOKE", "BATTLESUIT", "GHOSTKEEL"),
    model_lines=[
        ModelLine(GhostkeelProfile, 1, _GHOSTKEEL_LOADOUT, name=_GHOSTKEEL_LINE),
    ],
    # The Cyclic Ion Raker is the one priced option here ("per Cyclic Ion
    # Raker 15 pts"); both twin-weapon swaps are free on the list.
    wargear_options=[
        WargearOption(
            _GHOSTKEEL_LINE, replaces=FusionColliderProfile, with_weapons=[CyclicIonRakerStandardProfile],
            max_models=1, name=GHOSTKEEL_FUSION_TO_ION_RAKER, points=_GHOSTKEEL_POINTS.wargear["Cyclic Ion Raker"],
        ),
        WargearOption(_GHOSTKEEL_LINE, replaces=TwinTauFlamerProfile, with_weapons=[TwinFusionBlasterProfile], max_models=1, name=GHOSTKEEL_FLAMER_TO_FUSION_BLASTER),
        WargearOption(_GHOSTKEEL_LINE, replaces=TwinTauFlamerProfile, with_weapons=[TwinBurstCannonProfile], max_models=1, name=GHOSTKEEL_FLAMER_TO_BURST_CANNON),
    ],
    # Official list: 1 model 150 pts (1st-2nd unit) / 165 pts (3rd+), plus 15
    # for the Cyclic Ion Raker. This replaces an earlier hardcoded
    # `points={1: 160}`, which matched no line of the real list; main.py's
    # demo build (Ion Raker + Twin Fusion Blaster) comes to 150 + 15 = 165 as
    # the army's first Ghostkeel.
    points=_GHOSTKEEL_POINTS,
    abilities_text=[
        'Battlesuit Support System: The unit is eligible to shoot in a turn in which it Fell Back.',
        'Stealth Drones: Twice per battle, after an attack has been allocated to this model, you '
        'can change the Damage characteristic of that attack to 0. Designer\'s Note: Place two '
        'Stealth Drone tokens next to the unit, removing one each time this ability has been used.',
        'Damaged: 1-4 Wounds Remaining: While this model has 1-4 wounds remaining, each time this '
        'model makes an attack, subtract 1 from the Hit roll.',
    ],
))

_COLDSTAR_COMMANDER_LOADOUT = [HighOutputBurstCannonProfile, CrisisBattlesuitFistsProfile]
_COLDSTAR_COMMANDER_LINE = "Commander in Coldstar Battlesuit"

# User-supplied build (not from an official screenshot, same "flagged, not
# confirmed" status as every other inferred T'au wargear item in this file):
# "2x Shield Drone, 2x Burst cannon, Cyclic ion blaster, High-output burst
# cannon, Battlesuit fists" - the user's own clarification for how a Coldstar
# Battlesuit's loadout works: "ein Coldstar kann die 4 Slots beliebig füllen
# mit Waffen/Unterstützungssystemen" (it freely fills 4 slots with weapons or
# support systems, unlike the single-hardpoint-with-swap-alternates model
# every other T'au Battlesuit datasheet in this file has). Modeled as two
# pure ADDITIONS on top of the printed default (High-output Burst Cannon +
# Battlesuit Fists, kept as-is) rather than a real generic N-slot system
# (that's the still-deferred "Später-Liste" generic wargear system) - this
# is scoped to exactly the two extra weapons this one build actually needs:
# +2x Burst Cannon (one option, `with_weapons` listing the same class twice -
# same technique DEVILFISH_SEEKER_MISSILE_OPTION already uses for "2x Seeker
# Missile") and +1x Cyclic Ion Blaster. Both free (points=0, not on the
# official points list's own wargear dict) since nothing here is confirmed
# priced wargear.
# The printed menu is one REPLACEMENT of the high-output burst cannon plus up
# to THREE additions from the same ten-item list. The additions used to be
# hand-picked BUNDLES here (+ 2x Burst Cannon, + Cyclic Ion Blaster, + 3x
# Fusion Blaster) - one option per combination a shipped list happened to buy.
# They are gone: the datasheet now carries the real menu as Gear, the way the
# Enforcer Commander always did, so any legal pick of three is expressible and
# the three support systems are reachable at all.
#
# All the replacements below are free (points=0): none of them is on the
# official points list's own wargear dict.
COLDSTAR_BURST_TO_FUSION = "High-output Burst Cannon -> Fusion Blaster"
COLDSTAR_BURST_TO_BURST_CANNON = "High-output Burst Cannon -> Burst Cannon"
COLDSTAR_BURST_TO_CYCLIC_ION = "High-output Burst Cannon -> Cyclic Ion Blaster"
COLDSTAR_BURST_TO_MISSILE_POD = "High-output Burst Cannon -> Missile Pod"
# These three are what makes Experimental Prototype Cadre's Enhancements
# reachable at all: each names a weapon ("select one of this model's Plasma
# Rifle weapons"), and until a list equipped one they were dormant by
# construction.
COLDSTAR_BURST_TO_PLASMA_RIFLE = "High-output Burst Cannon -> Plasma Rifle"
COLDSTAR_BURST_TO_TAU_FLAMER = "High-output Burst Cannon -> T'au Flamer"
COLDSTAR_BURST_TO_AIRBURSTING = "High-output Burst Cannon -> Airbursting Fragmentation Projector"

COMMANDER_IN_COLDSTAR_BATTLESUIT = TAU_EMPIRE.add_datasheet(Datasheet(
    "Commander in Coldstar Battlesuit",
    # User-supplied Keywords line: Character, Vehicle, Walker, Fly,
    # Battlesuit, Faction: T'au Empire (Faction dropped, same reasoning as
    # every other T'au datasheet - implicit in Faction registration).
    keywords=("CHARACTER", "VEHICLE", "WALKER", "FLY", "BATTLESUIT", "COMMANDER", "COLDSTAR"),
    model_lines=[
        ModelLine(ColdstarCommanderProfile, 1, _COLDSTAR_COMMANDER_LOADOUT, name=_COLDSTAR_COMMANDER_LINE),
    ],
    # TWO independent printed menus, exactly like the Enforcer Commander above:
    # "up to two of the following [drones], and can take duplicates" and "up to
    # three of the following", the second mixing guns with the three support
    # systems. Two groups, so a support system can never eat a drone slot.
    #
    # THIS USED TO BE THREE HAND-PICKED BUNDLES (+ 2x Burst Cannon, + Cyclic Ion
    # Blaster, + 3x Fusion Blaster) - one WargearOption per combination some
    # shipped list happened to buy. That could not express a menu-three pick of
    # three DIFFERENT items, and it could not express the support systems at all,
    # because a WargearOption trades a weapon for weapons and a Weapon Support
    # System is not one. The Enforcer had the printed shape right all along; this
    # is that shape, and the bundles are gone rather than kept alongside it -
    # two ways to say "+ 3 fusion blasters" is the drift this repo consolidates.
    gear_options=(drone_options(_COLDSTAR_COMMANDER_LINE, include_guardian=False,
                                allow_duplicates=True)
                  + support_menu_gear(_COLDSTAR_COMMANDER_LINE, [
                      # The starred items cannot be duplicated; the rest can,
                      # up to the menu's own cap of three.
                      ("Airbursting Fragmentation Projector",
                       AirburstingFragmentationProjectorProfile, 1),
                      ("Burst Cannon", BurstCannonProfile, 3),
                      ("Cyclic Ion Blaster", CyclicIonBlasterStandardProfile, 1),
                      ("Fusion Blaster", FusionBlasterProfile, 3),
                      ("Missile Pod", MissilePodProfile, 3),
                      ("Plasma Rifle", PlasmaRifleProfile, 3),
                      ("T'au Flamer", TauFlamerProfile, 3),
                  ])),
    gear_slots={_COLDSTAR_COMMANDER_LINE: {DRONE_GROUP: DRONE_SLOTS,
                                           BATTLESUIT_SUPPORT_GROUP: BATTLESUIT_SUPPORT_SLOTS}},
    wargear_options=[
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=HighOutputBurstCannonProfile,
            with_weapons=[FusionBlasterProfile],
            max_models=1, name=COLDSTAR_BURST_TO_FUSION,
        ),
        # The printed menu-one list is ten items long; these are the seven that
        # are weapons. Its other three are the support systems, which live in
        # the menu above for the reason written there.
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=HighOutputBurstCannonProfile,
            with_weapons=[BurstCannonProfile],
            max_models=1, name=COLDSTAR_BURST_TO_BURST_CANNON,
        ),
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=HighOutputBurstCannonProfile,
            with_weapons=[CyclicIonBlasterStandardProfile],
            max_models=1, name=COLDSTAR_BURST_TO_CYCLIC_ION,
        ),
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=HighOutputBurstCannonProfile,
            with_weapons=[MissilePodProfile],
            max_models=1, name=COLDSTAR_BURST_TO_MISSILE_POD,
        ),
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=HighOutputBurstCannonProfile,
            with_weapons=[PlasmaRifleProfile],
            max_models=1, name=COLDSTAR_BURST_TO_PLASMA_RIFLE,
        ),
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=HighOutputBurstCannonProfile,
            with_weapons=[TauFlamerProfile],
            max_models=1, name=COLDSTAR_BURST_TO_TAU_FLAMER,
        ),
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=HighOutputBurstCannonProfile,
            with_weapons=[AirburstingFragmentationProjectorProfile],
            max_models=1, name=COLDSTAR_BURST_TO_AIRBURSTING,
        ),
    ],
    # Official list: 1 model 95 pts, no per-copy tiering. The two wargear
    # additions above are both free (see their own note) so this stays 95
    # pts regardless of which/how many a build takes.
    points=TAU_EMPIRE_POINTS["Commander in Coldstar Battlesuit"],
    abilities_text=[
        'Leader: This model can be attached to the following units: Crisis Sunforge Battlesuits, '
        'Crisis Fireknife Battlesuits, Crisis Starscythe Battlesuits.',
        'Coldstar Commander: While this model is leading a unit, models in that unit have a Move '
        'characteristic of 12" and ranged weapons equipped by models in that unit have the [ASSAULT] '
        'ability.',
    ],
))
# Leader/Coldstar Commander are NOT engine-wired: both only ever take effect
# on an ATTACHED unit, which depends on the live Attached-Units flow this
# engine deliberately doesn't have yet (see CLAUDE.md's Später-Liste, same
# gap as Warboss's own "Might is Right") - see ColdstarCommanderProfile's own
# docstring in game/units.py.

_CADRE_FIREBLADE_LOADOUT = [CadreFirebladeCloseCombatWeaponProfile, FirebladePulseRifleProfile]
_CADRE_FIREBLADE_LINE = "Cadre Fireblade"

CADRE_FIREBLADE = TAU_EMPIRE.add_datasheet(Datasheet(
    "Cadre Fireblade",
    # User-supplied Keywords line: Character, Infantry, Grenades, Faction:
    # T'au Empire (Faction dropped, same reasoning as every other T'au
    # datasheet - implicit in Faction registration).
    keywords=("CHARACTER", "INFANTRY", "GRENADES", "CADRE FIREBLADE"),
    model_lines=[
        ModelLine(CadreFirebladeProfile, 1, _CADRE_FIREBLADE_LOADOUT, name=_CADRE_FIREBLADE_LINE),
    ],
    # No wargear_options: no "Wargear Options" swap-rule text was given for
    # this datasheet (only a "Unselected Profiles" reference block - Twin
    # Pulse Carbine/Missile Pod, both already exist as TwinPulseCarbineProfile
    # /MissilePodProfile in game/weapons.py with identical stats, so no new
    # classes were needed for them - but with no swap rule text of their
    # own), same documented gap as every other T'au datasheet's own
    # alternates. The DRONE menu is the printed one: "up to two of the
    # following, and can take duplicates - gun drone, marker drone, shield
    # drone", which is exactly drone_options(include_guardian=False,
    # allow_duplicates=True).
    #
    # It used to be gun_drone_gear() alone, "since only Gun Drone was ever
    # asked for on this model" - which is not a reason, it is the defect. A
    # datasheet is a transcription of what GW prints; which options a shipped
    # list happens to buy has nothing to do with which ones exist, and modelling
    # only the bought ones means the next list is blocked by a gap nobody put
    # there on purpose. Three of eighteen T'au datasheets were short this way;
    # the other two are the Coldstar and Enforcer menu-one support systems,
    # which are a real structural limit (a WargearOption trades weapons for
    # weapons and cannot set a profile flag), not an oversight.
    gear_options=drone_options(_CADRE_FIREBLADE_LINE, include_guardian=False,
                               allow_duplicates=True),
    gear_slots={_CADRE_FIREBLADE_LINE: 2},
    #
    # Official list: 1 model 50 pts, no per-copy tiering, no priced wargear.
    points=TAU_EMPIRE_POINTS["Cadre Fireblade"],
    abilities_text=[
        'Volley Fire: While this model is leading a unit, add 1 to the Attacks characteristic of '
        'ranged weapons equipped by models in that unit.',
        'Crack Shot: Each time this model makes a ranged attack, on a Critical Wound, that attack has '
        'an Armour Penetration characteristic of -3.',
        'Leader: This model can be attached to the following units: Breacher Team, Strike Team.',
    ],
))
# All three of this datasheet's abilities are engine-wired: Crack Shot (see
# game/crack_shot.py, game/shooting.py's own _begin_crack_shot_save()), Volley
# Fire (game/volley_fire.py, applied in game/shooting.py's _begin_resolution())
# and Leader (game/attached_units.py's can_attach(), which reads the pairing
# off this list's own `leads` table). Volley Fire was deferred while there was
# no Attached-Units flow for it to act on and was not picked up again when that
# arrived - which showed up as a Breacher Team firing 20 shots instead of 30.

# The two Missile Drones the Riptide "comes with" (user-supplied) are part of
# the printed loadout, not an optional menu item, so they live here rather
# than in gear_options - a build that didn't opt in would otherwise silently
# be missing baseline equipment.
#
# Each drone contributes its Missile pod, which is how EVERY drone in this
# engine is modeled: as a weapon/characteristic grant on the bearer, not as a
# separate model with its own wounds (see game/drones.py - Gun Drone adds a
# Twin pulse carbine to the bearer the same way).
#
# DroneMissilePodProfile, not the plain MissilePodProfile: the drone's own
# printed BS is 5+ while the Riptide is BS4+, so the override is doing real
# work here. The two were one class until a battlesuit carried a missile pod
# of its own (the Enforcer at BS3+, Crisis Fireknife at BS4+) and the drone's
# 5+ started forcing a wrong value - see MissilePodProfile's own note.
_RIPTIDE_LOADOUT = [
    RiptideFistsProfile, HeavyBurstCannonProfile, TwinPlasmaRifleProfile,
    DroneMissilePodProfile, DroneMissilePodProfile,  # 2x Missile Drone
]
_RIPTIDE_LINE = "Riptide Battlesuit"

_RIPTIDE_POINTS = TAU_EMPIRE_POINTS["Riptide Battlesuit"]

# The one wired wargear option. Its swap TEXT was not supplied (this
# datasheet came with a stat block, an Abilities list and an "Unselected
# Profiles" table, but no "Wargear Options" section) - what makes it more
# than a guess is that the official points list prices exactly one item for
# this unit, "per Ion accelerator 25 pts", which is only meaningful if the
# Ion accelerator is a real choice. It replaces the Heavy burst cannon
# rather than the Twin plasma rifle because those are the two big-gun
# profiles (72"/A6 vs 36"/A12), while the Twin plasma rifle is the
# secondary; flagged here as inferred, same "flagged, not confirmed" status
# as every other T'au wargear item in this file that has no screenshot.
RIPTIDE_BURST_TO_ION_ACCELERATOR = "Heavy Burst Cannon -> Ion Accelerator"
# Wired once a real army list actually asked for it ("1x Riptide Battlesuit:
# Riptide fists, Ion accelerator, 2x Missile pod, Twin fusion blaster"). The
# Twin fusion blaster is one of this datasheet's own "Unselected Profiles",
# and it replaces the Twin plasma rifle because that is the other
# secondary-weapon slot - the Ion accelerator already occupies the main one.
# Still an inference (no swap text was supplied) and free, since the points
# list prices nothing but the Ion accelerator for this unit.
RIPTIDE_PLASMA_TO_TWIN_FUSION = "Twin Plasma Rifle -> Twin Fusion Blaster"

RIPTIDE_BATTLESUIT = TAU_EMPIRE.add_datasheet(Datasheet(
    "Riptide Battlesuit",
    keywords=("VEHICLE", "WALKER", "FLY", "BATTLESUIT", "RIPTIDE"),
    model_lines=[
        ModelLine(RiptideProfile, 1, _RIPTIDE_LOADOUT, name=_RIPTIDE_LINE),
    ],
    wargear_options=[
        WargearOption(
            _RIPTIDE_LINE, replaces=HeavyBurstCannonProfile, with_weapons=[IonAcceleratorStandardProfile],
            max_models=1, name=RIPTIDE_BURST_TO_ION_ACCELERATOR,
            points=_RIPTIDE_POINTS.wargear["Ion accelerator"],
        ),
        WargearOption(
            _RIPTIDE_LINE, replaces=TwinPlasmaRifleProfile, with_weapons=[TwinFusionBlasterProfile],
            max_models=1, name=RIPTIDE_PLASMA_TO_TWIN_FUSION,
        ),
    ],
    # The remaining "Unselected Profiles" (Twin fusion blaster, Twin smart
    # missile system) stay unwired - no swap text was given for them and,
    # unlike the Ion accelerator, the points list prices neither, so there is
    # nothing to corroborate a guess. Same documented gap as every other T'au
    # datasheet's own alternates (see CLAUDE.md). The third entry, Missile
    # pod, is no longer in that category: it is the weapon the two baseline
    # Missile Drones carry (see _RIPTIDE_LOADOUT above).
    #
    # No optional drone MENU: the two Missile Drones are fixed equipment, and
    # no "can be equipped with" drone line was supplied for this datasheet -
    # inventing one would be inventing points-free wargear.
    #
    # Official list: 1 model 190 pts (1st-2nd unit) / 220 pts (3rd+), plus 25
    # for the Ion accelerator.
    points=_RIPTIDE_POINTS,
    abilities_text=[
        'Nova Charge: Once per battle, when this unit is selected to shoot in your Shooting phase, '
        'select one ranged weapon equipped by this model. Until the end of the phase, that weapon '
        'has the [DEVASTATING WOUNDS] ability.',
        'Damaged: 1-4 Wounds Remaining: While this model has 1-4 wounds remaining, each time this '
        'model makes an attack, subtract 1 from the Hit roll.',
        'Invulnerable Save (4+): This model has a 4+ invulnerable save.',
        "Battlesuit Support System: The bearer's unit is eligible to shoot in a turn in which it "
        'Fell Back, but when doing so only models equipped with this wargear can make ranged attacks.',
        'Weapon Support System: Each time the bearer makes a ranged attack, you can ignore any or '
        'all modifiers to the Hit roll.',
    ],
))
# Every one of this datasheet's abilities is engine-wired: Nova Charge
# (game/nova_charge.py, offered from ShootingController.start_shooting()),
# Damaged (game/shooting.py's _damaged_modifier(), the same field the
# Ghostkeel already uses), Invulnerable Save (UnitProfile.invulnerable_save -
# the first T'au datasheet here to have one), Battlesuit Support System
# (shooting.py's available_shooting_types(), reused from Crisis Starscythe -
# its extra "only models equipped with this wargear" clause is a no-op on a
# single-model unit that has the wargear) and Weapon Support System
# (shooting.py's _hit_modifiers(), handled exactly like rule 24.29's
# [PSYCHIC], whose wording it copies). Deadly Demise D6 and For The Greater
# Good are core/army rules already implemented elsewhere.

_PATHFINDER_LOADOUT = [TauCloseCombatWeaponProfile, PulseCarbineProfile, PulsePistolProfile]
_PATHFINDER_LEADER = "Pathfinder Shas'ui"
_PATHFINDER_LINE = "Pathfinder"

# Inferred wargear option (no "Wargear Options" text was supplied for this
# datasheet - only the stat block, an Abilities list and an "Unselected
# Profiles" table). What lifts it above a guess is the table's own "(x2)"
# annotation on both Semi-automatic grenade launcher sub-profiles: an
# up-to-2-models allowance is exactly the shape of a wargear swap, and 2 of
# 10 is not a number anything else on this datasheet produces. It replaces
# the Pulse carbine because that is the only weapon every rank-and-file
# model has to give up. Free, like everything else here - the official
# points list prices exactly one item for this unit, an "Ion rifle", which
# the supplied datasheet never mentions and which is therefore NOT modeled.
# An ADDITION, not a replacement - see the option itself. The name kept its
# old spelling so no caller has to change; it reads as a swap and is not one.
PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER = "+ Semi-automatic Grenade Launcher"
# The two special weapons, both supplied as real stat lines after the initial
# datasheet paste. Each replaces the Pulse carbine - that is the weapon the
# army list's own rail-rifle models give up ("3 with Close combat weapon,
# Pulse pistol, Rail rifle").
#
# max_models=3 because a supplied army list actually fields three Rail
# rifles, so three is demonstrably legal. Whether three is also the printed
# CAP is not confirmed - the rail rifle/ion rifle tables carry no "(xN)"
# annotation the way the grenade launcher's do - so this is a floor read as
# a cap, flagged rather than presented as fact.
PATHFINDER_CARBINE_TO_RAIL_RIFLE = "Pulse Carbine -> Rail Rifle"
PATHFINDER_CARBINE_TO_ION_RIFLE = "Pulse Carbine -> Ion Rifle"

_PATHFINDER_POINTS = TAU_EMPIRE_POINTS["Pathfinder Team"]
# THE LAUNCHER IS OFFERED ON BOTH MODEL LINES, and the second entry is not
# decoration: the printed text is "1 MODEL IN THIS UNIT equipped with a pulse
# carbine", and the Shas'ui carries one, so he is as eligible as any of the
# nine. A supplied army list buys exactly that ("1x Pathfinder Shas'ui: ...
# 1x Semi-automatic grenade launcher"), and with the option on the rank and
# file alone that build is silently unbuildable - build_squad() drops a
# `choices` entry naming a (line, option) pair the datasheet does not have,
# so the unit comes out one weapon short and correctly priced.
#
# This comment used to claim both lines while only one was wired, which is
# how the gap survived: a comment promising behaviour no code delivers.
#
# LIMITATION, named rather than enforced: max_models is per LINE, so the two
# entries together allow TWO launchers where the text allows one. Same
# already-documented shortcoming WargearOption has everywhere else - it has no
# way to express a cap across lines.

PATHFINDER_TEAM = TAU_EMPIRE.add_datasheet(Datasheet(
    "Pathfinder Team",
    keywords=("INFANTRY", "GRENADES", "MARKERLIGHT", "PATHFINDER TEAM"),
    model_lines=[
        ModelLine(PathfinderShasUiProfile, 1, _PATHFINDER_LOADOUT, name=_PATHFINDER_LEADER),
        ModelLine(PathfinderProfile, 9, _PATHFINDER_LOADOUT, name=_PATHFINDER_LINE),
    ],
    wargear_options=[
        # PRINTED: "1 model in this unit equipped with a pulse carbine can be
        # equipped with 1 semi-automatic grenade launcher. That model's pulse
        # carbine cannot be replaced." So it is an ADDITION, not a swap - the
        # model keeps its carbine - and it is ONE model in the whole unit.
        # This used to be two swap options (max 2 on the rank and file plus 1
        # on the Shas'ui), which cost the unit a pulse carbine it should keep
        # and allowed three launchers where the text allows one. Found by
        # transcribing the supplied army list, whose Pathfinder Team prints
        # "6x Pulse carbine ... 1x Semi-automatic grenade launcher" across nine
        # models - ten weapons for nine bodies, which only adds up if the
        # launcher is carried alongside a carbine.
        WargearOption(
            _PATHFINDER_LINE, replaces=None,
            with_weapons=[SemiAutomaticGrenadeLauncherEmpProfile],
            max_models=1, name=PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER,
        ),
        # The same option on the Shas'ui - see the note above the datasheet.
        WargearOption(
            _PATHFINDER_LEADER, replaces=None,
            with_weapons=[SemiAutomaticGrenadeLauncherEmpProfile],
            max_models=1, name=PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER,
        ),
        WargearOption(
            _PATHFINDER_LINE, replaces=PulseCarbineProfile, with_weapons=[RailRifleProfile],
            max_models=3, name=PATHFINDER_CARBINE_TO_RAIL_RIFLE,
        ),
        WargearOption(
            _PATHFINDER_LINE, replaces=PulseCarbineProfile, with_weapons=[IonRifleStandardProfile],
            max_models=3, name=PATHFINDER_CARBINE_TO_ION_RIFLE,
            points=_PATHFINDER_POINTS.wargear["Ion rifle"],
        ),
    ],
    # User: "kann 2 drohnen erhalten und eine spezialdrohne aus den 3" - two
    # menus with separate allowances, which is why gear_slots is the
    # per-group dict form here (see Datasheet.gear_slots): without it the
    # three special drones and the ordinary ones would share one pool and a
    # model could take three specials.
    #
    # WHICH ordinary drones was not stated. The menu is the same
    # drone_options() default every other T'au datasheet without a
    # screenshot uses (Marker/Shield/Guardian/Gun, no duplicates) - flagged
    # as unconfirmed, the same status Breacher Team's own menu carries -
    # plus a Missile Drone, which is NOT a guess: this datasheet's own
    # "Unselected Profiles" table lists a Missile pod, and no model of this
    # unit has any way to carry one except on a drone. The table's Twin
    # pulse carbine is accounted for the same way, by the Gun Drone.
    gear_options=(
        # allow_duplicates: a supplied army list gives this Shas'ui "2x Shield
        # Drone", so the no-duplicates default (an unconfirmed guess for this
        # datasheet, same status as Breacher Team's) would make a real build
        # unbuildable. Guardian Drone stays capped at 1 by its own text
        # wherever it appears - drone_options() enforces that regardless.
        drone_options(_PATHFINDER_LEADER, include_missile=True, allow_duplicates=True)
        + special_drone_options(_PATHFINDER_LEADER)
    ),
    gear_slots={_PATHFINDER_LEADER: {DRONE_GROUP: DRONE_SLOTS, SPECIAL_DRONE_GROUP: SPECIAL_DRONE_SLOTS}},
    #
    # Official list: 10 models 85 pts (1st-2nd unit) / 100 pts (3rd+), plus
    # 5 pts per Ion rifle - the list's one priced item, and now a real option
    # (its stat line arrived after the initial datasheet paste). The Rail
    # rifle is free by the same list.
    points=_PATHFINDER_POINTS,
    abilities_text=[
        'Target Uploaded: Each time a model in this unit makes an attack that targets their '
        'Spotted unit, improve the Ballistic Skill characteristic of that attack by 1 and that '
        'attack has the [IGNORES COVER] ability.',
    ],
))
# Both of this datasheet's rules and its ability are engine-wired: Target
# Uploaded (game/target_uploaded.py, applied in game/shooting.py's
# _hit_modifiers() and _cover_ignored_for_group()), Scouts 7" (rule
# 24.31/24.32 - game/scouts.py's Scout Move step of the Pre-game Sequence
# reads profile.scouts) and For The Greater Good (game/greater_good.py).
# The three special drones are wired in their own modules:
# game/grav_inhibitor_drone.py, game/pulse_accelerator.py, and - for the
# Recon Drone's Infiltrators half - game/squad.py's squad_has_infiltrators().

_SUNFORGE_LOADOUT = [CrisisBattlesuitFistsProfile, FusionBlasterProfile, FusionBlasterProfile]
_SUNFORGE_SHAS_VRE = "Crisis Sunforge Shas'vre"
_SUNFORGE_SHAS_UI_1 = "Crisis Sunforge Shas'ui (1)"
_SUNFORGE_SHAS_UI_2 = "Crisis Sunforge Shas'ui (2)"

CRISIS_SUNFORGE = TAU_EMPIRE.add_datasheet(Datasheet(
    "Crisis Sunforge Battlesuits",
    keywords=("VEHICLE", "WALKER", "FLY", "BATTLESUIT", "CRISIS", "SUNFORGE"),
    # Three separate ModelLines rather than one line of 3, mirroring its
    # sibling Crisis Starscythe: gear (drones) is tracked per line, so each
    # model needs its own line to make its own drone choice - see
    # build_squad()'s own note on that.
    model_lines=[
        ModelLine(CrisisSunforgeShasVreProfile, 1, _SUNFORGE_LOADOUT, name=_SUNFORGE_SHAS_VRE),
        ModelLine(CrisisSunforgeShasUiProfile, 1, _SUNFORGE_LOADOUT, name=_SUNFORGE_SHAS_UI_1),
        ModelLine(CrisisSunforgeShasUiProfile, 1, _SUNFORGE_LOADOUT, name=_SUNFORGE_SHAS_UI_2),
    ],
    # User: "Selbe drohnenregeln wie starsythe" - so exactly Crisis
    # Starscythe's menu, verbatim: up to two per model, no duplicates, no
    # Guardian Drone, re-scoped to each of the three lines. Deliberately NOT
    # include_missile, even though this datasheet's "Unselected Profiles"
    # table shows a Missile pod the way Pathfinder Team's does - Starscythe's
    # table shows one too and doesn't get one, and "same as Starscythe" is an
    # explicit instruction that outranks that inference.
    gear_options=[
        *drone_options(_SUNFORGE_SHAS_VRE, include_guardian=False),
        *drone_options(_SUNFORGE_SHAS_UI_1, include_guardian=False),
        *drone_options(_SUNFORGE_SHAS_UI_2, include_guardian=False),
    ],
    gear_slots={_SUNFORGE_SHAS_VRE: DRONE_SLOTS, _SUNFORGE_SHAS_UI_1: DRONE_SLOTS, _SUNFORGE_SHAS_UI_2: DRONE_SLOTS},
    # No wargear_options: every model carries the same printed 2x Fusion
    # blaster + Battlesuit fists, and no "Wargear Options" text was supplied.
    # The "Unselected Profiles" block (a Shas'ui with a Twin pulse carbine +
    # Missile pod instead) has no swap rule of its own and the official
    # points list prices nothing for this unit - same documented gap as every
    # other T'au datasheet's own Unselected Profiles.
    #
    # Official list: 3 models 125 pts (1st-2nd unit) / 135 pts (3rd+), no
    # priced wargear.
    points=TAU_EMPIRE_POINTS["Crisis Sunforge Battlesuits"],
    abilities_text=[
        'Sunforge: Each time a model in this unit makes a ranged attack that targets a Monster or '
        'Vehicle unit, you can re-roll the Wound roll and you can re-roll the Damage roll.',
        'Invulnerable Save (4+): Models in this unit have a 4+ invulnerable save.',
    ],
))
# Both abilities and both rules are engine-wired: Sunforge (game/sunforge.py -
# the Wound half joins game/shooting.py's existing _wound_reroll_reason(),
# the Damage half is a new DamageAllocationSession collaborator), Invulnerable
# Save (UnitProfile.invulnerable_save), Deep Strike (24.09, game/ingress.py)
# and For The Greater Good (game/greater_good.py). This datasheet is also a
# legal Leader target for Commander in Coldstar Battlesuit - the pairing is
# already in the points list's own `leads` table, which game/attached_units.py
# reads.

# Both models carry the same three "support" entries; only the main gun
# differs. Each of Fusion eliminator / XV pulse pistol / Ion scattercannon
# prints BOTH a ranged and a melee profile on the datasheet, so both classes
# are in the loadout - the printed sheet lists each in both tables, and this
# engine keys a weapon's type off `weapon_type`.
#
# The MV15 Gun Drone is baseline equipment, not an optional menu item
# ("MV15 Gun Drone: The bearer is equipped with 1 Twin pulse blaster"), so
# its weapon sits in the loadout directly - same treatment as the Riptide's
# two Missile Drones, and the same engine-wide convention that a drone is a
# weapon grant on its bearer rather than a model of its own.
_TWIN_LANCE_SHARED = [
    ShardstormBurstSystemProfile,
    XvPulsePistolProfile, XvPulsePistolMeleeProfile,
    TwinPulseBlasterProfile,  # MV15 Gun Drone
]
_RI_LANTAR_LOADOUT = [FusionEliminatorProfile, FusionEliminatorMeleeProfile] + _TWIN_LANCE_SHARED
_RI_LOCAI_LOADOUT = [IonScattercannonStandardProfile, IonScattercannonMeleeProfile] + _TWIN_LANCE_SHARED

THE_TWIN_LANCE = TAU_EMPIRE.add_datasheet(Datasheet(
    "The Twin Lance",
    keywords=("EPIC HERO", "VEHICLE", "WALKER", "FLY", "CHARACTER", "BATTLESUIT", "THE TWIN LANCE"),
    # Two ModelLines for two named models with different main guns - not a
    # leader/rank-and-file split (this unit has no leader in the rules
    # sense), purely because their loadouts differ.
    model_lines=[
        ModelLine(RiLantarProfile, 1, _RI_LANTAR_LOADOUT, name="Ri'Lantar"),
        ModelLine(RiLocaiProfile, 1, _RI_LOCAI_LOADOUT, name="Ri'Locai"),
    ],
    # No wargear_options and no drone menu: every weapon on this datasheet is
    # printed equipment, the only "➤" pair is the Ion scattercannon's two
    # firing modes (one weapon, see IonScattercannonStandardProfile), and no
    # "can be equipped with" text was supplied. The official points list
    # prices nothing for this unit.
    #
    # Official list: 2 models 220 pts, flat - an EPIC HERO, so no per-copy
    # tiering.
    points=TAU_EMPIRE_POINTS["The Twin Lance"],
    abilities_text=[
        "Neocapacitor Shields: At the start of your opponent's Charge phase, you can select one "
        'enemy unit (excluding Monster and Vehicle units) within 12" of this unit. That unit must '
        'take a Battle-shock test and, until the end of the turn, subtract 1 from Charge rolls '
        'made for that unit.',
        "Exemplars of Mont'ka: Each time a model in this unit makes a ranged attack that targets "
        'the closest eligible target, that attack has the [SUSTAINED HITS 1] and [IGNORES COVER] '
        'abilities.',
        'Retro-thrusters: At the end of the Fight phase, if this unit was eligible to fight this '
        'phase, this unit can either make a Normal move of up to 6" or a Fall Back move.',
        'Invulnerable Save (4+): Models in this unit have a 4+ invulnerable save.',
        'MV15 Gun Drone: The bearer is equipped with 1 Twin pulse blaster.',
    ],
))
# Every ability and rule on this datasheet is engine-wired: Neocapacitor
# Shields (game/neocapacitor_shields.py), Exemplars of Mont'ka
# (game/exemplars_of_montka.py), Retro-thrusters (game/retro_thrusters.py),
# Invulnerable Save (UnitProfile.invulnerable_save), MV15 Gun Drone (in the
# loadout above), For The Greater Good (game/greater_good.py), Scouts 8"
# (game/scouts.py), Deep Strike (24.09, game/ingress.py) and the unit-level
# Ignores Cover (UnitProfile.ignores_cover, read by shooting.py's
# _cover_ignored_for_group()).

_FARSIGHT_LOADOUT = [
    HighIntensityPlasmaRifleProfile,
    # The Dawn Blade's two "➤" modes are two melee WeaponProfiles rather
    # than a firing-mode pair - rule 04.01 already lets a model attack with
    # only ONE of its melee weapons per fight, so carrying both IS "pick a
    # mode". See their own note in game/weapons.py.
    DawnBladeStrikeProfile, DawnBladeSweepProfile,
]

COMMANDER_FARSIGHT = TAU_EMPIRE.add_datasheet(Datasheet(
    "Commander Farsight",
    keywords=("EPIC HERO", "VEHICLE", "WALKER", "FLY", "CHARACTER", "BATTLESUIT", "COMMANDER FARSIGHT"),
    model_lines=[
        ModelLine(CommanderFarsightProfile, 1, _FARSIGHT_LOADOUT, name="Commander Farsight"),
    ],
    # No wargear options and no drone menu: everything on this datasheet is
    # printed equipment, no "can be equipped with" text was supplied, and the
    # official points list prices nothing for this unit.
    #
    # Official list: 1 model 70 pts, flat - an EPIC HERO, so no per-copy
    # tiering.
    points=TAU_EMPIRE_POINTS["Commander Farsight"],
    abilities_text=[
        'Way of the Short Blade: While this model is leading a unit, each time a model in that '
        'unit makes an attack that targets an enemy unit within 9", add 1 to the Wound roll.',
        "Puretide's Teachings: Once per battle round, one unit from your army with this ability "
        'can use it when its unit is targeted with a Stratagem. If it does, reduce the CP cost of '
        'that use of that Stratagem by 1CP.',
        'Leader: This model can be attached to the following units: Crisis Sunforge Battlesuits, '
        'Crisis Fireknife Battlesuits, Crisis Starscythe Battlesuits.',
        'Invulnerable Save (4+): This model has a 4+ invulnerable save.',
        'Independent Power: If your army includes Commander Farsight, it cannot include any '
        'Ethereal units. If your army includes any Ethereal units, it cannot include Commander '
        'Farsight.',
    ],
))
# Every ability is engine-wired except one, and that one is named here rather
# than dropped silently: Way of the Short Blade (game/way_of_the_short_blade.py,
# applied in BOTH shooting.py's and fight.py's _wound_modifiers()), Puretide's
# Teachings (game/puretide.py, plugged into StratagemController.cost_discounts),
# Leader (game/attached_units.py's can_attach(), reading the pairing off this
# list's own `leads` table - two of the three named units, Crisis Fireknife
# Battlesuits, still has no datasheet here), Invulnerable Save
# (UnitProfile.invulnerable_save), plus Deep Strike (24.09) and For The Greater
# Good. "Independent Power" is the exception: it is an army-BUILDING
# restriction, and this engine has no army-building flow to enforce it against
# - the same documented gap that leaves EPIC HERO's own "only one" unenforced.
# No Ethereal datasheet exists here either, so nothing can violate it today.


register_faction(TAU_EMPIRE)
