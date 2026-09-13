"""Hypercrypt Legion Enhancement: Hyperspatial Transfer Node (15 pts).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  "NECRONS model only. Each time the bearer's unit Advances, do not make an
   Advance roll for it. Instead, until the end of the phase, add 6" to the Move
   characteristic of models in the bearer's unit."

WORD FOR WORD the first half of the Overlord with translocation shroud's own
ability and Mont'ka's Aggressive Mobility, so it takes MovementController.
start_run()'s existing no-roll branch rather than a fifth one beside it - no die
is thrown, so there is nothing for Command Re-roll to replace. Unlike the
Shroud it carries no "through models and terrain" half: this text has none.

"The bearer's unit" is rule 19.03's pooled unit; the bearer being alive and the
detachment being fielded are enhancements.is_active()'s two halves.
"""

from game import enhancements

HYPERSPATIAL_TRANSFER_NODE = "Hyperspatial Transfer Node"
HYPERSPATIAL_TRANSFER_NODE_BONUS_IN = 6.0


def skips_advance_roll(squad):
    """MovementController.start_run()'s no-roll branch asks this."""
    return squad is not None and enhancements.is_active(squad, HYPERSPATIAL_TRANSFER_NODE)
