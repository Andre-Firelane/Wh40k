"""Orks detachment rule: Da Big Hunt's Da Hunt is On (2026-09 codex, Mecha Orks
stage G5).

PRINTED (rules/orks/detachments/Da Big Hunt.md):

    Da Hunt is On
    Friendly BEAST SNAGGA units' attacks that target a MONSTER/VEHICLE unit
    have +1 AP.

"ATTACKS", not "melee attacks", so it is a link in BOTH adjuster chains -
game/shooting.py's and game/fight.py's - the shape Auxiliary Cadre's
Experimental Modifications already has. "+1 AP" is one MORE negative, as
everywhere in this engine.

THE CONDITION IS THE TARGET'S, so the adjuster takes it: squad.py's
is_monster_or_vehicle_unit() is the same question every other
MONSTER/VEHICLE clause here asks. With no target in hand nothing is granted -
it can under-report, never over-report.

"BEAST SNAGGA units" is the per-model `beast_snagga` flag, pooled over the
components (19.03): a Beastboss leading Beast Snagga Boyz is one BEAST SNAGGA
unit, and a Weirdboy joining them does not dilute it.

The Enhancements are game/enh_glory_hog.py and It Came from da Drops (NOT
wired - see NOT_WIRED); the three Stratagems are game/da_hunt_*.py.
"""

import copy

from game import attached_units
from game.detachment_gate import has_detachment
from game.ork_units import is_orks_unit  # noqa: F401 - the faction half, for callers that need it
from game.squad import is_monster_or_vehicle_unit

#: The config constant game/detachments.py writes for this detachment.
SETTING = "DA_BIG_HUNT_PLAYERS"
DA_HUNT_IS_ON = "Da Hunt is On"
#: "+1 AP".
DA_HUNT_IS_ON_AP = 1

#: Printed, deliberately NOT wired - no BEASTBOSS ON SQUIGOSAUR datasheet exists
#: in this engine, so nothing could ever bear it. Named rather than faked with a
#: bearer it does not have; test_ork_da_big_hunt.py pins that.
NOT_WIRED = {
    "It Came from da Drops": ("BEASTBOSS ON SQUIGOSAUR is not a built datasheet, so no model in "
                              "this engine can bear it - unreachable, not broken"),
}


def fields_da_big_hunt(player):
    return has_detachment(player, SETTING)


def is_beast_snagga_unit(squad):
    """"BEAST SNAGGA unit" - rule 19.03's any-model reading of the keyword."""
    return attached_units.unit_has_keyword(
        squad, lambda m: getattr(m.profile, "beast_snagga", False)) if squad is not None else False


def applies(squad, target_squad=None):
    """Da Hunt is On for this attacking unit against this target."""
    if squad is None or target_squad is None:
        return False
    if not fields_da_big_hunt(getattr(squad, "owner", None)):
        return False
    return is_beast_snagga_unit(squad) and is_monster_or_vehicle_unit(target_squad)


def adjusted_weapon(weapon, squad, target_squad=None):
    """+1 AP on any weapon of a BEAST SNAGGA unit shooting at or fighting a
    MONSTER/VEHICLE unit. A copy - the shared WeaponProfile instance is never
    mutated."""
    if weapon is None or not applies(squad, target_squad):
        return weapon
    sharpened = copy.copy(weapon)
    sharpened.ap = weapon.ap - DA_HUNT_IS_ON_AP
    return sharpened
