"""One D6 per enemy unit in a set - each unit that passes suffers mortal wounds.

RULES (printed, word for word). Three carriers, measured across the last three
stages of the Necron backfill before the first line of this module was written:

  DRAIN LIFE - C'tan Shard of the Nightbringer:
    "At the end of the Fight phase, roll one D6 for each enemy unit within 6"
     of this model: on a 4+, that enemy unit suffers D3 mortal wounds."

  LORD OF THE STORM - Imotekh the Stormlord (stage 7):
    "Once per battle, at the end of your Command phase, this model can use
     this ability. If it does, roll one D6 for each enemy unit within 12" of
     this model: on a 2-5, that enemy unit suffers D3 mortal wounds; on a 6,
     that enemy unit suffers D3+3 mortal wounds."

  MALEVOLENT ARCING - Annihilation Barge (stage 8):
    "In your Shooting phase, each time you select a target for this model's
     twin tesla destructor, roll one D6 for the target unit and one D6 for
     every other enemy unit within 3" of the target unit. On a 5+, the unit
     being rolled for is struck by arcing energies; after resolving all of
     this model's attacks against the target unit, each unit struck by arcing
     energies suffers D3 mortal wounds."

WHY THIS SUBCLASSES MortalWoundOfferController RATHER THAN COPYING IT
---------------------------------------------------------------------
That base (game/mortal_wound_abilities.py) is a ONE-TARGET machine: all six of
its carriers print "select one enemy unit", so it picks a target, rolls, and
allocates. These three print "for EACH enemy unit" - there is no selection at
all, and the number of allocations is the number of units in range.

So only the target-selection half is replaced. The 06.02 plumbing -
pending_damage_choice, choose_damage_model, the Feel No Pain leg, the session
slot - stays written ONCE, for what are now nine carriers. That plumbing is
also the half this engine has already shipped broken twice (see the base's own
"IT USED TO BE WRITTEN ZERO TIMES" note, and game/mortal_wound_sessions.py's),
which is the strongest argument there is against a fourth hand-rolled copy.

WHY A QUEUE AND NOT A LIST OF PARALLEL SESSIONS
------------------------------------------------
game/mortal_wound_sessions.py exists for abilities that open SEVERAL sessions
at once. This is deliberately the other shape - game/deadly_demise.py's - and
for the reason that module gives: DiceManager holds ONE roll at a time, and
every unit here needs its own wound roll BETWEEN its gate die and its
allocation. Parallel sessions would have to interleave rolls that cannot
coexist.

THE GATE IS ONE HANDFUL; THE WOUNDS ARE ONE ROLL PER UNIT
----------------------------------------------------------
"Roll one D6 for each enemy unit" is a handful and is rolled as one - Kroot
Linebreakers' shape, and one acknowledgement instead of N.

Die i belongs to candidate i, so THE CANDIDATE ORDER IS FROZEN when the handful
is rolled and the log prints the pairing. Re-deriving the list when the dice
come back would let the two ends disagree about whose die was whose: models die
and move between the two moments, and _candidates() reads live positions.

The wound amounts cannot be one handful in return. They go to DIFFERENT units,
each owes its own 06.02 allocation, and Lord of the Storm's amount depends on
the band its own gate die landed in - a combined roll could not show which
number belonged to which unit, the same objection Crimson Harvest records for
its two rolls.

ACTIVE PLAYER IS NOT FLIPPED, and that is measured rather than overlooked.
game/deadly_demise.py flips turn_tracker.set_active(squad.owner) per unit
because its blast catches FRIEND AND FOE, so consecutive units can belong to
different players. Every candidate here is by definition an enemy of the
bearer, so in a two-player game they share one owner and there is nothing to
alternate between - which is also why none of the base's six carriers flips.
"""

from game.dice import DAMAGE_ROLL
from game.dice_notation import D3, DiceNotationRoll, describe
from game.mortal_wound_abilities import (
    MortalWoundOfferController, bearers, enemy_squads, gap_to,
)


