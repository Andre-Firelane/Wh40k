"""The Clanblade's "Blade of the Clans" - a datasheet ability.

RULE (printed, word for word):
  "This unit's melee attacks have [Sustained Hits 1]."

THE THIRD GRANT OF THIS EXACT KEYWORD, and the simplest of them: no leader
clause, no range, no round window. Ritual Butchery (Kroot War Shaper) and
United In Destruction (Skorpekh Lord) are the other two, and all three sit in
FightController._adjusted_weapon() for the same reason - _crit_note() has to
know at ROLL time whether a critical die is a [SUSTAINED HITS] one.

"THIS UNIT'S" - so unlike the other two it is NOT gated on leading anything; it
is a property of whatever unit the Clanblade is part of. 19.04's any() shape is
the right reading: a Clanblade attached to Dragon Knights makes it that unit's
ability too, which is exactly what the Leader line is for.

NEVER A DOWNGRADE: "have the [SUSTAINED HITS 1] ability" GRANTS it, it does not
set the value - so a weapon printing a higher X keeps it. The same guard its two
siblings carry, and the Clanblade's own Moonblades print no [SUSTAINED HITS] at
all, so the case is real rather than hypothetical the moment a stronger melee
weapon joins the unit.
"""
import copy

BLADE_OF_THE_CLANS_LABEL = "Blade of the Clans"


def applies(squad):
    """Any living model in the unit printing it, per 19.04."""
    if squad is None:
        return False
    return any(getattr(m.profile, "blade_of_the_clans", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def adjusted_weapon(weapon, squad):
    """A copy with [SUSTAINED HITS 1], or the SAME OBJECT untouched."""
    if weapon is None or not applies(squad):
        return weapon
    if getattr(weapon, "sustained_hits", 0) >= 1:
        return weapon
    adjusted = copy.copy(weapon)
    adjusted.sustained_hits = 1
    return adjusted
