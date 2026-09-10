"""A/B probes for the 2026-09-09 Branching Fates report, at the SOURCE.

  "Branching fates auf brightlance damage Wurf hat den Wurf auf 4 geändert,
   nicht auf 6"

Reproduced in the user's own log, as a PAIR:
    line  282  ... Eldritch Storm counts as an unmodified 6 (die 1 -> 6).
    line 1239  ... Bright Lance   counts as an unmodified 6 (die 1 -> 4).

The Bright Lance is D6+2, the Eldritch Storm a plain D3 - so the old reading
("the RESULT becomes 6") set the lance's die to 4, capping a weapon whose own
maximum is 8, and withheld the offer entirely once the result already reached
6 (a die of 5 is a result of 7). The printed sentence has ONE predicate for
all three roll types - "change the result of one Hit roll, one Wound roll or
one Damage roll ... to an unmodified 6" - and the hit/wound halves have always
set the DIE. So does game/structural_collapse.py, whose header says outright
that "a Damage roll of 1" names the die and not the total.

Each probe restores one piece of the pre-fix world and has to make its suite red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

BF = os.path.join("game", "branching_fates.py")
CTRL = os.path.join("game", "unmodified_six_controller.py")
DN = os.path.join("game", "dice_notation.py")

FARSEER = "test_farseer.py"


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


# --------------------------------------------- 1. the whole pre-fix world
# _damage_offer() back on the RESULT reading, with face_for_total()'s
# arithmetic inlined (the helper itself is gone, and restoring it would test
# the helper rather than the reading).
OFFER_NEW = '''        squad, model, roll = context
        if not roll.single_die:
            return None
        values = self.dice_manager.pending_values
        if not values:
            return None
        face = branching_fates.damage_change(squad, model, values[0])
        if face is None:
            return None  # the die is already a 6, or the ability is not live
        return (face, squad, model)'''
OFFER_OLD = '''        squad, model, roll = context
        if not roll.single_die:
            return None
        amount = roll.projected_total
        if amount is None:
            return None
        wanted = branching_fates.damage_change(squad, model, amount)
        if wanted is None:
            return None
        face = wanted - roll.notation.bonus * roll.count
        if face < 1 or self.dice_manager.pending_values[0] == face:
            return None
        return (face, squad, model)'''

# --------------------------------------------------- 2. only the GATE moves
# damage_change() gating on the RESULT again. On its own this is the half that
# WITHHELD the offer: a D6+2 die of 5 is a result of 7, so nothing was offered.
GATE_NEW = '''    if face >= BRANCHING_FATES_RESULT:
        return None
    return BRANCHING_FATES_RESULT'''
GATE_OLD = '''    if face + 2 >= BRANCHING_FATES_RESULT:
        return None
    return BRANCHING_FATES_RESULT'''

# ------------------------------------------- 3. the multi-die guard removed
SINGLE_NEW = '''        return self.count * self.notation.dice == 1'''
SINGLE_OLD = '''        return True'''

# --------------------------------------- 4. the log stops naming the amount
LOG_NEW = '''            amount = "" if total is None else f", for {total} damage"'''
LOG_OLD = '''            amount = ""  # probe: the log stops naming the resulting amount'''

PROBES = [
    ("the RESULT reading is back (the whole pre-fix world)",
     [(CTRL, OFFER_NEW, OFFER_OLD)], FARSEER),
    ("only the GATE reads the result - the withheld offers return",
     [(BF, GATE_NEW, GATE_OLD)], FARSEER),
    ("the multi-die guard is gone",
     [(DN, SINGLE_NEW, SINGLE_OLD)], FARSEER),
    ("the log stops naming the resulting amount",
     [(CTRL, LOG_NEW, LOG_OLD)], FARSEER),
]

print(__doc__.strip())
print()
baselines = {}
for suite in {p[2] for p in PROBES}:
    got, total, _t = run(suite)
    baselines[suite] = got
    print("BASELINE %s: %s/%s" % (suite, got, total))
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
