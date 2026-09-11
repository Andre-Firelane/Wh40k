"""Eldrad Ulthran's "Diviner of Futures" - a datasheet ability.

RULE (printed, word for word):
  "At the start of your Command phase, if this model is on the battlefield,
  you gain 1CP."

THE MACHINE MOVED OUT when Imotekh the Stormlord's Grand Strategist arrived
printing the identical sentence: it lives in game/command_phase_cp.py, whose
docstring carries the gain_cp()-not-gain_core_cp() reasoning and the
"on the battlefield" reading. This file is the flag and the label.

DIVINER_OF_FUTURES_CP, REASON and bearers_on_battlefield() are RE-EXPORTED
rather than moved, so every existing reader keeps working unchanged.
"""

from game.command_phase_cp import (  # noqa: F401  (re-exported, see below)
    COMMAND_PHASE_CP as DIVINER_OF_FUTURES_CP,
    CommandPhaseCpController,
)
from game import command_phase_cp

REASON = "Diviner of Futures"


def bearers_on_battlefield(player, all_tokens):
    """The living models with this ability that `player` has on the board."""
    return command_phase_cp.bearers_on_battlefield(
        player, all_tokens, "diviner_of_futures")


class DivinerOfFuturesController(CommandPhaseCpController):
    flag = "diviner_of_futures"
    reason = REASON
