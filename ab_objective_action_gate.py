"""A/B probes for the 2026-09-10 objective-action control gate, at the SOURCE.

  User: "Actions wie plunder werden angeboten, obwohl Einheit gar nicht auf
   einem objective steht ( muss nach Move aktualisiert werden)"

MEASURED BEFORE ANY CHANGE, and the report needed re-reading first: PLUNDER
WAS NEVER DRAWN in the reported game. logs/game_20260909_221504.log lists the
ten cards Player 1 drew, and the objective action on screen was CLEANSE.
"Actions wie plunder" names the CLASS.

Plunder itself is correct and stays untouched: its printed UNITS line asks for
a TERRAIN AREA outside your territory, not an objective (5 of map4's 8
plunderable areas carry no objective at all).

The defect is one question with two answers, three inches apart:

    objectives.is_within_range_of_objective()  footprint + 3"  <- START gate
    Objective.level_of_control()               footprint only  <- controlled_by,
                                                                  which COMPLETES needs

Measured at 0.5" over every shipped board - share of offers standing where the
unit cannot contribute to control at all: map1 55%, map2 58%, map3 61%,
map4 (the reported board) 59%. Reproduced end to end at 0.06" off the
footprint: button drawn, action started, 16.01 locked shooting AND charging,
controlled_by None, nothing completed.

Probe 4 is the one to watch. It narrows the gate to the footprint instead of
adding the control term - the OTHER fix that was on the table, and the one the
user did not choose. If it ever stops biting, the assurance that the 3" reach
survived has gone with it.
"""

import io
import os
import re
import shutil
import subprocess
import sys

MCTX = os.path.join("game", "mission_context.py")
SEC = os.path.join("game", "secondary_missions.py")
PRI = os.path.join("game", "primary_missions.py")

ACTIONS = "test_actions.py"
PRIMARY = "test_primary_missions.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
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


# ------------------------------------------- 1. the whole pre-fix world
GATE_NEW = """    return [o for o in _non_home_objectives(ctx)
            if o.controlled_by == ctx.player
            and is_within_range_of_objective(squad, [o])]"""
GATE_OLD = """    return [o for o in _non_home_objectives(ctx)
            if is_within_range_of_objective(squad, [o])]"""

# --------------------- 2/3. one caller keeps a private copy of the old form
CLEANSE_NEW = "    return objective_action_targets_for(squad, ctx)"
CLEANSE_OLD = """    return [o for o in _non_home_objectives(ctx)
            if is_within_range_of_objective(squad, [o])]"""

# ------------------------- 4. THE OTHER FIX: narrow the reach instead
# The function-local import keeps this probe RED rather than a NameError -
# a probe that crashes does not say WHICH assurance broke (nineteen instances).
NARROW_OLD = """    from game.objectives import is_on_objective
    return [o for o in _non_home_objectives(ctx)
            if o.controlled_by == ctx.player
            and is_on_objective(squad, [o])]"""

# ---------------------------- 5. control read from the wrong player
WRONG_PLAYER_OLD = """    return [o for o in _non_home_objectives(ctx)
            if o.controlled_by is not None
            and is_within_range_of_objective(squad, [o])]"""

PROBES = [
    ("the control term does not exist (the whole pre-fix world)",
     [(MCTX, GATE_NEW, GATE_OLD)], ACTIONS),
    ("...and the same world, measured through Secure Asset",
     [(MCTX, GATE_NEW, GATE_OLD)], PRIMARY),
    ("Cleanse keeps a private copy of the old gate",
     [(SEC, CLEANSE_NEW, CLEANSE_OLD)], ACTIONS),
    ("Secure Asset keeps a private copy of the old gate",
     [(PRI, CLEANSE_NEW, CLEANSE_OLD)], PRIMARY),
    ("THE OTHER FIX: narrow to the footprint instead of adding control",
     [(MCTX, GATE_NEW, NARROW_OLD)], ACTIONS),
    ("control is read as 'anybody holds it' rather than 'I do'",
     [(MCTX, GATE_NEW, WRONG_PLAYER_OLD)], ACTIONS),
]

print(__doc__.strip())
print()
baselines = {}
for _suite in sorted({p[2] for p in PROBES}):
    got, total, _t = run(_suite)
    baselines[_suite] = got
    print("BASELINE %-28s %s/%s" % (_suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {}
    try:
        ok = True
        for path, new, old in edits:
            originals.setdefault(path, read(path))
            cur = read(path)
            if cur.count(new) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)"
                      % (label, path, cur.count(new)))
                ok = False
                bad += 1
                break
            write(path, cur.replace(new, old))
        if not ok:
            continue
        got, tot, text = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < baselines[suite]:
            verdict, detail = "BITES", "%d/%d" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%d/%d - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL"):
                    print("             " + line.strip()[:112])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
