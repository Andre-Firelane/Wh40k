"""A/B probes for the TITANIC reader consolidation (Etappe 0).

Each probe restores ONE piece of the pre-fix world AT THE SOURCE and must make
the suite that covers it go red. A probe that does not bite is a finding about
the TEST, not an all-clear.

THE PRE-FIX WORLD, measured: TITANIC was answered three ways, and four sites
read `getattr(profile, "titanic", False)` - a field UnitProfile does not
declare, so they were unconditionally False. Nothing built carried the keyword,
so nothing could tell the difference. The Monolith is the first carrier, which
is why this is repaid before the datasheet arrives rather than after.
"""
import io, os, re, shutil, subprocess, sys

PROBES = [
    ("the shared reader always answers False (the pre-fix world, all sites)",
     [("game/titanic.py",
       "    if squad is None:\n        return False\n    return unit_has_datasheet_keyword(squad, TITANIC_KEYWORD)",
       "    return False")],
     ["test_actions.py", "test_support_weapon_platforms.py"]),

    ("actions.py 16.01 reads the profile flag again (engaged carve-out)",
     [("game/actions.py",
       "    if not titanic.is_titanic_unit(squad) and _is_engaged(squad, tokens):",
       '    if not _flag(profile, "titanic") and _is_engaged(squad, tokens):')],
     ["test_titanic_reader.py", "test_actions.py"]),

    ("actions.py blocks_shooting reads the profile flag again",
     [("game/actions.py",
       "        return not titanic.is_titanic_unit(squad)",
       '        return not _flag(squad.models[0].profile, "titanic") if squad.models else True')],
     ["test_actions.py"]),

    ("structural_collapse reads the profile flag again (the D-cannon clause)",
     [("game/structural_collapse.py",
       "    return titanic.is_titanic_unit(target_squad)",
       '    models = getattr(target_squad, "models", None) or ()\n'
       '    return any(getattr(m.profile, "titanic", False) for m in models)')],
     ["test_support_weapon_platforms.py"]),

    ("elemental_ensnarement reads the profile flag again (cross-faction)",
     [("game/elemental_ensnarement.py",
       "            if titanic.is_titanic_unit(other):",
       '            if any(getattr(m.profile, "titanic", False) for m in _living(other)):')],
     ["test_titanic_reader.py", "test_exodites.py"]),

    ("wraith_construct stops re-exporting and defines its own (two readers)",
     [("game/wraith_construct.py",
       "from game.titanic import TITANIC_KEYWORD, is_titanic_unit  # noqa: F401 - re-exported",
       'TITANIC_KEYWORD = "TITANIC"\n\n\ndef is_titanic_unit(squad):\n    return False')],
     ["test_titanic_reader.py"]),
]


def clear_cache():
    """The documented __pycache__ race: these probes rewrite and restore inside
    the same second, so a stale .pyc reports the PREVIOUS run's result."""
    for root, dirs, _ in os.walk("."):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run(suite):
    if not os.path.exists(suite):
        return None, None
    clear_cache()
    out = subprocess.run([sys.executable, suite], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    m = re.search(r"(\d+)/(\d+) checks passed", out.stdout + out.stderr)
    if not m:
        return None, None          # crashed - counts as red
    return int(m.group(1)), int(m.group(2))


baselines = {}
for _, _, suites in PROBES:
    for s in suites:
        if s not in baselines:
            baselines[s] = run(s)
print("baselines:")
for s, (g, t) in baselines.items():
    print("   %-45s %s" % (s, "MISSING" if g is None else "%d/%d" % (g, t)))
print()

bad = 0
for label, edits, suites in PROBES:
    originals = {}
    ok = True
    for path, old, new in edits:
        src = io.open(path, encoding="utf-8").read()
        if src.count(old) != 1:
            print("NO ANCHOR (%d)  %s" % (src.count(old), label))
            ok = False
            break
        originals[path] = src
        io.open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
    if not ok:
        for p, s in originals.items():
            io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        bad += 1
        continue
    try:
        verdicts = []
        for s in suites:
            base = baselines.get(s, (None, None))[0]
            got, tot = run(s)
            if base is None:
                verdicts.append((s, "NO SUITE", ""))
            elif got is None:
                verdicts.append((s, "BITES", "(crashed - counts as red)"))
            elif got < base:
                verdicts.append((s, "BITES", "%d/%d" % (got, tot)))
            else:
                verdicts.append((s, "NO BITE", "%d/%d" % (got, tot)))
    finally:
        for p, s in originals.items():
            io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    bit = any(v == "BITES" for _, v, _ in verdicts)
    print("%-9s %s" % ("bites" if bit else "NO BITE", label))
    for s, v, d in verdicts:
        print("            %-45s %-8s %s" % (s, v, d))
    if not bit:
        bad += 1

clear_cache()
print("\nprobes: %d, all biting: %s" % (len(PROBES), not bad))
raise SystemExit(1 if bad else 0)
