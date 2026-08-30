"""What the T'au detachment rules share.

WHY THIS EXISTS
---------------
Extracted at the SECOND consumer, per this repo's standing rule. Kauyon
(game/kauyon.py) and Mont'ka (game/montka.py) are the same mechanism twice:

    "During the <N>, <N> and <N> battle rounds, ranged weapons equipped by
     T'AU EMPIRE models from your army have the [<KEYWORD>] ability. During
     those rounds, while a unit is a Guided unit, <something more>."

Only the rounds, the keyword and the second clause differ. Written twice, the
three tests they share - is this a T'AU EMPIRE unit, does this player actually
have this detachment, is the battle round inside the window - would be three
pairs of copies that could drift apart, and the round window is exactly the
kind of off-by-one that only shows up in a game.

is_tau_unit() ALSO MOVED HERE, and that is a rename in disguise: it lived in
game/retaliation_cadre.py, which is a DETACHMENT module, while the question it
answers is a FACTION one ("is this unit T'au"). One detachment owning it was
fine while there was one detachment; with six it is precisely the lying name
this repo renames rather than copies. game/retaliation_cadre.py imports it from
here now, so there is still one definition.
"""

from game import config, detachment_gate

TAU_KEYWORD = "T'AU EMPIRE"


def is_tau_unit(squad):
    """"a T'AU EMPIRE unit from your army".

    Read off the DATASHEET's faction rather than a per-model flag, like
    game/awakened_dynasty.py's is_necrons_unit(): that is what the keyword
    actually is, and it keeps working for a unit whose models happen to lack
    any particular ability."""
    if squad is None:
        return False
    # Imported inside the function: `game.factions.faction` pulls the whole
    # game.factions package, and game/coldstar.py now reaches this module very
    # early in game/squad.py's own import - a module-level import closes that
    # cycle. Nothing here is on a hot path that a local import would matter to.
    from game.factions.faction import faction_keyword_of
    return faction_keyword_of(squad) == TAU_KEYWORD


#: Re-exported, not redefined. The question has no faction in it - it reads one
#: config constant - and the seven Aeldari detachment rules are the first
#: non-T'au callers, so it moved to game/detachment_gate.py under the same
#: second-consumer rule that moved is_tau_unit() here. Kept reachable through
#: this name because a dozen T'au modules already import it from here, and the
#: test pins that both names are the SAME object.
has_detachment = detachment_gate.has_detachment


def battle_round_in(turn_tracker, rounds):
    """Is the battle round one of `rounds`?

    A missing turn_tracker, or one with no battle round yet, reads as OUT of
    the window - the safe direction for a detachment rule, since it withholds a
    bonus rather than inventing one.

    That falls out of the getattr default rather than needing a guard of its
    own: the default is None, and None is never one of the printed rounds. An
    explicit `if turn_tracker is None: return False` was written here first and
    removed once an A/B probe showed deleting it changed no answer - a branch
    no input can reach is a branch that will eventually be trusted wrongly.
    """
    return getattr(turn_tracker, "battle_round", None) in tuple(rounds)


def doctrine_active(squad, setting, rounds, turn_tracker):
    """The condition both halves of both rules open with: a T'au unit whose
    owner brought this detachment, during one of its battle rounds.

    The round window is not simply `rounds`: the two Exemplar Enhancements
    WIDEN their own detachment's window for the one unit their bearer leads
    ("from the second battle round onwards instead of from the third", "during
    the fourth battle round as well"). That widening is asked here, in the one
    place both detachment rules and all four of their grant sites go through -
    see game/enh_exemplars.py for why it cannot live at the grant sites
    instead. A unit with no such bearer gets `rounds` back unchanged, so
    nothing that already existed changes.
    """
    if squad is None:
        return False
    if not has_detachment(getattr(squad, "owner", None), setting):
        return False
    if not is_tau_unit(squad):
        return False
    # Imported inside the function: game/enh_exemplars.py reaches back into
    # game/kauyon.py and game/montka.py for their SETTING constants, and both
    # of those import this module - a module-level import would close that
    # cycle. Same reasoning as is_tau_unit()'s local import above.
    from game import enh_exemplars
    return battle_round_in(turn_tracker, enh_exemplars.rounds_for(squad, setting, rounds))


def is_guided_attack(greater_good, attacking_squad, target_squad):
    """"while a unit is a Guided unit" - and, because the army rule defines
    Guided as "while targeting one or more Spotted units", that is a question
    about the ATTACK rather than about the unit alone.

    GreaterGoodController already answers exactly this (it is what the army
    rule's own +1 BS is gated on), so it is asked rather than re-derived - a
    second opinion on which units are Guided is precisely the drift this repo
    keeps consolidating. Degrades to False without a controller, so a scene
    built without the army rule simply never sees the second clause."""
    if greater_good is None:
        return False
    return greater_good.is_guided_attack(attacking_squad, target_squad)
