from collections import Counter

from game import attached_units
from game import coldstar
from game import config  # imports nothing itself, so this cannot cycle
from game.modifiers import Modifier
from game.terrain import DENSE
from game.thresholds import parse_threshold

COHERENCY_RANGE_IN = 2.0
MAX_SPREAD_IN = 9.0


def spread_limit_applies(squad):
    """Whether rule 09.02's MAX_SPREAD_IN half is enforced for this unit - see
    config.SPREAD_LIMIT_PLAYERS for the house rule and the measurements behind
    it.

    Keyed on the OWNER, exactly like terrain.may_cross_walls(), and for the
    same reason: it lifts a handicap off the AI while the human keeps playing
    the printed rule. Anything whose owner cannot be determined gets the strict
    answer, so a duck-typed probe is never accidentally granted a permission
    the human does not have.

    The 2" single-connected-group half is NOT covered by this and stays in
    force for everyone - that is the half that stops a unit being strung out
    across the board, which is what the limit was protecting against."""
    owner = getattr(squad, "owner", None)
    return owner in config.SPREAD_LIMIT_PLAYERS
ENGAGEMENT_RANGE_IN = 2.0  # rule 03.04 also has a 5" vertical component we don't model on a flat 2D board
OBJECTIVE_CONSOLIDATION_RANGE_IN = 3.0  # rule 12.08: both "within 3\" of an objective" (eligibility) and "within range of the selected objective" (after moving) share this one number


def edge_distance(a, b):
    # Measured from base edge to base edge, not center to center.
    center_dist = ((a.x_in - b.x_in) ** 2 + (a.y_in - b.y_in) ** 2) ** 0.5
    return max(0.0, center_dist - a.radius_in - b.radius_in)


def model_engaged_with(model, other_squad):
    """Rule 12.02: is this specific model within Engagement Range of
    other_squad - unlike Squad.is_engaged_with, which only needs one model
    pair anywhere in the two squads to be true, so a squad-wide "yes" doesn't
    mean every individual model qualifies to attack that target."""
    return any(edge_distance(model, other) <= ENGAGEMENT_RANGE_IN for other in other_squad.models)


def model_terrain_violation(model, obstacles, x_in=None, y_in=None):
    """Rule 13.05: True if model's position overlaps a Dense terrain feature -
    the single-model primitive behind Squad.check_terrain() and
    MovementController.try_commit_segment()'s instant per-model check.
    Applies unconditionally (no FLYING/Desperate Escape exception - those
    flags only loosen what clamp_move() allows a model to pass *through*
    mid-drag, never the legality of where it actually ends up).

    `x_in`/`y_in` ask the same question about a HYPOTHETICAL position instead
    of where the model currently stands, so a caller weighing candidate spots
    does not have to move the model there and back to find out (the AI's charge
    odds ask exactly this of every possible engagement position)."""
    x = model.x_in if x_in is None else x_in
    y = model.y_in if y_in is None else y_in
    return any(
        o.category == DENSE and o.overlaps_circle(x, y, model.radius_in)
        for o in obstacles
    )


def model_overlaps_any(model, all_tokens, exclude=frozenset()):
    """Rule 03.01 (ending a move): True if model overlaps any OTHER token in
    all_tokens (friendly or enemy), except those in `exclude` - e.g.
    squadmates that haven't been placed yet this move and are still sitting
    at a stale pre-move position (same exclusion SetupController.
    position_valid() and _clamp_target_against_friendly_models() already
    use). The single-model primitive behind Squad.check_model_overlap()."""
    for other in all_tokens:
        if other is model or other in exclude:
            continue
        center_dist = ((model.x_in - other.x_in) ** 2 + (model.y_in - other.y_in) ** 2) ** 0.5
        if center_dist < model.radius_in + other.radius_in:
            return True
    return False


def is_monster_or_vehicle_unit(squad):
    """True if every model in squad has the MONSTER or VEHICLE keyword -
    used by rule 06.03 (hazard rolls) and rule 10.06 (close-quarters
    shooting)."""
    return all(m.profile.monster or m.profile.vehicle for m in squad.models)


def tank_hunters_modifiers(attacking_model, target_squad):
    """Tankbustas' own "Tank Hunters" ability (user-supplied, not a core
    rule): "each time a model in this unit makes an attack that targets a
    MONSTER or VEHICLE unit, add 1 to the Hit roll and add 1 to the Wound
    roll" - a bonus to both, so per this engine's Modifier sign convention
    (positive worsens a threshold, negative improves it) that's -1 to each.
    Shared by game/shooting.py's and game/fight.py's own _hit_modifiers()/
    _wound_modifiers(), since the ability isn't restricted to ranged
    attacks - depends only on the attacking MODEL's own ability and the
    TARGET unit's keywords, not on which phase the attack happens in."""
    if not attacking_model.profile.tank_hunters or not is_monster_or_vehicle_unit(target_squad):
        return []
    return [Modifier(-1, "Tank Hunters (MONSTER/VEHICLE)")]


def allocation_target_profile(squad):
    """The profile an attack against this unit should resolve its SAVE
    against: the first allocation group that still has a living model.

    Save rolls are batched here - one threshold for a whole group of wounds,
    with DamageAllocationSession then handing the failures out model by model
    (rules 05.03/05.04). That batching is exact while every model in the unit
    shares a save, which was true of every Squad before attached units
    existed. It stops being exact the moment a 2+ Warboss stands in a mob of
    6+ Boyz.

    Reading models[0] would pick an arbitrary model. Reading the first
    allocation group picks the one the rules say actually takes the wounds:
    05.03 orders non-CHARACTER groups first, so a character in a unit does
    not lend its better save to the bodyguards being shot off in front of
    it - and once those bodyguards are gone, the group order advances and
    the character's own save applies, unprompted.

    Still an approximation for a unit whose bodyguard models themselves have
    mixed saves and are all hit in one batch; the exact rule would roll each
    save separately. Left batched deliberately - that is a pre-existing
    property of this engine's dice flow, not something attached units
    introduced, and splitting it would mean a dice roll per model."""
    for group in squad.allocation_groups():
        if any(not m.is_dead() for m in group):
            return group[0].profile
    return squad.models[0].profile if squad.models else None


