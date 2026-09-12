"""Runtime proof through the REAL main() loop that the autosave is written on
every phase change, that each file holds the phase it was written on, and that
loading it does not immediately rewrite it.

User: "der autosave scheint nicht zu funktionieren. bitte mach einen autosave
bei jedem phasenwechsel."

TWO PASSES of selfplay.py's real main() loop:

  1. PLAY. Every phase the battle reaches is recorded as it happens, off the
     live TurnTracker, next to every autosave actually written - and each
     written file is READ BACK, because a write proves the writer ran and only
     the file proves what a Resume would open.
  2. RESUME. The last autosave is loaded into a second main() the way the
     menu's Resume entry does it (config.LOAD_SCENE), and this reports whether
     that battle resumed on the saved phase and whether anything rewrote the
     autosave before a single phase had changed.

THE AUTOSAVE IS SANDBOXED, and the harness opt-out is part of what is measured.
selfplay.py turns the autosave OFF (it is one of the harnesses that used to
replace a person's battle with its own), so this probe switches it back on at
the one moment main() builds its edge - and records what the flag said just
before, which is selfplay's opt-out seen live. scene_io.SCENES_DIR points at a
throwaway folder for both passes, so nothing here touches scenes/autosave.json.
(The real file's mtime is deliberately NOT used as evidence: a game the user
has open writes it too.)

Nothing about the battle is staged - phase changes happen on their own, so this
is one of the questions that is measurable passively. A MockAgent run reaches
only a handful of phases per few thousand frames (the harness limit CLAUDE.md
records), which is why the frame budget defaults high.

--neutralize restores the pre-fix world in both halves: the edge is the battle
ROUND, and a loaded battle is not seeded - so pass 1 must report phases with no
save, and pass 2 must report the autosave rewritten on load.

Usage:  python verify_phase_autosave.py [map2] [frames] [--neutralize]
"""

import os
import runpy
import sys
import tempfile
import time

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")
ARGS = sys.argv[1:]
MAP = ARGS[0] if ARGS else "map2"
FRAMES = ARGS[1] if len(ARGS) > 1 else "3000"
RESUME_FRAMES = "400"

from game import autosave, config, scene_io  # noqa: E402

SANDBOX = tempfile.mkdtemp(prefix="verify_phase_autosave_")
scene_io.SCENES_DIR = SANDBOX
SANDBOX_FILE = os.path.join(SANDBOX, scene_io.AUTOSAVE_NAME)

_real_key = autosave.phase_key
if NEUTRALIZE:
    # The round edge: every key inside a round is the same key.
    def _round_only(turn_tracker):
        key = _real_key(turn_tracker)
        return None if key is None else (key[0], key[1] and None, key[2] and None)

    autosave.phase_key = _round_only
    # ...and the seed that ran before the snapshot was restored, i.e. none.
    autosave.AutosaveEdge.seed = lambda self, turn_tracker: None

run = {"name": None}
passes = {}


def _pass():
    return passes.setdefault(run["name"], {
        "flag_before_edge": [], "phases": [], "writes": [], "stray_writes": [],
        "last_key": None,
    })


_real_init = autosave.AutosaveEdge.__init__


def _init(self):
    _real_init(self)
    _pass()["flag_before_edge"].append(config.AUTOSAVE)
    config.AUTOSAVE = True


autosave.AutosaveEdge.__init__ = _init

_real_take = autosave.AutosaveEdge.take


def _take(self, turn_tracker, settled):
    p = _pass()
    real = _real_key(turn_tracker)
    if real is not None and (not p["phases"] or p["phases"][-1] != real):
        p["phases"].append(real)
    p["last_key"] = real
    return _real_take(self, turn_tracker, settled)


autosave.AutosaveEdge.take = _take

_real_write = scene_io.write


def _write(data, path):
    p = _pass()
    if os.path.basename(path) != scene_io.AUTOSAVE_NAME:
        return _real_write(data, path)
    if os.path.dirname(os.path.abspath(path)) != os.path.abspath(SANDBOX):
        p["stray_writes"].append(path)
        return path
    started = time.perf_counter()
    result = _real_write(data, path)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    turn = scene_io.read(path).get("turn") or {}
    on_file = (turn.get("battle_round"), turn.get("turn_owner"), turn.get("phase"))
    p["writes"].append({"phase": p["last_key"], "file": on_file, "ms": elapsed_ms})
    return result


