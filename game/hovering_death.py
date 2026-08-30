"""The Foetid Bloat-drone's own ability "Hovering Death".

RULE (printed, word for word):

  "This model is eligible to shoot and declare a charge in a turn in which it
  Fell Back."

RULE 09.07 normally forbids both after a Fall Back, and this engine enforces
that through Squad.fell_back_this_turn, read by shooting.can_shoot() and
charge.can_declare_charge(). So the ability is a single exception asked at
those two gates, and nothing else in the Fall Back path changes.

A UNIT-WIDE test, not a per-model one. The Bloat-drone is a one-model unit, so
the two cannot be told apart today - but any() over the unit is the reading
that matches every other keyword-style ability in this engine (FLY, DEEP
STRIKE), and a hypothetical attached model would not take the exception away
from the drone that prints it.
"""


def squad_ignores_fall_back(squad):
    """Whether this unit may still shoot and charge after Falling Back."""
    if squad is None:
        return False
    return any(getattr(m.profile, "hovering_death", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())