def max_model_radius(squad, default=0.5):
    """The largest base radius in the unit.

    Every "lay this squad out" geometry helper (disembark rings, Ingress
    spreads, charge engagement slots, exposure probes) used to read
    squad.models[0].radius_in as THE radius, which was exactly right while a
    Squad was homogeneous. Attached units (19.01) break that assumption for
    the first time: a Warboss (0.98") merged into a Boyz mob (0.63") makes
    models[0] the SMALL one, so spacing computed from it is too tight and the
    character overlaps its neighbours - rule 03.01 then rejects the whole
    placement at every candidate point on the board. That is the same
    self-collision failure this file's disembark-gap comment already
    documents for uniformly wide squads, and it is why these helpers must
    size against the widest model rather than an arbitrary one.

    Deliberately the MAX rather than a mean: these are all clearance
    questions, where being too generous merely spreads a unit out slightly
    more than necessary, while being too tight fails placement outright."""
    return max((m.radius_in for m in squad.models), default=default)


def min_model_movement(squad, default=0.0):
    """The slowest model's Move characteristic - what the UNIT can guarantee
    to cover in one move.

    Movement itself is already per-model (MovementController budgets each
    model its own effective Move), so this is only for the planning/AI side,
    which asks "how far can this unit get this turn" as a single number. For
    an attached unit that number is the slowest component's: coherency (09.02)
    keeps the unit together, so a fast Character attached to a slow bodyguard
    unit does not actually get to travel at its own speed.

    Reads the EFFECTIVE Move, not the printed one, so an ability that
    overrides it is not invisible to the planner. Coldstar Commander is the
    case that makes the difference: it sets its whole unit to 12", so the old
    "slowest printed characteristic" answer reported a led Crisis team at 8"
    - the exact shape of gap that has repeatedly made the planner write orders
    the Movement phase could actually have carried out."""
    return min((coldstar.effective_movement_in(m) for m in squad.models), default=default)


def strongest_model(squad, alive_only=True):
    """The single model that best represents this unit's power - ranked by
    Wounds first (ties broken by Toughness, then base size), the same
    "durability" signal that already distinguishes a leader/character model
    on a real datasheet from the rank-and-file around it: a Boss Nob prints
    2 wounds against a Boy's 1, an attached Warboss/Commander/Cadre
    Fireblade prints 6 against a squad in the low single digits - no
    attached-unit-specific logic is needed, the same "most wounds" rule
    picks out both cases.

    User request: while a squad is embarked (18.02) its models are pulled
    off the board entirely, so there was no way to tell what a TRANSPORT
    was actually carrying without opening its passengers' datacard -
    Renderer.draw_embarked_passengers() shows this model's icon pinned
    above the TRANSPORT at all times instead."""
    models = [m for m in squad.models if not m.is_dead()] if alive_only else list(squad.models)
    if not models:
        return None
    return max(models, key=lambda m: (m.profile.wounds, m.profile.toughness, m.radius_in))


def unit_wide_ability(squad, attribute):
    """Shared implementation of every "does this unit have ability X"
    predicate below, which are all phrased on their datasheets as "while
    every model in a unit has this ability".

    For an ordinary unit that is exactly all(...) over its models, as it
    always was. For an attached unit (19.01) it is rule 19.04 instead: an
    ability applies "to every model in an attached unit, until the source
    of that ability/rule is destroyed", so a Warboss joining a Boyz mob does
    NOT strip the mob of Get Da Good Bitz - the bodyguard component is still
    the source and still confers it on the whole unit. A naive all()-over-
    merged-models would silently delete an ability from every unit a
    character joins, which is the single most likely way attaching a leader
    could break a datasheet."""
    return attached_units.unit_has_ability(squad, lambda m: getattr(m.profile, attribute))


def squad_has_fights_first(squad):
    """A unit is a Fights First unit either via rule 11.04's temporary
    post-charge grant (Squad.fights_first, cleared at end of turn) or rule
    24.13's permanent datasheet ability, granted only "while every model in
    a unit has this ability" (UnitProfile.fights_first)."""
    return squad.fights_first or unit_wide_ability(squad, "fights_first")


def squad_is_attached_unit(squad):
    """Whether this squad is an attached unit (19.01) - used by rule 24.24
    (LONE OPERATIVE)'s "unless part of an attached unit" carve-out.

    This used to answer "does the squad contain a Leader/Support model",
    because merging one in by hand was the only way an attached unit could
    exist and there was no record of how a squad had been assembled. That
    proxy has a false positive that now matters: a Leader unit that is NOT
    attached to anything - a Commander sitting alone in Reserves - also
    contains a Leader model, and so was wrongly stripped of Lone Operative
    exactly when it was most entitled to it. Both of this engine's Lone
    Operative datasheets are Leader units, so the carve-out was effectively
    always on.

    With game/attached_units.py recording real provenance, the question can
    be answered properly: a unit built by attach() knows its components. The
    keyword heuristic is kept only as a fallback for a squad that was never
    formed by attach() (hand-built test squads), and tightened to require a
    genuine MIX - a leader model AND a non-leader model in one unit - which
    is what "attached" actually means and which a lone Character fails."""
    if attached_units.is_attached_unit(squad):
        return True
    has_leader = any(m.profile.leader or m.profile.support for m in squad.models)
    has_bodyguard = any(not (m.profile.leader or m.profile.support) for m in squad.models)
    return has_leader and has_bodyguard


