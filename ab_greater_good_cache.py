"""A/B probes at the SOURCE for game/greater_good.py's rewrite and its cache.

Each probe rewrites game/greater_good.py into a plausible WRONG version, runs
test_greater_good.py, and restores the file.

The cache probes are the ones that matter. A cache whose key is missing a term
does not crash and does not slow anything down - it answers a stale True or
False for a BUTTON, which is the failure mode nothing else in this repo would
catch. Probes 2-4 remove one key term each, so every term has to earn its place.

Probe 5 is declared NOT to bite, with a reason: moving is_detectable() back to
the right of the `and` is lossless (that is the whole argument for moving it),
so a correctness suite must not see it. It shows up in
measure_shooting_frame_cost.py instead.

Run: python ab_greater_good_cache.py
"""
import io
import subprocess
import sys

SRC = "game/greater_good.py"
SUITE = "test_greater_good.py"

PROBES = [
    (
        "the cache key is frozen (never invalidates)",
        """        if key != self._any_target_cache_key:""",
        """        key = "frozen"
        if key != self._any_target_cache_key:""",
        True,
    ),
    (
        "the key drops the board fingerprint (misses every move)",
        """            board_epoch.fingerprint(self.all_tokens),""",
        """            len(self.all_tokens),""",
        True,
    ),
    (
        "the key drops len(spotted_by) (misses a fresh mark)",
        """            len(self.spotted_by),""",
        """""",
        True,
    ),
    (
        "the key drops the round/turn term",
        """            getattr(self.turn_tracker, "battle_round", None),
            getattr(self.turn_tracker, "turn_owner", None),""",
        """""",
        True,
    ),
    (
        "any_eligible_target builds the whole list again (no short circuit)",
        """            self._any_target_cache_result = next(self._eligible_targets(squad), None) is not None""",
        """            self._any_target_cache_result = bool(list(self._eligible_targets(squad)))""",
        # Declared NOT to bite: building the list and stopping at the first hit
        # give the same ANSWER by construction - that is why the short circuit
        # was safe to add. It only shows up as time, and time belongs in
        # measure_shooting_frame_cost.py (measured 4732 ms -> 134 ms cold).
        False,
    ),
    (
        "is_detectable moves back to the right of the `and`",
        """            detectable = [
                defender for defender in enemy.models
                if status_effects.is_detectable(
                    defender, squad, self.terrain_areas, self.turn_tracker, last_ranged_attack_turn)
            ]
            if not detectable:
                continue
            if any(
                line_of_sight.has_line_of_sight(friendly, defender, self.obstacles, self.all_tokens, self.terrain_areas)
                for friendly in squad.models
                for defender in detectable
            ):
                yield enemy""",
        """            if any(
                line_of_sight.has_line_of_sight(friendly, defender, self.obstacles, self.all_tokens, self.terrain_areas)
                and status_effects.is_detectable(
                    defender, squad, self.terrain_areas, self.turn_tracker, last_ranged_attack_turn)
                for friendly in squad.models
                for defender in enemy.models
            ):
                yield enemy""",
        # Declared NOT to bite for the CONJUNCTION's sake - but section 5's AST
        # guard still fires on it, because the reordering is the very thing that
        # made the detection_range divergence easy to "tidy up" by accident.
        True,
    ),
    (
        "can_use goes back to building the list (bypasses the cache entirely)",
        """        return self.any_eligible_target(squad)""",
        """        return bool(self.eligible_targets(squad))""",
        # Declared NOT to bite on ANSWERS - it is the pre-fix line and it was
        # correct. What it costs is the cache, i.e. the whole report. Pinned by
        # the "30 more asks do no sight work" check, which measures calls.
        True,
    ),
]


def run():
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
            print(f"  ANCHOR MISS  {label}  (found {original.count(old)}x)")
            continue
        io.open(SRC, "w", encoding="utf-8", newline="\n").write(original.replace(old, new))
        passed, total = run()
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
