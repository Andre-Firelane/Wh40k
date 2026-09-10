"""Attached Units - rules 19.01-19.04, plus the two core abilities that
form them: Leader (24.22) and Support (24.34).

WHAT AN ATTACHED UNIT IS, AND HOW IT'S MODELED HERE

Rule 19.01: "An attached unit is a single unit for all rules purposes."
That sentence decides the entire representation. Rather than inventing a
second kind of unit that the ~40 modules touching Squad would each have to
learn about, forming an attached unit MERGES the leader/support unit's
models into the bodyguard unit's own Squad.models and throws the leader's
Squad object away. There is then genuinely one Squad, so every rule that
already operates on a Squad - targeting, coherency, movement, charging,
Reserves, embarking, objective control, Battle-Shock - is correct for
attached units without knowing they exist. Three of the user's four
requirements for this feature (reserves arrive together, transports carry
them together, the AI can't shoot the character out of the squad) are
consequences of that one decision rather than separate features.

What the merge costs, and what this module therefore has to provide, is
everything that DOESN'T pool: a Squad had been implicitly homogeneous
(one profile, one base size, one set of abilities) and now isn't.

- 19.02 wants the bodyguard models' Toughness even when the leader's
  differs, and wants "unit destroyed" triggers held back until the last
  model that STARTED the battle in the attached unit is gone.
- 19.03 pools KEYWORDS across components (any-model semantics) while
  leaving per-model keyword grants alone.
- 19.04 scopes ABILITIES to their source: a leader's ability applies to
  the whole attached unit until the last model of the LEADER unit dies -
  not until the attached unit dies - and a bodyguard ability likewise
  lasts only while a bodyguard model lives. That's a question about the
  component a model came from, which the merged models list alone can no
  longer answer, hence AttachedComponent below.

Provenance is therefore kept explicitly, in Squad.attached_components:
one AttachedComponent per unit that went into the merge, each holding the
models it contributed AS OF FORMATION - deliberately a private list that
is never pruned, because both 19.02 and 19.04 ask about models that
started the battle here, and GameState.remove_dead_models() strips dead
models out of Squad.models.

WHAT IS NOT MODELED

Rule 19.01/24.22 place the attachment decision "before the battle, in the
Muster Armies step". This engine has no army-building or deployment flow
(see CLAUDE.md's Spaeter-Liste), so attach() is called directly by the
scene that builds the armies (main.py), which is the same convention every
other pre-battle fact here already uses. can_attach() still enforces the
rule's legality conditions, so a scene can't form an attachment the rules
wouldn't allow.

Enhancements are not modeled at all (no enhancement system exists), so
19.04's "abilities that affect a single specified model" case is
represented only by wargear, which is already per-model by construction -
a Token's own profile flags and weapons - and so needs no support here.
"""

LEADER = "leader"
SUPPORT = "support"
#: The Cryptothralls' Cryptek Retinue - a whole non-character UNIT joining a
#: bodyguard unit. ITS OWN ROLE rather than a second kind of SUPPORT, and that
#: is what buys the printed "(a unit cannot have more than one CRYPTOTHRALLS
#: unit joined to it)" for free: 19.01's one-unit-per-ROLE check below then
#: enforces it, while a retinue and a Cryptek can still attach side by side.
RETINUE = "retinue"
BODYGUARD = "bodyguard"


class AttachedComponent:
    """One of the units that were merged to form an attached unit (19.01),
    remembered so 19.02 and 19.04 can still tell the components apart after
    the merge.

    `starting_models` is this component's contribution as of formation and
    is never pruned - "the last model that started the battle in an
    attached unit" (19.02) and "the last model in that leader/support unit
    is destroyed" (19.04) are both questions about the ORIGINAL roster, and
    a dead model is removed from Squad.models by
    GameState.remove_dead_models() but keeps its Token object (and its
    current_wounds of 0) alive, so holding the reference here answers both
    correctly."""

    def __init__(self, name, role, models, points=None, datasheet=None):
        self.name = name
        self.role = role  # LEADER / SUPPORT / BODYGUARD
        self.starting_models = list(models)
        self.points = points
        self.datasheet = datasheet

    @property
    def is_leader_or_support(self):
        return self.role in (LEADER, SUPPORT)

    def alive_models(self):
        return [m for m in self.starting_models if not m.is_dead()]

    def is_destroyed(self):
        """Every model this component brought to the attached unit is dead.
        Note this is about the component, not the attached unit - a
        destroyed leader component sits inside a very much alive attached
        unit, which is exactly the distinction 19.04 turns on."""
        return all(m.is_dead() for m in self.starting_models)

    def __repr__(self):
        return f"<AttachedComponent {self.name} ({self.role}), {len(self.alive_models())}/{len(self.starting_models)} alive>"