scene_io.write = _write


def _drive(frames):
    sys.argv = ["selfplay.py", MAP, frames]
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass


# ------------------------------------------------------------------ pass 1
run["name"] = "play"
config.MAP = MAP
_drive(FRAMES)
play = _pass()

# ------------------------------------------------------------------ pass 2
resume = None
if os.path.exists(SANDBOX_FILE):
    saved = scene_io.read(SANDBOX_FILE).get("turn") or {}
    saved_key = (saved.get("battle_round"), saved.get("turn_owner"), saved.get("phase"))
    run["name"] = "resume"
    config.LOAD_SCENE = SANDBOX_FILE
    _drive(RESUME_FRAMES)
    config.LOAD_SCENE = None
    resume = _pass()
    resume["saved_key"] = saved_key


def fmt(key):
    return "-" if key is None else f"R{key[0]} {key[1]} {key[2]}"


print()
print("--- phase autosave" + (" (NEUTRALIZED: round edge, no seed on load)" if NEUTRALIZE else "")
      + " ---")
print(f"  sandbox                         {SANDBOX}")
print(f"  selfplay's opt-out live         config.AUTOSAVE was {play['flag_before_edge']} "
      "when main() built its edge")
print(f"  phases the battle reached       {len(play['phases'])}")
written = {w["phase"] for w in play["writes"]}
print(f"  autosaves written               {len(play['writes'])}")
for w in play["writes"]:
    match = "holds that phase" if w["file"] == w["phase"] else "DIFFERENT PHASE ON FILE"
    print(f"      at {fmt(w['phase']):28} -> file {fmt(w['file']):28} {match} ({w['ms']:.1f} ms)")
missing = [k for k in play["phases"] if k not in written]
print(f"  phases with NO autosave         {len(missing)}")
for key in missing[:12]:
    print(f"      {fmt(key)}")
mismatched = [w for w in play["writes"] if w["file"] != w["phase"]]
print(f"  files holding another phase     {len(mismatched)}")
print(f"  writes outside the sandbox      {len(play['stray_writes'])}")

rewrote = None
if resume is not None:
    first = resume["phases"][0] if resume["phases"] else None
    rewrote = any(w["phase"] == resume["saved_key"] for w in resume["writes"])
    print(f"  RESUME: file held               {fmt(resume['saved_key'])}")
    print(f"  RESUME: battle resumed on       {fmt(first)}")
    print(f"  RESUME: autosave rewritten before any phase changed   {rewrote}")
    print(f"  RESUME: autosaves after the load                      "
          f"{[fmt(w['phase']) for w in resume['writes']]}")
else:
    print("  RESUME: no autosave was written, nothing to load")

# The last phase may legitimately be unsaved: the run can end on a frame that is
# not settled. Every other phase must have been written.
unsaved_before_last = [k for k in missing if k != (play["phases"][-1] if play["phases"] else None)]
problems = []
if len(play["phases"]) < 4:
    problems.append(f"only {len(play['phases'])} phases reached - INCONCLUSIVE, raise the frame budget")
if unsaved_before_last:
    problems.append(f"{len(unsaved_before_last)} phase(s) went by without an autosave")
if mismatched:
    problems.append(f"{len(mismatched)} autosave(s) hold a different phase than they were written on")
if play["stray_writes"]:
    problems.append("an autosave was written outside the sandbox")
if play["flag_before_edge"] and any(play["flag_before_edge"]):
    problems.append("selfplay.py did not opt out of the autosave")
if resume is None:
    problems.append("no autosave to resume from")
else:
    if resume["phases"] and resume["phases"][0] != resume["saved_key"]:
        problems.append("the resumed battle did not start on the saved phase")
    if rewrote:
        problems.append("loading the autosave rewrote it before any phase changed")

print()
if problems:
    print("VERDICT: FAIL")
    for line in problems:
        print(f"  - {line}")
    raise SystemExit(1)
print("VERDICT: PASS - every phase reached was autosaved, each file holds its phase, "
      "and a resume does not rewrite what it opened")
