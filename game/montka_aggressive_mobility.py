"""Mont'ka Stratagem: Aggressive Mobility (1CP).

RULE (verbatim, rules/tau_empire/detachments/Mont'ka.md):
  WHEN:   Your Movement phase.
  TARGET: One T'AU EMPIRE unit from your army that has not been selected to
          move this phase.
  EFFECT: Until the end of the phase, if your unit Advances, do not make an
          Advance roll for it. Instead, until the end of the phase, add 6" to
          the Move characteristic of models in your unit.

IT REPLACES THE ROLL, IT DOES NOT ADD TO IT
--------------------------------------------
"do not make an Advance roll ... INSTEAD add 6" to the Move characteristic" -
so the flat 6" is not a bonus on top of a D6, it is what happens instead of
one. A D6 averages 3.5, so this is both better on average and, more to the
point, CERTAIN - which is the whole reason to spend a CP on it.

Two halves, and both must be honoured or the Stratagem is a downgrade: the
Advance roll is skipped, AND the Move characteristic grows. Skipping the roll
alone would make Advancing move the unit nothing extra at all.
"""

from game import montka, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

AGGRESSIVE_MOBILITY_CP = 1
AGGRESSIVE_MOBILITY_NAME = "Aggressive Mobility"
AGGRESSIVE_MOBILITY_BONUS_IN = 6.0


def is_active(squad):
    return bool(getattr(squad, "aggressive_mobility_active", False))


def move_bonus_for(squad):
    """+6" to the Move characteristic, read by effective_movement_in()."""
    return AGGRESSIVE_MOBILITY_BONUS_IN if is_active(squad) else 0.0


def skips_advance_roll(squad):
    """"do not make an Advance roll for it" - read where the roll is made."""
    return is_active(squad)


class AggressiveMobilityController:
    def __init__(self, stratagem_controller, movement_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=AGGRESSIVE_MOBILITY_NAME, cp_cost=AGGRESSIVE_MOBILITY_CP,
            effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.aggressive_mobility_active = False

    def panel_label(self, squad):
        return (f"{AGGRESSIVE_MOBILITY_NAME} ({AGGRESSIVE_MOBILITY_CP} CP) - "
                f'Advance without rolling, +{AGGRESSIVE_MOBILITY_BONUS_IN:g}" Move')

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if is_active(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, montka.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        # "has not been selected to move this phase".
        if self.movement_controller is not None:
            if squad in getattr(self.movement_controller, "moved_squad_ids", ()):
                return False
            if getattr(self.movement_controller, "selected_squad", None) is squad:
                return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.aggressive_mobility_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{AGGRESSIVE_MOBILITY_NAME}: {squad.name} Advances without a roll and "
                    f'adds {AGGRESSIVE_MOBILITY_BONUS_IN:g}" to its Move this phase.'
                )