def attached_unit_toughness(squad):
    """Rule 19.02: an attached unit (19.01 - formed by
    game.attached_units.attach(), which merges a Leader/Support unit's
    models into the bodyguard unit's own Squad.models so the two become
    "a single unit for all rules purposes") resolves attacks against it
    using the highest Toughness among its bodyguard models, even if an
    attached Leader/Support model has a different T - or, once no bodyguard
    models are left alive, the highest T among the remaining Leader/Support
    models instead. For an ordinary (non-attached) unit every model shares
    the same T anyway, so this is a safe drop-in replacement for reading
    a single representative model's toughness.

    Which models count as "bodyguard" comes from the recorded components
    when the unit was really formed by attach(), and falls back to reading
    the Leader/Support profile flags directly otherwise - so a hand-built
    squad (tests, and every squad predating this module) still behaves.

    Gretchin's own "Runtherd" ability (user-supplied, not a core rule):
    "each time an attack targets this unit, if it contains one or more
    Gretchin models, ... Runtherd models in this unit have a Toughness
    characteristic of 2" - modeled as a per-model effective-toughness
    override right here, rather than a separate function, since it's the
    exact same "what T does this attack actually resolve against" question
    this function already answers (and it needs to interact correctly with
    the SAME bodyguard/leader pooling logic above: once every Gretchin
    model is dead, `has_gretchin` goes False and a Runtherd's own real T
    applies again, unprompted)."""
    alive = [m for m in squad.models if not m.is_dead()]
    if not alive:
        alive = squad.models
    bodyguards = [m for m in attached_units.bodyguard_models(squad) if m in alive]
    pool = bodyguards if bodyguards else alive
    has_gretchin = any(m.profile.gretchin for m in alive)

    def _effective_toughness(model):
        if has_gretchin and model.profile.runtherd_shares_gretchin_toughness:
            return 2
        return model.profile.toughness

    return max(_effective_toughness(m) for m in pool)


def _current_and_starting_strength(squad):
    """Shared basis for the Appendix's "Starting Strength and Half-Strength"
    definitions: a unit with starting strength 1 (a single model, e.g. a
    Vehicle or Monster) compares Wounds; a unit with starting strength 2+
    compares model count. Which branch applies is keyed off STARTING
    strength, not current model count - so an attached unit reduced to just
    its Leader still uses the model-count rule, exactly as the Appendix's
    own worked example describes: "the remaining Captain would be below
    half-strength, despite having his full wounds remaining"."""
    if squad.starting_model_count <= 1:
        model = squad.models[0] if squad.models else None
        current = model.current_wounds if model is not None else 0
        starting = model.profile.wounds if model is not None else max(squad.starting_model_count, 1)
        return current, starting
    return len(squad.models), squad.starting_model_count


def is_below_starting_strength(squad):
    """Appendix ("Starting Strength and Half-Strength"): fewer remaining
    models (or, for a starting-strength-1 unit, fewer remaining wounds)
    than the unit had at the start of the first battle round."""
    current, starting = _current_and_starting_strength(squad)
    return current < starting


def is_at_half_strength(squad):
    """Rule 08.03 needs "at half-strength or below" as a single combined
    check (both trigger the same Battle-Shock requirement there), so this
    covers both - the Appendix's EXACT (not rounded) half: current <=
    starting/2, kept in integers as 2*current <= starting. Fixes an earlier
    ceiling-division approximation (before the Appendix text was available)
    that overcounted "at half-strength" by one model for odd starting
    strengths - e.g. starting=5 has no unit count that's exactly half (2.5),
    only below it, but the old rounded-up formula wrongly treated 3
    remaining models (which is ABOVE half) as already being at half-strength."""
    current, starting = _current_and_starting_strength(squad)
    return 2 * current <= starting


def is_below_half_strength(squad):
    """Appendix: "Below Half-Strength" specifically - strictly less than
    half, as opposed to is_at_half_strength()'s "at or below"."""
    current, starting = _current_and_starting_strength(squad)
    return 2 * current < starting


def _group_weakness(models):
    """Sort key for automatic wound-allocation ordering (rule 05.03): weakest
    group first. 'Weakest' is decided, in order, by whether the group has
    already lost any wounds, how depleted it is (as a fraction, so it's fair
    across models with different W), how many wounds it can actually soak,
    and how poor its armor save is.

    That third term was missing and made this key put the SQUAD LEADER
    first in every squad whose leader is simply tougher than its rank and
    file (user report: "bei mir wird die erste wunde auch automatisch auf
    den squad leader gelegt"). A fresh 2W Boss Nob and a fresh 1W Boy both
    score is_undamaged=True and fraction=1.0, and they share an armor save,
    so all three terms tied - and a tie is resolved by the stable sort,
    i.e. by datasheet order, which lists the leader first. Result: the
    leader's group came first, it was the group's only model, so no choice
    was ever offered to EITHER player and every wound went onto the leader
    until it died. Comparing absolute remaining wounds breaks that tie the
    right way round: a 1-wound model is the weaker, more expendable one.
    Measured to flip Strike Team (Shas'ui 2W), Breacher Team, Boyz,
    Stormboyz and Warbikers (Boss Nob 2W/2W/4W); Gretchin already came out
    right by accident, because the Runtherd's better save broke the tie
    first.

    Where the leader shares its squad's W AND Sv it shares its allocation
    GROUP, so no group ordering can help - that half is the defending
    player's within-group pick (a human click, or the AI's own
    _wound_allocation_pick(), which likewise puts the leader last)."""
    is_undamaged = all(m.current_wounds >= m.profile.wounds for m in models)
    wounds_fraction_remaining = min(m.current_wounds / m.profile.wounds for m in models)
    wounds_remaining = min(m.current_wounds for m in models)
    save_threshold = parse_threshold(models[0].profile.armor_save) or 7  # no save = weakest
    return (is_undamaged, wounds_fraction_remaining, wounds_remaining, -save_threshold)


