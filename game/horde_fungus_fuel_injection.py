"""War Horde Stratagem: Fungus-Fuel Injection (1CP).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  WHEN:   Your Movement phase, when a friendly ORKS MOUNTED/VEHICLE unit is
          selected to move.
  TARGET: That ORKS MOUNTED/VEHICLE unit.
  EFFECT: Your unit has +2" M.

"SELECTED TO MOVE" is read the way Mont'ka's Aggressive Mobility reads its
identical WHEN: the unit has not moved or Advanced yet this phase - NOT
`movement_controller.selected_squad is squad`, which a mere click sets and which
once kept that button from ever rendering. The Move characteristic is read when
the move starts, so the Stratagem has to be bought before.

+2" ADDS to whatever the characteristic has become, so it is a term on
game/coldstar.py's `total`. It lasts the phase: the move it is bought for is in
this phase, and reset_phase() clears it at the boundary.

THE AI (ai/agent_driver.py's _handle_fungus_fuel()) buys it when the nearest
enemy is further than the unit's Move and within Move + 2".
"""

from game import attached_units, war_horde
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

FUNGUS_FUEL_NAME = "Fungus-Fuel Injection"
FUNGUS_FUEL_CP = 1
#: "+2\" M".
FUNGUS_FUEL_BONUS_IN = 2.0


def is_active(squad):
    return bool(getattr(squad, "fungus_fuel_injection_active", False))


def move_bonus_for(squad):
    """game/coldstar.py's effective_movement_in() asks this."""
    return FUNGUS_FUEL_BONUS_IN if squad is not None and is_active(squad) else 0.0


def is_mounted_or_vehicle(squad):
    return attached_units.unit_has_keyword(
        squad, lambda m: getattr(m.profile, "mounted", False) or getattr(m.profile, "vehicle", False))


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "fungus_fuel_injection_active", False):
            squad.fungus_fuel_injection_active = False


class FungusFuelInjectionController:
    """A panel button (game/proactive_stratagems.py): can_use / use / panel_label."""

    def __init__(self, stratagem_controller, turn_tracker=None, movement_controller=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.movement_controller = movement_controller
        self.game_log = game_log
        self._stratagem = Stratagem(FUNGUS_FUEL_NAME, FUNGUS_FUEL_CP, self._grant)

    def panel_label(self, squad):
        return f"{FUNGUS_FUEL_NAME} ({FUNGUS_FUEL_CP} CP) - +2\" Move"

    def reset_phase(self, squads=()):
        reset_phase(squads)

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.turn_owner:
            return False
        if is_active(squad):
            return False
        if not war_horde.fields_war_horde(squad.owner) or not war_horde.is_orks_unit(squad):
            return False
        if not is_mounted_or_vehicle(squad):
            return False
        if self.movement_controller is not None:
            if squad in getattr(self.movement_controller, "moved_squad_ids", ()):
                return False
            if squad in getattr(self.movement_controller, "advanced_squad_ids", ()):
                return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.fungus_fuel_injection_active = True
            if self.game_log is not None:
                self.game_log.add(f"{FUNGUS_FUEL_NAME}: {squad.name} has +2\" Move this phase.")
        return True
