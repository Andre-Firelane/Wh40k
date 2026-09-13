"""Hypercrypt Legion Stratagem: Dimensional Corridor (2CP).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  WHEN:   Your Charge phase.
  TARGET: One NECRONS unit from your army that was set up on the battlefield this
          turn using the Eternity Gate ability of a MONOLITH model that started
          the turn on the battlefield.
  EFFECT: Your unit is eligible to charge this phase.

WHAT IT LIFTS IS ONE LOCK, and that is why the lock has its own field. The
Monolith's Eternity Gate prints "That unit cannot make a charge move this turn",
and it used to ride Squad.charge_locked_until_end_of_turn - the lock rules
18.04/18.05 and Cosmic Precision's RESTRICTIONS also set. A unit that came
through the gate AND bought Cosmic Precision must stay unable to charge, so
lifting the shared field would have lifted Cosmic Precision's lock as well.
Squad.eternity_gate_charge_locked is the gate's lock alone (game/eternity_gate.py,
read by ChargeController.can_declare_charge()), and this clears it and nothing
else. Every other eligibility clause of rule 11.02 still applies.

THE TARGET HAS THREE FACTS, and each is recorded where it happens rather than
reconstructed:
  * "set up on the battlefield this turn USING THE ETERNITY GATE" -
    IngressController.gate_arrivals_this_turn, filled in confirm_ingress() while
    the gate's arrival rule is still armed. A passenger whose gated arrival was
    cancelled and who then arrived the ordinary way keeps the gate's lock but is
    not in that set.
  * "a MONOLITH model that STARTED THE TURN on the battlefield" -
    Squad.eternity_gate_bearer_started_on_board, stamped by EternityGateController
    .use(): the gate is offered at the start of the Movement phase, so a Monolith
    that itself arrived this turn carries set_up_this_turn at that moment.
  * the unit is still on the battlefield - a unit wiped out since cannot charge.

NEVER OFFERED WHEN IT BUYS NOTHING: the button appears only when lifting the
gate's lock would actually make the unit eligible to declare a charge - no enemy
within 12", an Advance, a second lock from somewhere else, and the unit gets no
button. That is asked of ChargeController.can_declare_charge() itself, with the
gate's lock set aside for the duration of the question and restored in a
`finally`, so the one definition of rule 11.02 answers and no second copy of it
lives here.

THE AI (ai/agent_driver.py _handle_dimensional_corridor) buys it when the nearest
enemy is a charge it would take anyway. NAMED: it is dormant for the AI today,
because the AI declines the Eternity Gate (game/eternity_gate.py records why), so
no AI unit is ever set up through the gate.
"""

from game import necron_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_CHARGE

DIMENSIONAL_CORRIDOR_NAME = "Dimensional Corridor"
DIMENSIONAL_CORRIDOR_CP = 2
SETTING = "HYPERCRYPT_LEGION_PLAYERS"


def _alive_on_board(squad, tokens):
    return any(not m.is_dead() and m in tokens for m in getattr(squad, "models", ()) or ())


class DimensionalCorridorController:
    """A registered proactive Stratagem on the unit screen, in the Charge phase."""

    def __init__(self, stratagem_controller, turn_tracker=None, charge_controller=None,
                 ingress_controller=None, game_state=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.charge_controller = charge_controller
        self.ingress_controller = ingress_controller
        self.game_state = game_state
        self.game_log = game_log
        self._stratagem = Stratagem(name=DIMENSIONAL_CORRIDOR_NAME,
                                    cp_cost=DIMENSIONAL_CORRIDOR_CP, effect=self._grant)

    # ------------------------------------------------------------- reading
    def arrived_through_gate(self, squad):
        ic = self.ingress_controller
        if squad is None or ic is None:
            return False
        if squad not in getattr(ic, "gate_arrivals_this_turn", ()):
            return False
        if not getattr(squad, "eternity_gate_charge_locked", False):
            return False       # nothing to lift (already lifted, or never locked)
        if not getattr(squad, "eternity_gate_bearer_started_on_board", False):
            return False
        return _alive_on_board(squad, getattr(self.game_state, "tokens", ()) or ())

    def eligible_once_lifted(self, squad):
        """Rule 11.02's own answer with ONLY the gate's lock set aside."""
        cc = self.charge_controller
        if cc is None or squad is None:
            return False
        before = squad.eternity_gate_charge_locked
        squad.eternity_gate_charge_locked = False
        try:
            return bool(cc.can_declare_charge(squad))
        finally:
            squad.eternity_gate_charge_locked = before

    # -------------------------------------------------------------- the button
    def panel_label(self, squad):
        return (f"{DIMENSIONAL_CORRIDOR_NAME} ({DIMENSIONAL_CORRIDOR_CP} CP) - eligible to charge "
                "after the Eternity Gate")

    def can_use(self, squad):
        tt = self.turn_tracker
        if squad is None or tt is None or self.stratagem_controller is None:
            return False
        if tt.phase != PHASE_CHARGE or tt.turn_owner != squad.owner:
            return False
        if not necron_detachments.has_detachment(squad.owner, SETTING):
            return False
        if not necron_detachments.is_necrons_unit(squad):
            return False
        if not self.arrived_through_gate(squad):
            return False
        if not self.eligible_once_lifted(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.eternity_gate_charge_locked = False
            if self.game_log is not None:
                self.game_log.add(
                    f"{DIMENSIONAL_CORRIDOR_NAME}: {squad.name} came through the Eternity Gate and is "
                    "eligible to charge this phase.")
