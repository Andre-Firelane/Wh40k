"""A/B probes for the turquoise Agile Manoeuvre colour code.

Each probe restores ONE piece of the pre-fix world AT THE SOURCE, runs
test_battle_focus.py, and reports how many checks fall. A probe that does not
bite is a finding about the TEST, not proof the code is fine (this repo has hit
that a dozen times) - so every one of them is expected to go red here.

__pycache__ is cleared between runs: these probes write and restore inside the
same second, which is the documented race that once made a whole run report the
previous pass's failures.
"""

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

PANEL = os.path.join(ROOT, "game", "ui", "action_panel.py")
OVERLAY = os.path.join(ROOT, "game", "ui", "decision_overlay.py")
POOL = os.path.join(ROOT, "game", "battle_focus.py")
STYLE = os.path.join(ROOT, "game", "ui", "button_style.py")


def clear_pycache():
    for dirpath, dirnames, _ in os.walk(ROOT):
        for name in list(dirnames):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, name), ignore_errors=True)
                dirnames.remove(name)


def run_suite():
    clear_pycache()
    proc = subprocess.run(
        [sys.executable, "test_battle_focus.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    match = re.search(r"(\d+)/(\d+) checks passed", proc.stdout)
    if not match:
        return None, None, proc.stdout[-600:]
    passed, total = int(match.group(1)), int(match.group(2))
    first_fail = ""
    for line in proc.stdout.splitlines():
        if "FAIL:" in line:
            first_fail = line.strip()
            break
    return passed, total, first_fail


def probe(name, edits):
    """edits: [(path, old, new), ...] applied together, then reverted."""
    originals = {}
    try:
        for path, old, new in edits:
            if path not in originals:
                originals[path] = io.open(path, encoding="utf-8").read()
            src = io.open(path, encoding="utf-8").read()
            assert src.count(old) == 1, f"{name}: anchor not unique in {path}"
            io.open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
        passed, total, note = run_suite()
    finally:
        for path, text in originals.items():
            io.open(path, "w", encoding="utf-8").write(text)
        clear_pycache()
    if passed is None:
        print(f"  {name}: SUITE CRASHED (also a bite)\n    {note}")
        return True
    fell = total - passed
    verdict = "BITES" if fell else "*** DID NOT BITE ***"
    print(f"  {name}: {passed}/{total}  ({fell} fell)  {verdict}")
    if note:
        print(f"    first: {note}")
    return bool(fell)


print("baseline:")
base_passed, base_total, base_note = run_suite()
print(f"  {base_passed}/{base_total}" + (f"  {base_note}" if base_note else ""))
assert base_passed == base_total, "baseline is not green - fix that before reading the probes"

print("\nprobes:")
results = []

results.append(probe(
    "1. Movement-phase manoeuvre buttons back to Stratagem violet",
    [(PANEL,
      'surface, bf_rect, f"{label}  ({tokens_left} token(s))", accent="battle_focus",',
      'surface, bf_rect, f"{label}  ({tokens_left} token(s))", accent="stratagem",')],
))

results.append(probe(
    "2. Sudden Strike back to Stratagem violet",
    [(PANEL,
      '''                    f"Sudden Strike - Pile-in/Consolidate 6\\"  ({tokens_left} token(s))",
                    accent="battle_focus",''',
      '''                    f"Sudden Strike - Pile-in/Consolidate 6\\"  ({tokens_left} token(s))",
                    accent="stratagem",''')],
))

results.append(probe(
    "3. the pool stops flagging its offer (heading falls back to gold)",
    [(POOL,
      '''            options,
            is_battle_focus=True,
        )''',
      '''            options,
        )''')],
))

results.append(probe(
    "4. the overlay ignores the accent (old is_stratagem-only branch)",
    [(OVERLAY,
      '''        border_color, player_color = ACCENT_COLORS.get(
            getattr(decision_manager, "accent", None), ACCENT_COLORS[None])''',
      '''        border_color = STRATAGEM_BOX_BORDER_COLOR if decision_manager.is_stratagem else BOX_BORDER_COLOR
        player_color = STRATAGEM_PLAYER_COLOR if decision_manager.is_stratagem else PLAYER_COLOR''')],
))

results.append(probe(
    "5. the palette entry is gone (accent silently falls back to blue)",
    [(STYLE,
      '''    "battle_focus": (
        BG_NORMAL_BATTLE_FOCUS, BG_HOVER_BATTLE_FOCUS, BG_ACTIVE_BATTLE_FOCUS,
        BORDER_NORMAL_BATTLE_FOCUS, BORDER_HOVER_BATTLE_FOCUS, BORDER_ACTIVE_BATTLE_FOCUS,
        TEXT_NORMAL_BATTLE_FOCUS, TEXT_HOVER_BATTLE_FOCUS,
    ),
}''',
      "}")],
))

results.append(probe(
    "6. turquoise nudged to be indistinguishable from the default blue",
    [(STYLE,
      "BORDER_NORMAL_BATTLE_FOCUS = (64, 224, 208)",
      "BORDER_NORMAL_BATTLE_FOCUS = (62, 160, 206)")],
))

results.append(probe(
    "7. the WHOLE pre-fix world (buttons violet, no flag, old overlay branch)",
    [(PANEL,
      'surface, bf_rect, f"{label}  ({tokens_left} token(s))", accent="battle_focus",',
      'surface, bf_rect, f"{label}  ({tokens_left} token(s))", accent="stratagem",'),
     (PANEL,
      '''                    f"Sudden Strike - Pile-in/Consolidate 6\\"  ({tokens_left} token(s))",
                    accent="battle_focus",''',
      '''                    f"Sudden Strike - Pile-in/Consolidate 6\\"  ({tokens_left} token(s))",
                    accent="stratagem",'''),
     (POOL,
      '''            options,
            is_battle_focus=True,
        )''',
      '''            options,
        )'''),
     (OVERLAY,
      '''        border_color, player_color = ACCENT_COLORS.get(
            getattr(decision_manager, "accent", None), ACCENT_COLORS[None])''',
      '''        border_color = STRATAGEM_BOX_BORDER_COLOR if decision_manager.is_stratagem else BOX_BORDER_COLOR
        player_color = STRATAGEM_PLAYER_COLOR if decision_manager.is_stratagem else PLAYER_COLOR''')],
))

print("\n%d of %d probes bit." % (sum(1 for r in results if r), len(results)))
sys.exit(0 if all(results) else 1)
