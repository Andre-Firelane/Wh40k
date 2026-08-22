"""T'au Empire detachment rule: Retaliation Cadre's Bonded Heroes, as
supplied by the user (not a rule from the generic 40k core rulebook, so it
lives in its own module - same reasoning as game/greater_good.py for the
army rule). See game/factions/tau_empire.py for the descriptive Detachment
record.

RULE: each time a T'au Empire Battlesuit model from your army makes a
ranged attack that targets a unit within 12", improve the Strength
characteristic of that attack by 1. If that attack targets a unit within
9", improve the Armour Penetration characteristic of that attack by 1 as
well.

Simplification (documented, matching game/greater_good.py's precedent):
this engine has no army-building/detachment-selection flow yet (see
CLAUDE.md's Später-Liste), and Retaliation Cadre is currently the only
detachment that exists - bonded_heroes_adjusted_weapon() therefore applies
unconditionally to any BATTLESUIT-keyword model's ranged attack, the same
way game/greater_good.py's For The Greater Good applies unconditionally to
any model with that ability, without an "is this army actually T'au Empire
under this detachment" check. Revisit once a real detachment-selection
system exists."""

import copy

from game.attached_units import unit_has_keyword
from game.squad import edge_distance

BONDED_HEROES_STRENGTH_RANGE_IN = 12.0
BONDED_HEROES_AP_RANGE_IN = 9.0


def is_battlesuit_unit(squad):
    """Rule 19.03: an attached unit has all of its components' keywords, so
    a Commander joined to a Crisis team is a BATTLESUIT unit as a whole.

    Lives here rather than in either stratagem module because BOTH of this
    detachment's stratagems key off the same keyword (Stim Injectors'
    TARGET clause and The Arro'kon Protocol's), and the detachment module
    is the one thing they already have in common - importing it from one
    stratagem into the other would couple them for no reason."""
    return unit_has_keyword(squad, lambda model: model.profile.battlesuit)


def bonded_heroes_adjusted_weapon(weapon, pairs, target_squad):
    """"Improve the Strength/Armour Penetration characteristic" is modeled
    as an actual change to those characteristics (a shallow copy, like
    melta_adjusted_weapon() - the shared WeaponProfile instance is never
    mutated), not as a flat modifier on the wound/save threshold: the S-vs-T
    and AP-vs-Sv lookups are stepped, not linear (e.g. S8 vs T4 and S9 vs T4
    both already need a 2+ to wound), so a real characteristic change and a
    flat roll modifier can diverge at those boundaries - the rule text says
    "characteristic", so this follows that literally.

    Whether the group counts as a Battlesuit attack is decided from its
    representative shooter (pairs[0][0]) - the same simplification already
    used throughout game/shooting.py (e.g. extra_attack_dice(),
    melta_adjusted_weapon() itself) for a group that could theoretically mix
    models with identical weapon stats but different keywords. "Within
    12"/9"" is read the same way [MELTA X]/[RAPID FIRE X] already read their
    own range checks in that file: true if ANY attacking model in `pairs` is
    within that distance of ANY target model, using CURRENT positions
    (nothing moves between target selection and resolution within a single
    activation in this engine)."""
    shooter_model = pairs[0][0] if pairs else None
    if shooter_model is None or not shooter_model.profile.battlesuit:
        return weapon
    if not any(
        edge_distance(shooter, defender) <= BONDED_HEROES_STRENGTH_RANGE_IN
        for shooter, _ in pairs
        for defender in target_squad.models
    ):
        return weapon
    boosted = copy.copy(weapon)
    boosted.strength = weapon.strength + 1
    if any(
        edge_distance(shooter, defender) <= BONDED_HEROES_AP_RANGE_IN
        for shooter, _ in pairs
        for defender in target_squad.models
    ):
        boosted.ap = weapon.ap - 1  # AP is stored negative (see save_threshold += -weapon.ap) - "improve" means more negative
    return boosted
