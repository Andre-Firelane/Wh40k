"""Windrider Host Enhancement: Mirage Field (25 pts).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  "ASURYANI MOUNTED model only. Each time an attack targets the bearer's unit,
  subtract 1 from the Hit roll."

"AN ATTACK", SO BOTH PHASES. The word this card does NOT print is "ranged" -
its Aspect Host neighbour Shimmerstone does, one line over, and that single
word is the whole difference between the two. So this is folded into
game/shooting.py's AND game/fight.py's _hit_modifiers(), and the melee half is
tested rather than assumed.

"THE BEARER'S UNIT", NOT THE BEARER. Under rule 19.01 a joined character is
merged into the squad, so the Enhancement is carried by one MODEL but shields
every model that shares its unit - which is what makes it worth 25 points on a
jetbike squad. Read with enhancements.is_active(squad, ...), the unit-level
question, rather than per model.

DEFENDER-SIDE, so it takes the TARGET squad and asks nothing about the
attacker. That also makes it phase-symmetric: the same call, the same
argument, in both chains.

SIGN POSITIVE. game/modifiers.py's convention adjusts the THRESHOLD, and
"subtract 1 from the Hit roll" makes the roll harder - so +1. Written the other
way round this would be an army-wide BONUS to everything shooting at the
bearer, which is the failure mode this repo has recorded for Command Protocols
and Structural Analyser, and it looks correct from inside the module either
way.
"""
from game import enhancements

MIRAGE_FIELD = "Mirage Field"

#: "subtract 1 from the Hit roll" - a WORSE roll, so a positive threshold
#: adjustment under game/modifiers.py's convention.
MIRAGE_FIELD_PENALTY = 1

MIRAGE_FIELD_LABEL = "Mirage Field"


def applies(target_squad):
    """Whether attacks targeting this unit take the malus."""
    return enhancements.is_active(target_squad, MIRAGE_FIELD)
