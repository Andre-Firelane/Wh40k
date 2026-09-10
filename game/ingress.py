from game.homing_beacon import HOMING_BEACON_MIN_ENEMY_DISTANCE_IN, HOMING_BEACON_RANGE_IN
from game import tunnelling_horrors
from game import unshrouded_truth
from game.squad import edge_distance
from game import ride_the_wind

INGRESS_SET_UP_DISTANCE_IN = 6.0
INGRESS_MIN_ENEMY_DISTANCE_IN = 8.0
INGRESS_MIN_BATTLE_ROUND = 2
# The one number Retaliation Cadre's The Shortened Blade stratagem changes.
# Defined here rather than in game/shortened_blade.py, which imports THIS
# module for the distance it replaces - one definition, no import cycle.
SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN = 6.0


class IngressController:
    """Rules 20.03/20.04 (Strategic Reserves, Ingress Move): a unit in
    strategic reserves (game_state.reserves) can arrive on the battlefield
    from battle round 2 onward via an Ingress move - mechanically Set Up
    (03.02, reused via SetupController's extra_check hook) plus two extra
    constraints checked at confirm time: every model wholly within 6" of a
    battlefield edge, and more than 8" from every enemy model. Rule 24.09
    ([DEEP STRIKE]): if every model in the unit has this ability, the
    edge-distance constraint is dropped entirely - it can be set up
    anywhere more than 8" from all enemy units, "even if that is within
    your opponent's deployment zone".
    Rule 20.04's own "Before the Third Battle Round: no models can be set
    up within your opponent's deployment zone" IS now enforced, per model,
    by _in_enemy_deployment_zone(). It could not be when this file was
    written - there were no deployment-zone coordinates then - but main.py
    has defined real ones since, so the old "isn't checked" note here had
    gone stale rather than the rule. That zone restriction is a constraint
    on the normal, arrive-from-a-battlefield-edge Ingress move, and a
    [DEEP STRIKE] unit is EXEMPT from it (user, confirming the open question
    this docstring used to record: "bei deep strike gibt es da eigentlich
    keine einschraenkungen. nur bei normalen platzieren von der
    spielfeldkante ohne deep strike"). So both of the normal move's
    placement constraints - within 6" of an edge, and outside the
    opponent's deployment zone before round 3 - are waived together for
    such a unit; only the "more than 8" from all enemy models" one still
    applies. That reading also matches 24.09's own "even if that is within
    your opponent's deployment zone" above, which was previously left
    unenforced because the wording hadn't been verified.
    The "excluding units embarked within TRANSPORTS that are themselves in
    reserves" carve-out doesn't apply either - we have no Transport/Embark
    mechanic.

    After a successful ingress, the unit can't make any other type of move
    until the next Charge phase (Squad.ingress_locked, checked by
    MovementController/ChargeController and cleared by main.py whenever the
    turn tracker reaches PHASE_CHARGE) - units still eligible to shoot in
    the meantime, since shooting isn't a move type."""

    def __init__(
        self, setup_controller, game_state, all_tokens, game_log=None,
        turn_tracker=None, board_width_in=None, board_height_in=None,
    ):
        self.setup_controller = setup_controller
        self.game_state = game_state
        self.all_tokens = all_tokens
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.board_width_in = board_width_in
        self.board_height_in = board_height_in
        self._ingressing_squad = None
        self.ingressed_this_phase = set()  # squads that ingressed THIS Movement phase - rule 18.04's Rapid Disembark reads this
        # The same fact on the TURN's clock, for rules that ask "was this unit
        # set up on the battlefield from Reserves this turn" after the
        # Movement phase is over - Windrider Host's Death from on High is the
        # first. Kept as its own set rather than read off the phase one: that
        # answer happens to be right today only because
        # reset_movement_phase() has not run again yet, which is a coincidence
        # of ordering rather than a statement about turns. And deliberately
        # not Squad.set_up_this_turn, which SetupController sets for EVERY
        # placement, deployment included, so it cannot answer a question about
        # Reserves.
        self.ingressed_this_turn = set()
        # Homing Beacon (user-supplied wargear item, game/homing_beacon.py):
        # the bearer Squad whose alternate placement rule (3" of the bearer,
        # >9" from enemies, instead of the normal 6"-of-edge/>8"-from-
        # enemies) applies to the CURRENT ingress - set by main.py as soon as
        # a reserves card matching RapidIngressController.pending_squad
        # starts being dragged (so the placement overlay is accurate for the
        # whole drag, not just after the drop), cleared once that ingress
        # actually finishes or is cancelled. None means "use the normal rule".
        self.homing_beacon_bearer = None
        # Retaliation Cadre's The Shortened Blade stratagem (2CP,
        # game/shortened_blade.py): the Squad whose CURRENT arrival was bought
        # the relaxed "more than 6\" from all enemy models" placement rule
        # instead of the normal 8". Scoped to one arrival exactly like
        # homing_beacon_bearer above, and cleared in the same two places -
        # nothing about the placement RULE outlives the placement. (The
        # stratagem's RESTRICTIONS clause does outlive it, but that lives on
        # the Squad, not here.) None means "use the normal rule".
        # The unit whose CURRENT arrival uses the relaxed 6" minimum in place
        # of rule 20.04's 8", and skips the board-edge band. Armed by TWO
        # sources with the same printed effect - Retaliation Cadre's The
        # Shortened Blade (see game/shortened_blade.py) and Baharroth's
        # Cloudstrider (see game/cloudstrider.py) - which is why it is named
        # after what it DOES rather than after either of them.
        self.relaxed_arrival_squad = None
        # Optional callable(squad) - fired once `squad`'s Set Up workflow
        # actually concludes (confirm_ingress() succeeds, or
        # cancel_ingress() abandons it) - wired in main.py to
        # RapidIngressController.notify_placement_resolved() so a Rapid
        # Ingress-chained Fire Overwatch offer (rule 15.08) waits for the
        # human to actually finish this placement instead of hijacking it
        # mid-drag (see that method's own docstring for the full bug report).
        # Listeners for "this unit is set up on the battlefield" - a LIST since
        # Swooping Hawks' Grenade Pack Flyover joined Rapid Ingress on it, the
        # same generalisation on_move_finished and on_squad_finished_shooting
        # already got.
        self.on_ingress_resolved = []

    def reset_movement_phase(self):
        self.ingressed_this_phase = set()

    def reset_turn(self):
        """Called from main.py's end-of-turn block. Its own method, and its
        own set, because "this phase" and "this turn" are different clocks."""
        self.ingressed_this_turn = set()

    def can_ingress(self, squad):
        if squad is None or squad not in self.game_state.reserves:
            return False
        # Seer Council's Unshrouded Truth prints "your unit MUST make an ingress
        # move this phase", which is only possible if it overrides rule 20.03's
        # round gate - so it does, and only for the unit it was used on. See
        # game/unshrouded_truth.py.
        if unshrouded_truth.applies(squad):
            return True
        # The Ophydian Destroyers' Tunnelling Horrors prints the same override
        # one phase later - "this unit MUST make an ingress move in your next
        # Movement phase (INCLUDING IN YOUR FIRST TURN)". That parenthesis is
        # what makes it load-bearing: a unit that tunnelled at the end of the
        # opponent's first turn is expected back in battle round 1, which 20.03
        # forbids. See game/tunnelling_horrors.py for why its flag has a
        # different lifetime from its twin's.
        #
        # NOT added to _has_deep_strike() below, which reads the same
        # unshrouded_truth.applies() two methods down: that grant exists
        # because an ASURYANI INFANTRY unit has no Deep Strike of its own, and
        # the Ophydian Destroyers print [DEEP STRIKE] on their datasheet.
        if tunnelling_horrors.applies(squad):
            return True
        # Windrider Host's Ride the Wind: "for the purposes of SETTING UP ...
        # on the battlefield, treat the current battle round number as being
        # one higher". Scoped to arrival and to nothing else - the counter
        # itself is untouched, so VP, mission timing and the round-3
        # destruction below all still read the real number.
        if self.turn_tracker is not None and ride_the_wind.arrival_battle_round(
                squad, self.turn_tracker.battle_round) < INGRESS_MIN_BATTLE_ROUND:
            return False
        return True

    def start_ingress(self, squad, x_in, y_in):
        if not self.can_ingress(squad):
            if self.game_log is not None:
                self.game_log.add(
                    f"{squad.owner if squad is not None else '?'}: can't make an Ingress move yet "
                    f"(rule 20.03 - only from battle round {INGRESS_MIN_BATTLE_ROUND} onwards)."
                )
            return
        self.game_state.reserves.remove(squad)
        self.setup_controller.start_setup(
            squad, x_in, y_in,
            on_cancel=lambda s: self.game_state.reserves.append(s),
            extra_check=self._extra_check,
            # Live per-position counterpart of _extra_check, so the drag
            # itself is held inside rule 20.04's legal ground instead of only
            # being told about it at Confirm - same predicate the green/red
            # overlay paints.
            placement_validator=lambda token, x, y: self.position_valid(squad, token, x, y),
        )
        self._ingressing_squad = squad

    def is_ingressing(self, squad):
        return squad is not None and squad is self._ingressing_squad

    def _has_deep_strike(self, squad):
        """Rule 24.09 ([DEEP STRIKE]): only applies "if every model in this
        unit has this ability" - a mixed unit gets no benefit from it.

        Seer Council's Unshrouded Truth grants it to the unit for this arrival
        ("your unit has Deep Strike"), which is a UNIT-level grant and therefore
        not subject to the every-model test - the datasheet ability is what that
        test is about."""
        if unshrouded_truth.applies(squad):
            return True
        return all(m.profile.deep_strike for m in squad.models)

    def deep_striking(self, squad):
        """Public name for the same question, for callers outside this module
        that have to ask it about the arrival in progress - The Shortened
        Blade's TARGET clause ("arriving using the Deep Strike ability this
        phase") is one. An alias rather than a rename, so the internal call
        sites stay put."""
        return self._has_deep_strike(squad)

    def _min_enemy_distance_relaxed(self, squad):
        """Kept beside _uses_relaxed_arrival() so the two halves of one rule
        cannot drift: whoever waives the board-edge band also relaxes the
        distance."""
        return SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN

    def _min_enemy_distance(self, squad):
        """How far every model of `squad` must end up from every enemy model
        for THIS arrival - one definition, so _extra_check() (Confirm) and
        position_valid() (overlay + drag clamp) cannot disagree.

        The Shortened Blade is checked before the Homing Beacon because it
        replaces the placement rule outright ("anywhere on the battlefield
        that is more than 6\"..."), and is strictly the more permissive of the
        two on distance - a player who has just spent 2 CP on it should not
        then be held to the beacon's own 9"."""
        if self.relaxed_arrival_squad is squad:
            return SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN
        if self.homing_beacon_bearer is not None:
            return HOMING_BEACON_MIN_ENEMY_DISTANCE_IN
        if self._uses_relaxed_arrival(squad):
            return self._min_enemy_distance_relaxed(squad)
        return INGRESS_MIN_ENEMY_DISTANCE_IN

    def _enemy_models_of(self, squad):
        return [
            t for t in self.all_tokens
            if t.squad is not None and t.squad is not squad and t.squad.owner != squad.owner
        ]

    def _in_enemy_deployment_zone(self, squad, x_in, y_in):
        """Rule 20.04, WHILE MOVING: "Before the Third Battle Round: While doing
        so, no models can be set up within your opponent's deployment zone."

        Rule 24.09 ([DEEP STRIKE]) exempts a unit whose every model has the
        ability - it "can be set up anywhere on the battlefield more than 8"
        from all enemy units, even if that is within your opponent's
        deployment zone". Reported from a real game: neither side could place
        a Deep Strike unit in the opponent's half at all, because this check
        applied to every unit (deliberately, while the wording was
        unverified - see the class docstring). Both demo Battlesuit
        datasheets in reserves have the ability, so it blocked every arrival
        that mattered.

        Was genuinely unimplementable when this module was written - the comment
        at the top of the file said so ("isn't checked - no concrete deployment
        zones") - but main.py has defined real zones since then, so the premise
        went stale rather than the rule. Reported from a real game: Ork
        Tankbustas arriving in battle round 2 landed at (2,39) with the
        opponent's zone starting at y=42, so the landing POINT was 3" clear but
        the squad spreads out from there and nothing stopped a model crossing in.

        Per MODEL, exactly as the rule is worded, and only before round 3 - from
        the third round on the restriction lifts entirely."""
        # The SECOND arrival gate the round number reaches, and Ride the Wind
        # says "for the purposes of setting up" without naming one - so this
        # takes the adjusted number too. A version that changed only
        # can_ingress() would look complete from can_ingress().
        if self.turn_tracker is None or ride_the_wind.arrival_battle_round(
                squad, self.turn_tracker.battle_round) >= 3:
            return False
        if self._has_deep_strike(squad):
            return False
        for zone in getattr(self.game_state, "deployment_zones", ()):
            if zone.owner != squad.owner and zone.contains_point(x_in, y_in):
                return True
        return False

    def _uses_relaxed_arrival(self, squad):
        """Whether this arrival uses the "anywhere on the battlefield, more
        than 6\" from all enemy models" rule.

        THREE sources now, on TWO clocks. The Shortened Blade and Baharroth's
        Cloudstrider arm relaxed_arrival_squad, which is ONE arrival and is
        cleared when that placement is confirmed or cancelled. Windrider
        Host's Daring Riders is bought while the unit is still in Reserves and
        lasts "until the end of the phase", so it keeps its own latch on the
        Squad. One rule, one enforcement, two lifetimes - each owned by the
        source whose printed text names it."""
        # Function-local: game/windrider_daring_riders.py imports the
        # distance constant from THIS module, so a top-level import here would
        # cycle. The same remedy game/tau_detachments.py records for its own.
        from game import windrider_daring_riders
        return (self.relaxed_arrival_squad is squad
                or windrider_daring_riders.is_active(squad))

    def _extra_check(self, squad):
        if self._uses_relaxed_arrival(squad):
            return self._relaxed_arrival_extra_check(squad)
        if self.homing_beacon_bearer is not None:
            return self._homing_beacon_extra_check(squad)

        errors = []
        deep_strike = self._has_deep_strike(squad)
        if not deep_strike and not all(self._within_setup_distance_of_point(m.x_in, m.y_in, m.radius_in) for m in squad.models):
            errors.append(
                f'Every model must be set up wholly within {INGRESS_SET_UP_DISTANCE_IN:.0f}" '
                f'of a battlefield edge (rule 20.04).'
            )

        too_close = any(
            edge_distance(model, enemy) <= INGRESS_MIN_ENEMY_DISTANCE_IN
            for model in squad.models
            for enemy in self._enemy_models_of(squad)
        )
        if too_close:
            errors.append(
                f'Every model must be set up more than {INGRESS_MIN_ENEMY_DISTANCE_IN:.0f}" '
                f'from all enemy units (rule 20.04).'
            )

        if any(self._in_enemy_deployment_zone(squad, m.x_in, m.y_in) for m in squad.models):
            errors.append(
                "Before the third battle round, no model can be set up within your "
                "opponent's deployment zone (rule 20.04)."
            )
        return errors

    def _relaxed_arrival_extra_check(self, squad):
        """"Can be set up anywhere on the battlefield that is more than 6\"
        horizontally away from all enemy models" - one constraint, and the
        only one.

        Named after the RULE rather than after The Shortened Blade, which was
        merely the first of what are now three sources (Cloudstrider and
        Daring Riders are the others). The distance below keeps that
        Stratagem's constant name because game/ingress.py is where it is
        defined and both other sources import it from here.

        The edge-distance and before-round-3 deployment-zone rules are absent
        here because "anywhere on the battlefield" removes them; the target is
        a [DEEP STRIKE] unit by the stratagem's own TARGET clause, so rule
        24.09 had already waived both anyway. "Horizontally" is the full
        distance on this flat board (no verticality is modelled)."""
        too_close = any(
            edge_distance(model, enemy) <= SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN
            for model in squad.models
            for enemy in self._enemy_models_of(squad)
        )
        if too_close:
            return [
                f'Every model must be set up more than {SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN:.0f}" '
                f'from all enemy models.'
            ]
        return []

    def _homing_beacon_extra_check(self, squad):
        """Homing Beacon (user-supplied wargear item): "The target must be
        set up within 3\" of the bearer's unit and more than 9\" away from
        all enemy units" - replaces (not adds to) the normal Ingress
        placement rule above; [DEEP STRIKE] is irrelevant here, since the
        edge-distance rule it would otherwise waive doesn't apply anyway."""
        bearer = self.homing_beacon_bearer
        errors = []
        near_bearer = all(
            any(edge_distance(m, b) <= HOMING_BEACON_RANGE_IN for b in bearer.models)
            for m in squad.models
        )
        if not near_bearer:
            errors.append(
                f'Every model must be set up within {HOMING_BEACON_RANGE_IN:.0f}" of '
                f'"{bearer.name}" (Homing Beacon).'
            )

        too_close = any(
            edge_distance(model, enemy) <= HOMING_BEACON_MIN_ENEMY_DISTANCE_IN
            for model in squad.models
            for enemy in self._enemy_models_of(squad)
        )
        if too_close:
            errors.append(
                f'Every model must be set up more than {HOMING_BEACON_MIN_ENEMY_DISTANCE_IN:.0f}" '
                f'from all enemy units (Homing Beacon).'
            )
        return errors

    def _within_setup_distance_of_point(self, x_in, y_in, radius_in):
        if self.board_width_in is None or self.board_height_in is None:
            return True
        return (
            x_in - radius_in <= INGRESS_SET_UP_DISTANCE_IN
            or (self.board_width_in - x_in - radius_in) <= INGRESS_SET_UP_DISTANCE_IN
            or y_in - radius_in <= INGRESS_SET_UP_DISTANCE_IN
            or (self.board_height_in - y_in - radius_in) <= INGRESS_SET_UP_DISTANCE_IN
        )

    def position_valid(self, squad, token, x_in, y_in):
        """Whether `token` (a model of `squad`) could legally end up at
        (x_in, y_in) right now - used to paint the green/red placement
        overlay. `squad` is passed explicitly (rather than read off
        self.setup_controller.setting_up_squad) so this also works while a
        squad is still being dragged out of the Reserves panel, before
        it's actually been dropped and PLACING has begun - the user wants
        the overlay visible from the moment the drag starts, not just
        after the drop.

        Combines SetupController's base checks (board edge, terrain, no
        overlap with already-placed OTHER tokens) with this rule's own:
        within 6" of a battlefield edge AND (before round 3) outside the
        opponent's deployment zone - both skipped entirely for a [DEEP
        STRIKE] unit, rule 24.09 - and more than 8" from every enemy
        model, which applies to everyone - or, while self.homing_beacon_bearer is set (user-supplied
        wargear item, game/homing_beacon.py), within 3" of the bearer's
        unit instead of the board edge, and more than 9" from every enemy
        model. Like _extra_check(), doesn't cover squad coherency/
        engagement, which depend on where the rest of the squad ends up."""
        if not self.setup_controller.position_valid(token, x_in, y_in, squad=squad):
            return False

        # Rule 20.04's zone restriction (waived for [DEEP STRIKE], 24.09),
        # checked here as well as in _extra_check() so the red/green overlay
        # shows it and, more importantly, so ai/agent_driver.py's candidate
        # sweep (which filters on this predicate) never offers such a spot in
        # the first place.
        if self._in_enemy_deployment_zone(squad, x_in, y_in):
            return False

        bearer = self.homing_beacon_bearer
        min_enemy_distance = self._min_enemy_distance(squad)

        if self._uses_relaxed_arrival(squad):
            pass  # "anywhere on the battlefield" - only the distance below applies
        elif bearer is not None:
            if not any(
                ((x_in - b.x_in) ** 2 + (y_in - b.y_in) ** 2) ** 0.5 - token.radius_in - b.radius_in <= HOMING_BEACON_RANGE_IN
                for b in bearer.models
            ):
                return False
        elif not self._has_deep_strike(squad) and not self._within_setup_distance_of_point(x_in, y_in, token.radius_in):
            return False

        for enemy in self._enemy_models_of(squad):
            dist = ((x_in - enemy.x_in) ** 2 + (y_in - enemy.y_in) ** 2) ** 0.5
            if dist - token.radius_in - enemy.radius_in <= min_enemy_distance:
                return False
        return True

    def confirm_ingress(self):
        squad = self.setup_controller.setting_up_squad
        if squad is None or not self.is_ingressing(squad):
            return
        self.setup_controller.confirm_setup()
        if self.setup_controller.setting_up_squad is None:
            # confirm_setup() succeeded (it clears setting_up_squad only then).
            squad.ingress_locked = True
            self.ingressed_this_phase.add(squad)
            self.ingressed_this_turn.add(squad)
            if self.game_log is not None:
                self.game_log.add(f"{squad.owner}: {squad.name} arrives via Ingress move (rule 20.04).")
            self._ingressing_squad = None
            self.homing_beacon_bearer = None
            self.relaxed_arrival_squad = None
            for listener in (self.on_ingress_resolved or ()):
                listener(squad)

    def cancel_ingress(self):
        squad = self.setup_controller.setting_up_squad
        if squad is None or not self.is_ingressing(squad):
            return
        self.setup_controller.cancel_setup()
        self._ingressing_squad = None
        self.homing_beacon_bearer = None
        self.relaxed_arrival_squad = None
        for listener in (self.on_ingress_resolved or ()):
            listener(squad)

    def destroy_remaining_reserves(self):
        """Rule 20.03: "At the end of the third battle round... all
        strategic reserves units that have not made one or more ingress
        moves are destroyed" - the TRANSPORT exception doesn't apply, since
        we have no Transport/Embark mechanic."""
        destroyed = list(self.game_state.reserves)
        self.game_state.reserves = []
        if self.game_log is not None:
            for squad in destroyed:
                self.game_log.add(
                    f"{squad.owner}: {squad.name} is destroyed - never arrived from strategic reserves (rule 20.03)."
                )
        return destroyed
