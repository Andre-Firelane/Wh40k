"""A/B probes for "the map tiles are too tall and their text falls out".

User: "Die map kacheln sind sehr hoch. unten der text ist sehr gequetscht und
faellt teilweise raus. mach die kacheln etwas kleiner. dann hat der NEXT button
auch etwas mehr platz."

TWO faults in one report, so the probes take them apart one at a time - a
single "restore everything" probe would go red either way and prove neither
half is guarded:

  the text  - _text_height() reserved ONE name line while three of the four
              shipped maps wrap to two, putting the last line 3 px past the
              tile's own bottom edge and into the footer strip.
  the tile  - the preview box took "whatever is left over", so a tile filled
              the whole band whatever the boards actually needed. Measured at
              1920x1080: a 414x796 box for a tallest board that fills 565.

Section 3b of the suite is new, and a new section is exactly where you want
proof that it measures something rather than agreeing with whatever the source
currently says: 166 checks were green while the reported text sat outside its
tile.

Run: python ab_map_tile_height.py   (exclusively - it rewrites the source)
"""

import io
import os
import re
import shutil
import subprocess
import sys

TARGET = os.path.join("game", "ui", "map_select.py")
MAPS = os.path.join("game", "maps.py")
SUITE = "test_map_select.py"


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


# The three lines the fix turns on, each quoted exactly once in the source.
RESERVE = """        text_height = self._text_height(
            max((self._name_lines(m, tile_width) for m in page), default=1))"""
CAP = "        box_height = min(room, self._preview_box_height(box_width))"
CENTRE = "        block = ts.grid_block(area, per_page, len(page), tile_height)"

# The four shipped map names, and the same four cut to a word. Three of them
# wrap to two lines in a 446 px tile at 1920x1080 - that IS the reported fault
# - and with these none of them can.
MAP_NAMES = [
    'name="Take Cover (44\\"x60\\", portrait)",',
    'name="Landscape layout (60\\"x44\\")",',
    'name="Crucible (60\\"x44\\", corner deployment)",',
    'name="Sundered (60\\"x44\\", diagonal)",',
]
SHORT_NAMES = ['name="Cover",', 'name="Land",', 'name="Cruci",', 'name="Sund",']

# (file, anchor, replacement). Most probes rewrite the layout; the vacuity
# guard has to rewrite the MAPS, because the suite wraps the names itself and
# a shorter name in the drawing would leave what it measures untouched - which
# is exactly what the first version of that probe found out the hard way.
PROBES = [
    # THE REPORT, first half: one name line reserved again. Written as a call
    # with the argument dropped rather than by editing _text_height's default,
    # because that IS the shipped pre-fix world - the old call site passed
    # nothing at all.
    ("one name line reserved again (THE REPORT: text falls out)",
     TARGET, RESERVE, "        text_height = self._text_height()"),

    # THE REPORT, second half: the box eats the band again. This is the whole
    # of "die kacheln sind sehr hoch" - note it leaves the text reservation
    # correct, so whatever falls here falls for the HEIGHT and not for the
    # wrapping.
    ("the preview box takes whatever is left over (THE REPORT: tiles too tall)",
     TARGET, CAP, "        box_height = room"),

    # The cap is there but half-hearted - a tile that gives back only a
    # sliver still reads as too tall and still crowds the footer. The suite
    # must not accept "smaller by any amount".
    ("the box capped, but barely - only a sliver given back",
     TARGET, CAP, "        box_height = min(room, max(room - 40, self._preview_box_height(box_width)))"),

    # The cap the other way: a box shrunk past what the tallest board needs
    # would letterbox EVERY map, which is the opposite failure and the reason
    # the suite carries a counterweight beside the cap check.
    ("the box capped too hard - the tallest board no longer fills it",
     TARGET, CAP, "        box_height = min(room, self._preview_box_height(box_width) * 2 // 3)"),

    # Height given back but spent badly: the row nailed to the top of the band
    # with the whole void under it. ts.grid_block() exists for exactly this and
    # the suite has to notice when it is not used.
    ("the row pinned to the top of the band instead of centred",
     TARGET, CENTRE, "        block = area"),

    # ...and pinned to the BOTTOM, which passes "the tiles are smaller" and
    # "the row is not at the top" while taking back the clearance the footer
    # was the point of.
    ("the row pinned to the bottom, on top of the footer",
     TARGET, CENTRE,
     "        block = pygame.Rect(area.x, area.bottom - tile_height, area.width, tile_height)"),

    # THE VACUITY GUARD, and it has to rewrite the MAPS. Section 3b's text
    # checks all pass on a page whose names happen to fit one line - which is
    # the case the old reservation got RIGHT - so the section needs a liveness
    # line saying a shipped name really does wrap. Shortening the name in the
    # DRAWING does not test that: the suite calls wrap_text() itself, on the
    # real name, so it would go on measuring two lines while the tile drew one.
    # The first version of this probe did exactly that and came back NO BITE.
    ("every shipped map name short enough not to wrap "
     "(guard against a vacuous section)",
     MAPS, MAP_NAMES, SHORT_NAMES),
]

base, total, blob = run()
if base is None:
    print("BASELINE DID NOT RUN:\n" + blob[-1500:])
    raise SystemExit(2)
print(f"baseline: {base}/{total}\n")

bad = 0
for label, path, anchor, replacement in PROBES:
    src = read(path)
    anchors = anchor if isinstance(anchor, list) else [anchor]
    swaps = replacement if isinstance(replacement, list) else [replacement]
    if any(src.count(a) != 1 for a in anchors):
        print(f"  SKIP     {label}: anchor not unique "
              f"({[src.count(a) for a in anchors]})")
        bad += 1
        continue
    try:
        patched = src
        for a, b in zip(anchors, swaps):
            patched = patched.replace(a, b)
        write(path, patched)
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
        write(path, src)

# The whole pre-fix world at once, last, so the single-fault probes above have
# already said which half each check belongs to.
src = read(TARGET)
try:
    both = src.replace(RESERVE, "        text_height = self._text_height()")
    both = both.replace(CAP, "        box_height = room").replace(CENTRE, "        block = area")
    write(TARGET, both)
    got, tot, text = run()
    print(f"\n  the whole pre-fix world: {got}/{tot}"
          + ("" if got is None else f"  ({tot - got} red)"))
    if got is not None and got >= base:
        print("  NO BITE - FINDING ABOUT THE TEST")
        bad += 1
finally:
    write(TARGET, src)

print()
print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
raise SystemExit(1 if bad else 0)