class MortalWoundSweepController(MortalWoundOfferController):
    """The machine. A subclass supplies five things and nothing else:

      flag        the UnitProfile attribute that marks a bearer model
      label       what the dice panel and the log call it
      range_in    the printed radius, measured from the BEARER
      threshold   the lowest die that does anything at all
      wounds_for  a gate die -> dice notation (or None for "nothing")

    Everything below the eligibility line is the same for all three.
    """

    label = "Mortal Wound Sweep"
    flag = None
    range_in = 6.0
    threshold = 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stage = None
        self._queue = []          # [(squad, notation)] still owed a wound roll
        self._wound_roll = None   # DiceNotationRoll for the unit at the head
        self._wound_squad = None
        self._bearer_queue = []   # bearer squads still owed a whole sweep

    # ------------------------------------------------------------ the knobs
    def wounds_for(self, roll):
        """The mortal wounds a gate die of `roll` inflicts, as dice notation,
        or None for "this die does nothing".

        Called ONLY for dice that already met `threshold`, so a subclass with
        one band needs no comparison at all."""
        return D3()

    # ------------------------------------------------------- who and against
    def bearer_models(self, squad):
        return bearers(squad, self.flag) if self.flag else []

    def candidates(self, squad):
        """Every enemy unit within `range_in` of ANY bearer model.

        Measured bearer-to-unit (gap_to), not unit-to-unit: all three printed
        texts say "within N" of this MODEL", and for a merged 19.01 unit those
        are different numbers."""
        out = []
        for bearer in self.bearer_models(squad):
            for enemy in enemy_squads(squad, self._tokens()):
                if enemy not in out and gap_to(bearer, enemy) <= self.range_in:
                    out.append(enemy)
        return out

    def can_use(self, squad):
        return (not self._sweep_running
                and bool(self.bearer_models(squad))
                and bool(self.candidates(squad)))

    # ------------------------------------------------------------- the sweep
    def start(self, squad, candidates=None):
        """Roll the gate handful. `candidates` lets a carrier whose set was
        decided at another moment hand it in - Malevolent Arcing picks its
        units when the target is SELECTED and pays them after the attacks are
        resolved, so re-deriving them here would measure the wrong board."""
        if self._sweep_running or self.dice_manager is None:
            return False
        targets = list(candidates) if candidates is not None else self.candidates(squad)
        targets = [t for t in targets if any(not m.is_dead() for m in t.models)]
        if not targets:
            return False
        # FROZEN here on purpose - see the module docstring. Die i is targets[i].
        self._pending = {"squad": squad, "targets": targets}
        self._stage = "gate"
        self.dice_manager.roll(
            len(targets), 6, label=self.label,
            success_threshold=self.threshold, attacker_squad=squad)
        return True

    def start_many(self, squads):
        """Sweep for EVERY eligible bearer, one whole sweep after another.

        The end-of-Fight-phase window belongs to no player, so both sides can
        owe a sweep in the same instant - and DiceManager holds ONE roll at a
        time, so they cannot simply both start. Queued rather than dropped: a
        rule that silently skips its second carrier is the quiet kind of wrong
        this repo keeps finding years later."""
        eligible = [s for s in sorted(squads, key=lambda s: s.name) if self.can_use(s)]
        if not eligible:
            return False
        self._bearer_queue = eligible[1:]
        return self.start(eligible[0])

    def on_dice_acknowledged(self):
        if self._stage == "gate":
            return self._resolve_gate()
        if self._stage == "wounds":
            return self._resolve_wounds()
        # No roll of our own outstanding - but an open allocation may still owe
        # a Feel No Pain acknowledgement. Same guard every sibling opens with.
        return self._ack_session()

    def _resolve_gate(self):
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or []
        ctx = self._pending
        targets = ctx["targets"]
        self._stage = None
        # THE SLOT IS RELEASED HERE, not when the whole sweep ends. It holds the
        # gate roll's context and nothing else, and the gate is now resolved -
        # leaving it set would make `_pending is not None` a second, quieter
        # answer to "is this sweep running", and every other term of
        # _sweep_running below would be dead weight that only LOOKS defensive.
        # An A/B probe that reduced is_busy to this one field went green,
        # which is how that was measured rather than argued.
        self._pending = None
        struck = []
        for i, target in enumerate(targets):
            roll = values[i] if i < len(values) else 1
            notation = self.wounds_for(roll) if roll >= self.threshold else None
            if notation is None:
                self._log("%s (%s): rolled %d for %s - no effect."
                          % (self.label, ctx["squad"].name, roll, target.name))
                continue
            self._log("%s (%s): rolled %d for %s - %s mortal wound(s) to come."
                      % (self.label, ctx["squad"].name, roll, target.name,
                         describe(notation)))
            struck.append((target, notation))
        self._queue = struck
        if not struck:
            return self._start_next_bearer() or True
        self._begin_next()
        return True

    def _begin_next(self):
        """Take the next struck unit and roll ITS wound amount. Empty queue
        ends the sweep - and only then is the pending slot released, so the
        phase gate waits for the whole thing."""
        while self._queue:
            target, notation = self._queue.pop(0)
            if not any(not m.is_dead() for m in target.models):
                # Wiped out by an earlier unit's allocation in this same sweep
                # - rule 12 of this repo's error classes: remove_dead_models()
                # runs once a frame, so `models` still holds the corpses.
                self._log("%s: %s is already destroyed - its mortal wounds are lost."
                          % (self.label, target.name))
                continue
            self._wound_squad = target
            self._stage = "wounds"
            self._wound_roll = DiceNotationRoll(
                notation, count=1, dice_manager=self.dice_manager,
                label="%s - mortal wounds (%s)" % (self.label, target.name),
                roll_kind=DAMAGE_ROLL, log=self._log,
            )
            return
        self._stage = None
        self._start_next_bearer()

    def _start_next_bearer(self):
        """This bearer is finished; the next one's whole sweep starts here."""
        while self._bearer_queue:
            nxt = self._bearer_queue.pop(0)
            if self.can_use(nxt) and self.start(nxt):
                return True
        return False

    def _resolve_wounds(self):
        self._wound_roll.on_dice_acknowledged()
        target = self._wound_squad
        wounds = self._wound_roll.total
        self._wound_roll = None
        self._wound_squad = None
        self._stage = None
        self._log("%s: %s suffers %d mortal wound(s)." % (self.label, target.name, wounds))
        self._inflict(target, wounds)
        self._check_session_done()
        return True

    # ---------------------------------------------------------------- 06.02
    def _check_session_done(self):
        """Draining one unit's allocation is what starts the next unit's roll.

        The base's version only clears the slot; the queue is this class's, so
        the continuation has to be too."""
        if self.mortal_wound_session is not None and self.mortal_wound_session.done:
            self.mortal_wound_session = None
        if self.mortal_wound_session is None and self._stage is None:
            self._begin_next()

    @property
    def _sweep_running(self):
        """Whether ONE bearer's sweep is mid-flight.

        Deliberately NOT is_busy: can_use() and start() gate on this, and the
        bearer queue must not gate them or the chain in _begin_next() could
        never start its own next sweep."""
        return (self._pending is not None
                or bool(self._queue)
                or self._wound_roll is not None
                or self.mortal_wound_session is not None)

    @property
    def is_busy(self):
        """True for ALL the work owed, not just while a die is in the air.

        main.py's phase gate reads this, and a sweep that reported idle between
        two units - or between two bearers - would let the phase advance out
        from under the rest of the queue."""
        return self._sweep_running or bool(self._bearer_queue)
