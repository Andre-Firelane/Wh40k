"""A/B probes for "Fireknife kann all failed hits rerollen ... das wurde mir
nicht angeboted", at the SOURCE.

Seven abilities print the same two-clause sentence, and both attack steps used
to read its second clause as all-or-nothing. The player's only way to touch his
misses was to discard the successes with them - on the reported roll that cost
him a hit (6 -> 5).

Each probe restores ONE half of the pre-fix world. Two of them are worth more
than the rest:

  * the four "suppress the failures" probes have to bite in BOTH steps and BOTH
    files. The bug was one reading applied four times; a fix that reaches one
    twin is the same bug with a smaller blast radius.

  * "the offer is not spent by being made" is the second, unreported defect
    found while reading these four. It can only bite through the "1s only"
    path, because that is the only one that returns through _finish_hit_roll()
    and re-opens the gate.
"""

import io
import os
import re
import shutil
import subprocess
import sys

SHOOT = os.path.join("game", "shooting.py")
FIGHT = os.path.join("game", "fight.py")
SCOPE = os.path.join("game", "reroll_scope.py")

SUITE = "test_reroll_scope.py"
WIND = "test_windriders.py"


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


# --- the hit step, both files ----------------------------------------------
SHOOT_HIT_NEW = '''        options = []
        if free_misses > 0:'''
SHOOT_HIT_OLD = '''        options = []
        if free_misses > 0 and not swift:'''

FIGHT_HIT_NEW = '''        options = []
        if free_misses > 0:'''
FIGHT_HIT_OLD = '''        options = []
        if free_misses > 0 and not ones_or_whole:'''

# --- the wound step, both files --------------------------------------------
SHOOT_WOUND_NEW = '''            options = []
            if free_no_effect > 0:
                options.append((
                    f"Re-roll failed wound rolls ({free_no_effect} dice)",
                    lambda: self._reroll_wound(free_no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, reason),
                ))
            options.append(('''
SHOOT_WOUND_OLD = '''            options = []
            if False:
                pass
            options.append(('''

FIGHT_WOUND_NEW = '''            options = []
            if free_no_effect > 0:
                options.append((
                    f"Re-roll failed wound rolls ({free_no_effect} dice)",
                    lambda: self._reroll_wound(free_no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, reason=reason),
                ))
            options.append(('''
FIGHT_WOUND_OLD = '''            options = []
            if False:
                pass
            options.append(('''

# --- the unreported one: the offer was not spent by being raised ------------
SPENT_NEW = '''        self._hit_reroll_used = True
        self.decision_manager.request(owner, f"{weapon_label}: {reason} - re-roll the Hit roll?", options)'''
SPENT_OLD = '''        self.decision_manager.request(owner, f"{weapon_label}: {reason} - re-roll the Hit roll?", options)'''

# ...and the fix put in the WRONG place. Spending the flag inside the automatic
# 1s path would also eat a later Monster Hunters offer, which has nothing to do
# with this ability.
MISPLACED_NEW = '''        self._pending_ones_reroll = {'''
MISPLACED_OLD = '''        self._hit_reroll_used = True
        self._pending_ones_reroll = {'''

# --- the label that names the wrong ability --------------------------------
LABEL_NEW = '''            label=f"Wound Roll (re-rolling {no_effect} failed): {weapon_label} {reason}",'''
LABEL_OLD = '''            label=f"Wound Roll (re-rolling {no_effect} failed): {weapon_label} [TWIN-LINKED]",'''

# --- the membership test itself, emptied ------------------------------------
EMPTY_NEW = '''    return reason in ONES_OR_WHOLE_LABELS'''
EMPTY_OLD = '''    return False'''

PROBES = [
    ("shooting's hit step suppresses the failures again",
     [(SHOOT, SHOOT_HIT_NEW, SHOOT_HIT_OLD)], SUITE),
    ("...and the same, against the Windriders suite",
     [(SHOOT, SHOOT_HIT_NEW, SHOOT_HIT_OLD)], WIND),
    ("fight's hit step suppresses the failures again",
     [(FIGHT, FIGHT_HIT_NEW, FIGHT_HIT_OLD)], SUITE),
    ("shooting's wound step suppresses the failures again",
     [(SHOOT, SHOOT_WOUND_NEW, SHOOT_WOUND_OLD)], SUITE),
    ("fight's wound step suppresses the failures again",
     [(FIGHT, FIGHT_WOUND_NEW, FIGHT_WOUND_OLD)], SUITE),
    ("THE UNREPORTED ONE: the offer is not spent by being made",
     [(SHOOT, SPENT_NEW, SPENT_OLD)], SUITE),
    ("...and the same, against the Windriders suite",
     [(SHOOT, SPENT_NEW, SPENT_OLD)], WIND),
    ("...and spent in the wrong place, where it would eat a later offer",
     [(SHOOT, SPENT_NEW, SPENT_OLD), (SHOOT, MISPLACED_NEW, MISPLACED_OLD)], SUITE),
    ("a melee wound re-roll names [TWIN-LINKED] whatever threw it",
     [(FIGHT, LABEL_NEW, LABEL_OLD)], SUITE),
    ("the membership test answers 'no' for everything",
     [(SCOPE, EMPTY_NEW, EMPTY_OLD)], SUITE),
    ("THE WHOLE PRE-FIX WORLD: all four call sites plus the unspent offer",
     [(SHOOT, SHOOT_HIT_NEW, SHOOT_HIT_OLD), (FIGHT, FIGHT_HIT_NEW, FIGHT_HIT_OLD),
      (SHOOT, SHOOT_WOUND_NEW, SHOOT_WOUND_OLD), (FIGHT, FIGHT_WOUND_NEW, FIGHT_WOUND_OLD),
      (SHOOT, SPENT_NEW, SPENT_OLD)], SUITE),
]


baselines = {}
for suite in (SUITE, WIND):
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-28s %d/%d" % (suite, got, total))
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
                print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
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
