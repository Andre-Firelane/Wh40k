"""Warp Spiders' Flickerjump - a datasheet ability, not a core rule, so it
lives in its own module like every other named ability in this codebase.

RULE (printed, word for word):
  "In your Movement phase, each time this unit is selected to make a Normal
  move, it can use this ability. If it does, until the end of the turn, this
  unit is not eligible to declare a charge and models in it have a Move
  characteristic of 24". Each time this unit uses this ability, at the end of
  the phase, roll one D6 for each model in this unit: for each 1, this unit
  suffers 1 mortal wound."

THREE PARTS, THREE PLACES
-------------------------
1. The Move characteristic is an OVERRIDE ("have a Move characteristic of
   24 inches"), not a bonus - so it is folded into effective_movement_in()
   alongside the Coldstar Commander's own override, and Battle Focus's Swift
   as the Wind still ADDS its 2" on top of whichever override won. Where two
   overrides could ever coexist the higher one wins; today they cannot (one is
   T'au, one is Aeldari).
2. "Not eligible to declare a charge ... until the end of the turn" is exactly
   Squad.charge_locked_until_end_of_turn, which rules 18.04/18.05 and The
   Shortened Blade already use and which main.py already clears at end of
   turn. No second flag, and no second place to forget to clear.
3. The mortal wounds are deferred to the END of the phase, not taken when the
   ability is used - so the controller keeps a queue and resolves it from
   main.py's phase change, one unit at a time (DiceManager holds a single
   pending roll).

WHY THE BUTTON HAS TO COME BEFORE THE MOVE
------------------------------------------
MovementController._begin_move() reads effective_movement_in() once, when the
move starts, to set the distance budget. So the ability is offered while the
unit is selected and has not moved yet - the same slot, and the same reason,
as the 'Ere We Go stratagem button sitting above "Move".

NOT A STRATAGEM: no CP, no once-per-phase limit across the army, and the
printed text says "each time this unit is selected to make a Normal move", so
a unit could in principle use it in more than one Movement phase - and each
use queues its own end-of-phase roll. What it cannot do is use it twice for
the same move, which is what _used_this_phase guards.
"""

# game/turn.py imports nothing, so this cannot cycle. MortalWoundAllocationSession
# is deliberately NOT imported here: game/coldstar.py reads movement_override_in()
# below, and game/squad.py imports coldstar - a module-level import of
# game/damage_resolution.py (which reaches back into game/squad.py) would close
# that loop. It is imported locally in on_dice_acknowledged() instead, which is
# off the movement hot path anyway.
from game import empyric_ambush
from game.turn import PHASE_MOVEMENT

FLICKERJUMP_MOVEMENT_IN = 24
# "for each 1" - anything else is fine for the unit, so this is compared with
# == rather than with a >= success threshold.
FLICKERJUMP_MORTAL_ON = 1


def squad_has_flickerjump(squad):
    """Rule 19.04's shape: the ability belongs to the models, so a unit only
    has it while at least one model that prints it is alive. Deliberately
    any() rather than all(): an attached CHARACTER joining a Warp Spider unit
    would not take the ability away from it."""
    models = getattr(squad, "models", None)
    if not models:
        return False
    return any(getattr(m.profile, "flickerjump", False) and not m.is_dead() for m in models)


def movement_override_in(squad):
    """The Move characteristic this ability imposes, or None if it is not
    active on this unit. Read by game/coldstar.py's effective_movement_in()."""
    if squad is not None and getattr(squad, "flickerjump_active", False):
        return FLICKERJUMP_MOVEMENT_IN
    return None


def alive_models(squad):
    return [m for m in squad.models if not m.is_dead()]


