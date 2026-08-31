"""Warhost Enhancement: Timeless Strategist (15 pts).

RULE (verbatim, rules/aeldari/detachments/Warhost.md):
  "ASURYANI model only. At the start of the battle round, if the bearer is on
  the battlefield (or any TRANSPORT it is embarked within is on the
  battlefield), you receive 1 additional Battle Focus token."

THE SECOND SOURCE OF AN EXTRA BATTLE FOCUS TOKEN, after its own detachment's
Martial Grace - and it lands at the same spot in game/battle_focus.py's grant,
which already adds a per-player term there rather than inside
tokens_for_battle_size() (that function answers a question about the BATTLE
SIZE and would have handed the token to both armies).

BUT IT NEEDS THE BOARD, WHICH MARTIAL GRACE DOES NOT. Martial Grace is
"anyone fielding Warhost gets one" - a pure player question. This one is
conditional on where a specific MODEL is, so it takes the squads. That is why
the two are separate terms rather than one shared helper: they answer
differently shaped questions and only happen to add to the same number.

"ON THE BATTLEFIELD (OR ANY TRANSPORT IT IS EMBARKED WITHIN IS)" - TWO ways to
qualify, and the second is the one that is easy to drop. A bearer riding in a
Wave Serpent is NOT on the battlefield in this engine's terms (its models are
off the token list), so a naive "is it on the board" test would silently switch
the Enhancement off for exactly the army that bought a transport for it.
Strategic Reserves are the case that must still NOT qualify: a unit in reserve
is not on the battlefield and is not embarked in anything that is.

"AT THE START OF THE BATTLE ROUND" - the same moment the tokens are granted, so
it is read there rather than latched earlier. A battle round is not a turn: the
token arrives once for the round, not once per player turn.
"""
from game import enhancements

TIMELESS_STRATEGIST = "Timeless Strategist"

TIMELESS_STRATEGIST_LABEL = "Timeless Strategist"

#: "you receive 1 additional Battle Focus token".
TIMELESS_STRATEGIST_EXTRA_TOKENS = 1


def bearer_models(squad):
    """is_active(), not bearer_models() alone: an Enhancement only exists while
    its detachment is fielded, and bearer_models() answers only "is the model
    still alive"."""
    if not enhancements.is_active(squad, TIMELESS_STRATEGIST):
        return []
    return enhancements.bearer_models(squad, TIMELESS_STRATEGIST)


def _qualifies(squad, on_board_squads, embarked_squads):
    """Either printed way of being present."""
    if not bearer_models(squad):
        return False
    if squad in on_board_squads:
        return True
    # "...or any TRANSPORT it is embarked within is on the battlefield". The
    # transport being on the board is what embarked_squads means: a unit in
    # Strategic Reserves is in neither collection and correctly gets nothing.
    return squad in embarked_squads


def extra_tokens_for(player, on_board_squads=(), embarked_squads=()):
    """The additional tokens this player gets. Zero for anyone without a
    bearer, so the caller can add it unconditionally - the same contract
    game/martial_grace.py's own extra_tokens_for() offers."""
    on_board = set(on_board_squads or ())
    embarked = set(embarked_squads or ())
    for squad in on_board | embarked:
        if squad.owner != player:
            continue
        if _qualifies(squad, on_board, embarked):
            return TIMELESS_STRATEGIST_EXTRA_TOKENS
    return 0
