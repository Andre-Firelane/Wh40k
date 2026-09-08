"""A/B probes at the SOURCE for The Arro'kon Protocol's single sweep and cache.

Probe 1 restores the reported bug itself - the panel asking can_use() and then
best_available_tier() in the same frame, which is the same has_valid_target()
sweep twice. It has to turn section 8 red; a comment saying "measured 660 ms"
cannot.

Two of these five probes passed against the first version of section 8, and
both were findings about the TEST rather than the code: the double panel call
is invisible to any behaviour test once the cache makes the second ask free,
and the tier ordering is invisible on a board with a single target. Section 8
answers the first with an AST guard on the panel and the second with a
two-tier scene. Neither gap was closed by weakening a probe.

Run: python ab_arrokon_double_sweep.py
"""
import io
import subprocess
import sys

SUITE = "test_arrokon_protocol.py"
CTRL = "game/arrokon_protocol.py"
PANEL = "game/ui/action_panel.py"

# (label, file, old, new, expect_bite)
PROBES = [
    (
        "the panel asks twice again (the reported double sweep)",
        PANEL,
        """            arrokon_tier = arrokon_controller.offer_tier(squad) if arrokon_controller is not None else 0
            can_arrokon_now = arrokon_tier > 0""",
        """            can_arrokon_now = arrokon_controller is not None and arrokon_controller.can_use(squad)
            arrokon_tier = arrokon_controller.best_available_tier(squad) if can_arrokon_now else 0""",
        # With the cache in place the second ask is FREE, so no behaviour test
        # can see this - and that is exactly why section 8 pins the panel's
        # shape at the SOURCE (an AST guard: offer_tier and the click callback,
        # never can_use or best_available_tier). Without that guard this probe
        # passed, and the reported bug could have walked straight back in the
        # moment someone tightened the cache key.
        True,
    ),
    (
        "the tier cache is removed entirely (every ask is a sweep)",
        CTRL,
        """        if key != self._tier_cache_key:
            self._tier_cache_key = key
            best = next(self._qualifying(squad, by_tier=True), None)
            self._tier_cache_result = sustained_hits_for_target(best) if best is not None else 0
        return self._tier_cache_result""",
        """        best = next(self._qualifying(squad, by_tier=True), None)
        return sustained_hits_for_target(best) if best is not None else 0""",
        True,
    ),
    (
        "the cache key is frozen (never invalidates)",
        CTRL,
        """        if key != self._tier_cache_key:""",
        """        key = "frozen"
        if key != self._tier_cache_key:""",
        True,
    ),
    (
        "the key drops the board fingerprint (misses the wiped-out target)",
        CTRL,
        """            board_epoch.fingerprint(self.all_tokens),""",
        """            len(self.all_tokens),""",
        True,
    ),
    (
        "best_available_tier walks candidates in NAME order (no tier short circuit)",
        CTRL,
        """        key = ((lambda s: (-sustained_hits_for_target(s), s.name)) if by_tier
               else (lambda s: s.name))""",
        """        key = (lambda s: s.name)""",
        # This one only means anything on a board with two enemy units on
        # DIFFERENT tiers, and the suite used to build exactly one target - so
        # the probe passed while the ordering was completely unguarded. Section
        # 8 now adds a 6-model unit named "2 Aaa Small 1", which sorts FIRST by
        # name and LAST by tier: name order answers 1, tier order answers 2.
        True,
    ),
]


def run():
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True, timeout=1800)
    for line in out.stdout.splitlines():
        if line.strip().endswith("failed") and "passed" in line:
            passed = int(line.split()[0])
            failed = int(line.split()[2])
            return passed, failed
    return -1, -1


originals = {path: io.open(path, encoding="utf-8").read() for path in (CTRL, PANEL)}
base_passed, base_failed = run()
print(f"BASELINE: {base_passed} passed, {base_failed} failed\n")

as_declared = 0
try:
    for label, path, old, new, expect_bite in PROBES:
        src = originals[path]
        if src.count(old) != 1:
            print(f"  ANCHOR MISS  {label}  (found {src.count(old)}x)")
            continue
        io.open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, new))
        passed, failed = run()
        io.open(path, "w", encoding="utf-8", newline="\n").write(src)
        bit = passed != -1 and failed > base_failed
        if passed == -1:
            print(f"  CRASHED (not a red line)  {label}")
        elif bit == expect_bite:
            as_declared += 1
            head = f"BITES  {failed} failed" if bit else f"no bite, as declared  {failed} failed"
            print(f"  {head}  {label}")
        elif expect_bite:
            print(f"  NO BITE  {failed} failed  {label}")
        else:
            print(f"  BIT UNEXPECTEDLY  {failed} failed  {label}")
finally:
    for path, src in originals.items():
        io.open(path, "w", encoding="utf-8", newline="\n").write(src)

print(f"\n{as_declared}/{len(PROBES)} probes behaved as declared")
sys.exit(0 if as_declared == len(PROBES) else 1)
