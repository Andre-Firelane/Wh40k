"""A/B probes for "pick the unit on the battlefield, not from a list".

Each probe restores ONE piece of the pre-fix world AT THE SOURCE and must make
a suite go red. A probe that does not bite is a finding about the TEST, not a
clean bill of health - this repo has recorded that lesson often enough that the
script counts it as a failure.

Two suites, because the feature has two halves that fail differently: the
generic mechanism (test_unit_pick.py) and the one ability that used to own a
private copy of it (test_mission_unit_pick.py, Burden of Trust).
"""

import io
import os
import re
import shutil
import subprocess
import sys

DECISION = os.path.join("game", "decision.py")
PICK = os.path.join("game", "unit_pick.py")
PANEL = os.path.join("game", "ui", "action_panel.py")
OVERLAY = os.path.join("game", "ui", "decision_overlay.py")
MISSIONS = os.path.join("game", "secondary_missions.py")
MIRRORS = os.path.join("game", "kauyon_wall_of_mirrors.py")
MAIN = "main.py"

SUITES = ["test_unit_pick.py", "test_mission_unit_pick.py"]


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def clear_pycache():
    """The documented __pycache__ race: these probes write and restore inside
    the same second, so a stale .pyc makes the next run report the previous
    world's results."""
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


def run():
    clear_pycache()
    scores = []
    text = ""
    for suite in SUITES:
        out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
        blob = out.stdout + out.stderr
        text += blob
        match = re.search(r"(\d+)/(\d+) checks passed", blob)
        scores.append((int(match.group(1)), int(match.group(2))) if match else (None, None))
    return scores, text


# (label, file, fixed source, pre-fix source)
PROBES = [
    ("the tag thrown away (the whole feature off)", DECISION,
     "        squad = entry[2] if len(entry) > 2 else None",
     "        squad = None"),
    ("no on-board guard - an unclickable prompt (Fehlerklasse 25)", PICK,
     "        if id(squad) not in on_board:\n            return None                    # nothing to click - Fehlerklasse 25",
     "        if False:\n            return None"),
    ("no duplicate guard - a click with two answers", PICK,
     "        if id(squad) in indices:\n            return None                    # same unit twice - see the docstring",
     "        if False:\n            return None"),
    ("dead models counted as clickable", PICK,
     "        if getattr(token, \"is_dead\", None) is not None and token.is_dead():\n            continue",
     "        if False:\n            continue"),
    ("the way out dropped from the panel", PANEL,
     "        for label, index in pick.skip_options:",
     "        for label, index in []:"),
    ("the panel screen never reached", PANEL,
     "        if unit_pick is not None:\n            self._draw_unit_pick_ui(surface, rect, unit_pick)",
     "        if False:\n            self._draw_unit_pick_ui(surface, rect, unit_pick)"),
    ("the overlay dimming the board it has to be clicked on", OVERLAY,
     "        if not decision_manager.is_pending or board_pick:",
     "        if not decision_manager.is_pending:"),
    ("main.py back to overlay-only - blocked but unclickable", MAIN,
     "                    pick = board_unit_pick()\n                    if pick is not None:",
     "                    pick = board_unit_pick()\n                    if False:"),
    ("no rings on the board - hunting by trial and error", MAIN,
     "            board_surface, board, unit_pick.target_models(frame_unit_pick, state.tokens))",
     "            board_surface, board, set())"),
    ("Burden of Trust's guards back to a name list", MISSIONS,
     "        options = [(squad.name, (lambda s=squad: on_pick(s)), squad) for squad in eligible]",
     "        options = [(squad.name, (lambda s=squad: on_pick(s))) for squad in eligible]"),
    ("Wall of Mirrors back to a name list (THE REPORT)", MIRRORS,
     "            [(squad.name, (lambda s=squad: self.use(s)), squad) for squad in candidates]",
     "            [(squad.name, (lambda s=squad: self.use(s))) for squad in candidates]"),
]

baseline, blob = run()
if any(got is None for got, _total in baseline):
    print("BASELINE DID NOT RUN:\n" + blob[-2000:])
    raise SystemExit(2)
print("baseline: " + ", ".join(f"{s}: {g}/{t}" for s, (g, t) in zip(SUITES, baseline)) + "\n")

bad = 0
for label, path, fixed, prefix in PROBES:
    src = read(path)
    if src.count(fixed) != 1:
        print(f"  SKIP     {label}: anchor not unique in {path}")
        bad += 1
        continue
    try:
        write(path, src.replace(fixed, prefix))
        scores, text = run()
        drops = [f"{s}: {g}/{t}" for s, (g, t), (b, _bt) in zip(SUITES, scores, baseline)
                 if g is None or g < b]
        if drops:
            print(f"  BITES    {label}: " + ", ".join(drops))
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:110]}")
                    break
        else:
            print(f"  NO BITE  {label}: unchanged - FINDING ABOUT THE TEST")
            bad += 1
    finally:
        write(path, src)

clear_pycache()
print()
print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
raise SystemExit(1 if bad else 0)
