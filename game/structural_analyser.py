"""Darkstrider's "Structural Analyser".

RULE (printed, word for word):
  "While this model is leading a unit, each time a model in that unit makes a
   ranged attack, add 1 to the Wound roll."

A BONUS ON THE WOUND ROLL, WHICH IS A NEGATIVE MODIFIER HERE. game/modifiers.py
adjusts the THRESHOLD, not the die, so "add 1 to the roll" makes the roll
easier and is therefore -1 on the threshold. Getting this backwards would turn
Darkstrider into an army-wide malus - which is exactly the mistake Command
Protocols' own note records having nearly made.

RANGED ONLY, so it lives in ShootingController._wound_modifiers() and NOT in
FightController's. The printed text says "a ranged attack" where the Necron
Guardian Protocols next door says "an attack" and therefore needs both; the
test pins the absence from game/fight.py at the source rather than by building
a melee scene that proves nothing.

ATTACKER-SIDE, unlike almost everything else in _wound_modifiers(): that
function is mostly the defender's own protection (Guardian Drone, the Wave
Serpent Shield), and this is only the second entry that reads the SHOOTING
squad instead - Tank Hunters is the first.

leader_ability() rather than unit_wide_ability(), for the usual reason: none of
the Pathfinders he leads print this, so a unit_wide_ability() predicate would
be False for every unit that actually has the ability. It also brings 19.04's
grace window, so Darkstrider dying partway through does not shrink the rest of
his unit's attacks.
"""

from game.attached_units import leader_ability

STRUCTURAL_ANALYSER_LABEL = "Structural Analyser"
# Negative because game/modifiers.py's convention is that a positive number
# WORSENS the threshold, and "add 1 to the Wound roll" is a bonus.
STRUCTURAL_ANALYSER_WOUND_MODIFIER = -1


def applies(attacking_squad):
    """"While this model is leading a unit" - 24.22, via 19.04's source models,
    so a dead Darkstrider stops conferring at the documented moment."""
    return leader_ability(attacking_squad, "structural_analyser")
