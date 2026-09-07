"""A/B probes for the Aeldari panel-button suite, at the SOURCE.

test_aeldari_stratagem_ui.py is a NEW file, and a new suite owes proof that it
bites. These probes attack the PANEL PATH specifically - the one no existing
probe in this repo touches, because until now no test passed
`proactive_stratagems=` to ActionPanel.draw() at all.

Each restores one piece of a plausible broken world and reruns the suite. A
probe that does NOT go red is a finding about the test, not a clean bill of
health.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
MAIN = "main.py"
REG = os.path.join("game", "proactive_stratagems.py")
PANEL = os.path.join("game", "ui", "action_panel.py")
SUITE = "test_aeldari_stratagem_ui.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    # The probes rewrite modules within the same second - the documented
    # __pycache__ race that has produced phantom failures in this repo.
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


PROBES = [
    # THE DEAD WIRING. main.py builds the registry, registers nineteen
    # controllers on it, and never hands it to the panel - so every button is
    # correct and none is on screen. This is literally what happened to
    # overflight_controller for two batches.
    ("main.py never hands the registry to the panel", MAIN,
     "            proactive_stratagems=proactive_stratagems,",
     "            proactive_stratagems=None,",
     SUITE),

    # THE GATE IGNORED. Every registered Stratagem drawn in every phase - the
    # world in which section 2's matrix is satisfied by "offered always" and
    # section 3's detachment gate never bites.
    ("buttons_for() ignoring can_use()", REG,
     "        return [c for c in self.controllers if c.can_use(squad)]",
     "        return list(self.controllers)",
     SUITE),

    # THE OPPOSITE. Nothing usable ever - the world in which every negative
    # passes and no positive does, which proves the negatives are not what is
    # carrying the file.
    ("usable_for() returning nothing at all", REG,
     "        return [c for c in self.controllers if c.can_use(squad)]",
     "        return []",
     SUITE),

    # ONE REGISTRATION UNWRAPPED. The controller is still built and still
    # correct; it is simply not on the registry - so exactly one row of the
    # matrix and section 8's set difference have to name it.
    ("Seer's Eye built but not registered", MAIN,
     "    seers_eye_controller = proactive_stratagems.add(SeersEyeController(",
     "    seers_eye_controller = (SeersEyeController(",
     SUITE),

    # THE SECOND HANDLE. _stratagem_buttons is what makes "drawn with the
    # Stratagem accent" measurable without a pixel scan; with the recording
    # gone the labels still come out of the spy, so this probe proves the two
    # handles are independent rather than one reading the other.
    ("the accent='stratagem' recording removed", PANEL,
     "            self._stratagem_buttons.append((drawn, _stratagem_name_in(label)))",
     "            pass",
     SUITE),
]

got, total, text = run(SUITE)
if got is None:
    print("BASELINE DID NOT RUN:" + NL + text[-2000:])
    raise SystemExit(2)
BASE = got
print("baseline %-42s %s/%s" % (SUITE, got, total))
print()

bad = 0
for label, path, new, old, suite in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
        bad += 1
        continue
    try:
        write(path, src.replace(new, old))
        got, tot, out = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < BASE:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < BASE:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:104])
                    break
    finally:
        write(path, src)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
