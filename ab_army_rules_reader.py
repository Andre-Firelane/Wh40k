"""A/B probes for the army-rules reader, at the SOURCE.

Each probe restores one piece of the pre-fix world and reruns
test_army_rules_overlay.py. A probe that does NOT go red is a finding about
the test, not a clean bill of health - this repo has hit that four times.

The first probe is the load-bearing one: it puts back the catch-all
MOUSEBUTTONDOWN dismiss and feeds the reader the event PAIR pygame really
delivers for one wheel notch. That is the reported bug, and it is also the
reason 58 green checks never saw it - they all sent a bare MOUSEWHEEL.
"""

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

OVERLAY = os.path.join("game", "ui", "army_rules_overlay.py")
PANEL = os.path.join("game", "ui", "game_status_panel.py")
RULES = os.path.join("game", "rules_text.py")
SUITE = "test_army_rules_overlay.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite=SUITE):
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    if not match:
        return None, None, text
    return int(match.group(1)), int(match.group(2)), text


PROBES = [
    (
        "the catch-all MOUSEBUTTONDOWN dismiss (THE REPORTED BUG)",
        OVERLAY,
        "if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:",
        "if event.type == pygame.MOUSEBUTTONDOWN:",
    ),
    (
        "no keyboard scrolling",
        OVERLAY,
        "            step = _KEY_SCROLL.get(event.key)",
        "            step = None",
    ),
    (
        "the un-capped text column (151 characters a line)",
        OVERLAY,
        "        width = min(width, MAX_TEXT_WIDTH + chrome)",
        "        width = width",
    ),
    (
        "everything rendered as flat body text",
        OVERLAY,
        "        out.append(Block(line.kind, text, runs=line.runs, label=line.label,\n"
        "                         cells=line.cells, new_para=line.starts_block))",
        "        out.append(Block('text', text))",
    ),
    (
        "inline bold discarded at the parser",
        RULES,
        "        if piece:\n            out.append((_fold(piece), bool(index % 2)))",
        "        if piece:\n            out.append((_fold(piece), False))",
    ),
    (
        "one shared link instead of one per player",
        PANEL,
        "            for tile, (player, _keyword, _path) in zip((left_tile, right_tile), badges):",
        "            for tile, (player, _keyword, _path) in list(zip((left_tile, right_tile), badges))[:1]:",
    ),
    (
        "the reader opening on BOTH armies again",
        OVERLAY,
        "    if not armies or player not in armies:\n        return []",
        "    if not armies:\n        return []\n"
        "    player = sorted(armies)[0] if player not in armies else player",
    ),
]

base_pass, base_total, base_text = run()
if base_pass is None:
    print("BASELINE DID NOT RUN:\n" + base_text[-2000:])
    raise SystemExit(2)
print(f"baseline: {base_pass}/{base_total}\n")

failures = 0
for label, path, new, old in PROBES:
    source = read(path)
    if source.count(new) != 1:
        print(f"  SKIP  {label}: anchor not found exactly once in {path}")
        failures += 1
        continue
    backup = source
    try:
        write(path, source.replace(new, old))
        got, total, text = run()
        if got is None:
            verdict, detail = "BITES", "(the suite crashed - counts as red)"
        elif got < base_pass:
            verdict, detail = "BITES", f"{got}/{total}"
        else:
            verdict, detail = "NO BITE", f"{got}/{total} - FINDING ABOUT THE TEST"
            failures += 1
        print(f"  {verdict:8} {label}: {detail}")
        if verdict == "BITES" and got is not None:
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:110]}")
                    break
    finally:
        write(path, backup)

for root, dirs, _files in os.walk("."):
    for name in list(dirs):
        if name == "__pycache__":
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)
            dirs.remove(name)

print()
print("all probes bite" if not failures else f"{failures} probe(s) did not bite")
raise SystemExit(1 if failures else 0)
