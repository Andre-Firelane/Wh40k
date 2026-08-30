"""Guardian Battlehost Stratagem: Time to Strike (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  WHEN:   Your Movement phase.
  TARGET: One STORM GUARDIANS unit from your army that has not been selected to
          move this phase.
  EFFECT: Until the end of the phase, each time your unit Advances, do not make
          an Advance roll. Instead, until the end of the phase, add 6" to the
          Move characteristic of models in your unit. Until the end of the turn,
          your unit is eligible to shoot and declare a charge in a turn in which
          it Advanced.
  RESTRICTIONS: none printed.

MONT'KA'S AGGRESSIVE MOBILITY PLUS TWO EXEMPTIONS. The first two sentences are
that Stratagem word for word - no Advance roll, +6" instead - and they read the
same two seams: game/coldstar.py's effective_movement_in() and the no-roll
branch in game/movement.py. Rather than a second flag meaning the same thing at
those two places, this sets ITS OWN flag and both modules ask a shared
question, which is the second-consumer rule applied to a two-line predicate.

TWO CLOCKS, AND THE PRINTED TEXT IS EXPLICIT ABOUT IT. The Advance change lasts
"until the end of the PHASE"; the shoot-and-charge exemption lasts "until the
end of the TURN". Two lifetimes on one purchase, so two flags rather than one -
folding them together would silently extend or cut one of them, which is the
mistake game/protocol_sudden_storm.py records for its own pair.

THE TWO EXEMPTIONS GO TO game/move_exceptions.py, not to a keyword grant.
"Eligible to shoot ... in a turn in which it Advanced" is about the UNIT; the
weapon-level way to shoot after Advancing is [ASSAULT], and granting that would
mean something different (it would also survive into other rules that read the
keyword).

STORM GUARDIANS ONLY - narrower than this detachment's other Stratagems, which
say "DIRE AVENGERS or GUARDIANS". STORM GUARDIANS is its own keyword line, and
GUARDIANS is on it too, so reading the wider one would hand this to Guardian
Defenders as well. Its own list, checked at its own name.
"""

from game import aeldari_detachments, defend_at_all_costs
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

TIME_TO_STRIKE_NAME = "Time to Strike"
TIME_TO_STRIKE_CP = 1

#: 'add 6" to the Move characteristic'.
TIME_TO_STRIKE_BONUS_IN = 6.0

#: The unit this Stratagem names - narrower than the detachment's others.
TIME_TO_STRIKE_KEYWORD = "STORM GUARDIANS"

#: The turn-long half, read by game/move_exceptions.py.
TIME_TO_STRIKE_TURN_FLAG = "time_to_strike_active"


def is_active(squad):
    """The PHASE-long half: no Advance roll, +6" Move."""
    return bool(getattr(squad, "time_to_strike_move_active", False))


def move_bonus_for(squad):
    return TIME_TO_STRIKE_BONUS_IN if is_active(squad) else 0.0


def skips_advance_roll(squad):
    """"do not make an Advance roll" - read where the roll is made."""
    return is_active(squad)


def eligible_unit(squad):
    if squad is None or not defend_at_all_costs.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, TIME_TO_STRIKE_KEYWORD)


def reset_phase(squads=()):
    """Only the MOVE half. The shoot-and-charge exemption is turn-long and is
    cleared by game/move_exceptions.py's own sweep."""
    for squad in squads or ():
        if squad is not None:
            squad.time_to_strike_move_active = False


class TimeToStrikeController:
    """A Movement-phase panel button."""

    def __init__(self, stratagem_controller, movement_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=TIME_TO_STRIKE_NAME, cp_cost=TIME_TO_STRIKE_CP, effect=self._grant,
        )

    def panel_label(self, squad):
        return ('%s (%d CP) - auto-Advance +%g", and still shoot and charge'
                % (TIME_TO_STRIKE_NAME, TIME_TO_STRIKE_CP, TIME_TO_STRIKE_BONUS_IN))

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
            # TWO CLOCKS: the move change is phase-long, the exemptions are
            # turn-long. Two flags, cleared by two different sweeps.
            squad.time_to_strike_move_active = True
            setattr(squad, TIME_TO_STRIKE_TURN_FLAG, True)
            if self.game_log is not None:
                self.game_log.add(
                    '%s: %s Advances %g" without a roll this phase, and may still '
                    "shoot and charge this turn."
                    % (TIME_TO_STRIKE_NAME, squad.name, TIME_TO_STRIKE_BONUS_IN))
