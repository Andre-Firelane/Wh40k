"""A/B probes for "die KI darf ALLE einheiten durch waende bewegen", at the
SOURCE.

The permission half of the crossing house rule was always keyword-blind - it
ends in `not may_cross_walls(model)`, an OWNER answer, and measured over all
ten shipped lists on all three maps it blocks 0 of Player 2's 701 models
(MOUNTED included) against 116 of Player 1's. The PRICE was not: 584 of those
701 crossed free by rule 13.06 and the other 117 paid
config.WALL_CROSSING_COST_IN. That toll is now 0.

Each probe restores ONE half of the pre-fix world, or removes one thing the
change had to LEAVE standing, and has to make test_wall_crossing.py red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

CONFIG = os.path.join("game", "config.py")
MOVEMENT = os.path.join("game", "movement.py")
TERRAIN = os.path.join("game", "terrain.py")
SQUAD = os.path.join("game", "squad.py")

SUITE = "test_wall_crossing.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    # The documented __pycache__ race: these probes rewrite and restore inside
    # the same second, so a stale .pyc reports the PREVIOUS run's result.
    for root, dirs, _f in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


def run(suite):
    clear_cache()
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    if not match:
        return None, None, text
    return int(match.group(1)), int(match.group(2)), text


# 1. The whole pre-fix world: the toll back at the figure it shipped with.
COST_NEW = "WALL_CROSSING_COST_IN = 0.0"
COST_OLD = "WALL_CROSSING_COST_IN = 3.0"

# 2. The mechanism deleted rather than switched off. At the shipped toll of 0
#    this changes NOTHING - which is the point: only section 2b, which sets a
#    non-zero toll itself, can tell the difference, and it has to.
TOLL_GUARD_NEW = """        if not may_cross_walls(token) or config.WALL_CROSSING_COST_IN <= 0:
            return 0.0, False"""
TOLL_GUARD_OLD = """        return 0.0, False
        if not may_cross_walls(token) or config.WALL_CROSSING_COST_IN <= 0:
            return 0.0, False"""

# 3. The half-fix that looks done: the constant goes to zero but the mover
#    keeps the old figure hardcoded. Everything about the SHIPPED price is
#    then a lie, and section 2a has to say so.
HARDCODE_PAIRS = [
    ("if not may_cross_walls(token) or config.WALL_CROSSING_COST_IN <= 0:",
     "if not may_cross_walls(token) or 3.0 <= 0:"),
    ("if remaining <= config.WALL_CROSSING_COST_IN:",
     "if remaining <= 3.0:"),
    ("affordable = min(dist, remaining - config.WALL_CROSSING_COST_IN)",
     "affordable = min(dist, remaining - 3.0)"),
    ("return (config.WALL_CROSSING_COST_IN, False) if crosses else (0.0, True)",
     "return (3.0, False) if crosses else (0.0, True)"),
]

# 4. What the change had to LEAVE standing #1: the permission stays keyed on
#    the owner. Free crossing for the AI must not become free crossing.
OWNER_NEW = "    return owner in config.WALL_CROSSING_PLAYERS"
OWNER_OLD = "    return True"

# 5. What it had to leave standing #2: rule 13.05. "Crosses for nothing" must
#    not quietly turn into "may stop on top of a wall".
END_NEW = """    x = model.x_in if x_in is None else x_in
    y = model.y_in if y_in is None else y_in"""
END_OLD = """    return False
    x = model.x_in if x_in is None else x_in
    y = model.y_in if y_in is None else y_in"""

PROBES = [
    ("the toll back at 3.0 (the pre-fix world)",
     [(CONFIG, COST_NEW, COST_OLD)], SUITE),
    ("the toll machinery deleted instead of switched off",
     [(MOVEMENT, TOLL_GUARD_NEW, TOLL_GUARD_OLD)], SUITE),
    ("constant 0 but _wall_toll keeps 3.0 hardcoded",
     [(MOVEMENT, a, b) for a, b in HARDCODE_PAIRS], SUITE),
    ("the permission stops being owner-keyed (the human crosses too)",
     [(TERRAIN, OWNER_NEW, OWNER_OLD)], SUITE),
    ("rule 13.05 lifted as well (ending ON a wall allowed)",
     [(SQUAD, END_NEW, END_OLD)], SUITE),
]

baselines = {}
for suite in {p[2] for p in PROBES}:
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-40s %d/%d" % (suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {}
    try:
        ok = True
        for path, new, old in edits:
            originals.setdefault(path, read(path))
            src = read(path)
            if src.count(new) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)"
                      % (label, path, src.count(new)))
                ok = False
                bad += 1
                break
            write(path, src.replace(new, old))
        if not ok:
            continue
        got, total, text = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < baselines[suite]:
            verdict, detail = "BITES", "%d/%d" % (got, total)
        else:
            verdict, detail = "NO BITE", "%d/%d - FINDING ABOUT THE TEST" % (got, total)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:110])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
