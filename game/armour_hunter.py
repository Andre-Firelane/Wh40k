"""Hammerhead Gunship's "Armour Hunter".

RULE (printed, word for word):
  "Each time this model makes an attack that targets a MONSTER or VEHICLE, add
   1 to the Hit roll."

TANK HUNTERS WITH ONE HALF MISSING. The Tankbustas' ability and the Myphitic
Blight-hauler's both add 1 to the Hit roll AND 1 to the Wound roll against the
same two keywords; this one adds only the Hit half. That is why it gets its own
flag rather than reusing either of theirs - a shared flag would silently hand a
Hammerhead a +1 to wound that its datasheet does not print, which is exactly
the trap tank_hunters_modifiers()'s own docstring records having avoided once
already between the Ork and Death Guard versions.

IT DOES SHARE THE HELPER, though: the keyword test ("a MONSTER or VEHICLE
unit") is is_monster_or_vehicle_unit(), the same one Tank Hunters asks, so the
two cannot disagree about what a vehicle is.

SIGN: negative. game/modifiers.py adjusts the THRESHOLD, so "add 1 to the Hit
roll" - a bonus - is -1 on the number the die has to reach.

PER MODEL ("this model"), not per unit - so it is read off the attacking
model's own profile, the same way tank_hunters_modifiers() is. On this
datasheet the unit is one model and the two readings coincide; written this way
because the printed text says so, not because it currently matters.
"""

from game.modifiers import Modifier
from game.squad import is_monster_or_vehicle_unit

ARMOUR_HUNTER_LABEL = "Armour Hunter (MONSTER/VEHICLE)"
# Negative because a positive modifier WORSENS a threshold in this engine.
ARMOUR_HUNTER_HIT_MODIFIER = -1


def modifiers(attacking_model, target_squad):
    """The Hit-roll modifier this attack gets, as a list (empty when none) -
    the same shape tank_hunters_modifiers() returns, so a caller can extend
    with it."""
    if attacking_model is None or not is_monster_or_vehicle_unit(target_squad):
        return []
    if not getattr(attacking_model.profile, "armour_hunter", False):
        return []
    return [Modifier(ARMOUR_HUNTER_HIT_MODIFIER, ARMOUR_HUNTER_LABEL)]