class Squad:
    """Groups several models (Tokens) together. Every model always belongs to
    exactly one squad, even if that squad only has one model in it."""

    def __init__(self, name, models, owner="Player 1", points=None):
        self.name = name
        self.models = models
        self.owner = owner  # which player controls this squad
        self.points = points  # this unit's cost from its faction's published points list, as computed by build_squad(); None = not priced (no list for that faction yet, see game/factions/points.py). Purely informational - no army-building flow spends it yet
        self.battle_shocked = False  # rules 08.03/09.07 set this; the roll itself is game.battle_shock.BattleShockController
        self.charged_this_turn = False  # rule 11.04: this unit made a Charge move this turn. A SEPARATE flag from fights_first below, which looks like it would do - but game/counteroffensive.py (15.12) also sets that one, so it means "fights first" and not "charged". Read by game/crit_hit.py for Striking Scorpions' Mandiblasters; cleared at end of turn
        self.fights_first = False  # rule 11.04/24.13 sets this; nothing clears it at end of turn yet (no Fight phase to consume it)
        self.stim_injectors_active = False  # Retaliation Cadre's Stim Injectors stratagem: "until the end of the phase, models in your unit have the Feel No Pain 6+ ability" - see game/stim_injectors.py. A unit-level flag rather than a controller threaded into each damage source, so it reaches EVERY one of them (including Crushing Impact/Deadly Demise/Explosives/Hazardous mortal wounds, which game/waaagh.py's own conditional FNP documents itself as NOT reaching). Cleared on every phase change, alongside StratagemController.reset_phase()
        self.arrokon_protocol_active = False  # Retaliation Cadre's The Arro'kon Protocol stratagem: "until the end of the phase", this unit's attacks have [SUSTAINED HITS 1] against enemy units of 6+ models ([SUSTAINED HITS 2] against 11+) - see game/arrokon_protocol.py. A unit-level flag for the same reason stim_injectors_active is one, and cleared in the same place
        self.ere_we_go_active = False  # War Horde's 'Ere We Go stratagem: "until the end of the turn, add 2 to Advance and Charge rolls made for your unit" - see game/ere_we_go.py. A unit-level flag like the two below, but cleared at END OF TURN (alongside fights_first/set_up_this_turn/charge_locked_until_end_of_turn), not on every phase change
        self.ard_as_nails_active = False  # War Horde's 'Ard as Nails stratagem: "until the end of the phase, each time an attack targets your unit, subtract 1 from the Wound roll" - see game/ard_as_nails.py. A unit-level flag for the same reason stim_injectors_active is one, and cleared in the same place
        # The three Aeldari Agile Manoeuvres (army rule Battle Focus, see
        # game/battle_focus.py). Unit-level flags for the same reason as the
        # four above, but note the two DIFFERENT lifetimes: Swift as the Wind
        # is "until the end of the phase" and is cleared with the phase flags,
        # while Star Engines and Flitting Shadows are "until the end of the
        # turn" and are cleared with ere_we_go_active/fights_first.
        self.swift_as_the_wind_active = False  # add 2" to this unit's Move characteristic - read by game/coldstar.py's effective_movement_in()
        self.star_engines_active = False       # this unit's ranged weapons have [ASSAULT] - read by game/coldstar.py's weapon_has_assault()
        self.flitting_shadows_active = False   # enemies cannot Fire Overwatch (15.08) at this unit - read by game/shooting.py's _is_valid_target_squad(), gated on Snap Shooting
        self.sudden_strike_active = False      # Pile-in/Consolidation moves may go 6" instead of 3" - read by game/pile_in.py and game/consolidate.py; phase lifetime, like swift_as_the_wind_active
        self.neocapacitor_shielded = False  # The Twin Lance's Neocapacitor Shields: -1 to Charge rolls made for this unit "until the end of the turn" - see game/neocapacitor_shields.py. A unit-level flag like ere_we_go_active, and cleared in the same end-of-turn place
        self.nova_charge_grants = {}  # Riptide Battlesuit's Nova Charge ability: {model.id -> {weapon instance id, ...}} that have [DEVASTATING WOUNDS] "until the end of the phase" - see game/nova_charge.py. A dict rather than a bool like the flags around it because this ability names ONE weapon of one model, not the whole unit; cleared on every phase change in the same place they are
        self.spirit_of_gork_strength = False  # Kill Rig's Spirit of Gork: "until the end of the phase, add 1 to the Strength characteristic of melee weapons equipped by models in that unit" - see game/spirit_of_gork.py. A unit-level flag for the same reason the others here are (the buff lands on a unit that is not the one being resolved when a fight happens), and cleared in the same place
        self.spirit_of_gork_lethal = False  # Kill Rig's Spirit of Gork, the "on a 6" half: those same weapons also gain [LETHAL HITS]
        self.ammo_runt_active = False  # Flash Gitz' Ammo Runt wargear: "until the end of the phase, ranged weapons equipped by models in this unit have the [LETHAL HITS] ability" - see game/ammo_runt.py. A unit-level flag for the same reason the ones above are, and cleared in the same place
        self.unbridled_carnage_active = False  # War Horde's Unbridled Carnage stratagem: "until the end of the phase", this unit's melee attacks score a Critical Hit on an unmodified hit roll of 5+ - see game/unbridled_carnage.py. A unit-level flag for the same reason the two above are, and cleared in the same place
        self.ingress_locked = False  # rule 20.04: set on a successful Ingress move, cleared once the next Charge phase begins
        self.aspect_shrine_tokens = 0  # ASPECT WARRIORS wargear: how many Aspect Shrine tokens this unit was built with (starting strength // 5) - set by build_squad(), see game/aspect_shrine.py
        self.aspect_shrine_tokens_used = 0  # ...and how many of them have been spent. Once per battle each, so this only ever grows
        self.flickerjump_active = False  # Warp Spiders' Flickerjump: "until the end of the turn, models in it have a Move characteristic of 24 inches" - read by game/coldstar.py's effective_movement_in() as an OVERRIDE, not a bonus. The other half of the ability ("not eligible to declare a charge") reuses charge_locked_until_end_of_turn below rather than adding a second flag with the same lifetime; see game/flickerjump.py
        self.disembarked_from_this_turn = None  # the TRANSPORT token this unit disembarked from this turn, if any - set by TransportController.confirm_disembark(), read by game/fire_support.py, cleared at end of turn alongside the flags below
        self.charge_locked_until_end_of_turn = False  # rules 18.04/18.05: Rapid/Combat Disembark and Emergency Disembark set this
        self.fell_back_this_turn = False  # rule 09.07: a Fall Back move sets this - blocks shooting/charging until end of turn, cleared alongside charge_locked_until_end_of_turn
        self.set_up_this_turn = False  # rule 18.02: blocks embarking the same turn a unit was set up; cleared at end of turn
        self.embarked_in = None  # rule 18.02: the TRANSPORT Token this squad is embarked within, or None if it's on the battlefield
        self.starting_model_count = len(models)  # the Appendix's "starting strength" - see is_at_half_strength() etc. game.attached_units.attach() re-derives this from the merged components when an attached unit (19.01) is formed, so it stays the whole unit's starting strength
        self.datasheet = None  # the game.factions.datasheet.Datasheet this unit was built from, set by build_squad() - None for a hand-built Squad. Needed by rule 19.01's "can only lead specific bodyguard units" pairing lookup (see game/attached_units.py's leadable_unit_names())
        self.attached_components = []  # rule 19.01: one game.attached_units.AttachedComponent per unit merged into this one, empty for an ordinary unit - the provenance 19.02/19.04 need after the merge
        self.attached_ability_grace = False  # rule 19.04's "applies until the attacking unit has resolved all of its attacks" window - see game/attached_units.py's begin/end_attack_sequence()
        self.destroyed_models = []  # every Token of this unit that has been removed by GameState.remove_dead_models(), oldest first. Kept because a model removed from `models` is otherwise unrecoverable, and one ability now puts models BACK: Painboy's Grot Orderly (see game/grot_orderly.py). Purely a record - no rule reads it except that one, and nothing here resurrects anything on its own
        self.absorbed_into = None  # set on a leader Squad that attach() merged away, pointing at the attached unit that now owns its models - so a stale reference can be followed rather than silently acting on an empty squad
        for model in models:
            model.squad = self

    def check_coherency(self):
        """Returns a list of violation messages; empty list means the squad
        is fine. Rule 09.02 requires the unit to form a SINGLE group - not
        merely that each model individually has some neighbor within 2".
        Real bug found via a live user report (their own game log showed a
        5-model squad's exact final positions after a move): a per-model
        "does THIS model have any neighbor at all" check can be satisfied
        by two or more mutually-coherent sub-clusters that are, as a whole,
        disconnected from one another - 2 models 0.69" apart, the other 3
        0.35-0.46" apart from each other, but every cross-link between the
        two groups over 2" (max pairwise spread 8.18", still under
        MAX_SPREAD_IN) - the OLD check (each model's own nearest neighbor)
        saw every model individually satisfied and missed the unit having
        split into two pieces entirely. Became far more likely to actually
        occur once each model started routing independently around
        obstacles/other units (this session's "Umbau Bewegung" movement
        refactor and the per-model movement fixes before it) rather than
        moving as one rigid block, which could never produce two separate
        clusters by construction - but the gap in this check itself
        predates that and isn't specific to it. Fixed via graph
        connectivity: build the "within 2\"" adjacency graph over every
        model in the unit and verify it's a single connected component - an
        isolated model with zero neighbors at all is simply the degenerate
        case of "not connected to the rest", so this subsumes the old
        check rather than needing it kept separately."""
        if len(self.models) <= 1:
            return []

        errors = []

        reachable = {self.models[0]}
        frontier = [self.models[0]]
        while frontier:
            current = frontier.pop()
            for other in self.models:
                if other not in reachable and edge_distance(current, other) <= COHERENCY_RANGE_IN:
                    reachable.add(other)
                    frontier.append(other)
        if len(reachable) < len(self.models):
            errors.append(
                f'Not every model is within {COHERENCY_RANGE_IN}" of another model in a single connected group.'
            )

        # Second half, and it is house-ruled per owner - see
        # spread_limit_applies(). Skipping the whole O(n^2) sweep rather than
        # computing it and discarding the answer: for a 22-model unit this is
        # 231 pairs, and check_coherency() is called several times per
        # candidate placement by the AI's movement search.
        if spread_limit_applies(self):
            max_dist = max(
                edge_distance(a, b)
                for i, a in enumerate(self.models)
                for b in self.models[i + 1:]
            )
            if max_dist > MAX_SPREAD_IN:
                errors.append(
                    f'The squad is spread too far apart (max {MAX_SPREAD_IN}" between any two models).'
                )

        return errors

    def check_terrain(self, obstacles):
        """Returns a list of violation messages; empty list means no model
        ends its move on a Dense terrain feature (a wall - rule 13.05).
        INFANTRY/BEASTS/SWARM/MOBILE models can move horizontally *through*
        Dense terrain (rule 13.06, see Obstacle.blocks_movement_for()), but
        that's about crossing it mid-move, not finishing the move standing
        on/in it - every model, regardless of keywords, must end up clear of
        it. Exposed (13.03) and Light (13.04) terrain never block ending a
        move there."""
        for model in self.models:
            if model_terrain_violation(model, obstacles):
                return ["Models cannot end their move on top of Dense terrain (walls)."]
        return []

    def check_model_overlap(self, all_tokens):
        """Rule 03.01 (ending a move): no model may end up on top of another
        model, friendly or enemy."""
        for model in self.models:
            if model_overlaps_any(model, all_tokens):
                return ["Models cannot end their move on top of another model."]
        return []

    def is_engaged(self, all_tokens):
        """Rule 03.04: this squad is engaged if any of its models is within
        engagement range (2") of any enemy model."""
        for model in self.models:
            for other in all_tokens:
                if other.squad is None or other.squad is self or other.squad.owner == self.owner:
                    continue
                if edge_distance(model, other) <= ENGAGEMENT_RANGE_IN:
                    return True
        return False

    def is_engaged_with(self, other_squad):
        """Rule 10.06: is this squad specifically engaged with other_squad
        (as opposed to Squad.is_engaged, which checks against any enemy)."""
        for model in self.models:
            for other in other_squad.models:
                if edge_distance(model, other) <= ENGAGEMENT_RANGE_IN:
                    return True
        return False

    def min_distance_to(self, other_squad):
        """Rule 11.02: unit-to-unit distance, taken as the closest edge
        distance between any pair of models across the two squads - used
        for the charge phase's "within 12"" checks."""
        return min(edge_distance(a, b) for a in self.models for b in other_squad.models)

    def disallowed_enemy_squads_for_move(self, all_tokens, move_mode, charge_targets=(), surge_target=None):
        """Move-type-specific set of enemy squads a model of this unit must
        not be within Engagement Range of THE INSTANT it's placed - the
        fail-fast half of confirm_move()'s mode-specific engagement checks
        below, used by MovementController.try_commit_segment() for its
        instant per-model check. The "must actually reach the declared
        target" half of Charge/Pile-In/Consolidate/Surge has no per-model
        equivalent (it's a squad-wide success condition, can only be
        verified once every model has been placed) and stays confirm-time
        -only via check_charge_engagement()/check_pile_in_engagement()/etc.
        Pile-In and Consolidate have no forbidding half at all (rule 12.03/
        12.08 never forbids touching a non-target enemy), hence the empty
        set for those two."""
        enemy_squads = {
            t.squad for t in all_tokens
            if t.squad is not None and t.squad.owner != self.owner
        }
        if move_mode == "charge":
            return enemy_squads - set(charge_targets)
        if move_mode == "surge":
            return enemy_squads - ({surge_target} if surge_target is not None else set())
        if move_mode in ("pile_in", "consolidate"):
            return set()
        return enemy_squads  # None or "fall_back": rule 09.05/09.06/09.07 - must end fully unengaged

    def check_charge_engagement(self, charge_targets, all_tokens):
        """Rule 11.04 AFTER MOVING: a charge move must end with this squad
        engaged with every declared charge target, and not engaged with any
        enemy unit that wasn't one."""
        errors = []
        for target in charge_targets:
            if not self.is_engaged_with(target):
                errors.append(f'Your unit must be engaged with charge target "{target.name}".')

        enemy_squads = {
            token.squad for token in all_tokens
            if token.squad is not None and token.squad.owner != self.owner
        }
        for enemy_squad in enemy_squads:
            if enemy_squad not in charge_targets and self.is_engaged_with(enemy_squad):
                errors.append(f'Your unit cannot be engaged with "{enemy_squad.name}", which is not a charge target.')

        return errors

    def check_pile_in_engagement(self, pile_in_targets, all_tokens):
        """Rule 12.03 AFTER MOVING: a pile-in move must end with this squad
        engaged, and still engaged with every enemy unit it was already
        engaged with before the move (pile_in_targets) - unlike a charge,
        piling in doesn't forbid ending engaged with some other unit too."""
        errors = []
        if not self.is_engaged(all_tokens):
            errors.append("Your unit must be engaged after piling in.")
        for target in pile_in_targets:
            if not self.is_engaged_with(target):
                errors.append(f'Your unit must still be engaged with "{target.name}" after piling in.')
        return errors

    def check_ongoing_consolidation(self, targets, all_tokens):
        """Rule 12.08 AFTER MOVING (Ongoing Consolidation): identical
        requirement to a pile-in move - stay engaged with every enemy unit
        this squad was already engaged with before consolidating."""
        return self.check_pile_in_engagement(targets, all_tokens)

    def check_engaging_consolidation(self, targets):
        """Rule 12.08 AFTER MOVING (Engaging Consolidation): must end
        engaged with every selected enemy unit - but unlike a charge,
        ending engaged with some other unit too is fine (that's what
        triggers the "opponent must select it to fight" consequence)."""
        errors = []
        for target in targets:
            if not self.is_engaged_with(target):
                errors.append(f'Your unit must be engaged with "{target.name}" after consolidating.')
        return errors

    def check_objective_consolidation(self, objective, range_in=OBJECTIVE_CONSOLIDATION_RANGE_IN):
        """Rule 12.08 AFTER MOVING (Objective Consolidation): "Your unit
        must be within range of the selected objective" - reuses the same
        3" the rule already defines as the qualifying distance for this
        mode in the first place (BEFORE MOVING: "within 3\" of one or more
        objectives"), since the rule never restates a different number for
        the after-moving check. Deliberately NOT game/objectives.py's
        Level of Control range (terrain-area overlap, a stricter, different
        concept used for scoring, not for this move type)."""
        if any(objective.terrain_area.distance_to_model(m) <= range_in for m in self.models):
            return []
        return [f'Your unit must end this move within range of "{objective.name}".']

    def check_surge_engagement(self, surge_target, all_tokens):
        """Rule 21.02 AFTER MOVING (Surge move): "Your unit cannot be
        engaged with one or more enemy units that were not the surge
        target." Unlike a charge, ending engaged with the surge target
        itself isn't a hard requirement here - only the WHILE MOVING "if
        possible" wording asks for that, and (like Charge/Pile-In/
        Consolidate's own WHILE-MOVING wording) we don't enforce soft
        "get as close/engaged as possible" constraints, only this hard
        AFTER-MOVING one."""
        enemy_squads = {
            token.squad for token in all_tokens
            if token.squad is not None and token.squad.owner != self.owner
        }
        errors = []
        for enemy_squad in enemy_squads:
            if enemy_squad is not surge_target and self.is_engaged_with(enemy_squad):
                errors.append(f'Your unit cannot be engaged with "{enemy_squad.name}", which is not the surge target.')
        return errors

    def check_scout_move_clearance(self, all_tokens):
        """Rule 24.32 (SCOUT MOVE) AFTER MOVING: "Your unit must be more than
        8" horizontally from all enemy units."

        "Horizontally" is plain 2D board distance here - this engine models no
        vertical axis - and measured edge to edge, like every other distance in
        this file."""
        errors = []
        for token in all_tokens:
            if token.squad is None or token.squad.owner == self.owner:
                continue
            for model in self.models:
                if edge_distance(model, token) <= SCOUT_MOVE_MIN_ENEMY_DISTANCE_IN:
                    errors.append(
                        f'Your unit must end a Scout move more than '
                        f'{SCOUT_MOVE_MIN_ENEMY_DISTANCE_IN:g}" from all enemy units '
                        f'(rule 24.32) - "{token.squad.name}" is closer.'
                    )
                    return errors
        return errors

    def allocation_groups(self):
        """Rule 05.03, groups formed and ordered automatically instead of
        asking the defending player: one group per CHARACTER model, and one
        group for all other models sharing the same W and Sv (InSv doesn't
        exist in our engine yet, so it's left out of the grouping key for
        now). Order: non-CHARACTER groups first, weakest first; then
        CHARACTER groups, weakest first - which already satisfies both "a
        damaged non-CHARACTER group goes first" and "a damaged CHARACTER
        group goes before undamaged CHARACTER groups" as a side effect of
        sorting weakest-to-strongest throughout.
        """
        characters = [m for m in self.models if m.profile.character]
        others = [m for m in self.models if not m.profile.character]

        other_groups = {}
        for model in others:
            key = (model.profile.wounds, model.profile.armor_save)
            other_groups.setdefault(key, []).append(model)

        ordered_others = sorted(other_groups.values(), key=_group_weakness)
        ordered_characters = sorted(([c] for c in characters), key=_group_weakness)

        return ordered_others + ordered_characters

    def unusual_loadout_models(self):
        """Rendering helper (Später-Liste: 'optische Unterscheidung
        innerhalb von Squads'): models whose weapon loadout differs from the
        squad's most common loadout - e.g. a Boss Nob equipped differently
        than the rank-and-file Boyz around it. Purely cosmetic (a lighter
        color tint), no rule attaches to it."""
        if len(self.models) <= 1:
            return set()
        loadouts = [tuple(sorted(w.name for w in m.weapons)) for m in self.models]
        majority = Counter(loadouts).most_common(1)[0][0]
        return {m for m, l in zip(self.models, loadouts) if l != majority}

    def apply_damage(self, total_damage):
        """Placeholder wound allocation: damage is soaked up model by model, in
        squad order, until it's used up. Proper allocation rules (letting the
        controlling player choose, multi-wound spillover, etc.) come later."""
        remaining = total_damage
        for model in self.models:
            if remaining <= 0:
                break
            if model.is_dead():
                continue
            absorbed = min(remaining, model.current_wounds)
            model.apply_damage(absorbed)
            remaining -= absorbed


