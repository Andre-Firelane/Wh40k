"""A/B probes for the two-beat pre-battle pickers.

User: "momentan geschieht die auswahl schon, wenn man draufklickt. ich haette
gerne ein auswahl highlight + button. also erst auswaehlen, dann wird die
entsprechende kachel gehighlightet und dann auf den auswahl button unten
druecken."

Each probe restores ONE pre-fix world at the SOURCE and must break its own
checks. A probe that does NOT bite is a finding about the TEST (CLAUDE.md's
error class 24), so this script exits non-zero on a silent one.

The most important probe is the first: put the commit back on the tile click.
That is literally the behaviour being removed, and if the suites stay green
under it, they are not testing the change at all.

Run: python ab_pick_then_confirm.py
"""

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

SUITES = ["test_map_select.py", "test_army_select.py"]
SMOKE = "smoke_setup_screens.py"


def run_suite(suite):
    proc = subprocess.run([sys.executable, suite], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", out)
    if not match:
        return (-1, -1)   # crashed: that counts as bitten
    return int(match.group(1)), int(match.group(2))


def run_smoke():
    proc = subprocess.run([sys.executable, SMOKE], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", out)
    if not match:
        return (-1, -1)
    return int(match.group(1)), int(match.group(2))


TARGETS = {s: run_suite for s in SUITES}
TARGETS[SMOKE] = lambda _name: run_smoke()


class Patch:
    def __init__(self, name, edits, expect):
        self.name = name
        self.edits = edits
        self.expect = expect

    def __enter__(self):
        self.backup = {}
        for path, old, new in self.edits:
            full = os.path.join(ROOT, path)
            if full not in self.backup:
                self.backup[full] = io.open(full, encoding="utf-8").read()
            src = io.open(full, encoding="utf-8").read()
            if old not in src:
                raise SystemExit(f"{self.name}: anchor not found in {path}:\n  {old[:100]}")
            io.open(full, "w", encoding="utf-8").write(src.replace(old, new, 1))
        return self

    def __exit__(self, *exc):
        for full, text in self.backup.items():
            io.open(full, "w", encoding="utf-8").write(text)
        # The documented __pycache__ race: these probes rewrite and restore
        # inside one second, so without clearing it the next probe runs the
        # previous probe's bytecode.
        for dirpath, dirnames, _ in os.walk(ROOT):
            for d in list(dirnames):
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                    dirnames.remove(d)
        return False


PROBES = [
    # 1. THE change: a tile click commits again, so there is no second beat.
    Patch(
        "clicking a map tile commits again",
        [("game/ui/map_select.py",
          "                self.select(self.tiles[index].battle_map)",
          "                self.choose(self.tiles[index].battle_map)")],
        expect=["test_map_select.py", SMOKE],
    ),
    Patch(
        "clicking an army tile commits again",
        [("game/ui/army_select.py",
          "                self.select(self.tiles[index].entry.key)",
          "                self.choose(self.tiles[index].entry.key)")],
        expect=["test_army_select.py", SMOKE],
    ),
    # 2. The button is drawn but never hit-tested - the classic "built, but
    #    never fed": it looks right and does nothing.
    Patch(
        "the map confirm button is not clickable",
        [("game/ui/map_select.py",
          "            if self.footer.confirm is not None and self.footer.confirm.collidepoint(event.pos):\n"
          "                self.confirm()\n"
          "                return not self.done",
          "            if False:\n"
          "                self.confirm()\n"
          "                return not self.done")],
        expect=["test_map_select.py", SMOKE],
    ),
    Patch(
        "the army confirm button is not clickable",
        [("game/ui/army_select.py",
          "            if self.footer.confirm is not None and self.footer.confirm.collidepoint(event.pos):\n"
          "                self.confirm()\n"
          "                return not self.done",
          "            if False:\n"
          "                self.confirm()\n"
          "                return not self.done")],
        expect=["test_army_select.py", SMOKE],
    ),
    # 3. The button is never drawn at all, so nothing can ever be committed.
    Patch(
        "the footer never draws a confirm button",
        [("game/ui/tile_screen.py",
          "    if confirm_label:\n"
          "        rect = pygame.Rect(screen_rect.right - MARGIN - CONFIRM_BUTTON_WIDTH, top,",
          "    if False:\n"
          "        rect = pygame.Rect(screen_rect.right - MARGIN - CONFIRM_BUTTON_WIDTH, top,")],
        expect=["test_map_select.py", "test_army_select.py", SMOKE],
    ),
    # 4. Confirm stops checking that anything is selected, so a press on an
    #    empty footer advances the screen with nothing picked.
    Patch(
        "confirm does not require a selection",
        [("game/ui/map_select.py",
          "        if self.selected is None:\n            return False\n        self.chosen = self.selected",
          "        self.chosen = self.selected")],
        expect=["test_map_select.py"],
    ),
    # 5. The highlight disappears: a selected tile looks like any other, so
    #    the player cannot see what they are about to confirm.
    Patch(
        "a selected tile is not highlighted",
        [("game/ui/tile_screen.py",
          "    if selected:\n"
          "        border = (TILE_BORDER_SELECTED_HOVER_COLOR if hovered\n"
          "                  else TILE_BORDER_SELECTED_COLOR)\n"
          "        bg = TILE_BG_SELECTED_COLOR",
          "    if False:\n"
          "        border = (TILE_BORDER_SELECTED_HOVER_COLOR if hovered\n"
          "                  else TILE_BORDER_SELECTED_COLOR)\n"
          "        bg = TILE_BG_SELECTED_COLOR")],
        expect=["test_map_select.py"],
    ),
    # 6. Selection reuses the HOVER colour, so "the cursor is here" and "this
    #    is your answer" become one look - the confusion being removed.
    Patch(
        "the selection colour is the hover colour",
        [("game/ui/tile_screen.py",
          "TILE_BORDER_SELECTED_COLOR = (120, 235, 150)",
          "TILE_BORDER_SELECTED_COLOR = TILE_BORDER_HOVER_COLOR")],
        expect=["test_map_select.py"],
    ),
    # 7. The badge goes, leaving colour as the only signal - nothing for a
    #    colour-blind reader.
    Patch(
        "no SELECTED badge is drawn",
        [("game/ui/tile_screen.py",
          '    surf = fonts["label"].render("SELECTED", True, SELECTED_BADGE_COLOR)',
          '    surf = fonts["label"].render("", True, SELECTED_BADGE_COLOR)')],
        expect=["test_map_select.py"],
    ),
    # 8. The army step keeps the previous player's pick, so Player 2 opens
    #    with Player 1's list already selected and one stray Confirm fields it.
    Patch(
        "the next player inherits the previous pick",
        [("game/ui/army_select.py",
          "        self.selected_key = None   # the next player starts with nothing picked\n",
          "")],
        expect=["test_army_select.py"],
    ),
    # 9. The confirm button loses its label, so pressing it from another page
    #    no longer says what is about to be committed.
    Patch(
        "the confirm button does not name the pick",
        [("game/ui/army_select.py",
          '        return f"Confirm: {army_lists.get(self.selected_key).name}"',
          '        return "Confirm"')],
        expect=["test_army_select.py"],
    ),
    # 10. Paging drops the selection - a pick made on page 1 is lost by
    #     looking at page 2.
    Patch(
        "paging throws the selection away",
        [("game/ui/army_select.py",
          "        self.hovered_tile = None\n"
          "        self.hovered_entry = None\n"
          "        self.tiles = []\n"
          "        return True\n\n"
          "    def preview(self, key, owner):",
          "        self.hovered_tile = None\n"
          "        self.hovered_entry = None\n"
          "        self.selected_key = None\n"
          "        self.tiles = []\n"
          "        return True\n\n"
          "    def preview(self, key, owner):")],
        expect=["test_army_select.py"],
    ),
]


def main():
    print("baseline...")
    base = {}
    for name, runner in TARGETS.items():
        base[name] = runner(name)
        print(f"  {name:28s} {base[name][0]}/{base[name][1]}")
        if base[name][0] != base[name][1]:
            raise SystemExit(f"baseline is not green: {name}")

    print()
    silent = []
    for probe in PROBES:
        with probe:
            results = {name: TARGETS[name](name) for name in probe.expect}
        bit = False
        lines = []
        for name, (passed, total) in results.items():
            before = base[name][0]
            if passed == -1:
                lines.append(f"{name} CRASHED")
                bit = True
            else:
                lines.append(f"{name} {passed}/{total} (was {before})")
                if passed < before:
                    bit = True
        print(f"{'BITES ' if bit else 'SILENT'}  {probe.name}")
        for line in lines:
            print(f"           {line}")
        if not bit:
            silent.append(probe.name)

    print()
    if silent:
        print("PROBES THAT DID NOT BITE (a finding about the TEST, not the code):")
        for name in silent:
            print("  -", name)
        raise SystemExit(1)
    print(f"all {len(PROBES)} probes bit")


if __name__ == "__main__":
    main()
