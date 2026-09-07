"""A/B probes for the detachment-Stratagem reader and tooltip, at the SOURCE.

Each restores one piece of the pre-fix world and reruns the suite. A probe that
does NOT go red is a finding about the test, not a clean bill of health.
"""

import io
import os
import re
import shutil
import subprocess
import sys

RULES = os.path.join("game", "rules_text.py")
OVERLAY = os.path.join("game", "ui", "army_rules_overlay.py")
PANEL = os.path.join("game", "ui", "action_panel.py")
TIP = os.path.join("game", "ui", "stratagem_tooltip.py")
MAIN = "main.py"
SUITE = "test_stratagem_tooltip.py"


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
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


PROBES = [
    ("the reader stopping at the detachment RULE (the report)", OVERLAY,
     "        blocks.extend(_stratagem_blocks(\n"
     "            rules_text.detachment_stratagems(entry.faction_keyword, detachment)))",
     "        pass"),
    ("no Stratagems section reader at all", RULES,
     '    body = _section_named(path, "Stratagems")\n    if not body:\n        return []',
     '    body = None\n    if not body:\n        return []'),
    ("shortened names not resolved (exact match only)", RULES,
     "    suffixed = [s for s in candidates if _normalise(s.name).endswith(wanted)]\n"
     "    return suffixed[0] if len(suffixed) == 1 else None",
     "    return None"),
    ("an AMBIGUOUS suffix guessing instead of refusing", RULES,
     "    return suffixed[0] if len(suffixed) == 1 else None",
     "    return suffixed[0] if suffixed else None"),
    ("italic subtitles left as literal asterisks", RULES,
     '    match = _SUBTITLE_LINE.match(line)\n    if match:\n'
     '        return RuleLine("subtitle", _runs(match.group(1)), starts_block=starts_block)',
     "    match = None"),
    ("the panel not recording its Stratagem buttons", PANEL,
     "            self._stratagem_buttons.append((drawn, _stratagem_name_in(label)))",
     "            pass"),
    ("a tooltip that opens on CONTACT rather than on a dwell", PANEL,
     "        dwelt = (self._tip_since is not None\n"
     "                 and now_ms - self._tip_since >= STRATAGEM_TIP_DELAY_MS)",
     "        dwelt = True"),
    ("the dwell keyed on the rect, which is rebuilt every frame", PANEL,
     "        if name != self._tip_name or moved:",
     "        if name is not self._tip_name or moved:"),
    ("an empty box for a Stratagem with no printed entry", TIP,
     "        if not blocks:\n            self.last_rect = None\n            return None",
     "        if not blocks:\n            blocks = [rules_body.Block('note', '')]"),
    ("main() not polling the tooltip", MAIN,
     "        _tip_name = action_panel.update_tooltip(",
     "        _tip_name = None or (lambda *a, **k: None)("),
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
