"""Who forces a falling-back unit into DESPERATE ESCAPE, and what it costs it.

Rule 09.07 gives a falling-back unit a choice of two modes, and abilities take
it away. Two sources today, and they print nearly the same sentence:

  * the Clanblade's Cornered Prey (game/cornered_prey.py) - a datasheet ability;
  * Da Big Hunt's Where D'ya Fink You're Going? (game/da_hunt_where_dya_fink.py,
    Mecha Orks G5) - a Stratagem, which adds hazard rolls on top.

game/fall_back.py asked cornered_prey by name in three places (declare(),
choose_mode() and confirm()'s hazard step). A second source would have meant
three more `or` terms and three chances to add only two - the shape error class
10 keeps producing - so the question moved here at that second source, as a
REGISTRY: each carrier registers what it answers, and fall_back asks the
registry.

THREE QUESTIONS, because the printed sentences ask three:
  * forces()          - "must use the desperate escape mode";
  * hazard_penalty()  - "-1 from those hazard rolls" (both print it, both only
    for a battle-shocked unit);
  * extra_hazard_rolls() - "three additional hazard rolls for each BEAST SNAGGA
    unit it is engaged with", which only the Stratagem prints.

SOURCES SUM rather than take the best: two different rules subtracting from the
same roll are two modifiers, and 40k adds them. It cannot arise today - one
source is Aeldari, the other Orks, and only two armies are on the table - which
is stated rather than relied on.

The registry is a module-level TUPLE listing its sources, like
game/conditional_lone_operative.py's: a source is a fact about the rules, not
about a particular battle, and nothing has to remember to register itself.
"""

from game import cornered_prey, da_hunt_where_dya_fink

#: (label, forces, penalty, extra_rolls) - the last three are callables taking
#: (squad, all_tokens) and returning bool / int / int, or None for "this source
#: does not answer that question".
#:
#: LISTED HERE, not registered by an import side effect: that is
#: game/conditional_lone_operative.py's arrangement, and it means a caller that
#: imports only this module gets every source - a source that registers itself
#: on import is a source that is missing whenever nobody imported it.
SOURCES = (
    (cornered_prey.CORNERED_PREY_LABEL,
     cornered_prey.forces_desperate_escape,
     cornered_prey.hazard_penalty_for,
     None),
    # Da Big Hunt's Where D'ya Fink You're Going? (Mecha Orks G5) - the same
    # two clauses, bought, plus the extra rolls only it prints.
    (da_hunt_where_dya_fink.WHERE_DYA_FINK_NAME,
     da_hunt_where_dya_fink.forces_desperate_escape,
     da_hunt_where_dya_fink.hazard_penalty_for,
     da_hunt_where_dya_fink.extra_hazard_rolls_for),
)


def forces(squad, all_tokens=()):
    """Must this unit use the Desperate Escape mode, whatever it would pick?

    Live: this is asked BEFORE the move (at declare() and choose_mode()), while
    the engagement both sources talk about still exists."""
    return any(fn(squad, all_tokens) for _label, fn, _p, _x in SOURCES if fn is not None)


def _live_penalty(squad, all_tokens):
    return sum(fn(squad, all_tokens) for _label, _f, fn, _x in SOURCES if fn is not None)


def _live_extra_rolls(squad, all_tokens):
    return sum(fn(squad, all_tokens) for _label, _f, _p, fn in SOURCES if fn is not None)


def _live_reasons(squad, all_tokens):
    return [label for label, fn, _p, _x in SOURCES if fn is not None and fn(squad, all_tokens)]


def snapshot(squad, all_tokens=()):
    """Freeze what this unit's hazard rolls will cost, AT THE INSTANT THE
    ENGAGEMENT STILL EXISTS.

    Both sources are written as "an enemy unit ENGAGED WITH this unit is
    selected to make a fall-back move", and both put their cost on the hazard
    rolls - which happen after that move. A fall-back move must END unengaged
    (rule 09.07), so a live count at the roll is zero for every unit that ever
    gets there: the -1 and the extra rolls could never apply. Cornered Prey had
    that defect from the day it was built, invisibly, because its suite asks its
    module functions while the two units still stand together; the second source
    made it visible.

    Called at each of the three moments the engagement is still true: the
    declaration, the mode choice, and - for a Stratagem a human buys frames
    later, when both earlier moments have already passed - the purchase."""
    if squad is None:
        return None
    penalty = _live_penalty(squad, all_tokens)
    extra = _live_extra_rolls(squad, all_tokens)
    if not penalty and not extra:
        return getattr(squad, "forced_escape_hazard", None)
    frozen = (penalty, extra, tuple(_live_reasons(squad, all_tokens)))
    squad.forced_escape_hazard = frozen
    return frozen


def clear_snapshot(squad):
    """The fall back is over - see game/fall_back.py, which owns both ends."""
    if squad is not None and getattr(squad, "forced_escape_hazard", None):
        squad.forced_escape_hazard = None


def _frozen(squad):
    return getattr(squad, "forced_escape_hazard", None) or (0, 0, ())


def hazard_penalty(squad, all_tokens=()):
    """The total subtracted from each of its hazard rolls - the larger of what
    is true now and what was frozen when it was selected to fall back. Two
    sources SUM: two rules subtracting from the same roll are two modifiers."""
    return max(_live_penalty(squad, all_tokens), _frozen(squad)[0])


def extra_hazard_rolls(squad, all_tokens=()):
    """Hazard rolls this unit makes ON TOP of one per model."""
    return max(_live_extra_rolls(squad, all_tokens), _frozen(squad)[1])


def reasons(squad, all_tokens=()):
    """Which sources are speaking, by label - for the roll line that says WHY a
    unit has no choice and what it is paying."""
    live = _live_reasons(squad, all_tokens)
    return live or list(_frozen(squad)[2])