def closest_enemy_squad(squad, all_tokens):
    """Rule 21.02 BEFORE MOVING (Surge move): "Select the closest enemy
    unit to be the surge target" - ties are broken arbitrarily (whichever
    enemy squad set-iteration happens to reach first), since the rule
    doesn't say how to resolve them and it's rare enough not to be worth a
    dedicated player choice yet."""
    enemy_squads = {
        token.squad for token in all_tokens
        if token.squad is not None and token.squad.owner != squad.owner
    }
    if not enemy_squads:
        return None
    return min(enemy_squads, key=lambda s: squad.min_distance_to(s))


INFILTRATORS_MIN_ENEMY_DISTANCE_IN = 8.0
# Rule 24.32 (SCOUT MOVE), AFTER MOVING. A separate named constant from
# INFILTRATORS_MIN_ENEMY_DISTANCE_IN even though both are 8.0: two different
# rules that happen to share a number stay two constants with their own
# citations, so changing one never silently changes the other.
SCOUT_MOVE_MIN_ENEMY_DISTANCE_IN = 8.0


def squad_has_infiltrators(squad):
    """Rule 24.20 (INFILTRATORS): only applies "if every model in a unit
    has this ability" - a mixed unit gets no benefit, same all()-vs-any()
    distinction as _has_deep_strike() in game/ingress.py.

    The Recon Drone (game/drones.py, user-supplied wargear) is an explicit
    exception, and an any() one: its text grants the ability to "the
    bearer's UNIT", not to the bearer. That is a unit-level grant, i.e.
    exactly the state 24.20's every-model gate is testing for, so one live
    bearer is enough - which is also why the drone sets its own
    `recon_drone` flag rather than `infiltrators` on the bearer (that would
    have granted nothing, since the datasheet's other models don't have
    it)."""
    if unit_wide_ability(squad, "infiltrators"):
        return True
    if squad is None:
        return False
    return any(m.profile.recon_drone for m in squad.models if not m.is_dead())


