"""The "AI is busy" corner badge - the class, and a guard on how main() calls it.

User report: "wenn die KI am Zug ist, kommt immer so ein dunkles Overlay mit
'Claude is thinking'. Das nervt ein bisschen, weil man dann nicht so gut
verfolgen kann, was grade passiert. Ich haette es lieber, wenn kein dunkles
Overlay kommt und nur links oben in der Ecke diese Meldung kommt... Mache aber
das links oben in der Ecke noch ein bisschen auffaelliger dafuer. Meinetwegen
kann ein Overlay ueber die Seitenleisten sein, damit man nicht in die
Versuchung kommt, irgendwelche Knoepfe druecken zu wollen."

Two halves, and the second one is the point:

  1. the badge draws what it says it draws (sections 1-3), measured in actual
     PIXELS on a real Surface - "the board is still legible" is a claim about
     what reached the screen, not about which function got called;
  2. main() still calls it the way the report asks for (section 4), checked at
     the SOURCE - the old full-window dim lived inline in main(), so a
     behavioural test of the class cannot see it come back.
"""
import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from game import config
from game.ui import button_style
from game.ui.ai_busy_badge import AiBusyBadge


c = tk.Checks("AI busy badge")


def section(title):
    print(f"\n--- {title} ---")


pygame.init()
pygame.display.set_mode((1920, 1080))

# The same geometry main() computes (see its layout block): fixed-width side
# panels pinned to their own screen edge, board = whatever is left in between.
TOP = 1080 - config.RESERVES_PANEL_HEIGHT
BOARD = pygame.Rect(config.LEFT_PANEL_WIDTH, 0, 1920 - config.LEFT_PANEL_WIDTH - config.RIGHT_PANEL_WIDTH, TOP)
LEFT = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, TOP)
RIGHT = pygame.Rect(1920 - config.RIGHT_PANEL_WIDTH, 0, config.RIGHT_PANEL_WIDTH, TOP)

BOARD_GREEN = (40, 90, 40)
PANEL_BLUE = (20, 40, 70)


def fresh_surface():
    """A frame that already has a board and two panels on it, the way the
    badge always finds one - it draws ON TOP of a finished frame, never in
    place of it."""
    surf = pygame.Surface((1920, 1080))
    surf.fill(BOARD_GREEN)
    pygame.draw.rect(surf, PANEL_BLUE, LEFT)
    pygame.draw.rect(surf, PANEL_BLUE, RIGHT)
    return surf


badge = AiBusyBadge()


# ------------------------------------------------------- 1. where it lands
section("1. corner placement")

surf = fresh_surface()
rect = badge.draw(surf, "Claude is thinking...", BOARD)

c.true("badge sits inside the board area", BOARD.contains(rect))
c.eq("...pinned to the board's left edge", rect.x - BOARD.x, 12)
c.eq("...and to its top edge", rect.y - BOARD.y, 12)
c.true("badge is drawn, not just measured", surf.get_at(rect.center)[:3] != BOARD_GREEN)

# "auffaelliger" is a size claim, so measure it. The old inline badge was
# config.FONT_SIZE with an 8x5 inflate; anything at or below that would not be
# the change that was asked for.
old_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
old_height = old_font.size("Claude is thinking...")[1] + 10
c.true(f"badge is taller than the old inline one ({rect.height} vs {old_height})", rect.height > old_height)
c.true("badge font is larger than the panels' own", badge.font.get_height() > old_font.get_height())


# --------------------------------------------------- 2. what it does NOT do
section("2. the board stays legible")

# The whole complaint: a full-window dim. Sample the board well clear of the
# badge and assert the original pixels survived, at four corners of the board
# plus its middle.
surf = fresh_surface()
badge.draw(surf, "Claude is thinking...", BOARD, dim_rects=(LEFT, RIGHT))
probes = [
    ("centre", BOARD.center),
    ("top-right", (BOARD.right - 20, 20)),
    ("bottom-left", (BOARD.x + 20, BOARD.bottom - 20)),
    ("bottom-right", (BOARD.right - 20, BOARD.bottom - 20)),
    ("just below the badge", (BOARD.x + 30, rect.bottom + 40)),
]
for label, pos in probes:
    c.eq(f"board pixel untouched: {label}", surf.get_at(pos)[:3], BOARD_GREEN)


# --------------------------------------------------- 3. the panels get dimmed
section("3. side panels covered on request")

