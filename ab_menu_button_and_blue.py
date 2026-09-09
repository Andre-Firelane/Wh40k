"""A/B probes for the three clauses of one report.

User: "und bei normalen overlays habe ich jetzt meiste einen grauen knopf und
einen roten decline knopf. aendere die grauen knoepfe in blau. / ausserdem
haette ich den 'Menu' Knopf gerne oben rechts in der rechten spalte neben der
Game Status ueberschrift. / Dann liegt nur noch der AI Schalter ueber der Map"

Three clauses, three files apart, and each probe restores ONE of them at the
SOURCE. The two that matter most are the ones a pixel test cannot tell apart
from the fix:

  * a blue written by HAND instead of read from button_style - identical
    pixels, so only the source guard can see it, and that guard is the whole
    reason the modal box and the left panel cannot drift to two blues;
  * `reserve_right` accepted and then ignored, which is the half-finished edit
    this change actually passed through: the parameter is there, the caller
    passes it, and the bar does not shorten.

Run: python ab_menu_button_and_blue.py
(Exclusively - it rewrites source files while it runs. Never alongside a test
run, a measurement, an edit or a commit; CLAUDE.md error class 20 records a
probe run being caught by another session's `git add -A`.)
"""

import io
import os
import re
import shutil
import subprocess
import sys

OVERLAY = os.path.join("game", "ui", "decision_overlay.py")
STYLE = os.path.join("game", "ui", "button_style.py")
STATUS = os.path.join("game", "ui", "game_status_panel.py")
MENU = os.path.join("game", "ui", "game_menu.py")
MAIN = "main.py"

BLUE_SUITE = "test_decline_buttons.py"
MENU_SUITE = "test_game_menu.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    # The probes rewrite and restore within the same second, so a stale
    # __pycache__ entry can hand the next run the PREVIOUS world's bytecode -
    # CLAUDE.md error class 19.
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


BLUE_TRIPLE = ("BUTTON_BG_COLOR = button_style.BG_NORMAL\n"
               "BUTTON_BORDER_COLOR = button_style.BORDER_NORMAL\n"
               "BUTTON_TEXT_COLOR = button_style.TEXT_NORMAL\n")

MENU_DELEGATES = "        return button_style.header_button_rect(panel_rect)\n"

PROBES = [
    # ---- clause 1: the grey buttons ------------------------------------
    (BLUE_SUITE, OVERLAY, "the flat greys back (THE REPORT)", BLUE_TRIPLE,
     "BUTTON_BG_COLOR = (45, 45, 45)\n"
     "BUTTON_BORDER_COLOR = (120, 120, 120)\n"
     "BUTTON_TEXT_COLOR = (255, 255, 255)\n"),
    # Half of it: the fill is what the eye reads first, and a fix that moved
    # only the border would look done in a screenshot of a hovered button.
    (BLUE_SUITE, OVERLAY, "only the FILL left grey", BLUE_TRIPLE,
     "BUTTON_BG_COLOR = (45, 45, 45)\n"
     "BUTTON_BORDER_COLOR = button_style.BORDER_NORMAL\n"
     "BUTTON_TEXT_COLOR = button_style.TEXT_NORMAL\n"),
    # THE DRIFT PROBE. Same three values, written out by hand. Every pixel is
    # identical, so this bites only if the source guard is load-bearing - and
    # a copy is exactly how the box and the panel end up with two blues.
    (BLUE_SUITE, OVERLAY, "the same blue, but COPIED instead of read", BLUE_TRIPLE,
     "BUTTON_BG_COLOR = (10, 24, 40)\n"
     "BUTTON_BORDER_COLOR = (60, 150, 205)\n"
     "BUTTON_TEXT_COLOR = (170, 220, 245)\n"),
    # A blue that is not THE blue: still blue-dominant, still not grey.
    (BLUE_SUITE, OVERLAY, "a second, slightly different blue", BLUE_TRIPLE,
     "BUTTON_BG_COLOR = (12, 28, 48)\n"
     "BUTTON_BORDER_COLOR = button_style.BORDER_NORMAL\n"
     "BUTTON_TEXT_COLOR = button_style.TEXT_NORMAL\n"),

    # ---- clause 2: the MENU button in the header row --------------------
    # The half-finished edit this change really passed through: the parameter
    # exists, the panel passes it, and nothing shortens.
    (MENU_SUITE, STYLE, "reserve_right accepted and IGNORED",
     "    width = rect.width - 2 * HEADER_MARGIN - reserve_right\n",
     "    width = rect.width - 2 * HEADER_MARGIN\n"),
    # The reserve forgets the gap, so the bar and the button touch.
    (MENU_SUITE, STYLE, "the reserve forgets the gap",
     "    return HEADER_BUTTON_WIDTH + HEADER_BUTTON_GAP\n",
     "    return HEADER_BUTTON_WIDTH\n"),
    # The button placed with a margin of its own instead of the header's -
    # two answers to "how far in do things sit up there".
    (MENU_SUITE, STYLE, "the button uses a margin of its own",
     "        rect.right - HEADER_MARGIN - HEADER_BUTTON_WIDTH,\n",
     "        rect.right - 12 - HEADER_BUTTON_WIDTH,\n"),
    # The panel stops reserving: the bar goes full width and the button is
    # simply drawn on top of it - which looks right until a title grows.
    (MENU_SUITE, STATUS, "the panel reserves nothing",
     "        button_style.draw_panel_header(surface, rect, \"Game Status\", self.header_font,\n"
     "                                       reserve_right=button_style.header_button_reserve())\n",
     "        button_style.draw_panel_header(surface, rect, \"Game Status\", self.header_font)\n"),
    # GameMenu doing half the arithmetic itself instead of delegating.
    (MENU_SUITE, MENU, "GameMenu keeps geometry of its own", MENU_DELEGATES,
     "        return pygame.Rect(panel_rect.right - 12 - 74, panel_rect.y + 12, 74, 26)\n"),
    (MENU_SUITE, MAIN, "the hit test back on the board rect",
     "game_menu.button_rect(right_panel_rect).collidepoint(event.pos)",
     "game_menu.button_rect(board_rect_screen).collidepoint(event.pos)"),
    (MENU_SUITE, MAIN, "the draw back on the board rect",
     "game_menu.draw_button(screen, right_panel_rect, pygame.mouse.get_pos())",
     "game_menu.draw_button(screen, board_rect_screen, pygame.mouse.get_pos())"),

    # ---- clause 3: only the AI switch is left over the map ---------------
    (MENU_SUITE, MAIN, "the AI switch told to dodge the button again",
     "            screen, board_rect_screen, ai_mode.enabled(), ai_toggle_font,\n        )",
     "            screen, board_rect_screen, ai_mode.enabled(), ai_toggle_font,\n"
     "            avoid_rects=(game_menu.button_rect(board_rect_screen),),\n        )"),
]

