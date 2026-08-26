"""Which DICE a granted re-roll may actually be thrown over.

This engine has two shapes of re-roll offer, and until the Necrons arrived only
one of them had a name:

  FAILURES-OR-WHOLE - the ordinary shape. The ability says "you can re-roll the
  Hit/Wound roll", so the player picks between re-rolling just the failures
  (never a loss) and the whole roll (can lose successes, but is the only way to
  improve a roll whose failures are few). Monster Hunters, [TWIN-LINKED],
  Breach and Clear, Sunforge, Assured Destruction, Storm of Silence.

  ONES-OR-WHOLE - the shape this module names. The ability has TWO clauses:
  an automatic "re-roll a roll of 1", and a conditional "you can re-roll the
  roll INSTEAD". "Instead" makes them alternatives, so the player picks which
  of the two to take and "failures only" is NOT among the options - offering it
  would allow re-rolling a 2 that missed, which none of these abilities permit.

WHY THIS IS A MODULE AND NOT A BOOLEAN COMPARISON. Both attack steps used to
decide this with a literal `reason == swift_demise.SWIFT_DEMISE_LABEL`, because
the Windriders were the only carrier. The Necrons bring four more, and a
hard-coded single value in a place that is really a SET is precisely the bug
CLAUDE.md records twice over - the Fade Back / Path of the Outcast gate, which
compared move_mode against the one string "battle_focus" and let the AI walk
straight over the second ability that needed it.

So the membership test lives here, once, and both the hit step and the wound
step ask it. A future ability with this shape has one place to register, and
the two steps cannot disagree about it.
"""

from game.destroyer_cult import HARD_WIRED_LABEL, WHIRLING_ONSLAUGHT_LABEL
from game.implacable_eradication import IMPLACABLE_ERADICATION_LABEL
from game.protocol_conquering_tyrant import CONQUERING_TYRANT_LABEL
from game.swift_demise import SWIFT_DEMISE_LABEL

#: Every re-roll source whose entitlement is "the 1s, OR the whole roll".
#: A source NOT listed here gets the ordinary failures-or-whole offer.
ONES_OR_WHOLE_LABELS = frozenset({
    SWIFT_DEMISE_LABEL,                 # Windriders (hit)
    HARD_WIRED_LABEL,                   # Lokhust Destroyers (hit)
    WHIRLING_ONSLAUGHT_LABEL,           # Skorpekh Destroyers (hit)
    IMPLACABLE_ERADICATION_LABEL,       # Immortals (wound)
    CONQUERING_TYRANT_LABEL,            # Awakened Dynasty Stratagem (hit)
})


def is_ones_or_whole(reason):
    """Whether `reason` (a re-roll source's label) grants the two-alternative
    shape rather than the ordinary failures-or-whole choice."""
    return reason in ONES_OR_WHOLE_LABELS
