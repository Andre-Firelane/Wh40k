"""Trukk's Pilin' Out (2026-09 Ork codex, stage E3d).

RULE (verbatim, rules/orks/Trukk.md):
  "Pilin' Out: In your opponent's Movement phase, when an enemy unit ends a move
   within 8" of this model, units embarked within this model can make a
   disembark move using the rapid disembark mode."

A REACTIVE DISEMBARK, and a disembark in this engine is a SET-UP PLACEMENT, not a
MovementController move. That decides every seam:

  - the move is TransportController.start_disembark(squad, mode=RAPID) - the mode
    is PRINTED, so determine_mode()'s "what did the TRANSPORT do this phase" is
    not asked;
  - it is waited on the way every placement is: SetupController's PLACING state
    stands in main.py's phase gate, and ai/agent_driver.py's _is_blocked() holds
    the AI while a placement that is not its own is open. So there is no
    move_mode to list in MovementController.REACTIVE_MOVE_MODES, and no is_busy
    term: a gate term that can never be the one that holds is a dead branch;
  - the AI's own passengers are set up by _maybe_resume_disembark_placement(),
    which already places a Disembark Move of the AI's "in any phase, whoever's
    turn it is" (it was built for the Emergency Disembark).

"WHEN AN ENEMY UNIT ENDS A MOVE" - three triggers, one per kind of move the
Movement phase has: MovementController.on_move_finished (Normal, Advance, Fall
Back), IngressController.on_ingress_resolved (an arrival - read as ended only if
the unit is on the board afterwards, since a cancel fires the same hook) and
TransportController.on_disembark_resolved (a confirmed Disembark Move). The phase
and the owner are checked here: "your OPPONENT'S Movement phase" means the mover
owns the turn and the Trukk does not.

"WITHIN 8" OF THIS MODEL" is edge to edge from any living model of the mover.

ONE PASSENGER AT A TIME. A Trukk can hold more than one unit, and two Trukks can be
in range of the same move. SetupController is single-slot, so the passengers wait
in a queue and the next is asked only once the open disembark is RESOLVED -
TransportController.on_disembark_resolved, fired synchronously from confirm and
cancel. A prompt raised while a placement was open would sit on top of it and,
answered yes, find the slot taken.

ASKED ONCE PER PHASE. A human who answers "Stay put" for a unit is not asked again
for it in the same Movement phase, however many more enemy moves end in range: the
AI moves its units one by one, and a question per move is noise rather than a
choice. The memo is cleared with the transport's own phase bookkeeping in main.py.
A cancelled placement counts as a decline for the same reason.

"CAN" - an option for a human, a policy for the AI: main.py injects
ai/agent_driver.py's pilin_out_verdict() as `choose` (0 API calls), because game/
must not import ai/.

NAMED DEVIATIONS: the engine's Rapid Disembark makes no hazard roll (pre-existing,
every Rapid Disembark shares it), and a disembarked unit's "not eligible to
declare a charge" lock ends with THIS turn, which is the opponent's - the
end-of-turn sweep in main.py clears it for every unit, so the Boyz charge in their
own turn.
"""

from game import ai_mode
from game.squad import edge_distance
from game.transport import RAPID
from game.turn import PHASE_MOVEMENT

PILIN_OUT_NAME = "Pilin' Out"
PILIN_OUT_RANGE_IN = 8.0
DISEMBARK_LABEL = "Disembark (rapid disembark)"
STAY_LABEL = "Stay put"


def has_ability(transport_token):
    profile = getattr(transport_token, "profile", None)
    return bool(getattr(profile, "pilin_out", False))


