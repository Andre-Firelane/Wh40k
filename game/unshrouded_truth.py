"""Seer Council's "Unshrouded Truth" (1CP, Strategic Ploy).

RULE (printed, word for word):
  WHEN: "Your Movement phase"
  TARGET: "One ASURYANI INFANTRY unit from your army (excluding WRAITH CONSTRUCT
  units) that has not been selected to move this phase, was not set up on the
  battlefield this phase, and is within 9" of one or more friendly ASURYANI
  PSYKER models"
  EFFECT: "Place your unit in strategic reserves. Your unit has Deep Strike.
  Your unit must make an ingress move this phase."
  RESTRICTIONS: "Until the end of the phase, your unit is not eligible to be
  selected to move."

THE ONE DIRECTION THAT USED TO BE MISSING WAS ALREADY BUILT
-----------------------------------------------------------
This was deferred as "real new machinery: game/ingress.py only ever takes units
OUT of reserves". That was wrong - game/starflare_ignition.py's own withdraw()
had done board -> reserves since the T'au Enhancement was added. So this is its
second consumer, and the mechanical move now lives in
game/strategic_reserves.py.

WHAT IS ACTUALLY THIS STRATAGEM'S OWN is three small things, and each one is a
sentence of the EFFECT:

  * "Your unit HAS DEEP STRIKE" - a phase-scoped grant, so the arrival uses rule
    24.09's "anywhere more than 9" from every enemy" rather than 20.04's 6"
    board-edge band. Read off the unit by game/ingress.py, the same arrangement
    Squad.psychic_shield_range and Squad.ard_as_nails_active use.
  * "MUST make an ingress move THIS phase" - which normally cannot happen at
    all, because rule 20.03 lets reserves arrive only from battle round 2. The
    printed text overrides that for this unit; the same flag lifts the round
    gate, and only for it.
  * "must make an ingress move this phase", read as the user spelled it out
    ("ja der unterschied ist nur, dass ich sie sofort wieder platzieren muss") -
    so the placement is armed IMMEDIATELY rather than left as a card to pick up
    later. pending_placement is what main.py reads to arm the drag that already
    exists for a reserves card, so the very next board click sets the unit down.

THE RESTRICTIONS LINE NEEDS NO CODE, and that was checked rather than assumed:
"not eligible to be selected to move" is already true twice over. While the unit
is in reserves it is not on the battlefield at all, and once it arrives rule
20.04's own Squad.ingress_locked blocks any further move (game/movement.py's
can_move()/can_make_move() both read it) - and blocks the charge too, which is
20.04 being stricter than this stratagem, not this stratagem being ignored.

"WAS NOT SET UP ON THE BATTLEFIELD THIS PHASE" is read off Squad.set_up_this_turn,
which is per TURN rather than per phase. Exact in practice: the only ways to be
set up mid-game are an Ingress or a Rapid Ingress, both of which happen in a
Movement phase, so "this turn" and "this phase" cannot disagree for a unit whose
own Movement phase is running. Noted because the two words differ.
"""

from game.stratagems import Stratagem
from game.strategic_reserves import withdraw_to_reserves
from game.turn import PHASE_MOVEMENT
from game import strands_of_fate

UNSHROUDED_TRUTH_CP = 1
UNSHROUDED_TRUTH_NAME = "Unshrouded Truth"


def applies(squad):
    """Whether this unit is mid-Unshrouded-Truth: it has Deep Strike for the
    arrival and may arrive regardless of the battle round. Read by
    game/ingress.py."""
    return squad is not None and getattr(squad, "unshrouded_truth_active", False)


def reset_phase(squads=()):
    """"Until the end of the phase". Also the point at which an unmet
    obligation stops mattering - the unit simply stays in reserves and arrives
    under the ordinary rules later."""
    for squad in squads:
        squad.unshrouded_truth_active = False


