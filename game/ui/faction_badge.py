"""One faction badge: the artwork in a chamfered tile, or a monogram when the
faction has no logo file.

29th extraction, at the second consumer as the convention requires. It lived in
game/ui/game_status_panel.py while that panel was the only thing that drew a
badge; the turn-start banner is the second, and "what does a faction tile look
like" is one question with one answer. The panel re-exports every constant and
delegates its own method here, so its pixel tests are unchanged BY
CONSTRUCTION rather than by being re-run and hoped over.

THE TILE RECT IS THE CALLER'S, and that is the whole reason this takes one
instead of a size. The panel's LOGO_BOX (58 px) is sized for a 200 px column;
a screen-centre banner has no such constraint and picks its own. Only the FONT
is searched to fit, so a bigger tile costs nothing here.

WHAT "active" MEANS is also the caller's: the panel lights up
turn_tracker.active_player (the transient "who is the game waiting on"), while
the banner lights up the player it is naming. Both are "this tile is the
subject", which is why one flag serves both.
"""

import pygame

from game import config
from game.ui import button_style

LOGO_PADDING = 4         # px between the tile's frame and the artwork inside it
ACTIVE_BORDER_WIDTH = 3  # the active tile gets a thicker frame
#: Dim gold ring just outside that frame, so it reads as a glow rather than as
#: a second hard outline.
ACTIVE_GLOW_COLOR = (120, 100, 20)
MONOGRAM_LENGTH = 2      # chars in a placeholder tile's text, see monogram()
#: Dimmer than PANEL_TEXT_COLOR: a placeholder should not out-shout the real
#: art next to it.
MONOGRAM_COLOR = (135, 175, 205)
#: Font sizes tried largest-first when fitting a monogram into its tile. Only
#: the SIZE is searched - the box comes from the caller's rect, so this list
#: does not have to be maintained alongside any one of them.
MONOGRAM_FONT_SIZES = (44, 40, 36, 32, 28, 24, 20, 16, 12)

_FONTS = {}   # (text, box px) -> font, see font_for()


def monogram(keyword):
    """Short text for the tile of a faction that has no logo file.

    Two characters for every faction, so two tiles stay visually symmetrical
    whichever one is missing art: the initials of a multi-word keyword ("DEATH
    GUARD" -> "DG", "T'AU EMPIRE" -> "TE"), and the first two letters of a
    single-word one ("AELDARI" -> "AE"). A single initial was the obvious first
    form and reads as a typo rather than as a badge.

    This is the tile's whole content, not a label - wherever a badge is drawn
    the faction is already spelled out next to it, so the tile only has to be
    identifiable, not self-explaining."""
    if not keyword:
        return ""
    words = keyword.split()
    if len(words) > 1:
        return "".join(word[0] for word in words[:MONOGRAM_LENGTH]).upper()
    return words[0][:MONOGRAM_LENGTH].upper()


def font_for(text, box_px):
    """The largest font from MONOGRAM_FONT_SIZES whose rendering of `text` fits
    inside a `box_px` square, cached.

    MEASURED rather than derived from the box height: a bold two-character
    string is wider than it is tall, so a size picked off the height alone
    would overrun the tile sideways. Cached because this runs on the draw path,
    once per placeholder tile per frame."""
    key = (text, box_px)
    if key not in _FONTS:
        chosen = None
        for size in MONOGRAM_FONT_SIZES:
            font = pygame.font.SysFont(config.FONT_NAME, size, bold=True)
            width, height = font.size(text)
            if width <= box_px and height <= box_px:
                chosen = font
                break
        _FONTS[key] = chosen or pygame.font.SysFont(
            config.FONT_NAME, MONOGRAM_FONT_SIZES[-1], bold=True)
    return _FONTS[key]


def draw(surface, tile_rect, logo_path, active, keyword=None):
    """The artwork inside a chamfered tile, framed in the panel's usual cyan -
    or in the header gold, thicker and doubled for a glow, when this tile is
    the active one. That frame is what replaced an "(Active)" line of text
    (user request), so it has to be readable at a glance rather than a subtle
    tint.

    `logo_path` of None means this faction has no badge file, and the tile is
    filled with its monogram instead. Everything else about the tile is
    identical - same frame, same size, same active highlight - because the
    missing piece is the artwork, not the badge."""
    # Imported here rather than at module level: game/sprites.py loads and
    # caches surfaces, and this module is imported by the panel long before
    # any of that is wanted.
    from game import sprites

    # Outer ring first, tile on top of it: draw_box() fills as well as
    # outlines, so drawing the larger one second would paint over the tile it
    # is supposed to sit around.
    if active:
        button_style.draw_box(
            surface, tile_rect.inflate(4, 4), chamfer=5,
            border_color=ACTIVE_GLOW_COLOR, border_width=1,
        )
    border = config.PANEL_HEADER_COLOR if active else button_style.BOX_BORDER_COLOR
    button_style.draw_box(
        surface, tile_rect, chamfer=4, border_color=border,
        border_width=ACTIVE_BORDER_WIDTH if active else 1,
    )
    inner = tile_rect.width - 2 * LOGO_PADDING
    if logo_path is not None:
        art = sprites.fitted_surface(logo_path, inner)
        surface.blit(art, art.get_rect(center=tile_rect.center))
        return
    text = monogram(keyword)
    if not text:
        return
    # The active tile's monogram goes gold with its frame. Real artwork is
    # never recoloured (it is someone's badge), so only this branch can carry
    # the highlight into the tile's inside - which is worth having, since a
    # placeholder tile has no art to catch the eye on its own.
    color = config.PANEL_HEADER_COLOR if active else MONOGRAM_COLOR
    text_surf = font_for(text, inner).render(text, True, color)
    surface.blit(text_surf, text_surf.get_rect(center=tile_rect.center))


def has_content(logo_path, keyword):
    """Whether drawing this tile would show anything at all.

    A caller that RESERVES room for a badge needs this: a hand-built squad has
    no datasheet and therefore no faction keyword, and an empty framed square
    in the middle of a banner reads as something that failed to load."""
    return logo_path is not None or bool(monogram(keyword))
