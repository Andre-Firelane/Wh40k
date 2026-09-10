"""A/B probes for the 2026-09-09 left-panel report, at the SOURCE.

  "das overwatch panel links scheint manchmal noch Faehigkeiten zu verdecken.
   manchmal muss ich Einheiten fuer die Verteilung irgendwelcher Mortal wounds
   auswaehlen, links steht aber overwatch."

MEASURED FIRST, and the obvious diagnosis was wrong: Fire Overwatch is branch
#29 of 30 in _draw_dispatch() and sits BELOW both damage branches, so it never
hid them. What it filled was the hole left by TWENTY-FIVE controllers with no
branch at all - main.py drew the board highlight 28 times and listed 27
controllers for the AI pause, and the panel answered for two.

The reproduced path is one pair of lines in advance_turn_phase():
flickerjump_controller.end_of_phase() starts an ASYNCHRONOUS D6 roll, and two
lines below fire_overwatch_controller.offer() sets CHOOSING_UNIT synchronously.

Fixed as ONE list with four readers (game/damage_pick.py). Each probe restores
one piece of the pre-fix world and has to make its suite red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

MAIN = "main.py"
PANEL = os.path.join("game", "ui", "action_panel.py")
PICK = os.path.join("game", "damage_pick.py")

SUITE = "test_damage_pick_panel.py"
WIRING = "test_event_chain_wiring.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    for root, dirs, _f in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


def run(suite):
    clear_cache()
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    if not match:
        return None, None, text
    return int(match.group(1)), int(match.group(2)), text


# ------------------------------------- 1. the panel loses its screen entirely
BRANCH_NEW = """        if damage_pick is not None:"""
BRANCH_OLD = """        if False:"""

# ------------------ 2. the panel answers for TWO controllers again, by name
TWO_NEW = """            self._draw_action_required(
                surface, rect, DAMAGE_CHOICE_ACCENT_COLOR,
                f'Choose which model of "{damage_pick.squad.name}" takes the wound. '
                f"Click a highlighted model on the battlefield."
            )"""
TWO_OLD = """            if damage_pick.controller.__class__.__name__ not in ("ShootingController", "FightController"):
                return
            self._draw_action_required(
                surface, rect, DAMAGE_CHOICE_ACCENT_COLOR,
                "Choose which model takes the wound. Click a highlighted model on the battlefield."
            )"""

# ------------------------------------------- 3. the record never reaches it
MAIN_REACH_NEW = """            damage_pick=frame_damage_pick,
"""
MAIN_REACH_OLD = """            damage_pick=None,
"""

# --------------------------------- 4. the panel goes inert again on a click
CLICK_NEW = """            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and left_panel_rect.collidepoint(event.pos)
                  and damage_pick.pending(damage_choice_controllers, human_players) is not None):
                action_panel.handle_click(event.pos)
"""
CLICK_OLD = ""

# ---------------------------------- 5. the board rings two answers at once
RINGS_NEW = """        fire_overwatch_target_models = (
            set() if damage_pick.pending(damage_choice_controllers, human_players) is not None
            else {token for token in state.tokens if token.squad in fire_overwatch_eligible_squads})"""
RINGS_OLD = """        fire_overwatch_target_models = {token for token in state.tokens if token.squad in fire_overwatch_eligible_squads}"""

# ------------------------- 6. the hardcoded player name comes back
OWNER_NEW = """        return damage_pick.pending(damage_choice_controllers, human_players) is not None"""
OWNER_OLD = """        return damage_pick.pending(damage_choice_controllers, {"Player 1"}) is not None"""

# --------------------------------- 7. the order stops being part of the answer
ORDER_NEW = """    for controller in controllers:
        found = _choice(controller)
        if found is None:
            continue
        choice, squad = found
        if owners is not None and squad.owner not in owners:
            continue
        return DamagePick(controller, choice, squad)
    return None"""
ORDER_OLD = """    found_all = all_pending(controllers, owners)
    return found_all[-1] if found_all else None"""

PROBES = [
    ("the panel loses the allocation screen entirely", [(PANEL, BRANCH_NEW, BRANCH_OLD)], SUITE),
    ("the panel answers for shooting and fight only, as before",
     [(PANEL, TWO_NEW, TWO_OLD)], SUITE),
    # Aimed at the WIRING suite, not the panel one: test_damage_pick_panel.py
    # calls the panel directly, so main.py's hand-off is invisible to it. That
    # is what the source guard in section 20 is for, and pointing this probe at
    # the behaviour suite would only prove the probe was pointed wrong.
    ("the record never reaches the panel", [(MAIN, MAIN_REACH_NEW, MAIN_REACH_OLD)], WIRING),
    ("the panel goes inert on a click again", [(MAIN, CLICK_NEW, CLICK_OLD)], WIRING),
    ("the board rings overwatch AND the allocation at once",
     [(MAIN, RINGS_NEW, RINGS_OLD)], WIRING),
    ("the hardcoded player name comes back", [(MAIN, OWNER_NEW, OWNER_OLD)], WIRING),
    ("pending() stops answering in list order", [(PICK, ORDER_NEW, ORDER_OLD)], SUITE),
]

print(__doc__.strip())
print()
baselines = {}
for _suite in sorted({p[2] for p in PROBES}):
    got, total, _t = run(_suite)
    baselines[_suite] = got
    print("BASELINE %-32s %s/%s" % (_suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {}
    try:
        ok = True
        for path, new, old in edits:
            originals.setdefault(path, read(path))
            src = read(path)
            if src.count(new) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)"
                      % (label, path, src.count(new)))
                ok = False
                bad += 1
                break
            write(path, src.replace(new, old))
        if not ok:
            continue
        got, tot, text = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < baselines[suite]:
            verdict, detail = "BITES", "%d/%d" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%d/%d - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL"):
                    print("             " + line.strip()[:110])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
