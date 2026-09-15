"""War Horde Stratagem: Orks Is Never Beaten (1CP).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  WHEN:   Fight phase, when an enemy unit targets a friendly ORKS unit
          (excluding TITANIC units).
  TARGET: That ORKS unit.
  EFFECT: When a model in your unit is destroyed, if your unit has not been
          selected to fight this phase, roll one D6, with +1 to that roll if
          your unit is riled up:
          - On a 4+, do not remove that model from the battlefield. When your
            unit has fought, or at the end of the phase (whichever comes
            first), that model is removed from the battlefield.

THE WHEN is FightController.target_reactions, maybe_offer(attacker, target,
melee=...) - the moment Undying Spite answers. THE "DEAD, STILL ON THE BOARD"
STATE is game/fight_after_death.py's ledger: main.py's death sweep hands it the
models it was about to remove, the ledger rolls, and a 4+ goes back.

WHAT DIFFERS FROM UNDYING SPITE, each printed or a user decision:
  * the REMOVAL is tied to the ORKS unit's own activation ("when YOUR unit has
    fought"), not to the attacker's - so the ledger removes per unit
    (remove_for()), from main.py's after-fight hook with the fighter, and
    whatever is still kept at the phase boundary goes in reset_phase();
  * +1 to the roll while the unit is riled up (the ledger's bonus_for);
  * a kept model fights with its unit (fight.py's melee groups read every model
    of the unit), is allocated no wounds (every allocation session skips dead
    models), and counts for neither Objective Control nor coherency -
    game/objectives.py's level_of_control() and Squad.check_coherency() skip
    dead models.

NAMED LIMITATION: FightController.is_eligible_to_fight() asks for a LIVING
model, so a unit whose every model is being kept cannot be selected to fight;
its kept models are then removed at the end of the phase.

THE AI (user decision; auto_players plus an injected verdict, no API call): buy
it when the incoming melee activation is expected to destroy at least
NEVER_BEATEN_MIN_EXPECTED_KILLS models and the unit has not been selected to
fight.
"""

from game import ai_mode, riled_up, titanic, war_horde
from game.fight_after_death import FightAfterDeath
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT

NEVER_BEATEN_NAME = "Orks Is Never Beaten"
NEVER_BEATEN_CP = 1
#: "On a 4+".
NEVER_BEATEN_THRESHOLD = 4
#: "+1 to that roll if your unit is riled up".
NEVER_BEATEN_RILED_UP_BONUS = 1
#: The AI's rule.
NEVER_BEATEN_MIN_EXPECTED_KILLS = 2


class OrksIsNeverBeatenController:
    """Sits in FightController.target_reactions; fed by the death sweep."""

    def __init__(self, stratagem_controller, decision_manager=None, turn_tracker=None,
                 fight_controller=None, game_state=None, game_log=None, auto_players=(),
                 worth_using=None):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self.game_state = game_state
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # worth_using(attacking_squad, target_squad) -> bool: the AI's answer,
        # injected by main.py. None means "always".
        self.worth_using = worth_using
        self._stratagem = Stratagem(NEVER_BEATEN_NAME, NEVER_BEATEN_CP, self._effect)
        self._active = set()      # id(squad) protected this phase
        self._handled = set()     # (id(target), id(attacker)) already offered this phase
        self._ledger = FightAfterDeath(
            NEVER_BEATEN_THRESHOLD, NEVER_BEATEN_NAME,
            game_state=game_state, game_log=game_log, bonus_for=self._bonus_for)

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)

    def _bonus_for(self, model):
        squad = getattr(model, "squad", None)
        return NEVER_BEATEN_RILED_UP_BONUS if riled_up.is_riled_up(squad) else 0

    def is_active(self, squad):
        return squad is not None and id(squad) in self._active

    def has_been_selected_to_fight(self, squad):
        fc = self.fight_controller
        ledger = getattr(fc, "fought_squad_ids", None) or ()
        return squad in ledger or getattr(fc, "fighting_squad", None) is squad

    # ----------------------------------------------------------- conditions
    def can_use(self, squad):
        if squad is None or self.is_active(squad):
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if not war_horde.fields_war_horde(squad.owner) or not war_horde.is_orks_unit(squad):
            return False
        if titanic.is_titanic_unit(squad):
            return False
        if not any(not m.is_dead() for m in squad.models):
            return False
        if self.has_been_selected_to_fight(squad):
            return False   # the EFFECT would never apply
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def is_worth_using(self, squad, attacking_squad=None):
        if self.worth_using is None or attacking_squad is None:
            return True
        return bool(self.worth_using(attacking_squad, squad))

    # ------------------------------------------------------------ the offer
    def maybe_offer(self, attacking_squad, target_squad, melee=False):
        """FightController's target_reactions entry. The unit protected is the
        TARGET - the list calls every reaction as (attacker, target, melee)."""
        if not melee or attacking_squad is None or target_squad is None:
            return False
        if attacking_squad.owner == target_squad.owner:
            return False
        key = (id(target_squad), id(attacking_squad))
        if key in self._handled:
            return False
        if not self.can_use(target_squad):
            return False
        # The verdict gates the AI only - a human is asked.
        if target_squad.owner in self.auto_players and not self.is_worth_using(
                target_squad, attacking_squad):
            return False
        self._handled.add(key)
        if target_squad.owner in self.auto_players or self.decision_manager is None:
            return self.use(target_squad)
        self.decision_manager.request(
            target_squad.owner,
            f"{attacking_squad.name} is attacking {target_squad.name} - {NEVER_BEATEN_NAME} "
            f"({NEVER_BEATEN_CP} CP)? Destroyed models roll a D6 (+1 if riled up): on a 4+ "
            f"they stay and fight with the unit.",
            [(f"Use {NEVER_BEATEN_NAME} ({NEVER_BEATEN_CP} CP)", lambda: self.use(target_squad)),
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
            self._log(f"{NEVER_BEATEN_NAME}: {squad.name} - destroyed models roll to stay and "
                      f"fight ({NEVER_BEATEN_THRESHOLD}+).")
        return True

    # --------------------------------------------------- intercepting death
    def intercept_destroyed(self, models):
        """Called from main.py's death sweep with the models it is about to
        remove. Returns those kept - already back on the board."""
        return self._ledger.roll_for(models, self._model_is_protected)

    def _model_is_protected(self, model):
        squad = getattr(model, "squad", None)
        return self.is_active(squad) and not self.has_been_selected_to_fight(squad)

    def models_kept(self):
        return self._ledger.models_owed_an_activation()

    def on_unit_finished_fighting(self, squad):
        """"When your unit has fought" - this unit's kept models are removed."""
        return self._ledger.remove_for(squad)

    def reset_phase(self):
        """"...or at the end of the phase" - everything still kept is removed."""
        self._ledger.resolve_after_attacks()
        self._active.clear()
        self._handled.clear()
