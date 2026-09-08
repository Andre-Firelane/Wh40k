import copy

from game import attached_units, battle_focus, line_of_sight, status_effects
from game.ard_as_nails import ARD_AS_NAILS_WOUND_PENALTY, ard_as_nails_wound_modifier_applies
from game.damage_estimate import wound_threshold as _wound_threshold  # rule 05.02's S-vs-T table; moved to a leaf module so game/stim_injectors.py can reach it without an import cycle - re-exported here under its old private name for game/fight.py and ai/ (see game/damage_estimate.py's docstring)
from game.damage_resolution import DamageAllocationSession, DevastatingWoundAllocationSession, MortalWoundAllocationSession, displayed_save_threshold, save_is_impossible, AUTO_FAILED_SAVE
from game.hazard import hazard_failures, hazard_mortal_wounds
from game.dice import ATTACKS_ROLL, HIT_ROLL, SAVE_ROLL, SNAP_SHOT_HIT_ROLL, WOUND_ROLL
from game.dice_notation import DiceNotation, DiceNotationRoll, describe as describe_dice_notation
from game.modifiers import Modifier, apply_modifiers, describe_modifiers
from game.objectives import is_on_objective
from game.arrokon_protocol import arrokon_adjusted_weapon
from game import psychic_guidance
from game import protect
from game.doom import DOOM_WOUND_BONUS
from game.crit_hit import crit_hit_threshold
from game import psychic_communion
from game import storm_of_silence
from game import assured_destruction
from game import swift_demise
from game import target_acquisition
from game import crystalline_targeting
from game import wave_serpent_shield
from game.fire_support import FIRE_SUPPORT_LABEL
from game.hand_of_asuryan import hand_of_asuryan_adjusted_weapon
from game.notation_reroll import DamageRerollOffer
from game.weapons import NON_MONSTER_VEHICLE, anti_entries
from game import conditional_devastating_wounds
from game import corsair_abilities
from game import reavers_of_the_void
from game import structural_collapse
from game.bladestorm import bladestorm_adjusted_weapon
from game import crit_ap
from game import fate_inescapable
from game.drive_by_dakka import drive_by_dakka_adjusted_weapon
from game.gun_crazy_showoffs import gun_crazy_adjusted_weapon, unit_has_gun_crazy_showoffs
from game.ammo_runt import ammo_runt_adjusted_weapon
from game.nova_charge import nova_charge_adjusted_weapon
from game import awakened_dynasty, destroyer_cult, dlc_mortarions_teachings, exemplars_of_montka, gift_of_contagion, hovering_death, miasma_of_pestilence, protocol_conquering_tyrant, protocol_sudden_storm, guardian_protocols, implacable_eradication, mechanical_augmentation, monster_hunters, overwhelming_obliteration, plagues, reroll_scope, sunforge, target_uploaded, way_of_the_short_blade
from game import weapon_range
from game.retaliation_cadre import bonded_heroes_adjusted_weapon
from game import (aux_experimental_modifications, aux_guided_fire,
                  epc_experimental_ammunition, hidden_after_shooting,
                  exemplars_of_montka, kauyon, kauyon_coordinate_to_engage,
                  kauyon_point_blank_ambush, kauyon_tempting_trap, montka,
                  montka_combat_debarkation, montka_focused_fire,
                  montka_pinpoint_counter_offensive)
# The T'au detachment Enhancements that touch the shooting sequence. Each is
# registered in game/enhancements.py, which owns who bears one and gates it on
# the detachment actually fielded; these modules hold only the rule.
from game import (enh_guided_keyword_grants, enh_precision_patient_hunter,
                  enh_prototype_weapon_system)
from game.starscythe import starscythe_adjusted_weapon
from game.squad import (
    allocation_target_model, allocation_target_profile, attached_unit_toughness, edge_distance, is_monster_or_vehicle_unit, squad_has_advanced_guardian_drone, squad_has_agile_combatant, squad_has_battlesuit_support_system, squad_has_war_construct,
    squad_has_breach_and_clear, squad_has_guardian_drone, squad_has_stealth, tank_hunters_modifiers,
)
from game import advanced_scouting as advanced_scouting_module
from game import fated_hero as fated_hero_module
from game import defend_at_all_costs
from game import guardian_blades_of_asuryan
from game import guardian_shield_nodes
from game import guardian_warding_salvoes
from game import enh_breath_of_vaul
from game import enh_guiding_presence
from game import enh_mirage_field
from game import enh_protector_of_the_paths
from game import enh_rune_of_mists
from game import enh_shimmerstone
from game import enh_assassins_eye
from game import enh_psychic_weapons
from game import aspect_doom_inescapable
from game import aspect_preternatural_precision
from game import aspect_warrior_focus
from game import conclave_seers_eye
from game import warhost_blitzing_firepower
from game import warhost_lightning_fast_reactions
from game import windrider_death_from_on_high
from game import windrider_focused_firepower
from game import move_exceptions
from game import shepherds_of_the_dead
from game import path_of_the_warrior
from game import far_reaching_doom
from game import skilled_crews
from game import ynnari_abilities
from game import misfortune as misfortune_module
from game import spiritseer
from game import armour_hunter as armour_hunter_module
from game import fireknife
from game import velocity_tracker as velocity_tracker_module
from game import bounty_hunters as bounty_hunters_module
from game import oversight_drone as oversight_drone_module
from game import hero_of_the_empire as hero_of_the_empire_module
from game import precise_targeting as precise_targeting_module
from game import structural_analyser as structural_analyser_module
from game.coldstar import weapon_has_assault
from game.thresholds import parse_threshold as _parse_threshold
from game.turn import PHASE_SHOOTING
from game.volley_fire import volley_fire_extra_attacks
from game.weapons import RANGED

# The abilities that can turn one die of a roll into an unmodified 6. Both
# expose the same four names, so the offer below is built from whichever one
# actually applies rather than duplicated per ability - the same "second
# consumer turns a field into a list" move made for target_reactions,
# cost_discounts and on_squad_finished_shooting.


IDLE = "idle"
CHOOSING_SHOOTING_TYPE = "choosing_shooting_type"  # pick Normal/Assault/Close-Quarters/Indirect (rule 10.02)
CHOOSING_TARGET = "choosing_target"     # non-split-fire: pick the single enemy squad
CHOOSING_WEAPON = "choosing_weapon"     # pick an attack group to fire (also used while a group resolves)
ASSIGNING = "assigning"                 # split-fire: assign each model+weapon its own target

# Rule 10.02 step 2 / 10.04-10.07: the four shooting types.
NORMAL_SHOOTING = "Normal"
ASSAULT_SHOOTING = "Assault"
CLOSE_QUARTERS_SHOOTING = "Close-Quarters"
INDIRECT_SHOOTING = "Indirect"
# Rule 15.09: a fifth shooting type, but never offered as a normal choice
# (it never appears in available_shooting_types()) - only ever entered via
# ShootingController.start_snap_shooting(), which a stratagem (Fire
# Overwatch, 15.08, game/overwatch.py) triggers reactively outside the
# unit's own Shooting phase.
SNAP_SHOOTING = "Snap Shooting"
SNAP_SHOT_RANGE_IN = 24.0  # rule 15.09: "one visible enemy unit within 24\" of your unit" - a unit-level cap on top of each weapon's own range

_UNSET = object()  # sentinel for _is_valid_target_squad's optional overrides - None is a real shooting_type value (nothing active yet)


def _resolve_roll(roll, threshold, crit_threshold=6):
    """Rules 05.01/05.02: unmodified 1 always fails, unmodified 6 is always a
    critical success, otherwise it succeeds if it meets the required threshold.
    Shared by hit rolls (BS/WS) and wound rolls (S vs T). Rule 24.03's
    [ANTI-X Y+] lowers the wound roll's critical threshold to Y against a
    matching target - see _wound_crit_threshold()."""
    if roll == 1:
        return "fail"
    if roll >= crit_threshold:
        return "critical"
    if threshold is not None and roll >= threshold:
        return "success"
    return "fail"


_KEYWORD_FIELDS = {
    "INFANTRY": "infantry", "BEASTS": "beasts", "SWARM": "swarm", "MOBILE": "mobile",
    "CHARACTER": "character", "MONSTER": "monster", "VEHICLE": "vehicle",
    # The Visarch's mythic stance prints [ANTI-EPIC HERO 2+] - the first
    # weapon here to name that keyword, and the profile flag already
    # existed for rule 15.03 (Epic Challenge).
    "EPIC HERO": "epic_hero",
}


def _unit_has_keyword(squad, keyword):
    """Whether ANY model in squad has the named keyword - used by rule
    24.03's [ANTI-X Y+]. Only the keywords we actually model as UnitProfile
    fields are recognized (see the Boyz entry in CLAUDE.md's Später-Liste
    for why there's no generic keyword system yet); an unrecognized keyword
    (e.g. PSYKER) never matches.

    Rule 19.03 (Keywords in Attached Units): "An attached unit has all of
    the keywords of all of its component units" - e.g. a Leader model with
    PSYKER gives the whole attached unit the PSYKER keyword even though its
    bodyguard models don't have it, so [ANTI-PSYKER] still triggers against
    that unit regardless of which specific model the wound is allocated to.
    any(), not all(): for an ordinary (non-attached) unit every model
    shares the same keywords anyway, so this is behaviorally identical to
    the old all()-based check there - the difference only matters once a
    squad actually mixes profiles (an attached unit, rule 19.01)."""
    if keyword == NON_MONSTER_VEHICLE:
        # The NEGATED form, which no keyword field can express - the
        # Stonesinger prints [ANTI-non-MONSTER/VEHICLE X+]. Answered as the
        # exact complement of is_monster_or_vehicle_unit(), which is the
        # same pair Monster Hunters and Grim Reapers already use to divide
        # the board between them.
        return not is_monster_or_vehicle_unit(squad)
    field = _KEYWORD_FIELDS.get(keyword)
    if field is None:
        return False
    return any(getattr(m.profile, field, False) for m in squad.models)


#: Rule 24.03's [ANTI-X Y+] as a uniform sequence of (keyword, threshold).
#: The definition lives in game/weapons.py beside the field it reads, because
#: printed_keywords() is a second consumer of the same question - re-exported
#: here so this module's own call site and its name are unchanged.
_anti_entries = anti_entries


def _wound_crit_threshold(weapon, target_squad):
    """Rule 05.02 default: an unmodified 6 is always a critical wound. Rule
    24.03's [ANTI-X Y+] lowers that to Y against a target with keyword X.

    A weapon may carry several [ANTI-X] keywords; where more than one names
    a keyword this target has, the BEST (lowest) threshold applies - each is
    an independent grant, and nothing in 24.03 makes them cancel. A target
    that is both MONSTER and VEHICLE therefore just gets the better of the
    two, rather than whichever happened to be listed first."""
    thresholds = [
        threshold for keyword, threshold in _anti_entries(weapon)
        if _unit_has_keyword(target_squad, keyword)
    ]
    return min(thresholds) if thresholds else 6


def _weapon_split_across_targets(weapon_key, split_fire, assignments):
    """Rule 24.06's [CLEAVE] bonus only applies if "you only selected one
    target for all of that weapon's attacks" - true unless split-fire sent
    this same weapon at more than one distinct target this attack sequence."""
    if not split_fire:
        return False
    targets = {target for key, target in assignments if key == weapon_key}
    return len(targets) > 1


