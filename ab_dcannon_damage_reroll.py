"""A/B probes for the 2026-09-08 D-cannon report, at the SOURCE.

  "absturz im letzten spiel / feuern der d-cannon"
  AttributeError: 'function' object has no attribute 'add'

TWO defects on one weapon, found by reproducing the one that was reported.

  1. THE CRASH. This repo runs two logging idioms told apart only by the field
     NAME - `self.game_log` is the OBJECT (.add(msg), ~90 controllers) and
     `self.log` is a CALLABLE (log(msg), four modules). The automatic Damage
     re-roll branch was written in the first idiom against a field holding the
     second. It shipped because the D-cannon's Structural Collapse is the only
     ability that can reach that branch, so the line had never run once.

  2. THE UNEARNED RE-ROLL, measured while reproducing #1. "If that attack
     targets a TITANIC unit, you can re-roll the Damage roll INSTEAD" is gated
     on the target; the offer was built with a decision_manager unconditionally,
     so every D-cannon roll that was NOT a 1 opened a free-re-roll prompt the
     rule never granted - and the session parked on it, so the damage never
     landed at all (measured: 0 instead of 6). The predicate written for
     exactly this, structural_collapse.targets_titanic(), had no caller.

Each probe restores one half of the pre-fix world and has to make its suite red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

DR = os.path.join("game", "damage_resolution.py")
SHOOT = os.path.join("game", "shooting.py")
NR = os.path.join("game", "notation_reroll.py")

PLATFORMS = "test_support_weapon_platforms.py"
WIRING = "test_event_chain_wiring.py"
SUNFORGE = "test_sunforge.py"


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


# ------------------------------------------------------------- 1. the crash
LOG_NEW = '''                self.log("%s: re-rolling %s's Damage roll of 1."
                         % (self.damage_reroll.label, self.weapon.name))'''
LOG_OLD = '''                self.log.add("%s: re-rolling %s's Damage roll of 1."
                             % (self.damage_reroll.label, self.weapon.name))'''

# The caller half of the same contract, from the other end: hand the session
# the GameLog OBJECT. Behaviour is untouched until a line actually logs, which
# is precisely why it needs a source guard.
CTOR_NEW = "log=self._log, priority_group=priority_group,"
CTOR_OLD = "log=self.game_log, priority_group=priority_group,"

# ------------------------------------------------- 2. the unearned re-roll
GATE_NEW = '''                titanic = structural_collapse.targets_titanic(target_squad)
                damage_reroll = DamageRerollOffer(
                    structural_collapse.STRUCTURAL_COLLAPSE_LABEL,
                    automatic_faces=(() if titanic
                                     else structural_collapse.STRUCTURAL_COLLAPSE_AUTOMATIC_FACES),
                    offerable=titanic,
                    notation=weapon.damage_notation, **common,
                )'''
GATE_OLD = '''                damage_reroll = DamageRerollOffer(
                    structural_collapse.STRUCTURAL_COLLAPSE_LABEL,
                    automatic_faces=structural_collapse.STRUCTURAL_COLLAPSE_AUTOMATIC_FACES,
                    notation=weapon.damage_notation, **common,
                )'''

# The flag is built but never read - this repo's own "built, never fed" class.
READ_NEW = "        if self.decision_manager is None or not self.offerable or not self.can_offer():"
READ_OLD = "        if self.decision_manager is None or not self.can_offer():"

# ...and the mirror: the default must stay True, or the four abilities that
# ARE plain offers (Sunforge, Breath of Vaul, Assured Destruction) go silent.
DEFAULT_NEW = 'roll_name="Damage", offerable=True):'
DEFAULT_OLD = 'roll_name="Damage", offerable=False):'


PROBES = [
    ("the callable log is used as the GameLog object (THE CRASH)",
     [(DR, LOG_NEW, LOG_OLD)], PLATFORMS),
    ("...and the source guard sees it too",
     [(DR, LOG_NEW, LOG_OLD)], WIRING),
    ("a session is handed the GameLog object instead of a callable",
     [(SHOOT, CTOR_NEW, CTOR_OLD)], WIRING),
    ("the TITANIC gate is gone - a free re-roll on every shot",
     [(SHOOT, GATE_NEW, GATE_OLD)], PLATFORMS),
    ("the offerable flag is built but never read",
     [(NR, READ_NEW, READ_OLD)], PLATFORMS),
    ("offerable defaults to False - the plain offers go silent",
     [(NR, DEFAULT_NEW, DEFAULT_OLD)], SUNFORGE),
    ("the WHOLE pre-fix world",
     [(DR, LOG_NEW, LOG_OLD), (SHOOT, GATE_NEW, GATE_OLD)], PLATFORMS),
]


baselines = {}
for suite in (PLATFORMS, WIRING, SUNFORGE):
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
                print("  SKIP     %s: anchor not unique in %s" % (label, path))
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
        print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:112])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
