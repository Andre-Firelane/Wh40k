"""Wraithblades' "Malevolent Souls" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "Each time a model in this unit is destroyed by a melee attack, if that model
  has not fought this phase, roll one D6. On a 3+, do not remove it from play;
  that destroyed model can fight after the attacking unit has finished making
  its attacks, and is then removed from play."

THE MECHANISM IS SHARED, THE RULE IS NOT
----------------------------------------
"dead, still on the board, owed one activation, then removed" is
game/fight_after_death.py - extracted when this became its second consumer
after Death Lord's Chosen's UNDYING SPITE. What this module owns is only what
the printed text says that the Stratagem's does not:

  * ALWAYS ON. Undying Spite is bought for 1 CP and lasts until the end of the
    phase, so it carries a `_active` set, an offer, and 15.01 bookkeeping.
    This is a datasheet ability: if the models are on the board it applies.
    There is nothing to ask, so there is no DecisionManager prompt and nothing
    for `auto_players` to answer - which is also why it needs no AI path.
  * 3+, not 4+.
  * "BY A MELEE ATTACK". Undying Spite has no such clause; this one does, and
    it is the half most easily lost, because the sweep that reports the death
    does not itself know what killed the model. It is answered from the TURN
    PHASE (game/turn.py's PHASE_FIGHT) rather than by tracing the killing
    weapon: every melee attack in this engine resolves in the Fight phase, and
    nothing else does, so the phase is an exact test and a weapon-provenance
    trail would be a second, weaker answer to a question already settled.
    A Wraithblade shot down in the Shooting phase therefore gets nothing,
    which is the rule.

"IF THAT MODEL HAS NOT FOUGHT THIS PHASE" is read off
FightController.fought_squad_ids - per UNIT, which is what that ledger records
and which is exact here, because a unit fights as a whole. Same source Undying
Spite uses for the same clause.

RULE 19.04's shape for the ability itself: any() rather than all(), so a
character attached to the unit does not take the ability away from the
Wraithblades - and, symmetrically, only models that actually PRINT the ability
are eligible to come back. A Spiritseer leading the unit does not rise again.
"""
from game.fight_after_death import FightAfterDeath
from game.turn import PHASE_FIGHT

MALEVOLENT_SOULS_THRESHOLD = 3   # "On a 3+"
MALEVOLENT_SOULS_LABEL = "Malevolent Souls"


class MalevolentSoulsController:
    """Fed by main.py's death sweep; drained at on_unit_finished_fighting."""

    def __init__(self, game_state=None, game_log=None, turn_tracker=None,
                 fight_controller=None):
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self._ledger = FightAfterDeath(
            MALEVOLENT_SOULS_THRESHOLD, MALEVOLENT_SOULS_LABEL,
            game_state=game_state, game_log=game_log)

    # ---------------------------------------------------------- conditions

    def _has_fought(self, squad):
        ledger = getattr(self.fight_controller, "fought_squad_ids", None) or ()
        return squad in ledger or id(squad) in {id(s) for s in ledger}

    def _in_fight_phase(self):
        """"destroyed by a melee attack" - see the module docstring for why the
        phase is the exact test rather than an approximation of one."""
        if self.turn_tracker is None:
            return True
        return self.turn_tracker.phase == PHASE_FIGHT

    def is_eligible(self, model):
        """Whether THIS destroyed model comes back on a 3+."""
        if model is None or not getattr(model.profile, "malevolent_souls", False):
            return False
        squad = getattr(model, "squad", None)
        if squad is None:
            return False
        if not self._in_fight_phase():
            return False
        return not self._has_fought(squad)

    # ------------------------------------------------------------ the hooks

    @property
    def is_busy(self):
        return self._ledger.is_busy

    def models_owed_an_activation(self):
        return self._ledger.models_owed_an_activation()

    def intercept_destroyed(self, models):
        """From the death sweep. Returns the models that stayed up; they are
        already back on the board (game/fight_after_death.py does that)."""
        return self._ledger.roll_for(models, self.is_eligible)

    def resolve_after_attacks(self, attacking_squad=None):
        return self._ledger.resolve_after_attacks(attacking_squad)

    def reset_phase(self):
        """Anything still owed an activation when the phase ends is removed, so
        no model survives into a phase in which it has no right to strike."""
        return self._ledger.resolve_after_attacks()
