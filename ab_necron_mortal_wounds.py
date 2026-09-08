"""A/B probes for the four abilities that opened a mortal-wound session and
could not drain it.

Each probe restores one piece of the pre-fix world AT THE SOURCE, runs the
suite that should notice, and puts it back. A probe that does NOT go red is a
finding about the TEST, so this file exits non-zero if any survives.

TWO SUITES, and the split is the point of the whole arrangement:

  * test_event_chain_wiring.py section 17 is the SET DIFFERENCE at the source -
    it sees a module that cannot drain, including the twenty-second one that
    does not exist yet.
  * test_mortal_wound_drains.py is the BEHAVIOUR - the wounds really land.

A fix that satisfies only one of them is exactly the drift this pair exists to
catch, so several probes below are aimed deliberately at the suite that is NOT
the obvious one.

THE main.py PROBES ARE AIMED AT THE WIRING GUARD ON PURPOSE. No behaviour test
can see a missing click branch or a missing highlight: it drives the controller
directly, so the controller answers. Only the source knows whether main.py ever
asks - which is the "gebaut, aber nie GEFUETTERT" class, and why sections 6, 12
and 17c exist at all.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)

WRAITH = os.path.join("game", "wraith_form.py")
SNARE = os.path.join("game", "monofilament_snare.py")
DRAKO = os.path.join("game", "drakolithe.py")
HARVEST = os.path.join("game", "harvester_of_souls.py")
MAIN = "main.py"

WIRING = "test_event_chain_wiring.py"
DRAINS = "test_mortal_wound_drains.py"
SUITES = (WIRING, DRAINS)


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


# --------------------------------------------------------------- the edits
# Written as (new -> old) pairs, i.e. the anchor is what is there NOW and the
# replacement is the pre-fix world.

_WF_PENDING = ("    @property" + NL
               + "    def pending_damage_choice(self):")
_WF_PENDING_OFF = ("    @property" + NL
                   + "    def _pending_damage_choice_removed_by_probe(self):")

_WF_CHOOSE = "    def choose_damage_model(self, model):"
_WF_CHOOSE_OFF = "    def _choose_damage_model_removed_by_probe(self, model):"

# The FNP leg, which must come BEFORE the `_pending is None` early return.
# Removing it leaves a controller that looks completely wired and drops every
# Feel No Pain acknowledgement on the floor.
_WF_FNP = ("        if (self._pending is None and self.mortal_wound_session is not None" + NL
           + "                and self.mortal_wound_session.pending_fnp is not None):")
_WF_FNP_OFF = ("        if (False and self._pending is None"
               + " and self.mortal_wound_session is not None" + NL
               + "                and self.mortal_wound_session.pending_fnp is not None):")

_SNARE_PENDING = ("    @property" + NL
                  + "    def pending_damage_choice(self):")
_SNARE_PENDING_OFF = ("    @property" + NL
                      + "    def _pending_damage_choice_removed_by_probe(self):")

# The callable log, in each of the three modules that handed over the object.
_LOG_DRAKO = "            log=self._log))"
_LOG_DRAKO_OFF = "            log=self.game_log))"
_LOG_HARVEST = "            unit, count, dice_manager=self.dice_manager, log=self._log))"
_LOG_HARVEST_OFF = "            unit, count, dice_manager=self.dice_manager, log=self.game_log))"
_LOG_SNARE = "            squad, count, dice_manager=self.dice_manager, log=self._log)"
_LOG_SNARE_OFF = "            squad, count, dice_manager=self.dice_manager, log=self.game_log)"

# main.py's five seams.
_MAIN_PAUSE = ("                wraith_form_controller, drakolithe_controller," + NL
               + "                harvester_of_souls_controller, monofilament_snare_controller,")
_MAIN_PAUSE_OFF = "                pass  # AI pause entry removed by ab_necron_mortal_wounds.py"

_MAIN_GATE = ("            or wraith_form_controller.is_busy" + NL
              + "            or wraith_form_controller.pending_damage_choice is not None")
_MAIN_GATE_OFF = "            or False  # phase gate term removed by ab_necron_mortal_wounds.py"

_MAIN_CLICK = ("                    if clicked is not None and clicked in "
               "wraith_form_controller.pending_damage_choice:" + NL
               + "                        wraith_form_controller.choose_damage_model(clicked)")
_MAIN_CLICK_OFF = ("                    pass  # click branch removed by "
                   "ab_necron_mortal_wounds.py")

_MAIN_DRAW = ("        renderer.draw_damage_choice_highlight(board_surface, board, "
              "wraith_form_controller.pending_damage_choice)")
_MAIN_DRAW_OFF = "        pass  # highlight removed by ab_necron_mortal_wounds.py"

_MAIN_ACK = "                        drakolithe_controller.on_dice_acknowledged()"
_MAIN_ACK_OFF = "                        pass  # dice ack removed by ab_necron_mortal_wounds.py"

# The guard's own exemption, pointed at a module that no longer opens a
# session - a stale excuse, which its three liveness assertions must reject.
_GAPS = '_MW_DRAIN_GAPS = {"damage_resolution.py"}'
_GAPS_STALE = '_MW_DRAIN_GAPS = {"damage_resolution.py", "shooting.py"}'


PROBES = [
    # ---- 1. the drain itself, both halves, both suites ---------------------
    ("Wraith Form has no pending_damage_choice (the shipped world)",
     [(WRAITH, _WF_PENDING, _WF_PENDING_OFF)], WIRING),
    ("...and the same, measured as wounds that never land",
     [(WRAITH, _WF_PENDING, _WF_PENDING_OFF)], DRAINS),
    ("Wraith Form has no choose_damage_model",
     [(WRAITH, _WF_CHOOSE, _WF_CHOOSE_OFF)], WIRING),
    ("Monofilament Snare has no pending_damage_choice",
     [(SNARE, _SNARE_PENDING, _SNARE_PENDING_OFF)], WIRING),

    # ---- 2. the FNP leg -----------------------------------------------------
    # Deliberately NOT the whole method: everything else about the controller
    # still works, and only a Feel No Pain acknowledgement is dropped. The
    # ordering of this branch is what six Aeldari controllers paid for.
    ("Wraith Form's FNP leg runs after the early return instead of before it",
     [(WRAITH, _WF_FNP, _WF_FNP_OFF)], DRAINS),

    # ---- 3. the callable log, one probe per module -------------------------
    # These restore the CRASH, not a leak. run() treats a crashed suite as red,
    # and the suite itself catches the TypeError so it degrades to a red check
    # rather than an exception - the rule this repo has paid seventeen times.
    ("drakolithe hands its session the GameLog object",
     [(DRAKO, _LOG_DRAKO, _LOG_DRAKO_OFF)], DRAINS),
    ("harvester_of_souls hands its session the GameLog object",
     [(HARVEST, _LOG_HARVEST, _LOG_HARVEST_OFF)], DRAINS),
    ("monofilament_snare hands its session the GameLog object",
     [(SNARE, _LOG_SNARE, _LOG_SNARE_OFF)], DRAINS),
    ("...and the source guard sees all three at once",
     [(DRAKO, _LOG_DRAKO, _LOG_DRAKO_OFF),
      (HARVEST, _LOG_HARVEST, _LOG_HARVEST_OFF),
      (SNARE, _LOG_SNARE, _LOG_SNARE_OFF)], WIRING),

    # ---- 4. main.py's five seams -------------------------------------------
    ("main.py never pauses the AI for these four choices",
     [(MAIN, _MAIN_PAUSE, _MAIN_PAUSE_OFF)], WIRING),
    ("main.py's phase gate never waits on Wraith Form",
     [(MAIN, _MAIN_GATE, _MAIN_GATE_OFF)], WIRING),
    ("main.py has no click branch for Wraith Form (a blocked, unanswerable choice)",
     [(MAIN, _MAIN_CLICK, _MAIN_CLICK_OFF)], WIRING),
    ("main.py never draws which models are choosable",
     [(MAIN, _MAIN_DRAW, _MAIN_DRAW_OFF)], WIRING),
    ("main.py never acknowledges drakolithe's Feel No Pain roll",
     [(MAIN, _MAIN_ACK, _MAIN_ACK_OFF)], WIRING),

    # ---- 5. the guard's own honesty ----------------------------------------
    # An exemption that no longer covers a session-opening module is an expired
    # excuse, and it must fall through rather than stand green forever - the
    # lesson of the Mont'ka gap.
    ("the exemption list names a module that opens no session",
     [(WIRING, _GAPS, _GAPS_STALE)], WIRING),

    # ---- 6. the whole pre-fix world ----------------------------------------
    ("the whole pre-fix world - all four undrained",
     [(WRAITH, _WF_PENDING, _WF_PENDING_OFF),
      (SNARE, _SNARE_PENDING, _SNARE_PENDING_OFF),
      (DRAKO, "    def pending_damage_choice(self):",
       "    def _pending_damage_choice_removed_by_probe(self):"),
      (HARVEST, "    def pending_damage_choice(self):",
       "    def _pending_damage_choice_removed_by_probe(self):")], WIRING),
]


# FAILURES, not passes. One probe here ADDS checks (a stale exemption entry
# makes the guard's own loop run one more time), so "fewer passed than the
# baseline" is false while two checks are red - the probe would report NO BITE
# for a guard that is working exactly as intended. Counting what went RED is
# the comparison that survives a changing total.
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
