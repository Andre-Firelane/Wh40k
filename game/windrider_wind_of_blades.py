"""Windrider Host Stratagem: Wind of Blades (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  WHEN:   Your Movement phase.
  TARGET: One ASURYANI MOUNTED or VYPER unit from your army that has not been
          selected to move this phase.
  EFFECT: Until the end of the turn, your unit is eligible to shoot and declare
          a charge in a turn in which it Advanced or Fell Back.
  RESTRICTIONS: none printed.

FOUR EXEMPTIONS ON ONE LATCH, and that is the whole of it. This is the widest
of the four Stratagems that touch rules 09.06 and 09.07 - Vectored Engines
lifts one ban, Time to Strike two, Feigned Retreat two, and this one all FOUR
("shoot and declare a charge" x "Advanced or Fell Back"). Written as a single
flag registered in all four of game/move_exceptions.py's sets rather than as
four separate grants, because it IS one purchase: a version where the unit may
charge after Falling Back but not after Advancing would pass any test that only
drove one of the two moves.

WHY IT IS NOT A KEYWORD GRANT. The weapon-level way to fire after Advancing is
[ASSAULT] (24.04), which is a property of the WEAPON; this exempts the UNIT and
so reaches every gun it carries, including ones the keyword would be wrong for.
That argument, and the module it led to, are written out in
game/move_exceptions.py's own docstring.

TURN-LONG, and cleared by move_exceptions.clear_turn_flags() with its three
siblings rather than by a sweep of this module's own - one lifetime, one place
that ends it.

BOUGHT BEFORE THE MOVE, NOT AFTER. "has not been selected to move this phase"
is the printed TARGET clause, so the decision is made without knowing what the
dice will do - which is what makes it a Ploy rather than a rebate.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import move_exceptions, ride_the_wind
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

WIND_OF_BLADES_NAME = "Wind of Blades"
WIND_OF_BLADES_CP = 1

#: The latch itself. Registered in ALL FOUR of move_exceptions' sets; the name
#: lives here because this module owns it, and that module reads it by name.
WIND_OF_BLADES_FLAG = "wind_of_blades_active"


def is_active(squad):
    return bool(getattr(squad, WIND_OF_BLADES_FLAG, False))


def eligible_unit(squad):
    """"One ASURYANI MOUNTED or VYPER unit from your army" - the detachment
    rule's own set, asked of the module that owns it."""
    if squad is None or not ride_the_wind.has_detachment(getattr(squad, "owner", None)):
        return False
    return ride_the_wind.applies(squad)


class WindOfBladesController:
    """A Movement-phase panel button."""

    def __init__(self, stratagem_controller, movement_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=WIND_OF_BLADES_NAME, cp_cost=WIND_OF_BLADES_CP, effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - shoot and charge after Advancing or Falling Back"
                % (WIND_OF_BLADES_NAME, WIND_OF_BLADES_CP))

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False               # "YOUR Movement phase"
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        # "has not been selected to move this phase".
        if self.movement_controller is not None \
                and squad in getattr(self.movement_controller, "moved_squad_ids", ()):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            setattr(squad, WIND_OF_BLADES_FLAG, True)
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s may shoot and charge this turn even after Advancing "
                    "or Falling Back." % (WIND_OF_BLADES_NAME, squad.name))