surf = fresh_surface()
badge.draw(surf, "Claude is thinking...", BOARD, dim_rects=(LEFT, RIGHT))
left_px = surf.get_at((LEFT.centerx, 400))[:3]
right_px = surf.get_at((RIGHT.centerx, 400))[:3]
c.true(f"left panel darkened {PANEL_BLUE} -> {tuple(left_px)}", sum(left_px) < sum(PANEL_BLUE))
c.true(f"right panel darkened {PANEL_BLUE} -> {tuple(right_px)}", sum(right_px) < sum(PANEL_BLUE))
# ...but still visibly THERE. A panel dimmed to solid black reads as a crash.
c.true("left panel not blacked out entirely", sum(left_px) > 0)

# The bottom Reserves strip is deliberately NOT in main()'s dim set, and the
# badge only covers what it is handed - no rect of its own invention.
surf = fresh_surface()
badge.draw(surf, "Claude is thinking...", BOARD)
c.eq("no dim_rects -> left panel untouched", surf.get_at((LEFT.centerx, 400))[:3], PANEL_BLUE)
c.eq("no dim_rects -> right panel untouched", surf.get_at((RIGHT.centerx, 400))[:3], PANEL_BLUE)


# --------------------------------------------- 3b. stepping out of a roll's way
section("3b. avoid_rects")

