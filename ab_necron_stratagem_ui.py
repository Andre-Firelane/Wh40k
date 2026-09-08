"""A/B probes for the three Necron panel Stratagems.

Each probe restores one piece of a plausible broken world AT THE SOURCE, runs
test_necron_stratagem_ui.py, and puts it back. A probe that does NOT go red is
a finding about the TEST, so this file exits non-zero if any survives.

WHY THESE PROBES AND NOT OTHERS. The three buttons reach ActionPanel.draw() as
their own keyword arguments rather than through game/proactive_stratagems.py,
so section 14 of test_event_chain_wiring.py cannot see them and the only
standing proof was a substring of main.py. The probes therefore attack the two
things that substring cannot distinguish:

  * THE THREE-STAGE CHAIN. draw() -> _draw_dispatch() -> _draw_movement_ui(),
    and action_panel.py's own comment records the failure this catches: a
    parameter added to two of the three signatures crashes every frame.
  * THE WHEN. A button drawn in the wrong phase, or for the wrong player, or
    regardless of the detachment, all satisfy "the name appears in main.py".

Hungry Void gets its own pair, in both directions: it prints "Fight phase."
with no "Your", so ADDING an owner clause is as much a defect as removing one
from its two neighbours - and the Fight phase is the one place a real panel can
tell the difference, because can_select() admits both players there.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)

VOID = os.path.join("game", "protocol_hungry_void.py")
STORM = os.path.join("game", "protocol_sudden_storm.py")
TYRANT = os.path.join("game", "protocol_conquering_tyrant.py")
DYNASTY = os.path.join("game", "awakened_dynasty.py")
PANEL = os.path.join("game", "ui", "action_panel.py")

UI = "test_necron_stratagem_ui.py"
SUITES = (UI,)


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


# ------------------------------------------------------------------- edits

# 1. THE CHAIN, one stage at a time. Renaming the parameter in the LAST stage
# is the exact half-wiring action_panel.py's comment describes.
# The parameter name appears in all three signatures, so the anchor carries its
# NEIGHBOURS - _draw_movement_ui() is the only one that lists it between
# conquering_tyrant_controller and path_of_the_outcast_controller.
_LAST_STAGE = ("        conquering_tyrant_controller=None," + NL
               + "        hungry_void_controller=None," + NL
               + "        path_of_the_outcast_controller=None,")
_LAST_STAGE_OFF = ("        conquering_tyrant_controller=None," + NL
                   + "        hungry_void_controller_renamed=None," + NL
                   + "        path_of_the_outcast_controller=None,")

# ...and the forwarding hop INTO that stage, likewise pinned by its neighbour.
_FORWARD = ("            hungry_void_controller=hungry_void_controller," + NL
            + "            blooming_pestilence_controller=blooming_pestilence_controller,")
_FORWARD_OFF = "            blooming_pestilence_controller=blooming_pestilence_controller,"

# 2. HUNGRY VOID GAINS an owner clause it does not print.
_VOID_PHASE = ("            if self.turn_tracker.phase != PHASE_FIGHT:" + NL
               + "                return False")
_VOID_PHASE_OWNED = ("            if self.turn_tracker.phase != PHASE_FIGHT:" + NL
                     + "                return False" + NL
                     + "            if squad.owner != self.turn_tracker.turn_owner:" + NL
                     + "                return False")

# ...and LOSES its phase test, so it is offered in all five.
_VOID_PHASE_OFF = ("            if False:" + NL
                   + "                return False")

# 3. SUDDEN STORM loses the owner half of "YOUR Movement phase".
_STORM_OWNER = ("            if squad.owner != self.turn_tracker.turn_owner:" + NL
                + "                return False" + NL
                + "        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])" + NL
                + NL
                + "    def use(self, squad):")
_STORM_OWNER_OFF = ("        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])" + NL
                    + NL
                    + "    def use(self, squad):")

# 4. CONQUERING TYRANT loses its phase test entirely.
_TYRANT_PHASE = ("            if self.turn_tracker.phase != PHASE_SHOOTING:" + NL
                 + "                return False")
_TYRANT_PHASE_OFF = ("            if False:" + NL
                     + "                return False")

# 5. ...and its printed TARGET ledger.
_TYRANT_LEDGER = ("        if self.shooting_controller is not None:" + NL
                  + '            if squad in getattr(self.shooting_controller, "shot_squad_ids", ()) or ():' + NL
                  + "                return False")
_TYRANT_LEDGER_OFF = "        if False:" + NL + "            return False"

# 6. HUNGRY VOID loses its ledger too.
_VOID_LEDGER = ("        if self.fight_controller is not None:" + NL
                + '            if squad in getattr(self.fight_controller, "fought_squad_ids", ()) or ():' + NL
                + "                return False")
_VOID_LEDGER_OFF = "        if False:" + NL + "            return False"

# 7. THE DETACHMENT GATE stops mattering, so the buttons appear for anybody.
# The BODY, not the name: renaming the function breaks its six importers and
# the suite dies of an ImportError instead of going red, which hides which
# check broke.
_GATE = ("    if not has_detachment(squad.owner):" + NL
         + "        return False")
_GATE_OFF = ("    if False:" + NL
             + "        return False")


PROBES = [
    ("the LAST stage of the panel chain loses the parameter (the half-wiring scar)",
     [(PANEL, _LAST_STAGE, _LAST_STAGE_OFF)], UI),
    ("...and the forwarding hop into it is dropped",
     [(PANEL, _FORWARD, _FORWARD_OFF)], UI),

    ("Hungry Void gains an owner clause its printed WHEN does not have",
     [(VOID, _VOID_PHASE, _VOID_PHASE_OWNED)], UI),
    ("Hungry Void loses its phase test and is offered in all five",
     [(VOID, _VOID_PHASE, _VOID_PHASE_OFF)], UI),

    ("Sudden Storm forgets that its WHEN says YOUR Movement phase",
     [(STORM, _STORM_OWNER, _STORM_OWNER_OFF)], UI),
    ("Conquering Tyrant loses its phase test",
     [(TYRANT, _TYRANT_PHASE, _TYRANT_PHASE_OFF)], UI),

    ("Conquering Tyrant ignores the unit that already shot",
     [(TYRANT, _TYRANT_LEDGER, _TYRANT_LEDGER_OFF)], UI),
    ("Hungry Void ignores the unit that already fought",
     [(VOID, _VOID_LEDGER, _VOID_LEDGER_OFF)], UI),

    ("the detachment gate stops applying",
     [(DYNASTY, _GATE, _GATE_OFF)], UI),

    ("the whole WHEN table collapses - no phase test anywhere",
     [(VOID, _VOID_PHASE, _VOID_PHASE_OFF),
      (TYRANT, _TYRANT_PHASE, _TYRANT_PHASE_OFF)], UI),
]


BASE = {}
for _suite in SUITES:
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:%s%s" % (_suite, NL, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = total - got
    print("baseline %-34s %s/%s (%d red)" % (_suite, got, total, total - got))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {path: read(path) for path, _, _ in edits}
    ok = True
    for path, new, old in edits:
        src = read(path)
        if src.count(new) != 1:
            print("  SKIP     %s: anchor not unique in %s (%d)"
                  % (label, path, src.count(new)))
            ok = False
            break
        write(path, src.replace(new, old))
    try:
        if not ok:
            bad += 1
            continue
        got, tot, out = run(suite)
        red = None if got is None else tot - got
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif red > BASE[suite]:
            verdict, detail = "BITES", "%s/%s (%d red)" % (got, tot, red)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail))
        if red is not None and red > BASE[suite]:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:104])
                    break
    finally:
        for path, text in originals.items():
            write(path, text)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
