"""A/B probes for the Advance re-roll prompt loop.

User: "im letzten spiel wurde ich immer wieder gefragt, ob ich den advance
rerollen will mit den destroyern. es war eine schleife bis ich ihn gererollt
habe."

Each probe restores ONE piece of the pre-fix world AT THE SOURCE and must turn
its own checks red. A probe that does not bite is a finding about the TEST
(Fehlerklasse 24).

THREE suites are driven, not one. The seam is shared by the Autarch's
Superlative Strategist and Protocol of the Sudden Storm, and a fix reaching only
one of them is exactly the drift this repo keeps consolidating - so both are
run. The DiceManager's own suite is the third, because one claim can only be
shown there: no unit can hold both abilities, so probe 5 has nothing to bite in
the other two.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SUITES = {
    "autarchs": os.path.join(ROOT, "test_autarchs_and_maugan_ra.py"),
    "dynasty": os.path.join(ROOT, "test_awakened_dynasty.py"),
    # The DiceManager's own suite: the per-SOURCE keying can only be shown
    # there, because no unit can hold both abilities (see probe 5).
    "dice": os.path.join(ROOT, "test_hazard_lock_and_dice.py"),
}
BASE = {"autarchs": 137, "dynasty": 95, "dice": 50}

G = lambda *p: os.path.join(ROOT, "game", *p)


def clear_cache():
    for root, dirs, _f in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run(path):
    out = subprocess.run([sys.executable, path], capture_output=True, text=True,
                         cwd=ROOT).stdout
    for line in out.splitlines():
        if "checks passed" in line:
            got, total = line.strip().split()[0].split("/")
            return int(got), int(total)
    return -1, -1


def probe(label, path, old, new):
    src = open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print("  SKIP %s: anchor found %dx" % (label, src.count(old)))
        return
    open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
    try:
        clear_cache()
        results = {name: run(p) for name, p in SUITES.items()}
    finally:
        open(path, "w", encoding="utf-8").write(src)
    bit = any(results[n][0] < BASE[n] for n in results)
    shown = "  ".join("%s %d/%d" % (n, results[n][0], results[n][1]) for n in sorted(results))
    print("  %-22s %s  %s" % ("BITES" if bit else "*** DID NOT BITE ***", shown, label))


clear_cache()
print("baseline: " + "  ".join("%s %d/%d" % (n, run(p)[0], BASE[n])
                               for n, p in sorted(SUITES.items())))

# 1. THE WHOLE PRE-FIX WORLD: an offer is never booked, so declining leaves the
#    board that raised the question and the next click raises it again.
probe(
    "an offer is never remembered - the reported loop",
    G("dice.py"),
    "        if self.pending_values is None or source in self._reroll_offers:\n"
    "            return False\n"
    "        self._reroll_offers.add(source)\n"
    "        return True",
    "        return self.pending_values is not None",
)

# 2. ...the same thing from the Sudden Storm side only, which is the ability
#    the report names.
probe(
    "Sudden Storm stops booking its offer",
    G("protocol_sudden_storm.py"),
    "        if not self.dice_manager.claim_reroll_offer(SUDDEN_STORM_NAME):\n"
    "            return False\n",
    "",
)

# 3. ...and from the Autarch side, which shares the seam. A fix that reached
#    only one of the two would pass every check of the other.
probe(
    "Superlative Strategist stops booking its offer",
    G("superlative_strategist.py"),
    "        if not self.dice_manager.claim_reroll_offer(SUPERLATIVE_STRATEGIST_LABEL):\n"
    "            return False\n",
    "",
)

# 4. The other direction, and the one a "just set a flag once" fix gets wrong:
#    the memory must be cleared by roll(), or the SECOND Advance of the battle
#    is never offered at all. A silent loss is worse than the loop.
probe(
    "the memory outlives its roll, so the next Advance is never offered",
    G("dice.py"),
    "        self.already_rerolled = set(range(count)) if is_reroll else set()\n"
    "        self._reroll_offers = set()",
    "        self.already_rerolled = set(range(count)) if is_reroll else set()",
)

# 5. Keyed by source, not one shared flag: two abilities may each offer once.
#    Today no unit can hold both, so this is a guard for the third one.
probe(
    "one shared flag instead of one per ability",
    G("dice.py"),
    "        if self.pending_values is None or source in self._reroll_offers:\n"
    "            return False\n"
    "        self._reroll_offers.add(source)",
    "        if self.pending_values is None or self._reroll_offers:\n"
    "            return False\n"
    "        self._reroll_offers.add(source)",
)
