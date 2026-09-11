"""A/B probes for the 2026-09-11 Battle Focus report, at the SOURCE.

  "battle focus +2 Movement wurde beim unteren guardian trupp nicht angeboten,
   obwohl ich noch tokens hatte. diese faehigkeit kann mehrmals angewendet
   werden pro phase."

Measured: the RULE was never broken. rules/aeldari/army_rules.md:23 prints
"You can trigger this Agile Manoeuvre more than once per phase (provided a
different unit performs it each time)", REPEATABLE_PER_PHASE implements
exactly that, and test_battle_focus.py section 3 already pinned it. The log of
the reported game says the same: logs/game_20260911_100813.log:303 spends a
token for the Avatar, seven more units move in that same Movement phase - both
Guardian Defenders squads among them - and no second Swift as the Wind, with
3 tokens still in hand.

The PANEL was the bug. The manoeuvre block lived only in _draw_movement_ui()'s
`else` arm, so pressing "Move" made all three buttons vanish, and after
Confirm moved_squad_ids shut Swift as the Wind for good. Star Engines was
worse off still: its TRIGGER requires the Advance to have HAPPENED, which only
start_run() sets, and start_run() is reachable only FROM the arm with no
buttons - so its printed trigger moment was never offered at all.

Each probe restores one piece of the pre-fix world and has to make its suite
red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

PANEL = os.path.join("game", "ui", "action_panel.py")
BF = os.path.join("game", "battle_focus.py")
MOVE = os.path.join("game", "movement.py")

SUITE = "test_battle_focus.py"
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


# ------------------------- 1. the MOVING arm loses its call - THE HEADLINE
ARM_NEW = """            # The same three manoeuvres the `else` arm below draws. A move in
            # progress IS the printed trigger ("selected to make a Normal,
            # Advance or Fall Back move"), and for Star Engines it is the only
            # state its trigger can be satisfied in at all.
            button_y = self._draw_agile_manoeuvres(
                surface, rect, button_width, button_y, squad, battle_focus_pool,
                movement_controller)

            if is_charge:"""
ARM_OLD = """            if is_charge:"""

# ---------------- 2. the two readers DIVERGE - the real hazard of (bool, why)
# The derivation probes only tip source guards; this one makes can_*() and
# why_not() genuinely disagree, so the panel would draw a live button next to
# a refusal reason for the same manoeuvre.
DIV_NEW = """    def can_swift_as_the_wind(self, squad):
        return self.why_not(SWIFT_AS_THE_WIND, squad)[0]"""
DIV_OLD = """    def can_swift_as_the_wind(self, squad):
        return (self._own_movement_phase(squad)
                and self.can_use(squad.owner, SWIFT_AS_THE_WIND, squad))"""

# --------------------------------------------- 3. the hint arm goes silent
HINT_NEW = """            elif why:
                refusals.setdefault(why, []).append(manoeuvre)"""
HINT_OLD = """            elif why:
                pass"""

# ------------- 4. why_not stops saying nothing for an army without the rule
# The naive port: refusal_reason()'s first branch is reachable whenever the
# trigger is shut, so this prints a Battle Focus line on every unit of every
# non-Aeldari army, every frame.
SILENT_NEW = """        if squad.owner not in self.tokens or not has_battle_focus(squad):
            return False, None      # never had the rule - say nothing"""
SILENT_OLD = """        if squad.owner not in self.tokens or not has_battle_focus(squad):
            return False, self.refusal_reason(squad.owner, manoeuvre, squad)"""

# --------------------------------------------- 5. the move-TYPE gate is gone
GATE_NEW = """        if movement_controller is not None and movement_controller.state == movement.MOVING:
            if movement_controller.move_mode not in movement.MovementController.NORMAL_ADVANCE_FALL_BACK_MODES:
                return button_y

        tokens_left"""
GATE_OLD = """        tokens_left"""

# ------------------------------- 6. the shared set forgets one of its three
MODES_NEW = """    NORMAL_ADVANCE_FALL_BACK_MODES = frozenset({None, "fall_back"})"""
MODES_OLD = """    NORMAL_ADVANCE_FALL_BACK_MODES = frozenset({None})"""

# ------------------------------ 7. the refusal repeats the manoeuvre's name
NAME_NEW = '            return "this Agile Manoeuvre has already been triggered this phase"'
NAME_OLD = '            return f"{manoeuvre} has already been triggered this phase"'


PROBES = [
    ("THE HEADLINE: the MOVING arm draws no manoeuvres",
     [(PANEL, ARM_NEW, ARM_OLD)], SUITE),
    ("...and the source guard sees it too", [(PANEL, ARM_NEW, ARM_OLD)], WIRING),
    ("the boolean and the reason DISAGREE", [(BF, DIV_NEW, DIV_OLD)], SUITE),
    ("the hint arm goes silent", [(PANEL, HINT_NEW, HINT_OLD)], SUITE),
    ("why_not explains itself to armies without the rule",
     [(BF, SILENT_NEW, SILENT_OLD)], SUITE),
    ("the move-TYPE gate is removed", [(PANEL, GATE_NEW, GATE_OLD)], SUITE),
    ("the shared move-mode set drops fall_back", [(MOVE, MODES_NEW, MODES_OLD)], SUITE),
    ("the refusal repeats the manoeuvre's name", [(BF, NAME_NEW, NAME_OLD)], SUITE),
    ("THE WHOLE PRE-FIX WORLD",
     [(PANEL, ARM_NEW, ARM_OLD), (BF, DIV_NEW, DIV_OLD), (PANEL, HINT_NEW, HINT_OLD)],
     SUITE),
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
