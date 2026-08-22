"""Orks datasheet ability: Gretchin's Thievin' Scavengers, as supplied by
the user (not a rule from the generic 40k core rulebook, so it lives in its
own module - same reasoning as game/fieldcraft.py etc.). User: "diese
Ability wird noch öfters kommen" - a shared UnitProfile.thievin_scavengers
flag (same reuse pattern as `fieldcraft`), so a future datasheet printing
this identical ability needs no new code, just the flag set.

RULE: at the start of your Movement phase, roll one D6 for each objective
marker you control that has one or more units from your army with this
ability within range of it (excluding Battle-shocked units). If one or
more of those rolls is a 4+, you gain 1CP.

User instruction: "Bei der CP roll Ability muss auch ein Würfel im Panel
geworfen werden mit Hinweistext" - a real, visible DiceManager roll (one
combined roll of N dice, success_threshold=4, same shape DiceManager/
DicePanel already render for e.g. a Hit Roll - "N dice against one shared
threshold" is exactly that shape, no new UI needed), not a silent
CP grant.

Follow-up user house rule (explicitly not in the core rulebook): "man kann
in einer Schlachtrunde nicht mehr als 1 zusätzlichen CP dazugewinnen" - the
actual cap is enforced centrally in game/command_points.py's own gain_cp()
(BONUS_CP_PER_ROUND_CAP), not here - this controller just calls it with the
current battle_round and reports whatever it actually granted (which may
be less than the roll would otherwise justify, or 0 if that round's cap
was already used by some other ability)."""

from game.objectives import is_within_range_of_objective
from game.squad import squad_has_thievin_scavengers
from game.dice import THIEVIN_SCAVENGERS_ROLL

THIEVIN_SCAVENGERS_SUCCESS_THRESHOLD = 4


class ThievinScavengersController:
    """Tracks a single pending roll (`_pending_player`) the same way
    BattleShockController does (no distinguishing roll_kind needed for
    dispatch - THIEVIN_SCAVENGERS_ROLL exists mainly for DicePanel/Command-
    Reroll-exclusion bookkeeping, see game/dice.py's own note) - only one
    can ever be in flight at a time since start_check() is only ever called
    once, at the start of a Movement phase."""

    def __init__(
        self, dice_manager=None, command_points=None, all_tokens=None, objectives=None, turn_tracker=None,
        game_log=None,
    ):
        self.dice_manager = dice_manager
        self.command_points = command_points
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.objectives = objectives if objectives is not None else []
        self.turn_tracker = turn_tracker  # needed for battle_round, see game/command_points.py's gain_cp() cap
        self.game_log = game_log
        self._pending_player = None

    def _qualifying_squads(self, player):
        return [
            squad for squad in {t.squad for t in self.all_tokens if t.squad is not None and t.squad.owner == player}
            if not squad.battle_shocked and squad_has_thievin_scavengers(squad)
        ]

    def _qualifying_objective_count(self, player):
        qualifying_squads = self._qualifying_squads(player)
        if not qualifying_squads:
            return 0
        return sum(
            1 for objective in self.objectives
            if objective.controlled_by == player
            and any(is_within_range_of_objective(squad, [objective]) for squad in qualifying_squads)
        )

    def start_check(self, player):
        """Called once at the start of `player`'s own Movement phase (see
        main.py's advance_turn_phase()) - a no-op (no roll at all) if there
        are no qualifying objectives, exactly matching the rule text ("roll
        one D6 for EACH objective marker...")."""
        if self.dice_manager is None:
            return
        count = self._qualifying_objective_count(player)
        if count == 0:
            return
        self._pending_player = player
        self.dice_manager.roll(
            count=count, sides=6,
            label=(
                f"Thievin' Scavengers Roll ({count} objective(s) controlled with a qualifying unit in range) - "
                "1+ die at 4+ grants 1CP"
            ),
            success_threshold=THIEVIN_SCAVENGERS_SUCCESS_THRESHOLD,
            target_name=player, roll_kind=THIEVIN_SCAVENGERS_ROLL,
        )

    def on_dice_acknowledged(self):
        if self._pending_player is None or self.dice_manager is None:
            return
        player = self._pending_player
        self._pending_player = None
        rolls = self.dice_manager.last_values
        success = any(r >= THIEVIN_SCAVENGERS_SUCCESS_THRESHOLD for r in rolls)
        if success and self.command_points is not None:
            battle_round = self.turn_tracker.battle_round if self.turn_tracker is not None else None
            self.command_points.gain_cp(player, battle_round, amount=1, reason="Thievin' Scavengers")
        elif self.game_log is not None:
            self.game_log.add(f"{player}: Thievin' Scavengers roll {rolls} - no 4+, no CP gained.")