# Rule 15.02's Command Re-roll is decided WHILE the roll is on screen, and the
# dice panel is top-anchored in the same board rect - measured here rather than
# assumed, since it is the one case where the corner is already occupied.
dice_rect = pygame.Rect(BOARD.x + (BOARD.width - 640) // 2, 32, 640, 300)
plain = badge.draw(fresh_surface(), "Claude is considering a Command Re-roll...", BOARD)
c.true("the long re-roll message really would hit the dice panel", plain.colliderect(dice_rect))

dodged = badge.draw(fresh_surface(), "Claude is considering a Command Re-roll...", BOARD,
                    avoid_rects=(dice_rect,))
c.true("...so it steps clear of it", not dodged.colliderect(dice_rect))
c.eq("...downwards, staying on the board's left edge", dodged.x, plain.x)
c.true("...and no further than it has to", dodged.y <= dice_rect.bottom + 12)
c.true("...still on the board", BOARD.contains(dodged))

# A frame with no roll on screen hands over None (DicePanel.last_backdrop_rect
# is cleared on every draw that puts nothing up), which must not move anything.
c.eq("None blocker is ignored",
     badge.draw(fresh_surface(), "Claude is thinking...", BOARD, avoid_rects=(None,)).topleft,
     (BOARD.x + 12, BOARD.y + 12))
c.eq("a blocker it does not touch is ignored",
     badge.draw(fresh_surface(), "Claude is thinking...", BOARD,
                avoid_rects=(pygame.Rect(BOARD.right - 200, BOARD.bottom - 200, 100, 100),)).topleft,
     (BOARD.x + 12, BOARD.y + 12))


# ------------------------------------------- 3c. DicePanel actually reports it
section("3c. DicePanel.last_backdrop_rect")

from game.dice import DiceManager
from game.ui.dice_panel import DicePanel

panel = DicePanel()
c.eq("fresh panel has nothing on screen", panel.last_backdrop_rect, None)

dice_manager = DiceManager()
surf = fresh_surface()
panel.draw(surf, dice_manager, bounds_rect=BOARD)
c.eq("no roll -> still nothing on screen", panel.last_backdrop_rect, None)

dice_manager.roll(3, label="Charge roll")
for _ in range(3):  # slide-in is time-based; the rect is recorded on every drawn frame
    panel.draw(surf, dice_manager, bounds_rect=BOARD)
reported = panel.last_backdrop_rect
c.true("a visible roll reports its backdrop", reported is not None)
c.true("...inside the board bounds it was given",
       reported is not None and BOARD.colliderect(reported))

# Suppressed (a modal notice is still unread) means nothing was drawn, so
# nothing may be reported either - a stale rect would push the badge around a
# roll that is not on screen.
panel.draw(surf, dice_manager, bounds_rect=BOARD, suppressed=True)
c.eq("suppressed -> reports nothing", panel.last_backdrop_rect, None)


# ------------------------------------------------------------ 4. main() wiring
section("4. main() calls it the way the report asks")

main_src = io.open("main.py", encoding="utf-8").read()

# The bug being guarded against is the old look coming back, so this asks
# about the AI paths specifically: show_thinking_overlay() and the per-frame
# planning badge must not build a window-sized overlay any more.
thinking_i = main_src.index("def show_thinking_overlay(")
thinking_body = main_src[thinking_i:main_src.index("\n    def ", thinking_i + 10)]
c.eq("no full-window Surface left in the thinking path",
     thinking_body.count("pygame.Surface((window_width, window_height)"), 0)
c.eq("...and it goes through the shared badge", thinking_body.count("ai_busy_badge.draw("), 1)
c.true("...dimming the side panels", "dim_rects=ai_busy_dim_rects" in thinking_body)
c.true("...and stepping around a visible roll", "avoid_rects=(dice_panel.last_backdrop_rect,)" in thinking_body)
c.true("...still flipping the frame it drew", "pygame.display.flip()" in thinking_body)

# The dim set is the two SIDE panels, named - not the board, and not the
# bottom Reserves strip (User said "Seitenleisten").
dim_line = next(ln for ln in main_src.splitlines() if ln.strip().startswith("ai_busy_dim_rects ="))
c.true("dim set is exactly the two side panels",
       "left_panel_rect" in dim_line and "right_panel_rect" in dim_line
       and "board_rect_screen" not in dim_line and "reserves_panel_rect" not in dim_line)

# Both big badges come from one object - the drift this replaces was three
# hand-drawn rounded rects in three places. AUTO-PLAY is no longer one of them
# (see section 6), so two.
c.eq("every AI badge goes through AiBusyBadge", main_src.count("ai_busy_badge.draw("), 2)
c.eq("no hand-drawn badge rect left behind", main_src.count("auto_play_font"), 0)

# rindex, not index: show_thinking_overlay() now tests the same flag (it
# stands down while the planning badge is up), and the per-frame render
# block is the LAST of the two.
planning_i = main_src.rindex("if ai_memory.is_planning:")
planning_body = main_src[planning_i:main_src.index("pygame.display.flip()", planning_i)]
c.true("planning badge pulses (it is redrawn every frame)", "pulse=True" in planning_body)
c.true("planning badge dims the panels too", "dim_rects=ai_busy_dim_rects" in planning_body)
# The AI MODE is not a wait and not a badge - it is a switch, drawn every
# frame in both states, OUTSIDE the busy-badge chain. It used to be an `elif`
# on that chain, which is how it came to be drawn only while it was on.
switch_body = planning_body[planning_body.index("draw_ai_mode_toggle("):]
c.eq("the switch is not a badge", switch_body.count("ai_busy_badge.draw("), 0)
c.eq("...and never dims the panels", switch_body.count("dim_rects="), 0)
c.eq("the old auto-play dot is gone for good",
     main_src.count("draw_auto_play_dot("), 0)
c.eq("...and so is the local flag it was drawn from",
     main_src.count("ai_auto_play ="), 0)
# Drawn unconditionally: an `elif` here is exactly what made the control
# invisible - and therefore unclickable - in the state you need it in.
# Not merely "outside the elif": the assignment itself must be a bare call.
# An A/B probe wrote `ai_toggle_rect = ai_mode.enabled() and draw_ai_mode_toggle(`
# and this section stayed green - a control that is only drawn while it is on
# is a control you cannot click to turn on, which is the whole defect.
c.true("the switch is drawn unconditionally",
       re.search(r"\n\s*ai_toggle_rect = draw_ai_mode_toggle\(", main_src) is not None)
c.true("the switch is not a branch of the busy-badge chain",
       "elif" not in planning_body[planning_body.index("ai_busy_badge.draw("):
                                   planning_body.index("draw_ai_mode_toggle(")])

# The two big badges share one corner, and the thinking flash lands on top of
# an already-drawn frame - so it must stand down while the planning badge is up
# rather than leaving the wider one's tail sticking out.
c.true("the thinking flash yields to the planning badge",
       "if ai_memory.is_planning:" in thinking_body and "return" in thinking_body)

# The engine's own loading flash is a different thing and keeps its full-window
# look - guarded so a later cleanup does not "unify" the two by accident.
loading_i = main_src.index("def show_loading_overlay(")
loading_body = main_src[loading_i:main_src.index("\n    def ", loading_i + 10)]
c.eq("the ENGINE loading flash keeps its full-window dim",
     loading_body.count("pygame.Surface((window_width, window_height)"), 1)


# ------------------------------------------- 5. the glow lives in one place
section("5. shared glow")

c.true("button_style exposes draw_glow()", callable(getattr(button_style, "draw_glow", None)))
style_src = io.open("game/ui/button_style.py", encoding="utf-8").read()
c.eq("draw_button() uses it rather than its own copy",
     len(re.findall(r"glow_surf\s*=", style_src)), 1)
badge_src = io.open("game/ui/ai_busy_badge.py", encoding="utf-8").read()
c.true("the badge uses it too", "button_style.draw_glow(" in badge_src)


# ------------------------------------------------- 6. the AI-MODE switch
section("6. AI mode switch")

# User: "auesserdem waere ein toggle in der oberflaeche gut fuer den KI Modus.
# vielleicht dort, wo jetzt der rote punkt ist." It replaced a dot that was
# only drawn while the mode was ON - so there was nothing to click to turn it
# back on, which is the defect a light has and a switch does not.
from game.ui.ai_busy_badge import (  # noqa: E402
    AI_TOGGLE_LABEL, AI_TOGGLE_WIDTH, ai_mode_toggle_rect, draw_ai_mode_toggle,
)

toggle_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)

