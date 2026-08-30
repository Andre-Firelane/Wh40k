"""The Daemon Prince of Nurgle's own ability "Death Guard Defenders".

RULE (printed, word for word):

  "While this model is within 3" of one or more friendly DEATH GUARD INFANTRY
  units, this model has the Lone Operative ability."

A CONDITIONAL FORM of UnitProfile.lone_operative, so it cannot be a printed
value on the profile and has to be resolved at read time. That is exactly the
shape game/illuminor.py already has for Illuminor Szeras, and this module is
written to plug into the SAME place: status_effects.lone_operative_range()'s
optional all_tokens argument. Two conditional granters, one seam.

WHY THIS MATTERS MORE THAN IT LOOKS: the Daemon Prince has no LEADER line at
all, so it can never hide inside a bodyguard unit the way every other character
in this list does. Lone Operative (24.24) is its entire protection, and it is
switched on by standing near the infantry it fights alongside - which is also
why the ability is not simply always-on.

"DEATH GUARD INFANTRY" is both keywords: the army rule flag (which every Death
Guard model prints) AND the INFANTRY keyword. Checked separately rather than
collapsed, because this faction's vehicles and beasts carry the first and not
the second, and they must not switch the ability on.
"""

DEATH_GUARD_DEFENDERS_RANGE_IN = 3.0
#: Rule 24.24's default range, the same value game/status_effects.py uses when
#: an ability is granted without naming its own X".
DEATH_GUARD_DEFENDERS_LONE_OPERATIVE_RANGE_IN = 12.0


def _is_death_guard_infantry(squad):
    return any(getattr(m.profile, "nurgles_gift", False)
               and getattr(m.profile, "infantry", False)
               and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


def grants_lone_operative(squad, all_tokens=()):
    """Whether `squad` currently has Lone Operative from this ability.

    Same signature and same contract as illuminor.grants_lone_operative(), so
    game/status_effects.py can ask both the same way."""
    if squad is None:
        return False
    if not any(getattr(m.profile, "death_guard_defenders", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ()):
        return False
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other is squad or token.is_dead():
            continue
        if other.owner != squad.owner:
            continue           # "friendly"
        if not _is_death_guard_infantry(other):
            continue
        if squad.min_distance_to(other) <= DEATH_GUARD_DEFENDERS_RANGE_IN:
            return True
    return False
