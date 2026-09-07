"""The bottom-left toggle strip: ONE switch, its state shown as colour and as a
sliding knob, and the "LOS Check" toggle gone for good.

Three user decisions in one place:

  1. "anstatt des textes On/Off soll es einen farblichen unterschied geben,
      damit man schneller sieht, ob etwas eingeschaltet oder ausgeschaltet ist.
      vielleicht gruen/grau. noch besser waere ein richtiger optischer toggle"
  2. "und den LOS Check Knopf brauch ich nicht mehr. der soll immer aktiviert
      sein."
  3. "ich glaube, dass man Block Deployment und Block Movement zusammenfassen
      kann. Mir faellt keine Situation ein, wo man das getrennt braeuchte."

Measured before (1): with every toggle flipped, the rendered rows were
PIXEL-IDENTICAL - the only difference in the whole strip was the word "On" or
"Off" inside the label. Section 1 pins that from the other side.

Measured for (2)+(3) together: the live LOS highlight costs 8.3 ms per
recompute on a 142-model map2 board, so the skip during a whole-unit drag has
to stay. It is now gated on a drag being IN PROGRESS rather than on the
preference - gated on the preference, decisions 2 and 3 would cancel out
(the merged toggle defaults ON, so the highlight would be off by default,
which is what decision 2 asked to stop). Section 5 pins that.

Nothing in this repo drew this strip in a test before, which is how three rows
that looked the same in both states survived unnoticed."""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((100, 100))

from game import aura_ruler, config, whole_unit_drag
from game.dice import DiceManager
from game.movement import MovementController
from game.setup import SetupController
from game.turn import TurnTracker
from game.ui import button_style
from game.ui.action_panel import ActionPanel
from testkit import Checks

c = Checks("bottom-left toggle switch")


def section(title):
    print("\n--- %s ---" % title)


HERE = os.path.dirname(os.path.abspath(__file__))
PANEL_H = 400


def toolbar(on=False, mouse=(-1, -1)):
    """Draw JUST the global toolbar and hand back (surface, rows, controllers)."""
    turn, dice = TurnTracker(), DiceManager()
    move = MovementController(turn_tracker=turn, all_tokens=[], dice_manager=dice, obstacles=[])
    setup = SetupController(game_state=None, obstacles=[], all_tokens=[])
    whole_unit_drag.set_enabled(on)
    # The range ruler's own toggle shares this strip. Pinned OFF so this
    # suite's row list is deterministic - it is a module-level session
    # preference, so another suite could otherwise leave it on - and so
    # that its radius radio (which exists only while it is on) stays out
    # of the way. test_aura_ruler.py owns that half.
    aura_ruler.set_enabled(False)

    panel = ActionPanel()
    surface = pygame.Surface((config.LEFT_PANEL_WIDTH, PANEL_H))
    surface.fill((0, 0, 0))
    panel._buttons = []
    panel._mouse_pos = mouse
    panel._mouse_down = False
    panel._draw_global_toolbar(surface, pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, PANEL_H), move)
    return surface, list(panel._buttons), move, setup


def differing_pixels(a, b):
    return sum(
        1
        for x in range(a.get_width())
        for y in range(a.get_height())
        if a.get_at((x, y)) != b.get_at((x, y))
    )


def track_rect(row):
    """Where draw_toggle() puts the switch inside one row."""
    width = min(button_style.TOGGLE_TRACK_WIDTH, max(0, row.width - 2 * button_style.TOGGLE_TEXT_MARGIN))
    return pygame.Rect(
        row.right - button_style.TOGGLE_TEXT_MARGIN - width,
        row.centery - button_style.TOGGLE_TRACK_HEIGHT // 2,
        width, button_style.TOGGLE_TRACK_HEIGHT,
    )


def knob_side(surface, row):
    """Which end of the track holds the (bright) knob - the one state cue that
    survives greyscale and colour-blindness."""
    tr = track_rect(row)
    inset = button_style.TOGGLE_KNOB_INSET + 2
    left = sum(surface.get_at((tr.x + inset, tr.centery))[:3])
    right = sum(surface.get_at((tr.right - inset, tr.centery))[:3])
    return "left" if left > right else "right"


def to_grey(surface):
    out = surface.copy()
    for x in range(out.get_width()):
        for y in range(out.get_height()):
            r, g, b = out.get_at((x, y))[:3]
            v = (r * 299 + g * 587 + b * 114) // 1000
            out.set_at((x, y), (v, v, v))
    return out


# ---------------------------------------------- 1. off and on look different

section("1. an off toggle and an on toggle do not look the same")

off_surf, off_rows, _, _ = toolbar(on=False)
on_surf, on_rows, _, _ = toolbar(on=True)

diff = differing_pixels(off_surf, on_surf)
c.true("flipping the toggle changes the strip's pixels (it used to change 0)", diff > 300)
c.eq("...and it does not change the layout", [r for r, _ in off_rows], [r for r, _ in on_rows])

