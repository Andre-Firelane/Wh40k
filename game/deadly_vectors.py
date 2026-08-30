"""The Death Lord's Chosen detachment rule: "Deadly Vectors".

RULE (printed, word for word):

  "In your opponent's Command phase, roll 2D6 for each Afflicted enemy unit,
  subtracting 1 from the result if that unit is Below Half-strength. If the
  result is 6 or less, that enemy unit suffers D3 mortal wounds."

FOUR THINGS IN THAT SENTENCE ARE EASY TO GET BACKWARDS, so each is stated:

  * "IN YOUR OPPONENT'S Command phase". The Death Guard player rolls during
    the OTHER player's Command phase, not their own. main.py therefore feeds
    this from the same `phase_before == PHASE_COMMAND` seam Reanimation
    Protocols uses, but with the opposite player - and the controller finds
    the Death Guard side from config rather than from the phase owner,
    because on that seam the phase owner is by definition NOT them.

  * "SUBTRACTING 1 ... if Below Half-strength" makes the roll MORE likely to
    trigger, not less: the rule fires on 6 OR LESS. A weakened unit is easier
    to finish, which is the point of the rule. Signs here are the opposite way
    round from every threshold roll in this engine.

  * "BELOW Half-strength" is the Appendix term, so it is
    squad.is_below_half_strength() (STRICTLY less than half) and expressly not
    is_at_half_strength() (at-or-below), which battle-shock and 'Ard as Nails
    use. Exactly at half is NOT below half, and that boundary is the only
    place the two definitions differ - so it is where the test measures.

  * "6 OR LESS" is an inverted threshold. DiceManager.success_threshold means
    "this value or MORE passes", so passing it here would colour the dice
    panel exactly backwards - a rolled 3 shown as a failure when it is the
    result that kills. It is therefore left unset and the number is carried in
    the roll's LABEL instead, which is also what this repo's diagnostic-logging
    rule asks for: a line that omits the contested number sends the next
    investigation back to the board.

SHAPE: A QUEUE, exactly like game/reanimation_protocols.py's controller, and
for the same reason - this fires for EVERY Afflicted enemy unit, every one of
the opponent's Command phases, so there is a list of units still owed a roll
that drains one dice acknowledgement at a time. Two visible rolls per unit that
actually triggers (the 2D6 that decides IF, then the D3 for HOW MUCH), the same
two-stage arrangement game/mortal_wound_abilities.py's Crimson Harvest uses and
for the same reason: one combined roll could not show which number did what.

NOT OPTIONAL. The printed text has no "you can", so there is no
DecisionManager prompt anywhere in here and no auto_players fork - the human
and the AI get identical treatment, and the only interaction is acknowledging
the dice. That also means this rule costs no API call by construction.
"""

from game import death_lords_chosen, nurgles_gift
from game.damage_resolution import MortalWoundAllocationSession
from game.squad import is_below_half_strength

DEADLY_VECTORS_DICE_COUNT = 2
DEADLY_VECTORS_DICE_SIDES = 6
#: "If the result is 6 or less" - an INVERTED threshold; see the module docstring.
DEADLY_VECTORS_MAX_RESULT = 6
#: "subtracting 1 from the result if that unit is Below Half-strength"
DEADLY_VECTORS_WEAKNESS_PENALTY = 1
DEADLY_VECTORS_DAMAGE_SIDES = 3  # "D3 mortal wounds"

LABEL = "Deadly Vectors"


def result_penalty(squad):
    """The modifier applied to this unit's 2D6, and why."""
    if is_below_half_strength(squad):
        return DEADLY_VECTORS_WEAKNESS_PENALTY, "Below Half-strength"
    return 0, None


def triggers(total, squad):
    """Whether a 2D6 total of `total` triggers against `squad`."""
    penalty, _ = result_penalty(squad)
    return (total - penalty) <= DEADLY_VECTORS_MAX_RESULT


def _alive(squad):
    """Liveness has to be any(not is_dead()), never `not squad.models`:
    GameState.remove_dead_models() runs once a frame, so a corpse can still be
    in squad.models when this queue is filled or drained."""
    return any(not m.is_dead() for m in getattr(squad, "models", ()) or ())


