"""Hypercrypt Legion Stratagem: Reanimation Crypts (1CP).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  WHEN:   Your Command phase.
  TARGET: Your NECRONS WARLORD.
  EFFECT: For each of your NECRONS units in Reserves, that Reserves unit's
          Reanimation Protocols activate.

"YOUR NECRONS WARLORD" IS A DOCUMENTED NO-OP (user decision). This engine has no
Warlord - Supreme Commander and "cannot be your WARLORD" are the same recorded
no-op elsewhere. The target names who the Stratagem is used ON, and the effect
never reads it, so the button stands on any NECRONS unit of the army the panel
has selected, and that unit is only what rule 15.01's ledger records.

THE EFFECT GOES THROUGH THE ONE DOOR. game/reanimation_protocols.activate() is
how every "Reanimation Protocols activate" in this engine resolves (user
decision: the Canoptek boosts apply on every activation, so no door may bypass
it). A unit in Reserves is the case activate(off_board=True) exists for:
healing is unchanged, a revived model rejoins the unit without a spot or a
token, and stands up with the rest of it when the unit arrives - rule 20.04's
ingress move places every model in squad.models. The boosts add nothing there,
and that is the printed text: both are auras, and a unit in Strategic Reserves
is within 3" of nothing.

ONE VISIBLE D3 PER UNIT, in name order, like the army rule's own queue
(game/reanimation_protocols.py ReanimationProtocolsController): the dice panel
holds one roll at a time, and the user asked for one labelled roll per unit.
While the queue is draining the controller is busy, and main.py's phase gate
waits for it.

ONLY UNITS WITH SOMETHING TO RECOVER ROLL, and a Stratagem with no such unit is
not offered at all (UNITS_MUST_HAVE_SOMETHING_TO_GAIN, the army rule's own
reading): the die of a full-strength unit provably does nothing.

"IN RESERVES" is GameState.reserves - Strategic Reserves and Deep Strike
reserves are one list here. An embarked unit is not in Reserves.

THE AI (ai/agent_driver.py _handle_reanimation_crypts) buys it in its Command
phase when the reserve units together have at least two wounds' worth to
recover (each counted up to two, the D3's average).
"""

from game import necron_detachments, reanimation_protocols
from game.stratagems import Stratagem
from game.turn import PHASE_COMMAND

REANIMATION_CRYPTS_NAME = "Reanimation Crypts"
REANIMATION_CRYPTS_CP = 1
REANIMATION_CRYPTS_DICE_SIDES = reanimation_protocols.REANIMATION_DICE_SIDES
SETTING = "HYPERCRYPT_LEGION_PLAYERS"


def reserve_units(game_state, player):
    """"each of your NECRONS units in Reserves" that has Reanimation Protocols."""
    if game_state is None:
        return []
    return sorted(
        (s for s in getattr(game_state, "reserves", ()) or ()
         if s.owner == player and necron_detachments.is_necrons_unit(s)
         and reanimation_protocols.has_reanimation_protocols(s)),
        key=lambda s: s.name)


def recovering_units(game_state, player):
    """The reserve units whose roll could do anything."""
    return [s for s in reserve_units(game_state, player)
            if reanimation_protocols.recoverable_wounds(s) > 0]


class ReanimationCryptsController:
    """A registered proactive Stratagem on the unit screen, in the Command phase."""

    def __init__(self, stratagem_controller, turn_tracker=None, game_state=None,
                 dice_manager=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.game_state = game_state
        self.dice_manager = dice_manager
        self.game_log = game_log
        #: Passed on to activate(); it adds nothing for a unit off the board.
        self.boost = None
        self._queue = []
        self._current = None
        self._stratagem = Stratagem(name=REANIMATION_CRYPTS_NAME, cp_cost=REANIMATION_CRYPTS_CP,
                                    effect=self._effect)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    @property
    def is_busy(self):
        return self._current is not None or bool(self._queue)

    # -------------------------------------------------------------- the button
    def panel_label(self, squad):
        count = len(recovering_units(self.game_state, getattr(squad, "owner", None)))
        return (f"{REANIMATION_CRYPTS_NAME} ({REANIMATION_CRYPTS_CP} CP) - Reanimation Protocols "
                f"for {count} unit(s) in Reserves")

    def can_use(self, squad):
        tt = self.turn_tracker
        if squad is None or tt is None or self.stratagem_controller is None:
            return False
        if tt.phase != PHASE_COMMAND or tt.turn_owner != squad.owner:
            return False
        if self.is_busy:
            return False
        if not necron_detachments.has_detachment(squad.owner, SETTING):
            return False
        if not necron_detachments.is_necrons_unit(squad):
            return False
        if not recovering_units(self.game_state, squad.owner):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    # --------------------------------------------------------------- the queue
    def _effect(self, controller, player, targets):
        self._queue = recovering_units(self.game_state, player)
        self._log(f"{REANIMATION_CRYPTS_NAME}: {player}'s {len(self._queue)} NECRONS unit(s) in "
                  "Reserves activate their Reanimation Protocols.")
        self._roll_next()

    def _roll_next(self):
        while self._queue:
            squad = self._queue.pop(0)
            if reanimation_protocols.recoverable_wounds(squad) <= 0:
                continue
            if self.dice_manager is None:
                from game import dice
                self._apply(squad, dice.random.randint(1, REANIMATION_CRYPTS_DICE_SIDES))
                continue
            self._current = squad
            self.dice_manager.roll(
                1, REANIMATION_CRYPTS_DICE_SIDES, label=REANIMATION_CRYPTS_NAME,
                target_name=squad.name, target_squad=squad, rolled_for=squad,
                subject_label="Reanimating")
            return True
        self._current = None
        return False

    def on_dice_acknowledged(self):
        if self._current is None or self.dice_manager is None:
            return False
        squad = self._current
        rolled = (self.dice_manager.last_values or [1])[0]
        self._apply(squad, rolled)
        self._roll_next()
        return True

    def _apply(self, squad, rolled):
        self._current = None
        wounds, spent, revived = reanimation_protocols.activate(
            squad, rolled,
            boost=self.boost,
            game_state=self.game_state,
            log=self._log,
            off_board=True,
        )
        detail = f"{spent} wound(s)"
        if revived:
            detail += f", {len(revived)} model(s) back in the unit"
        self._log(f"{REANIMATION_CRYPTS_NAME} ({squad.name}, in Reserves): rolled a {rolled} for "
                  f"{wounds} - reanimated {detail}.")
