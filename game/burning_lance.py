"""Fuegan's "Burning Lance".

RULE (printed, word for word):
  "While this model is leading a unit, add 6" to the Range characteristic of
   Melta weapons equipped by models in that unit."

THE SAME SHAPE AS THE PULSE ACCELERATOR DRONE, which is the useful thing to say
about it: one model changes a Range characteristic for every model in its unit,
so the number cannot be baked into the weapon at build time - it has to be
derived live, wherever range is actually measured. That is game/weapon_range.py,
which folds this and the drone into the one answer to "how far does this weapon
reach right now"; this module supplies only the term.

TWO DIFFERENCES from the drone, both straight from the wording:

  * "MELTA weapons", not a named weapon. The drone names pulse carbines and so
    matches on the printed NAME (and documents that reading as uncertain); this
    one names a KEYWORD, so it reads weapon.melta and there is nothing to guess.
    Fuegan's own Searsong is [MELTA] on both its firing profiles, and he is a
    model in that unit, so his own range grows too - that is what "models in
    that unit" says.

  * "While this model is LEADING a unit" is 24.22's own condition, read through
    attached_units.leader_ability() and NOT squad.unit_wide_ability(): the
    latter asks whether EVERY model prints the ability, which for a leader
    ability no bodyguard does. It also brings 19.04's grace window along, so
    Fuegan dying mid-sequence does not silently shorten the rest of the unit's
    attacks - and, with Unquenchable Resolve putting him back, does not
    permanently end the ability either.

WHY IT REACHES HALF RANGE TOO. game/shooting.py's [MELTA X] and [RAPID FIRE X]
steps ask "is the target within HALF this weapon's range", and half of a
CHARACTERISTIC that has been added to is half of the new number. The printed
text modifies the characteristic itself, not "the range at which this weapon can
be selected", so 12" fusion gun becomes 18" and its melta bonus reaches out to
9" rather than 6". shooting.py's own comment predicted this case exactly ("no
pulse carbine has either keyword - if one ever does, they need the same
treatment"); a [MELTA] weapon is the one that does.
"""

from game import attached_units

BURNING_LANCE_BONUS_IN = 6.0


def unit_has_burning_lance(squad):
    """True while a model with the ability is LEADING this unit (24.22)."""
    return attached_units.leader_ability(squad, "burning_lance")


def bonus_for(model, weapon):
    """This weapon's Range bonus from Burning Lance - 0 unless the weapon is
    [MELTA] and its wielder's unit is being led by Fuegan.

    Takes the MODEL rather than the squad for the same reason the drone's
    version does: game/shooting.py measures per shooter on the hot path, and a
    model with no squad (probe tokens, tests) degrades to no bonus instead of
    raising."""
    if not getattr(weapon, "melta", 0):
        return 0.0
    if not unit_has_burning_lance(getattr(model, "squad", None)):
        return 0.0
    return BURNING_LANCE_BONUS_IN
