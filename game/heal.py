"""Core rules 02.02.04 and 01.02.03: a unit HEALS wounds.

  02.02.04 Healing Or Regaining Lost Wounds - per wound healed: "If that unit
  has one or more models that does not have its full wounds remaining, select
  one of those models; that model regains one lost wound." Once every living
  model is at full wounds and one or more models are destroyed, "revive one of
  those destroyed models (excluding CHARACTER models), with one wound
  remaining."

  01.02.03 Revived and Adding Models to a Unit - revived models come back with
  their original equipment, "This cannot expand a unit beyond its starting
  strength", they must be set up in coherency with the models that started the
  phase on the battlefield, and they may only be set up engaged with enemy
  units that were ALREADY engaged with the unit they rejoin.

EXTRACTED AT THE SECOND CONSUMER. This lived in game/reanimation_protocols.py
as reanimate(), because the Necron army rule ("that unit heals D3 wounds") was
the first datasheet text that named it. The Painboy's Crude Surgery ("this
unit heals 3 wounds", 2026-09 Ork codex) is the second, and it is not a
Reanimation Protocols activation - so a Necron module was the wrong home for a
core rule both read (Fehlerklasse 11). reanimation_protocols re-exports every
name it had, and its reanimate() is now a delegation here, so no Necron caller
moved.

Two consequences worth stating because they are easy to get backwards:

  * HEALING COMES FIRST, ALWAYS. A unit with one wounded model and four dead
    ones spends its first wound topping the wounded model up, not raising a
    corpse. That is why heal() drains the damaged models to full before it
    looks at destroyed_models at all.
  * CHARACTERS ARE NOT REVIVED. 02.02.04 excludes them, which is why Awakened
    Dynasty's "Protocol of the Eternal Revenant" exists, and why a Painboy
    healing his own mob can top himself up but never stand back up.

The four-part "put the model back" sequence and the Engagement Range test are
NOT here - they are shared with other abilities and live in
game/model_return.py.
"""

from game import model_return
from game.formation_layout import returning_positions
from game.squad import ENGAGEMENT_RANGE_IN


