"""Canoptek Court Stratagem: Countertemporal Shift (1CP).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  WHEN:   Your opponent's Shooting phase, just after an enemy unit has selected its
          targets.
  TARGET: One CANOPTEK unit from your army that was selected as the target of one
          or more of the attacking unit's attacks.
  EFFECT: Until the end of the phase, your unit can only be selected as the target
          of a ranged attack if the attacking model is within 18".

THE EFFECT IS AN EXISTING MECHANIC, and its template is Seer Council's Psychic
Shield (game/psychic_shield.py), which prints the same EFFECT word for word. The
range lives on the unit (Squad.countertemporal_shift_range) and folds into
game/status_effects.py's targeting_range_limit() with LONE OPERATIVE and Psychic
Shield - the tighter wins. And like Psychic Shield it can make the selection that
triggered it ILLEGAL, so on_activated is wired to ShootingController.
revalidate_target_selection().

AND LIKE PSYCHIC SHIELD IT IS ONLY OFFERED WHEN IT DOES SOMETHING: the engine
denies such a target only when NO attacking model is within the limit of ANY
target model, i.e. when the closest pair is beyond 18". A shooter already inside
keeps its target either way.

THE AI USES IT WHENEVER IT IS OFFERED, for exactly that reason: offered means the
attack against its unit is denied outright.
"""

from game import ai_mode, necron_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

COUNTERTEMPORAL_SHIFT_NAME = "Countertemporal Shift"
COUNTERTEMPORAL_SHIFT_CP = 1
COUNTERTEMPORAL_SHIFT_RANGE_IN = 18.0
SETTING = "CANOPTEK_COURT_PLAYERS"


def applies(squad):
    return squad is not None and getattr(squad, "countertemporal_shift_range", None) is not None


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads or ():
        if getattr(squad, "countertemporal_shift_range", None) is not None:
            squad.countertemporal_shift_range = None


class CountertemporalShiftController:
    """An entry in main.py's shooting_target_reactions - maybe_offer(attacker,
    target, melee=False)."""

    def __init__(self, stratagem_controller=None, decision_manager=None, game_log=None,
                 turn_tracker=None, on_activated=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.on_activated = on_activated
        self.auto_players = ai_mode.players(auto_players)
        self._stratagem = Stratagem(name=COUNTERTEMPORAL_SHIFT_NAME,
                                    cp_cost=COUNTERTEMPORAL_SHIFT_CP, effect=self._effect)
        self._handled_this_phase = set()

    def reset_phase(self):
        self._handled_this_phase.clear()

    def can_use(self, attacker, target):
        if self.stratagem_controller is None or attacker is None or target is None:
            return False
        if target.owner == attacker.owner:
            return False
        if not necron_detachments.has_detachment(target.owner, SETTING):
            return False
        if not necron_detachments.is_canoptek_unit(target):
            return False
        if applies(target):
            return False
        tt = self.turn_tracker
        if tt is None or tt.phase != PHASE_SHOOTING or tt.turn_owner != attacker.owner:
            return False
        if attacker.min_distance_to(target) <= COUNTERTEMPORAL_SHIFT_RANGE_IN:
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        if melee:
            return False
        key = (id(attacker), id(target))
        if key in self._handled_this_phase:
            return False
        if not self.can_use(attacker, target):
            return False
        self._handled_this_phase.add(key)
        if target.owner in self.auto_players:
            self._use(target)
            return False
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            target.owner,
            f"{COUNTERTEMPORAL_SHIFT_NAME} ({COUNTERTEMPORAL_SHIFT_CP} CP): {attacker.name} has "
            f"targeted {target.name}. Until the end of the phase it can only be targeted by ranged "
            f"attacks from within {COUNTERTEMPORAL_SHIFT_RANGE_IN:g}\" - which forces "
            f"{attacker.name} to pick a different target.",
            [(f"{COUNTERTEMPORAL_SHIFT_NAME} ({COUNTERTEMPORAL_SHIFT_CP} CP)",
              lambda: self._use(target)),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def _use(self, target):
        return self.stratagem_controller.use(target.owner, self._stratagem, [target])

    def _effect(self, controller, player, targets):
        target = targets[0]
        target.countertemporal_shift_range = COUNTERTEMPORAL_SHIFT_RANGE_IN
        if self.game_log is not None:
            self.game_log.add(
                f"{COUNTERTEMPORAL_SHIFT_NAME}: until the end of the phase, {target.name} can only "
                f"be selected as the target of a ranged attack from within "
                f"{COUNTERTEMPORAL_SHIFT_RANGE_IN:g}\".")
        if self.on_activated is not None:
            self.on_activated()
