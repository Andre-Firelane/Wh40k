"""A/B probes for the three Stratagems that were never offered, at the SOURCE.

Each restores one piece of the pre-fix world and reruns the suite. A probe that
does NOT go red is a finding about the test, not a clean bill of health.

  * Aggressive Mobility refused movement_controller.selected_squad - the only
    squad the panel ever asks about ("wird nie angeboten").
  * Marker Beacon was a Movement-phase panel button reading an objective
    control snapshot that is only recomputed at a phase boundary, so the case
    it exists for was unreachable ("wird nie angeboten").
  * Pinpoint Counter-Offensive dropped a death whose killer the sweep could not
    name, which is precisely the wiped-by-the-last-shot case ("wird nie
    angeboten"), and clobbered a shared _pending slot when two units died at
    once.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
MAIN = "main.py"
AGG = os.path.join("game", "montka_aggressive_mobility.py")
BEACON = os.path.join("game", "aac_marker_beacon.py")
PIN = os.path.join("game", "montka_pinpoint_counter_offensive.py")
SHOOTING = os.path.join("game", "shooting.py")
SUITE = "test_tau_detachment_stratagems.py"
WIRING = "test_event_chain_wiring.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    # The probes rewrite modules within the same second - the documented
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
    # One hazard roll per attack GROUP instead of per WEAPON - the second
    # report ("viel zu wenig ... fuer jede waffe, die abgefeuert wurde").
    ("the hazard ledger back to one roll per attack group", SHOOTING,
     "            len(pairs) if pairs and self._adjusted_weapon(pairs, target_squad).hazardous"
     + NL + "            else 0)",
     "            bool(pairs) and self._adjusted_weapon(pairs, target_squad).hazardous)",
     SUITE),
    # [HAZARDOUS] read off the PRINTED weapon, so a granted one never counted.
    # Restores BOTH halves of the pre-fix world at once - the printed profile
    # AND the per-group flag - because that is what shipped.
    ("the hazard ledger back on the printed weapon", SHOOTING,
     "        self._pending_subgroups_hazardous = (" + NL
     + "            len(pairs) if pairs and self._adjusted_weapon(pairs, target_squad).hazardous"
     + NL + "            else 0)",
     "        self._pending_subgroups_hazardous = bool(pairs) and pairs[0][1].hazardous",
     SUITE),
    ("Aggressive Mobility refusing the selected squad again", AGG,
     '            if squad in getattr(self.movement_controller, "advanced_squad_ids", ()):\n'
     '                return False',
     '            if getattr(self.movement_controller, "selected_squad", None) is squad:\n'
     '                return False',
     SUITE),

    ("Marker Beacon back on a live Movement-phase test", BEACON,
     "        if not self._window.is_open(squad.owner):\n            return False",
     "        from game.turn import PHASE_MOVEMENT\n"
     "        if self.turn_tracker is None or self.turn_tracker.phase != PHASE_MOVEMENT:\n"
     "            return False",
     SUITE),
    ("Marker Beacon never offered at the boundary", MAIN,
     "            marker_beacon_controller.offer_at_end_of_movement_phase(mover_before)",
     "            pass",
     SUITE),

    ("Pinpoint dropping a death whose killer is unknown", PIN,
     "        if killer_squad is None:\n"
     "            if self._could_offer(dead_squad):\n"
     "                self._owed.append(dead_squad)\n"
     "            return False",
     "        if killer_squad is None:\n            return False",
     SUITE),
    ("Pinpoint's owed deaths never drained", PIN,
     "        owed, self._owed = self._owed, []",
     "        owed, self._owed = [], []",
     SUITE),
    ("Pinpoint back on a shared _pending slot written at request() time", PIN,
     "            self._pending = (dead, killer)" + NL
     + "            used = self.stratagem_controller.use(dead.owner, self._stratagem, [dead])",
     "            used = self.stratagem_controller.use(dead.owner, self._stratagem, [dead])",
     SUITE),
    ("Pinpoint's owed list outliving its phase", PIN,
     '    def reset_phase(self):\n        """An owed death does not outlive the phase it happened in."""\n'
     "        self._owed = []",
     '    def reset_phase(self):\n        """An owed death does not outlive the phase it happened in."""\n'
     "        pass",
     SUITE),
    ("Pinpoint never answered from the after-activation hooks", MAIN,
     "        pinpoint_controller.maybe_offer(shooter_squad)",
     "        pass",
     SUITE),
]

BASE = {}
for _suite in (SUITE, WIRING):
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (_suite, text[-2000:]))
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
