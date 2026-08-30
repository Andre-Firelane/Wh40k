"""Auxiliary Cadre Stratagem: Alien Expertise (1CP).

RULE (verbatim, rules/tau_empire/detachments/Auxiliary Cadre.md):
  WHEN:   Your Movement phase, when a friendly KROOT/VESPID STINGWINGS unit is
          selected to make an advance move.
  TARGET: That KROOT/VESPID STINGWINGS unit.
  EFFECT: That move does not prevent your unit from being eligible to declare a
          charge.

THE FOURTH SOURCE OF ONE EXCEPTION
-----------------------------------
"Advanced this turn, may still charge" is already printed on three things -
the Orks' Waaagh!, Full Throttle, and Kroot Hounds' Loping Pounce - and
game/charge.py folds them into one `advance_ok` at one gate. This joins that
fold rather than adding a fourth condition somewhere else, which is the whole
reason that line reads as a disjunction.

LATCHED, LIKE LOPING POUNCE, NOT LIVE
--------------------------------------
The two older sources are live properties (does this unit have Full Throttle,
is a Waaagh! running). This one is bought for ONE unit at ONE moment, so it has
to be remembered - a flag on the squad, cleared at the end of the turn because
that is how long rule 09.06's ban it lifts would otherwise last.

BOUGHT BEFORE THE ADVANCE, NOT AFTER
-------------------------------------
"when a unit is SELECTED TO MAKE an advance move" - so can_use() asks for a
unit that has not moved yet, not one that already Advanced. Buying it after the
fact would be the more forgiving reading and is not the printed one; it also
could not work, since the panel offers Advance as part of the move itself.
"""

from game import auxiliary_cadre, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

ALIEN_EXPERTISE_CP = 1
ALIEN_EXPERTISE_NAME = "Alien Expertise"


def is_active(squad):
    """Read by game/charge.py's `advance_ok`, next to its three siblings."""
    return bool(getattr(squad, "alien_expertise_active", False))


class AlienExpertiseController:
    def __init__(self, stratagem_controller, movement_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=ALIEN_EXPERTISE_NAME, cp_cost=ALIEN_EXPERTISE_CP, effect=self._grant,
        )

    def expire_for_turn(self, squads=()):
        """End of TURN, not of phase: the ban it lifts (09.06) lasts the whole
        turn, so a grant that expired at the end of the Movement phase would
        buy nothing at all - the Charge phase is where it is read."""
        for squad in squads or ():
            squad.alien_expertise_active = False

    def panel_label(self, squad):
        return (f"{ALIEN_EXPERTISE_NAME} ({ALIEN_EXPERTISE_CP} CP) - "
                "may charge after Advancing")

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if is_active(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, auxiliary_cadre.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        if not auxiliary_cadre.is_harnessed_unit(squad):
            return False
        # "when it is SELECTED TO MAKE an advance move" - before the move, so
        # a unit that has already moved this phase is too late.
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
            squad.alien_expertise_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{ALIEN_EXPERTISE_NAME}: {squad.name} can declare a charge this turn "
                    "even if it Advances."
                )
