"""A/B probes for the two Aeldari end-of-phase windows, at the SOURCE.

Both Stratagems were a guaranteed, silent no-op: NEVER offered, in any game.
Each expressed its printed WHEN as a LIVE clock read, and main.py runs those
offers AFTER turn_tracker.advance_phase() - so the clock has already moved on.
The same shape and the same cause as Wall of Mirrors and Cost of Victory
before them, which is why game/phase_window.py exists.

  * Skyborne Sanctuary (BOTH printings, Warhost and Aspect Host) read
    `phase != PHASE_FIGHT`, and Fight is the last phase, so at the offer the
    clock had rolled all the way round to Command.
  * Overflight was dead THREE times over: the same live clock read; a
    reset_phase() that CLEARED the kill ledger the offer was about to read
    (main.py's per-phase reset block runs before that boundary's own offers);
    and a killerless death dropped on the floor, which is the ordinary case
    when the last weapon group of an activation wipes a unit.

Each probe restores ONE of those, and the last two restore whole pre-fix
worlds - error class 16: half a pre-fix world proves nothing, and two halves
that mask each other prove less than that. A probe that does NOT go red is a
finding about the test, not a clean bill of health.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
MAIN = "main.py"
SKY = os.path.join("game", "skyborne_sanctuary.py")
OVER = os.path.join("game", "windrider_overflight.py")
SUITE = "test_aeldari_detachment_stratagems.py"
WIRING = "test_event_chain_wiring.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


# (label, [(path, new, old), ...], suite) - a list so one probe can restore
# several pieces of the same pre-fix world at once.
PROBES = [
    ("Skyborne back on a live phase test",
     [(SKY, "        if not self._window.is_open(squad.owner):",
       "        if self.turn_tracker is not None and self.turn_tracker.phase != 'Fight':")],
     SUITE),

    ("Skyborne's window never armed",
     [(SKY, "            self._window.arm(squad.owner)", "            pass")],
     SUITE),

    ("Skyborne's reset_phase() a no-op (the stale prompt)",
     [(SKY, "        the per-phase reset block, which runs BEFORE that boundary's offers.\"\"\""
       + NL + "        self._window.close()",
       "        the per-phase reset block, which runs BEFORE that boundary's offers.\"\"\""
       + NL + "        pass")],
     SUITE),

    ("main.py never resets the Skyborne windows",
     [(MAIN, "            _skyborne.reset_phase()", "            pass")],
     WIRING),

    ("Overflight back on a live phase test",
     [(OVER, "        if not self._window.is_open(squad.owner):",
       "        if self.turn_tracker is None or self.turn_tracker.phase != 'Fight':")],
     SUITE),

    ("Overflight's reset_phase() back to clearing the ledger",
     [(OVER, "        self._killers_ending_phase = self._killers_this_phase",
       "        self._killers_ending_phase = set()")],
     SUITE),

    ("Overflight dropping a killerless death again",
     [(OVER, "            self._owed.append(dead_squad)" + NL + "            return False",
       "            return False")],
     SUITE),

    ("main.py never settles Overflight's owed kills",
     [(MAIN, "        overflight_controller.credit_owed_kills(shooter_squad)", "        pass"),
      (MAIN, "            overflight_controller.credit_owed_kills(_fighter)", "            pass")],
     SUITE),

    # THE WHOLE PRE-FIX WORLD, both halves at once. Restoring only one leaves
    # the other still fixed, and a half-restored world is the trap CLAUDE.md
    # records as error class 16.
    ("the ENTIRE pre-fix Skyborne (live clock, no window, no reset)",
     [(SKY, "        if not self._window.is_open(squad.owner):",
       "        if self.turn_tracker is not None and self.turn_tracker.phase != 'Fight':"),
      (SKY, "            self._window.arm(squad.owner)", "            pass"),
      (MAIN, "            _skyborne.reset_phase()", "            pass")],
     SUITE),

    ("the ENTIRE pre-fix Overflight (live clock, clearing reset, dropped kill)",
     [(OVER, "        if not self._window.is_open(squad.owner):",
       "        if self.turn_tracker is None or self.turn_tracker.phase != 'Fight':"),
      (OVER, "        self._killers_ending_phase = self._killers_this_phase",
       "        self._killers_ending_phase = set()"),
      (OVER, "            self._owed.append(dead_squad)" + NL + "            return False",
       "            return False")],
     SUITE),
]

BASE = {}
for _suite in (SUITE, WIRING):
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:%s%s" % (_suite, NL, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = got
    print("baseline %-42s %s/%s" % (_suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {path: read(path) for path, _, _ in edits}
    ok = True
    for path, new, old in edits:
        src = read(path)
        if src.count(new) != 1:
            print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
            ok = False
            break
        write(path, src.replace(new, old))
    try:
        if not ok:
            bad += 1
            continue
        got, tot, out = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < BASE[suite]:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < BASE[suite]:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:104])
                    break
    finally:
        for path, text in originals.items():
            write(path, text)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
