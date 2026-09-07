"""A/B probes for the T'au Stratagem panel matrix.

Each probe restores one piece of a pre-fix world AT THE SOURCE, runs the suite,
and puts it back. A probe that does NOT go red is a finding about the TEST -
so this exits non-zero if any survives.

WHAT THESE ATTACK that no existing probe does: the PANEL PATH. Every other T'au
probe in this repo drives can_use() or greps main.py, and both hold perfectly
while the panel draws nothing - which is the whole reason
test_tau_stratagem_ui.py exists. So the probes here cut the registry off from
the panel, cut the two pre-registry keyword arguments, break the second SCREEN,
and collapse the two Experimental Ammunition modes into one.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
MAIN = "main.py"
PANEL = os.path.join("game", "ui", "action_panel.py")
REGISTRY = os.path.join("game", "proactive_stratagems.py")
SUITE = "test_tau_stratagem_ui.py"


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


PROBES = [
    # THE ONE THAT MATTERS MOST: the registry is built, filled and handed over,
    # and the panel simply never asks it. Literally what shipped for
    # overflight_controller on the Aeldari side.
    ("the panel never asks the registry for buttons", REGISTRY,
     '''        return [(c.panel_label(squad), (lambda c=c, s=squad: c.use(s)))
                for c in self.usable_for(squad)]''',
     "        return []"),

    # The registry never reaches the panel at all.
    ("main.py never hands the registry to the panel", MAIN,
     "            proactive_stratagems=proactive_stratagems,",
     "            proactive_stratagems=None,"),

    # The second panel path: the two pre-registry controllers, cut one at a
    # time so a partial regression is not just a list diff.
    ("the Arro'kon button is never drawn", PANEL,
     "            if can_arrokon_now:",
     "            if False:  # can_arrokon_now"),
    ("the Torchstar button is never drawn", PANEL,
     "            can_torchstar_now = torchstar_controller is not None and torchstar_controller.can_use(squad)",
     "            can_torchstar_now = False"),

    # The SECOND SCREEN. The Shortened Blade is the only button on it, and a
    # suite that rendered only the movement screen would report it absent in
    # all five phases - a bug where in fact the wrong screen was measured.
    ("the setup screen never draws The Shortened Blade", PANEL,
     "        if shortened_blade_controller is not None and shortened_blade_controller.can_use(squad):",
     "        if False:"),

    # The violet accent is what fills _stratagem_buttons, which is how every
    # name in this suite is read. Losing it makes the buttons invisible to the
    # matrix while they are still on the panel - so the suite must not be able
    # to confuse "not drawn" with "drawn without its accent".
    ("the Stratagem accent is dropped, so nothing is recorded as one", PANEL,
     '        if accent == "stratagem":',
     "        if False:"),

    # ONE NAME, TWO BUTTONS. Collapsing the two printed modes into one is the
    # regression the exact-label handling exists for: matching on the printed
    # name alone would still find "a" button and report the pair intact.
    ("Experimental Ammunition offers only one of its two printed modes", MAIN,
     "        for mode in (MODE_STRENGTH, MODE_STRENGTH_AP_HAZARDOUS)",
     "        for mode in (MODE_STRENGTH,)"),

    # The phase gate itself: a Stratagem that is drawn in EVERY phase. This is
    # the failure the matrix's four negatives per Stratagem exist for, and no
    # single-phase test can see it.
    ("Aggressive Mobility ignores its printed phase",
     os.path.join("game", "montka_aggressive_mobility.py"),
     "        if self.turn_tracker.phase != PHASE_MOVEMENT:" + NL
     + "            return False",
     "        if False:" + NL + "            return False"),

    # The owner clause, measured at can_use() - section 4.
    ("Point-Blank Ambush ignores whose turn it is",
     os.path.join("game", "kauyon_point_blank_ambush.py"),
     "        if squad.owner != self.turn_tracker.active_player:" + NL
     + "            return False",
     "        if False:" + NL + "            return False"),

    # The detachment gate - section 3 is what makes section 2 non-vacuous.
    ("Guided Fire is offered without its detachment",
     os.path.join("game", "aux_guided_fire.py"),
     "        if not tau_detachments.has_detachment(squad.owner, auxiliary_cadre.SETTING):" + NL
     + "            return False",
     "        if False:" + NL + "            return False"),

    # Rule 15.01 - section 5.
    ("a Stratagem can be bought twice in one phase",
     os.path.join("game", "stratagems.py"),
     "    def reset_phase(self",
     "    def _unused_reset_phase(self"),
]


got, total, text = run(SUITE)
if got is None:
    print("BASELINE DID NOT RUN:" + NL + text[-2500:])
    raise SystemExit(2)
BASE = got
print("baseline %-34s %s/%s" % (SUITE, got, total))
print()

bad = 0
for label, path, new, old in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print("  SKIP     %s: anchor not unique in %s (%d)"
              % (label, path, src.count(new)))
        bad += 1
        continue
    try:
        write(path, src.replace(new, old))
        got, tot, out = run(SUITE)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < BASE:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < BASE:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:104])
                    break
    finally:
        write(path, src)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