def extra_attack_dice(weapon, target_squad, weapon_key, split_fire, assignments, pairs=()):
    """Rules 24.05/24.06/24.30: [BLAST]/[CLEAVE] add extra attack dice for
    every five models in the target unit (rounding down), based on the
    group's representative weapon (pairs[0][1]) - same simplification
    already used elsewhere in this file (e.g. _hit_modifiers) when a group
    could theoretically mix weapons with identical stats but different
    abilities. [RAPID FIRE X] instead adds X extra attack dice PER
    ATTACKING MODEL in `pairs` (not scaled by target size, unlike
    [BLAST]/[CLEAVE]) if the target was within half range - the same
    half-range aggregate-group check melta_adjusted_weapon() uses ("was...
    in the Select Targets step" approximated with current positions, since
    nothing moves between target selection and dice-gathering here).
    Shared by shooting.py and fight.py, like _resolve_roll/_wound_threshold."""
    model_count = len(target_squad.models)
    bonus = 0
    if weapon.blast:
        bonus += weapon.blast * (model_count // 5)
    if weapon.cleave and not _weapon_split_across_targets(weapon_key, split_fire, assignments):
        bonus += weapon.cleave * (model_count // 5)
    if weapon.rapid_fire and pairs:
        # Half of the EFFECTIVE Range characteristic, not the printed one - see
        # game/weapon_range.py. Measured per shooter because the bonus comes
        # from the shooter's own unit.
        in_half_range = any(
            edge_distance(shooter, defender) <= weapon_range.half_range_in(shooter, weapon)
            for shooter, _ in pairs
            for defender in target_squad.models
        )
        if in_half_range:
            bonus += weapon.rapid_fire * len(pairs)
    return bonus


def melta_adjusted_weapon(weapon, pairs, target_squad):
    """Rule 24.25 ([MELTA X]): "if the target unit was within half range of
    that weapon in the Select Targets step... add X to that weapon's D
    characteristic". Approximated using CURRENT positions rather than a
    snapshot from Select Targets - equivalent here, since nothing moves
    between target selection and damage resolution within a single
    activation in this engine. Evaluated once for the whole group (true if
    ANY attacking model in `pairs` is within half range of ANY target
    model), the same representative-group simplification already used
    elsewhere in this file (e.g. [HEAVY], [CLOSE-QUARTERS]). Returns a
    shallow copy with `.damage` bumped by X, so the shared WeaponProfile
    instance itself is never mutated - callers that don't need the bonus
    just get `weapon` back unchanged. When the weapon's Damage is itself
    dice-notation (`.damage_notation` - e.g. Ghostkeel's Twin Fusion
    Blaster, printed "D6", which also has [MELTA 2]), the bonus has to land
    on the notation's own flat bonus instead (bumping only the preview/
    grouping placeholder `.damage` would do nothing once DamageAllocationSession
    actually rolls the die) - `.damage` is still bumped too, purely so the
    Save-roll preview text and _attack_key grouping stay consistent with it."""
    if not weapon.melta:
        return weapon
    # Half of the EFFECTIVE Range characteristic. Fuegan's Burning Lance adds 6"
    # to exactly these weapons, and half of a characteristic that has been added
    # to is half of the new number - so a 12" fusion gun under his lead reaches
    # 18" and its melta bonus reaches 9". See game/weapon_range.py.
    in_half_range = any(
        edge_distance(shooter, defender) <= weapon_range.half_range_in(shooter, weapon)
        for shooter, _ in pairs
        for defender in target_squad.models
    )
    if not in_half_range:
        return weapon
    boosted = copy.copy(weapon)
    boosted.damage = weapon.damage + weapon.melta
    if weapon.damage_notation is not None:
        boosted.damage_notation = DiceNotation(weapon.damage_notation.sides, weapon.damage_notation.bonus + weapon.melta)
    return boosted


def _model_can_reach(model, weapon, target_squad, obstacles, visible_models, all_tokens=(),
                     shooting_type=None, terrain_areas=()):
    """Rule 10.07: an [INDIRECT FIRE] weapon fired as Indirect shooting can
    target units not visible to the attacking model - range still applies,
    line of sight doesn't. Rule 24.24 (LONE OPERATIVE): on top of the
    general "not visible to enemy models" gate in _is_valid_target_squad(),
    a Lone Operative "cannot be targeted by [INDIRECT FIRE] weapons unless
    the attacking model is within X\" of this unit" - a per-MODEL
    restriction, since Indirect Fire otherwise lets any model in the unit
    fire regardless of its own distance to the target.

    `visible_models` is REQUIRED, and it is the models of `target_squad` rule
    13.09 lets this attacking unit see - see _detectable_models(). Required
    rather than defaulted to "all of them", because the default is precisely
    the bug it exists to prevent:

        Reported by a user, and measured on their own board. Hidden was asked
        ONCE, at unit level, in _is_valid_target_squad ("is ANY model of the
        target detectable"), and range+line of sight were asked here over
        target_squad.models - so the two halves could be satisfied by
        DIFFERENT models. On the reported board the Lokhust Destroyers had
        line of sight to Pathfinders 1, 2 and 3 only, all three hidden and 20
        to 22" away (detection range 15"), while the models that passed the
        Hidden gate were 6 to 9, standing outside the ruin with no line of
        sight to them at all. Nothing was both visible and shootable, and the
        unit was shot anyway.

    The LONE OPERATIVE clause below deliberately still measures against the
    whole unit: its printed text is "within X\" of this UNIT", a distance, not
    a visibility question."""
    bypass_los = shooting_type == INDIRECT_SHOOTING and weapon.indirect_fire
    if bypass_los:
        lone_range = status_effects.targeting_range_limit(target_squad)
        if lone_range is not None and not any(
            edge_distance(model, defender) <= lone_range for defender in target_squad.models
        ):
            return False
    # Two abilities can have added to this weapon's Range characteristic (the
    # Pulse Accelerator Drone, Fuegan's Burning Lance), both derived live from
    # the shooter's own unit rather than baked into the weapon - see
    # game/weapon_range.py, which is now the one definition and is also read by
    # the two HALF-range sites above ([RAPID FIRE X], [MELTA X]).
    reach_in = weapon_range.effective_range_in(model, weapon)
    return any(
        edge_distance(model, defender) <= reach_in
        and (bypass_los or line_of_sight.has_line_of_sight(model, defender, obstacles, all_tokens, terrain_areas))
        for defender in visible_models
    )


def is_close_quarters(weapon, squad):
    """Does this weapon have [CLOSE-QUARTERS]/[PISTOL] - printed, or granted?

    Rule 24.27 ([PISTOL]): "[PISTOL] and [CLOSE-QUARTERS] are identical for all
    rules purposes" - a pure alias, checked everywhere [CLOSE-QUARTERS]
    (10.06/24.07) is checked, instead of duplicating each call site's logic for
    a second flag.

    `squad` IS REQUIRED, and that is the whole of the fix here. Like [ASSAULT]
    (see weapon_has_assault(), which this mirrors), [PISTOL] is read in TWO
    places that look nothing like each other: the adjuster chain, which is the
    damage maths and is what every unit test drives, AND the ELIGIBILITY GATE
    below - available_shooting_types() and _weapon_eligible_for_type(), which
    decide whether an engaged unit may shoot at all (10.06). That permission is
    the ONE thing a [PISTOL] grant is bought for, so a grant reaching only the
    chain looks wired while failing to do it.

    REPORTED, of Blades of Asuryan: "ich konnte zwar mit asurmen schiessen,
    aber nicht mit dem rest meines avengers squads. das umwandeln der waffen in
    pistol hat wohl nicht geklappt." Measured on that scene: after buying the
    Stratagem the chain granted [PISTOL] to 6 of 6 ranged weapons while this
    gate still saw 1 of 6 - Asurmen's Bloody Twins, which is printed [PISTOL].
    Word for word the Protocol of the Sudden Storm finding, one detachment
    over, which is why the parameter is MANDATORY rather than defaulted: a
    default is exactly the bug it is here to prevent (the same reasoning
    _detectable_models() gives for its own).

    ONE GRANT TODAY, and any second one belongs in this body -
    test_event_chain_wiring.py section 19 is the set difference that says so.
    """
    if weapon.close_quarters or weapon.pistol:
        return True
    # Blades of Asuryan (Guardian Battlehost): "until the end of the phase,
    # ranged weapons equipped by models in your unit have the [PISTOL]
    # ability". Its own adjusted_weapon() applies the RANGED gate and the
    # never-a-downgrade rule, so this asks it rather than re-reading the flag.
    granted = guardian_blades_of_asuryan.adjusted_weapon(weapon, squad)
    return bool(granted is not weapon and granted.pistol)


def _living_count(squad):
    """Living models in a unit, right now.

    Its own function because "living" is not "in Squad.models":
    remove_dead_models() runs once per frame, so a model killed this
    activation is still in the list with is_dead() True. Every count this file
    compares across an activation has to mean the same thing."""
    return sum(1 for m in (getattr(squad, "models", ()) or ()) if not m.is_dead())


def _damaged_modifier(model):
    """Ghostkeel Battlesuit's own "Damaged: 1-4 Wounds Remaining" ability
    (user-supplied, not a core rule): "while this model has 1-4 wounds
    remaining, each time this model makes an attack, subtract 1 from the
    Hit roll" - a living model always has at least 1 wound remaining, so
    this only ever needs the upper bound (UnitProfile.damaged_threshold).
    Shared by shooting.py's and fight.py's own _hit_modifiers() - the
    ability isn't restricted to ranged attacks."""
    threshold = model.profile.damaged_threshold
    if threshold is not None and model.current_wounds <= threshold:
        return [Modifier(1, "Damaged")]
    return []


def _threshold_note(final, base, modifiers):
    """The number a reported roll is actually about: what it needed, and -
    when modifiers moved it - what it started from and which ability moved
    it.

    The dice panel has shown this all along (see _begin_resolution()'s roll
    label), but the LOG line only ever printed the dice and the outcome, so
    every "this should have hit on 3+" report had to be re-derived from the
    board by hand instead of read off the log. Same lesson as the [move
    choice] / [charge] / [coherency] lines: a diagnostic that omits the one
    contested number sends the next investigation back to the coordinates.

    Silent when there is nothing to explain (no threshold at all - e.g. an
    auto-hitting [TORRENT] attack - or an unmodified roll keeps it to the
    bare "needed X+")."""
    if final is None:
        return ""
    if not modifiers or base is None:
        return f" (needed {final}+)"
    return f" (needed {final}+: base {base}+, {describe_modifiers(modifiers)})"


def effective_ballistic_skill(model, weapon):
    """Almost every weapon's accuracy is purely the wielding model's own BS
    (see WeaponProfile's own docstring). A few (e.g. Strike Team's Support
    Turret, Twin Pulse Carbine, Missile Pod) print their own, worse BS on
    the datasheet instead of using their wielder's - weapon.ballistic_skill,
    when set, overrides the model's."""
    return weapon.ballistic_skill if weapon.ballistic_skill is not None else model.profile.ballistic_skill


def _attack_key(model, weapon):
    """Two attacks are 'identical' (rule 04.03) when they share BS/WS, S, AP
    and D - regardless of the weapons' names - and so get rolled together.
    [CLOSE-QUARTERS] (and, per 24.27, [PISTOL]) is also part of the key:
    rule 24.07 treats a model's [CLOSE-QUARTERS]/[PISTOL] weapon(s) and its
    other ranged weapons as two mutually exclusive "sides" for the shooting
    activation, even if their stats happen to coincide - they must stay in
    separate groups so one side can be chosen (and locked in, see
    _weapon_side_lock) independently of the other. Uses the weapon's
    EFFECTIVE BS (see effective_ballistic_skill()), not just the model's
    own, so e.g. a Shas'ui's Pulse Pistol (BS4+) and a borrowed/granted
    Support Turret (its own BS5+) never end up rolled together even though
    every other stat coincides.

    [MELTA X] (24.25) is in the key too, because it is a Damage modifier and
    Damage is one of the four things 04.03 groups on - two weapons that differ
    only in their melta value do NOT deal the same damage inside half range.
    Without it they would share a group, and melta_adjusted_weapon()'s
    one-representative shortcut would then hand the whole group whichever
    value the first model happened to carry. Fire Dragons are the datasheet
    that exposed this: the Exarch's Dragon fusion gun is [MELTA 6] where the
    squad's is [MELTA 3], and everything else about the two rows is identical.
    Every other melta weapon in this engine is [MELTA 2], so nothing that
    already existed groups differently because of this.

    The Warlock Conclave's Psychic Communion bonus is in the key for the same
    reason: it is a PER-MODEL bonus (each Warlock counts the psykers around
    ITSELF) that raises Strength and Attacks, so two Warlocks of one unit can
    legitimately deserve different numbers. game/psychic_communion.py's
    docstring claimed the groups "sort themselves out for free" because the
    bonus changes S and S is part of this key - but this key reads the RAW
    weapon.strength, before any adjuster runs, so they did NOT: both Warlocks
    landed in one group and psychic_communion_adjusted_weapon()'s
    one-representative shortcut handed whichever bonus pairs[0] happened to
    carry to the whole group. Putting the bonus itself in the key is what
    makes that docstring true and the shortcut exact. It is 0 for every model
    without the ability, so no group that already existed splits.

    Two T'au Enhancements are in the key for exactly that reason, and it is
    exactly that trap: Precision of the Patient Hunter is a PER-MODEL bonus to
    the Hit roll (and, from round 3, the Wound roll), and Prototype Weapon
    System grants a keyword to THE BEARER's weapons only. After a rule 19.01
    merge either is carried by one model out of ten, so without them here the
    one-representative shortcut would hand pairs[0]'s answer to the whole
    group. Both read 0/"" for every model without the Enhancement, so no group
    that already existed splits."""
    return (effective_ballistic_skill(model, weapon), weapon.strength, weapon.ap, weapon.damage,
            is_close_quarters(weapon, getattr(model, "squad", None)), weapon.melta,
            getattr(model, "psychic_communion_bonus", 0),
            enh_precision_patient_hunter.hit_bonus(model),
            enh_prototype_weapon_system.attack_key(model),
            # Seersight Strike and Psychic Destroyer are per BEARER and change
            # characteristics this key groups on - fourth and fifth instance of
            # the one-representative fix. (False, False) for every other model.
            enh_psychic_weapons.attack_key(model))


def _weapon_eligible_for_type(weapon, shooting_type, squad):
    """Rule 10.05/10.06: Assault shooting only uses [ASSAULT] weapons;
    Close-Quarters shooting only uses [CLOSE-QUARTERS] weapons unless the
    unit is a MONSTER/VEHICLE unit (which can use any weapon, at a hit
    penalty applied elsewhere). Normal and Indirect shooting don't restrict
    which ranged weapons can be used."""
    if shooting_type == ASSAULT_SHOOTING:
        # weapon_has_assault(), not weapon.assault: Coldstar Commander's own
        # ability (user-supplied) grants [ASSAULT] to every ranged weapon in
        # the unit it leads - see game/coldstar.py.
        return weapon_has_assault(weapon, squad)
    if shooting_type == CLOSE_QUARTERS_SHOOTING:
        return True if is_monster_or_vehicle_unit(squad) else is_close_quarters(weapon, squad)
    return True


def _weapon_side(weapon, squad):
    """Which of rule 24.07's two sides this weapon is on.

    Takes the squad for the same reason is_close_quarters() does: a
    granted [PISTOL] really does put the weapon on the pistol side, and
    when the grant covers every ranged weapon in the unit the side-lock
    stops splitting them - which is exactly what "they are all pistols
    now" means."""
    return "close_quarters" if is_close_quarters(weapon, squad) else "other"


def _side_locked_out(model, weapon, shooting_type, side_lock):
    """Rule 24.07: outside Close-Quarters shooting, each non-MONSTER/VEHICLE
    model can only make attacks with one "side" of its ranged weapons this
    shooting activation - its [CLOSE-QUARTERS] weapon(s), or its other
    ranged weapon(s), not both. Whichever side the model's first fired
    weapon this activation belongs to locks in the choice (side_lock,
    populated as weapon groups actually get committed) for the rest of it."""
    if shooting_type == CLOSE_QUARTERS_SHOOTING:
        return False
    if model.profile.monster or model.profile.vehicle:
        return False
    locked = side_lock.get(model)
    return locked is not None and locked != _weapon_side(weapon, getattr(model, "squad", None))


def _attack_groups(squad, shooting_type=None, side_lock=None, one_shot_used=None):
    """{attack_key: [(model, weapon), ...]} for every *ranged* weapon every
    model in the squad carries (melee weapons are for the fight phase,
    later), filtered by shooting_type's weapon-keyword restriction if any,
    by rule 24.07's [CLOSE-QUARTERS] side-lock if a side_lock dict is given
    (only meaningful within a single already-started shooting activation -
    callers checking bare eligibility pass none), and by rule 24.26's
    [ONE SHOT] - a (model, weapon) pair already in `one_shot_used` (a
    ShootingController's persistent-for-the-whole-battle set, unlike the
    per-phase fired_weapon_types) can never be selected again."""
    groups = {}
    for model in squad.models:
        for weapon in model.weapons:
            if weapon.weapon_type != RANGED:
                continue
            if shooting_type is not None and not _weapon_eligible_for_type(weapon, shooting_type, squad):
                continue
            if side_lock is not None and _side_locked_out(model, weapon, shooting_type, side_lock):
                continue
            if one_shot_used is not None and weapon.one_shot and (model.id, id(weapon)) in one_shot_used:
                continue
            groups.setdefault(_attack_key(model, weapon), []).append((model, weapon))
    return groups


def _overcharge_instance(weapon):
    """A fresh instance of `weapon`'s alternate firing mode (e.g. a Cyclic Ion
    Raker's Overcharge), tagged with which real weapon it stands for. Never
    mutates or shares the Standard-mode instance sitting in model.weapons -
    same "never share weapon instances" invariant ModelLine's own docstring
    documents. The tag exists purely for rule 24.26's [ONE SHOT] ledger, which
    is keyed by weapon instance - see _finish_group()."""
    instance = weapon.overcharge_profile()
    instance.overcharge_of_id = id(weapon)
    return instance


def _group_label(pairs):
    names = sorted({weapon.name for _, weapon in pairs})
    return "/".join(names) if names else "Weapon"


def _visible_to_any_friendly(squad, target_squad, obstacles, all_tokens, terrain_areas=()):
    friendlies = [t for t in all_tokens if t.squad is not None and t.squad.owner == squad.owner]
    return any(
        line_of_sight.has_line_of_sight(friendly, defender, obstacles, all_tokens, terrain_areas)
        for friendly in friendlies
        for defender in target_squad.models
    )


def available_shooting_types(squad, all_tokens, movement_controller=None):
    """Rule 10.02 step 2 / 10.04-10.07: which shooting types this squad is
    eligible to select for its one shooting activation this phase. Rule
    09.07: a unit that Fell Back this turn cannot shoot at all - unlike
    Advance (which only rules out Normal Shooting, still allowing Assault
    weapons), this blocks every shooting type. Crisis Starscythe
    Battlesuits' "Battlesuit Support System" ability (user-supplied, not a
    core rule) is a whole-unit exception to that block - see
    squad_has_battlesuit_support_system(). Wraithguard's "War Construct" is
    the second source of exactly the same exception, word for word ("this
    unit is eligible to shoot in a turn in which it Fell Back")."""
    # The Foetid Bloat-drone's Hovering Death is the second exception to rule
    # 09.07's shooting ban after a Fall Back, alongside the Crisis suits'
    # Battlesuit Support System - so it is asked at the same gate.
    # Commander Shadowsun's Agile Combatant is the fourth exception, and the
    # third printed wording of the same sentence - so it is asked at the same
    # gate as the other three.
    if squad.fell_back_this_turn and not move_exceptions.may_shoot_after_falling_back(squad):
        return []
    engaged = squad.is_engaged(all_tokens)
    advanced = movement_controller is not None and squad in movement_controller.advanced_squad_ids

    groups = _attack_groups(squad)  # unfiltered - just checking which weapon keywords exist at all
    has_assault = any(weapon_has_assault(w, squad) for plist in groups.values() for _, w in plist)
    # is_close_quarters(w, squad), not w.pistol: Blades of Asuryan grants
    # [PISTOL] to the whole unit, and THIS is the gate that decides whether
    # an engaged unit may shoot at all - the one thing the grant is bought
    # for. See is_close_quarters()'s own docstring for the report.
    has_close_quarters = any(is_close_quarters(w, squad) for plist in groups.values() for _, w in plist)
    has_indirect_fire = any(w.indirect_fire for plist in groups.values() for _, w in plist)

    # Guardian Battlehost's Time to Strike and Windrider Host's Wind of Blades
    # both say "your unit is eligible to shoot ... in a turn in which it
    # Advanced" - about the UNIT, not about a weapon, so it cannot be a
    # keyword grant. See game/move_exceptions.py.
    if advanced and move_exceptions.may_shoot_after_advancing(squad):
        advanced = False

    types = []
    if not engaged and not advanced:
        types.append(NORMAL_SHOOTING)
    if not engaged and advanced and has_assault:
        types.append(ASSAULT_SHOOTING)
    if engaged and not advanced and (has_close_quarters or is_monster_or_vehicle_unit(squad)):
        types.append(CLOSE_QUARTERS_SHOOTING)
    if not engaged and not advanced and has_indirect_fire:
        types.append(INDIRECT_SHOOTING)
    return types


class ShootingController:
    """Squad-level shooting with 'fast dice rolling': every weapon making
    identical attacks (same BS/WS, S, AP, D) at the same target rolls its
    hit/wound/save dice together, per rule 04.03 - unless part of that
    group has Benefit of Cover (13.08) against the target and part doesn't
    (different models, different line of sight through terrain), in which
    case _dispatch_group() splits it into two separate dice sequences
    instead (see its docstring and _finish_group()'s _pending_subgroups).

    Default (split_fire off): the whole squad fires at one target you pick
    once. Toggle split_fire on to assign every model+weapon its own target
    individually before anything is rolled.
    """

    def __init__(
        self, obstacles=None, game_log=None, player_name="Player 1", dice_manager=None,
        turn_tracker=None, all_tokens=None, movement_controller=None, terrain_areas=None,
        decision_manager=None, greater_good=None, suppression=None, objectives=None, stealth_drones=None,
        barrage_of_filth=None, spore_laced=None,
        waaagh=None, target_reactions=(), nova_charge=None, ammo_runt=None, fire_support=None, hand_of_asuryan=None, guide=None, doom=None, whispering_web=None,
        advanced_scouting=None, bounty_hunters=None, oversight_drone=None,
        sonic_destruction=None, monofilament_snare=None, misfortune=None,
        spirit_mark=None, piratical_raiders=None, fury_of_the_void=None,
        fated_hero=None, herald_of_ynnead=None, path_of_the_warrior=None,
        shepherds_of_the_dead=None,
        targeting_array=None,
        prototype_weapon_system=None,
        unmasking_suite=None,
    ):
        self.active_squad = None
        self.state = IDLE
        self.split_fire = False
        self.obstacles = obstacles if obstacles is not None else []
        self.terrain_areas = terrain_areas if terrain_areas is not None else []
        self.objectives = objectives if objectives is not None else []  # Breacher Team's Breach and Clear ability - see _wound_reroll_reason()
        self.game_log = game_log
        # The Defiler's Barrage of Filth (game/barrage_of_filth.py), which strips
        # cover from a unit it hit. A collaborator like `suppression` above rather
        # than a flag, because the mark lives for a phase and belongs to nobody's
        # Squad in particular.
        self.barrage_of_filth = barrage_of_filth
        # The Plagueburst Crawler's Spore-laced Shock Waves - fed at target
        # selection, resolved from on_squad_finished_shooting. A collaborator
        # for the same reason barrage_of_filth is one.
        self.spore_laced = spore_laced
        self.player_name = player_name
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager  # rule 24.23's [LETHAL HITS]: "you can choose" - the first real DecisionManager consumer
        self.greater_good = greater_good  # T'au Empire army rule (For The Greater Good) - optional, like decision_manager; see game/greater_good.py
        self.suppression = suppression  # Strike Team's Suppression Volley ability - optional, like greater_good; see game/suppression.py
        self.stealth_drones = stealth_drones  # Ghostkeel Battlesuit's Stealth Drones ability - optional, like greater_good; see game/stealth_drones.py
        self.hand_of_asuryan = hand_of_asuryan  # Asurmen's once-per-battle weapon grant - optional, same shape and same start_shooting()-only trigger as nova_charge (see game/hand_of_asuryan.py)
        self.guide = guide  # the Farseer's Guide mark - optional; read by _hit_modifiers() (see game/guide.py)
        self.doom = doom  # Eldrad Ulthran's Doom mark - optional; read by _wound_modifiers() (see game/doom.py)
        self.whispering_web = whispering_web  # Lhykhis' Whispering Web mark - optional; read by the hit step's crit threshold (see game/whispering_web.py)
        self.fire_support = fire_support  # the Falcon's Fire Support mark - optional; read by _wound_reroll_reason() (see game/fire_support.py)
        self.bounty_hunters = bounty_hunters  # Kroot Farstalkers' battle-long bounty - optional; read by _adjusted_weapon()'s chain (see game/bounty_hunters.py)
        self.oversight_drone = oversight_drone  # the Vespid Strain Leader's once-per-battle [IGNORES COVER] - optional, same shape and same start_shooting()-only trigger as nova_charge (see game/oversight_drone.py)
        self.targeting_array = targeting_array  # the two gunships' once-per-activation single-die re-roll - optional; its ledger is opened by start_shooting() and closed by _actually_finish_squad() (see game/targeting_array.py)
        self.unmasking_suite = unmasking_suite  # Advanced Acquisition Cadre's Unmasking Suite Enhancement - optional; read by rule 13.09's detectability check, and opened/closed on the same activation seams as prototype_weapon_system below ("when this unit is selected to shoot" / "until this unit has shot"). See game/enh_unmasking_suite.py
        self.prototype_weapon_system = prototype_weapon_system  # Retaliation Cadre's Prototype Weapon System Enhancement - optional; opened and closed on the SAME two seams as targeting_array above, because its printed timing is the same pair ("each time the bearer is selected to shoot" / "until those attacks are resolved"). See game/enh_prototype_weapon_system.py
        self.advanced_scouting = advanced_scouting  # the Kroot Lone-Spear's mark - optional; WRITTEN by the hit step (a mark placed by a hit, not by an attack) and read by _hit_reroll_reason() (see game/advanced_scouting.py)
        self.fated_hero = fated_hero  # the Wraithlord's chosen-keyword ledger - optional; read by BOTH _hit_reroll_reason() and _wound_reroll_reason(), because the printed text re-rolls a 1 on each (see game/fated_hero.py)
        self.shepherds_of_the_dead = shepherds_of_the_dead  # Spirit Conclave's Vengeful Dead tokens - optional; read by BOTH _hit_modifiers() and _wound_modifiers() here and in game/fight.py, because the printed text says "makes an attack" (see game/shepherds_of_the_dead.py)
        self.path_of_the_warrior = path_of_the_warrior  # Aspect Host's per-activation choice of a mandatory 1s re-roll on Hit OR Wound - optional; offered by start_shooting() and read by BOTH automatic-ones branches in this file (see game/path_of_the_warrior.py)
        self.herald_of_ynnead = herald_of_ynnead  # Yvraine's start-of-Fight-phase mark - optional. A BELIEVED NO-OP on this side today and wired anyway: the printed text says "makes an attack", not "a melee attack", but the mark is set at the start of the Fight phase and cleared at its end, so nothing in an ordinary Shooting phase can see it. Written out rather than left to the next reader to re-derive - the same call Command Protocols records. See game/ynnari_abilities.py
        self.misfortune = misfortune  # the Farseer Skyrunner's mark - optional; read here on the ATTACKER side, since it penalises the marked unit's OWN Wound rolls (see game/misfortune.py)
        self.spirit_mark = spirit_mark  # the Spiritseer's (friendly, enemy) pairs - optional; see game/spiritseer.py
        self.piratical_raiders = piratical_raiders  # the Voidscarred's battle-long mark - optional; see game/corsair_abilities.py
        self.fury_of_the_void = fury_of_the_void  # Kharseth's riven mark - optional; a STRENGTH change, so it rides the adjuster chain (see game/fury_of_the_void.py)
        self.sonic_destruction = sonic_destruction  # the Vibro Cannon Platforms' shared per-phase ledger - optional; see game/sonic_destruction.py
        self.monofilament_snare = monofilament_snare  # the Shadow Weaver Platforms' snare marks - optional; WRITTEN here (the mark is placed by a hit) and read from game/movement.py
        self.ammo_runt = ammo_runt  # Flash Gitz' Ammo Runt wargear - optional, same shape and same start_shooting()-only trigger as nova_charge (see game/ammo_runt.py)
        self.nova_charge = nova_charge  # Riptide Battlesuit's Nova Charge ability - optional, like greater_good; offered from start_shooting() only (see game/nova_charge.py)
        self.waaagh = waaagh  # Orks army rule "Waaagh!" - optional, like greater_good (its invulnerable-save boost applies to an Ork squad being SHOT AT, not just when it's shooting/fighting); see game/waaagh.py
        # Reactive stratagems whose WHEN is "just after an enemy unit has
        # selected its targets" - Stim Injectors and 'Ard as Nails today.
        # A LIST rather than one named field per stratagem: the trigger is a
        # shared moment in the sequence (rule 10.02's "select targets" step,
        # i.e. wherever _snapshot_target_state() is called), and the two that
        # exist differ only in what they then do. Each entry needs one method,
        # maybe_offer(attacker, target, melee=...).
        self.target_reactions = [r for r in target_reactions if r is not None]
        self.shot_squad_ids = set()
        self.fired_weapon_types = {}  # squad -> set of attack_keys already fired this phase
        self.last_ranged_attack_turn = {}  # squad -> turn_tracker.turn_number_for(owner) as of its last shot (rule 13.09)
        # Auxiliary Cadre's prey mark, set after construction like the other
        # optional collaborators here. None means "no such detachment in this
        # battle", and rule 13.09 then measures the printed detection range.
        self.auxiliary_cadre = None
        # Kauyon's A Tempting Trap, for the wound step. None means "nobody
        # plays that detachment", and the modifier is simply never added.
        self.tempting_trap = None
        # Mont'ka's Pinpoint Counter-Offensive, for the hit re-roll. None
        # means nobody plays that detachment.
        self.pinpoint_counter_offensive = None
        # Armoured Warhost's Guiding Presence, for the hit step. Its mark
        # lives on the controller (it is per PLAYER, not per squad), so this
        # is a collaborator rather than a flag. None means nobody plays it.
        self.guiding_presence = None
        # Guardian Battlehost's Protector of the Paths, for the Snap Shooting
        # threshold. The DISCOUNT object itself, because the latch that says
        # which activation is the free one lives on it.
        self.protector_of_the_paths = None
        self.one_shot_used = set()  # rule 24.26: (model.id, id(weapon)) pairs already fired - persists for the whole battle, never reset
        # Shroud Runners' Target Acquisition needs to know WHICH weapon hit,
        # not just which unit - "hit by one or more of those attacks made with
        # a long rifle". Weapon NAMES rather than classes, because the rule
        # names the weapon that way too and the deciding is left to
        # game/target_acquisition.py rather than done here.
        self._hit_weapon_names_this_activation = {}  # id(squad) -> {weapon name}
        self._living_when_first_hit = {}  # id(squad) -> living models when first hit this activation; see _handle_hit_results() and models_lost_this_activation()
        self._hit_target_squads_this_activation = set()  # Suppression Volley: enemy squads hit by 1+ attacks this activation, see _handle_hit_results()/on_squad_finished_shooting
        # Maugan Ra's Harvester of Souls needs "every attack targets the SAME
        # unit", which the hit set above cannot answer: a group that targeted a
        # second unit and missed with everything still split the fire. Recorded
        # at _begin_resolution(), where the target is decided.
        self._targeted_squads_this_activation = set()
        # Rule 13.09 (Hidden): whether this activation has actually resolved a
        # weapon group yet. Deliberately NOT _hit_target_squads_this_activation,
        # which is about HITTING - a unit that fires and misses with everything
        # still made a ranged attack and still stops being Hidden.
        self._fired_this_activation = False
        # Callables (squad, hit_target_squads), fired for every REAL
        # (non-reactive) activation, unlike the per-call
        # _on_activation_finished below. A LIST since it grew a second
        # consumer: Suppression Volley (game/suppression.py) and the Aeldari
        # Agile Manoeuvre Fade Back (game/battle_focus.py), which needs
        # exactly the "was hit by one or more of those attacks" set this
        # already tracks. Same generalisation target_reactions and
        # StratagemController.cost_discounts got for the same reason.
        self.on_squad_finished_shooting = []
        self.target_acquisition = None  # game/target_acquisition.py, set in main.py
        self.crystalline_targeting = None  # game/crystalline_targeting.py, set in main.py

        # shooting type (rule 10.02 step 2)
        self.shooting_type = None
        self.available_types = []  # the choices offered while state == CHOOSING_SHOOTING_TYPE

        # non-split-fire
        self.target_squad = None
        self.remaining_weapon_types = []  # list of attack_keys not yet fired

        # split-fire
        self.assignment_queue = []   # [(model, weapon), ...] still needing a target
        self.assignments = {}        # (attack_key, target_squad) -> [(model, weapon), ...]
        self.assignment_overcharge = False  # alternate firing mode armed for the NEXT assignment - see toggle_assignment_overcharge()
        self.resolved_groups = []    # queued {"weapon_key", "weapon_label", "target_squad", "pairs"} dicts

        self.current_group = None    # the group currently being rolled
        self.pending_step = None     # "attacks" | "hit" | "wound" | "save" | "save_crit_ap" | "allocate" | None
        # Set by _skip_impossible_save() when a Save roll was skipped because
        # no model of the target could ever pass it; read and cleared by
        # _check_allocation_done() so the log says so instead of listing dice
        # that were never thrown.
        self._save_not_rolled = None
        self.damage_session = None   # DamageAllocationSession while pending_step == "allocate"
        self.devastating_wound_session = None  # DevastatingWoundAllocationSession, rule 24.10
        self._devastating_crits = 0  # crits pulled out of the current wound roll for [DEVASTATING WOUNDS]
        self._pending_crit_ap_crits = 0  # critical wounds pulled out of the current wound roll for their own Save roll at a different AP - Cadre Fireblade's Crack Shot (override to -3) or Seer Council's Fate Inescapable (improve by 1); see game/crit_ap.py, _begin_crit_ap_save()
        self._hazardous_count = 0  # [HAZARDOUS] weapons FIRED this activation - one roll each, rule 24.15
        self._lethal_hits_auto_wounds = 0  # rule 24.23: hits chosen to auto-wound, folded into normal_wounds once the (possibly skipped) wound roll resolves
        self._twin_linked_used = False  # rule 24.38: whether this group's one-time re-roll offer has already been made/used
        self._pending_attacks_roll = None  # DiceNotationRoll while pending_step == "attacks" (a dice-notation Attacks characteristic, e.g. a printed "D6", rolled once per attacking model before the Hit roll can even start - see WeaponProfile.attacks_notation)
        self._pending_ones_reroll = None  # Forward Observers (user-supplied): context dict while pending_step == "hit_reroll_ones"/"wound_reroll_ones"
        self._pending_twin_linked_reroll = None  # rule 24.38/Breach and Clear: context dict while pending_step == "wound_twin_linked_reroll"
        self._hit_reroll_used = False  # Monster Hunters (user-supplied): whether this group's one-time Hit-roll re-roll offer has already been made/used - the hit-step twin of _twin_linked_used above
        self._pending_hit_reroll = None  # Monster Hunters: context dict while pending_step == "hit_monster_hunters_reroll"
        self._pending_sustained = None       # hit-step context while pending_step == "sustained_hits"
        self._pending_sustained_roll = None  # DiceNotationRoll while pending_step == "sustained_hits" (a dice-notation [SUSTAINED HITS X], one die per critical hit)
        self._pending_strength_roll = None  # DiceNotationRoll while pending_step == "strength" (a dice-notation Strength characteristic, e.g. the Zzap gun's printed "D6+6")
        self._pending_strength = None       # context dict carried across that roll
        self._rolled_strength = None        # what it came up as, for THIS weapon group
        self.mortal_wound_session = None  # MortalWoundAllocationSession while pending_step == "hazard_wounds"

        # Rule 13.08 (Benefit of Cover): a single weapon selection (or one
        # split-fire resolved_groups entry) can end up cover-split into two
        # physical dice sequences - see _dispatch_group()/_finish_group().
        # _pending_subgroups holds whatever's left to resolve for the
        # CURRENT selection; the other three fields are its shared context
        # (weapon_key/target_squad/base label stay constant across the
        # split, only `pairs` and the label suffix differ per sub-group).
        self._pending_subgroups = []  # [(pairs, label_suffix), ...] still queued
        self._pending_subgroups_target_squad = None
        self._pending_subgroups_base_label = None
        self._pending_subgroups_hazardous = 0  # how many [HAZARDOUS] weapons this selection fired; added once, not per sub-group

        self._weapon_side_lock = {}  # rule 24.07: model -> "close_quarters"/"other", once committed this activation

        # Rule 10.02: targets are selected BEFORE any of the unit's attacks
        # are resolved, so range/line of sight/cover are judged once, at that
        # moment, and hold for the unit's whole activation - see
        # _snapshot_target_state()/_can_reach()/_has_benefit_of_cover().
        self._reach_snapshot = {}  # (model, id(weapon), target_squad) -> bool
        self._cover_snapshot = {}  # (shooter_model, target_squad) -> bool
        self._closest_target_snapshot = {}  # target_squad -> was it the closest eligible target when selected (Exemplars of Mont'ka)

        self._weapon_eligibility_cache_key = None    # see weapon_eligibility() - avoids re-running
        self._weapon_eligibility_cache_result = []   # a has_line_of_sight() sweep every single frame

        # Rule 15.08/15.09 (Fire Overwatch / Snap Shooting): a reactive
        # activation started via start_snap_shooting(), not the unit's own
        # real Shooting-phase turn - see that method's docstring. Kept
        # separate from _on_activation_finished below: "reactive" is about
        # shot_squad_ids/fired_weapon_types bookkeeping, not about whether
        # there's a completion callback (rule 24.14's Firing Deck needs one
        # for a perfectly normal, non-reactive activation too).
        self._reactive = False
        # Awakened Dynasty's Protocol of the Vengeful Stars: "it MUST target
        # only that enemy unit". None = no restriction, which is every other
        # activation in the game.
        self._restrict_targets_to = None
        self._on_activation_finished = None  # callable, fires once this activation ends, reactive or not

    # Set by main.py once game/actions.py's controller exists - rule 16.01's
    # "not eligible to shoot" lock. None means no actions system in play.
    action_controller = None

    def can_shoot(self, squad):
        if squad is None or squad in self.shot_squad_ids:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False  # rule 07.02: units only shoot during the Shooting phase
            # ...and it has to be the unit's OWN Shooting phase. Real user
            # report ("der battle wagon hat overwatch eingesetzt und hat
            # einfach immer wieder mit den big shoota geschossen und auch auf
            # 5en getroffen"): the phase check above was the whole of rule
            # 07.02 here, so during PLAYER 1's Shooting phase this happily
            # said yes to a PLAYER 2 unit. reset_shooting_phase() runs on
            # every entry into a Shooting phase and clears both players'
            # bookkeeping, and a reactive Snap Shot (rule 15.08/15.09) is
            # deliberately never booked into shot_squad_ids/
            # fired_weapon_types at all - so nothing else stood in the way
            # either, and the AI's own shoot loop (ai/agent_driver.py's
            # _handle_shooting()) called start_shooting() on the very unit
            # that had just Overwatched, replacing SNAP_SHOOTING with a
            # normal activation: hits on 5+ instead of rule 15.09's
            # unmodified 6, and the same weapon group handed back to be
            # fired again. turn_owner, not active_player - the latter is a
            # transient "whose decision is this right now" flag that a
            # defender's save roll flips mid-activation (see game/turn.py).
            if self.turn_tracker.turn_owner != squad.owner:
                return False
        # Rule 16.01: "If a unit starts an action, until the end of the turn
        # it is not eligible to shoot (excluding TITANIC units)." Asked of the
        # ActionController rather than tracked here, so there is one record of
        # who is performing what - see game/actions.py.
        if self.action_controller is not None and self.action_controller.blocks_shooting(squad):
            return False
        if not available_shooting_types(squad, self.all_tokens, self.movement_controller):
            return False
        already_fired = self.fired_weapon_types.get(squad, set())
        return any(key not in already_fired for key in _attack_groups(squad, one_shot_used=self.one_shot_used))

    def reset_shooting_phase(self):
        """Rule 07.02/07.03: a new Shooting phase comes around every battle
        round, so squads that already shot in a previous one must be able to
        shoot again. Called once when the active player's turn reaches the
        Shooting phase."""
        self.shot_squad_ids = set()
        self.fired_weapon_types = {}

    def toggle_split_fire(self):
        if self.shooting_type == SNAP_SHOOTING:
            return  # rule 15.09: "you can only target one visible enemy unit" - no split fire during Snap Shooting
        self.split_fire = not self.split_fire

    def start_shooting(self, squad, on_finished=None):
        """`on_finished`, called once this activation ends (see
        _actually_finish_squad()/cancel()), is optional - most callers
        (a plain "Shoot" button click) don't need it. Rule 24.14 (Firing
        Deck) does: game/firing_deck.py's FiringDeckController borrows
        embarked passengers' weapons onto a TRANSPORT for the duration of
        exactly one activation and needs to know when to take them back."""
        if not self.can_shoot(squad):
            return
        # Never start a normal activation on top of a reactive one still in
        # flight (rule 15.08/15.09's Snap Shooting - start_snap_shooting()).
        # Same user report as can_shoot()'s owner check above: every field
        # reset below - shooting_type included - silently replaced the live
        # Snap Shot with a Normal one, which is how an unmodified-6 Overwatch
        # turned into a 5+ hit roll on the same weapon. can_shoot() alone now
        # makes the reported route impossible, but this is the invariant that
        # was actually violated, and it holds against any other caller.
        # Deliberately narrow: the AI advances a NORMAL activation to its
        # next weapon group by calling this again mid-activation (see
        # ai/agent_driver.py's _handle_shooting()), so refusing every
        # in-progress activation here would strand it in CHOOSING_WEAPON.
        if self._reactive and self.active_squad is not None:
            return
        self.active_squad = squad
        self.target_squad = None
        self._weapon_side_lock = {}
        self._reset_target_snapshots()
        self._hazardous_count = 0
        self._lethal_hits_auto_wounds = 0
        self._hit_target_squads_this_activation = set()
        self._living_when_first_hit = {}
        self._targeted_squads_this_activation = set()
        self._hit_weapon_names_this_activation = {}
        self._fired_this_activation = False
        # An activation started HERE is by definition the unit's own, not a
        # reactive one - leaving a stale True behind (start_snap_shooting()
        # sets it, only _actually_finish_squad()/cancel() clear it) is what
        # made the reported failure unbounded rather than a one-off: with it
        # still set, nothing was ever booked into shot_squad_ids/
        # fired_weapon_types, so can_shoot() kept saying yes and the same
        # weapon group kept coming back.
        self._reactive = False
        self._restrict_targets_to = None   # see start_reactive_shooting()
        self._on_activation_finished = on_finished
        # Riptide Battlesuit's Nova Charge: "when this unit is SELECTED to
        # shoot" - i.e. right here, before a target is chosen and long
        # before any die is rolled. Only on this path, never on
        # start_snap_shooting(): a Snap Shot happens in the opponent's
        # Movement phase, and the ability names your own Shooting phase.
        # No need to wait on the answer - the decision is modal in main.py's
        # event chain, and nothing reads the grant until dice are rolled.
        if self.nova_charge is not None:
            self.nova_charge.maybe_offer(squad)
        # Warlock Conclave's Psychic Communion is computed HERE - "each time
        # this unit is selected to shoot ... until the end of the phase" - and
        # held per model for the rest of it (see game/psychic_communion.py).
        psychic_communion.on_selected_to_shoot(squad, self.all_tokens)
        if self.hand_of_asuryan is not None:
            self.hand_of_asuryan.maybe_offer(squad)
        if self.ammo_runt is not None:
            self.ammo_runt.offer(squad)
        # The Vespid Strain Leader's Oversight Drone - "when the bearer's
        # unit is SELECTED TO SHOOT", which is this instant. Offered here
        # only, never mid-sequence, exactly like Nova Charge above.
        if self.oversight_drone is not None:
            self.oversight_drone.offer(squad)
        # The gunships' Targeting Array is "each time this model is SELECTED
        # TO SHOOT" - so this instant opens its one use for the activation.
        # No offer here: it is a panel button on the roll, not a decision now.
        if self.targeting_array is not None:
            self.targeting_array.begin_activation(squad)
        # Path of the Outcast's Far-Reaching Doom: "when a friendly
        # RANGERS/SHROUD RUNNERS unit is SELECTED TO SHOOT". Same pair of
        # seams as the targeting array above, because it is the same printed
        # window - opened here, closed in _actually_finish_squad(). Module
        # state rather than a controller: game/detection_range.py's fold reads
        # it from inside a pure function.
        far_reaching_doom.begin_shooting(squad)
        # Aspect Host's Path of the Warrior: "each time an ASPECT WARRIORS
        # or AVATAR OF KHAINE unit is SELECTED TO SHOOT or fight, select one
        # of the following". A real choice between two exclusive options,
        # so a real prompt - unlike Herald of Ynnead, whose single option
        # was pure gain. The fight step offers the same thing at its own
        # activation, and the ledger keys on the phase so the two are
        # independent.
        if self.path_of_the_warrior is not None:
            self.path_of_the_warrior.offer(squad)
        if self.prototype_weapon_system is not None:
            self.prototype_weapon_system.begin_activation(squad)
        if self.unmasking_suite is not None:
            self.unmasking_suite.begin_activation(squad)
        self.available_types = available_shooting_types(squad, self.all_tokens, self.movement_controller)
        if len(self.available_types) == 1:
            self.shooting_type = self.available_types[0]
            self._enter_target_selection()
        else:
            self.shooting_type = None
            self.state = CHOOSING_SHOOTING_TYPE

    def choose_shooting_type(self, shooting_type):
        """Rule 10.02 step 2: pick one shooting type this unit is eligible
        to make; only reached when more than one is available (a real
        choice) - start_shooting() auto-picks the sole option otherwise."""
        if self.state != CHOOSING_SHOOTING_TYPE or shooting_type not in self.available_types:
            return
        self.shooting_type = shooting_type
        self._enter_target_selection()

    def start_reactive_shooting(self, squad, restrict_to=None, on_finished=None):
        """A full, NORMAL shooting activation granted outside this unit's own
        Shooting phase - Awakened Dynasty's Protocol of the Vengeful Stars
        ("your unit can shoot as if it were your Shooting phase").

        NOT start_snap_shooting(): that one is rule 15.09's deliberately weaker
        Snap Shooting mode, and this Stratagem grants the ordinary thing. What
        the two share is being reactive, so `_reactive` is set for the same
        reason - the activation must not consume the unit's real Shooting-phase
        turn later in the round.

        `restrict_to` is the printed "must target only that enemy unit"; it is
        enforced in _is_valid_target_squad(), the one place that decides what
        may be shot at, so no separate filtering can drift from it."""
        if squad is None or not _attack_groups(squad):
            return
        self.active_squad = squad
        self.target_squad = None
        self.split_fire = False
        self._weapon_side_lock = {}
        self._reset_target_snapshots()
        self._hazardous_count = 0
        self._lethal_hits_auto_wounds = 0
        self._hit_target_squads_this_activation = set()
        self._living_when_first_hit = {}
        self._targeted_squads_this_activation = set()
        self._hit_weapon_names_this_activation = {}
        self._fired_this_activation = False
        self._reactive = True
        self._restrict_targets_to = list(restrict_to) if restrict_to else None
        self._on_activation_finished = on_finished
        self.available_types = available_shooting_types(squad, self.all_tokens, self.movement_controller)
        self.shooting_type = self.available_types[0] if self.available_types else None
        if self.shooting_type is None:
            self._restrict_targets_to = None
            return
        self._enter_target_selection()

    def start_snap_shooting(self, squad, on_finished=None):
        """Rule 15.08/15.09 (Fire Overwatch / Snap Shooting): a reactive
        shooting activation triggered by a stratagem (game/overwatch.py's
        FireOverwatchController) outside the unit's own Shooting phase -
        eligibility (friendly, unengaged, not TITANIC) is entirely that
        controller's call, not can_shoot()'s, which gates on "already shot
        this Shooting phase" and the unit's own engaged/advanced status -
        neither applies to an out-of-sequence reactive shot. Skips
        CHOOSING_SHOOTING_TYPE (Snap Shooting is the only option here) and
        forces split_fire off ("you can only target one visible enemy
        unit"). `_reactive` keeps this activation OUT of shot_squad_ids/
        fired_weapon_types (see _actually_finish_squad()/_finish_group()) -
        Overwatching doesn't use up the unit's real Shooting-phase
        activation later this round. `on_finished`, called once this
        activation actually ends (completed OR cancelled, see
        _actually_finish_squad()/cancel()), is how the caller finds out -
        active_squad here belongs to the OPPONENT of whoever's phase this
        actually still nominally is, unlike every other shooting
        activation, so the caller needs to know when it's safe to restore
        turn_tracker.active_player."""
        if squad is None or not _attack_groups(squad):
            return
        self.active_squad = squad
        self.target_squad = None
        self.split_fire = False
        self._weapon_side_lock = {}
        self._reset_target_snapshots()
        self._hazardous_count = 0
        self._lethal_hits_auto_wounds = 0
        self._hit_target_squads_this_activation = set()
        self._living_when_first_hit = {}
        self._targeted_squads_this_activation = set()
        self._hit_weapon_names_this_activation = {}
        self._fired_this_activation = False
        self.shooting_type = SNAP_SHOOTING
        self._reactive = True
        self._on_activation_finished = on_finished
        self._enter_target_selection()

    def _enter_target_selection(self):
        already_fired = self.fired_weapon_types.get(self.active_squad, set())
        self.remaining_weapon_types = [
            key for key in _attack_groups(self.active_squad, self.shooting_type, self._weapon_side_lock, self.one_shot_used)
            if key not in already_fired
        ]
        self.state = CHOOSING_TARGET

    def begin_assignment(self):
        """Split-fire only: leave target-picking behind and start assigning
        every model+weapon its own target individually."""
        if self.state != CHOOSING_TARGET or not self.split_fire or self.active_squad is None:
            return
        groups = _attack_groups(self.active_squad, self.shooting_type, self._weapon_side_lock, self.one_shot_used)
        self.assignment_queue = [pair for plist in groups.values() for pair in plist]
        self.assignments = {}
        self.assignment_overcharge = False
        self.state = ASSIGNING
        # Drops weapons that have no legal target before the player is ever
        # asked about them, and ends the activation outright if that leaves
        # nothing to assign - see _advance_assignment().
        self._advance_assignment()

    def cancel(self):
        # Rule 13.09 (Hidden): if this activation already resolved a weapon
        # group, the unit shot - abandoning the rest of the activation does not
        # undo that. See _note_ranged_attack() for the user report behind this.
        if self._fired_this_activation:
            self._note_ranged_attack()
        self.active_squad = None
        self.state = IDLE
        self.shooting_type = None
        self.available_types = []
        self.target_squad = None
        self.remaining_weapon_types = []
        self.assignment_queue = []
        self.assignments = {}
        self.assignment_overcharge = False
        self.resolved_groups = []
        self.current_group = None
        self.pending_step = None
        self.damage_session = None
        self.devastating_wound_session = None
        self._devastating_crits = 0
        self._pending_crit_ap_crits = 0
        self._hazardous_count = 0
        self._lethal_hits_auto_wounds = 0
        self._pending_attacks_roll = None
        self._pending_ones_reroll = None
        self._pending_twin_linked_reroll = None
        self._pending_hit_reroll = None
        self._pending_strength_roll = None
        self._pending_strength = None
        self._pending_sustained_roll = None
        self._pending_sustained = None
        self._rolled_strength = None
        self.mortal_wound_session = None
        self._weapon_side_lock = {}
        self._reset_target_snapshots()
        self._pending_subgroups = []
        self._pending_subgroups_target_squad = None
        self._pending_subgroups_base_label = None
        self._pending_subgroups_hazardous = 0
        self._finish_activation()

    def _finish_activation(self):
        """Fires the completion callback set by start_shooting()/
        start_snap_shooting()'s on_finished (if any), whether this
        activation actually resolved or was cancelled early, then clears
        the reactive flag. A safe no-op when nothing set a callback - the
        common case for a plain "Shoot" button click. Reactive callers
        (game/overwatch.py's FireOverwatchController) use this to know when
        it's safe to restore turn_tracker.active_player; non-reactive ones
        (game/firing_deck.py's FiringDeckController) use it to know when to
        take borrowed weapons back off the TRANSPORT."""
        self._reactive = False
        self._restrict_targets_to = None   # see start_reactive_shooting()
        callback = self._on_activation_finished
        self._on_activation_finished = None
        if callback is not None:
            callback()

    @property
    def pending_damage_choice(self):
        """Board-highlight helper: candidate models the (defending, or -
        rule 24.15's [HAZARDOUS] - attacking) player must pick from to
        receive the current failed save's wound, Devastating Wounds mortal
        wound, or Hazardous mortal wound, or None."""
        if self.damage_session is not None:
            return self.damage_session.pending_choice
        if self.devastating_wound_session is not None:
            return self.devastating_wound_session.pending_choice
        if self.mortal_wound_session is not None:
            return self.mortal_wound_session.pending_choice
        return None

    def active_attack_pair(self):
        """Board-highlight helper: (attacker_squad, target_squad) for the
        'attack arrow' overlay, or None when there's no single well-defined
        target right now (still choosing a target, or mid split-fire
        assignment where several targets may be involved over time)."""
        if self.current_group is not None:
            return self.active_squad, self.current_group["target_squad"]
        if self.state == CHOOSING_WEAPON and self.target_squad is not None:
            return self.active_squad, self.target_squad
        return None

    def _is_valid_target_squad(self, target_squad, all_tokens, attacking_squad=_UNSET, shooting_type=_UNSET):
        """Rule 10.06: under Close-Quarters shooting, an INFANTRY shooter can
        only target enemy units its own unit is engaged with, while a
        MONSTER/VEHICLE unit may also shoot out of the melee at another enemy
        unit (one that is not itself engaged - see the branch below). Every
        other shooting type excludes engaged enemy units entirely (rule 03.04
        already blocked those from normal shooting). Rule 13.09: a unit that's entirely
        Hidden and outside every one of the shooter's models' detection
        range can't be targeted at all. Rule 24.24 (LONE OPERATIVE): a unit
        with this ability "is not visible to enemy models unless they are
        within X\"" - a separate, always-on (not terrain-dependent)
        visibility restriction on top of Hidden.

        Real bug, found via user report (the AI shot one of its own units):
        this used to only reject target_squad is self.active_squad (the
        exact same squad object) - any OTHER friendly squad slipped through
        undetected, since Squad.is_engaged()/is_engaged_with() (checked
        below) already skip same-owner squads by design (rule 03.04:
        engagement is an enemy-only concept), so a friendly squad is almost
        never "engaged" here and sailed past that check too. Every other
        target-enumeration site in this codebase (fight.py's
        engaged_enemy_squads(), explosives.py, crushing_impact.py, charge.py,
        greater_good.py) already filters by owner - this was the one
        outlier.

        `attacking_squad`/`shooting_type` default to self.active_squad/
        self.shooting_type (every normal call site, mid-activation) but can
        be overridden - see has_valid_target(), which probes a squad that
        ISN'T (yet) self.active_squad, for a stratagem deciding whether to
        even offer it a reactive activation in the first place."""
        if attacking_squad is _UNSET:
            attacking_squad = self.active_squad
        if shooting_type is _UNSET:
            shooting_type = self.shooting_type
        if target_squad is None or target_squad is attacking_squad:
            return False
        # A granted activation may carry a target restriction (Vengeful Stars).
        # Checked early because it is absolute: no later clause can restore a
        # target the grant excluded.
        if self._restrict_targets_to is not None and target_squad not in self._restrict_targets_to:
            return False
        # Mont'ka's Focused Fire: "it can only target that enemy unit".
        # Checked beside the grant restriction above and for the same
        # reason - it is absolute, and no later clause restores a target it
        # excluded. The "(and only if it is an eligible target)" clause is
        # the rest of this method, which still runs.
        if not montka_focused_fire.target_allowed(attacking_squad, target_squad):
            return False
        if target_squad.owner == attacking_squad.owner:
            return False
        if shooting_type == CLOSE_QUARTERS_SHOOTING:
            if not attacking_squad.is_engaged_with(target_squad):
                # Rule 10.06's MONSTER/VEHICLE clause: such a unit is NOT
                # confined to the unit it is locked with - it can shoot out of
                # the melee at a different enemy unit. Reported from a real
                # game ("monster und fahrzeuge koennen aus dem nahkampf
                # rausschiessen auf eine andere einheit"): an engaged C'tan
                # Shard of the Void Dragon could only ever be pointed back at
                # the unit it had charged.
                #
                # Everything else about that other unit is unchanged, which is
                # why this repeats the `elif` below rather than skipping it:
                # rule 03.04 keeps a unit that is itself locked in someone
                # else's melee off the target list, for this shooting type
                # exactly as for every other one.
                #
                # Deliberately NOT widened to a non-MONSTER/VEHICLE unit
                # shooting its [CLOSE-QUARTERS]/[PISTOL] weapons while engaged:
                # the report names monsters and vehicles, and those two are
                # also the only units _weapon_eligible_for_type() lets fire a
                # non-[CLOSE-QUARTERS] weapon here at all. Infantry keeps
                # today's behaviour - it shoots the unit it is locked with.
                if not is_monster_or_vehicle_unit(attacking_squad):
                    return False
                if target_squad.is_engaged(all_tokens):
                    return False
        elif target_squad.is_engaged(all_tokens):
            return False
        # Rule 15.09 (Snap Shooting): "one visible enemy unit within 24\" of
        # your unit" - a unit-level cap independent of any individual
        # weapon's own range (still checked separately by _model_can_reach).
        if shooting_type == SNAP_SHOOTING and not any(
            edge_distance(shooter, defender) <= SNAP_SHOT_RANGE_IN
            for shooter in attacking_squad.models
            for defender in target_squad.models
        ):
            return False
        # Aeldari Battle Focus, Flitting Shadows: "until the end of the turn,
        # enemy units cannot use the Fire Overwatch Stratagem to shoot at that
        # unit". It says Fire Overwatch (15.08), so it is gated on the Snap
        # Shooting type that stratagem uses (15.09) and leaves ordinary
        # shooting alone. Here rather than in game/overwatch.py because this
        # protects the TARGET, and overwatch's own offer() only ever knows
        # which PLAYER just moved - it picks the firing unit and lets normal
        # targeting choose what to shoot. has_valid_target() runs through this
        # same predicate, so a would-be Overwatcher with nothing else in range
        # also stops being eligible, and an offer with no eligible unit
        # already no-ops - the whole chain follows from this one check.
        if shooting_type == SNAP_SHOOTING and battle_focus.blocks_fire_overwatch(target_squad):
            return False
        # LONE OPERATIVE (24.24) and Seer Council's Psychic Shield are the same
        # restriction from two sources - see status_effects.targeting_range_limit().
        # Measured LIVE, not from the rule-10.02 snapshot, which is what lets a
        # reactive Psychic Shield invalidate a selection that already happened.
        lone_range = status_effects.targeting_range_limit(target_squad)
        if lone_range is not None and not any(
            edge_distance(shooter, defender) <= lone_range
            for shooter in attacking_squad.models
            for defender in target_squad.models
        ):
            return False
        return bool(self._detectable_models(target_squad, attacking_squad))

    def _detectable_models(self, target_squad, attacking_squad):
        """Rule 13.09, per DEFENDER: which of `target_squad`'s models this
        attacking unit is allowed to see right now.

        The ONE definition, read by both halves of targeting - the unit-level
        gate above ("is there anything here I may see") and _model_can_reach()
        ("is one of those in range and in line of sight"). They used to ask it
        separately, the unit-level one with any() and the other not at all,
        which let a unit be TARGETED through models the shooter could not see
        and then SHOT through models it was not allowed to see. See
        _model_can_reach()'s own note for the reported board that showed it."""
        if target_squad is None or attacking_squad is None:
            return []
        return [
            model for model in target_squad.models
            if status_effects.is_detectable(
                model, attacking_squad, self.terrain_areas, self.turn_tracker,
                self.last_ranged_attack_turn,
                prey_marks=self.auxiliary_cadre, unmasking=self.unmasking_suite,
            )
        ]

    def has_valid_target(self, squad, shooting_type, all_tokens, target_filter=None):
        """Whether `squad` would have at least one legal target if it
        activated RIGHT NOW with `shooting_type` - a pure eligibility probe
        that never touches self.active_squad/self.state, so it's safe to
        call on a squad that isn't (and may never become) this controller's
        active one.

        `target_filter`, if given, narrows WHICH candidate squads count as
        an answer, without changing what "legal target" means - added for
        The Arro'kon Protocol (game/arrokon_protocol.py), which needs "could
        this unit legally shoot anything with 6+ models right now". Asking
        that here rather than re-deriving range/line of sight/Hidden/LONE
        OPERATIVE at the call site is the whole point of this method
        existing (see the report below).

        Real gap found via user report: Fire Overwatch's offer (rule 15.08,
        game/overwatch.py) used to only check "unengaged + has any ranged
        weapon at all" - completely ignoring Snap Shooting's own range cap
        (rule 15.09, SNAP_SHOT_RANGE_IN) and each weapon's individual range/
        line of sight, so a unit clear across the board with nothing even
        remotely in reach was offered the stratagem every single time. This
        reuses the exact same eligibility logic real targeting already
        enforces (_is_valid_target_squad + _model_can_reach), just against
        every candidate squad up front instead of one already-chosen target."""
        pairs = [p for plist in _attack_groups(squad, shooting_type, one_shot_used=self.one_shot_used).values() for p in plist]
        if not pairs:
            return False
        candidate_squads = {t.squad for t in all_tokens if t.squad is not None}
        if target_filter is not None:
            candidate_squads = {s for s in candidate_squads if target_filter(s)}
        return any(
            self._is_valid_target_squad(target_squad, all_tokens, attacking_squad=squad, shooting_type=shooting_type)
            and any(
                _model_can_reach(model, weapon, target_squad, self.obstacles,
                                 self._detectable_models(target_squad, squad),
                                 all_tokens, shooting_type, self.terrain_areas)
                for model, weapon in pairs
            )
            for target_squad in candidate_squads
        )

    def _reset_target_snapshots(self):
        self._reach_snapshot = {}
        self._cover_snapshot = {}
        self._closest_target_snapshot = {}  # target squad -> was it the closest eligible target when selected

    def _is_closest_eligible_target(self, target_squad):
        """Whether `target_squad` is the closest target this unit could
        legally have selected right now (The Twin Lance's Exemplars of
        Mont'ka).

        "Eligible" is settled with the same probe real targeting uses -
        has_valid_target() with a filter - rather than a hand-rolled second
        opinion about range/line of sight/Hidden/LONE OPERATIVE, for exactly
        the reason that method's own docstring records.

        Only computed for a unit that actually needs the answer: it is an
        eligibility sweep over every enemy unit, far too expensive to run
        for everyone else's activations. TWO abilities read it now - The
        Twin Lance's Exemplars of Mont'ka and Flash Gitz' Gun-crazy
        Show-offs - so the guard asks whether either applies. A third
        consumer belongs in this same condition; leaving it out does not
        fail loudly, it just silently returns False."""
        if self.active_squad is None:
            return False
        if not (
            exemplars_of_montka.unit_has_exemplars_of_montka(self.active_squad)
            or unit_has_gun_crazy_showoffs(self.active_squad)
        ):
            return False
        candidates = {
            t.squad for t in self.all_tokens
            if t.squad is not None and t.squad.owner != self.active_squad.owner
            and any(not m.is_dead() for m in t.squad.models)
        }
        eligible = [
            squad for squad in candidates
            if self.has_valid_target(
                self.active_squad, self.shooting_type, self.all_tokens,
                target_filter=lambda s, t=squad: s is t,
            )
        ]
        closest = exemplars_of_montka.closest_eligible_target(self.active_squad, eligible)
        return closest is target_squad

    def _offer_target_reactions(self, target_squad):
        """"Just after an enemy unit has selected its targets" - the WHEN of
        every reactive stratagem in self.target_reactions. Called from both
        places that constitute that step (choose_target_squad() and Split
        Fire's assign_current()), i.e. alongside _snapshot_target_state(),
        which freezes rule 10.02's state at exactly the same moment. Each
        controller decides for itself whether it wants to act at all - see
        game/stim_injectors.py and game/ard_as_nails.py."""
        if self.active_squad is None:
            return
        for reaction in self.target_reactions:
            reaction.maybe_offer(self.active_squad, target_squad, melee=False)

    def _snapshot_target_state(self, target_squad):
        """Rule 10.02: a unit's shooting activation selects its target(s)
        BEFORE a single attack is resolved, and every eligibility question
        about that target - is it in range, is it visible, does it have the
        Benefit of Cover (13.08) - is answered at THAT moment, for the whole
        activation. Freeze those answers here, when the target is locked in.

        Real bug, found via user report: the player fired one weapon group at
        an enemy squad, its two closest models were removed as casualties, and
        the survivors turned out to be behind terrain - so weapon_eligibility()
        (which re-ran _model_can_reach() from scratch for every REMAINING
        weapon group, against whatever models were still standing) reported
        0 eligible models for the rest of the unit's weapons, and the squad
        simply lost them. That is exactly backwards: removing casualties is a
        consequence of the attack sequence, and it cannot retroactively
        un-select a target the unit had already legally selected. The same
        went for cover - _dispatch_group()/_hit_modifiers() re-derived it per
        weapon group, so a target could gain (or lose) cover halfway through
        one unit's shooting purely because its front models had died.

        Snapshotting the whole _model_can_reach() predicate (not just its
        line-of-sight half) is deliberate: range is selected-at-the-same-time
        information, so a short-range weapon must not become ineligible
        either just because the models nearest it are gone.

        Every entry is keyed by the target squad as well as the shooter, so
        Split Fire - which assigns several different targets up front, in
        assign_current(), still before any dice - freezes each of them
        independently. Weapon instances are keyed by id() (the same reason
        one_shot_used does): choose_weapon(overcharge=True) builds fresh
        profile instances, and it filters eligibility on the ORIGINAL
        instances before swapping, so the snapshot is always consulted with
        the weapon that was actually snapshotted."""
        if self.active_squad is None or target_squad is None:
            return
        # The Twin Lance's Exemplars of Mont'ka: "targets the closest
        # eligible target" is target-SELECTION information, so it is frozen
        # here with everything else 10.02 settles - see
        # game/exemplars_of_montka.py for why, and for why it must not be
        # recomputed per weapon group.
        if target_squad not in self._closest_target_snapshot:
            self._closest_target_snapshot[target_squad] = self._is_closest_eligible_target(target_squad)
        for model in self.active_squad.models:
            key = (model, target_squad)
            if key not in self._cover_snapshot:
                self._cover_snapshot[key] = self._compute_benefit_of_cover(model, target_squad)
        # Unfiltered by the [CLOSE-QUARTERS] side lock (24.07) and [ONE SHOT]
        # (24.26) on purpose: those decide WHICH weapons may still be
        # selected later, which is a separate question from "could this
        # weapon reach this target at the moment the target was picked".
        for pairs in _attack_groups(self.active_squad, self.shooting_type).values():
            for model, weapon in pairs:
                key = (model, id(weapon), target_squad)
                if key not in self._reach_snapshot:
                    self._reach_snapshot[key] = _model_can_reach(
                        model, weapon, target_squad, self.obstacles,
                        self._detectable_models(target_squad, self.active_squad),
                        self.all_tokens, self.shooting_type, self.terrain_areas,
                    )

    def _can_reach(self, model, weapon, target_squad):
        """_model_can_reach() as it was answered when this target was
        selected (see _snapshot_target_state()). Falls back to a live
        computation for anything never snapshotted - e.g. eligibility probes
        for a squad that isn't the active one (has_valid_target()).

        Casualties among the target's SURVIVING models deliberately change
        nothing here - that is the whole point of the snapshot. A target wiped
        out ENTIRELY is a different matter: there is nothing left to shoot at,
        so the unit's remaining weapons can't be fired at it. Same treatment
        _begin_next_split_group() already gives an already-assigned group whose
        target died before it got to fire."""
        if not any(not m.is_dead() for m in target_squad.models):
            return False
        key = (model, id(weapon), target_squad)
        if key in self._reach_snapshot:
            return self._reach_snapshot[key]
        return _model_can_reach(
            model, weapon, target_squad, self.obstacles,
            self._detectable_models(target_squad, model.squad),
            self.all_tokens, self.shooting_type, self.terrain_areas,
        )

    def _squad_qualifies(self, squad, all_tokens, checker, cache):
        """Both branches of valid_target_models() below used to call
        _is_valid_target_squad()/_model_can_reach() once per TOKEN, even
        though both only ever depend on the token's SQUAD - for a 10-model
        squad that's the exact same (expensive, LOS-raycasting) result
        computed 10 times over. Real perf bug found via user report ("the
        game hangs in the Shooting phase"): with this scene's ~130-model
        two-T'au-army board and ~103 terrain obstacles, has_line_of_sight()
        alone can cost tens of milliseconds per call - multiplied by this
        10x-per-squad redundancy across every enemy squad, a single
        valid_target_models() call was observed taking 27+ seconds (Windows
        reports the window as "Not Responding" for the whole synchronous
        call, since nothing can process the event queue meanwhile - see
        CLAUDE.md). Memoizing per squad for the lifetime of one
        valid_target_models() call preserves the exact same result (neither
        check depends on which particular token of the squad triggered it)
        while cutting this cost by roughly the squad's model count."""
        cached = cache.get(squad)
        if cached is None:
            cached = cache[squad] = checker(squad)
        return cached

    def valid_target_models(self, all_tokens):
        """Board-highlight helper: enemy tokens belonging to squads that are
        currently valid to pick as a target (or the already-locked-in target)."""
        if self.active_squad is None:
            return set()  # defensive: state should never say CHOOSING_TARGET/ASSIGNING without an active squad
        if self.state == CHOOSING_TARGET and not self.split_fire:
            pairs = [
                p for plist in _attack_groups(self.active_squad, self.shooting_type, self._weapon_side_lock, self.one_shot_used).values()
                for p in plist
            ]
            cache = {}

            def check(squad):
                visible = self._detectable_models(squad, self.active_squad)
                return self._is_valid_target_squad(squad, all_tokens) and any(
                    _model_can_reach(model, weapon, squad, self.obstacles, visible,
                                     all_tokens, self.shooting_type, self.terrain_areas)
                    for model, weapon in pairs
                )

            return {
                token for token in all_tokens
                if token.squad is not None and self._squad_qualifies(token.squad, all_tokens, check, cache)
            }

        if self.state == ASSIGNING and self.assignment_queue:
            model, weapon = self.assignment_queue[0]
            cache = {}

            def check(squad):
                return self._is_valid_target_squad(squad, all_tokens) and _model_can_reach(
                    model, weapon, squad, self.obstacles,
                    self._detectable_models(squad, self.active_squad),
                    all_tokens, self.shooting_type, self.terrain_areas
                )

            return {
                token for token in all_tokens
                if token.squad is not None and self._squad_qualifies(token.squad, all_tokens, check, cache)
            }

        if self.state == CHOOSING_WEAPON and self.target_squad is not None:
            return set(self.target_squad.models)

        return set()

    def weapon_eligibility(self):
        """[(attack_key, label, eligible_count, total_count, overcharge_label), ...]
        against the chosen target. Eligibility comes from the snapshot taken
        when the target was selected (rule 10.02, see
        _snapshot_target_state()) - it deliberately does NOT re-measure range
        or line of sight per weapon group, or casualties from this unit's own
        earlier weapon groups could disqualify its later ones. Still cached
        (invalidated whenever the relevant state actually changes) since this
        is called every frame to render the weapon-choice screen.
        overcharge_label is None if this weapon has no
        alternate firing mode, otherwise the overcharge profile's own
        display name (e.g. "Cyclic Ion Raker - Overcharge") - present means
        choose_weapon(key, overcharge=True) is also offered for this entry;
        see WeaponProfile.overcharge_profile."""
        if self.active_squad is None or self.target_squad is None:
            return []
        cache_key = (
            self.active_squad, self.target_squad, self.shooting_type,
            tuple(self.remaining_weapon_types), len(self.all_tokens),
            frozenset(self._weapon_side_lock.items()),
        )
        if cache_key == self._weapon_eligibility_cache_key:
            return self._weapon_eligibility_cache_result

        groups = _attack_groups(self.active_squad, self.shooting_type, self._weapon_side_lock, self.one_shot_used)
        result = []
        for key in self.remaining_weapon_types:
            pairs = groups.get(key, [])
            eligible = sum(1 for m, w in pairs if self._can_reach(m, w, self.target_squad))
            overcharge_cls = pairs[0][1].overcharge_profile if pairs else None
            overcharge_label = overcharge_cls().name if overcharge_cls is not None else None
            result.append((key, _group_label(pairs), eligible, len(pairs), overcharge_label))

        self._weapon_eligibility_cache_key = cache_key
        self._weapon_eligibility_cache_result = result
        return result

    def choose_target_squad(self, target_squad):
        if self.state != CHOOSING_TARGET or self.split_fire:
            return
        if not self._is_valid_target_squad(target_squad, self.all_tokens):
            return
        self.target_squad = target_squad
        # Rule 10.02: this IS the "select targets" step - freeze range/line of
        # sight/cover for the rest of the activation, right here.
        self._snapshot_target_state(target_squad)
        self._offer_target_reactions(target_squad)
        self.state = CHOOSING_WEAPON

    def revalidate_target_selection(self):
        """Rule 10.02 selects targets before anything is resolved - and a
        reactive ability can make that selection ILLEGAL just after it happened.
        Seer Council's Psychic Shield is the first: it restricts what may be
        "selected as the target", and its WHEN is exactly this moment.

        So the activation goes back to the select-targets step rather than
        carrying on against a target it may no longer choose. Called by the
        ability, not polled: nothing else in the pipeline can invalidate a
        selection after the fact, so a per-frame check would be pure cost.

        Both selection shapes are handled. In Split Fire each assignment is its
        own selection, so only the ones whose target went illegal are undone and
        their (model, weapon) pairs go back on the queue - the rest stand. The
        rule-10.02 snapshot entries for an undone target are dropped too: they
        describe a selection that no longer exists."""
        if self.active_squad is None:
            return False
        if self.split_fire:
            undone = []
            for key in list(self.assignments):
                _, target = key
                if self._is_valid_target_squad(target, self.all_tokens):
                    continue
                for pair in self.assignments.pop(key):
                    undone.append(pair)
                self._forget_target_snapshots(target)
            if not undone:
                return False
            # Front of the queue, so the player answers for them first rather
            # than after every other still-unassigned weapon.
            self.assignment_queue[:0] = undone
            self._log(
                f"{self.active_squad.name}: {len(undone)} weapon assignment(s) undone - their "
                "target can no longer be selected."
            )
            return True
        target = self.target_squad
        if target is None or self._is_valid_target_squad(target, self.all_tokens):
            return False
        self._forget_target_snapshots(target)
        self.target_squad = None
        self.state = CHOOSING_TARGET
        self._log(
            f"{self.active_squad.name} must select a different target: {target.name} can no "
            "longer be chosen."
        )
        return True

    def _forget_target_snapshots(self, target_squad):
        """Drop the rule-10.02 freeze for one target. Keyed per target squad, so
        a Split Fire activation's other, still-valid selections keep theirs."""
        for store in (self._reach_snapshot, self._cover_snapshot):
            for key in [k for k in store if k[-1] is target_squad]:
                del store[key]

    def stop_shooting(self):
        """Rule 04.01 allows selecting 'one or more' ranged weapons, not all
        of them — this lets you deliberately leave remaining weapon types
        unfired instead of being forced to work through every one."""
        if self.state != CHOOSING_WEAPON or self.current_group is not None:
            return
        self._finish_squad()

    def choose_weapon(self, weapon_key, overcharge=False):
        """overcharge=True fires this weapon group in its alternate
        high-power mode instead (e.g. Ghostkeel's Cyclic Ion Raker
        Overcharge) - only meaningful when weapon_eligibility() reported
        overcharge_available for this key. Builds fresh per-model instances
        of the overcharge profile (never mutates/shares the original
        Standard-mode instances still sitting in each model's weapons list -
        same "never share weapon instances" invariant ModelLine's own
        docstring documents), so everything downstream (attack count,
        strength, AP, damage, [HAZARDOUS]) reads correctly off the swapped
        weapon with no other change to the resolution pipeline."""
        if self.state != CHOOSING_WEAPON or weapon_key not in self.remaining_weapon_types:
            return
        groups = _attack_groups(self.active_squad, self.shooting_type, self._weapon_side_lock, self.one_shot_used)
        pairs = [(m, w) for m, w in groups.get(weapon_key, []) if self._can_reach(m, w, self.target_squad)]
        if overcharge:
            pairs = [(m, _overcharge_instance(w)) for m, w in pairs if w.overcharge_profile is not None]
            if not pairs:
                return
        # _group_label() reads each pair's own weapon.name, so this already
        # says e.g. "Cyclic Ion Raker - Overcharge" once pairs holds the
        # swapped-in overcharge instances - no separate "(Overcharge)"
        # suffix needed.
        self._lock_weapon_sides(pairs)
        self._dispatch_group(weapon_key, _group_label(pairs), pairs, self.target_squad)

    def _lock_weapon_sides(self, pairs):
        """Rule 24.07: committing to fire these (model, weapon) pairs locks
        each non-MONSTER/VEHICLE model into that weapon's [CLOSE-QUARTERS]
        side for the rest of this shooting activation (no-op during
        Close-Quarters shooting itself, which isn't restricted)."""
        if self.shooting_type == CLOSE_QUARTERS_SHOOTING:
            return
        for model, weapon in pairs:
            if model.profile.monster or model.profile.vehicle:
                continue
            self._weapon_side_lock[model] = _weapon_side(weapon, self.active_squad)

    def current_assignment_overcharge_label(self):
        """The alternate firing mode's own display name (e.g. "Cyclic Ion
        Raker - Overcharge") for the weapon currently awaiting a target during
        Split Fire assignment, or None if that weapon has only one mode (or
        nothing is awaiting assignment). Present means
        toggle_assignment_overcharge()/assign_current(overcharge=True) are
        meaningful for it - the Split Fire counterpart of
        weapon_eligibility()'s own overcharge_label."""
        current = self.current_assignment()
        if current is None:
            return None
        overcharge_cls = current[1].overcharge_profile
        return overcharge_cls().name if overcharge_cls is not None else None

    def toggle_assignment_overcharge(self):
        """Arms/disarms the alternate firing mode for the NEXT Split Fire
        assignment (the target itself is clicked on the battlefield, so the
        mode can't be a second button next to the target the way it is in the
        non-split flow). Deliberately reset after every assignment (see
        assign_current()) rather than persisting: choosing Overcharge is
        usually choosing [HAZARDOUS], and silently carrying that over to the
        next model's weapon would risk wounds the player never asked for."""
        if self.state != ASSIGNING or self.current_assignment_overcharge_label() is None:
            return
        self.assignment_overcharge = not self.assignment_overcharge

    def assign_current(self, target_squad, overcharge=None):
        """`overcharge=True` fires this one model+weapon in its alternate
        high-power mode (see choose_weapon()'s own docstring); None means "use
        whatever toggle_assignment_overcharge() has armed".

        Real gap, reported by the user ("beim Split fire kann ich nicht
        zwischen waffenmodi wählen zb overcharge"): the mode was only ever
        offered in the non-split flow, because that one picks target first and
        weapon second, leaving a natural place for a second button. Split Fire
        inverts that - each weapon picks its own target - so the choice had no
        home and the weapon always fired in Standard mode.

        The swap happens HERE, not at resolution time, and that matters for
        more than convenience: the assignment is keyed by _attack_key(), which
        reads S/AP/D off the weapon. Keying by the SWAPPED profile is what
        keeps an overcharged model in its own group instead of being folded in
        with its standard-mode squadmates and silently resolved with their
        stats. It also makes the mode per MODEL here (finer than the non-split
        flow's per-group choice), which is the correct granularity: the
        [HAZARDOUS] risk it usually buys is per weapon fired."""
        if self.state != ASSIGNING or not self.assignment_queue or target_squad is None:
            return
        if not self._is_valid_target_squad(target_squad, self.all_tokens):
            return
        # Rule 10.02: Split Fire's assignment step is this activation's
        # "select targets" step, so snapshotting here (before the reach check
        # that gates the assignment itself) freezes exactly the state the
        # assignment was made under - see _snapshot_target_state().
        self._snapshot_target_state(target_squad)
        if overcharge is None:
            overcharge = self.assignment_overcharge
        model, weapon = self.assignment_queue.pop(0)
        fire_weapon = weapon
        if overcharge and weapon.overcharge_profile is not None:
            fire_weapon = _overcharge_instance(weapon)
        if not self._can_reach(model, fire_weapon, target_squad):
            self.assignment_queue.insert(0, (model, weapon))
            return
        self.assignment_overcharge = False

        key = (_attack_key(model, fire_weapon), target_squad)
        self.assignments.setdefault(key, []).append((model, fire_weapon))
        # Offered only once the assignment has actually landed (the reach check
        # above can bounce it), and de-duplicated per target inside the
        # controller, so a ten-model split-fire activation asks once per target
        # unit rather than once per weapon.
        self._offer_target_reactions(target_squad)
        self._lock_weapon_sides([(model, fire_weapon)])
        # Rule 24.07: that lock may now rule out other still-queued pairs for
        # the same model (its other ranged weapons, once it's committed to
        # [CLOSE-QUARTERS], or vice versa) - drop them instead of letting the
        # player assign a target for a weapon it can no longer fire.
        self.assignment_queue = [
            (m, w) for m, w in self.assignment_queue
            if not _side_locked_out(m, w, self.shooting_type, self._weapon_side_lock)
        ]

        self._advance_assignment()

    def skip_current(self):
        """Leave the model+weapon at the front of the assignment queue
        unfired and move on to the next one.

        Rule 04.01 allows selecting "one or more" ranged weapons, not all of
        them - the same basis stop_shooting() cites for the non-split flow.
        Split Fire had no equivalent at all: every queued weapon had to be
        given a target, and the only way out was Cancel, which throws the
        whole activation away.

        Real user report ("bei Split fire brauche ich noch die Option, mit
        einer Waffe nicht zu schiessen, denn hat eine Waffe kein Ziel, laufe
        ich derzeit beim Assignment in eine Sackgasse"): assign_current()
        bounces a pair back onto the front of the queue when the clicked
        target is out of reach, so a weapon with NO legal target at all froze
        the queue permanently - reproduced as a Pulse Pistol (12") in a unit
        activating at 20". _advance_assignment() now drops those on its own,
        so this button is the deliberate choice not to fire a weapon that
        COULD, rather than the escape hatch from that dead end."""
        if self.state != ASSIGNING or not self.assignment_queue:
            return
        model, weapon = self.assignment_queue.pop(0)
        self.assignment_overcharge = False
        self._log(f"{self.active_squad.name}: {model.profile.name} does not fire its {weapon.name}.")
        self._advance_assignment()

    def finish_assignment(self):
        """Stop assigning and resolve whatever has a target already - the
        split-fire counterpart of stop_shooting(), on the same rule 04.01
        basis. Without it, skipping the last fifteen pistols of a ten-model
        unit meant fifteen clicks, and there was no way at all to say "fire
        what I have assigned" short of Cancel (which fires nothing)."""
        if self.state != ASSIGNING:
            return
        skipped = len(self.assignment_queue)
        self.assignment_queue = []
        self.assignment_overcharge = False
        if skipped:
            self._log(f"{self.active_squad.name}: {skipped} weapon(s) left unfired.")
        self._advance_assignment()

    def _pair_has_any_target(self, model, weapon, valid_cache):
        """Whether this model+weapon could legally be assigned ANY target
        right now - exactly the question assign_current() answers for one
        clicked squad, asked against every candidate instead.

        Uses _can_reach() rather than _model_can_reach() so a target already
        selected earlier in this same activation keeps its rule-10.02 freeze
        (see _snapshot_target_state()); anything not yet selected has no
        snapshot and is computed live either way.

        Asked of the STANDARD-mode instance, which is exact as long as no
        alternate firing mode changes Range - verified: every
        overcharge_profile in game/weapons.py keeps its weapon's range. If one
        ever reaches further than its standard mode, this needs to ask about
        both, or it would drop a weapon that could still reach on Overcharge."""
        for squad in {t.squad for t in self.all_tokens if t.squad is not None}:
            ok = valid_cache.get(squad)
            if ok is None:
                ok = valid_cache[squad] = self._is_valid_target_squad(squad, self.all_tokens)
            if ok and self._can_reach(model, weapon, squad):
                return True
        return False

    def _prune_unassignable(self):
        """Drop pairs from the FRONT of the queue that have no legal target
        at all, so the player is never asked to pick a target that does not
        exist (the reported dead end - see skip_current()).

        Front-only, and that is deliberate on cost: the answer cannot change
        during the assignment step (nothing moves and no dice are rolled -
        the only thing that shrinks the queue meanwhile is rule 24.07's side
        lock, handled separately), so a pair sitting further back gets the
        same treatment when its turn comes. Measured on map2's real terrain a
        single "can this weapon reach anything" probe costs ~11 ms with
        line of sight involved, which is what valid_target_models() already
        spends on the head pair every frame anyway - sweeping the whole queue
        up front would pay that for pairs the player may never reach."""
        dropped = []
        valid_cache = {}
        while self.assignment_queue:
            model, weapon = self.assignment_queue[0]
            if self._pair_has_any_target(model, weapon, valid_cache):
                break
            self.assignment_queue.pop(0)
            dropped.append(weapon.name)
        if dropped and self.active_squad is not None:
            names = ", ".join(sorted(set(dropped)))
            self._log(
                f"{self.active_squad.name}: {len(dropped)} weapon(s) have no target in "
                f"range/line of sight and are not fired ({names})."
            )

    def _advance_assignment(self):
        """Shared tail of every split-fire assignment step (assign, skip,
        finish, and the initial begin_assignment): make sure the pair now at
        the front is one the player can actually answer for, and once nothing
        is left to assign, resolve what was assigned.

        With nothing assigned at all, _begin_next_split_group() finds no
        groups and ends the activation through _finish_squad() - the same
        "the unit's shot is used up whether or not every weapon fired"
        bookkeeping stop_shooting() goes through."""
        self._prune_unassignable()
        if self.assignment_queue:
            return

        self.resolved_groups = [
            {
                "weapon_key": key[0],
                "weapon_label": _group_label(pairs),
                "target_squad": key[1],
                "pairs": pairs,
            }
            for key, pairs in self.assignments.items()
        ]
        self._begin_next_split_group()

    def current_assignment(self):
        """(model, weapon) awaiting a target during split-fire assignment, or None."""
        return self.assignment_queue[0] if self.assignment_queue else None

    def _begin_next_split_group(self):
        """Real crash, found via user report (IndexError on target_squad.
        models[0], mid-Shooting-phase, right as the target squad was wiped
        out): Split Fire locks in EVERY model+weapon's target assignment up
        front, in assign_current(), before a single die is rolled - so it's
        entirely legal (and not even unusual) for two DIFFERENT queued
        groups in resolved_groups to share the same target_squad (e.g. two
        different weapon types on the unit both aimed at the same enemy
        squad). If the FIRST of those groups kills every model in that
        squad, main.py's state.remove_dead_models() strips it down to an
        empty Squad.models by the time this method gets around to starting
        the SECOND one - _begin_resolution() (and everything downstream of
        it, e.g. on_dice_acknowledged()'s target_squad.models[0]) assumed
        there was always at least one model left to read a representative
        profile/stats off of. Skip any further already-resolved group whose
        target has since been wiped out entirely, instead of starting a
        resolution against nothing - loop rather than recurse once, since
        more than one queued group could share that now-dead target."""
        while self.resolved_groups:
            group = self.resolved_groups[0]
            if any(not m.is_dead() for m in group["target_squad"].models):
                break
            self.resolved_groups.pop(0)
            self._log(f"{group['target_squad'].name} was destroyed before {group['weapon_label']} could fire - skipped.")
        if not self.resolved_groups:
            self._finish_squad()
            return
        group = self.resolved_groups.pop(0)
        self.state = CHOOSING_WEAPON
        self._dispatch_group(group["weapon_key"], group["weapon_label"], group["pairs"], group["target_squad"])

    def _cover_ignored_for_group(self, weapon, target_squad):
        """Whether Benefit of Cover (13.08) is bypassed entirely for this
        weapon+target combination - via the weapon's own [IGNORES COVER]
        (24.18), or a Guided-and-Markerlight-Spotted attack (T'au "For The
        Greater Good", user-supplied). Neither depends on which particular
        model within the group is doing the shooting, so when either
        applies there's nothing to split by in _dispatch_group() - every
        model would get the same "no cover" result regardless of its own
        line of sight."""
        guided_ignores_cover = (
            self.greater_good is not None
            and self.greater_good.is_guided_attack(self.active_squad, target_squad)
            and self.greater_good.marked_by_markerlight(target_squad)
        )
        # Kauyon's Coordinate to Engage grants [IGNORES COVER] as well, but
        # only "if your unit has the MARKERLIGHT keyword" - so the two halves
        # of that Stratagem are asked separately, and a unit without the
        # keyword gets the Ballistic Skill half alone.
        if kauyon_coordinate_to_engage.ignores_cover(
                self.greater_good, self.active_squad, target_squad):
            return True
        # Pathfinder Team's Target Uploaded: "that attack has the [IGNORES
        # COVER] ability" against the unit THIS unit Spotted. ORed, not
        # summed - see game/target_uploaded.py on why it and the Guided
        # branch above can never both be true for the same attack. Like the
        # other two, it doesn't depend on which model in the group shoots,
        # so it needs no cover-split either.
        # A UNIT-level "Ignores Cover" rule (The Twin Lance) bypasses cover
        # against every target regardless of the weapon's own keyword, and
        # Exemplars of Mont'ka bypasses it against the closest eligible one.
        # All ORed - each is independently sufficient.
        unit_ignores = any(
            m.profile.ignores_cover for m in self.active_squad.models if not m.is_dead()
        ) if self.active_squad is not None else False
        montka_ignores = (
            exemplars_of_montka.unit_has_exemplars_of_montka(self.active_squad)
            and self._closest_target_snapshot.get(target_squad, False)
        )
        return (
            weapon.ignores_cover or guided_ignores_cover or unit_ignores or montka_ignores
            or target_uploaded.applies(self.greater_good, self.active_squad, target_squad)
            # Seer Council's Fate Inescapable: "ranged weapons equipped by
            # models in your unit have the [IGNORES COVER] ability" - a
            # unit-level, phase-scoped grant, so it sits here with the other
            # unit-level terms rather than on a copied weapon.
            or fate_inescapable.applies(self.active_squad)
            # Shroud Runners' Target Acquisition, and the only term here that
            # is a mark on the TARGET rather than a grant on the shooter:
            # "that enemy unit cannot have the Benefit of Cover" holds against
            # attacks from anyone for the rest of the phase.
            or (self.target_acquisition is not None
                and self.target_acquisition.is_marked(target_squad))
        )

    def _dispatch_group(self, weapon_key, weapon_label, pairs, target_squad):
        """Rule 13.08 (Benefit of Cover) is evaluated per ATTACKING model
        against the target unit - _has_benefit_of_cover() takes a single
        shooter_model, since intervening terrain can block one model's line
        of sight to the target without blocking another's. Rule 04.03
        still groups attacks purely by BS/S/AP/D (see _attack_key()), so
        it's entirely possible for a group to contain models that disagree
        on whether the target has cover against THEM specifically - real
        user report: half a squad hidden behind terrain, half not, all
        firing the same weapon. Such a group can no longer share one hit
        roll/threshold: split it into up to two cover-homogeneous
        sub-groups here and resolve them as two entirely separate
        hit/wound/save/damage sequences, one after the other (continued by
        _finish_group()'s _pending_subgroups check). The common case (the
        whole group agrees on cover, or cover is ignored entirely for this
        weapon/attack - see _cover_ignored_for_group()) is unaffected: a
        single group, unchanged label, exactly as before this existed."""
        self._pending_subgroups = []
        self._pending_subgroups_target_squad = target_squad
        self._pending_subgroups_base_label = weapon_label
        # Rule 24.15 ([HAZARDOUS]): "roll one D6 for each [HAZARDOUS] weapon
        # that was used to make one or more of those attacks" - so this is a
        # COUNT of weapons, not a flag for the group. `pairs` holds one entry
        # per (model, weapon) and is already filtered by _can_reach(), so its
        # length is exactly "the weapons that were used". A three-model
        # Sunforge team with two Fusion Blasters each, plus an attached
        # Commander with four, owes TEN rolls - it used to owe one per attack
        # GROUP, which is two. Reported: "Hazardous bei den sunforge viel zu
        # wenig ... fuer jede waffe, die abgefeuert wurde muss gewuerfelt
        # werden".
        #
        # Asked of the ADJUSTED weapon, not the printed one: every other
        # keyword this step reads comes off _adjusted_weapon()'s copy (see
        # _crit_note()'s call at the hit step), and reading pairs[0][1] here
        # meant a GRANTED [HAZARDOUS] - the third clause of Experimental
        # Ammunition's richer mode - never counted at all.
        self._pending_subgroups_hazardous = (
            len(pairs) if pairs and self._adjusted_weapon(pairs, target_squad).hazardous
            else 0)

        if not pairs or not target_squad.models or self.shooting_type == SNAP_SHOOTING:
            # Rule 15.09 (Snap Shooting) ignores every hit modifier,
            # cover included - never worth splitting for it.
            self._begin_resolution(weapon_key, weapon_label, pairs, target_squad)
            return

        weapon = pairs[0][1]
        if self._cover_ignored_for_group(weapon, target_squad):
            self._begin_resolution(weapon_key, weapon_label, pairs, target_squad)
            return

        with_cover, without_cover = [], []
        for pair in pairs:
            (with_cover if self._has_benefit_of_cover(pair[0], target_squad) else without_cover).append(pair)

        if not with_cover or not without_cover:
            self._begin_resolution(weapon_key, weapon_label, pairs, target_squad)
            return

        self._log(
            f"{weapon_label}: {len(with_cover)} model(s) have Benefit of Cover against "
            f"{target_squad.name} and {len(without_cover)} don't (rule 13.08, differing line of "
            f"sight) - resolved as two separate attack sequences."
        )
        self._pending_subgroups = [(without_cover, "models without cover")]
        self._begin_resolution(weapon_key, f"{weapon_label} (models with cover)", with_cover, target_squad)

    def _begin_resolution(self, weapon_key, weapon_label, pairs, target_squad):
        self.current_group = {
            "weapon_key": weapon_key,
            "weapon_label": weapon_label,
            "pairs": pairs,
            "target_squad": target_squad,
        }
        self._twin_linked_used = False  # rule 24.38: fresh chance to re-roll for each new weapon group's attacks
        self._hit_reroll_used = False  # Monster Hunters: likewise a fresh chance per weapon group - see _hit_reroll_choice_needed()
        self._rolled_strength = None  # a dice-notation Strength is rolled once per weapon group - see _effective_strength()
        if target_squad is not None:
            self._targeted_squads_this_activation.add(target_squad)
        # Sonic Destruction's ledger, the 'also targeted that enemy unit this
        # phase' half. Noted HERE, the same seam Spore-laced Shock Waves uses,
        # because this is where target and weapon are first both known - and
        # noted for EVERY firing platform, not just the ones that benefit,
        # since the first shooter is what the second one counts.
        if self.sonic_destruction is not None:
            for _model, _weapon in (pairs or ()):
                self.sonic_destruction.note_attack(
                    _model, _weapon, target_squad, reactive=self._reactive)

        if not pairs or not target_squad.models:
            self._finish_group()
            return

        shooter_model = pairs[0][0]
        if self.turn_tracker is not None:
            self.turn_tracker.set_active(shooter_model.squad.owner)

        # The Plagueburst Crawler's Spore-laced Shock Waves: "each time you
        # SELECT A TARGET for this model's Plagueburst mortar". This engine
        # picks the target first and the weapon second, so the printed instant
        # is the moment the MORTAR's group begins resolving against that
        # target - the first point at which both halves of the clause are
        # known. The D6s are rolled here, before any attack, which is what
        # freezes the set of units at risk (see the module's own docstring).
        if self.spore_laced is not None:
            self.spore_laced.notify_target_selected(self.active_squad, pairs[0][1], target_squad)

        weapon = pairs[0][1]
        # Psychic Communion (Warlock Conclave) adds to the ATTACKS
        # characteristic as well as to Strength, and Attacks is read HERE -
        # before anything else in the sequence. The late adjuster chain in
        # on_dice_acknowledged()/the [TORRENT] shortcut runs long after this
        # roll has already been thrown, so its Attacks half was simply never
        # read: a 2-Warlock Conclave rolled a plain D6 each while its Strength
        # half worked, which is exactly the reported symptom ("schau mal ob
        # die anzahl des destruktors richtig berechnet wurde"). Same place,
        # and the same reason, as Gun-crazy Show-offs further down - an
        # adjuster that touches Attacks has to land at the count site, not
        # with the ones that touch Strength/AP/keywords.
        #
        # Only used for the count (and the label the player reads); the raw
        # weapon is what is handed on, so the late chain still starts from
        # pairs and cannot double-apply. Reading it off the representative
        # model is exact because the bonus is part of _attack_key() - see
        # that function.
        attacks_weapon = psychic_communion.psychic_communion_adjusted_weapon(weapon, pairs)
        if weapon.attacks_notation is not None:
            # Rule: this weapon's printed Attacks characteristic is itself a
            # die roll (e.g. a T'au Flamer's "D6") - real 40k timing rolls
            # it separately for EACH attacking model, so `count=len(pairs)`,
            # summed once acknowledged. Has to happen BEFORE the Hit roll
            # can even start (that roll's own `count` is the resulting
            # total) - a real, visible dice_manager step
            # (game/dice_notation.py's DiceNotationRoll) exactly like the
            # Damage roll this mirrors (see WeaponProfile.damage_notation),
            # not the earlier "store the die's max value as a fixed
            # placeholder, never actually roll it" simplification.
            self._pending_attacks_roll = DiceNotationRoll(
                attacks_weapon.attacks_notation, count=len(pairs), dice_manager=self.dice_manager,
                label=f"Attacks: {weapon_label} ({len(pairs)} model(s), {describe_dice_notation(attacks_weapon.attacks_notation)} each)",
                roll_kind=ATTACKS_ROLL, log=self._log,
                target_name=target_squad.name,
                attacker_squad=self.active_squad, target_squad=target_squad,
            )
            if self._pending_attacks_roll.is_pending:
                self.pending_step = "attacks"
                return
            total = self._pending_attacks_roll.total
            self._pending_attacks_roll = None
            total_attacks = total + extra_attack_dice(weapon, target_squad, weapon_key, self.split_fire, self.assignments, pairs)
            total_attacks += volley_fire_extra_attacks(pairs)
            self._continue_resolution_with_attacks(weapon, total_attacks)
            return

        # Flash Gitz' Gun-crazy Show-offs (user-supplied): a Snazzgun aimed
        # at the closest eligible target has an Attacks characteristic of 4.
        # It has to land HERE, before the count is summed - unlike every
        # other adjuster in this file, which touches Strength/AP/keywords
        # that are read later in the sequence. Per model, since the check is
        # on each shooter's own profile. "Closest" comes from rule 10.02's
        # target-selection snapshot, never recomputed - see
        # game/gun_crazy_showoffs.py.
        is_closest = self._closest_target_snapshot.get(target_squad, False)
        total_attacks = sum(
            gun_crazy_adjusted_weapon(w, [(m, w)], is_closest).attacks for m, w in pairs
        )
        total_attacks += extra_attack_dice(weapon, target_squad, weapon_key, self.split_fire, self.assignments, pairs)
        # Cadre Fireblade's "Volley Fire" (user-supplied): +1 A to every ranged
        # weapon in the unit he is leading. Added here rather than folded into
        # extra_attack_dice() for the same reason fight.py adds Waaagh!'s own
        # +1 A separately - that function is the WEAPON's own abilities
        # (24.05/24.06/24.30), this is a unit ability granted by another model.
        total_attacks += volley_fire_extra_attacks(pairs)
        self._continue_resolution_with_attacks(weapon, total_attacks)

    def _after_attacks_reroll(self, weapon, group, total, again):
        """Resumes the Attacks step once Breath of Vaul's offer is answered.

        The melee-free twin of DamageAllocationSession._after_damage_reroll(),
        and it works the same way: `again` means throw the dice once more as a
        brand new, VISIBLE dice_manager roll marked is_reroll=True - not a
        silent recomputation - so it lands back in _pending_attacks_roll and
        comes through the "attacks" branch again once acknowledged. It cannot
        loop, because is_reroll marks every index of the roll as spent and the
        offer's can_offer() then declines.

        NAMED SIMPLIFICATION: the printed text is "each time you roll", i.e.
        per flamer, and this engine rolls all of a group's Attacks dice in ONE
        DiceNotationRoll (count=len(pairs)). So two flamers get one offer that
        re-rolls both dice rather than two separate offers. That follows from
        the existing group roll, not from this card, and Storm Guardians can
        field at most two flamers, so the gap is one die's worth of choice."""
        if again:
            reroll = DiceNotationRoll(
                weapon.attacks_notation, count=len(group["pairs"]),
                dice_manager=self.dice_manager,
                label=f"Attacks ({enh_breath_of_vaul.BREATH_OF_VAUL_LABEL} re-roll): "
                      f"{group['weapon_label']}",
                roll_kind=ATTACKS_ROLL, log=self._log, is_reroll=True,
                target_name=group["target_squad"].name,
                attacker_squad=self.active_squad, target_squad=group["target_squad"],
            )
            if reroll.is_pending:
                self._pending_attacks_roll = reroll
                self.pending_step = "attacks"
                return
            total = reroll.total
        self._finish_attacks_roll(weapon, group, total)

    def _finish_attacks_roll(self, weapon, group, total):
        """The shared tail of the Attacks step - reached whether or not a
        re-roll was offered, taken or declined."""
        total_attacks = total + extra_attack_dice(
            weapon, group["target_squad"], group["weapon_key"],
            self.split_fire, self.assignments, group["pairs"],
        )
        self._continue_resolution_with_attacks(weapon, total_attacks)

    def _continue_resolution_with_attacks(self, weapon, total_attacks):
        """Shared tail of _begin_resolution(), reached directly (a plain
        fixed-int Attacks characteristic, the overwhelmingly common case) or
        after a dice-notation Attacks roll (see attacks_notation above) has
        been acknowledged - `weapon`/`total_attacks` are the same either
        way, this just doesn't need to know which path got it here."""
        group = self.current_group
        weapon_key, weapon_label, pairs, target_squad = (
            group["weapon_key"], group["weapon_label"], group["pairs"], group["target_squad"],
        )
        # Rule 24.37 ([TORRENT]): "that attack automatically hits the
        # target" - no hit roll at all, so no die can come up a natural 6:
        # every attack becomes an ordinary (non-critical) hit.
        if weapon.torrent:
            self._log(f"{weapon_label} automatically hits ({total_attacks} attack(s)) - [TORRENT].")
            # Retaliation Cadre (Bonded Heroes) / Starscythe: [TORRENT]
            # skips the hit roll entirely, so on_dice_acknowledged()'s own
            # adjustment point (below) is never reached for this group -
            # applied here instead, before the weapon is handed off to
            # wound/save resolution. Chained the same way melta_adjusted_
            # weapon() chains after bonded_heroes_adjusted_weapon() further
            # down - each is a no-op copy unless its own condition applies.
            bonded_weapon = self._adjusted_weapon(pairs, target_squad)
            self._handle_hit_results(total_attacks, 0, bonded_weapon, target_squad, weapon_label)
            return
        threshold = self._hit_threshold(self.current_group)
        modifiers = self._hit_modifiers(self.current_group)
        is_snap_shot = self.shooting_type == SNAP_SHOOTING
        label = f"{'Snap Shot Hit Roll' if is_snap_shot else 'Hit Roll'}: {weapon_label} ({total_attacks} attack(s))"
        if modifiers:
            label += f" [{describe_modifiers(modifiers)}]"
        self.dice_manager.roll(
            count=total_attacks, sides=6,
            label=label,
            success_threshold=threshold if threshold is not None else 7,
            target_name=target_squad.name, attacker_squad=self.active_squad, target_squad=target_squad,
            # Rule 15.09: "you cannot re-roll hit rolls" - a distinct kind so
            # CommandRerollController's REROLLABLE_KINDS never offers this one.
            roll_kind=SNAP_SHOT_HIT_ROLL if is_snap_shot else HIT_ROLL,
            # `weapon` above is the printed profile; the conditional grants
            # ([LETHAL HITS] from an Ammo Runt, [SUSTAINED HITS] from
            # Bladestorm/Arro'kon/Mont'ka) are only applied at resolution
            # time, so the note has to ask for the adjusted one itself.
            **self._crit_note("hit", self._adjusted_weapon(pairs, target_squad), target_squad),
        )
        self.pending_step = "hit"

    def _base_hit_threshold(self, group):
        """The un-modified hit threshold: normally BS-based, special-cased
        for [INDIRECT FIRE] attacks made as Indirect shooting (rule 10.07),
        which ignore BS entirely, and for rule 15.09's Snap Shooting, which
        ignores BS/[INDIRECT FIRE] alike - "each attack only hits on an
        unmodified hit roll of 6, irrespective of the attacking weapon's BS
        characteristic"."""
        if self.shooting_type == SNAP_SHOOTING:
            # Guardian Battlehost's Protector of the Paths is the FIRST thing
            # that changes 15.09's flat 6. It is an OVERRIDE here rather than a
            # modifier because 15.09 also ignores every modifier - a Modifier
            # would be correctly thrown away by the very rule this is meant to
            # beat. None means nothing applies and the printed 6 stands.
            override = enh_protector_of_the_paths.snap_hit_threshold(
                self.protector_of_the_paths, self.active_squad, self.objectives)
            return override if override is not None else 6
        shooter_model, weapon = group["pairs"][0]
        if self.shooting_type == INDIRECT_SHOOTING and weapon.indirect_fire:
            stationary = (
                self.movement_controller is not None
                and self.active_squad in self.movement_controller.stationary_squad_ids
            )
            visible = _visible_to_any_friendly(
                self.active_squad, group["target_squad"], self.obstacles, self.all_tokens, self.terrain_areas,
            )
            return 4 if (stationary and visible) else 6
        return _parse_threshold(effective_ballistic_skill(shooter_model, weapon))

    def _hit_modifiers(self, group):
        """Situational adjustments to the hit threshold - rule 10.06's
        Close-Quarters Monster/Vehicle malus and rule 13.08's Benefit of
        Cover both "worsen the [hit] characteristic by 1" (i.e. +1 to the
        threshold, since lower is better for BS); rule 24.16's [HEAVY]
        "add 1 to the hit roll" is the opposite - a -1 to the threshold.
        Rule 15.09 (Snap Shooting) ignores every one of these: "irrespective
        of... any modifiers"."""
        if self.shooting_type == SNAP_SHOOTING:
            return []
        shooter_model, weapon = group["pairs"][0]
        target_squad = group["target_squad"]
        modifiers = list(_damaged_modifier(shooter_model))
        # Wraithguard's Psychic Guidance: "each time a model in this unit
        # makes an attack, add 1 to the Hit roll" while near a friendly
        # AELDARI PSYKER. "Makes an attack", not "makes a ranged attack",
        # so it is in BOTH phases' hit modifiers - see
        # game/psychic_guidance.py.
        if psychic_guidance.applies(self.active_squad, self.all_tokens):
            modifiers.append(Modifier(-1, "Psychic Guidance"))
        # Prince Yriel's Piratical Hero, second half: "add 1 to the Hit roll"
        # while he leads. A bonus, so a -1 on the threshold.
        if corsair_abilities.piratical_hero_applies(self.active_squad):
            modifiers.append(Modifier(-1, corsair_abilities.PIRATICAL_HERO_LABEL))
        # Guardian Battlehost's Defend at All Costs: +1 to Hit for a DIRE
        # AVENGERS/GUARDIANS/SUPPORT WEAPON/WAR WALKERS model while its unit
        # AND/OR the target is within range of an objective. "makes an attack",
        # so it is in both phases' hit modifiers, like Psychic Guidance above.
        # Appended here, i.e. BEFORE the ignore-modifier filters at the end of
        # this method - a bonus added after them would simply be dropped.
        modifiers.extend(defend_at_all_costs.hit_modifiers(
            [m for m, _ in group["pairs"]], self.active_squad, target_squad,
            self.objectives))
        # Spirit Conclave's Shepherds of the Dead: +1 Hit AND +1 Wound for a
        # WRAITH CONSTRUCT against a unit carrying Vengeful Dead tokens. Two
        # modifiers at two seams, in both phases - "makes an attack".
        if self.shepherds_of_the_dead is not None:
            modifiers.extend(self.shepherds_of_the_dead.hit_modifiers(
                self.active_squad, target_squad))
        # The Wraithlord prints the same ability NAME with the other half:
        # "improve the Ballistic Skill and Weapon Skill characteristics of
        # weapons equipped by this model by 1". Separate flag, separate
        # predicate, same arithmetic - see game/psychic_guidance.py for why
        # the two readings cannot diverge in this engine.
        if psychic_guidance.applies_characteristics(self.active_squad, self.all_tokens):
            modifiers.append(Modifier(-1, "Psychic Guidance"))
        # The Farseer's Guide: "each time a friendly AELDARI model makes an
        # attack that targets that enemy unit, add 1 to the Hit roll" - a
        # bonus, so a -1 on the threshold. Army-wide, not unit-wide, which
        # is why the mark is held per player. See game/guide.py.
        if self.guide is not None and self.guide.applies(shooter_model, target_squad):
            modifiers.append(Modifier(-1, "Guide"))
        if self.shooting_type == CLOSE_QUARTERS_SHOOTING and is_monster_or_vehicle_unit(self.active_squad):
            # `targets_engaged_unit` was UNREACHABLE (always True) until
            # _is_valid_target_squad() started letting a MONSTER/VEHICLE shoot
            # out of the melee - this half of the condition was written from
            # the printed rule and then had nothing to distinguish. It is live
            # now, so the two ways of earning the malus get their own labels:
            # a die that says "non-[CLOSE-QUARTERS] weapon" while the weapon
            # plainly IS one sends the next investigation back to the board.
            targets_engaged_unit = self.active_squad.is_engaged_with(target_squad)
            if not is_close_quarters(weapon, self.active_squad):
                modifiers.append(Modifier(1, "Close-Quarters (non-[CLOSE-QUARTERS] weapon)"))
            elif not targets_engaged_unit:
                modifiers.append(Modifier(1, "Close-Quarters (target not engaged with this unit)"))
        # Strike Team's Suppression Volley ability (user-supplied, not a
        # core rule): "each time a model in that [suppressed] unit makes an
        # attack, subtract 1 from the Hit roll" - checked against the
        # SHOOTING squad (self.active_squad), the opposite direction from
        # Guided/Cover below, which check the TARGET.
        if self.suppression is not None and self.suppression.is_suppressed(self.active_squad):
            modifiers.append(Modifier(1, "Suppressed"))
        # T'au "For The Greater Good" army rule: a Guided attack against a
        # Spotted unit gets [IGNORES COVER] on top of its own weapon
        # keyword, but only if the mark came from a MARKERLIGHT Observer.
        guided = self.greater_good is not None and self.greater_good.is_guided_attack(self.active_squad, target_squad)
        # Rule 24.18 ([IGNORES COVER]): the target "cannot have the benefit
        # of cover against that attack", full stop - checked (via the
        # shared _cover_ignored_for_group(), also used by _dispatch_group()
        # to decide whether a group is even worth cover-splitting) before
        # Benefit of Cover so an ignores-cover weapon never even queries
        # for it. shooter_model already reflects a cover-homogeneous
        # sub-group by the time this runs (see _dispatch_group()), so this
        # is now an exact per-model result, not an approximation.
        if not self._cover_ignored_for_group(weapon, target_squad) and self._has_benefit_of_cover(shooter_model, target_squad):
            modifiers.append(Modifier(1, "Benefit of Cover"))
        if weapon.heavy and self._heavy_bonus_applies():
            modifiers.append(Modifier(-1, "[HEAVY] (stationary)"))
        if guided:
            # "improve the Ballistic Skill characteristic of that attack by
            # 1" - a better BS is a LOWER threshold, so -1 per this file's
            # Modifier convention (see [HEAVY] above).
            modifiers.append(Modifier(-1, "For the Greater Good (Guided)"))
        elif target_uploaded.applies(self.greater_good, self.active_squad, target_squad):
            # Pathfinder Team's Target Uploaded - the same "+1 BS" the
            # Guided branch above gives, for the case Guided structurally
            # cannot cover: an Observer unit shooting the target it marked
            # itself. `elif` rather than a second `if` so the two can never
            # stack into -2; see game/target_uploaded.py.
            modifiers.append(Modifier(-1, "Target Uploaded"))
        modifiers.extend(tank_hunters_modifiers(shooter_model, target_squad))
        # Warhost's Lightning-Fast Reactions - DEFENDER-side, like Guardian
        # Drone above: a penalty on the attacker's Hit roll because of
        # something the unit being attacked bought. Its printed WHEN names
        # both attack phases, so it is read in both files.
        modifiers.extend(
            warhost_lightning_fast_reactions.hit_modifiers(target_squad))
        # The Hammerhead's Armour Hunter - Tank Hunters with the WOUND half
        # missing, so it sits beside it and shares its keyword test.
        modifiers.extend(armour_hunter_module.modifiers(shooter_model, target_squad))
        # Riptide Battlesuit's "Weapon Support System" wargear ability
        # (user-supplied, not a core rule), and Dark Reapers' "Inescapable
        # Accuracy", which prints the same permission under another name:
        # "you can ignore any or all modifiers to that attack's Ballistic
        # Skill characteristic and any or all modifiers to the Hit roll" -
        # both halves land on the same threshold here, so one test covers
        # them. Word for word the same permission rule 24.29 ([PSYCHIC])
        # gives, so it gets the same automatic handling for the same reason
        # (see the [PSYCHIC] branch below: dropping every worsening modifier
        # and keeping every improving one is always the better play, so
        # there is no real choice to interrupt the game for). Per MODEL,
        # not per unit - it is a wargear ability of the bearer - and
        # shooter_model is exact here, not an approximation, since
        # _dispatch_group() has already split the group by cover.
        # Awakened Dynasty's Command Protocols: "while a NECRONS CHARACTER
        # model is leading this unit, ... add 1 to the Hit roll". Its text says
        # "an attack", so game/fight.py reads it too. Added BEFORE the two
        # ignore-modifier filters below so it is treated like every other
        # modifier - it is an IMPROVING one, so both filters keep it, but
        # placing it here means that stays true by construction rather than by
        # where the line happens to sit.
        modifiers.extend(awakened_dynasty.hit_modifiers(self.active_squad))
        # The Death Guard Plague Skullsquirm Blight: "each time a model in this
        # [Afflicted] unit makes an attack, subtract 1 from the Hit roll". "An
        # attack", not "a ranged attack", so game/fight.py reads the same
        # function - and it is asked of the SHOOTER, since it is the afflicted
        # unit's own attacks that are blunted.
        modifiers.extend(plagues.hit_modifiers(self.active_squad))
        # Kauyon's Precision of the Patient Hunter Enhancement: "each time the
        # BEARER makes a ranged attack, add 1 to the Hit roll" - per MODEL, and
        # shooter_model is exact for it because the Enhancement is part of
        # _attack_key(). Added before the two ignore-modifier filters, like
        # Command Protocols above and for the same reason: it is an IMPROVING
        # modifier, so both filters keep it, and placing it here means that
        # stays true by construction rather than by where the line sits.
        modifiers.extend(enh_precision_patient_hunter.hit_modifiers(shooter_model))
        if shooter_model.profile.ignores_hit_modifiers:
            modifiers = [m for m in modifiers if m.amount <= 0]
        # Kauyon's Patient Hunter, second half: "you can ignore any or all
        # modifiers to that attack's Ballistic Skill characteristic and/or all
        # modifiers to the Hit roll" while Guided against a Spotted unit, in
        # rounds 3-5. Word for word what the flag above and [PSYCHIC] below
        # say, so it gets their treatment - drop the worsening modifiers, keep
        # the improving ones, automatically. See game/kauyon.py for why a
        # "you can" is resolved without asking.
        # Kauyon's Coordinate to Engage: "improve the Ballistic Skill
        # characteristic of that attack by 1" against the unit this OBSERVER
        # marked - a better BS is a LOWER threshold, so -1 per this file's
        # Modifier convention. Added BEFORE the ignore-modifier filters, like
        # Command Protocols above and for the same reason: it is an IMPROVING
        # modifier, so both filters keep it, and placing it here means that
        # stays true by construction.
        if kauyon_coordinate_to_engage.applies(
                self.greater_good, self.active_squad, target_squad):
            modifiers.append(Modifier(-1, "Coordinate to Engage"))
        if kauyon.hit_modifiers_ignored(
                self.active_squad, target_squad, self.turn_tracker, self.greater_good):
            modifiers = [m for m in modifiers if m.amount <= 0]
        # Windrider Host's Mirage Field. DEFENDER-side, and it says "an
        # attack" rather than "a ranged attack", so game/fight.py carries the
        # same two lines - one printed word apart from Shimmerstone below.
        if enh_mirage_field.applies(target_squad):
            modifiers.append(Modifier(enh_mirage_field.MIRAGE_FIELD_PENALTY,
                                      enh_mirage_field.MIRAGE_FIELD_LABEL))
        # Armoured Warhost's Guiding Presence - ATTACKER-side, and a BONUS, so
        # a negative amount. Held as a per-player mark, hence the controller.
        if (self.guiding_presence is not None
                and self.guiding_presence.applies(self.active_squad)):
            modifiers.append(Modifier(enh_guiding_presence.GUIDING_PRESENCE_BONUS,
                                      enh_guiding_presence.GUIDING_PRESENCE_LABEL))
        if weapon.psychic:
            # Rule 24.29 ([PSYCHIC]): "you can ignore any or all modifiers...
            # to the hit roll" - always rational to drop every WORSENING
            # (positive) modifier and keep every IMPROVING (negative) one,
            # so unlike e.g. [LETHAL HITS]/[PRECISION] (where the choice has
            # a real downstream trade-off) this is applied automatically
            # rather than as an interactive decision - there's no case where
            # keeping a positive modifier would ever be the better play.
            modifiers = [m for m in modifiers if m.amount <= 0]
        # Aspect Host's Warrior Focus: "ignore any or all modifiers to that
        # attack's Ballistic Skill, Weapon skill ... and/or any or all
        # modifiers to the Hit roll". Three printed nouns, one threshold
        # here - so it gets the same treatment as the flag above and
        # [PSYCHIC]: drop the worsening modifiers, keep the improving
        # ones, automatically. Its Strength/AP/Damage third rides the
        # adjuster chain instead.
        if aspect_warrior_focus.ignores_hit_modifiers(self.active_squad):
            modifiers = [m for m in modifiers if m.amount <= 0]
        return modifiers

    def _wound_modifiers(self, target_squad, strength=None):
        """The Guardian Drone wargear item (user-supplied, not a core rule -
        game/drones.py): "each time a model makes a ranged attack that
        targets the bearer's unit, subtract 1 from the Wound roll" - a
        malus, so per this file's Modifier sign convention (positive
        worsens) that's a +1 on the wound THRESHOLD, same "X to the roll"
        handling as Suppression Volley's hit-roll malus in _hit_modifiers().
        Checked against the TARGET squad (unlike _hit_modifiers' mostly
        attacker-side checks) - this is the defender's own protection.

        `strength` is this attack's Strength as the wound step computed it
        (the already-adjusted one), and it is read by exactly one source: the
        Wave Serpent Shield, whose condition is about the ATTACK rather than
        about who is shooting - "if the Strength characteristic of that attack
        is greater than the Toughness characteristic of this model". Optional,
        so the callers that have no attack in hand keep meaning what they did.

        Tankbustas' own "Tank Hunters" (user-supplied, not a core rule) is
        the opposite direction - an ATTACKER-side bonus, checked against
        self.active_squad's representative model (same "read it off model
        0" simplification as e.g. squad_waaagh_active())."""
        modifiers = []
        if squad_has_guardian_drone(target_squad):
            modifiers.append(Modifier(1, "Guardian Drone"))
        # The Farseer Skyrunner's Misfortune: a MARKED enemy unit subtracts 1
        # from its OWN Wound rolls. Attacker-side, unlike the defender-side
        # maluses below it - the mark sits on the unit attacking HERE, so
        # reading it against target_squad would build the mirror image of
        # the printed rule. A malus, so a POSITIVE modifier.
        if (self.misfortune is not None
                and self.misfortune.afflicts(self.active_squad)):
            modifiers.append(Modifier(misfortune_module.MISFORTUNE_PENALTY,
                                      misfortune_module.MISFORTUNE_LABEL))
        # Commander Shadowsun's Advanced Guardian Drone - the same malus
        # one word narrower ("targets the bearer", not "the bearer's
        # unit"), which on a LONE OPERATIVE single-model unit is the same
        # set of attacks. See game/squad.py's own note.
        if squad_has_advanced_guardian_drone(target_squad):
            modifiers.append(Modifier(1, "Advanced Guardian Drone"))
        # War Horde's 'Ard as Nails (user-supplied): "each time an attack
        # targets your unit, subtract 1 from the Wound roll" - the same
        # defender-side malus as the Guardian Drone above, from a stratagem
        # instead of wargear. See game/ard_as_nails.py.
        if ard_as_nails_wound_modifier_applies(target_squad):
            modifiers.append(Modifier(ARD_AS_NAILS_WOUND_PENALTY, "'Ard as Nails"))
        # Warlock Conclave's Protect: "while a FARSEER model is leading this
        # unit, each time an attack targets this unit, subtract 1 from the
        # Wound roll" - the same defender-side malus, from a datasheet
        # ability. See game/protect.py.
        if protect.applies(target_squad):
            modifiers.append(Modifier(1, "Protect"))
        # Eldrad Ulthran's Doom: Guide's twin one word apart - a mark set at the
        # end of his Movement phase that lasts until the start of his next
        # Command phase, so it is live through the opponent's whole turn. The
        # bonus is army-wide ("each time a friendly AELDARI model makes an
        # attack"), which is why the mark is held per player, and it is a bonus
        # rather than a malus, so a NEGATIVE amount. See game/doom.py.
        if self.doom is not None and self.doom.applies_to_squad(self.active_squad, target_squad):
            modifiers.append(Modifier(DOOM_WOUND_BONUS, "Doom"))
        # Darkstrider's Structural Analyser: "while this model is leading a
        # unit, each time a model in that unit makes a ranged attack, add 1 to
        # the Wound roll" - only the SECOND attacker-side entry in this
        # defender-oriented list, after Tank Hunters just below, and a BONUS,
        # so a negative amount (see game/structural_analyser.py on the sign).
        if structural_analyser_module.applies(self.active_squad):
            modifiers.append(Modifier(
                structural_analyser_module.STRUCTURAL_ANALYSER_WOUND_MODIFIER,
                structural_analyser_module.STRUCTURAL_ANALYSER_LABEL))
        # Shepherds of the Dead's second half: the SAME condition as the hit
        # modifier, on the other roll. Two seams rather than one, because the
        # printed text adds 1 to each.
        if self.shepherds_of_the_dead is not None:
            modifiers.extend(self.shepherds_of_the_dead.wound_modifiers(
                self.active_squad, target_squad))
        # Guardian Battlehost's Shield Nodes - DEFENDER-side, like Guardian
        # Drone and Protect beside it: a penalty on the attacker's Wound roll
        # because of something about the unit being shot at.
        modifiers.extend(guardian_shield_nodes.wound_modifiers(target_squad))
        if self.active_squad.models:
            modifiers.extend(tank_hunters_modifiers(self.active_squad.models[0], target_squad))
        # Commander Farsight's Way of the Short Blade: "+1 to the Wound
        # roll" for a unit he is LEADING, against a target within 9".
        # Hooked into both phases because its text says "makes an
        # attack", not "makes a ranged attack" - see
        # game/way_of_the_short_blade.py.
        modifiers.extend(way_of_the_short_blade.wound_modifiers(self.active_squad, target_squad))
        # The Wave Serpent Shield, the only defender-side modifier here whose
        # condition is about the ATTACK: "if the Strength characteristic of
        # that attack is greater than the Toughness characteristic of this
        # model, subtract 1 from the Wound roll" - so a positive threshold
        # adjustment, per this file's sign convention.
        if wave_serpent_shield.applies(target_squad, strength):
            modifiers.append(Modifier(
                wave_serpent_shield.WAVE_SERPENT_SHIELD_PENALTY,
                wave_serpent_shield.WAVE_SERPENT_SHIELD_LABEL))
        # Aspect Host's Shimmerstone. DEFENDER-side like the shield above, and
        # RANGED-only: the one printed word that keeps it out of game/fight.py,
        # where its Etappe-3 sibling Mirage Field does appear.
        if enh_shimmerstone.applies(target_squad):
            modifiers.append(Modifier(enh_shimmerstone.SHIMMERSTONE_PENALTY,
                                      enh_shimmerstone.SHIMMERSTONE_LABEL))
        # Lychguard's Guardian Protocols - the same S > T comparison and the
        # same positive sign as the shield above, differing only in its
        # "while a NOBLE model is leading this unit" clause. See
        # game/guardian_protocols.py for why it shares this hook rather than
        # restating the arithmetic.
        if guardian_protocols.applies(target_squad, strength):
            modifiers.append(Modifier(
                guardian_protocols.GUARDIAN_PROTOCOLS_PENALTY,
                guardian_protocols.GUARDIAN_PROTOCOLS_LABEL))
        # Kauyon's A Tempting Trap: "add 1 to the Wound roll" against an enemy
        # within range of the player's Trap objective - an ATTACKER-side entry
        # in a mostly defender-side list, like Structural Analyser, so it reads
        # self.active_squad for the shooter. A bonus, so a -1 on the threshold.
        if (self.tempting_trap is not None
                and self.tempting_trap.wound_bonus_applies(self.active_squad, target_squad)):
            modifiers.append(Modifier(-1, kauyon_tempting_trap.TEMPTING_TRAP_NAME))
        # Kauyon's Precision of the Patient Hunter Enhancement, second half:
        # "from the third battle round onwards, add 1 to the Wound roll as
        # well". PER MODEL, so it needs the group's shooter rather than
        # self.active_squad - and that read is exact rather than a
        # simplification, because the Enhancement is part of _attack_key().
        modifiers.extend(enh_precision_patient_hunter.wound_modifiers(
            self._representative_shooter(), self.turn_tracker))
        return modifiers

    def _representative_shooter(self):
        """The model whose per-model properties stand for the weapon group
        currently being resolved.

        current_group is set before a group is dispatched and holds its pairs,
        so this is the SAME model _hit_modifiers() reads as `shooter_model`.
        Falls back to the unit's first model for the callers that ask outside a
        live group (previews and log lines), which is the older
        one-representative simplification this file already uses for
        Tank Hunters - and is exact for anything that is part of
        _attack_key()."""
        group = self.current_group
        if group and group.get("pairs"):
            return group["pairs"][0][0]
        models = getattr(self.active_squad, "models", None) or []
        return models[0] if models else None

    def _forward_observers_applies(self, target_squad):
        """Stealth Battlesuits' "Forward Observers" ability (user-supplied,
        not a core rule) - see game/greater_good.py's has_forward_observers()."""
        return self.greater_good is not None and self.greater_good.has_forward_observers(self.active_squad, target_squad)

    def _begin_ones_reroll(self, kind, ones, threshold, weapon, target_squad, weapon_label, **ctx):
        """Forward Observers: "re-roll a Hit roll of 1"/"re-roll a Wound
        roll of 1" - an AUTOMATIC (not optional) re-roll of just the dice
        that came up a natural 1, kept as a real, visible dice step (like
        every other roll in this engine) rather than silently swapped in
        the background. `kind` is "hit" or "wound"; on_dice_acknowledged()'s
        "{kind}_reroll_ones" branch resolves it and folds the extra
        hits/wounds into the running total via _finish_hit_roll()/
        _finish_wound_roll().

        `ones` counts only the natural 1s that may still be re-rolled - a 1
        that is itself the result of an earlier re-roll (a Command Re-roll,
        rule 15.02) stays a 1, because a dice can never be re-rolled more
        than once. is_reroll=True marks the dice thrown here as spent for
        the same reason, so nothing may throw them again."""
        self._pending_ones_reroll = {
            "kind": kind, "ones": ones, "threshold": threshold, "weapon": weapon,
            "target_squad": target_squad, "weapon_label": weapon_label, **ctx,
        }
        self.dice_manager.roll(
            count=ones, sides=6,
            label=f"{weapon_label}: {'Hit' if kind == 'hit' else 'Wound'} Roll re-roll of 1s "
                  f"({ctx.get('reason', 'Forward Observers')})",
            success_threshold=threshold, target_name=target_squad.name, attacker_squad=self.active_squad, target_squad=target_squad,
            roll_kind=HIT_ROLL if kind == "hit" else WOUND_ROLL,
            is_reroll=True, **self._crit_note(kind, weapon, target_squad),
        )
        self.pending_step = f"{kind}_reroll_ones"

    def _finish_hit_roll(self, hits, crits, weapon, target_squad, weapon_label, rerollable=None, hit_threshold=None, ones=0):
        """Shared tail of the hit-roll step, reached directly (no natural 1s
        to reroll, or Forward Observers doesn't apply) or after that
        ability's automatic reroll-of-1s resolves.

        Beast Snagga Boyz' Monster Hunters offers its optional Hit-roll
        re-roll HERE rather than at the caller, so it sits after Forward
        Observers' automatic reroll-of-1s (the two chain: the 1s are thrown
        first and are then spent, so only what is left may still be
        re-rolled) and, crucially, BEFORE [SUSTAINED HITS] is applied below -
        the extra hits a critical grants are a consequence of the final hit
        roll, so they have to be computed from whichever roll actually
        stands.

        `rerollable` is the (hits, crits, count) breakdown counted over only
        the dice that still have their one re-roll left; `hit_threshold` is
        needed to throw them again. Both default to None for the callers
        that have nothing left to offer (and for [TORRENT]'s own auto-hit
        shortcut, which never rolled a Hit roll at all)."""
        if rerollable is not None and self._hit_reroll_choice_needed(target_squad, rerollable[2]):
            self._offer_hit_reroll_choice(
                hits, crits, weapon, target_squad, weapon_label, hit_threshold, rerollable,
                self.active_squad.owner, ones=ones,
            )
            return
        self._apply_sustained_hits(hits, crits, weapon, target_squad, weapon_label)

    def _apply_sustained_hits(self, hits, crits, weapon, target_squad, weapon_label):
        """Every path through the hit step funnels through here - both
        _finish_hit_roll()'s tail and Monster Hunters' own re-roll branch,
        which reaches it directly. That makes it the one place an Aspect
        Shrine token can be offered against the roll that actually STANDS,
        and it has to happen before _apply_sustained_hits_now() below turns
        criticals into extra hits."""
        self._apply_sustained_hits_now(hits, crits, weapon, target_squad, weapon_label)

    def _apply_sustained_hits_now(self, hits, crits, weapon, target_squad, weapon_label):
        """The part of the hit step that must run on the FINAL hit roll -
        split out of _finish_hit_roll() so Monster Hunters' optional re-roll
        can interpose between the two."""
        # Rule 24.36 ([SUSTAINED HITS X]): each critical hit adds X extra
        # hits directly (no extra hit roll) - these extra hits are ordinary
        # (non-critical) hits, so `crits` itself is untouched and still
        # reflects only the real critical hits for [LETHAL HITS]'s purposes.
        if crits and weapon.sustained_hits_notation is not None:
            self._begin_sustained_hits_roll(hits, crits, weapon, target_squad, weapon_label)
            return
        self._add_sustained_hits(
            hits, crits, crits * weapon.sustained_hits, weapon, target_squad, weapon_label,
        )

    def _begin_sustained_hits_roll(self, hits, crits, weapon, target_squad, weapon_label):
        """[SUSTAINED HITS X] where X is itself a die (the Avatar of Khaine's
        printed "d3"). One die PER CRITICAL HIT, thrown as a single visible
        roll and summed - which is the fast-dice equivalent of rolling each
        critical hit's own X and adds up to the same distribution.

        Same shape as _begin_strength_roll()/the "attacks" step: a real
        dice_manager step rather than the "use the die's maximum as a fixed
        value" simplification, with the hit step's context stashed so it can
        carry on once the roll resolves."""
        self._pending_sustained = {
            "hits": hits, "crits": crits, "weapon": weapon,
            "target_squad": target_squad, "weapon_label": weapon_label,
        }
        self._pending_sustained_roll = DiceNotationRoll(
            weapon.sustained_hits_notation, count=crits, dice_manager=self.dice_manager,
            label=(f"[SUSTAINED HITS {describe_dice_notation(weapon.sustained_hits_notation)}]: "
                   f"{weapon_label} ({crits} critical hit(s))"),
            log=self._log, target_name=target_squad.name,
            attacker_squad=self.active_squad, target_squad=target_squad,
        )
        if self._pending_sustained_roll.is_pending:
            self.pending_step = "sustained_hits"
            return
        # No dice_manager (the non-interactive test wrappers): resolved
        # immediately, same convenience path DiceNotationRoll documents.
        self._finish_sustained_hits_roll()

    def _finish_sustained_hits_roll(self):
        ctx = self._pending_sustained
        total = self._pending_sustained_roll.total
        self._pending_sustained = None
        self._pending_sustained_roll = None
        self._add_sustained_hits(
            ctx["hits"], ctx["crits"], total, ctx["weapon"], ctx["target_squad"], ctx["weapon_label"],
        )

    def _add_sustained_hits(self, hits, crits, sustained, weapon, target_squad, weapon_label):
        """The shared tail: fold the extra hits in and carry on. `crits` is
        deliberately NOT increased - rule 24.36's extra hits are ordinary
        hits, which is what [LETHAL HITS] downstream depends on."""
        hits += sustained
        if sustained:
            self._log(f"{weapon_label}: [SUSTAINED HITS] adds {sustained} extra hit(s).")
        self._handle_hit_results(hits, crits, weapon, target_squad, weapon_label)

    def _rerollable_dice_indices(self, rolls):
        """Which dice of the roll just acknowledged may still be re-rolled -
        a dice can never be re-rolled more than once, and DiceManager is
        where that memory lives (see its already_rerolled)."""
        spent = self.dice_manager.already_rerolled if self.dice_manager is not None else set()
        return [i for i in range(len(rolls)) if i not in spent]

    def _finish_wound_roll(self, wounds, crits, no_effect, weapon, target_squad, target_profile, weapon_label, wound_threshold, rerollable, ones=0):
        """Shared tail of the wound-roll step, reached directly or after
        Forward Observers' automatic reroll-of-1s resolves - `no_effect`
        already reflects the post-reroll failure count, so [TWIN-LINKED]/
        Breach and Clear's own offer correctly sees whether a failure still
        remains worth using it on.

        `rerollable` is that same (wounds, crits, no_effect) breakdown
        counted over ONLY the dice that still have their re-roll left. The
        two differ whenever something already re-rolled part of this roll
        (Command Re-roll, or Forward Observers' reroll-of-1s), and it is the
        rerollable half that decides what may be thrown again - a dice can
        never be re-rolled more than once."""
        if self._twin_linked_choice_needed(weapon, rerollable[2], target_squad):
            self._offer_twin_linked_choice(
                no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold,
                self.active_squad.owner, rerollable, ones=ones,
            )
        else:
            self._resolve_wounds(weapon, target_squad, target_profile, weapon_label, wounds, crits)

    def _heavy_bonus_applies(self):
        """Rule 24.16 ([HEAVY]): "add 1 to the hit roll if all of the
        following apply to the attacking unit": unengaged, not set up on
        the battlefield this turn (Squad.set_up_this_turn, rule 18.02),
        and no model in the unit moved more than 3" this turn
        (MovementController.moved_distance_this_turn, defaults to 0.0 for
        a unit that hasn't made a Normal/Advance/Surge move this turn at
        all - e.g. Remain Stationary - which correctly counts as "not
        moved more than 3"")."""
        squad = self.active_squad
        if squad.is_engaged(self.all_tokens):
            return False
        if squad.set_up_this_turn:
            return False
        if self.movement_controller is not None:
            moved = self.movement_controller.moved_distance_this_turn.get(squad, 0.0)
            if moved > 3.0:
                return False
        return True

    def _has_benefit_of_cover(self, shooter_model, target_squad):
        """Rule 13.08 as it stood when this target was selected (rule 10.02,
        see _snapshot_target_state()) - cover cannot change halfway through
        one unit's shooting just because the target's front models became
        casualties of that same unit's earlier weapon groups. Falls back to a
        live computation when nothing was snapshotted for this pair."""
        key = (shooter_model, target_squad)
        if key in self._cover_snapshot:
            return self._cover_snapshot[key]
        return self._compute_benefit_of_cover(shooter_model, target_squad)

    def _compute_benefit_of_cover(self, shooter_model, target_squad):
        """Rule 13.08: the unit has the benefit of cover only if EVERY model
        in it qualifies, via either condition - INFANTRY/BEASTS/SWARM within
        any terrain area, or not fully visible to the shooting model due to
        intervening terrain (rule 13.10's obscuring terrain areas are folded
        into model_fully_visible via terrain_areas). Rule 24.33 (STEALTH):
        "if every model in a unit has this ability", that unit unconditionally
        has the benefit of cover against every ranged attack - checked first
        so a Stealth unit never needs terrain/visibility at all."""
        if self.barrage_of_filth is not None and self.barrage_of_filth.denies_cover(target_squad):
            # The Defiler's Barrage of Filth: "that unit CANNOT have the
            # benefit of Cover". Checked FIRST and returning False, because it
            # is an absolute statement while everything below it is a grant -
            # so it has to beat STEALTH and the two Death Guard cover-granting
            # abilities rather than merely joining them.
            return False
        if squad_has_stealth(target_squad):
            return True
        # The Daemon Prince's Miasma of Pestilence - the third unconditional
        # grant here, and asked of the TARGET where Skullsquirm Blight above is
        # asked of the shooter. The two read almost identically in prose and
        # sit on opposite sides of this function.
        if miasma_of_pestilence.applies(target_squad, self.all_tokens):
            return True
        # Spirit Conclave's Rune of Mists - the first cover grant here with a
        # DISTANCE, and an INVERTED one: cover applies "unless the attacking
        # model is within 18". It fits without a new parameter because this
        # function is already asked per SHOOTER, which is what "the attacking
        # model" needs. Rule 10.02 then freezes the answer for the whole
        # activation, like every other cover source.
        if enh_rune_of_mists.grants_cover(shooter_model, target_squad):
            return True
        for model in target_squad.models:
            keyword_in_area = (
                (model.profile.infantry or model.profile.beasts or model.profile.swarm)
                and any(area.overlaps_model(model) for area in self.terrain_areas)
            )
            if keyword_in_area:
                continue
            if not line_of_sight.model_fully_visible(shooter_model, model, self.obstacles, self.all_tokens, self.terrain_areas):
                continue
            return False
        return True

    def _hit_threshold(self, group):
        return apply_modifiers(self._base_hit_threshold(group), self._hit_modifiers(group))

    def on_dice_acknowledged(self):
        # Rule 24.15 ([HAZARDOUS]): these two steps run after the unit's
        # last weapon group has already finished (current_group is None by
        # then) - handled up front, before the "no current_group" guard
        # below that every other pending_step relies on.
        if self.pending_step == "hazard":
            if self.dice_manager is None:
                return
            rolls = self.dice_manager.last_values
            total_mortal_wounds = hazard_mortal_wounds(self.active_squad, rolls)
            self._log(
                f"Hazard Rolls {rolls}: {hazard_failures(rolls)}/{len(rolls)} failed -> "
                f"{total_mortal_wounds} mortal wound(s)."
            )
            if total_mortal_wounds > 0:
                self.mortal_wound_session = MortalWoundAllocationSession(
                    self.active_squad, total_mortal_wounds, dice_manager=self.dice_manager, log=self._log,
                    waaagh=self.waaagh,
                )
                self.pending_step = "hazard_wounds"
                self._check_hazard_wounds_done()
            else:
                self._actually_finish_squad()
            return

        if self.pending_step == "hazard_wounds":
            if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
                self.mortal_wound_session.on_fnp_acknowledged()
                self._check_hazard_wounds_done()
            return

        if self.pending_step is None or self.dice_manager is None or self.current_group is None:
            return

        rolls = self.dice_manager.last_values
        group = self.current_group
        weapon_label = group["weapon_label"]
        target_squad = group["target_squad"]
        if not any(not m.is_dead() for m in target_squad.models):
            # Real crash, found via user report (IndexError right as their
            # squad died to enemy fire): a target squad can be wiped out
            # mid-ACTIVATION by an earlier weapon group of the SAME
            # shooting unit (most commonly under Split Fire, which locks in
            # every model+weapon's target up front - see
            # _begin_next_split_group()'s docstring for the full mechanism)
            # - and main.py's state.remove_dead_models() (the ONLY place a
            # dead model actually leaves Squad.models) is a once-per-frame
            # step entirely outside this resolution chain, so a model can
            # still be sitting in target_squad.models, merely marked dead,
            # right up until the very next weapon group starts rolling
            # against the very same now-empty unit. Checking "no living
            # model left" (not just "list is empty") catches both timings.
            # Nothing left to hit/wound/save/damage - abandon this group
            # instead of reading a representative profile off of nothing.
            self._log(f'{target_squad.name} was destroyed before {weapon_label} could finish resolving - abandoned.')
            # Drop the half-finished session too: unlike every other way out
            # of a group, this one skips _check_allocation_done() (which is
            # what normally clears it), and a lingering session would keep
            # answering pending_damage_choice for a group that no longer
            # exists - masking the NEXT session's own choice, since that
            # property returns the first non-None SESSION, not the first
            # non-None choice.
            self.damage_session = None
            self._finish_group()
            return
        if self.pending_step == "sustained_hits":
            # A dice-notation [SUSTAINED HITS X] (the Avatar of Khaine's
            # "d3"), acknowledged between the Hit roll and the Wound roll it
            # feeds - same shape as the "strength"/"attacks" branches.
            if self._pending_sustained_roll is None:
                return
            self._pending_sustained_roll.on_dice_acknowledged()
            if self._pending_sustained_roll.is_pending:
                return
            self._finish_sustained_hits_roll()
            return

        if self.pending_step == "strength":
            # A dice-notation Strength (e.g. the Zzap gun's "D6+6"),
            # acknowledged before the Wound roll it feeds - same shape as
            # the "attacks" branch below.
            if self._pending_strength_roll is None:
                return
            self._pending_strength_roll.on_dice_acknowledged()
            if self._pending_strength_roll.is_pending:
                return
            self._finish_strength_roll()
            return

        if self.pending_step == "attacks":
            # Rule: acknowledging a dice-notation Attacks roll (see
            # _begin_resolution()'s attacks_notation branch) - the RAW
            # (un-adjusted) representative weapon is used here, matching
            # _begin_resolution()'s own synchronous path exactly: Bonded
            # Heroes/Starscythe only ever touch Strength/AP, applied once
            # right after the (real) Hit roll below, never before it - using
            # the already-adjusted `weapon` computed further down for this
            # step would double-apply those bonuses the moment the Hit roll
            # actually starts.
            if self._pending_attacks_roll is None:
                return
            self._pending_attacks_roll.on_dice_acknowledged()
            total = self._pending_attacks_roll.total
            self._pending_attacks_roll = None
            raw_weapon = group["pairs"][0][1]
            # Guardian Battlehost's Breath of Vaul: "each time you roll to
            # determine the number of attacks made with a flamer ... you can
            # re-roll the result". The FIRST re-roll offer on an Attacks roll -
            # Damage rolls have had one since Sunforge, and that machinery
            # turned out to be generic apart from the word in its prompt (see
            # game/notation_reroll.py). A True return means the answer arrives
            # later through the callback, so this must not carry on.
            if enh_breath_of_vaul.attacks_reroll_applies(self.active_squad, raw_weapon):
                offer = DamageRerollOffer(
                    enh_breath_of_vaul.BREATH_OF_VAUL_LABEL,
                    decision_manager=self.decision_manager, dice_manager=self.dice_manager,
                    game_log=self.game_log, owner=self.active_squad.owner,
                    weapon_name=raw_weapon.name, roll_name="Attacks",
                    notation=raw_weapon.attacks_notation,
                )
                if offer.maybe_offer(
                    total,
                    lambda again, w=raw_weapon, g=group, t=total: self._after_attacks_reroll(w, g, t, again),
                ):
                    return
            self._finish_attacks_roll(raw_weapon, group, total)
            return

        target_profile = allocation_target_profile(target_squad)
        # Retaliation Cadre (Bonded Heroes): a no-op copy unless the group's
        # representative shooter is a BATTLESUIT model within range - see
        # bonded_heroes_adjusted_weapon()'s docstring. Applied once here so
        # it flows through every downstream use of `weapon` this call
        # (wound threshold, and - chained via melta_adjusted_weapon() -
        # damage), matching how [MELTA X] itself is only ever applied at
        # its own point of use rather than mutating the shared weapon.
        # Starscythe (Crisis Starscythe Battlesuits) and Drive-by Dakka
        # (Warbikers) chain right after it for the same reason - all three
        # only ever touch AP/Strength, never Damage, so chaining order
        # between them doesn't matter.
        weapon = self._adjusted_weapon(group["pairs"], target_squad)
        if self.pending_step == "hit":
            threshold = self._hit_threshold(group)
            # Lhykhis' Whispering Web is the first source of a lowered crit
            # threshold that reaches a RANGED attack ("makes an attack", not
            # "makes a melee attack"), so this step passes one at all now -
            # it used to take rule 05.02's default 6 implicitly. melee_only
            # is False here, which is what keeps the two melee-worded sources
            # (Unbridled Carnage, Mandiblasters) out. See game/crit_hit.py.
            crit_threshold = crit_hit_threshold(
                group["pairs"][0][0], target_squad, self.whispering_web,
                hit_threshold=threshold, weapon=weapon,
            )
            results = [_resolve_roll(r, threshold, crit_threshold) for r in rolls]
            hits = sum(1 for r in results if r != "fail")
            crits = sum(1 for r in results if r == "critical")
            misses = len(rolls) - hits
            # Only 1s that still have their re-roll left (a dice can never be
            # re-rolled more than once) - a die a Command Re-roll (15.02) has
            # already thrown stays as it landed, even on a 1.
            free = self._rerollable_dice_indices(rolls)
            ones = sum(1 for i in free if rolls[i] == 1)
            # Same split as the wound step below: what the roll produced
            # overall vs. what part of it may still be re-rolled at all.
            # Monster Hunters (offered in _finish_hit_roll()) may only throw
            # the latter.
            free_hits = sum(1 for i in free if results[i] != "fail")
            free_crits = sum(1 for i in free if results[i] == "critical")
            rerollable = (free_hits, free_crits, len(free))
            self._log(
                f"{weapon_label} hit roll {rolls}{_threshold_note(threshold, self._base_hit_threshold(group), self._hit_modifiers(group))}: "
                f"{hits} hit(s) (of which {crits} critical), {misses} miss(es)."
            )
            # Swift Demise's two halves are mutually exclusive ("you can
            # re-roll the Hit roll INSTEAD"), so when the whole-roll choice is
            # on offer the automatic 1s throw is HELD BACK and appears as one
            # of the options instead - see game/swift_demise.py. Forward
            # Observers has no such upgrade and is unaffected.
            ones_or_whole_choice = (
                reroll_scope.is_ones_or_whole(self._hit_reroll_reason(target_squad))
                and self._hit_reroll_choice_needed(target_squad, len(free))
            )
            hard_wired = destroyer_cult.hard_wired_applies(
                self.active_squad, target_squad, self._eligible_target_squads())
            tyrant = protocol_conquering_tyrant.applies(
                self.active_squad, weapon, group.get("pairs"), target_squad)
            # Commander Shadowsun's Hero of the Empire - the only AURA among
            # these, so it is a property of where her model stands rather than
            # of the attacking unit, and it re-rolls the HIT roll only (Forward
            # Observers, which it otherwise resembles, does both).
            hero_aura = hero_of_the_empire_module.applies(self.active_squad, self.all_tokens)
            fireknife_ones = fireknife.applies(self.active_squad)
            # Reavers of the Void's base clause: "re-roll a Hit roll of 1",
            # unconditional. Its whole-roll upgrade is the reason above, and
            # when that is on offer these 1s are held back like every other
            # two-clause source here.
            reavers_ones = reavers_of_the_void.applies(self.active_squad)
            # Path of the Warrior's first option. A PLAIN automatic 1s
            # re-roll - no "you can", no "instead" - so it belongs in this
            # disjunction and NOT in _hit_reroll_reason(), which drives the
            # failures-or-whole offer the printed text never gives.
            warrior_hit_ones = (self.path_of_the_warrior is not None
                                and self.path_of_the_warrior.hit_ones_apply(self.active_squad))
            automatic_ones = ones and not ones_or_whole_choice and (
                self._forward_observers_applies(target_squad)
                or swift_demise.applies(self.active_squad)
                or hard_wired
                or tyrant
                or hero_aura
                or fireknife_ones
                or reavers_ones
                or warrior_hit_ones
            )
            if automatic_ones:
                if self._forward_observers_applies(target_squad):
                    ones_reason = "Forward Observers"
                elif hero_aura:
                    ones_reason = hero_of_the_empire_module.HERO_OF_THE_EMPIRE_LABEL
                elif fireknife_ones:
                    ones_reason = fireknife.FIREKNIFE_LABEL
                elif reavers_ones:
                    ones_reason = reavers_of_the_void.REAVERS_OF_THE_VOID_LABEL
                elif swift_demise.applies(self.active_squad):
                    ones_reason = swift_demise.SWIFT_DEMISE_LABEL
                elif hard_wired:
                    ones_reason = destroyer_cult.HARD_WIRED_LABEL
                else:
                    ones_reason = protocol_conquering_tyrant.CONQUERING_TYRANT_LABEL
                self._begin_ones_reroll(
                    "hit", ones, threshold, weapon, target_squad, weapon_label, hits=hits, crits=crits,
                    reason=ones_reason,
                    # The 1s are about to be thrown, so they are spent: every
                    # one of them was a miss, hence only the count drops -
                    # free_hits/free_crits are untouched.
                    rerollable=(free_hits, free_crits, len(free) - ones),
                )
            else:
                self._finish_hit_roll(hits, crits, weapon, target_squad, weapon_label, rerollable, threshold,
                                      ones=ones)

        elif self.pending_step == "hit_reroll_ones":
            ctx = self._pending_ones_reroll
            self._pending_ones_reroll = None
            results = [_resolve_roll(r, ctx["threshold"]) for r in rolls]
            extra_hits = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            self._log(
                f"{ctx['weapon_label']}: {ctx.get('reason', 'Forward Observers')} re-roll of 1s {rolls} -> "
                f"{extra_hits} additional hit(s) (of which {extra_crits} critical)."
            )
            # The dice just thrown are spent, so what they produced counts
            # towards the RESULT but never towards what Monster Hunters may
            # still re-roll - ctx's rerollable pool is carried through
            # untouched, same as the wound side's own ones-reroll branch.
            self._finish_hit_roll(
                ctx["hits"] + extra_hits, ctx["crits"] + extra_crits, ctx["weapon"], ctx["target_squad"],
                ctx["weapon_label"], ctx.get("rerollable"), ctx["threshold"],
            )

        elif self.pending_step == "hit_monster_hunters_reroll":
            # Which scope the player picked arrives here purely as "how many
            # hits/crits are carried over" (see _offer_hit_reroll_choice()),
            # so this branch needs no branching of its own beyond the
            # wording - the same shape as the wound side's own re-roll
            # branch.
            ctx = self._pending_hit_reroll
            self._pending_hit_reroll = None
            crit_threshold = crit_hit_threshold(
                group["pairs"][0][0], ctx["target_squad"], self.whispering_web,
                hit_threshold=ctx["hit_threshold"], weapon=ctx["weapon"],
            )
            results = [_resolve_roll(r, ctx["hit_threshold"], crit_threshold) for r in rolls]
            extra_hits = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            if ctx.get("full"):
                self._log(
                    f"{ctx['weapon_label']}: re-rolled the whole Hit roll {rolls} ({ctx['reason']}) -> "
                    f"{extra_hits} hit(s) (of which {extra_crits} critical); the previous roll is discarded."
                )
            else:
                self._log(
                    f"{ctx['weapon_label']}: re-rolled failed hit rolls {rolls} ({ctx['reason']}) -> "
                    f"{extra_hits} additional hit(s) (of which {extra_crits} critical)."
                )
            self._apply_sustained_hits(
                ctx["hits"] + extra_hits, ctx["crits"] + extra_crits, ctx["weapon"], ctx["target_squad"],
                ctx["weapon_label"],
            )

        elif self.pending_step == "wound":
            # _effective_strength(), not weapon.strength: a dice-notation
            # Strength was rolled before this step and must be the same value
            # the threshold was shown with.
            wound_threshold = _wound_threshold(self._effective_strength(weapon), attached_unit_toughness(target_squad))
            wound_threshold = apply_modifiers(
                wound_threshold,
                self._wound_modifiers(target_squad, self._effective_strength(weapon)))
            crit_threshold = _wound_crit_threshold(weapon, target_squad)
            results = [_resolve_roll(r, wound_threshold, crit_threshold) for r in rolls]
            wounds = sum(1 for r in results if r != "fail")
            crits = sum(1 for r in results if r == "critical")
            no_effect = len(rolls) - wounds
            # Same split as the hit step: what this roll produced overall vs.
            # what part of it may still be re-rolled at all (see
            # _rerollable_dice_indices()). [TWIN-LINKED]/Breach and Clear
            # below may only throw the latter.
            free = self._rerollable_dice_indices(rolls)
            ones = sum(1 for i in free if rolls[i] == 1)
            free_wounds = sum(1 for i in free if results[i] != "fail")
            free_crits = sum(1 for i in free if results[i] == "critical")
            rerollable = (free_wounds, free_crits, len(free) - free_wounds)
            self._log(
                f"{weapon_label} wound roll {rolls}"
                f"{_threshold_note(wound_threshold, _wound_threshold(self._effective_strength(weapon), attached_unit_toughness(target_squad)), self._wound_modifiers(target_squad, self._effective_strength(weapon)))}: "
                f"{wounds} wound(s) (of which {crits} critical), {no_effect} no effect."
            )
            # Same arrangement the hit step uses: a two-clause source's
            # automatic 1s are HELD BACK while its whole-roll alternative is
            # actually on offer, because "instead" makes them exclusive.
            wound_choice = (
                reroll_scope.is_ones_or_whole(self._wound_reroll_reason(weapon, target_squad))
                and self._twin_linked_choice_needed(weapon, len(free) - free_wounds, target_squad)
            )
            if self._forward_observers_applies(target_squad):
                ones_reason = "Forward Observers"
            elif implacable_eradication.applies(self.active_squad):
                ones_reason = implacable_eradication.IMPLACABLE_ERADICATION_LABEL
            elif destroyer_cult.optimised_for_slaughter_applies(self.active_squad, weapon, target_squad):
                ones_reason = destroyer_cult.OPTIMISED_FOR_SLAUGHTER_LABEL
            elif (self.path_of_the_warrior is not None
                    and self.path_of_the_warrior.wound_ones_apply(self.active_squad)):
                # Path of the Warrior's SECOND option - the same plain
                # automatic 1s re-roll on the other roll.
                ones_reason = path_of_the_warrior.PATH_OF_THE_WARRIOR_LABEL
            else:
                ones_reason = None
            if ones and ones_reason is not None and not wound_choice:
                self._begin_ones_reroll(
                    "wound", ones, wound_threshold, weapon, target_squad, weapon_label,
                    wounds=wounds, crits=crits, no_effect=no_effect, crit_threshold=crit_threshold,
                    target_profile=target_profile, reason=ones_reason,
                    # The 1s are about to be thrown, so they are spent: every
                    # one of them was a failure, hence only the failure count
                    # drops.
                    rerollable=(free_wounds, free_crits, len(free) - free_wounds - ones),
                )
            else:
                self._finish_wound_roll(
                    wounds, crits, no_effect, weapon, target_squad, target_profile, weapon_label, wound_threshold,
                    rerollable, ones=ones,
                )

        elif self.pending_step == "wound_reroll_ones":
            ctx = self._pending_ones_reroll
            self._pending_ones_reroll = None
            results = [_resolve_roll(r, ctx["threshold"], ctx["crit_threshold"]) for r in rolls]
            extra_wounds = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            extra_no_effect = len(rolls) - extra_wounds
            self._log(
                f"{ctx['weapon_label']}: {ctx.get('reason', 'Forward Observers')} re-roll of 1s {rolls} -> "
                f"{extra_wounds} additional wound(s) (of which {extra_crits} critical)."
            )
            # The dice just thrown are spent, so the extra wounds/failures
            # they produced count towards the RESULT but never towards what
            # [TWIN-LINKED]/Breach and Clear may still re-roll - ctx's
            # rerollable pool is carried through untouched.
            self._finish_wound_roll(
                ctx["wounds"] + extra_wounds, ctx["crits"] + extra_crits,
                (ctx["no_effect"] - ctx["ones"]) + extra_no_effect,
                ctx["weapon"], ctx["target_squad"], ctx["target_profile"], ctx["weapon_label"], ctx["threshold"],
                ctx["rerollable"],
            )

        elif self.pending_step == "wound_twin_linked_reroll":
            # Rule 24.38 ([TWIN-LINKED]) re-rolls the FAILED dice only (user
            # correction: "es sollten nur fails sein"); Breach and Clear
            # re-rolls the whole Wound roll and discards the old result (user:
            # "vollständig rerollen"). Which one this was is decided by
            # _offer_twin_linked_choice() - see _wound_reroll_is_full() - and
            # arrives here purely as "how many wounds/crits are carried over",
            # so this branch needs no branching of its own beyond the wording.
            ctx = self._pending_twin_linked_reroll
            self._pending_twin_linked_reroll = None
            crit_threshold = _wound_crit_threshold(ctx["weapon"], ctx["target_squad"])
            results = [_resolve_roll(r, ctx["wound_threshold"], crit_threshold) for r in rolls]
            extra_wounds = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            if ctx.get("full"):
                self._log(
                    f"{ctx['weapon_label']}: re-rolled the whole Wound roll {rolls} ({ctx['reason']}) -> "
                    f"{extra_wounds} wound(s) (of which {extra_crits} critical); the previous roll is discarded."
                )
            else:
                self._log(
                    f"{ctx['weapon_label']}: re-rolled failed wounds {rolls} ({ctx['reason']}) -> "
                    f"{extra_wounds} additional wound(s) (of which {extra_crits} critical)."
                )
            self._resolve_wounds(
                ctx["weapon"], ctx["target_squad"], ctx["target_profile"], ctx["weapon_label"],
                ctx["wounds"] + extra_wounds, ctx["crits"] + extra_crits,
            )

        elif self.pending_step == "save":
            self._continue_after_save(rolls, weapon, target_squad, weapon_label, group)

        elif self.pending_step == "save_crit_ap":
            # Cadre Fireblade's own "Crack Shot" ability's own Save roll (see
            # _begin_crit_ap_save()) - `weapon` here is the same Bonded
            # Heroes/Starscythe/Drive-by Dakka-adjusted value computed above
            # from the group's raw representative weapon, but
            # crit_ap.adjusted_weapon() sets its AP from the live source,
            # so those adjustments make no difference to the outcome.
            crit_ap_weapon = crit_ap.adjusted_weapon(
                weapon, group["pairs"][0][0], self.active_squad)
            self._continue_after_save(rolls, crit_ap_weapon, target_squad, weapon_label, group)

        elif self.pending_step == "allocate":
            # The dice roll just acknowledged belongs to DamageAllocationSession
            # itself, not a new hit/wound/save roll - either its dice-notation
            # Damage roll (rule: a printed "D6" etc., see WeaponProfile.
            # damage_notation) or (rule 24.12) Feel No Pain's own extra step,
            # whichever is actually pending right now.
            if self.damage_session is not None:
                if self.damage_session.pending_damage_roll is not None:
                    self.damage_session.on_damage_roll_acknowledged()
                else:
                    self.damage_session.on_fnp_acknowledged()
                self._check_allocation_done()

        elif self.pending_step == "devastating":
            if self.devastating_wound_session is not None:
                self.devastating_wound_session.on_fnp_acknowledged()
                self._check_devastating_wounds_done()

    def _crit_note(self, kind, weapon, target_squad):
        """dice_manager.roll() kwargs that let the panel mark the critical
        dice of THIS roll with what they actually buy.

        Presentation only - the engine re-derives all of this from the weapon
        when it resolves the roll (see _resolve_roll()/_wound_crit_threshold()
        and _finish_hit_roll()). What it needs from here is that the answer
        exists at ROLL time, which the panel does not otherwise have: the
        keywords are mostly CONDITIONAL grants, so `weapon` has to be the
        already-adjusted profile from _adjusted_weapon(), not the printed one.

        [SUSTAINED HITS] is reported without its X: the number is on the roll's
        own heading already, and a die is 50px wide."""
        if kind == "hit":
            model = self.current_group["pairs"][0][0] if self.current_group else None
            threshold = crit_hit_threshold(model, target_squad, self.whispering_web,
                                           weapon=weapon)
            labels = []
            if weapon.lethal_hits:
                labels.append("LETHAL HIT")
            if weapon.sustained_hits or weapon.sustained_hits_notation is not None:
                labels.append("SUSTAINED HIT")
        else:
            threshold = _wound_crit_threshold(weapon, target_squad)
            labels = ["DEVASTATING WOUND"] if weapon.devastating_wounds else []
        return {"crit_threshold": threshold, "crit_labels": tuple(labels)}

    def _adjusted_weapon(self, pairs, target_squad):
        """This weapon group's profile with every conditional grant applied,
        in one place.

        Retaliation Cadre (Bonded Heroes): a no-op copy unless the group's
        representative shooter is a BATTLESUIT model within range - see
        bonded_heroes_adjusted_weapon()'s docstring. Applied once so it flows
        through every downstream use (wound threshold, and - chained via
        melta_adjusted_weapon() - damage), matching how [MELTA X] itself is
        only ever applied at its own point of use rather than mutating the
        shared weapon. Starscythe and Drive-by Dakka chain right after it for
        the same reason - all three only ever touch AP/Strength, never
        Damage, so ordering between them does not matter.

        The ones after that DO matter: Arro'kon, Bladestorm, Exemplars of
        Mont'ka ([SUSTAINED HITS]), Nova Charge, Hand of Asuryan
        ([DEVASTATING WOUNDS]) and Ammo Runt ([LETHAL HITS]) all grant
        keywords the hit/wound steps read straight off the returned weapon,
        so they have to be in place before those steps run.

        Nova Charge takes `pairs` rather than the already-copied weapon to
        identify the group's weapon, because each copy() above gives the
        profile a new id() and that grant is keyed by instance identity; see
        game/nova_charge.py.

        Extracted because there are now THREE callers that need the same
        answer and must not disagree: the [TORRENT] shortcut (which skips
        straight to _handle_hit_results without ever reaching the hit step),
        on_dice_acknowledged()'s own resolution, and _crit_note(), which has
        to know at ROLL time whether a critical die will end up being a
        [LETHAL HITS]/[SUSTAINED HITS]/[DEVASTATING WOUNDS] one - the grants
        are what decide that, and they are all conditional."""
        weapon = bonded_heroes_adjusted_weapon(pairs[0][1], pairs, target_squad)
        # The Anhrathe grants, all keyword or characteristic changes that the
        # hit/wound steps read off the returned weapon:
        #   Piratical Hero      [SUSTAINED HITS 1] while Prince Yriel leads
        #   Faolchu             [IGNORES COVER] on the bearer's unit (ranged only)
        #   Piratical Raiders   [LETHAL HITS] + [PRECISION] vs the marked unit
        #   Fury of the Void    +1 STRENGTH vs a riven unit - a characteristic,
        #                       not a modifier, so it must reach the weapon
        #                       BEFORE the wound threshold is computed
        weapon = corsair_abilities.piratical_hero_adjusted_weapon(weapon, self.active_squad)
        weapon = corsair_abilities.faolchu_adjusted_weapon(weapon, self.active_squad)
        if self.piratical_raiders is not None:
            weapon = self.piratical_raiders.adjusted_weapon(
                weapon, self.active_squad, target_squad)
        if self.fury_of_the_void is not None:
            weapon = self.fury_of_the_void.adjusted_weapon(
                weapon, self.active_squad, target_squad)
        # The Leystalker's Long Rifle prints [DEVASTATING WOUNDS] restricted to
        # non-MONSTER/VEHICLE targets. Applied here rather than as a flat flag,
        # because both the wound step and _crit_note() read it off the weapon
        # this chain returns - see game/conditional_devastating_wounds.py.
        weapon = conditional_devastating_wounds.adjusted_weapon(weapon, target_squad)
        # The Spiritseer's Spirit Mark: [SUSTAINED HITS 1] on the marked
        # FRIENDLY unit's weapons, but only against the marked ENEMY unit -
        # the pair is the rule, and granting it to the friendly unit alone
        # would be a strictly larger ability. In the adjuster chain rather
        # than at the wound step because _crit_note() has to know at ROLL
        # time whether a critical die is a [SUSTAINED HITS] one.
        if self.spirit_mark is not None:
            weapon = spiritseer.spirit_mark_adjusted_weapon(
                weapon, self.spirit_mark, self.active_squad, target_squad)
        # The Vibro Cannon Platform's Sonic Destruction: +1 to S, AP AND D for
        # each OTHER friendly platform that already fired its vibro cannon at
        # this same target this phase. Here rather than at the wound step
        # because the save roll reads this weapon's AP and the damage step
        # reads its Damage - only the adjuster chain delivers all three at
        # once. The ledger it counts is fed at _begin_resolution(), which is
        # the moment target AND weapon are both first known.
        if self.sonic_destruction is not None:
            weapon = self.sonic_destruction.adjusted_weapon(
                weapon, pairs[0][0] if pairs else None, target_squad,
                reactive=self._reactive)
        # Kauyon's Patient Hunter and Mont'ka's Killing Blow - the two T'au
        # detachments whose rule is a battle-round window plus an army-wide
        # keyword grant. Both are here rather than at the wound step because
        # _crit_note() has to know at ROLL time whether a critical die is a
        # [SUSTAINED HITS] or [LETHAL HITS] one. Mutually exclusive in practice
        # (a player has one detachment), but each gates on its own config
        # setting rather than on the other being absent.
        # The T'au detachment Stratagems that adjust a weapon. Experimental
        # Ammunition and Experimental Modifications only touch S/AP, so their
        # place in the chain is free; Guided Fire grants [LETHAL HITS] and so
        # MUST be here rather than at the wound step, because _crit_note()
        # reads the keyword at ROLL time.
        weapon = epc_experimental_ammunition.adjusted_weapon(weapon, self.active_squad)
        weapon = aux_experimental_modifications.adjusted_weapon(weapon, self.active_squad)
        weapon = aux_guided_fire.adjusted_weapon(
            weapon, self.active_squad, target_squad, self._all_squads_for_auras())
        weapon = kauyon.adjusted_weapon(weapon, self.active_squad, self.turn_tracker)
        # Kauyon's Point-Blank Ambush: +1 AP against a target within 9", so
        # it needs the pairs (to measure from the shooters) and the target.
        weapon = kauyon_point_blank_ambush.adjusted_weapon(
            weapon, self.active_squad, pairs, target_squad)
        # Mont'ka's Focused Fire: +1 AP against the one enemy the unit was
        # locked onto. Same mark as the targeting restriction below, so the
        # bonus and its cost cannot come apart.
        weapon = montka_focused_fire.adjusted_weapon(
            weapon, self.active_squad, target_squad)
        weapon = montka.adjusted_weapon(
            weapon, self.active_squad, self.turn_tracker,
            target_squad=target_squad, greater_good=self.greater_good)
        # Through Unity, Devastation (Kauyon) and Coordinated Exploitation
        # (Mont'ka) - the two Enhancements that turn one Observer action into a
        # phase-long [LETHAL HITS]/[SUSTAINED HITS 1] on every Guided attack.
        # Here rather than at the wound step for the same reason their
        # detachment rules are: _crit_note() reads both keywords at ROLL time.
        weapon = enh_guided_keyword_grants.adjusted_weapon(
            weapon, self.active_squad, target_squad, self.greater_good)
        # Retaliation Cadre's Prototype Weapon System: the keyword the bearer
        # chose when this activation started, on THE BEARER's weapons only -
        # hence the model, not the squad. pairs[0] is exact because the choice
        # is part of _attack_key().
        weapon = enh_prototype_weapon_system.adjusted_weapon(weapon, pairs[0][0])
        # War Walkers' Crystalline Targeting: "improve the Armour Penetration
        # characteristic of that attack by 1" against a unit they marked. Like
        # Bonded Heroes above it only ever touches AP, so its position among
        # the AP/Strength adjusters does not matter - but it MUST be in the
        # chain rather than at the wound step, because the Save roll reads AP
        # off this same returned weapon.
        weapon = crystalline_targeting.adjusted_weapon(
            weapon, self.crystalline_targeting, self.active_squad, target_squad)
        weapon = starscythe_adjusted_weapon(weapon, pairs, target_squad)
        weapon = drive_by_dakka_adjusted_weapon(weapon, pairs, target_squad)
        weapon = arrokon_adjusted_weapon(weapon, pairs, target_squad)
        weapon = bladestorm_adjusted_weapon(weapon, pairs, target_squad)
        # Blitzing Firepower is Bladestorm with a fixed 12" instead of half
        # range, so it sits directly beside it and takes the same shape.
        weapon = warhost_blitzing_firepower.adjusted_weapon(weapon, pairs, target_squad)
        weapon = nova_charge_adjusted_weapon(weapon, pairs)
        weapon = hand_of_asuryan_adjusted_weapon(weapon, pairs)
        weapon = psychic_communion.psychic_communion_adjusted_weapon(weapon, pairs)
        weapon = ammo_runt_adjusted_weapon(weapon, self.active_squad)
        # Kroot Farstalkers' Pech'ra: [IGNORES COVER] on the whole unit's
        # ranged weapons, unconditionally once taken - the simplest grant
        # in this chain, and ranged-only by its own printed wording.
        weapon = bounty_hunters_module.pechra_adjusted_weapon(weapon, self.active_squad)
        # The Vespid Strain Leader's Oversight Drone: the same keyword, but
        # spent once per battle and lasting only the phase.
        weapon = oversight_drone_module.adjusted_weapon(weapon, self.active_squad)
        # Kroot Farstalkers' Bounty Hunters: [LETHAL HITS] and [PRECISION]
        # against the one enemy unit chosen at the start of the battle. In
        # the chain rather than at the wound step because _crit_note() must
        # know at ROLL time that a critical die is a [LETHAL HITS] one.
        if self.bounty_hunters is not None:
            weapon = self.bounty_hunters.adjusted_weapon(
                weapon, self.active_squad, target_squad)
        # Doomsday Ark's Overwhelming Obliteration: [DEVASTATING WOUNDS] on
        # its doomsday cannon alone, until the end of a turn it Remained
        # Stationary in. Weapon-specific, unlike every other grant here.
        weapon = overwhelming_obliteration.adjusted_weapon(weapon, self.active_squad)
        # Illuminor Szeras's Mechanical Augmentation - BOTH halves of the
        # aura in one call, so an augmented unit shooting another one nets
        # out to no change, which is what the printed text says.
        weapon = mechanical_augmentation.adjusted_weapon(
            weapon, self.active_squad, target_squad, self.all_tokens)
        # Awakened Dynasty's Protocol of the Sudden Storm: [ASSAULT] on ranged
        # weapons until the end of the turn.
        weapon = protocol_sudden_storm.adjusted_weapon(weapon, self.active_squad)
        # Armoured Warhost's Skilled Crews: the same keyword granted to a
        # whole faction's vehicles for the whole battle. Beside its
        # Necron twin because they do the same thing to the same field.
        weapon = skilled_crews.adjusted_weapon(weapon, self.active_squad)
        # Guardian Battlehost's Blades of Asuryan: [PISTOL] on this unit's
        # ranged weapons for the phase. In the chain, like every keyword
        # grant, because _crit_note() reads the returned weapon at roll time.
        weapon = guardian_blades_of_asuryan.adjusted_weapon(weapon, self.active_squad)
        # Focused Firepower improves this unit's AP by 1 for the phase. In
        # the chain because the Save roll reads the AP off the weapon this
        # returns - anywhere else and the change never reaches the roll.
        weapon = windrider_focused_firepower.adjusted_weapon(weapon, self.active_squad)
        # Seer's Eye runs LAST: it undoes every WORSENING modifier to AP and
        # Damage by comparing this chain's own output against the printed
        # class, so anything added above is inside what it can ignore.
        weapon = aspect_doom_inescapable.adjusted_weapon(weapon, self.active_squad)
        weapon = aspect_preternatural_precision.adjusted_weapon(
            weapon, self.active_squad)
        weapon = conclave_seers_eye.adjusted_weapon(
            weapon, self.active_squad, target_squad)
        # Warrior Focus runs LAST for the same reason Seer's Eye does: it
        # undoes worsening S/AP/Damage modifiers by comparing this chain's own
        # output against the printed class, so everything above is inside what
        # it can ignore.
        weapon = enh_assassins_eye.adjusted_weapon(
            weapon, self.active_squad, target_squad)
        # Seersight Strike's [ANTI-X] and Psychic Destroyer's +1 Damage, both
        # per BEARER - hence the attack-key terms beside them.
        weapon = enh_psychic_weapons.adjusted_weapon(weapon, pairs[0][0] if pairs else None)
        weapon = aspect_warrior_focus.adjusted_weapon(weapon, self.active_squad)
        # Death Lord's Chosen's Mortarion's Teachings: [ASSAULT] AND [HEAVY] on
        # ranged weapons, until the end of the PHASE (Sudden Storm above grants
        # only [ASSAULT], and until the end of the TURN).
        weapon = dlc_mortarions_teachings.adjusted_weapon(weapon, self.active_squad)
        # The Malignant Plaguecaster's Gift of Contagion: [SUSTAINED HITS 1]
        # while he leads this unit AND the target is Afflicted. Its text says
        # "an attack", not "a ranged attack", so game/fight.py reads the same
        # module - and it is in the chain, not the wound step, because
        # _crit_note() reads the keyword off the returned weapon at ROLL time.
        weapon = gift_of_contagion.adjusted_weapon(weapon, self.active_squad, target_squad)
        # Exemplars of Mont'ka's "is it the closest eligible target" answer
        # comes from the target-selection snapshot, never recomputed here -
        # see game/exemplars_of_montka.py.
        return exemplars_of_montka.montka_adjusted_weapon(
            weapon, pairs, self._closest_target_snapshot.get(target_squad, False),
        )

    def squads_hit_by_weapon(self, weapon_name):
        """Which enemy units this activation hit with a weapon of that printed
        name - what Shroud Runners' Target Acquisition needs on top of the
        plain "which units were hit" the listener hook already carries."""
        return [s for s in self._hit_target_squads_this_activation
                if weapon_name in self._hit_weapon_names_this_activation.get(id(s), ())]

    def models_lost_this_activation(self, target_squad):
        """How many models `target_squad` has lost since this activation first
        hit it.

        Zero for a unit this activation never hit, which is the honest answer:
        the question is only ever asked about a unit that WAS hit."""
        before = self._living_when_first_hit.get(id(target_squad))
        if before is None:
            return 0
        return max(0, before - _living_count(target_squad))

    def _handle_hit_results(self, hits, crits, weapon, target_squad, weapon_label):
        """Shared continuation after the hit count is known - whether from
        an actual hit roll or (rule 24.37, [TORRENT]) with no roll at all."""
        if hits > 0:
            # Suppression Volley (user-supplied Strike Team ability, see
            # game/suppression.py): "select one enemy INFANTRY unit hit by
            # one or more of those attacks" - tracked here, the one place
            # that already knows a target_squad was actually hit (as
            # opposed to just targeted), regardless of shooting type/weapon.
            self._hit_target_squads_this_activation.add(target_squad)
            # How many models that unit still had when it was FIRST hit this
            # activation. Path of the Outcast's Eldritch Suppression asks "was
            # a model in that enemy unit destroyed BY THOSE ATTACKS", and there
            # is no other way to answer it afterwards: remove_dead_models()
            # runs once per frame, so at the end of the activation a corpse may
            # be from this activation or from the last one. Recorded once, on
            # the first hit, beside the hit itself.
            self._living_when_first_hit.setdefault(
                id(target_squad), _living_count(target_squad))
            self._hit_weapon_names_this_activation.setdefault(
                id(target_squad), set()).add(weapon.name)
            # The Kroot Lone-Spear's Advanced Scouting: "each time this model
            # makes a ranged attack THAT HITS an enemy unit". Same reason this
            # lives here as Suppression Volley one line up - this is the one
            # place that knows a target was actually hit rather than merely
            # targeted. The controller ignores the call unless the shooter
            # really has the ability, so it is made unconditionally.
            if self.advanced_scouting is not None:
                self.advanced_scouting.record_hit(self.active_squad, target_squad)
            # Rule 19.04's trailing clause: if the last model of a component
            # of an attached unit is destroyed by an attack, the ability it
            # was conferring "applies until the attacking unit has resolved
            # all of its attacks". Open that window here - the first point
            # this activation is known to have hit this target, and still
            # before any damage is allocated - and close it in
            # _actually_finish_squad(), which is already this file's
            # canonical "the unit has resolved all of its attacks" moment
            # (rule 24.15 [HAZARDOUS] uses the very same point).
            attached_units.begin_attack_sequence(target_squad)
            # Rule 24.23 ([LETHAL HITS]): "you CAN choose for that attack to
            # automatically wound" - taken for every critical hit, without
            # asking. This used to be a DecisionManager prompt offering
            # 0..crits, on the strength of the Designer's Note (an auto-wound
            # is never itself a critical wound, so it cannot trigger
            # [DEVASTATING WOUNDS], which makes declining meaningful on a
            # weapon carrying both). User: "bei lethal hits kommt gerade ein
            # seltsames overlay... das koennen wir uns sparen. es sollen
            # einfach alle kritischen treffer automatisch verwunden." The
            # trade is real but small and was interrupting every single
            # activation of such a weapon; see CLAUDE.md.
            self._continue_after_hit_roll(
                hits, crits if weapon.lethal_hits else 0, weapon, target_squad, weapon_label,
            )
        else:
            self._finish_group()

    def _effective_strength(self, weapon):
        """The Strength this group's attacks actually resolve with.

        Normally the weapon's printed value. For a weapon whose Strength is
        itself a die roll (`strength_notation`, e.g. the Zzap gun's printed
        "D6+6"), the value rolled for THIS weapon group - see
        _begin_strength_roll(). The printed `strength` on such a weapon is
        only a preview/grouping placeholder, never what an attack uses.

        Rolled once per weapon group rather than once per attack. Exact for
        every such weapon that exists here (the Zzap gun is A1, so the two
        coincide); for a hypothetical multi-attack dice-Strength weapon it
        would be an approximation, and a documented one - this engine's
        wound roll is batched against a single threshold, so it has no way
        to express several Strengths at once."""
        if self._rolled_strength is not None:
            return self._rolled_strength
        return weapon.strength

    def _begin_strength_roll(self, hits, auto_wounds, weapon, target_squad, weapon_label):
        """Starts the visible roll for a dice-notation Strength, and stashes
        what the wound step needs to carry on once it resolves."""
        self._pending_strength = {
            "hits": hits, "auto_wounds": auto_wounds, "weapon": weapon,
            "target_squad": target_squad, "weapon_label": weapon_label,
        }
        self._pending_strength_roll = DiceNotationRoll(
            weapon.strength_notation, count=1, dice_manager=self.dice_manager,
            label=f"Strength: {weapon_label} ({describe_dice_notation(weapon.strength_notation)})",
            log=self._log, target_name=target_squad.name,
            attacker_squad=self.active_squad, target_squad=target_squad,
        )
        if self._pending_strength_roll.is_pending:
            self.pending_step = "strength"
            return True
        # No dice_manager (the non-interactive test wrappers): resolved
        # immediately, same convenience path DiceNotationRoll documents.
        self._finish_strength_roll()
        return False

    def _finish_strength_roll(self):
        ctx, self._pending_strength = self._pending_strength, None
        self._rolled_strength = self._pending_strength_roll.total
        self._pending_strength_roll = None
        self._log(
            f"{ctx['weapon_label']}: Strength {self._rolled_strength} "
            f"({describe_dice_notation(ctx['weapon'].strength_notation)})."
        )
        self._continue_after_hit_roll(
            ctx["hits"], ctx["auto_wounds"], ctx["weapon"], ctx["target_squad"], ctx["weapon_label"],
        )

    def _continue_after_hit_roll(self, hits, auto_wounds, weapon, target_squad, weapon_label):
        """Rolls the wound dice for whatever's left after `auto_wounds`
        critical hits were chosen to auto-wound (rule 24.23) - or, if every
        hit was auto-wounded, skips the wound roll entirely and resolves
        straight through (mirroring _resolve_wounds's post-roll handling).

        A weapon with a dice-notation Strength interposes its own visible
        roll first (see _effective_strength()), since the wound threshold
        below cannot be computed until that value exists."""
        if weapon.strength_notation is not None and self._rolled_strength is None:
            if self._begin_strength_roll(hits, auto_wounds, weapon, target_squad, weapon_label):
                return
        self._lethal_hits_auto_wounds = auto_wounds
        remaining = hits - auto_wounds
        if remaining > 0:
            wound_threshold = _wound_threshold(self._effective_strength(weapon), attached_unit_toughness(target_squad))
            # Name the modifiers on the roll, as game/fight.py's identical
            # wound step and this file's own HIT step both already do. Without
            # it a defensive malus (Guardian Drone, 'Ard as Nails) silently
            # made the roll harder with nothing on screen saying why.
            wound_modifiers = self._wound_modifiers(target_squad, self._effective_strength(weapon))
            wound_threshold = apply_modifiers(wound_threshold, wound_modifiers)
            label = f"Wound Roll: {weapon_label} ({remaining} hit(s))"
            if wound_modifiers:
                label += f" [{describe_modifiers(wound_modifiers)}]"
            self.dice_manager.roll(
                count=remaining, sides=6,
                label=label,
                success_threshold=wound_threshold,
                target_name=target_squad.name, attacker_squad=self.active_squad, target_squad=target_squad, roll_kind=WOUND_ROLL,
                **self._crit_note("wound", weapon, target_squad),
            )
            self.pending_step = "wound"
        else:
            target_profile = allocation_target_profile(target_squad)
            self._resolve_wounds(weapon, target_squad, target_profile, weapon_label, wounds=0, crits=0)

    def _resolve_wounds(self, weapon, target_squad, target_profile, weapon_label, wounds, crits):
        """Every path through the wound step funnels through here, so this is
        where an Aspect Shrine token is offered against the roll that stands -
        the wound-step twin of _apply_sustained_hits() above, and for the same
        reason: it must land before criticals are turned into anything."""
        self._resolve_wounds_now(weapon, target_squad, target_profile, weapon_label, wounds, crits)

    def _resolve_wounds_now(self, weapon, target_squad, target_profile, weapon_label, wounds, crits):
        """Shared tail end of wound resolution, reachable either after an
        actual wound roll or (rule 24.23, fully auto-wounded) with no roll
        at all. Rule 24.10 ([DEVASTATING WOUNDS]): critical wounds skip the
        save roll entirely and become mortal wounds instead - resolved after
        any normal damage from the rest of this group's wounds. Auto-wounds
        from [LETHAL HITS] join the normal-wound/save pool (never critical,
        per its Designer's Note). Cadre Fireblade's own "Crack Shot" ability
        (user-supplied, not a core rule): whatever critical wounds are left
        after [DEVASTATING WOUNDS] has taken its own share get pulled out of
        this group's normal Save roll too, and get their own, separate Save
        roll at AP-3 instead - see _begin_crit_ap_save()."""
        self._devastating_crits = crits if weapon.devastating_wounds else 0
        shooter_model = self.current_group["pairs"][0][0] if self.current_group else None
        # Cadre Fireblade's Crack Shot and Seer Council's Fate Inescapable both
        # give a CRITICAL wound its own AP - see game/crit_ap.py, which folds
        # them and is where a third source would go.
        crit_ap_active = crit_ap.applies(weapon, shooter_model, self.active_squad)
        self._pending_crit_ap_crits = (crits - self._devastating_crits) if crit_ap_active else 0
        normal_wounds = (
            wounds - self._devastating_crits - self._pending_crit_ap_crits + self._lethal_hits_auto_wounds
        )
        self._lethal_hits_auto_wounds = 0

        if normal_wounds > 0:
            if self.turn_tracker is not None:
                # Rule 05.03/05.04: save rolls and damage allocation are the
                # *defending* player's decisions, not the attacker's.
                self.turn_tracker.set_active(target_squad.owner)

            # The number a die must REACH, from the same definition
            # game/damage_resolution.py resolves the save with - so a die
            # saved by the INVULNERABLE save (or under Ramshackle's worsened
            # AP) is no longer coloured red and counted as a failure. User
            # report: "oft werden bestandene rettungswuerfe rot angezeigt".
            save_threshold = displayed_save_threshold(
                allocation_target_model(target_squad), weapon, self.waaagh,
            )
            # Melta-adjusted damage preview (rule 24.25) - positions don't
            # change between kicking off this roll and its acknowledgement,
            # so this is the same value _begin_damage_allocation() will use.
            # None (suppresses DicePanel's "N attack(s) get through..."
            # summary line) whenever Damage is dice-notation - there's no
            # single fixed number to preview until DamageAllocationSession
            # actually rolls it per failed save, see its own docstring.
            melta_weapon = melta_adjusted_weapon(weapon, self.current_group["pairs"], target_squad)
            damage_preview = None if melta_weapon.damage_notation is not None else melta_weapon.damage
            if self._skip_impossible_save(target_squad, weapon, save_threshold, normal_wounds):
                # No model of the target can pass this save, so there is no
                # roll to make - see _skip_impossible_save().
                self._continue_after_save(
                    [AUTO_FAILED_SAVE] * normal_wounds, weapon,
                    target_squad, weapon_label, self.current_group)
                return
            self.dice_manager.roll(
                count=normal_wounds, sides=6,
                label=f"Save Roll: {weapon_label} ({normal_wounds} wound(s))",
                success_threshold=save_threshold if save_threshold is not None else 7,
                target_name=target_squad.name, attacker_squad=self.active_squad, target_squad=target_squad, roll_kind=SAVE_ROLL,
                damage_per_failure=damage_preview,
            )
            self.pending_step = "save"
        elif self._devastating_crits > 0:
            self._begin_devastating_wounds(weapon, target_squad)
        elif self._pending_crit_ap_crits > 0:
            self._begin_crit_ap_save()
        else:
            self._finish_group()

    def _hit_reroll_reason(self, target_squad):
        """Which ability, if any, grants a re-roll of THIS group's Hit roll.
        The hit-step twin of _wound_reroll_reason() below, kept as its own
        named lookup for the same reason: the offer only needs to know the
        label, and a second source can be added here without touching the
        step itself.

        Currently one source - Beast Snagga Boyz' Monster Hunters (see
        game/monster_hunters.py). Unlike the wound side it takes no `weapon`
        argument: no hit-roll re-roll here comes from a weapon keyword."""
        # Mont'ka's Pinpoint Counter-Offensive: "you can re-roll the Hit
        # roll" against the unit that destroyed one of yours, for the rest
        # of the battle. "An attack", so game/fight.py reads it too.
        if (self.pinpoint_counter_offensive is not None
                and self.pinpoint_counter_offensive.applies(self.active_squad, target_squad)):
            return montka_pinpoint_counter_offensive.PINPOINT_NAME

        if monster_hunters.applies(self.active_squad, target_squad):
            return monster_hunters.MONSTER_HUNTERS_REROLL_LABEL
        # Firesight Team's Precise Targeting - the first source here whose
        # condition is a MARK on the target rather than a keyword or a
        # distance, and it needs no new state: Spotted is already what the
        # T'au army rule sets. Ordinary failures-or-whole shape, so it is
        # deliberately NOT registered in game/reroll_scope.py.
        if precise_targeting_module.applies(self.active_squad, target_squad, self.greater_good):
            return precise_targeting_module.PRECISE_TARGETING_LABEL
        # The Kroot Lone-Spear's Advanced Scouting - the same mark-on-the-target
        # shape, but the mark was placed by a DIFFERENT unit (his) and is read
        # by every other KROOT unit in the army.
        if self.advanced_scouting is not None \
                and self.advanced_scouting.applies(self.active_squad, target_squad):
            return advanced_scouting_module.ADVANCED_SCOUTING_LABEL
        # Fire Dragons' Assured Destruction - the only other source, and the
        # first that is phase-restricted ("in YOUR Shooting phase"), which is
        # why it is the one that reads the turn tracker.
        if assured_destruction.applies(self.active_squad, target_squad, self.turn_tracker):
            return assured_destruction.ASSURED_DESTRUCTION_LABEL
        # Windriders' Swift Demise, and the ONLY one of the three that is
        # conditional on which target was picked: its whole-roll half is
        # available against the closest eligible target alone. Against any
        # other target the ability still applies, but only as the automatic
        # re-roll of 1s, which is not an offer and so is not a "reason" here.
        # The cheap flag test comes FIRST on purpose: _eligible_target_squads()
        # below runs a line-of-sight sweep, and this lookup is reached on every
        # hit roll in the game.
        # Awakened Dynasty's Protocol of the Conquering Tyrant - the same
        # two-clause shape, and the only one whose condition is a DISTANCE
        # (half range), so it needs the measured gap rather than a keyword.
        pairs = self.current_group.get("pairs") if self.current_group else None
        tyrant_weapon = pairs[0][1] if pairs else None
        if protocol_conquering_tyrant.offers_full_reroll(
                self.active_squad, tyrant_weapon, pairs, target_squad):
            return protocol_conquering_tyrant.CONQUERING_TYRANT_LABEL
        # Lokhust Destroyers' Hard-wired for Destruction: same two-clause
        # shape as Swift Demise below, so it is only a "reason" when its
        # WHOLE-roll half is available - the base clause is the automatic 1s.
        if destroyer_cult.hard_wired_offers_full_reroll(
                self.active_squad, target_squad, self._eligible_target_squads(), self.objectives):
            return destroyer_cult.HARD_WIRED_LABEL
        # Crisis Fireknife Battlesuits' Fireknife - the same two-clause
        # shape, and the condition is the TARGET's Starting Strength.
        if fireknife.offers_full_reroll(self.active_squad, target_squad):
            return fireknife.FIREKNIFE_LABEL
        # The Sky Ray's Velocity Tracker - an ordinary "you can re-roll the
        # Hit roll", so deliberately NOT a reroll_scope source.
        if velocity_tracker_module.applies(self.active_squad, target_squad):
            return velocity_tracker_module.VELOCITY_TRACKER_LABEL
        # The Lokhust Lord's Driven by Hatred. Deliberately NOT one of the
        # ones-or-whole sources above it: its text is the ordinary "you can
        # re-roll the Hit roll", with no automatic-1s clause to be an
        # alternative to. It is also the only source here that is per MODEL,
        # hence the group form of the predicate.
        if destroyer_cult.driven_by_hatred_applies_to_group(pairs, target_squad):
            return destroyer_cult.DRIVEN_BY_HATRED_LABEL
        # Corsair Voidreavers' Reavers of the Void. Like Fireknife it is a
        # two-clause source, so it is a "reason" only while its WHOLE-roll
        # half is live - i.e. while the target stands on an objective. The
        # base clause is the automatic 1s below, which apply regardless.
        if reavers_of_the_void.offers_full_reroll(
                self.active_squad, target_squad, self.objectives):
            return reavers_of_the_void.REAVERS_OF_THE_VOID_LABEL
        # The Wraithlord's Fated Hero: "re-roll a Hit roll of 1 AND re-roll a
        # Wound roll of 1" against a unit with the keyword it chose at the
        # start of the battle. Both rolls, so it appears at FOUR sites - the
        # hit and wound reasons in this file and in the other attack step.
        # Per MODEL, like Driven by Hatred above it, hence the group form.
        if (self.fated_hero is not None
                and self.fated_hero.applies_to_group(pairs, target_squad)):
            return fated_hero_module.FATED_HERO_LABEL
        if swift_demise.applies(self.active_squad) and swift_demise.is_closest_target(
                self.active_squad, target_squad, self._eligible_target_squads()):
            return swift_demise.SWIFT_DEMISE_LABEL
        return None

    def _eligible_target_squads(self):
        """The enemy units this unit could legally shoot at - rule 10.02's own
        "eligible target", answered by the same _is_valid_target_squad() the
        targeting step uses rather than a second opinion.

        Deduplicated per SQUAD rather than per token, like valid_target_models()
        and for the same reason: a ten-model unit would otherwise be tested ten
        times. Only used to decide which candidate is the CLOSEST (Swift
        Demise), so an empty list degrades safely - the unit actually shot at
        is then the closest by default."""
        if self.active_squad is None or not self.all_tokens:
            return []
        seen, out = set(), []
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            if squad is None or squad.owner == self.active_squad.owner or id(squad) in seen:
                continue
            seen.add(id(squad))
            if self._is_valid_target_squad(squad, self.all_tokens):
                out.append(squad)
        return out

    def _hit_reroll_choice_needed(self, target_squad, free_count):
        """Pointless to offer with no re-rollable dice left, and offered only
        once per weapon group's attack sequence (_hit_reroll_used, reset per
        group in _begin_resolution) - "each time a model makes an attack"
        means each attack SEQUENCE gets its own chance, exactly as
        _twin_linked_choice_needed() reads the same phrasing on the wound
        side.

        Note what is NOT required here, unlike the wound side: a failure.
        This is a re-roll of the WHOLE roll (see _offer_hit_reroll_choice()),
        so it is a legal - if rarely wise - choice even with every die a hit,
        and the prompt lets the player see that and decline."""
        if self.decision_manager is None or self._hit_reroll_used:
            return False
        return free_count > 0 and self._hit_reroll_reason(target_squad) is not None

    def _offer_hit_reroll_choice(self, hits, crits, weapon, target_squad, weapon_label, hit_threshold, rerollable, owner, ones=0):
        """BOTH scopes are offered as real choices, per explicit user
        instruction ("man muss die entscheidung haben entweder nur fails zu
        rerollen, oder alles zu rerollen"):

          * failures only - keeps every hit already rolled, and is therefore
            never a loss; the safe option.
          * the whole roll - discards the current result, which can lose
            hits, but is the only way to improve on a roll whose failures
            are few and whose hits are non-critical.

        Neither is strictly better, which is exactly why the player picks
        rather than the engine. This differs from the wound side, where each
        source is fixed to one scope by its own explicit ruling (see
        _wound_reroll_is_full()) - Monster Hunters is the first re-roll here
        offered as a genuine two-way choice.

        Only the still-free share of the roll may be thrown either way -
        dice that already used their one re-roll keep what they landed on,
        so the hits among THEM are carried over even by the "discard
        everything" option."""
        reason = self._hit_reroll_reason(target_squad)
        free_hits, free_crits, free_count = rerollable
        free_misses = free_count - free_hits
        kept_hits, kept_crits = hits - free_hits, crits - free_crits
        # Swift Demise grants only TWO scopes, and "failed hits" is not one of
        # them: its entitlement is the 1s, or - against the closest eligible
        # target - the whole roll. Offering "failures only" there would let a
        # Windrider re-roll a 2 that missed, which the printed text does not
        # allow. Every other source keeps all three.
        swift = reroll_scope.is_ones_or_whole(reason)
        options = []
        if free_misses > 0 and not swift:
            options.append((
                f"Re-roll failed hit rolls ({free_misses} dice)",
                lambda: self._reroll_hit(
                    free_misses, hits, crits, weapon, target_squad, weapon_label, hit_threshold, reason,
                ),
            ))
        options.append((
            f"Re-roll the whole Hit roll ({free_count} dice)",
            lambda: self._reroll_hit(
                free_count, kept_hits, kept_crits, weapon, target_squad, weapon_label, hit_threshold, reason,
                full=True,
            ),
        ))
        # ...and its two halves are ALTERNATIVES rather than a free choice on
        # top of nothing: the re-roll of 1s is MANDATORY, so with 1s on the
        # table "keep result" is not a legal answer - the player picks which of
        # the two re-rolls to take. With no 1s there is nothing mandatory left
        # and it behaves like the others.
        if swift and ones > 0:
            options.append((
                f"Re-roll the 1s only ({ones} dice)",
                lambda: self._begin_ones_reroll(
                    "hit", ones, hit_threshold, weapon, target_squad, weapon_label,
                    hits=hits, crits=crits, reason=reason,
                    rerollable=(free_hits, free_crits, free_count - ones),
                ),
            ))
        else:
            options.append(
                ("Keep result", lambda: self._apply_sustained_hits(hits, crits, weapon, target_squad, weapon_label))
            )
        self.decision_manager.request(owner, f"{weapon_label}: {reason} - re-roll the Hit roll?", options)

    def _reroll_hit(self, count, hits, crits, weapon, target_squad, weapon_label, hit_threshold, reason, full=False):
        """`count` dice are thrown again; `hits`/`crits` are only whatever
        the caller still carries over (see _offer_hit_reroll_choice()) and
        are stashed for on_dice_acknowledged()'s
        "hit_monster_hunters_reroll" branch to add back in.

        Failures-only: count == the failed dice, and the hits already rolled
        carry over. Whole roll: count == everything still re-rollable and
        only the dice held back from this throw carry over. `full` just
        labels it - the arithmetic is entirely in what the caller passes."""
        self._hit_reroll_used = True
        self._pending_hit_reroll = {
            "hits": hits, "crits": crits, "weapon": weapon, "target_squad": target_squad,
            "weapon_label": weapon_label, "hit_threshold": hit_threshold, "reason": reason, "full": full,
        }
        scope = f"re-rolling all {count}" if full else f"re-rolling {count} failed"
        self.dice_manager.roll(
            count=count, sides=6, label=f"Hit Roll ({scope}): {weapon_label} {reason}",
            success_threshold=hit_threshold, target_name=target_squad.name, attacker_squad=self.active_squad, target_squad=target_squad, roll_kind=HIT_ROLL,
            is_reroll=True,  # these dice have now used their one re-roll
            **self._crit_note("hit", weapon, target_squad),
        )
        self.pending_step = "hit_monster_hunters_reroll"

    def _wound_reroll_reason(self, weapon, target_squad):
        """Rule 24.38 ([TWIN-LINKED]) and Breacher Team's "Breach and Clear"
        ability (user-supplied, not a core rule) both grant a wound-roll
        re-roll for a group's attack sequence - checked together since they
        produce the exact same effect, only the DecisionManager prompt's
        label needs to know which one actually applies right now. None if
        neither does. Breach and Clear uses is_on_objective() (the target
        must actually be standing on the objective's terrain footprint),
        not the looser 3" is_within_range_of_objective() - see its own
        docstring for the user correction behind that distinction."""
        # Mont'ka's Combat Debarkation: "re-roll the Wound roll" against
        # THE CLOSEST enemy unit. Closest is asked of
        # game/exemplars_of_montka.py, which already settled that it is
        # measured edge to edge and fixed at target selection (10.02).
        if montka_combat_debarkation.is_active(self.active_squad):
            closest = exemplars_of_montka.closest_eligible_target(
                self.active_squad, self._eligible_target_squads())
            if montka_combat_debarkation.applies(self.active_squad, target_squad, closest):
                return montka_combat_debarkation.COMBAT_DEBARKATION_NAME

        if weapon.twin_linked:
            return "[TWIN-LINKED]"
        if squad_has_breach_and_clear(self.active_squad) and is_on_objective(target_squad, self.objectives):
            return "Breach and Clear"
        # Crisis Sunforge Battlesuits' Sunforge ability: "you can re-roll the
        # Wound roll" against a MONSTER or VEHICLE target. Listed last, so a
        # weapon that is ALSO [TWIN-LINKED] keeps that label and its
        # failures-only scope - the stricter of the two, and the one that
        # cannot lose an already-rolled success (same precedence reasoning
        # already documented for Breach and Clear).
        if sunforge.applies(self.active_squad, target_squad):
            return sunforge.SUNFORGE_REROLL_LABEL
        # Fire Dragons' Assured Destruction: the same MONSTER/VEHICLE
        # condition and the same "you can re-roll the Wound roll" wording as
        # Sunforge, plus its own Shooting-phase clause.
        if assured_destruction.applies(self.active_squad, target_squad, self.turn_tracker):
            return assured_destruction.ASSURED_DESTRUCTION_LABEL
        # The Falcon's Fire Support: the marked target, for a unit that rode
        # in that Falcon this turn. Same "you can re-roll the Wound roll"
        # wording, so the same whole-roll scope.
        if self.fire_support is not None and self.fire_support.applies(self.active_squad, target_squad):
            return FIRE_SUPPORT_LABEL
        # Jain Zar's Storm of Silence - the only source here keyed on the
        # attacking MODEL rather than its unit, because the rule says "each
        # time THIS MODEL makes an attack".
        pairs = self.current_group.get("pairs") if self.current_group else None
        if storm_of_silence.applies(pairs[0][0] if pairs else None, target_squad):
            return storm_of_silence.STORM_OF_SILENCE_LABEL
        # Immortals' Implacable Eradication - a two-clause source like the hit
        # side's Swift Demise, so it is a "reason" only when its WHOLE-roll
        # half is live; the base clause is the automatic re-roll of 1s.
        if implacable_eradication.offers_full_reroll(self.active_squad, target_squad, self.objectives):
            return implacable_eradication.IMPLACABLE_ERADICATION_LABEL
        # The Lokhust Lord's Driven by Hatred covers BOTH rolls, so it appears
        # here as well as in _hit_reroll_reason() - the only source in this
        # engine that does. Per model, like Storm of Silence above.
        if destroyer_cult.driven_by_hatred_applies_to_group(pairs, target_squad):
            return destroyer_cult.DRIVEN_BY_HATRED_LABEL
        # The Wraithlord's Fated Hero: "re-roll a Hit roll of 1 AND re-roll a
        # Wound roll of 1" against a unit with the keyword it chose at the
        # start of the battle. Both rolls, so it appears at FOUR sites - the
        # hit and wound reasons in this file and in the other attack step.
        # Per MODEL, like Driven by Hatred above it, hence the group form.
        if (self.fated_hero is not None
                and self.fated_hero.applies_to_group(pairs, target_squad)):
            return fated_hero_module.FATED_HERO_LABEL
        # Yvraine's Herald of Ynnead: "you CAN re-roll a Wound roll of 1"
        # against the unit she marked at the start of the Fight phase, for
        # every AELDARI unit in her army rather than just her own. Resolved
        # automatically like Fated Hero above: a bare optional re-roll of 1s
        # has no downside - a 1 always fails - so a prompt would have exactly
        # one right answer (error class 5). NOT a game/reroll_scope.py entry;
        # the printed text has no "instead", so the ones-or-whole offer does
        # not apply and offering "failures only" would re-roll 2s it never
        # allows.
        if (self.herald_of_ynnead is not None
                and self.herald_of_ynnead.grants(self.active_squad, target_squad)):
            return ynnari_abilities.HERALD_OF_YNNEAD_LABEL
        # Guardian Battlehost's Warding Salvoes: the condition is on the
        # TARGET, so it is asked per attack rather than at purchase - the
        # same shape Reavers of the Void and Implacable Eradication have.
        if guardian_warding_salvoes.offers_reroll(self.active_squad, target_squad, self.objectives):
            return guardian_warding_salvoes.WARDING_SALVOES_NAME
        # Death from on High: "you can re-roll the Wound roll" - the WHOLE
        # roll, and its WHEN names both this phase and the other one, so it is
        # read from both chains.
        if windrider_death_from_on_high.offers_reroll(self.active_squad):
            return windrider_death_from_on_high.DEATH_FROM_ON_HIGH_NAME
        return None

    def _wound_reroll_is_full(self, weapon, target_squad):
        """Whether the re-roll granted right now covers the WHOLE Wound roll
        or only its failed dice.

        Implacable Eradication is a third answer wearing the first one's
        clothes: its upgrade says "you can re-roll the Wound roll instead", so
        it is full - but "instead" makes it an ALTERNATIVE to the automatic 1s
        rather than a superset, which is why _offer_twin_linked_choice() asks
        game/reroll_scope.py rather than reading this alone.

        The two sources this engine has read differently, on purpose:

        [TWIN-LINKED] (24.38) re-rolls only the failures - explicit user
        correction, "reroll wound - nur fails oder alle? es sollten nur fails
        sein".

        Breach and Clear re-rolls the entire roll - equally explicit, and
        about this ability specifically: "breacher können ihre wound rolls
        vollständig rerollen, wenn der gegner auf einem objective steht".
        That is also the literal reading of its own datasheet line ("you can
        re-roll the Wound roll"), and how it was originally built here before
        the [TWIN-LINKED] correction above was applied to both sources at
        once.

        A full re-roll gives up the successes already rolled, so it is not
        automatically the better deal - the offer stays a real choice
        against "Keep result", it just re-rolls a different set of dice.
        Which is why this only decides what the FULL option looks like:
        wherever a full re-roll is on offer, _offer_twin_linked_choice()
        also offers the failures-only subset of it, since "you can re-roll
        the Wound roll" permits re-rolling fewer of its dice than all.
        Where both sources apply at once (a [TWIN-LINKED] weapon in a
        Breacher Team), _wound_reroll_reason()'s own order decides, and it
        names [TWIN-LINKED] first - the failures-only version, i.e. the one
        that cannot lose a wound already rolled.

        Sunforge (Crisis Sunforge Battlesuits) re-rolls the entire roll too,
        on the same literal reading as Breach and Clear - its datasheet line
        is word for word "you can re-roll the Wound roll"."""
        return self._wound_reroll_reason(weapon, target_squad) in (
            "Breach and Clear", sunforge.SUNFORGE_REROLL_LABEL,
            assured_destruction.ASSURED_DESTRUCTION_LABEL, FIRE_SUPPORT_LABEL,
            storm_of_silence.STORM_OF_SILENCE_LABEL,
            # The Lokhust Lord's Driven by Hatred - "you can re-roll the Wound
            # roll", the same wording, so the same whole-roll scope. It is NOT
            # in game/reroll_scope.py: it has no automatic-1s clause for the
            # whole roll to be an alternative TO, so the ordinary
            # failures-or-whole offer is the right one.
            destroyer_cult.DRIVEN_BY_HATRED_LABEL,
        )

    def _twin_linked_choice_needed(self, weapon, no_effect, target_squad):
        """Pointless to offer with zero failures, and only offered once per
        weapon group's attack sequence (_twin_linked_used, reset per group
        in _begin_resolution - "each time an attack is made" means each
        attack SEQUENCE gets its own chance, not the whole squad activation)."""
        reason = self._wound_reroll_reason(weapon, target_squad)
        return reason is not None and no_effect > 0 and self.decision_manager is not None and not self._twin_linked_used

    def _offer_twin_linked_choice(self, no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, owner, rerollable, ones=0):
        """`no_effect` is the number of FAILED wound dice. Which dice a
        re-roll actually covers depends on the source - see
        _wound_reroll_is_full(). For the failures-only sources the `wounds`/
        `crits` already rolled are kept as-is (passed through to
        _reroll_wound() for later combination); for a full re-roll the whole
        roll is thrown again and the previous result is discarded, so
        nothing is carried over.

        Either way only the `rerollable` share of the roll is thrown - dice
        that already used their one re-roll keep whatever they landed on,
        and for the full re-roll that means the wounds among THEM are the
        one thing a "discard the previous result" re-roll still carries
        over."""
        reason = self._wound_reroll_reason(weapon, target_squad)
        free_wounds, free_crits, free_no_effect = rerollable
        keep = ("Keep result", lambda: self._resolve_wounds(weapon, target_squad, target_profile, weapon_label, wounds, crits))
        # A two-clause source (Implacable Eradication) grants the 1s OR the
        # whole roll, never "the failures" - offering that would allow
        # re-rolling a 2 that failed, which the printed text does not permit.
        # And with 1s on the table the base clause is MANDATORY, so "keep
        # result" is not a legal answer: the player picks which re-roll to
        # take. Exactly the arrangement _offer_hit_reroll_choice() already
        # uses; see game/reroll_scope.py.
        if reroll_scope.is_ones_or_whole(reason):
            total = free_wounds + free_no_effect
            kept_wounds, kept_crits = wounds - free_wounds, crits - free_crits
            options = [(
                f"Re-roll the whole Wound roll ({total} dice)",
                lambda: self._reroll_wound(total, kept_wounds, kept_crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, reason, full=True),
            )]
            if ones > 0:
                options.append((
                    f"Re-roll the 1s only ({ones} dice)",
                    lambda: self._begin_ones_reroll(
                        "wound", ones, wound_threshold, weapon, target_squad, weapon_label,
                        wounds=wounds, crits=crits, no_effect=no_effect,
                        crit_threshold=_wound_crit_threshold(weapon, target_squad),
                        target_profile=target_profile, reason=reason,
                        rerollable=(free_wounds, free_crits, free_no_effect - ones),
                    ),
                ))
            else:
                options.append(keep)
            self._twin_linked_used = True
            self.decision_manager.request(
                owner, f"{weapon_label}: {reason} - re-roll the Wound roll?", options)
            return
        if self._wound_reroll_is_full(weapon, target_squad):
            # `crits` is a SUBSET of `wounds` (a critical wound is a wound
            # that also crit - see how both are counted from the same
            # results list), so the roll's own size is wounds + no_effect.
            # Adding crits on top rolled more dice than were ever thrown.
            total = free_wounds + free_no_effect
            kept_wounds, kept_crits = wounds - free_wounds, crits - free_crits
            options = [
                (
                    f"Re-roll the whole Wound roll ({total} dice)",
                    lambda: self._reroll_wound(total, kept_wounds, kept_crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, reason, full=True),
                ),
            ]
            # "You CAN re-roll the Wound roll" permits re-rolling any subset
            # of it, and re-rolling only the failures is the subset a player
            # almost always wants - throwing successes away is a cost, not a
            # bonus. Offering the whole roll as the ONLY way to use the
            # ability made that cost compulsory, which is a strictly worse
            # deal than the rule grants. User report: "ich kann mich nicht
            # dazu entscheiden NUR die failed wounds zu wiederholen, entweder
            # alles oder nichts. das ist falsch."
            #
            # Skipped when there is no successful re-rollable die, because
            # then "the whole roll" and "only the failures" are literally the
            # same dice - two buttons with one outcome.
            if free_wounds > 0:
                options.append((
                    f"Re-roll only the {free_no_effect} failed dice",
                    lambda: self._reroll_wound(free_no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, reason),
                ))
            options.append(keep)
            prompt = f"{weapon_label}: {reason} - re-roll the Wound roll?"
        else:
            options = [
                (
                    "Re-roll failed wound rolls",
                    lambda: self._reroll_wound(free_no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, reason),
                ),
                keep,
            ]
            prompt = f"{weapon_label}: {reason} - re-roll failed wound rolls?"
        self.decision_manager.request(owner, prompt, options)

    def _reroll_wound(self, count, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, reason="[TWIN-LINKED]", full=False):
        """`count` dice are rolled again, and whatever `wounds`/`crits` the
        caller still wants to keep are stashed in _pending_twin_linked_reroll
        to be added back in once the new roll resolves (see
        on_dice_acknowledged()'s "wound_twin_linked_reroll" branch).

        Failures-only re-roll: count == the failed dice, and the successes
        already rolled are carried over. Full re-roll (Breach and Clear, see
        _wound_reroll_is_full()): count == the whole roll and nothing is
        carried over - the previous result is discarded, which is the point
        of throwing it again. `full` only labels it; the arithmetic is
        entirely in what the caller passes - including the case where part
        of the roll had already been re-rolled once and is therefore held
        back (see _offer_twin_linked_choice()), which is why even a "full"
        re-roll can carry wounds over."""
        self._twin_linked_used = True
        self._pending_twin_linked_reroll = {
            "wounds": wounds, "crits": crits, "weapon": weapon, "target_squad": target_squad,
            "target_profile": target_profile, "weapon_label": weapon_label, "wound_threshold": wound_threshold,
            "reason": reason, "full": full,
        }
        if full:
            label = f"Wound Roll (re-rolling all {count}): {weapon_label} {reason}"
        else:
            label = f"Wound Roll (re-rolling {count} failed): {weapon_label} {reason}"
        self.dice_manager.roll(
            count=count, sides=6, label=label,
            success_threshold=wound_threshold,
            target_name=target_squad.name, attacker_squad=self.active_squad, target_squad=target_squad, roll_kind=WOUND_ROLL,
            is_reroll=True,  # these dice have now used their one re-roll
            **self._crit_note("wound", weapon, target_squad),
        )
        self.pending_step = "wound_twin_linked_reroll"

    def _visible_precision_characters(self, target_squad, pairs):
        """Rule 24.28 ([PRECISION]): CHARACTER models in the target unit
        "visible to one or more of the attacking models" in this group."""
        attackers = [m for m, _ in pairs]
        return [
            c for c in target_squad.models
            if c.profile.character
            and any(
                line_of_sight.has_line_of_sight(a, c, self.obstacles, self.all_tokens, self.terrain_areas)
                for a in attackers
            )
        ]

    def _precision_choice_needed(self, weapon, target_squad, pairs):
        if not weapon.precision or self.decision_manager is None:
            return False
        return bool(self._visible_precision_characters(target_squad, pairs))

    def _offer_precision_choice(self, rolls, weapon, target_squad, pairs, weapon_label, owner):
        """"The active player can select one allocation group that contains
        one of those visible CHARACTER models" - rule 05.03/05.04 elsewhere
        make save/damage allocation the *defending* player's decision, but
        24.28 is an explicit exception: this particular choice belongs to
        the ACTIVE (attacking) player, hence `owner` is self.active_squad's
        owner, not target_squad's."""
        characters = self._visible_precision_characters(target_squad, pairs)
        options = [
            (
                f"Prioritize {c.profile.name}",
                lambda c=c: self._begin_damage_allocation(rolls, weapon, target_squad, priority_group=[c]),
            )
            for c in characters
        ]
        options.append((
            "Resolve normally",
            lambda: self._begin_damage_allocation(rolls, weapon, target_squad, priority_group=None),
        ))
        self.decision_manager.request(
            owner, f"{weapon_label}: [PRECISION] - prioritize a visible CHARACTER for allocation?", options,
        )

    def _continue_after_save(self, rolls, weapon, target_squad, weapon_label, group):
        """Everything that happens once a group's Save roll is settled.

        One method because there are now two ways to get here: the roll was
        acknowledged, or it was never made at all (_skip_impossible_save()).
        [PRECISION] still has to be offered on the skipped path - the attacker
        directing failed saves at a CHARACTER is a choice about WHERE the
        wounds land, entirely independent of whether a die could have stopped
        them - so the branch belongs here rather than at the acknowledgement."""
        damage_weapon = melta_adjusted_weapon(weapon, group["pairs"], target_squad)
        if self._precision_choice_needed(weapon, target_squad, group["pairs"]):
            self._offer_precision_choice(rolls, damage_weapon, target_squad, group["pairs"], weapon_label, self.active_squad.owner)
        else:
            self._begin_damage_allocation(rolls, damage_weapon, target_squad, priority_group=None)

    def _skip_impossible_save(self, target_squad, weapon, save_threshold, wounds):
        """Whether this Save roll may be skipped outright, recording WHY so
        _check_allocation_done() can say so instead of printing dice that were
        never thrown.

        User: "Save Rolls, die man gar nicht bestehen kann, sollten auch gar
        nicht gewuerfelt werden. Manchmal werden da 6en gewuerfelt, die dann
        aber rot sind."

        The predicate lives in game/damage_resolution.py next to the thresholds
        it reads - the same one definition that already stops the panel and the
        resolution disagreeing about a save. Note it asks about EVERY model of
        the unit, not the representative `save_threshold` shown on the panel."""
        if wounds <= 0 or not save_is_impossible(target_squad, weapon, self.waaagh):
            self._save_not_rolled = None
            return False
        needed = save_threshold if save_threshold is not None else 7
        self._save_not_rolled = f"not rolled - no save is possible, needed {needed}+"
        self._log(f"{self.current_group['weapon_label']}: no save is possible "
                  f"(needed {needed}+), so {wounds} wound(s) go straight through.")
        return True

    def _begin_damage_allocation(self, rolls, weapon, target_squad, priority_group):
        # Sunforge's Damage-roll half - only built when the ability actually
        # applies to this group, so the session's mere possession of one
        # means "a re-roll is on offer here" (see game/sunforge.py).
        damage_reroll = None
        if weapon.damage_notation is not None:
            common = dict(
                decision_manager=self.decision_manager, dice_manager=self.dice_manager,
                game_log=self.game_log, owner=self.active_squad.owner, weapon_name=weapon.name,
            )
            if sunforge.applies(self.active_squad, target_squad):
                damage_reroll = sunforge.damage_reroll_offer(**common)
            elif structural_collapse.applies(self.active_squad, weapon):
                # MANDATORY, not an offer: "re-roll a Damage roll of 1" has no
                # "you can". The face is derived from the notation because the
                # D-cannon's Damage is D6+2, so a die of 1 reads as a total of
                # 3 - see game/structural_collapse.py.
                #
                # THE SECOND CLAUSE IS EXCLUSIVE, AND IT IS GATED ON THE
                # TARGET: "if that attack targets a TITANIC unit, you can
                # re-roll the Damage roll INSTEAD". So exactly one of the two
                # halves is live per attack - the free re-roll REPLACES the
                # automatic one rather than stacking with it. Without the gate
                # the offer half fired against every target, handing out a free
                # re-roll on every D-cannon roll that was not a 1; the
                # predicate written for exactly this had no caller at all.
                # Nothing built carries TITANIC, so the TITANIC branch is
                # measured-inert today - see structural_collapse.py.
                titanic = structural_collapse.targets_titanic(target_squad)
                damage_reroll = DamageRerollOffer(
                    structural_collapse.STRUCTURAL_COLLAPSE_LABEL,
                    automatic_faces=(() if titanic
                                     else structural_collapse.STRUCTURAL_COLLAPSE_AUTOMATIC_FACES),
                    offerable=titanic,
                    notation=weapon.damage_notation, **common,
                )
            elif enh_breath_of_vaul.damage_reroll_applies(self.active_squad, weapon):
                # Breath of Vaul's fusion-gun half. Unlike every other entry
                # in this chain it asks nothing about the TARGET - "a Damage
                # roll for a model equipped with a fusion gun in that unit" is
                # a question about what the shooter is holding.
                damage_reroll = DamageRerollOffer(
                    enh_breath_of_vaul.BREATH_OF_VAUL_LABEL, **common)
            elif assured_destruction.applies(self.active_squad, target_squad, self.turn_tracker):
                # Two abilities, one die, and a die is never re-rolled twice -
                # so whichever applies builds the single offer. They cannot
                # both apply anyway (one is T'au, one is Aeldari).
                damage_reroll = DamageRerollOffer(
                    assured_destruction.ASSURED_DESTRUCTION_LABEL,
                    prompt_suffix="against this MONSTER/VEHICLE target", **common,
                )
        # The Farseer's Branching Fates can SET a Damage roll instead of
        # re-rolling it - a separate collaborator on the same die.
        self.damage_session = DamageAllocationSession(
            rolls, weapon, target_squad, dice_manager=self.dice_manager, log=self._log, priority_group=priority_group,
            stealth_drones=self.stealth_drones, waaagh=self.waaagh, damage_reroll=damage_reroll,
        )
        self.damage_session.on_resumed = self._make_damage_resume_hook(self.damage_session, rolls)
        self.pending_step = "allocate"
        self._check_allocation_done(rolls)

    def _make_damage_resume_hook(self, session, rolls):
        """Lets a DamageAllocationSession that was carried forward by one of
        its DecisionManager collaborators (Stealth Drones, or Sunforge's
        Damage re-roll) run this controller's own completion check - see
        DamageAllocationSession.on_resumed for the freeze this fixes.

        Bound to the session OBJECT, not just to `self`: the answer can
        arrive after this controller has already moved on to another weapon
        group (a stale prompt left open across an abandoned group), and
        finishing the group that is current NOW on the strength of an older
        group's session would end the wrong one."""
        def resume():
            if self.damage_session is session:
                self._check_allocation_done(rolls)
        return resume

    def choose_damage_model(self, model):
        """Rule 05.04/24.10/24.15: the defending (or, for Hazardous,
        attacking) player's choice of which model takes a wound (normal
        damage), a Devastating Wounds mortal wound, or a Hazardous mortal
        wound, when more than one model in the group qualifies."""
        if self.damage_session is not None:
            self.damage_session.choose_model(model)
            self._check_allocation_done()
        elif self.devastating_wound_session is not None:
            self.devastating_wound_session.choose_model(model)
            self._check_devastating_wounds_done()
        elif self.mortal_wound_session is not None:
            self.mortal_wound_session.choose_model(model)
            self._check_hazard_wounds_done()

    def _check_allocation_done(self, rolls=None):
        if not self.damage_session.done:
            return
        saved, failed = self.damage_session.saved, self.damage_session.failed
        weapon_label = self.current_group["weapon_label"]
        summary = f"{weapon_label} save roll"
        if self._save_not_rolled is not None:
            # Never print a dice list for a roll that did not happen: the
            # stand-in 1s are rule 05.04 bookkeeping, not dice anyone threw.
            summary += f" ({self._save_not_rolled})"
            self._save_not_rolled = None
        elif rolls is not None:
            summary += f" {rolls}"
        self._log(f"{summary}: {saved} saved, {failed} failed.")
        self.damage_session = None
        if self._devastating_crits > 0:
            weapon = self.current_group["pairs"][0][1]
            target_squad = self.current_group["target_squad"]
            self._begin_devastating_wounds(weapon, target_squad)
        elif self._pending_crit_ap_crits > 0:
            self._begin_crit_ap_save()
        else:
            self._finish_group()

    def _begin_devastating_wounds(self, weapon, target_squad):
        damage_weapon = melta_adjusted_weapon(weapon, self.current_group["pairs"], target_squad)
        self.devastating_wound_session = DevastatingWoundAllocationSession(
            target_squad, damage_weapon.damage, self._devastating_crits, dice_manager=self.dice_manager, log=self._log,
            waaagh=self.waaagh,
        )
        self._devastating_crits = 0
        self.pending_step = "devastating"
        self._check_devastating_wounds_done()

    def _check_devastating_wounds_done(self):
        if self.devastating_wound_session is None or not self.devastating_wound_session.done:
            return
        self.devastating_wound_session = None
        if self._pending_crit_ap_crits > 0:
            self._begin_crit_ap_save()
        else:
            self._finish_group()

    def _begin_crit_ap_save(self):
        """The critical-wound subset pulled out of this group's main Save roll
        (see _resolve_wounds()) gets its OWN Save roll here, at whatever AP its
        source dictates - Cadre Fireblade's Crack Shot overrides to a flat -3,
        Seer Council's Fate Inescapable improves by 1; see game/crit_ap.py.

        Reuses the same DamageAllocationSession machinery as a normal Save roll
        (via on_dice_acknowledged()'s "save_crit_ap" branch), not
        DevastatingWoundAllocationSession's mortal-wound path, since these
        wounds still take a real Armour save, just at a different AP.

        Reads the RAW representative weapon straight off `pairs` (same access
        pattern as _begin_devastating_wounds() above) rather than replaying
        Bonded Heroes/Starscythe/Drive-by Dakka's own AP adjustments first. That
        was exact while Crack Shot's unconditional override was the only source
        and stays exact for it; for Fate Inescapable's +1 it means those other
        adjustments are not compounded into the critical share - a documented
        simplification, and the two can never co-occur (T'au ability vs Aeldari
        stratagem)."""
        crits = self._pending_crit_ap_crits
        self._pending_crit_ap_crits = 0
        weapon = self.current_group["pairs"][0][1]
        target_squad = self.current_group["target_squad"]
        weapon_label = self.current_group["weapon_label"]
        target_profile = allocation_target_profile(target_squad)
        shooter_model = self.current_group["pairs"][0][0]
        crit_source = crit_ap.label(weapon, shooter_model, self.active_squad)
        crit_ap_weapon = crit_ap.adjusted_weapon(weapon, shooter_model, self.active_squad)

        if self.turn_tracker is not None:
            self.turn_tracker.set_active(target_squad.owner)

        # The number a die must REACH, from the same definition
        # game/damage_resolution.py resolves the save with - so a die
        # saved by the INVULNERABLE save (or under Ramshackle's worsened
        # AP) is no longer coloured red and counted as a failure. User
        # report: "oft werden bestandene rettungswuerfe rot angezeigt".
        save_threshold = displayed_save_threshold(
            allocation_target_model(target_squad), crit_ap_weapon, self.waaagh,
        )
        melta_weapon = melta_adjusted_weapon(crit_ap_weapon, self.current_group["pairs"], target_squad)
        damage_preview = None if melta_weapon.damage_notation is not None else melta_weapon.damage
        if self._skip_impossible_save(target_squad, crit_ap_weapon, save_threshold, crits):
            self._continue_after_save(
                [AUTO_FAILED_SAVE] * crits, crit_ap_weapon,
                target_squad, weapon_label, self.current_group)
            return
        self.dice_manager.roll(
            count=crits, sides=6,
            label=(f"Save Roll: {weapon_label} ({crit_source}, AP{crit_ap_weapon.ap}, "
                   f"{crits} critical wound(s))"),
            success_threshold=save_threshold if save_threshold is not None else 7,
            target_name=target_squad.name, attacker_squad=self.active_squad, target_squad=target_squad, roll_kind=SAVE_ROLL,
            damage_per_failure=damage_preview,
        )
        self.pending_step = "save_crit_ap"

    def _finish_group(self):
        self.pending_step = None
        weapon_key = self.current_group["weapon_key"] if self.current_group else None
        pairs = self.current_group["pairs"] if self.current_group else None
        # Rule 24.26 ([ONE SHOT]): "can only be selected to make attacks
        # with once per battle" - mark every model+weapon pair that just
        # fired in THIS physical dice sequence so _attack_groups() never
        # offers them again, for the rest of the game (never reset, unlike
        # fired_weapon_types). Safe to do per cover sub-group (see
        # _dispatch_group()): a given (model, weapon) pair only ever ends
        # up in one of them.
        if pairs:
            for model, weapon in pairs:
                if weapon.one_shot:
                    # An alternate-firing-mode copy stands in for a real weapon
                    # in model.weapons - mark THAT one, since _attack_groups()
                    # looks the ledger up by the instances it finds there.
                    self.one_shot_used.add((model.id, weapon.overcharge_of_id or id(weapon)))
        self.current_group = None

        # Back to the attacker's decisions (pick the next weapon, or stop shooting).
        if self.turn_tracker is not None and self.active_squad is not None:
            self.turn_tracker.set_active(self.active_squad.owner)

        if self._pending_subgroups:
            # Rule 13.08: this weapon selection got cover-split (see
            # _dispatch_group()) and the sub-group that just finished its
            # full hit/wound/save/damage sequence wasn't the last one -
            # continue with the next before touching any of the "this whole
            # selection is done" bookkeeping below, all of which is per
            # SELECTION (once), not per physical dice sequence.
            next_pairs, label_suffix = self._pending_subgroups.pop(0)
            self.state = CHOOSING_WEAPON
            self._begin_resolution(
                weapon_key, f"{self._pending_subgroups_base_label} ({label_suffix})",
                next_pairs, self._pending_subgroups_target_squad,
            )
            return

        # Rule 13.09 (Hidden): this weapon selection has now fully resolved,
        # so the unit has genuinely made a ranged attack this activation -
        # which is what cancel() needs to know (see _note_ranged_attack()).
        self._fired_this_activation = True

        # Rule 24.15 ([HAZARDOUS]): add this group's weapons to the tally -
        # one roll per weapon that fired. Added ONCE for the whole selection
        # even when it got cover-split into two physical dice sequences above,
        # which is what zeroing the pending count here is for.
        if self._pending_subgroups_hazardous:
            self._hazardous_count += self._pending_subgroups_hazardous
            self._pending_subgroups_hazardous = 0

        if self.split_fire:
            self._begin_next_split_group()
        else:
            if weapon_key in self.remaining_weapon_types:
                self.remaining_weapon_types.remove(weapon_key)
            # Rule 15.08/15.09: a reactive Snap Shooting activation isn't
            # the unit's real Shooting-phase activation - don't mark this
            # weapon type as "already fired this phase" against it.
            if not self._reactive:
                self.fired_weapon_types.setdefault(self.active_squad, set()).add(weapon_key)
            if self.remaining_weapon_types:
                self.state = CHOOSING_WEAPON
            else:
                self._finish_squad()

    def _finish_squad(self):
        """Rule 24.15 ([HAZARDOUS]): "after that unit has resolved all of
        its attacks" - the unit's whole shooting activation genuinely ends
        here (whether by running out of weapons, split-fire's last group,
        or the player stopping early via stop_shooting()) - so this is
        exactly the point to make any owed hazard rolls before the squad is
        actually released."""
        if self._hazardous_count > 0:
            self._begin_hazard_rolls()
        else:
            self._actually_finish_squad()

    def _begin_hazard_rolls(self):
        count = self._hazardous_count
        self._hazardous_count = 0
        self.dice_manager.roll(
            count=count, sides=6,
            label=f"Hazard Rolls: {self.active_squad.name} ({count} [HAZARDOUS] weapon(s))",
        )
        self.pending_step = "hazard"

    def _check_hazard_wounds_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._actually_finish_squad()

    def _all_squads_for_auras(self):
        """Every unit with a live model on the board, deduplicated.

        Only the aura half of Auxiliary Cadre's Localised Stealth Projectors
        needs it, and only at the end of an activation - so it is derived here
        rather than kept as another list to maintain. `id()`-keyed because a
        Squad is not hashable-by-value and two tokens of one unit must not
        yield it twice."""
        by_id = {}
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            if squad is None or id(squad) in by_id:
                continue
            if any(not m.is_dead() for m in squad.models):
                by_id[id(squad)] = squad
        return list(by_id.values())

    def _note_ranged_attack(self):
        """Rule 13.09 (Hidden): record that this unit made a ranged attack, in
        its owner's own turn-number terms, so status_effects.is_hidden() stops
        reporting it as Hidden (and the board's HD label disappears) until a
        turn has passed.

        Called from BOTH ways an activation ends, which is the whole point:

          * _actually_finish_squad(), the normal end - unconditionally, the
            long-standing behaviour. An activation that reaches its end has
            used the unit's shot, whether or not every weapon was fired.
          * cancel(), the abandon-and-move-on path - but only when a weapon
            group actually resolved (_fired_this_activation).

        Real bug, found via user report ("teste mal bitte ob die hidden-mechanik
        funktioniert" / "schau mal bitte, dass das HD label verschwindet, wenn
        die einheit geschossen hat"): main.py's Next Phase button calls
        cancel() unconditionally - a deliberate "abandon and move on" design
        for shooting specifically - and cancel() used to skip this bookkeeping
        entirely. So the ordinary human sequence "fire the main gun, don't
        bother with the pistol, click Next Phase" left the unit recorded as
        having never shot: it stayed Hidden, kept its HD label, and stayed
        unshootable from beyond its detection range for the rest of the battle.

        The condition is what keeps the fix from breaking the other direction:
        cancel() also runs on every Next Phase click for a unit that merely had
        its shooting UI open, and marking that as "made a ranged attack" would
        strip Hidden off a unit that never fired a shot."""
        if self.turn_tracker is None or self.active_squad is None:
            return
        # Advanced Acquisition Cadre's Expert Fieldcraft: "those ranged attacks
        # do not prevent your unit from being hidden". Suppressing the write IS
        # the rule - Hidden has no second record. Placed inside this method so
        # BOTH callers see it; gating only the normal end would leave cancel()
        # stripping Hidden, which is precisely half of the bug this method's
        # docstring above was written for.
        if hidden_after_shooting.keeps_hidden(
                self.active_squad, reactive=self._reactive,
                all_squads=self._all_squads_for_auras()):
            return
        self.last_ranged_attack_turn[self.active_squad] = self.turn_tracker.turn_number_for(self.active_squad.owner)

    def _actually_finish_squad(self):
        # Rule 19.04: "the ability it was conferring upon the attached unit
        # applies until the attacking unit has resolved all of its attacks"
        # - that is exactly here, so every attached unit this activation hit
        # stops extending a wiped-out component's abilities now. Closed
        # before the early-return-free bookkeeping below so a reactive Snap
        # Shooting activation (15.09) closes its window too.
        for hit_squad in self._hit_target_squads_this_activation:
            attached_units.end_attack_sequence(hit_squad)
        # The gunships' Targeting Array is spent per ACTIVATION, so its
        # ledger closes at the same instant 19.04's window does - the one
        # canonical "this unit has resolved all of its attacks" moment.
        if self.targeting_array is not None:
            self.targeting_array.end_activation(self.active_squad)
        # "...until that friendly unit HAS SHOT".
        far_reaching_doom.end_shooting(self.active_squad)
        if self.prototype_weapon_system is not None:
            self.prototype_weapon_system.end_activation(self.active_squad)
        if self.unmasking_suite is not None:
            self.unmasking_suite.end_activation(self.active_squad)
        # Rule 15.08/15.09: a reactive Snap Shooting activation doesn't use
        # up the unit's real Shooting-phase activation - last_ranged_attack_turn
        # (rule 13.09, Hidden) still updates though, since it genuinely was
        # a ranged attack.
        if not self._reactive:
            self.shot_squad_ids.add(self.active_squad)
            # Suppression Volley (user-supplied Strike Team ability): "In
            # your Shooting phase, after this unit has shot" - a reactive
            # Snap Shooting activation (rule 15.09) is explicitly NOT the
            # unit's own Shooting phase, so it's excluded here the same way
            # shot_squad_ids itself is.
            for listener in self.on_squad_finished_shooting:
                listener(self.active_squad, self._hit_target_squads_this_activation)
        self._note_ranged_attack()
        self.active_squad = None
        self.shooting_type = None
        self.available_types = []
        self.target_squad = None
        self.remaining_weapon_types = []
        self.pending_step = None
        self._reset_target_snapshots()
        self.state = IDLE
        self._finish_activation()

    def unmodified_six_context(self):
        """(squad, model, weapon) for the roll this controller currently has
        on the table, or None when it has no weapon group open.

        Read by game/unmodified_six_controller.py, which needs all three: the
        MODEL because both abilities exclude one ("excluding CHARACTER models"
        for an Aspect Shrine token, "excluding SUPPORT WEAPON models" for
        Branching Fates), and the WEAPON because whether a critical is worth
        buying depends on it ([SUSTAINED HITS]/[LETHAL HITS] on a hit,
        [DEVASTATING WOUNDS] on a wound - see game/unmodified_six.py).

        The representative model of the weapon group is the one the old prompt
        judged from too: a joined character carries its own datasheet's
        weapons, so it lands in its own attack group rather than sharing one.

        The ADJUSTED weapon, not pairs[0][1]: whether a critical buys anything
        depends on conditional grants. Bladestorm hands the Dire Avengers'
        catapult [SUSTAINED HITS] within half range, and reading the printed
        profile would mean the button never appeared in exactly the case where
        the token is worth spending. _adjusted_weapon() is the one place those
        grants are applied, and what every other downstream reader uses."""
        if self.current_group is None:
            return None
        pairs = self.current_group.get("pairs") or ()
        if not pairs:
            return None
        target_squad = self.current_group.get("target_squad")
        return (self.active_squad, pairs[0][0], self._adjusted_weapon(pairs, target_squad))

    def unmodified_six_damage_context(self):
        """(squad, model, notation_roll) when a DAMAGE roll for this
        controller's current weapon group is on the table, or None.

        Separate from unmodified_six_context() because a Damage roll is a
        different shape: not a die that succeeds or fails but a rolled AMOUNT,
        and only the Farseer's Branching Fates covers it at all.

        The MODEL handed over is the weapon group's representative ATTACKER,
        the same one the hit/wound hook uses - the printed clause is
        "excluding SUPPORT WEAPON models" about the model making the attack.
        The prompt this replaced passed the model that was taking the wound
        instead; harmless today (no SUPPORT WEAPON datasheet exists here) but
        the wrong model to ask, so it is not carried over."""
        session = self.damage_session
        if session is None or self.current_group is None:
            return None
        roll = getattr(session, "pending_damage_roll", None)
        if roll is None or not roll.is_pending:
            return None
        pairs = self.current_group.get("pairs") or ()
        if not pairs:
            return None
        return (self.active_squad, pairs[0][0], roll)

    def _log(self, message):
        if self.game_log is not None:
            player = self.turn_tracker.active_player if self.turn_tracker is not None else self.player_name
            self.game_log.add(f"{player}: {message}")
