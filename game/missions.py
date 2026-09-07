from game import config


def _other_player(player):
    return "Player 2" if player == "Player 1" else "Player 1"


# The standard missions' rates. User: "ändere die Missionen der ki leicht.
# primary gibt 6 Punkte pro objektive, statt 3. und secondary gibt 3 statt 1."
#
# "The AI's missions" is what these are IN THE SHIPPED CONFIG, and it is worth
# being exact about why: neither mission is owned by a player. Hold the Line is
# what everyone NOT in config.PRIMARY_MISSION_CARD_PLAYERS plays, and No Mercy
# what everyone NOT in config.SECONDARY_MISSION_CARD_PLAYERS plays - and both
# tuples name Player 1, the human, who runs a Force Disposition Primary and the
# Tactical Secondary deck instead. So today these rates reach only the AI. Empty
# either tuple (as the headless harnesses do) and the human gets them too.
PRIMARY_POINTS_PER_OBJECTIVE = 6
SECONDARY_POINTS_PER_KILL = 3

# The first battle round pays no Primary VP for objectives (user: "man sollte
# im ersten zug noch keine vp fuer objectives bekommen. erst ab zug 2").
#
# This is Hold the Line catching up with what every Force Disposition Primary
# already prints: all five of them band their objective boxes "2ND ROUND
# ONWARD" (primary_missions.SECOND_ROUND_ONWARD), so before this the standard
# mission was the ONLY one paying for the board as it stood at deployment - and
# a player deploying onto three objectives banked a full round's worth of VP
# before a single model had moved (reported as "der erste zug ging noch nicht
# los und der gegner spieler 2 hat schon 36 VP"; the duplicated battle start
# that doubled it is a separate fix, see game/pregame.py's Resume).
#
# NAMED EXCEPTION, deliberately left alone: Battlefield Dominance's "MORE OBJ"
# box is printed "Rounds 1-2" on the card it was transcribed from, and a
# transcribed rule wins over this one.
PRIMARY_FIRST_SCORING_ROUND = 2

PRIMARY_MISSION_NAME = "Hold the Line"
# Built FROM the rate rather than repeating it: this text is what the mission
# strip prints, and a card that promised a different number than the ledger
# pays is the drift this repo consolidates on sight. Same for the AI prompts,
# which quote both rates - see ai/planner_prompt.py.
PRIMARY_MISSION_TEXT = (
    f"From battle round {PRIMARY_FIRST_SCORING_ROUND}, at the start of your "
    f"Command phase, score {PRIMARY_POINTS_PER_OBJECTIVE} victory points for "
    "each objective marker you currently control."
)
SECONDARY_MISSION_NAME = "No Mercy"
SECONDARY_MISSION_TEXT = (
    f"At the end of your turn, score {SECONDARY_POINTS_PER_KILL} victory "
    "points for each enemy unit that has been destroyed."
)


# Rule 07.01: a battle lasts five battle rounds (user: "Rundenlimit ist immer
# 5. Danach endet das Spiel."). Lives here because missions define game length -
# TurnTracker deliberately keeps no limit of its own.
BATTLE_ROUNDS = 5


