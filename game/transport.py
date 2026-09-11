import math

from game.hazard import HazardRollStep
from game.ingress import INGRESS_MIN_ENEMY_DISTANCE_IN
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance

EMBARK_RANGE_IN = 3.0
RAPID_DISEMBARK_DISTANCE_IN = 3.0
TACTICAL_DISEMBARK_DISTANCE_IN = 3.0
COMBAT_DISEMBARK_DISTANCE_IN = 6.0
EMERGENCY_DISEMBARK_DISTANCE_IN = 6.0

RAPID = "rapid"
TACTICAL = "tactical"
COMBAT = "combat"
EMERGENCY = "emergency"

DISEMBARK_DISTANCE_IN = {
    RAPID: RAPID_DISEMBARK_DISTANCE_IN,
    TACTICAL: TACTICAL_DISEMBARK_DISTANCE_IN,
    COMBAT: COMBAT_DISEMBARK_DISTANCE_IN,
    EMERGENCY: EMERGENCY_DISEMBARK_DISTANCE_IN,
}

DOUBLE_CAPACITY_COST = 2  # rule 18.01: what a MEGA ARMOUR or JUMP PACK model costs a TRANSPORT, per Trukk's and Battlewagon's own printed exceptions - see _model_capacity_cost()
MEGA_ARMOUR_CAPACITY_COST = DOUBLE_CAPACITY_COST  # kept as the original name for existing importers


def _model_capacity_cost(model):
    """Rule 18.01: how much room one model takes up inside a TRANSPORT.

    All three doubled cases come from printed datasheet lines - Trukk's "each
    MEGA ARMOUR model takes up the space of 2 models", Battlewagon's "each
    MEGA ARMOUR or JUMP PACK model takes up the space of 2 models", and the
    Falcon's "each WRAITH CONSTRUCT model takes the space of 2 models".
    Applied globally rather than per TRANSPORT, which is exact for every
    datasheet modeled here: the only other TRANSPORTs are the Trukk (which
    refuses JUMP PACK models outright, so the cost never comes up), the
    Devilfish (T'au, no JUMP PACK models exist on that side) and the Kill Rig
    (BEAST SNAGGA INFANTRY only, none of which have any of the three
    keywords) - and no non-Aeldari TRANSPORT can carry a WRAITH CONSTRUCT
    either, since none of them accept AELDARI models. A TRANSPORT that prints
    a DIFFERENT cost would need this made per-profile.

    Battlewagon's third clause, "the GHAZGHKULL THRAKA model takes up the
    space of 4 models", is not modeled - that datasheet does not exist here,
    so there is nothing to charge."""
    if (model.profile.mega_armour or model.profile.jump_pack
            or getattr(model.profile, "wraith_construct", False)):
        return DOUBLE_CAPACITY_COST
    return 1


def fits_pools(squad, pools, already_embarked=()):
    """Rule 18.02 for a capacity line printed as SEVERAL SUB-POOLS.

    The Ghost Ark prints "a transport capacity of 10 NECRON WARRIOR models and
    1 NECRONS INFANTRY CHARACTER model" - two pools with different keyword
    rules and different limits. transport_requires cannot express that: its
    contract is "EVERY model has EVERY keyword", which is one pool by
    definition, and pointing it at ("necron_warrior",) would reject the
    realistic passenger outright, because rule 19.01 MERGES the character into
    the Warriors unit and that one model carries no warrior keyword.

    THE THIRD CONSUMER of attached_units.model_has_datasheet_keyword() (the
    39th extraction). The pools are named by DATASHEET keyword rather than by
    UnitProfile flag for two reasons: "NECRON WARRIORS" is a datasheet's own
    name and has no flag, and after a 19.01 merge matching a model against its
    component's starting_models is the only granularity at which a per-MODEL
    keyword question can be answered at all.

    ALREADY-EMBARKED LOADS COUNT, and each is asked about ITS OWN squad - a
    passenger's datasheet keywords belong to the squad it came in with, not to
    the one now trying to board.

    FIRST-FITTING POOL WINS, so pool ORDER would matter if two pools ever
    overlapped. The Ghost Ark's two are DISJOINT (no NECRON WARRIORS model is
    a CHARACTER), which is measured and pinned in the suite rather than left to
    luck - the same treatment game/objective_control.py gives its setters. A
    future overlapping pair would need a real assignment search here, and this
    comment is where that discovery should start.

    ALL OR NOTHING, like every other clause of 18.02: one model that fits no
    pool refuses the whole unit."""
    from game.attached_units import model_has_datasheet_keyword
    counts = [0] * len(pools)
    for load in list(already_embarked) + [squad]:
        for model in load.models:
            for i, (_limit, keywords) in enumerate(pools):
                if all(model_has_datasheet_keyword(load, model, kw) for kw in keywords):
                    counts[i] += _model_capacity_cost(model)
                    break
            else:
                return False          # this model fits no pool at all
    return all(count <= limit for count, (limit, _kw) in zip(counts, pools))


