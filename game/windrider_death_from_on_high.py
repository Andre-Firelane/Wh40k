"""Windrider Host Stratagem: Death from on High (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  WHEN:   Your Shooting phase or the Fight phase.
  TARGET: One ASURYANI MOUNTED or VYPER unit from your army that was set upon
          the battlefield from Reserves this turn and has not been selected to
          shoot or fight this phase.
  EFFECT: Until the end of the phase, each time a model in your unit makes an
          attack, you can re-roll the Wound roll.
  RESTRICTIONS: none printed.

"SET UPON THE BATTLEFIELD FROM RESERVES THIS TURN" IS THE WHOLE PROBLEM, and
the two obvious answers are both wrong:

  * Squad.set_up_this_turn is set by SetupController for EVERY placement,
    deployment included - so during battle round 1 it would be true of the
    entire army, and this Stratagem would be buyable by units that never saw a
    Reserve.
  * IngressController.ingressed_this_phase is the right FACT on the wrong
    CLOCK. It is reset at the start of each Movement phase, so during the
    Shooting and Fight phases of that same turn it still happens to hold the
    right answer - but only because reset_movement_phase() has not run again
    yet. That is a coincidence of ordering rather than a statement about
    turns, and the next change to the reset would have broken this silently.

So IngressController grew ingressed_this_turn, written beside the phase set at
the one place an arrival is confirmed, and cleared in main.py's end-of-turn
block. It covers Rapid Ingress (15.07) too, which arrives during the
OPPONENT's Movement phase: such a unit genuinely was "set up from Reserves
this turn" when the shared Fight phase comes round, and the printed text does
not exclude it.

"THE FIGHT PHASE", NOT "YOUR FIGHT PHASE" - so the Fight-phase half carries no
owner check while the Shooting-phase half does. One printed word, and it is
the difference between a unit that can use this in its opponent's turn and one
that cannot. Its own test line, because the two halves are one sentence and
read as one.

"YOU CAN RE-ROLL THE WOUND ROLL" IS THE WHOLE ROLL, not just the failures -
the distinction game/reroll_scope.py exists for. It is deliberately NOT
registered there: that module is for the narrower "the 1s OR the whole roll,
never just the failures" shape, which comes from an automatic-1s clause this
Stratagem does not print. Listing it there would offer a 1s-only option the
printed text never gives. Pinned as an absence, since that is the only place
it shows.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import ride_the_wind
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

DEATH_FROM_ON_HIGH_NAME = "Death from on High"
DEATH_FROM_ON_HIGH_CP = 1


def is_active(squad):
    return bool(getattr(squad, "death_from_on_high_active", False))


def eligible_unit(squad):
    """"One ASURYANI MOUNTED or VYPER unit from your army"."""
    if squad is None or not ride_the_wind.has_detachment(getattr(squad, "owner", None)):
        return False
    return ride_the_wind.applies(squad)


def offers_reroll(squad):
    """Read by BOTH attack chains' _wound_reroll_reason() - the printed WHEN
    names both phases."""
    return is_active(squad)


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.death_from_on_high_active = False


class DeathFromOnHighController:
    """A Shooting- or Fight-phase panel button."""

    def __init__(self, stratagem_controller, ingress_controller=None,
                 shooting_controller=None, fight_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.ingress_controller = ingress_controller
        self.shooting_controller = shooting_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=DEATH_FROM_ON_HIGH_NAME, cp_cost=DEATH_FROM_ON_HIGH_CP,
            effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - re-roll this unit's Wound rolls this phase"
                % (DEATH_FROM_ON_HIGH_NAME, DEATH_FROM_ON_HIGH_CP))

    def arrived_this_turn(self, squad):
        """"was set upon the battlefield from Reserves this turn" - asked of
        the controller that owns that fact rather than re-derived."""
        if self.ingress_controller is None:
            return False
        return squad in getattr(self.ingress_controller, "ingressed_this_turn", ())

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        phase = self.turn_tracker.phase
        if phase == PHASE_SHOOTING:
            if squad.owner != self.turn_tracker.active_player:
                return False           # "YOUR Shooting phase"
            if self.shooting_controller is not None \
                    and self.shooting_controller.active_squad is squad:
                return False           # "has not been selected to shoot"
        elif phase == PHASE_FIGHT:
            # "THE Fight phase" - it belongs to nobody, so no owner check.
            if self.fight_controller is not None \
                    and getattr(self.fight_controller, "fighting_squad", None) is squad:
                return False           # "...or fight this phase"
        else:
            return False
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        if not self.arrived_this_turn(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.death_from_on_high_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s arrived from Reserves this turn and may re-roll its "
                    "Wound rolls this phase."
                    % (DEATH_FROM_ON_HIGH_NAME, squad.name))
