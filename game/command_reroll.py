from game.dice import ADVANCE_ROLL, ATTACKS_ROLL, CHARGE_ROLL, DAMAGE_ROLL, HAZARD_ROLL, HIT_ROLL, SAVE_ROLL, WOUND_ROLL
from game.stratagems import Stratagem

COMMAND_REROLL_CP_COST = 1
REROLLABLE_KINDS = {ADVANCE_ROLL, CHARGE_ROLL, DAMAGE_ROLL, HAZARD_ROLL, HIT_ROLL, SAVE_ROLL, WOUND_ROLL, ATTACKS_ROLL}


class CommandRerollController:
    """Rule 15.02 (Core Stratagem, 1CP): just after making an Advance,
    Charge, Damage, Hazard, Hit, Save, Wound, or attacks-count roll for a
    friendly unit/model, re-roll it - one die of your choice if several
    were rolled together, except a Charge roll, which must be re-rolled in
    full. The CP-spend and 15.01 bookkeeping are the generic machinery
    (StratagemController); this controller only owns the interactive "which
    die" selection step, which has to happen before the stratagem can
    actually be "used" (targets must be selected first, rule 15.01 step 1).

    WHOSE STRATAGEM, AND ON WHAT - THE ROLL SAYS (DiceManager.rolled_for).
    The printed TARGET is "that unit or model from your army", i.e. the unit
    the roll was made for, and both halves of rule 15.01 hang off it:
      * "the same Stratagem once per phase" is keyed by the PLAYER, so the
        player has to be the unit's owner;
      * "a unit can be targeted by one Stratagem per phase" needs the UNIT
        handed in as the target.

    This used to read turn_tracker.active_player and pass no target at all.
    active_player is the transient "whose decision is it right now" flag -
    the save step hands it to the defender, and it is still the defender
    when the attacker's own Damage roll comes up. So an attacker who used
    Command Re-roll on a Wound roll was offered it AGAIN on that attack's
    Damage roll, under the opponent's key, and 15.01 found nothing to refuse:
    the second use was billed to the opponent's CP. User report: "ich konnte
    gerade command reroll in der selben aktiverung 2 mal einsetzen. einmal
    bei wound, einmal bei damage" (logs/game_20260912_225758.log: "Player 1
    uses Command Re-roll" on the wound roll, "Player 2 spends 1 CP / uses
    Command Re-roll" on Player 1's Bright Lance damage roll). And with an
    empty target list, "one Stratagem per unit per phase" could never refuse
    it either.

    A roll with no unit on it is refused rather than guessed onto an
    account - a guess is exactly the bug above. test_command_reroll.py holds
    every re-rollable roll site in game/ to naming its unit.

    `turn_tracker` is still accepted (main.py and several suites pass it) but
    no longer decides anything here."""

    def __init__(self, stratagem_controller, dice_manager, turn_tracker=None):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.selecting_die = False
        self._pending_index = None
        # No allow_repeat_target: 15.01's "one Stratagem per unit per phase"
        # applies to this one like to any other. It was set back when this
        # stratagem passed no target, where it could not matter.
        self._stratagem = Stratagem(
            name="Command Re-roll", cp_cost=COMMAND_REROLL_CP_COST,
            effect=self._do_reroll,
        )

    def rolling_unit(self):
        """The unit the roll on the table was made for, or None."""
        if self.dice_manager is None:
            return None
        return getattr(self.dice_manager, "rolled_for", None)

    def roll_owner(self):
        """Who may use Command Re-roll on the roll on the table - the owner of
        the unit it was made for - or None. The dice panel and the AI both ask
        this; neither may read active_player for it (see the class docstring)."""
        return getattr(self.rolling_unit(), "owner", None)

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
        unit = self.rolling_unit()
        if unit is None or getattr(unit, "owner", None) is None:
            return False
        return self.stratagem_controller.can_use(unit.owner, self._stratagem, [unit])

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
        unit = self.rolling_unit()
        if unit is not None:
            self.stratagem_controller.use(unit.owner, self._stratagem, [unit])
        self._pending_index = None

    def _do_reroll(self, controller, player, targets):
        if self.dice_manager.roll_kind == CHARGE_ROLL:
            self.dice_manager.reroll_all()
        else:
            self.dice_manager.reroll_die(self._pending_index)
