"""Hypercrypt Legion Enhancement: Dimensional Overseer (25 pts).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  "NECRONS model only. While the bearer is on the battlefield or in Strategic
   Reserves, add one to the number of units from your army that you can select
   for the Hyperphasing rule."

ONE READER: game/hypercrypt_hyperphasing.py's limit(), which is where the cap
the rule prints is computed - the Enhancement changes the number, not who may be
selected.

"ON THE BATTLEFIELD OR IN STRATEGIC RESERVES" is two places, and the third place
a unit can be - EMBARKED within a TRANSPORT - is neither. Asked of the board's
tokens and of GameState.reserves, which are exactly those two containers; an
embarked unit is in game_state.embarked_squads and in neither. The bearer being
alive is enhancements.is_active()'s 19.04 reading.

"ADD ONE" is one, however many bearers there are: an Enhancement is taken once
per army, and a second copy on the table would be a list-building error rather
than a second +1.
"""

from game import enhancements

DIMENSIONAL_OVERSEER = "Dimensional Overseer"
DIMENSIONAL_OVERSEER_EXTRA_UNITS = 1


def bearer_squads(player, game_state):
    """The units carrying a living, active Dimensional Overseer that are on the
    battlefield or in Strategic Reserves."""
    if player is None or game_state is None:
        return []
    squads = []
    for token in getattr(game_state, "tokens", ()) or ():
        squad = getattr(token, "squad", None)
        if squad is not None and squad not in squads:
            squads.append(squad)
    for squad in getattr(game_state, "reserves", ()) or ():
        if squad not in squads:
            squads.append(squad)
    # No embarked_in term: measured redundant. TransportController.embark() and
    # the pregame EMBARK declaration both take the unit out of the tokens and
    # never put it in reserves, so the two containers above ARE the rule's two
    # places - a sweep over GameState.all_squads() would be the wrong reading.
    return [s for s in squads
            if s.owner == player and enhancements.is_active(s, DIMENSIONAL_OVERSEER)]


def extra_units(player, game_state):
    """How many more units this player's Hyperphasing may select."""
    return DIMENSIONAL_OVERSEER_EXTRA_UNITS if bearer_squads(player, game_state) else 0
