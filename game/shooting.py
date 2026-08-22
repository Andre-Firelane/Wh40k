import copy

from game import attached_units, battle_focus, line_of_sight, status_effects
from game.ard_as_nails import ARD_AS_NAILS_WOUND_PENALTY, ard_as_nails_wound_modifier_applies
from game.damage_estimate import wound_threshold as _wound_threshold  # rule 05.02's S-vs-T table; moved to a leaf module so game/stim_injectors.py can reach it without an import cycle - re-exported here under its old private name for game/fight.py and ai/ (see game/damage_estimate.py's docstring)
from game.damage_resolution import DamageAllocationSession, DevastatingWoundAllocationSession, MortalWoundAllocationSession
from game.hazard import hazard_failures, hazard_mortal_wounds
from game.dice import ATTACKS_ROLL, HIT_ROLL, SAVE_ROLL, SNAP_SHOT_HIT_ROLL, WOUND_ROLL
from game.dice_notation import DiceNotation, DiceNotationRoll, describe as describe_dice_notation
from game.modifiers import Modifier, apply_modifiers, describe_modifiers
from game.objectives import is_on_objective
from game.arrokon_protocol import arrokon_adjusted_weapon
from game import aspect_shrine
from game import branching_fates
from game import psychic_guidance
from game import protect
from game.doom import DOOM_WOUND_BONUS
from game.crit_hit import crit_hit_threshold
from game import psychic_communion
from game import storm_of_silence
from game import assured_destruction
from game.fire_support import FIRE_SUPPORT_LABEL
from game.hand_of_asuryan import hand_of_asuryan_adjusted_weapon
from game.damage_reroll import DamageRerollOffer
from game.bladestorm import bladestorm_adjusted_weapon
from game import crit_ap
from game import fate_inescapable
from game.drive_by_dakka import drive_by_dakka_adjusted_weapon
from game.gun_crazy_showoffs import gun_crazy_adjusted_weapon, unit_has_gun_crazy_showoffs
from game.ammo_runt import ammo_runt_adjusted_weapon
from game.nova_charge import nova_charge_adjusted_weapon
from game import exemplars_of_montka, monster_hunters, pulse_accelerator, sunforge, target_uploaded, way_of_the_short_blade
from game.retaliation_cadre import bonded_heroes_adjusted_weapon
from game.starscythe import starscythe_adjusted_weapon
from game.squad import (
    allocation_target_profile, attached_unit_toughness, edge_distance, is_monster_or_vehicle_unit, squad_has_battlesuit_support_system, squad_has_war_construct,
    squad_has_breach_and_clear, squad_has_guardian_drone, squad_has_stealth, tank_hunters_modifiers,
)
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
_UNMODIFIED_SIX_SOURCES = (aspect_shrine, branching_fates)


def _unmodified_six_source(method, squad, model, *args):
    """The first source that would buy something here, and what it buys."""
    for source in _UNMODIFIED_SIX_SOURCES:
        change = getattr(source, method)(squad, model, *args)
        if change is not None:
            return source, change
    return None, None


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
    field = _KEYWORD_FIELDS.get(keyword)
    if field is None:
        return False
    return any(getattr(m.profile, field, False) for m in squad.models)


