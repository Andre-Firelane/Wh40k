"""Green Tide Stratagem: 'Ere We Go (1CP, Mecha Orks stage G3).

RULE (verbatim, rules/orks/detachments/Green Tide.md):
  WHEN:   Your Movement phase, when a friendly BEAST SNAGGA BOYZ/BOYZ unit is
          selected to move.
  TARGET: That BEAST SNAGGA BOYZ/BOYZ unit.
  EFFECT: Your unit has +2 to advance rolls.

ADVANCE ROLLS ONLY. The pre-codex War Horde card of the same name (retired in
1786db5) added 2 to Advance AND Charge rolls for any ORKS INFANTRY unit; this
one names only the Advance roll and only the two datasheets. So it is not a term
of game/roll_bonus.py's advance_and_charge_bonus() - which the Charge roll also
reads - but of roll_bonus.advance_sources(), the Advance-only list that
game/movement.py's advance_roll_modifiers() folds in. The +2 lands on the roll
TOTAL, so the dice panel's heading and a Command Re-roll's reconciliation see
the same number (advance_total() is the one place).

"SELECTED TO MOVE" is read the way Fungus-Fuel Injection and Mont'ka's
Aggressive Mobility read their identical WHEN: the unit has not moved or
Advanced yet this phase. The Advance roll is made when the move starts, so the
Stratagem has to be bought before - and a unit that already Advanced gains
nothing, which is also why it is refused then (error class 5).

"BEAST SNAGGA BOYZ/BOYZ" are two datasheet names (game/green_tide.py). It lasts
the phase: the move it is bought for is in this phase.

THE AI buys it at the moment it has decided to Advance with such a unit, before
the roll - ai/agent_driver.py's _handle_movement(), the one place that knows.
"""

from game import green_tide
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

ERE_WE_GO_NAME = "'Ere We Go"
ERE_WE_GO_CP = 1
#: "+2 to advance rolls".
ERE_WE_GO_ADVANCE_BONUS = 2


def is_active(squad):
    return bool(getattr(squad, "ere_we_go_active", False))


def advance_bonus(squad):
    """game/roll_bonus.py's advance_sources() asks this."""
    return ERE_WE_GO_ADVANCE_BONUS if squad is not None and is_active(squad) else 0


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "ere_we_go_active", False):
            squad.ere_we_go_active = False


def is_eligible_target(squad):
    return (squad is not None and green_tide.fields_green_tide(getattr(squad, "owner", None))
            and green_tide.is_beast_snagga_boyz_or_boyz_unit(squad))


class EreWeGoController:
    """A panel button (game/proactive_stratagems.py): can_use / use / panel_label."""

    def __init__(self, stratagem_controller, turn_tracker=None, movement_controller=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.movement_controller = movement_controller
        self.game_log = game_log
        self._stratagem = Stratagem(ERE_WE_GO_NAME, ERE_WE_GO_CP, self._grant)

    def panel_label(self, squad):
        return f"{ERE_WE_GO_NAME} ({ERE_WE_GO_CP} CP) - +2 to the Advance roll"

    def reset_phase(self, squads=()):
        reset_phase(squads)

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.turn_owner:
            return False
        if is_active(squad) or not is_eligible_target(squad):
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
            squad.ere_we_go_active = True
            if self.game_log is not None:
                self.game_log.add(f"{ERE_WE_GO_NAME}: {squad.name} has +2 to its Advance roll this phase.")
        return True
