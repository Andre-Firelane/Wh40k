"""A/B probes for the Unit Statistics feature.

Each probe restores one piece of the world as it was BEFORE this feature and
re-runs the suite that is supposed to notice. A probe that does NOT break is a
finding about the TEST, not a reassurance about the code.

Run:  python ab_unit_stats.py
"""

import io
import os
import re
import shutil
import subprocess
import sys

STATS = "test_battle_stats.py"
OVERLAY = "test_unit_stats_overlay.py"

SHOOTING = "game/shooting.py"
FIGHT = "game/fight.py"
DAMAGE = "game/damage_resolution.py"
FNP = "game/feel_no_pain.py"
WEAPONS = "game/weapons.py"
MOVEMENT = "game/movement.py"
UI = "game/ui/unit_stats_overlay.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def clear_cache():
    """The documented __pycache__ race: these rewrite and restore inside the
    same second, so a stale .pyc reports the PREVIOUS run's result."""
    for root, dirs, _files in os.walk("."):
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


# --------------------------------------------------------------------- probes
# (label, [(file, current source, pre-fix source)], suite)

PROBES = [
    ("the group outcome is never reported (a missed volley credits nobody)",
     [(SHOOTING, "        self._report_group_statistics()\n", ""),
      (FIGHT, "        self._report_group_statistics()\n", "")],
     STATS),

    ("only the SAVE results are counted, so an all-miss volley is invisible",
     [(SHOOTING, "        self._report_group_statistics()\n", "")],
     STATS),

    ("the attacker is never named when damage lands (shooting)",
     [(SHOOTING, "damage_reroll=damage_reroll, attacker_squad=self.active_squad,",
       "damage_reroll=damage_reroll,")],
     STATS),

    ("the attacker is never named when damage lands (melee)",
     [(FIGHT, "stealth_drones=self.stealth_drones, waaagh=self.waaagh, attacker_squad=self.fighting_squad,",
       "stealth_drones=self.stealth_drones, waaagh=self.waaagh,")],
     STATS),

    ("Feel No Pain no longer counts as damage turned aside",
     [(FNP, "        battle_stats.report_prevented(self.model, min(successes, self.amount))\n", "")],
     STATS),

    ("damage REDUCTION no longer counts as damage turned aside",
     [(DAMAGE, "        battle_stats.report_prevented(model, amount - reduced)\n", "")],
     STATS),

    ("max_damage reads the placeholder int instead of the printed notation",
     [(WEAPONS,
       "    notation = weapon.damage_notation\n"
       "    if notation is not None:\n"
       "        return notation.sides * notation.dice + notation.bonus\n"
       "    return weapon.damage\n",
       "    return weapon.damage\n")],
     STATS),

    ("max_damage forgets multi-dice notations (2D6 reads as D6)",
     [(WEAPONS, "return notation.sides * notation.dice + notation.bonus",
       "return notation.sides + notation.bonus")],
     STATS),

    ("attacks that never got through are not counted (landed is always 0)",
     [(SHOOTING,
       '            self.current_group["landed"] = self.current_group.get("landed", 0) + failed\n',
       '            self.current_group["landed"] = self.current_group.get("landed", 0)\n')],
     STATS),

    ("the attack count is never stashed, so nothing can be compared to it",
     [(SHOOTING, '        group["attacks"] = total_attacks\n', "")],
     STATS),

    ("distance is not recorded at all",
     [(MOVEMENT,
       "        battle_stats.report_move(self.selected_squad, self.move_mode,\n"
       "                                 self._farthest_moved(self.selected_squad))\n", "")],
     STATS),

    ("the [HEAVY] bookkeeping keeps its own copy of the distance formula",
     [(MOVEMENT,
       "            self.moved_distance_this_turn[self.selected_squad] = self._farthest_moved(\n"
       "                self.selected_squad)\n",
       "            max_dist = 0.0\n"
       "            for model in self.selected_squad.models:\n"
       "                start = self.move_start.get(model.id)\n"
       "                if start is not None:\n"
       "                    dist = ((model.x_in - start[0]) ** 2 + (model.y_in - start[1]) ** 2) ** 0.5\n"
       "                    max_dist = max(max_dist, dist)\n"
       "            self.moved_distance_this_turn[self.selected_squad] = max_dist\n")],
     STATS),

    ("rule 19.01's merge is not followed, so numbers strand on a dead squad",
     [("game/battle_stats.py",
       '    while squad is not None and getattr(squad, "absorbed_into", None) is not None:',
       "    while False:")],
     STATS),

    ("the ranking keeps units with nothing to show, padding the table with zeroes",
     [("game/battle_stats.py",
       "        rows = [r for r in self._records.values() if r.owner == player and key(r) > 0]",
       "        rows = [r for r in self._records.values() if r.owner == player]")],
     STATS),

    ("a tie is broken by insertion order, so the table shuffles between frames",
     [("game/battle_stats.py",
       "        rows.sort(key=lambda r: (-key(r), r.name))",
       "        rows.sort(key=lambda r: -key(r))")],
     STATS),

    ("the resume is not saved with the scene",
     [("game/battle_stats.py",
       '        return {"units": {name: record.as_dict()\n'
       "                          for name, record in sorted(self._records.items())},\n"
       '                "unattributed_wounds": self.unattributed_wounds}',
       '        return {"units": {}, "unattributed_wounds": 0}')],
     STATS),

    # ---- the overlay -----------------------------------------------------
    ("the button is placed on its own instead of from the AI switch's rect",
     [(UI,
       "    return pygame.Rect(ai_toggle_rect.x - BUTTON_GAP - BUTTON_WIDTH, ai_toggle_rect.y,\n"
       "                       BUTTON_WIDTH, ai_toggle_rect.height)",
       "    return pygame.Rect(ai_toggle_rect.x, ai_toggle_rect.y,\n"
       "                       BUTTON_WIDTH, ai_toggle_rect.height)")],
     OVERLAY),

    ("a click on a badge falls through to the dismiss (switching army closes it)",
     [(UI,
       "            for player, rect in self.last_badge_rects.items():\n"
       "                if rect.collidepoint(event.pos):\n"
       "                    if player != self.player:\n"
       "                        self.player = player\n"
       "                        self.scroll = 0\n"
       "                    return True\n", "")],
     OVERLAY),

    ("the reported wheel bug returns: any mouse button dismisses",
     [(UI, "            if event.button != 1:\n                return True\n", "")],
     OVERLAY),

    ("the height prediction and the drawing read two different heading heights",
     [(UI, "        y += self._heading_height(heading)",
       "        y += head.get_height() + 6")],
     OVERLAY),

    ("the panel is not clipped, so its text spills past the frame",
     [(UI, "        surface.set_clip(body.clip(previous_clip) if previous_clip else body)", "")],
     OVERLAY),

    ("an empty table draws nothing at all rather than saying why",
     [(UI,
       "            empty = self.font.render(EMPTY_TEXT[key], True, DIM_TEXT_COLOR)\n"
       "            surface.blit(empty, (body.x + THUMB_COLUMN, y + 4))\n", "")],
     OVERLAY),

    ("first place is drawn like every other row",
     [(UI, "            colour = LEAD_COLOR if place == 0 else TEXT_COLOR",
       "            colour = TEXT_COLOR")],
     OVERLAY),

    # ---- the whole pre-fix world ----------------------------------------
    ("THE WHOLE PRE-FIX WORLD: nothing is recorded anywhere",
     [(SHOOTING, "        self._report_group_statistics()\n", ""),
      (FIGHT, "        self._report_group_statistics()\n", ""),
      (SHOOTING, "damage_reroll=damage_reroll, attacker_squad=self.active_squad,",
       "damage_reroll=damage_reroll,"),
      (FIGHT, "stealth_drones=self.stealth_drones, waaagh=self.waaagh, attacker_squad=self.fighting_squad,",
       "stealth_drones=self.stealth_drones, waaagh=self.waaagh,"),
      (FNP, "        battle_stats.report_prevented(self.model, min(successes, self.amount))\n", ""),
      (DAMAGE, "        battle_stats.report_prevented(model, amount - reduced)\n", ""),
      (MOVEMENT,
       "        battle_stats.report_move(self.selected_squad, self.move_mode,\n"
       "                                 self._farthest_moved(self.selected_squad))\n", "")],
     STATS),
]


