"""A/B probes at the SOURCE for game/line_of_sight.py's _first_blocker() memo.

Each probe rewrites game/line_of_sight.py into a plausible WRONG version, runs
test_line_of_sight.py, and restores the file. A probe that does not turn the
suite red is a finding about the TEST, not an all-clear - unless it is declared
that way up front, with a reason, which probe 3 is.

Probes 2 and 3 are the ones worth having. Probe 2 is not a typo anyone would
make by accident - it is the OBVIOUS next optimisation (carry the memo across
calls, since eligible_targets() asks about the same wall a thousand times in a
row), and it is wrong because _blocking_models() and _obscuring_areas_between()
exclude candidates PER PAIR. It exists so the boundary _first_blocker's
docstring claims is held by a red line rather than by a paragraph.

Run: python ab_line_of_sight_memo.py
"""
import io
import subprocess
import sys

SRC = "game/line_of_sight.py"
SUITE = "test_line_of_sight.py"

# (label, old, new, expect_bite). expect_bite=False is not a get-out: it is the
# claim that the probe changes SPEED and not answers, and the runner still fails
# if such a probe does turn the suite red.
PROBES = [
    (
        "memo is trusted without re-testing it",
        """    if memo is not None:
        kind, candidate = memo
        if kind == OBSTACLE:
            if _blocked_by_obstacle(p1, p2, candidate):
                return memo
        elif kind == MODEL:
            if _blocked_by_model(p1, p2, candidate):
                return memo
        elif candidate.crosses_segment(p1, p2):
            return memo""",
        """    if memo is not None:
        return memo""",
        True,
    ),
    (
        "memo carried across calls, including MODELS (kills the house rule)",
        """    memo = None
    for pa in points_a:
        for pb in points_b:
            memo = _first_blocker(pa, pb, obstacles, blockers, obscuring_areas, memo)
            if memo is None:
                return True
    return False""",
        """    global _CROSS_CALL_MEMO
    memo = globals().get("_CROSS_CALL_MEMO")
    for pa in points_a:
        for pb in points_b:
            memo = _first_blocker(pa, pb, obstacles, blockers, obscuring_areas, memo)
            if memo is None:
                return True
    _CROSS_CALL_MEMO = memo
    return False""",
        True,
    ),
    (
        # EXPECTED NOT TO BITE, and the reason is a measurement rather than a
        # shrug: a fresh memo per facing point is exactly as LOSSLESS, only
        # slower. Measured on map2, 300 pairs, median of 5 runs - shared
        # 46.9 ms, fresh 53.4 ms, no memo at all 83.2 ms. So carrying it across
        # facing points is a real 1.14x and the memo itself is 1.77x, and a
        # CORRECTNESS suite cannot see either; that number belongs in
        # measure_shooting_frame_cost.py. What does guard this path is probe 1,
        # which flips 9 and 7 model_fully_visible mismatches on map2/map3.
        "model_fully_visible drops its memo between facing points",
        """    memo = [None]
    return all(
        _point_reachable(pb, points_a, obstacles, blockers, obscuring_areas, memo)
        for pb in facing_points
    )""",
        """    return all(
        _point_reachable(pb, points_a, obstacles, blockers, obscuring_areas, [None])
        for pb in facing_points
    )""",
        False,
    ),
    (
        "obstacles are no longer checked before models",
        """    for obstacle in obstacles:
        if _blocked_by_obstacle(p1, p2, obstacle):
            return (OBSTACLE, obstacle)
    for model in blockers:
        if _blocked_by_model(p1, p2, model):
            return (MODEL, model)""",
        """    for model in blockers:
        if _blocked_by_model(p1, p2, model):
            return (MODEL, model)
    for obstacle in obstacles:
        if _blocked_by_obstacle(p1, p2, obstacle):
            return (OBSTACLE, obstacle)""",
        True,
    ),
]


def run():
    """(passed, total) for the suite, or (-1, -1) if it crashed outright."""
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True, timeout=1800)
    for line in out.stdout.splitlines():
        if "checks passed" in line:
            got, total = line.split()[0].split("/")
            return int(got), int(total)
    return -1, -1


original = io.open(SRC, encoding="utf-8").read()
base_passed, base_total = run()
print(f"BASELINE: {base_passed}/{base_total}\n")

as_declared = 0
try:
    for label, old, new, expect_bite in PROBES:
        if original.count(old) != 1:
            print(f"  ANCHOR MISS  {label}  (found {original.count(old)}x - probe not applied)")
            continue
        io.open(SRC, "w", encoding="utf-8", newline="\n").write(original.replace(old, new))
        passed, total = run()
        # A probe must make the suite RED, not make it CRASH - a crash hides
        # which check broke. Seventeen times over in this repo.
        bit = passed != -1 and passed < base_passed
        if passed == -1:
            print(f"  CRASHED (not a red line)  {label}")
        elif bit == expect_bite:
            as_declared += 1
            head = f"BITES  {passed}/{total}" if bit else f"no bite, as declared  {passed}/{total}"
            print(f"  {head}  {label}")
        elif expect_bite:
            print(f"  NO BITE  {passed}/{total}  {label}")
        else:
            print(f"  BIT UNEXPECTEDLY  {passed}/{total}  {label}")
finally:
    io.open(SRC, "w", encoding="utf-8", newline="\n").write(original)

print(f"\n{as_declared}/{len(PROBES)} probes behaved as declared")
sys.exit(0 if as_declared == len(PROBES) else 1)
