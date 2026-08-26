"""The Technomancer's "Rites of Reanimation".

RULE (printed, word for word):
  "While this model is leading a unit, models in that unit have the Feel No
   Pain 5+ ability."

WORD FOR WORD THE SAME SHAPE as the Ork Painboy's Dok's Toolz
(game/doks_toolz.py) - a leader granting his whole unit Feel No Pain 5+ - so
this is deliberately its twin rather than anything cleverer, and it folds into
game/feel_no_pain.py's current_feel_no_pain() the same way. That function
folds sources pairwise, so "adding a source is one more fold" and the
never-worse-than-printed guarantee holds for free: Illuminor Szeras, who prints
Feel No Pain 4+, keeps his 4+ if he ever stands in a unit granted this 5+.

leader_ability() rather than unit_wide_ability(), for the reason that helper's
own docstring gives: unit_wide_ability() asks whether EVERY model prints the
ability, and for a leader grant none of the bodyguards do. It also brings rule
19.04's grace window along, so a Technomancer killed mid-sequence does not
silently strip his unit's Feel No Pain for the rest of the attacking unit's
attacks.
"""

from game.attached_units import leader_ability

RITES_OF_REANIMATION_FEEL_NO_PAIN = "5+"


def rites_of_reanimation_feel_no_pain(model):
    """This model's Feel No Pain threshold from a Technomancer leading its
    unit, or "-" if there is none.

    Returns a threshold STRING, matching UnitProfile.feel_no_pain's own
    convention, so the caller keeps parsing it with parse_threshold()."""
    squad = getattr(model, "squad", None)
    if squad is None:
        return "-"
    return (RITES_OF_REANIMATION_FEEL_NO_PAIN
            if leader_ability(squad, "rites_of_reanimation") else "-")
