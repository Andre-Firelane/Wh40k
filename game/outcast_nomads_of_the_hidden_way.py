"""Path of the Outcast Stratagem: Nomads of the Hidden Way (1CP).

RULE (verbatim, rules/aeldari/detachments/Path of the Outcast.md):
  WHEN:   Your Shooting phase, when a friendly RANGERS/SHROUD RUNNERS unit has
          shot.
  TARGET: That RANGERS/SHROUD RUNNERS unit.
  EFFECT: - Your unit can make a normal move of up to D6".
          - Your unit is not eligible to declare a charge or embark within a
            TRANSPORT until the end of the turn.
  RESTRICTIONS: none printed - both bullets are inside the EFFECT.

THE SECOND BULLET IS PRINTED AS AN EFFECT, NOT A RESTRICTION, and Warhost's
Fire and Fade prints the same idea as a RESTRICTIONS clause. Mechanically the
same here, but the difference is transcribed rather than normalised: a later
reader comparing the two files should find the engine saying what the pages say.

TWO LOCKS, AND ONLY ONE OF THEM EXISTED. Squad.charge_locked_until_end_of_turn
has five users; there was no counterpart for embarking, so
embark_locked_until_end_of_turn was added beside it in game/transport.py's
can_embark(). Both are set here, and both at CONFIRM rather than at accept -
the printed effect is a move, and a move the player then cancels should not
leave the unit locked out of two things it never traded for. That is the call
game/fire_and_fade.py already makes for its own charge lock.

AN OWN-TURN MOVE, so it goes through MovementController.start_post_shooting_move()
and NOT through start_battle_focus_move(). The difference matters:
REACTIVE_MOVE_MODES is what stops the AI walking over a human's open move
during the OPPONENT'S turn, and this move happens in the player's own Shooting
phase - registering it there would be wrong, and CLAUDE.md records what
happened twice when a reactive mode was left OUT of that set.

THE D6 IS ROLLED FIRST. The move budget is not known until the die falls, so
the roll opens, and the move opens on its acknowledgement - the arrangement
game/raid_and_run.py uses for its own D3+3".

THE AI DECLINES (standing Aeldari instruction).
"""

from game import ai_mode, far_reaching_doom
from game.dice_notation import D6, DiceNotationRoll
from game.stratagems import Stratagem

NOMADS_NAME = "Nomads of the Hidden Way"
NOMADS_CP = 1

#: "a normal move of up to D6\"" - no flat bonus, unlike Fire and Fade's D6+1".
NOMADS_MOVE_NOTATION = "D6"

#: The move_mode this grant routes the Confirm button to. Its own name, because
#: a move mode is what tells the panel which controller owns the consequence.
NOMADS_MOVE_MODE = "nomads_of_the_hidden_way"


def is_locked(squad):
    """Both locks, which this Stratagem always sets together."""
    return (bool(getattr(squad, "charge_locked_until_end_of_turn", False))
            and bool(getattr(squad, "embark_locked_until_end_of_turn", False)))


class NomadsOfTheHiddenWayController:
    """The offer, the D6, the move, and the two locks."""

    def __init__(self, stratagem_controller, movement_controller=None,
                 dice_manager=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._roll = None
        self._moving_squad = None
        self._stratagem = Stratagem(
            name=NOMADS_NAME, cp_cost=NOMADS_CP, effect=self._effect,
        )

    @property
    def is_busy(self):
        return self._roll is not None or self._moving_squad is not None

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.is_busy:
            return False
        if not far_reaching_doom.applies(squad):
            return False
        if not any(not m.is_dead() for m in (getattr(squad, "models", ()) or ())):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def offer_after_shooting(self, squad, hit_squads=None):
        """`hit_squads` is accepted and ignored: this one names no target
        beyond the shooting unit, unlike its two siblings on the same hook."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False                      # no AI path
        self.decision_manager.request(
            squad.owner,
            '%s (%d CP): %s has shot - make a Normal move of up to %s"? '
            "It could not charge or embark this turn."
            % (NOMADS_NAME, NOMADS_CP, squad.name, NOMADS_MOVE_NOTATION),
            [("Use (%d CP)" % NOMADS_CP, (lambda: self.use(squad))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _effect(self, controller, player, targets):
        squad = targets[0] if targets else None
        if squad is None:
            return
        self._moving_squad = squad
        self._roll = DiceNotationRoll(
            D6(), count=1, dice_manager=self.dice_manager,
            label="%s: %s move distance" % (NOMADS_NAME, squad.name),
            log=(self.game_log.add if self.game_log is not None else None),
        )
        if self._roll.done:                   # no dice_manager (tests)
            total, self._roll = self._roll.total, None
            self._start_move(total)

    def on_dice_acknowledged(self):
        if self._roll is None:
            return
        self._roll.on_dice_acknowledged()
        if self._roll.done:
            total, self._roll = self._roll.total, None
            self._start_move(total)

    def _start_move(self, distance):
        squad = self._moving_squad
        if squad is None or self.movement_controller is None:
            self._moving_squad = None
            return
        self.movement_controller.select(squad.models[0])
        self.movement_controller.start_post_shooting_move(
            squad, move_mode=NOMADS_MOVE_MODE, max_distance=distance)
        if self.game_log is not None:
            self.game_log.add('%s: %s may make a Normal move of up to %d".'
                              % (NOMADS_NAME, squad.name, distance))

    def confirm_move(self):
        """The locks land HERE, not at accept: a cancelled move should not cost
        the unit its charge and its transport."""
        squad, self._moving_squad = self._moving_squad, None
        if squad is None:
            return False
        squad.charge_locked_until_end_of_turn = True
        squad.embark_locked_until_end_of_turn = True
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s cannot declare a charge or embark within a TRANSPORT "
                "for the rest of the turn." % (NOMADS_NAME, squad.name))
        return True

    def cancel_move(self):
        self._moving_squad = None
        return True
