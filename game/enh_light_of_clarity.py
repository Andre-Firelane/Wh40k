"""Spirit Conclave Enhancement: Light of Clarity (30 pts).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  "SPIRITSEER model only. In your Command phase, select one friendly WRAITH
  CONSTRUCT unit within 12" of the bearer. Until the start of your next Command
  phase, add 1 to the Objective Control characteristic of INFANTRY models in
  that unit and add 3 to the Objective Control characteristic of MONSTER models
  in that unit."

THE MARKING HALF IS SHARED. Three Spirit Conclave Enhancements print the same
opening sentence, and Auxiliary Cadre's Admired Leader prints it too - four
carriers, so the machine lives in game/command_phase_mark.py. This module is
the effect and nothing else.

`exclude_own_unit=False`, as printed: "one friendly WRAITH CONSTRUCT unit" says
nothing about excluding the bearer's own, and a Spiritseer prints no LEADER
line so its unit is itself. Admired Leader passes True for the skip it has
always had - both settings are pinned, because folding either into the shared
machine would move the other silently.

TWO NUMBERS, ONE PER KEYWORD, and they are not the same number: +1 for
INFANTRY, +3 for MONSTER. Two separate test lines, because a single check
covering "the OC went up" is a tautology that passes with one bonus wired and
the other missing - and MONSTER is the one worth three times as much.

A MODEL THAT IS NEITHER GETS NOTHING. Wraithguard and Wraithblades are
INFANTRY, the Wraithlord is a MONSTER, and every WRAITH CONSTRUCT built here is
one or the other - so the "neither" branch is a MEASURED no-op today. Written
and tested anyway, with a hand-built model, because "already impossible" and
"forgotten" look identical from the code.

AN ADD, so it lands in effective_oc()'s third layer beside Strategic Savant and
the two T'au Enhancements - after Hunting Hounds' set and Soulrot's floor, so
that thirty points always buy what they say.
"""

from game.command_phase_mark import CommandPhaseMark
from game.wraith_construct import is_wraith_construct_unit

LIGHT_OF_CLARITY = "Light of Clarity"

#: 'select one friendly WRAITH CONSTRUCT unit within 12" of the bearer'.
LIGHT_OF_CLARITY_RANGE_IN = 12.0

#: The two printed bonuses. NOT one number - see the docstring.
LIGHT_OF_CLARITY_INFANTRY_OC = 1
LIGHT_OF_CLARITY_MONSTER_OC = 3

FLAG_ATTR = "light_of_clarity_active"


def is_marked(squad):
    return bool(getattr(squad, FLAG_ATTR, False))


def oc_bonus(model):
    """The bonus for THIS model, which depends on its own keyword line rather
    than on the unit's - the printed text names two keywords with two numbers,
    and a unit can in principle hold both. Read by
    game/objective_control.py's fold."""
    if model is None or not is_marked(getattr(model, "squad", None)):
        return 0
    # INFANTRY and MONSTER are both UnitProfile FLAGS in this engine (unlike
    # MOUNTED, which is datasheet-only), so the per-model question is a direct
    # read - the same two fields game/fated_hero.py maps those keywords onto.
    # MONSTER is checked first: it is worth three times as much, and nothing
    # printed says a model cannot carry both.
    if getattr(model.profile, "monster", False):
        return LIGHT_OF_CLARITY_MONSTER_OC
    if getattr(model.profile, "infantry", False):
        return LIGHT_OF_CLARITY_INFANTRY_OC
    return 0


class LightOfClarityController(CommandPhaseMark):
    """The Command-phase offer. All of the machine is shared - see
    game/command_phase_mark.py; what is this card's own is the keyword clause,
    the flag, and `exclude_own_unit=False`."""

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        super().__init__(
            LIGHT_OF_CLARITY, LIGHT_OF_CLARITY_RANGE_IN, FLAG_ATTR,
            is_wraith_construct_unit,
            "gets +%d OC (INFANTRY) and +%d OC (MONSTER)"
            % (LIGHT_OF_CLARITY_INFANTRY_OC, LIGHT_OF_CLARITY_MONSTER_OC),
            game_state=game_state, decision_manager=decision_manager,
            game_log=game_log, auto_players=auto_players,
            exclude_own_unit=False,
        )
