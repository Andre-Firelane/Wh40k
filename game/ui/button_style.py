"""Sci-fi HUD button look (chamfered hex outline + glowing border), shared
by every ActionPanel button. Replaces the old flat rect + 1px border with
something closer to a reference image the user supplied (dark panel,
angled corners, glowing cyan/blue outline, brighter on hover, brighter
still while held down).

Also carries the matching panel-chrome pieces (draw_panel_header,
draw_box) - a second reference image asked for "the bar behind the
heading and the box" to look the same on both the left (Actions) and
right (Game Status/Log) columns, so those live here too rather than being
copy-pasted per panel."""

import pygame

from game import config
from game.ui.text_utils import wrap_text

CHAMFER_SIZE = 10

# Panel chrome (section headers + boxes) - shared by ActionPanel,
# GameStatusPanel and LogPanel so the left and right columns read as one
# consistent HUD instead of three different label/box styles. Headers get
# a filled background bar behind the title (reference image: "Actions"
# sits inside its own bar, not just text with a line under it) - flat,
# no border/chamfer, so it doesn't read as a (clickable) button - the same
# bar style is reused at a shorter height for inline sub-headers (e.g.
# GameStatusPanel's ROUND/PHASE/ACTIVE PLAYER/COMMAND POINTS labels).
HEADER_MARGIN = 4
HEADER_BAR_HEIGHT = 34
HEADER_BG_COLOR = (16, 38, 58)

SUBHEADER_HEIGHT = 22

BOX_BG_COLOR = (10, 18, 28)
BOX_BORDER_COLOR = (55, 120, 165)
BOX_CHAMFER = 6

# Default ("blue") palette.
BG_NORMAL = (10, 24, 40)
BG_HOVER = (16, 42, 64)
BG_ACTIVE = (28, 74, 100)
BORDER_NORMAL = (60, 150, 205)
BORDER_HOVER = (110, 210, 255)
BORDER_ACTIVE = (190, 240, 255)
TEXT_NORMAL = (170, 220, 245)
TEXT_HOVER = (225, 245, 255)
TEXT_ACTIVE = (255, 255, 255)

# "confirm" accent (was CONFIRM_BUTTON_COLOR's flat green fill).
BG_NORMAL_CONFIRM = (10, 32, 18)
BG_HOVER_CONFIRM = (16, 56, 28)
BG_ACTIVE_CONFIRM = (28, 92, 46)
BORDER_NORMAL_CONFIRM = (70, 185, 105)
BORDER_HOVER_CONFIRM = (120, 235, 145)
BORDER_ACTIVE_CONFIRM = (200, 255, 210)

# "danger" accent - user-specified color code: red is reserved for
# Cancel/Decline buttons (was previously also used for the urgent
# Battle-Shock Roll button; that one is now the default blue instead, so
# red means one thing - "this button abandons/declines the current
# action" - consistently across the whole UI).
BG_NORMAL_DANGER = (36, 10, 10)
BG_HOVER_DANGER = (60, 16, 16)
BG_ACTIVE_DANGER = (96, 26, 26)
BORDER_NORMAL_DANGER = (205, 65, 65)
BORDER_HOVER_DANGER = (255, 110, 110)
BORDER_ACTIVE_DANGER = (255, 190, 190)

# "stratagem" accent (violet) - user-specified color code: any button that
# spends CP to use a Stratagem (Command Re-roll, Epic Challenge, Insane
# Bravery, Explosives, Crushing Impact, ...) gets this color instead of the
# default blue, so a stratagem spend is visually distinct from a free action.
BG_NORMAL_STRATAGEM = (28, 10, 40)
BG_HOVER_STRATAGEM = (46, 16, 66)
BG_ACTIVE_STRATAGEM = (72, 28, 102)
BORDER_NORMAL_STRATAGEM = (150, 70, 210)
BORDER_HOVER_STRATAGEM = (195, 120, 250)
BORDER_ACTIVE_STRATAGEM = (230, 180, 255)

