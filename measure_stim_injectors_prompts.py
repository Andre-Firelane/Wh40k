"""How often does Stim Injectors actually interrupt a real game?

The design question behind the relevance gate was the user's: a stratagem whose
WHEN is "just after an enemy unit has selected its targets" fires on every
enemy attack, and being asked that often "würde sehr nerven". The gate is the
answer; this measures whether it worked, by counting the two numbers that
matter over a full self-play run:

  * how many times the hook fires at all (every target selection, both sides)
  * how many of those actually open a prompt

and, for the suppressed ones, WHY - so a future report of "it asks too much"
or "it never asks" can be checked against the reason rather than guessed at.

Usage:  python measure_stim_injectors_prompts.py [map] [frames]
Uses selfplay.py's harness, so: MockAgent, no API calls, no money.
"""
import runpy
import sys
from collections import Counter

import game.stim_injectors as si

stats = Counter()
_original = si.StimInjectorsController.maybe_offer


def _reason(self, attacker, target, melee):
    """Which clause suppressed this one - mirrors can_offer()'s order."""
    if attacker is None or target is None or self.decision_manager is None:
        return "no attacker/target/decision manager"
    if self.turn_tracker is not None and self.turn_tracker.phase not in (si.PHASE_SHOOTING, si.PHASE_FIGHT):
        return "outside the Shooting/Fight phase (WHEN)"
    if target.owner == attacker.owner:
        return "not an enemy attack"
    if not target.models or all(m.is_dead() for m in target.models):
        return "target already wiped out"
    if not si.is_battlesuit_unit(target):
        return "target is not a BATTLESUIT unit (TARGET)"
    if target.stim_injectors_active or si._already_as_good(target):
        return "already has Feel No Pain 6+ or better"
    if not self.stratagem_controller.can_use(target.owner, self._stratagem, [target]):
        return "rule 15.01 / CP / battle-shock"
    return "RELEVANCE GATE - not worth 1 CP"


def _wrapped(self, attacker, target, melee=False):
    stats["hook fired"] += 1
    key = (id(attacker), id(target))
    if key in self._offered_this_phase:
        stats["deduplicated (same attack, split fire)"] += 1
        return False
    if not self.can_offer(attacker, target, melee=melee):
        stats["suppressed: " + _reason(self, attacker, target, melee)] += 1
        return False
    saved = si.expected_wounds_saved(attacker, target, melee=melee)
    stats["PROMPTED"] += 1
    stats_detail.append((saved, attacker.name, target.name, "melee" if melee else "ranged"))
    return _original(self, attacker, target, melee=melee)


stats_detail = []
si.StimInjectorsController.maybe_offer = _wrapped

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "4000"])
try:
    runpy.run_path("selfplay.py", run_name="__main__")
except SystemExit:
    pass

print("\n=== Stim Injectors prompt count over one self-play run ===")
total = stats["hook fired"]
print(f"target selections seen by the hook: {total}")
for key, n in sorted(stats.items(), key=lambda kv: -kv[1]):
    if key == "hook fired":
        continue
    print(f"   {n:5d}  {key}")
if total:
    print(f"\nprompts per target selection: {stats['PROMPTED']}/{total} "
          f"({100.0 * stats['PROMPTED'] / total:.1f}%)")
for saved, a, t, kind in stats_detail:
    print(f"   prompted: {a} -> {t} ({kind}), ~{saved:.2f} wounds saved")
