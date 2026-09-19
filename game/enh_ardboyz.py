"""Green Tide Enhancement: 'Ardboyz (25 pts, Mecha Orks stage G3).

RULE (verbatim, rules/orks/detachments/Green Tide.md):
  "'Ardboyz - 25 pts. BOYZ unit only. This unit has 4+ Sv."

A UNIT-LEVEL Enhancement (game/enhancements.py's unit_level=True, the shape of
the T'au "STEALTH BATTLESUITS unit only" ones): no CHARACTER bears it, the Boyz
unit does. army_roster grants Enhancements BEFORE rule 19.01's attach(), so the
flag lands on the Boyz models and never on a Warboss who joins them later.

"THIS UNIT HAS 4+ Sv" after a 19.01 merge is read the way this engine reads
every ability of an attached unit's component (rule 19.04,
squad.unit_wide_ability()): it applies to every model of the attached unit for
as long as its source - a living Boyz model - is there. enhancements.is_active()
answers exactly that (a living bearer and the detachment). A joined Painboy or
Weirdboy (both 5+) therefore has a 4+ while his mob stands; a Warboss or Bigboss
(both 4+) is unchanged.

A REPLACEMENT, not a modifier: "has 4+ Sv" is the characteristic, so it is one
of game/save_characteristic.py's overrides and every reader of the Save
characteristic sees it - the roll, the dice panel, the allocation order, the AI
estimates and observation, and the datacard. No model that can join a BOYZ
unit has a better save than 4+, so the literal replacement never worsens one.
"""

from game import enhancements

ARDBOYZ = "'Ardboyz"
#: "This unit has 4+ Sv."
ARDBOYZ_SAVE = "4+"


def applies(squad):
    return squad is not None and enhancements.is_active(squad, ARDBOYZ)


def save_override(model):
    """game/save_characteristic.py's override for `model`, or None."""
    if model is None:
        return None
    return ARDBOYZ_SAVE if applies(getattr(model, "squad", None)) else None
