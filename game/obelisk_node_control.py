"""The Geomancer's "Obelisk Node Control" (Necrons).

RULE (printed, word for word):
  "While this model is within range of an objective marker you control, enemy
   units that are set up on the battlefield from Reserves cannot be set up
   within 12" of this model."

THE FIRST RULE IN THIS ENGINE THAT RESTRICTS WHERE THE OPPONENT MAY ARRIVE, and
that is not a guess: game/units.py records the T'au Ethereal's Jammer Array as
NOT built for exactly this reason - "no ability in this engine has ever
restricted where the other player may arrive". The Geomancer is the second
carrier of that idea, which is the point at which this repo builds it; the
Jammer Array can now be one call away when someone wants it.

WHERE IT LANDS is IngressController.position_valid(), the predicate that paints
the green/red placement overlay AND that ai/agent_driver.py's candidate sweep
filters on. Both matter: a human sees the ground go red, and the AI never
offers itself a spot the rule forbids in the first place. There is no second
copy of the restriction anywhere - one predicate, both consumers.

TWO CONDITIONS, AND BOTH ARE LIVE:
  * "WHILE THIS MODEL IS WITHIN RANGE OF AN OBJECTIVE MARKER YOU CONTROL" -
    both halves, and neither is decoration. A Geomancer standing on ground
    nobody controls, or on an objective the OPPONENT controls, blocks nothing.
    Read through game/objectives.py's own two predicates rather than measured
    again here, so "within range" and "control" mean what they mean everywhere
    else.
  * "WITHIN 12" OF THIS MODEL" - of the MODEL, not of its unit. A Geomancer
    attached to a bodyguard unit does not project the bubble from its
    bodyguards, which is what the printed word says and what a unit-level test
    would get wrong the moment he joins Necron Warriors.

IT BLOCKS ARRIVAL, NOT MOVEMENT. A unit already on the battlefield may walk
inside the 12" freely; only "set up ... from Reserves" is forbidden. That is
why it lives on the ingress predicate and nowhere near clamp_move().
"""

from game.objectives import model_is_within_range_of_objective

OBELISK_NODE_CONTROL_LABEL = "Obelisk Node Control"

#: "cannot be set up within 12" of this model".
OBELISK_NODE_RANGE_IN = 12.0


def active_bearers(all_tokens=(), objectives=(), owner=None):
    """Every living Geomancer model whose two conditions currently hold.

    `owner` narrows to one player's bearers; None means every player's, which
    is what the ingress predicate wants (it is asked about the ARRIVING unit
    and must consider every enemy bearer)."""
    out = []
    for token in all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is None or token.is_dead():
            continue
        if owner is not None and squad.owner != owner:
            continue
        if not getattr(token.profile, "obelisk_node_control", False):
            continue
        if _on_controlled_objective(token, squad, objectives):
            out.append(token)
    return out


def _on_controlled_objective(token, squad, objectives):
    """"within range of an objective marker YOU CONTROL" - both halves."""
    for objective in objectives or ():
        if getattr(objective, "controlled_by", None) != squad.owner:
            continue
        if model_is_within_range_of_objective(token, objective):
            return True
    return False


def blocks_arrival(squad, x_in, y_in, radius_in, all_tokens=(), objectives=()):
    """Whether an ENEMY bearer forbids `squad` arriving with a model centred
    here.

    Returns True to REFUSE the spot. Asked of the arriving unit's owner, so a
    player's own Geomancer never blocks their own reserves - the printed word
    is "enemy units"."""
    if squad is None:
        return False
    owner = getattr(squad, "owner", None)
    for bearer in active_bearers(all_tokens, objectives):
        if getattr(bearer.squad, "owner", None) == owner:
            continue
        gap = ((x_in - bearer.x_in) ** 2 + (y_in - bearer.y_in) ** 2) ** 0.5
        if gap - radius_in - bearer.radius_in <= OBELISK_NODE_RANGE_IN:
            return True
    return False
