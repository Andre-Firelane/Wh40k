"""The Deathshroud Terminators' own ability "Death Approaches".

RULE (printed): when this unit is set up by Deep Strike, it can be set up more
than 6" horizontally away from any Afflicted enemy unit, and more than 8"
horizontally away from any other enemy unit - instead of rule 20.04's usual 9".

TWO NUMBERS, NOT ONE, and that is the whole point of the ability: 8" is a flat
improvement on 9" against anything, and 6" is a further one against a unit the
army rule has already touched. Reading it as a single relaxed distance would
throw away the half that makes Nurgle's Gift and Deep Strike work together.

WHY THE DISTANCE IS ASKED PER ENEMY UNIT rather than as one number for the
placement: the two thresholds apply to DIFFERENT enemies at the same time, so
"the minimum distance for this drop" is not a well-defined quantity - a landing
spot 7" from an Afflicted unit and 9" from a fresh one is legal, and no single
number describes that. minimum_distance_to() therefore answers for one enemy
unit, and the placement check asks it once per enemy.

THE 9" DEFAULT IS READ FROM game/ingress.py rather than written again here, so
a change to the core rule cannot leave this ability quietly out of step.
"""
from game import nurgles_gift

DEATH_APPROACHES_AFFLICTED_IN = 6.0
DEATH_APPROACHES_OTHER_IN = 8.0


def has_ability(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "death_approaches", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


def minimum_distance_to(squad, enemy_squad, default_in):
    """How far from `enemy_squad` this unit must be set up, in inches.

    `default_in` is rule 20.04's usual distance, passed in by the caller so the
    core number lives in one place. A unit without the ability always gets it
    back unchanged, which is what lets the call site ask unconditionally."""
    if not has_ability(squad):
        return default_in
    if nurgles_gift.is_afflicted(enemy_squad):
        return DEATH_APPROACHES_AFFLICTED_IN
    return DEATH_APPROACHES_OTHER_IN
