"""Spirit Conclave Enhancement: Higher Duty (25 pts).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  "SPIRITSEER model only. In your opponent's Movement phase, if an enemy unit
  ends a move within 8" of this unit, if this unit is not within Engagement
  Range of one or more enemy units, this unit can make a Normal move of up to
  6"."

IT CLOSES THE TRAIL FINDING GAP. CLAUDE.md records the Kroot Trail Shaper's
Trail Finding as unbuilt with a precise diagnosis: "it is not the MOVE that is
missing, it is the TRIGGER - an enemy has just ENDED a move". That trigger now
exists as MovementController.on_move_finished, a LIST, and this is its first
enemy-side consumer.

A REACTIVE MOVE, WITH EVERY PIECE THAT ENTAILS. CLAUDE.md records this exact
failure being reported THREE times, so all four parts are here rather than
discovered later:

  1. move_mode listed in MovementController.REACTIVE_MOVE_MODES - without it
     the AI walks straight over the move it was just offered;
  2. the ACTIVE_PLAYER hand-off: select() would refuse this unit in the
     opponent's turn, so the reacting player holds active_player until the
     move is confirmed or cancelled, and it is handed back either way;
  3. its own move_mode, which is what routes the Confirm button back to THIS
     controller rather than to the generic one;
  4. a confirm/cancel pair that restores the turn.

Modelled on game/windrider_overflight.py, which is the same shape one clause
poorer - it costs CP and is triggered by a kill rather than by a move.

THREE CONDITIONS, AND THE MIDDLE ONE IS ABOUT THE BEARER'S OWN UNIT: the enemy
must END a move (not merely pass through) within 8", and the reacting unit must
NOT itself be in Engagement Range of anything. A unit already in combat cannot
use this to walk away - that is what Fall Back is for, and reading the clause
off the enemy instead of off the reactor would allow exactly that.

"IN YOUR OPPONENT'S MOVEMENT PHASE" is not re-checked here: on_move_finished
fires from a move, and the only moves that reach it belong to whoever is
moving. The reactor is by construction not that player, which the owner
comparison already establishes.
"""
from game import enhancements
from game.squad import edge_distance

HIGHER_DUTY = "Higher Duty"

HIGHER_DUTY_LABEL = "Higher Duty"

#: "if an enemy unit ends a move within 8" of this unit".
HIGHER_DUTY_TRIGGER_RANGE_IN = 8.0

#: "a Normal move of up to 6"".
HIGHER_DUTY_MOVE_IN = 6.0

#: Its own mode, so the Confirm button routes back here - and it MUST also be
#: listed in MovementController.REACTIVE_MOVE_MODES.
HIGHER_DUTY_MOVE_MODE = "higher_duty"


def has_bearer(squad):
    return enhancements.is_active(squad, HIGHER_DUTY)


class HigherDutyController:
    """The reactive Normal move, hung on MovementController.on_move_finished."""

    def __init__(self, game_state=None, movement_controller=None,
                 decision_manager=None, turn_tracker=None, game_log=None,
                 auto_players=(), all_tokens=None):
        self.game_state = game_state
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self.all_tokens = all_tokens
        self._moving_squad = None
        self._restore_active = None

    def _squads(self):
        seen, out = set(), []
        for token in getattr(self.game_state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def _tokens(self):
        if self.all_tokens is not None:
            return self.all_tokens
        return getattr(self.game_state, "tokens", ()) or ()

    def _within(self, squad, other, range_in):
        for a in getattr(squad, "models", ()) or ():
            if a.is_dead():
                continue
            for b in getattr(other, "models", ()) or ():
                if b.is_dead():
                    continue
                if edge_distance(a, b) <= range_in:
                    return True
        return False

    def can_react(self, squad, mover):
        """All three printed conditions."""
        if squad is None or mover is None or squad.owner == mover.owner:
            return False
        if not has_bearer(squad):
            return False
        # "if an enemy unit ENDS A MOVE within 8" of this unit"
        if not self._within(squad, mover, HIGHER_DUTY_TRIGGER_RANGE_IN):
            return False
        # "if THIS UNIT is not within Engagement Range of one or more enemy
        # units" - about the reactor, not the mover. Read off the enemy it
        # would let a unit already in combat walk out of it.
        return not squad.is_engaged(self._tokens())

    def reactors_for(self, mover):
        return sorted((s for s in self._squads() if self.can_react(s, mover)),
                      key=lambda s: (str(s.owner), s.name))

    # --- the trigger ------------------------------------------------------

    def on_move_finished(self, mover):
        """"if an enemy unit ends a move within 8"" - the first enemy-side
        consumer of this hook."""
        for squad in self.reactors_for(mover):
            if squad.owner in self.auto_players or self.decision_manager is None:
                return False           # no AI path (standing Aeldari rule)
            self.decision_manager.request(
                squad.owner,
                '%s: %s ended a move within %g" of %s - make a Normal move of '
                'up to %g"?'
                % (HIGHER_DUTY_LABEL, mover.name, HIGHER_DUTY_TRIGGER_RANGE_IN,
                   squad.name, HIGHER_DUTY_MOVE_IN),
                [("Move", (lambda s=squad: self._move(s))),
                 ("Stay put", lambda: None)],
            )
            return True
        return False

    def _move(self, squad):
        if self.movement_controller is None:
            return False
        # select() refuses this unit in the opponent's turn, so the reacting
        # player holds active_player until the move is confirmed or cancelled.
        if self.turn_tracker is not None:
            self._restore_active = self.turn_tracker.active_player
            self.turn_tracker.set_active(squad.owner)
        self.movement_controller.select(squad.models[0])
        if self.movement_controller.selected_squad is not squad:
            self._finish()
            return False
        self.movement_controller.start_battle_focus_move(
            squad, HIGHER_DUTY_MOVE_IN, move_mode=HIGHER_DUTY_MOVE_MODE)
        self._moving_squad = squad
        if self.game_log is not None:
            self.game_log.add('%s: %s makes a Normal move of up to %g".'
                              % (HIGHER_DUTY_LABEL, squad.name, HIGHER_DUTY_MOVE_IN))
        return True

    @property
    def is_busy(self):
        return self._moving_squad is not None

    def confirm_move(self):
        if self.movement_controller is None or self._moving_squad is None:
            return
        self.movement_controller.confirm_move()
        if not self.movement_controller.errors:
            self._finish()

    def cancel_move(self):
        if self.movement_controller is not None:
            self.movement_controller.cancel_move()
        self._finish()

    def _finish(self):
        self._moving_squad = None
        if self.turn_tracker is not None and self._restore_active is not None:
            self.turn_tracker.set_active(self._restore_active)
        self._restore_active = None
