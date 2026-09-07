"""Runtime probe: does rule 03.01's pre-game finish ONCE, and does battle
round 1 pay any Primary VP?

Both halves of one report - "der erste zug ging noch nicht los und der gegner
spieler 2 hat schon 36 VP". A unit test drives the controller directly and sees
every field set correctly; what it cannot see is main()'s own wiring, and
"built but never fed / entered twice" has bitten this repo repeatedly. So this
runs selfplay.py's REAL main() loop through runpy and counts the calls that
actually happen in it.

Nothing is staged: the pre-game runs of its own accord at the start of every
battle, so this is the rare case that is measurable PASSIVELY.

    python verify_pregame_starts_once.py [map] [frames] [--neutralize]

--neutralize restores the pre-fix world at the source (both hand-offs back to
their shipped form, _begin_battle() without its guard, Hold the Line paying
from round 1) and MUST report the reported behaviour instead.
"""

import io
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
NEUTRALIZE = "--neutralize" in sys.argv[1:]
MAP_KEY = ARGS[0] if ARGS else "map3"
FRAMES = ARGS[1] if len(ARGS) > 1 else "900"

# The paired armies from the report: Necrons (human) against Death Guard (AI).
# Set BEFORE main() reads them, and before selfplay.py imports main.
from game import config  # noqa: E402

config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "death_guard"
config.MAP = MAP_KEY

from game import missions, pregame, scouts  # noqa: E402

_ORIGINALS = {}


def _patch(path, old, new):
    full = os.path.join(ROOT, path)
    src = io.open(full, encoding="utf-8").read()
    if old not in src:
        raise SystemExit("--neutralize: anchor not found in %s" % path)
    _ORIGINALS.setdefault(full, src)
    io.open(full, "w", encoding="utf-8").write(src.replace(old, new, 1))


def _restore():
    for full, src in _ORIGINALS.items():
        io.open(full, "w", encoding="utf-8").write(src)


if NEUTRALIZE:
    # The pre-fix world, in full. A half-restored one measures nothing: with
    # only the guard removed the drivers still walk their queues once.
    _patch("game/pregame.py",
           "            resume = Resume(self._deployment_finished)\n"
           "            if self.redeploy_step.start(self, resume) or resume.fired:\n"
           "                return\n",
           "            if self.redeploy_step.start(self, self._finish_deployment):\n"
           "                return\n")
    _patch("game/pregame.py",
           "            resume = Resume(self._run_next_prebattle_step)\n"
           "            if step.start(self, resume) or resume.fired:\n"
           "                return\n",
           "            if step.start(self, self._run_next_prebattle_step):\n"
           "                return\n")
    _patch("game/pregame.py",
           "        if self.state == DONE:\n            return\n        self.state = DONE\n",
           "        self.state = DONE\n")
    _patch("game/missions.py",
           "        if battle_round is not None and battle_round < PRIMARY_FIRST_SCORING_ROUND:",
           "        if False and battle_round < PRIMARY_FIRST_SCORING_ROUND:")
    # main.py's own hand-off too. Leaving it fixed would still reproduce the
    # report, but only through the Pre-battle Abilities half - and a probe that
    # restores half a world is one this repo has been burned by before.
    _patch("main.py",
           "                nxt = pregame.Resume(\n"
           "                    lambda: self._run(index + 1, pregame_controller, on_done))\n"
           "                if self.steps[index].start(pregame_controller, nxt) or nxt.fired:\n",
           "                nxt = lambda: self._run(index + 1, pregame_controller, on_done)\n"
           "                if self.steps[index].start(pregame_controller, nxt):\n")
    # The modules were imported above, so re-import them under the patch.
    import importlib

    importlib.reload(pregame)
    importlib.reload(missions)
    importlib.reload(scouts)

counts = {
    "deployment finished": 0,
    "first-turn roll-offs": 0,
    "Pre-battle Abilities steps": 0,
    "Scouts queues walked": 0,
    "battles started": 0,
}
primary_lines = []


def _spy(cls, name, key):
    original = getattr(cls, name)

    def wrapper(self, *args, **kwargs):
        counts[key] += 1
        return original(self, *args, **kwargs)

    setattr(cls, name, wrapper)


_spy(pregame.PregameController, "_deployment_finished", "deployment finished")
_spy(pregame.PregameController, "_begin_first_turn_rolloff", "first-turn roll-offs")
_spy(pregame.PregameController, "_begin_prebattle_abilities", "Pre-battle Abilities steps")
_spy(pregame.PregameController, "_begin_battle", "battles started")
_spy(scouts.ScoutsStep, "start", "Scouts queues walked")

_real_score = missions.MissionController.score_primary


def _score_primary(self, objectives, player, battle_round):
    gained = _real_score(self, objectives, player, battle_round)
    if gained:
        primary_lines.append((battle_round, player, gained))
    return gained


missions.MissionController.score_primary = _score_primary

sys.argv = ["selfplay.py", MAP_KEY, FRAMES]
try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass
finally:
    _restore()

print()
print("=== pre-game, through the real main() loop (%s, %s frames%s) ==="
      % (MAP_KEY, FRAMES, ", NEUTRALIZED" if NEUTRALIZE else ""))
for label, value in counts.items():
    print("  %-28s %d" % (label, value))
round_one = [entry for entry in primary_lines if entry[0] == 1]
print("  %-28s %s" % ("Primary VP paid in round 1",
                      round_one if round_one else "none"))
print("  %-28s %s" % ("Primary VP paid later",
                      [e for e in primary_lines if e[0] != 1] or "none (run was short)"))