class MissionController:
    """Basic-setup missions (user-supplied, not core rules): one Primary
    ("Hold the Line" - PRIMARY_POINTS_PER_OBJECTIVE per objective controlled at
    the start of your own Command phase, rule 14.02's controlled_by) and one
    Secondary ("No Mercy" - SECONDARY_POINTS_PER_KILL per enemy unit destroyed,
    credited at the end of your own turn). Both rates are named rather than
    written out here, because they have been retuned once already and a
    docstring quoting the old number reads as the rule.
    Modeled after CommandPointManager - a simple per-player
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

    def save_state(self):
        """The VP ledger, as plain data for game/scene_io.py.

        `_destroyed_squad_ids` is deliberately NOT here: it is keyed by
        id(squad), which means nothing once the armies have been rebuilt, and
        it only exists to stop one squad being counted twice. After a restore
        the destroyed squads are gone from the scene entirely (scene_io evicts
        them), so they can never be recorded again and an empty set is the
        correct starting point rather than a lossy one."""
        return {
            "primary_points": dict(self.primary_points),
            "secondary_points": dict(self.secondary_points),
            "unscored_kills": dict(self._unscored_kills),
        }

    def load_state(self, data):
        """Put a saved ledger back. Unknown players are ignored rather than
        added: the roster is what says who is playing."""
        for field, target in (("primary_points", self.primary_points),
                              ("secondary_points", self.secondary_points),
                              ("unscored_kills", self._unscored_kills)):
            for player, value in (data.get(field) or {}).items():
                if player in target:
                    target[player] = value

    def total_points(self, player):
        return self.primary_points.get(player, 0) + self.secondary_points.get(player, 0)

    def plays_primary_mission_card(self, player):
        """Whether this player runs a FORCE DISPOSITION Primary Mission
        (game/primary_missions.py) INSTEAD of "Hold the Line". Read from config
        at call time for the same reason its Secondary twin below is: a harness
        that empties the tuple really turns it off.

        Which Primary a player brought is a list-building declaration in
        exactly the sense config.py's own notes use the phrase - it follows
        from the Force Disposition their army list declares, and there is
        nothing on the board to infer it from."""
        return player in config.PRIMARY_MISSION_CARD_PLAYERS

    def add_primary_points(self, player, amount):
        """The one way anything other than "Hold the Line" credits Primary VP -
        used by the Force Disposition Primary Missions. Lands in the SAME
        primary_points ledger GameStatusPanel, BattleEndOverlay and
        ai/observation.py already read, so no display needs to know where the
        points came from. Twin of add_secondary_points() below, and deliberately
        the same shape."""
        if amount <= 0:
            return 0
        self.primary_points[player] = self.primary_points.get(player, 0) + amount
        return amount

    def plays_secondary_cards(self, player):
        """Whether this player runs the Tactical Secondary card deck
        (game/secondary_missions.py) INSTEAD of "No Mercy". Read from config at
        call time, never imported by value, so a harness that empties the tuple
        really turns it off."""
        return player in config.SECONDARY_MISSION_CARD_PLAYERS

    def add_secondary_points(self, player, amount):
        """The one way anything other than "No Mercy" credits Secondary VP -
        used by the Tactical card deck when the human cashes a card in. Lands
        in the SAME secondary_points ledger GameStatusPanel and the mission
        cards already read, so no display needs to know where the points came
        from."""
        if amount <= 0:
            return 0
        self.secondary_points[player] = self.secondary_points.get(player, 0) + amount
        return amount

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

    def score_primary(self, objectives, player, battle_round):
        """Rule 14.02's controlled_by, checked at the start of `player`'s
        own Command phase (main.py calls this exactly once per Command
        phase, right after update_control() has already run for that
        boundary).

        Skipped entirely for a player running a Force Disposition Primary
        Mission (game/primary_missions.py): that mission REPLACES this player's
        standard Primary, exactly as the Tactical card deck replaces "No Mercy"
        below. Written here rather than at the three call sites (main.py's two
        battle-start paths and its Command-phase hook) so there is one
        definition of who gets Hold the Line - and, for the same reason, one
        definition of WHEN it starts paying.

        `battle_round` has no default on purpose. The round band is the whole
        point of this change, and a call site that forgot to pass it would
        silently go back to paying for the deployment - which is the reported
        bug, not a lesser version of it."""
        if self.plays_primary_mission_card(player):
            return 0
        if battle_round is not None and battle_round < PRIMARY_FIRST_SCORING_ROUND:
            return 0
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
        cleared.

        Skipped entirely for a player running the Tactical Secondary card deck
        (game/secondary_missions.py): the deck REPLACES this player's standard
        Secondary, per the user - "die Missionen sollen nur fuer mich gelten...
        die KI soll ihre Standard-Mission erstmal behalten". The pending kill
        count is still cleared, so it cannot build up a backlog that would land
        all at once if the flag ever changed mid-battle."""
        if self.plays_secondary_cards(player):
            self._unscored_kills[player] = 0
            return 0
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
