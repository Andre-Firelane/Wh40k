BONUS_CP_PER_ROUND_CAP = 1  # user-supplied house rule, not in the core rulebook: "man kann in einer Schlachtrunde nicht mehr als 1 zusätzlichen CP dazugewinnen" - see gain_cp()'s own docstring


class CommandPointManager:
    """Rule 08.02 (Gain Core CP): every Command phase, both players gain 1
    Command Point - not just the active player. Stratagems (rule 08.04,
    Command Abilities) will spend CP later via spend_cp(); nothing calls it
    yet since we don't have stratagems, but the ledger is ready for them."""

    def __init__(self, players=("Player 1", "Player 2"), game_log=None):
        self.cp = {player: 0 for player in players}
        self.game_log = game_log
        self._bonus_cp_gained = {player: 0 for player in players}  # additional (non-core) CP gained so far THIS battle round, see gain_cp()
        self._bonus_cp_round = {player: None for player in players}  # which battle_round _bonus_cp_gained's count is for - a mismatch means it's stale and gets reset lazily

    def gain_core_cp(self, amount=1):
        for player in self.cp:
            self.cp[player] += amount
        self._log(f"Gain Core CP: every player gains {amount} CP.")

    def gain_cp(self, player, battle_round, amount=1, reason=None):
        """Single-player CP grant (unlike gain_core_cp(), which is every
        player alike, rule 08.02) - for unit abilities that award CP to
        just their own controller, e.g. Gretchin's Thievin' Scavengers
        (user-supplied, not a core rule; see game/thievin_scavengers.py).

        House rule (user-supplied, explicitly NOT in the core rulebook):
        "man kann in einer Schlachtrunde nicht mehr als 1 zusätzlichen CP
        dazugewinnen" - a player can gain at most BONUS_CP_PER_ROUND_CAP
        "additional" CP per battle round, from ALL such abilities combined,
        not per-ability - e.g. if two different units' abilities would each
        grant 1CP the same round, only the first actually lands. Doesn't
        touch gain_core_cp()'s own guaranteed Command-phase CP - that's the
        baseline, not "additional". `battle_round` (turn_tracker.
        battle_round) is required, not optional, specifically so this cap
        can never be silently skipped by a caller forgetting to pass it -
        every non-core CP grant is expected to go through this one method.
        Returns the amount actually granted (0 if the cap was already hit)."""
        if self._bonus_cp_round.get(player) != battle_round:
            self._bonus_cp_round[player] = battle_round
            self._bonus_cp_gained[player] = 0
        remaining = max(0, BONUS_CP_PER_ROUND_CAP - self._bonus_cp_gained[player])
        granted = min(amount, remaining)
        if granted <= 0:
            self._log(
                f"{player}: would gain {amount} CP ({reason}), but the +{BONUS_CP_PER_ROUND_CAP} CP/battle round "
                "cap is already reached this round - 0 CP gained."
            )
            return 0
        self._bonus_cp_gained[player] += granted
        self.cp[player] = self.cp.get(player, 0) + granted
        suffix = f" ({reason})" if reason else ""
        self._log(f"{player} gains {granted} CP{suffix} - now has {self.cp[player]} CP.")
        return granted

    def spend_cp(self, player, amount):
        """Returns True and deducts the CP if the player can afford it,
        False (no change) otherwise."""
        if self.cp.get(player, 0) < amount:
            return False
        self.cp[player] -= amount
        self._log(f"{player} spends {amount} CP.")
        return True

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