# --- Forming attached units (19.01, 24.22, 24.34) ---


def _points_entry(squad):
    datasheet = getattr(squad, "datasheet", None)
    return getattr(datasheet, "points", None) if datasheet is not None else None


def _datasheet_name(squad):
    datasheet = getattr(squad, "datasheet", None)
    return datasheet.name if datasheet is not None else None


def attachment_role(squad):
    """LEADER, SUPPORT or None: which of the two core abilities (24.22 /
    24.34) this unit has, read off its models' profiles. A unit is only a
    leader/support unit if EVERY model has the ability - both abilities are
    printed on single-model CHARACTER datasheets, so this is really just a
    guard against calling this on a mixed/already-attached squad."""
    if not squad.models:
        return None
    if all(m.profile.leader for m in squad.models):
        return LEADER
    if all(m.profile.support for m in squad.models):
        return SUPPORT
    # The Cryptothralls' Cryptek Retinue - see RETINUE above. Last, so a model
    # that somehow printed both keeps the answer it had before this existed.
    if all(getattr(m.profile, "cryptek_retinue", False) for m in squad.models):
        return RETINUE
    return None


def leadable_unit_names(squad):
    """Which bodyguard units this leader/support unit may be attached to -
    rule 19.01's "as listed in the Warhammer 40,000 app".

    That list is already transcribed: every points-list entry carries its
    own printed "LEADER: ..." / "SUPPORT: ..." line as UnitPoints.leads /
    .supports (see game/factions/points.py). Reading it here rather than
    re-declaring the pairings on the Datasheet keeps one source of truth -
    the same reason a datasheet reads its wargear prices out of its points
    entry instead of repeating the literals."""
    entry = _points_entry(squad)
    if entry is None:
        return ()
    role = attachment_role(squad)
    if role == SUPPORT:
        return tuple(entry.supports) or tuple(entry.leads)
    return tuple(entry.leads) or tuple(entry.supports)


def is_attached_unit(squad):
    """Whether this Squad was formed by attach() - i.e. genuinely has more
    than one component.

    Deliberately distinct from game.squad.squad_is_attached_unit(), which
    answers the looser "does this unit contain a Leader/Support model"
    question that rule 24.24 (LONE OPERATIVE)'s carve-out actually asks, and
    which predates this module. Both are true for a real attached unit; only
    the older one is (vacuously) true for a lone unattached Character."""
    return len(getattr(squad, "attached_components", ()) or ()) > 1


def components(squad):
    return list(getattr(squad, "attached_components", ()) or ())


def leader_components(squad):
    return [c for c in components(squad) if c.is_leader_or_support]


def bodyguard_components(squad):
    return [c for c in components(squad) if c.role == BODYGUARD]


def leader_models(squad, alive_only=True):
    """Every model contributed by a leader/support component. Falls back to
    reading the profiles directly for a squad that was never formed via
    attach() (e.g. a hand-built test squad), so callers get a sensible
    answer either way."""
    if not components(squad):
        pool = [m for m in squad.models if m.profile.leader or m.profile.support]
        return [m for m in pool if not m.is_dead()] if alive_only else pool
    out = []
    for component in leader_components(squad):
        out.extend(component.alive_models() if alive_only else component.starting_models)
    return out


def bodyguard_models(squad, alive_only=True):
    """The counterpart of leader_models(): every model that came from a
    bodyguard component (19.02's "bodyguard models")."""
    if not components(squad):
        pool = [m for m in squad.models if not (m.profile.leader or m.profile.support)]
        return [m for m in pool if not m.is_dead()] if alive_only else pool
    out = []
    for component in bodyguard_components(squad):
        out.extend(component.alive_models() if alive_only else component.starting_models)
    return out


BODYGUARD_TWO_LEADERS_STRENGTH = 20  # "a Starting Strength of 20"


def _warboss_unit(squad):
    """Whether this leader unit is "a WARBOSS model" - read off the datasheet
    keyword line, since WARBOSS is not one of the handful of keywords modeled
    as a UnitProfile flag (see unit_has_datasheet_keyword())."""
    return unit_has_datasheet_keyword(squad, "WARBOSS")


