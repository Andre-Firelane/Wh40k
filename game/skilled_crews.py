"""Armoured Warhost's "Skilled Crews" - the detachment rule.

RULE (printed, word for word):
  "Friendly AELDARI VEHICLE units' ranged attacks have [ASSAULT]."

The shortest detachment rule in the repo: no window, no choice, no state. One
keyword granted to a keyword-selected set of units for the whole battle.

IN THE ADJUSTER CHAIN, NOT THE WOUND STEP. That is where every keyword grant
goes, and the reason is not tidiness: ShootingController._crit_note() has to
know at ROLL TIME whether a crit die is a Sustained/Lethal/Devastating die, so
it reads the weapon the chain returned. A grant applied later would be invisible
to it. Form copied from game/protocol_sudden_storm.py, which grants the same
keyword.

NEVER A DOWNGRADE. "have the [ASSAULT] ability" GRANTS it; a weapon that
already prints [ASSAULT] is returned untouched rather than re-flagged. The
standing guard on every keyword grant here.

RANGED ONLY, and that is the printed text ("ranged attacks"), not a
simplification - checked as negative space in the test, since game/fight.py
never importing this module is stronger evidence than a melee scene that
happens to come out unchanged.

THE SECOND READER IS THE ONE THAT MATTERS. [ASSAULT] is what lets a unit shoot
after Advancing (rule 24.04), and that question is answered by
game/coldstar.py's weapon_has_assault(), NOT by the wound step. A grant that
reached only the damage maths would leave the rule looking wired while doing
the one thing it is bought for - so the test drives a real Advance and then a
real shot.
"""
import copy

from game import aeldari_detachments
from game.weapons import RANGED

SKILLED_CREWS_LABEL = "Skilled Crews"

#: The config constant game/detachments.py writes for Armoured Warhost.
SETTING = "ARMOURED_WARHOST_PLAYERS"


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def applies(squad):
    """"Friendly AELDARI VEHICLE units" - both halves, plus the detachment.

    VEHICLE is read off the models' profiles (it is one of the handful of
    keywords with a real flag), AELDARI off the datasheet's faction, which is
    where game/factions/aeldari.py keeps it. Rule 19.03 pooling for the
    VEHICLE half: an Aeldari VEHICLE cannot currently be in an attached unit,
    but any() is what "unit has the keyword" means and costs nothing."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    return any(getattr(m.profile, "vehicle", False)
               for m in (getattr(squad, "models", ()) or ()) if not m.is_dead())


def adjusted_weapon(weapon, squad):
    """[ASSAULT] on this unit's ranged weapons."""
    if weapon is None or not applies(squad):
        return weapon
    if getattr(weapon, "weapon_type", None) != RANGED or weapon.assault:
        return weapon
    granted = copy.copy(weapon)
    granted.assault = True
    return granted
