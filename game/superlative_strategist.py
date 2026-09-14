"""The Autarch's "Superlative Strategist" - a datasheet ability.

RULE (printed, word for word):
  "While this model is leading a unit, you can re-roll Advance rolls made for
  that unit, and you can re-roll any rolls made for that unit while it is
  performing an Agile Manoeuvre."

TWO CLAUSES, AND ONLY THE FIRST IS WIRED
-----------------------------------------
  * THE ADVANCE RE-ROLL is built, on the machinery it now shares with the Orks
    army rule Waaagh! - see game/advance_reroll_offer.py.
  * "ANY ROLLS MADE FOR THAT UNIT WHILE IT IS PERFORMING AN AGILE MANOEUVRE" is
    NOT modelled. game/battle_focus.py's manoeuvres are resolved without a dice
    step of their own - the six are movement and eligibility effects, and the
    only dice they touch belong to the move or the shot that follows, which are
    not "rolls made while performing the manoeuvre". There is no roll here to
    re-roll, so the clause has nothing to attach to. Named rather than dropped,
    the same treatment Trail Finding and Jammer Array get.

THE SEAM THIS NEEDED DID NOT EXIST, AND ITS ABSENCE WAS A LIVE BUG
-------------------------------------------------------------------
game/protocol_sudden_storm.py has had maybe_offer_advance_reroll() since the
Necron work. It is unit-tested and was never called from main.py - the "built
but never FED" failure this repo has now hit five times, and which only a
source-level guard can see.

Worse, its own docstring says it is "called from main.py right after an Advance
roll is acknowledged", and that could not have worked either:
DiceManager.acknowledge() clears pending_values, and reroll_die() refuses a
roll with none. So the offer has to come BEFORE the acknowledgement, which is
where main.py now makes it - for every carrier, from one place.
"""
from game.advance_reroll_offer import ADVANCE_REROLL_FLOOR, AdvanceRerollOfferController  # noqa: F401 - re-exported
from game.attached_units import leader_ability

SUPERLATIVE_STRATEGIST_LABEL = "Superlative Strategist"


def applies(squad):
    """"While this model is LEADING a unit" - so 24.22's leader question, not
    a plain flag check: an Autarch standing alone grants nothing, and a
    bodyguard model never carries it."""
    return bool(squad is not None and leader_ability(squad, "superlative_strategist"))


class SuperlativeStrategistController(AdvanceRerollOfferController):
    """The Advance re-roll offer. One per battle."""

    LABEL = SUPERLATIVE_STRATEGIST_LABEL

    def applies(self, squad):
        return applies(squad)
