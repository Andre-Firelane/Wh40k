"""A/B probes for the two reports of 2026-09-08, at the SOURCE.

  1. "der grosse necron warrior squad hat den avatar of khaine gecharged" -
     the tactical charge decision was given the odds and no valuation at all,
     so a charge worth 8 points a turn that costs 89 read exactly like one
     that wins the game.
  2. "die necrons kommen immer nicht so richtig von ihrem home objective weg"
     - an enemy anywhere within 12" switched the whole over-garrison pass off
     for that objective, so any number of units could sit on it for the rest
     of the battle.

Each probe restores ONE half of the pre-fix world and has to make its own
suite red. The last two restore a whole pre-fix world.
"""

import io
import os
import re
import shutil
import subprocess
import sys

DRIVER = os.path.join("ai", "agent_driver.py")
GEOMETRY = os.path.join("game", "geometry.py")

REPORT = "test_report_20260908.py"
OVER = "test_over_garrison.py"
HOME = "test_home_garrison.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    # The documented __pycache__ race: these probes rewrite and restore inside
    # the same second, so a stale .pyc reports the PREVIOUS run's result.
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


# --------------------------------------------------------------- report 1

# The declaration option as it was: odds, and nothing about what the charge
# is worth.
DECLARE_NEW = '''                    "declaring uses up this unit's charge for the phase whether or not the roll gets there"
                    # HOW LIKELY it is was added here for a reported failure;
                    # WHAT IT IS WORTH is the other half of the same sentence,
                    # and its absence is the reported one now. See
                    # _charge_trade_note(): a 92% charge that removes nothing
                    # and costs the squad 89 points a turn read exactly like a
                    # 92% charge that wins the game.
                    + _charge_trade_note(candidate, nearest_enemy)
                )'''
DECLARE_OLD = '''                    "declaring uses up this unit's charge for the phase whether or not the roll gets there"
                )'''

# The target choice as it was: two reachable enemies, two bare names.
TARGET_NEW = '''                        f"{squad.name}: charge {t.name}"
                        # The trade, per target. This is the choice the whole
                        # note exists for: two reachable enemies read as
                        # interchangeable when the option says only their
                        # names, and on the reported board they were worth 57
                        # and 7.5 points a turn.
                        + _charge_trade_note(squad, t)'''
TARGET_OLD = '''                        f"{squad.name}: charge {t.name}"'''

# The counter-swing half alone - the number the planner's own threat line does
# not carry either, and the one that separates this charge from a good one.
LOSS_NEW = '''        f" - it would remove about {got['models_killed_per_turn']:.1f} of its models "
        f"({gain:.0f} pts/turn) and that unit's own attacks would take about "
        f"{loss:.0f} pts/turn of this squad back for as long as the fight lasts"'''
LOSS_OLD = '''        f" - it would remove about {got['models_killed_per_turn']:.1f} of its models "
        f"({gain:.0f} pts/turn)"'''

# --------------------------------------------------------------- report 2

# The gate as it was: an enemy within 12" exempted the objective entirely.
GATE_NEW = '''        threat_oc = sum(objective_control.effective_oc(token, state.tokens, objective)
                        for token in _enemies_near_objective(objective, state, player))
        out.append((objective, threat_oc))
    return out'''
GATE_OLD = '''        threat_oc = sum(objective_control.effective_oc(token, state.tokens, objective)
                        for token in _enemies_near_objective(objective, state, player))
        if _enemies_near_objective(objective, state, player):
            continue
        out.append((objective, threat_oc))
    return out'''

# The bar itself, without the enemy's Objective Control: keep exactly one, as
# the pass always did. This is the half that decides HOW MANY stay.
BAR_NEW = '''            if keepers and oc > threat_oc:'''
BAR_OLD = '''            if keepers:'''

# The self-occupied position check, removed outright.
HULL_NEW = '''        if spot is not None and squad.models and id(squad) not in reserve_ids \\
                and entry.get("role") not in ("hold", "screen", "stage") \\
                and geometry.point_inside_hull(spot, [(m.x_in, m.y_in) for m in squad.models]):'''