class PilinOutController:
    def __init__(self, transport_controller, game_state=None, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=(), choose=None):
        self.transport_controller = transport_controller
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: The AI's policy: choose(transport_token, passenger, mover) -> bool.
        self.choose = choose
        self._queue = []        # [(transport_token, passenger, mover), ...]
        self._current = None    # the passenger whose disembark is open
        self._asking = None     # the passenger whose prompt is open
        self._declined = set()  # id(passenger) - asked and refused this Movement phase

    # ------------------------------------------------------------------ state
    def reset_movement_phase(self):
        self._declined = set()

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return getattr(self.game_state, "tokens", None) or []

    # ------------------------------------------------------------ eligibility
    def transports_in_range(self, mover):
        tokens = self._tokens()
        living = [m for m in mover.models if not m.is_dead() and m in tokens]
        if not living:
            return []
        found = []
        for token in tokens:
            squad = getattr(token, "squad", None)
            if squad is None or squad.owner == mover.owner or token.is_dead():
                continue
            if not has_ability(token):
                continue
            if any(edge_distance(token, m) <= PILIN_OUT_RANGE_IN for m in living):
                found.append(token)
        return sorted(found, key=lambda t: (t.squad.name, t.id))

    def can_offer(self, transport_token, passenger):
        if passenger is None or id(passenger) in self._declined:
            return False
        if getattr(passenger, "embarked_in", None) is not transport_token:
            return False
        if transport_token not in self._tokens() or transport_token.is_dead():
            return False
        if not any(not m.is_dead() for m in passenger.models):
            return False
        return self.transport_controller.can_disembark(passenger)

    # ---------------------------------------------------------------- triggers
    def on_move_finished(self, mover, kind=None):
        """MovementController.on_move_finished listener (squad, kind)."""
        return self.notify_move_ended(mover)

    def on_ingress_resolved(self, squad):
        """IngressController.on_ingress_resolved listener - fired on confirm AND
        on cancel, so only a unit that is on the board afterwards ended a move.
        That reading needs no gate of its own: transports_in_range() measures
        from the mover's living models ON THE BOARD, and a cancelled arrival has
        none (an A/B probe found a second copy of the test here unable to hold)."""
        return self.notify_move_ended(squad)

    def on_disembark_resolved(self, squad, confirmed):
        """TransportController.on_disembark_resolved listener. Either the open
        Pilin' Out disembark has resolved - ask the next passenger - or an enemy
        unit has just ended its own Disembark Move."""
        if squad is not None and squad is self._current:
            self._current = None
            if not confirmed:
                self._declined.add(id(squad))
            self._advance()
            return True
        if confirmed:
            return self.notify_move_ended(squad)
        return False

    def notify_move_ended(self, mover):
        tt = self.turn_tracker
        if mover is None or self.game_state is None or tt is None:
            return False
        if tt.phase != PHASE_MOVEMENT or tt.turn_owner != mover.owner:
            return False
        queued = {id(p) for _t, p, _m in self._queue}
        added = False
        for transport_token in self.transports_in_range(mover):
            for passenger in sorted(self.transport_controller.embarked_squads_in(transport_token),
                                    key=lambda s: s.name):
                if id(passenger) in queued or passenger is self._current or passenger is self._asking:
                    continue
                if not self.can_offer(transport_token, passenger):
                    continue
                self._queue.append((transport_token, passenger, mover))
                queued.add(id(passenger))
                added = True
        if added:
            self._advance()
        return added

    # ------------------------------------------------------------------- queue
    def _advance(self):
        while self._current is None and self._asking is None and self._queue:
            transport_token, passenger, mover = self._queue.pop(0)
            if not self.can_offer(transport_token, passenger):
                continue
            if passenger.owner in self.auto_players:
                wants = bool(self.choose(transport_token, passenger, mover)) if self.choose is not None else False
                if not wants or not self._start(transport_token, passenger, mover):
                    self._declined.add(id(passenger))
                continue
            if self.decision_manager is None:
                continue
            self._asking = passenger
            self.decision_manager.request(
                passenger.owner,
                "%s: %s ended a move within %g\" of %s - disembark %s (rapid disembark)?"
                % (PILIN_OUT_NAME, mover.name, PILIN_OUT_RANGE_IN, transport_token.squad.name,
                   passenger.name),
                [(DISEMBARK_LABEL, lambda t=transport_token, p=passenger, m=mover: self._answer(t, p, m, True)),
                 (STAY_LABEL, lambda t=transport_token, p=passenger, m=mover: self._answer(t, p, m, False))])

    def _answer(self, transport_token, passenger, mover, yes):
        self._asking = None
        if not yes or not self._start(transport_token, passenger, mover):
            self._declined.add(id(passenger))
        self._advance()

    def _start(self, transport_token, passenger, mover):
        if not self.can_offer(transport_token, passenger):
            return False
        self.transport_controller.start_disembark(passenger, mode=RAPID)
        if not self.transport_controller.is_disembarking(passenger):
            return False
        self._current = passenger
        self._log("%s: %s - %s disembarks from %s (rapid disembark) after %s ended a move within %g\"."
                  % (passenger.owner, PILIN_OUT_NAME, passenger.name, transport_token.squad.name,
                     mover.name, PILIN_OUT_RANGE_IN))
        return True
