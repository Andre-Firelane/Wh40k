"""Advanced Acquisition Cadre Stratagem: Microdrone Support (1CP).

RULE (verbatim, rules/tau_empire/detachments/Advanced Acquisition Cadre.md):
  WHEN:   Your Shooting phase, when a friendly PATHFINDER TEAM/STEALTH
          BATTLESUITS unit starts an action.
  TARGET: That PATHFINDER TEAM/STEALTH BATTLESUITS unit.
  EFFECT: That action does not prevent your unit from being eligible to shoot.

IT LIFTS ONE HALF OF RULE 16.01, NOT BOTH
------------------------------------------
Starting an action locks a unit out of BOTH shooting and declaring a charge
(game/actions.py's blocks_shooting() and blocks_charge()). This lifts the
SHOOTING half only - the printed text says "eligible to shoot" and nothing
about charging - so the charge lock stays. The two halves are already separate
methods there, which is what makes lifting one of them a one-line question
rather than a new concept.

game/actions.py's own note records that the shooting half has a TITANIC
carve-out and the charge half does not; that asymmetry is untouched here.
"""

from game import advanced_acquisition_cadre as aac, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

MICRODRONE_SUPPORT_CP = 1
MICRODRONE_SUPPORT_NAME = "Microdrone Support"


def is_active(squad):
    """Read by game/actions.py's blocks_shooting()."""
    return bool(getattr(squad, "microdrone_support_active", False))


class MicrodroneSupportController:
    def __init__(self, stratagem_controller, action_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.action_controller = action_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=MICRODRONE_SUPPORT_NAME, cp_cost=MICRODRONE_SUPPORT_CP, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.microdrone_support_active = False

    def panel_label(self, squad):
        return (f"{MICRODRONE_SUPPORT_NAME} ({MICRODRONE_SUPPORT_CP} CP) - "
                "shoot despite the action")

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if is_active(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, aac.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        if not aac.is_fieldcraft_unit(squad):
            return False
        # "when a unit STARTS AN ACTION" - so it must actually have one, and
        # that action must be what is stopping it from shooting. Without this
        # the Stratagem would be on offer to buy nothing.
        if self.action_controller is None:
            return False
        if not self.action_controller.blocks_shooting(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.microdrone_support_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{MICRODRONE_SUPPORT_NAME}: {squad.name} can still shoot this phase "
                    "despite its action."
                )
