from game.stratagems import Stratagem
from game.turn import PHASE_COMMAND

INSANE_BRAVERY_CP_COST = 1


class InsaneBraveryController:
    """Rule 15.04 (Insane Bravery, Core Stratagem, 1CP): WHEN just before a
    battle-shock roll (08.03) is made for a friendly unit, TARGET that
    unit, EFFECT that roll is automatically successful. RESTRICTIONS:
    usable at most once per battle (Stratagem.max_per_battle=1), not once
    per phase like the rule 15.01 default.

    Presented as a second button ("Insane Bravery (1CP)") right next to the
    existing "Battle-Shock Roll" button, for exactly the same qualifying
    squad (BattleShockController.can_roll()) - "just before you make a
    battle-shock roll" is naturally read as "instead of clicking the normal
    roll button for this squad this phase"."""

    def __init__(self, stratagem_controller, battle_shock_controller, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.battle_shock_controller = battle_shock_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self._stratagem = Stratagem(
            name="Insane Bravery", cp_cost=INSANE_BRAVERY_CP_COST, effect=self._resolve,
            when=self._when, max_per_battle=1, allow_battle_shocked_target=True,
        )
        self._acting_squad = None

    def _when(self, controller, player):
        return self.turn_tracker is None or self.turn_tracker.phase == PHASE_COMMAND

    def why_not(self, squad):
        """(True, None) when the button belongs on screen, else (False,
        reason) - the reason being what the panel prints instead.

        User report: "Insane bravery wird manchmal nicht angeboten." Nothing
        was broken; four different clauses could each remove the button, at
        four different moments, and none of them said so:
          * max_per_battle=1, i.e. it was already spent (15.04);
          * 15.01's targeted_this_phase - ANY other stratagem on this same
            squad this phase hides it, and Command Re-roll is a stratagem;
          * not enough CP, surcharges included;
          * the unit no longer owes a roll at all (08.03).

        Composed in the printed order of can_use()'s conjunction, and
        can_use() is derived from this so the two cannot disagree.

        (False, None) for "nothing is selected" - there is no question to
        answer, so the panel prints nothing rather than a reason."""
        if squad is None:
            return False, None
        ok, reason = self.battle_shock_controller.why_cannot_roll(squad)
        if not ok:
            return False, reason
        refusal = self.stratagem_controller.refusal(squad.owner, self._stratagem, [squad])
        if refusal is not None:
            return False, refusal
        return True, None

    def can_use(self, squad):
        return self.why_not(squad)[0]

    def use(self, squad):
        if not self.can_use(squad):
            return
        self._acting_squad = squad
        if not self.stratagem_controller.use(squad.owner, self._stratagem, [squad]):
            self._acting_squad = None

    def _resolve(self, controller, player, targets):
        self.battle_shock_controller.force_pass(self._acting_squad)
        self._acting_squad = None
