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
  of the two to take - and because the base clause is MANDATORY, "keep result"
  is not a legal answer while a 1 is on the table. That is the whole of what
  membership here decides.

WHAT IT DOES *NOT* DECIDE, AND THE READING THAT WAS WRONG.

This module used to add "...and 'failures only' is NOT among the options -
offering it would allow re-rolling a 2 that missed, which none of these
abilities permit", and both attack steps suppressed that option on the
strength of it. User report: "Fireknife kann all failed hits rerollen, wenn
Gegner noch volles Leben hat. das wurde mir nicht angeboten."

The report is right, and the printed text says so three times over:

  * The clause is scoped PER ATTACK - "Each time a model in this unit makes a
    ranged attack ... you can re-roll the Hit roll instead" - and one attack's
    Hit roll is ONE DIE. game/protocol_conquering_tyrant.py quotes its own
    datasheet as "you can re-roll the Hit roll FOR THAT ATTACK instead", which
    is the same sentence with the scope spelled out. The pooled roll this
    engine throws is a convenience of the engine, not a unit of the rule.

  * So the permission is per die, and re-rolling FEWER dice than allowed is a
    voluntary forbearance, not an illegal extra. game/shooting.py's own wound
    step had already written this down, four lines below the suppression it
    contradicted: "'You CAN re-roll the Wound roll' permits re-rolling any
    subset of it, and re-rolling only the failures is the subset a player
    almost always wants - throwing successes away is a cost, not a bonus."

  * Which made this one printed sentence carry two readings in one file. On
    the reported roll the player took the only option offered - the whole roll
    - and went from 6 hits to 5.

The failures-only option is therefore offered by every source, in both steps.
What remains ONES-OR-WHOLE about these seven is the mandatory 1s: they replace
"Keep result" with "Re-roll the 1s only", because declining outright is not
something their text allows.

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
from game.fireknife import FIREKNIFE_LABEL
from game.implacable_eradication import IMPLACABLE_ERADICATION_LABEL
from game.protocol_conquering_tyrant import CONQUERING_TYRANT_LABEL
from game.reavers_of_the_void import REAVERS_OF_THE_VOID_LABEL
from game.swift_demise import SWIFT_DEMISE_LABEL

#: Every re-roll source whose base clause is a MANDATORY re-roll of the 1s, so
#: that "keep result" is not among its answers. A source NOT listed here offers
#: "keep result" instead. Both kinds offer failures-only and the whole roll -
#: see the module docstring for the reading that used to say otherwise.
ONES_OR_WHOLE_LABELS = frozenset({
    SWIFT_DEMISE_LABEL,                 # Windriders (hit)
    HARD_WIRED_LABEL,                   # Lokhust Destroyers (hit)
    WHIRLING_ONSLAUGHT_LABEL,           # Skorpekh Destroyers (hit)
    IMPLACABLE_ERADICATION_LABEL,       # Immortals (wound)
    CONQUERING_TYRANT_LABEL,            # Awakened Dynasty Stratagem (hit)
    FIREKNIFE_LABEL,                    # Crisis Fireknife Battlesuits (hit)
    REAVERS_OF_THE_VOID_LABEL,          # Corsair Voidreavers (hit)
})


def is_ones_or_whole(reason):
    """Whether `reason` (a re-roll source's label) has the mandatory-1s clause,
    so its offer ends in "Re-roll the 1s only" rather than "Keep result"."""
    return reason in ONES_OR_WHOLE_LABELS
