"""A/B probes for the phase autosave: every guard in test_autosave.py (and the
one pin left in test_game_menu.py) has to go RED when the thing it guards is
taken away at the SOURCE - and red, not crashed.

Each probe replaces one exact span, clears __pycache__ (CLAUDE.md error class
19: a probe that writes and runs in the same second otherwise measures the
previous probe), runs the suites it names, and restores the file in `finally`.
A probe that does not turn at least one check red is reported as NO BITE,
which is a finding about the TEST, not an all-clear. A suite that ends without
its "N/M checks passed" line is reported as CRASHED, which is its own outcome.

EXCLUSIVE: this rewrites source files while it runs. No suite, measurement,
edit or commit may overlap it.

Run: python ab_phase_autosave.py
"""

import io
import os
import re
import shutil
import subprocess
import sys

AUTOSAVE = "test_autosave.py"
MENU = "test_game_menu.py"

PROBES = [
    ("the key drops the phase (one key per turn)",
     "game/autosave.py",
     '            getattr(turn_tracker, "phase", None))',
     "            None)",
     (AUTOSAVE,)),
    ("the key reads active_player instead of the turn owner",
     "game/autosave.py",
     '            getattr(turn_tracker, "turn_owner", None),',
     '            getattr(turn_tracker, "active_player", None),',
     (AUTOSAVE,)),
    ("an unsettled frame records its phase as written",
     "game/autosave.py",
     "        key = phase_key(turn_tracker)\n"
     "        if key is None or key == self.last_saved or not settled:",
     "        key = phase_key(turn_tracker)\n"
     "        if key is not None and not settled:\n"
     "            self.last_saved = key\n"
     "        if key is None or key == self.last_saved or not settled:",
     (AUTOSAVE,)),
    ("seed() is a no-op (a loaded battle rewrites what it opened)",
     "game/autosave.py",
     "        self.last_saved = phase_key(turn_tracker)",
     "        pass",
     (AUTOSAVE,)),
    ("scene_io.write is not atomic (the original write)",
     "game/scene_io.py",
     '    temp = f"{path}.tmp"\n'
     "    try:\n"
     '        with open(temp, "w", encoding="utf-8") as handle:\n'
     "            json.dump(data, handle, indent=1)\n"
     "        os.replace(temp, path)\n"
     "    except BaseException:\n"
     "        # The target is untouched either way; this only keeps a failed write\n"
     "        # from leaving its half-file lying next to it.\n"
     "        try:\n"
     "            os.remove(temp)\n"
     "        except OSError:\n"
     "            pass\n"
     "        raise\n",
     '    with open(path, "w", encoding="utf-8") as handle:\n'
     "        json.dump(data, handle, indent=1)\n",
     (AUTOSAVE,)),
    ("main.py never seeds a loaded battle",
     "main.py",
     "        autosave_edge.seed(turn_tracker)\n",
     "        pass\n",
     (AUTOSAVE,)),
    ("main.py saves while a declaration is still open",
     "main.py",
     "                         and not _has_unresolved_declaration()\n",
     "",
     (AUTOSAVE,)),
    ("main.py ignores config.AUTOSAVE",
     "main.py",
     "        if config.AUTOSAVE:\n            _autosave_key = autosave_edge.take(",
     "        if True:\n            _autosave_key = autosave_edge.take(",
     (AUTOSAVE,)),
    ("a disk error ends the battle",
     "main.py",
     "                except OSError as exc:\n"
     "                    # A locked or full disk must not end the battle the save is",
     "                except ZeroDivisionError as exc:\n"
     "                    # A locked or full disk must not end the battle the save is",
     (AUTOSAVE,)),
    ("main.py writes the autosave past the one scene writer",
     "main.py",
     '                    _save_scene(f"autosaved at {autosave.describe(_autosave_key)}",',
     '                    _save_scene_directly(f"autosaved at {autosave.describe(_autosave_key)}",',
     (AUTOSAVE, MENU)),
    ("selfplay.py leaves the autosave on",
     "selfplay.py",
     "config.AUTOSAVE = False\n",
     "",
     (AUTOSAVE,)),
    ("a smoke leaves the autosave on",
     "smoke_pregame.py",
     "config.AUTOSAVE = False\n",
     "",
     (AUTOSAVE,)),
    ("the autosave ships OFF",
     "game/config.py",
     "AUTOSAVE = True\n",
     "AUTOSAVE = False\n",
     (AUTOSAVE,)),
]


def clear_pycache():
    for root, dirs, _files in os.walk("."):
        for name in dirs:
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def run_suite(suite):
    proc = subprocess.run([sys.executable, suite], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    match = re.search(r"(\d+)/(\d+) checks passed", proc.stdout)
    if not match:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
        return None, " | ".join(tail)
    passed, total = int(match.group(1)), int(match.group(2))
    return total - passed, f"{passed}/{total}"


def main():
    clear_pycache()
    baseline = {}
    for suite in (AUTOSAVE, MENU):
        red, summary = run_suite(suite)
        baseline[suite] = red
        print(f"baseline {suite}: {summary}")
        if red != 0:
            print("the baseline is not green - probes would bite trivially, stopping")
            return 2

    silent = 0
    for label, path, old, new, suites in PROBES:
        src = io.open(path, encoding="utf-8", newline="").read()
        if src.count(old) != 1:
            print(f"ANCHOR MISSING ({src.count(old)}x) for probe: {label}")
            silent += 1
            continue
        try:
            io.open(path, "w", encoding="utf-8", newline="").write(src.replace(old, new))
            clear_pycache()
            outcomes = []
            bit = False
            for suite in suites:
                red, summary = run_suite(suite)
                if red is None:
                    outcomes.append(f"{suite}: CRASHED ({summary})")
                else:
                    outcomes.append(f"{suite}: {summary}")
                    bit = bit or red > 0
            crashed = any("CRASHED" in o for o in outcomes)
            verdict = "BITES" if bit and not crashed else ("CRASHED" if crashed else "NO BITE")
            if verdict != "BITES":
                silent += 1
            print(f"[{verdict:7}] {label}  ->  " + "; ".join(outcomes))
        finally:
            io.open(path, "w", encoding="utf-8", newline="").write(src)
            clear_pycache()

    print()
    if silent:
        print(f"{silent} probe(s) did not bite cleanly")
        return 1
    print(f"all {len(PROBES)} probes bite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