def _bodyguard_allows_second_leader(bodyguard_squad, incoming, already):
    """Boyz'/Kroot Carnivores' "Bodyguard" ability, which is exactly the
    "unless otherwise stated" escape hatch rule 19.01 leaves open:

        "If this unit has a Starting Strength of 20, you can attach up to two
         Leader units to it instead of one (but only if one of those is a
         WARBOSS model)."

    Three conditions, each read where the rule points:

    * the ability belongs to the BODYGUARD unit, so it is read off the
      bodyguard components only. unit_wide_ability() would be wrong here and
      not subtly: by the time a SECOND leader is offered the unit already
      contains the first, who does not have the ability - the same trap 19.04
      exists to avoid, and the reason every squad_has_*() predicate in this
      codebase stopped being a plain all().
    * "a Starting Strength of 20" likewise means the bodyguard unit's own,
      not the merged unit's - attach() re-derives Squad.starting_model_count
      across every component, so that number is already 21 once one leader is
      on board.
    * "only if one of those is a WARBOSS": satisfied by either the leader
      already attached or the one arriving now.

    Only ever WIDENS what is legal, so a datasheet without the ability behaves
    exactly as before. This used to be refused outright on the grounds that
    abilities_text is display-only - correct while nothing needed it, but the
    fix for that is a real flag (UnitProfile.bodyguard_two_leaders), not a
    permanent refusal.

    NOTE the ability's second sentence - the attached Leaders becoming
    separate units again if the mob is destroyed - is still not implemented;
    it needs a runtime split of an attached unit, which nothing else in 19.x
    asks for. Documented gap, unchanged by this.
    """
    bodyguards = bodyguard_models(bodyguard_squad, alive_only=False)
    if not bodyguards or not all(m.profile.bodyguard_two_leaders for m in bodyguards):
        return False
    if len(bodyguards) != BODYGUARD_TWO_LEADERS_STRENGTH:
        return False
    if len(already) >= 2:  # "up to two", not more
        return False
    if not (_warboss_unit(incoming) or any(_warboss_unit(c) for c in already)):
        return False
    return True


def _warlocks_unit(squad):
    """Whether this leader unit is "a WARLOCKS unit" - read off the datasheet
    keyword line, like _warboss_unit() and for the same reason (WARLOCKS is
    not one of the handful of keywords modeled as a UnitProfile flag)."""
    return unit_has_datasheet_keyword(squad, "WARLOCKS")


def _leader_allows_joining_led_unit(incoming, already):
    """Eldrad Ulthran's own LEADER line, which is rule 19.01's "unless
    otherwise stated" escape hatch reached from the OTHER side:

        "If this model is not already attached to a unit, you can attach this
         model to a unit, even if one WARLOCKS unit has already been attached
         to it."

    THE MIRROR IMAGE of _bodyguard_allows_second_leader() above, and the
    difference is which datasheet the permission is printed on:

      * Boyz'/Kroot Carnivores' "Bodyguard" says "TWO leaders may attach to
        ME", so it is read off the BODYGUARD unit, and its condition is about
        what the arriving leader is (a WARBOSS).
      * this says "I may attach even if something is already there", so it is
        read off the INCOMING LEADER, and its condition is about what is
        ALREADY attached (a WARLOCKS unit).

    Getting that direction wrong would grant the permission to the wrong
    datasheet: this clause is Eldrad's, and it is what lets HIM be the second
    unit on a Conclave-joined bodyguard. The reverse direction - a Conclave
    joining a unit that a Farseer already leads - is legal for a completely
    different reason and is NOT this clause; see
    _join_not_bound_by_leader_slot() below.

    "EVEN IF ONE WARLOCKS UNIT" - exactly one, and it must be the WARLOCKS
    unit. So this widens one leader to two and no further, and only for that
    specific pairing; a unit already led by anything else is untouched.

    "IF THIS MODEL IS NOT ALREADY ATTACHED TO A UNIT" is not re-checked here:
    can_attach() already refuses an incoming leader that is itself an attached
    unit, a few lines above, for every leader alike.

    Only ever WIDENS what is legal, so a datasheet without the flag behaves
    exactly as before.

    WHY THIS MATTERS BEYOND THE ATTACHMENT: it is what finally makes Warlock
    Conclave's Protect reachable. Protect needs a FARSEER model leading a unit
    that contains Warlocks, and until this clause there was no legal way to
    build one - a Conclave is itself a leader unit, so no Farseer could attach
    to it, and no bodyguard datasheet here prints the two-leader permission.
    Eldrad is a FARSEER and this clause lets him be the second leader on a unit
    a Conclave has already joined. See game/protect.py.
    """
    if not any(getattr(m.profile, "joins_warlock_led_unit", False)
               for m in getattr(incoming, "models", None) or ()):
        return False
    if len(already) != 1:
        return False
    return _warlocks_unit(already[0])


