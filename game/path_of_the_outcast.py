"""Rangers' "Path of the Outcast".

RULE (printed, word for word, as supplied by the user):
  "Path of the Outcast: Once per turn, when an enemy unit ends a Normal,
   Advance or Fall Back move within 9" of this unit, it can make a Normal move
   of up to D6"."

That wording replaced an earlier transcription which said 8" and had no
once-per-turn limit; both are corrected here, since a user-supplied rule text
is this project's source of truth (see CLAUDE.md).

ONE CLAUSE IS KEPT THAT THE SUPPLIED TEXT DOES NOT MENTION: "if this unit is
not within Engagement Range of one or more enemy units". Kept deliberately
rather than dropped along with the rest of the old transcription - without it
this ability would let a unit locked in combat make a NORMAL move away, which
core rule 09.02 allows no unit to do (that is what Fall Back, 09.07, is for),
and nothing else on this path re-checks it. It is flagged here, not buried: if
the supplied text really is complete, deleting reacting_squads()'s
is_engaged() branch is the whole change.

EVERY PIECE OF THIS ALREADY HAD A HOME, which is why it is small:

  * the TRIGGER is MovementController.on_move_finished - the hook Seer
    Council's Isha's Fury introduced for "directly after an enemy unit ends a
    Normal, Advance or Fall Back move". Second consumer, so main.py's single
    assignment became a list.
  * the D6 is a DiceNotationRoll, the same visible, re-rollable step every
    other dice-notation value in this engine gets rather than a silent
    random.randint().
  * the MOVE is MovementController.start_battle_focus_move(), built for Battle
    Focus' own reactive "Normal move of up to D6+1"" - identical in every way
    that matters (a Normal move in the OPPONENT's turn, of an already-rolled
    distance, ending unengaged). It takes its move_mode as an argument now, so
    each ability's Confirm button routes back to the controller that owns the
    consequence.

TURN OWNERSHIP IS THE TRAP, and it is the one Battle Focus already documented:
MovementController.select() refuses a unit whose owner is not
turn_tracker.active_player outside the Fight phase, and this move happens in
the OPPONENT's turn. So active_player is flipped to the reacting player for the
duration and handed back on confirm/cancel - the same flight game/explosives.py
makes for rule 06.02.

"WITHIN 9 INCHES" is measured edge to edge
(Squad.min_distance_to), like every other distance in this engine, and the
enemy unit that just moved is the only candidate - the hook says which one.

WHICH KIND OF MOVE is not tested here, and does not need to be: the supplied
text names exactly Normal, Advance and Fall Back, and those are exactly the
three MovementController.on_move_finished fires for (see its
_move_finished_pending, set only for move_mode None or "fall_back"). The hook
reports the kind anyway and this ability ignores it - noted because the sister
consumer (Isha's Fury) does read it.

"ONCE PER TURN" is tracked per SQUAD, not per controller: two Ranger units each
get their own use. Reset from main.py's end-of-turn sweep, alongside every other
"until the end of the turn" marker, rather than by this controller guessing when
a turn changed.
"""

from game.dice_notation import D6, DiceNotationRoll
from game.turn import PHASE_MOVEMENT

PATH_OF_THE_OUTCAST_RANGE_IN = 9.0
PATH_OF_THE_OUTCAST_LABEL = "Path of the Outcast"
PATH_OF_THE_OUTCAST_MOVE_MODE = "path_of_the_outcast"


def applies(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "path_of_the_outcast", False)
               for m in squad.models if not m.is_dead())


