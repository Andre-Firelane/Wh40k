def _other_player(player):
    return "Player 2" if player == "Player 1" else "Player 1"


PRIMARY_POINTS_PER_OBJECTIVE = 3
SECONDARY_POINTS_PER_KILL = 1

PRIMARY_MISSION_NAME = "Hold the Line"
PRIMARY_MISSION_TEXT = (
    "At the start of your Command phase, score 3 victory points for each "
    "objective marker you currently control."
)
SECONDARY_MISSION_NAME = "No Mercy"
SECONDARY_MISSION_TEXT = (
    "At the end of your turn, score 1 victory point for each enemy unit "
    "that has been destroyed."
)


# Rule 07.01: a battle lasts five battle rounds (user: "Rundenlimit ist immer
# 5. Danach endet das Spiel."). Lives here because missions define game length -
# TurnTracker deliberately keeps no limit of its own.
BATTLE_ROUNDS = 5


class MissionController:
    """Basic-setup missions (user-supplied, not core rules): one Primary
    ("Hold the Line" - 3 points per objective controlled at the start of
    your own Command phase, rule 14.02's controlled_by) and one Secondary
    ("No Mercy" - 1 point per enemy unit destroyed, credited at the end of
    your own turn). Modeled after CommandPointManager - a simple per-player
    ledger, fed by two hooks main.py's advance_turn_phase() already calls at
    exactly the right instants (the `if turn_tracker.phase == PHASE_COMMAND`
    block for Primary, the `if ending_player is not None` block for
    Secondary), plus a third hook from the existing dead-model-removal loop
    for destroyed-unit tracking."""

    def __init__(self, players=("Player 1", "Player 2"), game_log=None):
        self.primary_points = {player: 0 for player in players}
        self.secondary_points = {player: 0 for player in players}
        self.game_log = game_log
        self._destroyed_squad_ids = set()  # id(squad) already recorded, so a squad is only ever counted once
        self._unscored_kills = {player: 0 for player in players}  # player -> enemy units destroyed, not yet scored

    def total_points(self, player):
        return self.primary_points.get(player, 0) + self.secondary_points.get(player, 0)

    def record_destroyed_squad(self, squad):
        """Call once a squad's model list has reached zero (see main.py's
        remove_dead_models() loop) - credits the OPPONENT of that squad's
        owner with one pending Secondary kill, not yet added to their score
        until their own end-of-turn (score_secondary_end_of_turn()).
        Idempotent per squad (tracked by identity) so processing several
        dead models from the same squad in one frame can't double-count
        it."""
        squad_id = id(squad)
        if squad_id in self._destroyed_squad_ids:
            return
        self._destroyed_squad_ids.add(squad_id)
        credited_player = _other_player(squad.owner)
        if credited_player in self._unscored_kills:
            self._unscored_kills[credited_player] += 1

    def score_primary(self, objectives, player):
        """Rule 14.02's controlled_by, checked at the start of `player`'s
        own Command phase (main.py calls this exactly once per Command
        phase, right after update_control() has already run for that
        boundary)."""
        controlled = sum(1 for objective in objectives if objective.controlled_by == player)
        gained = controlled * PRIMARY_POINTS_PER_OBJECTIVE
        if gained:
            self.primary_points[player] = self.primary_points.get(player, 0) + gained
            self._log(f"{player} scores {gained} Primary point(s) (controls {controlled} objective(s)).")
        return gained

    def score_secondary_end_of_turn(self, player):
        """Every enemy unit destroyed and not yet scored (whenever during
        the game it happened - e.g. a reactive kill made during the
        opponent's own turn, such as Fire Overwatch, simply waits here
        until `player`'s own turn actually ends) is credited now, then
        cleared."""
        kills = self._unscored_kills.get(player, 0)
        gained = kills * SECONDARY_POINTS_PER_KILL
        if gained:
            self.secondary_points[player] = self.secondary_points.get(player, 0) + gained
            self._log(f"{player} scores {gained} Secondary point(s) ({kills} enemy unit(s) destroyed).")
        self._unscored_kills[player] = 0
        return gained

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