def _join_not_bound_by_leader_slot(incoming, already):
    """The Warlock Conclave's LEADER ability, which is not worded as an
    attachment at all:

        "At the start of the Declare Battle Formations step, if this unit is
         not an Attached unit, this unit can join one GUARDIAN DEFENDERS or
         STORM GUARDIANS unit from your army (a unit cannot have more than one
         WARLOCK CONCLAVE unit joined to it). If it does, until the end of the
         battle, every model in this unit counts as being part of that
         Bodyguard unit, and that Bodyguard unit's Starting Strength is
         increased accordingly."

    It states its OWN limit, and that limit is one Conclave per unit - not
    19.01's one-leader-per-bodyguard default, which the rule itself prefixes
    with "unless otherwise stated". So a Conclave may join a unit a Farseer
    already leads.

    THE ASYMMETRY IS DELIBERATE, and it is what the two printed texts together
    say rather than a convenience:

      * Conclave joining a Farseer-led unit: allowed here, because the
        Conclave's own restriction says nothing about other leaders.
      * Farseer attaching to a Conclave-joined unit: still refused, because
        that IS an ordinary 19.01 attachment. Eldrad Ulthran's LEADER line
        overrides it explicitly ("even if one WARLOCKS unit has already been
        attached to it") and a plain Farseer's does not - fetched verbatim
        from both datasheets rather than assumed either way.

    Which means the ORDER matters for a plain Farseer: Farseer first, then
    Conclave. main.py's Player 1 roster attaches them in that order and says
    why. If Eldrad's clause did not exist this asymmetry would be
    unmotivated - his clause is the evidence that a Conclave-joined unit does
    block an ordinary leader.

    Only ever WIDENS what is legal, so a datasheet without the flag behaves
    exactly as before.
    """
    if not any(getattr(m.profile, "joins_without_leader_slot", False)
               for m in getattr(incoming, "models", None) or ()):
        return False
    # "A unit cannot have more than one WARLOCK CONCLAVE unit joined to it" -
    # the one restriction it does print. Asked of the components already
    # attached, which is the granularity a datasheet keyword line has (19.01's
    # merge keeps each component's datasheet) - see unit_has_datasheet_keyword().
    return not any(_warlocks_unit(component) for component in already)


