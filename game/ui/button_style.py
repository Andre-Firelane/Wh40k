"""Sci-fi HUD button look (chamfered hex outline + glowing border), shared
by every ActionPanel button. Replaces the old flat rect + 1px border with
something closer to a reference image the user supplied (dark panel,
angled corners, glowing cyan/blue outline, brighter on hover, brighter
still while held down).

Also carries the matching panel-chrome pieces (draw_panel_header,
draw_box, draw_scrollbar) - a second reference image asked for "the bar
behind the heading and the box" to look the same on both the left
(Actions) and right (Game Status/Log) columns, so those live here too
rather than being copy-pasted per panel."""

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
#: The inset of a header bar's title from its own left edge. Named because
#: draw_panel_header(wrap=True) has to subtract it to know how wide the title
#: may run - two hardcoded 10s would be one edit away from a title that wraps
#: against a width it is not drawn at.
HEADER_TEXT_MARGIN = 10

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

# "battle_focus" accent (turquoise) - user-specified color code: "colorcode
# fuer agile manouvers ist momentan lila wie stratagems. soll aber tuerkis
# sein. (buttons, ueberschriften)". An Agile Manoeuvre (the Aeldari Battle
# Focus army rule, game/battle_focus.py) spends a Battle Focus TOKEN, not CP,
# so it is not a rule-15.01 Stratagem spend - it used to borrow the violet
# palette, which said the wrong thing about what a click costs.
#
# Turquoise and not simply the default blue: blue means "free action" here,
# and a manoeuvre is not free - it spends a per-round, shared, four-deep
# resource. It is its own kind of cost, so it gets its own colour, exactly
# like violet is CP's. The hue is real turquoise (#40E0D0) rather than a
# blue-green nudged off the default, so the two cannot be confused at a
# glance; test_battle_focus.py pins the distance from BOTH neighbours.
BG_NORMAL_BATTLE_FOCUS = (8, 38, 36)
BG_HOVER_BATTLE_FOCUS = (14, 62, 58)
BG_ACTIVE_BATTLE_FOCUS = (24, 100, 94)
BORDER_NORMAL_BATTLE_FOCUS = (64, 224, 208)
BORDER_HOVER_BATTLE_FOCUS = (140, 245, 235)
BORDER_ACTIVE_BATTLE_FOCUS = (215, 255, 250)

TEXT_NORMAL_CONFIRM = (170, 235, 195)
TEXT_HOVER_CONFIRM = (220, 255, 230)
TEXT_NORMAL_DANGER = (245, 190, 190)
TEXT_HOVER_DANGER = (255, 225, 225)
TEXT_NORMAL_STRATAGEM = (220, 190, 245)
TEXT_HOVER_STRATAGEM = (240, 220, 255)
TEXT_NORMAL_BATTLE_FOCUS = (165, 240, 232)
TEXT_HOVER_BATTLE_FOCUS = (225, 255, 250)

# Toggle-switch palette (see draw_toggle) - a state, not an accent, so it is
# NOT in _PALETTES: an accent picks a button's colour, this picks between two
# looks of the SAME control. User-Wunsch: "anstatt des textes On/Off soll es
# einen farblichen unterschied geben... vielleicht gruen/grau. noch besser
# waere ein richtiger optischer toggle" - so the state is carried twice over,
# by COLOUR (green on / grey off) and by the KNOB's side of the track, which
# survives both a colour-blind reader and a greyscale screenshot.
#
# The green deliberately reuses the "confirm" accent's border/text/fill: green
# already means "this proceeds" everywhere else in this HUD, and a second,
# slightly different green would read as a different kind of thing.
TOGGLE_BG_ON = BG_NORMAL_CONFIRM
TOGGLE_BG_ON_HOVER = BG_HOVER_CONFIRM
TOGGLE_BORDER_ON = BORDER_NORMAL_CONFIRM
TOGGLE_BORDER_ON_HOVER = BORDER_HOVER_CONFIRM
TOGGLE_TEXT_ON = TEXT_NORMAL_CONFIRM
TOGGLE_TEXT_ON_HOVER = TEXT_HOVER_CONFIRM
TOGGLE_TRACK_ON = (52, 150, 84)
TOGGLE_TRACK_ON_HOVER = (72, 196, 112)
TOGGLE_KNOB_ON = (228, 255, 236)