def infiltrators_clear_of_enemies(x_in, y_in, radius_in, all_tokens, owner):
    """Rule 24.20's geometric half: "more than 8\" horizontally from...
    all enemy units". The other half of the rule ("your opponent's
    deployment zone") is checked by the CALLER - game/pregame.py's
    _infiltrator_position_valid(), which measures the zone itself and then
    delegates the enemy-model half to this function. That became possible
    once the Pre-game Sequence (03.01) arrived and brought real deployment
    zones with it; pregame.py is the live caller, and it deliberately
    deploys INFILTRATORS units LAST (the ability is evaluated at the moment
    of setting up, so going early gains nothing). The earlier note here -
    "not wired into any live placement flow... kept as ready-to-use
    infrastructure" - was left behind when that flow was built."""
    for other in all_tokens:
        if other.squad is None or other.squad.owner == owner:
            continue
        dist = ((x_in - other.x_in) ** 2 + (y_in - other.y_in) ** 2) ** 0.5
        if dist - radius_in - other.radius_in <= INFILTRATORS_MIN_ENEMY_DISTANCE_IN:
            return False
    return True


def squad_has_stealth(squad):
    """Rule 24.33 (STEALTH): "if every model in a unit has this ability" -
    same all()-vs-any() distinction as squad_has_infiltrators()/
    _has_deep_strike()."""
    return unit_wide_ability(squad, "stealth")


