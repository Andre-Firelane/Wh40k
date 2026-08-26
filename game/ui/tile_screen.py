"""The shared skeleton behind the pre-battle picking screens.

Two of them exist now - pick a battlefield (game/ui/map_select.py), then pick
each player's army list (game/ui/army_select.py) - and they are the same screen
with different things on the tiles: a full-window header, a row of large
clickable tiles that pages when they will not all fit, a footer with the pager
and an optional Back button, and a loop of their own.

Extracted at the SECOND consumer, which is this repo's standing rule (CLAUDE.md
error class 10) - the map screen would otherwise have been ~130 lines copied
out of the army screen, and the first thing two copies of a layout do is drift
into two different-looking screens.

WHAT IS HERE and what is not. Here: the paging arithmetic, the tile rectangles,
the header and footer chrome, and the event/draw/quit loop. Not here: what a
tile CONTAINS, how tall it needs to be, or what clicking one means - those are
the whole difference between the two screens, and a base class that tried to
own them would just be an abstract method per difference.

So this is functions plus one small mixin holding the paging state, and each
screen keeps its own class. A screen supplies:

    self.items          the things tiles show, in order
    self.title / hint / accent_color()
    self.done / self.cancelled
    tile_height(...)    how tall this page's tiles need to be
    draw_tile(...)      what goes in one
    on_tile_click(item) what picking it means

ITS OWN LOOP, deliberately, for both screens: main()'s event chain is a long
if/elif over controller state and has swallowed a keypress five times over
(CLAUDE.md error class 15). These screens answer one question each, before any
of those controllers exist, so they take their events themselves.
"""

import math

import pygame

from game import config
from game.ui import button_style

BG_COLOR = (12, 16, 24)
TITLE_COLOR = (255, 215, 0)
TEXT_COLOR = (200, 226, 245)
DIM_TEXT_COLOR = (135, 160, 180)
HEADER_BG_COLOR = (16, 26, 40)
TILE_BG_COLOR = (10, 18, 28)
TILE_BG_HOVER_COLOR = (16, 34, 52)
TILE_BORDER_COLOR = (55, 120, 165)
TILE_BORDER_HOVER_COLOR = (120, 215, 255)
RULE_LINE_COLOR = (40, 78, 108)

# Same fixed per-player identity colors the mission cards and the board's
# objective markers use - a step reads as "this is Player 1's pick" from the
# accent alone. Duplicated rather than imported, matching this codebase's usual
# per-module small-constant convention.
PLAYER_ACCENT_COLORS = {
    "Player 1": (70, 140, 230),
    "Player 2": (220, 60, 60),
}
DEFAULT_ACCENT_COLOR = (90, 160, 205)

MARGIN = 34
HEADER_HEIGHT = 104
FOOTER_HEIGHT = 58
TILE_GAP = 22
TILE_PAD = 16
TILE_CHAMFER = 12

# How many tiles one page shows. NOT "however many items there are": the tiles
# are the point (user: "in grossen Kacheln auswaehlen"), and dividing one
# screen between six of them makes six small ones. So a page holds as many
# tiles as fit at MIN_TILE_WIDTH and the rest go to the next page.
#
# Derived from the window rather than fixed, because both halves of that
# sentence are true at different resolutions: 1920 px fits four 446 px tiles
# comfortably, 1366 px fits three at 418, and a fixed three would waste the
# wide screen while a fixed four would cramp the narrow one. Measured at both.
#
# The cap exists so a very wide screen does not line up eight tiles and call
# them large - past four, an item is easier to compare by paging than by
# scanning across.
MIN_TILE_WIDTH = 400
MAX_TILES_PER_PAGE = 4

PAGER_BUTTON_WIDTH = 130
PAGER_BUTTON_HEIGHT = 38


def make_fonts():
    """The one font set both screens use, so their headings, labels and body
    text are the same size on both."""
    return {
        "title": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 14, bold=True),
        "subtitle": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 2),
        "name": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 8, bold=True),
        "label": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1, bold=True),
        "body": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2),
        "small": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4),
    }


def tile_area(screen_rect):
    """The band tiles live in: the whole window minus header, footer and
    margins."""
    return pygame.Rect(
        screen_rect.x + MARGIN,
        screen_rect.y + HEADER_HEIGHT,
        screen_rect.width - 2 * MARGIN,
        screen_rect.height - HEADER_HEIGHT - FOOTER_HEIGHT,
    )


def tiles_that_fit(area_width):
    """How many tiles this width holds at MIN_TILE_WIDTH, capped."""
    fits = (area_width + TILE_GAP) // (MIN_TILE_WIDTH + TILE_GAP)
    return max(1, min(MAX_TILES_PER_PAGE, int(fits)))


def tile_rects(area, per_page, count, height):
    """`count` tile rectangles across `area`, each `height` tall.

    Every tile keeps the width one of `per_page` gets, even on a page that is
    not full - a leftover page must not stretch two tiles across the screen,
    because paging is meant to move the eye, not to redraw at a new scale."""
    width = (area.width - TILE_GAP * (per_page - 1)) // max(1, per_page)
    return [pygame.Rect(area.x + i * (width + TILE_GAP), area.y, width, height)
            for i in range(count)]


