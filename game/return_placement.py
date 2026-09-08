"""Where a returning model stands - the player's answer, or the engine's.

Rule 01.02.03: a model put back on the battlefield is SET UP, and setting up
is something the controlling player does. Eight abilities in this engine return
models, and until now all eight picked the spot themselves for BOTH sides:

    reanimation_protocols  grot_orderly       curse_of_the_walking_pox
    protocol_eternal_revenant                 word_of_the_phoenix
    unquenchable_resolve   enh_phoenix_gem    spiritseer (Tears of Isha)

The engine's pick was never wrong - formation_layout.returning_positions()
seats a model touching the survivors so rule 09.02 holds by construction, and
ring_candidates() walks outwards from where a model fell for the ones whose
text says "as close as possible". What was wrong is that it was the only
answer available, so a human playing Necrons watched their Warriors reappear
wherever the first legal ring slot happened to be (user: "muss er die
stratagems, Faehigkeiten und Platzierung der Modelle manuell ganz normal
steuern koennen").

WHAT THIS MODULE IS, AND MOSTLY IS NOT. It is a fork, not a placement engine.
The spots still come from formation_layout; the dragging, the green/red
overlay, the clamping and Confirm/Cancel are all SetupController's, which
already does exactly this for Ingress (20.04) and Disembark (18.x). The only
new thing underneath is that SetupController can now place a SUBSET of a unit -
a return puts one or two models back into a unit that is already standing, and
the survivors must not move.

WHY IT REUSES THAT FLOW RATHER THAN GROWING ITS OWN. A new pending state that
main() blocks on has to be clickable AND drawn or it is a hard deadlock -
CLAUDE.md's Fehlerklasse 25, which cost this repo a game-stopping bug against
Death Guard. `setup_controller.state == PLACING` is already in
_has_unresolved_declaration(), already routed by the input handler, already
painted by the overlay and already has Confirm/Cancel in the action panel. A
second family would have had to earn all five of those; this inherits them.

THE AI IS UNCHANGED, deliberately and provably: for an owner in `auto_players`
the models land on exactly the spots the ability computed, in the same frame,
and nothing is opened. That is what keeps every AI measurement in this repo
comparable, and what keeps the AI free of API calls - a prompt it cannot answer
falls through to the model.
"""

from game import ai_mode, model_return


