"""A queue of forced Battle-shock tests, one per unit, drained one roll at a time.

WHY THIS EXISTS. BattleShockController holds ONE roll at a time
(start_forced_roll() refuses a second while one is open), and a rule that makes
"each enemy unit engaged with this unit" test can name several. Beast Snagga
Boyz' Mobbed (game/mobbed.py) wrote the queue for that; Blitz Brigade's
Impending Krunch (Mecha Orks G4) prints the same sentence shape - so it moved
here at its second consumer (error class 10). The Psychomancer's Nightmare
Shroud keeps its own older copy (game/psychomancer.py), named as the next
candidate rather than rewritten inside an Ork stage.

WHAT IS SHARED is exactly the part that is easy to get wrong:
  * a roll some OTHER rule has open is waited out, never overwritten;
  * one test starts per acknowledgement - main.py calls on_dice_acknowledged()
    AFTER battle_shock_controller's own, so the finished test is applied before
    the next one opens;
  * a target that died meanwhile is dropped, and a target already queued is not
    queued twice.

The tests are FORCED (start_forced_roll() with a penalty) - the entry every
out-of-turn test in this engine uses.
"""


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


class ForcedShockQueue:
    def __init__(self, battle_shock_controller=None, game_log=None):
        self.battle_shock_controller = battle_shock_controller
        self.game_log = game_log
        self._queue = []   # [(target squad, penalty, source label, log line)]

    def enqueue(self, target, penalty, source, message=None):
        """Queue one forced test; False when that unit is already waiting."""
        if any(queued is target for queued, _p, _s, _m in self._queue):
            return False
        self._queue.append((target, penalty, source, message))
        return True

    def _roll_is_open(self):
        bsc = self.battle_shock_controller
        if bsc is None:
            return False
        if getattr(bsc, "rolling_squad", None) is not None:
            return True
        dice = getattr(bsc, "dice_manager", None)
        return bool(getattr(dice, "pending_values", None))

    def drain(self):
        """Start the next test if nothing is open. True while the queue is
        working (a test started or is being waited for)."""
        while self._queue:
            target, penalty, source, message = self._queue[0]
            if self.battle_shock_controller is None or not _living(target):
                self._queue.pop(0)
                continue
            if self._roll_is_open():
                return True          # come back on the next acknowledgement
            started = self.battle_shock_controller.start_forced_roll(
                target, source, penalty=penalty)
            if not started:
                return True
            self._queue.pop(0)
            if message and self.game_log is not None:
                self.game_log.add(message)
            return True
        return False

    def on_dice_acknowledged(self):
        """The queue's re-entry point - one more test per acknowledged roll."""
        return self.drain()

    @property
    def is_busy(self):
        return bool(self._queue)
