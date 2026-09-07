"""A/B probes for the standard missions' retuned rates.

Each probe restores one pre-fix world at the SOURCE and must break its own
checks. The point of probes 3-5 in particular: raising the ledger's rate while
the mission card or the AI prompt keeps quoting the old one is a change that
LOOKS done and is not - the AI would go on weighing ground against kills with
3-and-1 arithmetic, and nothing in the game would contradict it.

Run: python ab_mission_rates.py
"""

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

SUITES = ["test_standard_missions.py", "test_primary_missions.py",
          "test_secondary_missions.py", "test_mission_cards_ui.py"]


def run(suite):
    proc = subprocess.run([sys.executable, suite], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", out)
    if not match:
        return (-1, -1)   # crashed: counts as bitten
    return int(match.group(1)), int(match.group(2))


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
                raise SystemExit(f"{self.name}: anchor not found in {path}:\n  {old[:90]}")
            io.open(full, "w", encoding="utf-8").write(src.replace(old, new, 1))
        return self

    def __exit__(self, *exc):
        for full, text in self.backup.items():
            io.open(full, "w", encoding="utf-8").write(text)
        for dirpath, dirnames, _ in os.walk(ROOT):
            for d in list(dirnames):
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                    dirnames.remove(d)
        return False


PROBES = [
    # 1-2. The rates themselves, back where they were.
    Patch("the Primary rate is back to 3",
          [("game/missions.py", "PRIMARY_POINTS_PER_OBJECTIVE = 6",
            "PRIMARY_POINTS_PER_OBJECTIVE = 3")],
          expect=["test_standard_missions.py"]),
    Patch("the Secondary rate is back to 1",
          [("game/missions.py", "SECONDARY_POINTS_PER_KILL = 3",
            "SECONDARY_POINTS_PER_KILL = 1")],
          expect=["test_standard_missions.py"]),

    # 3. The ledger pays the new rate, the mission CARD still prints the old
    #    one. The strip and the scoreboard then disagree.
    Patch("the Primary card prints a hardcoded 3 again",
          [("game/missions.py",
            'f"At the start of your Command phase, score {PRIMARY_POINTS_PER_OBJECTIVE} "\n'
            '    "victory points for each objective marker you currently control."',
            '"At the start of your Command phase, score 3 "\n'
            '    "victory points for each objective marker you currently control."')],
          expect=["test_standard_missions.py"]),
    Patch("the Secondary card prints a hardcoded 1 again",
          [("game/missions.py",
            'f"At the end of your turn, score {SECONDARY_POINTS_PER_KILL} victory "\n'
            '    "points for each enemy unit that has been destroyed."',
            '"At the end of your turn, score 1 victory "\n'
            '    "points for each enemy unit that has been destroyed."')],
          expect=["test_standard_missions.py"]),

    # 5-6. The AI keeps planning against the old economy. This is the one that
    #      would ship silently: the game plays correctly and the opponent
    #      simply makes worse decisions every turn.
    Patch("the planner prompt quotes the old rates",
          [("ai/planner_prompt.py",
            'f"{PRIMARY_POINTS_PER_OBJECTIVE} VP per objective you control at the start of each of your own "\n'
            '    f"Command phases; Secondary (\\"No Mercy\\") pays {SECONDARY_POINTS_PER_KILL} VP per enemy unit "',
            '"3 VP per objective you control at the start of each of your own "\n'
            '    "Command phases; Secondary (\\"No Mercy\\") pays 1 VP per enemy unit "')],
          expect=["test_standard_missions.py"]),
    Patch("the tactical prompt quotes the old rates",
          [("ai/tactical_prompt.py",
            'f"Line\\") pays {PRIMARY_POINTS_PER_OBJECTIVE} VP for each objective your side controls, scored "',
            '"Line\\") pays 3 VP for each objective your side controls, scored "')],
          expect=["test_standard_missions.py"]),

    # 7. Rate ignored entirely - one point per objective, whatever the constant
    #    says. Catches a scorer that stopped multiplying.
    Patch("score_primary() stops multiplying by the rate",
          [("game/missions.py",
            "gained = controlled * PRIMARY_POINTS_PER_OBJECTIVE",
            "gained = controlled")],
          expect=["test_standard_missions.py", "test_primary_missions.py"]),
    Patch("score_secondary_end_of_turn() stops multiplying by the rate",
          [("game/missions.py",
            "gained = kills * SECONDARY_POINTS_PER_KILL",
            "gained = kills")],
          expect=["test_standard_missions.py", "test_secondary_missions.py"]),

    # 9. The card systems stop replacing the standard missions, so the human
    #    would score BOTH their Force Disposition Primary and Hold the Line.
    Patch("Hold the Line is no longer skipped for the card player",
          [("game/missions.py",
            "        if self.plays_primary_mission_card(player):\n            return 0",
            "        if False:\n            return 0")],
          expect=["test_standard_missions.py", "test_primary_missions.py"]),
]


def main():
    print("baseline...")
    base = {}
    for suite in SUITES:
        base[suite] = run(suite)
        print(f"  {suite:32s} {base[suite][0]}/{base[suite][1]}")
        if base[suite][0] != base[suite][1]:
            raise SystemExit(f"baseline is not green: {suite}")

    print()
    silent = []
    for probe in PROBES:
        with probe:
            results = {s: run(s) for s in probe.expect}
        bit = False
        lines = []
        for suite, (passed, total) in results.items():
            before = base[suite][0]
            if passed == -1:
                lines.append(f"{suite} CRASHED")
                bit = True
            else:
                lines.append(f"{suite} {passed}/{total} (was {before})")
                if passed < before:
                    bit = True
        print(f"{'BITES ' if bit else 'SILENT'}  {probe.name}")
        for line in lines:
            print(f"           {line}")
        if not bit:
            silent.append(probe.name)

    print()
    if silent:
        print("PROBES THAT DID NOT BITE (a finding about the TEST, not the code):")
        for name in silent:
            print("  -", name)
        raise SystemExit(1)
    print(f"all {len(PROBES)} probes bit")


if __name__ == "__main__":
    main()