class PathOfTheOutcastController:
    """Wired to MovementController.on_move_finished in main.py."""

    def __init__(self, movement_controller=None, decision_manager=None,
                 dice_manager=None, turn_tracker=None, game_log=None, all_squads=None):
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        # A callable returning every squad on the battlefield - the reacting
        # units are found through it rather than held, so a destroyed unit
        # cannot linger.
        self.all_squads = all_squads or (lambda: [])
        self._roll = None
        self._moving_squad = None
        self._restore_active = None
        # "Once per turn", per SQUAD. Squads, not ids: the same objects the
        # rest of this module already holds, and cleared wholesale each turn.
        self._used_this_turn = set()

    # -- the trigger ------------------------------------------------------
    def offer_after_move(self, mover, kind=None):
        """`kind` is reported by the hook and deliberately ignored: the hook
        already fires for exactly the three kinds the rule names (Normal,
        Advance, Fall Back) - see the module docstring."""
        if mover is None or self.turn_tracker is None:
            return
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return
        for squad in self.reacting_squads(mover):
            self._offer(squad, mover)
            return   # one unit at a time; the next move offers again

    def reacting_squads(self, mover):
        """Every unit of the OTHER player that may react to `mover`."""
        out = []
        for squad in self.all_squads():
            if squad is None or squad is mover or squad.owner == mover.owner:
                continue
            if not applies(squad) or not squad.models:
                continue
            # "if this unit is not within Engagement Range of one or more
            # enemy units" - the ability's own condition, and the reason a
            # unit that has just been charged cannot slip away with it.
            if squad.is_engaged(self._enemy_models(squad)):
                continue
            if squad.min_distance_to(mover) > PATH_OF_THE_OUTCAST_RANGE_IN:
                continue
            # "Once per turn" - and counted from the moment the unit ACCEPTS
            # (see _begin), not from the offer, so declining does not burn it.
            if squad in self._used_this_turn:
                continue
            out.append(squad)
        return out

    def reset_for_new_turn(self):
        """Called from main.py's end-of-turn sweep, where every other "until
        the end of the turn" marker is cleared."""
        self._used_this_turn = set()

    def _enemy_models(self, squad):
        return [m for other in self.all_squads() if other.owner != squad.owner
                for m in other.models if not m.is_dead()]

    def _offer(self, squad, mover):
        if self.decision_manager is None:
            return
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: {PATH_OF_THE_OUTCAST_LABEL} - {mover.name} ended a move within "
            f'{PATH_OF_THE_OUTCAST_RANGE_IN:g}". Make a D6" Normal move?',
            [("Move D6\"", lambda: self._begin(squad)), ("Stay put", lambda: None)],
        )

    # -- the D6, then the move --------------------------------------------
    def _begin(self, squad):
        # Spent here rather than in _offer(): "Stay put" is an answer, not a
        # use, and a unit that declines must still be able to react to the
        # next enemy that ends a move nearby this turn.
        self._used_this_turn.add(squad)
        self._moving_squad = squad
        self._roll = DiceNotationRoll(
            D6(), count=1, dice_manager=self.dice_manager,
            label=f"{PATH_OF_THE_OUTCAST_LABEL}: {squad.name} Normal move distance",
            log=(self.game_log.add if self.game_log is not None else None),
        )
        if self._roll.done:                     # no dice_manager (tests)
            self._start_move(self._roll.total)

    @property
    def is_busy(self):
        return self._roll is not None or self._moving_squad is not None

    def on_dice_acknowledged(self):
        if self._roll is None or self._roll.is_pending is False and self._roll.total is None:
            return
        self._roll.on_dice_acknowledged()
        if self._roll.done:
            total = self._roll.total
            self._roll = None
            self._start_move(total)

    def _start_move(self, distance):
        squad = self._moving_squad
        if squad is None or self.movement_controller is None:
            self._moving_squad = None
            return
        # See the module docstring: select() would refuse this unit in the
        # opponent's turn, so the reacting player holds active_player until the
        # move is confirmed or cancelled.
        if self.turn_tracker is not None:
            self._restore_active = self.turn_tracker.active_player
            self.turn_tracker.set_active(squad.owner)
        self.movement_controller.select(squad.models[0])
        self.movement_controller.start_battle_focus_move(
            squad, distance, move_mode=PATH_OF_THE_OUTCAST_MOVE_MODE)
        if self.game_log is not None:
            self.game_log.add(
                f'{squad.owner}: {squad.name} makes a {distance:g}" '
                f"{PATH_OF_THE_OUTCAST_LABEL} move.")

    # -- confirm / cancel -------------------------------------------------
    def confirm_move(self):
        if self.movement_controller is None:
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
