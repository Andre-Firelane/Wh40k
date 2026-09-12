"""Tests for the autosave on every PHASE change (game/autosave.py).

User: "der autosave scheint nicht zu funktionieren. bitte mach einen autosave
bei jedem phasenwechsel."

Two things were wrong, and only one of them was the edge:

  * The edge was the battle ROUND - ten phases, two whole turns - so Resume
    opened a board from long before the one the player remembered.
  * Every headless harness that drives main() wrote the SAME file the menu's
    Resume entry offers. Of the 26 runs that wrote an autosave on 2026-09-12,
    at least 17 were harnesses, each replacing a person's battle with its own
    round-1 board. From the menu that is indistinguishable from "it does not
    save".

  1. the key      - (battle round, turn owner, phase): None before the battle,
                    distinct at every one of a round's ten phase edges, and
                    blind to active_player, which flips for every save roll.
  2. the edge     - take(): one write per phase, none on an unsettled frame,
                    a held-back phase written on the first settled one, two
                    held-back phases coalesced, and a LOADED battle seeded.
  3. the file     - scene_io.write() is atomic: a write that dies half-way
                    leaves the previous snapshot readable and no temp file.
  4. main.py      - the wiring no behaviour test can see: the edge is built
                    before the load path, seeded AFTER the restore, gated on
                    config.AUTOSAVE and a settled board, written through the
                    one scene writer, outside the event loop and ahead of the
                    AI's tick, and a disk error cannot end the battle.
  5. harnesses    - every script that drives main() opts out, before it
                    imports main; the shipped default is ON.

Run: python test_autosave.py
"""

import ast
import io
import json
import os
import re
import shutil
import tempfile

from game import autosave, scene_io
from game.turn import PHASES, TurnTracker
from testkit import Checks

c = Checks("autosave")


def _read(path):
    return io.open(path, encoding="utf-8").read()


def _tracker(first="Player 1"):
    t = TurnTracker(deferred_start=True)
    t.start_battle(first)
    return t


# --------------------------------------------------------------------------
# 1. the key
# --------------------------------------------------------------------------
print("\n=== 1. the phase key ===")

pre = TurnTracker(deferred_start=True)
c.eq("no key before the battle begins (rule 03.01's deployment)", autosave.phase_key(pre), None)
c.eq("...and none for no tracker at all", autosave.phase_key(None), None)

t = _tracker("Player 2")
c.eq("the battle's first phase is keyed", autosave.phase_key(t), (1, "Player 2", PHASES[0]))

keys = [autosave.phase_key(t)]
for _ in range(10):
    t.advance_phase()
    keys.append(autosave.phase_key(t))
# Ten advances from the first Command phase: nine inside round 1, the tenth
# opens round 2. Eleven keys, all different.
c.eq("every phase edge of a whole round gives a new key", len(set(keys)), len(keys))
c.eq("...including the two players' same-named phases",
     keys[1][2] == keys[6][2] and keys[1] != keys[6], True)
c.eq("...and the round's edge", keys[10][0], 2)

before = autosave.phase_key(t)
t.set_active("Player 1" if t.turn_owner == "Player 2" else "Player 2")
c.eq("active_player flipping (a defender's save) is not a phase edge",
     autosave.phase_key(t), before)

c.eq("describe() names round, owner AND phase",
     autosave.describe((2, "Player 1", "Shooting")),
     "battle round 2, Player 1's Shooting phase")


# --------------------------------------------------------------------------
# 2. the edge
# --------------------------------------------------------------------------
print("\n=== 2. take() ===")

edge = autosave.AutosaveEdge()
c.eq("nothing is due before the battle", edge.take(pre, settled=True), None)

t = _tracker("Player 1")
first = edge.take(t, settled=True)
c.eq("a fresh battle writes its first phase", first, (1, "Player 1", PHASES[0]))
c.eq("...once", edge.take(t, settled=True), None)

t.advance_phase()
c.eq("an unsettled frame writes nothing", edge.take(t, settled=False), None)
c.eq("...and does NOT record the phase as written",
     edge.take(t, settled=True), (1, "Player 1", PHASES[1]))

t.advance_phase()
edge.take(t, settled=False)
t.advance_phase()
edge.take(t, settled=False)
coalesced = edge.take(t, settled=True)
c.eq("two phases gone by while unsettled coalesce into the latest",
     coalesced, (1, "Player 1", PHASES[3]))
c.eq("...and nothing for the skipped one afterwards", edge.take(t, settled=True), None)

# A full battle round of ten phases, settled throughout: exactly ten writes.
edge = autosave.AutosaveEdge()
t = _tracker("Player 2")
written = []
for step in range(10):
    for _frame in range(3):   # several frames per phase, as in the real loop
        key = edge.take(t, settled=True)
        if key is not None:
            written.append(key)
    t.advance_phase()
c.eq("a whole battle round writes exactly ten times", len(written), 10)
c.eq("...one per phase, in order", written == sorted(set(written), key=written.index), True)

# A LOADED battle: the phase it resumed on is not written again.
loaded = _tracker("Player 1")
for _ in range(7):
    loaded.advance_phase()
edge = autosave.AutosaveEdge()
edge.seed(loaded)
c.eq("a loaded battle does not rewrite the phase it resumed on",
     edge.take(loaded, settled=True), None)
loaded.advance_phase()
c.eq("...but writes the next one", edge.take(loaded, settled=True), autosave.phase_key(loaded))
unseeded = autosave.AutosaveEdge()
c.eq("(without seed() it WOULD have rewritten it - the check is not vacuous)",
     unseeded.take(_tracker("Player 1"), settled=True) is not None, True)