def can_attach(leader_squad, bodyguard_squad):
    """Rule 19.01/24.22/24.34's legality conditions, as a list of reasons it
    is NOT allowed (empty list = allowed) - the same shape as Squad's own
    check_*() methods, so a caller can surface the reason rather than a bare
    False."""
    errors = []
    role = attachment_role(leader_squad)
    if role is None:
        errors.append(f'"{leader_squad.name}" has neither the Leader (24.22) nor the Support (24.34) ability.')
    if leader_squad is bodyguard_squad:
        errors.append("A unit cannot be attached to itself.")
        return errors
    if leader_squad.owner != bodyguard_squad.owner:
        errors.append("A leader can only be attached to a friendly unit (19.01).")
    if is_attached_unit(leader_squad):
        errors.append(f'"{leader_squad.name}" is already an attached unit.')
    if attachment_role(bodyguard_squad) is not None:
        errors.append(f'"{bodyguard_squad.name}" is itself a leader/support unit, not a bodyguard unit (19.01).')

    # "Unless otherwise stated, each bodyguard unit can only have one leader
    # unit and one support unit attached to it" (19.01). The exception the rule
    # leaves room for is real and is printed on FIVE datasheets here, in THREE
    # shapes: Boyz' and Kroot Carnivores' "Bodyguard" grants it from the
    # bodyguard side, Eldrad Ulthran's LEADER line from the incoming-leader
    # side, and Warlock Conclave's LEADER ability is not an attachment at all
    # but a JOIN that states its own limit.
    # Each helper carries its own conditions and why the direction matters.
    if role is not None:
        # components(), NOT leader_components(): that helper answers "which
        # components are a leader or a support", and RETINUE is a THIRD role
        # (game/retinue.py) which it deliberately excludes - a Cryptothralls
        # unit is not a character and must not be counted among a unit's
        # leader models by 05.03/[PRECISION]. Reading it here meant this check
        # never SAW a retinue, so BOTH of the printed parentheses that stage 2
        # said it gave for free - "a unit cannot have more than one
        # CRYPTOTHRALLS unit joined to it" and "cannot have both a TOMB
        # CRAWLERS and a CRYPTOTHRALLS unit joined to it" - were unenforced.
        # Byte-identical for LEADER and SUPPORT by construction: this filters
        # the same components by the same role, one helper earlier.
        already = [c for c in components(bodyguard_squad) if c.role == role]
        if already and not (role == LEADER and (
                _bodyguard_allows_second_leader(bodyguard_squad, leader_squad, already)
                or _leader_allows_joining_led_unit(leader_squad, already)
                or _join_not_bound_by_leader_slot(leader_squad, already))):
            label = {LEADER: "leader", SUPPORT: "support"}.get(role, "retinue")
            errors.append(
                f'"{bodyguard_squad.name}" already has a {label} unit attached '
                f'("{already[0].name}") - 19.01 allows only one of each.'
            )

    # 19.01: "Leader and support units can only lead specific bodyguard
    # units". Only enforced when we actually know the pairing table - a
    # datasheet with no points entry (an untranscribed faction) would
    # otherwise be unattachable to anything at all, which is worse than
    # being unchecked.
    allowed = leadable_unit_names(leader_squad)
    target_datasheet = _datasheet_name(bodyguard_squad)
    if allowed and target_datasheet is not None and target_datasheet not in allowed:
        # LEAD or JOIN, by role. A SUPPORT unit does not lead anything - its
        # printed text says "join" - and this message became player-facing the
        # day Support Artillery got its Declare Battle Formations offer, where
        # it is the reason a Guardian unit is not on the list.
        # A retinue joins as well - its printed text says "can join one other
        # unit", the same word the SUPPORT platforms use.
        verb = "lead" if attachment_role(leader_squad) == LEADER else "join"
        errors.append(
            f'"{leader_squad.name}" cannot {verb} "{bodyguard_squad.name}" - '
            f'it may only {verb}: {", ".join(allowed)} (19.01).'
        )
    return errors


def _component_for(squad):
    """The component list `squad` contributes to a merge: its own components
    if it is already an attached unit, otherwise a single component standing
    for the whole unit."""
    existing = components(squad)
    if existing:
        return existing
    role = attachment_role(squad) or BODYGUARD
    return [AttachedComponent(
        squad.name, role, squad.models,
        points=squad.points, datasheet=getattr(squad, "datasheet", None),
    )]


def attached_unit_name(bodyguard_squad, leader_squads):
    """Display/identity name for the formed unit. The bodyguard's name stays
    the stem so existing references (and the AI's plan orders, which address
    units by exact name) still recognise it, with the attached characters
    named after it - a player and the planner both need to see at a glance
    that the character is in there."""
    joined = ", ".join(_datasheet_name(s) or s.name for s in leader_squads)
    return f"{bodyguard_squad.name} + {joined}"


def attach(leader_squad, bodyguard_squad, game_state=None, game_log=None, force=False):
    """Form an attached unit (19.01) from a leader/support unit and a
    bodyguard unit, returning the single surviving Squad (the bodyguard
    one, mutated in place).

    The leader's models are appended to the bodyguard's models list and
    re-pointed at it; the leader Squad object is then removed from wherever
    the game was tracking it (`game_state`: the board, Reserves, or a
    TRANSPORT's passenger list) and is dead afterwards - callers must not
    keep using it. Appending rather than prepending keeps models[0] a
    bodyguard model, which is both the right representative for 19.02's
    Toughness and what the many `squad.models[0]`-as-representative call
    sites throughout the AI already want.

    `force=True` skips can_attach()'s legality check - for tests and for a
    scene that deliberately wants an attachment the pairing table doesn't
    list. It never skips the structural work.
    """
    if not force:
        errors = can_attach(leader_squad, bodyguard_squad)
        if errors:
            raise ValueError(f"Cannot attach: {' '.join(errors)}")

    leader_parts = _component_for(leader_squad)
    bodyguard_parts = _component_for(bodyguard_squad)

    # Take both model lists BEFORE mutating anything: `incoming` so an
    # already-attached leader squad (not reachable today, but the structure
    # allows it) contributes all of its models, and `host_models` because
    # _detach_squad_object() below has to ask where the BODYGUARD is, which
    # is unanswerable once the two lists have been merged.
    incoming = list(leader_squad.models)
    host_models = list(bodyguard_squad.models)
    for model in incoming:
        model.squad = bodyguard_squad
    bodyguard_squad.models.extend(incoming)

    bodyguard_squad.attached_components = bodyguard_parts + leader_parts
    bodyguard_squad.starting_model_count = sum(
        len(c.starting_models) for c in bodyguard_squad.attached_components
    )
    # An attached unit's cost is simply the sum of its components' - each
    # was bought separately in the list. None stays infectious: one
    # unpriced component makes the whole unit unpriced rather than
    # understating it (see game/factions/points.py).
    part_costs = [c.points for c in bodyguard_squad.attached_components]
    bodyguard_squad.points = None if any(p is None for p in part_costs) else sum(part_costs)

    absorbed_name = leader_squad.name
    bodyguard_squad.name = attached_unit_name(bodyguard_squad, [leader_squad])

    if game_state is not None:
        _detach_squad_object(leader_squad, host_models, incoming, game_state)
    leader_squad.models = []
    leader_squad.absorbed_into = bodyguard_squad

    if game_log is not None:
        game_log.add(
            f"{bodyguard_squad.owner}: {absorbed_name} is attached to form "
            f"{bodyguard_squad.name} (rule 19.01)."
        )
    return bodyguard_squad


