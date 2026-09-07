"""A/B probes for the end-of-Fight-phase reaction seam, at the SOURCE.

Two independent bugs shared one cause, and each half has to be restorable on
its own - a probe that only puts back one of them proves less than the report
(error class 16):

  1. main.py read turn_tracker.turn_owner AFTER advance_phase() had flipped it,
     so all four offers at that seam named the WRONG side. Reported for Wall of
     Mirrors: "Frage nach Wall of Mirrors kam am Anfang der Gegner Runde".
  2. The controllers expressed their WHEN as a live `phase == PHASE_FIGHT`
     test, which by then can never hold - so accepting did nothing at all.
     Reported: "funktioniert auch nicht".

Each probe restores one piece and reruns the suite. A probe that does NOT go
red is a finding about the test, not a clean bill of health.
"""

import io
import os
import re
import shutil
import subprocess
import sys

MAIN = "main.py"
MIRRORS = os.path.join("game", "kauyon_wall_of_mirrors.py")
COV = os.path.join("game", "guardian_cost_of_victory.py")
WEBWAY = os.path.join("game", "warhost_webway_tunnel.py")
WINDOW = os.path.join("game", "phase_window.py")
TAU_SUITE = "test_tau_detachment_stratagems.py"
AELDARI_SUITE = "test_aeldari_detachment_stratagems.py"
WIRING_SUITE = "test_event_chain_wiring.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    # The probes rewrite modules within the same second, which is exactly the
    # __pycache__ race this repo has recorded as a phantom failure.
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
    # ---- half 1: the wrong player -------------------------------------
    ("Wall of Mirrors offered against the post-advance turn_owner", MAIN,
     "            wall_of_mirrors_controller.offer_at_end_of_fight_phase(mover_before)",
     "            wall_of_mirrors_controller.offer_at_end_of_fight_phase(turn_tracker.turn_owner)",
     WIRING_SUITE),
    ("Cost of Victory offered against the post-advance turn_owner", MAIN,
     "            cost_of_victory_controller.offer_at_end_of_fight_phase(\n"
     "                {t.squad for t in state.tokens if t.squad is not None},\n"
     "                mover_before)",
     "            cost_of_victory_controller.offer_at_end_of_fight_phase(\n"
     "                {t.squad for t in state.tokens if t.squad is not None},\n"
     "                turn_tracker.turn_owner)",
     WIRING_SUITE),

    # ---- half 2: the dead phase guard ---------------------------------
    ("Wall of Mirrors back on a live phase test", MIRRORS,
     "        if not self._window.is_open(squad.owner):\n            return False",
     "        from game.turn import PHASE_FIGHT\n"
     "        if self.turn_tracker.phase != PHASE_FIGHT:\n            return False",
     TAU_SUITE),
    ("Cost of Victory back on a live phase test", COV,
     "        if not self._window.is_open(squad.owner):\n            return False",
     "        from game.turn import PHASE_FIGHT\n"
     "        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:\n"
     "            return False",
     AELDARI_SUITE),
    ("Webway Tunnel back on a live phase test", WEBWAY,
     "        if not self._window.is_open(squad.owner):\n            return False",
     "        from game.turn import PHASE_FIGHT\n"
     "        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:\n"
     "            return False",
     AELDARI_SUITE),

    # ---- the window itself --------------------------------------------
    ("a window that never closes (a stale prompt stays answerable)", WINDOW,
     "    def close(self):\n        self._player = None",
     "    def close(self):\n        pass",
     TAU_SUITE),
    ("a window that is never armed", MIRRORS,
     "        self._window.arm(reactor)",
     "        pass",
     TAU_SUITE),
]

BASE = {}
for _suite in (TAU_SUITE, AELDARI_SUITE, WIRING_SUITE):
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (_suite, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = got
    print("baseline %-46s %s/%s" % (_suite, got, total))
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
