"""Painboy's "Dok's Toolz" ability (user-supplied datasheet text, not a core
rule - hence its own module, same reasoning as game/volley_fire.py and
game/coldstar.py, the two other "while this model is leading a unit..."
abilities in this engine).

RULE (Painboy, Orks):
  Dok's Toolz: While this model is leading a unit, models in that unit have
  the Feel No Pain 5+ ability.

WHY leader_ability() AND NOT unit_wide_ability()
------------------------------------------------
game/attached_units.py's leader_ability() is the predicate written for exactly
this wording, and unit_wide_ability() is not merely imprecise here but always
wrong: it asks whether EVERY model is printed with the ability, and for a
leader ability none of the bodyguards are - that is the whole point of one.
leader_ability() also brings rule 19.04's grace window along for free, so a
Painboy killed mid-sequence does not silently strip the rest of his mob's
Feel No Pain part-way through an attack.

WHY THIS NEEDS NO THREADING THROUGH THE CONTROLLERS
---------------------------------------------------
Contrast game/waaagh.py's Krumpin' Time, whose own note lists the damage
sources it does NOT reach (Crushing Impact, Deadly Demise, Explosives,
[HAZARDOUS] mortal wounds) because those controllers are never handed a
WaaaghController. This ability is a property of the UNIT the model is in, so
it is readable from the model alone - exactly like Stim Injectors - and
therefore reaches every source that builds a FeelNoPainRoll at all, with no
optional collaborator to forget to pass. game/feel_no_pain.py's
current_feel_no_pain() folds it in with the rest.
"""

from game.attached_units import leader_ability

DOKS_TOOLZ_FEEL_NO_PAIN = "5+"


def doks_toolz_feel_no_pain(model):
    """This model's Feel No Pain threshold from a Painboy leading its unit,
    or "-" if there is none.

    Returns a threshold STRING, matching UnitProfile.feel_no_pain's own
    convention, so the caller keeps parsing it with parse_threshold()."""
    squad = getattr(model, "squad", None)
    if squad is None:
        return "-"
    return DOKS_TOOLZ_FEEL_NO_PAIN if leader_ability(squad, "doks_toolz") else "-"
