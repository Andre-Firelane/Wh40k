"""run_tests.py - the whole regression sweep in one call.

WHY THIS EXISTS
---------------
Measured before it was built (user: "deine tests dauern immer sehr lange"):
all 50 suites together are 36 s of CPU, 40 of them finish under 0.7 s, the
slowest is 4.7 s. The RUNTIME was never the problem. The problem was that a
full sweep meant fifty separate invocations, each printing its own summary -
that is what made it feel long and what filled the transcript. This runs them
in parallel and prints only what went wrong.

For contrast, the heavy scripts are a different order of magnitude and are
deliberately NOT in the default sweep: selfplay.py 105 s, smoke_pregame.py
45 s, measure_deployment_safety.py 17 s. Per the standing scope rule those
belong to changes that touch geometry, placement, the UI or main.py - not to
every new datasheet. `--smoke` runs them when they do apply.

THE ONLY SIGNAL THIS TRUSTS IS THE EXIT CODE
--------------------------------------------
A suite must exit 0 when everything passed and non-zero otherwise. That is the
contract, because the printed summary line comes in three different shapes
across this repo ("N/M checks passed", "passed N, failed M", "N passed, M
failed") and TWO suites have already been caught printing FAILED while exiting
0 - a sweep that trusts exit codes reported those green for a while. The check
COUNTS below are parsed best-effort and feed the totals line only; a suite that
prints several summaries has its last one counted, so the total is indicative,
not authoritative.

USAGE
    python run_tests.py                  every test_*.py, quiet
    python run_tests.py painboy target   only suites matching a substring
    python run_tests.py -v               one line per suite, including green
    python run_tests.py --smoke          also run the heavy scripts, in series
    python run_tests.py --list           show what would run
"""

import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))

# Suites whose failure is understood and NOT a regression. The expected number
# of failing checks is part of the entry on purpose: listing a file wholesale
# would hide a NEW break in it, whereas a changed count falls through to
# "unexpected" and turns the run red again - including when someone finally
# FIXES the listed ones, which is also worth knowing.
KNOWN_FAILURES = {
    "test_formation_coherency.py": (
        2,
        "stale A/B probe - it asserts the pre-fix world (spread stayed frozen), "
        "but the pre-fix copy tightens too now that the 9 inch spread limit is "
        "lifted for the AI (see CLAUDE.md)",
    ),
}

# Heavy scripts for --smoke, cheapest to read first. selfplay gets an explicit
# frame count: its default run is 105 s and a smoke pass does not need the long
# tail.
HEAVY = (
    # A handful of frames: it clicks a map tile and two army tiles, then reads
    # the built battlefield, so it is by far the cheapest thing here.
    ("smoke_setup_screens.py", ()),
    # A dozen frames, and the only harness that drives main.run() - so it is
    # the one place the menu, the ESC rung, the board button, the AI pause and
    # the whole restart loop are proved against the real thing rather than
    # against a source guard.
    ("smoke_game_menu.py", ()),
    # Also only a few dozen frames, and it proves a CHAIN no suite can reach:
    # a real click reaching the controller and main.py then handing that live
    # selection to the renderer. Cheap enough to belong in the automatic sweep
    # rather than in the run-it-by-hand set - the whole point of it is the
    # failure class where each link is unit-tested and the chain is not.
    ("smoke_selection.py", ("map2",)),
    # ~45 frames, and it proves the chain that fails WORST when it breaks: a
    # decision whose options name units is answered by clicking one on the
    # board, and if that click never arrives the game is blocked on a prompt
    # nobody can answer (Fehlerklasse 25) rather than quietly doing nothing.
    ("smoke_unit_pick.py", ("map2",)),
    # Same argument: a few dozen frames, and it proves the one thing no suite
    # can - that a right-press really reaches the gesture through main()'s
    # state-gated chain, and that the polled continuation runs under a modal.
    ("smoke_line_drag.py", ("map2",)),
    # ~20 frames, and it proves the other half of that chain: a click on a real
    # card in the Reserves strip, and a right-press that sets the carried unit
    # down AND forms it up in the same gesture. The pair "nothing placed yet" /
    # "placed and dragging" is the whole difference between one gesture and two.
    ("smoke_pool_line_drag.py", ("map2",)),
    ("smoke_log_input.py", ("map2",)),
    ("smoke_pregame.py", ("map2",)),
    ("selfplay.py", ("map2", "1500")),
)