class UnshroudedTruthController:
    """Proactive: the owner buys it at a moment of their own choosing, so an
    ActionPanel button rather than a DecisionManager break point - the same
    shape as Fate Inescapable and The Arro'kon Protocol.

    Human-only in practice like the rest of the Aeldari work. An AI would need
    its own path here (unlike the reactive four, which go through
    DecisionManager), because arming a placement is not a prompt - noted rather
    than half-built."""

    def __init__(self, stratagem_controller=None, game_state=None, movement_controller=None,
                 turn_tracker=None, game_log=None, all_tokens=None):
        self.stratagem_controller = stratagem_controller
        self.game_state = game_state
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self._stratagem = Stratagem(
            name=UNSHROUDED_TRUTH_NAME, cp_cost=UNSHROUDED_TRUTH_CP, effect=self._effect,
        )
        # The squad whose arrival is owed right now. main.py reads this once and
        # takes it, arming the reserves drag - see take_pending_placement().
        self.pending_placement = None

    def panel_label(self, squad):
        """The label says what happens NEXT, because what happens next is a
        board click the player has to know is coming."""
        return ("%s (%d CP) - into Reserves, then place it now"
                % (UNSHROUDED_TRUTH_NAME, UNSHROUDED_TRUTH_CP))

    def can_use(self, squad):
        from game.forewarned import eligible_unit, near_friendly_psyker
        if squad is None or self.stratagem_controller is None or self.game_state is None:
            return False
        # Seer Council only - see game/strands_of_fate.py's has_detachment().
        if not strands_of_fate.has_detachment(squad.owner):
            return False
        if applies(squad):
            return False
        if self.turn_tracker is None or self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if self.turn_tracker.turn_owner != squad.owner:
            return False   # "YOUR Movement phase"
        # It has to still BE on the battlefield to be placed into reserves.
        if squad in self.game_state.reserves or squad in self.game_state.embarked_squads:
            return False
        # "has not been selected to move this phase" - which is exactly what
        # MovementController.can_move() answers ("correct phase, and not yet
        # selected to move", per its own docstring), so it is asked rather than
        # re-derived. NOT selected_squad: that only means "highlighted in the
        # UI", and refusing it would make the ActionPanel button unreachable,
        # since the panel only draws for the highlighted squad.
        #
        # A unit MID-move is excluded too: start_move() is what "selecting it to
        # move" means, and move_start holds its origin until the move is
        # confirmed or cancelled.
        if self.movement_controller is not None:
            if not self.movement_controller.can_move(squad):
                return False
            starts = getattr(self.movement_controller, "move_start", {})
            if any(model.id in starts for model in squad.models):
                return False
        # "was not set up on the battlefield this phase" - see the module
        # docstring on turn vs phase.
        if getattr(squad, "set_up_this_turn", False):
            return False
        # The unit conditions are Forewarned's, word for word - read from there
        # rather than duplicated.
        if not eligible_unit(squad):
            return False
        if not near_friendly_psyker(squad, self.all_tokens):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _effect(self, controller, player, targets):
        squad = targets[0]
        # Set BEFORE the withdrawal, so nothing can observe the unit sitting in
        # reserves without the grant that lets it come straight back.
        squad.unshrouded_truth_active = True
        withdraw_to_reserves(
            self.game_state, squad, log=self.game_log,
            message=(f"{squad.owner}: {squad.name} uses Unshrouded Truth - into Strategic "
                     "Reserves with Deep Strike, and it must make its ingress move now."),
        )
        # No cancel_move() here on purpose: can_use() already refuses a unit
        # whose move has started, so there is never a half-finished move to
        # unwind at this point.
        self.pending_placement = squad

    def take_pending_placement(self):
        """Hand the owed arrival to main.py exactly once, which arms the same
        drag a reserves card would - so the next board click places the unit.
        Taken rather than read so a second frame cannot re-arm it."""
        squad = self.pending_placement
        self.pending_placement = None
        return squad