class ReturnPlacementController:
    """One fork, shared by every ability that puts a model back.

    `place()` is the whole interface: hand it the unit, the models coming back,
    the spots the ability computed, and what to do when it is done."""

    def __init__(self, setup_controller=None, game_state=None, game_log=None,
                 auto_players=()):
        self.setup_controller = setup_controller
        self.game_state = game_state
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._pending = None      # (squad, [models], on_done) while a human places
        # Placements that arrived while one of OURS was still open. A
        # human whose second unit reanimates in the same Command phase
        # used to have its models seated by the engine, silently: see
        # place()'s third branch.
        self._waiting = []        # [(squad, [models], on_done)]

    @property
    def is_busy(self):
        """INVARIANT: a queued placement always has an open one in front of it.

        place() only appends to _waiting while _pending is set, and
        _start_next() either opens the next one (setting _pending again) or
        empties the list - so `_waiting` can never be non-empty on its own.
        An `or bool(self._waiting)` here would be a branch no input reaches,
        which is how a dead term ends up being believed load-bearing; its own
        A/B probe reported NO BITE and that is how this was found.
        """
        return self._pending is not None

    @property
    def pending_squad(self):
        return self._pending[0] if self._pending else None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    # ------------------------------------------------------------------ place

    def place(self, squad, models, spots, wounds=None, validator=None, on_done=None):
        """Put `models` back into `squad`, one spot each.

        `spots` is what the ability worked out - the same list it used to apply
        outright - and a None entry means that model found nowhere legal, which
        every one of the eight already honours as "it stays down". They are
        dropped here rather than offered, so a human is never asked to place a
        model the rule did not return.

        `wounds` is passed through to model_return.set_up_model(): most
        abilities return a model at full wounds, Reanimation Protocols at one,
        the Eternal Revenant at half.

        Returns the models that came back. For a human that is the same list -
        they are ON the board while being positioned, exactly as a Set Up
        works - and the placement is still open until Confirm."""
        pairs = [(m, s) for m, s in zip(models, spots) if s is not None]
        if not pairs:
            return []

        returned = []
        for index, (model, spot) in enumerate(pairs):
            give = wounds[index] if isinstance(wounds, (list, tuple)) else wounds
            model_return.set_up_model(model, spot, wounds=give,
                                      game_state=self.game_state)
            returned.append(model)

        if squad.owner in self.auto_players or self.setup_controller is None:
            # The AI's answer, and the answer whenever there is no placement
            # flow to open - byte for byte what every one of these abilities
            # did before, in the same frame. THE AI PATH DOES NOT MOVE: this
            # disjunct stays first and untouched, which is the promise this
            # module's docstring makes.
            if on_done is not None:
                on_done(returned)
            return returned

        if not self.setup_controller.can_start_setup(squad):
            # can_start_setup() is "state == IDLE", so this branch means
            # SOMEBODY is already placing. It used to be folded into the line
            # above, which made it a silent human -> engine fallback: measured
            # with two damaged human Necron units reanimating in one Command
            # phase, the placement opened for the FIRST one twice and the
            # second unit's models were seated by the engine with no prompt and
            # no distinguishing log line.
            if self._pending is not None:
                # Ours. Queue it - confirm()/_on_cancel() start the next.
                self._waiting.append((squad, list(returned),
                                      [spot for _m, spot in pairs], validator, on_done))
                self._log("%s: %d returning model(s) queued behind %s's placement."
                          % (squad.name, len(returned), self._pending[0].name),
                          file_only=True)
                return returned
            # Somebody ELSE is placing (an arrival, a disembark). Queuing here
            # would be a deadlock: nothing in this controller owns the resume
            # for a placement it did not open. So the engine still answers -
            # but it SAYS SO, which is the half that was missing.
            self._log("%s: %d returning model(s) placed by the engine - another "
                      "placement was already open." % (squad.name, len(returned)))
            if on_done is not None:
                on_done(returned)
            return returned

        self._open(squad, list(returned), [spot for _m, spot in pairs],
                   validator, on_done)
        return returned

    def _open(self, squad, models, positions, validator, on_done):
        """Hand ONE placement to the human. The single door, so a queued
        placement re-enters by exactly the same arguments the first one used
        rather than through a second copy of them."""
        self._pending = (squad, list(models), on_done)
        self.setup_controller.start_setup(
            squad, models[0].x_in, models[0].y_in,
            on_cancel=self._on_cancel,
            # Only the returning models move; the survivors are standing
            # somewhere legal already and this must not pick them up.
            models=list(models),
            # ...starting from the engine's own spots, so the human adjusts an
            # answer rather than dragging a pile apart.
            positions=list(positions),
            # Rule 01.02.03 lets a returning model be set up engaged when its
            # unit already is. `validator` is the ability's own per-position
            # predicate, which enforces the narrower half of that clause; the
            # waiver only stops confirm_setup() rejecting the whole squad for
            # a fight the survivors were already in.
            allow_engaged=True,
            placement_validator=validator,
            # Rule 18.02: the unit was NOT set up, it got a model back.
            mark_set_up=False,
        )
        self._log("%s: place the returning model(s), then Confirm." % squad.name,
                  file_only=True)

    def _start_next(self):
        """Open the next queued placement, if any. Called from BOTH exits -
        a cancelled placement owes the queue exactly what a confirmed one
        does."""
        while self._waiting:
            squad, models, positions, validator, on_done = self._waiting.pop(0)
            living = [m for m in models if m in squad.models]
            if not living:
                # Nothing left to place (the models went back down, or the unit
                # was wiped in between). Its on_done is still owed an answer.
                if on_done is not None:
                    on_done([])
                continue
            self._open(squad, living, positions[:len(living)], validator, on_done)
            return True
        return False

    # ------------------------------------------------------- resolving it

    def confirm(self):
        """The human is happy with where they stand."""
        if self._pending is None:
            return False
        squad, models, on_done = self._pending
        if self.setup_controller is not None:
            self.setup_controller.confirm_setup()
            if self.setup_controller.state != "idle" and self.setup_controller.errors:
                return False          # still illegal - the panel shows why
        self._pending = None
        if on_done is not None:
            on_done(models)
        self._start_next()
        return True

    def cancel(self):
        """Abandoned. The models go back down: a return that is not placed did
        not happen, which is how all eight abilities already read a model with
        nowhere legal to stand."""
        if self._pending is None:
            return False
        if self.setup_controller is not None:
            self.setup_controller.cancel_setup()
        return True

    def _on_cancel(self, squad):
        """SetupController's own way out. Undoes model_return.set_up_model()'s
        four halves for the models this placement was holding - they go back to
        destroyed, off the squad and off the board."""
        pending, self._pending = self._pending, None
        if pending is None:
            return
        _squad, models, on_done = pending
        for model in models:
            if model in squad.models:
                squad.models.remove(model)
            if model not in squad.destroyed_models:
                squad.destroyed_models.append(model)
            model.current_wounds = 0
            if self.game_state is not None and model in self.game_state.tokens:
                self.game_state.tokens.remove(model)
        self._log("%s: the returning model(s) were not placed - they stay down."
                  % squad.name)
        if on_done is not None:
            on_done([])
        self._start_next()
