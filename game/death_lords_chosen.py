"""The Death Guard detachment "Death Lord's Chosen": the predicates its rule
and its six Stratagems share.

The detachment RULE itself - Deadly Vectors - lives in game/deadly_vectors.py,
because unlike Awakened Dynasty's Command Protocols it is not a modifier but a
whole roll-and-resolve cycle with a queue and two dice steps. This module is
the part that is genuinely shared: who has the detachment, and what its
Stratagems may target.

WHY THE PREDICATES LIVE HERE and not one per Stratagem module: five of the six
Death Lord's Chosen Stratagems open with "One TERMINATOR unit from your army"
and the sixth with "One LORD OF VIRULENCE model from your army". Six copies of
"is this mine, is it Death Guard, does my army even have this detachment" is
exactly the drift this repo keeps consolidating away - the same reasoning
game/awakened_dynasty.py records for its own six.

WHOSE ARMY HAS THE DETACHMENT cannot be derived from the units: a detachment is
a list-building declaration, and a Plague Marine looks identical whichever
detachment it was taken in. So it is config.DEATH_LORDS_CHOSEN_PLAYERS, written
at startup by army_lists.apply_to_config().

Contrast that with the ARMY rule sitting next to it: Nurgle's Gift IS derivable
from the units (every Death Guard datasheet prints it), so
nurgles_gift.qualifying_players() reads the board instead. Two rules of the
same faction, two different sources, for a reason that is worth stating rather
than discovering.
"""

from game import config
from game import nurgles_gift
from game.factions.faction import faction_keyword_of

DEATH_GUARD_KEYWORD = "DEATH GUARD"
TERMINATOR_KEYWORD = "TERMINATOR"
LORD_OF_VIRULENCE_KEYWORD = "LORD OF VIRULENCE"


def is_death_guard_unit(squad):
    """"One ... unit from your army", where your army is Death Guard.

    Read off the DATASHEET's faction keyword, which is what the keyword
    actually is - the same primary source game/awakened_dynasty.py's
    is_necrons_unit() uses.

    The fallback to the army rule is a DEGRADATION for a squad built without a
    datasheet (a hand-built test squad, which has no faction to read), not a
    second opinion: Nurgle's Gift is printed on every Death Guard datasheet
    and on nothing else, so the two can only ever agree. game/squad.py's own
    attached_unit_toughness() documents the same kind of fallback for the same
    kind of squad."""
    if squad is None:
        return False
    if faction_keyword_of(squad) == DEATH_GUARD_KEYWORD:
        return True
    return getattr(squad, "datasheet", None) is None and nurgles_gift.has_nurgles_gift(squad)


def has_detachment(player):
    """Whether this player's army is a Death Lord's Chosen one."""
    return player in tuple(getattr(config, "DEATH_LORDS_CHOSEN_PLAYERS", ()) or ())


def detachment_players():
    """Every player fielding this detachment, sorted. Used by Deadly Vectors,
    which has to find the Death Guard player from the OTHER player's Command
    phase and so cannot simply ask about a unit."""
    return sorted(tuple(getattr(config, "DEATH_LORDS_CHOSEN_PLAYERS", ()) or ()))


def _has_datasheet_keyword(squad, keyword):
    sheet = getattr(squad, "datasheet", None)
    if sheet is None:
        return False
    return keyword in (getattr(sheet, "keywords", ()) or ())


def is_terminator_unit(squad):
    """"One TERMINATOR unit from your army" - the TARGET line of five of the
    six Stratagems.

    A datasheet keyword rather than a UnitProfile flag, read the same way
    game/mechanical_augmentation.py reads BATTLELINE. Under rule 19.01 an
    attached unit keeps its bodyguard unit's datasheet, and 19.03 pools
    keywords with any() - so Typhus (himself a TERMINATOR) leading Deathshroud
    Terminators is one TERMINATOR unit however the merge went, which is what
    makes the datasheet the right place to ask."""
    return _has_datasheet_keyword(squad, TERMINATOR_KEYWORD)


def is_lord_of_virulence_unit(squad):
    """"One LORD OF VIRULENCE model from your army" - Signal Pox's TARGET.

    NOTE, and it is deliberate: no datasheet in the Death Guard list this
    engine fields carries this keyword. Signal Pox is therefore a documented
    NO-OP for the current roster - the same status as the AIRCRAFT/
    FORTIFICATION/TITANIC clauses game/actions.py and game/rapid_ingress.py
    write out. It is implemented rather than skipped so that adding a Lord of
    Virulence later is one datasheet and no rules work, and
    test_death_guard_stratagems.py pins the emptiness so that day is a visible
    change rather than a silent one."""
    return _has_datasheet_keyword(squad, LORD_OF_VIRULENCE_KEYWORD)


def stratagem_target_ok(squad, player=None):
    """The TARGET line all six Stratagems share: a Death Guard unit from an
    army that actually has this detachment, optionally checked as belonging to
    a given player."""
    if squad is None or not is_death_guard_unit(squad):
        return False
    if not has_detachment(squad.owner):
        return False
    return player is None or squad.owner == player
