"""Rule 03.01's Declare Battle Formations step: before anything is deployed,
each player declares which units start embarked within which TRANSPORTs
(18.01), which units start in Strategic Reserves (20.01), and which SUPPORT
WEAPON platforms join a Guardian Defenders unit ("Support Artillery").

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

from game import attached_units
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


def embark_errors(squad, transport_token, already_assigned=(), joining=()):
    """Why `squad` cannot start the battle embarked within `transport_token`
    (rule 18.01). Empty list = allowed. `already_assigned` is the squads
    already declared for this same TRANSPORT, so capacity is checked against
    the whole declared load rather than one unit at a time. `joining` is the
    SUPPORT WEAPON platforms already declared to join `squad`, which the
    printed Support Artillery text forbids embarking."""
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
    # "This model, AND ANY UNIT IT IS JOINED TO, cannot embark within a
    # TRANSPORT" (Support Artillery, second sentence). can_embark() has
    # enforced this since the platforms were built; 18.01 did NOT, so the
    # pre-game step would happily declare a D-cannon into a Wave Serpent and
    # only the mid-battle rule would ever have objected. One rule, two
    # readers, and only one of them answering.
    if any(getattr(m.profile, "cannot_embark", False) for m in squad.models):
        errors.append(f"{squad.name} cannot embark within a TRANSPORT.")
    # The "any unit it is joined to" half at DECLARATION time. After the join
    # resolves, the merged unit carries the platform's own model and the test
    # above answers it; between the two declarations it does not exist yet,
    # which is exactly the window the pre-game step lives in.
    for platform in joining or ():
        errors.append(
            f"{squad.name} cannot embark within a TRANSPORT while "
            f"{platform.name} is joined to it."
        )
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


def eligible_transports(squad, transport_tokens, assignments, joining=()):
    """Every TRANSPORT token `squad` could legally be declared into.
    `assignments` maps id(transport_token) -> list of squads already
    declared into it."""
    return [
        t for t in transport_tokens
        if not embark_errors(squad, t, assignments.get(id(t), ()), joining)
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


# --- Support Artillery (the SUPPORT WEAPON platforms) ---------------------
#
# PRINTED, word for word: "At the start of the Declare Battle Formations step,
# this model can join one GUARDIAN DEFENDERS unit from your army (a unit cannot
# have more than one SUPPORT WEAPON model joined to it). This model then counts
# as part of that GUARDIANS unit for the rest of the battle, and that unit's
# Starting Strength is increased accordingly."
#
# WHY IT LIVES HERE AND NOT AT LIST-BUILD TIME. The engine could already FORM
# this attachment - rule 19.01's SUPPORT role, can_attach() and the pairing
# table have been in place since the platforms were built, and an armies/*.json
# entry can name one under `leaders`. What did not exist was the DECISION: the
# printed text puts it in the Declare Battle Formations step, beside the
# transport and Reserves declarations, and a list that bakes it in answers a
# question the player is supposed to be asked. User: "im pre game muss man sich
# entscheiden ob die Support weapons (d-cannons) an einen Guardian Trupp
# angeschlossen werden sollen oder allein stehen. ähnlich wie man im pregame
# Einheiten in Transporter steckt."
#
# So this is the honest-eligibility half, in the module both the panel and the
# AI already read: one implementation of "legal", two choosers.

#: "A unit cannot have more than one SUPPORT WEAPON model joined to it."
MAX_SUPPORT_WEAPONS_PER_UNIT = 1


def is_support_platform(squad):
    """Whether `squad` is a unit that joins via Support Artillery.

    ASKED OF THE SUPPORT WEAPON KEYWORD, AND THAT IS A CORRECTION. It used to
    read the ATTACHMENT ROLE - "is every model in this unit a SUPPORT model"
    (24.34) - which was exact while the three Aeldari platforms were the only
    SUPPORT-role units in the game. They are not any more: the Necron Crypteks
    print "CORE: Support" too, and the day their profiles started carrying the
    matching role the pre-game panel began offering all five of them a Support
    Artillery join.

    That is the wrong question, because the join is not a property of the
    Support ability at all. It is a printed clause on THREE datasheets ("At
    the start of the Declare Battle Formations step, this model can join one
    GUARDIAN DEFENDERS unit from your army"), and every other Support model
    attaches at list-building time instead. The SUPPORT WEAPON keyword is
    what those three share and what the clause is printed beside, so a fourth
    platform is still covered by building it rather than by editing a list -
    the property the old reading was chosen for, kept.

    MEASURED, not assumed: the three platforms set `support_weapon` and print
    the keyword; the five Crypteks set neither."""
    return (squad is not None and getattr(squad, "models", None)
            and attached_units.unit_has_keyword(
                squad, lambda m: getattr(m.profile, "support_weapon", False)))


def support_join_errors(platform, target, already_joined=(), target_destination=None):
    """Why `platform` cannot join `target` at Declare Battle Formations.
    Empty list = allowed.

    `already_joined` is the platforms already declared into this same target,
    which is what makes the printed one-per-unit limit checkable while the
    declarations are still being collected. `target_destination` is the
    target's own declaration, if it has one yet.

    The PAIRING is delegated to can_attach() rather than re-derived: that is
    the one place rule 19.01's legality lives, and it reads the printed
    "SUPPORT: ..." line out of the points list. Everything added here is a
    condition of the Declare Battle Formations step itself, which can_attach()
    has no business knowing about."""
    if platform is None or target is None:
        return ["No unit selected."]
    if not is_support_platform(platform):
        return [f"{platform.name} is not a SUPPORT WEAPON unit."]
    if platform is target:
        return ["A unit cannot join itself."]
    if getattr(platform, "owner", None) != getattr(target, "owner", None):
        return [f"{target.name} is not from your army."]

    errors = list(attached_units.can_attach(platform, target))
    if len(already_joined) >= MAX_SUPPORT_WEAPONS_PER_UNIT and platform not in already_joined:
        errors.append(
            f"{target.name} already has a SUPPORT WEAPON model joined to it."
        )
    # The transport ban, from the joining side. The platform cannot embark, and
    # neither can the unit it joins - so a target already declared into a
    # TRANSPORT is not a legal host, and refusing here is what keeps the two
    # declarations from contradicting each other whichever order they arrive
    # in (embark_errors() refuses the mirror case).
    if target_destination == "embark":
        errors.append(f"{target.name} is declared to start embarked in a TRANSPORT.")
    return errors


#: Which printed rule lets a unit join another at Declare Battle Formations.
#: TWO of them now, and they are genuinely different rules rather than one
#: mechanism with two names - Support Artillery is printed on three SUPPORT
#: WEAPON platforms and names GUARDIAN DEFENDERS; Cryptek Retinue is printed on
#: the Cryptothralls and names "a unit being led by a CRYPTEK INFANTRY model".
#: The panel heading says which, because "Support Artillery" over a
#: Cryptothralls offer would name the wrong rule.
SUPPORT_ARTILLERY = "Support Artillery"
CRYPTEK_RETINUE = "Cryptek Retinue"


def join_rule_label(joiner):
    """The printed rule that lets `joiner` join something, or None.

    THREE rules now, not two: the Canoptek Tomb Crawlers print "Canoptek
    Retinue" where the Cryptothralls print "Cryptek Retinue", and the panel
    heading has to say which - naming the wrong one over an offer is exactly
    what this function exists to prevent."""
    if is_support_platform(joiner):
        return SUPPORT_ARTILLERY
    from game import retinue
    carrier = retinue.carrier_of(joiner)
    return carrier[0] if carrier else None


def eligible_join_targets(platform, army, joins=None, destinations=None):
    """Every unit in `army` that `platform` could legally join.

    `joins` maps id(target) -> the units already declared into it;
    `destinations` maps id(unit) -> its own declaration.

    DISPATCHES ON THE RULE, because there are two of them now and their extra
    conditions are not the same one: the platforms' limit is one SUPPORT WEAPON
    MODEL per unit and a ban on joining a unit bound for a TRANSPORT, the
    retinue's is one CRYPTOTHRALLS UNIT per host and a host led by a Cryptek.
    Both delegate rule 19.01 itself to can_attach(), which is the one place it
    lives."""
    joins = joins or {}
    destinations = destinations or {}
    from game import retinue
    carrier = retinue.carrier_of(platform)
    if carrier is not None:
        label, require_infantry = carrier
        return retinue.eligible_hosts(platform, army, joins,
                                      require_infantry=require_infantry,
                                      unit_label=label)
    if join_rule_label(platform) is None:
        return []
    return [
        unit for unit in army
        if not support_join_errors(platform, unit, joins.get(id(unit), ()),
                                   destinations.get(id(unit)))
    ]
