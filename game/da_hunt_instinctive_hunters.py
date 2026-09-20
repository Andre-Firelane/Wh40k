"""Da Big Hunt Stratagem: Instinctive Hunters (1CP, Mecha Orks stage G5).

RULE (verbatim, rules/orks/detachments/Da Big Hunt.md):
  WHEN:   End of your opponent's Fight phase.
  TARGET: One friendly unengaged BEAST SNAGGA unit within 6" of a battlefield
          edge.
  EFFECT: Place your unit in strategic reserves.

THE DEFFKOPTAS' AERIAL MANOOVER, BOUGHT AND WITH AN EDGE. That ability says the
same thing at the same seam ("at the end of your opponent's Fight phase, if this
unit is unengaged, you can place this unit in strategic reserves"), so
everything it learned applies here:

  * the offer takes `mover_before`, never turn_tracker.turn_owner - Fight is the
    last phase and advance_phase() has already flipped the owner by the time the
    end-of-phase offers run (test_event_chain_wiring.py section 8);
  * can_use() reads no clock: the window is the seam, held by
    game/phase_window.py, because a human answers frames later (section 15);
  * NEVER OFFERED WHEN IT CANNOT COME BACK - strategic_reserves.withdrawal_is_doomed()
    refuses the end of battle round 3 and the last turn, where the only outcome
    is the unit's destruction (rules 20.01.02/20.03);
  * the withdrawal itself is strategic_reserves.withdraw_to_reserves().

WHAT IS DIFFERENT, and both differences are printed: it costs 1CP and names ONE
unit (the ability is per unit and asks each), and the TARGET adds "within 6" of
a battlefield edge" - game/board_edges.py, which moved out of the mission deck
when this became its second reader.

ONE PROMPT listing every eligible unit, each tagged with itself, through
game/unit_choice_offer.py - the shape every "One <X> unit from your army"
Stratagem here uses, so the choice is made by clicking the unit on the board.

THE AI answers through the injected `choose` policy main.py hands it -
ai/agent_driver.py's aerial_manoover_choice(), the same "rescue or reposition"
rule, trimmed to the one unit this Stratagem may name. 0 API calls.
"""

from game import ai_mode, board_edges, da_big_hunt, engagement, unit_choice_offer
from game.phase_window import PhaseWindow
from game.stratagems import Stratagem
from game.strategic_reserves import withdraw_to_reserves, withdrawal_is_doomed

INSTINCTIVE_HUNTERS_NAME = "Instinctive Hunters"
INSTINCTIVE_HUNTERS_CP = 1
#: "within 6" of a battlefield edge".
INSTINCTIVE_HUNTERS_EDGE_RANGE_IN = 6.0
DECLINE_LABEL = "Stay on the battlefield"


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


class InstinctiveHuntersController:
    def __init__(self, stratagem_controller, game_state=None, all_tokens=None, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=(), choose=None):
        self.stratagem_controller = stratagem_controller
        self.game_state = game_state
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: choose(eligible) -> the units the AI would withdraw, best first.
        self.choose = choose
        self._window = PhaseWindow()
        self._stratagem = Stratagem(INSTINCTIVE_HUNTERS_NAME, INSTINCTIVE_HUNTERS_CP, self._withdraw)
        self._acting = None

    # ----------------------------------------------------------- questions
    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None:
            return False
        # The window this offer opened, not a live phase test - Fight is the
        # last phase, so the clock has already rolled round to Command.
        if not self._window.is_open(squad.owner):
            return False
        if not _living(squad):
            return False
        if not da_big_hunt.fields_da_big_hunt(squad.owner) or not da_big_hunt.is_beast_snagga_unit(squad):
            return False
        if engagement.is_engaged(squad, self.all_tokens):
            return False
        if not board_edges.unit_is_within_of_edge(squad, INSTINCTIVE_HUNTERS_EDGE_RANGE_IN):
            return False
        if withdrawal_is_doomed(self.turn_tracker):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def eligible_squads(self, squads, player):
        return sorted((s for s in squads if s is not None and s.owner == player and self.can_use(s)),
                      key=lambda s: s.name)

    def reset_phase(self):
        self._window.close()

    # ------------------------------------------------------- the boundary
    def offer_at_end_of_fight_phase(self, squads, mover_before):
        """`mover_before` is the player whose Fight phase just ended; the offer
        goes to everyone else ("your OPPONENT'S Fight phase")."""
        acted = False
        for player in sorted({s.owner for s in squads if s is not None and s.owner != mover_before}):
            self._window.arm(player)
            eligible = self.eligible_squads(squads, player)
            if not eligible:
                self._window.close()
                continue
            if player in self.auto_players:
                chosen = list(self.choose(eligible)) if self.choose is not None else []
                if chosen:
                    acted = self.use(chosen[0]) or acted
                if not acted:
                    self._window.close()
                continue
            if unit_choice_offer.offer_one_of(
                    self.decision_manager, player, eligible,
                    "%s (%d CP): which unit goes into Strategic Reserves?"
                    % (INSTINCTIVE_HUNTERS_NAME, INSTINCTIVE_HUNTERS_CP),
                    self.use, decline_label=DECLINE_LABEL, is_stratagem=True):
                return True
            self._window.close()
        return acted

    def use(self, squad):
        if not self.can_use(squad):
            return False
        self._acting = squad
        try:
            return bool(self.stratagem_controller.use(squad.owner, self._stratagem, [squad]))
        finally:
            self._acting = None

    def _withdraw(self, controller, player, targets):
        squad = self._acting or (targets[0] if targets else None)
        if squad is None or self.game_state is None:
            return False
        return withdraw_to_reserves(
            self.game_state, squad, log=self.game_log,
            message="%s: %s uses %s and is placed in Strategic Reserves."
                    % (squad.owner, squad.name, INSTINCTIVE_HUNTERS_NAME))