TEXT_NORMAL_CONFIRM = (170, 235, 195)
TEXT_HOVER_CONFIRM = (220, 255, 230)
TEXT_NORMAL_DANGER = (245, 190, 190)
TEXT_HOVER_DANGER = (255, 225, 225)
TEXT_NORMAL_STRATAGEM = (220, 190, 245)
TEXT_HOVER_STRATAGEM = (240, 220, 255)

_PALETTES = {
    None: (BG_NORMAL, BG_HOVER, BG_ACTIVE, BORDER_NORMAL, BORDER_HOVER, BORDER_ACTIVE, TEXT_NORMAL, TEXT_HOVER),
    "confirm": (
        BG_NORMAL_CONFIRM, BG_HOVER_CONFIRM, BG_ACTIVE_CONFIRM,
        BORDER_NORMAL_CONFIRM, BORDER_HOVER_CONFIRM, BORDER_ACTIVE_CONFIRM,
        TEXT_NORMAL_CONFIRM, TEXT_HOVER_CONFIRM,
    ),
    "danger": (
        BG_NORMAL_DANGER, BG_HOVER_DANGER, BG_ACTIVE_DANGER,
        BORDER_NORMAL_DANGER, BORDER_HOVER_DANGER, BORDER_ACTIVE_DANGER,
        TEXT_NORMAL_DANGER, TEXT_HOVER_DANGER,
    ),
    "stratagem": (
        BG_NORMAL_STRATAGEM, BG_HOVER_STRATAGEM, BG_ACTIVE_STRATAGEM,
        BORDER_NORMAL_STRATAGEM, BORDER_HOVER_STRATAGEM, BORDER_ACTIVE_STRATAGEM,
        TEXT_NORMAL_STRATAGEM, TEXT_HOVER_STRATAGEM,
    ),
}