def _detach_squad_object(leader_squad, host_models, incoming, game_state):
    """Drop the now-absorbed leader Squad from every list the game tracks
    units in, and make sure its models are in the same PLACE as the unit
    they just joined.

    That second half is the part it would be easy to miss. A unit lives in
    exactly one of three places - on the battlefield (its models are in
    GameState.tokens), in Reserves, or embarked in a TRANSPORT (models NOT
    in tokens either way) - and the two units being merged need not have
    started in the same one. Attaching a deployed Character to a unit held
    in Reserves would otherwise leave that Character's models on the board
    while the unit they belong to is off it: visible, targetable, and part
    of a squad that is supposed to be elsewhere. Rule 19.01's "a single unit
    for all rules purposes" has to include being in one place, so the
    leader's models follow the bodyguard's, which is the location the
    attached unit keeps.

    "Where is the bodyguard" is answered by whether its OWN models are in
    GameState.tokens - deliberately not by looking it up in
    reserves/embarked_squads. Those lists are maintained by the caller, and
    a scene very reasonably builds a unit, attaches its character, and only
    THEN registers it as embarked. Reading the lists made the answer depend
    on that ordering, and got it wrong for every attachment in the demo
    scene: each attached unit ended up embarked or in Reserves with its
    character alone left standing on the battlefield, whose move then failed
    every turn. Token membership is a fact about the models themselves, so
    it is correct whichever order the caller does things in."""
    if leader_squad in game_state.reserves:
        game_state.reserves.remove(leader_squad)
    if leader_squad in game_state.embarked_squads:
        game_state.embarked_squads.remove(leader_squad)

    host_on_board = any(m in game_state.tokens for m in host_models)
    for model in incoming:
        on_board = model in game_state.tokens
        if host_on_board and not on_board:
            game_state.add_token(model)
        elif not host_on_board and on_board:
            game_state.tokens.remove(model)


def attach_all(pairs, game_state=None, game_log=None, force=False):
    """Convenience for a scene forming several attached units at once:
    `pairs` is [(leader_squad, bodyguard_squad), ...]. Returns the list of
    formed units, in the order given."""
    return [attach(leader, bodyguard, game_state=game_state, game_log=game_log, force=force)
            for leader, bodyguard in pairs]


# --- 19.02 Attacking attached units ---


def unit_is_destroyed(squad):
    """Rule 19.02: "Rules that are triggered when a unit is destroyed are
    only triggered when the last model that started the battle in an
    attached unit is destroyed."

    For an ordinary unit this is just "no models left", which is what every
    caller already meant; for an attached unit it deliberately does NOT fire
    when merely the leader component (or merely the bodyguard component) is
    wiped out."""
    parts = components(squad)
    if not parts:
        return not [m for m in squad.models if not m.is_dead()]
    return all(c.is_destroyed() for c in parts)


# --- 19.04 Abilities in attached units ---


def _grace_active(squad):
    """19.04's trailing clause: "if that last model was destroyed as the
    result of an attack, the ability it was conferring upon the attached
    unit applies until the attacking unit has resolved all of its attacks."
    begin_attack_sequence()/end_attack_sequence() bracket one attacking
    unit's activation around that."""
    return bool(getattr(squad, "attached_ability_grace", False))