class TransportController:
    """Rules 18.01-18.05 (Transports): embarking, capacity, and the three
    Disembark Move variants plus Emergency Disembark - all reuse
    SetupController for the actual placement (03.02), exactly like Ingress
    (20.04). "Before the battle, in the Declare Battle Formations step"
    (18.01) isn't modeled - we have no pre-game deployment sequence
    distinct from turn 1. "Eligible to embark... as described on that
    TRANSPORT's datasheet" (18.02) is now PARTIALLY modeled, first needed by
    Devilfish ("transport capacity of 12 T'AU EMPIRE INFANTRY models... it
    cannot transport BATTLESUIT, KROOT or VESPID STINGWINGS models"): a
    TRANSPORT's own UnitProfile.transport_requires_infantry/
    transport_excludes (see can_embark() below) can restrict which squads
    may embark. Still not modeled: the "T'au Empire" half of that same
    restriction - this engine has no per-model faction tracking (a squad's
    faction is only known indirectly, via which Faction object registered
    its Datasheet - see game/factions/faction.py - not something a Token/
    UnitProfile carries), so a non-T'au INFANTRY unit would still (wrongly)
    be accepted by a transport_requires_infantry TRANSPORT. A TRANSPORT
    with neither field set (e.g. the demo VehicleProfile) keeps the old
    "any non-TRANSPORT unit is eligible" behavior unchanged. Embark's
    "after a normal, advance or fall-back move this phase" (18.02) is just
    `squad in movement_controller.moved_squad_ids` below - that set is
    move-type-agnostic (populated by confirm_move() for every move type
    except Pile-In/Consolidate, see game/movement.py), so a Fall Back move
    (rule 09.07, game/fall_back.py) already satisfies it with no extra code
    here.

    Emergency Disembark (18.05)'s "each model that cannot be set up this
    way is destroyed" is simplified to all-or-nothing, like every other
    Set Up failure in this codebase: if the whole unit can't be placed,
    the whole unit is destroyed, rather than tracking which individual
    models could or couldn't fit. "As close as possible to that TRANSPORT"
    is approximated as "within 6" of it", without also maximizing
    closeness.

    Sequence when a TRANSPORT is destroyed (user-reported, and the order
    the code now follows): its passengers disembark first, then the hazard
    roll (06.03) is made for the unit that just got out, and only then
    does Deadly Demise (24.08) resolve for the wreck - main.py's frame loop
    holds Deadly Demise back on is_busy for exactly that reason. The one
    deviation, deliberate: the TRANSPORT's own token is already out of
    state.tokens by the time placement runs (main.py's remove_dead_models()
    is what discovers the death in the first place). Nothing measures
    differently for it - edge_distance() reads the dead token's last
    position, which never changes - it only means the passengers may be set
    up in the footprint the wreck occupied, which is both what physically
    happens at the table and the forgiving direction for the single most
    expensive failure in this codebase (a failed disembark destroys the
    unit).

    Devilfish's own "Rapid Deployment" ability (user-supplied, not a core
    rule) lifts the normal "a TRANSPORT that Advanced this phase can't be
    disembarked from at all" restriction (can_disembark() below) - such a
    disembark then resolves exactly like a normal RAPID Disembark Move
    (determine_mode() below), which already happens to match the ability's
    own wording ("counts as having made a Normal move that phase, and
    cannot declare a charge" - RAPID/COMBAT/EMERGENCY Disembark Moves
    already lock out a further charge this turn via charge_locked_until_
    end_of_turn, see confirm_disembark()). Implementing this surfaced a
    genuine, pre-existing gap unrelated to Devilfish specifically: none of
    RAPID/COMBAT/EMERGENCY Disembark Moves were adding the disembarked
    squad to movement_controller.moved_squad_ids, so such a unit could
    incorrectly still make an entirely separate Normal/Advance move
    afterwards this phase (only Tactical Disembark is actually meant to
    allow that) - fixed alongside this ability's own wiring, see
    confirm_disembark()."""

    def __init__(
        self, setup_controller, game_state, all_tokens, movement_controller, ingress_controller, dice_manager,
        game_log=None, turn_tracker=None, board_width_in=None, board_height_in=None,
    ):
        self.setup_controller = setup_controller
        self.game_state = game_state
        self.all_tokens = all_tokens
        self.movement_controller = movement_controller
        self.ingress_controller = ingress_controller
        self.dice_manager = dice_manager
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.board_width_in = board_width_in
        self.board_height_in = board_height_in

        self._embarked_this_phase = set()  # squads that embarked THIS Movement phase (rule 18.04 eligibility)
        self._disembarking_squad = None
        self._disembark_mode = None
        self._disembark_transport = None
        self._hazard_step = None       # HazardRollStep while Combat/Emergency Disembark's POST-placement hazard roll is pending (see confirm_disembark())
        self._emergency_queue = []     # [(transport_token, squad), ...] awaiting their emergency disembark

    def reset_movement_phase(self):
        self._embarked_this_phase = set()

    # --- Embarking (18.02) ---

    def embarked_squads_in(self, transport_token):
        return [s for s in self.game_state.embarked_squads if s.embarked_in is transport_token]

    def embarked_model_count(self, transport_token):
        return sum(_model_capacity_cost(m) for s in self.embarked_squads_in(transport_token) for m in s.models)

    def remaining_capacity(self, transport_token):
        return transport_token.profile.transport_capacity - self.embarked_model_count(transport_token)

    def eligible_transports(self, squad):
        """TRANSPORT tokens `squad` could embark within right now - see
        can_embark() for the full eligibility list."""
        return [
            t for t in self.all_tokens
            if t.profile.transport and t.squad is not None and self.can_embark(squad, t)
        ]

    def can_embark(self, squad, transport_token, require_move=True, range_in=None):
        """Rule 18.02's embark check.

        `range_in` overrides the printed 3", for a rule that grants an embark
        at a different distance - Skyborne Sanctuary says "wholly within 6"".
        A named parameter beside `require_move` rather than a second function,
        because it changes ONE number and leaves every other condition alone;
        the default keeps every existing caller measuring exactly what it did.

        `require_move=False` drops ONLY 18.02's "after a Normal, Advance or
        Fall Back move this phase" clause, for a rule that grants an embark at
        another moment - Kauyon's Combat Embarkation, which happens in the
        opponent's Charge phase, where nothing of yours has moved. Every
        PHYSICAL condition still applies: the 3", the capacity, the transport's
        own keyword restrictions. A rule that changes WHEN you may embark does
        not change WHETHER you fit.
        """
        if squad is None or transport_token is None or transport_token.squad is None:
            return False
        if not transport_token.profile.transport:
            return False
        if squad is transport_token.squad:
            return False
        if any(m.profile.transport for m in squad.models):
            return False  # simplification: a TRANSPORT can't itself embark within another one
        if any(getattr(m.profile, "cannot_embark", False) for m in squad.models):
            # Support Weapon Platforms: "This model, AND ANY UNIT IT IS JOINED
            # TO, cannot embark within a TRANSPORT." Both halves fall out of
            # one per-model test, because 19.01 merges a joined platform into
            # the Guardians' own Squad.models - so the unit it joined carries
            # the model that carries the ban, and asking per model answers the
            # printed sentence exactly rather than approximating it.
            return False
        if squad.embarked_in is not None:
            return False
        if squad.set_up_this_turn:
            return False
        if getattr(squad, "embark_locked_until_end_of_turn", False):
            # The twin of Squad.charge_locked_until_end_of_turn, which has five
            # users and no counterpart for embarking. Two Aeldari Stratagems
            # print "not eligible to declare a charge OR EMBARK within a
            # TRANSPORT" - the charge half was already covered, the embark half
            # had nothing to set.
            return False
        if require_move and squad not in self.movement_controller.moved_squad_ids:
            return False  # rule 18.02: only after a normal, advance or fall-back move this phase
        if transport_token.profile.transport_requires_infantry and not all(m.profile.infantry for m in squad.models):
            return False  # e.g. Devilfish: "T'AU EMPIRE INFANTRY models" (INFANTRY half only, see class docstring)
        required_keywords = getattr(transport_token.profile, "transport_requires", ())
        if required_keywords and not all(
            getattr(m.profile, kw, False) for m in squad.models for kw in required_keywords
        ):
            return False  # e.g. Kill Rig: "11 BEAST SNAGGA INFANTRY models" - the BEAST SNAGGA half
        excluded_keywords = transport_token.profile.transport_excludes
        if excluded_keywords and any(getattr(m.profile, kw, False) for m in squad.models for kw in excluded_keywords):
            return False  # e.g. Devilfish: "cannot transport BATTLESUIT, KROOT or VESPID STINGWINGS models"
        pools = getattr(transport_token.profile, "transport_pools", ())
        if pools and not fits_pools(squad, pools, self.embarked_squads_in(transport_token)):
            return False  # e.g. Ghost Ark: "10 NECRON WARRIOR models and 1 NECRONS INFANTRY CHARACTER model" - see fits_pools()
        reach = EMBARK_RANGE_IN if range_in is None else range_in
        if not all(edge_distance(m, transport_token) <= reach for m in squad.models):
            return False
        return sum(_model_capacity_cost(m) for m in squad.models) <= self.remaining_capacity(transport_token)

    def embark(self, squad, transport_token, require_move=True, range_in=None):
        if not self.can_embark(squad, transport_token, require_move=require_move,
                               range_in=range_in):
            return
        for model in squad.models:
            if model in self.game_state.tokens:
                self.game_state.tokens.remove(model)
        squad.embarked_in = transport_token
        self.game_state.embarked_squads.append(squad)
        self._embarked_this_phase.add(squad)
        if self.game_log is not None:
            self.game_log.add(f"{squad.owner}: {squad.name} embarks within {transport_token.profile.name} (rule 18.02).")

    # --- Disembark Move (18.04) ---

    def can_disembark(self, squad):
        if squad is None or squad.embarked_in is None or self._disembarking_squad is not None:
            return False
        transport_token = squad.embarked_in
        if transport_token not in self.game_state.tokens:
            return False  # destroyed - handled via Emergency Disembark instead
        if squad in self._embarked_this_phase:
            return False
        if transport_token.squad in self.movement_controller.advanced_squad_ids and not transport_token.profile.rapid_deployment:
            return False  # "Rapid Deployment" (Devilfish's own ability) is the one exception to this
        return True

    def determine_mode(self, transport_token, squad):
        """Rule 18.04 BEFORE MOVING: the disembark mode isn't a free choice
        - it's forced by what move the TRANSPORT made this phase. Note
        that can_disembark() already excludes a TRANSPORT that advanced or
        fell back this phase (that's "not eligible to disembark at all",
        not "must Combat Disembark") - the only states left here are
        normal/ingress move, remained stationary, or hasn't moved yet -
        UNLESS the TRANSPORT has "Rapid Deployment" (see class docstring)
        and DID Advance, which resolves as RAPID anyway."""
        transport_squad = transport_token.squad
        mc = self.movement_controller
        ingressed = self.ingress_controller is not None and transport_squad in self.ingress_controller.ingressed_this_phase
        advanced = transport_squad in mc.advanced_squad_ids
        rapid_deployment_after_advance = advanced and transport_token.profile.rapid_deployment
        if ingressed or rapid_deployment_after_advance or (transport_squad in mc.moved_squad_ids and not advanced):
            return RAPID
        # Stationary or not-yet-moved: rule 18.04 requires Tactical "if you
        # can set up your unit as described below" - approximated by
        # sampling points around the TRANSPORT (see
        # _tactical_placement_feasible()) rather than solving true
        # feasibility (coherency across the whole squad, etc.); Combat
        # Disembark is the fallback when none of those samples are clear.
        if self._tactical_placement_feasible(transport_token, squad):
            return TACTICAL
        return COMBAT

    def _tactical_placement_feasible(self, transport_token, squad):
        """Is there anywhere within Tactical range this unit could legally
        stand? Sampled, not solved - coherency across the whole squad is not
        checked, only that at least one model-sized spot is legal.

        "Legal" has to include being UNENGAGED (03.02), which is the entire
        difference between the two modes: a Combat Disembark is the fallback
        precisely because it may be set up engaged. Judging the samples by
        terrain and overlap alone made a TRANSPORT parked among enemy models
        report Tactical as feasible, and the resulting placement can then
        never confirm - so the unit stays aboard instead of getting the
        Combat Disembark the rule gives it.

        Sampled across the whole 3" band rather than only its outer edge, so
        a spot that exists closer in still counts as Tactical and the unit
        isn't pushed into Combat's Battle-shock and hazard roll for nothing."""
        representative = squad.models[0]
        cx, cy = transport_token.x_in, transport_token.y_in
        inner = transport_token.radius_in + representative.radius_in + 0.05
        outer = transport_token.radius_in + representative.radius_in + TACTICAL_DISEMBARK_DISTANCE_IN
        enemy_models = [
            t for t in self.all_tokens
            if t.squad is not None and t.squad.owner != squad.owner
        ]
        samples = 12
        for band in range(3):
            radius = outer if band == 0 else inner + (outer - inner) * (3 - band) / 4
            for i in range(samples):
                angle = 2 * math.pi * i / samples
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                if not self.setup_controller.position_valid(representative, x, y, squad=squad):
                    continue
                if any(
                    ((x - e.x_in) ** 2 + (y - e.y_in) ** 2) ** 0.5
                    - representative.radius_in - e.radius_in <= ENGAGEMENT_RANGE_IN
                    for e in enemy_models
                ):
                    continue
                return True
        return False

    def start_disembark(self, squad):
        if not self.can_disembark(squad):
            return
        self._disembarking_squad = squad
        self._disembark_mode = self.determine_mode(squad.embarked_in, squad)
        self._disembark_transport = squad.embarked_in
        # Placement first, hazard roll afterwards - for EVERY mode. See
        # confirm_disembark() for why the roll can't come first.
        self._begin_placement()

    def is_disembarking(self, squad):
        return squad is not None and squad is self._disembarking_squad

    @property
    def disembarking_squad(self):
        """Public read of the squad currently mid-Disembark-Move (or None)
        - e.g. ai/agent_driver.py needs this to resume placement once a
        Combat/Emergency hazard roll it kicked off has been acknowledged."""
        return self._disembarking_squad

    @property
    def disembark_mode(self):
        """Public read of the current Disembark Move's mode (RAPID/
        TACTICAL/COMBAT/EMERGENCY), or None - squad.embarked_in is already
        cleared by the time placement begins, so this is the only way to
        recover which mode (and therefore which DISEMBARK_DISTANCE_IN
        applies) a caller is currently placing for."""
        return self._disembark_mode

    @property
    def disembark_transport(self):
        """Public read of the TRANSPORT token the squad currently being
        placed disembarked from, or None."""
        return self._disembark_transport

    def _begin_placement(self):
        squad = self._disembarking_squad
        transport_token = self._disembark_transport
        mode = self._disembark_mode

        dead = [m for m in squad.models if m.is_dead()]
        for m in dead:
            squad.models.remove(m)
        if not squad.models:
            if mode != EMERGENCY and squad in self.game_state.embarked_squads:
                self.game_state.embarked_squads.remove(squad)
            if self.game_log is not None:
                self.game_log.add(f"{squad.owner}: {squad.name} was wiped out before it could disembark.")
            self._reset_disembark_state()
            return

        if squad in self.game_state.embarked_squads:
            self.game_state.embarked_squads.remove(squad)
        squad.embarked_in = None

        self.setup_controller.start_setup(
            squad, transport_token.x_in, transport_token.y_in,
            on_cancel=self._on_cancel_disembark,
            extra_check=self._make_extra_check(transport_token, mode),
            allow_engaged=(mode == COMBAT),
            # Live per-position counterpart of extra_check, so a model can't
            # be dragged outside rule 18.04's set-up distance (or onto the
            # TRANSPORT's own hull) in the first place - same predicate the
            # green/red overlay paints.
            placement_validator=lambda token, x, y: self.position_valid(squad, token, x, y),
        )

    def _make_extra_check(self, transport_token, mode):
        distance = DISEMBARK_DISTANCE_IN[mode]

        def check(squad):
            errors = []
            if not all(edge_distance(m, transport_token) <= distance for m in squad.models):
                errors.append(f'Every model must be set up within {distance:.0f}" of the TRANSPORT (rule 18.04/18.05).')

            if mode == RAPID and self.ingress_controller is not None and transport_token.squad in self.ingress_controller.ingressed_this_phase:
                # Rule 18.04: "each model must follow the same rules that
                # TRANSPORT had to follow while resolving [its Ingress] move."
                transport_deep_strike = all(m.profile.deep_strike for m in transport_token.squad.models)
                if not transport_deep_strike and not all(
                    self.ingress_controller._within_setup_distance_of_point(m.x_in, m.y_in, m.radius_in) for m in squad.models
                ):
                    errors.append('Every model must also be set up within the Ingress set-up distance the TRANSPORT itself used (rule 18.04).')
                enemy_models = [
                    t for t in self.all_tokens
                    if t.squad is not None and t.squad is not squad and t.squad.owner != squad.owner
                ]
                if any(edge_distance(m, e) <= INGRESS_MIN_ENEMY_DISTANCE_IN for m in squad.models for e in enemy_models):
                    errors.append('Every model must also be more than 8" from all enemy units, as the TRANSPORT was (rule 18.04).')
            return errors

        return check

    def confirm_disembark(self):
        squad = self.setup_controller.setting_up_squad
        if squad is None or not self.is_disembarking(squad):
            return
        mode = self._disembark_mode
        self.setup_controller.confirm_setup()
        if self.setup_controller.setting_up_squad is None:
            # confirm_setup() succeeded (it clears setting_up_squad only then).
            # Which TRANSPORT this unit stepped out of, for abilities that ask
            # (Falcon's Fire Support - see game/fire_support.py). The token
            # rather than the squad, because that is what the ability's "this
            # TRANSPORT" identifies; cleared at end of turn in main.py with the
            # other turn-scoped flags.
            squad.disembarked_from_this_turn = self._disembark_transport
            if mode in (RAPID, COMBAT, EMERGENCY):
                squad.charge_locked_until_end_of_turn = True
                # Rule 18.04/18.05: "that unit cannot move any further this
                # phase" for these three modes (only Tactical Disembark
                # allows a further Normal/Advance move) - a genuine,
                # pre-existing gap this codebase's own moved_squad_ids set
                # was never populated for here, found while wiring
                # Devilfish's "Rapid Deployment" (whose own wording, "counts
                # as having made a Normal move that phase", is this exact
                # behavior for the RAPID mode it resolves as).
                self.movement_controller.moved_squad_ids.add(squad)
            if self.game_log is not None:
                self.game_log.add(f"{squad.owner}: {squad.name} disembarks ({mode} disembark, rule 18.04/18.05).")
            if mode in (COMBAT, EMERGENCY):
                squad.battle_shocked = True
                # Rule 18.04/18.05: the hazard roll (06.03) happens AFTER the
                # unit is on the battlefield, not before it. Two reasons, and
                # the second one is a hard engine constraint, not a
                # preference:
                #
                #  - Sequence (user report: "erst muss ausgestiegen werden
                #    ... dann hazard rolls, dann noch eventuell deadly
                #    demise"). Rolling first also meant a model killed by the
                #    roll never had to be set up at all, quietly making a
                #    tight Emergency Disembark easier than the rule allows.
                #
                #  - Resolvability. A hazard failure inflicts mortal wounds,
                #    and 06.02 lets the OWNING player pick which model takes
                #    each one - which, in this UI, means clicking that model
                #    on the battlefield (main.py routes
                #    pending_damage_choice through
                #    input_manager.token_at_event(state.tokens, ...)). An
                #    embarked squad's models are deliberately NOT in
                #    state.tokens (see GameState.embarked_squads), so a
                #    pre-placement roll asked the human to click models that
                #    are not on the board and cannot be: a hard, permanent
                #    deadlock, reproduced with a destroyed Trukk carrying 10
                #    Boyz (4 hazard failures, 10 candidates, 0 of them
                #    clickable). That was the reported "das Spiel hängt
                #    daran, die Insassen aussteigen zu lassen".
                #
                # _disembarking_squad deliberately stays set until this step
                # finishes, so is_busy keeps Deadly Demise (24.08) and the
                # next queued Emergency Disembark waiting behind it.
                self._hazard_step = HazardRollStep(squad, len(squad.models), self.dice_manager, log=self._log)
            else:
                self._reset_disembark_state()

    def cancel_disembark(self):
        squad = self.setup_controller.setting_up_squad
        if squad is None or not self.is_disembarking(squad):
            return
        self.setup_controller.cancel_setup()  # triggers _on_cancel_disembark synchronously
        self._reset_disembark_state()

    def _on_cancel_disembark(self, squad):
        if self._disembark_mode == EMERGENCY:
            if self.game_log is not None:
                self.game_log.add(
                    f'{squad.owner}: {squad.name} is destroyed - could not be set up within 6" of its '
                    f'TRANSPORT (rule 18.05).'
                )
            # Nowhere to go back to - the TRANSPORT is gone. "Destroyed" has
            # to actually happen, though: cancel_setup() only pulled the
            # models back OUT of state.tokens, and _begin_placement() had
            # already taken the squad out of embarked_squads - so simply
            # returning here left a unit with living models that belonged
            # nowhere. It vanished from everything derived from the token
            # list (so it looked destroyed), but never went through the real
            # death pipeline, and main.py's "No Mercy" secondary therefore
            # silently scored nothing for it. Killing the models and putting
            # them back on the board lets remove_dead_models() do all of
            # that bookkeeping next frame, exactly as for any other
            # casualty - blood decals included, at the spot the TRANSPORT
            # died.
            for model in squad.models:
                model.current_wounds = 0
                if model not in self.game_state.tokens:
                    self.game_state.add_token(model)
            return
        squad.embarked_in = self._disembark_transport
        if squad not in self.game_state.embarked_squads:
            self.game_state.embarked_squads.append(squad)

    def _reset_disembark_state(self):
        self._disembarking_squad = None
        self._disembark_mode = None
        self._disembark_transport = None
        self._hazard_step = None

    # --- Emergency Disembark (18.05) ---

    def queue_transport_destroyed(self, dead_transport_token):
        """Rule 18.03/18.05: called from the same "model just destroyed"
        hook as Deadly Demise (main.py's remove_dead_models() loop) - every
        unit embarked within the destroyed TRANSPORT must make an
        emergency disembark move. `dead_transport_token` has already been
        removed from state.tokens by the time this runs, but its last
        known position (still on the object) is what "within 6\" of that
        TRANSPORT" is measured from."""
        for squad in list(self.embarked_squads_in(dead_transport_token)):
            self._emergency_queue.append((dead_transport_token, squad))

    @property
    def is_busy(self):
        """True while any disembark (player-driven or emergency) is in
        progress or queued - Deadly Demise must wait for this before
        rolling for the same destroyed TRANSPORT (rule 24.08's "after the
        units embarked within it have made their emergency disembark
        moves")."""
        return self._disembarking_squad is not None or bool(self._emergency_queue)

    def maybe_start_next_emergency(self):
        if self._disembarking_squad is not None or not self._emergency_queue:
            return
        if self.dice_manager is not None and self.dice_manager.is_pending:
            return
        transport_token, squad = self._emergency_queue.pop(0)
        self._disembarking_squad = squad
        self._disembark_mode = EMERGENCY
        self._disembark_transport = transport_token
        # Placement first; the hazard roll follows it in confirm_disembark().
        self._begin_placement()

    # --- shared dice/damage-choice plumbing for the pre-move hazard roll ---

    @property
    def pending_damage_choice(self):
        return self._hazard_step.pending_damage_choice if self._hazard_step is not None else None

    def choose_damage_model(self, model):
        if self._hazard_step is None:
            return
        self._hazard_step.choose_damage_model(model)
        self._finish_hazard_step_if_done()

    def on_dice_acknowledged(self):
        if self._hazard_step is None:
            return
        self._hazard_step.on_dice_acknowledged()
        self._finish_hazard_step_if_done()

    def _finish_hazard_step_if_done(self):
        """The hazard roll is the LAST step of a Combat/Emergency Disembark
        (see confirm_disembark()), so finishing it ends the whole disembark -
        releasing is_busy, which is what Deadly Demise (24.08) and the next
        queued Emergency Disembark are waiting on."""
        if self._hazard_step is None or not self._hazard_step.done:
            return
        self._hazard_step = None
        self._reset_disembark_state()

    # --- placement overlay ---

    def position_valid(self, squad, token, x_in, y_in):
        """Whether `token` (a model of the disembarking `squad`) could
        legally end up at (x_in, y_in) right now - used to paint the
        green/red placement overlay. Approximation: only the set-up
        distance from the TRANSPORT is checked (not the Rapid-Ingress
        follow-on constraint, which the overlay skips for simplicity, like
        Ingress's own overlay skips squad coherency)."""
        if not self.setup_controller.position_valid(token, x_in, y_in, squad=squad):
            return False
        transport_token = self._disembark_transport if self.is_disembarking(squad) else squad.embarked_in
        if transport_token is None:
            return True
        mode = self._disembark_mode if self.is_disembarking(squad) else self.determine_mode(transport_token, squad)
        # Rule 03.02: the unit must end up unengaged unless the mode waives
        # it (18.04's Combat Disembark). Painted here rather than left to
        # confirm_disembark(), so the overlay doesn't show green ground that
        # a single model standing on it would fail the whole placement from -
        # the same mismatch that destroyed a unit on the AI side, see
        # ai/agent_driver.py's _disembark_pack_positions().
        if mode != COMBAT and any(
            other.squad is not None and other.squad.owner != squad.owner
            and ((x_in - other.x_in) ** 2 + (y_in - other.y_in) ** 2) ** 0.5
            - token.radius_in - other.radius_in <= ENGAGEMENT_RANGE_IN
            for other in self.all_tokens
        ):
            return False
        distance = DISEMBARK_DISTANCE_IN[mode]
        dist = ((x_in - transport_token.x_in) ** 2 + (y_in - transport_token.y_in) ** 2) ** 0.5
        return dist - token.radius_in - transport_token.radius_in <= distance

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
