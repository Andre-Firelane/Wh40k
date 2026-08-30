"""Death Lord's Chosen Stratagem: UNDYING SPITE (1 CP, Strategic Ploy).

  WHEN: Fight phase, just after an enemy unit has selected its targets.
  TARGET: One TERMINATOR unit from your army that was selected as the target of
        one or more of the attacking unit's attacks.
  EFFECT: Until the end of the phase, each time a model in your unit is
        destroyed, if that model has not fought this phase, roll one D6. On a
        4+, do not remove the destroyed model from play; it can fight after the
        attacking unit has finished making its attacks, and is then removed
        from play.

THE ONLY ONE OF THE SIX WITH GENUINELY NEW SEQUENCING, and it is worth spelling
out what is new and what is not:

  * "just after an enemy unit has selected its targets" ALREADY EXISTS as
    FightController.target_reactions - the list 'Ard as Nails, Forewarned and
    Psychic Shield all sit in. So the WHEN is free.
  * "after the attacking unit has finished making its attacks" ALREADY EXISTS
    as FightController.on_unit_finished_fighting - the instant Protocol of the
    Vengeful Stars and the Chaos Spawn's Lethal Ichor both use. So the
    resolution moment is free too.
  * WHAT IS NEW is the state in between: a model that is DEAD, is still on the
    battlefield, gets an activation, and is then removed. Nothing in this
    engine has needed that before.

WHY THE DEATH IS INTERCEPTED IN THE SWEEP AND NOT AT RESOLUTION: GameState.
remove_dead_models() runs once per frame and is what would take the model off
the board. So this controller is fed from the same sweep - it is told which
models were about to be removed, rolls for each, and RE-ADDS the ones that
passed. Trying to notice the death later would be trying to read a board the
sweep has already changed, which is the recurring ordering trap CLAUDE.md
records as error class 12.

"IF THAT MODEL HAS NOT FOUGHT THIS PHASE" is the clause that stops the
Stratagem giving a unit a second activation: a Deathshroud squad that has
already swung gets nothing. Read off FightController.fought_squad_ids, the same
ledger the other five Stratagems' "has not been selected to fight" clauses use -
per UNIT, which is what that ledger records, and which is exact here because a
unit fights as a whole.

REACTIVE, so `auto_players` answers for the AI and nothing goes in ai/.

THE AI VERDICT IS THE USER'S: buy it when, computationally, at least one
Terminator would die to the incoming melee attack.

Why it had to be phrased that way rather than as a count of the dead: the WHEN
is "just after an enemy unit has SELECTED its targets", which is before a
single model has been removed - so the CP has to be committed while the losses
are still hypothetical. The verdict is therefore the EXPECTED losses of the
activation about to happen, from game/damage_estimate.py, which is the same
measure every other deterministic CP decision in this engine uses.

The threshold of ONE is not arbitrary given what the Stratagem does: a model
that dies is exactly the model that gets to strike back on a 4+, so one
projected casualty already means one coin-flip at a Manreaper's worth of
attacks. Below that there is nothing for the Stratagem to act on at all.

The estimate is deliberately an UNDER-estimate (it counts no re-rolls and no
[SUSTAINED/LETHAL/DEVASTATING]), so the Stratagem is bought slightly less often
than the rule intends rather than more - the safe direction for a CP decision.

The estimate is INJECTED as `worth_using` from main.py rather than imported,
for the same reason VengefulStarsController takes its verdict as a closure:
game/ modules do not depend on ai/.

"""
from game import death_lords_chosen
from game.fight_after_death import FightAfterDeath
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT

UNDYING_SPITE_CP = 1
UNDYING_SPITE_THRESHOLD = 4   # "On a 4+"
UNDYING_SPITE_LABEL = "Undying Spite"


