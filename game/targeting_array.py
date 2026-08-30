"""Hammerhead and Sky Ray Gunships' "Targeting Array".

RULE (printed, word for word):
  "Each time this model is selected to shoot, you can re-roll one Hit roll or
   you can re-roll one Wound roll when resolving those attacks."

RULE 15.02'S COMMAND RE-ROLL WITHOUT THE CP. One die, chosen by the player,
re-rolled - which is exactly what game/command_reroll.py already does, down to
the interactive "click a die" step. So it follows its shape precisely
(`can_use` -> `start` -> `choose_die` / `cancel_selection`, with
`selecting_die` driving both the panel and the click routing), and it is a
PANEL BUTTON rather than a prompt for the same reason the Aspect Shrine tokens
and Branching Fates are: the user asked for that shape explicitly, and a
question after every roll is unbearable.

THREE DIFFERENCES FROM COMMAND RE-ROLL, and each is printed:

  * NO COST and no 15.01 bookkeeping - it is a datasheet ability, not a
    Stratagem, so there is no StratagemController involved at all.
  * ITS RESOURCE IS THE ACTIVATION: "each time this model is SELECTED TO
    SHOOT" gives exactly one use per shooting activation of that unit.
  * ONE KIND OR THE OTHER: "one Hit roll OR one Wound roll". Not one of each -
    a single use, spendable on whichever of the two rolls the player prefers.

THE MACHINERY NOW LIVES IN game/activation_reroll.py, extracted when the Fire
Prism's Crystal Matrix became the second ability of this shape - it prints the
same sentence with AND where this one has OR. What stays here is this
datasheet's own reading, plus the names its call sites already use, so nothing
outside had to move. The OR/AND distinction is `RerollAbility.shared_use`.
"""
from game.activation_reroll import (  # noqa: F401  (re-exported for call sites)
    REROLLABLE_KINDS,
    ActivationRerollController as TargetingArrayController,
)

TARGETING_ARRAY_LABEL = "Targeting Array"


def unit_has_targeting_array(squad):
    """Read live off the living models, so it ends with the gunship."""
    if squad is None:
        return False
    return any(getattr(m.profile, "targeting_array", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())
