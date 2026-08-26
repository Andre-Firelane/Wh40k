"""Illuminor Szeras's "Illuminor".

RULE (printed, word for word):
  "While this model is within 3" of one or more other friendly NECRONS units,
   this model has the Lone Operative ability."

A CONDITIONAL CORE ABILITY, which is what makes it worth its own module rather
than a flag. Every other Lone Operative in this engine is printed on the
datasheet and is simply true; this one switches on and off as the board moves,
so game/status_effects.py's lone_operative_range() has to be able to ASK rather
than read a static value.

"ONE OR MORE OTHER FRIENDLY NECRONS UNITS" - the word doing the work is OTHER.
His own unit does not count, which for a single-model unit would otherwise make
the condition trivially true and the ability unconditional. Measured edge to
edge with the same Squad.min_distance_to() every other range test here uses.

WHY IT IS BACKWARDS FROM THE USUAL LONE OPERATIVE. The core ability protects a
lone character; this one only works while he is standing WITH the army, which
reads oddly until you notice it is a bodyguard rule expressed from the other
side - he is hard to shoot at precisely because there are Necrons around him.
Nothing in the implementation depends on that reading; it is recorded so the
condition is not "corrected" later by someone who expects the usual shape.
"""

ILLUMINOR_RANGE_IN = 3.0
#: Rule 24.24's default X for a granted Lone Operative with no printed number.
ILLUMINOR_LONE_OPERATIVE_RANGE_IN = 12


def has_illuminor(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "illuminor", False)
               for m in squad.models if not m.is_dead())


def _friendly_necron_squads(squad, all_tokens):
    """Every OTHER friendly NECRONS unit currently on the board."""
    seen = {}
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other is squad or token.is_dead():
            continue
        if other.owner != squad.owner:
            continue
        if not any(getattr(m.profile, "reanimation_protocols", False)
                   for m in other.models if not m.is_dead()):
            continue  # the NECRONS faction test: the army rule is on every Necron datasheet
        seen[id(other)] = other
    return list(seen.values())


def grants_lone_operative(squad, all_tokens=()):
    """Whether the condition currently holds."""
    if not has_illuminor(squad):
        return False
    for other in _friendly_necron_squads(squad, all_tokens):
        if squad.min_distance_to(other) <= ILLUMINOR_RANGE_IN:
            return True
    return False
