"""The Dragon Knights' "Agile Reach" - a datasheet ability.

RULE (printed, word for word):
  "When this unit is selected to fight, melee weapons equipped by unengaged
  models in this unit that are within 3" of an enemy unit that is engaged with
  this unit can target that enemy unit."

IT WIDENS 12.02, WHICH IS THE ONE THING IN THE FIGHT PHASE MOST WORTH BEING
CAREFUL WITH
---------------------------------------------------------------------------
Rule 12.02 asks, per MODEL, "is this model within Engagement Range (2") of the
target". game/fight.py answers it with model_engaged_with(), and the answer is
SNAPSHOTTED at target selection so that losses cannot retroactively unmake a
legal choice - the fix a user report already paid for once.

This ability extends the reach for models that are NOT engaged: 3" instead of
2", but only towards a unit some OTHER model of theirs is already engaged with.
So it cannot bring a wholly disengaged unit into a fight; it only lets the back
rank of a unit already in combat swing.

BECAUSE THE ANSWER IS SNAPSHOTTED, this has to widen the question at the point
the snapshot is TAKEN, not at the point it is read - otherwise the extra models
would be counted for one activation and forgotten for the next.
"""
from game.squad import edge_distance, model_engaged_with

AGILE_REACH_LABEL = "Agile Reach"

#: "within 3 inches of an enemy unit that is engaged with this unit".
AGILE_REACH_RANGE_IN = 3.0


def applies(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "agile_reach", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def unit_is_engaged_with(squad, target_squad):
    """"an enemy unit that is ENGAGED WITH THIS UNIT" - the unit-level question,
    not the per-model one, which is the whole point: one engaged model opens the
    reach for the rest."""
    return any(model_engaged_with(m, target_squad)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def model_can_reach(model, squad, target_squad):
    """Whether THIS model may target that enemy under the widened rule.

    Returns False for a model that is already engaged - it needs no help, and
    12.02's own test already says yes."""
    if model is None or not applies(squad):
        return False
    if not unit_is_engaged_with(squad, target_squad):
        return False
    if model_engaged_with(model, target_squad):
        return False          # already engaged; the ordinary rule covers it
    return any(edge_distance(model, other) <= AGILE_REACH_RANGE_IN
               for other in getattr(target_squad, "models", ()) or ()
               if not other.is_dead())
