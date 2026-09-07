"""A/B probes for the selection box in the left column.

Each probe restores ONE piece of the pre-change world AT THE SOURCE, runs both
affected suites, and puts it back. A probe that does not bite is a finding about
the TEST (CLAUDE.md error class 24).

Two suites, because the change has two halves and either could be delivered
without the other: test_selection_header.py owns "the box is in the panel" and
test_unit_selection.py section 4 owns "the plate is off the board".
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(ROOT, "game", "ui", "action_panel.py")
RENDERER = os.path.join(ROOT, "game", "renderer.py")

SUITES = {
    "header": (os.path.join(ROOT, "test_selection_header.py"), 29),
    "board": (os.path.join(ROOT, "test_unit_selection.py"), 77),
}


def clear_cache():
    # These probes write and restore inside the same second; a stale .pyc has
    # reported the previous pass's result here before (error class 19).
    for root, dirs, _f in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run(path):
    out = subprocess.run([sys.executable, path], capture_output=True, text=True,
                         cwd=ROOT).stdout
    for line in out.splitlines():
        if "checks passed" in line:
            got, total = line.strip().split()[0].split("/")
            return int(got), int(total)
    return -1, -1


def probe(label, old, new, path=PANEL):
    src = open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print(f"  SKIP {label}: anchor found {src.count(old)}x")
        return
    open(path, "w", encoding="utf-8").write(src.replace(old, new))
    try:
        clear_cache()
        results = {k: run(p) for k, (p, _b) in SUITES.items()}
    finally:
        open(path, "w", encoding="utf-8").write(src)
    bit = any(results[k][0] < SUITES[k][1] for k in results)
    shown = "  ".join(f"{k} {results[k][0]}/{results[k][1]}" for k in SUITES)
    print(f"  {'BITES' if bit else '*** DID NOT BITE ***':22} {shown}  {label}")


clear_cache()
print("baseline: " + "  ".join(f"{k} {run(p)[0]}/{b}" for k, (p, b) in SUITES.items()))

# 1. THE WHOLE PRE-CHANGE WORLD: no box in the panel, the plate back on the
#    board, and the movement branch printing the portrait and name again.
#    Restoring only one of the three would leave the other two doing the new
#    thing - a half probe, which is how this repo has twice been told a bug
#    never existed (error class 16). Applied to both files in turn below,
#    because probe() edits one file at a time; probes 2-4 are its pieces.
probe(
    "no box: draw() skips the header entirely",
    "        rect = self._draw_selection_header(surface, rect, movement_controller)",
    "        pass  # PRE-CHANGE: no selection box",
)

# 2. The box drawn, but INSIDE the dispatch's movement branch - where it would
#    vanish in the other ~39 branches. This is the shape the change would take
#    if someone "just added it where the name already was".
probe(
    "the box only exists in the movement branch",
    "        rect = self._draw_selection_header(surface, rect, movement_controller)",
    "        # PRE-CHANGE shape: only the movement UI knows about it\n"
    "        rect = pygame.Rect(rect)",
)

# 3. The box drawn, but the dispatch NOT shortened - so it lands underneath
#    whatever the branch below draws at rect.y + 40.
probe(
    "the dispatch is not given room for the box",
    "        top = box.bottom + SELECTION_BOX_GAP\n"
    "        return pygame.Rect(rect.x, top, rect.width, rect.bottom - top)",
    "        return rect",
)

# 4. An empty box with nothing picked - the "always draw the chrome" reading
#    this file's conventions reject.
probe(
    "a box is drawn even with nothing selected",
    "        squad = movement_controller.selected_squad\n        if squad is None:\n            return rect",
    "        squad = movement_controller.selected_squad\n        if squad is None:\n            "
    "button_style.draw_box(surface, pygame.Rect(rect.x + TEXT_MARGIN, rect.y + 7,\n"
    "                                                       rect.width - 2 * TEXT_MARGIN, 54),\n"
    "                                  chamfer=6, bg_color=SELECTION_BOX_BG_COLOR,\n"
    "                                  border_color=SELECTION_BOX_BORDER_COLOR)\n            return rect",
)

# 5. Name but no sprite - half the request.
probe(
    "the box shows the name but no art",
    "        paths = sprites.portrait_paths(squad, limit=1)\n        text_x = rect.x + TEXT_MARGIN + pad",
    "        paths = []\n        text_x = rect.x + TEXT_MARGIN + pad",
)

# 6. Sprite but no name.
probe(
    "the box shows art but no name",
    "        for line in lines:\n"
    "            surface.blit(self.font.render(line, True, config.PANEL_TEXT_COLOR), (text_x, text_y))\n"
    "            text_y += ERROR_LINE_HEIGHT",
    "        for line in lines:\n            text_y += ERROR_LINE_HEIGHT",
)

# 7. The name unwrapped - it would run out of the box and off the panel, which
#    is the failure a 300px attached-unit name actually produces.
probe(
    "the name is not wrapped",
    "        lines = wrap_text(self.font, label, text_width) or [label]",
    "        lines = [label]",
)

# 8. The board plate back. This is the half the user asked to REMOVE, and only
#    test_unit_selection.py can see it.
probe(
    "the name plate is back on the board",
    "                width=self._ring_width(SELECTION_ANCHOR_WIDTH_PX),\n            )\n",
    "                width=self._ring_width(SELECTION_ANCHOR_WIDTH_PX),\n            )\n"
    "        self._draw_selection_label(surface, board, selection.squad)\n",
    path=RENDERER,
)

# 9. The placement identity's plate removed too - the over-correction. It is a
#    DIFFERENT question (a unit the sequencer named, not one the player picked)
#    and the request did not touch it.
probe(
    "the placement identity loses its plate as well",
    "            SELECTION_OUTLINE_BUMP_PX, SELECTION_OUTLINE_WIDTH_PX,\n"
    "        )\n        self._draw_selection_label(surface, board, squad)",
    "            SELECTION_OUTLINE_BUMP_PX, SELECTION_OUTLINE_WIDTH_PX,\n        )",
    path=RENDERER,
)

# 10. The toolbar handed the SHORTENED rect - the bottom strip would drift up
#     by the box's height, which is the mistake the full_rect line exists to
#     prevent.
probe(
    "the bottom toolbar gets the shortened rect",
    "        self._draw_global_toolbar(surface, full_rect, movement_controller)",
    "        self._draw_global_toolbar(surface, rect, movement_controller)",
)