def _anti_entries(weapon):
    """WeaponProfile.anti as a uniform sequence of (keyword, threshold).

    It may be written either as a single tuple - ("VEHICLE", 4) - or as a
    tuple of those, for a weapon that prints more than one [ANTI-X] at once
    (the Beastboss's Beast Snagga klaw and Beastchoppa each carry
    Anti-Monster 4+ AND Anti-Vehicle 4+). The single form is detected by its
    second element being an int, which no nested form can be."""
    anti = weapon.anti
    if anti is None:
        return ()
    if len(anti) == 2 and isinstance(anti[1], int):
        return (anti,)
    return tuple(anti)


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
        half_range = weapon.range_in / 2
        in_half_range = any(
            edge_distance(shooter, defender) <= half_range
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
    half_range = weapon.range_in / 2
    in_half_range = any(
        edge_distance(shooter, defender) <= half_range
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


def _model_can_reach(model, weapon, target_squad, obstacles, all_tokens=(), shooting_type=None, terrain_areas=()):
    """Rule 10.07: an [INDIRECT FIRE] weapon fired as Indirect shooting can
    target units not visible to the attacking model - range still applies,
    line of sight doesn't. Rule 24.24 (LONE OPERATIVE): on top of the
    general "not visible to enemy models" gate in _is_valid_target_squad(),
    a Lone Operative "cannot be targeted by [INDIRECT FIRE] weapons unless
    the attacking model is within X\" of this unit" - a per-MODEL
    restriction, since Indirect Fire otherwise lets any model in the unit
    fire regardless of its own distance to the target."""
    bypass_los = shooting_type == INDIRECT_SHOOTING and weapon.indirect_fire
    if bypass_los:
        lone_range = status_effects.targeting_range_limit(target_squad)
        if lone_range is not None and not any(
            edge_distance(model, defender) <= lone_range for defender in target_squad.models
        ):
            return False
    # Pulse Accelerator Drone: "+6\" to the Range characteristic of pulse
    # carbines equipped by models in the bearer's unit" - derived live from
    # the shooter's own unit rather than baked into the weapon, see
    # game/pulse_accelerator.py. This is THE place range decides anything;
    # the two half-range sites above (_extra_attack_dice's [RAPID FIRE] and
    # melta_adjusted_weapon's [MELTA X]) deliberately still read the printed
    # range, because no pulse carbine has either keyword - if one ever does,
    # they need the same treatment.
    weapon_range = pulse_accelerator.effective_range_in(model, weapon)
    return any(
        edge_distance(model, defender) <= weapon_range
        and (bypass_los or line_of_sight.has_line_of_sight(model, defender, obstacles, all_tokens, terrain_areas))
        for defender in target_squad.models
    )


def is_close_quarters(weapon):
    """Rule 24.27 ([PISTOL]): "[PISTOL] and [CLOSE-QUARTERS] are identical
    for all rules purposes" - a pure alias, checked everywhere
    [CLOSE-QUARTERS] (10.06/24.07) is checked, instead of duplicating each
    call site's logic for a second flag."""
    return weapon.close_quarters or weapon.pistol


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
    already existed groups differently because of this."""
    return (effective_ballistic_skill(model, weapon), weapon.strength, weapon.ap, weapon.damage,
            is_close_quarters(weapon), weapon.melta)


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
        return True if is_monster_or_vehicle_unit(squad) else is_close_quarters(weapon)
    return True


def _weapon_side(weapon):
    return "close_quarters" if is_close_quarters(weapon) else "other"


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
    return locked is not None and locked != _weapon_side(weapon)


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
    if (squad.fell_back_this_turn and not squad_has_battlesuit_support_system(squad)
            and not squad_has_war_construct(squad)):
        return []
    engaged = squad.is_engaged(all_tokens)
    advanced = movement_controller is not None and squad in movement_controller.advanced_squad_ids

    groups = _attack_groups(squad)  # unfiltered - just checking which weapon keywords exist at all
    has_assault = any(weapon_has_assault(w, squad) for plist in groups.values() for _, w in plist)
    has_close_quarters = any(is_close_quarters(w) for plist in groups.values() for _, w in plist)
    has_indirect_fire = any(w.indirect_fire for plist in groups.values() for _, w in plist)

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
        waaagh=None, target_reactions=(), nova_charge=None, ammo_runt=None, fire_support=None, hand_of_asuryan=None, guide=None, doom=None, whispering_web=None,
    ):
        self.active_squad = None
        self.state = IDLE
        self.split_fire = False
        self.obstacles = obstacles if obstacles is not None else []
        self.terrain_areas = terrain_areas if terrain_areas is not None else []
        self.objectives = objectives if objectives is not None else []  # Breacher Team's Breach and Clear ability - see _wound_reroll_reason()
        self.game_log = game_log
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
        self.one_shot_used = set()  # rule 24.26: (model.id, id(weapon)) pairs already fired - persists for the whole battle, never reset
        self._hit_target_squads_this_activation = set()  # Suppression Volley: enemy squads hit by 1+ attacks this activation, see _handle_hit_results()/on_squad_finished_shooting
        # Callables (squad, hit_target_squads), fired for every REAL
        # (non-reactive) activation, unlike the per-call
        # _on_activation_finished below. A LIST since it grew a second
        # consumer: Suppression Volley (game/suppression.py) and the Aeldari
        # Agile Manoeuvre Fade Back (game/battle_focus.py), which needs
        # exactly the "was hit by one or more of those attacks" set this
        # already tracks. Same generalisation target_reactions and
        # StratagemController.cost_discounts got for the same reason.
        self.on_squad_finished_shooting = []

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
        # Defaults for the per-group counters set in _begin_resolution() -
        # see there for what they are for (game/aspect_shrine.py).
        self._hit_dice_count = None
        self._wound_dice_count = None
        self._aspect_shrine_hit_offered = False
        self._aspect_shrine_wound_offered = False
        self.pending_step = None     # "attacks" | "hit" | "wound" | "save" | "save_crit_ap" | "allocate" | None
        self.damage_session = None   # DamageAllocationSession while pending_step == "allocate"
        self.devastating_wound_session = None  # DevastatingWoundAllocationSession, rule 24.10
        self._devastating_crits = 0  # crits pulled out of the current wound roll for [DEVASTATING WOUNDS]
        self._pending_crit_ap_crits = 0  # critical wounds pulled out of the current wound roll for their own Save roll at a different AP - Cadre Fireblade's Crack Shot (override to -3) or Seer Council's Fate Inescapable (improve by 1); see game/crit_ap.py, _begin_crit_ap_save()
        self._hazardous_count = 0  # distinct [HAZARDOUS] weapon groups fired this activation, rule 24.15
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
        self._pending_subgroups_hazardous = False  # apply once, when the whole selection is done - not per sub-group

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
        self._on_activation_finished = None  # callable, fires once this activation ends, reactive or not

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
        # An activation started HERE is by definition the unit's own, not a
        # reactive one - leaving a stale True behind (start_snap_shooting()
        # sets it, only _actually_finish_squad()/cancel() clear it) is what
        # made the reported failure unbounded rather than a one-off: with it
        # still set, nothing was ever booked into shot_squad_ids/
        # fired_weapon_types, so can_shoot() kept saying yes and the same
        # weapon group kept coming back.
        self._reactive = False
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

    def cancel(self):
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
        self._pending_subgroups_hazardous = False
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
        """Rule 10.06: under Close-Quarters shooting, only enemy units your
        unit is engaged with can be targeted. Every other shooting type
        excludes engaged enemy units entirely (rule 03.04 already blocked
        those from normal shooting). Rule 13.09: a unit that's entirely
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
        if target_squad.owner == attacking_squad.owner:
            return False
        if shooting_type == CLOSE_QUARTERS_SHOOTING:
            if not attacking_squad.is_engaged_with(target_squad):
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
        return any(
            status_effects.is_detectable(
                model, attacking_squad, self.terrain_areas, self.turn_tracker, self.last_ranged_attack_turn,
            )
            for model in target_squad.models
        )

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
                _model_can_reach(model, weapon, target_squad, self.obstacles, all_tokens, shooting_type, self.terrain_areas)
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
                        model, weapon, target_squad, self.obstacles, self.all_tokens,
                        self.shooting_type, self.terrain_areas,
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
            model, weapon, target_squad, self.obstacles, self.all_tokens,
            self.shooting_type, self.terrain_areas,
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
                return self._is_valid_target_squad(squad, all_tokens) and any(
                    _model_can_reach(model, weapon, squad, self.obstacles, all_tokens, self.shooting_type, self.terrain_areas)
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
                    model, weapon, squad, self.obstacles, all_tokens, self.shooting_type, self.terrain_areas
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
            self._weapon_side_lock[model] = _weapon_side(weapon)

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
        self._pending_subgroups_hazardous = bool(pairs) and pairs[0][1].hazardous

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
        # ASPECT WARRIORS wargear (game/aspect_shrine.py): how many dice each
        # step of THIS group threw. The count never changes across re-rolls
        # (a re-roll replaces dice, it never adds or removes any), so it is
        # an exact way to recover the failure count at the end of the step
        # without threading it through every signature in between. None
        # means that step made no roll at all ([TORRENT], or a fully
        # auto-wounded group), i.e. no failures.
        self._hit_dice_count = None
        self._wound_dice_count = None
        self._aspect_shrine_hit_offered = False   # at most one offer per group per step
        self._aspect_shrine_wound_offered = False
        self._hit_reroll_used = False  # Monster Hunters: likewise a fresh chance per weapon group - see _hit_reroll_choice_needed()
        self._rolled_strength = None  # a dice-notation Strength is rolled once per weapon group - see _effective_strength()

        if not pairs or not target_squad.models:
            self._finish_group()
            return

        shooter_model = pairs[0][0]
        if self.turn_tracker is not None:
            self.turn_tracker.set_active(shooter_model.squad.owner)

        weapon = pairs[0][1]
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
                weapon.attacks_notation, count=len(pairs), dice_manager=self.dice_manager,
                label=f"Attacks: {weapon_label} ({len(pairs)} model(s), {describe_dice_notation(weapon.attacks_notation)} each)",
                roll_kind=ATTACKS_ROLL, log=self._log,
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
            bonded_weapon = bonded_heroes_adjusted_weapon(weapon, pairs, target_squad)
            bonded_weapon = starscythe_adjusted_weapon(bonded_weapon, pairs, target_squad)
            bonded_weapon = drive_by_dakka_adjusted_weapon(bonded_weapon, pairs, target_squad)
            # The Arro'kon Protocol: chained here too for the same
            # completeness reason as the three above, even though [TORRENT]
            # forces crits=0 below - so [SUSTAINED HITS] is a no-op in
            # practice for a torrent weapon specifically. Same treatment
            # game/fight.py gives War Horde's own [SUSTAINED HITS] grant at
            # its [TORRENT] shortcut.
            bonded_weapon = arrokon_adjusted_weapon(bonded_weapon, pairs, target_squad)
            # Dire Avengers' Bladestorm - another conditional [SUSTAINED HITS]
            # grant, so it chains next to Arro'kon's; see game/bladestorm.py.
            bonded_weapon = bladestorm_adjusted_weapon(bonded_weapon, pairs, target_squad)
            # Nova Charge: chained here too, and unlike [SUSTAINED HITS] this
            # one is NOT a no-op for a torrent weapon - [DEVASTATING WOUNDS]
            # (24.10) triggers on the WOUND roll, which a [TORRENT] weapon
            # still makes; only the hit roll is skipped.
            bonded_weapon = nova_charge_adjusted_weapon(bonded_weapon, pairs)
            bonded_weapon = hand_of_asuryan_adjusted_weapon(bonded_weapon, pairs)
            bonded_weapon = psychic_communion.psychic_communion_adjusted_weapon(bonded_weapon, pairs)
            # Ammo Runt: [LETHAL HITS] on this unit's ranged weapons. A no-op
            # for a [TORRENT] weapon in practice (crits are forced to 0
            # below), chained for the same completeness reason as the others.
            bonded_weapon = ammo_runt_adjusted_weapon(bonded_weapon, self.active_squad)
            # Exemplars of Mont'ka's [SUSTAINED HITS 1]: chained here for
            # completeness like Arro'kon above, and a no-op in practice for
            # a torrent weapon (crits are forced to 0 below).
            bonded_weapon = exemplars_of_montka.montka_adjusted_weapon(
                bonded_weapon, pairs, self._closest_target_snapshot.get(target_squad, False),
            )
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
            target_name=target_squad.name,
            # Rule 15.09: "you cannot re-roll hit rolls" - a distinct kind so
            # CommandRerollController's REROLLABLE_KINDS never offers this one.
            roll_kind=SNAP_SHOT_HIT_ROLL if is_snap_shot else HIT_ROLL,
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
            return 6
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
        # The Farseer's Guide: "each time a friendly AELDARI model makes an
        # attack that targets that enemy unit, add 1 to the Hit roll" - a
        # bonus, so a -1 on the threshold. Army-wide, not unit-wide, which
        # is why the mark is held per player. See game/guide.py.
        if self.guide is not None and self.guide.applies(shooter_model, target_squad):
            modifiers.append(Modifier(-1, "Guide"))
        if self.shooting_type == CLOSE_QUARTERS_SHOOTING and is_monster_or_vehicle_unit(self.active_squad):
            targets_engaged_unit = self.active_squad.is_engaged_with(target_squad)
            if not (is_close_quarters(weapon) and targets_engaged_unit):
                modifiers.append(Modifier(1, "Close-Quarters (non-[CLOSE-QUARTERS] weapon)"))
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
        # Riptide Battlesuit's "Weapon Support System" wargear ability
        # (user-supplied, not a core rule): "each time the bearer makes a
        # ranged attack, you can ignore any or all modifiers to the Hit
        # roll" - word for word the same permission rule 24.29 ([PSYCHIC])
        # gives, so it gets the same automatic handling for the same reason
        # (see the [PSYCHIC] branch below: dropping every worsening modifier
        # and keeping every improving one is always the better play, so
        # there is no real choice to interrupt the game for). Per MODEL,
        # not per unit - it is a wargear ability of the bearer - and
        # shooter_model is exact here, not an approximation, since
        # _dispatch_group() has already split the group by cover.
        if shooter_model.profile.weapon_support_system:
            modifiers = [m for m in modifiers if m.amount <= 0]
        if weapon.psychic:
            # Rule 24.29 ([PSYCHIC]): "you can ignore any or all modifiers...
            # to the hit roll" - always rational to drop every WORSENING
            # (positive) modifier and keep every IMPROVING (negative) one,
            # so unlike e.g. [LETHAL HITS]/[PRECISION] (where the choice has
            # a real downstream trade-off) this is applied automatically
            # rather than as an interactive decision - there's no case where
            # keeping a positive modifier would ever be the better play.
            modifiers = [m for m in modifiers if m.amount <= 0]
        return modifiers

    def _wound_modifiers(self, target_squad):
        """The Guardian Drone wargear item (user-supplied, not a core rule -
        game/drones.py): "each time a model makes a ranged attack that
        targets the bearer's unit, subtract 1 from the Wound roll" - a
        malus, so per this file's Modifier sign convention (positive
        worsens) that's a +1 on the wound THRESHOLD, same "X to the roll"
        handling as Suppression Volley's hit-roll malus in _hit_modifiers().
        Checked against the TARGET squad (unlike _hit_modifiers' mostly
        attacker-side checks) - this is the defender's own protection.

        Tankbustas' own "Tank Hunters" (user-supplied, not a core rule) is
        the opposite direction - an ATTACKER-side bonus, checked against
        self.active_squad's representative model (same "read it off model
        0" simplification as e.g. squad_waaagh_active())."""
        modifiers = []
        if squad_has_guardian_drone(target_squad):
            modifiers.append(Modifier(1, "Guardian Drone"))
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
        if self.active_squad.models:
            modifiers.extend(tank_hunters_modifiers(self.active_squad.models[0], target_squad))
        # Commander Farsight's Way of the Short Blade: "+1 to the Wound
        # roll" for a unit he is LEADING, against a target within 9".
        # Hooked into both phases because its text says "makes an
        # attack", not "makes a ranged attack" - see
        # game/way_of_the_short_blade.py.
        modifiers.extend(way_of_the_short_blade.wound_modifiers(self.active_squad, target_squad))
        return modifiers

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
            label=f"{weapon_label}: {'Hit' if kind == 'hit' else 'Wound'} Roll re-roll of 1s (Forward Observers)",
            success_threshold=threshold, target_name=target_squad.name,
            roll_kind=HIT_ROLL if kind == "hit" else WOUND_ROLL,
            is_reroll=True,
        )
        self.pending_step = f"{kind}_reroll_ones"

    def _finish_hit_roll(self, hits, crits, weapon, target_squad, weapon_label, rerollable=None, hit_threshold=None):
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
                self.active_squad.owner,
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
        if self._offer_aspect_shrine_hit(hits, crits, weapon, target_squad, weapon_label):
            return
        self._apply_sustained_hits_now(hits, crits, weapon, target_squad, weapon_label)

    def _offer_aspect_shrine_hit(self, hits, crits, weapon, target_squad, weapon_label):
        """ASPECT WARRIORS wargear: "change the result of one Hit roll ... to
        an unmodified 6". Returns True if a decision was raised, in which case
        the caller must stop - the chosen callback resumes the step.

        The miss count is derived rather than threaded through the nine
        signatures between here and the roll, and it is exact: _hit_dice_count
        is the number of attacks this group made, and no re-roll can change
        that - a re-roll replaces dice, it never adds or removes any. None
        means no Hit roll happened at all ([TORRENT]), which is correctly zero
        misses."""
        if self.decision_manager is None or self.current_group is None or self._aspect_shrine_hit_offered:
            return False
        squad = self.active_squad
        pairs = self.current_group.get("pairs") or ()
        model = pairs[0][0] if pairs else None
        misses = 0 if self._hit_dice_count is None else max(0, self._hit_dice_count - hits)
        source, change = _unmodified_six_source(
            "hit_change", squad, model, weapon, hits, crits, misses)
        if change is None:
            return False
        self._aspect_shrine_hit_offered = True
        new_hits, new_crits, what = change

        def spend():
            source.spend(squad)
            self._log(
                f"{weapon_label}: {source.ACCEPT_LABEL} - one hit roll counts as an unmodified 6 "
                f"({hits} hit(s) of which {crits} critical -> {new_hits} of which {new_crits})."
            )
            self._apply_sustained_hits_now(new_hits, new_crits, weapon, target_squad, weapon_label)

        def keep():
            self._apply_sustained_hits_now(hits, crits, weapon, target_squad, weapon_label)

        self.decision_manager.request(
            squad.owner, source.prompt_for(squad, weapon_label, what, "hit"),
            [(source.ACCEPT_LABEL, spend), ("Keep the roll", keep)],
        )
        return True

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
            log=self._log,
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

    def _finish_wound_roll(self, wounds, crits, no_effect, weapon, target_squad, target_profile, weapon_label, wound_threshold, rerollable):
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
                self.active_squad.owner, rerollable,
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
        if squad_has_stealth(target_squad):
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
            total_attacks = total + extra_attack_dice(
                raw_weapon, target_squad, group["weapon_key"], self.split_fire, self.assignments, group["pairs"],
            )
            self._continue_resolution_with_attacks(raw_weapon, total_attacks)
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
        weapon = bonded_heroes_adjusted_weapon(group["pairs"][0][1], group["pairs"], target_squad)
        weapon = starscythe_adjusted_weapon(weapon, group["pairs"], target_squad)
        weapon = drive_by_dakka_adjusted_weapon(weapon, group["pairs"], target_squad)
        # The Arro'kon Protocol: unlike the three above (Strength/AP only)
        # this one touches [SUSTAINED HITS], which _finish_hit_roll() reads
        # off `weapon` at the hit step below - so it has to be chained in
        # before that branch, which is exactly where this already sits. The
        # target's model count is read live, per weapon group, rather than
        # from rule 10.02's target-selection snapshot: see
        # game/arrokon_protocol.py's docstring for why.
        weapon = arrokon_adjusted_weapon(weapon, group["pairs"], target_squad)
        weapon = bladestorm_adjusted_weapon(weapon, group["pairs"], target_squad)
        # Nova Charge (Riptide Battlesuit): grants [DEVASTATING WOUNDS] to
        # the one weapon it was spent on. Chained here for the same reason
        # as the four above - it has to be on `weapon` before the wound step
        # below reads the ability off it. Takes `pairs` rather than the
        # already-copied `weapon` to identify the group's weapon, because
        # each copy() above gives the profile a new id() and the grant is
        # keyed by instance identity; see game/nova_charge.py's docstring.
        weapon = nova_charge_adjusted_weapon(weapon, group["pairs"])
        weapon = hand_of_asuryan_adjusted_weapon(weapon, group["pairs"])
        weapon = psychic_communion.psychic_communion_adjusted_weapon(weapon, group["pairs"])
        # Flash Gitz' Ammo Runt (user-supplied): [LETHAL HITS] on this
        # unit's ranged weapons until the end of the phase. Chained here for
        # the same reason as Nova Charge above - the hit step reads the
        # keyword off `weapon`. See game/ammo_runt.py.
        weapon = ammo_runt_adjusted_weapon(weapon, self.active_squad)
        # Exemplars of Mont'ka (The Twin Lance): [SUSTAINED HITS 1] against
        # the closest eligible target. Like Arro'kon it touches
        # [SUSTAINED HITS], which _finish_hit_roll() reads off `weapon` at
        # the hit step below, so it has to be chained in before that branch.
        # The "is it the closest" answer comes from the target-selection
        # snapshot, never recomputed here - see game/exemplars_of_montka.py.
        weapon = exemplars_of_montka.montka_adjusted_weapon(
            weapon, group["pairs"], self._closest_target_snapshot.get(target_squad, False),
        )

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
            )
            results = [_resolve_roll(r, threshold, crit_threshold) for r in rolls]
            hits = sum(1 for r in results if r != "fail")
            crits = sum(1 for r in results if r == "critical")
            misses = len(rolls) - hits
            self._hit_dice_count = len(rolls)
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
            if ones and self._forward_observers_applies(target_squad):
                self._begin_ones_reroll(
                    "hit", ones, threshold, weapon, target_squad, weapon_label, hits=hits, crits=crits,
                    # The 1s are about to be thrown, so they are spent: every
                    # one of them was a miss, hence only the count drops -
                    # free_hits/free_crits are untouched.
                    rerollable=(free_hits, free_crits, len(free) - ones),
                )
            else:
                self._finish_hit_roll(hits, crits, weapon, target_squad, weapon_label, rerollable, threshold)

        elif self.pending_step == "hit_reroll_ones":
            ctx = self._pending_ones_reroll
            self._pending_ones_reroll = None
            results = [_resolve_roll(r, ctx["threshold"]) for r in rolls]
            extra_hits = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            self._log(
                f"{ctx['weapon_label']}: Forward Observers re-roll of 1s {rolls} -> "
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
            wound_threshold = apply_modifiers(wound_threshold, self._wound_modifiers(target_squad))
            crit_threshold = _wound_crit_threshold(weapon, target_squad)
            results = [_resolve_roll(r, wound_threshold, crit_threshold) for r in rolls]
            wounds = sum(1 for r in results if r != "fail")
            crits = sum(1 for r in results if r == "critical")
            no_effect = len(rolls) - wounds
            # Same split as the hit step: what this roll produced overall vs.
            # what part of it may still be re-rolled at all (see
            # _rerollable_dice_indices()). [TWIN-LINKED]/Breach and Clear
            # below may only throw the latter.
            self._wound_dice_count = len(rolls)
            free = self._rerollable_dice_indices(rolls)
            ones = sum(1 for i in free if rolls[i] == 1)
            free_wounds = sum(1 for i in free if results[i] != "fail")
            free_crits = sum(1 for i in free if results[i] == "critical")
            rerollable = (free_wounds, free_crits, len(free) - free_wounds)
            self._log(
                f"{weapon_label} wound roll {rolls}"
                f"{_threshold_note(wound_threshold, _wound_threshold(self._effective_strength(weapon), attached_unit_toughness(target_squad)), self._wound_modifiers(target_squad))}: "
                f"{wounds} wound(s) (of which {crits} critical), {no_effect} no effect."
            )
            if ones and self._forward_observers_applies(target_squad):
                self._begin_ones_reroll(
                    "wound", ones, wound_threshold, weapon, target_squad, weapon_label,
                    wounds=wounds, crits=crits, no_effect=no_effect, crit_threshold=crit_threshold,
                    target_profile=target_profile,
                    # The 1s are about to be thrown, so they are spent: every
                    # one of them was a failure, hence only the failure count
                    # drops.
                    rerollable=(free_wounds, free_crits, len(free) - free_wounds - ones),
                )
            else:
                self._finish_wound_roll(
                    wounds, crits, no_effect, weapon, target_squad, target_profile, weapon_label, wound_threshold,
                    rerollable,
                )

        elif self.pending_step == "wound_reroll_ones":
            ctx = self._pending_ones_reroll
            self._pending_ones_reroll = None
            results = [_resolve_roll(r, ctx["threshold"], ctx["crit_threshold"]) for r in rolls]
            extra_wounds = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            extra_no_effect = len(rolls) - extra_wounds
            self._log(
                f"{ctx['weapon_label']}: Forward Observers re-roll of 1s {rolls} -> "
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
            damage_weapon = melta_adjusted_weapon(weapon, group["pairs"], target_squad)
            if self._precision_choice_needed(weapon, target_squad, group["pairs"]):
                self._offer_precision_choice(rolls, damage_weapon, target_squad, group["pairs"], weapon_label, self.active_squad.owner)
            else:
                self._begin_damage_allocation(rolls, damage_weapon, target_squad, priority_group=None)

        elif self.pending_step == "save_crit_ap":
            # Cadre Fireblade's own "Crack Shot" ability's own Save roll (see
            # _begin_crit_ap_save()) - `weapon` here is the same Bonded
            # Heroes/Starscythe/Drive-by Dakka-adjusted value computed above
            # from the group's raw representative weapon, but
            # crit_ap.adjusted_weapon() sets its AP from the live source,
            # so those adjustments make no difference to the outcome.
            crit_ap_weapon = crit_ap.adjusted_weapon(
                weapon, group["pairs"][0][0], self.active_squad)
            damage_weapon = melta_adjusted_weapon(crit_ap_weapon, group["pairs"], target_squad)
            if self._precision_choice_needed(crit_ap_weapon, target_squad, group["pairs"]):
                self._offer_precision_choice(rolls, damage_weapon, target_squad, group["pairs"], weapon_label, self.active_squad.owner)
            else:
                self._begin_damage_allocation(rolls, damage_weapon, target_squad, priority_group=None)

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
            if self._lethal_hits_choice_needed(weapon, crits):
                self._offer_lethal_hits_choice(hits, crits, weapon, target_squad, weapon_label, self.active_squad.owner)
            else:
                self._continue_after_hit_roll(hits, 0, weapon, target_squad, weapon_label)
        else:
            self._finish_group()

    def _lethal_hits_choice_needed(self, weapon, crits):
        """Rule 24.23 ([LETHAL HITS]): the choice only exists when there's
        at least one critical hit to choose for, and only if we actually
        have a DecisionManager to pause on (it's optional, like dice_manager
        elsewhere in this file's test-friendly design)."""
        return weapon.lethal_hits and crits > 0 and self.decision_manager is not None

    def _offer_lethal_hits_choice(self, hits, crits, weapon, target_squad, weapon_label, owner):
        """"Each time an attack... results in a critical hit, you can choose
        for that attack to automatically wound the target" - since crit dice
        are fungible, "choose per attack" reduces to "choose how many of the
        `crits` critical hits to auto-wound" (0..crits); the Designer's Note
        explains the real tension (an auto-wound is never itself a critical
        wound, so it can't trigger e.g. [DEVASTATING WOUNDS]) which is why
        this is a genuine choice, not an automatic "always take it"."""
        options = []
        for n in range(crits, -1, -1):
            label = f"Auto-wound {n} of {crits} critical hit(s)" if n > 0 else "Roll all hits normally"
            options.append((
                label,
                lambda n=n: self._continue_after_hit_roll(hits, n, weapon, target_squad, weapon_label),
            ))
        self.decision_manager.request(
            owner, f"{weapon_label}: [LETHAL HITS] - how many critical hits should automatically wound?", options,
        )

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
            log=self._log,
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
            wound_modifiers = self._wound_modifiers(target_squad)
            wound_threshold = apply_modifiers(wound_threshold, wound_modifiers)
            label = f"Wound Roll: {weapon_label} ({remaining} hit(s))"
            if wound_modifiers:
                label += f" [{describe_modifiers(wound_modifiers)}]"
            self.dice_manager.roll(
                count=remaining, sides=6,
                label=label,
                success_threshold=wound_threshold,
                target_name=target_squad.name, roll_kind=WOUND_ROLL,
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
        if self._offer_aspect_shrine_wound(weapon, target_squad, target_profile, weapon_label, wounds, crits):
            return
        self._resolve_wounds_now(weapon, target_squad, target_profile, weapon_label, wounds, crits)

    def _offer_aspect_shrine_wound(self, weapon, target_squad, target_profile, weapon_label, wounds, crits):
        """See _offer_aspect_shrine_hit(). The failure count is derived the
        same exact way: _wound_dice_count is how many hits went into this
        group's wound roll, which no re-roll changes."""
        if self.decision_manager is None or self.current_group is None or self._aspect_shrine_wound_offered:
            return False
        squad = self.active_squad
        pairs = self.current_group.get("pairs") or ()
        model = pairs[0][0] if pairs else None
        no_effect = 0 if self._wound_dice_count is None else max(0, self._wound_dice_count - wounds)
        source, change = _unmodified_six_source(
            "wound_change", squad, model, weapon, wounds, crits, no_effect)
        if change is None:
            return False
        self._aspect_shrine_wound_offered = True
        new_wounds, new_crits, _new_no_effect, what = change

        def spend():
            source.spend(squad)
            self._log(
                f"{weapon_label}: {source.ACCEPT_LABEL} - one wound roll counts as an unmodified 6 "
                f"({wounds} wound(s) of which {crits} critical -> {new_wounds} of which {new_crits})."
            )
            self._resolve_wounds_now(weapon, target_squad, target_profile, weapon_label, new_wounds, new_crits)

        def keep():
            self._resolve_wounds_now(weapon, target_squad, target_profile, weapon_label, wounds, crits)

        self.decision_manager.request(
            squad.owner, source.prompt_for(squad, weapon_label, what, "wound"),
            [(source.ACCEPT_LABEL, spend), ("Keep the roll", keep)],
        )
        return True

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

            save_threshold = _parse_threshold(target_profile.armor_save)
            if save_threshold is not None:
                save_threshold += -weapon.ap
            # Melta-adjusted damage preview (rule 24.25) - positions don't
            # change between kicking off this roll and its acknowledgement,
            # so this is the same value _begin_damage_allocation() will use.
            # None (suppresses DicePanel's "N attack(s) get through..."
            # summary line) whenever Damage is dice-notation - there's no
            # single fixed number to preview until DamageAllocationSession
            # actually rolls it per failed save, see its own docstring.
            melta_weapon = melta_adjusted_weapon(weapon, self.current_group["pairs"], target_squad)
            damage_preview = None if melta_weapon.damage_notation is not None else melta_weapon.damage
            self.dice_manager.roll(
                count=normal_wounds, sides=6,
                label=f"Save Roll: {weapon_label} ({normal_wounds} wound(s))",
                success_threshold=save_threshold if save_threshold is not None else 7,
                target_name=target_squad.name, roll_kind=SAVE_ROLL,
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
        if monster_hunters.applies(self.active_squad, target_squad):
            return monster_hunters.MONSTER_HUNTERS_REROLL_LABEL
        # Fire Dragons' Assured Destruction - the only other source, and the
        # first that is phase-restricted ("in YOUR Shooting phase"), which is
        # why it is the one that reads the turn tracker.
        if assured_destruction.applies(self.active_squad, target_squad, self.turn_tracker):
            return assured_destruction.ASSURED_DESTRUCTION_LABEL
        return None

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

    def _offer_hit_reroll_choice(self, hits, crits, weapon, target_squad, weapon_label, hit_threshold, rerollable, owner):
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
        options = []
        if free_misses > 0:
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
            success_threshold=hit_threshold, target_name=target_squad.name, roll_kind=HIT_ROLL,
            is_reroll=True,  # these dice have now used their one re-roll
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
        return None

    def _wound_reroll_is_full(self, weapon, target_squad):
        """Whether the re-roll granted right now covers the WHOLE Wound roll
        or only its failed dice.

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
        )

    def _twin_linked_choice_needed(self, weapon, no_effect, target_squad):
        """Pointless to offer with zero failures, and only offered once per
        weapon group's attack sequence (_twin_linked_used, reset per group
        in _begin_resolution - "each time an attack is made" means each
        attack SEQUENCE gets its own chance, not the whole squad activation)."""
        reason = self._wound_reroll_reason(weapon, target_squad)
        return reason is not None and no_effect > 0 and self.decision_manager is not None and not self._twin_linked_used

    def _offer_twin_linked_choice(self, no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, owner, rerollable):
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
            target_name=target_squad.name, roll_kind=WOUND_ROLL,
            is_reroll=True,  # these dice have now used their one re-roll
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
        damage_override = None
        if weapon.damage_notation is not None and branching_fates.available(self.active_squad):
            damage_override = branching_fates.BranchingFatesDamageOffer(
                squad=self.active_squad, decision_manager=self.decision_manager,
                game_log=self.game_log, owner=self.active_squad.owner, weapon_name=weapon.name,
            )
        self.damage_session = DamageAllocationSession(
            rolls, weapon, target_squad, dice_manager=self.dice_manager, log=self._log, priority_group=priority_group,
            stealth_drones=self.stealth_drones, waaagh=self.waaagh, damage_reroll=damage_reroll,
            damage_override=damage_override,
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
        if rolls is not None:
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

        save_threshold = _parse_threshold(target_profile.armor_save)
        if save_threshold is not None:
            save_threshold += -crit_ap_weapon.ap
        melta_weapon = melta_adjusted_weapon(crit_ap_weapon, self.current_group["pairs"], target_squad)
        damage_preview = None if melta_weapon.damage_notation is not None else melta_weapon.damage
        self.dice_manager.roll(
            count=crits, sides=6,
            label=(f"Save Roll: {weapon_label} ({crit_source}, AP{crit_ap_weapon.ap}, "
                   f"{crits} critical wound(s))"),
            success_threshold=save_threshold if save_threshold is not None else 7,
            target_name=target_squad.name, roll_kind=SAVE_ROLL,
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

        # Rule 24.15 ([HAZARDOUS]): count this as one of the "[HAZARDOUS]
        # weapons you selected in the Select Weapons step" - once per
        # weapon SELECTION (i.e. once total, even if it got cover-split
        # into two physical dice sequences above), not once per model or
        # per physical dice sequence.
        if self._pending_subgroups_hazardous:
            self._hazardous_count += 1
            self._pending_subgroups_hazardous = False

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

    def _actually_finish_squad(self):
        # Rule 19.04: "the ability it was conferring upon the attached unit
        # applies until the attacking unit has resolved all of its attacks"
        # - that is exactly here, so every attached unit this activation hit
        # stops extending a wiped-out component's abilities now. Closed
        # before the early-return-free bookkeeping below so a reactive Snap
        # Shooting activation (15.09) closes its window too.
        for hit_squad in self._hit_target_squads_this_activation:
            attached_units.end_attack_sequence(hit_squad)
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
        if self.turn_tracker is not None:
            # Rule 13.09 (Hidden): tracks when this unit last made a ranged
            # attack, in its owner's own turn-number terms.
            self.last_ranged_attack_turn[self.active_squad] = self.turn_tracker.turn_number_for(self.active_squad.owner)
        self.active_squad = None
        self.shooting_type = None
        self.available_types = []
        self.target_squad = None
        self.remaining_weapon_types = []
        self.pending_step = None
        self._reset_target_snapshots()
        self.state = IDLE
        self._finish_activation()

    def _log(self, message):
        if self.game_log is not None:
            player = self.turn_tracker.active_player if self.turn_tracker is not None else self.player_name
            self.game_log.add(f"{player}: {message}")
