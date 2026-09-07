"""A/B probes for the faction logo on the "PLAYER 2 TURN 1" banner.

Each probe restores ONE piece of the pre-fix world at the source and must make
the suite go red. A probe that does not bite is a finding about the TEST.

The badge is drawn in two places now (the Game Status panel and this banner),
so both suites are run: a change to the shared module that only the panel
notices, or only the banner, is exactly the drift the extraction exists to
prevent.
"""

import io
import os
import re
import shutil
import subprocess
import sys

BADGE = os.path.join("game", "ui", "faction_badge.py")
BANNER = os.path.join("game", "ui", "turn_start_overlay.py")
PANEL = os.path.join("game", "ui", "game_status_panel.py")
MAIN = "main.py"

SUITES = ["test_turn_start_overlay.py", "test_faction_badges.py"]


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def clear_pycache():
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


def run():
    clear_pycache()
    scores, text = [], ""
    for suite in SUITES:
        out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
        blob = out.stdout + out.stderr
        text += blob
        match = re.search(r"(\d+)/(\d+) checks passed", blob)
        scores.append((int(match.group(1)), int(match.group(2))) if match else (None, None))
    return scores, text


PROBES = [
    ("the banner back to no badge at all (THE REQUEST)", BANNER,
     "        badge = faction_badge.has_content(self._logo_path, self._keyword)",
     "        badge = False"),
    ("room reserved but nothing drawn in it", BANNER,
     "            faction_badge.draw(surface, tile, self._logo_path, True, self._keyword)",
     "            pass"),
    ("the heading not moved down - the badge sits on the text", BANNER,
     "            header_rect = pygame.Rect(box_rect.x, tile.bottom + BADGE_BOTTOM_GAP,\n"
     "                                      box_rect.width, box_rect.height)",
     "            header_rect = box_rect"),
    ("the logo never looked up - every faction gets a monogram", BANNER,
     "        self._logo_path = (sprites.faction_logo_path(faction_keyword)\n"
     "                           if faction_keyword else None)",
     "        self._logo_path = None"),
    ("dismiss() keeping the last army's badge", BANNER,
     "    def dismiss(self):\n        self._text = None\n        self._keyword = None\n"
     "        self._logo_path = None",
     "    def dismiss(self):\n        self._text = None"),
    ("a tile drawn for a faction that has no name either", BADGE,
     "    return logo_path is not None or bool(monogram(keyword))",
     "    return True"),
    ("the panel re-implementing the monogram instead of sharing it", PANEL,
     "_faction_monogram = faction_badge.monogram",
     "_faction_monogram = lambda keyword: (keyword or '')[:1].upper()"),
    ("the panel drawing its own tile again", PANEL,
     "        faction_badge.draw(surface, tile_rect, logo_path, active, keyword)",
     "        pass"),
    ("two derivations of who fields what", MAIN,
     "                               player_factions=current_player_factions())",
     "                               player_factions=derive_player_factions(_all_squads(state, pregame_controller)))"),
    ("the banner not told which faction (built but never fed)", MAIN,
     "                faction_keyword=current_player_factions().get(turn_tracker.turn_owner),",
     "                faction_keyword=None,"),
]

baseline, blob = run()
if any(got is None for got, _total in baseline):
    print("BASELINE DID NOT RUN:\n" + blob[-2000:])
    raise SystemExit(2)
print("baseline: " + ", ".join(f"{s}: {g}/{t}" for s, (g, t) in zip(SUITES, baseline)) + "\n")

bad = 0
for label, path, fixed, prefix in PROBES:
    src = read(path)
    if src.count(fixed) != 1:
        print(f"  SKIP     {label}: anchor not unique in {path}")
        bad += 1
        continue
    try:
        write(path, src.replace(fixed, prefix))
        scores, text = run()
        drops = [f"{s}: {g}/{t}" for s, (g, t), (b, _bt) in zip(SUITES, scores, baseline)
                 if g is None or g < b]
        if drops:
            print(f"  BITES    {label}: " + ", ".join(drops))
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:110]}")
                    break
        else:
            print(f"  NO BITE  {label}: unchanged - FINDING ABOUT THE TEST")
            bad += 1
    finally:
        write(path, src)

clear_pycache()
print()
print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
raise SystemExit(1 if bad else 0)
