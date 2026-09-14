"""Orks detachment rule: War Horde's Get Stuck In (2026-09 codex).

PRINTED (rules/orks/detachments/War Horde.md):

    Get Stuck In: Friendly ORKS units' melee attacks have [Sustained Hits 1].

GATED ON THE DETACHMENT. Until the 2026-09 codex this applied to every model
with the `orks` UnitProfile flag, with no "is this army running War Horde"
check, because War Horde was the only Ork detachment modelled and there was no
army list to declare anything. Neither is true any more: Wahapedia prints 15 Ork
detachments, and a list declares its own (game/detachments.py writes
config.WAR_HORDE_PLAYERS from it). So the rule asks the one gate every other
detachment rule asks, game/detachment_gate.py's has_detachment().

The Enhancements are game/enh_headwoppas_killchoppa.py and its three siblings;
the six Stratagems are game/horde_*.py.
"""

import copy

from game.detachment_gate import has_detachment
from game.weapons import MELEE

#: The config constant game/detachments.py writes for this detachment.
SETTING = "WAR_HORDE_PLAYERS"
GET_STUCK_IN_SUSTAINED_HITS = 1


def fields_war_horde(player):
    return has_detachment(player, SETTING)


def is_orks_unit(squad):
    """"Friendly ORKS units" - read off the models' `orks` flag, which every Ork
    UnitProfile sets (there is no per-model faction tracking to read instead)."""
    return bool(squad is not None and any(
        getattr(m.profile, "orks", False) for m in getattr(squad, "models", ()) or ()))


def get_stuck_in_adjusted_weapon(weapon, pairs):
    """[SUSTAINED HITS 1] on the group's melee weapons, as a copy so the shared
    WeaponProfile instance is never mutated. A GRANT, not a set: a weapon that
    already has a higher value keeps it.

    Decided from the group's representative fighter (pairs[0][0]), the same
    simplification every other army-rule adjuster in the fight chain uses."""
    if weapon.weapon_type != MELEE:
        return weapon
    fighter_model = pairs[0][0] if pairs else None
    if fighter_model is None or not fighter_model.profile.orks:
        return weapon
    squad = getattr(fighter_model, "squad", None)
    if not fields_war_horde(getattr(squad, "owner", None)):
        return weapon
    if weapon.sustained_hits >= GET_STUCK_IN_SUSTAINED_HITS:
        return weapon
    boosted = copy.copy(weapon)
    boosted.sustained_hits = GET_STUCK_IN_SUSTAINED_HITS
    return boosted
