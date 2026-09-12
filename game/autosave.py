"""The autosave: one snapshot on every PHASE change of a battle.

User, first: "Auto save pro Schlachtrunde". Then, after playing with it: "der
autosave scheint nicht zu funktionieren. bitte mach einen autosave bei jedem
phasenwechsel."

WHY THE EDGE MOVED FROM THE ROUND TO THE PHASE. A battle round is two whole
turns, ten phases, and at a human's pace that is a long time. The round edge
meant a closed window or a crash could throw away almost two turns of play,
and Resume then opened a board from long before the one the player remembered
- which reads exactly as "it did not save". The phase is the smallest edge at
which the board is settled by construction: the rules put a boundary there,
every activation of the phase before it has finished, and rule 15.01's
once-per-phase ledger is empty.

THE KEY IS (battle round, turn owner, phase), and all three are needed. The
phase NAME alone repeats: a player's Command phase comes back every turn, and
the two players' Movement phases of one round are different moments. The
round alone was the old edge. The turn owner alone misses four of the five
changes in a turn. Rule 07.03's order means the tuple changes at EVERY phase
boundary and at no other time - `active_player` is deliberately not part of
it, because it flips for every defender's save (game/turn.py), which is not a
boundary of anything.

ONE CALL, NOT AN ASK-THEN-REMEMBER PAIR. take() answers "is a save due" and
records the answer in the same breath - the same shape as
DiceManager.claim_reroll_offer(), and for the same reason: a caller that asks
and forgets to record writes the file on every frame; one that records and
forgets to write skips a phase silently. With one call there is no way to do
half of it.

THE BOARD HAS TO BE SETTLED, and that is main()'s call rather than this
module's: "settled" means no decision, roll, notice, allocation or open
declaration is pending, and every one of those lives in main(). take() is
simply handed the answer. A save that is held back is not lost: the key it
would have written stays unrecorded, so the first settled frame writes it - and
if two phase changes go by while something is pending, the second simply
replaces the first. The file only ever holds the latest board anyway.

A LOADED BATTLE IS SEEDED, NOT SAVED. seed() records the phase the snapshot
resumed on, so opening a save does not immediately rewrite the autosave over
the top of what was just opened - the promise the round-edge code made in a
comment and broke in its own ordering (it seeded before the snapshot was
restored, so the very first frame after a --load always wrote).

WHAT A MID-TURN AUTOSAVE CANNOT BRING BACK, named rather than discovered. The
round-edge autosave was complete by construction because every TURN-scoped
ledger is empty at the start of a round. A phase edge inside a turn is not
such a moment, and a snapshot taken there is exactly as complete as F9 or the
menu's Save Game taken at the same instant - no more, no less:

  * KEPT: positions, wounds, which model is which, reserves and transports,
    command points, the VP ledger, the Secondary deck and hand, the Primary's
    battle-long latches, Unit Statistics, and - through game/activation_state.py
    - who has already moved, advanced, fallen back, shot, charged and fought.
  * LOST: the mission controllers' turn-scoped bookkeeping (units and models
    destroyed THIS turn, which several end-of-turn cards count; the
    start-of-turn snapshots Overwhelming Force and three Primary boxes read;
    objective actions started this turn), and the once-per-turn ledgers held
    inside individual ability controllers. A battle resumed mid-turn scores
    the rest of that turn as though those had not happened.
"""


def phase_key(turn_tracker):
    """(battle round, turn owner, phase) - or None before the battle begins.

    None rather than a key during the pre-game: rule 03.01's deployment runs on
    a TurnTracker held at battle round 0, and a snapshot of a half-deployed
    army is not a battle anyone can resume."""
    if turn_tracker is None or not getattr(turn_tracker, "started", False):
        return None
    return (getattr(turn_tracker, "battle_round", None),
            getattr(turn_tracker, "turn_owner", None),
            getattr(turn_tracker, "phase", None))


def describe(key):
    """The log line's wording for a key - "battle round 2, Player 1's Shooting
    phase". A save that names the round but not the phase is the diagnostic
    line that leaves out exactly the number in question."""
    battle_round, owner, phase = key
    return f"battle round {battle_round}, {owner}'s {phase} phase"


class AutosaveEdge:
    """Remembers the last phase that was written. One per battle."""

    def __init__(self):
        self.last_saved = None

    def seed(self, turn_tracker):
        """Record the phase a loaded snapshot resumed on, WITHOUT saving it."""
        self.last_saved = phase_key(turn_tracker)

    def take(self, turn_tracker, settled):
        """The key to write now, recorded as written - or None.

        None before the battle, on a phase already written, and on any frame
        that is not `settled`. The caller writes the file whenever this returns
        a key; nothing else has to be remembered."""
        key = phase_key(turn_tracker)
        if key is None or key == self.last_saved or not settled:
            return None
        self.last_saved = key
        return key
