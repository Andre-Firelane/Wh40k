"""Ancient Collector - Trazyn the Infinite's own ability.

RULE (printed, word for word):

  "While this model is leading a unit, at the end of your Command phase, if
   that unit is within range of an objective marker you control, it remains
   under your control, even if you have no models within range of it, until
   your opponent controls it at start or end of any turn."

That is game/fieldcraft.py's sentence with ONE clause added, so it joins that
sweep rather than starting a second sticky-objective scheme - the choice
fieldcraft.py itself argues for at length, and the reason rule 14.03's Secured
already exists (Objective.secure_for()/secured_by, released exactly when "the
opponent's raw level of control is strictly greater").

THE ONE CLAUSE IS "WHILE THIS MODEL IS LEADING A UNIT", and it is the half a
copy of Fieldcraft would lose. A Trazyn standing on his own secures nothing.

  * Asked with attached_units.leader_ability(), NOT squad.unit_wide_ability().
    The latter asks whether EVERY model prints the ability, which for a leader
    ability is false for every bodyguard - so a predicate written that way is
    False for exactly the units that have it. That module's own docstring
    records the trap.
  * leader_ability() also requires a REAL rule 19.01 attachment rather than
    merely a squad containing the model, which is precisely "leading a unit".

FOURTH CALLER of Objective.secure_for(). Its docstring said "not called by
anything yet, since we have no unit-ability system; here for when one exists" -
that stopped being true three abilities ago (Marker Beacon, the Spirit Conclave
token, Fieldcraft) and is corrected rather than left to mislead a fifth.
"""

from game import attached_units

ANCIENT_COLLECTOR_NAME = "Ancient Collector"


def applies(squad):
    """Whether this unit is currently secured by a Trazyn who is leading it."""
    return bool(attached_units.leader_ability(squad, "ancient_collector"))
