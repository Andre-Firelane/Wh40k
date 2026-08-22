from game.dice import ADVANCE_ROLL, ATTACKS_ROLL, CHARGE_ROLL, DAMAGE_ROLL, HAZARD_ROLL, HIT_ROLL, SAVE_ROLL, WOUND_ROLL
from game.stratagems import Stratagem

COMMAND_REROLL_CP_COST = 1
REROLLABLE_KINDS = {ADVANCE_ROLL, CHARGE_ROLL, DAMAGE_ROLL, HAZARD_ROLL, HIT_ROLL, SAVE_ROLL, WOUND_ROLL, ATTACKS_ROLL}


class CommandRerollController:
    """Rule 15.02 (Core Stratagem, 1CP): just after making an Advance,
    Charge, Damage, Hazard, Hit, Save, Wound, or attacks-count roll for a
    friendly unit/model, re-roll it - one die of your choice if several
    were rolled together, except a Charge roll, which must be re-rolled in
    full. The CP-spend and once-per-phase bookkeeping are the generic
    15.01 machinery (StratagemController); this controller only owns the
    interactive "which die" selection step, which has to happen before the
    stratagem can actually be "used" (targets must be selected first, rule
    15.01 step 1)."""

    def __init__(self, stratagem_controller, dice_manager, turn_tracker=None):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.selecting_die = False
        self._pending_index = None
        self._stratagem = Stratagem(
            name="Command Re-roll", cp_cost=COMMAND_REROLL_CP_COST,
            effect=self._do_reroll, allow_repeat_target=True,
        )

    def _active_player(self):
        return self.turn_tracker.active_player if self.turn_tracker is not None else None

    def can_use(self):
        if self.dice_manager is None or not self.dice_manager.is_pending:
            return False
        if self.dice_manager.roll_kind not in REROLLABLE_KINDS:
            return False
        # Core rule: a dice can never be re-rolled more than once. The dice
        # on the table may already be an ability's re-roll ([TWIN-LINKED],
        # Breach and Clear, Forward Observers all roll their re-roll as a
        # real, pending roll of the same kind), and a Charge roll has to be
        # re-rolled in full, so it needs EVERY die to still be free.
        if self.dice_manager.roll_kind == CHARGE_ROLL:
            if not self.dice_manager.can_reroll_all():
                return False
        elif not self.dice_manager.rerollable_indices():
            return False
        return self.stratagem_controller.can_use(self._active_player(), self._stratagem, [])

    def start(self):
        """The player clicks the "Command Re-roll" button."""
        if not self.can_use():
            return
        rerollable = self.dice_manager.rerollable_indices()
        if self.dice_manager.roll_kind == CHARGE_ROLL:
            self._confirm()  # "must be re-rolled in full" - no die to pick
        elif len(rerollable) == 1:
            self._pending_index = rerollable[0]  # only one die to choose from
            self._confirm()
        else:
            self.selecting_die = True

    def choose_die(self, index):
        """The player clicked a specific die in the DicePanel while
        selecting_die is True. A die that has already been re-rolled once
        cannot be picked - the click is simply ignored, leaving the
        selection open, rather than silently spending the CP on nothing."""
        if not self.selecting_die:
            return
        if index not in self.dice_manager.rerollable_indices():
            return
        self._pending_index = index
        self.selecting_die = False
        self._confirm()

    def cancel_selection(self):
        self.selecting_die = False
        self._pending_index = None

    def _confirm(self):
        self.stratagem_controller.use(self._active_player(), self._stratagem, [])
        self._pending_index = None

    def _do_reroll(self, controller, player, targets):
        if self.dice_manager.roll_kind == CHARGE_ROLL:
            self.dice_manager.reroll_all()
        else:
            self.dice_manager.reroll_die(self._pending_index)
