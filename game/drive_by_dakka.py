"""Orks datasheet ability: Warbikers' Drive-by Dakka, as supplied by the
user (not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/starscythe.py/game/retaliation_cadre.py for
the equivalent T'au abilities).

RULE: each time a model in this unit makes a ranged attack that targets a
unit within 9", improve the Armour Penetration characteristic of that
attack by 1."""

import copy

from game.squad import edge_distance

DRIVE_BY_DAKKA_RANGE_IN = 9.0


def drive_by_dakka_adjusted_weapon(weapon, pairs, target_squad):
    """"Improve the Armour Penetration characteristic" is modeled as an
    actual change to that characteristic (a shallow copy, same reasoning as
    starscythe_adjusted_weapon()/bonded_heroes_adjusted_weapon() - the
    shared WeaponProfile instance is never mutated), not a flat modifier on
    the save threshold, for the same stepped-lookup reason those two
    document.

    Whether the group counts as a Drive-by Dakka attack is decided from its
    representative shooter (pairs[0][0]), same simplification as the other
    two. "Within 9"" is read the same way Bonded Heroes reads its own
    AP-tier range check: true if ANY attacking model in `pairs` is within
    that distance of ANY target model, using CURRENT positions (nothing
    moves between target selection and resolution within a single
    activation in this engine)."""
    shooter_model = pairs[0][0] if pairs else None
    if shooter_model is None or not shooter_model.profile.drive_by_dakka:
        return weapon
    if not any(
        edge_distance(shooter, defender) <= DRIVE_BY_DAKKA_RANGE_IN
        for shooter, _ in pairs
        for defender in target_squad.models
    ):
        return weapon
    boosted = copy.copy(weapon)
    boosted.ap = weapon.ap - 1  # AP is stored negative (see save_threshold += -weapon.ap) - "improve" means more negative
    return boosted
