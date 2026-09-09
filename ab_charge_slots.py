"""A/B probes for the engagement ring (ai/agent_driver._engagement_slots, its
legal filter and the ranked de-dupe), at the SOURCE. Each probe restores ONE
clause of the pre-fix world in ai/agent_driver.py, runs test_charge_slots.py
and must make it red - red, not crashed.

A probe that does not bite is a finding about the TEST, not a pass.

Run: python ab_charge_slots.py
"""
import io
import os
import re
import shutil
import subprocess
import sys

DRIVER = os.path.join("ai", "agent_driver.py")
SUITE = "test_charge_slots.py"

PROBES = [
    ("the ring is sampled one base apart again (the old pitch)",
     "            steps = max(8, int(round((2 * math.pi * ring) / arc_step_in)))\n",
     "            steps = max(6, int((2 * math.pi * ring) / max(0.5, 2 * own_radius + 0.1)))\n"),
    ("the ring depth is one base again (one ring for anything bigger than a Boy)",
     "            ring += _ENGAGEMENT_RING_STEP_IN\n",
     "            ring += max(0.5, 2 * own_radius + 0.1)\n"),
    ("the legal filter is never asked",
     "                if legal is not None and not legal(x, y):\n                    continue\n",
     "                if False:\n                    continue\n"),
    ("rule 13.05 is not asked of a slot",
     "        if model_terrain_violation(probe, dense, x, y):\n            return False\n",
     "        if False:\n            return False\n"),
    # Anchored on the slot filter's own `legal` (the `probe, dense` line and
    # the bare `return True` after the keep-out loop): the landing search's
    # legal() has the same two loops word for word, so the loops alone match
    # twice and the probe would be SKIPPED.
    ("the keep-out engagement range is not asked of a slot",
     "        for t in keep_out:\n            if math.hypot(x - t.x_in, y - t.y_in) - r - t.radius_in <= ENGAGEMENT_RANGE_IN + _LANDING_OVERLAP_MARGIN_IN:\n                return False\n        return True\n",
     "        for t in ():\n            if math.hypot(x - t.x_in, y - t.y_in) - r - t.radius_in <= ENGAGEMENT_RANGE_IN + _LANDING_OVERLAP_MARGIN_IN:\n                return False\n        return True\n"),
    ("other units' bases do not block a slot",
     "        if model_terrain_violation(probe, dense, x, y):\n            return False\n        for t in blockers:\n",
     "        if model_terrain_violation(probe, dense, x, y):\n            return False\n        for t in ():\n"),
    ("the ranked list no longer de-dupes (six neighbours on one arc)",
     "        if any((slot[0] - k[0]) ** 2 + (slot[1] - k[1]) ** 2 < min_gap * min_gap for k in kept):\n            continue\n",
     "        if False:\n            continue\n"),
    ("the ladder rebuilds the ring per approach (slots not handed down)",
     "                              approach_angle_deg=angle, detour_fraction=detour, slots=slots)\n",
     "                              approach_angle_deg=angle, detour_fraction=detour, slots=None)\n"),
]


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


def run(script):
    clear_cache()
    out = subprocess.run([sys.executable, script], capture_output=True, text=True)
    return out.stdout + out.stderr, out.returncode


def result(text):
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)


original = read(DRIVER)
base_text, base_code = run(SUITE)
base = result(base_text)
print(f"baseline {SUITE}: {base[0]}/{base[1]} (exit {base_code})")
if base[0] is None or base_code != 0:
    sys.exit("baseline is not green - fix that first")

bad = 0
try:
    for label, old, new in PROBES:
        if original.count(old) != 1:
            print(f"  PROBE SKIPPED (anchor not found exactly once): {label}")
            bad += 1
            continue
        write(DRIVER, original.replace(old, new))
        try:
            text, code = run(SUITE)
        finally:
            write(DRIVER, original)
        got, total = result(text)
        if got is None:
            verdict, detail = "CRASHED", "the suite did not report - a probe must make it red, not crash it"
            bad += 1
        elif got < base[0]:
            verdict, detail = "BITES", f"{got}/{total}"
        else:
            verdict, detail = "NO BITE", f"{got}/{total} - FINDING ABOUT THE TEST"
            bad += 1
        print(f"  {verdict:8s} {label}: {detail}")
finally:
    write(DRIVER, original)
    clear_cache()

print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
sys.exit(1 if bad else 0)
