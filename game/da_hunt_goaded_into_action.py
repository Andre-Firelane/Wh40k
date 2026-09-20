"""Da Big Hunt Stratagem: Goaded into Action (1CP, Mecha Orks stage G5).

RULE (verbatim, rules/orks/detachments/Da Big Hunt.md):
  WHEN:   Your opponent's Shooting phase, when an enemy unit has shot.
  TARGET: One friendly unengaged BEAST SNAGGA unit that lost a wound as a
          result of those attacks.
  EFFECT: Your unit can make a surge move of up to D6". If your unit is riled
          up, it can re-roll that D6.

THE FIRST SURGE MOVE IN THIS ENGINE. MovementController.start_surge_move()
(rule 21.02) was built as reusable machinery with no caller - "we have none
yet", said its docstring. This is it: the maximum distance comes from the D6,
and AFTER MOVING the unit may not be engaged with anything except its surge
target (Squad.check_surge_engagement(), the rule's own hard clause). The target
is the closest enemy unit, which is what rule 21.01/21.02 names.

"SURGE" IS A REACTIVE MOVE, made in the OPPONENT'S turn, so the mode is
registered in MovementController.REACTIVE_MOVE_MODES (and through it
OUT_OF_PHASE_MOVE_MODES): without that the AI walks over the move it was just
granted, and "Next Phase" orphans a paid-for move - both reported before.

THE SHAPE IS PATH OF THE OUTCAST'S: a D6 as a real, visible DiceNotationRoll,
then the reactive move opened on the same MovementController, with
active_player held by the reacting player until Confirm or Cancel.

"LOST A WOUND AS A RESULT OF THOSE ATTACKS" is asked of the ShootingController,
which records the wounds of every unit it HIT when it hits it and answers
squads_wounded_this_activation() at the end - the one activation-scoped ledger
beside _hit_target_squads_this_activation. A unit that was hit and saved
everything is not a target, which is the whole point of the clause.

"IF YOUR UNIT IS RILED UP, IT CAN RE-ROLL THAT D6" - riled up is
game/riled_up.py's one question; the re-roll is offered through the dice
panel's ordinary re-roll route (game/roll_choice.py) via this controller's
pending_roll_choice(), the same door Advance re-rolls use.

THE AI (injected destination/mover from ai/agent_driver.py, the arrangement
Canoptek Court's Reactive Subroutines uses) surges toward the enemy that just
shot it - a BEAST SNAGGA unit closing on what hurt it. 0 API calls.
"""

from game import ai_mode, da_big_hunt, riled_up
from game.dice_notation import D6, DiceNotationRoll
from game.engagement import is_engaged
from game.squad import closest_enemy_squad
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

GOADED_INTO_ACTION_NAME = "Goaded into Action"
GOADED_INTO_ACTION_CP = 1
#: The move_mode the reactive surge runs under - see MovementController.
GOADED_MOVE_MODE = "surge"
USE_LABEL = "Use Goaded into Action (1 CP)"
DECLINE_LABEL = "Stay put"


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


