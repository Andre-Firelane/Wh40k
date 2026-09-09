"""The "the AI is holding the game up right now" indicator.

User report: "wenn die KI am Zug ist, kommt immer so ein dunkles Overlay mit
'Claude is thinking'. Das nervt ein bisschen, weil man dann nicht so gut
verfolgen kann, was grade passiert. Ich haette es lieber, wenn kein dunkles
Overlay kommt und nur links oben in der Ecke diese Meldung kommt, dass die KI
grade was macht. So aehnlich wie wenn sie den Plan erstellt. Mache aber das
links oben in der Ecke noch ein bisschen auffaelliger dafuer. Meinetwegen kann
ein Overlay ueber die Seitenleisten sein, damit man nicht in die Versuchung
kommt, irgendwelche Knoepfe druecken zu wollen."

So the wait is signalled the other way round from how it used to be: the BOARD
stays fully legible (that is the thing you want to watch while the AI acts),
and what gets covered is the side panels - exactly the parts that are nothing
but buttons, and therefore the only parts that could tempt a click into a turn
that isn't yours. The message itself moves into a corner badge loud enough to
carry the whole signal on its own, since nothing dims any more to carry it.

One definition for every one of those moments (the flashed pause before a
blocking Claude round-trip, the threaded planning wait, and the persistent
AUTO-PLAY reminder) rather than three near-identical rounded rects copy-pasted
around main() - they sit in the same corner and must read as the same thing.
"""

import math
import time

import pygame

from game import config
from game.ui import button_style

# Amber, not the panels' cyan: this badge is the one HUD element that means
# "wait" - it deliberately does not read as another button.
BG_COLOR = (255, 199, 54)
BORDER_COLOR = (255, 246, 205)
TEXT_COLOR = (24, 18, 4)
SHADOW_COLOR = (0, 0, 0, 150)
DOT_COLOR = (150, 52, 0)

CHAMFER = 8
MARGIN = 12          # from the board area's top-left corner
PAD_X = 18
PAD_Y = 11
DOT_RADIUS = 7
DOT_GAP = 14
SHADOW_OFFSET = 4

# How hard the side panels are covered. High enough that no button reads as
# pressable, low enough that the panel is still recognisably there (a panel
# that vanishes outright looks like a crash, not like a lock).
PANEL_DIM_ALPHA = 185
PANEL_DIM_COLOR = (4, 7, 11)
PANEL_EDGE_COLOR = (255, 199, 54)   # thin amber seam facing the board, so the dim reads as "locked by the badge"
PANEL_EDGE_WIDTH = 2


# The AI-mode switch below replaced a red DOT that used to live in this file.
# User: "vielleicht dort, wo jetzt der rote punkt ist." A dot could only ever
# say "on" - it was not drawn at all while the mode was off - so there was
# nothing to click to turn the mode back on, and nothing on screen said the
# mode existed at all. The switch says both states and is the control as well
# as the indicator.


def _pulse(t):
    """0..1, one full breath every ~1.6s."""
    return 0.5 + 0.5 * math.sin(t * 4.0)


AI_TOGGLE_WIDTH = 92      # measured: "AI" needs more than the 17px a 74px-wide
                          # toggle leaves once the 32px track and its gaps are
                          # taken out. (74 was the MENU button's width, which
                          # used to share this corner.)
AI_TOGGLE_LABEL = "AI"


def ai_mode_toggle_rect(board_rect, font, avoid_rects=()):
    """Where the AI-mode switch sits: the board's top-right corner.

    User: "auesserdem waere ein toggle in der oberflaeche gut fuer den KI
    Modus. vielleicht dort, wo jetzt der rote punkt ist." So it takes the dot's
    corner - and it has to be a real control rather than a light, because a dot
    that is only drawn while the mode is ON is a thing you can never click to
    turn it back on.

    It has that corner to ITSELF now: the MENU button used to sit here and the
    switch stepped down out of its way, and the button has moved into the right
    panel's header row - "dann liegt nur noch der AI Schalter ueber der Map".
    So no caller passes avoid_rects any more and the switch stops moving, which
    is worth more than a tight margin for a control this often clicked.

    avoid_rects stays for the next thing that shares this corner, and the only
    free direction is still DOWN, for the same measured reason: the dice panel
    is top-anchored and centred inside this very board rect."""
    height = button_style.toggle_height(AI_TOGGLE_WIDTH, AI_TOGGLE_LABEL, font)
    rect = pygame.Rect(board_rect.right - MARGIN - AI_TOGGLE_WIDTH,
                       board_rect.y + MARGIN, AI_TOGGLE_WIDTH, height)
    blockers = [r for r in avoid_rects if r is not None]
    for _ in range(len(blockers)):   # cleared of one blocker, it can land on the next
        hit = next((r for r in blockers if rect.colliderect(r)), None)
        if hit is None:
            break
        rect.y = hit.bottom + MARGIN
    return rect


