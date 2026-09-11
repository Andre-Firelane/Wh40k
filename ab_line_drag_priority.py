"""A/B probes for the 2026-09-11 line-drag ordering request, at the SOURCE.

  "wenn ich den drag move mache, wobei sich die modelle an meiner gezogenen
   linie aufreihen. wie ist da die reihenfolge momentan? ich haette gerne eine
   prioliste. ganz vorne soll es losgehen mit Charactere, dann squadleader,
   dann spezialwaffen."

The answer to "wie ist da die reihenfolge momentan" was: there is none.
line_positions() sorted purely geometrically - whoever already stood nearest
the drawn line became rank 1 - so a character landed wherever it happened to
be. Measured on the real `Pathfinder Team + Darkstrider` with the character at
the back, before the change:

    rank 1 (the drawn line):  SGT Shas'ui | spec | spec | spec
    rank 2:                   ---- | ---- | ---- | ----
    rank 3 (at the back):     ---- | ---- | CHAR Darkstrider

attach() appends leader models to the END of squad.models, and geometry did
the rest.

A latent crash was found in the same function while checking its callers and
is fixed with it: SetupController passes placing_models, which during a rule
01.02.03 return is a genuine SUBSET, while line_positions() read squad.models
and indexed origins by the subset - IndexError, i.e. a right-drag in the
middle of a Reanimation placement crashed the game.

Each probe restores one piece of the pre-fix world and has to make its suite
red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

LAYOUT = os.path.join("game", "formation_layout.py")
FRONT = os.path.join("game", "front_rank.py")
MOVE = os.path.join("game", "movement.py")
DRAG = os.path.join("game", "line_drag.py")

SUITE = "test_line_drag.py"


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


# ------------------------------ 1. no priority at all - THE HEADLINE
ORDER_NEW = """    order = sorted(range(n), key=lambda i: (tier_of.get(id(models[i]), unranked),
                                            depth_proj(i), lateral_proj(i)))"""
ORDER_OLD = """    order = sorted(range(n), key=lambda i: (depth_proj(i), lateral_proj(i)))"""

# --------------------------------------------- 2. the tiers come out backwards
TIERS_NEW = "    return (characters, sergeants, specials)"
TIERS_OLD = "    return (specials, sergeants, characters)"

# ------------- 3. geometry stops being the tiebreak INSIDE a tier
# Squad order instead, which is what a flat priority list would give - and is
# exactly the thing that makes two same-ranked models' walks cross.
TIE_NEW = """                                            depth_proj(i), lateral_proj(i)))"""
TIE_OLD = """                                            i, i))"""

# ------------------------------------------- 4. the ladder loses its middle rung
LADDER_NEW = """    for rung in (tiers, tiers[:1]):"""
LADDER_OLD = """    for rung in (tiers,):"""

# -------------------------- 5. the legality sweep measures a different block
SWEEP_NEW = """                origins=origins, frontage=frontage, gap_in=gap_in,
                priority=priority,
            )"""
SWEEP_OLD = """                origins=origins, frontage=frontage, gap_in=gap_in,
            )"""

# ------------------ 6. the melee-only confusion: the AI's set, not the player's
MELEE_NEW = """    pool = list(models) if models is not None else list(getattr(squad, "models", []))"""
MELEE_OLD = """    return (front_rank_models(squad), [], [])
    pool = list(models) if models is not None else list(getattr(squad, "models", []))"""

# ---------------------------------- 7. the subset crash comes back
SUBSET_NEW = """    models = list(models) if models is not None else squad.models"""
SUBSET_OLD = """    models = squad.models"""


PROBES = [
    ("THE HEADLINE: no priority, purely geometric again",
     [(LAYOUT, ORDER_NEW, ORDER_OLD)], SUITE),
    ("the tiers come out backwards", [(FRONT, TIERS_NEW, TIERS_OLD)], SUITE),
    ("geometry stops breaking ties inside a tier", [(LAYOUT, TIE_NEW, TIE_OLD)], SUITE),
    ("the ladder loses its characters-only rung", [(MOVE, LADDER_NEW, LADDER_OLD)], SUITE),
    ("the legality sweep ignores the priority", [(DRAG, SWEEP_NEW, SWEEP_OLD)], SUITE),
    ("drag_priority_tiers returns the AI's melee set", [(FRONT, MELEE_NEW, MELEE_OLD)], SUITE),
    ("the subset crash comes back", [(LAYOUT, SUBSET_NEW, SUBSET_OLD)], SUITE),
    ("THE WHOLE PRE-FIX WORLD",
     [(LAYOUT, ORDER_NEW, ORDER_OLD), (LAYOUT, SUBSET_NEW, SUBSET_OLD)], SUITE),
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
