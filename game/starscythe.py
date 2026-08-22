"""T'au Empire datasheet ability: Crisis Starscythe Battlesuits' Starscythe,
as supplied by the user (not a rule from the generic 40k core rulebook, so
it lives in its own module - same reasoning as game/retaliation_cadre.py for
Bonded Heroes and game/suppression.py etc. for the other user-supplied T'au
abilities).

RULE: each time a model in this unit makes a ranged attack (excluding
attacks that target MONSTERS and VEHICLES), improve the Armour Penetration
characteristic of that attack by 1."""

import copy

from game.squad import is_monster_or_vehicle_unit


def starscythe_adjusted_weapon(weapon, pairs, target_squad):
    """"Improve the Armour Penetration characteristic" is modeled as an
    actual change to that characteristic (a shallow copy, same reasoning as
    bonded_heroes_adjusted_weapon()/melta_adjusted_weapon() - the shared
    WeaponProfile instance is never mutated), not a flat modifier on the
    save threshold, for the same stepped-lookup reason those two document.

    Whether the group counts as a Starscythe attack is decided from its
    representative shooter (pairs[0][0]) - the same simplification
    bonded_heroes_adjusted_weapon() itself already uses for a group that
    could theoretically mix models with identical weapon stats but
    different abilities. "Excluding attacks that target MONSTERS and
    VEHICLES" is a target-UNIT-keyword exclusion (not a range check, unlike
    Bonded Heroes/[MELTA X]/[RAPID FIRE X]), so it's read straight off
    target_squad via the already-existing is_monster_or_vehicle_unit()."""
    shooter_model = pairs[0][0] if pairs else None
    if shooter_model is None or not shooter_model.profile.starscythe:
        return weapon
    if is_monster_or_vehicle_unit(target_squad):
        return weapon
    boosted = copy.copy(weapon)
    boosted.ap = weapon.ap - 1  # AP is stored negative (see save_threshold += -weapon.ap) - "improve" means more negative
    return boosted
