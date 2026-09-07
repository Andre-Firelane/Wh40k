"""Warhost Stratagem: Feigned Retreat (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Warhost.md):
  WHEN:   Your Movement phase, just after an ASURYANI unit from your army Falls
          Back.
  TARGET: That ASURYANI unit.
  EFFECT: Until the end of the turn, your unit is eligible to shoot and declare
          a charge in a turn in which it Fell Back.
  RESTRICTIONS: none printed.

TWO OF THE FOUR EXEMPTIONS, where Wind of Blades has all four - and the
difference is printed, not a simplification. This one says only "in a turn in
which it Fell Back"; the Windrider one adds "or Advanced". So the latch is
registered in exactly two of game/move_exceptions.py's four sets, and the two
it is NOT in have their own test line. Registering it in all four would be a
free extra permission that no test looking at Fall Back could see.

"JUST AFTER ... FALLS BACK" IS A MOMENT THIS ENGINE DID NOT PUBLISH. Fall Back
is confirmed in FallBackController.confirm(), which had no listeners at all -
so it grew on_fall_back_finished, a LIST for the same reason
on_ingress_resolved and on_squad_finished_shooting are lists rather than single
slots. It fires only when the move actually succeeded: confirm() leaves the
controller in MOVING and returns early when the move failed (still engaged, no
room), and a Stratagem offered on a retreat that did not happen would be a
refund waiting to be spent.

AND IT FIRES BEFORE THE DESPERATE ESCAPE HAZARD ROLL RATHER THAN AFTER. The
printed WHEN is "just after the unit Falls Back", and the Fall Back is what has
just happened; the Hazard Roll is a consequence of one KIND of it. Ordering it
after would also mean the offer never appears for a unit the roll wipes out,
which the printed text does not say.

IT IS AN OFFER, NOT A BUTTON. Every other Warhost Stratagem with a "your
Movement phase" WHEN could be a panel button because the player picks the
moment; this one names an instant that has just passed, so it is asked at that
instant like the reactive ones - and refused for a unit that did not just Fall
Back, which is the whole TARGET clause.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, ai_mode, martial_grace, move_exceptions
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

FEIGNED_RETREAT_NAME = "Feigned Retreat"
FEIGNED_RETREAT_CP = 1

#: The latch. Registered in exactly TWO of move_exceptions' four sets - this
#: Stratagem says nothing about Advancing.
FEIGNED_RETREAT_FLAG = "feigned_retreat_active"


def is_active(squad):
    return bool(getattr(squad, FEIGNED_RETREAT_FLAG, False))


def eligible_unit(squad):
    """"One ASURYANI unit from your army"."""
    if squad is None or not martial_grace.has_detachment(getattr(squad, "owner", None)):
        return False
    return aeldari_detachments.is_asuryani_unit(squad)


class FeignedRetreatController:
    """The just-after-a-Fall-Back offer."""

    def __init__(self, stratagem_controller, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._stratagem = Stratagem(
            name=FEIGNED_RETREAT_NAME, cp_cost=FEIGNED_RETREAT_CP, effect=self._grant,
        )

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_MOVEMENT:
                return False
            # "YOUR Movement phase".
            if squad.owner != self.turn_tracker.turn_owner:
                return False
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def notify_fell_back(self, squad):
        """Fed from FallBackController.confirm(), and only on a move that
        actually succeeded."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False               # no AI path
        self.decision_manager.request(
            squad.owner,
            "%s (%d CP): %s just Fell Back - let it shoot and declare a charge "
            "this turn anyway?"
            % (FEIGNED_RETREAT_NAME, FEIGNED_RETREAT_CP, squad.name),
            [("Use (%d CP)" % FEIGNED_RETREAT_CP, (lambda: self.use(squad))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            setattr(squad, FEIGNED_RETREAT_FLAG, True)
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s may shoot and declare a charge this turn despite "
                    "Falling Back." % (FEIGNED_RETREAT_NAME, squad.name))
