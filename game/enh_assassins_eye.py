"""Path of the Outcast Enhancement: Assassins' Eye (15 pts).

RULE (verbatim, rules/aeldari/detachments/Path of the Outcast.md):
  "RANGERS/SHROUD RUNNERS unit only. This unit's ranged attacks that target a
  CHARACTER unit have +1 AP."

A UNIT-LEVEL ENHANCEMENT, one of exactly two in this batch. "RANGERS/SHROUD
RUNNERS UNIT only" names a unit rather than a model, so the registry marks
every model (`unit_level=True`) and "a living model still has it" comes to mean
"the unit still exists" - which is the right lifetime for a rule that says
"this unit's ranged attacks".

"+1 AP" IS ap - 1. AP is printed as a negative number, so improving it makes it
MORE negative - the same arithmetic game/crit_ap.py, Crystalline Targeting and
Focused Firepower all write out, and the one line here that would still pass a
"the AP changed" test while doing the exact opposite of the printed text.

CONDITIONAL ON THE TARGET, not on the phase: "attacks that target a CHARACTER
unit". So it rides the adjuster chain, which already carries the target, and
the same unit shooting at a non-character gets nothing. That is the difference
between this and a plain per-phase buff, and it has its own test line.

"A CHARACTER UNIT" IS 19.03's POOLING - any model with the keyword makes the
unit one, which is how a merged bodyguard unit shields its leader in this
engine and exactly why the printed text says "unit" rather than "model".
attached_units.unit_has_keyword() is that question; asked of the TARGET.

RANGED ONLY, as printed. Neither datasheet has a melee attack worth the words,
but the clause is checked rather than assumed - game/fight.py never importing
this module is the stronger statement, and it is pinned that way.
"""
import copy

from game import attached_units, enhancements
from game.weapons import RANGED

ASSASSINS_EYE = "Assassins' Eye"

#: "+1 AP" - an IMPROVEMENT, so ap - 1.
ASSASSINS_EYE_AP_BONUS = 1


def target_is_character(target_squad):
    """19.03's pooling: any model with the keyword makes it a CHARACTER unit."""
    if target_squad is None:
        return False
    # The predicate takes a MODEL, not a profile - the same shape every other
    # caller of unit_has_keyword() uses.
    return attached_units.unit_has_keyword(
        target_squad, lambda m: getattr(m.profile, "character", False))


def applies(squad, target_squad):
    return (enhancements.is_active(squad, ASSASSINS_EYE)
            and target_is_character(target_squad))


def adjusted_weapon(weapon, squad, target_squad):
    """+1 AP against a CHARACTER unit. A COPY, never the shared instance."""
    if weapon is None or getattr(weapon, "weapon_type", None) != RANGED:
        return weapon
    if not applies(squad, target_squad):
        return weapon
    improved = copy.copy(weapon)
    improved.ap = weapon.ap - ASSASSINS_EYE_AP_BONUS
    return improved
