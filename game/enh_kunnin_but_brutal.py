"""War Horde Enhancement: Kunnin' But Brutal (20 pts).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  "ORKS model only. When this unit is selected to make a fall-back move, that
   fall-back move does not prevent this unit from being eligible to shoot/
   declare a charge."

BOTH HALVES OF RULE 09.07, so it is a source in BOTH of game/move_exceptions.py's
Fall Back folds - may_shoot_after_falling_back() and
may_charge_after_falling_back(). That is the Royal Warden's Adaptive Strategy
pair, and exactly the half a copy of the Triarch Praetorians' Relentless
Combatants (charge only) would lose.

Read as a property of the unit while the bearer lives (rule 19.04), which is
enhancements.is_active()'s own reading, with the War Horde gate folded in.
"""

from game import enhancements

KUNNIN_BUT_BRUTAL = "Kunnin' But Brutal"


def applies(squad):
    return squad is not None and enhancements.is_active(squad, KUNNIN_BUT_BRUTAL)
