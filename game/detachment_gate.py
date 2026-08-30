"""Does this player field that detachment? The question, with no faction in it.

WHY THIS MODULE EXISTS
----------------------
This function lived in game/tau_detachments.py, and that was fine while T'au
were the only faction with more than one detachment: every caller was a T'au
rule, so a T'au-named home read as accurate. It never was, though - the body
reads one game/config.py constant and knows nothing about any faction:

    return player in tuple(getattr(config, setting, ()) or ())

The seven Aeldari detachment rules are the first non-T'au callers, which makes
this the same lying name game/tau_detachments.py itself records for
is_tau_unit() (it came out of game/retaliation_cadre.py, a DETACHMENT module
answering a FACTION question) and the same second-consumer rule that produced
game/weapon_range.py, game/detection_range.py and the twenty extractions before
them.

game/tau_detachments.py re-exports it, so there is still exactly ONE
definition and its dozen existing callers did not have to move. The test pins
that the two names are the same object rather than two copies that agree today.

WHO WRITES THE CONSTANT is game/detachments.py, and only it - from scratch on
every apply_to_config(), so switching army list cannot leave a stale
detachment live. A rule that gates on a constant nobody writes is inert and
looks correct from the inside, which is why every detachment rule's test also
checks its setting is one game/detachments.py actually knows about.
"""

from game import config


def has_detachment(player, setting):
    """Whether `player` fields the detachment whose config constant is
    `setting` - the name game/detachments.py wrote it under.

    A missing constant reads as "not fielded" rather than raising: that is the
    safe direction for a detachment rule, since it withholds a bonus instead of
    inventing one, and it keeps a half-configured test harness from crashing on
    a rule it never meant to exercise."""
    if player is None:
        return False
    return player in tuple(getattr(config, setting, ()) or ())