class FlickerjumpController:
    """Offer, grant, and the end-of-phase mortal wound roll.

    Human-only, like the rest of the Aeldari work: no AI path reads this. The
    ability is offered as an ActionPanel button rather than a modal break
    point because it is the owning player's own optional upgrade to their own
    move, not a reaction to the opponent."""

    def __init__(self, turn_tracker=None, movement_controller=None, dice_manager=None, game_log=None):
        self.turn_tracker = turn_tracker
        self.movement_controller = movement_controller
        self.dice_manager = dice_manager
        self.game_log = game_log
        self._used_this_phase = set()   # id(squad) - one use per Movement phase per unit
        self._pending_rolls = []        # squads whose end-of-phase D6s are still owed
        self._rolling_for = None
        self.mortal_wound_session = None

    def _log(self, message, **kwargs):
        if self.game_log is not None:
            self.game_log.add(message, **kwargs)

    @property
    def is_busy(self):
        return self._rolling_for is not None or self.mortal_wound_session is not None

    def can_use(self, squad):
        """The printed WHEN, plus the one thing the engine can check for it:
        the unit must still be able to make a Normal move, otherwise there is
        no move for the 24" to apply to."""
        if squad is None or not squad_has_flickerjump(squad):
            return False
        if getattr(squad, "flickerjump_active", False) or id(squad) in self._used_this_phase:
            return False
        if self.turn_tracker is None or self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if self.turn_tracker.turn_owner != squad.owner:
            return False
        if self.movement_controller is None:
            return False
        # "each time this unit is selected to make a Normal move" - so it has
        # to still have that move available. can_make_move() is rule 09.05's
        # own predicate, the same one the "Move" button is gated on.
        return self.movement_controller.can_make_move(squad)

    def use(self, squad):
        if not self.can_use(squad):
            return False
        squad.flickerjump_active = True
        # Lhykhis' Empyric Ambush: "while this model is leading a unit, that
        # unit is eligible to declare a charge in a turn in which it used its
        # Flickerjump ability". Expressed by NOT setting the lock rather than by
        # ignoring it later, because charge_locked_until_end_of_turn is shared
        # with 18.04/18.05, The Shortened Blade and The Torchstar Gambit - a
        # reader that ignored it would hand a charge back to a unit that
        # disembarked. See game/empyric_ambush.py.
        if not empyric_ambush.applies(squad):
            squad.charge_locked_until_end_of_turn = True
        self._used_this_phase.add(id(squad))
        self._pending_rolls.append(squad)
        self._log(
            f"{squad.name} uses Flickerjump: Move {FLICKERJUMP_MOVEMENT_IN}\" this turn, "
            f"no charge, and a D6 per model at the end of the phase."
        )
        return True

    def end_of_phase(self):
        """Called from main.py's phase change. Starts the first owed roll;
        the rest follow as each one resolves."""
        self._used_this_phase.clear()
        self._start_next_roll()

    def _start_next_roll(self):
        while self._pending_rolls:
            squad = self._pending_rolls.pop(0)
            models = alive_models(squad)
            if not models or self.dice_manager is None:
                continue
            self._rolling_for = squad
            self.dice_manager.roll(
                count=len(models), sides=6, label="Flickerjump",
                success_threshold=FLICKERJUMP_MORTAL_ON + 1, target_name=squad.name,
            )
            return

    def on_dice_acknowledged(self):
        if self.dice_manager is None:
            return
        # Rule 24.12 (Feel No Pain) rolls inside the mortal-wound session come
        # back through here too - same shape as every other mortal-wound
        # source in this codebase.
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_mortal_wounds_done()
            return
        if self._rolling_for is None:
            return
        squad = self._rolling_for
        self._rolling_for = None
        rolls = self.dice_manager.last_values
        hits = sum(1 for r in rolls if r == FLICKERJUMP_MORTAL_ON)
        self._log(f"Flickerjump roll {rolls}: {hits} mortal wound(s) to {squad.name}.")
        if hits > 0:
            from game.damage_resolution import MortalWoundAllocationSession  # local: see the import note at the top of this module

            self.mortal_wound_session = MortalWoundAllocationSession(
                squad, hits, dice_manager=self.dice_manager, log=self._log,
            )
            self._check_mortal_wounds_done()
        else:
            self._start_next_roll()

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_mortal_wounds_done()

    def _check_mortal_wounds_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._start_next_roll()

    def expire_for_turn(self, squads=()):
        """"Until the end of the turn" for the 24" half. The charge lock is
        cleared by main.py alongside the other end-of-turn flags, so it is not
        touched here."""
        for squad in squads:
            squad.flickerjump_active = False