class GoadedIntoActionController:
    #: Set by main.py: the controller whose activation ledger answers "lost a
    #: wound as a result of those attacks".
    shooting_controller = None

    def __init__(self, stratagem_controller, movement_controller=None, turn_tracker=None,
                 decision_manager=None, dice_manager=None, all_tokens=None, game_log=None,
                 auto_players=(), ai_destination=None, ai_mover=None):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.dice_manager = dice_manager
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: The AI's policy, injected by main.py (game/ must not import ai/).
        self.ai_destination = ai_destination
        self.ai_mover = ai_mover
        self._stratagem = Stratagem(GOADED_INTO_ACTION_NAME, GOADED_INTO_ACTION_CP, self._grant)
        self._acting = None          # the unit being paid for
        self._roll = None            # the D6 while it is on the table
        self._moving_squad = None
        self._shooter = None         # the enemy unit whose attacks triggered it
        self._restore_active = None

    # ----------------------------------------------------------- questions
    def eligible(self, squad, wounded):
        """TARGET: one friendly unengaged BEAST SNAGGA unit that lost a wound."""
        if squad is None or not _living(squad):
            return False
        if not da_big_hunt.fields_da_big_hunt(squad.owner) or not da_big_hunt.is_beast_snagga_unit(squad):
            return False
        if squad not in wounded:
            return False
        if is_engaged(squad, self.all_tokens):
            return False
        # 21.02's own eligibility, asked of the controller that owns it.
        if self.movement_controller is not None and not self.movement_controller.can_make_surge_move(squad):
            return False
        return True

    def candidates(self, shooter, wounded):
        return sorted((s for s in wounded
                       if s.owner != shooter.owner and self.eligible(s, wounded)),
                      key=lambda s: s.name)

    def can_use(self, squad, shooter=None, wounded=()):
        tt = self.turn_tracker
        if tt is None or self.is_busy:
            return False
        # "YOUR OPPONENT'S Shooting phase" - the shooter is the active player's.
        if tt.phase != PHASE_SHOOTING or squad is None or squad.owner == tt.turn_owner:
            return False
        if not self.eligible(squad, set(wounded)):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    @property
    def is_busy(self):
        return self._roll is not None or self._moving_squad is not None

    # ------------------------------------------------------- the moment
    def on_squad_finished_shooting(self, shooter, hit_squads):
        """The listener main.py appends to ShootingController - it asks that
        controller which of the units it HIT actually lost a wound, which is the
        printed TARGET clause."""
        wounded = (self.shooting_controller.squads_wounded_this_activation()
                   if self.shooting_controller is not None else ())
        return self.offer_after_shooting(shooter, wounded)

    def offer_after_shooting(self, shooter, wounded):
        """Fed from ShootingController.on_squad_finished_shooting - `wounded` is
        squads_wounded_this_activation()."""
        if shooter is None:
            return False
        wounded = set(wounded or ())
        candidates = [s for s in self.candidates(shooter, wounded) if self.can_use(s, shooter, wounded)]
        if not candidates:
            return False
        self._shooter = shooter
        owner = candidates[0].owner
        if owner in self.auto_players or self.decision_manager is None:
            return bool(self.use(candidates[0]))
        from game import unit_choice_offer
        return unit_choice_offer.offer_one_of(
            self.decision_manager, owner, candidates,
            "%s (%d CP): %s shot you - which unit makes a D6\" surge move?"
            % (GOADED_INTO_ACTION_NAME, GOADED_INTO_ACTION_CP, shooter.name),
            self.use, decline_label=DECLINE_LABEL, is_stratagem=True)

    def use(self, squad):
        if not self.can_use(squad, self._shooter, self._wounded_now(squad)):
            return False
        self._acting = squad
        try:
            return bool(self.stratagem_controller.use(squad.owner, self._stratagem, [squad]))
        finally:
            self._acting = None

    def _wounded_now(self, squad):
        """The eligibility of a unit that has already been named by the offer:
        a human answers frames later, and the ledger it was picked from is the
        one the offer used."""
        return (squad,)

    def _grant(self, controller, player, targets):
        squad = self._acting or (targets[0] if targets else None)
        if squad is None:
            return False
        self._moving_squad = squad
        self._roll = DiceNotationRoll(
            D6(), count=1, dice_manager=self.dice_manager,
            label="%s: %s surge move distance" % (GOADED_INTO_ACTION_NAME, squad.name),
            log=(self.game_log.add if self.game_log is not None else None),
            rolled_for=squad,
        )
        if self._roll.done:            # no dice_manager (tests)
            total = self._roll.total
            self._roll = None
            self._start_move(total)
        return True

    # ------------------------------------------------------------ the dice
    def pending_roll_choice(self):
        """"If your unit is riled up, it can re-roll that D6" - the dice panel's
        own re-roll button while this roll is on the table."""
        from game import roll_choice
        squad = self._moving_squad
        dm = self.dice_manager
        if (self._roll is None or squad is None or dm is None or not dm.pending_values
                or not riled_up.is_riled_up(squad) or not dm.rerollable_indices()
                or squad.owner in self.auto_players or self.decision_manager is None
                or dm.reroll_offer_claimed(GOADED_INTO_ACTION_NAME)):
            return None
        return roll_choice.RollChoice(squad.owner, [
            roll_choice.RollOption(roll_choice.ACCEPT),
            roll_choice.RollOption(roll_choice.WHOLE, 1, label="Re-roll the D6", acknowledges=False,
                                   apply=self._reroll),
        ], claims=(GOADED_INTO_ACTION_NAME,))

    def _reroll(self):
        if self.dice_manager is None or not self.dice_manager.claim_reroll_offer(GOADED_INTO_ACTION_NAME):
            return
        if self.dice_manager.reroll_die(0) and self.game_log is not None:
            self.game_log.add("%s: %s re-rolls its surge distance (riled up)."
                              % (GOADED_INTO_ACTION_NAME, self._moving_squad.name))

    def maybe_reroll_for_ai(self):
        """The AI's half of the same clause: re-roll a 1 or 2, keep the rest.
        Free, so the only question is whether it can get worse - it cannot."""
        squad = self._moving_squad
        dm = self.dice_manager
        if (self._roll is None or squad is None or dm is None or not dm.pending_values
                or squad.owner not in self.auto_players or not riled_up.is_riled_up(squad)
                or not dm.rerollable_indices() or not dm.claim_reroll_offer(GOADED_INTO_ACTION_NAME)):
            return False
        if dm.pending_values[0] > 2:
            return False
        return bool(dm.reroll_die(0))

    def on_dice_acknowledged(self):
        if self._roll is None:
            return
        self._roll.on_dice_acknowledged()
        if self._roll.done:
            total = self._roll.total
            self._roll = None
            self._start_move(total)

    # ------------------------------------------------------------ the move
    def _start_move(self, distance):
        squad = self._moving_squad
        mc = self.movement_controller
        if squad is None or mc is None or not distance:
            self._moving_squad = None
            return
        if self.turn_tracker is not None:
            self._restore_active = self.turn_tracker.active_player
            self.turn_tracker.set_active(squad.owner)
        mc.select(squad.models[0])
        mc.start_surge_move(squad, float(distance), closest_enemy_squad(squad, self.all_tokens))
        if self.game_log is not None:
            self.game_log.add('%s: %s makes a %g" surge move.'
                              % (GOADED_INTO_ACTION_NAME, squad.name, distance))
        if squad.owner in self.auto_players:
            self._move_for_ai(squad, distance)

    def _move_for_ai(self, squad, distance):
        if self.ai_destination is None or self.ai_mover is None:
            self.cancel_move()
            return
        point = self.ai_destination(squad, self._shooter)
        if point is None or not self.ai_mover(squad, point, distance):
            self.cancel_move()
            return
        self.confirm_move()

    def confirm_move(self):
        mc = self.movement_controller
        if mc is None:
            return
        mc.confirm_move()
        if not mc.errors:
            self._finish()

    def cancel_move(self):
        if self.movement_controller is not None:
            self.movement_controller.cancel_move()
        self._finish()

    def _finish(self):
        self._moving_squad = None
        self._shooter = None
        if self.turn_tracker is not None and self._restore_active is not None:
            self.turn_tracker.set_active(self._restore_active)
        self._restore_active = None
