"""The Awakened Dynasty detachment: its rule, and the predicates its six
Stratagems share.

DETACHMENT RULE - Command Protocols (printed, word for word):
  "While a NECRONS CHARACTER model is leading this unit, each time a model in
   this unit makes an attack, add 1 to the Hit roll."

A HIT MODIFIER, so it belongs in _hit_modifiers() in BOTH attack steps -
"makes an attack", not "a ranged attack". Its sign is NEGATIVE: game/modifiers.py's
convention is that a Modifier adjusts the THRESHOLD a die must beat, and "add 1
to the Hit roll" makes that easier, i.e. lowers it. Getting the sign backwards
would hand the whole army a permanent penalty, which is why it is stated here
rather than left to the reader of a bare `-1`.

WHY THE PREDICATES LIVE HERE and not one per Stratagem module: all six protocols
open with "One NECRONS unit from your army", and five of them have a "if a
NECRONS CHARACTER is leading your unit" clause on top. Six copies of those two
tests is exactly the drift this repo keeps consolidating away, and the leader
half in particular is easy to get wrong (see leader_ability()'s own docstring on
why unit_wide_ability() is the WRONG helper for a leader clause).

WHOSE ARMY HAS THE DETACHMENT cannot be derived from the units - a detachment
is a list-building declaration, and a Necron unit looks identical whichever
detachment it was taken in. So it is config.AWAKENED_DYNASTY_PLAYERS, exactly
as game/strands_of_fate.py's own docstring reasons about SEER_COUNCIL_PLAYERS.
"""

from game import config
from game.attached_units import leader_ability
from game.factions.faction import faction_keyword_of

NECRONS_KEYWORD = "NECRONS"
#: Negative because game/modifiers.py adjusts the THRESHOLD - see the module
#: docstring. "Add 1 to the Hit roll" makes the roll easier to pass.
COMMAND_PROTOCOLS_HIT_BONUS = -1
COMMAND_PROTOCOLS_LABEL = "Command Protocols"


def is_necrons_unit(squad):
    """"One NECRONS unit from your army".

    Read off the DATASHEET's faction rather than off a per-model flag: that is
    what the keyword actually is, and it keeps working for a unit whose models
    all happen to lack any particular ability."""
    if squad is None:
        return False
    return faction_keyword_of(squad) == NECRONS_KEYWORD


def has_detachment(player):
    """Whether this player's army is an Awakened Dynasty one."""
    return player in tuple(getattr(config, "AWAKENED_DYNASTY_PLAYERS", ()) or ())


def is_led_by_character(squad):
    """"While a NECRONS CHARACTER model is leading this unit".

    leader_ability() is the right helper and unit_wide_ability() is not: the
    latter asks whether EVERY model prints the thing, and for a leader clause
    none of the bodyguards do. It also requires a REAL attached unit (19.01)
    rather than merely a squad containing a character, and brings 19.04's
    grace window with it, so a leader killed mid-sequence does not silently
    shrink the rest of his unit's attacks."""
    return leader_ability(squad, "character")


def command_protocols_applies(squad):
    """The detachment rule's full condition."""
    if squad is None or not has_detachment(squad.owner):
        return False
    return is_necrons_unit(squad) and is_led_by_character(squad)


def hit_modifiers(squad):
    """The Modifier list the two attack steps extend with. Empty unless the
    rule applies, so both call sites can extend unconditionally."""
    from game.modifiers import Modifier
    if not command_protocols_applies(squad):
        return []
    return [Modifier(COMMAND_PROTOCOLS_HIT_BONUS, COMMAND_PROTOCOLS_LABEL)]


def stratagem_target_ok(squad, player=None):
    """The TARGET line all six protocols share: a NECRONS unit from an army
    that actually has this detachment, optionally checked as belonging to a
    given player."""
    if squad is None or not is_necrons_unit(squad):
        return False
    if not has_detachment(squad.owner):
        return False
    return player is None or squad.owner == player
