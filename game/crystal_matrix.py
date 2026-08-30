"""The Fire Prism's "Crystal Matrix" - a datasheet ability.

RULE (printed, word for word):
  "Each time this model is selected to shoot, you can re-roll one Hit roll and
   you can re-roll one Wound roll when resolving those attacks."

ONE WORD FROM TARGETING ARRAY, AND THE WORD IS THE RULE
-------------------------------------------------------
The Hammerhead's Targeting Array prints the identical sentence with OR: one
use, spendable on either roll. This prints AND: one use of EACH. So the two
share every piece of machinery - the panel button, the click-a-die selection,
the per-activation window - and differ only in how the ledger is keyed.

That machinery is game/activation_reroll.py, extracted when this became its
second consumer. This ability's own reading is the single line below:
`shared_use=False`, i.e. the Hit use and the Wound use are separate.

WHY THAT MATTERS RATHER THAN BEING A DETAIL: with a shared ledger, spending the
re-roll on a Hit roll would silently remove the Wound re-roll the datasheet
grants - a Fire Prism would get half the ability and nothing would look wrong.
Both halves are measured separately in the test for that reason.

NO AI PATH (standing Aeldari instruction). Nothing stalls without one: the
ability is a panel BUTTON, not a prompt, so an AI-owned Fire Prism simply never
presses it - the same way it never presses Targeting Array.
"""

CRYSTAL_MATRIX_LABEL = "Crystal Matrix"


def unit_has_crystal_matrix(squad):
    """Read live off the living models, so it ends with the tank."""
    if squad is None:
        return False
    return any(getattr(m.profile, "crystal_matrix", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())
