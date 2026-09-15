"""Boyz' Tide of Muscle (2026-09 Ork codex).

RULE (verbatim, rules/orks/Boyz.md):
  "Tide of Muscle: In the Fight phase, if this unit made a charge move this
   turn, this unit's melee attacks have [Lethal Hits]."

A keyword grant, so it sits in FightController._adjusted_weapon(): the hit
step and _crit_note() read [LETHAL HITS] off the returned weapon at ROLL time.
"In the Fight phase" is structural - only game/fight.py asks. "Made a charge
move this turn" is Squad.charged_this_turn (rule 11.04's flag, cleared at the
end of the turn). "This unit" is rule 19.04's unit-wide reading, so a Warboss
leading the mob swings with it too.
"""

import copy

from game.squad import unit_wide_ability
from game.weapons import MELEE

TIDE_OF_MUSCLE_NAME = "Tide of Muscle"


def applies(squad):
    return (squad is not None and bool(getattr(squad, "charged_this_turn", False))
            and bool(unit_wide_ability(squad, "tide_of_muscle")))


def adjusted_weapon(weapon, squad):
    """[LETHAL HITS] on a melee weapon while the rule applies. A copy; never
    downgrades a weapon that already has the keyword."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or weapon.lethal_hits:
        return weapon
    if not applies(squad):
        return weapon
    granted = copy.copy(weapon)
    granted.lethal_hits = True
    return granted
