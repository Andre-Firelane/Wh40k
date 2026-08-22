"""T'au Empire detachment stratagem: Retaliation Cadre's The Torchstar Gambit,
as supplied by the user (not a rule from the generic 40k core rulebook, so it
lives in its own module - same reasoning as game/retaliation_cadre.py for that
detachment's Bonded Heroes rule, and its three sibling stratagems in
game/stim_injectors.py, game/arrokon_protocol.py and game/shortened_blade.py).

RULE (The Torchstar Gambit, 1CP, Retaliation Cadre Strategic Ploy Stratagem):
  WHEN:   Your Shooting phase.
  TARGET: One T'AU EMPIRE BATTLESUIT unit from your army that can FLY whose
          attacks have been resolved this phase.
  EFFECT: If your unit is not within Engagement Range of one or more enemy
          units, it can make a Normal move. If it does, your unit cannot
          declare a charge this turn.

WHERE THE WORK IS

Not in the move itself - MovementController already has every piece of a
Normal move. The two things that needed saying are WHEN it may happen and
what "if it does" attaches to:

  * A Normal move outside the Movement phase. can_move()/can_make_move() ask
    "is this the unit's Movement-phase move?" (right phase, not selected to
    move yet), which is the wrong question here: this unit has normally
    already made that move, then shot. start_post_shooting_move() therefore
    skips those gates - exactly as start_scout_move() does, and for the same
    stated reason - and this controller's can_use() carries the stratagem's
    own conditions instead. The move's DISTANCE and END CONDITION are
    unchanged from a Normal move, which is what "can make a Normal move"
    actually promises.

  * "If it DOES" - the no-charge restriction is conditional on the move
    happening, not on the stratagem being used. So it is applied at confirm
    time, not at use time, which is why this controller owns confirm/cancel
    rather than letting the panel call MovementController directly. Same
    shape as IngressController.confirm_ingress(): call through, then read
    whether it actually took. (Its sibling The Shortened Blade sets its own
    charge lock at USE time, because its RESTRICTIONS clause is unconditional
    - the difference is in the two rules' wording, not an inconsistency.)

"Whose attacks have been resolved this phase" is ShootingController.
shot_squad_ids, which is populated in _actually_finish_squad() - i.e. it
means exactly "resolved", not "started", so a unit mid-activation is
correctly refused.

SIMPLIFICATION (documented, matching game/retaliation_cadre.py's own note):
this engine has no army-building/detachment-selection flow yet, and
Retaliation Cadre is currently the only detachment that exists - the T'AU
EMPIRE half of the TARGET clause is therefore not checked, exactly as Bonded
Heroes applies unconditionally to any BATTLESUIT model. The BATTLESUIT and
FLY halves ARE checked, both through rule 19.03's keyword pooling.

DELIBERATE OMISSION: rule 21.03's "Take to the Skies" is not offered during
this move. can_take_to_the_skies() already restricts itself to move_mode in
(None, "charge"), so "torchstar" is excluded without a new check. Arguable
either way - 21.03 applies to "a Normal move", which this is - but it is a
Movement-phase declaration everywhere else in this engine, its 2" penalty and
HOVER interaction are untested outside that, and the stratagem's own text does
not mention it. Left out rather than silently included; trivially reversible
by adding "torchstar" to that tuple.
"""

from game.attached_units import unit_has_keyword
from game.retaliation_cadre import is_battlesuit_unit
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

TORCHSTAR_CP_COST = 1


def can_fly(squad):
    """Rule 19.03: keywords pool across an attached unit, so a unit counts as
    able to FLY if any of its models does."""
    return unit_has_keyword(squad, lambda model: model.profile.fly)


class TorchstarGambitController:
    """WHEN/TARGET bookkeeping, plus ownership of the move's confirm/cancel so
    the conditional RESTRICTIONS clause can be applied at the right moment.

    Proactive and human-driven like its two siblings - the active player picks
    the moment, so there is nothing to interrupt and no relevance gate to
    build. can_use() is the printed clauses and nothing else."""

    def __init__(self, stratagem_controller, movement_controller=None, shooting_controller=None,
                 all_tokens=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.shooting_controller = shooting_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name="The Torchstar Gambit", cp_cost=TORCHSTAR_CP_COST, effect=self._begin_move,
        )

    def is_moving(self, squad=None):
        """Whether a Torchstar move is open right now (optionally: for this
        squad). What the panel routes Confirm/Cancel on."""
        if self.movement_controller is None or self.movement_controller.move_mode != "torchstar":
            return False
        return squad is None or self.movement_controller.selected_squad is squad

    def can_use(self, squad):
        if squad is None or self.movement_controller is None or self.shooting_controller is None:
            return False
        if self.turn_tracker is not None:
            # WHEN: "Your Shooting phase" - the user's own, not the opponent's.
            # This also excludes a reactive Snap Shot (Fire Overwatch,
            # 15.08/15.09), which resolves in the opponent's Movement phase.
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        # TARGET: "whose attacks have been resolved this phase". shot_squad_ids
        # is filled in _actually_finish_squad(), so it means resolved, not
        # started - a unit still mid-activation is correctly refused, and so is
        # one that never shot.
        if squad not in self.shooting_controller.shot_squad_ids:
            return False
        if not is_battlesuit_unit(squad) or not can_fly(squad):
            return False
        # EFFECT is conditional on this, so it is part of "can this do
        # anything at all" rather than something to discover after paying.
        if squad.is_engaged(self.all_tokens):
            return False
        if self.movement_controller.state == "moving":
            return False  # some move is already open - including this one
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        # The panel draws this button for the selected squad, and
        # start_post_shooting_move() requires that identity - make it explicit
        # rather than depending on the caller having done it.
        self.movement_controller.selected_squad = squad
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _begin_move(self, controller, player, targets):
        squad = targets[0]
        self.movement_controller.start_post_shooting_move(squad)
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: The Torchstar Gambit - {squad.name} makes a Normal move after shooting."
            )

    def confirm_move(self):
        """Confirm the Normal move, then apply "if it does" - the no-charge
        restriction lands only when the move actually took.

        Success is read the same way IngressController.confirm_ingress() reads
        its own: confirm_move() clears move_mode only when it succeeds, and
        leaves the placement open (state MOVING, errors set) when it does
        not."""
        if self.movement_controller is None or not self.is_moving():
            return False
        squad = self.movement_controller.selected_squad
        self.movement_controller.confirm_move()
        if self.movement_controller.move_mode == "torchstar":
            return False  # rejected - still open for the player to fix
        # RESTRICTIONS: "If it does, your unit cannot declare a charge this
        # turn." The same field rules 18.04/18.05 already use for their own
        # no-charge lock, so ChargeController needs no new case and main.py's
        # end-of-turn cleanup already clears it.
        squad.charge_locked_until_end_of_turn = True
        if self.game_log is not None:
            self.game_log.add(
                f"{squad.owner}: {squad.name} moved with The Torchstar Gambit and "
                "cannot declare a charge this turn."
            )
        return True

    def cancel_move(self):
        """Backing out leaves no charge lock - the RESTRICTIONS clause is
        conditional on the move being made ("if it does"). The CP is gone
        either way: rule 15.01 spends it when the stratagem is used, and
        nothing in this rule refunds it."""
        if self.movement_controller is None or not self.is_moving():
            return False
        self.movement_controller.cancel_move()
        return True
