"""Ghazghkull Thraka's Prophet of da Great Waaagh! (2026-09 Ork codex, Mecha Orks
stage G2).

RULE (verbatim, rules/orks/Ghazghkull Thraka.md):
  "Prophet of da Great Waaagh! (Aura): While a friendly ORKS unit is within 6" of
   this unit, that unit's melee attacks have:
   - +1 to hit rolls.
   - +1 to wound rolls."

AN AURA, read the way Shadowsun's Hero of the Empire is (game/hero_of_the_empire.py):
a distance from a model in what is usually a THIRD unit, measured edge to edge
from HIS model, and satisfied by any one model of the friendly unit being inside -
the aura affects the unit. His own unit is a friendly ORKS unit at distance 0, so
he benefits himself; "not the bearer's own unit" is the obvious wrong guess.

MELEE ONLY, so only game/fight.py asks - its _hit_modifiers() and
_wound_modifiers(), both players' Fight phases. Two ROLL modifiers ("+1 to hit
rolls", "+1 to wound rolls"), so game/modifiers.py's +/-1 cap folds them with
every other hit/wound modifier on the attack (a Beastboss's Dodge Dis! beside it
still nets +1).

"FRIENDLY ORKS UNIT" is the `orks` flag on a living model of the attacking unit.
"""

from game.modifiers import Modifier
from game.squad import edge_distance

PROPHET_NAME = "Prophet of da Great Waaagh!"
PROPHET_RANGE_IN = 6.0


def bearers(all_tokens, owner):
    return [t for t in all_tokens or ()
            if not t.is_dead() and getattr(t.profile, "prophet_of_da_great_waaagh", False)
            and getattr(getattr(t, "squad", None), "owner", None) == owner]


def applies(attacking_squad, all_tokens):
    """Whether this unit is inside a Prophet aura right now."""
    if attacking_squad is None or not all_tokens:
        return False
    models = [m for m in getattr(attacking_squad, "models", ()) or () if not m.is_dead()]
    if not any(getattr(m.profile, "orks", False) for m in models):
        return False
    for bearer in bearers(all_tokens, attacking_squad.owner):
        for model in models:
            if edge_distance(bearer, model) <= PROPHET_RANGE_IN:
                return True
    return False


def hit_modifiers(attacking_squad, all_tokens):
    """+1 to hit (-1 on the threshold) for a melee attack inside the aura."""
    return [Modifier(-1, PROPHET_NAME)] if applies(attacking_squad, all_tokens) else []


def wound_modifiers(attacking_squad, all_tokens):
    """+1 to wound (-1 on the threshold) for a melee attack inside the aura."""
    return [Modifier(-1, PROPHET_NAME)] if applies(attacking_squad, all_tokens) else []