def squad_has_greater_good(squad):
    """T'au Empire army rule "For The Greater Good" (user-supplied, not a
    generic core-rulebook rule - see game/greater_good.py for the actual
    Observer/Spotted/Guided logic): "if every model in a unit has this
    ability" - same all()-vs-any() convention as squad_has_stealth()/
    squad_has_infiltrators() (a core/faction ability granted uniformly
    across a homogeneous unit)."""
    return unit_wide_ability(squad, "for_the_greater_good")


def squad_has_markerlight(squad):
    """The MARKERLIGHT keyword - any(), not all(): read as a per-model
    marker/weapon keyword (e.g. a single Markerlight-equipped drone
    attached to an otherwise-unmarkered unit still lets that unit's
    Observer marking count as Markerlight-sourced), unlike a uniform core
    ability."""
    return attached_units.unit_has_keyword(squad, lambda m: m.profile.markerlight)


def squad_has_suppression_volley(squad):
    """T'au Strike Team ability "Suppression Volley" (user-supplied, not a
    core rulebook rule - see game/suppression.py): whether every model in
    squad carries it - same all() convention as squad_has_stealth() etc.
    (a datasheet ability granted uniformly across a homogeneous unit)."""
    return unit_wide_ability(squad, "suppression_volley")


def squad_has_volley_fire(squad):
    """T'au Cadre Fireblade ability "Volley Fire" (user-supplied, not a core
    rulebook rule - see game/volley_fire.py): does this unit currently have a
    Fireblade LEADING it? +1 Attack on every ranged weapon in the unit."""
    return attached_units.leader_ability(squad, "volley_fire")


