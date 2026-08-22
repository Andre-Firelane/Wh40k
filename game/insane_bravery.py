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

    def can_use(self, squad):
        if squad is None or not self.battle_shock_controller.can_roll(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return
        self._acting_squad = squad
        if not self.stratagem_controller.use(squad.owner, self._stratagem, [squad]):
            self._acting_squad = None

    def _resolve(self, controller, player, targets):
        self.battle_shock_controller.force_pass(self._acting_squad)
        self._acting_squad = None
