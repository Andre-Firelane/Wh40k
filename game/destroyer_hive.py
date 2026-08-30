"""Typhus' own ability "The Destroyer Hive".

RULE (printed, word for word):

  "While this model is leading a unit, each time a melee attack targets that
  unit, subtract 1 from the Hit roll."

A DEFENDER-SIDE HIT MODIFIER, which is unusual enough to say out loud: almost
everything in FightController._hit_modifiers() asks about the ATTACKER, and
this asks about the TARGET. It is the melee twin of Forewarned, which already
sits in the same list for the same reason.

The sign is POSITIVE. game/modifiers.py's convention is that a Modifier adjusts
the THRESHOLD a die must beat, and "subtract 1 from the Hit roll" makes that
harder - so it is +1 on the threshold, not -1. Getting this backwards would
turn Typhus' bodyguard into the easiest unit on the table to hit.

MELEE ONLY, exactly as printed - it says "a melee attack", so game/shooting.py
does not read this module at all, and the test asserts that at the source
rather than by building a shooting scene that proves nothing.

leader_ability() rather than unit_wide_ability(): "while this model is LEADING
a unit" is rule 24.22's shape, and unit_wide_ability() asks whether EVERY model
prints the thing - which for a leader clause no bodyguard does. It also brings
19.04's grace window with it, so Typhus dying mid-sequence does not silently
un-protect his unit for the rest of the attacking unit's attacks.
"""
from game.attached_units import leader_ability
from game.modifiers import Modifier

DESTROYER_HIVE_PENALTY = 1  # positive worsens the threshold - see the docstring
DESTROYER_HIVE_LABEL = "The Destroyer Hive"


def applies(target_squad):
    """Whether melee attacks against `target_squad` are -1 to Hit right now."""
    return leader_ability(target_squad, "destroyer_hive")


def hit_modifiers(target_squad):
    """The Modifier list game/fight.py's _hit_modifiers() extends with. Empty
    unless the ability applies, so the call site can extend unconditionally."""
    if not applies(target_squad):
        return []
    return [Modifier(DESTROYER_HIVE_PENALTY, DESTROYER_HIVE_LABEL)]
