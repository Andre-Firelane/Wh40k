"""Warhost Enhancement: Gift of Foresight (15 pts).

RULE (verbatim, rules/aeldari/detachments/Warhost.md):
  "ASURYANI model only. Once per battle round, you can target the bearer's unit
  with the Command Re-roll Stratagem for 0CP."

THE WHOLE CARD IS THE SHARED SENTENCE, so this module is a name and two
constants - see game/free_stratagem_once_per_round.py for the machinery and for
why it is a subclass rather than a fifth consumer of the plain CP discount.

Its sibling Protector of the Paths prints the same sentence with Fire Overwatch
in place of Command Re-roll AND a second clause about hit rolls; that clause is
why the two are separate modules rather than two instances of one.
"""
from game.command_reroll import COMMAND_REROLL_CP_COST  # noqa: F401
from game.free_stratagem_once_per_round import FreeNamedStratagemOncePerRound

GIFT_OF_FORESIGHT = "Gift of Foresight"

GIFT_OF_FORESIGHT_LABEL = "Gift of Foresight"

#: The Stratagem this makes free, by the name StratagemController knows.
GIFT_OF_FORESIGHT_STRATAGEM = "Command Re-roll"


class GiftOfForesightDiscount(FreeNamedStratagemOncePerRound):
    flag = "gift_of_foresight"
    stratagem_name = GIFT_OF_FORESIGHT_STRATAGEM
    enhancement_name = GIFT_OF_FORESIGHT
    label = GIFT_OF_FORESIGHT_LABEL
