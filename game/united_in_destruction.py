"""Skorpekh Lord's "United In Destruction".

RULE (printed, word for word):
  "While this model is leading a unit, melee weapons equipped by models in
   that unit have the [LETHAL HITS] ability."

THE SHAPE IS SPIRIT OF GORK'S SECOND HALF, one grant short. Both hand [LETHAL
HITS] to a whole unit's melee weapons; the difference is only the condition -
Spirit of Gork asks about a psychic power being up, this one asks 24.22's
"while this model is LEADING a unit". So the READER is a chain entry in
FightController._adjusted_weapon(), same as that one, and for the same reason:
_crit_note() has to know at ROLL time whether a critical die is a [LETHAL HITS]
die, and it reads that off the returned weapon.

WHY leader_ability() AND NOT unit_wide_ability(): the printed text is the
"while this model is leading" form, so none of the bodyguards print it - a
unit_wide_ability() predicate would be False for every unit that actually has
the ability. That trap is written out in game/attached_units.py's own docstring
and this repo has fallen into it before. leader_ability() also brings 19.04's
grace window along for free, which matters here: a Lord killed by the enemy's
own attacks partway through does not silently shrink the rest of his squad's.

NO PHASE LEDGER, deliberately. There is nothing to spend and nothing to time
out - the condition is simply whether he is alive and leading, which is read
live on every attack. Contrast Plasmacyte next door, which needs both.
"""

import copy

from game.attached_units import leader_ability


def unit_has_united_in_destruction(squad):
    """"While this model is leading a unit" - 24.22, via 19.04's source
    models, so a dead Lord stops conferring at the documented moment."""
    return leader_ability(squad, "united_in_destruction")


def adjusted_weapon(weapon, squad):
    """[LETHAL HITS] on this unit's melee weapons while the Lord leads it.

    Copies rather than mutating: WeaponProfile instances are shared per model
    and this repo's standing rule is that effects copy. Melee-only is not
    checked here because the whole chain this sits in is FightController's -
    game/shooting.py never calls it, which the test pins at the source rather
    than by building a shooting scene."""
    if weapon is None or weapon.lethal_hits:
        return weapon
    if not unit_has_united_in_destruction(squad):
        return weapon
    granted = copy.copy(weapon)
    granted.lethal_hits = True
    return granted
