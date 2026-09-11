"""A/B probes for the 2026-09-11 Explosives report, at the SOURCE.

  "explosives geht nur vor dem schiessen, weil man eligible to shoot sein
   muss. ich konnte es aber nach dem schiessen machen."

The user is right, and the printed card settles it - it just was not in the
repo. rules/*/*.md holds datasheets, army rules and detachments only; the core
Stratagems survive as tooltips inside rules/.cache/<faction>.html, where 15.05
reads "One friendly unengaged EXPLOSIVES / GRENADES unit that is eligible to
shoot and did not make an advance move this turn."

game/explosives.py's can_use() stopped at available_shooting_types() - rule
10.02 step 2, which knows nothing about having already shot - and never
consulted ShootingController. It was not even given one. The old docstring
documented that as a deliberate reading, and CLAUDE.history.md:150 records it
as a guess made "mangels weiterer Regeltexte".

Each probe restores one piece of the pre-fix world and has to make its suite
red - RED, not crashed: probe 1 carries a function-local import precisely so
that removing the module-level one does not turn a finding into a traceback.
"""

import io
import os
import re
import shutil
import subprocess
import sys

EXPL = os.path.join("game", "explosives.py")
MAIN = "main.py"

SUITE = "test_explosives.py"
WIRING = "test_event_chain_wiring.py"


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


# ------------------------------------- 1. the gate stops asking who has shot
GATE_NEW = """        if self.shooting_controller.active_squad is squad:
            return False
        if not self.shooting_controller.can_shoot(squad):
            return False"""
# The function-local import is what keeps this a RED result instead of an
# ImportError: the module-level one went away with the fix.
GATE_OLD = """        from game.shooting import available_shooting_types
        if not available_shooting_types(squad, self.all_tokens, self.movement_controller):
            return False"""

# ---------------------------------- 2. only the mid-activation guard is gone
MID_NEW = """        if self.shooting_controller.active_squad is squad:
            return False
        if not self.shooting_controller.can_shoot(squad):"""
MID_OLD = """        if not self.shooting_controller.can_shoot(squad):"""

# --------------------------------------- 3. ownership goes back to the flag
OWNER_NEW = "            if squad.owner != self.turn_tracker.turn_owner:"
OWNER_OLD = "            if squad.owner != self.turn_tracker.active_player:"

# ------------------------------- 4. main.py stops handing over the collaborator
# Must go RED rather than crash: the constructor default is None, so main()
# still builds and can_use() simply refuses forever. That silent no-op is
# exactly what section 22 exists to catch, and no behaviour test can see it.
WIRE_NEW = """        shooting_controller=shooting_controller,
    )"""
WIRE_OLD = """    )"""

# ------------------------------------ 5. the printed text loses its provenance
DOC_NEW = "    in the repo: rules/.cache/orks.html, in the Core Stratagems block that"
DOC_OLD = "    in the repo: somewhere on the internet, in the Core Stratagems block that"

# --------------------------------------------- 6. the whole pre-fix world
# The gate, the ownership flag and the collaborator, all at once - what the
# module actually shipped as.
WHOLE_NEW = """        if squad is None or self.state != IDLE or self.shooting_controller is None:"""
WHOLE_OLD = """        if squad is None or self.state != IDLE:"""


PROBES = [
    ("the gate stops asking who has already shot", [(EXPL, GATE_NEW, GATE_OLD)], SUITE),
    ("only the mid-activation guard is removed", [(EXPL, MID_NEW, MID_OLD)], SUITE),
    ("ownership goes back to active_player", [(EXPL, OWNER_NEW, OWNER_OLD)], SUITE),
    ("main.py stops passing shooting_controller", [(MAIN, WIRE_NEW, WIRE_OLD)], WIRING),
    ("the printed text loses its provenance", [(EXPL, DOC_NEW, DOC_OLD)], SUITE),
    ("THE WHOLE PRE-FIX WORLD",
     [(EXPL, GATE_NEW, GATE_OLD), (EXPL, OWNER_NEW, OWNER_OLD),
      (EXPL, WHOLE_NEW, WHOLE_OLD)], SUITE),
]

print(__doc__.strip())
print()
baselines = {}
for _suite in sorted({p[2] for p in PROBES}):
    got, total, _t = run(_suite)
    baselines[_suite] = got
    print("BASELINE %-32s %s/%s" % (_suite, got, total))
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
                    print("             " + line.strip()[:110])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
