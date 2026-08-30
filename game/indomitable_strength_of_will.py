"""The Autarch Wayleaper's "Indomitable Strength of Will" - a datasheet ability.

RULE (printed, word for word):
  "While this model is leading a unit, each time you spend a Battle Focus token
  to enable that unit to perform an Agile Manoeuvre, roll one D6: on a 3+, you
  gain 1 Battle Focus token."

A REFUND, AND THE ONE CLAUSE THAT DECIDES WHERE IT HANGS
--------------------------------------------------------
"Each time you SPEND a Battle Focus token" - so the trigger is the spend, not
the manoeuvre. game/battle_focus.py's _spend() is the one place a token leaves
the pool, and it has a branch that does NOT spend one: Fleet of Foot makes some
manoeuvres free. A refund hung on "performed a manoeuvre" would hand a token
back for a manoeuvre that cost nothing, printing free tokens out of an ability
that is meant to return them.

So it is fed from the spend itself, after the decrement, and only on the paid
path - which is also why this module takes the SQUAD and asks 24.22's leader
question rather than reading a flag off any model in it.

THE ROLL IS RESOLVED IMMEDIATELY rather than as a dice-panel step, for the same
reason Undying Spite's and the Monofilament Snare's are: nothing is decided by
it, and a manoeuvre is a routine, repeated action. Reported in the log instead.

"YOU GAIN 1 BATTLE FOCUS TOKEN" is a plain refund into the same pool, so it can
carry a unit past its starting allowance - the printed text sets no ceiling and
game/battle_focus.py keeps none.
"""
from game.attached_units import leader_ability

INDOMITABLE_LABEL = "Indomitable Strength of Will"

#: "on a 3+".
INDOMITABLE_THRESHOLD = 3


def applies(squad):
    """"While this model is LEADING a unit" - 24.22's question, so a Wayleaper
    standing alone refunds nothing."""
    return bool(squad is not None
                and leader_ability(squad, "indomitable_strength_of_will"))


class IndomitableStrengthOfWillController:
    """Fed from game/battle_focus.py's _spend(), on the paid path only."""

    def __init__(self, battle_focus=None, game_log=None):
        self.battle_focus = battle_focus
        self.game_log = game_log

    def on_token_spent(self, player, squad, manoeuvre=None):
        """Returns True when a token was actually refunded."""
        if not applies(squad) or self.battle_focus is None:
            return False
        rolled = self._roll_one()
        if rolled < INDOMITABLE_THRESHOLD:
            if self.game_log is not None:
                self.game_log.add("[indomitable] %s rolled a %d - no token back."
                                  % (squad.name, rolled), file_only=True)
            return False
        self.battle_focus.tokens[player] = self.battle_focus.tokens.get(player, 0) + 1
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s rolled a %d - %s gains 1 Battle Focus token back."
                % (INDOMITABLE_LABEL, squad.name, rolled, player))
        return True

    def _roll_one(self):
        from game.dice import random as dice_random
        return dice_random.randint(1, 6)
