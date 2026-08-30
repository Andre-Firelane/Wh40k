"""The Ethereal's "Failure Is Not an Option".

RULE (printed, word for word):
  "While this model is leading a unit, models in that unit have the Feel No
   Pain 5+ ability."

THE THIRD DATASHEET TO PRINT THIS EXACT SENTENCE, after the Ork Painboy's
Dok's Toolz (game/doks_toolz.py) and the Necron Technomancer's Rites of
Reanimation (game/rites_of_reanimation.py). So it is deliberately their twin,
and folds into game/feel_no_pain.py's current_feel_no_pain() the same way -
which makes the never-worse-than-printed guarantee free.

leader_ability() rather than unit_wide_ability(), for the reason that helper's
own docstring gives: unit_wide_ability() asks whether EVERY model prints the
ability, and for a leader grant none of the bodyguards do. It also brings rule
19.04's grace window along, so an Ethereal killed mid-sequence does not
silently strip his unit's Feel No Pain for the rest of the attacking unit's
attacks.
"""

from game.attached_units import leader_ability

FAILURE_IS_NOT_AN_OPTION_FEEL_NO_PAIN = "5+"


def failure_is_not_an_option_feel_no_pain(model):
    """This model's Feel No Pain threshold from an Ethereal leading its unit,
    or "-" if there is none.

    Returns a threshold STRING, matching UnitProfile.feel_no_pain's own
    convention, so the caller keeps parsing it with parse_threshold()."""
    squad = getattr(model, "squad", None)
    if squad is None:
        return "-"
    return (FAILURE_IS_NOT_AN_OPTION_FEEL_NO_PAIN
            if leader_ability(squad, "failure_is_not_an_option") else "-")