def begin_attack_sequence(squad):
    """Called when an attacking unit starts resolving attacks against
    `squad`: from here until end_attack_sequence(), a component whose last
    model dies keeps conferring its abilities (19.04)."""
    if squad is not None and is_attached_unit(squad):
        squad.attached_ability_grace = True


def end_attack_sequence(squad):
    """Called once the attacking unit has resolved ALL of its attacks -
    game/shooting.py's _actually_finish_squad() and game/fight.py's
    equivalent, the same points rule 24.15 ([HAZARDOUS]) already treats as
    "after that unit has resolved all of its attacks"."""
    if squad is not None:
        squad.attached_ability_grace = False


def confers_abilities(component, squad):
    """Whether `component` is still granting its abilities to the attached
    unit (19.04's table): until its own last model is destroyed, plus the
    grace window above.

    Note the asterisked row of that table - a leader/support unit "continues
    to benefit from their own 'while this model is leading a unit' abilities
    even after their bodyguard unit is destroyed, provided they started the
    battle in an attached unit". That falls out for free here: a component's
    lifetime depends only on ITS OWN models, so a surviving leader keeps
    conferring after every bodyguard model is gone."""
    return not component.is_destroyed() or _grace_active(squad)


def ability_source_models(squad):
    """Every model whose abilities currently apply to the whole attached
    unit (19.04) - i.e. the models of every component still conferring.

    This is the function the unit-wide ability predicates should consult
    instead of squad.models: it excludes a wiped-out component's models
    (which are also gone from squad.models, so that part is moot) but, more
    importantly, it is the hook where the grace window keeps a just-killed
    component's ability alive for the rest of the attacker's activation."""
    parts = components(squad)
    if not parts:
        return [m for m in squad.models if not m.is_dead()]
    out = []
    for component in parts:
        if confers_abilities(component, squad):
            out.extend(component.starting_models if _grace_active(squad) else component.alive_models())
    return out


def leader_ability(squad, attribute):
    """The counterpart of game/squad.py's unit_wide_ability() for the OTHER
    shape a datasheet ability comes in: "while this model is LEADING a unit,
    <the whole unit gets X>" (Cadre Fireblade's Volley Fire, Warboss's Might
    is Right, Coldstar Commander's own named ability).

    unit_wide_ability() is wrong for these, and not subtly: it asks whether
    EVERY model is printed with the ability, and for a leader ability none of
    the bodyguards are - that is the entire point of one. Every such predicate
    written that way would be False for every unit that actually has it.

    Two conditions, both straight from the wording:
    - "while this model is LEADING a unit" - a Character standing on its own
      is not leading anything, so a real attached unit (19.01) is required,
      not merely a squad that contains the model. Exactly the false positive
      game/squad.py's squad_is_attached_unit() documents for rule 24.24.
    - the granting model has to still be conferring. ability_source_models()
      is 19.04's own answer, and it brings 19.04's grace window
      ("...applies until the attacking unit has resolved all of its attacks")
      along for free, so a leader killed mid-sequence does not silently shrink
      the rest of his unit's attacks.

    Lives here rather than beside unit_wide_ability() because this module has
    no imports of its own, which lets the per-ability modules that need it
    (game/volley_fire.py, game/coldstar.py) depend on it without importing
    game/squad.py and creating a cycle."""
    if not is_attached_unit(squad):
        return False
    return any(getattr(m.profile, attribute) for m in ability_source_models(squad))


def unit_has_ability(squad, predicate):
    """Rule 19.04's default: "abilities/rules that affect a unit (or models
    in it) apply to every model in an attached unit, until the source of
    that ability/rule is destroyed".

    So a unit-wide ability holds if EVERY model of ANY still-conferring
    component has it - the component is the source, and it grants to the
    whole attached unit. For a plain unit this collapses to the familiar
    all(...) over its models, which is why the existing squad_has_*()
    helpers can delegate here without changing behaviour for the ordinary
    case."""
    parts = components(squad)
    if not parts:
        alive = [m for m in squad.models if not m.is_dead()] or squad.models
        return bool(alive) and all(predicate(m) for m in alive)
    for component in parts:
        if not confers_abilities(component, squad):
            continue
        pool = component.starting_models if _grace_active(squad) else component.alive_models()
        if pool and all(predicate(m) for m in pool):
            return True
    return False


# --- 19.03 Keywords in attached units ---


