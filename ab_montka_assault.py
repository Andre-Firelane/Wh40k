"""A/B probes for Mont'ka's Killing Blow at the rule-10.05 Advance gate.

Each probe restores one piece of the pre-fix world AT THE SOURCE, runs the
suites that should notice, and puts it back. A probe that does NOT go red is a
finding about the TEST, not a clean bill of health - so this file exits
non-zero if any of them survives.

THE FIX HAS THREE PARTS AND EACH NEEDS ITS OWN PROBE, because two of them pass
while the third is missing:
  * the READER - coldstar.weapon_has_assault() asking montka.grants_assault().
  * the WINDOW - refresh_killing_blow() deriving the round from is_active(),
    so the Exemplar of the Mont'ka's fourth round is not dropped at this gate
    alone.
  * the FEED - main.py actually calling the stamper. Without this probe the
    flag can be honoured by the reader and set by nothing, which is the
    "gebaut, aber nie GEFUETTERT" class that has caught this repo six times.

Three suites, because a fix that reaches only one of them is exactly the drift
this arrangement exists to catch: the wiring guard reads coldstar.py's source,
the doctrines suite drives the gate, and the enhancements suite owns the
Exemplar's widened window.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
COLDSTAR = os.path.join("game", "coldstar.py")
MONTKA = os.path.join("game", "montka.py")
MAIN = "main.py"

WIRING = "test_event_chain_wiring.py"
DOCTRINES = "test_tau_doctrines.py"
ENHANCEMENTS = "test_tau_enhancements.py"
SUITES = (WIRING, DOCTRINES, ENHANCEMENTS)


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


_READER = ("            or dlc_mortarions_teachings.is_active(squad)" + NL
           + "            or montka.grants_assault(squad))")
_READER_OFF = "            or dlc_mortarions_teachings.is_active(squad))"

_WINDOW = "        squad.montka_killing_blow = is_active(squad, turn_tracker)"
_WINDOW_LITERAL = ("        squad.montka_killing_blow = tau_detachments.doctrine_active("
                   + NL + "            squad, SETTING, KILLING_BLOW_ROUNDS, turn_tracker)"
                   + NL + "        squad.montka_killing_blow = ("
                   + NL + "            squad.montka_killing_blow"
                   + NL + "            and turn_tracker.battle_round in KILLING_BLOW_ROUNDS)")

_FEED = "        montka.refresh_killing_blow(_detachment_squads, turn_tracker)"
_FEED_OFF = "        pass  # refresh removed by ab_montka_assault.py"

PROBES = [
    # 1. THE READER. The literal pre-fix world: the grant reaches the damage
    # chain and not the gate, which is how it shipped.
    ("the Advance gate never asks Mont'ka (the shipped gap)",
     [(COLDSTAR, _READER, _READER_OFF)], WIRING),
    ("...and the same, measured as behaviour rather than as source",
     [(COLDSTAR, _READER, _READER_OFF)], DOCTRINES),

    # 2. THE WINDOW. Not "no window at all" - the SUBTLE version: the stamp
    # still happens, still honours the detachment and the faction, and is only
    # narrowed to the printed rounds. Everything about Killing Blow itself
    # still passes; only the Exemplar's fourth round is lost, and only at this
    # gate. If this does not bite, the widening is untested on the flag path.
    ("the stamp uses the printed rounds instead of the widened window",
     [(MONTKA, _WINDOW, _WINDOW_LITERAL)], ENHANCEMENTS),

    # 3. THE FEED. Reader and window both intact; nothing calls the stamper.
    # No behaviour test that sets the flag itself can see this.
    ("main.py never stamps the flag (built, but never fed)",
     [(MAIN, _FEED, _FEED_OFF)], DOCTRINES),

    # 4. THE WHOLE PRE-FIX WORLD, and it is aimed at the BEHAVIOUR suite for a
    # reason worth writing down. Restoring the gap entry alongside the reader
    # puts section 7 of the wiring guard back into its "documented gap" branch,
    # where it is DESIGNED to be green - that is what declaring a gap means.
    # Pointed at the wiring guard this probe therefore reports NO BITE, which
    # is a true statement about a source guard that tolerates a named gap and
    # says nothing about the engine.
    #
    # That is precisely why the gap could go stale for as long as it did, and
    # precisely why the fix needed a behaviour test rather than only an empty
    # gap set: the source guard cannot tell "closed" from "excused".
    ("the whole pre-fix world - reader off AND the gap entry back",
     [(COLDSTAR, _READER, _READER_OFF),
      (WIRING, "_ASSAULT_GRANT_GAPS = set()", '_ASSAULT_GRANT_GAPS = {"montka"}')],
     DOCTRINES),
]


BASE = {}
for _suite in SUITES:
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:%s%s" % (_suite, NL, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = got
    print("baseline %-34s %s/%s" % (_suite, got, total))
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
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < BASE[suite]:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail))
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
