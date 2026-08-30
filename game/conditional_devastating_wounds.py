"""[DEVASTATING WOUNDS] granted only against certain targets.

The Leystalker's Long Rifle prints its keyword line as
"DEVASTATING WOUNDS: non-MONSTER/VEHICLE" - the ability, restricted to a class
of target. Every other carrier in this engine prints it unconditionally.

WHY IT IS NOT JUST A FLAG. game/shooting.py reads `weapon.devastating_wounds`
at the wound step and again in _crit_note(), and neither has any notion of a
condition. Setting the flat flag would hand the rifle [DEVASTATING WOUNDS]
against exactly the MONSTER and VEHICLE targets its printed line excludes -
which is the half of the ability that matters, since those are the targets
where mortal wounds would hurt most.

So the grant is applied in the ADJUSTER CHAIN instead, against the real target,
and the weapon that comes out of that chain is what both readers see. That is
the same place Sonic Destruction, the Spirit Mark and both T'au doctrines sit,
and for the same reason: _crit_note() has to know at ROLL time.

THE CONDITION IS THE EXACT COMPLEMENT of squad.is_monster_or_vehicle_unit(),
the same pair Monster Hunters and Grim Reapers use to divide the board between
them - so a unit is never both and never neither.
"""
import copy

from game.squad import is_monster_or_vehicle_unit


def adjusted_weapon(weapon, target_squad):
    """A copy with [DEVASTATING WOUNDS], or the SAME OBJECT untouched - so a
    caller can tell "unchanged" from "copied" by identity."""
    if weapon is None or target_squad is None:
        return weapon
    if not getattr(weapon, "devastating_wounds_vs_non_monster_vehicle", False):
        return weapon
    if getattr(weapon, "devastating_wounds", False):
        return weapon          # already unconditional; nothing to add
    if is_monster_or_vehicle_unit(target_squad):
        return weapon          # the targets the printed line excludes
    adjusted = copy.copy(weapon)
    adjusted.devastating_wounds = True
    return adjusted
