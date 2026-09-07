"""A/B probes for "the battle starts exactly once" and "round 1 pays no
Primary VP".

Both come from one report: "der erste zug ging noch nicht los und der gegner
spieler 2 hat schon 36 VP". The 36 was TWO faults multiplying - the pre-game
finished three times over (three deployment completions, three Scouts queues,
three battle starts, so the first Command phase handed out Core CP and scored
its Primary three times), on top of Hold the Line paying for the board as it
stood at deployment at all.

Each probe restores ONE pre-fix world at the SOURCE and must break its own
checks. Probe 2 is the one worth reading: a driver that walks its queue twice
is INVISIBLE behind _begin_battle()'s idempotence guard, which is why
test_pregame.py counts the hand-back itself rather than only the battle start.

Run: python ab_pregame_starts_once.py
"""

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

SUITES = ["test_pregame.py", "test_standard_missions.py", "test_tau_enhancements.py"]


def run(suite):
    """(passed, total) for either reporter shape used in this repo - testkit's
    "N/M checks passed" and test_pregame.py's "passed N, failed M". A crash
    counts as bitten."""
    proc = subprocess.run([sys.executable, suite], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", out)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(r"passed (\d+), failed (\d+)", out)
    if match:
        passed, failed = int(match.group(1)), int(match.group(2))
        return passed, passed + failed
    return (-1, -1)


class Patch:
    def __init__(self, name, edits, expect):
        self.name = name
        self.edits = edits
        self.expect = expect

    def __enter__(self):
        self.backup = {}
        for path, old, new in self.edits:
            full = os.path.join(ROOT, path)
            if full not in self.backup:
                self.backup[full] = io.open(full, encoding="utf-8").read()
            src = io.open(full, encoding="utf-8").read()
            if old not in src:
                raise SystemExit("%s: anchor not found in %s:\n  %s"
                                 % (self.name, path, old[:90]))
            io.open(full, "w", encoding="utf-8").write(src.replace(old, new, 1))
        return self

    def __exit__(self, *exc):
        for full, text in self.backup.items():
            io.open(full, "w", encoding="utf-8").write(text)
        # The probes rewrite and restore inside the same second, so the
        # __pycache__ race this repo has hit before is live here - clear it
        # between passes rather than measure the previous world.
        for dirpath, dirnames, _ in os.walk(ROOT):
            for name in list(dirnames):
                if name == "__pycache__":
                    shutil.rmtree(os.path.join(dirpath, name), ignore_errors=True)
                    dirnames.remove(name)
        return False


REDEPLOY_NEW = (
    "            resume = Resume(self._deployment_finished)\n"
    "            if self.redeploy_step.start(self, resume) or resume.fired:\n"
    "                return\n"
)
REDEPLOY_OLD = (
    "            if self.redeploy_step.start(self, self._finish_deployment):\n"
    "                return\n"
)

PREBATTLE_NEW = (
    "            resume = Resume(self._run_next_prebattle_step)\n"
    "            if step.start(self, resume) or resume.fired:\n"
    "                return\n"
)
PREBATTLE_OLD = (
    "            if step.start(self, self._run_next_prebattle_step):\n"
    "                return\n"
)

BATTLE_GUARD = (
    "        if self.state == DONE:\n"
    "            return\n"
    "        self.state = DONE\n"
)
BATTLE_GUARD_OFF = "        self.state = DONE\n"

ONCE_NEW = (
    "    def __call__(self):\n"
    "        if self.fired:\n"
    "            return\n"
    "        self.fired = True\n"
    "        self._fn()\n"
)
ONCE_OLD = (
    "    def __call__(self):\n"
    "        self._fn()\n"
)

CHAIN_NEW = (
    "                nxt = pregame.Resume(\n"
    "                    lambda: self._run(index + 1, pregame_controller, on_done))\n"
    "                if self.steps[index].start(pregame_controller, nxt) or nxt.fired:\n"
)
CHAIN_OLD = (
    "                nxt = lambda: self._run(index + 1, pregame_controller, on_done)\n"
    "                if self.steps[index].start(pregame_controller, nxt):\n"
)

SCORE_CALL = (
    "            mission_controller.score_primary(state.objectives, turn_tracker.active_player,\n"
    "                                             turn_tracker.battle_round)"
)
SCORE_CALL_HARDCODED = (
    "            mission_controller.score_primary(state.objectives, turn_tracker.active_player,\n"
    "                                             2)"
)

BAND_TEST = (
    "        if battle_round is not None and battle_round < PRIMARY_FIRST_SCORING_ROUND:"
)
BAND_TEST_OFF = (
    "        if False and battle_round < PRIMARY_FIRST_SCORING_ROUND:"
)


PROBES = [
    # 1. The Deploy Armies hand-off, exactly as it shipped: the redeploy step
    #    resumes the sequence itself AND answers "nothing to do", so the caller
    #    runs the rest a second time - a second first-turn roll-off.
    Patch("the redeploy hand-off is back to its pre-fix form",
          [("game/pregame.py", REDEPLOY_NEW, REDEPLOY_OLD)],
          expect=["test_pregame.py", "test_tau_enhancements.py"]),

    # 2. The Pre-battle Abilities queue, same shape. Measured on the hand-back
    #    COUNT, because _begin_battle()'s guard hides this one from the score.
    Patch("the pre-battle queue is back to its pre-fix form",
          [("game/pregame.py", PREBATTLE_NEW, PREBATTLE_OLD)],
          expect=["test_pregame.py"]),

    # 3. The backstop alone. Nothing else changes - which is the point: it has
    #    to hold even when a future caller reaches _begin_battle() twice.
    Patch("_begin_battle() loses its idempotence guard",
          [("game/pregame.py", BATTLE_GUARD, BATTLE_GUARD_OFF)],
          expect=["test_pregame.py"]),

    # 4. Resume stops being one-shot in the only way that matters here: `fired`
    #    never gets set, so both drivers fall through and advance twice.
    Patch("Resume stops recording that it fired",
          [("game/pregame.py", ONCE_NEW, ONCE_OLD)],
          expect=["test_pregame.py", "test_tau_enhancements.py"]),

    # 5. main.py's own chain back to the plain lambda. Source-guarded, because
    #    _RedeployChain is a local class inside main() that no test can reach.
    Patch("main.py's redeploy chain drops the one-shot",
          [("main.py", CHAIN_NEW, CHAIN_OLD)],
          expect=["test_pregame.py"]),

    # 6. THE WHOLE PRE-FIX WORLD - the state the report was made against.
    Patch("the whole pre-fix pre-game is restored",
          [("game/pregame.py", REDEPLOY_NEW, REDEPLOY_OLD),
           ("game/pregame.py", PREBATTLE_NEW, PREBATTLE_OLD),
           ("game/pregame.py", BATTLE_GUARD, BATTLE_GUARD_OFF)],
          expect=["test_pregame.py", "test_tau_enhancements.py"]),

    # 7-9. The round band.
    Patch("Hold the Line pays from round 1 again",
          [("game/missions.py", "PRIMARY_FIRST_SCORING_ROUND = 2",
            "PRIMARY_FIRST_SCORING_ROUND = 1")],
          expect=["test_standard_missions.py"]),
    Patch("score_primary() ignores the round band",
          [("game/missions.py", BAND_TEST, BAND_TEST_OFF)],
          expect=["test_standard_missions.py"]),
    Patch("a main.py call site hardcodes the round instead of passing the live one",
          [("main.py", SCORE_CALL, SCORE_CALL_HARDCODED)],
          expect=["test_standard_missions.py"]),
]


def main():
    print("baseline...")
    base = {}
    for suite in SUITES:
        base[suite] = run(suite)
        print("  %-32s %d/%d" % (suite, base[suite][0], base[suite][1]))
        if base[suite][0] != base[suite][1] or base[suite][0] < 0:
            raise SystemExit("baseline is not green: %s" % suite)

    print()
    silent = []
    for probe in PROBES:
        with probe:
            results = {suite: run(suite) for suite in probe.expect}
        bit = False
        lines = []
        for suite, (passed, total) in results.items():
            before = base[suite][0]
            if passed == -1:
                lines.append("%s CRASHED" % suite)
                bit = True
            else:
                lines.append("%s %d/%d (was %d)" % (suite, passed, total, before))
                if passed < before:
                    bit = True
        print("%s  %s" % ("BITES " if bit else "SILENT", probe.name))
        for line in lines:
            print("           %s" % line)
        if not bit:
            silent.append(probe.name)

    print()
    if silent:
        print("PROBES THAT DID NOT BITE (a finding about the TEST, not the code):")
        for name in silent:
            print("  -", name)
        raise SystemExit(1)
    print("all %d probes bit" % len(PROBES))


if __name__ == "__main__":
    main()
