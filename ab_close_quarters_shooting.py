"""A/B probes at the SOURCE for rule 10.06's close-quarters targeting.

Each probe restores one clause of the pre-fix world in game/shooting.py and
must make test_close_quarters_shooting.py go red. A probe that does not bite is
a finding about the TEST, not about the code.

Run: python ab_close_quarters_shooting.py
"""
import io, os, re, shutil, subprocess, sys

SHOOTING = os.path.join("game", "shooting.py")
SUITE = "test_close_quarters_shooting.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_pycache():
    # These probes write and restore the same file within one second, which is
    # exactly the __pycache__ race CLAUDE.md records as a repeated source of
    # phantom failures.
    for root, dirs, _f in os.walk("."):
        for n in list(dirs):
            if n == "__pycache__":
                shutil.rmtree(os.path.join(root, n), ignore_errors=True)
                dirs.remove(n)


def run():
    clear_pycache()
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    t = out.stdout + out.stderr
    m = re.search(r"(\d+)/(\d+) checks passed", t)
    return (int(m.group(1)), int(m.group(2)), t) if m else (None, None, t)


FIXED_BRANCH = """                if not is_monster_or_vehicle_unit(attacking_squad):
                    return False
                if target_squad.is_engaged(all_tokens):
                    return False"""

PROBES = [
    # The whole pre-fix world: an engaged unit could only ever shoot the unit
    # it was locked with, whoever it was. This is the report.
    ("the pre-fix world - engaged means one target only (THE REPORT)", SHOOTING,
     FIXED_BRANCH,
     "                return False"),
    # Widened to everybody: the half the report did NOT ask for.
    ("widened to INFANTRY with pistols too", SHOOTING,
     "                if not is_monster_or_vehicle_unit(attacking_squad):\n                    return False\n",
     ""),
    # Rule 03.04 dropped from the new branch: a MONSTER could fire into
    # somebody else's melee.
    ("rule 03.04 dropped for the far unit", SHOOTING,
     "                if target_squad.is_engaged(all_tokens):\n                    return False\n        elif",
     "        elif"),
    # The malus label before it had to tell the two halves apart.
    ("the old single close-quarters malus label", SHOOTING,
     """            if not is_close_quarters(weapon):
                modifiers.append(Modifier(1, "Close-Quarters (non-[CLOSE-QUARTERS] weapon)"))
            elif not targets_engaged_unit:
                modifiers.append(Modifier(1, "Close-Quarters (target not engaged with this unit)"))""",
     """            if not (is_close_quarters(weapon) and targets_engaged_unit):
                modifiers.append(Modifier(1, "Close-Quarters (non-[CLOSE-QUARTERS] weapon)"))"""),
    # And the malus itself: without it, shooting out of a melee would be free.
    ("the close-quarters malus removed entirely", SHOOTING,
     "            targets_engaged_unit = self.active_squad.is_engaged_with(target_squad)",
     "            targets_engaged_unit = True"),
]

base, total, txt = run()
if base is None:
    print("BASELINE DID NOT RUN:\n" + txt[-1500:])
    raise SystemExit(2)
print("baseline: %s/%s\n" % (base, total))

bad = 0
for label, path, new, old in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
        bad += 1
        continue
    try:
        write(path, src.replace(new, old))
        got, tot, t = run()
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < base:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < base:
            for line in t.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:110])
                    break
    finally:
        write(path, src)

clear_pycache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
