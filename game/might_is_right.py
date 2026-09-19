"""The Warboss's Might Is Right (2026-09 Ork codex).

RULE (verbatim, rules/orks/Warboss.md):
  "Might Is Right: If this unit made a charge move this turn, this model's
   melee attacks have:
   - +3 A.
   - +2 S."

NOT the pre-codex ability of the same name ("while this model is leading a
unit, each time a model in that unit makes a melee attack, add 1 to the Hit
roll"). That leader grant went with the old sheet, and so did
squad_has_might_is_right().

TWO SUBJECTS IN ONE SENTENCE, the shape Headwoppa's Killchoppa already has:
"this UNIT made a charge move" is Squad.charged_this_turn (rule 11.04's flag),
and "this MODEL's melee attacks" is the Warboss alone. After a 19.01 merge he is
one model of twenty, so game/fight.py's _melee_attack_key() carries attack_key()
below; without it the one-representative shortcut could hand +3 A to the Boyz he
leads, or take it from him.

A DICE-NOTATION characteristic takes the bonus on its flat part, the way
game/rokkit_charge.py does it. The grant rides the fight adjuster chain, which
the attack count, the Strength of the wound roll and extra_attack_dice() read.
"""

import copy

from game import dice_notation
from game.weapons import MELEE

MIGHT_IS_RIGHT_NAME = "Might Is Right"
#: "+3 A".
MIGHT_IS_RIGHT_ATTACKS = 3
#: "+2 S".
MIGHT_IS_RIGHT_STRENGTH = 2


def is_bearer(model):
    return bool(model is not None and not model.is_dead()
                and getattr(model.profile, "might_is_right", False))


def attack_key(model):
    """The per-model term for _melee_attack_key(): True for a bearer only, so no
    group that existed before splits."""
    return bool(model is not None and getattr(model.profile, "might_is_right", False))


def applies(model):
    """A living bearer whose unit made a charge move this turn."""
    return is_bearer(model) and bool(getattr(getattr(model, "squad", None), "charged_this_turn", False))


def _plus(notation, bonus):
    return dice_notation.plus(notation, bonus)


def adjusted_weapon(weapon, model):
    """+3 A and +2 S on the bearer's melee weapons once his unit has charged
    this turn. A copy - a WeaponProfile instance is never mutated."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not applies(model):
        return weapon
    boosted = copy.copy(weapon)
    boosted.attacks = weapon.attacks + MIGHT_IS_RIGHT_ATTACKS
    boosted.attacks_notation = _plus(getattr(weapon, "attacks_notation", None), MIGHT_IS_RIGHT_ATTACKS)
    boosted.strength = weapon.strength + MIGHT_IS_RIGHT_STRENGTH
    if getattr(weapon, "strength_notation", None) is not None:
        boosted.strength_notation = _plus(weapon.strength_notation, MIGHT_IS_RIGHT_STRENGTH)
    return boosted
