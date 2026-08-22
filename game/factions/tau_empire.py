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

from game.drones import (
    DRONE_GROUP, DRONE_SLOTS, SPECIAL_DRONE_GROUP, SPECIAL_DRONE_SLOTS,
    drone_options, gun_drone_gear, marker_drone_gear, special_drone_options,
)
from game.homing_beacon import homing_beacon_gear
from game.factions import Datasheet, Detachment, Enhancement, Faction, ModelLine, WargearOption, register_faction
from game.factions.tau_empire_points import TAU_EMPIRE_POINTS
from game.units import (
    BreacherFireWarriorProfile, BreacherFireWarriorShasUiProfile, CadreFirebladeProfile,
    ColdstarCommanderProfile, CommanderFarsightProfile,
    CrisisStarscytheShasUiProfile, CrisisStarscytheShasVreProfile,
    CrisisSunforgeShasUiProfile, CrisisSunforgeShasVreProfile, DevilfishProfile, FireWarriorProfile,
    FireWarriorShasUiProfile, GhostkeelProfile, KrootCarnivoreProfile, LongQuillProfile,
    PathfinderProfile, PathfinderShasUiProfile, RiLantarProfile, RiLocaiProfile, RiptideProfile,
    StealthShasUiProfile, StealthShasVreProfile,
)
from game.weapons import (
    AcceleratorBurstCannonProfile, ArmouredHullProfile, BattlesuitFistsProfile, BurstCannonProfile,
    CadreFirebladeCloseCombatWeaponProfile, CrisisBattlesuitFistsProfile, CyclicIonBlasterStandardProfile,
    CyclicIonRakerStandardProfile, DevilfishTwinPulseCarbineProfile, FirebladePulseRifleProfile,
    FusionBlasterProfile, FusionColliderProfile, GhostkeelFistsProfile, HeavyBurstCannonProfile,
    HighOutputBurstCannonProfile, IonAcceleratorStandardProfile,
    KrootCloseCombatWeaponProfile, KrootPistolProfile, KrootRifleProfile, MissilePodProfile,
    PulseBlasterProfile,
    PulseCarbineProfile, PulsePistolProfile, PulseRifleProfile, RiptideFistsProfile,
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
    rule_text=(
        'Bonded Heroes: Each time a T\'au Empire Battlesuit model from your army makes a '
        'ranged attack that targets a unit within 12", improve the Strength characteristic '
        'of that attack by 1. If that attack targets a unit within 9", improve the Armour '
        'Penetration characteristic of that attack by 1 as well.'
    ),
    # Unlike `rule_text` and `stratagems` above, this Enhancement IS
    # engine-wired (game/starflare_ignition.py) - the record here is its
    # descriptive half, and game/starflare_ignition.py's grant() is what
    # actually puts it on a model. Filed under this detachment because it is
    # the only one that exists; the user supplied it as a T'au Empire
    # Enhancement without naming a detachment, so that placement is an
    # assumption, not something read off the source.
    enhancements=[
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
    # `stratagems` is deliberately left empty: this detachment's two
    # stratagems (Stim Injectors, The Arro'kon Protocol) are engine-wired
    # in game/stim_injectors.py and game/arrokon_protocol.py, and a real
    # game.stratagems.Stratagem needs a per-battle controller for its
    # `effect` - so the objects are built in main.py, not stored as static
    # faction data. Same relationship the Bonded Heroes rule_text above has
    # to game/retaliation_cadre.py.
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
    # blaster" doesn't say WHICH 2 of the unit's 5 models - scoped here to
    # the Shas'ui line only (max_models=2, capping at that line's own
    # rank-and-file models rather than the one-model Shas'vre line), a
    # judgment call flagged the same way as similar per-line splits
    # elsewhere in this module.
    wargear_options=[
        WargearOption(_STEALTH_LEADER, replaces=None, with_weapons=[PulsePistolProfile], max_models=1, name=STEALTH_PULSE_PISTOL_OPTION),
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
    already part of the printed default loadout. The reverse swap is free,
    and the default flamer itself is never charged (see
    game/factions/points.py for why)."""
    return [
        WargearOption(
            line_name, replaces=BurstCannonProfile, with_weapons=[TauFlamerProfile],
            name=STARSCYTHE_BURST_TO_FLAMER, points=_STARSCYTHE_POINTS.wargear["T'au flamer"],
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
COLDSTAR_ADD_2X_BURST_CANNON = "+ 2x Burst Cannon (Slot)"
COLDSTAR_ADD_CYCLIC_ION_BLASTER = "+ Cyclic Ion Blaster (Slot)"

COMMANDER_IN_COLDSTAR_BATTLESUIT = TAU_EMPIRE.add_datasheet(Datasheet(
    "Commander in Coldstar Battlesuit",
    # User-supplied Keywords line: Character, Vehicle, Walker, Fly,
    # Battlesuit, Faction: T'au Empire (Faction dropped, same reasoning as
    # every other T'au datasheet - implicit in Faction registration).
    keywords=("CHARACTER", "VEHICLE", "WALKER", "FLY", "BATTLESUIT", "COMMANDER", "COLDSTAR"),
    model_lines=[
        ModelLine(ColdstarCommanderProfile, 1, _COLDSTAR_COMMANDER_LOADOUT, name=_COLDSTAR_COMMANDER_LINE),
    ],
    # Drones: no official screenshot for this datasheet's own drone menu
    # either - reusing the same generic "up to 2, no Guardian Drone, can
    # take duplicates" menu already used for Crisis Starscythe/Stealth
    # Battlesuits (Battlesuit-line convention), flagged the same way.
    gear_options=drone_options(_COLDSTAR_COMMANDER_LINE, include_guardian=False, allow_duplicates=True),
    gear_slots={_COLDSTAR_COMMANDER_LINE: 2},
    wargear_options=[
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=None, with_weapons=[BurstCannonProfile, BurstCannonProfile],
            max_models=1, name=COLDSTAR_ADD_2X_BURST_CANNON,
        ),
        WargearOption(
            _COLDSTAR_COMMANDER_LINE, replaces=None, with_weapons=[CyclicIonBlasterStandardProfile],
            max_models=1, name=COLDSTAR_ADD_CYCLIC_ION_BLASTER,
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
    # alternates. Gun Drone gear IS added (user-supplied, "2x Gun Drone" -
    # not from an official screenshot for this specific datasheet, same
    # "flagged, not confirmed" status as Coldstar Commander's own drone menu
    # above) - reusing the standalone gun_drone_gear() helper (same one
    # Stealth Battlesuits' Shas'vre uses for its own single Gun Drone) with
    # max_count=2 instead of the full drone_options() menu, since only Gun
    # Drone was ever asked for on this model.
    gear_options=[gun_drone_gear(_CADRE_FIREBLADE_LINE, max_count=2)],
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
# MissilePodProfile is reused as-is, and its hardcoded "5+" ballistic_skill
# override is CORRECT here for the second time on this datasheet: the drone's
# own printed BS is 5+ while the Riptide is BS4+, so the override is doing
# real work rather than forcing a wrong value (same reasoning as the
# datasheet's own "Unselected Profiles" Missile pod entry below).
_RIPTIDE_LOADOUT = [
    RiptideFistsProfile, HeavyBurstCannonProfile, TwinPlasmaRifleProfile,
    MissilePodProfile, MissilePodProfile,  # 2x Missile Drone
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
PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER = "Pulse Carbine -> Semi-automatic Grenade Launcher"
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
# Offered on BOTH model lines. The "(x2)" annotation caps the unit at two
# launchers, but says nothing about WHICH two models - and a supplied army
# list puts one on the Shas'ui ("1x Pathfinder Shas'ui: ... Semi-automatic
# grenade launcher"), so restricting the option to the rank and file would
# make a real, legal build unbuildable. max_models is per LINE, so the two
# entries could in principle total three; the printed cap is not enforced
# across lines, the same already-documented limitation WargearOption has
# everywhere else.

PATHFINDER_TEAM = TAU_EMPIRE.add_datasheet(Datasheet(
    "Pathfinder Team",
    keywords=("INFANTRY", "GRENADES", "MARKERLIGHT", "PATHFINDER TEAM"),
    model_lines=[
        ModelLine(PathfinderShasUiProfile, 1, _PATHFINDER_LOADOUT, name=_PATHFINDER_LEADER),
        ModelLine(PathfinderProfile, 9, _PATHFINDER_LOADOUT, name=_PATHFINDER_LINE),
    ],
    wargear_options=[
        WargearOption(
            _PATHFINDER_LINE, replaces=PulseCarbineProfile,
            with_weapons=[SemiAutomaticGrenadeLauncherEmpProfile],
            max_models=2, name=PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER,
        ),
        WargearOption(
            _PATHFINDER_LEADER, replaces=PulseCarbineProfile,
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