# --------------------------------------------------------------------- driver

baselines = {}
for suite in sorted({probe[2] for probe in PROBES}):
    green, total, text = run(suite)
    if green is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-2000:]))
        raise SystemExit(2)
    if green != total:
        print("BASELINE IS NOT CLEAN for %s: %d/%d" % (suite, green, total))
        raise SystemExit(2)
    baselines[suite] = green
    print("baseline %-32s %d/%d" % (suite, green, total))

print()
bad = 0
for label, edits, suite in PROBES:
    originals = {}
    ok = True
    try:
        for path, new, old in edits:
            originals.setdefault(path, read(path))
            src = read(path)
            if src.count(new) != 1:
                print("  SKIP     %s\n           anchor not unique in %s (%d matches)"
                      % (label, path, src.count(new)))
                ok = False
                bad += 1
                break
            write(path, src.replace(new, old))
        if not ok:
            continue
        green, total, text = run(suite)
        if green is None:
            # A probe that CRASHES the suite is still a bite, but a noisy one:
            # a crashed run does not name the assertion that broke.
            verdict = "BITES (crash)"
        elif green < baselines[suite]:
            verdict = "BITES"
        else:
            verdict = "NO BITE  <-- FINDING ABOUT THE TEST"
            bad += 1
        got = "crash" if green is None else "%d/%d" % (green, total)
        print("  %-14s %s\n                 %s" % (verdict, label, got))
        if green is not None and green < total:
            first = next((line.strip() for line in text.splitlines()
                          if line.strip().startswith("FAIL:")), "")
            if first:
                print("                 %s" % first[:150])
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print("\n%d probe(s) did not bite" % bad if bad else "\nevery probe bit")
raise SystemExit(1 if bad else 0)
