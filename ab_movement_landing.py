"""A/B probes for the landing-spot search (ai/agent_driver._free_landing_near),
at the SOURCE. Each probe restores ONE clause of the pre-fix world in
ai/agent_driver.py, runs test_landing_search.py, and must make it red; the
last one restores the whole pre-fix world (the clamp truncating at the first
friendly base on the line) and additionally has to send measure_reported_moves.py
case C back from 3.80" to its old 2.71".

A probe that does not bite is a finding about the TEST, not a pass.

Run: python ab_movement_landing.py
"""
import io
import os
import re
import shutil
import subprocess
import sys

DRIVER = os.path.join("ai", "agent_driver.py")
SUITE = "test_landing_search.py"
FIXTURES = "measure_reported_moves.py"


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


def run(script, *args):
    clear_cache()
    out = subprocess.run([sys.executable, script, *args], capture_output=True, text=True)
    return out.stdout + out.stderr


def suite_result(text):
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)


def case_c(text):
    match = re.search(r"C: progress ([\d.]+)\"", text)
    return float(match.group(1)) if match else None


PROBES = [
    ("the whole search returns None (the clamp's old truncation everywhere)",
     "    if caller in LANDING_SEARCH_OFF_FOR or caller in _LANDING_SEARCH_EXCLUDED:\n        return None\n",
     "    if caller in LANDING_SEARCH_OFF_FOR or caller in _LANDING_SEARCH_EXCLUDED or True:\n        return None\n"),
    ("the lateral penalty is gone (sideways costs the same as short)",
     "_LANDING_LATERAL_WEIGHT = 1.0\n",
     "_LANDING_LATERAL_WEIGHT = 0.0\n"),
    ("the route walker is no longer excluded",
     "_LANDING_SEARCH_EXCLUDED = frozenset({\"route\", \"engagement-step\"})\n",
     "_LANDING_SEARCH_EXCLUDED = frozenset({\"engagement-step\"})\n"),
    ("the engagement step is no longer excluded (a piling-in model re-lands out of range)",
     "_LANDING_SEARCH_EXCLUDED = frozenset({\"route\", \"engagement-step\"})\n",
     "_LANDING_SEARCH_EXCLUDED = frozenset({\"route\"})\n"),
    ("the coherency preference is gone (any legal spot, nearest first)",
     "        if not anchors:\n            return True\n        return any(",
     "        if not anchors or True:\n            return True\n        return any("),
    ("the caller's per-model cap is ignored",
     "    if max_travel is not None:\n        budget = min(budget, max_travel)\n",
     "    if max_travel is not None and False:\n        budget = min(budget, max_travel)\n"),
    ("rule 13.05 is not asked (a spot on a wall counts as a landing)",
     "        if model_terrain_violation(model, obstacles, x, y):\n            return False\n        for t in blockers:",
     "        if model_terrain_violation(model, obstacles, x, y) and False:\n            return False\n        for t in blockers:"),
    ("the disallowed-enemy clause is gone (a Normal move may land beside an enemy)",
     "    keep_out = [t for t in blockers if t.squad in disallowed]\n",
     "    keep_out = []\n"),
    ("the per-caller switch is dead",
     "    if caller in LANDING_SEARCH_OFF_FOR or caller in _LANDING_SEARCH_EXCLUDED:\n        return None\n",
     "    if False:\n        return None\n"),
]

original = read(DRIVER)
bad = 0
try:
    base_text = run(SUITE)
    base = suite_result(base_text)
    print(f"baseline {SUITE}: {base[0]}/{base[1]}")
    for label, old, new in PROBES:
        if original.count(old) != 1:
            print(f"  PROBE SKIPPED (anchor not found exactly once): {label}")
            bad += 1
            continue
        write(DRIVER, original.replace(old, new))
        try:
            got, total = suite_result(run(SUITE))
        finally:
            write(DRIVER, original)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < base[0]:
            verdict, detail = "BITES", f"{got}/{total}"
        else:
            verdict, detail = "NO BITE", f"{got}/{total} - FINDING ABOUT THE TEST"
            bad += 1
        print(f"  {verdict:8s} {label}: {detail}")

    # The whole pre-fix world, measured where the report was: the blob.
    old_seam = ("    if radius is None or radius > 0.0:\n"
                "        spot = _free_landing_near(model, (target_x, target_y), squad, movement_controller, placed,\n"
                "                                  max_travel=max_travel, caller=caller, max_radius=radius)\n"
                "    if spot is not None:\n")
    new_seam = ("    if False:\n"
                "        spot = None\n"
                "    if spot is not None:\n")
    if original.count(old_seam) != 1:
        print("  PROBE SKIPPED (seam anchor not found once): whole pre-fix world")
        bad += 1
    else:
        write(DRIVER, original.replace(old_seam, new_seam))
        try:
            got, total = suite_result(run(SUITE))
            before = case_c(run(FIXTURES, "C"))
        finally:
            write(DRIVER, original)
        after = case_c(run(FIXTURES, "C"))
        bites = (got is None or got < base[0]) and before is not None and after is not None and before < after - 0.5
        print(f"  {'BITES' if bites else 'NO BITE':8s} the seam never asks the search: suite {got}/{total}, "
              f"case C {before}\" (pre-fix) vs {after}\" (fixed)")
        bad += 0 if bites else 1
finally:
    write(DRIVER, original)
    clear_cache()

print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
sys.exit(1 if bad else 0)