_COUNT_PATTERNS = (
    (re.compile(r"(\d+)\s*/\s*(\d+)\s+checks passed"), "passed/total"),
    (re.compile(r"passed\s+(\d+),\s*failed\s+(\d+)"), "passed,failed"),
    (re.compile(r"(\d+)\s+passed,\s*(\d+)\s+failed"), "passed,failed"),
)


def parse_counts(text):
    """(passed, failed) from a suite's own summary line, or None."""
    for pattern, shape in _COUNT_PATTERNS:
        matches = pattern.findall(text)
        if not matches:
            continue
        first, second = (int(x) for x in matches[-1])
        return (first, second - first) if shape == "passed/total" else (first, second)
    return None


def child_env():
    env = dict(os.environ)
    # Every suite that renders sets this itself, but a new one can forget, and
    # a real window opening mid-sweep is both slow and confusing.
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    # The suites print German text. A cp1252 console would raise
    # UnicodeEncodeError inside the CHILD, which looks exactly like a test
    # failure and is not one.
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run_script(script, args=(), env=None):
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, script, *args],
        cwd=ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return {
        "script": script,
        "rc": proc.returncode,
        "out": (proc.stdout or "") + (proc.stderr or ""),
        "secs": time.monotonic() - start,
    }


def tail(text, limit=40):
    lines = text.rstrip().splitlines()
    if len(lines) <= limit:
        return "\n".join(lines)
    omitted = len(lines) - limit
    return f"... ({omitted} earlier lines omitted)\n" + "\n".join(lines[-limit:])


def main(argv):
    verbose = "-v" in argv or "--verbose" in argv
    smoke = "--smoke" in argv
    listing = "--list" in argv
    filters = [a.lower() for a in argv if not a.startswith("-")]

    suites = sorted(
        f for f in os.listdir(ROOT)
        if f.startswith("test_") and f.endswith(".py")
    )
    if filters:
        suites = [s for s in suites if any(f in s.lower() for f in filters)]

    if listing:
        for suite in suites:
            print(suite)
        if smoke:
            for name, args in HEAVY:
                print(name, *args)
        return 0

    if not suites:
        print(f"no suite matched {filters}")
        return 2

    env = child_env()
    wall_start = time.monotonic()
    workers = max(1, min(len(suites), os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda s: run_script(s, env=env), suites))
    wall = time.monotonic() - wall_start

    unexpected, known = [], []
    checks_passed = checks_failed = 0
    for result in results:
        counts = parse_counts(result["out"])
        if counts:
            checks_passed += counts[0]
            checks_failed += counts[1]
        if result["rc"] == 0:
            continue
        expected = KNOWN_FAILURES.get(result["script"])
        if expected and counts and counts[1] == expected[0]:
            known.append((result, expected[1]))
        else:
            unexpected.append(result)

    for result in unexpected:
        print("=" * 72)
        print(f"FAILED  {result['script']}   exit {result['rc']}, {result['secs']:.1f}s")
        print(tail(result["out"]))
    if unexpected:
        print("=" * 72)

    if verbose:
        for result in sorted(results, key=lambda r: r["script"]):
            mark = "ok  " if result["rc"] == 0 else "FAIL"
            print(f"{mark} {result['script']:<40} {result['secs']:5.1f}s")

    green = len(results) - len(unexpected) - len(known)
    print(
        f"\n{len(results)} suites, ~{checks_passed + checks_failed} checks"
        f"  |  {green} green  |  {len(unexpected)} FAILED"
        f"  |  {len(known)} known  |  {wall:.1f}s wall"
    )
    for result, why in known:
        print(f"  known  {result['script']}: {why}")
    slowest = sorted(results, key=lambda r: -r["secs"])[:3]
    print("  slowest: " + ", ".join(f"{r['script']} {r['secs']:.1f}s" for r in slowest))

    heavy_failed = 0
    if smoke:
        print("\n--- heavy scripts (in series; these drive main()) ---")
        for name, args in HEAVY:
            result = run_script(name, args, env=env)
            mark = "ok  " if result["rc"] == 0 else "FAIL"
            print(f"{mark} {name} {' '.join(args)}   {result['secs']:.1f}s")
            if result["rc"] != 0:
                heavy_failed += 1
                print(tail(result["out"], 25))

    return 1 if (unexpected or heavy_failed) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
