"""A/B probes for "place out of the pool/reserves AND form up in one gesture".

Each probe restores ONE piece of the pre-fix world AT THE SOURCE, runs
test_line_drag.py, and reports how many checks fall. A probe that does not bite
is a finding about the TEST, not proof the code is fine - this repo has hit that
a dozen times - so every one of them is expected to go red here.

The smoke (smoke_pool_line_drag.py) carries its own --neutralize, which is the
whole-chain version of probe 1.

__pycache__ is cleared between runs: these probes write and restore inside the
same second, which is the documented race that once made a whole run report the
previous pass's failures.
"""

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

MAIN = os.path.join(ROOT, "main.py")
INPUT = os.path.join(ROOT, "game", "input_handler.py")


def clear_pycache():
    for dirpath, dirnames, _ in os.walk(ROOT):
        for name in list(dirnames):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, name), ignore_errors=True)
                dirnames.remove(name)


def run_suite():
    clear_pycache()
    proc = subprocess.run(
        [sys.executable, "test_line_drag.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    match = re.search(r"(\d+)/(\d+) checks passed", proc.stdout)
    if not match:
        return None, None, (proc.stdout + proc.stderr)[-700:]
    passed, total = int(match.group(1)), int(match.group(2))
    first_fail = ""
    for line in proc.stdout.splitlines():
        if "FAIL:" in line:
            first_fail = line.strip()
            break
    return passed, total, first_fail


def probe(name, edits):
    """edits: [(path, old, new), ...] applied together, then reverted."""
    originals = {}
    try:
        for path, old, new in edits:
            if path not in originals:
                originals[path] = io.open(path, encoding="utf-8").read()
            src = io.open(path, encoding="utf-8").read()
            assert src.count(old) == 1, f"{name}: anchor not unique in {path}"
            io.open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
        passed, total, note = run_suite()
    finally:
        for path, text in originals.items():
            io.open(path, "w", encoding="utf-8", newline="\n").write(text)
        clear_pycache()
    if passed is None:
        print(f"  {name}: SUITE CRASHED (also a bite)\n    {note}")
        return True
    fell = total - passed
    verdict = "BITES" if fell else "*** DID NOT BITE ***"
    print(f"  {name}: {passed}/{total}  ({fell} fell)  {verdict}")
    if note:
        print(f"    first: {note}")
    return bool(fell)


print("baseline:")
base_passed, base_total, base_note = run_suite()
print(f"  {base_passed}/{base_total}" + (f"  {base_note}" if base_note else ""))
assert base_passed == base_total, "baseline is not green - fix that before reading the probes"

print("\nprobes:")
results = []

# The route itself: with it gone, a carried unit has no way into the gesture at
# all, which is the world the report described.
results.append(probe(
    "1. the gesture has no route to a carried unit",
    [(INPUT,
      """        elif (setup_controller is not None and start_placement is not None
                and start_placement(mx_in, my_in)):""",
      """        elif False:""")],
))

# ORDER: trying the placement FIRST would interrupt a placement already open,
# and SetupController is single-slot.
results.append(probe(
    "2. the carried unit is tried BEFORE an open placement",
    [(INPUT,
      """        if setup_controller is not None and setup_controller.state == setup.PLACING:
            controller = setup_controller
            squad = setup_controller.setting_up_squad
            setup_controller.begin_drag()
        elif (setup_controller is not None and start_placement is not None
                and start_placement(mx_in, my_in)):""",
      """        if (setup_controller is not None and start_placement is not None
                and start_placement(mx_in, my_in)):
            controller = setup_controller
            squad = setup_controller.setting_up_squad
            setup_controller.begin_drag()
        elif setup_controller is not None and setup_controller.state == setup.PLACING:""")],
))

# The callback PLACES a unit, so a modal owning the board's clicks must not have
# it consulted at all.
results.append(probe(
    "3. a blocked press still consults the placement callback",
    [(INPUT,
      "        if blocked or self.line_drag_active or self.dragging_token is not None:",
      "        if self.line_drag_active or self.dragging_token is not None:")],
))

# main.py's half: without the argument the route above is dead code.
results.append(probe(
    "4. main.py never hands the gesture the callback",
    [(MAIN,
      "                    start_placement=_place_picked_unit,\n",
      "")],
))

# Three gestures, one answer. Sending the release down its own path is how one
# of them ends up skipping consume() or leaving the card carried.
results.append(probe(
    "5. the left-drag release answers the question by itself again",
    [(MAIN,
      "                    _place_picked_unit(*board.to_in(*camera.to_native_px(local)))",
      """                    ingress_controller.start_ingress(
                        picked_reserve_squad, *board.to_in(*camera.to_native_px(local)))
                    picked_reserve_squad = None""")],
))

# The left button's board branch must gate on "can this be placed NOW", not on
# "is something picked" - the latter matches while another placement is open and
# then swallows the clicks that adjust it.
results.append(probe(
    "6. the board branch gates on the flag instead of the question",
    [(MAIN,
      "                elif board_rect_screen.collidepoint(event.pos) and _carrying_a_unit():",
      "                elif board_rect_screen.collidepoint(event.pos) and (\n"
      "                        pregame_controller.awaiting_drop or picked_reserve_squad is not None):")],
))

# Set Up is single-slot: without this guard start_ingress() takes the unit off
# state.reserves and then finds start_setup() a no-op - the unit ends up on
# neither the board nor the reserve list.
results.append(probe(
    "7. the placer forgets that Set Up is single-slot",
    [(MAIN,
      "        if squad is None or not setup_controller.can_start_setup(squad):",
      "        if squad is None:")],
))

# A carried card outlives its release now, so it needs an expiry -
# can_ingress() checks the battle round but never the phase.
results.append(probe(
    "8. a carried card never expires",
    [(MAIN,
      """        if picked_reserve_squad is not None and (
                picked_reserve_squad not in state.reserves
                or turn_tracker.phase != PHASE_MOVEMENT):
            picked_reserve_squad = None""",
      "        pass")],
))

# The Rapid Ingress window is one attempt, spent on the drop whether or not the
# arrival is accepted (15.07).
results.append(probe(
    "9. the placer stops spending the Rapid Ingress window",
    [(MAIN,
      "        rapid_ingress_controller.consume(squad, setup_controller=setup_controller)",
      "        pass")],
))

# The one behavioural change no live run can reach: measured, a MockAgent game
# never puts a Player 1 unit into state.reserves at all (6000 frames, the list
# stays empty), so this probe is the only thing that can speak for "a click on a
# reserves card is a PICK, not a flicker".
results.append(probe(
    "10. the release throws the pick away again when the drop misses the board",
    [(MAIN,
      """                    _place_picked_unit(*board.to_in(*camera.to_native_px(local)))""",
      """                    _place_picked_unit(*board.to_in(*camera.to_native_px(local)))
                picked_reserve_squad = None""")],
))

results.append(probe(
    "11. no way to let go of a carried card by hand",
    [(MAIN,
      """                if picked_reserve_squad is not None:
                    picked_reserve_squad = None
                elif movement_controller.selected_squad is not None:""",
      """                if movement_controller.selected_squad is not None:""")],
))

print(f"\n{sum(results)}/{len(results)} probes bit"
      + ("" if all(results) else "   *** a probe that does not bite is a finding about the TEST ***"))
sys.exit(0 if all(results) else 1)
