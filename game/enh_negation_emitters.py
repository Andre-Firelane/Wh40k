"""Advanced Acquisition Cadre Enhancement: Negation Emitters (15 pts).

RULE (verbatim, rules/tau_empire/detachments/Advanced Acquisition Cadre.md):
  STEALTH BATTLESUITS unit only. This unit has -3" detection range.

A UNIT-LEVEL ENHANCEMENT, WHICH IS UNUSUAL AND IS THE PRINTED TEXT
-------------------------------------------------------------------
"STEALTH BATTLESUITS unit only. THIS UNIT has..." - not "model only", and not
"the bearer". Every other T'au Enhancement here goes on one CHARACTER model;
this one and Unmasking Suite go on a unit, and neither of the datasheets they
name has a CHARACTER at all, so requiring one would make them unbuildable.

game/enhancements.py handles that with `unit_level=True`: grant() marks every
model of the unit, and its 19.04 reading ("a living model still carries it")
then means "the unit still exists", which is the right lifetime for something
the unit as a whole has.

WHERE IT LANDS, AND WHICH WAY THE SIGN GOES
--------------------------------------------
game/detection_range.py, the fold rule 13.09's is_detectable() now asks once.
Detection range belongs to the HIDDEN model there - is_detectable() asks whether
an observer is within the hidden model's own range - so -3" means the unit must
be approached 3" CLOSER before it can be seen. That is a benefit to the bearer,
which is what a device that "masks energy emissions" should be. Read the other
way round it would expose the unit that paid 15 points to hide.

Measured in BOTH bands rather than one, because the base is not a single
number: 15" default -> 12", and the 12" house rule (a Dense wall on the model's
own footprint) -> 9". A bonus tested only against the default would pass while
being applied to the wrong base.
"""

from game import enhancements

NEGATION_EMITTERS = "Negation Emitters"
NEGATION_EMITTERS_MODIFIER_IN = -3.0     # "-3" detection range"


def applies(squad):
    """A living model of the unit still carries it, and the owner really
    fields Advanced Acquisition Cadre."""
    return enhancements.is_active(squad, NEGATION_EMITTERS)


def detection_bonus_in(squad):
    """This Enhancement's contribution to game/detection_range.py's fold.

    Named `..._bonus_in` like every other source there even though its value is
    negative: the fold sums signed contributions, and a source that inverted
    the sign in its own name would have to be inverted again at the call site.
    """
    return NEGATION_EMITTERS_MODIFIER_IN if applies(squad) else 0.0
