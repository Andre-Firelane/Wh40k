"""A/B probes for "the board-edge lines as thick as the inner ones".

User: "bei den Aufstellungszonen gibt es an den spielfeldraendern sehr dicke
Linien. koennen die genau so dick sein wie die innenliegenden Linien?"

The change itself is one line, which is exactly why it needs probing: two pins
in test_deployment_zone_markings.py had to be TURNED AROUND (they asserted the
edge was the thicker of the two), and a turned-around pin is the case where you
most want proof that the new one measures something rather than agreeing with
whatever the source says.
"""

import io
import os
import re
import shutil
import subprocess
import sys

RENDERER = os.path.join("game", "renderer.py")
SUITE = "test_deployment_zone_markings.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run():
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


DERIVED = "BOARD_EDGE_LINE_WIDTH = DEPLOYMENT_ZONE_LINE_WIDTH"

PROBES = [
    ("the fat edge line back (THE REPORT)", DERIVED, "BOARD_EDGE_LINE_WIDTH = 5"),
    # The value is right, the FORM is not - and this is the probe that matters,
    # because a copy passes every measurement until someone tunes one of them.
    # Note the suite deliberately does NOT test this with `is`: CPython folds
    # equal float constants in a module into one object, so an identity check
    # would pass for exactly this world.
    ("the same width, but COPIED instead of derived", DERIVED,
     "BOARD_EDGE_LINE_WIDTH = 2.4"),
    # A hair apart reads as identical on screen and is still two numbers.
    ("nearly the same width - the drift this guards against", DERIVED,
     "BOARD_EDGE_LINE_WIDTH = 2.6"),
    # The ORIGINAL bug, restored faithfully: the shipped raw 5, not multiplied
    # by the render resolution. Written as the literal rather than by handing
    # the constant through raw, because the constant is a float now and pygame
    # REFUSES a float width - the probe would abort instead of going red, which
    # hides which claim broke (the lesson this repo has recorded nine times).
    ("the edge line unscaled again (the ORIGINAL bug)",
     "                                    self._ring_width(BOARD_EDGE_LINE_WIDTH))",
     "                                    5)"),
]

base, total, blob = run()
if base is None:
    print("BASELINE DID NOT RUN:\n" + blob[-1500:])
    raise SystemExit(2)
print(f"baseline: {base}/{total}\n")

bad = 0
for label, fixed, prefix in PROBES:
    src = read(RENDERER)
    if src.count(fixed) != 1:
        print(f"  SKIP     {label}: anchor not unique")
        bad += 1
        continue
    try:
        write(RENDERER, src.replace(fixed, prefix))
        got, tot, text = run()
        if got is None:
            print(f"  BITES    {label}: crashed - counts as red")
        elif got < base:
            print(f"  BITES    {label}: {got}/{tot}")
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:110]}")
                    break
        else:
            print(f"  NO BITE  {label}: {got}/{tot} - FINDING ABOUT THE TEST")
            bad += 1
    finally:
        write(RENDERER, src)

print()
print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
raise SystemExit(1 if bad else 0)
