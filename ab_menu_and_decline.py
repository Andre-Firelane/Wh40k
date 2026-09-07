"""A/B probes for the four presentation fixes of 2026-09-07.

Each probe restores ONE piece of the pre-fix world AT THE SOURCE, runs the
suites that are supposed to notice, and puts the file back. A probe that does
NOT bite is a finding about the TEST, not a clean bill of health - this repo
has that lesson written down about a dozen times over.

    python ab_menu_and_decline.py
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))

SUITES = {
    "decline": "test_decline_buttons.py",
    "menu": "test_menu_presentation.py",
    "return": "test_return_placement.py",
    "selection": "test_unit_selection.py",
    "map": "test_map_select.py",
    "gamemenu": "test_game_menu.py",
    "army": "test_army_select.py",
}


def _run(suite):
    """(passed, total) for one suite."""
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    out = subprocess.run([sys.executable, os.path.join(ROOT, SUITES[suite])],
                         capture_output=True, text=True, env=env, cwd=ROOT)
    for line in reversed((out.stdout + out.stderr).splitlines()):
        if "checks passed" in line:
            got, total = line.strip().split(" ")[0].split("/")
            return int(got), int(total)
    return 0, 0


def _clear_cache():
    """The documented __pycache__ race (error class 19): these probes rewrite
    and restore a file inside one second, so the cache is dropped between
    runs rather than letting one pass report the previous one's failures."""
    for base, dirs, _files in os.walk(ROOT):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(base, name), ignore_errors=True)


BASELINE = {}
print("baseline")
for key in SUITES:
    BASELINE[key] = _run(key)
    print("  %-10s %d/%d" % (key, *BASELINE[key]))


def probe(name, path, old, new, suites):
    """Swap `old` -> `new` in `path`, run `suites`, restore."""
    full = os.path.join(ROOT, path)
    src = io.open(full, encoding="utf-8").read()
    if old not in src:
        print("  !! %-52s PATTERN NOT FOUND in %s" % (name, path))
        return
    backup = tempfile.mktemp(suffix=".bak")
    io.open(backup, "w", encoding="utf-8", newline="").write(src)
    io.open(full, "w", encoding="utf-8", newline="").write(src.replace(old, new, 1))
    _clear_cache()
    try:
        results = {key: _run(key) for key in suites}
    finally:
        io.open(full, "w", encoding="utf-8", newline="").write(src)
        os.remove(backup)
        _clear_cache()
    bit = []
    for key, (got, total) in results.items():
        base_got, base_total = BASELINE[key]
        if got < base_got or total != base_total:
            bit.append("%s %d/%d (was %d/%d)" % (key, got, total, base_got, base_total))
    verdict = "BITES  " + "; ".join(bit) if bit else "NO BITE"
    print("  %-52s %s" % (name, verdict))


print("\n1) decline buttons")
probe("the overlay ignores the decline predicate",
      "game/ui/decision_overlay.py",
      "declines = decline_option.is_decline(option[\"label\"])",
      "declines = False",
      ["decline"])
probe("...red is a second colour of its own, not button_style's",
      "game/ui/decision_overlay.py",
      "DECLINE_BG_COLOR = button_style.BG_NORMAL_DANGER",
      "DECLINE_BG_COLOR = (90, 20, 20)",
      ["decline"])
probe("the predicate forgets a whole family of 'no'",
      "game/decline_option.py",
      '    "Keep the ",',
      "",
      ["decline"])
probe("...and forgets Cancel",
      "game/decline_option.py",
      '    "Cancel",',
      "",
      ["decline"])

print("\n2) which models just came back")
probe("the identity draw ignores the subset",
      "game/renderer.py",
      "returning = [m for m in (placing_models or []) if m in squad.models]",
      "returning = []",
      ["return"])
probe("...it rings the WHOLE unit instead",
      "game/renderer.py",
      "        if partial:\n            self.draw_returning_models(surface, board, returning)",
      "        if partial:\n            self.draw_returning_models(surface, board, list(squad.models))",
      ["return"])
probe("...one ring instead of two",
      "game/renderer.py",
      "for extra in (bump, bump + gap):",
      "for extra in (bump,):",
      ["return"])
probe("main.py never passes the subset",
      "main.py",
      "placing_models=(setup_controller.placing_models\n                                    if setup_controller.is_partial else None),",
      "placing_models=None,",
      ["selection"])

print("\n3) bigger type")
probe("the fonts go back to the old, smaller set",
      "game/ui/tile_screen.py",
      "TITLE_FONT_DELTA = 26",
      "TITLE_FONT_DELTA = 14",
      ["menu"])
probe("...the footer boxes stay measured for the old set",
      "game/ui/tile_screen.py",
      "CONFIRM_BUTTON_WIDTH = 300",
      "CONFIRM_BUTTON_WIDTH = 240",
      ["menu"])
probe("...the footer strip stays at its old height",
      "game/ui/tile_screen.py",
      "FOOTER_HEIGHT = 70",
      "FOOTER_HEIGHT = 58",
      ["menu"])
probe("...the captions under the rows come back",
      "game/ui/game_menu.py",
      "                (RESUME, _entry_label(RESUME, True), True),",
      '                (RESUME, _entry_label(RESUME, True), True, "back to the battle"),',
      ["menu", "gamemenu"])
probe("the header hint is no longer cut to fit",
      "game/ui/tile_screen.py",
      "            ellipsised(fonts[\"subtitle\"], hint, hint_max_width), True, DIM_TEXT_COLOR),",
      "            hint, True, DIM_TEXT_COLOR),",
      ["menu"])
probe("...the map screen stops measuring the room it has",
      "game/ui/map_select.py",
      "hint_max_width=self._hint_width(screen_rect),",
      "hint_max_width=None,",
      ["menu"])

print("5) the army tile header")
probe("the header height ignores how the lines really wrap",
      "game/ui/army_select.py",
      "        if entries and text_width:",
      "        if False:",
      ["army"])
probe("...and the four header blocks are not wrapped at all",
      "game/ui/army_select.py",
      "wrap_text(font, text, text_width) or [text])",
      "[text])",
      ["army"])
probe("...the summary line keeps its old fixed gap",
      "game/ui/army_select.py",
      "                + HEADER_BLOCK_GAP + self.label_font.get_height() + SUMMARY_RULE_GAP)",
      "                + 18)",
      ["army"])

print("\n4) the main menu backdrop")
probe("the startup menu goes back to the flat fill",
      "game/ui/game_menu.py",
      "            self._draw_backdrop(surface, screen_rect)",
      "            surface.fill(ts.BG_COLOR)",
      ["menu"])
probe("...the artwork is drawn with no veil over it",
      "game/ui/game_menu.py",
      "        veil = pygame.Surface(screen_rect.size, pygame.SRCALPHA)",
      "        return\n        veil = pygame.Surface(screen_rect.size, pygame.SRCALPHA)",
      ["menu"])
probe("...it is letterboxed instead of covering",
      "game/sprites.py",
      "    scale = max(width / src_w, height / src_h)",
      "    scale = min(width / src_w, height / src_h)",
      ["menu"])
probe("...the file name is spelled 'correctly' and resolves to nothing",
      "game/sprites.py",
      'MENU_BACKGROUND_NAME = "main-manu-background"',
      'MENU_BACKGROUND_NAME = "main-menu-background"',
      ["menu"])
probe("the in-battle host starts painting it too",
      "game/ui/game_menu.py",
      "        if self.in_game:\n            scrim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)",
      "        if False:\n            scrim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)",
      ["menu", "gamemenu"])
