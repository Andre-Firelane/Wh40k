"""Orks detachment rule: War Horde's Get Stuck In, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/retaliation_cadre.py for T'au Empire's
Retaliation Cadre). See game/factions/orks.py for the descriptive
Detachment record.

RULE: melee weapons equipped by Orks models from your army have the
[SUSTAINED HITS 1] ability.

Simplification (documented, matching game/retaliation_cadre.py's own
precedent for Bonded Heroes): this engine has no army-building/detachment-
selection flow yet (see CLAUDE.md's Später-Liste), and War Horde is
currently the only Orks detachment that exists - get_stuck_in_adjusted_
weapon() therefore applies unconditionally to any model with the `orks`
UnitProfile flag, without an "is this army actually running War Horde"
check."""

import copy

from game.weapons import MELEE

GET_STUCK_IN_SUSTAINED_HITS = 1


def get_stuck_in_adjusted_weapon(weapon, pairs):
    """"Have the [SUSTAINED HITS 1] ability" is modeled as an actual
    characteristic change (shallow copy, same reasoning as
    bonded_heroes_adjusted_weapon()/waaagh_melee_adjusted_weapon() - the
    shared WeaponProfile instance is never mutated), only for MELEE weapons
    (the rule text says "melee weapons" explicitly).

    Whether the group counts as an Orks attack is decided from its
    representative fighter (pairs[0][0]), same simplification as every
    other detachment/army-rule adjuster in this codebase. Granting the
    ability sets it to (at least) 1 rather than unconditionally overwriting
    it - a weapon that already has SUSTAINED HITS at a higher value from
    some other source (none currently exists among Ork weapons, but the
    rule only GRANTS the ability, it doesn't say "set to 1") keeps its
    better value."""
    if weapon.weapon_type != MELEE:
        return weapon
    fighter_model = pairs[0][0] if pairs else None
    if fighter_model is None or not fighter_model.profile.orks:
        return weapon
    if weapon.sustained_hits >= GET_STUCK_IN_SUSTAINED_HITS:
        return weapon
    boosted = copy.copy(weapon)
    boosted.sustained_hits = GET_STUCK_IN_SUSTAINED_HITS
    return boosted
