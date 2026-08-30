"""Aspect Host Enhancement: Strategic Savant (10 pts).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  "AUTARCH or AUTARCH WAYLEAPER model only. While the bearer is leading an
  ASPECT WARRIORS unit, add 1 to the Objective Control characteristic of models
  in that unit."

AN ADD, so it goes in effective_oc()'s third layer with the two T'au
Enhancements - and that layer runs LAST on purpose: paying points for a +1
should always buy one, rather than being clamped away by Scabrous Soulrot's
floor or overwritten by Hunting Hounds' set.

"MODELS IN THAT UNIT", not the bearer - the opposite noun from Craftworld's
Champion in the same batch, which says "the bearer has". So this is read off
the model's SQUAD while that one is read off the model. One word, and the test
puts the two side by side.

"WHILE THE BEARER IS LEADING" is rule 24.22, so it goes through
attached_units.leader_ability() rather than a distance test: that helper
enforces 19.01's attachment AND carries 19.04's grace window, so a bearer that
dies mid-phase does not silently take the bonus away from models that already
used it.

AND THE UNIT MUST BE ASPECT WARRIORS. A merged unit pools its keywords under
19.03, so the check is asked of the unit rather than of the bodyguard models -
the Autarch's own datasheet is not ASPECT WARRIORS, and the unit is.
"""

from game import attached_units, enhancements

STRATEGIC_SAVANT = "Strategic Savant"

#: "add 1 to the Objective Control characteristic".
STRATEGIC_SAVANT_OC_BONUS = 1

#: The unit the bearer must be leading.
STRATEGIC_SAVANT_KEYWORD = "ASPECT WARRIORS"


def applies(squad):
    """Whether this UNIT is currently getting the bonus."""
    if squad is None:
        return False
    if not enhancements.is_active(squad, STRATEGIC_SAVANT):
        return False
    if not attached_units.leader_ability(squad, "strategic_savant"):
        return False
    return attached_units.unit_has_datasheet_keyword(squad, STRATEGIC_SAVANT_KEYWORD)


def oc_bonus(model):
    """+1 to every model in the led unit. Read by
    game/objective_control.py's fold."""
    if model is None:
        return 0
    return STRATEGIC_SAVANT_OC_BONUS if applies(getattr(model, "squad", None)) else 0
