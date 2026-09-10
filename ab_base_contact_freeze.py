"""A/B probes for the 2026-09-09 base-contact house rule, at the SOURCE.

  User: "Modelle in Base contact duerfen weder Pile in noch consolidate moves
   durchfuehren... als Base contact wuerde ich weniger als 0,2 Zoll Abstand
   definieren."

  ...and, separately: "denke aber daran, dass bei einem rueckzug models
   natuerlich den base contact verlassen koennen."

MEASURED BEFORE ANY CHANGE: the rule existed in ONE place - a `continue` in
ai/agent_driver.py's phase-2 spreading loop, AI only, pile-in only, against the
single aimed target squad, at 0.15" (PILE_IN_CLEARANCE_IN 0.1 plus a bare 0.05
literal the same line uses for a CHARGE at 1.05"). It was written as an
optimisation, not a rule gate. The human side had nothing at all, and
Consolidation had nothing on either side.

Probe 4 is the one that matters most: it puts "fall_back" into the frozen set,
which is the failure mode the user warned about - a unit in base contact that
can never retreat out of it. If that probe ever stops biting, the counter-check
protecting retreats has gone.
"""

import io
import os
import re
import shutil
import subprocess
import sys

BC = os.path.join("game", "base_contact.py")
MOVE = os.path.join("game", "movement.py")
DRIVER = os.path.join("ai", "agent_driver.py")

SUITE = "test_base_contact.py"
MELEE = "test_melee_engagement.py"


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


# ----------------------------------------- 1. the whole pre-fix world
RULE_NEW = """    if move_mode not in FROZEN_MOVE_MODES:
        return False
    if model is None or squad is None:
        return False
    return in_base_contact(model, enemy_models(squad, all_tokens))"""
RULE_OLD = """    return False   # probe: the rule does not exist"""

# --------------------------------- 2. the human can drag again (clamp_move)
CLAMP_NEW = """        if base_contact.is_frozen(token, self.selected_squad, self.all_tokens, self.move_mode):
            return origin"""
CLAMP_OLD = """        pass  # probe: the clamp carries no contact term"""

# ------------------------------- 3. a frozen model can be picked up again
PICKUP_NEW = """            and not base_contact.is_frozen(token, self.selected_squad,
                                           self.all_tokens, self.move_mode)"""
PICKUP_OLD = ""

# ------------------- 4. THE RETREAT TRAP the user warned about
FROZEN_SET_NEW = '''FROZEN_MOVE_MODES = ("pile_in", "consolidate")'''
FROZEN_SET_OLD = '''FROZEN_MOVE_MODES = ("pile_in", "consolidate", "fall_back",
                     "retro_thrusters_fall_back")'''

# ---------------------- 5. the threshold drops back to the AI's old 0.15"
GAP_NEW = "BASE_CONTACT_GAP_IN = 0.2"
GAP_OLD = "BASE_CONTACT_GAP_IN = 0.15"

# ------------------------------------------ 6. corpses pin models again
DEAD_NEW = """    return [t for t in all_tokens
            if t.squad is not None and t.squad.owner != squad.owner and not t.is_dead()]"""
DEAD_OLD = """    return [t for t in all_tokens
            if t.squad is not None and t.squad.owner != squad.owner]"""

PROBES = [
    ("the rule does not exist (the whole pre-fix world)", [(BC, RULE_NEW, RULE_OLD)], SUITE),
    ("clamp_move() carries no contact term", [(MOVE, CLAMP_NEW, CLAMP_OLD)], SUITE),
    ("a frozen model can be picked up again", [(MOVE, PICKUP_NEW, PICKUP_OLD)], SUITE),
    ("A RETREAT IS FROZEN TOO - the trap the user warned about",
     [(BC, FROZEN_SET_NEW, FROZEN_SET_OLD)], SUITE),
    ("the threshold drops to the AI's old 0.15\"", [(BC, GAP_NEW, GAP_OLD)], SUITE),
    ("a model killed this frame still pins its neighbours", [(BC, DEAD_NEW, DEAD_OLD)], SUITE),
]

print(__doc__.strip())
print()
baselines = {}
for _suite in sorted({p[2] for p in PROBES}):
    got, total, _t = run(_suite)
    baselines[_suite] = got
    print("BASELINE %-28s %s/%s" % (_suite, got, total))
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
