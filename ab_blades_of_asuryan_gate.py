"""A/B probes for the 2026-09-08 Blades of Asuryan report, at the SOURCE.

  "ich konnte zwar mit asurmen schiessen, aber nicht mit dem rest meines
   avengers squads. das umwandeln der waffen in pistol hat wohl nicht
   geklappt."

[PISTOL] is read in TWO places: the adjuster chain (the damage maths) and the
eligibility gate that decides whether an ENGAGED unit may shoot at all (10.06).
The grant reached only the chain, so the chain handed [PISTOL] to 6 of 6 ranged
weapons while the gate saw 1 of 6 - Asurmen's Bloody Twins, printed [PISTOL],
which is why he alone could fire.

Each probe restores one half of the pre-fix world and has to make its suite red.
The last one restores the whole of it.

THE FIRST PROBE IS THE LOAD-BEARING ONE: it leaves the adjuster chain granting
exactly as it does today and blinds ONLY the gate - the faithful shipped world,
not a version with the Stratagem switched off. A probe that disabled the grant
outright would prove something much weaker.
"""

import io
import os
import re
import shutil
import subprocess
import sys

SHOOT = os.path.join("game", "shooting.py")
WIRING_FILE = "test_event_chain_wiring.py"

AELDARI = "test_aeldari_detachment_stratagems.py"
CQ = "test_close_quarters_shooting.py"
WIRING = WIRING_FILE


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


# ---------------------------------------------------------------- the gate
# THE SHIPPED WORLD: the chain still grants, the gate reads the printed flag
# only. This is the bug as reported.
GATE_NEW = """    if weapon.close_quarters or weapon.pistol:
        return True
    # Blades of Asuryan (Guardian Battlehost): "until the end of the phase,
    # ranged weapons equipped by models in your unit have the [PISTOL]
    # ability". Its own adjusted_weapon() applies the RANGED gate and the
    # never-a-downgrade rule, so this asks it rather than re-reading the flag.
    granted = guardian_blades_of_asuryan.adjusted_weapon(weapon, squad)
    return bool(granted is not weapon and granted.pistol)"""

GATE_OLD = """    return weapon.close_quarters or weapon.pistol"""

# ------------------------------------------------- the two gate call sites,
# each on its own: available_shooting_types() decides whether the unit gets a
# Close-Quarters option at all, _weapon_eligible_for_type() decides which of
# its weapons may then fire. The report is BOTH, and either alone leaves the
# squad half-armed.
TYPES_NEW = ("    has_close_quarters = any(is_close_quarters(w, squad) "
             "for plist in groups.values() for _, w in plist)")
TYPES_OLD = ("    has_close_quarters = any((w.close_quarters or w.pistol) "
             "for plist in groups.values() for _, w in plist)")

ELIGIBLE_NEW = ("        return True if is_monster_or_vehicle_unit(squad) "
                "else is_close_quarters(weapon, squad)")
ELIGIBLE_OLD = ("        return True if is_monster_or_vehicle_unit(squad) "
                "else (weapon.close_quarters or weapon.pistol)")

# ------------------------------------------------------------ rule 24.07's
# side lock. A granted [PISTOL] puts the weapon on the pistol side; reading
# the printed flag here splits a unit whose weapons are now all pistols.
SIDE_NEW = '    return "close_quarters" if is_close_quarters(weapon, squad) else "other"'
SIDE_OLD = '    return "close_quarters" if (weapon.close_quarters or weapon.pistol) else "other"'

# --------------------------------------------------------------- the guard
# Make the parameter optional again. Nothing breaks at once - which is the
# point: a default is how a missed caller becomes a silent no-op instead of a
# crash, and section 19 is what refuses it.
DEFAULT_NEW = "def is_close_quarters(weapon, squad):"
DEFAULT_OLD = "def is_close_quarters(weapon, squad=None):"

# The grantor's own name out of the gate's body: the set difference must
# notice even while behaviour is untouched.
NAMED_NEW = "    granted = guardian_blades_of_asuryan.adjusted_weapon(weapon, squad)"
NAMED_OLD = ("    _grantor = guardian_blades_of_asuryan\n"
             "    granted = _grantor.adjusted_weapon(weapon, squad)")


PROBES = [
    ("the gate reads the printed flag only (THE REPORT)",
     [(SHOOT, GATE_NEW, GATE_OLD)], AELDARI),
    ("...and rule 10.06's own suite sees it too",
     [(SHOOT, GATE_NEW, GATE_OLD)], CQ),
    ("available_shooting_types() alone goes blind - no Close-Quarters option",
     [(SHOOT, TYPES_NEW, TYPES_OLD)], AELDARI),
    ("_weapon_eligible_for_type() alone goes blind - option, but no weapons",
     [(SHOOT, ELIGIBLE_NEW, ELIGIBLE_OLD)], AELDARI),
    ("24.07's side lock reads the printed flag",
     [(SHOOT, SIDE_NEW, SIDE_OLD)], CQ),
    ("the squad parameter becomes optional again",
     [(SHOOT, DEFAULT_NEW, DEFAULT_OLD)], WIRING),
    ("the grantor is no longer named in the gate's body",
     [(SHOOT, NAMED_NEW, NAMED_OLD)], WIRING),
    ("the WHOLE pre-fix world",
     [(SHOOT, GATE_NEW, GATE_OLD), (SHOOT, TYPES_NEW, TYPES_OLD),
      (SHOOT, ELIGIBLE_NEW, ELIGIBLE_OLD), (SHOOT, SIDE_NEW, SIDE_OLD)], AELDARI),
]


baselines = {}
for suite in (AELDARI, CQ, WIRING):
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-44s %d/%d" % (suite, got, total))
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
                print("  SKIP     %s: anchor not unique in %s" % (label, path))
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
        print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:112])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
