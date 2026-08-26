"""The ALT ruler: InputManager's half, plus a guard on where main() calls it.

User report: "ich kann oft keine entfernungen messen. zb bei overwatch. sorge
bitte dafuer, dass ich immer entfernungen messen kann. mit alt."

The bug was never in the drawing or in the arithmetic - it was WHERE the two
entry points sat. main()'s event chain is a long if/elif over CONTROLLER STATE,
and both halves of the ruler used to live near its end: the ALT KEYDOWN/KEYUP
pair at branch 43, and InputManager.handle_event() (the only writer of
mouse_pos_in / hovered_token, the two fields renderer.draw_measure_tool()
reads) as the very last branch. Anything pending matched earlier and swallowed
both.

So this suite is in two halves, and the second one is the point:

  1. the class behaves (section 1-3), driven through real Board/token objects;
  2. main() still calls it from OUTSIDE that chain (section 4), checked at the
     SOURCE - a behavioural test of the class cannot see a wiring regression,
     which is exactly how this shipped broken. smoke_measure_tool.py proves the
     end-to-end effect through main()'s real loop; this is the cheap guard that
     runs in every regression pass.
"""
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from game import config
from game.board import Board
from game.input_handler import InputManager


c = tk.Checks("measure tool (ALT ruler)")


def section(title):
    print(f"\n--- {title} ---")


class _Token:
    """The two attributes InputManager reads off a model, and nothing else."""

    def __init__(self, x_in, y_in, radius_in):
        self.x_in = x_in
        self.y_in = y_in
        self.radius_in = radius_in

    def contains_point(self, x_in, y_in):
        return (x_in - self.x_in) ** 2 + (y_in - self.y_in) ** 2 <= self.radius_in ** 2


pygame.init()
pygame.display.set_mode((320, 240))

board = Board(config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN, config.PIXELS_PER_INCH)
PPI = config.PIXELS_PER_INCH


def px(x_in, y_in):
    return (int(round(x_in * PPI)), int(round(y_in * PPI)))


# --------------------------------------------------------- 1. pointer tracking

section("1. track_pointer() is the one writer of the two fields the ruler draws from")

alpha = _Token(10.0, 10.0, 1.0)
beta = _Token(20.0, 14.0, 1.0)
tokens = [alpha, beta]

im = InputManager()
c.eq("a fresh manager has not tracked anything yet", im.mouse_pos_in, (0.0, 0.0))
c.eq("...and hovers nothing", im.hovered_token, None)

got = im.track_pointer(px(10.0, 10.0), tokens, board)
c.true("tracking over a model returns its inches", abs(got[0] - 10.0) < 0.1 and abs(got[1] - 10.0) < 0.1)
c.true("...and records the cursor there", abs(im.mouse_pos_in[0] - 10.0) < 0.1)
c.eq("...and reports the model under it", im.hovered_token, alpha)

im.track_pointer(px(15.0, 5.0), tokens, board)
c.eq("empty ground hovers nothing", im.hovered_token, None)
c.true("...but the cursor is still tracked", abs(im.mouse_pos_in[0] - 15.0) < 0.1)

# Idempotence is what lets main() call this ahead of its event chain while
# handle_event() still calls it too - without that, the pre-chain call would
# have to consume the motion, which would freeze dragging everywhere the chain
# legitimately wants it.
before = (im.mouse_pos_in, im.hovered_token)
im.track_pointer(px(15.0, 5.0), tokens, board)
c.eq("running it twice for one event means the same as once",
     (im.mouse_pos_in, im.hovered_token), before)

# The whole safety argument for calling this ahead of handle_event() is that
# it touches NOTHING a drag depends on - not dragging_token, not drag_offset,
# not pending_move_token, not group_drag_start_in. Pinned as a field diff
# rather than left as an argument, because the day someone adds a third write
# here is the day the extra call stops being free.
im2 = InputManager()
im2.dragging_token = alpha
im2.pending_move_token = beta
im2.drag_offset = (1.5, -2.5)
im2.group_drag_start_in = (3.0, 4.0)
im2._pending_move_down_px = (11, 22)
snapshot = dict(im2.__dict__)
im2.track_pointer(px(20.0, 14.0), tokens, board)
changed = {k for k, v in im2.__dict__.items() if snapshot.get(k) is not v and snapshot.get(k) != v}
c.eq("it writes the two view fields and nothing a drag depends on",
     changed, {"mouse_pos_in", "hovered_token"})


# ------------------------------------------------------------- 2. the ALT poll

section("2. update_measuring() follows ALT's live state")

im = InputManager()
im.track_pointer(px(10.0, 10.0), tokens, board)

im.update_measuring(False)
c.eq("ALT up, nothing happens", im.measuring, False)

im.update_measuring(True)
c.eq("ALT down starts the ruler", im.measuring, True)
c.eq("...anchored on the model under the cursor", im.measure_origin_token, alpha)
c.eq("...at that model's true centre, not the pixel that was hovered",
     im.measure_origin_in, (alpha.x_in, alpha.y_in))

