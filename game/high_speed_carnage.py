"""Warbikers' High-speed Carnage (2026-09 Ork codex, stage E3d).

RULE (verbatim, rules/orks/Warbikers.md):
  "High-speed Carnage: If this unit made a charge move this turn, this unit's
   melee attacks have:
   - +1 S and D."

A CHARACTERISTIC GRANT, so it sits in FightController._adjusted_weapon(), beside
the other two charge-turn melee grants of this codex (Tide of Muscle, Rokkit
Charge): the Wound roll reads Strength and the allocation reads Damage off the
returned weapon.

"Made a charge move this turn" is Squad.charged_this_turn (rule 11.04's flag).
No phase is printed and none is needed - only the Fight phase makes melee
attacks. "This unit" is rule 19.04's unit-wide reading, so a Deffkilla Wartrike
leading the bikes would swing with it too (none is built).

A DICE-NOTATION CHARACTERISTIC takes the +1 on its flat bonus, the way Rokkit
Charge and game/psychic_communion.py do it; the grouping placeholder moves with
it. No Warbiker weapon rolls either characteristic today - the branch is the
shape a future leader's weapon would need.

NOT A CHOICE ("have", not "you can"), so there is no prompt and no AI path.
"""

import copy

from game.dice_notation import DiceNotation
from game.squad import unit_wide_ability
from game.weapons import MELEE

HIGH_SPEED_CARNAGE_NAME = "High-speed Carnage"
HIGH_SPEED_CARNAGE_BONUS = 1


def applies(squad):
    return (squad is not None and bool(getattr(squad, "charged_this_turn", False))
            and bool(unit_wide_ability(squad, "high_speed_carnage")))


def _plus(notation):
    if notation is None:
        return None
    return DiceNotation(notation.sides, notation.bonus + HIGH_SPEED_CARNAGE_BONUS, notation.dice)


def adjusted_weapon(weapon, squad):
    """+1 S and +1 D on a melee weapon while the rule applies. A copy - the
    shared WeaponProfile instance is never mutated."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not applies(squad):
        return weapon
    boosted = copy.copy(weapon)
    boosted.strength = weapon.strength + HIGH_SPEED_CARNAGE_BONUS
    if getattr(weapon, "strength_notation", None) is not None:
        boosted.strength_notation = _plus(weapon.strength_notation)
    boosted.damage = weapon.damage + HIGH_SPEED_CARNAGE_BONUS
    if getattr(weapon, "damage_notation", None) is not None:
        boosted.damage_notation = _plus(weapon.damage_notation)
    return boosted