def alive_models(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def revivable_models(squad):
    """The destroyed models this unit is allowed to bring back, oldest
    destruction first.

    Two filters, both printed: CHARACTER models are excluded by 02.02.04, and
    01.02.03's "cannot expand a unit beyond its starting strength" caps how
    many of them may actually stand up again."""
    room = max(0, getattr(squad, "starting_model_count", 0) - len(alive_models(squad)))
    if room <= 0:
        return []
    candidates = [m for m in getattr(squad, "destroyed_models", ()) or ()
                  if not getattr(m.profile, "character", False)]
    return candidates[:room]


def healable_wounds(squad):
    """How many healed wounds this unit could still turn into something.

    The shared gate: the Resurrection Orb, Protocol of the Undying Legions,
    Crude Surgery and every deterministic AI verdict all ask this one question
    rather than each re-deriving it, so they cannot drift apart. A unit at full
    strength and full health returns 0, which is exactly "healing this one is
    wasted"."""
    missing = sum(max(0, m.profile.wounds - m.current_wounds) for m in alive_models(squad))
    return missing + sum(m.profile.wounds for m in revivable_models(squad))


def engaged_enemy_squads(squad, all_tokens):
    """The enemy UNITS already within Engagement Range of this one.

    01.02.03 permits a returning model to be set up engaged only with enemies
    that were already engaged with its unit, and it says UNITS - so this is a
    set of squads, not of models."""
    engaged = set()
    for token in all_tokens:
        other = getattr(token, "squad", None)
        if other is None or other is squad or other.owner == squad.owner or token.is_dead():
            continue
        for mine in alive_models(squad):
            gap = (((token.x_in - mine.x_in) ** 2 + (token.y_in - mine.y_in) ** 2) ** 0.5
                   - token.radius_in - mine.radius_in)
            if gap <= ENGAGEMENT_RANGE_IN:
                engaged.add(id(other))
                break
    return engaged


def placement_validator(squad, all_tokens=(), position_valid=None):
    """The `position_valid` returning_positions() should be handed.

    Two conditions, and the second is the one SetupController.position_valid()
    explicitly does not cover: terrain/board legality, AND 01.02.03's
    engagement clause - clear of every enemy unit that was not already fighting
    this one. Getting that wrong would let a wiped-out squad come back
    directly into a combat it was never part of."""
    tokens = list(all_tokens or ())
    already = engaged_enemy_squads(squad, tokens)
    forbidden = [t for t in tokens
                 if getattr(t, "squad", None) is not None
                 and t.squad.owner != squad.owner
                 and not t.is_dead()
                 and id(t.squad) not in already]

    def _valid(model, x_in, y_in):
        if position_valid is not None and not position_valid(model, x_in, y_in):
            return False
        return model_return.clear_of_engagement(model, x_in, y_in, forbidden)

    return _valid


def revive_off_board(model, squad, wounds):
    """model_return.set_up_model()'s three non-positional halves, for a unit that
    is NOT on the battlefield: back into the unit, off the destroyed list, with
    `wounds` remaining - and deliberately NOT onto the board. A unit in
    Strategic Reserves has no battlefield to stand a model on; its models come
    down together when the unit arrives, because IngressController.start_ingress()
    places every model in squad.models (SetupController.start_setup())."""
    maximum = model.profile.wounds
    model.current_wounds = max(1, min(int(wounds), maximum))
    if model not in squad.models:
        squad.models.append(model)
    model.squad = squad
    if model in getattr(squad, "destroyed_models", ()):
        squad.destroyed_models.remove(model)
    return model


def heal(squad, wounds, all_tokens=(), position_valid=None, game_state=None,
         placer=None, on_placed=None, off_board=False):
    """Spend `wounds` healed wounds on `squad`, per 02.02.04 + 01.02.03.

    Returns (wounds_spent, revived_models). `wounds_spent` can be less than
    `wounds` - a unit simply may not have that much to recover, and a model
    with nowhere legal to stand does not come back at all. Both are legal
    outcomes of the printed rule, and the surplus is lost rather than banked.

    `placer`, if given, is a ReturnPlacementController: rule 01.02.03 says a
    returning model is SET UP, and setting up is the controlling player's job.
    With one, a HUMAN gets the engine's spots as a starting point and drags
    from there; an owner in its auto_players lands on them outright, which is
    what this did for everyone. None keeps that older path for every caller
    that has not been handed one.

    `off_board=True` is for a unit in RESERVES (Hypercrypt Legion's Reanimation
    Crypts). Healing is unchanged; a revived model goes back into the unit
    WITHOUT a spot, a token or a placer, and stands up with the rest of the
    unit when it arrives - see revive_off_board().
    """
    remaining = max(0, int(wounds))
    spent = 0

    # 02.02.04, first clause: every living model back to full before anything
    # is revived. One wound at a time to the model that has lost the most, so
    # the unit never carries a nearly-dead model it could have topped up.
    while remaining > 0:
        damaged = [m for m in alive_models(squad) if m.current_wounds < m.profile.wounds]
        if not damaged:
            break
        target = min(damaged, key=lambda m: (m.current_wounds, m.profile.name))
        target.current_wounds += 1
        remaining -= 1
        spent += 1

    if remaining <= 0:
        return spent, []

    # 02.02.04, second clause: revive with ONE wound, then keep healing that
    # model with whatever is left before moving to the next corpse.
    plan = []
    for model in revivable_models(squad):
        if remaining <= 0:
            break
        give = min(model.profile.wounds, remaining)
        plan.append((model, give))
        remaining -= give
    if not plan:
        return spent, []

    if off_board:
        revived = []
        for model, give in plan:
            revive_off_board(model, squad, give)
            revived.append(model)
            spent += give
        return spent, revived

    valid = placement_validator(squad, all_tokens, position_valid)
    spots = returning_positions(squad, [m for m, _ in plan], position_valid=valid)

    if placer is not None:
        # The spots become a STARTING POINT rather than the answer. Only the
        # models that found one are handed over; a model with nowhere legal to
        # stand still stays down, so nobody is asked to place something the
        # rule did not return.
        revived = placer.place(
            squad,
            [model for model, _give in plan],
            spots,
            wounds=[give for _model, give in plan],
            validator=valid,
            # Fires when the placement is CONFIRMED (or cancelled, with an
            # empty list) - which for a human is frames later. The Necron army
            # rule uses it to hold its queue; Crude Surgery does not need to,
            # because the placer queues its own placements.
            on_done=on_placed,
        )
        spent += sum(give for (model, give) in plan if model in revived)
        return spent, revived

    revived = []
    for (model, give), spot in zip(plan, spots):
        if spot is None:
            continue  # nowhere legal to stand - that model stays down, wounds lost
        model_return.set_up_model(model, spot, wounds=give, game_state=game_state)
        revived.append(model)
        spent += give
    return spent, revived