HULL_OLD = '''        if False and spot is not None and squad.models and id(squad) not in reserve_ids \\
                and entry.get("role") not in ("hold", "screen", "stage") \\
                and geometry.point_inside_hull(spot, [(m.x_in, m.y_in) for m in squad.models]):'''

# ...and the half that keeps it narrow: without the passive exemption it would
# also strip the KEEPER's own garrison coordinate, which is a real order.
PASSIVE_NEW = '''                and entry.get("role") not in ("hold", "screen", "stage") \\'''
PASSIVE_OLD = '''                and entry.get("role") not in ("screen", "stage") \\'''

# A hull that reports everything as outside - the shape a wrong winding order
# or a flipped comparison would give.
INSIDE_NEW = '''        if (bx - ax) * (py - ay) - (by - ay) * (px - ax) < -eps:
            return False
    return True'''
INSIDE_OLD = '''        if (bx - ax) * (py - ay) - (by - ay) * (px - ax) < -eps:
            return False
    return False'''

# The renderer's re-export, turned back into a private copy - the drift the
# extraction exists to prevent.
REEXPORT_NEW = '''_convex_hull = geometry.convex_hull'''
REEXPORT_OLD = '''def _convex_hull(points):
    return geometry.convex_hull(points)'''

RENDERER = os.path.join("game", "renderer.py")

PROBES = [
    ("the declare option loses the trade",
     [(DRIVER, DECLARE_NEW, DECLARE_OLD)], REPORT),
    ("the target choice loses the trade",
     [(DRIVER, TARGET_NEW, TARGET_OLD)], REPORT),
    ("the counter-swing half of the note is dropped",
     [(DRIVER, LOSS_NEW, LOSS_OLD)], REPORT),
    ("a threatened objective exempts the whole pass again",
     [(DRIVER, GATE_NEW, GATE_OLD)], REPORT),
    ("...and the same, against the over-garrison suite",
     [(DRIVER, GATE_NEW, GATE_OLD)], OVER),
    ("the keeper count ignores the enemy's Objective Control",
     [(DRIVER, BAR_NEW, BAR_OLD)], OVER),
    ("the self-occupied position check is removed",
     [(DRIVER, HULL_NEW, HULL_OLD)], REPORT),
    ("...and without the passive exemption it strips real orders too",
     [(DRIVER, PASSIVE_NEW, PASSIVE_OLD)], OVER),
    ("point_inside_hull answers 'outside' for everything",
     [(GEOMETRY, INSIDE_NEW, INSIDE_OLD)], REPORT),
    ("the renderer keeps its own copy of the hull",
     [(RENDERER, REEXPORT_NEW, REEXPORT_OLD)], REPORT),
    ("_garrison_fitness is read from a third place again",
     [(DRIVER, BAR_NEW, BAR_OLD + '''
                pass
            if _garrison_fitness(squad, objective, state) and False:''')], HOME),
    ("THE WHOLE PRE-FIX WORLD for report 1",
     [(DRIVER, DECLARE_NEW, DECLARE_OLD), (DRIVER, TARGET_NEW, TARGET_OLD)], REPORT),
    ("THE WHOLE PRE-FIX WORLD for report 2",
     [(DRIVER, GATE_NEW, GATE_OLD), (DRIVER, HULL_NEW, HULL_OLD)], REPORT),
]


baselines = {}
for suite in (REPORT, OVER, HOME):
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-40s %d/%d" % (suite, got, total))
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
                print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
                ok = False
                bad += 1
                break
            write(path, src.replace(new, old))
        if not ok:
            continue
        got, total, text = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < baselines[suite]:
            verdict, detail = "BITES", "%d/%d" % (got, total)
        else:
            verdict, detail = "NO BITE", "%d/%d - FINDING ABOUT THE TEST" % (got, total)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:110])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
