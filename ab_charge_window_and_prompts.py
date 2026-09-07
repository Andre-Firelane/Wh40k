"""A/B probes for the charge reaction window, Photon Grenades' embark check,
Solid-image's two-step board pick and the Resurrection Orb's decline memory.

Each restores one piece of the pre-fix world and reruns the suite that owns it.
A probe that does NOT go red is a finding about the test, not a clean bill of
health.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
CHARGE = os.path.join("game", "charge.py")
EMBARK = os.path.join("game", "kauyon_combat_embarkation.py")
PHOTON = os.path.join("game", "kauyon_photon_grenades.py")
SOLID = os.path.join("game", "enh_solid_image_projection.py")
ORB = os.path.join("game", "resurrection_orb.py")
TAU = "test_tau_detachment_stratagems.py"
ENH = "test_tau_enhancements.py"
GATES = "test_deterministic_gates.py"
PICK = "test_unit_pick.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    # These rewrite modules within the same second - the documented
    # __pycache__ race that has produced phantom failures in this repo.
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


PROBES = [
    # --- the charge window ------------------------------------------------
    ("Combat Embarkation not re-opening target declaration", EMBARK,
     "                reopened = self.charge_controller.reopen_target_selection(squad)",
     "                reopened = False",
     TAU),
    ("the re-opened window still falling through into the move", CHARGE,
     "                    and not self._declaration_reopened)",
     "                    )",
     TAU),
    ("the embarked unit left in the declared targets", CHARGE,
     "        if dropped_squad is not None and dropped_squad in self.charge_targets:" + NL
     + "            self.charge_targets.remove(dropped_squad)",
     "        pass",
     TAU),

    # --- Photon Grenades --------------------------------------------------
    ("Photon Grenades offered to a unit inside a transport", PHOTON,
     '            if getattr(squad, "embarked_in", None) is not None:' + NL
     + "                continue",
     "            pass",
     TAU),
    ("...and to one wiped out in the same frame", PHOTON,
     '            if not any(getattr(t, "squad", None) is squad for t in self.all_tokens):' + NL
     + "                continue",
     "            pass",
     TAU),

    # --- Solid-image Projection Unit --------------------------------------
    ("Solid-image back to one prompt naming each unit TWICE", SOLID,
     "            options = [" + NL
     + "                (target.name, (lambda t=target: self._offer_destination(player, t)), target)" + NL
     + "                for target in targets" + NL
     + "            ]",
     "            options = []" + NL
     + "            for target in targets:" + NL
     + '                options.append((f"redeploy {target.name}",' + NL
     + "                                (lambda t=target: self.choose(player, t, REDEPLOY))))" + NL
     + '                options.append((f"{target.name} into Reserves",' + NL
     + "                                (lambda t=target: self.choose(player, t, RESERVES))))",
     ENH),

    # --- the Resurrection Orb --------------------------------------------
    ("the orb forgetting a decline (the report)", ORB,
     "        candidates = sorted((s for s in squads if s.owner == player and self.can_use(s)" + NL
     + "                             and not self.declined_unchanged(s)),",
     "        candidates = sorted((s for s in squads if s.owner == player and self.can_use(s)),",
     GATES),
    ("...and the decline never being recorded at all", ORB,
     "        self._declined_at[id(squad)] = reanimation_protocols.recoverable_wounds(squad)",
     "        pass",
     GATES),
    ("a decline that never lifts, so new losses go unasked", ORB,
     "        return reanimation_protocols.recoverable_wounds(squad) <= was",
     "        return True",
     GATES),
]

BASE = {}
for _suite in (TAU, ENH, GATES, PICK):
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:%s%s" % (_suite, NL, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = got
    print("baseline %-42s %s/%s" % (_suite, got, total))
print()

bad = 0
for label, path, new, old, suite in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
        bad += 1
        continue
    try:
        write(path, src.replace(new, old))
        got, tot, out = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < BASE[suite]:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < BASE[suite]:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:104])
                    break
    finally:
        write(path, src)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
