from game.stratagems import Stratagem

HEROIC_INTERVENTION_CP_COST = 1
LEAP_TO_DEFEND = "leap_to_defend"
INTO_THE_FRAY = "into_the_fray"


def _other_player(player):
    return "Player 2" if player == "Player 1" else "Player 1"


class HeroicInterventionController:
    """Rule 15.11 (Heroic Intervention, Core Stratagem, 1CP): WHEN end of
    your opponent's Charge phase, TARGET one friendly unengaged unit within
    6" of one or more enemy units (HEROIC_INTERVENTION_RANGE_IN in
    game/charge.py - a separate, shorter distance than a normal charge
    declare's 12" range) - a VEHICLE unit only qualifies if it's
    also CHARACTER or WALKER (UnitProfile.walker, first given a real value
    by Crisis Starscythe Battlesuits - before that, this exclusion only ever
    ruled out a pure-VEHICLE unit, same "excludes what we can't model yet"
    carve-out Rapid Ingress's AIRCRAFT / Fire Overwatch's TITANIC still are,
    since no datasheet has needed those yet). EFFECT:
    resolve a charge with the unit (rule 11.02), after first choosing a mode
    that changes which enemy units can be selected as charge targets - the
    mode-specific mechanics (Leap to Defend / Into the Fray) live in
    game/charge.py's ChargeController.start_reactive_charge()/
    eligible_charge_target_squads(); this controller only owns the reactive
    offer plus the mode decision, exactly like game/overwatch.py's
    FireOverwatchController owns Fire Overwatch's offer while
    game/shooting.py owns Snap Shooting's mechanics.

    Same reactive-decision shape as Rapid Ingress/Fire Overwatch (see
    game/rapid_ingress.py's docstring for why a DecisionManager fits here) -
    triggered off `phase_before == PHASE_CHARGE` (end of the Charge phase)
    in main.py's advance_turn_phase(), a different instant than Rapid
    Ingress/Fire Overwatch's Movement-phase-end, so there's no offer to
    chain against here (unlike those two, which react to the same instant
    and therefore need on_resolved-chaining to share DecisionManager's
    single pending slot).

    Mode selection is a SECOND, immediately-following decision, opened from
    within the first one's own resolution (_offer_mode(), called as the
    Stratagem's effect) - by the time it's opened, DecisionManager.
    is_pending is already False again (DecisionManager.choose() clears
    self.options before invoking the chosen callback), so it doesn't
    collide with the first one.

    Unlike Fire Overwatch, ChargeController itself never touches
    active_player (no save rolls or similar mid-resolution player switch
    happens during a charge) - but the charge ROLL is still a rule-15.02
    Command Re-roll candidate, and CommandRerollController spends CP
    against whoever turn_tracker.active_player currently is
    (_active_player()), not whoever actually owns the pending roll. Left
    untouched, active_player would still read `mover` throughout this
    entire reactive window (nothing else moves it there), silently
    misattributing the Command Re-roll cost to the wrong player - so
    offer() explicitly flips it to `opponent` up front, and every exit path
    (Decline, or the charge concluding via _on_charge_finished()) restores
    it back to `mover`. This also naturally makes the UI (e.g.
    GameStatusPanel's "Active Player" readout) correctly show who's
    actually making all these choices for the whole window, not just the
    charge roll.

    The board selection start_reactive_charge() has to make (
    ChargeController.begin_charge_move() requires movement_controller.
    selected_squad is active_squad) gets cleared the same way, in
    _on_charge_finished() - a happy coincidence identical to Rapid
    Ingress/Fire Overwatch's timing lets this work at all: by the time this
    fires, turn_tracker.phase has already become PHASE_FIGHT (Charge's
    successor), and MovementController.can_select() already allows
    selecting ANY squad during the Fight phase (rule 12.02/12.04), so no
    special-casing is needed there either."""

    def __init__(
        self, stratagem_controller, charge_controller, movement_controller, decision_manager,
        all_tokens=None, turn_tracker=None, game_log=None,
    ):
        self.stratagem_controller = stratagem_controller
        self.charge_controller = charge_controller
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self._stratagem = Stratagem(name="Heroic Intervention", cp_cost=HEROIC_INTERVENTION_CP_COST, effect=self._offer_mode)
        self._mover = None  # whose phase this actually is, to restore once the reactive charge ends (or is declined)

    def _all_squads(self):
        return {t.squad for t in self.all_tokens if t.squad is not None}

    def _is_vehicle_only(self, squad):
        return all(m.profile.vehicle for m in squad.models)

    def _has_character(self, squad):
        return any(m.profile.character for m in squad.models)

    def _has_walker(self, squad):
        return any(m.profile.walker for m in squad.models)

    def _eligible_squads(self, player):
        eligible = []
        for squad in self._all_squads():
            if squad.owner != player:
                continue
            if not self.charge_controller.can_start_reactive_charge(squad):
                continue
            if self._is_vehicle_only(squad) and not (self._has_character(squad) or self._has_walker(squad)):
                continue  # rule 15.11: a VEHICLE unit only qualifies if also CHARACTER/WALKER
            eligible.append(squad)
        return eligible

    def offer(self, mover, decision_manager):
        """Called right after `mover`'s Charge phase ends - offers
        `mover`'s opponent a chance to Heroic Intervention with one of
        their own eligible units. No-op if nothing qualifies, so an empty
        offer never flashes a "Decline"-only prompt (and active_player is
        never touched in that case either)."""
        opponent = _other_player(mover)
        eligible = [
            squad for squad in self._eligible_squads(opponent)
            if self.stratagem_controller.can_use(opponent, self._stratagem, [squad])
        ]
        if not eligible:
            return

        self._mover = mover
        if self.turn_tracker is not None:
            self.turn_tracker.set_active(opponent)

        options = [
            (f"Heroic Intervention: {squad.name} (1 CP)", lambda squad=squad: self._pick(opponent, squad))
            for squad in eligible
        ]
        options.append(("Decline", self._decline))
        decision_manager.request(
            opponent, "Heroic Intervention (1 CP) - charge with an unengaged unit near the enemy?", options,
            is_stratagem=True,
        )

    def _pick(self, player, squad):
        self.stratagem_controller.use(player, self._stratagem, [squad])

    def _decline(self):
        if self.turn_tracker is not None and self._mover is not None:
            self.turn_tracker.set_active(self._mover)
        self._mover = None

    def _offer_mode(self, controller, player, targets):
        """The Stratagem's effect - CP is already spent. Rule 15.11:
        "before making the charge roll, you must select one of the
        following modes" - a second decision, opened right here."""
        squad = targets[0]
        self.decision_manager.request(
            player, f"{squad.name}: choose a Heroic Intervention mode before rolling the charge (rule 15.11).",
            [
                (
                    'Leap to Defend (only enemy units that made a charge move this phase)',
                    lambda: self._start(squad, LEAP_TO_DEFEND),
                ),
                (
                    'Into the Fray (charge roll capped at 6", enemy units within 6")',
                    lambda: self._start(squad, INTO_THE_FRAY),
                ),
            ],
            is_stratagem=True,
        )

    def _start(self, squad, mode):
        if self.game_log is not None:
            mode_label = "Leap to Defend" if mode == LEAP_TO_DEFEND else "Into the Fray"
            self.game_log.add(f"{squad.owner}: Heroic Intervention - {squad.name} charges ({mode_label}, rule 15.11).")
        self.movement_controller.select(squad.models[0])
        self.charge_controller.start_reactive_charge(squad, mode, on_finished=self._on_charge_finished)

    def _on_charge_finished(self):
        if self.turn_tracker is not None and self._mover is not None:
            self.turn_tracker.set_active(self._mover)
        self._mover = None
        self.movement_controller.select(None)
