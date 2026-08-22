"""Rule 03.01's Declare Battle Formations step: before anything is deployed,
each player declares which units start embarked within which TRANSPORTs
(18.01) and which units start in Strategic Reserves (20.01).

Deliberately free of pygame and of any controller: the human UI
(game/ui/action_panel.py) and the AI (ai/agent_driver.py's
plan_battle_formations) both have to answer exactly the same legality
questions, and this project's convention is that the engine generates the
legal options and the chooser only picks among them - which only works if
there is one implementation of "legal" for both sides to read.

Why this can't just call TransportController.can_embark() (rule 18.02):
that method answers the MID-BATTLE question and carries three conditions
that are meaningless before the battle starts - `squad.set_up_this_turn`,
`squad in movement_controller.moved_squad_ids` ("only after a normal,
advance or fall-back move this phase"), and "every model within 3" of the
hull" (nothing has a position yet). 18.01 is a different, more permissive
rule. The datasheet-level restrictions are shared, and _model_capacity_cost
is imported rather than reimplemented so MEGA ARMOUR's cost-2 rule has
exactly one implementation."""

from game.transport import _model_capacity_cost


def transport_name(transport_token):
    """How to NAME a transport in a message. Its unit name ("2 Trukk 1"), not
    its profile name ("Trukk") - the profile name is shared by every copy on
    the table, so a message built from it cannot say which transport it means.
    Falls back to the profile for a hand-built token with no squad."""
    squad = getattr(transport_token, "squad", None)
    if squad is not None and getattr(squad, "name", None):
        return squad.name
    return getattr(transport_token.profile, "name", "transport")


def transport_capacity_used(transport_token, assigned_squads):
    """How much of `transport_token`'s capacity `assigned_squads` take up
    (rule 18.01, counting MEGA ARMOUR models as 2)."""
    return sum(_model_capacity_cost(m) for s in assigned_squads for m in s.models)


def embark_errors(squad, transport_token, already_assigned=()):
    """Why `squad` cannot start the battle embarked within `transport_token`
    (rule 18.01). Empty list = allowed. `already_assigned` is the squads
    already declared for this same TRANSPORT, so capacity is checked against
    the whole declared load rather than one unit at a time."""
    errors = []
    if squad is None or transport_token is None or transport_token.squad is None:
        return ["No transport selected."]
    # Named by its unit throughout, so a message about one of two identical
    # Trukks says which one - see transport_name().
    name = transport_name(transport_token)
    if not transport_token.profile.transport:
        return [f"{name} is not a TRANSPORT."]
    if squad is transport_token.squad:
        return ["A unit cannot embark within itself."]
    if any(m.profile.transport for m in squad.models):
        # Same simplification TransportController.can_embark() makes: a
        # TRANSPORT never embarks within another one.
        errors.append(f"{squad.name} is a TRANSPORT and cannot embark within another one.")
    if squad.embarked_in is not None:
        errors.append(f"{squad.name} is already embarked.")
    if transport_token.profile.transport_requires_infantry and not all(m.profile.infantry for m in squad.models):
        # e.g. Devilfish: "T'AU EMPIRE INFANTRY models" - the INFANTRY half
        # only, see TransportController's class docstring on why the faction
        # half isn't checkable here either.
        errors.append(f"{name} can only transport INFANTRY models.")
    excluded = transport_token.profile.transport_excludes
    if excluded and any(getattr(m.profile, kw, False) for m in squad.models for kw in excluded):
        errors.append(f"{name} cannot transport {squad.name}.")

    capacity = transport_token.profile.transport_capacity
    used = transport_capacity_used(transport_token, already_assigned)
    needed = sum(_model_capacity_cost(m) for m in squad.models)
    if used + needed > capacity:
        errors.append(
            f"{name} has room for {capacity - used} more "
            f"model(s), {squad.name} needs {needed}."
        )
    return errors


def eligible_transports(squad, transport_tokens, assignments):
    """Every TRANSPORT token `squad` could legally be declared into.
    `assignments` maps id(transport_token) -> list of squads already
    declared into it."""
    return [
        t for t in transport_tokens
        if not embark_errors(squad, t, assignments.get(id(t), ()))
    ]


def reserve_limit_errors(all_units, reserve_units):
    """Rule 20.01: you cannot place more than half of your units, and cannot
    place units whose combined points are more than half of your army's, into
    Strategic Reserves.

    The points half is skipped entirely if ANY unit is unpriced, following
    this codebase's "None is infectious" convention (see
    attached_units.attach and game/factions/points.py): silently treating an
    unpriced unit as 0 points would let a whole army into reserves through a
    missing data entry rather than a rules decision."""
    errors = []
    all_units = list(all_units)
    reserve_units = list(reserve_units)
    if not all_units:
        return errors

    if len(reserve_units) * 2 > len(all_units):
        errors.append(
            f"Rule 20.01: no more than half your units can start in Strategic Reserves "
            f"({len(reserve_units)} of {len(all_units)})."
        )

    if all(getattr(u, "points", None) is not None for u in all_units):
        total = sum(u.points for u in all_units)
        reserved = sum(u.points for u in reserve_units)
        if reserved * 2 > total:
            errors.append(
                f"Rule 20.01: no more than half your army's points can start in Strategic "
                f"Reserves ({reserved} of {total} pts)."
            )
    return errors


def can_add_to_reserves(squad, all_units, reserve_units):
    """Whether declaring one more unit into Strategic Reserves would still
    satisfy rule 20.01. The UI uses this to decide whether to even draw the
    Reserves button - an option that would be rejected shouldn't be offered."""
    if squad in reserve_units:
        return True
    return not reserve_limit_errors(all_units, list(reserve_units) + [squad])
