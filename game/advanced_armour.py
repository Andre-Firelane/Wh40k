"""Broadside Battlesuits' "Advanced Armour".

RULE (printed, word for word):
  "Models in this unit have the Feel No Pain 4+ ability against mortal wounds."

THE FIRST CONDITIONAL FEEL NO PAIN IN THIS ENGINE. Every other source -
Krumpin' Time, Stim Injectors, Dok's Toolz, Rites of Reanimation, the
nanoscarab amulet, Silent Bodyguard, Rites of Feasting, Failure Is Not an
Option - grants a threshold that applies to ANY lost wound. This one applies
only against mortal wounds, and at 4+ it is the best threshold any source here
grants, so getting the condition wrong is not a rounding error: it would give
three Broadsides a 4+ against every attack in the game.

HOW THE CONDITION REACHES THE FOLD. FeelNoPainRoll now takes `mortal`, set by
MortalWoundAllocationSession alone - that session IS the mortal-wound path
(rule 06.02, its own mechanism separate from allocation), so "was this a mortal
wound" needs no new plumbing beyond passing the flag from the one place that
already knows. Every other caller keeps the default and therefore keeps meaning
exactly what it did.

IT IS A PROFILE FIELD, NOT A LEADER GRANT: the printed text is "models in this
unit have", and every model in a Broadside unit prints it. So no
leader_ability() and no 19.04 window - it is simply what the model is.
"""


def advanced_armour_feel_no_pain(model, mortal=False):
    """This model's Feel No Pain threshold against a MORTAL wound, or "-".

    Returns "-" for an ordinary wound however good the printed value is, which
    is the whole of the ability. Returns a threshold STRING, matching
    UnitProfile.feel_no_pain's own convention, so the caller keeps parsing it
    with parse_threshold()."""
    if not mortal:
        return "-"
    return getattr(model.profile, "feel_no_pain_vs_mortal_wounds", "-") or "-"
