"""Canoptek Court Stratagem: Reactive Subroutines (1CP).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  WHEN:   Your opponent's Movement phase, just after an enemy unit ends a Normal,
          Advance or Fall Back move.
  TARGET: One CANOPTEK unit from your army that is within 8" of that enemy unit.
  EFFECT: Your unit can make a Normal move of up to 6".

A REACTIVE MOVE, WITH EVERY PIECE THAT ENTAILS - the four this repo has been
reported for three times (see game/enh_higher_duty.py, whose trigger and shape
this shares one Stratagem cost richer):

  1. its move_mode is listed in MovementController.REACTIVE_MOVE_MODES (and so in
     OUT_OF_PHASE_MOVE_MODES) - otherwise the AI walks over the move;
  2. the ACTIVE_PLAYER hand-off: select() refuses this unit in the opponent's
     turn, so the reacting player holds active_player until the move is confirmed
     or cancelled, and it is handed back either way;
  3. its own move_mode, which routes the panel's Confirm/Cancel back here;
  4. is_busy in main.py's phase gate while the move is open.

THE TRIGGER is MovementController.on_move_finished, which fires only for "a Normal,
Advance or Fall Back move" (NORMAL_ADVANCE_FALL_BACK_MODES) - the printed list. The
phase and owner are checked here: "your OPPONENT'S Movement phase" means the mover
owns the turn and the reactor does not.

A UNIT IN ENGAGEMENT RANGE IS NOT A CANDIDATE, although the TARGET line does not
say so: a Normal move cannot be started by an engaged unit (09.02/09.07), so the
Stratagem would buy nothing - never offer what buys nothing.

ONE PROMPT, ONE TAGGED OPTION PER CANDIDATE ("One CANOPTEK unit from your army" is
the player's choice - game/unit_choice_offer.py), and the CP is spent when a unit
is picked.

THE AI MOVES AT ONCE. When the reactor is an `auto_players` owner the whole
Stratagem resolves inside the listener: an injected policy names a destination (or
declines) and an injected mover drives the move through the ordinary sweep. Both
are handed in by main.py, because game/ must not import ai/.
"""

from game import ai_mode, necron_detachments
from game.squad import edge_distance
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

REACTIVE_SUBROUTINES_NAME = "Reactive Subroutines"
REACTIVE_SUBROUTINES_CP = 1
REACTIVE_SUBROUTINES_TRIGGER_RANGE_IN = 8.0
REACTIVE_SUBROUTINES_MOVE_IN = 6.0
#: Its own mode, so Confirm routes back here - and it MUST be listed in
#: MovementController.REACTIVE_MOVE_MODES.
REACTIVE_SUBROUTINES_MOVE_MODE = "court_reactive_subroutines"
SETTING = "CANOPTEK_COURT_PLAYERS"
QUALIFYING_KINDS = ("normal", "advance", "fall_back")