# The origin is a SNAPSHOT. A poll runs every frame, so re-snapshotting would
# drag the anchor along with the cursor and the ruler would always read 0".
im.track_pointer(px(20.0, 14.0), tokens, board)
im.update_measuring(True)
c.eq("holding ALT does not re-anchor the origin", im.measure_origin_in, (alpha.x_in, alpha.y_in))
c.eq("...while the far end has moved on", im.hovered_token, beta)
c.eq("...and it is still measuring", im.measuring, True)

im.update_measuring(False)
c.eq("releasing ALT ends it", im.measuring, False)
c.eq("...and drops the origin point", im.measure_origin_in, None)
c.eq("...and the origin model", im.measure_origin_token, None)

# Free-hand: pressing ALT over empty ground anchors at the bare cursor.
im.track_pointer(px(15.0, 5.0), tokens, board)
im.update_measuring(True)
c.eq("over empty ground there is no origin model", im.measure_origin_token, None)
c.true("...so the anchor is the cursor itself",
       im.measure_origin_in is not None and abs(im.measure_origin_in[0] - 15.0) < 0.1)
im.update_measuring(False)

# The mirror-image bug the old KEYDOWN/KEYUP pair had: ALT+TAB delivers the
# KEYUP to another window, so the ruler used to stay stuck on. A poll reads the
# modifier itself, so "not held any more" is all it takes.
im.track_pointer(px(10.0, 10.0), tokens, board)
im.update_measuring(True)
c.eq("ruler on", im.measuring, True)
im.update_measuring(False)  # what ALT+TAB looks like: no KEYUP ever arrives
c.eq("a lost KEYUP cannot strand the ruler on", im.measuring, False)


# ------------------------------------------- 3. handle_event still tracks alone

section("3. handle_event() remains self-sufficient")

# test_block_placement.py drives InputManager directly, with no main() around
# it, so the MOUSEMOTION branch must still do its own tracking rather than
# assume someone called track_pointer() first.
im = InputManager()


class _NoMove:
    state = "idle"
    selected_squad = None
    selected_model = None
    group_move_enabled = False

    def select(self, token):
        pass

    def can_make_move(self, squad):
        return False


im.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": px(20.0, 14.0)}),
                tokens, board, _NoMove())
c.eq("a bare handle_event(MOUSEMOTION) still sets the hover", im.hovered_token, beta)
c.true("...and the cursor position", abs(im.mouse_pos_in[0] - 20.0) < 0.1)


# --------------------------------------------------------- 4. the wiring guard

section("4. main() calls both from OUTSIDE its state-gated event chain")

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"),
           encoding="utf-8").read()
lines = src.split("\n")

loop_i = next(i for i, ln in enumerate(lines) if ln.strip() == "for event in pygame.event.get():")
# The `for event` loop sits inside the per-frame `while running` loop, so
# its OWN indent is the frame body's indent - which is where anything that
# must run once a frame, unconditionally, has to sit.
frame_body_indent = len(lines[loop_i]) - len(lines[loop_i].lstrip())
chain_indent = frame_body_indent + 4

# Where the chain begins - every branch from here on gates on controller STATE
# and only handles mouse clicks, so anything reached after it can be swallowed.
chain_i = next(i for i in range(loop_i, len(lines))
               if lines[i].strip().startswith("if event.type == pygame.QUIT"))
# ...and where it ends: the first line back at the loop's own indent level.
after_loop_i = next(i for i in range(chain_i + 1, len(lines))
                    if lines[i].strip() and (len(lines[i]) - len(lines[i].lstrip())) <= frame_body_indent)

track_lines = [i for i, ln in enumerate(lines) if "input_manager.track_pointer(" in ln]
update_lines = [i for i, ln in enumerate(lines) if "input_manager.update_measuring(" in ln]

c.eq("main() tracks the pointer exactly once", len(track_lines), 1)
c.eq("main() polls ALT exactly once", len(update_lines), 1)

c.true("pointer tracking runs BEFORE the first state gate",
       bool(track_lines) and loop_i < track_lines[0] < chain_i)
c.true("the ALT poll runs OUTSIDE the event loop entirely",
       bool(update_lines) and update_lines[0] > after_loop_i)
c.eq("...at the frame loop's own indent, not nested in a condition",
     len(lines[update_lines[0]]) - len(lines[update_lines[0]].lstrip()), frame_body_indent)

# The transition logic has one home. A stray start/stop call inside the chain
# would be exactly the swallowed-keystroke bug growing back.
chain_src = "\n".join(lines[chain_i:after_loop_i])
c.eq("no start_measuring() left inside the chain", chain_src.count("start_measuring("), 0)
c.eq("no stop_measuring() left inside the chain", chain_src.count("stop_measuring("), 0)
c.eq("the old ALT KEYDOWN branch is gone",
     len(re.findall(r"K_LALT|K_RALT", chain_src)), 0)

# And the ruler is still actually drawn every frame - a view that is only
# computed is not one you can measure with.
draw_i = next(i for i, ln in enumerate(lines) if "renderer.draw_measure_tool(" in ln)
c.eq("draw_measure_tool() is drawn unconditionally each frame",
     len(lines[draw_i]) - len(lines[draw_i].lstrip()), frame_body_indent)


c.finish()
