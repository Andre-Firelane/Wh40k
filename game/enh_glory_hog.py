"""Da Big Hunt Enhancement: Glory Hog (25 pts, Mecha Orks stage G5).

RULE (verbatim, rules/orks/detachments/Da Big Hunt.md):
  "BEAST SNAGGA model only. When this unit is selected to make a fall-back
   move, that fall-back move does not prevent this unit from being eligible to
   declare a charge."

ONE HALF OF RULE 09.07, and the half matters: War Horde's Kunnin' But Brutal
prints "shoot/declare a charge" and is a source in BOTH of
game/move_exceptions.py's folds; this one says only "declare a charge", so it
joins may_charge_after_falling_back() and NOT its shooting twin - the same
distinction the Triarch Praetorians' Relentless Combatants makes there, and
exactly what a copy of the Ork neighbour would lose.

Read as a property of the unit while the bearer lives (rule 19.04), which is
enhancements.is_active()'s own reading, with the Da Big Hunt gate folded in.
"""

from game import enhancements

GLORY_HOG = "Glory Hog"


def applies(squad):
    return squad is not None and enhancements.is_active(squad, GLORY_HOG)
