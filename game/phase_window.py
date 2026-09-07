"""A reaction window opened at a PHASE BOUNDARY and answered frames later.

WHY THIS EXISTS
---------------
Three Stratagems fire "at the end of <someone's> Fight phase" and each of them
expressed that window as a LIVE phase test:

    if self.turn_tracker.phase != PHASE_FIGHT:
        return False

That check can never hold. main.py's advance_turn_phase() calls
turn_tracker.advance_phase() FIRST and only then runs the end-of-phase offers,
so by the time the offer is made the clock already reads the next phase - and
by the time a human answers the queued prompt it is later still. The result was
not "sometimes wrong": it was a guaranteed, silent no-op. Wall of Mirrors opened
a prompt whose every option returned False (reported: "funktioniert auch
nicht"); Cost of Victory never opened one at all.

So the window is a FACT THIS MODULE OWNS, not a fact about the clock: it is
open because an offer opened it, and it closes at the next phase boundary. The
same shape as the twelve `_offered_this_phase` memos around
game/fail_safe_detonator.py - state that main.py clears in its per-phase reset
block, rather than a question asked of a value that has already moved on.

WHY NOT "REMEMBER WHICH PHASE IT WAS"
-------------------------------------
Comparing against a remembered phase index would be the same bug with extra
steps: the fight phase's own boundary IS the moment the index changes, so the
value to compare against is already gone. What is unambiguous is WHO was
offered, which is exactly what arm() records.
"""


class PhaseWindow:
    """One end-of-phase reaction window, per controller.

    A controller arms it when it opens its offer and asks is_open() from
    can_use(), in place of a phase test. main.py closes it in the per-phase
    reset block, which runs BEFORE that boundary's offers - so the previous
    window is gone before a new one is armed.
    """

    __slots__ = ("_player",)

    def __init__(self):
        self._player = None

    def arm(self, player):
        """Open the window for `player` - the side being offered the reaction."""
        self._player = player

    def is_open(self, player=None):
        """Is the window standing (for `player`, when one is named)?"""
        if self._player is None:
            return False
        return player is None or player == self._player

    def close(self):
        self._player = None

    @property
    def player(self):
        return self._player