surf = fresh_surface()
on_rect = draw_ai_mode_toggle(surf, BOARD, True, toggle_font, mouse_pos=(-99, -99))

c.true("the switch sits in the board's TOP-RIGHT corner",
       on_rect.centerx > BOARD.centerx and on_rect.centery < BOARD.centery)
c.true("...inside the board, not under a side panel",
       BOARD.contains(on_rect) and not RIGHT.colliderect(on_rect)
       and not LEFT.colliderect(on_rect))

# DRAWN IN BOTH STATES - the whole reason it is a switch and not a light.
off_surf = fresh_surface()
off_rect = draw_ai_mode_toggle(off_surf, BOARD, False, toggle_font, mouse_pos=(-99, -99))
c.eq("...and in exactly the same place when it is OFF", off_rect, on_rect)


def _ink(surface, rect):
    return sum(1 for x in range(rect.x, rect.right) for y in range(rect.y, rect.bottom)
               if surface.get_at((x, y))[:3] != (0, 0, 0))


c.true("something is drawn when the mode is ON", _ink(surf, on_rect) > 100)
c.true("...and when it is OFF too", _ink(off_surf, off_rect) > 100)

# The two states must be TELLABLE APART, and not by colour alone: the knob
# slides to the other side of its track, which is the one cue that survives a
# greyscale print. Measured as "which half of the row carries more ink", the
# same way test_toggle_switches.py argues it for the left panel's switches.
def _grey_halves(surface, rect):
    left = right = 0
    for x in range(rect.x, rect.right):
        for y in range(rect.y, rect.bottom):
            r, g, b = surface.get_at((x, y))[:3]
            grey = (r * 299 + g * 587 + b * 114) // 1000
            if x < rect.centerx:
                left += grey
            else:
                right += grey
    return left, right


on_left, on_right = _grey_halves(surf, on_rect)
off_left, off_right = _grey_halves(off_surf, off_rect)
c.true("ON and OFF differ in GREYSCALE, not only in colour",
       abs((on_right - on_left) - (off_right - off_left)) > 500)
c.true("...because the knob moves to the right when it is on",
       on_right - on_left > off_right - off_left)

# Opposite corners from the flashed badge, which is drawn on top of an
# already-finished frame - the reason the label became a corner mark at all.
badge_rect = badge.draw(surf, "Claude is considering a Command Re-roll...", BOARD)
c.true("the switch cannot overlap the busy badge", not badge_rect.colliderect(on_rect))
c.true("...and it is small - the old label was a full-width badge",
       on_rect.width < badge_rect.width // 2)
c.eq("...and it is the width the module states", on_rect.width, AI_TOGGLE_WIDTH)

# It is a mode, on for whole turns, so it must not blink: two draws a moment
# apart have to look identical.
import time as _time  # noqa: E402

surf_a = fresh_surface()
draw_ai_mode_toggle(surf_a, BOARD, True, toggle_font, mouse_pos=(-99, -99))
_time.sleep(0.25)
surf_b = fresh_surface()
draw_ai_mode_toggle(surf_b, BOARD, True, toggle_font, mouse_pos=(-99, -99))
c.true("the switch does not blink",
       all(surf_a.get_at((x, on_rect.centery)) == surf_b.get_at((x, on_rect.centery))
           for x in range(on_rect.x, on_rect.right)))

# The label has to FIT, or the switch says nothing about what it switches.
c.eq("its label is one line at this width",
     len(button_style.wrap_text(toggle_font, AI_TOGGLE_LABEL.upper(),
                                AI_TOGGLE_WIDTH)), 1)

# The rect the caller hit-tests is the rect that was drawn - the switch can
# still step down out of a blocker's way, so a second computation of that
# geometry is how a control ends up clickable somewhere it is not drawn. No
# caller passes a blocker today (the MENU button used to be one and has moved
# into the right panel), so this is where the mechanism stays exercised.
blocker = pygame.Rect(BOARD.right - 90, BOARD.y + 8, 80, 30)
stepped = draw_ai_mode_toggle(fresh_surface(), BOARD, True, toggle_font,
                              mouse_pos=(-99, -99), avoid_rects=(blocker,))
c.eq("a blocked switch reports where it actually went",
     stepped, ai_mode_toggle_rect(BOARD, toggle_font, avoid_rects=(blocker,)))
c.true("...which is below the blocker", stepped.top >= blocker.bottom)


c.finish()