# --------------------------------------------------------------------------
# 3. the file
# --------------------------------------------------------------------------
print("\n=== 3. scene_io.write() is atomic ===")

def _map_of(path):
    """The map a snapshot names - or why it cannot be read. A probe that puts
    the non-atomic write back truncates the file, and a check that raised on
    that would crash the suite instead of turning its own line red."""
    try:
        return scene_io.read(path)["map"]
    except (OSError, ValueError, KeyError) as exc:
        return f"unreadable: {type(exc).__name__}"


tmp = tempfile.mkdtemp()
try:
    target = os.path.join(tmp, scene_io.AUTOSAVE_NAME)
    good = {"format": scene_io.FORMAT_VERSION, "map": "map2", "squads": []}
    scene_io.write(good, target)
    c.eq("a write lands", _map_of(target), "map2")
    c.eq("...and leaves no temp file behind", os.listdir(tmp), [scene_io.AUTOSAVE_NAME])

    class _Unwritable:
        pass

    bad = {"format": scene_io.FORMAT_VERSION, "map": "map3", "squads": [_Unwritable()]}
    raised = False
    try:
        scene_io.write(bad, target)
    except TypeError:
        raised = True
    c.eq("a write that dies half-way raises", raised, True)
    c.eq("...the previous snapshot is still readable and unchanged",
         _map_of(target), "map2")
    c.eq("...and the half-file was cleaned up", os.listdir(tmp), [scene_io.AUTOSAVE_NAME])

    with open(target + ".tmp", "w", encoding="utf-8") as stray:
        stray.write("{ half a snap")
    os.utime(target + ".tmp", None)
    c.eq("a stray temp file is never offered as the newest save",
         scene_io.newest(tmp), target)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# 4. main.py
# --------------------------------------------------------------------------
print("\n=== 4. the wiring in main.py ===")

main_src = _read("main.py")


def find(needle, start=0):
    return main_src.find(needle, start)


c.eq("the round edge is gone", "previous_battle_round" in main_src, False)
c.eq("one autosave edge per battle", main_src.count("autosave_edge = autosave.AutosaveEdge()"), 1)

build_at = find("autosave_edge = autosave.AutosaveEdge()")
load_at = find("if config.LOAD_SCENE:\n        # A saved board position replaces")
restore_turn_at = find("scene_io.restore_turn(loaded, turn_tracker, command_points)")
seed_at = find("autosave_edge.seed(turn_tracker)")
pregame_at = find("    elif config.PREGAME_DEPLOYMENT:", max(load_at, 0))
c.true("the edge is built before the load path reads it", 0 <= build_at < load_at)
c.true("a loaded battle is seeded AFTER its turn state is restored",
       0 <= restore_turn_at < seed_at)
c.true("...inside the load branch, not for a fresh battle", 0 <= seed_at < pregame_at)

# The frame-loop block, parsed, so a comment cannot satisfy it.
tree = ast.parse(main_src)
autosave_ifs = [
    node for node in ast.walk(tree)
    if isinstance(node, ast.If)
    and ast.unparse(node.test) == "config.AUTOSAVE"
]
c.eq("the write is gated on config.AUTOSAVE, exactly once", len(autosave_ifs), 1)
block = ast.unparse(autosave_ifs[0]) if autosave_ifs else ""
c.true("...and asks the edge", "autosave_edge.take(turn_tracker" in block)
for term in ("decision_manager.is_pending", "dice_manager.is_pending",
             "_front_notice() is None", "coherency_enforcer.pending_squad is None",
             "_any_pending_damage_choice()", "_has_unresolved_declaration()",
             "movement_controller.state != movement.MOVING",
             "shooting_controller.state == shooting.IDLE"):
    c.true(f"...only from a settled board: {term}", term in block)
c.true("...writes through the one scene writer, to the one file",
       "_save_scene(" in block and "scene_io.AUTOSAVE_NAME" in block)
c.true("...quietly (file-only log line)", "quiet=True" in block)
c.true("...and a disk error is logged, not raised", "except OSError" in block)

if_at = find("        if config.AUTOSAVE:")
c.true("the check runs outside the event loop, after the input polls",
       if_at > find("input_manager.update_measuring") > 0)
ai_tick_at = find("ai_mode.enabled() and not dice_panel.is_busy", max(if_at, 0))
c.true("...and before the AI's tick, so the AI does not act first in a new phase",
       0 <= if_at < ai_tick_at)


# --------------------------------------------------------------------------
# 5. harnesses and the shipped default
# --------------------------------------------------------------------------
print("\n=== 5. every harness opts out ===")

from game import config  # noqa: E402

c.eq("the autosave ships ON", config.AUTOSAVE, True)

drivers = []
for name in sorted(os.listdir(".")):
    if (not name.endswith(".py") or name.startswith("test_") or name in ("main.py", "run_tests.py")):
        continue
    src = _read(name)
    imports_main = re.search(r"(?m)^import main\b", src)
    if imports_main and re.search(r"\bmain\.(main|run)\(", src):
        drivers.append((name, src, imports_main.start()))

# LIVENESS: a sweep that stops finding drivers reports no violations and looks
# like a pass.
c.true(f"the sweep finds the drivers ({len(drivers)})", len(drivers) >= 12)
c.true("...selfplay.py among them - every verify_*.py runs through it",
       any(name == "selfplay.py" for name, _s, _i in drivers))
for name, src, main_at in drivers:
    opt_out = src.find("config.AUTOSAVE = False")
    c.true(f"{name} turns the autosave off before importing main", 0 <= opt_out < main_at)

c.finish()