class ReactiveSubroutinesController:
    def __init__(self, stratagem_controller, movement_controller=None, turn_tracker=None,
                 game_state=None, decision_manager=None, game_log=None, auto_players=(),
                 ai_destination=None, ai_mover=None):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # ai_destination(squad, mover) -> (x, y) or None; ai_mover(squad, point) -> bool
        self.ai_destination = ai_destination
        self.ai_mover = ai_mover
        self._moving_squad = None
        self._restore_active = None
        self._stratagem = Stratagem(name=REACTIVE_SUBROUTINES_NAME,
                                    cp_cost=REACTIVE_SUBROUTINES_CP, effect=self._effect)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _squads(self):
        seen, out = set(), []
        for token in getattr(self.game_state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def _tokens(self):
        return list(getattr(self.game_state, "tokens", ()) or ())

    @property
    def is_busy(self):
        return self._moving_squad is not None

    # ------------------------------------------------------------ eligibility
    def _within(self, squad, other, range_in):
        return any(edge_distance(a, b) <= range_in
                   for a in squad.models if not a.is_dead()
                   for b in other.models if not b.is_dead())

    def can_react(self, squad, mover):
        if squad is None or mover is None or squad.owner == mover.owner:
            return False
        if not necron_detachments.has_detachment(squad.owner, SETTING):
            return False
        if not necron_detachments.is_canoptek_unit(squad):
            return False
        if getattr(squad, "embarked_in", None) is not None:
            return False
        if not any(not m.is_dead() for m in squad.models):
            return False
        if not self._within(squad, mover, REACTIVE_SUBROUTINES_TRIGGER_RANGE_IN):
            return False
        if squad.is_engaged(self._tokens()):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def candidates_for(self, mover):
        return sorted((s for s in self._squads() if self.can_react(s, mover)),
                      key=lambda s: s.name)

    # --------------------------------------------------------------- trigger
    def on_move_finished(self, mover, kind=None):
        """MovementController.on_move_finished listener (squad, kind)."""
        if mover is None or self.is_busy:
            return False
        if kind is not None and kind not in QUALIFYING_KINDS:
            return False
        tt = self.turn_tracker
        if tt is not None and (tt.phase != PHASE_MOVEMENT or tt.turn_owner != mover.owner):
            return False
        candidates = self.candidates_for(mover)
        if not candidates:
            return False
        player = candidates[0].owner
        if player in self.auto_players:
            return self._ai_react(candidates, mover)
        from game import unit_choice_offer
        return unit_choice_offer.offer_one_of(
            self.decision_manager, player, candidates,
            f"{REACTIVE_SUBROUTINES_NAME} ({REACTIVE_SUBROUTINES_CP} CP): {mover.name} ended a move "
            f"within {REACTIVE_SUBROUTINES_TRIGGER_RANGE_IN:g}\" - which CANOPTEK unit makes a Normal "
            f"move of up to {REACTIVE_SUBROUTINES_MOVE_IN:g}\"?",
            self.buy_and_move,
            auto_players=self.auto_players, is_stratagem=True,
        )

    def _ai_react(self, candidates, mover):
        if self.ai_destination is None or self.ai_mover is None:
            return False
        for squad in candidates:
            point = self.ai_destination(squad, mover)
            if point is None:
                continue
            if not self.buy_and_move(squad):
                return False
            try:
                moved = bool(self.ai_mover(squad, point))
            finally:
                if self.movement_controller is not None and self._moving_squad is not None \
                        and getattr(self.movement_controller, "move_mode", None) == REACTIVE_SUBROUTINES_MOVE_MODE:
                    self.movement_controller.cancel_move()
                self._finish()
                if self.movement_controller is not None:
                    self.movement_controller.select(None)
            self._log(f"[reactive subroutines] {squad.name} -> ({point[0]:.1f},{point[1]:.1f}): "
                      f"{'moved' if moved else 'could not move'}.", file_only=True)
            return True
        return False

    # ------------------------------------------------------------------ move
    def buy_and_move(self, squad):
        if not self.can_react_now(squad):
            return False
        if not self.stratagem_controller.use(squad.owner, self._stratagem, [squad]):
            return False
        return self._move(squad)

    def can_react_now(self, squad):
        return (squad is not None and self.movement_controller is not None
                and self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad]))

    def _effect(self, controller, player, targets):
        for squad in targets or ():
            self._log(f"{REACTIVE_SUBROUTINES_NAME}: {squad.name} can make a Normal move of up "
                      f"to {REACTIVE_SUBROUTINES_MOVE_IN:g}\".")

    def _move(self, squad):
        mc = self.movement_controller
        if mc is None:
            return False
        if self.turn_tracker is not None:
            self._restore_active = self.turn_tracker.active_player
            self.turn_tracker.set_active(squad.owner)
        mc.select(squad.models[0])
        if mc.selected_squad is not squad:
            self._finish()
            return False
        mc.start_battle_focus_move(squad, REACTIVE_SUBROUTINES_MOVE_IN,
                                   move_mode=REACTIVE_SUBROUTINES_MOVE_MODE)
        self._moving_squad = squad
        return True

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
