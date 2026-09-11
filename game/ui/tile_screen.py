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
# Moved to text_utils at its second consumer (the mission strip's collapsed
# bar needs the same one-line cut); re-exported so every caller here and in
# test_menu_presentation.py keeps resolving ts.ellipsised.
from game.ui.text_utils import ellipsised  # noqa: F401

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

# The PICKED tile. Deliberately a different HUE from the hover blue, not a
# brighter version of it: hover says "the cursor is here" and moves with the
# mouse, selection says "this is your answer" and stays after the cursor has
# gone. Two shades of one colour would read as one state with two intensities,
# which is exactly the confusion this screen is being changed to remove - user:
# "erst auswaehlen, dann wird die entsprechende kachel gehighlightet und dann
# auf den auswahl button unten druecken". Green also matches the confirm button
# the selection enables, so the tile and the button read as one action.
TILE_BORDER_SELECTED_COLOR = (120, 235, 150)
TILE_BG_SELECTED_COLOR = (14, 40, 30)
# A picked tile with the cursor on it. Still green - it is still the answer -
# but lighter, so a selected tile does not go dead to the mouse. Without this
# the only tile on screen that gives no hover feedback would be the one you
# most likely want to click again.
TILE_BORDER_SELECTED_HOVER_COLOR = (185, 255, 205)
SELECTED_BADGE_COLOR = (170, 255, 195)

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
# HEADER_HEIGHT is UNCHANGED, and that is a measurement rather than an
# oversight: its bar is HEADER_HEIGHT - 18 tall and still clears the bigger
# title plus the hint under it, and every pixel taken from it comes straight
# out of tile_area()'s band. Its own A/B probe is what said so - restoring the
# old value changed nothing, which is the definition of a change not worth
# making.
#
# FOOTER_HEIGHT did move, and what it buys is the CLEARANCE under the buttons.
# The strip's controls got taller twice over - PAGER_BUTTON_HEIGHT below, and
# draw_button() growing a button to fit a wrapped label - and the old 58 left
# the longest real confirm label 4 px from the bottom of the window against the
# 14 px the footer used to have. FOOTER_CLEARANCE_PX is that margin, pinned in
# test_menu_presentation.py so the next font bump cannot quietly eat it.
HEADER_HEIGHT = 104
FOOTER_HEIGHT = 70
FOOTER_CLEARANCE_PX = 12
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

PAGER_BUTTON_WIDTH = 150
PAGER_BUTTON_HEIGHT = 46
# Wide enough that the longest real map/army name wraps to two lines rather
# than three: at three the button grows past the bottom of the window at 720p.
CONFIRM_BUTTON_WIDTH = 300
BACK_BUTTON_WIDTH = 170
FOOTER_HINT_GAP = 16


# How much bigger than the in-battle HUD each role is. User: "Die Font im Main
# Menu und Auswahl screen darf viel groesser sein" - and these screens can
# afford it, which the HUD cannot: they own the whole window, they are read
# from further back than a 220px side panel, and they carry a handful of words
# each rather than forty buttons.
#
# Every offset moved UP, none of them relative to each other: the roles were
# already in the right order (title > name > subtitle > label > body > small)
# and the ask was about size, not hierarchy. Measured at 1280x720, the
# narrowest window this game is run at - the pieces whose boxes are fixed
# rather than measured off the fonts (the footer's buttons, the header bar)
# moved with them, see the constants below.
TITLE_FONT_DELTA = 26
SUBTITLE_FONT_DELTA = 8
NAME_FONT_DELTA = 18
LABEL_FONT_DELTA = 6
BODY_FONT_DELTA = 5
SMALL_FONT_DELTA = 3


def make_fonts():
    """The one font set both screens use, so their headings, labels and body
    text are the same size on both."""
    return {
        "title": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + TITLE_FONT_DELTA, bold=True),
        "subtitle": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + SUBTITLE_FONT_DELTA),
        "name": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + NAME_FONT_DELTA, bold=True),
        "label": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + LABEL_FONT_DELTA, bold=True),
        "body": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + BODY_FONT_DELTA),
        "small": pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + SMALL_FONT_DELTA),
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