def squad_has_might_is_right(squad):
    """Ork Warboss ability "Might is Right" (user-supplied, not a core
    rulebook rule): "while this model is leading a unit, each time a model in
    that unit makes a melee attack, add 1 to the Hit roll" - see
    game/fight.py's own _hit_modifiers(). Shared verbatim by both Warboss
    datasheets (plain and in Mega Armour)."""
    return attached_units.leader_ability(squad, "might_is_right")


def support_turret_bearer(squad):
    """T'au "DS8 Support Turret" ability (user-supplied - shared by Strike
    Team and Breacher Team, see game/support_turret.py): "its Shas'ui
    model" - the one model in the unit flagged as this datasheet's turret
    bearer, or None if the unit has no such model."""
    for model in squad.models:
        if model.profile.support_turret_bearer:
            return model
    return None


def squad_has_breach_and_clear(squad):
    """T'au Breacher Team ability "Breach and Clear" (user-supplied, not a
    core rulebook rule - see game/shooting.py's _wound_reroll_reason()):
    whether every model in squad carries it - same all() convention as
    squad_has_suppression_volley() etc."""
    return unit_wide_ability(squad, "breach_and_clear")


def squad_has_guardian_drone(squad):
    """The Guardian Drone wargear item (user-supplied, not a core rule -
    see game/drones.py): any() rather than all() - "each time a model makes
    a ranged attack that targets THE BEARER'S UNIT" protects the whole unit
    a single Guardian-Drone-carrying model is part of, not just that model
    itself."""
    return attached_units.unit_has_keyword(squad, lambda m: m.profile.guardian_drone)


def squad_has_fieldcraft(squad):
    """The sticky-objective ability (user-supplied, not a core rulebook
    rule - see game/fieldcraft.py and UnitProfile.fieldcraft's own note):
    whether every model in squad carries it - same all() convention as
    squad_has_suppression_volley() etc. Shared verbatim by every datasheet
    that prints this rule under its own flavor name (Kroot Carnivores'
    Fieldcraft, Boyz's Get Da Good Bitz, ...)."""
    return unit_wide_ability(squad, "fieldcraft")


def squad_has_forward_observers(squad):
    """Stealth Battlesuits ability "Forward Observers" (user-supplied, not
    a core rulebook rule - see game/greater_good.py's has_forward_observers()):
    whether every model in squad carries it - same all() convention as
    squad_has_suppression_volley() etc."""
    return unit_wide_ability(squad, "forward_observers")


def squad_has_battlesuit_support_system(squad):
    """Crisis Starscythe Battlesuits ability "Battlesuit Support System"
    (user-supplied, not a core rulebook rule - see game/shooting.py's
    available_shooting_types(), rule 09.07's normal "Fell Back this turn ->
    cannot shoot" block): "The unit is eligible to shoot in a turn in which
    it Fell Back" - a whole-unit exception, same all() convention as
    squad_has_suppression_volley() etc."""
    return unit_wide_ability(squad, "battlesuit_support_system")


def squad_has_war_construct(squad):
    """Wraithguard's "War Construct" ability (user-supplied): "This unit is
    eligible to shoot in a turn in which it Fell Back" - word for word the
    same exception squad_has_battlesuit_support_system() above grants, and
    read at the same place (game/shooting.py's available_shooting_types()).
    Two abilities, one effect, so two predicates rather than one shared flag:
    they are different printed rules and a datasheet has one or the other."""
    return unit_wide_ability(squad, "war_construct")


def squad_has_full_throttle(squad):
    """Stormboyz ability "Full Throttle" (user-supplied, not a core
    rulebook rule - see game/charge.py's can_declare_charge(), rules
    09.06/09.07's normal "Advanced/Fell Back this turn -> cannot charge"
    blocks): "This unit is eligible to declare a charge in a turn in which
    it Advanced or Fell Back" - a whole-unit exception, same all()
    convention as squad_has_battlesuit_support_system() (the equivalent
    exception for shooting instead of charging)."""
    return unit_wide_ability(squad, "full_throttle")


def squad_has_thievin_scavengers(squad):
    """Gretchin ability "Thievin' Scavengers" (user-supplied, not a core
    rulebook rule - see game/thievin_scavengers.py): whether every model in
    squad carries it - same all() convention as squad_has_fieldcraft() etc.
    A shared flag, not Gretchin-exclusive (user: "diese Ability wird noch
    öfters kommen")."""
    return unit_wide_ability(squad, "thievin_scavengers")
