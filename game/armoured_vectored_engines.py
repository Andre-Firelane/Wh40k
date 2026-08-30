"""Armoured Warhost Stratagem: Vectored Engines (1CP).

RULE (verbatim, rules/aeldari/detachments/Armoured Warhost.md):
  WHEN:   Your Movement phase, when a friendly AELDARI VEHICLE unit makes a
          fall-back move.
  TARGET: That AELDARI VEHICLE unit.
  EFFECT: That move does not prevent your unit from being eligible to shoot.
  RESTRICTIONS: none printed.

THE FIFTH SOURCE OF ONE EXCEPTION, and it is why game/move_exceptions.py
exists. Rule 09.07's "a unit that Fell Back cannot shoot" had grown a
five-condition `and not` chain written inline in game/shooting.py, and rule
09.07's charge half a DIFFERENT two-condition chain in game/charge.py. This
Stratagem registers its latch in the one place instead of appending a sixth
term to a chain in whichever file noticed first - the hard-coded-set shape
CLAUDE.md records burning this repo twice.

IT LIFTS THE SHOOTING BAN ONLY. The printed effect is "does not prevent your
unit from being ELIGIBLE TO SHOOT" - it says nothing about charging, so it is
in SHOOT_AFTER_FALL_BACK_FLAGS and not in the charge list. Warhost's Feigned
Retreat and Windrider Host's Wind of Blades DO name both, and are in both. That
difference is the entire reason those are three lists rather than one.

BOUGHT WHEN THE MOVE HAPPENS, NOT BEFORE. "when a unit MAKES a fall-back move"
is the moment the move is declared or finished, not the start of the phase - so
this hangs on MovementController's fall-back completion rather than being a
button a unit could press while standing still. can_use() therefore asks
whether the unit actually Fell Back this turn.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, skilled_crews
from game.stratagems import Stratagem

VECTORED_ENGINES_NAME = "Vectored Engines"
VECTORED_ENGINES_CP = 1

#: The latch game/move_exceptions.py reads. Named there too - one string, two
#: readers, and the test pins that they are the same one.
VECTORED_ENGINES_FLAG = "vectored_engines_active"


def is_active(squad):
    return bool(getattr(squad, VECTORED_ENGINES_FLAG, False))


def applies(squad):
    if squad is None or not skilled_crews.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    return any(getattr(m.profile, "vehicle", False)
               for m in (getattr(squad, "models", ()) or ()) if not m.is_dead())


class VectoredEnginesController:
    """Offered the moment the fall-back move is made."""

    def __init__(self, stratagem_controller, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._stratagem = Stratagem(
            name=VECTORED_ENGINES_NAME, cp_cost=VECTORED_ENGINES_CP, effect=self._grant,
        )

    def can_use(self, squad):
        from game.turn import PHASE_MOVEMENT
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False                      # "YOUR Movement phase"
        if is_active(squad):
            return False
        if not applies(squad):
            return False
        # "when a unit MAKES a fall-back move" - the move has to have happened,
        # or the CP buys an exemption from a ban the unit is not under.
        if not getattr(squad, "fell_back_this_turn", False):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def offer_after_fall_back(self, squad):
        """Wired to the fall-back completion hook."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False                      # no AI path
        self.decision_manager.request(
            squad.owner,
            "%s (%d CP): %s fell back - may it still shoot this turn?"
            % (VECTORED_ENGINES_NAME, VECTORED_ENGINES_CP, squad.name),
            [("Use (%d CP)" % VECTORED_ENGINES_CP, (lambda: self.use(squad))),
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
            setattr(squad, VECTORED_ENGINES_FLAG, True)
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s may shoot this turn despite having fallen back."
                    % (VECTORED_ENGINES_NAME, squad.name))
