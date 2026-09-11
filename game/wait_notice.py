"""Say a thing ONCE per window, when the game is waiting on somebody.

Two callers, which is why this is a module rather than a set on one of them:

  * game/retro_thrusters.py - the Twin Lance's end-of-Fight-phase move. The
    AI holds its own turn-end open while the opponent still owes that decision,
    and the button for it only appears once the unit is selected, so without a
    line saying so the game just looks stalled.

  * ai/agent_driver.py's Fight-phase branch - every OTHER reason the AI stops
    there. That branch advances the phase only when FightController reaches
    DONE and had no `else` at all, so any other state was a silent frame loop:
    a human unit still owing a Pile In, or the 12.04 alternation sitting on the
    human's side, look from the outside exactly like an engine that has hung.

Both answer the same question - "has this already been said this phase?" - and
a ledger kept twice is the drift this repo keeps consolidating. Keyed, because
what counts as "already said" differs: retro-thrusters says it once per OWNER,
the Fight-phase branch once per REASON.

Not a general-purpose logger. It holds no formatting and decides nothing about
what is worth saying; it only refuses to say the same thing twice before the
next reset().
"""


class WaitNotice:
    """A once-per-key announcement ledger, cleared at a window boundary."""

    def __init__(self, game_log=None):
        self.game_log = game_log
        self._said = set()

    def say_once(self, key, message):
        """Log `message` unless `key` has already been said since the last
        reset(). Returns whether it was actually logged, so a caller can tell
        "announced" from "already known" without keeping its own copy."""
        if key in self._said:
            return False
        self._said.add(key)
        if self.game_log is not None:
            self.game_log.add(message)
        return True

    def already_said(self, key):
        return key in self._said

    def reset(self):
        """The point at X for the "deferred until X" note - without one of
        these, a once-per-phase line becomes a once-per-battle line and every
        later phase goes silent again. Called from whoever owns the window."""
        self._said = set()
