""""While a unit is pinned, subtract 2 from that unit's Move characteristic and
subtract 2 from Charge rolls made for it."

THE 42nd EXTRACTION, at the SECOND source. The status itself and both its
penalties were built for the Night Spinner's Monofilament Web and lived in that
module; the Geomancer's Tectonic Reverberations prints the SAME two sentences,
so the status moved out from under one ability's name (error class 11 - a lying
name is renamed the day a second carrier arrives).

  Monofilament Web (Night Spinner, Aeldari)
    "...until the start of your next turn, that enemy unit is pinned."

  Tectonic Reverberations (Geomancer, Necrons)
    "...Until the start of your next Movement phase that enemy unit is pinned."

WHAT IS SHARED IS THE STATUS AND THE TWO SEAMS. `is_pinned()` is the one
question, and the two penalties are read by game/coldstar.py's
effective_movement_in() and game/charge.py's _capped_roll() - neither of which
has a controller and neither of which should grow one for this.

WHAT DIFFERS IS THE CLOCK, and it is the only thing that does. Both are stored
as the APPLYING PLAYER plus which of that player's boundaries ends the pin:

  * UNTIL_TURN     - cleared when that player's next TURN begins.
  * UNTIL_MOVEMENT - cleared when that player's next MOVEMENT phase begins,
                     one phase later.

The difference is real and small: a unit pinned by the Geomancer is still
pinned through the applying player's Command phase, where a unit pinned by the
Night Spinner is not. Folding the two into one clock would silently shorten the
Geomancer's ability by a phase, which is exactly the half-length-flag mistake
CLAUDE.md's error class 14 is about - so each source names its own clock and
each boundary clears only its own.

PINNED IS NOT SHAKEN, and the difference is one clause: Mont'ka's Pulse
Onslaught applies SHAKEN, which is -2 Move, -2 ADVANCE and -2 Charge. Pinned
says nothing about Advance rolls. Two of the three seams are shared, and the
third is exactly why these are two statuses rather than one flag. They STACK,
deliberately: a unit that is both has two separate printed effects on it.

"CANNOT BE PINNED" (the Stonesinger's ENSNARED status) is enforced where a pin
is APPLIED rather than where it is read, so a unit ensnared AFTER being pinned
keeps the pin it already had - the printed text prevents BECOMING pinned.
"""

from game import elemental_ensnarement

#: "subtract 2 from that unit's Move characteristic" and "subtract 2 from
#: Charge rolls made for it". One pair of numbers for both sources - they print
#: the same two sentences.
PINNED_MOVE_PENALTY = 2
PINNED_CHARGE_PENALTY = 2

#: Which of the applying player's boundaries ends the pin. Named rather than
#: written as bare strings at the call sites, because a typo in one of them is
#: a pin that never expires.
UNTIL_TURN = "turn"
UNTIL_MOVEMENT = "movement"


def is_pinned(squad):
    """The one question both effects ask.

    Stored as an attribute ON THE SQUAD rather than in a controller, unlike the
    enemy MARKS this engine holds per player. The reason is where it is read: a
    mark is read during an ATTACK, where the attacking controller is in scope,
    but these two penalties are read by effective_movement_in() and
    _capped_roll() - neither of which has one."""
    return getattr(squad, "pinned_by_player", None) is not None


def move_penalty_for(squad):
    """-2 to the Move characteristic, read by effective_movement_in()."""
    return PINNED_MOVE_PENALTY if is_pinned(squad) else 0


def charge_penalty_for(squad):
    """-2 on Charge rolls made for this unit. NOT on Advance rolls - that is
    the one clause `shaken` has and `pinned` does not."""
    return PINNED_CHARGE_PENALTY if is_pinned(squad) else 0


def pin(squad, by_player, until=UNTIL_TURN, log=None, label="Pinned"):
    """Apply the status. Returns True if it was newly applied.

    `until` is the applying source's own clock - see the module docstring.
    `log` is a CALLABLE (see CLAUDE.md's two logging conventions); None is
    silent, which is what a headless test wants."""
    if squad is None or is_pinned(squad):
        return False
    if elemental_ensnarement.blocks_pinning(squad):
        if log is not None:
            log("[pinned] %s is ensnared and cannot be pinned." % squad.name,
                file_only=True)
        return False
    squad.pinned_by_player = by_player
    squad.pinned_until = until
    if log is not None:
        log("%s: %s is pinned until the start of %s's next %s "
            "(-%d Move, -%d to Charge rolls)."
            % (label, squad.name, by_player,
               "turn" if until == UNTIL_TURN else "Movement phase",
               PINNED_MOVE_PENALTY, PINNED_CHARGE_PENALTY))
    return True


def clear_at(player, boundary, squads=()):
    """Expire the pins `player` applied that end at THIS boundary.

    Takes the squads explicitly (or the caller walks the board) because the
    status lives on the squads themselves; there is no central registry."""
    cleared = 0
    for squad in squads or ():
        if getattr(squad, "pinned_by_player", None) != player:
            continue
        # Default UNTIL_TURN for anything pinned before this field existed, so
        # a scene restored from an older snapshot still expires.
        if getattr(squad, "pinned_until", UNTIL_TURN) != boundary:
            continue
        squad.pinned_by_player = None
        squad.pinned_until = None
        cleared += 1
    return cleared
