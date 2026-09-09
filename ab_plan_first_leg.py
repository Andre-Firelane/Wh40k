"""A/B probes for the first leg toward a distant goal, at the SOURCE. Each
probe restores ONE clause of the pre-fix world in ai/observation.py or
ai/agent_driver.py, runs test_plan_first_leg.py, and must make it red without
crashing it; the last one restores the whole pre-fix world (no field offered,
reach overshoots back on the retry channel, no backwards-order guard).

A probe that does not bite is a finding about the TEST, not a pass. A probe
that crashes the suite is a finding about the SUITE (it has to degrade to red).

Run: python ab_plan_first_leg.py
"""
import io
import os
import re
import shutil
import subprocess
import sys

OBSERVATION = os.path.join("ai", "observation.py")
DRIVER = os.path.join("ai", "agent_driver.py")
SUITE = "test_plan_first_leg.py"


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


# The retry channel's old reach clause, verbatim from before 2026-09-09.
OLD_REACH_CLAUSE = (
    "    for name, entry in plan.get(\"unit_plans\", {}).items():\n"
    "        spot = entry.get(\"position\")\n"
    "        if spot is None:\n"
    "            continue\n"
    "        squad = squads_by_name.get(name)\n"
    "        if squad is None or not squad.models:\n"
    "            continue\n"
    "        gap, reach = _reach_to_point(squad, spot, allow_advance=True)\n"
    "        if gap - reach > _CLAMP_TOLERANCE_IN:\n"
    "            problems.append(\n"
    "                f\"{name}: ordered to ({spot[0]:.0f},{spot[1]:.0f}), which is {gap:.0f}\\\" from where \"\n"
    "                f\"it stands, but it only reaches {reach:.0f}\\\" even Advancing - it cannot get there this turn\"\n"
    "            )\n"
)
CHANNEL_ANCHOR = "    problems.extend(_unshootable_from_position_problems(plan, squads_by_name, state))\n"

GUARD_ANCHOR = (
    "                if stands > plain and ordered > stands + _BACKWARD_ORDER_TOLERANCE_IN:\n"
)
FIELD_ANCHOR = (
    "        entry[\"first_leg_this_turn\"] = leg\n"
    "        return entry\n"
)
PASSIVE_ANCHOR = (
    "                and entry.get(\"role\") not in (\"hold\", \"screen\", \"stage\"):\n"
    "            goal, goal_name = _order_goal_point(entry, squad, state)\n"
)

PROBES = [
    ("the observation no longer attaches first_leg_this_turn",
     [(OBSERVATION, FIELD_ANCHOR, "        return entry\n")]),
    ("the sideways swing is gone (walk back only)",
     [(OBSERVATION,
       "_FIRST_LEG_SWING_DEGREES = (0.0, 6.0, -6.0, 12.0, -12.0, 18.0, -18.0, 24.0, -24.0, 30.0, -30.0)\n",
       "_FIRST_LEG_SWING_DEGREES = (0.0,)\n")]),
    ("no nudge at all (a blocked line yields no leg)",
     [(OBSERVATION, "_FIRST_LEG_NUDGE_MAX_IN = 6.0\n", "_FIRST_LEG_NUDGE_MAX_IN = 0.0\n"),
      (OBSERVATION,
       "_FIRST_LEG_SWING_DEGREES = (0.0, 6.0, -6.0, 12.0, -12.0, 18.0, -18.0, 24.0, -24.0, 30.0, -30.0)\n",
       "_FIRST_LEG_SWING_DEGREES = (0.0,)\n")]),
    ("the clamp is a second projection again, not the first leg",
     [(DRIVER,
       "                    leg = observation.first_leg_toward(squad, spot, reach, state.obstacles)\n",
       "                    leg = None\n")]),
    ("the backwards-order guard is gone",
     [(DRIVER, GUARD_ANCHOR, "                if False:\n")]),
    ("the guard no longer reads the goal from the reason text",
     [(DRIVER, "    reason = (entry.get(\"reason\") or \"\").lower()\n    if not reason:\n",
       "    reason = \"\"\n    if not reason:\n")]),
    ("the guard fires even when the goal is already within one move",
     [(DRIVER, GUARD_ANCHOR,
       "                if ordered > stands + _BACKWARD_ORDER_TOLERANCE_IN:\n")]),
    ("the guard ignores the tolerance (a sidestep is a step backwards)",
     [(DRIVER, GUARD_ANCHOR,
       "                if stands > plain and ordered > stands:\n")]),
    ("the guard is no longer scoped to active roles",
     [(DRIVER, PASSIVE_ANCHOR,
       "                and True:\n            goal, goal_name = _order_goal_point(entry, squad, state)\n")]),
    ("reach overshoots go back on the retry channel again",
     [(DRIVER, CHANNEL_ANCHOR, OLD_REACH_CLAUSE + CHANNEL_ANCHOR)]),
    ("the whole pre-fix world (no field, overshoots sent back, no guard)",
     [(OBSERVATION, FIELD_ANCHOR, "        return entry\n"),
      (DRIVER, CHANNEL_ANCHOR, OLD_REACH_CLAUSE + CHANNEL_ANCHOR),
      (DRIVER, GUARD_ANCHOR, "                if False:\n")]),
]


def main():
    originals = {p: read(p) for p in (OBSERVATION, DRIVER)}
    base_text = run(SUITE)
    base = suite_result(base_text)
    print(f"baseline: {base[0]}/{base[1]}")
    if base[0] is None or base[0] != base[1]:
        print("  baseline is not green - fix that first")
        print(base_text[-2000:])
        return 2
    outcomes = []
    try:
        for label, edits in PROBES:
            texts = dict(originals)
            skipped = None
            for path, old, new in edits:
                if texts[path].count(old) != 1:
                    skipped = f"anchor not unique in {path} ({texts[path].count(old)} hits)"
                    break
                texts[path] = texts[path].replace(old, new)
            if skipped:
                outcomes.append((label, "SKIPPED", skipped))
                print(f"SKIPPED  {label}: {skipped}")
                continue
            for path in (OBSERVATION, DRIVER):
                if texts[path] != originals[path]:
                    write(path, texts[path])
            try:
                text = run(SUITE)
            finally:
                for path in (OBSERVATION, DRIVER):
                    write(path, originals[path])
            got = suite_result(text)
            if got[0] is None:
                verdict = "CRASHED"
                detail = text.strip().splitlines()[-1] if text.strip() else "(no output)"
            elif got[0] < base[0]:
                verdict = "BITES"
                detail = f"{got[0]}/{got[1]}"
            else:
                verdict = "NO BITE"
                detail = f"{got[0]}/{got[1]}"
            outcomes.append((label, verdict, detail))
            print(f"{verdict:8s} {label}: {detail}")
    finally:
        for path in (OBSERVATION, DRIVER):
            write(path, originals[path])
        clear_cache()
    bad = [o for o in outcomes if o[1] != "BITES"]
    print(f"\n{len(outcomes) - len(bad)} of {len(outcomes)} probes bite")
    for label, verdict, detail in bad:
        print(f"  {verdict}: {label} ({detail})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
