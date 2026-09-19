"""Ghazghkull Thraka's Da Grand Warlord's Ladz (2026-09 Ork codex, Mecha Orks
stage G2).

RULE (verbatim, rules/orks/Ghazghkull Thraka.md):
  "Da Grand Warlord's Ladz: While this unit is within 3" of another friendly ORKS
   INFANTRY unit, this unit has Lone Operative."

THE SIXTH conditional LONE OPERATIVE, and the shape game/conditional_lone_
operative.py was extracted for: registered there as one more (predicate, range)
pair, so status_effects.lone_operative_range() needs no new branch. Rule 24.24's
default range (12") - the text prints none.

"ANOTHER" does the work Illuminor's "other" does: Ghazghkull's own unit does not
count, and for a one-model unit it would otherwise make the ability permanent.
"ORKS INFANTRY" is the `orks` flag plus INFANTRY, on at least one living model of
that unit; measured edge to edge with Squad.min_distance_to(). Ghazghkull prints
no Leader section, so rule 24.24's "unless part of an attached unit" never bites.
"""

GRAND_WARLORDS_LADZ_RANGE_IN = 3.0
#: Rule 24.24's default X for a granted Lone Operative with no printed number.
GRAND_WARLORDS_LADZ_LONE_OPERATIVE_RANGE_IN = 12


def has_ability(squad):
    return squad is not None and any(getattr(m.profile, "da_grand_warlords_ladz", False)
                                     for m in squad.models if not m.is_dead())


def _is_orks_infantry(squad):
    return any(getattr(m.profile, "orks", False) and getattr(m.profile, "infantry", False)
               for m in squad.models if not m.is_dead())


def grants_lone_operative(squad, all_tokens=()):
    """Registered in game/conditional_lone_operative.py."""
    if not has_ability(squad):
        return False
    seen = set()
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other is squad or id(other) in seen or token.is_dead():
            continue
        if other.owner != squad.owner:
            continue
        seen.add(id(other))
        if _is_orks_infantry(other) and squad.min_distance_to(other) <= GRAND_WARLORDS_LADZ_RANGE_IN:
            return True
    return False