# The colour half of the request: green when on, grey when off. Sampled at the
# BODY, left of any text, so this measures the fill and not the glyphs.
on_body = on_surf.get_at((on_rows[0][0].x + 3, on_rows[0][0].centery))[:3]
off_body = off_surf.get_at((off_rows[0][0].x + 3, off_rows[0][0].centery))[:3]
c.true("an on toggle's body is green-dominant %s" % (on_body,),
       on_body[1] > on_body[0] and on_body[1] > on_body[2])
c.true("an off toggle's body is neutral grey %s" % (off_body,),
       abs(off_body[0] - off_body[1]) <= 12 and abs(off_body[1] - off_body[2]) <= 12)

on_track = on_surf.get_at(track_rect(on_rows[0][0]).center)[:3]
off_track = off_surf.get_at((track_rect(off_rows[0][0]).right - 4, off_rows[0][0].centery))[:3]
c.true("the on track is green %s" % (on_track,), on_track[1] > on_track[0] and on_track[1] > on_track[2])
c.true("the off track is grey %s" % (off_track,),
       abs(off_track[0] - off_track[1]) <= 12 and abs(off_track[1] - off_track[2]) <= 12)

# The "richtiger optischer toggle" half: the knob actually slides.
c.eq("off: the knob rests on the left", knob_side(off_surf, off_rows[0][0]), "left")
c.eq("on: the knob rests on the right", knob_side(on_surf, on_rows[0][0]), "right")

# Greyscale survival - the knob cue must not need colour at all.
c.eq("in greyscale the on knob is still on the right", knob_side(to_grey(on_surf), on_rows[0][0]), "right")
c.eq("in greyscale the off knob is still on the left", knob_side(to_grey(off_surf), off_rows[0][0]), "left")


# ------------------------------------------------- 2. no more On/Off wording

section("2. the label no longer spells the state out")

_seen = []
_real_toggle = ActionPanel._draw_toggle
_real_button = ActionPanel._draw_button


def _spy_toggle(self, surface, rect, label, on):
    _seen.append((label, on))
    return _real_toggle(self, surface, rect, label, on)


def _spy_button(self, surface, rect, label, accent=None):
    _seen.append((label, None))
    return _real_button(self, surface, rect, label, accent=accent)


ActionPanel._draw_toggle = _spy_toggle
ActionPanel._draw_button = _spy_button
_seen.clear()
toolbar(on=True)
labels_on = list(_seen)
_seen.clear()
toolbar(on=False)
labels_off = list(_seen)
ActionPanel._draw_toggle = _real_toggle
ActionPanel._draw_button = _real_button

c.eq("the strip's wording does not change with the state",
     [l for l, _ in labels_on], [l for l, _ in labels_off])
c.true("no label says On/Off any more",
       not any(l.endswith(": On") or l.endswith(": Off") for l, _ in labels_on))
c.eq("...and every row in the strip is a toggle, not a plain button",
     [on for _, on in labels_on], [True, False])
c.eq("...carrying the real state", [on for _, on in labels_off], [False, False])
# One label has to cover placing AND moving now, so it names neither phase.
# The strip has since grown a second switch, the range ruler's - which is why
# this names both rows rather than counting to one.
c.eq("the rows are labelled for both jobs at once, and for the ruler",
     [l for l, _ in labels_on], ["Drag Whole Unit", "Aura"])
# It also has to fit the panel on ONE line - the two labels it replaced did
# not (measured: "Move Whole Squad" wrapped at 200px).
c.eq("...on a single line", len(button_style._toggle_layout(
    config.LEFT_PANEL_WIDTH - 20, "Drag Whole Unit", ActionPanel().button_font)[0]), 1)


# -------------------------------------------- 3. the row still works

section("3. the row is still clickable")

surf, rows, move, setup = toolbar(on=False)
# Was three, went to one when two of them merged, and is two again now that
# the range ruler has its own switch (game/aura_ruler.py).
c.eq("two toggles in the strip", len(rows), 2)
c.eq("...the drag one first, then the ruler",
     [cb.__name__ for _, cb in rows], ["toggle_group_move", "toggle"])
c.true("...tall enough for the switch",
       rows[0][0].height >= button_style.TOGGLE_TRACK_HEIGHT + 4)

# The hit-test rect is the rect DRAWN (draw_toggle grows it if a label wraps),
# the same contract _draw_button() has.
row, callback = rows[0]
c.true("the toggle's own centre lies inside its registered rect", row.collidepoint(row.center))
c.true("...and so does its bottom edge", row.collidepoint((row.centerx, row.bottom - 1)))
callback()
c.true("clicking the registered callback flips the state", move.group_move_enabled is True)
callback()
c.true("...and flips it back", move.group_move_enabled is False)

