"""A/B probes for the dice-panel overflow and the crit badge, at the SOURCE.

Each restores one piece of the pre-fix world and reruns the suite. A probe that
does NOT go red is a finding about the test, not a clean bill of health.
"""

import io
import os
import re
import shutil
import subprocess
import sys

PANEL = os.path.join("game", "ui", "dice_panel.py")
SUITE = "test_crit_labels.py"


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


PROBES = [
    ("the row counted at DICE_GAP and laid out wider (THE REPORT)", PANEL,
     "        max_per_row = _max_per_row(text_max_width, row_gap)",
     "        max_per_row = _max_per_row(text_max_width, DICE_GAP)"),
    ("the gap not derived from the badge that is drawn", PANEL,
     "        width = self._crit_badge_width(crit_labels)\n"
     "        return max(DICE_GAP, width - DICE_SIZE + CRIT_LABEL_SEPARATION)",
     "        return 26"),
    ("the spacing leaking which dice are critical while they tumble", PANEL,
     "        if not crit_labels or not revealed:\n            return DICE_GAP",
     "        if not crit_labels:\n            return DICE_GAP"),
    ("a panel that never grows for a huge roll", PANEL,
     "    width = preferred\n    while width < available:",
     "    return preferred\n    width = preferred\n    while width < available:"),
    ("...and one that grows for every roll", PANEL,
     "    available = bounds_rect.width - 2 * BACKDROP_MARGIN\n"
     "    preferred = min(available, MAX_PANEL_WIDTH)",
     "    available = bounds_rect.width - 2 * BACKDROP_MARGIN\n"
     "    preferred = available"),
    ("the label back to loose text instead of a badge", PANEL,
     "        points = button_style.chamfer_points(badge, CRIT_LABEL_CHAMFER)\n"
     "        pygame.draw.polygon(surface, CRIT_LABEL_BG_COLOR, points)\n"
     "        pygame.draw.lines(surface, CRIT_LABEL_BORDER_COLOR, True, points, 1)",
     "        pass"),
    ("a badge with no edge on it", PANEL,
     "        pygame.draw.lines(surface, CRIT_LABEL_BORDER_COLOR, True, points, 1)",
     "        pass"),
    ("one plate PER LINE again instead of one per label", PANEL,
     "        badge_h = len(rendered) * line_h + 2 * CRIT_LABEL_PAD_Y",
     "        badge_h = line_h + 2 * CRIT_LABEL_PAD_Y"),
]

base, total, text = run()
if base is None:
    print("BASELINE DID NOT RUN:\n" + text[-2000:])
    raise SystemExit(2)
print(f"baseline: {base}/{total}\n")

bad = 0
for label, path, new, old in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print(f"  SKIP     {label}: anchor not unique in {path} ({src.count(new)})")
        bad += 1
        continue
    try:
        write(path, src.replace(new, old))
        got, tot, out = run()
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < base:
            verdict, detail = "BITES", f"{got}/{tot}"
        else:
            verdict, detail = "NO BITE", f"{got}/{tot} - FINDING ABOUT THE TEST"
            bad += 1
        print(f"  {verdict:8} {label}: {detail}")
        if got is not None and got < base:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:104]}")
                    break
    finally:
        write(path, src)

for root, dirs, _files in os.walk("."):
    for name in list(dirs):
        if name == "__pycache__":
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)
            dirs.remove(name)

print()
print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
raise SystemExit(1 if bad else 0)