# Off is a neutral grey, NOT the default blue: blue is what every enabled
# button in this panel already is, so an off toggle drawn in it would read as
# "a button", which is the exact confusion being fixed here.
TOGGLE_BG_OFF = (16, 20, 26)
TOGGLE_BG_OFF_HOVER = (28, 34, 42)
TOGGLE_BORDER_OFF = (88, 98, 108)
TOGGLE_BORDER_OFF_HOVER = (135, 150, 163)
TOGGLE_TEXT_OFF = (140, 152, 163)
TOGGLE_TEXT_OFF_HOVER = (205, 216, 226)
TOGGLE_TRACK_OFF = (54, 62, 71)
TOGGLE_TRACK_OFF_HOVER = (76, 86, 96)
TOGGLE_KNOB_OFF = (152, 164, 175)

TOGGLE_TRACK_WIDTH = 32
TOGGLE_TRACK_HEIGHT = 16
TOGGLE_KNOB_INSET = 2     # gap between knob and track on the side it rests
TOGGLE_TEXT_MARGIN = 9    # inset of the label from the left edge
TOGGLE_TRACK_GAP = 7      # minimum gap between label and track

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
    "battle_focus": (
        BG_NORMAL_BATTLE_FOCUS, BG_HOVER_BATTLE_FOCUS, BG_ACTIVE_BATTLE_FOCUS,
        BORDER_NORMAL_BATTLE_FOCUS, BORDER_HOVER_BATTLE_FOCUS, BORDER_ACTIVE_BATTLE_FOCUS,
        TEXT_NORMAL_BATTLE_FOCUS, TEXT_HOVER_BATTLE_FOCUS,
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


def _toggle_layout(width, label, font):
    """Shared wrap math for draw_toggle() and toggle_height(), so the height
    a caller reserves and the height actually drawn cannot disagree."""
    track_width = min(TOGGLE_TRACK_WIDTH, max(0, width - 2 * TOGGLE_TEXT_MARGIN))
    text_width = max(1, width - 2 * TOGGLE_TEXT_MARGIN - track_width - TOGGLE_TRACK_GAP)
    lines = wrap_text(font, label.upper(), text_width) or [label.upper()]
    return lines, font.get_height() + 2, track_width


def toggle_height(width, label, font, min_height=0):
    """How tall draw_toggle() would draw this label at this width - so a
    caller with several toggles can give them all one shared height instead
    of letting a label that happens to wrap make its own row taller than its
    neighbours. Measured: at the 200px-wide left panel "Move Whole Squad"
    wraps to two lines and "Place as Block" does not, so without this the
    toolbar renders rows of 38px and 32px next to each other."""
    lines, line_height, _ = _toggle_layout(width, label, font)
    return max(min_height, len(lines) * line_height + 10, TOGGLE_TRACK_HEIGHT + 10)


def draw_toggle(surface, rect, label, on, font, hovered=False, pressed=False):
    """One on/off toggle: the same chamfered, glow-bordered body as
    draw_button(), but carrying its state visually instead of spelling it
    out in the label. Returns the rect actually drawn (same x/y/width,
    grown in height if the label wraps), exactly like draw_button() - the
    caller uses THAT for the click hit-test and for stacking.

    The label passed in must NOT contain "On"/"Off" - that was the whole
    complaint ("anstatt des textes On/Off soll es einen farblichen
    unterschied geben"). Measured before the change: with all three
    toolbar toggles flipped, the rendered rows were pixel-identical apart
    from those two words, so the state was legible only by reading.

    State is shown three ways at once, on purpose:
      * the sliding KNOB sits on the right of its track when on, left when
        off - the one cue that survives greyscale and colour-blindness,
        and the "richtiger optischer toggle" that was asked for;
      * the TRACK is green when on, grey when off;
      * the body's border/text follow the same green/grey, so the row
        reads as on/off from across the panel without finding the switch.

    `pressed` deliberately does NOT get its own third palette the way
    draw_button() does: a toggle flips on mouse-up, so a "pressed" look
    that previewed the OTHER colour would show a state the control is not
    in yet. It shares the hover look instead."""
    lines, line_height, track_width = _toggle_layout(rect.width, label, font)
    height = max(rect.height, len(lines) * line_height + 10, TOGGLE_TRACK_HEIGHT + 10)
    toggle_rect = pygame.Rect(rect.x, rect.y, rect.width, height)

    lit = hovered or pressed
    if on:
        bg = TOGGLE_BG_ON_HOVER if lit else TOGGLE_BG_ON
        border = TOGGLE_BORDER_ON_HOVER if lit else TOGGLE_BORDER_ON
        text_color = TOGGLE_TEXT_ON_HOVER if lit else TOGGLE_TEXT_ON
        track_color = TOGGLE_TRACK_ON_HOVER if lit else TOGGLE_TRACK_ON
        knob_color = TOGGLE_KNOB_ON
    else:
        bg = TOGGLE_BG_OFF_HOVER if lit else TOGGLE_BG_OFF
        border = TOGGLE_BORDER_OFF_HOVER if lit else TOGGLE_BORDER_OFF
        text_color = TOGGLE_TEXT_OFF_HOVER if lit else TOGGLE_TEXT_OFF
        track_color = TOGGLE_TRACK_OFF_HOVER if lit else TOGGLE_TRACK_OFF
        knob_color = TOGGLE_KNOB_OFF

    points = chamfer_points(toggle_rect, CHAMFER_SIZE)
    draw_glow(
        surface, toggle_rect, border, chamfer=CHAMFER_SIZE,
        width=7 if lit else 4, alpha=90 if lit else 45,
    )
    pygame.draw.polygon(surface, bg, points)
    pygame.draw.polygon(surface, border, points, width=2)

    text_y = toggle_rect.y + (toggle_rect.height - len(lines) * line_height) // 2
    for line in lines:
        line_surf = font.render(line, True, text_color)
        surface.blit(line_surf, line_surf.get_rect(x=toggle_rect.x + TOGGLE_TEXT_MARGIN, y=text_y))
        text_y += line_height

    track_rect = pygame.Rect(
        toggle_rect.right - TOGGLE_TEXT_MARGIN - track_width,
        toggle_rect.centery - TOGGLE_TRACK_HEIGHT // 2,
        track_width, TOGGLE_TRACK_HEIGHT,
    )
    radius = TOGGLE_TRACK_HEIGHT // 2
    pygame.draw.rect(surface, track_color, track_rect, border_radius=radius)
    pygame.draw.rect(surface, border, track_rect, width=1, border_radius=radius)

    knob_radius = max(1, radius - TOGGLE_KNOB_INSET)
    knob_x = (
        track_rect.right - TOGGLE_KNOB_INSET - knob_radius if on
        else track_rect.x + TOGGLE_KNOB_INSET + knob_radius
    )
    pygame.draw.circle(surface, knob_color, (knob_x, track_rect.centery), knob_radius)

    return toggle_rect


def draw_header_bar(surface, rect, text, font, text_color=None, bg_color=None,
                    text_margin=HEADER_TEXT_MARGIN, center=False):
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


def draw_panel_header(surface, rect, text, font, text_color=None, bg_color=None, wrap=False):
    """A panel's main title: a full-width background bar right under the
    panel's own top border (reference image: "Actions" sits inside its own
    bar), not just bare text. Fixed height (not measured off the rendered
    text) so this drops into ActionPanel's existing "title, then content
    starts at a hardcoded rect.y+N" layout everywhere without having to
    re-tune every one of those N's - the bar always ends well above the
    smallest of them (rect.y+40). Returns the y position just below it,
    for callers that stack content off the return value instead.

    `wrap` grows the bar DOWNWARDS instead of letting a long title run off
    the panel, and is off by default precisely because of the paragraph
    above: only a caller that stacks off the return value can afford a bar
    whose height depends on its text. The one that does is the board-pick
    screen, whose title is a PRINTED rule name - measured across the five
    factions, 9 of 147 printed ability titles are wider than this bar
    (widest: "Infused with the Blessings of Nurgle" at 268px against 192px
    of title room), so for that caller a single line is not an option.

    A one-line title takes the unchanged path, so every other screen in the
    game draws the same pixels it drew before."""
    width = rect.width - 2 * HEADER_MARGIN
    lines = wrap_text(font, text, width - 2 * HEADER_TEXT_MARGIN) if wrap else []
    if len(lines) <= 1:
        bar_rect = pygame.Rect(rect.x + HEADER_MARGIN, rect.y + HEADER_MARGIN, width, HEADER_BAR_HEIGHT)
        draw_header_bar(surface, bar_rect, lines[0] if lines else text, font,
                        text_color=text_color, bg_color=bg_color)
        return bar_rect.bottom + 8

    # The single-line bar's own vertical padding, kept rather than recomputed,
    # so a two-line title sits in the same amount of air as a one-line one.
    padding = max(0, (HEADER_BAR_HEIGHT - font.get_height()) // 2)
    line_height = font.get_height() + 2
    bar_rect = pygame.Rect(rect.x + HEADER_MARGIN, rect.y + HEADER_MARGIN, width,
                           2 * padding + len(lines) * line_height - 2)
    pygame.draw.rect(surface, bg_color if bg_color is not None else HEADER_BG_COLOR, bar_rect)
    y = bar_rect.y + padding
    for line in lines:
        line_surf = font.render(line, True,
                                text_color if text_color is not None else config.PANEL_HEADER_COLOR)
        surface.blit(line_surf, (bar_rect.x + HEADER_TEXT_MARGIN, y))
        y += line_height
    return bar_rect.bottom + 8


def draw_box(surface, rect, chamfer=BOX_CHAMFER, bg_color=None, border_color=None, border_width=1):
    """Chamfered panel box (message boxes, log entries, the big ACTION
    REQUIRED callout) - same dark-navy-fill/cyan-border/cut-corner
    language as the buttons and header bar, instead of each box picking
    its own flat rounded-rect style."""
    points = chamfer_points(rect, chamfer)
    pygame.draw.polygon(surface, bg_color if bg_color is not None else BOX_BG_COLOR, points)
    pygame.draw.polygon(surface, border_color if border_color is not None else BOX_BORDER_COLOR, points, width=border_width)


SCROLLBAR_COLOR = (120, 120, 120)
SCROLLBAR_TRACK_COLOR = (55, 55, 55)
SCROLLBAR_WIDTH = 5
SCROLLBAR_MIN_THUMB = 18


def draw_scrollbar(surface, track_rect, scroll, scroll_max, visible_fraction):
    """A track-and-thumb bar for a panel whose content is taller than it is.

    Extracted at the SECOND consumer, this repo's standing rule: the hover
    datacard grew one, and the army-rules overlay needs the same thing. The
    thumb's LENGTH says how much more there is and its POSITION says where you
    are - two facts a scroll offset alone does not show, which is why a long
    body of text needs it and a short one does not.

    `visible_fraction` is how much of the content fits (0..1); `scroll_max` is
    0 when there is nothing to scroll, in which case this draws nothing rather
    than a full-length thumb that suggests otherwise."""
    if scroll_max <= 0 or track_rect.height <= 0:
        return None
    pygame.draw.rect(surface, SCROLLBAR_TRACK_COLOR, track_rect, border_radius=2)
    thumb_height = max(SCROLLBAR_MIN_THUMB,
                       int(track_rect.height * max(0.0, min(1.0, visible_fraction))))
    travel = track_rect.height - thumb_height
    progress = max(0.0, min(1.0, scroll / float(scroll_max)))
    thumb = pygame.Rect(track_rect.x, track_rect.y + int(travel * progress),
                        track_rect.width, thumb_height)
    pygame.draw.rect(surface, SCROLLBAR_COLOR, thumb, border_radius=2)
    return thumb
