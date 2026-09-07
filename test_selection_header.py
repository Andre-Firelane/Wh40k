"""The selected unit's identity lives in the left column, not on the board.

User: "Entferne das Label, das den Squad namen anzeigt, wenn man eine Einheit
auswaehlt. das label stoert auf dem spielfeld. Verlagere die info stattdessen
ganz oben in die linke spalte mit Sprite + name in einen abgeschlossenen
kasten."

TWO HALVES, and each is worthless without the other: the plate has to be gone
from the board (test_unit_selection.py section 4 owns that half now), and the
same information has to turn up at the top of the panel instead. This suite is
the second half, plus the join between them - the box shows the SAME string the
plate did, so nothing was lost in the move.

WHERE IT IS DRAWN is itself the assurance. ActionPanel._draw_dispatch() is
about forty branches with early returns, and a fact that holds across all of
them must not sit inside one of them - that is why _draw_global_toolbar() is
called from draw() and not from the dispatch, and the selection box is called
from the same place for the same reason. So the checks below drive the panel
through several UNRELATED branches and demand the box in every one.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

c = Checks("selection header box")

pygame.init()
screen = pygame.display.set_mode((1280, 720))

from game import config, movement, renderer as rmod        # noqa: E402
from game.dice import DiceManager                          # noqa: E402
from game.movement import MovementController               # noqa: E402
from game.shooting import ShootingController               # noqa: E402
from game.turn import TurnTracker, PHASE_MOVEMENT          # noqa: E402
from game.ui import action_panel as ap                     # noqa: E402
from game.ui.action_panel import ActionPanel               # noqa: E402
from game.factions.aeldari import GUARDIAN_DEFENDERS, RANGERS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL_SRC = open(os.path.join(HERE, "game", "ui", "action_panel.py"), encoding="utf-8").read()
RENDERER_SRC = open(os.path.join(HERE, "game", "renderer.py"), encoding="utf-8").read()

PANEL_H = 720 - config.RESERVES_PANEL_HEIGHT
RECT = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, PANEL_H)
BG = config.PANEL_BG_COLOR


def scene(name="1 Guardian Defenders 1", datasheet=GUARDIAN_DEFENDERS):
    squad = tk.build(datasheet, "Player 1", name=name)
    tk.line_up(squad)
    tracker = TurnTracker()
    tokens = list(squad.models)
    move = MovementController(turn_tracker=tracker, all_tokens=tokens,
                              dice_manager=DiceManager(), obstacles=[])
    shoot = ShootingController(turn_tracker=tracker, all_tokens=tokens,
                               dice_manager=DiceManager(), obstacles=[])
    return squad, move, shoot


def render(move, shoot, **kw):
    surface = pygame.Surface(RECT.size)
    surface.fill((0, 0, 0))
    ActionPanel().draw(surface, RECT, move, shoot, **kw)
    return surface


def ink_rows(surface, top=0, bottom=None):
    """Every row carrying CONTENT: a pixel that is neither the panel background
    nor the panel's own 2px frame.

    The frame has to be excluded or every row from 0 is "ink" and "the box is
    at the top" is answered by the border rather than by the box - which is
    exactly what the first version of this measured."""
    bottom = PANEL_H if bottom is None else bottom
    return [y for y in range(top, bottom)
            if any(surface.get_at((x, y))[:3] not in (BG, config.PANEL_BORDER_COLOR)
                   for x in range(4, config.LEFT_PANEL_WIDTH - 4))]


def has_color(surface, rgb, top=0, bottom=None):
    bottom = PANEL_H if bottom is None else bottom
    return any(surface.get_at((x, y))[:3] == rgb
               for y in range(top, bottom)
               for x in range(2, config.LEFT_PANEL_WIDTH - 2))


squad, move, shoot = scene()
BORDER = ap.SELECTION_BOX_BORDER_COLOR


# --------------------------------------------------------------------------
# 1. The box appears with a selection and not without one
# --------------------------------------------------------------------------
print("=== 1. the box ===")

move.selected_squad = None
empty = render(move, shoot)
move.selected_squad = squad
picked = render(move, shoot)

c.true("with a unit picked, the box's border is on screen", has_color(picked, BORDER))
# No chrome for a control that cannot do anything - this file's standing
# convention, and the alternative (an empty bordered box saying "no unit")
# would cost every branch below the same ~54px in order to say nothing.
c.true("with nothing picked there is no box", not has_color(empty, BORDER))

rows = ink_rows(picked)


def border_rows(surface):
    """Rows carrying the box's border colour - EMPTY when there is no box.

    Every check below is written to go RED on an empty list rather than raise:
    a probe whose suite crashes tells you nothing about which check it broke,
    and this repo has recorded that lesson four times (two str.index() guards,
    a None-valued row, an empty list indexed into)."""
    return [y for y in range(PANEL_H)
            if any(surface.get_at((x, y))[:3] == BORDER
                   for x in range(2, config.LEFT_PANEL_WIDTH - 2))]


def band(box):
    """(top, bottom) to scan for the box's contents; an empty span if no box,
    so a content check on a missing box counts zero pixels instead of raising."""
    return (box[0], box[-1] + 1) if box else (0, 0)


box_rows = border_rows(picked)
c.true("the box is at the very TOP of the column",
       bool(box_rows) and bool(rows) and box_rows[0] <= rows[0] + 2)
c.true("...within the first quarter of it",
       bool(box_rows) and box_rows[-1] < PANEL_H // 4)
c.true("...and inside the panel",
       bool(box_rows) and box_rows[0] >= RECT.y and box_rows[-1] < RECT.bottom)

# It is a CLOSED box ("abgeschlossener kasten"), not a rule or an underline:
# the border colour has to appear both above and below its contents.
mid = (box_rows[0] + box_rows[-1]) // 2 if box_rows else 0
c.true("it is closed top and bottom, not an underline",
       bool(box_rows) and box_rows[0] < mid < box_rows[-1] and len(box_rows) >= 4)


# --------------------------------------------------------------------------
# 2. Sprite AND name, and the name is the panel's own string
# --------------------------------------------------------------------------
print("\n=== 2. sprite + name ===")

box_top, box_bottom = band(box_rows)

# The ART. Measured as "the portrait cell's own inset background is in there,
# with something drawn on top of it" rather than by comparing against the
# sprite file - the cell is what says a thumbnail was laid out at all.
c.true("the portrait cell is inside the box",
       has_color(picked, ap.PORTRAIT_BG_COLOR, box_top, box_bottom))
art_pixels = sum(
    1
    for y in range(box_top, box_bottom)
    for x in range(ap.TEXT_MARGIN, ap.TEXT_MARGIN + ap.SELECTION_BOX_PORTRAIT_PX + 8)
    if picked.get_at((x, y))[:3] not in (BG, ap.PORTRAIT_BG_COLOR, ap.SELECTION_BOX_BG_COLOR, BORDER)
)
c.true(f"...with art drawn in it ({art_pixels} px)", art_pixels > 40)

# The TEXT, to the right of the art, in the box.
text_pixels = sum(
    1
    for y in range(box_top, box_bottom)
    for x in range(ap.TEXT_MARGIN + ap.SELECTION_BOX_PORTRAIT_PX + 12,
                   config.LEFT_PANEL_WIDTH - ap.TEXT_MARGIN - 2)
    if picked.get_at((x, y))[:3] == config.PANEL_TEXT_COLOR
)
c.true(f"...and the name beside it ({text_pixels} px)", text_pixels > 40)

# The SAME STRING the removed board plate used, which is what makes this a move
# rather than a re-invention. Checked as source, because two renders of the
# same words are not evidence that they came from one place.
c.true("the box prints the panel's own name+count string",
       'f"{squad.name} ({len(squad.models)})"' in
       PANEL_SRC.split("def _draw_selection_header(")[1].split("def _draw_global_toolbar(")[0])

# A merged attached unit's name is ~300px against ~130px of room, so it MUST
# wrap - unwrapped it would be cut off at exactly the copy number that tells
# two units off one datasheet apart.
long_squad, long_move, long_shoot = scene(
    name="1 Guardian Defenders 1 + Farseer + Warlock Conclave")
long_move.selected_squad = long_squad
long_panel = render(long_move, long_shoot)
long_rows = border_rows(long_panel)
c.true("a long name makes the box TALLER rather than overflowing it",
       bool(long_rows) and bool(box_rows)
       and (long_rows[-1] - long_rows[0]) > (box_rows[-1] - box_rows[0]))
long_top, long_bottom = band(long_rows)
c.true("...and no text escapes it to the right",
       bool(long_rows) and not any(
           long_panel.get_at((config.LEFT_PANEL_WIDTH - 3, y))[:3] == config.PANEL_TEXT_COLOR
           for y in range(long_top, long_bottom)))


# --------------------------------------------------------------------------
# 3. It survives the dispatch, which is the whole reason it is where it is
# --------------------------------------------------------------------------
print("\n=== 3. every branch, not one ===")

# _draw_dispatch() is ~40 branches with early returns. Driven through several
# unrelated ones here; a box that lived inside the movement branch would
# vanish in every one of them.
branches = []

_, m_move, m_shoot = scene()
m_move.selected_squad = squad
branches.append(("movement", render(m_move, m_shoot)))

_, f_move, f_shoot = scene()
f_move.selected_squad = squad
f_move.turn_tracker.advance_phase()          # Movement
f_move.turn_tracker.advance_phase()          # Shooting
branches.append(("shooting phase", render(f_move, f_shoot)))

_, e_move, e_shoot = scene()
e_move.selected_squad = squad
e_move.errors = ["Something went wrong with this move."]
branches.append(("with an error box", render(e_move, e_shoot)))

for label, surf in branches:
    c.true(f"the box is drawn during: {label}", has_color(surf, BORDER, 0, PANEL_H // 4))

# And the source guard for WHY: called from draw(), above the dispatch, never
# from inside it. Checked as call expressions rather than by counting a name -
# a mention in a docstring has passed a count-based guard in this repo before.
draw_body = PANEL_SRC.split("    def draw(\n")[1].split("    def _draw_selection_header(")[0]
c.true("draw() calls the header",
       "rect = self._draw_selection_header(surface, rect, movement_controller)" in draw_body)
# find(), never index(): a missing needle makes index() RAISE, and a probe
# whose suite crashes hides which check it broke. Fifth instance of that lesson
# in this repo, which is why it is spelled out again here. -1 for a missing
# header call is also the correct ordering answer - "not before" - so the check
# needs no special case for it.
c.true("...before it dispatches",
       0 <= draw_body.find("_draw_selection_header(") < draw_body.find("self._draw_dispatch("))
dispatch_body = PANEL_SRC.split("    def _draw_dispatch(\n")[1].split("    def _draw_selection_header(")[0]
c.true("...and the dispatch never draws it itself",
       "_draw_selection_header(" not in dispatch_body)


# --------------------------------------------------------------------------
# 4. What the box costs the branches below it
# --------------------------------------------------------------------------
print("\n=== 4. the rect handed on ===")

# Every branch lays itself out from rect.y, so the box moves all forty at once
# by shortening that one rect. The bottom edge must NOT move: the global
# toolbar is pinned there.
c.true("the dispatch gets a shortened rect",
       "return pygame.Rect(rect.x, top, rect.width, rect.bottom - top)" in PANEL_SRC)
c.true("...and the toolbar keeps the full one",
       "self._draw_global_toolbar(surface, full_rect, movement_controller)" in PANEL_SRC)

# Measured rather than asserted: the toggle strip sits at the same rows whether
# or not a unit is picked. That is the visible half of "the bottom did not
# move", and it is the one a wrong rect would break first.
strip_empty = [y for y in ink_rows(empty) if y > PANEL_H - 90] or [-1, -1]
strip_picked = [y for y in ink_rows(picked) if y > PANEL_H - 90] or [-2, -2]
c.eq("the bottom toolbar does not move when a unit is picked",
     (strip_picked[0], strip_picked[-1]), (strip_empty[0], strip_empty[-1]))

# The movement branch no longer prints the name a second time. Before the box
# it drew a full-width portrait row plus the label; both are the box's job now,
# and printing them twice cost ~70px of a 220px column.
move_body = PANEL_SRC.split("    def _draw_movement_ui(\n")[1]
move_body = move_body.split("\n    def ")[0]
c.true("the movement branch does not repeat the portrait",
       "_draw_unit_portrait(surface, rect, squad, text_y)" not in move_body)
c.true("...nor the name", "squad_label" not in move_body)
# The counter-check: the OTHER three portrait calls are about different units
# and stay. Without this, deleting them all would pass the two lines above.
c.eq("the other unit-portrait rows are untouched",
     PANEL_SRC.count("self._draw_unit_portrait(surface, rect,"), 3)


# --------------------------------------------------------------------------
# 5. The join with the board it came from
# --------------------------------------------------------------------------
print("\n=== 5. board and panel say one thing ===")

# The box wears the anchor ring's colour, so the ring on the board and the box
# in the column read as one statement. Pinned against the renderer's constant
# rather than a literal, so the two cannot drift.
c.eq("the box border is the selection ring's colour",
     ap.SELECTION_BOX_BORDER_COLOR, rmod.SELECTED_MODEL_COLOR)
c.eq("...and its fill is the old plate's background",
     ap.SELECTION_BOX_BG_COLOR, rmod.SELECTION_LABEL_BG_COLOR)

# The renderer still HAS the label helper - the placement identity uses it, and
# that is a different question (a unit the sequencer named, not one the player
# picked). Both directions pinned, so removing either is a visible change.
c.true("the label helper is still defined", "_draw_selection_label" in RENDERER_SRC)
c.true("...and placement identity still uses it",
       "_draw_selection_label" in
       RENDERER_SRC.split("def draw_placement_identity(")[1].split("\n    def ")[0])
c.true("...while the click-selection does not",
       "_draw_selection_label" not in
       RENDERER_SRC.split("def draw_selection(")[1].split("def draw_placement_identity(")[0])

c.finish()
