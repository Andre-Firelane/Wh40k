"""A/B probes at the SOURCE for game/greater_good.py's rewrite and its cache.

Each probe rewrites game/greater_good.py into a plausible WRONG version, runs
test_greater_good.py, and restores the file.

The cache probes are the ones that matter. A cache whose key is missing a term
does not crash and does not slow anything down - it answers a stale True or
False for a BUTTON, which is the failure mode nothing else in this repo would
catch. Probes 2-4 remove one key term each, so every term has to earn its place.

Two probes are declared NOT to bite, each with a measured reason rather than a
shrug: dropping the short circuit, and putting is_detectable() back on the right
of the `and`. Both are LOSSLESS by construction - that is the whole argument for
making them - so a correctness suite must not see them, and pretending otherwise
would be a suite that fails on correct code. They show up in
measure_shooting_frame_cost.py instead.

Every probe here first ran against a WEAKER version of section 4, and four of
the seven sailed straight through it: the mutations moved models by +-9 inches
on open ground, where the target stayed markable throughout, so a cache with a
gutted key answered correctly by luck. Section 4 now measures two positions that
actually straddle the line and asserts that the mutations flip the answer at
least 20 times. That is the finding worth keeping: a cache test proves nothing
until its mutations are shown to change the answer.

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
        # Declared NOT to bite, and measured rather than assumed: `A and B` with
        # side-effect-free A and B gives the same ANSWER either way - that is
        # the whole argument for the reorder. What it costs is time (0.0023 ms
        # vs 4.52 ms per pair), and that belongs in the measure script. Note
        # section 5's AST guard does NOT fire here either: it asks whether
        # prey_marks/unmasking are passed, which is true of both orderings.
        False,
    ),
    (
        "can_use goes back to building the list (bypasses the cache entirely)",
        """        return self.any_eligible_target(squad)""",
        """        return bool(self.eligible_targets(squad))""",
        # The pre-fix line, and it was never WRONG - it just bypasses the cache,
        # i.e. it is the whole reported bug. Caught by the "30 more can_use()
        # calls do no sight work" check, which counts calls instead of answers;
        # asking any_eligible_target() directly there would have left can_use()
        # free to walk past the cache unnoticed, which is exactly what the first
        # version of that check did.
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
