"""Kroot Hounds' "Loping Pounce".

RULE (printed, word for word):
  "At the start of your Command phase, if this unit is within 6" of one or more
   friendly KROOT INFANTRY units, then until the end of the turn, this unit is
   eligible to declare a charge in a turn in which it Advanced."

THE THIRD SOURCE OF THE SAME EXCEPTION, after the Orks army rule Waaagh! and
Warbikers' Full Throttle - so it is read at the same gate in
game/charge.py's can_declare_charge(), next to those two, rather than anywhere
new.

WHAT MAKES IT DIFFERENT FROM BOTH IS THAT IT IS LATCHED. Waaagh! and Full
Throttle are live predicates, answered afresh on every charge declaration.
This one is checked ONCE, at the start of the Command phase, and then holds
"until the end of the turn" whatever happens afterwards - the hounds may run
away from the Kroot they were standing next to and still pounce. So it is a
flag on the Squad, set at that instant and cleared at end of turn, exactly the
arrangement 'Ard as Nails uses and for the same reason
status_effects.targeting_range_limit() gives: a live distance test would answer
a different question than the printed one.

"FRIENDLY KROOT INFANTRY UNITS" - both keywords, and INFANTRY is the half that
does the work: the Krootox (MOUNTED) and the Lone-Spear (MOUNTED) do not
qualify, nor do the hounds themselves, which are BEASTS. On the current roster
that leaves the Carnivores, the Farstalkers and the three Shapers.

MEASURED EDGE TO EDGE, like every range in this engine, and satisfied by any
one model of either unit being in range - "this unit is within 6" of one or
more friendly units" is a unit-to-unit test.
"""

from game.squad import edge_distance

LOPING_POUNCE_RANGE_IN = 6.0


def unit_has_loping_pounce(squad):
    """Read live off the living models."""
    if squad is None:
        return False
    return any(getattr(m.profile, "loping_pounce", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def is_kroot_infantry(squad):
    """Both keywords, on the same model - a KROOT unit that is not INFANTRY
    (the Krootox, the Lone-Spear) does not qualify, and neither does an
    INFANTRY unit that is not KROOT."""
    if squad is None:
        return False
    return any(getattr(m.profile, "kroot", False) and getattr(m.profile, "infantry", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def near_kroot_infantry(squad, all_squads):
    """Whether a friendly KROOT INFANTRY unit is within 6"."""
    if squad is None:
        return False
    for other in all_squads or ():
        if other is squad or other.owner != squad.owner or not is_kroot_infantry(other):
            continue
        for mine in getattr(squad, "models", ()) or ():
            if mine.is_dead():
                continue
            for theirs in getattr(other, "models", ()) or ():
                if not theirs.is_dead() and edge_distance(mine, theirs) <= LOPING_POUNCE_RANGE_IN:
                    return True
    return False


def begin_command_phase(squads, player, game_log=None):
    """"At the start of your Command phase" - checked once, for every unit of
    `player` with the ability, and latched onto the squad.

    Returns the units that got it, which is what the test reads."""
    granted = []
    for squad in sorted((s for s in squads if s.owner == player), key=lambda s: s.name):
        if not unit_has_loping_pounce(squad):
            continue
        if near_kroot_infantry(squad, squads):
            squad.loping_pounce_active = True
            granted.append(squad)
            if game_log:
                game_log.add(
                    f"[loping pounce] {squad.name} may declare a charge after Advancing "
                    f"this turn", file_only=True)
    return granted


def reset_turn(squads):
    """"Until the end of the turn" - cleared on the same seam as every other
    end-of-turn state in main.py."""
    for squad in squads or ():
        squad.loping_pounce_active = False


def is_active(squad):
    """What game/charge.py's can_declare_charge() asks.

    The flag AND a living bearer: a unit whose last hound died mid-turn is not
    a Kroot Hounds unit any more, and every other ability in this batch ends
    with its model."""
    return bool(getattr(squad, "loping_pounce_active", False)) and unit_has_loping_pounce(squad)
