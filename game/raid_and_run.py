"""Corsair Skyreavers' "Raid and Run" - a datasheet ability.

RULE (printed, word for word):
  "At the end of the Fight phase, if this unit was eligible to fight this
  phase, and is not within Engagement Range of one or more enemy units, it can
  make a Normal move of up to D3+3". Otherwise, if this unit was eligible to
  fight this phase, this unit can make a Fall Back move of up to D3+3"."

ONE CONDITION, TWO MOVES - AND "OTHERWISE" IS NOT A SECOND CONDITION
---------------------------------------------------------------------
Both branches share the same gate ("was eligible to fight this phase"); what
differs is only WHICH move, and that turns purely on whether the unit is still
engaged. So the eligibility is asked once and the mode falls out of the board:

  unengaged -> a Normal move          (nothing to disengage from)
  engaged   -> a Fall Back move       (09.07's rules then apply to it)

Reading "otherwise" as its own gate would let a unit that never fought take the
Fall Back branch, which is the wider ability and the wrong direction.

"WAS ELIGIBLE TO FIGHT THIS PHASE" is a fact about a phase that has ENDED by
the time this fires, so it cannot be recomputed afterwards - the same problem
The Twin Lance's Retro-thrusters has, and it takes the same answer: sample it
while the phase is still running. FightController already keeps that ledger.

THE DISTANCE IS ROLLED, D3+3", so the move budget is not known until the die is
thrown - which is why this grants a move through MovementController's
reactive-move door (start_battle_focus_move) with an explicit distance rather
than the unit's own M characteristic.

REACTIVE MOVE MODES: "raid_and_run" MUST be registered in
MovementController.REACTIVE_MOVE_MODES. That set is what stops the AI walking
straight over a human's open move - reported twice, for Fade Back and then for
Path of the Outcast - and a new granted move that forgets to register is
exactly how it happened the second time.
"""

RAID_AND_RUN_LABEL = "Raid and Run"

#: "a move of up to D3+3 inches" - the same distance for both branches.
RAID_AND_RUN_BONUS_IN = 3

NORMAL = "normal"
FALL_BACK = "fall_back"


def applies(squad):
    return any(getattr(m.profile, "raid_and_run", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def move_kind_for(squad, all_tokens=()):
    """Which of the two branches this unit takes right now.

    Returns NORMAL when it is not within Engagement Range of any enemy, and
    FALL_BACK when it is - the printed "otherwise"."""
    from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
    mine = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other.owner == squad.owner:
            continue
        living = [m for m in other.models if not m.is_dead()]
        if any(edge_distance(a, b) <= ENGAGEMENT_RANGE_IN for a in mine for b in living):
            return FALL_BACK
    return NORMAL


class RaidAndRunController:
    """The end-of-Fight-phase offer and the granted move."""

    def __init__(self, movement_controller=None, dice_manager=None,
                 decision_manager=None, game_log=None, fight_controller=None,
                 all_tokens=None, auto_players=()):
        self.movement_controller = movement_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.fight_controller = fight_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = set(auto_players)
        #: "was eligible to fight THIS PHASE" - sampled while the phase runs,
        #: because it cannot be recomputed once the phase has ended.
        self._was_eligible = set()

    def note_eligibility(self):
        """Called each frame during the Fight phase, like Retro-thrusters'."""
        controller = self.fight_controller
        if controller is None:
            return
        for squad in list(getattr(controller, "eligible_squads", lambda: ())() or ()):
            if applies(squad):
                self._was_eligible.add(id(squad))

    def note_eligible(self, squad):
        """Direct form, for a caller that already knows - and for tests."""
        if applies(squad):
            self._was_eligible.add(id(squad))

    def was_eligible(self, squad):
        return squad is not None and id(squad) in self._was_eligible

    def can_use(self, squad):
        return (applies(squad) and self.was_eligible(squad)
                and any(not m.is_dead() for m in getattr(squad, "models", ()) or ()))

    def distance_for(self, rolled):
        return rolled + RAID_AND_RUN_BONUS_IN

    def start_move(self, squad, rolled):
        """Grants the move through the reactive-move door, with the rolled
        distance rather than the unit's M characteristic."""
        if not self.can_use(squad) or self.movement_controller is None:
            return False
        kind = move_kind_for(squad, self.all_tokens)
        distance = self.distance_for(rolled)
        self.movement_controller.select(squad.models[0])
        self.movement_controller.start_battle_focus_move(
            squad, distance, move_mode="raid_and_run")
        if self.game_log is not None:
            self.game_log.add(
                '%s: %s may make a %s move of up to %d" (D3+%d).'
                % (RAID_AND_RUN_LABEL, squad.name,
                   "Normal" if kind == NORMAL else "Fall Back",
                   distance, RAID_AND_RUN_BONUS_IN))
        return True

    def reset_phase(self):
        self._was_eligible.clear()
