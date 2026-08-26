"""Putting a destroyed model BACK on the battlefield - the shared half.

WHY THIS EXISTS. Two modules already did this, character for character:
game/grot_orderly.py's _return_model() (Painboy's Grot Orderly) and
game/unquenchable_resolve.py's _set_up() (Fuegan). CLAUDE.md's standing rule is
to extract at the SECOND consumer, and the Necron Reanimation Protocols army
rule brings the third and fourth (game/reanimation_protocols.py, plus Awakened
Dynasty's Protocol of the Eternal Revenant), so this is overdue rather than
speculative.

THE FOUR HALVES OF "BACK", which is the part worth centralising. Fuegan's
module states it best: a model is back on the battlefield when it is

  * in GameState.tokens,
  * in its Squad.models,
  * OFF Squad.destroyed_models,
  * carrying a real current_wounds value,

and any one of those left out is a half-alive model that some other system
will trip over later, in a way that does not look like this bug.

WHAT IS DELIBERATELY NOT HERE: the choice of SPOT. The three callers do not
agree on it and should not be made to - the rules they implement genuinely
differ:

  * Grot Orderly and Reanimation Protocols return models INTO a standing unit,
    so they owe rule 09.02 coherency and use
    formation_layout.returning_positions(), which satisfies it by construction.
  * Fuegan and the Eternal Revenant name a POINT ("as close as possible to
    where it was destroyed"), and the unit's shape has no say in it, so they
    walk formation_layout.ring_candidates() outwards from where the model fell.

WHAT IS HERE is the engagement test, because that one is shared and easy to
forget: SetupController.position_valid() deliberately does NOT check
Engagement Range (its own docstring says so - engagement and coherency depend
on a whole squad's final positions, not on one point), so a caller that leans
on it alone will happily set a model up in combat. That mistake has already
cost a whole unit once, in the Emergency Disembark.
"""

import math

from game.squad import ENGAGEMENT_RANGE_IN


def enemy_tokens(model, all_tokens):
    """Every living token that does not belong to `model`'s owner."""
    owner = model.squad.owner if model.squad is not None else None
    return [t for t in all_tokens
            if t.squad is not None and t.squad.owner != owner and not t.is_dead()]


def clear_of_engagement(model, x_in, y_in, enemies):
    """True when standing `model` at (x_in, y_in) would leave it outside
    Engagement Range of every model in `enemies`.

    Measured edge to edge, like every other Engagement Range test in this
    engine, so a big base is treated as the big base it is."""
    for enemy in enemies:
        gap = (math.hypot(x_in - enemy.x_in, y_in - enemy.y_in)
               - model.radius_in - enemy.radius_in)
        if gap <= ENGAGEMENT_RANGE_IN:
            return False
    return True


def set_up_model(model, spot, wounds=None, game_state=None):
    """Put `model` back on the battlefield at `spot`, with `wounds` remaining.

    `wounds=None` means "its full wounds", which is what both original callers
    hard-coded. The parameter exists because the newer rules do not agree with
    them: Reanimation Protocols revives with exactly ONE wound (rule 02.02.04)
    and only then heals further, and the Eternal Revenant brings a character
    back on half its starting wounds. Clamped to the model's own maximum so no
    caller can over-heal it by passing a number that is too big.
    """
    squad = model.squad
    model.x_in, model.y_in = spot
    maximum = model.profile.wounds
    model.current_wounds = maximum if wounds is None else max(1, min(int(wounds), maximum))
    if squad is not None:
        if model not in squad.models:
            squad.models.append(model)
        model.squad = squad
        if model in getattr(squad, "destroyed_models", ()):
            squad.destroyed_models.remove(model)
    if game_state is not None and model not in game_state.tokens:
        game_state.tokens.append(model)
    return model