class DeadlyVectorsController:
    """Rolls the detachment rule at the start of the opponent's Command phase."""

    def __init__(self, dice_manager=None, game_log=None, game_state=None):
        self.dice_manager = dice_manager
        self.game_log = game_log
        self.game_state = game_state
        self._queue = []        # units still owed a 2D6 this Command phase
        self._current = None    # the unit whose dice are on the table
        self._stage = None      # "gate" -> the 2D6, "amount" -> the D3
        self.mortal_wound_session = None

    # ---------------------------------------------------------------- state

    @property
    def is_busy(self):
        return (self._current is not None or bool(self._queue)
                or self.mortal_wound_session is not None)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    # ----------------------------------------------------------- conditions

    def targets_for(self, squads, death_guard_player):
        """Every "Afflicted enemy unit" this player rolls against.

        "Enemy" is relative to the DEATH GUARD player, not to whoever owns the
        Command phase - with two players those coincide, but writing it this
        way is what makes a mirror match (both sides Death Lord's Chosen)
        resolve each side's rule against the other rather than against
        itself."""
        return sorted(
            (s for s in squads
             if s.owner != death_guard_player
             and nurgles_gift.is_afflicted(s)
             and _alive(s)
             and getattr(s, "embarked_in", None) is None),
            key=lambda s: s.name,
        )

    def begin_opponent_command_phase(self, squads, phase_owner):
        """`phase_owner` is whose Command phase it is. Every OTHER player with
        this detachment rolls now. Returns True if anything was queued.

        Sorted by name so a replay and a test see the same order: the units are
        independent of each other, but a non-deterministic order would make a
        failure hard to reproduce - the same reasoning
        ReanimationProtocolsController records."""
        if self.is_busy:
            return False
        queue = []
        for player in death_lords_chosen.detachment_players():
            if player == phase_owner:
                continue  # "in your OPPONENT's Command phase" - not your own
            for squad in self.targets_for(squads, player):
                queue.append((squad, player))
        self._queue = queue
        if not self._queue:
            return False
        return self._roll_next()

    # ------------------------------------------------------------ the cycle

    def _roll_next(self):
        while self._queue:
            squad, player = self._queue.pop(0)
            if not (_alive(squad) and nurgles_gift.is_afflicted(squad)):
                continue  # it died, or stopped being Afflicted, while the queue drained
            self._current = (squad, player)
            self._stage = "gate"
            penalty, reason = result_penalty(squad)
            note = f", -{penalty} ({reason})" if penalty else ""
            self.dice_manager.roll(
                DEADLY_VECTORS_DICE_COUNT, DEADLY_VECTORS_DICE_SIDES,
                # The threshold rides in the LABEL because it is INVERTED and
                # success_threshold would colour the panel backwards; see the
                # module docstring.
                label=f"{LABEL} (2D6, {DEADLY_VECTORS_MAX_RESULT} or less{note})",
                target_name=squad.name, target_squad=squad, subject_label="Afflicted",
            )
            return True
        self._current = None
        self._stage = None
        return False

    def on_dice_acknowledged(self):
        # Rule 24.12 (Feel No Pain): this acknowledgement may be the
        # allocation's own extra dice step rather than one of our two rolls.
        # Checked FIRST, exactly as game/deadly_demise.py does - the session
        # outlives the roll that created it.
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_session_done()
            return True

        if self._current is None or self.dice_manager is None:
            return False
        squad, player = self._current
        values = self.dice_manager.last_values or [1, 1]

        if self._stage == "gate":
            total = sum(values)
            penalty, reason = result_penalty(squad)
            adjusted = total - penalty
            note = f" -{penalty} ({reason})" if penalty else ""
            if adjusted > DEADLY_VECTORS_MAX_RESULT:
                self._log(f"[deadly vectors] {squad.name}: 2D6 {values} = {total}{note} "
                          f"-> {adjusted}, needed {DEADLY_VECTORS_MAX_RESULT} or less "
                          f"- no effect.", file_only=True)
                self._roll_next()
                return True
            self._log(f"{LABEL}: {squad.name} rolled {total}{note} -> {adjusted} "
                      f"({DEADLY_VECTORS_MAX_RESULT} or less) - it suffers D3 mortal wounds.")
            self._stage = "amount"
            self.dice_manager.roll(
                1, DEADLY_VECTORS_DAMAGE_SIDES, label=f"{LABEL} - mortal wounds (D3)",
                target_name=squad.name, target_squad=squad, subject_label="Afflicted",
            )
            return True

        # stage == "amount"
        wounds = values[0]
        self._current = None
        self._stage = None
        self._log(f"{LABEL}: {squad.name} suffers {wounds} mortal wound(s).")
        self.mortal_wound_session = MortalWoundAllocationSession(
            squad, wounds, dice_manager=self.dice_manager, log=self._log,
        )
        self._check_session_done()
        return True

    def _check_session_done(self):
        """The allocation can pause on a defender's model choice or on a Feel
        No Pain roll, so the queue may only advance once it has really
        finished - the same gate every other mortal-wound consumer applies."""
        session = self.mortal_wound_session
        if session is None:
            return
        if not session.done:
            return
        self.mortal_wound_session = None
        self._roll_next()

    @property
    def pending_damage_choice(self):
        """The defender's allocation choice, if the session is waiting on one.

        THE NAME IS LOAD-BEARING, not a style choice: main.py's event chain
        and ai/agent_driver.py's _any_pending_damage_choice() both key on
        exactly `pending_damage_choice` / `choose_damage_model`. A controller
        that spelled them differently would create a session nothing on earth
        could answer, and the queue would stall on a multi-model target -
        which is the common case here, since Deadly Vectors rolls against
        whole enemy units."""
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_session_done()
