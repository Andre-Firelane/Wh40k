"""Green Tide Enhancement: Ferocious Show-off (15 pts, Mecha Orks stage G3).

RULE (verbatim, rules/orks/detachments/Green Tide.md):
  "ORKS INFANTRY model only. This model's melee attacks have:
   - +1 A.
   - Or: If this unit has 11+ models, +2 A."

PER BEARER. "This MODEL's melee attacks" - after a 19.01 merge the bearer is one
model among many, so game/fight.py's _melee_attack_key() carries attack_key()
below and the bearer swings in a group of his own; without it the
one-representative shortcut would hand the bonus to whichever group he shares
(the term Headwoppa's Killchoppa and Aspect of Murder needed for the same
reason).

"OR: IF THIS UNIT HAS 11+ MODELS, +2 A" REPLACES the +1 - the two bullets are
alternatives, not a sum. Counted in LIVING models of the bearer's whole unit at
the moment the attacks are made (game/green_tide.py's living_model_count()), so
a mob shot down to ten swings the bearer at +1.

A dice-notation Attacks characteristic takes the bonus on its flat part
(game/dice_notation.py's plus()), as every other +A grant here does.
"""

import copy

from game import dice_notation, enhancements, green_tide
from game.weapons import MELEE

FEROCIOUS_SHOW_OFF = "Ferocious Show-off"
FEROCIOUS_SHOW_OFF_ATTACKS = 1
FEROCIOUS_SHOW_OFF_MOB_ATTACKS = 2
#: "If this unit has 11+ models".
FEROCIOUS_SHOW_OFF_MOB_SIZE = 11


def is_bearer(model):
    """A living bearer whose owner fields Green Tide."""
    return model is not None and enhancements.model_is_active(model, FEROCIOUS_SHOW_OFF)


def attack_key(model):
    """The per-model term for _melee_attack_key(): True for the bearer only, so
    no group that existed before splits."""
    return bool(is_bearer(model))


def attacks_bonus(model):
    """+2 while the bearer's unit has 11+ living models, else +1; 0 for anyone
    else."""
    if not is_bearer(model):
        return 0
    if green_tide.living_model_count(getattr(model, "squad", None)) >= FEROCIOUS_SHOW_OFF_MOB_SIZE:
        return FEROCIOUS_SHOW_OFF_MOB_ATTACKS
    return FEROCIOUS_SHOW_OFF_ATTACKS


def adjusted_weapon(weapon, model):
    """The bonus on the bearer's melee weapons. A copy - a WeaponProfile
    instance is never mutated."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE:
        return weapon
    bonus = attacks_bonus(model)
    if not bonus:
        return weapon
    boosted = copy.copy(weapon)
    boosted.attacks = weapon.attacks + bonus
    boosted.attacks_notation = dice_notation.plus(getattr(weapon, "attacks_notation", None), bonus)
    return boosted
