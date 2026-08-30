from game import objective_control  # the one answer to "what is this model's OC now"
from game import plagues  # imports only game/modifiers.py, so this cannot cycle
from game.squad import OBJECTIVE_CONSOLIDATION_RANGE_IN

# The generic "within range of an objective marker" distance used across
# the core rules (e.g. rule 12.08's Objective Consolidation, and now
# Breacher Team's Breach and Clear ability, game/shooting.py) - reuses the
# same constant/value rather than a second copy of the number 3.0.
OBJECTIVE_RANGE_IN = OBJECTIVE_CONSOLIDATION_RANGE_IN


def is_within_range_of_objective(squad, objectives, range_in=OBJECTIVE_RANGE_IN):
    """Whether any model in squad is within range_in of any objective's
    terrain area - "within range of an objective marker" as used by rule
    12.08's Objective Consolidation."""
    return any(
        objective.terrain_area.distance_to_model(m) <= range_in
        for objective in objectives
        for m in squad.models
    )


def is_on_objective(squad, objectives):
    """Whether any model in squad is actually standing on (overlapping the
    terrain footprint of) an objective marker - the SAME footprint-overlap
    definition Level of Control (14.02, see Objective.level_of_control())
    itself uses for "within range", not the separate 3" buffer
    is_within_range_of_objective() applies for Objective Consolidation.

    User correction for Breacher Team's Breach and Clear ability (user-
    supplied, not a core rule): "dürfen das nicht immer, sondern nur wenn
    Ziel auf Objective steht" - the reroll should only be offered when the
    TARGET is actually standing on the objective, not merely within some
    buffer distance of it (which - reusing is_within_range_of_objective's
    3" - was triggering far more often than intended, since several
    objectives' terrain footprints plus a 3" margin cover a large chunk of
    the board)."""
    return any(
        objective.terrain_area.overlaps_model(m)
        for objective in objectives
        for m in squad.models
    )


class Objective:
    """Rule 14.01-14.03: a terrain area (13.01) that's also a mission
    objective. Level of Control (14.02) is recomputed at the end of every
    phase/turn (see main.py's advance_turn_phase(), which calls
    update_control() for every objective right after advancing the phase).
    Secured (14.03) is a data hook for future unit abilities ("Hold At All
    Costs") to grant - no such ability exists yet (no abilities system at
    all), so nothing sets secured_by in the current demo; secure_for() is
    there for whenever that lands."""

    def __init__(self, terrain_area, name="Objective"):
        self.terrain_area = terrain_area
        self.name = name
        self.controlled_by = None
        self.secured_by = None

    def level_of_control(self, all_tokens):
        """Rule 14.02: sum of OC characteristics per player, for models
        with OC >= 1 that are within range (within the terrain area). Rule
        01.07/02.02: a battle-shocked unit's OC is modified to '-' for all
        of its models, so it contributes nothing to either player's total.

        The Death Guard Plague Scabrous Soulrot worsens OC by 1 (to a minimum
        of 1) - read through objective_control.effective_oc(), which is also what the
        `<= 0` eligibility test above now asks about, so a model whose OC the
        Plague reduced still counts with its reduced value rather than being
        judged eligible on one number and summed on another."""
        totals = {}
        for token in all_tokens:
            if token.squad is None or token.profile is None:
                continue
            if token.squad.battle_shocked:
                continue
            # `objective=self`: Mont'ka's Strategic Conqueror Enhancement adds
            # +1 only "within range of THAT objective marker", so the fold has
            # to know which one is being counted. Every other OC source ignores
            # it. See game/objective_control.py's own note on the argument.
            oc = objective_control.effective_oc(token, all_tokens, objective=self)
            if oc <= 0:
                continue
            if not self.terrain_area.overlaps_model(token):
                continue
            totals[token.squad.owner] = totals.get(token.squad.owner, 0) + oc
        return totals

    def secure_for(self, player):
        """Grant Secured status (rule 14.03) - not called by anything yet,
        since we have no unit-ability system; here for when one exists."""
        self.secured_by = player

    def update_control(self, all_tokens):
        """Rule 14.02 (highest OC total controls; a tie means nobody does)
        modified by rule 14.03 (a Secured objective's holder keeps control
        even with zero models in range, until the opponent's raw level of
        control is strictly greater than theirs)."""
        totals = self.level_of_control(all_tokens)
        players = sorted(totals.keys())

        if len(players) == 0:
            raw_leader = None
        elif len(players) == 1:
            raw_leader = players[0]
        else:
            p1, p2 = players
            if totals[p1] > totals[p2]:
                raw_leader = p1
            elif totals[p2] > totals[p1]:
                raw_leader = p2
            else:
                raw_leader = None

        if self.secured_by is None:
            self.controlled_by = raw_leader
            return

        opponent = next((p for p in totals if p != self.secured_by), None)
        secured_level = totals.get(self.secured_by, 0)
        opponent_level = totals.get(opponent, 0) if opponent is not None else 0
        if opponent_level > secured_level:
            self.secured_by = None
            self.controlled_by = raw_leader
        else:
            self.controlled_by = self.secured_by
