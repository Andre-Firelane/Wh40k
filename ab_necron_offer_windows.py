"""A/B probes for the three "the engine answered for the human" defects.

Each probe restores one piece of the pre-fix world AT THE SOURCE, runs the
suite that should notice, and puts it back. A probe that does NOT go red is a
finding about the TEST, so this file exits non-zero if any survives.

THE THREE, and why each needed its own probe rather than one "pre-fix world":

  * VENGEFUL STARS offered the human a bare yes/no on the FIRST valid pair and
    discarded the rest, while the AI walked all of them. Two halves - the
    candidate set and the board tag - and either alone still leaves a rule the
    two sides play differently, so they are probed separately.

  * RETURN PLACEMENT folded "somebody is already placing" in with "this is the
    AI", which made it a silent human -> engine fallback. The QUEUE and the
    "roll ahead" half live in two different modules and either alone is enough
    to lose a unit's placement, so again two probes.

  * PROMPT HYGIENE - a Decline the printed rule does not offer, and options
    that could not be clicked on the board.

COUNTING RED, NOT GREEN: one probe here changes the number of checks a suite
runs, and "fewer passed than the baseline" is false while checks are failing.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)

VS = os.path.join("game", "protocol_vengeful_stars.py")
RETURN = os.path.join("game", "return_placement.py")
REANIM = os.path.join("game", "reanimation_protocols.py")
MW = os.path.join("game", "mortal_wound_abilities.py")
TECHNO = os.path.join("game", "technomancer.py")

DYNASTY = "test_awakened_dynasty.py"
PLACEMENT = "test_return_placement.py"
REANIM_SUITE = "test_reanimation_protocols.py"
ABILITIES = "test_necron_abilities.py"
SUITES = (DYNASTY, PLACEMENT, REANIM_SUITE, ABILITIES)


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    # The documented __pycache__ race: these probes rewrite modules within the
    # same second.
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

# 1a. Vengeful Stars: the first valid pair only, which is the shipped world.
_VS_ALL = """        options = [
            (f"{a.name} shoots back at {k.name} ({VENGEFUL_STARS_CP_COST} CP)",
             (lambda a=a, k=k: self._use(a, k)), a)
            for a, k in valid
        ]"""
_VS_FIRST_ONLY = """        options = [
            (f"{a.name} shoots back at {k.name} ({VENGEFUL_STARS_CP_COST} CP)",
             (lambda a=a, k=k: self._use(a, k)), a)
            for a, k in valid[:1]
        ]"""

# 1b. ...and the SUBTLER half: every pair is offered, but untagged, so the
# choice cannot be made on the board. Everything about the candidate SET still
# passes.
_VS_TAG = "             (lambda a=a, k=k: self._use(a, k)), a)"
_VS_UNTAGGED = "             (lambda a=a, k=k: self._use(a, k)))"

# 1c. the printed name leaves the prompt, so prompt_rule finds nothing.
_VS_PROMPT = '            f"A unit died - use {VENGEFUL_STARS_NAME}? "'
_VS_PROMPT_OFF = '            f"A unit died - use this Stratagem? "'

# 2a. return_placement: the silent fallback, exactly as it shipped.
_RP_SPLIT = "        if not self.setup_controller.can_start_setup(squad):"
_RP_SILENT = ("        if not self.setup_controller.can_start_setup(squad):" + NL
              + "            if on_done is not None:" + NL
              + "                on_done(returned)" + NL
              + "            return returned" + NL
              + "        if False:")

# 2b. ...the queue exists, but nothing starts the next one after a confirm.
_RP_NEXT = ("        if on_done is not None:" + NL
            + "            on_done(models)" + NL
            + "        self._start_next()")
_RP_NEXT_OFF = ("        if on_done is not None:" + NL
                + "            on_done(models)")

# 2c IS DELIBERATELY ABSENT. The first version of this fix added an
# `or bool(self._waiting)` to is_busy and a second term to main.py's phase
# gate; both probes reported NO BITE, and measuring why showed both were dead:
# place() only queues while _pending is set, so a queued placement always has
# an open one in front of it - and an open one is already
# setup_controller.state == PLACING, which the gate waits on. The dead code was
# removed rather than given a probe that could not fail; the invariant it
# assumed is pinned in test_return_placement.py section 12.

# 3a. reanimation: roll the next unit immediately, over the open placement.
_RE_HOLD = ("        self._apply(squad, rolled)" + NL
            + "        if self.placer is not None and self.placer.is_busy:" + NL
            + "            return          # _resume_queue() picks it up when the human is done" + NL
            + "        self._roll_next()")
_RE_HOLD_OFF = ("        self._apply(squad, rolled)" + NL
                + "        self._roll_next()")

# 3b. the re-entrancy latch: the AI advances twice per unit without it.
_RE_LATCH = ("        if self._applying:" + NL
             + "            return" + NL
             + "        self._roll_next()")
_RE_LATCH_OFF = "        self._roll_next()"

# 4a. Living Lightning's phantom Decline comes back.
# The anchor is the WHOLE comment block: the first version matched only its
# first three lines, so the probe left two comment lines behind as code and the
# suite died of a SyntaxError instead of going red. A probe must make a suite
# RED, not crash - the rule this repo has paid seventeen times.
_LL_NO_DECLINE = """        # NO Decline. The printed rule is "select one enemy unit ... and roll
        # four D6" - mandatory, with no "you can", and the AI branch above
        # never declines either. Typhus' Eater Plague further down DOES print
        # "you can select" and keeps its Decline; that difference is the whole
        # reason both are spelled out here rather than sharing one offer."""
_LL_DECLINE = '        options.append(("Decline", None))'

# 4b. the Technomancer's options lose their squad tag.
_TM_TAG = '             (lambda target=t: self._use(squad, target)), getattr(t, "squad", None))'
_TM_UNTAGGED = "             (lambda target=t: self._use(squad, target)))"


PROBES = [
    ("Vengeful Stars offers only the first valid pair (the shipped world)",
     [(VS, _VS_ALL, _VS_FIRST_ONLY)], DYNASTY),
    ("...every pair is offered but none is board-clickable",
     [(VS, _VS_TAG, _VS_UNTAGGED)], DYNASTY),
    ("...the prompt no longer names the Stratagem, so the rule panel finds nothing",
     [(VS, _VS_PROMPT, _VS_PROMPT_OFF)], DYNASTY),

    ("return_placement seats the second unit silently (the reported bug)",
     [(RETURN, _RP_SPLIT, _RP_SILENT)], PLACEMENT),
    ("...it queues, but confirming never starts the next one",
     [(RETURN, _RP_NEXT, _RP_NEXT_OFF)], PLACEMENT),

    ("the reanimation queue rolls the next die over an open placement",
     [(REANIM, _RE_HOLD, _RE_HOLD_OFF)], REANIM_SUITE),
    ("...and without the latch the AI advances its queue twice per unit",
     [(REANIM, _RE_LATCH, _RE_LATCH_OFF)], REANIM_SUITE),

    ("Living Lightning offers a Decline its printed rule does not",
     [(MW, _LL_NO_DECLINE, _LL_DECLINE)], ABILITIES),
    ("the Technomancer's repair cannot be chosen on the board",
     [(TECHNO, _TM_TAG, _TM_UNTAGGED)], ABILITIES),

    ("the whole pre-fix world for the placement half",
     [(RETURN, _RP_SPLIT, _RP_SILENT), (REANIM, _RE_HOLD, _RE_HOLD_OFF)], REANIM_SUITE),
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
