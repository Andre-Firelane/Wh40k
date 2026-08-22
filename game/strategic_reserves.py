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
"""


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
