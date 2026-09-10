"""A/B probes for the 2026-09-09 Insane Bravery report, at the SOURCE.

  "Insane bravery wird manchmal nicht angeboten"

Measured: the rule was never broken. FOUR separate clauses can each remove the
button, at four different moments, and none of them said anything - it was
spent (15.04's max_per_battle=1), or another stratagem had touched the same
squad this phase (15.01's targeted_this_phase, and Command Re-roll is a
stratagem), or the CP were short, or the unit no longer owed a roll (08.03).

So the fix is the SILENCE, not the rule: three (bool, reason) explainers in
the shape of game/actions.py's start_eligibility(), each with its boolean
DERIVED from it so one rule cannot have two disagreeing readers, and a hint
line where the button would have been.

The Command-phase narrowing STAYS (the user's decision), so the ten
out-of-turn battle-shock triggers it still misses are a named gap guarded by
test_event_chain_wiring.py section 21 - which pins the measured mechanism
rather than a story, because that is the shape whose justification went stale
on Mont'ka's [ASSAULT] gap while the assertion stayed green.

Each probe restores one piece of the pre-fix world and has to make its suite red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

BS = os.path.join("game", "battle_shock.py")
ST = os.path.join("game", "stratagems.py")
IB = os.path.join("game", "insane_bravery.py")
PANEL = os.path.join("game", "ui", "action_panel.py")

BRAVERY = "test_insane_bravery.py"
WIRING = "test_event_chain_wiring.py"


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


def run(suite):
    clear_cache()
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    if not match:
        return None, None, text
    return int(match.group(1)), int(match.group(2)), text


# ---------------------------------------- 1. battle_shock says nothing again
BS_NEW = "    def can_roll(self, squad):\n        return self.why_cannot_roll(squad)[0]"
BS_OLD = """    def can_roll(self, squad):
        if squad is None or self.rolling_squad is not None or squad in self.rolled_squad_ids:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_COMMAND:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        return self._qualifies(squad)"""

# ------------------------------------------- 2. stratagems say nothing again
ST_NEW = ("    def can_use(self, player, stratagem, targets, extra_cp=0):\n"
          "        return self.refusal(player, stratagem, targets, extra_cp) is None")
ST_OLD = """    def can_use(self, player, stratagem, targets, extra_cp=0):
        if (player, stratagem.name) in self.used_this_phase:
            return False
        if stratagem.max_per_battle is not None:
            if self.used_this_battle.get((player, stratagem.name), 0) >= stratagem.max_per_battle:
                return False
        return True"""

# ------------------------------------ 3. insane_bravery composes no reason
IB_NEW = "    def can_use(self, squad):\n        return self.why_not(squad)[0]"
IB_OLD = """    def can_use(self, squad):
        if squad is None or not self.battle_shock_controller.can_roll(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])"""

# ------------------------------------- 4. the panel goes back to can_use()
PANEL_NEW = """                    bravery_ok, bravery_why = insane_bravery_controller.why_not(squad)
                    if bravery_ok:"""
PANEL_OLD = """                    bravery_ok, bravery_why = insane_bravery_controller.can_use(squad), None
                    if bravery_ok:"""

# ------------------------------- 5. the reasons stop carrying their numbers
NUM_NEW = ('                return "already used %d of %d times this battle"'
           ' % (used, stratagem.max_per_battle)')
NUM_OLD = '                return "not available"'

CP_NEW = '            return "needs %d CP, you have %d%s" % (cost, have, dearer)'
CP_OLD = '            return "not available"'

# ------------- 6. the boolean and the reason DISAGREE - the real hazard
# The three probes above only unpick the derivation, so they fall on the source
# guards. This one makes the two readers genuinely diverge, which is what the
# (bool, reason) shape exists to prevent and what "can_use() agrees with
# why_not()" is there to catch: can_roll() forgets a clause why_cannot_roll()
# still enforces, so the panel would print a reason next to a live button.
_DEF = "    def can_roll(self, squad):" + chr(10)
DIVERGE_NEW = _DEF + "        return self.why_cannot_roll(squad)[0]"
DIVERGE_OLD = _DEF + "        return squad is not None and self._qualifies(squad)"

# --------------------------- 7. the named gap loses one of its ten triggers
GAP_NEW = '    "drone_harassment",\n'
GAP_OLD = ''

PROBES = [
    ("battle_shock's clauses say nothing again", [(BS, BS_NEW, BS_OLD)], BRAVERY),
    ("stratagems' clauses say nothing again", [(ST, ST_NEW, ST_OLD)], BRAVERY),
    ("insane_bravery composes no reason", [(IB, IB_NEW, IB_OLD)], BRAVERY),
    ("the panel goes back to a silent can_use()", [(PANEL, PANEL_NEW, PANEL_OLD)], BRAVERY),
    ("the once-per-battle reason drops its numbers", [(ST, NUM_NEW, NUM_OLD)], BRAVERY),
    ("the CP reason drops how much is needed", [(ST, CP_NEW, CP_OLD)], BRAVERY),
    ("the boolean and the reason DISAGREE", [(BS, DIVERGE_NEW, DIVERGE_OLD)], BRAVERY),
    ("the named gap loses one of its ten triggers", [(WIRING, GAP_NEW, GAP_OLD)], WIRING),
]

print(__doc__.strip())
print()
baselines = {}
for _suite in sorted({p[2] for p in PROBES}):
    got, total, _t = run(_suite)
    baselines[_suite] = got
    print("BASELINE %-32s %s/%s" % (_suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {}
    try:
        ok = True
        for path, new, old in edits:
            originals.setdefault(path, read(path))
            src = read(path)
            if src.count(new) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)"
                      % (label, path, src.count(new)))
                ok = False
                bad += 1
                break
            write(path, src.replace(new, old))
        if not ok:
            continue
        got, tot, text = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < baselines[suite]:
            verdict, detail = "BITES", "%d/%d" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%d/%d - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL"):
                    print("             " + line.strip()[:110])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
