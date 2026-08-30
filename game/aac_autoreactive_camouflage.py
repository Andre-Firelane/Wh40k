"""Advanced Acquisition Cadre Stratagem: Autoreactive Camouflage (1CP).

RULE (verbatim, rules/tau_empire/detachments/Advanced Acquisition Cadre.md):
  WHEN:   Your opponent's Shooting phase, when an enemy unit targets a friendly
          PATHFINDER TEAM/STEALTH BATTLESUITS unit, if that friendly unit is
          hidden.
  TARGET: That PATHFINDER TEAM/STEALTH BATTLESUITS unit.
  EFFECT: Your unit has +1 Sv.

"+1 Sv" IS A BETTER SAVE, SO A LOWER THRESHOLD
-----------------------------------------------
A save characteristic improves downwards (3+ is better than 4+), and
game/damage_resolution.py's save_thresholds() works in thresholds - so "+1 Sv"
subtracts 1 there. It joins that function beside the Death Guard Plague's own
save penalty, which is the same arithmetic in the other direction, so the panel
and the resolution keep agreeing about a save (the whole reason that function
was extracted).

"IF THAT FRIENDLY UNIT IS HIDDEN" IS CHECKED, AND IT IS NOT FREE
-----------------------------------------------------------------
Hidden (13.09) needs terrain, a turn tracker and the shooting record - the same
four arguments status_effects.is_hidden() always takes - so the controller is
given a callable that answers it rather than reaching for that state itself.
The condition matters: this detachment's own rule keeps its units Hidden after
they shoot, so the two are meant to work together, and a version that skipped
the check would hand the bonus to units the Stratagem never covered.
"""

from game import advanced_acquisition_cadre as aac, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

AUTOREACTIVE_CP = 1
AUTOREACTIVE_NAME = "Autoreactive Camouflage"
AUTOREACTIVE_SAVE_BONUS = 1


def is_active(squad):
    return bool(getattr(squad, "autoreactive_camouflage_active", False))


def save_bonus_for(squad):
    """The amount to SUBTRACT from the save threshold - "+1 Sv" is better."""
    return AUTOREACTIVE_SAVE_BONUS if is_active(squad) else 0


class AutoreactiveCamouflageController:
    def __init__(self, stratagem_controller, turn_tracker=None,
                 is_hidden_check=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        # (squad) -> bool. Injected so this module needs no terrain, tracker or
        # shooting record of its own; None reads as "not hidden", which
        # withholds the Stratagem rather than granting it for free.
        self.is_hidden_check = is_hidden_check
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = tuple(auto_players)
        self._offered_this_phase = set()
        self._stratagem = Stratagem(
            name=AUTOREACTIVE_NAME, cp_cost=AUTOREACTIVE_CP, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.autoreactive_camouflage_active = False
        self._offered_this_phase = set()

    def _is_hidden(self, squad):
        return bool(self.is_hidden_check is not None and self.is_hidden_check(squad))

    def maybe_offer(self, attacker, target, melee=False):
        """ShootingController.target_reactions' protocol - the same instant
        Stim Injectors and Counterfire Defence Systems react at."""
        if melee or attacker is None or target is None:
            return False
        if target.owner == attacker.owner:
            return False
        if is_active(target):
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if not tau_detachments.has_detachment(target.owner, aac.SETTING):
            return False
        if not tau_detachments.is_tau_unit(target) or not aac.is_fieldcraft_unit(target):
            return False
        if not self._is_hidden(target):
            return False
        key = (id(attacker), id(target))
        if key in self._offered_this_phase:
            return False
        if not self.stratagem_controller.can_use(target.owner, self._stratagem, [target]):
            return False
        self._offered_this_phase.add(key)
        if target.owner in self.auto_players or self.decision_manager is None:
            return False
        self.decision_manager.request(
            target.owner,
            f"{AUTOREACTIVE_NAME} ({AUTOREACTIVE_CP} CP): {attacker.name} is shooting "
            f"{target.name}, which is hidden - give it +{AUTOREACTIVE_SAVE_BONUS} Sv?",
            [(f"Use ({AUTOREACTIVE_CP} CP)",
              (lambda: self.stratagem_controller.use(target.owner, self._stratagem, [target]))),
             ("Decline", lambda: None)],
        )
        return True

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.autoreactive_camouflage_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{AUTOREACTIVE_NAME}: {squad.name} has "
                    f"+{AUTOREACTIVE_SAVE_BONUS} to its Save characteristic this phase."
                )