def rows_that_fit(area_height, tile_height):
    """How many rows of `tile_height` tiles this band holds.

    The vertical twin of tiles_that_fit(), and the reason a page can hold more
    than one row at all. No cap: MAX_TILES_PER_PAGE exists because "past four,
    an item is easier to compare by paging than by scanning ACROSS" - that is
    an argument about a row's width, and it says nothing about stacking a
    second row of the same tiles underneath the first."""
    if tile_height <= 0:
        return 1
    return max(1, int((area_height + TILE_GAP) // (tile_height + TILE_GAP)))


def tile_rects(area, per_row, count, height):
    """`count` tile rectangles laid out across `area`, each `height` tall,
    WRAPPING to a new row after every `per_row`.

    Every tile keeps the width one of `per_row` gets, even on a row that is not
    full - a leftover row must not stretch two tiles across the screen, because
    paging is meant to move the eye, not to redraw at a new scale. The last row
    of a grid is left-aligned for the same reason: the columns have to line up
    with the rows above them.

    THE WRAPPING IS NEW AND CHANGES NOTHING FOR THE SINGLE-ROW CALLERS. They
    pass `count = len(page_items)`, which is at most `tiles_per_page`, which
    for them is the column count - so `i // per_row` is 0 for every tile and
    the arithmetic is the one that was here before, term for term."""
    width = (area.width - TILE_GAP * (per_row - 1)) // max(1, per_row)
    per_row = max(1, per_row)
    return [pygame.Rect(area.x + (i % per_row) * (width + TILE_GAP),
                        area.y + (i // per_row) * (height + TILE_GAP),
                        width, height)
            for i in range(count)]


def grid_block(area, columns, count, height):
    """Where a `count`-item grid of `height`-tall tiles sits inside `area`,
    CENTRED vertically.

    Centred rather than pinned to the top because a short grid in a tall band
    otherwise reads as one row nailed to the ceiling with a void under it -
    which is the report this exists to answer (User: "viel verschwendeter
    platz"). The tiles keep the height their content needs: stretching them to
    fill would contradict the picking screens' own standing decision that "a
    card that is mostly empty space reads as something failing to load", and
    the empty space is real either way - balanced above and below, it reads as
    margin instead of as a failure.

    Returns a rect to hand to tile_rects()."""
    rows = -(-count // max(1, columns))
    block = rows * height + TILE_GAP * (rows - 1)
    top = area.y + max(0, (area.height - block) // 2)
    return pygame.Rect(area.x, top, area.width, block)


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

    def fit_grid(self, area_width, area_height, tile_height):
        """Set tiles_per_page from a GRID that fills the band, and return the
        COLUMN count (which is what tile_rects() needs).

        Columns come from the same rule fit_page() uses, so a grid is as wide
        as a row would have been and no wider - MAX_TILES_PER_PAGE's argument
        ("past four, an item is easier to compare by paging than by scanning
        across") is about scanning sideways and still holds. Rows are however
        many fit underneath, uncapped: a second row of the same tiles is not
        harder to scan, it is the thing that was missing.

        WHAT THIS BUYS, measured on the faction step at 1920x1080: a band of
        1852x918 held four 104px tiles and paged five factions onto two pages,
        using 11% of the band. The same band holds 4 x 7 = 28 of them, so the
        pager does not appear until a 29th faction exists.

        The column clamp to len(items) is fit_page()'s, for its reason: three
        items on a screen that would hold four must not leave a quarter of the
        width empty and make all three a quarter too small. It is applied to
        COLUMNS and not to the page total, or a five-item grid would come out
        five columns wide."""
        columns = max(1, min(tiles_that_fit(area_width), len(self.items)))
        rows = rows_that_fit(area_height, tile_height)
        self.tiles_per_page = max(1, min(columns * rows, len(self.items)))
        self.page = min(self.page, self.page_count - 1)
        return columns

    def turn_page(self, delta):
        """Step through the pages, wrapping.

        Wrapping rather than clamping so neither arrow is ever a dead button -
        with two pages "Next" and "Prev" reach the same place anyway, and a
        button that silently does nothing is the worse of the two."""
        if self.page_count <= 1:
            return False
        self.page = (self.page + delta) % self.page_count
        return True


def header_bar(screen_rect):
    """The filled bar across the top - where the heading and hint sit.

    Its own function because a screen may want to put a control INSIDE it
    (the map picker's biome buttons) and hit-test that control in layout(),
    before anything is drawn. Computing the same rectangle in two places is
    how a control ends up a few pixels off the bar it looks like it is in."""
    return pygame.Rect(screen_rect.x, screen_rect.y, screen_rect.width, HEADER_HEIGHT - 18)


def draw_header(surface, screen_rect, fonts, title, hint, accent, notes=(),
                hint_max_width=None):
    """The title bar: heading, one line of instruction, and any already-made
    choices along the right so a later step is taken with the earlier ones in
    view rather than from memory.

    `hint_max_width` is how much room the hint really has, for a screen that
    has put a control of its own in this bar (the map picker's biome row). The
    hint is NOT a fixed string - it names the current selection - so a bar
    shared with a control cannot be laid out by measuring the longest heading
    once and hoping. Measured: the Crucible hint runs 608px even at the old,
    smaller subtitle size, against a biome row that starts 616px in at 1280
    and moved left again when a fourth biome arrived. Cut to fit instead."""
    bar = header_bar(screen_rect)
    pygame.draw.rect(surface, HEADER_BG_COLOR, bar)
    pygame.draw.line(surface, accent, (bar.x, bar.bottom - 1), (bar.right, bar.bottom - 1), 2)
    surface.blit(fonts["title"].render(title, True, TITLE_COLOR),
                 (screen_rect.x + MARGIN, bar.y + 12))
    surface.blit(
        fonts["subtitle"].render(
            ellipsised(fonts["subtitle"], hint, hint_max_width), True, DIM_TEXT_COLOR),
        (screen_rect.x + MARGIN, bar.y + 16 + fonts["title"].get_height()))

    x = screen_rect.right - MARGIN
    for text, color in reversed(list(notes)):
        surf = fonts["label"].render(text, True, color)
        x -= surf.get_width()
        surface.blit(surf, (x, bar.y + 14))
        x -= 24
    return bar


class FooterButtons:
    """The footer's clickable rects, by NAME.

    A record rather than the tuple this used to return, because the tuple was
    already being read positionally AND sliced (`draw_footer(...)[1:]` in the
    map picker) - so adding a fourth button would have silently handed one
    caller the wrong rectangles. That is CLAUDE.md's error class 22, the one
    the action panel carries a scar from. `None` means the control is not on
    screen this frame."""

    __slots__ = ("back", "prev", "next", "confirm")

    def __init__(self, back=None, prev=None, next=None, confirm=None):
        self.back = back
        self.prev = prev
        self.next = next
        self.confirm = confirm


def draw_footer(surface, screen_rect, fonts, page, page_count, back_label=None,
                confirm_label=None):
    """The bottom strip: an optional Back button on the left, the pager in the
    middle, the CONFIRM button on the right, and the key hints beside it.

    Returns a FooterButtons; any field is None when that control is not on
    screen. Like the pager - which only appears when there is somewhere to go -
    the confirm button is drawn only once something is SELECTED. Drawing a
    dead, greyed-out button instead would be a second thing to explain, and
    this module already has the convention: no chrome for a control that
    cannot do anything.

    `confirm_label` names the pick ("CONFIRM: ORKS") rather than saying just
    "Confirm". A selection survives paging, so the button can be pressed while
    a different page is on screen - the label is what makes that unambiguous
    instead of alarming."""
    mouse = pygame.mouse.get_pos()
    top = screen_rect.bottom - FOOTER_HEIGHT + 6
    buttons = FooterButtons()

    if back_label:
        rect = pygame.Rect(screen_rect.x + MARGIN, top, BACK_BUTTON_WIDTH, PAGER_BUTTON_HEIGHT)
        buttons.back = button_style.draw_button(
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
        buttons.prev = button_style.draw_button(
            surface, prev, "< Prev", fonts["label"], hovered=prev.collidepoint(mouse))
        buttons.next = button_style.draw_button(
            surface, nxt, "Next >", fonts["label"], hovered=nxt.collidepoint(mouse))

    hint_right = screen_rect.right - MARGIN
    if confirm_label:
        rect = pygame.Rect(screen_rect.right - MARGIN - CONFIRM_BUTTON_WIDTH, top,
                           CONFIRM_BUTTON_WIDTH, PAGER_BUTTON_HEIGHT)
        buttons.confirm = button_style.draw_button(
            surface, rect, confirm_label, fonts["label"],
            hovered=rect.collidepoint(mouse), accent="confirm",
        )
        hint_right = rect.left - FOOTER_HINT_GAP

    # Shortened while the confirm button is up. Measured at 1280 - the
    # narrowest window this game is run at - the long form would otherwise
    # reach back into the pager's Next button.
    if confirm_label:
        note = "ESC quits"
    else:
        note = "arrow keys or wheel to page  |  ESC quits" if page_count > 1 else "ESC quits"
    surf = fonts["small"].render(note, True, DIM_TEXT_COLOR)
    surface.blit(surf, (hint_right - surf.get_width(), top + 10))
    return buttons


def draw_tile_frame(surface, rect, hovered=False, selected=False):
    """The chamfered card every tile sits in: glowing while hovered, and in a
    different colour entirely once PICKED.

    Selection wins over hover on the border, because the answer matters more
    than where the cursor is - but a selected tile still brightens under the
    cursor, so it does not go dead to the mouse."""
    if selected:
        border = (TILE_BORDER_SELECTED_HOVER_COLOR if hovered
                  else TILE_BORDER_SELECTED_COLOR)
        bg = TILE_BG_SELECTED_COLOR
    else:
        border = TILE_BORDER_HOVER_COLOR if hovered else TILE_BORDER_COLOR
        bg = TILE_BG_HOVER_COLOR if hovered else TILE_BG_COLOR
    if hovered or selected:
        button_style.draw_glow(surface, rect, border, chamfer=TILE_CHAMFER,
                               width=10 if selected else 8,
                               alpha=120 if selected else 90)
    button_style.draw_box(
        surface, rect, chamfer=TILE_CHAMFER, bg_color=bg,
        border_color=border, border_width=3 if selected else 2,
    )
    return border


def draw_selected_badge(surface, rect, fonts):
    """A word in the picked tile's top-right corner.

    Colour alone is not enough on its own: this screen is the one place a
    player must be certain WHICH tile their answer is, and a green border is a
    weaker signal than a green border plus the word SELECTED. It also survives
    a colour-blind reader, who otherwise has only the border WIDTH to go on."""
    surf = fonts["label"].render("SELECTED", True, SELECTED_BADGE_COLOR)
    pos = surf.get_rect(topright=(rect.right - TILE_PAD, rect.y + 8))
    surface.blit(surf, pos)
    return pos


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
