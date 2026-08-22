from game.squad import COHERENCY_RANGE_IN, MAX_SPREAD_IN, edge_distance, spread_limit_applies


def connected_groups(models):
    """The unit's models partitioned into rule 09.02 "within 2\"" connected
    components - the same graph Squad.check_coherency() walks, but keeping
    the components themselves instead of only asking whether there is one.

    Public because two things outside this module need the components and not
    just the yes/no: ai/agent_driver.py's _regroup_move() (which group is the
    body of the unit that the stragglers have to rejoin) and its
    _coherency_removal_pick() (which group is the cheapest one to give up when
    the end of the turn forces a removal). Both would otherwise re-derive the
    same graph, and a second copy of it drifting from check_coherency() is
    exactly the kind of divergence this file exists to prevent."""
    remaining = list(models)
    groups = []
    while remaining:
        group = [remaining.pop()]
        frontier = list(group)
        while frontier:
            current = frontier.pop()
            for other in list(remaining):
                if edge_distance(current, other) <= COHERENCY_RANGE_IN:
                    remaining.remove(other)
                    group.append(other)
                    frontier.append(other)
        groups.append(group)
    return groups


def _pos(model):
    return f"({model.x_in:.2f},{model.y_in:.2f})"


def coherency_report(squad):
    """WHY this unit breaks rule 09.02, in numbers - or None if it doesn't.

    Squad.check_coherency() deliberately returns the two rule messages a
    PLAYER needs ("not a single connected group", "spread too far apart"),
    which is the right thing to show in the UI but says nothing about which
    models, how far off, or in which direction - so every reported case so
    far had to be reconstructed from the raw coordinates in the [move
    detail] line (the squad-spread charge failure took exactly that detour).
    This is the diagnostic counterpart: how many pieces the unit is in, the
    narrowest gap between two of those pieces (i.e. how far short of
    coherency it actually is, and between which two models), and the widest
    pair against the 9" spread limit. Never used for a rules decision -
    check_coherency() stays the single source of truth for that."""
    if len(squad.models) <= 1:
        return None

    parts = []

    groups = connected_groups(squad.models)
    if len(groups) > 1:
        sizes = " + ".join(str(len(g)) for g in sorted(groups, key=len, reverse=True))
        gap = None
        for i, group in enumerate(groups):
            for other_group in groups[i + 1:]:
                for a in group:
                    for b in other_group:
                        dist = edge_distance(a, b)
                        if gap is None or dist < gap[0]:
                            gap = (dist, a, b)
        parts.append(
            f"split into {len(groups)} groups ({sizes} models); closest gap between two groups "
            f'{gap[0]:.2f}" {_pos(gap[1])}<->{_pos(gap[2])} (needs <= {COHERENCY_RANGE_IN}")'
        )

    # Mirrors check_coherency()'s own gate - see squad.spread_limit_applies().
    # If the diagnostic reported a spread breach the rule no longer recognises,
    # every future investigation would start by chasing a violation that isn't
    # one.
    if spread_limit_applies(squad):
        widest = max(
            ((edge_distance(a, b), a, b)
             for i, a in enumerate(squad.models)
             for b in squad.models[i + 1:]),
            key=lambda item: item[0],
        )
        if widest[0] > MAX_SPREAD_IN:
            parts.append(
                f'widest pair {widest[0]:.2f}" apart {_pos(widest[1])}<->{_pos(widest[2])} '
                f'(limit {MAX_SPREAD_IN}")'
            )

    return "; ".join(parts) if parts else None


def log_coherency_state(squads, game_log, when, seen=None):
    """One `[coherency]` line per incoherent unit in `squads`, or nothing at
    all when they're all fine - so the file answers "which units were broken,
    when, and by how much" directly instead of leaving it to be inferred from
    a unit that mysteriously didn't move.

    `seen` is an optional dict used to debounce: the same unit broken in the
    same way across five phases of one turn is one fact, not five log lines,
    and repeating it would bury the transitions that actually matter."""
    if game_log is None:
        return
    for squad in squads:
        detail = coherency_report(squad)
        if detail is None:
            if seen is not None:
                seen.pop(id(squad), None)
            continue
        if seen is not None and seen.get(id(squad)) == detail:
            continue
        if seen is not None:
            seen[id(squad)] = detail
        game_log.add(
            f"  [coherency] {squad.owner}: {squad.name} is out of coherency {when} - {detail}",
            file_only=True,
        )


class CoherencyEnforcer:
    """'Regaining Coherency': at the end of a player's turn, any of their
    units that aren't in coherency (e.g. because casualties left a gap) must
    have models removed - the controlling player's choice, one at a time -
    until each is coherent again. Removed models are destroyed but don't
    trigger on-destroyed rules (we don't have any of those yet)."""

    def __init__(self, all_tokens, game_log=None):
        self.all_tokens = all_tokens
        self.game_log = game_log
        self.pending_squad = None  # squad currently needing a forced removal
        self._logged_state = {}  # id(squad) -> the last coherency_report() already written, so a standing violation isn't re-logged every phase

    def _squads_owned_by(self, player):
        seen = set()
        squads = []
        for token in self.all_tokens:
            squad = token.squad
            if squad is not None and squad.owner == player and id(squad) not in seen:
                seen.add(id(squad))
                squads.append(squad)
        return squads

    def log_state(self, player, when):
        """Write the coherency state of `player`'s units to the log file (see
        log_coherency_state()). Called at phase boundaries so a unit that
        sat still because it was already broken is visible as such, rather
        than looking like a movement failure."""
        log_coherency_state(
            self._squads_owned_by(player), self.game_log, when, seen=self._logged_state,
        )

    def check_end_of_turn(self, player):
        """Call when `player` wants to end their turn. Returns True if the
        turn may end immediately; False if a forced removal is now pending
        and the turn must wait."""
        owned = self._squads_owned_by(player)
        incoherent = [
            squad for squad in owned
            if len(squad.models) > 1 and squad.check_coherency()
        ]
        # Log BEFORE the forced removals below start changing the positions
        # this describes - this is the one moment where being out of
        # coherency actually costs models, so the "why" belongs next to it.
        # Passed the whole army, not just `incoherent`: log_coherency_state()
        # writes nothing for a coherent unit but does clear its debounce
        # entry, so a unit that breaks, gets fixed, and later breaks in the
        # exact same way is reported both times.
        log_coherency_state(
            owned, self.game_log, "at the end of its turn", seen=self._logged_state,
        )
        self.pending_squad = incoherent[0] if incoherent else None
        return self.pending_squad is None

    def remove_model(self, model):
        """The controlling player picks one model from the pending squad to
        destroy, trying to regain coherency."""
        if self.pending_squad is None or model not in self.pending_squad.models:
            return
        squad = self.pending_squad

        squad.models.remove(model)
        if model in self.all_tokens:
            self.all_tokens.remove(model)
        model.current_wounds = 0

        if self.game_log is not None:
            self.game_log.add(
                f"{squad.owner}: {model.profile.name} is destroyed (regaining coherency for {squad.name})."
            )

        if len(squad.models) > 1 and squad.check_coherency():
            return  # still incoherent - remove another from the same squad

        remaining = [
            other for other in self._squads_owned_by(squad.owner)
            if len(other.models) > 1 and other.check_coherency()
        ]
        self.pending_squad = remaining[0] if remaining else None