class UndyingSpiteController:
    """Sits in FightController.target_reactions; fed by the death sweep."""

    #: The user's rule: "when, computationally, one Terminator would die in
    #: melee". Expressed as EXPECTED losses because the CP is committed before
    #: any model is removed - see the module docstring.
    MIN_EXPECTED_KILLS = 1

    def __init__(self, stratagem_controller, dice_manager=None, decision_manager=None,
                 turn_tracker=None, fight_controller=None, game_log=None,
                 game_state=None, auto_players=(), worth_using=None):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self.game_log = game_log
        self.game_state = game_state
        self.auto_players = set(auto_players)
        # worth_using(attacking_squad, target_squad) -> bool. main.py passes the
        # shared damage estimate; None means "always worth it", which is what a
        # headless test wants and what a human prompt implies anyway.
        self.worth_using = worth_using
        self._stratagem = Stratagem(
            UNDYING_SPITE_LABEL, UNDYING_SPITE_CP, self._effect,
            # Each attacking unit selects its own targets, so each opens its own
            # window - 15.01's once-per-target-per-phase would be the wrong
            # bound. Same call Undying Legions and Sickening Impact make.
            allow_repeat_target=True,
        )
        self._active = set()      # id(squad) protected until the end of the phase
        self._handled = set()     # (id(target), id(attacker)) already offered this phase
        # "dead, still on the board, owed one activation, then removed" is shared
        # with the Wraithblades' Malevolent Souls - see game/fight_after_death.py.
        # What stays HERE is the Stratagem: the CP, the offer, 15.01's ledger and
        # the "until the end of the phase" window.
        self._ledger = FightAfterDeath(
            UNDYING_SPITE_THRESHOLD, UNDYING_SPITE_LABEL,
            game_state=game_state, game_log=game_log)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def is_active(self, squad):
        return squad is not None and id(squad) in self._active

    @property
    def is_busy(self):
        return self._ledger.is_busy

    # ----------------------------------------------------------- conditions

    def _has_fought(self, squad):
        ledger = getattr(self.fight_controller, "fought_squad_ids", None) or ()
        return squad in ledger or id(squad) in {id(s) for s in ledger}

    def can_use(self, squad):
        if squad is None or self.is_active(squad):
            return False
        if not death_lords_chosen.stratagem_target_ok(squad):
            return False
        if not death_lords_chosen.is_terminator_unit(squad):
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if self._has_fought(squad):
            return False   # "if that model has not fought this phase"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def is_worth_using(self, squad, attacking_squad=None):
        """The user's rule: only when the incoming melee activation is projected
        to destroy at least MIN_EXPECTED_KILLS model(s) of this unit.

        Without an estimate (no attacker known, or none injected) it falls back
        to "the unit still has something to lose", which is what a human prompt
        means anyway - the human is being ASKED, so the engine should not
        pre-judge it."""
        if not any(not m.is_dead() for m in getattr(squad, "models", ()) or ()):
            return False
        if self.worth_using is None or attacking_squad is None:
            return True
        return bool(self.worth_using(attacking_squad, squad))

    # ------------------------------------------------------------ the offer

    def maybe_offer(self, attacking_squad, target_squad, melee=False):
        """FightController's target_reactions entry: "just after an enemy unit
        has selected its targets".

        The argument order is the LIST's, not this Stratagem's: every reaction
        in target_reactions is called as (attacker, target, melee=...), and the
        unit this Stratagem protects is the TARGET. Getting that round the
        wrong way would offer it to the attacking unit instead - which
        can_use()'s TERMINATOR test would usually hide, and that is exactly
        what makes it worth stating."""
        if not melee:
            return False   # "Fight phase" - the ranged list never reaches here anyway
        key = (id(target_squad), id(attacking_squad))
        if key in self._handled:
            return False
        if not self.can_use(target_squad):
            return False
        # The verdict gate is applied ONLY to the AI. A human is being asked, so
        # pre-judging it for them would hide a Stratagem they might want - the
        # same split 'Ard as Nails makes between can_use() and is_worth_using().
        if target_squad.owner in self.auto_players and not self.is_worth_using(
                target_squad, attacking_squad):
            return False
        self._handled.add(key)
        if target_squad.owner in self.auto_players or self.decision_manager is None:
            return self.use(target_squad)
        self.decision_manager.request(
            target_squad.owner,
            f"{target_squad.name} is being attacked - Undying Spite (1 CP)? "
            f"Destroyed models that have not fought return on a 4+ to strike back.",
            [(f"{UNDYING_SPITE_LABEL} (1 CP)", lambda: self.use(target_squad)),
             ("Decline", None)],
            is_stratagem=True)
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _effect(self, controller, player, targets):
        for squad in targets or ():
            self._active.add(id(squad))
            self._log(f"{UNDYING_SPITE_LABEL}: {squad.name} - destroyed models that have "
                      f"not fought this phase return on a {UNDYING_SPITE_THRESHOLD}+ to "
                      f"strike back.")
        return True

    # --------------------------------------------------- intercepting death

    def intercept_destroyed(self, models):
        """Called from main.py's death sweep with the models it is about to
        remove. Returns those that SURVIVE - already put back on the board by
        the shared ledger, so the caller has nothing to re-add.

        Here rather than at resolution time because remove_dead_models() runs
        once per frame and is what takes them off; noticing afterwards would be
        reading a board that has already changed."""
        if self.dice_manager is None:
            return []
        return self._ledger.roll_for(models, self._model_is_protected)

    def _model_is_protected(self, model):
        squad = getattr(model, "squad", None)
        if squad is None or not self.is_active(squad):
            return False
        return not self._has_fought(squad)

    def models_owed_an_activation(self):
        return self._ledger.models_owed_an_activation()

    def resolve_after_attacks(self, attacking_squad=None):
        """"it can fight after the attacking unit has finished making its
        attacks, and is then removed from play."

        The activation itself is driven by main.py through the ordinary fight
        step; the removal half lives in the shared ledger."""
        return self._ledger.resolve_after_attacks(attacking_squad)

    def reset_phase(self):
        """"Until the end of the phase" - and anything still owed an
        activation when the phase ends is removed, so no model survives into
        the next phase on a Stratagem that has expired."""
        self.resolve_after_attacks()
        self._active.clear()
        self._handled.clear()