def unit_has_keyword(squad, predicate):
    """Rule 19.03: "An attached unit has all of the keywords of all of its
    component units. As such, an attached unit is affected by any rule that
    applies to units with any of those keywords."

    Any-model semantics, and deliberately NOT gated on 19.04's ability
    lifetime: a keyword is a property of the models present, so it is gone
    once those models are. The rule's own worked example is [ANTI-PSYKER]
    against an attached unit containing a PSYKER leader - the whole unit is
    a valid target for the rule even though the bodyguard models aren't
    psykers, and "attacks target units, not models"."""
    alive = [m for m in squad.models if not m.is_dead()]
    return any(predicate(m) for m in (alive or squad.models))


def unit_has_datasheet_keyword(squad, keyword):
    """Rule 19.03 again, for a keyword that is printed on the DATASHEET's
    keyword line rather than modeled as a UnitProfile flag (GROTS, MOB,
    BATTLELINE, ...). Only the handful of keywords some rule actually reads
    have their own flag - see game/shooting.py's _KEYWORD_FIELDS and
    CLAUDE.md's Später-Liste on the absent generic keyword system - so
    anything else has to be read off game.factions.Datasheet.keywords.

    Unlike unit_has_keyword() this cannot be a per-model question: a model
    does not know which datasheet it came from. It is answered per COMPONENT
    instead (19.01's merge keeps each one's datasheet on its
    AttachedComponent), which is the same granularity the keyword line has,
    plus squad.datasheet for an ordinary unit that was never merged."""
    sheets = [getattr(squad, "datasheet", None)]
    sheets += [c.datasheet for c in getattr(squad, "attached_components", None) or ()]
    return any(keyword in (getattr(s, "keywords", None) or ()) for s in sheets if s is not None)



def model_has_datasheet_keyword(squad, model, keyword):
    """Whether THIS MODEL carries a datasheet keyword, asked of the COMPONENT
    it came from.

    THE 39TH EXTRACTION, at the second consumer. game/cryptothralls.py wrote
    this out for "that CRYPTEK model" (Bound Creation); Nekrosor Ammentar's
    Infectious Murder-madness asks the identical question for "if that model
    has the DESTROYER CULT keyword", and a second hand-written copy is the
    shape this repo consolidates.

    WHY IT CANNOT BE unit_has_datasheet_keyword() WITH A MODEL: a model does
    not know which datasheet it came from - that function's own docstring says
    so. 19.01's merge keeps each component's datasheet on its
    AttachedComponent, and matching the model against a component's
    `starting_models` is the only granularity at which a per-MODEL keyword
    question can be answered after a merge.

    THE UNMERGED CASE IS THE COMMON ONE and is answered from squad.datasheet:
    a unit that was never merged has no components at all, and every one of
    its models came from that one sheet. Written first so the ordinary path
    costs one lookup.

    A DEAD MODEL IS NOT FILTERED HERE, deliberately: this answers "what is this
    model", not "is it still contributing". Every caller already knows which
    model it is holding, and remove_dead_models() runs once per frame - a
    filter here would make the answer depend on when in the frame it is
    asked."""
    if squad is None or model is None:
        return False
    comps = components(squad)
    if not comps:
        sheet = getattr(squad, "datasheet", None)
        return keyword in (getattr(sheet, "keywords", None) or ())
    for component in comps:
        sheet = getattr(component, "datasheet", None)
        if sheet is None:
            continue
        if keyword not in (getattr(sheet, "keywords", None) or ()):
            continue
        if any(m is model for m in getattr(component, "starting_models", ()) or ()):
            return True
    return False


def unit_has_faction_keyword(squad, keyword):
    """Rule 19.03 once more, for the datasheet's OTHER printed keyword line.

    Same pooling and the same per-COMPONENT granularity as
    unit_has_datasheet_keyword() above - a model does not know which datasheet
    it came from, so an attached unit is answered from the components 19.01's
    merge kept. Separate from that function because the two lines mean
    different things: "KEYWORDS" is what a model IS, "FACTION KEYWORDS" is
    which army it may be taken in. The Aeldari detachments are the first rules
    to ask about the second (ASURYANI), and reading it out of `keywords` would
    have meant writing a faction line into the wrong tuple on 51 datasheets."""
    sheets = [getattr(squad, "datasheet", None)]
    sheets += [c.datasheet for c in getattr(squad, "attached_components", None) or ()]
    return any(keyword in (getattr(s, "faction_keywords", None) or ())
               for s in sheets if s is not None)