class Paged:
    """The paging half of a picking screen, as a mixin.

    State rather than functions because `page` outlives a single layout and
    `tiles_per_page` is discovered during one: page_count and page_lists are
    asked outside a layout too (by the footer, and by anything driving the
    screen before it has drawn), so the last answer has to be kept."""

    def init_paging(self, items):
        self.items = list(items)
        self.page = 0
        self.tiles_per_page = MAX_TILES_PER_PAGE  # refined by layout(), see fit_page()

    @property
    def page_count(self):
        return max(1, math.ceil(len(self.items) / self.tiles_per_page))

    @property
    def page_items(self):
        start = self.page * self.tiles_per_page
        return self.items[start:start + self.tiles_per_page]

    def fit_page(self, area_width):
        """Set tiles_per_page from the window and clamp the page into range.

        Never more slots than there are items: with three maps on a screen that
        would hold four tiles, a fixed four would leave a quarter of the width
        empty and make all three tiles a quarter too small. Counted over ALL
        items rather than the current page, so a partial LAST page still draws
        its tiles at the same width as a full one.

        The clamp matters: a page index from a wider window would index past
        the end of a narrower one and the screen would show nothing."""
        self.tiles_per_page = max(1, min(tiles_that_fit(area_width), len(self.items)))
        self.page = min(self.page, self.page_count - 1)
        return self.tiles_per_page

    def turn_page(self, delta):
        """Step through the pages, wrapping.

        Wrapping rather than clamping so neither arrow is ever a dead button -
        with two pages "Next" and "Prev" reach the same place anyway, and a
        button that silently does nothing is the worse of the two."""
        if self.page_count <= 1:
            return False
        self.page = (self.page + delta) % self.page_count
        return True


def draw_header(surface, screen_rect, fonts, title, hint, accent, notes=()):
    """The title bar: heading, one line of instruction, and any already-made
    choices along the right so a later step is taken with the earlier ones in
    view rather than from memory."""
    bar = pygame.Rect(screen_rect.x, screen_rect.y, screen_rect.width, HEADER_HEIGHT - 18)
    pygame.draw.rect(surface, HEADER_BG_COLOR, bar)
    pygame.draw.line(surface, accent, (bar.x, bar.bottom - 1), (bar.right, bar.bottom - 1), 2)
    surface.blit(fonts["title"].render(title, True, TITLE_COLOR),
                 (screen_rect.x + MARGIN, bar.y + 12))
    surface.blit(fonts["subtitle"].render(hint, True, DIM_TEXT_COLOR),
                 (screen_rect.x + MARGIN, bar.y + 16 + fonts["title"].get_height()))

    x = screen_rect.right - MARGIN
    for text, color in reversed(list(notes)):
        surf = fonts["label"].render(text, True, color)
        x -= surf.get_width()
        surface.blit(surf, (x, bar.y + 14))
        x -= 24
    return bar


def draw_footer(surface, screen_rect, fonts, page, page_count, back_label=None):
    """The bottom strip: an optional Back button on the left, the pager in the
    middle, and the key hints on the right.

    Returns (back rect, prev rect, next rect), any of them None when that
    control is not on screen - the pager only appears when there is somewhere
    to go, so a build whose items all fit on one page shows no chrome at all.
    """
    mouse = pygame.mouse.get_pos()
    top = screen_rect.bottom - FOOTER_HEIGHT + 6
    back_rect = prev_rect = next_rect = None

    if back_label:
        rect = pygame.Rect(screen_rect.x + MARGIN, top, 150, PAGER_BUTTON_HEIGHT)
        back_rect = button_style.draw_button(
            surface, rect, back_label, fonts["label"],
            hovered=rect.collidepoint(mouse), accent="danger",
        )

    if page_count > 1:
        label_surf = fonts["label"].render(f"PAGE {page + 1} / {page_count}", True, TEXT_COLOR)
        label_rect = label_surf.get_rect(
            center=(screen_rect.centerx, top + PAGER_BUTTON_HEIGHT // 2))
        surface.blit(label_surf, label_rect)
        prev = pygame.Rect(label_rect.left - 18 - PAGER_BUTTON_WIDTH, top,
                           PAGER_BUTTON_WIDTH, PAGER_BUTTON_HEIGHT)
        nxt = pygame.Rect(label_rect.right + 18, top, PAGER_BUTTON_WIDTH, PAGER_BUTTON_HEIGHT)
        prev_rect = button_style.draw_button(
            surface, prev, "< Prev", fonts["label"], hovered=prev.collidepoint(mouse))
        next_rect = button_style.draw_button(
            surface, nxt, "Next >", fonts["label"], hovered=nxt.collidepoint(mouse))

    note = "arrow keys or wheel to page  |  ESC quits" if page_count > 1 else "ESC quits"
    surf = fonts["small"].render(note, True, DIM_TEXT_COLOR)
    surface.blit(surf, (screen_rect.right - MARGIN - surf.get_width(), top + 10))
    return back_rect, prev_rect, next_rect


def draw_tile_frame(surface, rect, hovered=False):
    """The chamfered card every tile sits in, glowing while hovered."""
    border = TILE_BORDER_HOVER_COLOR if hovered else TILE_BORDER_COLOR
    if hovered:
        button_style.draw_glow(surface, rect, border, chamfer=TILE_CHAMFER, width=8, alpha=90)
    button_style.draw_box(
        surface, rect, chamfer=TILE_CHAMFER,
        bg_color=TILE_BG_HOVER_COLOR if hovered else TILE_BG_COLOR,
        border_color=border, border_width=2,
    )
    return border


def run_screen(screen, picker, clock=None):
    """Pump events until `picker` says it is done.

    The `done` check sits BEFORE the draw, not after: the last click finishes
    the screen, and one more frame of it would flash a step that no longer
    exists."""
    clock = clock or pygame.time.Clock()
    screen_rect = screen.get_rect()
    while not picker.done:
        for event in pygame.event.get():
            picker.handle_event(event, screen_rect)
            if picker.done:
                break
        if picker.done:
            break
        picker.draw(screen, pygame.mouse.get_pos())
        pygame.display.flip()
        clock.tick(config.FPS)
    return not picker.cancelled
