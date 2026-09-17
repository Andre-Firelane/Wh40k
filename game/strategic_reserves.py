"""Moving a unit from the battlefield INTO Strategic Reserves - the one
direction that is not rule 20.03/20.04's own.

Extracted from game/starflare_ignition.py, which owned it while that T'au
Enhancement was the only thing that could send a unit back off the board. Seer
Council's Unshrouded Truth is the second, and a module named after one
faction's Enhancement is the wrong home for another faction's stratagem. Ninth
extraction of this shape, after game/invulnerable_save.py, game/crit_hit.py,
game/damage_reroll.py, game/damage_estimate.py, game/unmodified_six.py,
game/psychic_mark.py, game/roll_bonus.py and game/crit_ap.py, and for the same
two reasons each time: a second foreign consumer, and one call site to update.

MECHANICALLY IT IS TransportController.embark()'s removal step: the models leave
game_state.tokens and the unit is recorded off-board instead. A unit whose models
are not in tokens is, by this engine's own convention (see
GameState.add_reserve_squad's docstring), simply not on the battlefield - so
every on-board rule stops seeing it for free, and no rule needs to learn about
this.

TWO THINGS THAT ARE NOT OPTIONAL and are why this is a function rather than four
lines at each call site:

  * ingress_locked is cleared. Rule 20.04's post-arrival lock describes an
    arrival that has now been UNDONE; confirm_ingress() sets it again on the
    next one. Leaving it set would silently forbid the unit's next move.
  * Objective control is recomputed. Rule 14.02 recomputes Level of Control at
    the end of each phase and turn, and a unit vanishing mid-phase is exactly
    the kind of change that boundary exists to pick up - it may have been the
    only thing holding an objective.

WHAT IS NOT SHARED is each caller's own eligibility and wording: the
Enhancement's "not within Engagement Range of one or more enemy units" and the
stratagem's TARGET clause have nothing in common, and each logs in its own
voice. Both are checked BEFORE calling this.

WHEN A WITHDRAWAL CAN STILL COME BACK. withdrawal_is_doomed() and
misses_next_arrival() are rule 20.03 facts about the moment a unit leaves the
board at the end of an opponent's turn. They were written for Hypercrypt
Legion's Hyperphasing and moved here with their second reader, the Deffkoptas'
Aerial Manoover (stage E3d) - "at the end of your opponent's Fight phase" is
the same advance_turn_phase() call. game/hypercrypt_hyperphasing.py re-exports
both.
"""


#: Rule 20.03: "At the end of the third battle round ... all strategic reserves
#: units that have not made one or more ingress moves are destroyed."
RESERVES_DESTROYED_AFTER_ROUND = 3


def withdrawal_is_doomed(turn_tracker):
    """Whether a unit placed into Strategic Reserves at THIS end of turn is lost
    before it can arrive. Read after advance_phase(), which is when main.py makes
    the end-of-turn offers.

    True when the battle is over, and when the turn that just ended was the last
    of battle round 3: advance_phase() has then rolled the counter to 4 with the
    round's first turn still to come (turn_index_in_round 0), and rule 20.03's
    destruction runs right after the offers in the same call."""
    if turn_tracker is None:
        return False
    if getattr(turn_tracker, "battle_over", False):
        return True
    return (getattr(turn_tracker, "battle_round", 0) == RESERVES_DESTROYED_AFTER_ROUND + 1
            and getattr(turn_tracker, "turn_index_in_round", None) == 0)


def misses_next_arrival(turn_tracker):
    """Whether a unit withdrawn now cannot arrive in its owner's NEXT Movement
    phase because rule 20.03 forbids arrivals before battle round 2. The owner's
    next turn is the one advance_phase() has just started."""
    if turn_tracker is None:
        return False
    from game.ingress import INGRESS_MIN_BATTLE_ROUND
    return getattr(turn_tracker, "battle_round", 0) < INGRESS_MIN_BATTLE_ROUND


def withdraw_to_reserves(game_state, squad, log=None, message=None):
    """Take `squad` off the battlefield and into Strategic Reserves.

    Returns True. Callers do their own eligibility check first - this is the
    mechanical move, not a decision. `message` is the caller's own log line;
    without one nothing is logged, since the two callers describe very
    different events."""
    for model in list(squad.models):
        if model in game_state.tokens:
            game_state.tokens.remove(model)
    game_state.reserves.append(squad)
    squad.ingress_locked = False
    for objective in game_state.objectives:
        objective.update_control(game_state.tokens)
    if log is not None and message:
        log.add(message)
    return True
