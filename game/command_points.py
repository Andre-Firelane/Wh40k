BONUS_CP_PER_ROUND_CAP = 1  # user-supplied house rule, not in the core rulebook: "man kann in einer Schlachtrunde nicht mehr als 1 zusätzlichen CP dazugewinnen" - see gain_cp()'s own docstring

#: WHERE a non-core CP came from. Canoptek Court's Autodivinator made this a rule
#: question rather than bookkeeping - its FAQ reads "It only triggers when your
#: opponent gains CP as the result of an ability (not any other kind of rule)" and
#: names discarding a Secondary Mission card as a case that does NOT count.
#:
#: REQUIRED on every gain_cp() call, deliberately without a default: a new CP
#: grant cannot join the engine without deciding which of the two it is, and
#: test_necron_canoptek_court.py pins that by AST. Core CP (rule 08.02) goes
#: through gain_core_cp() and is neither - it never reaches a listener.
SOURCE_ABILITY = "ability"   # a datasheet ability or an Enhancement
SOURCE_MISSION = "mission"   # a mission rule, e.g. discarding a Secondary Mission card
SOURCES = (SOURCE_ABILITY, SOURCE_MISSION)


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
        # listener(player, granted, source=, battle_round=, reason=) - fired
        # once per gain_cp() call that ACTUALLY granted something. A LIST, so a
        # second reader joins without displacing the first. The Autodivinator
        # (game/enh_autodivinator.py) is the first.
        self.on_cp_gained = []

    def gain_core_cp(self, amount=1):
        for player in self.cp:
            self.cp[player] += amount
        self._log(f"Gain Core CP: every player gains {amount} CP.")

    def bonus_cp_remaining(self, player, battle_round):
        """How much of BONUS_CP_PER_ROUND_CAP this player has left THIS battle
        round. The one definition of the cap's arithmetic - gain_cp() below
        reads it too, so an offer that consults this can never disagree with
        what the grant actually does.

        Exists because an ability that OFFERS a bonus CP as a choice (e.g.
        discarding a Secondary Mission card, game/secondary_missions.py) has to
        know beforehand whether it would pay anything: offering a trade that
        silently grants 0 is the "the engine must not offer what it does not
        want chosen" mistake this codebase keeps running into. Read-only -
        unlike gain_cp() it does not lazily reset the stale round counter, it
        just reports 0 spent for a round that has not started counting yet."""
        if self._bonus_cp_round.get(player) != battle_round:
            return BONUS_CP_PER_ROUND_CAP
        return max(0, BONUS_CP_PER_ROUND_CAP - self._bonus_cp_gained.get(player, 0))

    def gain_cp(self, player, battle_round, amount=1, reason=None, *, source):
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

        `source` (SOURCE_ABILITY / SOURCE_MISSION) is required for the same
        reason - see the constants above. Listeners hear about a grant only
        once it has landed: a CP the cap swallowed was never gained.
        Returns the amount actually granted (0 if the cap was already hit)."""
        if source not in SOURCES:
            raise ValueError(f"gain_cp(): source must be one of {SOURCES}, not {source!r}")
        remaining = self.bonus_cp_remaining(player, battle_round)
        if self._bonus_cp_round.get(player) != battle_round:
            self._bonus_cp_round[player] = battle_round
            self._bonus_cp_gained[player] = 0
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
        for listener in list(self.on_cp_gained):
            listener(player, granted, source=source, battle_round=battle_round, reason=reason)
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
