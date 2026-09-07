"""Path of the Outcast Stratagem: Eldritch Suppression (1CP).

RULE (verbatim, rules/aeldari/detachments/Path of the Outcast.md):
  WHEN:   Your Shooting phase, when a friendly RANGERS/SHROUD RUNNERS unit has
          shot.
  TARGET: That RANGERS/SHROUD RUNNERS unit.
  EFFECT: Select one enemy unit hit by those ranged attacks. That enemy unit
          makes a battle-shock roll, with -1 to that battle-shock roll if a
          model in that enemy unit was destroyed by those attacks.
  RESTRICTIONS: none printed.

THE THIRD CONSUMER of game/battle_shock_after_shooting.py, after Maugan Ra's
Face of Death and the Leystalker's Panicked Quarry. Everything about the shape
- the trigger, the "select one enemy unit hit", the auto-pick when only one
qualifies, and the forced test through BattleShockController.start_forced_roll()
- comes from there. Two things are genuinely different and both are printed:

  * THE -1 IS CONDITIONAL. The other two subtract 1 always; this one subtracts
    1 only "if a model in that enemy unit was destroyed by those attacks". So
    the base grew penalty_for(target) - a method, defaulting to the flat class
    attribute, which neither of the other two notices.
  * IT IS A STRATAGEM, so "does this unit have the ability" is not a printed
    UnitProfile flag but a detachment plus two datasheet names. unit_has_ability
    is overridden rather than a fake profile field invented.

"DESTROYED BY THOSE ATTACKS" CANNOT BE ASKED AFTERWARDS, which is why
ShootingController now records how many models each target still had when this
activation FIRST hit it. remove_dead_models() runs once per frame, so at the
end of an activation a corpse in Squad.models may be from this activation or
from the previous one - counting bodies at the end would answer a different
question. The count is taken beside the hit itself, in the one place that
already knows a target was really hit rather than merely targeted.

WHY THE SELECTION IS OFFERED BEFORE THE CP IS SPENT. The base picks the target
unit and then tests; a Stratagem must be bought first. So use() spends the CP
for the SHOOTING unit - which is what the printed TARGET line names - and the
enemy unit is chosen inside the effect, the ordering
game/presentiment_of_dread.py already writes out.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import ai_mode, far_reaching_doom
from game.battle_shock_after_shooting import BATTLE_SHOCK_PENALTY, BattleShockAfterShooting, any_target
from game.stratagems import Stratagem

ELDRITCH_SUPPRESSION_NAME = "Eldritch Suppression"
ELDRITCH_SUPPRESSION_CP = 1


class EldritchSuppressionController(BattleShockAfterShooting):
    """The offer, made when a Rangers/Shroud Runners unit has finished shooting."""

    flag = None                      # not a printed profile flag - see below
    label = ELDRITCH_SUPPRESSION_NAME
    penalty = BATTLE_SHOCK_PENALTY
    eligible = staticmethod(any_target)

    def __init__(self, stratagem_controller, battle_shock_controller=None,
                 shooting_controller=None, decision_manager=None, game_log=None,
                 auto_players=()):
        super().__init__(battle_shock_controller=battle_shock_controller,
                         decision_manager=decision_manager, game_log=game_log)
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.auto_players = ai_mode.players(auto_players)
        self._pending_hits = ()
        self._stratagem = Stratagem(
            name=ELDRITCH_SUPPRESSION_NAME, cp_cost=ELDRITCH_SUPPRESSION_CP,
            effect=self._effect,
        )

    def unit_has_ability(self, squad):
        """A detachment and two datasheet names, not a profile flag.

        far_reaching_doom.applies() is the same question the detachment RULE
        asks - "a friendly RANGERS/SHROUD RUNNERS unit of a player fielding
        this detachment" - so it is read from there rather than restated."""
        return far_reaching_doom.applies(squad)

    def penalty_for(self, target):
        """-1 only if a model in that unit was destroyed by those attacks."""
        if self.shooting_controller is None:
            return 0
        lost = self.shooting_controller.models_lost_this_activation(target)
        return BATTLE_SHOCK_PENALTY if lost > 0 else 0

    def can_use(self, squad, hit_squads=()):
        if squad is None or self.stratagem_controller is None:
            return False
        if not self.unit_has_ability(squad):
            return False
        if not any(self.eligible(s) for s in hit_squads or ()):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def offer_after_shooting(self, squad, hit_squads):
        """Overrides the base: this one costs CP, so it asks first."""
        if not self.can_use(squad, hit_squads):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False                      # no AI path
        self._pending_hits = tuple(hit_squads or ())
        self.decision_manager.request(
            squad.owner,
            "%s (%d CP): %s has shot - force a Battle-shock test on a unit it hit?"
            % (ELDRITCH_SUPPRESSION_NAME, ELDRITCH_SUPPRESSION_CP, squad.name),
            [("Use (%d CP)" % ELDRITCH_SUPPRESSION_CP, (lambda: self.use(squad, self._pending_hits))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad, hit_squads=()):
        if not self.can_use(squad, hit_squads):
            return False
        self._pending_hits = tuple(hit_squads or self._pending_hits)
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _effect(self, controller, player, targets):
        """WHICH enemy unit is part of the EFFECT, so it is chosen here - after
        the CP is spent, the ordering rule 15.01 states."""
        hits, self._pending_hits = self._pending_hits, ()
        squad = targets[0] if targets else None
        options = sorted((s for s in hits if self.eligible(s)), key=lambda s: s.name)
        if not options:
            return
        if len(options) == 1 or self.decision_manager is None:
            self._test(options[0])
            return
        self.decision_manager.request(
            squad.owner,
            "%s: which unit takes the test?" % ELDRITCH_SUPPRESSION_NAME,
            [(t.name, (lambda t=t: self._test(t)), t) for t in options],
            is_stratagem=True,
        )
