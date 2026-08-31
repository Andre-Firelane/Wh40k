"""Spirit Conclave Enhancement: Rune of Mists (10 pts).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  "SPIRITSEER model only. In your Command phase, select one friendly WRAITH
  CONSTRUCT unit within 12" of the bearer. Until the start of your next
  Command phase, each time a ranged attack targets that unit, unless the
  attacking model is within 18", models in that unit have the Benefit of Cover
  against that attack."

THE THIRD CARRIER OF THE SHARED COMMAND-PHASE MARK. Light of Clarity (Etappe 1)
and Stave of Kurnous (Etappe 2) print the same first two sentences word for
word; only the effect differs. So the selection, the 12", the WRAITH CONSTRUCT
filter and the "until the start of your next Command phase" clock all come
from game/command_phase_mark.py, and this module carries nothing but its own
effect.

NOTE WHAT IT DOES *NOT* PRINT: Stave of Kurnous adds "(excluding TITANIC
units)" to the same sentence and this one does not. That exclusion therefore
lives in Stave's module and not in the shared machine - a shared filter would
apply a clause two of the three Enhancements never printed.

"UNLESS THE ATTACKING MODEL IS WITHIN 18"" - AN INVERTED RANGE. Almost every
range clause in this engine grants something INSIDE a distance; this one grants
it OUTSIDE. Written the usual way round it would hand cover to exactly the
enemies it is meant to leave uncovered, and the predicate would look perfectly
reasonable. Measured on both sides of the line in the test.

It also fits the existing seam without a new parameter, because
_has_benefit_of_cover(shooter_model, target_squad) already asks per SHOOTER -
which is what an "attacking model" clause needs.

BUT RULE 10.02 FREEZES IT, and that is worth knowing rather than discovering:
cover is snapshotted when the target is selected, so the 18" is measured ONCE
per activation, from each shooter, and does not re-measure per weapon group.
That is the same treatment every other cover source gets and the reason
casualties cannot change cover halfway through one unit's shooting.
"""
from game import wraith_construct
from game.command_phase_mark import CommandPhaseMark
from game.squad import edge_distance

RUNE_OF_MISTS = "Rune of Mists"

RUNE_OF_MISTS_LABEL = "Rune of Mists"

#: 'select one friendly WRAITH CONSTRUCT unit within 12" of the bearer'.
RUNE_OF_MISTS_RANGE_IN = 12.0

#: 'unless the attacking model is within 18"' - OUTSIDE this, cover is granted.
RUNE_OF_MISTS_MIN_ATTACKER_RANGE_IN = 18.0

FLAG_ATTR = "rune_of_mists_active"


def is_marked(squad):
    return bool(getattr(squad, FLAG_ATTR, False))


def grants_cover(shooter_model, target_squad):
    """Whether THIS shooter's ranged attack finds the target in cover.

    Read by game/shooting.py's _compute_benefit_of_cover(). The distance test
    is INVERTED on purpose - see the module docstring."""
    if shooter_model is None or not is_marked(target_squad):
        return False
    return not _within(shooter_model, target_squad, RUNE_OF_MISTS_MIN_ATTACKER_RANGE_IN)


def _within(shooter_model, target_squad, range_in):
    """Whether the attacking model is within `range_in` of any living model of
    the target unit - the ordinary reading of "within X of that unit"."""
    for other in getattr(target_squad, "models", ()) or ():
        if other.is_dead():
            continue
        if edge_distance(shooter_model, other) <= range_in:
            return True
    return False


def eligible_target(squad):
    """"one friendly WRAITH CONSTRUCT unit" - and, unlike Stave of Kurnous,
    with NO TITANIC exclusion, because this card does not print one."""
    return wraith_construct.is_wraith_construct_unit(squad)


def reset(squads=()):
    for squad in squads or ():
        if squad is not None:
            setattr(squad, FLAG_ATTR, False)


class RuneOfMistsController(CommandPhaseMark):
    """The Command-phase offer, on the shared machine."""

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        super().__init__(
            RUNE_OF_MISTS, RUNE_OF_MISTS_RANGE_IN, FLAG_ATTR,
            eligible_target,
            'has the Benefit of Cover against attackers further than 18"',
            game_state=game_state, decision_manager=decision_manager,
            game_log=game_log, auto_players=auto_players,
            exclude_own_unit=False,
        )
