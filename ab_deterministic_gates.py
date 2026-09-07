"""A/B probes for stage 1 - the rules that decided for a human.

Each probe restores ONE pre-fix world AT THE SOURCE, runs the suite, puts it
back. A probe that does not bite is a finding about the TEST (Fehlerklasse 24).

There is one probe per finding, and each is the exact line that shipped - so a
probe that stops biting means that finding has regressed, not that the probe is
stale.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.join(ROOT, "test_deterministic_gates.py")
BASE = 38

G = lambda *p: os.path.join(ROOT, "game", *p)


def clear_cache():
    for root, dirs, _f in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run():
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True,
                         cwd=ROOT).stdout
    for line in out.splitlines():
        if "checks passed" in line:
            got, total = line.strip().split()[0].split("/")
            return int(got), int(total)
    return -1, -1


def probe(label, path, old, new):
    src = open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print(f"  SKIP {label}: anchor found {src.count(old)}x")
        return
    open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
    try:
        clear_cache()
        got, total = run()
    finally:
        open(path, "w", encoding="utf-8").write(src)
    print(f"  {'BITES' if got < BASE else '*** DID NOT BITE ***':22} {got}/{total}  {label}")


clear_cache()
print(f"baseline: {run()[0]}/{BASE}")

# 1. The re-roll gated on the AI's verdict again - the reported shape: a human
#    who rolls a 2 is never offered it.
probe(
    "the re-roll is gated on the AI's verdict again",
    G("reanimation_protocols.py"),
    "if not self._reroll_offered and can_reroll(squad, rolled):",
    "if not self._reroll_offered and should_reroll(squad, rolled):",
)

# 2. ...and the other half: should_reroll() folded back into one predicate, so
#    there is no separate "the rule permits it" to offer on.
probe(
    "can_reroll collapses into the AI's policy",
    G("reanimation_protocols.py"),
    "    return can_reroll(squad, rolled) and rolled < REANIMATION_REROLL_FLOOR",
    "    return can_reroll(squad, rolled)",
)

# 3. The orb offers the alphabetically first unit as a bare yes/no again.
probe(
    "the orb offers only the first candidate",
    G("resurrection_orb.py"),
    """        options = [
            (f"{s.name} ({reanimation_protocols.recoverable_wounds(s)} wound(s) to recover)",
             (lambda target=s: self._use(target)))
            for s in candidates
        ]""",
    """        options = [("Use the Resurrection Orb",
                    (lambda target=candidates[0]: self._use(target)))]""",
)

# 4. 'Ard as Nails puts its verdict back above the split, so an AI heuristic
#    decides whether a human sees the Stratagem at all.
probe(
    "'Ard as Nails pre-filters the human's prompt",
    G("ard_as_nails.py"),
    "        if target.owner in self.auto_players:\n"
    "            if not is_worth_using(attacker, target, melee=melee):",
    "        if not is_worth_using(attacker, target, melee=melee):\n"
    "            pass\n"
    "        if target.owner in self.auto_players:\n"
    "            if not is_worth_using(attacker, target, melee=melee):",
)

# 5. Sickening Impact likewise - the second module that had it.
probe(
    "Sickening Impact pre-filters the human's prompt",
    G("dlc_sickening_impact.py"),
    "        if not self.can_use(squad):\n            return False",
    "        if not self.can_use(squad) or not self.is_worth_using(squad):\n            return False",
)

# 6. Pestilent Fallout's gate goes back to dead code with no channel - the
#    enfeeble target picked by the AI's damage ranking for both sides.
probe(
    "Pestilent Fallout picks for the human again",
    G("pestilent_fallout.py"),
    """        if (len(candidates) == 1 or shooter_squad.owner in self.auto_players
                or self.decision_manager is None):
            return self._use(shooter_squad, self._pick(shooter_squad, candidates))""",
    """        if True:
            return self._use(shooter_squad, self._pick(shooter_squad, candidates))""",
)

# 7. Word of the Phoenix's gate goes dead again - it fires for whichever
#    player's Command phase it is, Player 1 included.
probe(
    "Word of the Phoenix resolves itself for everyone",
    G("word_of_the_phoenix.py"),
    "        if squad.owner not in self.auto_players and self.decision_manager is not None:",
    "        if False:",
)

# 8. Bounty Hunters marks an enemy for the human's own units again.
probe(
    "Bounty Hunters picks the human's bounty",
    G("bounty_hunters.py"),
    "            if (hunter.owner not in self.auto_players\n"
    "                    and self.decision_manager is not None and len(enemies) > 1):",
    "            if False:",
)
