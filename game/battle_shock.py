from game.leadership import (
    IMPOSSIBLE_THRESHOLD, LEADERSHIP_DICE_COUNT, LEADERSHIP_DICE_SIDES,
    leadership_success, leadership_threshold,
)
from game.squad import is_at_half_strength
from game.turn import PHASE_COMMAND


def _ld_label(squad, all_tokens=None):
    """The Ld the roll is actually made against, for the dice-panel label.

    Rule 01.06 lets a unit use the LOWEST (easiest) Ld among its models, and
    leadership_threshold() has always done that - but the label read
    models[0]'s printed Ld, which agreed with it only because a Squad used to
    be homogeneous. In an attached unit (19.01) the character usually has the
    better Ld and genuinely improves the roll, so a label off models[0] would
    show a number the dice are not being compared against."""
    threshold = leadership_threshold(squad, all_tokens)
    return f"{threshold}+" if threshold is not None else "-"


class BattleShockController:
    """Rule 01.07: a battle-shock roll is a leadership roll (01.06) for a
    unit - success means the unit does not become (or stops being)
    battle-shocked; failure means the unit, and every model in it, becomes
    battle-shocked (tracked as the existing Squad.battle_shocked flag).

    Rule 08.03: the active player must make this roll, at the start of
    their Command phase, for each of their own units that is currently
    battle-shocked or at/below half-strength (game.squad.is_at_half_strength)
    - can_roll() only allows a squad to roll if it actually qualifies, and
    has_pending_required_rolls() gates leaving the Command phase (see
    main.py) until every qualifying squad has resolved theirs this phase."""

    def __init__(self, game_log=None, dice_manager=None, turn_tracker=None, all_tokens=None):
        # Only needed by abilities that override a Ld characteristic from off
        # the datasheet (Wraithguard's Psychic Guidance asks a distance), which
        # is why it is optional - see game/leadership.py.
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.rolling_squad = None
        self.rolled_squad_ids = set()

    def reset_command_phase(self):
        """A new Command phase comes around every battle round."""
        self.rolled_squad_ids = set()

    def _qualifies(self, squad):
        return squad.battle_shocked or is_at_half_strength(squad)

    def can_roll(self, squad):
        if squad is None or self.rolling_squad is not None or squad in self.rolled_squad_ids:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_COMMAND:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        return self._qualifies(squad)

    def has_pending_required_rolls(self, all_tokens, active_player):
        """Rule 08.03: whether any of active_player's units still need to
        resolve a mandatory Battle-Shock roll this Command phase."""
        squads = {t.squad for t in all_tokens if t.squad is not None and t.squad.owner == active_player}
        return any(self.can_roll(squad) for squad in squads)

    def pending_required_rolls(self, all_tokens, active_player):
        """Same query as has_pending_required_rolls(), but returns the
        actual squads still owing a roll - used by the UI (PlayerBanner) to
        name them, instead of just saying a roll is pending somewhere.
        User-reported gap: nothing told the player WHY "Next Phase" wasn't
        advancing out of the Command phase - this mirrors the existing
        "Regaining Coherency: remove a model from X" banner's approach of
        naming the actual blocking squad(s)."""
        squads = {t.squad for t in all_tokens if t.squad is not None and t.squad.owner == active_player}
        return sorted((squad for squad in squads if self.can_roll(squad)), key=lambda s: s.name)

    def start_roll(self, squad):
        if not self.can_roll(squad) or self.dice_manager is None:
            return
        label = f"Battle-Shock Roll (Ld {_ld_label(squad, self.all_tokens)})"
        self._start_roll_dice(squad, label)

    def start_desperate_escape_roll(self, squad):
        """Rule 09.07 (Desperate Escape): an immediate Leadership/Battle-
        Shock test right after falling back this way, skipped if the unit
        is already battle-shocked - the same roll as the mandatory Command-
        phase check (08.03), just triggered at a different time and without
        that check's phase/ownership gating (can_roll() requires
        PHASE_COMMAND, which doesn't apply here - Fall Back happens in the
        Movement phase). on_dice_acknowledged() resolves it exactly like any
        other battle-shock roll, including marking it in rolled_squad_ids -
        harmless here since that set only gates the Command-phase "already
        rolled this phase" check and gets cleared before the next one
        regardless."""
        if squad is None or squad.battle_shocked or self.dice_manager is None or self.rolling_squad is not None:
            return
        label = f"Desperate Escape Battle-Shock Roll (Ld {_ld_label(squad, self.all_tokens)})"
        self._start_roll_dice(squad, label)

    def start_forced_roll(self, squad, source, penalty=0):
        """A Battle-Shock test some rule imposes out of turn - "that enemy
        unit must immediately take a Battle-shock test". `source` names the
        rule on the dice panel.

        Same relationship to can_roll() that start_desperate_escape_roll()
        already has: that gate is rule 08.03's Command-phase check (right
        phase, your own unit, actually qualifies), and none of it applies to
        a test another rule orders. Unlike Desperate Escape this does NOT
        skip an already-battle-shocked unit: 01.07's outcome for a passed
        test is that the unit stops being battle-shocked, so the test is
        meaningful either way, and "must immediately take a test" says to
        take it.

        Returns whether the roll actually started, so a caller sequencing
        further steps behind it knows whether to wait for one."""
        if squad is None or self.dice_manager is None or self.rolling_squad is not None:
            return False
        note = f", -{penalty} to the test" if penalty else ""
        self._start_roll_dice(
            squad, f"Battle-Shock Roll - {source} (Ld {_ld_label(squad, self.all_tokens)}{note})",
            penalty=penalty,
        )
        return True

    def _start_roll_dice(self, squad, label, penalty=0):
        self.rolling_squad = squad
        # Only a forced test carries one (Seer Council's Presentiment of Dread);
        # every other route leaves it at 0.
        self._penalty = penalty
        threshold = leadership_threshold(squad, self.all_tokens)
        self.dice_manager.roll(
            count=LEADERSHIP_DICE_COUNT, sides=LEADERSHIP_DICE_SIDES,
            label=label,
            success_threshold=threshold if threshold is not None else IMPOSSIBLE_THRESHOLD,
            # The unit named here is the one TAKING the test, so the panel
            # shows its art and says so rather than calling it a target.
            target_name=squad.name, target_squad=squad, subject_label="Testing",
        )

    def on_dice_acknowledged(self):
        if self.rolling_squad is None or self.dice_manager is None:
            return
        squad = self.rolling_squad
        rolls = self.dice_manager.last_values
        penalty = getattr(self, "_penalty", 0)
        self._penalty = 0
        total = sum(rolls) - penalty
        # all_tokens is passed on purpose: leadership_success() used to
        # recompute the threshold without it and grade the roll against the
        # PRINTED Ld while _start_roll_dice() above showed the overridden one
        # on the dice panel - see that function's own note.
        if leadership_success(rolls, squad, self.all_tokens, penalty):
            was_shocked = squad.battle_shocked
            squad.battle_shocked = False
            outcome = "is no longer battle-shocked" if was_shocked else "is not battle-shocked"
            self._log(f"{squad.owner}: {squad.name} passes its Battle-Shock roll ({rolls}"
                      f"{f' - {penalty}' if penalty else ''} = {total}) and {outcome}.")
        else:
            squad.battle_shocked = True
            self._log(f"{squad.owner}: {squad.name} fails its Battle-Shock roll ({rolls}"
                      f"{f' - {penalty}' if penalty else ''} = {total}) and is battle-shocked.")

        self.rolled_squad_ids.add(squad)
        self.rolling_squad = None

    def force_pass(self, squad):
        """Rule 15.04 (Insane Bravery): "that battle-shock roll is
        automatically successful" - resolves the roll's outcome without any
        dice, same bookkeeping as a real passed roll (clears battle_shocked,
        counts towards this phase's mandatory rolls)."""
        was_shocked = squad.battle_shocked
        squad.battle_shocked = False
        self.rolled_squad_ids.add(squad)
        outcome = "is no longer battle-shocked" if was_shocked else "is not battle-shocked"
        self._log(f"{squad.owner}: {squad.name}'s Battle-Shock roll automatically succeeds (Insane Bravery) and {outcome}.")

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
