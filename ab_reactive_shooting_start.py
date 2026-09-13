"""A/B probes at the SOURCE for the reactive shooting start (game/shooting.py).

Each probe restores one clause of the pre-fix world and must make
test_reactive_shooting_start.py go RED. A probe that does not bite is a finding
about the TEST; a probe that makes the suite CRASH is one too (an aborted run
does not say which assurance broke), so it is counted as a failure here.

Every replacement carries the marker AB-PROBE. The probed file is hashed before
the run and must hash the same after every probe and at the end; afterwards
`git grep "AB-PROBE" -- . ":!ab_*.py"` must be empty.

Run EXCLUSIVELY: no suite, measurement, edit or commit alongside - a parallel
`git add -A` can capture a probed file mid-run (CLAUDE.md, error class 20).

Run: python ab_reactive_shooting_start.py
"""
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys

SHOOTING = os.path.join("game", "shooting.py")
SUITE = "test_reactive_shooting_start.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def digest(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def clear_pycache():
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


#: A probe that makes the suite HANG is a finding too, and the first run of
#: this file proved it can happen: the "flag never comes down" probe spun the
#: drain forever, the driver never got control back, and game/shooting.py was
#: left in the probed state until the processes were killed by hand. So every
#: suite run has a deadline, and output is line-buffered so a killed driver
#: still leaves a record of which probe it was on.
SUITE_TIMEOUT_S = 180
sys.stdout.reconfigure(line_buffering=True)


def run():
    clear_pycache()
    try:
        out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True,
                             timeout=SUITE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None, None, "HUNG: no result within %ds" % SUITE_TIMEOUT_S
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


NORMALIZE = """        if restrict_to is None:
            restrict = None
        elif hasattr(restrict_to, "models"):     # one unit, not a list of them
            restrict = [restrict_to]
        else:
            restrict = list(restrict_to) or None
"""
SHIPPED_LINE = "        restrict = list(restrict_to) if restrict_to else None  # AB-PROBE\n"

DEFER = """        if self._closing_activation:
            self._deferred_reactive.append((squad, restrict_to, on_finished))
            return True
"""
NO_DEFER = "        pass  # AB-PROBE\n"

FLAG_UP = """            self._closing_activation = True
            try:"""
NO_FLAG_UP = "            try:  # AB-PROBE"

FLAG_DOWN = """            finally:
                self._closing_activation = False"""
NO_FLAG_DOWN = """            finally:
                pass  # AB-PROBE"""

DRAIN_CALL = """            callback()
        self._open_deferred_reactive()"""
NO_DRAIN_CALL = "            callback()  # AB-PROBE"

DEAD_SKIP = """            if not any(not m.is_dead() for m in squad.models):
                continue
"""
NO_DEAD_SKIP = "            pass  # AB-PROBE\n"

NO_DRAIN_WHILE_CLOSING = """        if self._closing_activation:
            return
        while self._deferred_reactive and self.active_squad is None:"""
DRAIN_WHILE_CLOSING = """        while self._deferred_reactive and self.active_squad is None:  # AB-PROBE"""

REFUSAL_IDLE = """            self.active_squad = None
            self._reactive = False
            self._restrict_targets_to = None
            self._on_activation_finished = None
            return False"""
REFUSAL_SHIPPED = """            self._restrict_targets_to = None  # AB-PROBE
            return False"""

PROBES = [
    ("THE REPORT: restrict_to read as a list only", [(NORMALIZE, SHIPPED_LINE)]),
    ("opened inside the closing loop again (the wipe)", [(DEFER, NO_DEFER)]),
    ("the closing flag never goes up", [(FLAG_UP, NO_FLAG_UP)]),
    ("the closing flag never comes down", [(FLAG_DOWN, NO_FLAG_DOWN)]),
    ("queued starts are never opened", [(DRAIN_CALL, NO_DRAIN_CALL)]),
    ("the drain runs while the loop is still walking (the hang)",
     [(NO_DRAIN_WHILE_CLOSING, DRAIN_WHILE_CLOSING)]),
    ("a queued unit that has died is not skipped", [(DEAD_SKIP, NO_DEAD_SKIP)]),
    ("a refused start leaves the unit in active_squad", [(REFUSAL_IDLE, REFUSAL_SHIPPED)]),
    ("the whole pre-fix world", [(NORMALIZE, SHIPPED_LINE), (DEFER, NO_DEFER),
                                 (FLAG_UP, NO_FLAG_UP), (FLAG_DOWN, NO_FLAG_DOWN),
                                 (DRAIN_CALL, NO_DRAIN_CALL),
                                 (REFUSAL_IDLE, REFUSAL_SHIPPED)]),
]

ORIGINAL = read(SHOOTING)
ORIGINAL_HASH = digest(SHOOTING)
if "AB-PROBE" in ORIGINAL:
    print("REFUSED: %s already contains the AB-PROBE marker - a previous run was not "
          "restored" % SHOOTING)
    raise SystemExit(2)

base, total, text = run()
if base is None or base != total:
    print("BASELINE NOT GREEN (%s/%s):\n%s" % (base, total, text[-2000:]))
    raise SystemExit(2)
print("baseline: %s/%s\n" % (base, total))

bad = 0
try:
    for label, replacements in PROBES:
        src = ORIGINAL
        skipped = None
        for old, new in replacements:
            if src.count(old) != 1:
                skipped = "anchor found %d times: %r" % (src.count(old), old[:60])
                break
            src = src.replace(old, new)
        if skipped:
            print("  SKIP     %s: %s" % (label, skipped))
            bad += 1
            continue
        try:
            write(SHOOTING, src)
            got, tot, out = run()
        finally:
            write(SHOOTING, ORIGINAL)
        if digest(SHOOTING) != ORIGINAL_HASH:
            print("  ABORT    %s: %s did not restore byte-identically" % (label, SHOOTING))
            raise SystemExit(3)
        if got is None:
            print("  CRASHED  %s - the suite aborted instead of going red: FINDING ABOUT THE TEST"
                  % label)
            print("             " + (out.strip().splitlines() or ["?"])[-1][:110])
            bad += 1
        elif got < base:
            print("  BITES    %s: %s/%s" % (label, got, tot))
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:110])
                    break
        else:
            print("  NO BITE  %s: %s/%s - FINDING ABOUT THE TEST" % (label, got, tot))
            bad += 1
finally:
    write(SHOOTING, ORIGINAL)
    clear_pycache()

# CODE only: CLAUDE.md and its history name the marker in prose.
leftover = subprocess.run(["git", "grep", "-l", "AB-PROBE", "--", "*.py", ":!ab_*.py"],
                          capture_output=True, text=True).stdout.strip()
print()
if digest(SHOOTING) != ORIGINAL_HASH or leftover:
    print("RESTORE CHECK FAILED - hash changed or marker left in: %s" % (leftover or SHOOTING))
    raise SystemExit(3)
print("restored byte-identically; no AB-PROBE marker outside ab_*.py")
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
