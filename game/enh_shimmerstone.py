"""Aspect Host Enhancement: Shimmerstone (10 pts).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  "AUTARCH or AUTARCH WAYLEAPER model only. While the bearer is leading an
  ASPECT WARRIORS unit, each time a ranged attack targets that unit, subtract
  1 from the Wound roll."

"A RANGED ATTACK" - ONE WORD, AND IT IS THE WHOLE DIFFERENCE from Mirage Field
next door, which says only "an attack" and therefore reaches the Fight phase.
This one is wired into game/shooting.py alone, and that absence is asserted at
the SOURCE (game/fight.py never importing this module) rather than by building
a melee scene that happens to come out unchanged - the same way Aspect of
Murder's ranged-side absence is pinned.

THREE CONDITIONS, AND ALL THREE CAN BE MISSED SEPARATELY:

  1. the bearer carries it (an Enhancement, not a datasheet ability);
  2. the bearer is LEADING - rule 24.22, read through
     attached_units.leader_ability() rather than unit_wide_ability(), because
     no bodyguard prints this and the unit-wide question would answer False
     for every real unit. That also brings 19.04's trailing window with it for
     free;
  3. the unit it leads is an ASPECT WARRIORS unit. An Autarch can lead things
     that are not - and against those the Enhancement does nothing, which is
     why the keyword is checked rather than assumed from the leader.

SIGN POSITIVE - "subtract 1 from the Wound roll" is a HARDER roll, and
game/modifiers.py's convention adjusts the threshold. Same trap as Mirage
Field's.
"""
from game import attached_units, enhancements

SHIMMERSTONE = "Shimmerstone"

#: "subtract 1 from the Wound roll".
SHIMMERSTONE_PENALTY = 1

SHIMMERSTONE_LABEL = "Shimmerstone"

#: "an ASPECT WARRIORS unit".
SHIMMERSTONE_KEYWORD = "ASPECT WARRIORS"


def applies(target_squad):
    """Whether a RANGED attack targeting this unit takes the malus."""
    if target_squad is None:
        return False
    if not enhancements.is_active(target_squad, SHIMMERSTONE):
        return False
    # "While the bearer is LEADING" - 24.22, not "is in the unit".
    if not attached_units.leader_ability(target_squad, "shimmerstone"):
        return False
    return attached_units.unit_has_datasheet_keyword(target_squad, SHIMMERSTONE_KEYWORD)
