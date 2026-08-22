"""Dire Avengers' Bladestorm - a datasheet ability, so it gets its own module
like every other named ability in this codebase.

RULE (printed, word for word):
  "Ranged weapons equipped by models in this unit have the [SUSTAINED HITS 1]
  ability while targeting an enemy unit within half range."

SHAPE
-----
Structurally the same thing The Arro'kon Protocol does (grant [SUSTAINED HITS]
conditionally, per weapon group, as a real characteristic change on a shallow
copy) with a different condition, so it is chained into game/shooting.py's
resolution beside it. Two differences worth stating:

- It is a UNIT ABILITY, not a stratagem: no CP, no controller, no phase
  bookkeeping. The condition is entirely "this model's unit prints Bladestorm
  and the target is close enough", which is a pure function of the board - so
  it is a function, not a class.
- Its condition is a DISTANCE, and "half range" is measured the way every other
  half-range rule in this engine measures it (rule 24.25's [MELTA X] and rule
  24.30's [RAPID FIRE X]): once per weapon group, true if ANY attacking model
  is within half of THAT WEAPON's range of ANY model of the target unit. The
  half is per weapon, not per unit, which matters here because an Exarch can be
  carrying an 18" catapult while its squadmates carry the same 18" catapult and
  a 12" pistol - the pistol's half is 6", not 9".

GRANTS rather than overwrites, same as Arro'kon and War Horde's Get Stuck In: a
weapon that already has a higher [SUSTAINED HITS] keeps it, and two sources of
the same ability never add up.

RANGED ONLY, and that is the printed wording ("Ranged weapons equipped by
models in this unit"), not a simplification - so it is chained into
game/shooting.py alone and game/fight.py never asks.
"""

import copy

# edge_distance lives in game/squad.py, not game/geometry.py. No cycle:
# game/shooting.py imports this module and game/squad.py does not.
from game.squad import edge_distance
from game.weapons import RANGED

BLADESTORM_SUSTAINED_HITS = 1


def squad_has_bladestorm(squad):
    """Rule 19.04's shape: the ability belongs to the models that print it, so
    any() rather than all() - an attached CHARACTER joining a Dire Avenger
    squad does not take the ability away from the Avengers.

    Note this is deliberately NOT the same reading as "models in this unit have
    it": the ability is granted to weapons equipped by models in the unit, and
    the unit still has the ability as long as an Avenger is alive to carry it.
    A joined character's own guns get it too, which is what the wording says."""
    models = getattr(squad, "models", None)
    if not models:
        return False
    return any(getattr(m.profile, "bladestorm", False) and not m.is_dead() for m in models)


def bladestorm_adjusted_weapon(weapon, pairs, target_squad):
    """[SUSTAINED HITS 1] while the target unit is within half range.

    `pairs` is the weapon group's (shooter, weapon) list; whether the group's
    unit has the ability is decided from its representative shooter, the same
    exact-here simplification every other adjuster in this file's chain uses -
    a group's models all belong to one unit."""
    if getattr(weapon, "weapon_type", None) != RANGED:
        return weapon
    if not pairs or target_squad is None:
        return weapon
    shooter_model = pairs[0][0]
    if not squad_has_bladestorm(getattr(shooter_model, "squad", None)):
        return weapon
    if BLADESTORM_SUSTAINED_HITS <= weapon.sustained_hits:
        return weapon
    half_range = weapon.range_in / 2
    in_half_range = any(
        edge_distance(shooter, defender) <= half_range
        for shooter, _ in pairs
        for defender in target_squad.models
        if not defender.is_dead()
    )
    if not in_half_range:
        return weapon
    boosted = copy.copy(weapon)
    boosted.sustained_hits = BLADESTORM_SUSTAINED_HITS
    return boosted