# The whole pre-fix world for clause 2+3 at once, across four files - the
# faithful "before", not one line of it (CLAUDE.md error class 16).
WHOLE = [
    (STATUS,
     "        button_style.draw_panel_header(surface, rect, \"Game Status\", self.header_font,\n"
     "                                       reserve_right=button_style.header_button_reserve())\n",
     "        button_style.draw_panel_header(surface, rect, \"Game Status\", self.header_font)\n"),
    (MENU, MENU_DELEGATES,
     "        return pygame.Rect(panel_rect.right - 12 - 74, panel_rect.y + 12, 74, 26)\n"),
    (MAIN, "game_menu.button_rect(right_panel_rect).collidepoint(event.pos)",
     "game_menu.button_rect(board_rect_screen).collidepoint(event.pos)"),
    (MAIN, "game_menu.draw_button(screen, right_panel_rect, pygame.mouse.get_pos())",
     "game_menu.draw_button(screen, board_rect_screen, pygame.mouse.get_pos())"),
    (MAIN, "            screen, board_rect_screen, ai_mode.enabled(), ai_toggle_font,\n        )",
     "            screen, board_rect_screen, ai_mode.enabled(), ai_toggle_font,\n"
     "            avoid_rects=(game_menu.button_rect(board_rect_screen),),\n        )"),
]

baselines = {}
for suite in (BLUE_SUITE, MENU_SUITE):
    got, tot, blob = run(suite)
    if got is None:
        print(f"BASELINE DID NOT RUN for {suite}:\n" + blob[-1500:])
        raise SystemExit(2)
    baselines[suite] = got
    print(f"baseline {suite}: {got}/{tot}")
print()

bad = 0
for suite, path, label, fixed, replacement in PROBES:
    src = read(path)
    if src.count(fixed) != 1:
        print(f"  SKIP     {label}: anchor not unique in {path}")
        bad += 1
        continue
    try:
        write(path, src.replace(fixed, replacement))
        got, tot, text = run(suite)
        if got is None:
            print(f"  BITES    {label}: crashed - counts as red")
        elif got < baselines[suite]:
            print(f"  BITES    {label}: {got}/{tot}")
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:110]}")
                    break
        else:
            print(f"  NO BITE  {label}: {got}/{tot} - FINDING ABOUT THE TEST")
            bad += 1
    finally:
        write(path, src)

# the whole pre-fix world
saved = {path: read(path) for path, _f, _r in WHOLE}
try:
    for path, fixed, replacement in WHOLE:
        src = read(path)
        if src.count(fixed) != 1:
            print(f"  SKIP     whole pre-fix world: anchor not unique in {path}")
            bad += 1
            break
        write(path, src.replace(fixed, replacement))
    else:
        got, tot, text = run(MENU_SUITE)
        if got is None:
            print("  BITES    the WHOLE pre-fix world (clauses 2+3): crashed - counts as red")
        elif got < baselines[MENU_SUITE]:
            print(f"  BITES    the WHOLE pre-fix world (clauses 2+3): {got}/{tot}")
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:110]}")
                    break
        else:
            print(f"  NO BITE  the WHOLE pre-fix world: {got}/{tot} - FINDING ABOUT THE TEST")
            bad += 1
finally:
    for path, text in saved.items():
        write(path, text)

print()
print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
raise SystemExit(1 if bad else 0)