# Hover brightens without changing the state's story.
hover_surf, _, _, _ = toolbar(on=False, mouse=rows[0][0].center)
plain = off_surf.get_at((rows[0][0].x + 3, rows[0][0].centery))[:3]
hovered = hover_surf.get_at((rows[0][0].x + 3, rows[0][0].centery))[:3]
c.true("hover brightens the row %s -> %s" % (plain, hovered), sum(hovered) > sum(plain))
c.eq("...without moving the knob", knob_side(hover_surf, rows[0][0]), "left")


# ------------------------------- 4. block deployment and block movement merged

section("4. the two block toggles are one preference")

move = MovementController(turn_tracker=TurnTracker(), all_tokens=[], dice_manager=DiceManager(), obstacles=[])
setup = SetupController(game_state=None, obstacles=[], all_tokens=[])

whole_unit_drag.set_enabled(True)
c.true("movement sees it on", move.group_move_enabled is True)
c.true("...and so does deployment", setup.block_placement_enabled is True)

move.toggle_group_move()
c.true("toggling from the movement side turns deployment off too",
       setup.block_placement_enabled is False)
c.true("...consistently", move.group_move_enabled is False)

setup.toggle_block_placement()
c.true("toggling from the deployment side turns movement on too", move.group_move_enabled is True)

# Assigning either named attribute still works - fourteen read sites and
# several suites do exactly that - and lands on the one shared value.
setup.block_placement_enabled = False
c.true("assigning the deployment flag moves the shared value", whole_unit_drag.is_enabled() is False)
c.true("...which movement reads back", move.group_move_enabled is False)
move.group_move_enabled = True
c.true("assigning the movement flag moves it too", setup.block_placement_enabled is True)

# A brand-new controller must NOT reset the player's choice: it is a session
# preference, and both flags used to be __init__ assignments.
whole_unit_drag.set_enabled(False)
fresh_move = MovementController(turn_tracker=TurnTracker(), all_tokens=[], dice_manager=DiceManager(), obstacles=[])
fresh_setup = SetupController(game_state=None, obstacles=[], all_tokens=[])
c.true("a new MovementController does not reset it", fresh_move.group_move_enabled is False)
c.true("a new SetupController does not reset it either", fresh_setup.block_placement_enabled is False)

# Default: On, inherited from block placement's own long-standing default.
import importlib

importlib.reload(whole_unit_drag)
c.true("the shared default is On", whole_unit_drag.is_enabled() is True)

# The toolbar no longer needs a SetupController at all - the strongest source
# statement that the deployment half is not a second row any more.
import inspect

params = list(inspect.signature(ActionPanel._draw_global_toolbar).parameters)
c.eq("the toolbar takes no setup controller", params, ["self", "surface", "rect", "movement_controller"])

setup_src = io.open(os.path.join(HERE, "game", "setup.py"), encoding="utf-8").read()
move_src = io.open(os.path.join(HERE, "game", "movement.py"), encoding="utf-8").read()
for name, src in (("setup.py", setup_src), ("movement.py", move_src)):
    c.true("%s reads the shared preference" % name, "whole_unit_drag" in src)
    c.true("%s keeps no copy of its own" % name,
           "self.block_placement_enabled = True" not in src
           and "self.group_move_enabled = False" not in src)


# ------------------------------- 5. the LOS Check toggle is gone

section("5. the LOS Check toggle is gone and the highlight is unconditional")

c.true("MovementController has no live-LOS toggle any more",
       not hasattr(MovementController, "toggle_live_los_highlight"))
c.true("...and no live-LOS flag on the instance", not hasattr(fresh_move, "live_los_highlight_enabled"))

for name in ("main.py", os.path.join("game", "ui", "action_panel.py"), os.path.join("game", "movement.py")):
    src = io.open(os.path.join(HERE, name), encoding="utf-8").read()
    c.true("%s mentions live_los_highlight nowhere" % name, "live_los_highlight" not in src)

main_src = io.open(os.path.join(HERE, "main.py"), encoding="utf-8").read()
# Gated on a drag being IN PROGRESS, not on the preference: the preference now
# defaults to On, so reading it here would switch the highlight off by default
# and undo the decision that removed its toggle in the first place.
c.true("the highlight is skipped only while a whole-unit drag is running",
       "if anchor is None or input_manager.dragging_group or input_manager.dragging_setup_group:" in main_src)
c.true("...not while the preference merely happens to be on",
       "movement_controller.group_move_enabled:" not in main_src)
c.true("...and the block-placement drag counts as one too",
       "dragging_setup_group" in main_src)

# Those two flags really are per-drag: set on mouse-down, cleared on mouse-up.
handler_src = io.open(os.path.join(HERE, "game", "input_handler.py"), encoding="utf-8").read()
c.true("input_handler clears dragging_group when the drag ends",
       "self.dragging_group = False" in handler_src)
c.true("...and dragging_setup_group as well",
       "self.dragging_setup_group = False" in handler_src)

c.finish()
