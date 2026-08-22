from game.damage_resolution import MortalWoundAllocationSession
from game.dice import DAMAGE_ROLL
from game.dice_notation import DiceNotationRoll, describe
from game.squad import edge_distance

DEADLY_DEMISE_RANGE_IN = 6.0
DEADLY_DEMISE_SUCCESS_ROLL = 6


class DeadlyDemiseController:
    """Rule 24.08 (Deadly Demise X): each time a model with this ability is
    destroyed - after the (not yet implemented, rule 18.04) emergency
    disembark move of any units embarked within it, so currently a no-op -
    roll 1D6; on a 6, every unit (friend or foe) within 6" of where it died
    suffers X mortal wounds, the defending player choosing which model takes
    each one (same principle as any other mortal wound, see
    MortalWoundAllocationSession). When X is itself dice-notation (a printed
    "Deadly Demise D3", e.g. UnitProfile.deadly_demise_notation on both T'au
    vehicles - found via a user report that this was silently always
    resolving to the die's max value with no roll shown), an extra real,
    visible roll (game/dice_notation.py's DiceNotationRoll) determines X.

    There is exactly ONE detonation D6, and then one X roll PER CAUGHT UNIT -
    user-supplied ruling, "einmal wuerfeln, ob er explodiert. wenn ja, fuer
    JEDE einheit den schaden auswuerfeln". The X roll therefore lives in
    _begin_next_squad(), next to the unit it is for, not next to the
    detonation. See _start_detonation() for the reported case that a single
    shared X roll produced. Multiple models can die in the same frame (e.g. one weapon
    killing several squad members at once), and one detonation can owe
    mortal wounds to several different units - both queue up and resolve
    one at a time so nothing steps on another pending dice roll or
    allocation choice."""

    def __init__(self, dice_manager, all_tokens, turn_tracker=None, game_log=None):
        self.dice_manager = dice_manager
        self.all_tokens = all_tokens
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self._death_queue = []      # dead Tokens still awaiting their D6 roll
        self._rolling_for = None    # the dead Token whose D6 roll is currently pending
        self._pending_x_roll = None  # DiceNotationRoll while rolling THIS unit's dice-notation X value (e.g. "D3")
        self._x_roll_squad = None   # the squad that pending X roll is being made FOR (one roll per unit, see class docstring)
        self._detonating_model = None  # the dead Token whose detonation is currently working through _squad_queue
        self._squad_queue = []      # squads still owed mortal wounds from the current detonation
        self._active_before = None  # turn_tracker.active_player to restore once all squads are resolved
        self.mortal_wound_session = None
        # Retaliation Cadre's Fail-Safe Detonator (2CP, game/fail_safe_detonator.py):
        # "do not roll for that ability; instead, you can choose whether the
        # result of that roll is a 1 or a 6". id(model) -> the chosen value, so
        # maybe_start_next() skips the D6 entirely for that one death.
        self._forced_rolls = {}

    def queue_death(self, dead_model):
        if dead_model.profile.deadly_demise is not None:
            self._death_queue.append(dead_model)

    def has_queued_death(self, dead_model):
        """Whether this model's Deadly Demise is still waiting to resolve -
        what a rule that REPLACES that roll has to know before it offers to."""
        return dead_model in self._death_queue

    def force_roll(self, dead_model, value):
        """Rule (Fail-Safe Detonator, user-supplied): "do not roll for that
        ability; instead, you can choose whether the result of that roll is a
        1 or a 6."

        Stored rather than resolved on the spot so the detonation still goes
        through this controller's own queue - it is what serialises several
        deaths in one frame, and what waits for a destroyed TRANSPORT's
        passengers to disembark first (24.08's own ordering clause)."""
        self._forced_rolls[id(dead_model)] = value

    @property
    def is_busy(self):
        return (
            self._rolling_for is not None or self._pending_x_roll is not None
            or self.mortal_wound_session is not None
        )

    def maybe_start_next(self):
        """Call once per frame, only when nothing else is waiting on player
        input (another pending dice roll or damage/mortal-wound choice) -
        pops and rolls for the next queued death, if any."""
        if self.is_busy or not self._death_queue or self.dice_manager is None or self.dice_manager.is_pending:
            return
        dead_model = self._death_queue.pop(0)
        forced = self._forced_rolls.pop(id(dead_model), None)
        if forced is not None:
            # No dice: the result was chosen, not rolled. Resolved through the
            # exact same tail a real roll takes, so the outcome, the logging
            # and the dice-notation X step cannot diverge between the two.
            self._log(
                f"Deadly Demise ({dead_model.profile.name}): result chosen, not rolled "
                f"(Fail-Safe Detonator) - counts as a {forced}."
            )
            self._resolve_roll(dead_model, forced)
            return
        self._rolling_for = dead_model
        self.dice_manager.roll(
            count=1, sides=6,
            label=f"Deadly Demise: {dead_model.profile.name}",
            success_threshold=DEADLY_DEMISE_SUCCESS_ROLL,
        )

    def on_dice_acknowledged(self):
        # Rule 24.12 (Feel No Pain): this acknowledgement might be that
        # ability's extra dice step, not the D6 detonation roll itself.
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_session_done()
            return

        if self._pending_x_roll is not None:
            # Rule: a dice-notation X (e.g. a printed "Deadly Demise D3")
            # gets its own real, visible roll (game/dice_notation.py's
            # DiceNotationRoll) once the D6 detonation itself has already
            # succeeded - found missing via a user report: this used to
            # just apply the die's max value as a silent, fixed placeholder,
            # with no roll shown for how many mortal wounds it actually is.
            # There is one such roll per affected UNIT, not one per
            # detonation - see _begin_next_squad().
            self._pending_x_roll.on_dice_acknowledged()
            squad = self._x_roll_squad
            x = self._pending_x_roll.total
            self._pending_x_roll = None
            self._x_roll_squad = None
            self._log(
                f"Deadly Demise ({self._detonating_model.profile.name}): "
                f"{squad.name} suffers {x} mortal wound(s)."
            )
            self._begin_squad_wounds(squad, x)
            return

        if self._rolling_for is None or self.dice_manager is None:
            return
        dead_model = self._rolling_for
        self._rolling_for = None
        self._resolve_roll(dead_model, self.dice_manager.last_values[0])

    def _resolve_roll(self, dead_model, roll):
        """What a Deadly Demise result of `roll` means - shared by the real
        D6 and by a result that some rule chose instead of rolling (see
        force_roll())."""
        if roll < DEADLY_DEMISE_SUCCESS_ROLL:
            self._log(f"Deadly Demise ({dead_model.profile.name}): rolled {roll}, no detonation.")
            return

        self._start_detonation(dead_model, roll)

    def _start_detonation(self, dead_model, roll):
        """The detonation succeeded: work out which units are caught in it,
        then start paying them their mortal wounds one unit at a time.

        X is deliberately NOT decided here. When it is dice-notation, every
        caught unit rolls for its own (see _begin_next_squad()) - user-supplied
        ruling: "es muss fuer JEDE einheit in reichtweite separat gewuerfelt
        werden ... also einmal wuerfeln, ob er explodiert. wenn ja, fuer JEDE
        einheit den schaden auswuerfeln". This used to roll X once and hand the
        same number to every unit, which is where a real reported case got its
        size from: a Battlewagon (Deadly Demise D6) rolled a 6 for X and dealt
        6 mortal wounds to each of four units at once - 24 in one go, against
        the ~14 that four separate D6 rolls average to."""
        squads = {t.squad for t in self.all_tokens if t.squad is not None}
        self._squad_queue = [
            squad for squad in squads
            if any(edge_distance(dead_model, m) <= DEADLY_DEMISE_RANGE_IN for m in squad.models)
        ]
        self._detonating_model = dead_model
        self._active_before = self.turn_tracker.active_player if self.turn_tracker is not None else None

        notation = dead_model.profile.deadly_demise_notation
        caught = len(self._squad_queue)
        if notation is not None:
            self._log(
                f"Deadly Demise ({dead_model.profile.name}): rolled {roll} - detonates, rolling "
                f"{describe(notation)} mortal wounds separately for each of the {caught} unit(s) "
                f'within {DEADLY_DEMISE_RANGE_IN:.0f}".'
            )
        else:
            self._log(
                f"Deadly Demise ({dead_model.profile.name}): rolled {roll} - every unit within "
                f'{DEADLY_DEMISE_RANGE_IN:.0f}" suffers {dead_model.profile.deadly_demise} '
                f"mortal wound(s) ({caught} in range)."
            )
        self._begin_next_squad()

    def _begin_next_squad(self):
        """Take the next unit caught in the current detonation. A dice-notation
        X gets its own real, visible roll HERE, once per unit; a fixed X needs
        no roll at all and is used exactly as printed."""
        if not self._squad_queue:
            if self.turn_tracker is not None and self._active_before is not None:
                self.turn_tracker.set_active(self._active_before)
            self._active_before = None
            self._detonating_model = None
            return
        squad = self._squad_queue.pop(0)
        if self.turn_tracker is not None:
            # Rule 06.02: these mortal wounds land on THIS unit, so its own
            # controller picks which models take them - set before the roll, so
            # the whole per-unit step belongs to that player.
            self.turn_tracker.set_active(squad.owner)
        dead_model = self._detonating_model
        notation = dead_model.profile.deadly_demise_notation
        if notation is not None:
            self._x_roll_squad = squad
            self._pending_x_roll = DiceNotationRoll(
                notation, count=1, dice_manager=self.dice_manager,
                label=f"Deadly Demise: {dead_model.profile.name} vs {squad.name}",
                roll_kind=DAMAGE_ROLL, log=self._log,
            )
            return
        self._begin_squad_wounds(squad, dead_model.profile.deadly_demise)

    def _begin_squad_wounds(self, squad, x):
        self.mortal_wound_session = MortalWoundAllocationSession(
            squad, x, dice_manager=self.dice_manager, log=self._log,
        )
        self._check_session_done()

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_session_done()

    def _check_session_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._begin_next_squad()

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
