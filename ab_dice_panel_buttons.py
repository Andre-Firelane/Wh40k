"""A/B probes for the dice panel's heading and re-roll buttons, at the SOURCE.

  "Niemand liest lange Saetze mit Zahlen drin im Spielgeschehen. Bei jedem Roll
   muss gross und fett drueber stehen was das fuer ein Wurf ist ... Unten im
   Panel Buttons je nach Situation: Wurf akzeptieren / 1en wiederholen / alles
   wiederholen / Fehlschlaege wiederholen. Dann poppen nicht so viele Overlays
   hintereinander auf."

The design moves the QUESTION in front of the click and leaves the arithmetic
where it was: the controllers preview their own offer (the same step methods,
with preview=True), the panel draws it as buttons, the press leaves its answer
on the roll, and the offer site takes that answer instead of opening a prompt.

Each probe restores ONE piece of the pre-fix world (or a plausible wrong
version of the new one) and has to make its suite red. Run EXCLUSIVELY - the
probes rewrite source files while they run.
"""

import io
import os
import re
import shutil
import subprocess
import sys

MAIN = "main.py"
SHOOT = os.path.join("game", "shooting.py")
FIGHT = os.path.join("game", "fight.py")
DICE = os.path.join("game", "dice.py")
RC = os.path.join("game", "roll_choice.py")
MODS = os.path.join("game", "modifiers.py")
PANEL = os.path.join("game", "ui", "dice_panel.py")
DR = os.path.join("game", "damage_resolution.py")
CHARGE = os.path.join("game", "charge_reroll.py")
REAN = os.path.join("game", "reanimation_protocols.py")

ROLL = "test_roll_choice.py"
HEADER = "test_dice_panel_header.py"
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


PROBES = [
    ("a click anywhere accepts even with a re-roll on offer",
     [(MAIN, "if _choice is None or not _choice.has_rerolls:", "if True:")], WIRING),
    ("Space/Enter no longer reach Accept",
     [(MAIN, "and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)",
       "and event.key in ()")], WIRING),
    ("Accept stops claiming the pre-acceptance offers",
     [(MAIN, """                if option.key == roll_choice.ACCEPT:
                    for source in choice.claims:
                        dice_manager.claim_reroll_offer(source)
""", "")], WIRING),
    ("shooting's offer site ignores the panel's answer",
     [(SHOOT, "if roll_choice.take(self.dice_manager, keyed_options):",
       "if False and roll_choice.take(self.dice_manager, keyed_options):")], ROLL),
    ("fight's offer site ignores the panel's answer",
     [(FIGHT, "if roll_choice.take(self.dice_manager, keyed_options):",
       "if False and roll_choice.take(self.dice_manager, keyed_options):")], ROLL),
    ("a new roll keeps the last roll's answer",
     [(DICE, """        self._chosen_reroll = None
        return values""", """        return values""")], ROLL),
    ("Accept offered even when a mandatory 1s re-roll is on the table",
     [(RC, "        return ACCEPT in self.keys", "        return True")], ROLL),
    ("the shooting preview drifts from the offer (drops 'failures')",
     [(SHOOT, "        return roll_choice.from_offer(self.active_squad.owner, options)",
       "        return roll_choice.from_offer(self.active_squad.owner, "
       "[o for o in options if o[0] != roll_choice.FAILURES])")], ROLL),
    ("the view caches past a changed die",
     [(RC, "            id(dice_manager.pending_values), tuple(dice_manager.pending_values),",
       "            id(dice_manager.pending_values),")], ROLL),
    ("the view hands the AI's offer to the human's panel",
     [(RC, "        if choice is None or choice.player not in human_players:",
       "        if choice is None:")], ROLL),
    ("the Damage roll's panel answer is never asked",
     [(DR, "            answer = self.damage_reroll.panel_answer()", "            answer = None")], ROLL),
    ("the Charge button ignores whether a 12 could reach",
     [(CHARGE, """        rolled = sum(dm.pending_values)
        if not (self.charge_controller.targets_reachable_with(rolled)
                or self.charge_controller.targets_reachable_with(MAX_CHARGE_ROLL_TOTAL)):
            return None
""", """        rolled = sum(dm.pending_values)
""")], ROLL),
    ("reanimation's offer site ignores the panel's answer",
     [(REAN, "            if roll_choice.take(self.dice_manager, keyed):",
       "            if False:")], ROLL),
    ("modifier signs flipped on the panel",
     [(MODS, "delta, source = (-mod.amount if lower_is_better else mod.amount), mod.source",
       "delta, source = (mod.amount if lower_is_better else -mod.amount), mod.source")], HEADER),
    ("the panel never draws its button row",
     [(PANEL, "            elif pending:", "            elif False:")], HEADER),

    # --- "bei rerolls, sollte es keine reroll option geben. man darf rerolls
    #     nicht rerollen." - the optional re-roll is asked on the roll as thrown.
    ("shooting hit: the automatic 1s are thrown before the optional re-roll is asked",
     [(SHOOT, "            if self._hit_reroll_choice_needed(target_squad, len(free)):",
       "            if False and self._hit_reroll_choice_needed(target_squad, len(free)):")], ROLL),
    ("shooting wound: the automatic 1s are thrown before [TWIN-LINKED] is asked",
     [(SHOOT, "            if self._twin_linked_choice_needed(weapon, len(free) - free_wounds, target_squad):",
       "            if False and self._twin_linked_choice_needed(weapon, len(free) - free_wounds, target_squad):")],
     ROLL),
    ("the shooting preview asks a re-roll step again",
     [(SHOOT, '        if step not in ("hit", "wound"):',
       '        if step not in ("hit", "hit_reroll_ones", "wound", "wound_reroll_ones"):')], ROLL),
    ("melee: keeping the result drops a mandatory 1s re-roll",
     [(FIGHT, """                lambda: self._hit_without_optional_reroll(
                    hits, crits, weapon, target_squad, weapon_label, rerollable, hit_threshold, ones),""",
       """                lambda: self._apply_sustained_hits(hits, crits, weapon, target_squad, weapon_label),""")],
     ROLL),

    # --- "buttons für fähigkeiten und stratagems sollen doch mit in das würfel
    #     panel rein, statt links in die spalte."
    ("main.py does not ask the dice panel's ability buttons",
     [(MAIN, "                    if dice_panel.action_at(event.pos) is not None:",
       "                    if False:")], WIRING),
    ("the dice panel never draws the ability row",
     [(PANEL, """                if actions:
                    y = self._draw_buttons(ops, movable_rects, surface, None, y + BUTTON_GAP, text_max_width,""",
       """                if False:
                    y = self._draw_buttons(ops, movable_rects, surface, None, y + BUTTON_GAP, text_max_width,""")],
     HEADER),
    ("an ability button loses its accent (Command Re-roll not violet)",
     [(PANEL, "accent = options[k].accent or (", "accent = (")], HEADER),
    ("a die pick offers the ability buttons instead of its Cancel",
     [(RC, "        if controller is not None and controller.selecting_die:", "        if False:")], ROLL),
    ("the dice panel's height budget ignores the ability rows",
     [(PANEL, "                         - action_rows * (BUTTON_HEIGHT + BUTTON_GAP))", ")")], HEADER),
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
        for path, current, broken in edits:
            originals.setdefault(path, read(path))
            src = read(path)
            if src.count(current) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(current)))
                ok = False
                bad += 1
                break
            write(path, src.replace(current, broken))
        if not ok:
            continue
        got, tot, text = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red; a probe should redden, not crash)"
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
        elif got is None:
            print("             " + (text.strip().splitlines() or ["?"])[-1][:110])
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
