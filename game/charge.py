from game import grav_inhibitor_drone, hovering_death, neocapacitor_shields
from game import (aux_alien_expertise, kauyon_photon_grenades, loping_pounce,
                  montka_pulse_onslaught, monofilament_web, runes_of_fortune)
from game.dice import CHARGE_ROLL
from game.roll_bonus import advance_and_charge_bonus, sources as roll_bonus_sources
from game.squad import squad_has_full_throttle
from game.turn import PHASE_CHARGE
from game.waaagh import squad_waaagh_active
from game import move_exceptions

IDLE = "idle"
DECLARING_TARGETS = "declaring_targets"  # charge roll made (or pending); player picks 1+ charge targets

CHARGE_RANGE_IN = 12.0
HEROIC_INTERVENTION_RANGE_IN = 6.0  # rule 15.11: TARGET is within 6", not the normal 12" charge-declare range


class ChargeController:
    """Rules 11.01-11.04: declare a charge with an eligible unit, roll 2D6
    for the maximum charge distance, pick one or more enemy units within 12"
    and within that roll as charge targets, then (optionally) make the
    charge move. The actual model-by-model dragging reuses MovementController
    (rule 03) via start_charge_move(); this controller only tracks the
    charge-specific context (declared unit, roll, targets) and validates the
    result through Squad.check_charge_engagement on confirm.

    can_declare_charge() excludes a unit that Advanced or Fell Back this
    turn (rules 09.06/09.07), with two named exceptions: Stormboyz' own
    "Full Throttle" ability (user-supplied, see squad_has_full_throttle() -
    covers BOTH Advanced and Fell Back, permanently) and the Orks army rule
    "Waaagh!" (user-supplied, see game/waaagh.py - covers Advanced ONLY,
    and only while active for the squad's owner)."""

    def __init__(
        self, game_log=None, dice_manager=None, turn_tracker=None, all_tokens=None, movement_controller=None,
        waaagh=None,
    ):
        self.game_log = game_log
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.movement_controller = movement_controller
        self.waaagh = waaagh

        self.state = IDLE
        # Set by reopen_target_selection() when a reaction takes a declared
        # target off the board, so the reaction chain stops instead of falling
        # through into the move. See that method.
        self._declaration_reopened = False
        self.active_squad = None
        self.max_distance = None       # charge roll result (2D6), None until the roll is acknowledged
        self.charge_targets = []       # declared enemy squads for this charge
        # Optional callable(charging_squad, targets, resume) -> bool, fired by
        # begin_charge_move() at exactly rule 15.xx's "just after an enemy unit
        # has declared a charge" moment - the point where the targets are
        # locked in but no model has moved. Wired in main.py to Retaliation
        # Cadre's Grav-Inhibitor Field (game/grav_inhibitor_field.py). Returning
        # True means "I have opened something the player must answer first" and
        # takes ownership of `resume`, which starts the move once that is done;
        # returning False (or having no hook at all) leaves the flow exactly as
        # it was. The move is DEFERRED rather than started alongside because a
        # reaction can inflict mortal wounds, and a charge move left open on a
        # unit that has just been wiped out is the kind of half-state this
        # project has repeatedly had to unpick.
        self.on_charge_declared = None
        # Further reactors to the same instant, tried after the slot above.
        # A LIST because more than one Stratagem can answer one declaration -
        # Kauyon prints two (Photon Grenades and Combat Embarkation) - and
        # _offer_declaration_reactions() chains them so each gets its window
        # instead of the first one swallowing the rest. The single slot above
        # is kept so its existing owner needs no change; both use the same
        # "return True to take ownership of the resume" protocol.
        self.charge_declaration_reactions = []
        # Listeners for rule 11.04's "ends a Charge move" - fired with the
        # charging squad by confirm_charge_move() once the move is ACCEPTED.
        # Wired in main.py to the Skorpekh Lord's Crimson Harvest.
        #
        # A LIST rather than a single callable, unlike on_charge_declared just
        # above: that one has a return-value protocol ("True means I took
        # ownership of resume"), which forces exactly one owner. This is a
        # plain notification with nothing to own, so a second listener should
        # cost a line and not a refactor.
        #
        # And it is deliberately NOT in _finish_charge(), which also runs for
        # a DECLINED charge and for a unit destroyed before it could move -
        # neither of those ends a Charge move.
        self.on_charge_move_finished = []
        self.charged_squad_ids = set()  # squads that already declared a charge this phase
        self._pending_roll = False

        # Rule 15.11 (Heroic Intervention): a reactive charge triggered
        # outside the unit's own Charge phase - see start_reactive_charge().
        self._reactive = False
        self._mode = None                    # None | "leap_to_defend" | "into_the_fray"
        self._on_reactive_finished = None

    def reset_charge_phase(self):
        """Rule 11.02: a new Charge phase comes around every battle round."""
        self.charged_squad_ids = set()

    def _enemy_squads_within(self, squad, max_range):
        enemy_squads = {
            token.squad for token in self.all_tokens
            if token.squad is not None and token.squad.owner != squad.owner
        }
        return {s for s in enemy_squads if squad.min_distance_to(s) <= max_range}

    # Set by main.py - rule 16.01's "not eligible to declare a charge" lock.
    action_controller = None

    def can_declare_charge(self, squad, ignore_phase=False):
        """Rule 11.02 step 1 eligibility.

        ignore_phase=True answers the forecast "WOULD this unit be eligible
        once the Charge phase comes around", which is what the Shooting phase
        needs to know: shooting a unit you mean to charge removes its closest
        models and can push the charge out of reach (see
        _charge_cost_of_shooting() in ai/agent_driver.py), so that warning is
        only worth printing for a unit that can still charge this turn. Every
        other check here (Advanced/Fell Back, engaged, disembark/ingress
        locks, an enemy within 12") is already decided by the time Shooting
        runs, so this stays one source of truth instead of a second,
        drifting copy of the eligibility rules."""
        if squad is None or squad in self.charged_squad_ids:
            return False
        if not ignore_phase and self.turn_tracker is not None and self.turn_tracker.phase != PHASE_CHARGE:
            return False
        if squad.ingress_locked:
            return False  # rule 20.04: not eligible for any other move type until the next Charge phase
        if squad.charge_locked_until_end_of_turn:
            return False  # rules 18.04/18.05: Rapid/Combat/Emergency Disembark forbid a charge this turn
        # Rule 16.01: "If a unit starts an action, until the end of the turn...
        # it is not eligible to declare a charge." No TITANIC carve-out on this
        # half of the rule, unlike the shooting one.
        if self.action_controller is not None and self.action_controller.blocks_charge(squad):
            return False
        # Stormboyz' "Full Throttle" (user-supplied): "eligible to declare a
        # charge in a turn in which it Advanced or Fell Back" - a named
        # exception to the two checks right below, not to any other check
        # in this method (e.g. still blocked by Disembark-lock above, or by
        # already being engaged/out of range below).
        full_throttle = squad_has_full_throttle(squad)
        # The Foetid Bloat-drone's Hovering Death: "eligible to shoot AND declare
        # a charge in a turn in which it Fell Back" - so both halves of rule
        # 09.07's ban have to ask, not just the shooting one.
        if squad.fell_back_this_turn and not move_exceptions.may_charge_after_falling_back(squad):
            return False  # rule 09.07: a unit that Fell Back this turn cannot charge until the end of the turn
        if squad.is_engaged(self.all_tokens):
            return False
        # Orks army rule "Waaagh!" (user-supplied): "eligible to declare a
        # charge in a turn in which they Advanced" - ADVANCED only, unlike
        # Full Throttle above (no Fell Back exception in this ability's own
        # text), and only while active for this squad's owner.
        # Kroot Hounds' Loping Pounce is the THIRD source of the same
        # exception. Unlike the two beside it, it is LATCHED rather than
        # live - set at the start of the Command phase and held all turn -
        # so it reads a flag rather than a distance; see
        # game/loping_pounce.py on why the printed text demands that.
        # Auxiliary Cadre's Alien Expertise is the FOURTH source of the same
        # exception, and the second latched one - bought for one unit in the
        # Movement phase and read here, a phase later.
        advance_ok = move_exceptions.may_charge_after_advancing(squad, self.waaagh)
        if self.movement_controller is not None and squad in self.movement_controller.advanced_squad_ids and not advance_ok:
            return False
        return len(self._enemy_squads_within(squad, CHARGE_RANGE_IN)) > 0

    def declare_charge(self, squad):
        if not self.can_declare_charge(squad):
            return
        self.active_squad = squad
        self.max_distance = None
        self.charge_targets = []
        self.state = DECLARING_TARGETS
        if self.dice_manager is not None:
            # target_squad/subject_label: the unit named on a Charge roll is
            # the one DOING the charging (its targets are not even chosen yet -
            # they are filtered out of what the roll reaches, see
            # targets_reachable_with()), so the panel shows its art and calls
            # it "Charging" rather than "Target". User: "wenn charge overlay
            # kommt, also wenn angesagt wird, wer den charge roll macht - da
            # will ich auch ein sprite haben."
            self.dice_manager.roll(
                count=2, sides=6, label="Charge Roll", target_name=squad.name,
                roll_kind=CHARGE_ROLL, target_squad=squad, subject_label="Charging",
            )
            self._pending_roll = True

    def can_start_reactive_charge(self, squad):
        """Rule 15.11 (Heroic Intervention) TARGET eligibility: unengaged
        and within 6" of one or more enemy units - NOT the normal 12"
        charge-declare range (CHARGE_RANGE_IN), a separate, shorter,
        Heroic-Intervention-specific distance (HEROIC_INTERVENTION_RANGE_IN).
        Also deliberately NOT can_declare_charge()'s other checks (phase ==
        PHASE_CHARGE, ingress-lock, advanced-this-turn, already-charged-
        this-phase) - all of those are about the unit's OWN Charge-phase
        activation, which for the reacting player hasn't happened yet this
        round (Heroic Intervention fires during the OPPONENT's Charge
        phase). `self.state != IDLE` guards against a still-open normal
        charge declaration (shouldn't normally happen, but ChargeController
        is a single shared instance for both players)."""
        if squad is None or self.state != IDLE:
            return False
        if squad.is_engaged(self.all_tokens):
            return False
        return len(self._enemy_squads_within(squad, HEROIC_INTERVENTION_RANGE_IN)) > 0

    def start_reactive_charge(self, squad, mode, on_finished=None):
        """Rule 15.11 (Heroic Intervention): EFFECT is "resolve a charge
        with your unit (11.02)" - reuses declare_charge()'s roll/target/
        move/confirm machinery entirely, just entered through a different
        gate (can_start_reactive_charge() above) since can_declare_charge()
        doesn't apply here. `mode` ("leap_to_defend"/"into_the_fray")
        changes eligible_charge_target_squads() below and, for Into the
        Fray, caps the roll (on_dice_acknowledged()) - "before making the
        charge roll, you must select one of the following modes", so the
        caller (game/heroic_intervention.py) resolves that choice BEFORE
        calling this. `_reactive` keeps this OUT of charged_squad_ids (see
        _finish_charge()) - doesn't use up the unit's real Charge-phase
        activation later this round. `on_finished` fires once this
        concludes, whether completed or declined/cancelled."""
        if not self.can_start_reactive_charge(squad):
            return
        self.active_squad = squad
        self.max_distance = None
        self.charge_targets = []
        self.state = DECLARING_TARGETS
        self._reactive = True
        self._mode = mode
        self._on_reactive_finished = on_finished
        if self.dice_manager is not None:
            self.dice_manager.roll(
                count=2, sides=6, label="Charge Roll (Heroic Intervention)", target_name=squad.name,
                roll_kind=CHARGE_ROLL, target_squad=squad, subject_label="Charging",
            )
            self._pending_roll = True

    def _capped_roll(self, total):
        """Rule 15.11 (Into the Fray): "if the result is greater than 6
        (after modifiers), change it to 6". Returns (distance, note) - one
        definition, shared by the roll that is being acknowledged and by
        targets_reachable_with()'s forecast about a roll that isn't.

        Bonuses to the Charge roll (game/roll_bonus.py: War Horde's 'Ere We
        Go and the Avatar of Khaine's The Bloody-Handed, which stack) are added
        here, which puts them BEFORE the cap, exactly as Into the Fray's own
        "after modifiers" wording requires. Both callers get them for the same
        reason they both get the cap."""
        bonus = advance_and_charge_bonus(self.active_squad, self.all_tokens)
        note = "".join(f" (+{amount} - {label})"
                       for label, amount in roll_bonus_sources(self.active_squad, self.all_tokens))
        total += bonus
        # The Twin Lance's Neocapacitor Shields: -1 on Charge rolls made FOR
        # this unit (as opposed to the Grav-inhibitor Drone's -2, which
        # depends on who is being charged and is applied in
        # _distance_against()). Both are negative modifiers, and the drone's
        # own text says its -2 is not cumulative with any other - see
        # _negative_charge_modifier(), which is where the two are reconciled.
        penalty = neocapacitor_shields.charge_penalty_for(self.active_squad)
        if penalty:
            note += f" (-{penalty} - Neocapacitor Shields)"
            total -= penalty
        # Kauyon's Photon Grenades: "subtract 2 from Charge rolls made FOR that
        # enemy unit" - the same side as Neocapacitor Shields above, so it
        # joins the charger-side total here and the drone's
        # not-cumulative-with-anything -2 stays reconciled in one place.
        grenades = kauyon_photon_grenades.charge_penalty_for(self.active_squad)
        if grenades:
            note += f" (-{grenades} - Photon Grenades)"
            total -= grenades
        # Mont'ka's Pulse Onslaught leaves a unit `shaken`: -2 on Charge rolls
        # made for it, the third charger-side penalty in this fold.
        shaken = montka_pulse_onslaught.roll_penalty_for(self.active_squad)
        if shaken:
            note += f" (-{shaken} - shaken)"
            total -= shaken
        # The Night Spinner's Monofilament Web leaves a unit `pinned`: -2 on
        # Charge rolls, and NOT on Advance rolls - the one clause that makes
        # it a different status from shaken. They stack.
        pinned = monofilament_web.charge_penalty_for(self.active_squad)
        if pinned:
            note += f" (-{pinned} - pinned)"
            total -= pinned
        # The Warlock's Runes of Fortune: -2 if any DECLARED TARGET of this
        # charge carries it. The first defender-side term in this fold - the
        # other three are properties of the charging unit - which is why it
        # reads self.charge_targets. Only ever -2, however many targets carry
        # it: the rule says subtract 2, not subtract 2 per unit.
        runes = runes_of_fortune.charge_penalty_against(self.charge_targets)
        if runes:
            note += f" (-{runes} - Runes of Fortune)"
            total -= runes
        if self._mode == "into_the_fray" and total > 6:
            return 6, note + ' (capped to 6" - [Into the Fray])'
        return total, note

    def on_dice_acknowledged(self):
        if not self._pending_roll or self.dice_manager is None:
            return
        rolls = self.dice_manager.last_values
        total, capped_note = self._capped_roll(sum(rolls))
        self.max_distance = total
        self._pending_roll = False
        # Named, because an unattributed roll cannot be read back. Tracing a
        # reported "why did the Meganobz not charge" needed four consecutive
        # "Charge Roll ..." lines to be matched to units by alphabetical
        # elimination against which unit later moved - and the answer turned
        # out to be that the unit in question never rolled at all.
        who = self.active_squad.name if self.active_squad is not None else "?"
        self._log(f'{who} - Charge Roll {rolls}: maximum charge distance '
                  f'{self.max_distance}"{capped_note}.')

    def targets_reachable_with(self, roll_total):
        """Which units COULD be declared as charge targets if the roll came
        out as `roll_total` - the same rule 11.04 gate as
        eligible_charge_target_squads(), asked about a roll that hasn't been
        acknowledged yet (max_distance is still None while the dice sit on
        screen waiting for a click).

        Exists for the Command Re-roll decision (15.02, which by rule can
        only be made "just after making the charge roll", i.e. exactly in
        that window): "did this charge fail" is precisely "is this set
        empty", and "could a re-roll even help" is the same question asked
        with a maximum roll. Deliberately reuses the real gate rather than
        re-deriving it, so the reactive Heroic-Intervention modes (15.11)
        stay covered without a second copy of their rules."""
        distance, _ = self._capped_roll(roll_total)
        return self.eligible_charge_target_squads(max_distance=distance)

    def eligible_charge_target_squads(self, max_distance=None):
        """Rule 11.04 BEFORE MOVING: enemy units within 12" and within the
        charge roll - the only squads that can be declared as targets.
        Rule 15.11 overrides this while a reactive Heroic Intervention
        charge is in progress: Leap to Defend drops the 12" gate entirely
        in favor of "made a charge move this phase" (Squad.fights_first -
        set only by a successful charge move, see MovementController.
        confirm_move() - not rule 24.13's permanent datasheet ability,
        which lives on the model profile instead); Into the Fray narrows
        the range gate to 6" (redundant in practice with max_distance
        already capped to <=6" above, but matches the rule text exactly
        rather than relying on that being implied).

        `max_distance` overrides the acknowledged roll - only
        targets_reachable_with() passes it, to ask the same question about a
        roll that is still pending. Everything else calls this with no
        argument and gets exactly the behaviour it always had."""
        distance = self.max_distance if max_distance is None else max_distance
        if self.active_squad is None or distance is None:
            return set()
        if self._mode == "leap_to_defend":
            enemy_squads = {
                token.squad for token in self.all_tokens
                if token.squad is not None and token.squad.owner != self.active_squad.owner
            }
            return {
                s for s in enemy_squads
                if s.fights_first and self.active_squad.min_distance_to(s) <= self._distance_against(s, distance)
            }
        if self._mode == "into_the_fray":
            within_6 = self._enemy_squads_within(self.active_squad, HEROIC_INTERVENTION_RANGE_IN)
            return {s for s in within_6 if self.active_squad.min_distance_to(s) <= self._distance_against(s, distance)}
        within_12 = self._enemy_squads_within(self.active_squad, CHARGE_RANGE_IN)
        return {s for s in within_12 if self.active_squad.min_distance_to(s) <= self._distance_against(s, distance)}

    def _distance_against(self, candidate, distance):
        """`distance` reduced by any negative Charge-roll modifier that would
        apply once `candidate` is among the declared targets - today only the
        Grav-inhibitor Drone's -2 (see game/grav_inhibitor_drone.py for why
        the penalty is applied here, at the point the roll is CONSUMED,
        rather than where it is rolled).

        Evaluated as "the penalty of what is already declared, plus this
        candidate" rather than the candidate alone: the modifier hits the
        ROLL, so once any declared target carries the drone every other
        target of the same charge is measured against the reduced distance
        too. max() rather than a sum encodes the rule's own "not cumulative"
        clause."""
        return distance - self._extra_target_penalty(list(self.charge_targets) + [candidate])

    def _extra_target_penalty(self, targets):
        """How much MORE to subtract because of who is being charged, on top
        of whatever _capped_roll() already took off the roll itself.

        The Grav-inhibitor Drone's -2 "is not cumulative with any other
        negative modifiers to that Charge roll", so a unit that is also under
        Neocapacitor Shields (-1, already applied in _capped_roll()) ends up
        at -2 in total, not -3 - hence subtracting only the difference here
        rather than the drone's full value. This is the one place the two
        negative sources meet, which is why the reconciliation lives here and
        each module keeps only its own number."""
        drone = grav_inhibitor_drone.charge_penalty_against(targets)
        if not drone:
            return 0
        already = neocapacitor_shields.charge_penalty_for(self.active_squad)
        return max(0, drone - already)

    def effective_charge_distance(self):
        """The distance the models actually get to move, i.e. the acknowledged
        roll minus any negative modifier the DECLARED targets impose. The
        second half of "subtract 2 from the Charge roll": without it the
        charge would be harder to declare but no harder to complete."""
        if self.max_distance is None:
            return None
        return self.max_distance - self._extra_target_penalty(self.charge_targets)

    def toggle_charge_target(self, enemy_squad):
        if self.state != DECLARING_TARGETS or enemy_squad not in self.eligible_charge_target_squads():
            return
        if enemy_squad in self.charge_targets:
            self.charge_targets.remove(enemy_squad)
        else:
            self.charge_targets.append(enemy_squad)

    def reopen_target_selection(self, dropped_squad=None):
        """Hand target declaration back to the charging player, roll intact.

        Combat Embarkation (Kauyon) prints "Your unit can embark within that
        TRANSPORT. If it does, your opponent can select new targets for that
        charge." The second sentence had no implementation, and
        _start_declared_move() re-checks state, targets-non-empty and
        max_distance but never re-validates the TARGETS themselves - so the
        charge went ahead against a unit now sitting inside a vehicle, whose
        models embark() takes off the token list while leaving their
        coordinates alone, and check_charge_engagement() duly engaged a
        phantom. Reported: "nach combat embarkation stratagem: auswahl bei
        attacker muss zurueckspringen auf choose charge targets".

        No state-machine change is needed. The controller never LEAVES
        DECLARING_TARGETS during a declaration reaction, and max_distance is
        already fixed - the printed effect re-opens the TARGETS, not the roll.
        All this does is drop the target that left and stop the reaction chain
        falling through into the move, so toggle_charge_target() and the "Begin
        Charge Move" button are live again.

        The AI needs nothing new: _handle_charge() already returns when a
        reaction owns the resume and re-enters later, where an empty
        charge_targets makes it pick again from
        eligible_charge_target_squads() - which is built from the token list
        and therefore no longer offers the embarked unit.
        """
        if self.state != DECLARING_TARGETS:
            return False
        if dropped_squad is not None and dropped_squad in self.charge_targets:
            self.charge_targets.remove(dropped_squad)
        self._declaration_reopened = True
        return True

    def begin_charge_move(self):
        """Attempt Charge (11.02 step 3): start the actual drag-based move,
        capped at the charge roll distance."""
        if self.state != DECLARING_TARGETS or not self.charge_targets or self.max_distance is None:
            return
        if self.movement_controller is None or self.movement_controller.selected_squad is not self.active_squad:
            return
        self._offer_declaration_reactions(list(self.charge_targets))

    def _offer_declaration_reactions(self, targets):
        """Give each registered reactor its window, in order, then move.

        CHAINED rather than "first one wins": each reactor is handed a resume
        that continues to the NEXT one, so a charge declaration that two
        different reactions could answer offers both - which is what the rules
        say, and what a single-owner slot could not do.

        The single `on_charge_declared` slot is still honoured and goes FIRST,
        so nothing that already used it has to change. Both forms keep the same
        protocol: return True to say "I opened something and now own the
        resume", anything else to decline and let the chain continue.
        """
        reactors = ([self.on_charge_declared] if self.on_charge_declared is not None else [])
        reactors += list(self.charge_declaration_reactions)

        # Captured ONCE. Every reactor in this chain is answering the SAME
        # declaration, so the charging unit is a fixed fact of the window - and
        # re-reading self.active_squad per step is how a cleared field leaked
        # out to a reactor as None (reported crash: Photon Grenades resolved,
        # the resume ran, and Combat Embarkation was handed None).
        charging = self.active_squad
        self._declaration_reopened = False

        def window_is_open():
            """Is the declaration these reactors share still standing?

            A reaction's own resolution can END the charge outright - the
            Grav-Inhibitor Field's mortal wounds can destroy the charging unit,
            and its _finish() says in as many words that it relies on the
            resume landing somewhere that re-checks. That was true while the
            resume went straight to _start_declared_move(); chaining put other
            reactors in between, so the check has to move here. Their window is
            "just after an enemy unit has selected its charge target" - once
            there is no charge, there is nothing left to react to, and offering
            it anyway would let a player spend CP on a charge that is over.
            """
            return (charging is not None and self.active_squad is charging
                    and self.state == DECLARING_TARGETS
                    and not self._declaration_reopened)

        def step(index):
            while index < len(reactors):
                if not window_is_open():
                    return
                reactor = reactors[index]
                index += 1
                if reactor(charging, list(targets), lambda i=index: step(i)):
                    return  # that reactor owns the continuation now
            # Asked ONCE MORE at the end of the chain, not only between
            # reactors: a reaction that re-opened target declaration (Combat
            # Embarkation) is answered by the LAST reactor as often as not, and
            # falling out of the loop straight into the move would resolve a
            # charge whose targets the opponent is entitled to pick again.
            if not window_is_open():
                return
            self._start_declared_move()

        step(0)

    def _start_declared_move(self):
        """The second half of begin_charge_move(), split out so a reaction to
        the declaration (see on_charge_declared) can run to completion first
        and then resume it.

        Re-checks its preconditions rather than trusting the ones
        begin_charge_move() saw: an arbitrary amount of resolution can have
        happened in between, including one that destroys the charging unit -
        in which case there is no charge to make and the attempt is finished
        (rule 11.02: "the charge is resolved either way")."""
        if self.state != DECLARING_TARGETS or not self.charge_targets or self.max_distance is None:
            return
        if self.movement_controller is None or self.movement_controller.selected_squad is not self.active_squad:
            return
        if self.active_squad is None:
            # Nothing to log a name for, and nothing to finish - whoever
            # cleared it already ran _finish_charge(). Split from the check
            # below because the combined form short-circuited on None and then
            # formatted None.name, the same crash shape as the reported one.
            return
        if not any(not m.is_dead() for m in self.active_squad.models):
            self._log(f"{self.active_squad.name} cannot complete its charge - the unit was destroyed.")
            self._finish_charge()
            return
        # effective_charge_distance(), not max_distance: a Grav-inhibitor
        # Drone among the declared targets subtracts 2 from the Charge roll,
        # which has to shorten the MOVE as well as the declaration - see
        # game/grav_inhibitor_drone.py.
        distance = self.effective_charge_distance()
        if distance != self.max_distance:
            self._log(
                f'{self.active_squad.name}\'s charge distance is reduced to {distance}" '
                "(Grav-inhibitor Drone)."
            )
        self.movement_controller.start_charge_move(distance, list(self.charge_targets))

    def confirm_charge_move(self):
        """Wraps MovementController.confirm_move(): only finishes the charge
        (unit can't charge again this phase) once the move is confirmed
        without errors - a rejected move stays in progress so the player
        can reposition, exactly like a normal move."""
        if self.movement_controller is None:
            return
        squad = self.active_squad
        targets = list(self.charge_targets)
        rolled = self.max_distance
        self.movement_controller.confirm_move()
        if self.movement_controller.errors:
            return
        # Record WHAT was charged and how close it ended up. Logged here in the
        # engine rather than in the AI driver so it covers every charge on the
        # board: the human's, the AI's, and the reactive ones (Heroic
        # Intervention, 15.11) that never touch ai/agent_driver.py's charge path
        # at all - which is exactly the case that went unrecorded when a user
        # asked whether a charge had actually succeeded ("mindestens ein squad
        # hat den charge geschafft, aber sich dann nicht bewegt").
        #
        # The closing distance is included because rule 11.04's WHILE MOVING
        # wants 1" wherever a model can manage it, while "engaged" only needs
        # Engagement Range - so a charge can be legal and still look short, and
        # only the number distinguishes the two.
        if squad is not None:
            for target in targets:
                self._log(
                    f"  [charge] {squad.name} -> {target.name}: {rolled}\" roll, "
                    f"closed to {squad.min_distance_to(target):.1f}\" "
                    f"(engaged: {squad.is_engaged_with(target)})"
                )
        self._finish_charge()
        # Rule 11.04's "ends a Charge move", fired AFTER _finish_charge() so
        # the charge is fully concluded before a listener can open a dice roll
        # or a prompt on top of it. `squad` was captured above precisely
        # because _finish_charge() clears active_squad.
        for listener in list(self.on_charge_move_finished):
            listener(squad)

    def decline_charge_move(self):
        """Rule 11.02 step 3: 'if you still want to' - the player can
        decline to make the charge move at all (or abandon one already in
        progress); the charge is resolved either way, so the unit can't
        declare a charge again this phase."""
        if self.state != DECLARING_TARGETS:
            return
        if self.movement_controller is not None and self.movement_controller.move_mode == "charge":
            self.movement_controller.cancel_move()
        self._finish_charge()

    def reset_charge_move(self):
        """Real user report: the single Cancel button mid-drag used to
        always call decline_charge_move() - reverting the drag AND
        finishing the whole charge attempt (rule 11.02's "the charge is
        resolved either way", marking the unit as already charged this
        phase) - even when all the player wanted was to redo their
        positioning for the SAME already-declared charge (same roll, same
        targets). "ich kann danach keinen move mehr machen... ich bräuchte
        2 Optionen: Charge komplett abbrechen und Movement resetten."

        This is that second option: undoes the in-progress drag (models
        back to their pre-move positions, same as cancel_move() always
        does) WITHOUT finishing the charge - self.state stays
        DECLARING_TARGETS and max_distance/charge_targets are untouched, so
        the player can click "Begin Charge Move" again and try a different
        path with the exact same roll. Only meaningful mid-drag (movement_
        controller.move_mode == "charge"); a no-op otherwise, since there's
        nothing to reset before the move has even started."""
        if self.state != DECLARING_TARGETS:
            return
        if self.movement_controller is None or self.movement_controller.move_mode != "charge":
            return
        self.movement_controller.cancel_move()

    def _finish_charge(self):
        # Rule 15.11: a reactive Heroic Intervention charge isn't the
        # unit's real Charge-phase activation - don't mark it as "already
        # charged this phase" against it.
        if self.active_squad is not None and not self._reactive:
            self.charged_squad_ids.add(self.active_squad)
        self.active_squad = None
        self.max_distance = None
        self.charge_targets = []
        self.state = IDLE
        self._finish_reactive()

    def _finish_reactive(self):
        """Rule 15.11: whether a reactive charge (start_reactive_charge())
        actually resolved or was declined/cancelled, let the caller
        (game/heroic_intervention.py) know - it needs to clear the board
        selection start_reactive_charge() had to make (begin_charge_move()
        requires movement_controller.selected_squad is active_squad). A
        safe no-op for a normal (non-reactive) charge."""
        if not self._reactive:
            return
        callback = self._on_reactive_finished
        self._reactive = False
        self._mode = None
        self._on_reactive_finished = None
        if callback is not None:
            callback()

    def _log(self, message):
        if self.game_log is not None:
            player = self.turn_tracker.active_player if self.turn_tracker is not None else None
            self.game_log.add(f"{player}: {message}" if player else message)