def chamfer_points(rect, cut):
    """Hexagon outline: a rectangle with its top-left and bottom-right
    corners cut off diagonally, matching the angled-corner look."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    cut = max(0, min(cut, w // 3, h // 2))
    if cut == 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return [
        (x + cut, y),
        (x + w, y),
        (x + w, y + h - cut),
        (x + w - cut, y + h),
        (x, y + h),
        (x, y + cut),
    ]


def draw_glow(surface, rect, color, chamfer=CHAMFER_SIZE, width=4, alpha=45, pad=7):
    """Soft outward halo around a chamfered shape: a wide, low-alpha copy of
    the outline, on its own alpha surface, meant to be drawn BEFORE the fill -
    the fill then covers the inward half of that stroke, leaving only the
    outward halo visible around the shape.

    Extracted from draw_button() when game/ui/ai_busy_badge.py became the
    second caller (repo convention: extract at the SECOND consumer, not
    later), so the two cannot drift into two different-looking halos."""
    glow_surf = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
    points = [(px - rect.x + pad, py - rect.y + pad) for px, py in chamfer_points(rect, chamfer)]
    pygame.draw.polygon(glow_surf, (*color, alpha), points, width=width)
    surface.blit(glow_surf, (rect.x - pad, rect.y - pad))


def draw_button(surface, rect, label, font, hovered=False, pressed=False, accent=None):
    """Draws one chamfered, glow-bordered button and returns the rect
    actually drawn (same x/y/width as requested, but grown in height to
    fit wrapped text) - callers use that returned rect both for the click
    hit-test and to stack the next button below it, exactly like the old
    flat-rect _draw_button() did."""
    lines = wrap_text(font, label.upper(), rect.width - 16) or [label.upper()]
    line_height = font.get_height() + 2
    height = max(rect.height, len(lines) * line_height + 10)
    button_rect = pygame.Rect(rect.x, rect.y, rect.width, height)

    bg_normal, bg_hover, bg_active, border_normal, border_hover, border_active, text_normal, text_hover = (
        _PALETTES.get(accent, _PALETTES[None])
    )
    bg = bg_active if pressed else (bg_hover if hovered else bg_normal)
    border = border_active if pressed else (border_hover if hovered else border_normal)
    text_color = TEXT_ACTIVE if pressed else (text_hover if hovered else text_normal)

    points = chamfer_points(button_rect, CHAMFER_SIZE)

    # Brighter/wider while hovered or pressed - see draw_glow().
    draw_glow(
        surface, button_rect, border, chamfer=CHAMFER_SIZE,
        width=9 if pressed else (7 if hovered else 4),
        alpha=130 if pressed else (90 if hovered else 45),
    )

    pygame.draw.polygon(surface, bg, points)
    pygame.draw.polygon(surface, border, points, width=2)

    text_y = button_rect.y + (button_rect.height - len(lines) * line_height) // 2
    for line in lines:
        line_surf = font.render(line, True, text_color)
        surface.blit(line_surf, line_surf.get_rect(centerx=button_rect.centerx, y=text_y))
        text_y += line_height

    return button_rect


def draw_header_bar(surface, rect, text, font, text_color=None, bg_color=None, text_margin=10, center=False):
    """One flat, rectangular background bar with its title text sitting on
    top (left-aligned unless `center`, vertically centered) - the shared building block
    behind both draw_panel_header() (a panel's main title) and any inline
    sub-header a caller wants at a custom rect (see GameStatusPanel's
    ROUND/PHASE/... row labels). Deliberately plain (no border, no
    chamfer) - User feedback: with those, the header bars read as buttons
    rather than as section labels; a flat rect keeps buttons visually
    distinct as the only clickable chrome."""
    pygame.draw.rect(surface, bg_color if bg_color is not None else HEADER_BG_COLOR, rect)
    title_surf = font.render(text, True, text_color if text_color is not None else config.PANEL_HEADER_COLOR)
    if center:
        # For a bar that isn't the full width of its panel and so has no left
        # edge to align to - see GameStatusPanel's Round counter, which sits
        # in the gap between the two players' faction badges.
        surface.blit(title_surf, title_surf.get_rect(center=rect.center))
    else:
        surface.blit(title_surf, title_surf.get_rect(midleft=(rect.x + text_margin, rect.centery)))


def draw_panel_header(surface, rect, text, font, text_color=None, bg_color=None):
    """A panel's main title: a full-width background bar right under the
    panel's own top border (reference image: "Actions" sits inside its own
    bar), not just bare text. Fixed height (not measured off the rendered
    text) so this drops into ActionPanel's existing "title, then content
    starts at a hardcoded rect.y+N" layout everywhere without having to
    re-tune every one of those N's - the bar always ends well above the
    smallest of them (rect.y+40). Returns the y position just below it,
    for callers that stack content off the return value instead."""
    bar_rect = pygame.Rect(rect.x + HEADER_MARGIN, rect.y + HEADER_MARGIN, rect.width - 2 * HEADER_MARGIN, HEADER_BAR_HEIGHT)
    draw_header_bar(surface, bar_rect, text, font, text_color=text_color, bg_color=bg_color)
    return bar_rect.bottom + 8


def draw_box(surface, rect, chamfer=BOX_CHAMFER, bg_color=None, border_color=None, border_width=1):
    """Chamfered panel box (message boxes, log entries, the big ACTION
    REQUIRED callout) - same dark-navy-fill/cyan-border/cut-corner
    language as the buttons and header bar, instead of each box picking
    its own flat rounded-rect style."""
    points = chamfer_points(rect, chamfer)
    pygame.draw.polygon(surface, bg_color if bg_color is not None else BOX_BG_COLOR, points)
    pygame.draw.polygon(surface, border_color if border_color is not None else BOX_BORDER_COLOR, points, width=border_width)
