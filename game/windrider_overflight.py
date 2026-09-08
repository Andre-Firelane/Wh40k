"""Windrider Host Stratagem: Overflight (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  WHEN:   End of your Shooting phase or the end of the Fight phase.
  TARGET: One ASURYANI MOUNTED unit from your army that destroyed one or more
          enemy units this phase.
  EFFECT: Your unit can make a Normal move of up to 7".
  RESTRICTIONS: none printed.

NARROWER THAN ITS FIVE SIBLINGS: "ASURYANI MOUNTED", with no "or VYPER". Every
other Windrider Host Stratagem names both, so this is the one place the
detachment's own set is the wrong answer and ride_the_wind.applies() must not
be used. Its own predicate, and its own test line - the same shape as Time to
Strike being STORM GUARDIANS where its siblings are GUARDIANS.

"DESTROYED ONE OR MORE ENEMY UNITS THIS PHASE" is a fact about a moment that
is over by the time the offer is made, so it is RECORDED rather than derived:
main.py's death sweep already reports each wiped-out squad together with
whoever was attacking, and this controller keeps those killers for the phase.
Deriving it afterwards is not possible - the dead unit is gone, and nothing on
the killer remembers.

THREE THINGS ABOUT THAT LEDGER AND THAT WINDOW, ALL OF WHICH USED TO BE WRONG,
and each of which killed this Stratagem on its own:

  1. THE WINDOW IS A FACT THIS MODULE OWNS. can_use() used to read the live
     turn_tracker.phase. Its only offer is main.py's advance_turn_phase(),
     which calls advance_phase() FIRST - so at the end of Shooting the clock
     already reads Charge, and at the end of Fight it has rolled round to
     Command. Both halves of the WHEN therefore fell through the `elif phase
     != PHASE_FIGHT` arm and it was never offered. See game/phase_window.py.
  2. reset_phase() ROTATES, it does not clear. main.py's per-phase reset block
     runs BEFORE that boundary's own offers (deliberately, so a stale window
     cannot outlive its phase) - so emptying the ledger there emptied exactly
     the kills the offer was about to read. The kills of the phase that just
     ENDED are what this Stratagem asks about, so they move to their own set
     and the live one starts empty.
  3. A KILLERLESS DEATH IS DEFERRED, not dropped. main.py's sweep passes
     `shooting_controller.active_squad or fight_controller.fighting_squad`,
     and that is regularly NOBODY: remove_dead_models() runs once per frame
     after the event loop, and _actually_finish_squad() has already nulled
     active_squad when the LAST weapon group wipes a unit - which is the
     ordinary way a Windrider unit destroys something. Same cause and same
     fix as game/montka_pinpoint_counter_offensive.py: the death is parked and
     credited from the post-activation hooks, where the attacker arrives as an
     argument and cannot be guessed.

"THE END OF THE FIGHT PHASE", NOT "YOUR FIGHT PHASE" - so the Fight-phase half
carries no owner check while the Shooting-phase half does. That one printed
word makes this a REACTIVE move: a unit can destroy an enemy in its opponent's
Fight phase (it was charged, or it interrupted with Counteroffensive) and then
take this move in a turn that is not its own.

WHICH IS WHY IT GOES THROUGH start_battle_focus_move() AND IS LISTED IN
REACTIVE_MOVE_MODES. That method is the single door for a reactive Normal move
of a named distance, and its docstring makes registration a requirement: a
mode that skips the set is one the AI walks straight over, which has now been
reported twice in this repo in the same words. It also needs the same
active_player hand-off Path of the Outcast documents - MovementController's
select() refuses a unit in the opponent's turn - and therefore its own Confirm
branch in the panel to hand it back.

7" IS A NAMED DISTANCE, not the unit's Move characteristic. Passing it as the
cap rather than falling back to effective_movement_in() is what keeps a
16"-Move Vyper honest, and it is also usually the SMALLER number, so reading
it the other way would be a silent buff.

NO RESTRICTIONS ARE PRINTED, and the absence is the point: this move locks
nothing out. Tactical Acumen, Fire and Fade and The Torchstar Gambit all end
with a charge lock and each needed a controller branch to apply it "if it
does"; this one has nothing to apply on confirm, so the generic
confirm_move() would do - except for the active-player hand-off above. Pinned
as an absence, since a missing lock and a forgotten one look the same.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import ai_mode, ride_the_wind, unit_choice_offer
from game.phase_window import PhaseWindow
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

OVERFLIGHT_NAME = "Overflight"
OVERFLIGHT_CP = 1

#: 'a Normal move of up to 7"'.
OVERFLIGHT_MOVE_IN = 7.0

#: Routes the Confirm button back to this controller - see the docstring.
OVERFLIGHT_MOVE_MODE = "overflight"


def eligible_unit(squad):
    """"One ASURYANI MOUNTED unit" - NOT the detachment's ASURYANI MOUNTED or
    VYPER set. The one Windrider Host Stratagem that narrows it."""
    if squad is None or not ride_the_wind.has_detachment(getattr(squad, "owner", None)):
        return False
    from game import aeldari_detachments
    from game.attached_units import unit_has_datasheet_keyword
    return (aeldari_detachments.is_asuryani_unit(squad)
            and unit_has_datasheet_keyword(squad, "MOUNTED"))


class OverflightController:
    """The kill ledger, the end-of-phase offer, and the reactive move."""

    def __init__(self, stratagem_controller, movement_controller=None,
                 turn_tracker=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: Squads that destroyed an enemy unit this phase - recorded because
        #: the fact cannot be recovered afterwards.
        self._killers_this_phase = set()
        #: The same, for the phase that just ENDED. reset_phase() rotates the
        #: live set into this one; the offer reads THIS one, because it is
        #: made after that reset. See the docstring, point 2.
        self._killers_ending_phase = set()
        #: Deaths whose attacker the sweep could not name - see point 3.
        self._owed = []
        #: The end-of-phase window this controller's own offer opens, in place
        #: of a live phase test. See game/phase_window.py.
        self._window = PhaseWindow()
        self._moving_squad = None
        self._restore_active = None
        self._stratagem = Stratagem(
            name=OVERFLIGHT_NAME, cp_cost=OVERFLIGHT_CP, effect=self._move,
        )

    def reset_phase(self):
        """ROTATES rather than clears, and closes the window.

        main.py's per-phase reset block runs BEFORE that boundary's own
        offers, so clearing here would empty exactly the ledger the offer is
        about to read. An uncredited death does not outlive its phase."""
        self._killers_ending_phase = self._killers_this_phase
        self._killers_this_phase = set()
        self._owed = []
        self._window.close()

    def notify_unit_destroyed(self, dead_squad, killer_squad):
        """Fed once per wiped-out squad from main.py's death sweep, with
        whoever was attacking at the time - this engine's only answer to "who
        killed it", as Szeras' own note records.

        A death with no named attacker is PARKED rather than dropped: that is
        the ordinary case when the last weapon group of an activation wipes a
        unit. credit_owed_kills() settles it from the post-activation hooks."""
        if dead_squad is None:
            return False
        if killer_squad is None:
            self._owed.append(dead_squad)
            return False
        if killer_squad.owner == dead_squad.owner:
            return False
        self._killers_this_phase.add(id(killer_squad))
        return True

    def credit_owed_kills(self, killer_squad):
        """Settle the parked deaths against the unit that has just finished
        its attacks - the one seam where the attacker arrives as an argument
        instead of being guessed at."""
        if killer_squad is None or not self._owed:
            return False
        owed, self._owed = self._owed, []
        credited = False
        for dead_squad in owed:
            if dead_squad.owner == killer_squad.owner:
                continue               # no credit for friendly fire
            self._killers_this_phase.add(id(killer_squad))
            credited = True
        return credited

    def destroyed_a_unit_this_phase(self, squad):
        return id(squad) in self._killers_this_phase

    def destroyed_a_unit_in_the_ending_phase(self, squad):
        """What the offer asks. The live ledger has already been rotated away
        by the time this boundary's offers run."""
        return id(squad) in self._killers_ending_phase

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None:
            return False
        # No live phase test and no owner test here: both are facts about the
        # BOUNDARY, and the boundary is what armed the window. Reading the
        # clock meant neither half of the printed WHEN could ever hold.
        if not self._window.is_open(squad.owner):
            return False
        if not eligible_unit(squad):
            return False
        if not self.destroyed_a_unit_in_the_ending_phase(squad):
            return False
        if not any(not m.is_dead() for m in (getattr(squad, "models", ()) or ())):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def offer_at_end_of_phase(self, squads, phase_before, ending_player):
        """Offered at both phase boundaries the WHEN names.

        `phase_before` and `ending_player` are main.py's, captured BEFORE
        advance_phase() - the clock and turn_owner have both already moved on
        by the time this runs. The owner rule lives HERE, where the boundary
        is known, rather than in can_use(), which is asked frames later."""
        if phase_before == PHASE_SHOOTING:
            # "End of YOUR Shooting phase".
            candidates = [s for s in squads if s.owner == ending_player]
        elif phase_before == PHASE_FIGHT:
            # "the end of THE Fight phase" - it belongs to nobody, so this
            # half has no owner check at all.
            candidates = list(squads)
        else:
            return False
        # ONE prompt listing EVERY eligible unit, each tagged with itself, so
        # the choice is made by clicking on the board - "TARGET: One ASURYANI
        # MOUNTED unit from your army" is the player's choice, and this used to
        # raise a yes/no about whichever unit sorted first. See
        # game/unit_choice_offer.py.
        #
        # The window is armed BEFORE the eligibility test, because can_use()
        # asks it: the window IS this offer's own "right moment". Closed again
        # if nothing was actually put to that player.
        for player in sorted({s.owner for s in candidates}, key=str):
            self._window.arm(player)
            eligible = [s for s in sorted(candidates, key=lambda s: s.name)
                        if s.owner == player and self.can_use(s)]
            if unit_choice_offer.offer_one_of(
                    self.decision_manager, player, eligible,
                    '%s (%d CP): which unit that destroyed an enemy unit this '
                    'phase makes a Normal move of up to %g"?'
                    % (OVERFLIGHT_NAME, OVERFLIGHT_CP, OVERFLIGHT_MOVE_IN),
                    self.use, auto_players=self.auto_players,
                    is_stratagem=True):
                return True
            self._window.close()       # nothing offered - and no AI path
        return False

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _move(self, controller, player, targets):
        squad = (targets or [None])[0]
        if squad is None or self.movement_controller is None:
            return
        # select() would refuse this unit in the opponent's turn, so the
        # reacting player holds active_player until the move is confirmed or
        # cancelled - the hand-off Path of the Outcast documents.
        if self.turn_tracker is not None:
            self._restore_active = self.turn_tracker.active_player
            self.turn_tracker.set_active(squad.owner)
        self.movement_controller.select(squad.models[0])
        if self.movement_controller.selected_squad is not squad:
            self._finish()
            return
        self.movement_controller.start_battle_focus_move(
            squad, OVERFLIGHT_MOVE_IN, move_mode=OVERFLIGHT_MOVE_MODE)
        self._moving_squad = squad
        if self.game_log is not None:
            self.game_log.add(
                '%s: %s makes a Normal move of up to %g".'
                % (OVERFLIGHT_NAME, squad.name, OVERFLIGHT_MOVE_IN))

    def confirm_move(self):
        if self.movement_controller is None or self._moving_squad is None:
            return
        self.movement_controller.confirm_move()
        if not self.movement_controller.errors:
            self._finish()

    def cancel_move(self):
        if self.movement_controller is not None:
            self.movement_controller.cancel_move()
        self._finish()

    def _finish(self):
        self._moving_squad = None
        if self.turn_tracker is not None and self._restore_active is not None:
            self.turn_tracker.set_active(self._restore_active)
        self._restore_active = None
