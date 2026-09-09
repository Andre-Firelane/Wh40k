"""A/B probes for the slot-first charge approach and the feasibility gate, at
the SOURCE. Each probe restores ONE clause of the pre-fix world in
ai/agent_driver.py, runs the suite named with it and must make it red - red,
not crashed.

A probe that does not bite is a finding about the TEST, not a pass.

Run: python ab_charge_approach.py
"""
import io
import os
import re
import shutil
import subprocess
import sys

DRIVER = os.path.join("ai", "agent_driver.py")
SLOT_FIRST = "test_charge_slot_first.py"
FEASIBILITY = "test_charge_feasibility.py"

PROBES = [
    (SLOT_FIRST, "slot-first is no longer the first rung of the ladder",
     'for attempt in ["slot-first"] + (["route"] if routed_first else []) + approaches:',
     'for attempt in (["route"] if routed_first else []) + approaches:'),
    (SLOT_FIRST, "the approach never lands (pre-fix ladder)",
     "    if not slots or not squad.models or not target_squad.models:\n        return False\n    if movement_controller.move_mode != \"charge\":\n        return False\n    snapshot = _position_snapshot(movement_controller, squad)\n",
     "    if not slots or not squad.models or not target_squad.models:\n        return False\n    if movement_controller.move_mode != \"charge\" or True:\n        return False\n    snapshot = _position_snapshot(movement_controller, squad)\n"),
    (SLOT_FIRST, "the spread pass after landing is gone",
     "    _spread_into_engagement(movement_controller, squad, target_squad, CHARGE_TARGET_CLEARANCE_IN,\n                            True, 0, close_in_pairs, slots=slots)\n    return True\n",
     "    return True\n"),
    (SLOT_FIRST, "the charge ring starts at the old clearance again",
     "_CHARGE_RING_INNER_EDGE_IN = PILE_IN_CLEARANCE_IN\n",
     "_CHARGE_RING_INNER_EDGE_IN = CHARGE_TARGET_CLEARANCE_IN\n"),
    (SLOT_FIRST, "followers are accepted without touching the placed set",
     "        if walk(model, route) and touches_placed(model):\n            return True\n",
     "        if walk(model, route):\n            return True\n"),
    (FEASIBILITY, "the feasibility gate is gone (a hopeless charge is offered)",
     "        if reachable and not feasible:\n            memory.declined_charge.add(candidate.name)\n",
     "        if False:\n            memory.declined_charge.add(candidate.name)\n"),
    (FEASIBILITY, "the roll is quoted to the unit's edge even when the near side is blocked",
     "            needed = math.ceil(max(gap, walk))\n",
     "            needed = math.ceil(gap)\n"),
    (FEASIBILITY, "the blocked-side note is gone",
     "            elif walk - gap >= CHARGE_DETOUR_REPORT_IN:\n",
     "            elif False:\n"),
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
base = {}
for suite in (SLOT_FIRST, FEASIBILITY):
    text, code = run(suite)
    base[suite] = result(text)
    print(f"baseline {suite}: {base[suite][0]}/{base[suite][1]} (exit {code})")
    if base[suite][0] is None or code != 0:
        sys.exit("baseline is not green - fix that first")

bad = 0
try:
    for suite, label, old, new in PROBES:
        if original.count(old) != 1:
            print(f"  PROBE SKIPPED (anchor not found exactly once): {label}")
            bad += 1
            continue
        write(DRIVER, original.replace(old, new))
        try:
            text, code = run(suite)
        finally:
            write(DRIVER, original)
        got, total = result(text)
        if got is None:
            verdict, detail = "CRASHED", "the suite did not report - a probe must make it red, not crash it"
            bad += 1
        elif got < base[suite][0]:
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
