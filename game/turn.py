from game.missions import BATTLE_ROUNDS

# Rule 07.02: the 5 phases of a player turn, in order.
PHASE_COMMAND = "Command"
PHASE_MOVEMENT = "Movement"
PHASE_SHOOTING = "Shooting"
PHASE_CHARGE = "Charge"
PHASE_FIGHT = "Fight"
PHASES = [PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT]


class TurnTracker:
    """Rules 07.01-07.03: the battle is a series of battle rounds. Each round
    is Start of Battle Round -> Player Turns -> End of Battle Round. Both
    players take one turn each round; the same player always takes the
    first turn (mission-determined - we default to Player 1 since we don't
    have missions yet). Each player's turn is the Start of Turn step, then
    PHASES in order, then the End of Turn step.

    Missions decide how many battle rounds a game lasts (rule 07.01), and this
    one lasts game.missions.BATTLE_ROUNDS of them. Once the second player's
    turn of the last round ends, `battle_over` goes True and advance_phase()
    stops - user: "das spiel soll nach runde 5 enden". Before that it was
    documented here that nothing ended the battle at all; the counter simply
    kept climbing.

    This still doubles as the "whose decision is this" bookkeeping used
    during shooting (set_active/active_player) - that's independent of phase
    progression and doesn't touch battle_round/phase_index.

    `deferred_start=True` holds the battle at battle_round 0 until
    start_battle() is called - see there."""

    def __init__(self, first_player="Player 1", game_log=None, deferred_start=False):
        self.first_player = first_player
        self.game_log = game_log
        # Whether the battle proper has begun. False only while the pre-game
        # sequence (game/pregame.py) is still running: at that point nobody
        # has taken a turn, and - crucially - WHO takes the first one isn't
        # decided yet (rule 03.01's Determine First Turn roll-off happens
        # after deployment). battle_round 0 is a deliberate bonus: rule
        # 20.04's Ingress already gates on battle_round >= 2
        # (INGRESS_MIN_BATTLE_ROUND), so reserves can't arrive during the
        # pre-game without a single extra check anywhere.
        self.started = not deferred_start
        # Rule 07.01: True once the last battle round has been played out.
        # Nothing advances afterwards - see advance_phase().
        self.battle_over = False
        self.battle_round = 0 if deferred_start else 1
        self.turn_index_in_round = 0  # 0 = first_player's turn, 1 = the other player's turn
        self.active_player = first_player
        # Whose turn this actually is (all 5 phases) - unlike active_player,
        # this is ONLY ever changed here in advance_phase(), never by
        # set_active(). active_player is reused as "whose decision is this
        # right now" (e.g. the DEFENDER during a save roll, or whichever
        # player a reactive Stratagem currently belongs to) and flips back
        # and forth constantly mid-phase - main.py needs a stable "is it
        # actually Player 2's turn" signal (to auto-zoom the camera out
        # while the AI is acting, without flickering every time one of the
        # human's own shots forces a defending save roll on Player 2's
        # models) that this transient flipping can't provide.
        self.turn_owner = first_player
        self.phase_index = 0
        # How many turns each player has had so far (this one counts as their
        # first) - rule 13.09 (Hidden) needs to compare "this turn" against a
        # specific player's own turn history, not just the battle round.
        self.player_turn_count = {first_player: 1, self._other_player(first_player): 0}
        if self.started:
            self._announce_battle_start()

    def start_battle(self, first_player):
        """Rule 03.01 (Determine First Turn): who takes the first turn is only
        known once deployment is over - long after every controller that needs
        a TurnTracker has been constructed. So a deferred_start tracker is
        built up front with a placeholder first_player and told the real
        answer here, rather than main.py trying to construct ~35 controllers
        in the middle of the pre-game sequence.

        Idempotent-ish by assertion: calling this on an already-started
        battle would silently rewind the round counter, so it's refused."""
        if self.started:
            return
        self.first_player = first_player
        self.active_player = first_player
        self.turn_owner = first_player
        self.turn_index_in_round = 0
        self.phase_index = 0
        self.battle_round = 1
        self.player_turn_count = {first_player: 1, self._other_player(first_player): 0}
        self.started = True
        self.battle_over = False
        self._announce_battle_start()

    def _announce_battle_start(self):
        self._log(f"Battle Round {self.battle_round} begins.")
        self._log(f"{self.active_player}'s turn begins.")

    @property
    def phase(self):
        return PHASES[self.phase_index]

    def turn_number_for(self, player):
        """How many turns `player` has had so far, including a currently
        ongoing one - rule 13.09 (Hidden) compares this to when a unit last
        made a ranged attack."""
        return self.player_turn_count.get(player, 0)

    @property
    def is_last_phase(self):
        return self.phase_index == len(PHASES) - 1

    def set_active(self, player_name):
        if player_name is not None:
            self.active_player = player_name

    def advance_phase(self):
        """Move to the next phase, or - from the last phase - end this
        player's turn and start the next one (rule 07.02), rolling over into
        the next battle round (rule 07.03) once both players have gone.
        Purely mechanical: any end-of-turn rule that can block this (e.g.
        Regaining Coherency) must be resolved by the caller first."""
        if self.battle_over:
            return  # rule 07.01: nothing happens after the last battle round
        if not self.is_last_phase:
            self.phase_index += 1
            self._log(f"{self.active_player}: {self.phase} phase begins.")
            return

        self._log(f"{self.turn_owner}'s turn ends.")
        if self.turn_index_in_round == 0:
            self.turn_index_in_round = 1
            # Use turn_owner, not active_player, to compute who's up next:
            # active_player is a transient "whose decision is this right
            # now" flag (flipped constantly by Fight-phase resolution -
            # attacker/defender - and by reactive stratagems like Heroic
            # Intervention) and is not guaranteed to still equal the actual
            # mover by the time the Fight phase (the last phase) ends.
            # turn_owner is only ever changed here, so it's the reliable
            # value - using active_player here could otherwise compute the
            # wrong next player (e.g. silently skip the opponent's turn) if
            # active_player happened to be left pointing at the opponent.
            self.active_player = self._other_player(self.turn_owner)
            self.phase_index = 0
            self._log(f"{self.active_player}'s turn begins.")
        else:
            self._log(f"Battle Round {self.battle_round} ends.")
            if self.battle_round >= BATTLE_ROUNDS:
                # Rule 07.01: the battle is over. Deliberately left standing on
                # the last round rather than rolling into a phantom round 6 -
                # every "which round is it" reader (Beacon's timing, the AI's
                # scoring-turns-left, the status panel) then keeps showing the
                # round that was actually played.
                self.battle_over = True
                self._log(f"The battle ends after Battle Round {self.battle_round}.")
                return
            self.battle_round += 1
            self.turn_index_in_round = 0
            self.active_player = self.first_player
            self.phase_index = 0
            self._log(f"Battle Round {self.battle_round} begins.")
            self._log(f"{self.active_player}'s turn begins.")
        self.turn_owner = self.active_player
        self.player_turn_count[self.active_player] = self.player_turn_count.get(self.active_player, 0) + 1

    def _other_player(self, player):
        return "Player 2" if player == "Player 1" else "Player 1"

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
