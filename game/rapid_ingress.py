from game.stratagems import Stratagem

RAPID_INGRESS_CP_COST = 1
RAPID_INGRESS_MIN_BATTLE_ROUND = 2  # rule 15.07: "cannot use this stratagem during the first battle round"


class RapidIngressController:
    """Rule 15.07 (Rapid Ingress, Core Stratagem, 1CP): WHEN end of your
    opponent's Movement phase, TARGET one friendly unit in strategic
    reserves (excluding AIRCRAFT - we have no AIRCRAFT keyword, so every
    reserves unit qualifies), EFFECT that unit makes an ingress move (rule
    20.04). RESTRICTIONS: not during the first battle round.

    Every other stratagem so far is offered via a button the acting player
    clicks on their OWN turn. This one's WHEN is a reactive window that
    opens on the OTHER player's turn, at a phase-transition instant nobody
    clicks into - exactly the "certain rules... trigger at specific
    moments and must interrupt the game" case DecisionManager's own
    docstring already anticipated (its "fire Overwatch... at the end of
    the opponent's Shooting phase" example). main.py's advance_turn_phase()
    calls offer() right after leaving the Movement phase, passing whichever
    player's Movement phase just ended; offer() then opens a DecisionManager
    request for that player's OPPONENT - one option per eligible reserves
    squad plus "Decline". The overlay doesn't check whose turn
    turn_tracker.active_player says it is before accepting a click (nothing
    in this hotseat game does), so this works without any special-casing.

    Actually making the ingress move needs an (x, y) drop point that only a
    drag gesture can supply, so the decision's effect doesn't finish the
    move itself - it just spends the CP and records `pending_squad`.
    main.py's Reserves panel (normally shown/draggable only during the
    Movement phase) stays visible while a squad is pending, but is
    restricted to showing ONLY that squad - otherwise the open drag window
    would let either player sneak in an ordinary Ingress move for some
    unrelated reserves unit outside the Movement phase, which
    IngressController.can_ingress() doesn't itself guard against (it only
    checks battle round, never phase). The window is bounded to a single
    phase: expire_if_unused(), called at the top of every phase transition,
    forfeits `pending_squad` if it's still sitting there unplaced - the CP
    stays spent regardless (same sunk-cost convention as every other
    stratagem here), matching "resolved right then" rather than leaving an
    indefinitely-open drag target lying around.

    Known limitation, not new to this stratagem: the AI (ai/agent_driver.py)
    treats any pending decision as a blocking condition and never resolves
    one itself (see _is_blocked()) - exactly like the dormant [LETHAL
    HITS]/[PRECISION]/[TWIN-LINKED] decision points no datasheet has
    exercised yet. If Player 1 (human) ends their Movement phase, Player 2
    (AI) is offered Rapid Ingress, and the human has to click through it on
    the AI's behalf, same as they would for any other pending decision."""

    def __init__(self, stratagem_controller, game_state, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self.pending_squad = None
        # Homing Beacon (user-supplied wargear item, game/homing_beacon.py):
        # the bearer Squad, only set when the pending ingress was picked as
        # this stratagem's free (0CP) use - None for a normal, CP-paying one.
        self.pending_homing_beacon_bearer = None
        self._next_bearer = None  # staged between _choose() and _resolve(), see _choose()'s docstring
        # Set by consume() when the placement it just started is STILL in
        # progress (a human's reserves-panel drop, see consume()'s own
        # docstring) - the squad whose actual Set Up conclusion (confirm or
        # cancel) notify_placement_resolved() is waiting to hear about.
        self._awaiting_resolution_for = None
        # Real bug, found via user report: picking a squad used to chain
        # straight into on_resolved() (offering Fire Overwatch) immediately,
        # before the squad was ever actually placed - see offer()'s
        # docstring. Deferred here instead, fired once from consume() or
        # expire_if_unused(), whichever actually closes this window.
        self._pending_on_resolved = None
        self._stratagem = Stratagem(
            name="Rapid Ingress", cp_cost=RAPID_INGRESS_CP_COST, effect=self._resolve, when=self._when,
        )

    def _when(self, controller, player):
        return self.turn_tracker is None or self.turn_tracker.battle_round >= RAPID_INGRESS_MIN_BATTLE_ROUND

    def _eligible_squads(self, player):
        return [s for s in self.game_state.reserves if s.owner == player]

    def offer(self, mover, decision_manager, on_resolved=None, homing_beacon_controller=None):
        """Called right after `mover`'s Movement phase ends - offers
        `mover`'s opponent a chance to bring a reserves unit on early.
        No-op (and, if given, `on_resolved()` fires right away) if nothing
        qualifies (no reserves, not enough CP, battle round 1), so an empty
        offer never flashes a "Decline"-only prompt nor stalls a chained
        reactive-stratagem sequence - main.py chains Fire Overwatch
        (game/overwatch.py) after this one via `on_resolved`, since
        DecisionManager only ever holds one pending decision at a time and
        both react to the same end-of-Movement-phase instant. Declining is
        immediate (nothing left to wait for), but PICKING a squad defers
        `on_resolved()` until that squad is actually placed - see
        _pick()'s own comment for why.

        `homing_beacon_controller`, if given, adds a SECOND, free option per
        eligible reserves squad whenever the opponent still has an unused
        Homing Beacon bearer on the battlefield - both options use the exact
        same underlying Stratagem (same once-per-phase/once-per-target
        bookkeeping, rule 15.01), only the CP cost (and, once placed, the
        placement rule - see IngressController.homing_beacon_bearer)
        differs."""
        opponent = _other_player(mover)
        eligible = [
            squad for squad in self._eligible_squads(opponent)
            if self.stratagem_controller.can_use(opponent, self._stratagem, [squad])
        ]
        bearer = homing_beacon_controller.available_bearer(opponent) if homing_beacon_controller is not None else None
        homing_eligible = [
            squad for squad in self._eligible_squads(opponent)
            if self.stratagem_controller.can_use(opponent, self._stratagem, [squad], extra_cp=-RAPID_INGRESS_CP_COST)
        ] if bearer is not None else []
        if not eligible and not homing_eligible:
            if on_resolved is not None:
                on_resolved()
            return

        def _pick(squad, free_bearer):
            # Real bug, found via user report: calling on_resolved() here
            # (immediately on pick, same as _decline() below) used to offer
            # Fire Overwatch right away, on top of a Rapid Ingress squad
            # that hadn't been placed yet - for a human, this steals the
            # decision-overlay modal away from the Reserves-panel drag they
            # still needed to make (DecisionManager takes input priority
            # over everything else, see main.py's event loop), so the
            # placement was never reachable until Fire Overwatch got
            # resolved first; for the AI, _maybe_resolve_decision() (which
            # runs BEFORE _maybe_resolve_rapid_ingress_placement() in
            # ai/agent_driver.py's take_one_action()) would keep resolving
            # that new decision ahead of ever placing the squad too. Deferred
            # instead - fired once from consume() (squad actually dropped
            # onto the board) or expire_if_unused() (window closes without
            # ever placing it), whichever happens first.
            self._pending_on_resolved = on_resolved
            self._choose(opponent, squad, bearer=free_bearer)
            if free_bearer is not None and homing_beacon_controller is not None:
                homing_beacon_controller.mark_used(free_bearer)

        def _decline():
            if on_resolved is not None:
                on_resolved()

        # NOT tagged for a board pick (game/unit_pick.py). Both reasons that
        # module refuses apply here, and neither is fixable from this end: a
        # unit in Strategic Reserves has no token to click, and a unit with a
        # Homing Beacon is listed TWICE (1 CP and free), which a click cannot
        # tell apart. The list overlay is the answerable form of this prompt.
        options = [
            (f"Rapid Ingress: {squad.name} (1 CP)", lambda squad=squad: _pick(squad, None))
            for squad in eligible
        ]
        options += [
            (f"Rapid Ingress: {squad.name} (Free - Homing Beacon)", lambda squad=squad: _pick(squad, bearer))
            for squad in homing_eligible
        ]
        options.append(("Decline", _decline))
        decision_manager.request(
            opponent, "Rapid Ingress - bring a unit in from strategic reserves now?", options,
            is_stratagem=True,
        )

    def _choose(self, player, squad, bearer=None):
        """`bearer` (a Squad, or None) is staged here rather than passed
        straight through, since Stratagem.effect (_resolve, called from
        inside stratagem_controller.use() below) only receives
        (controller, player, targets) - the same shape every other
        stratagem's effect callback uses."""
        self._next_bearer = bearer
        extra_cp = -RAPID_INGRESS_CP_COST if bearer is not None else 0
        self.stratagem_controller.use(player, self._stratagem, [squad], extra_cp=extra_cp)

    def _resolve(self, controller, player, targets):
        self.pending_squad = targets[0]
        self.pending_homing_beacon_bearer = self._next_bearer
        self._next_bearer = None
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: Rapid Ingress - {self.pending_squad.name} may make an ingress move now (rule 20.04)."
            )

    def expire_if_unused(self):
        """Safety net, called at the top of every phase transition: if the
        squad picked by the last offer() was never actually dragged onto
        the board, this window has closed - the CP stays spent. Also the
        second (of two) places that can fire a deferred on_resolved() (see
        _pick()) - whichever of this or consume() happens first."""
        if self.pending_squad is not None:
            if self.game_log is not None:
                self.game_log.add(
                    f"{self.pending_squad.owner}: the Rapid Ingress window for {self.pending_squad.name} has closed."
                )
            self.pending_squad = None
            self.pending_homing_beacon_bearer = None
        callback, self._pending_on_resolved = self._pending_on_resolved, None
        if callback is not None:
            callback()

    def consume(self, squad, setup_controller=None):
        """Called once `squad` (== pending_squad) is actually dropped onto
        the board - whether or not IngressController accepts that
        particular drop, this one window's CP/once-per-phase usage is spent
        right then, regardless.

        Real, severe bug found via user report: "ich konnte nur einen
        crisis aus meinen reserven platzieren. der rest ging nicht. der
        squad hat nicht mehr reagiert. ich musste den rapid ingress move
        abbrechen." This method used to fire the on_resolved() callback
        deferred by _pick() (chaining into Fire Overwatch's own board-click
        "choose a unit" screen, see main.py's advance_turn_phase()) right
        HERE, unconditionally - for a human dragging the Reserves-panel
        card themselves, main.py calls this the INSTANT the card lands
        (IngressController.start_ingress() has only just stacked the
        unit's models and put SetupController into PLACING - the human
        hasn't dragged them apart or clicked Confirm/Cancel at all yet).
        Since main.py's event loop checks
        fire_overwatch_controller.state == CHOOSING_UNIT BEFORE it ever
        reaches the generic board-click dispatch InputManager's placement-
        drag logic depends on (see that branch's own comment), an eligible
        Fire Overwatch offer - opened synchronously by this very call -
        hijacked every subsequent mouse event: the still-stacked models had
        no way to be dragged apart at all until Fire Overwatch was itself
        resolved (pick a unit, or Decline), which nothing on screen
        signaled was even happening. Reproduced: with the opponent having
        an eligible Snap Shooting target, dropping the reserves card left
        the newly-arrived unit's other models completely unresponsive to
        clicks, exactly as reported.

        `setup_controller`, given only by the human drop path in main.py,
        tells this call apart from ai/agent_driver.py's own auto-ingress
        path (_maybe_resolve_rapid_ingress_placement(), which calls this
        only AFTER _auto_ingress_squad()'s whole - possibly multi-attempt -
        retry loop has already finished placing or giving up on the squad,
        with no setup_controller argument at all): if setup_controller
        confirms THIS squad's placement is still actively in progress right
        now, defer firing the callback (see notify_placement_resolved(),
        wired via IngressController.on_ingress_resolved) until the human
        actually finishes it - confirm or cancel, either way. Otherwise
        (no setup_controller given, or this squad's placement has already
        concluded/failed to even start), there's nothing left to wait for,
        so fire immediately, exactly as before."""
        if squad is self.pending_squad:
            self.pending_squad = None
            self.pending_homing_beacon_bearer = None
        if setup_controller is not None and setup_controller.setting_up_squad is squad:
            self._awaiting_resolution_for = squad
            return
        callback, self._pending_on_resolved = self._pending_on_resolved, None
        if callback is not None:
            callback()

    def notify_placement_resolved(self, squad):
        """Wired to IngressController.on_ingress_resolved - fires the
        callback consume() deferred (see its own docstring), but only once
        THIS squad's Set Up workflow has actually concluded (confirmed or
        cancelled), never for some unrelated squad's placement finishing in
        the meantime."""
        if squad is not self._awaiting_resolution_for:
            return
        self._awaiting_resolution_for = None
        callback, self._pending_on_resolved = self._pending_on_resolved, None
        if callback is not None:
            callback()


def _other_player(player):
    return "Player 2" if player == "Player 1" else "Player 1"
