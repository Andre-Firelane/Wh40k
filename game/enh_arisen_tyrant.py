"""Hypercrypt Legion Enhancement: Arisen Tyrant (25 pts).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  "NECRONS model only. Each time a model in the bearer's unit makes an attack,
   re-roll a Hit roll of 1. If the bearer's unit was set up on the battlefield
   this turn, you can re-roll the Hit roll instead."

THE TWO-CLAUSE SHAPE game/reroll_scope.py names: an automatic re-roll of 1s,
and "you can re-roll the Hit roll INSTEAD" - so its label is one of the
ones-or-whole sources, and it sits at the same five seams the Canoptek Court's
Power Matrix does (the Hit re-roll reason and the automatic 1s chain, in both
game/shooting.py and game/fight.py, plus the label). "An attack", so both phases.

"SET UP ON THE BATTLEFIELD THIS TURN" is Squad.set_up_this_turn, the field
SetupController sets on every confirmed placement and main.py clears at the end
of the turn - an ingress arrival, a Hyperphasic Recall, and the deployment
(which begin_battle() clears before the first turn, rule 18.02). A model RETURN
does not set it (SetupController's mark_set_up=False): the unit was not set up,
it got a model back.

The bearer being alive and the detachment being fielded are
enhancements.is_active()'s two halves.
"""

from game import enhancements

ARISEN_TYRANT = "Arisen Tyrant"
ARISEN_TYRANT_LABEL = "Arisen Tyrant"


def applies(squad):
    """The automatic half: re-roll a Hit roll of 1."""
    return squad is not None and enhancements.is_active(squad, ARISEN_TYRANT)


def offers_full_reroll(squad):
    """The conditional half: the whole Hit roll, INSTEAD of the 1s."""
    return applies(squad) and bool(getattr(squad, "set_up_this_turn", False))
