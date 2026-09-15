"""War Horde Enhancement: Headwoppa's Killchoppa (15 pts).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  "ORKS model only. If this unit made a charge move this turn, this model's
   melee attacks have +1 AP."

TWO SUBJECTS IN ONE SENTENCE. "This UNIT made a charge move" is asked of the
bearer's unit - Squad.charged_this_turn, rule 11.04's own flag, not
fights_first (Counteroffensive sets that one too). "This MODEL's melee attacks"
is the bearer alone. After a 19.01 merge the bearer is one model of many, so
game/fight.py's _melee_attack_key() carries attack_key() below: without it the
one-representative shortcut would hand +1 AP to whichever group the bearer
shares - the term Aspect of Murder's docstring already counts four of.

MELEE ONLY, so it lives in game/fight.py's chain and nowhere else. "+1 AP" is
one MORE negative, as everywhere in this engine.
"""

import copy

from game import enhancements
from game.weapons import MELEE

HEADWOPPAS_KILLCHOPPA = "Headwoppa's Killchoppa"
#: "+1 AP".
HEADWOPPAS_KILLCHOPPA_AP = 1


def is_bearer(model):
    """A living bearer whose owner fields War Horde."""
    return model is not None and enhancements.model_is_active(model, HEADWOPPAS_KILLCHOPPA)


def attack_key(model):
    """The per-model term for _melee_attack_key(): True for the bearer only, so
    no group that existed before splits."""
    return bool(is_bearer(model))


def adjusted_weapon(weapon, model):
    """+1 AP on the bearer's melee weapons, once its unit has charged this turn.
    A copy - a WeaponProfile instance is never mutated."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE:
        return weapon
    if not is_bearer(model):
        return weapon
    if not getattr(getattr(model, "squad", None), "charged_this_turn", False):
        return weapon
    granted = copy.copy(weapon)
    granted.ap = weapon.ap - HEADWOPPAS_KILLCHOPPA_AP
    return granted
