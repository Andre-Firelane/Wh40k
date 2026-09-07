"""A/B probes for the two unresolvable dice cycles, at the SOURCE.

  * Aspect Host's KHAINE'S VENGEANCE was a HARD DEADLOCK. Its is_busy sat in
    main.py's phase-advance gate while neither its dice acknowledgement nor its
    damage choice was wired anywhere in the event chain - built, blocking, and
    unclickable. Once bought, the phase could never advance again.
  * Spirit Conclave's CRUSHING STRIDES rolled its dice and nobody told the
    controller they had been acknowledged, so the mortal wounds were never
    inflicted AND its own _pending latch turned the Stratagem off for the rest
    of the battle.
  * Behind both: MortalWoundOfferController never drained its allocation
    session. Against any target with more than one eligible model the session
    parked on pending_choice and the wounds were silently never applied - six
    abilities across four factions, and the two suites that covered them
    measured how much was ORDERED rather than how much LANDED.

A probe that does NOT go red is a finding about the test, not a clean bill of
health. Two of these reported one on the first run: the Crushing Strides
acknowledgement is invisible to the suite that drives the controller itself
(only the wiring guard can see it), and the Feel No Pain leg exists in SIX
copies of the same guard, of which the first version of that probe restored
five.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
MAIN = "main.py"
MWA = os.path.join("game", "mortal_wound_abilities.py")
CCS = os.path.join("game", "conclave_crushing_strides.py")
AELDARI = "test_aeldari_detachment_stratagems.py"
WIRING = "test_event_chain_wiring.py"
SKORPEKH = "test_skorpekh_lord.py"
NECRON = "test_necron_abilities.py"

_LEG = ("            # No roll of our own outstanding - but an allocation session may" + NL
        + "            # still owe a Feel No Pain acknowledgement. See _ack_session()." + NL
        + "            return self._ack_session()")


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


# (label, [(path, needle_or_(needle, count), replacement), ...], suite)
PROBES = [
    ("Khaine's dice acknowledgement never called",
     [(MAIN, "                        khaines_vengeance_controller.on_dice_acknowledged()",
       "                        pass")],
     WIRING),

    ("Khaine's click branch removed",
     [(MAIN, "                    if clicked is not None and clicked in khaines_vengeance_controller.pending_damage_choice:"
       + NL + "                        khaines_vengeance_controller.choose_damage_model(clicked)",
       "                    pass")],
     WIRING),

    ("Khaine's board highlight removed",
     [(MAIN, "        renderer.draw_damage_choice_highlight(board_surface, board, khaines_vengeance_controller.pending_damage_choice)",
       "        pass")],
     WIRING),

    ("Crushing Strides' dice acknowledgement never called",
     [(MAIN, "                        crushing_strides_controller.on_dice_acknowledged()",
       "                        pass")],
     WIRING),

    # NO PROBE HERE FOR "the Stratagem then inflicts nothing" against the
    # Aeldari suite: that suite drives on_dice_acknowledged() ITSELF, which is
    # exactly why the missing call survived in the first place. Only the wiring
    # guard above can see it; the EFFECT is covered by the three probes below.

    # The shared allocation session. Each of these three is one third of the
    # machinery that was missing outright, and each alone is enough to strand
    # the allocation - measured on a DIFFERENT faction's suite each time,
    # because the fix is in the base class and reaches all six carriers.
    ("the base class's pending_damage_choice removed",
     [(MWA, "        if self.mortal_wound_session is None:" + NL
       + "            return None" + NL
       + "        return self.mortal_wound_session.pending_choice",
       "        return None")],
     AELDARI),

    ("...choose_damage_model() removed",
     [(MWA, "        self.mortal_wound_session.choose_model(model)" + NL
       + "        self._check_session_done()",
       "        pass")],
     SKORPEKH),

    ("...and _check_session_done() removed",
     [(MWA, "        if self.mortal_wound_session is not None and self.mortal_wound_session.done:"
       + NL + "            self.mortal_wound_session = None",
       "        pass")],
     SKORPEKH),

    # The Feel No Pain leg, in ALL SIX copies of the guard: five subclasses in
    # game/mortal_wound_abilities.py plus Crushing Strides in its own module.
    # Restoring only the five leaves the one the Aeldari suite actually drives
    # still fixed - half a pre-fix world, which is error class 16, and is how
    # this probe first reported a clean bill of health.
    ("the Feel No Pain leg back to returning False (all six copies)",
     [(MWA, (_LEG, 5), "            return False"),
      (CCS, (_LEG, 1), "            return False")],
     AELDARI),
]

BASE = {}
for _suite in (AELDARI, WIRING, SKORPEKH, NECRON):
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:%s%s" % (_suite, NL, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = got
    print("baseline %-42s %s/%s" % (_suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {path: read(path) for path, _, _ in edits}
    ok = True
    for path, needle, replacement in edits:
        want = 1
        if isinstance(needle, tuple):
            needle, want = needle
        src = read(path)
        if src.count(needle) != want:
            print("  SKIP     %s: anchor appears %d times in %s, wanted %d"
                  % (label, src.count(needle), path, want))
            ok = False
            break
        write(path, src.replace(needle, replacement))
    try:
        if not ok:
            bad += 1
            continue
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
        for path, text in originals.items():
            write(path, text)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