def draw_ai_mode_toggle(surface, board_rect, on, font, mouse_pos=None, avoid_rects=()):
    """The one AI switch, drawn in BOTH states. Returns its rect, so main()
    hit-tests exactly what was drawn.

    ONE SWITCH: user, when asked whether auto-play and the ability/Stratagem
    gates should be separate things - "das ist fuer mich das gleiche. KI -
    Modus ist autoplay, erkennbar am roten punkt. das steuert auch, ob die ki
    pfade fuer faehigkeiten und stratagems aktiviert sind. verstehe nicht warum
    man das trennen sollte." See game/ai_mode.py for how one live flag reaches
    the ~83 gates that were built once, at the start of the battle.

    button_style.draw_toggle() rather than a bespoke light, so the board's
    switch and the left panel's switches are one visual language - and so this
    one inherits the three redundant state cues that were argued for there
    (knob side, track colour, border/text colour), which a coloured dot has
    exactly none of."""
    rect = ai_mode_toggle_rect(board_rect, font, avoid_rects)
    mouse = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
    return button_style.draw_toggle(surface, rect, AI_TOGGLE_LABEL, on, font,
                                    hovered=rect.collidepoint(mouse))


class AiBusyBadge:
    """Draws the badge (and optionally dims a set of panel rects) onto an
    already-rendered frame. Owns nothing and remembers nothing - every caller
    decides for itself whether this frame is a waiting frame."""

    def __init__(self):
        # Deliberately bigger than the panels' own FONT_SIZE: this replaced a
        # full-window overlay, so it has to be readable at a glance from
        # wherever on the board the eye happens to be.
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 6, bold=True)

    def draw(self, surface, message, board_rect, dim_rects=(), pulse=False, avoid_rects=()):
        """`dim_rects` are covered first (so the badge is never dimmed by its
        own overlay), then the badge is drawn at `board_rect`'s top-left
        corner. `pulse` animates the glow and the leading dot - only
        meaningful for a caller that redraws every frame; a single flashed
        frame (see main()'s show_thinking_overlay()) passes False and gets the
        halo at full strength instead of at whatever phase it happened to
        catch. Returns the badge's rect.

        `avoid_rects` is what keeps the corner from becoming its own version
        of the problem this badge was built to solve: the dice panel is
        top-anchored inside the very same board rect, and rule 15.02's
        Command Re-roll is decided WHILE a roll is on screen - measured at
        1920x1080 the two overlap by ~56px, and by far more on a narrower
        window. Rather than covering the roll it is talking about, the badge
        steps down below anything it would land on. It only ever moves
        DOWN the left edge, so "top-left corner" still describes where to
        look for it."""
        for rect in dim_rects:
            dim = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            dim.fill((*PANEL_DIM_COLOR, PANEL_DIM_ALPHA))
            surface.blit(dim, (rect.x, rect.y))
            # The seam goes on whichever edge faces the board, so left and
            # right panels are each outlined on their inner side only.
            if rect.centerx < board_rect.centerx:
                seam = pygame.Rect(rect.right - PANEL_EDGE_WIDTH, rect.y, PANEL_EDGE_WIDTH, rect.height)
            else:
                seam = pygame.Rect(rect.x, rect.y, PANEL_EDGE_WIDTH, rect.height)
            pygame.draw.rect(surface, PANEL_EDGE_COLOR, seam)

        text_surf = self.font.render(message, True, TEXT_COLOR)
        width = PAD_X + DOT_RADIUS * 2 + DOT_GAP + text_surf.get_width() + PAD_X
        height = max(text_surf.get_height() + PAD_Y * 2, DOT_RADIUS * 2 + PAD_Y * 2)
        badge_rect = pygame.Rect(board_rect.x + MARGIN, board_rect.y + MARGIN, width, height)
        blockers = [r for r in avoid_rects if r is not None]
        for _ in range(len(blockers)):  # a rect pushed clear of one blocker can land on the next
            hit = next((r for r in blockers if badge_rect.colliderect(r)), None)
            if hit is None:
                break
            badge_rect.y = hit.bottom + MARGIN
        badge_rect.bottom = min(badge_rect.bottom, board_rect.bottom - MARGIN)

        # Drop shadow first - the badge sits on top of the board, which can be
        # any colour at all, and a shadow is what keeps its edge readable over
        # a light patch of terrain.
        shadow = pygame.Surface((badge_rect.width, badge_rect.height), pygame.SRCALPHA)
        pygame.draw.polygon(
            shadow, SHADOW_COLOR,
            [(px - badge_rect.x, py - badge_rect.y)
             for px, py in button_style.chamfer_points(badge_rect, CHAMFER)],
        )
        surface.blit(shadow, (badge_rect.x + SHADOW_OFFSET, badge_rect.y + SHADOW_OFFSET))

        level = _pulse(time.monotonic()) if pulse else 1.0
        button_style.draw_glow(
            surface, badge_rect, BG_COLOR, chamfer=CHAMFER,
            width=8, alpha=int(70 + 110 * level), pad=10,
        )
        button_style.draw_box(
            surface, badge_rect, chamfer=CHAMFER,
            bg_color=BG_COLOR, border_color=BORDER_COLOR, border_width=2,
        )

        dot_center = (badge_rect.x + PAD_X + DOT_RADIUS, badge_rect.centery)
        pygame.draw.circle(surface, DOT_COLOR, dot_center, DOT_RADIUS)
        if pulse:
            # A ring that breathes out of the dot - the cheapest "this window
            # is alive" cue there is, and the one thing a static badge during
            # a 30-second wait cannot say.
            pygame.draw.circle(
                surface, DOT_COLOR, dot_center,
                DOT_RADIUS + int(5 * level), width=1,
            )

        surface.blit(text_surf, text_surf.get_rect(
            midleft=(dot_center[0] + DOT_RADIUS + DOT_GAP, badge_rect.centery),
        ))
        return badge_rect
