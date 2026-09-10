"""The Unit Statistics overlay - the battle's resume, one player at a time.

User: "EIn grosses Overlay, dass eineheitenstatistiken anzeigt waere cool.
Beim echten 40k macht man sich immer gedanken, wie jede einheit performt hat
als resumee." Three tables, top three each, with the unit's own sprite beside
its name:

  BEST KILLING UNITS   wounds taken off the enemy, and what that is worth in
                       points
  BEST TANKING UNITS   potential damage turned aside
  FASTEST UNITS        inches travelled

The numbers all come from game/battle_stats.py; this file only draws them.

SHAPE: game/ui/army_rules_overlay.py, which is the other big modal reader in
this game - a scrim, a centred panel, wheel/keyboard scrolling, click or ESC
to dismiss. Like that one and unlike the eight click-away notices, it owns its
own handle_event() and therefore is deliberately NOT part of main.py's
_front_notice() ordering, which is the ordering of notices with a .dismiss().

ONE PLAYER AT A TIME, switched by the two faction badges in the header (user's
choice over showing both side by side). That buys the room for a real sprite
and an un-truncated unit name; the other army is one click away rather than
half a screen away.
"""

import pygame

from game import config, sprites
from game.ui import button_style, faction_badge, stat_table, unit_thumbs
from game.ui.text_utils import wrap_text

BG_COLOR = (12, 18, 28)
BORDER_COLOR = (90, 160, 205)
SCRIM_COLOR = (0, 0, 0)
SCRIM_ALPHA = 170
TITLE_COLOR = (255, 215, 0)
SECTION_COLOR = (255, 205, 120)
HEADER_COLOR = config.PANEL_HEADER_COLOR
TEXT_COLOR = (230, 230, 230)
DIM_TEXT_COLOR = (140, 165, 185)
TABLE_LINE_COLOR = (90, 90, 90)
#: The winner's row, so first place reads as first place without counting.
LEAD_COLOR = (255, 236, 160)

#: Same fixed per-player identity colours the mission strip, the board's
#: objective markers and the rules reader use.
PLAYER_ACCENT_COLORS = {
    "Player 1": (70, 140, 230),
    "Player 2": (220, 60, 60),
}
DEFAULT_ACCENT_COLOR = (90, 160, 205)

WIDTH_FRACTION = 0.72
HEIGHT_FRACTION = 0.86
MIN_WIDTH = 560
#: Wide enough for a sprite, a full attached-unit name and three number
#: columns without the name column having to ellipsise. Measured against the
#: longest name a shipped list fields ("1 Guardian Defenders 1 + Farseer +
#: Warlock Conclave"), which wraps to two lines here rather than being cut.
MAX_TABLE_WIDTH = 720
PADDING = 22
HEADER_HEIGHT = 44
FOOTER_HEIGHT = 26

BADGE_PX = 40
BADGE_GAP = 8
#: The sprite cell in a row. Larger than unit_thumbs' own 46px default: this
#: is a resume, the art is the point, and there is one per row rather than a
#: row of them.
THUMB_PX = 52
ROW_GAP = 4
SECTION_GAP = 18
#: Room for the sprite cell plus the gap after it, before the text columns.
THUMB_COLUMN = THUMB_PX + 10
#: Width of one number column. Wide enough for the longest value any of the
#: three tables prints (a four-digit points share, or a distance like 148.5").
NUMBER_COLUMN_WIDTH = 120

SCROLL_STEP = 48
PAGE_STEP = SCROLL_STEP * 4
_KEY_SCROLL = {
    pygame.K_DOWN: SCROLL_STEP,
    pygame.K_UP: -SCROLL_STEP,
    pygame.K_PAGEDOWN: PAGE_STEP,
    pygame.K_PAGEUP: -PAGE_STEP,
    pygame.K_SPACE: PAGE_STEP,
    pygame.K_HOME: "home",
    pygame.K_END: "end",
}

BUTTON_LABEL = "STATS"
BUTTON_WIDTH = 78
#: Between the STATS button and the AI switch it sits beside.
BUTTON_GAP = 8

#: (heading, which ranking, column headers, how each row's numbers are spelled)
#: - one entry per table, in the order the user listed them.
SECTIONS = (
    ("BEST KILLING UNITS", "top_killers", ("Unit", "Wounds", "Points"),
     lambda r: (str(r.wounds_dealt), _points(r.points_dealt))),
    ("BEST TANKING UNITS", "top_tanks", ("Unit", "Damage stopped"),
     lambda r: (f"{r.prevented:.0f}",)),
    ("FASTEST UNITS", "top_movers", ("Unit", "Distance"),
     lambda r: (f'{r.distance_in:.1f}"',)),
)

#: What an empty table says. Naming the reason beats an empty frame - before
#: a shot is fired every one of these is legitimately empty.
EMPTY_TEXT = {
    "top_killers": "no wounds dealt yet",
    "top_tanks": "nothing turned aside yet",
    "top_movers": "nothing has moved yet",
}


def _points(value):
    """A points share, rounded for reading. It is a pro-rata figure (see
    BattleStats.record_damage), so it is genuinely fractional - but a resume
    line wants "137", not "136.84"."""
    return f"{value:.0f}"


def button_rect(board_rect, font, ai_toggle_rect):
    """Where the STATS button goes: immediately LEFT of the AI switch, sharing
    its row and its height.

    User: "der knopf fuer das overlay soll nebn dem schalter fuer die KI
    sein." Derived from the switch's own rect rather than measured out from
    the board corner a second time, so "beside it" stays true by construction
    - if the switch ever has to step aside again (ai_busy_badge's avoid_rects,
    unused today), this follows it.

    Deliberately NOT passed to the switch as an avoid_rects blocker: that
    would push the AI switch down, and it is meant to stand still."""
    if ai_toggle_rect is None:
        return None
    return pygame.Rect(ai_toggle_rect.x - BUTTON_GAP - BUTTON_WIDTH, ai_toggle_rect.y,
                       BUTTON_WIDTH, ai_toggle_rect.height)


def draw_button(surface, board_rect, font, ai_toggle_rect, mouse_pos=None):
    """Draws the button and returns the rect it was drawn at, or None.

    A plain button and not a toggle: it opens a screen, it is not a state the
    board is in. Default (blue) accent, which in this HUD means "pressing this
    costs nothing"."""
    rect = button_rect(board_rect, font, ai_toggle_rect)
    if rect is None:
        return None
    hovered = bool(mouse_pos) and rect.collidepoint(mouse_pos)
    return button_style.draw_button(surface, rect, BUTTON_LABEL, font, hovered=hovered)


class UnitStatsOverlay:
    """The resume screen. Opened from the STATS button beside the AI switch."""

    def __init__(self):
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.section_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.label_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3, bold=True)
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1)
        self.small_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3)

        self._open = False
        self.stats = None            # the BattleStats ledger, set by main.py
        self.player = None           # which army is on screen
        self._players = ()           # (player, faction keyword) in board order
        self._squads = {}            # squad name -> the live Squad, for art
        self.scroll = 0
        self._scroll_max = 0
        #: What the last draw() actually laid down, read back by the click
        #: handler and by the tests rather than being derived a second time -
        #: the same last_track_rect idiom game/ui/round_progress_bar.py uses,
        #: and for the same reason: a second derivation measures a different
        #: rectangle than the one on screen.
        self.last_rect = None
        self.last_badge_rects = {}   # player -> the badge tile clicked to switch
        self._last_content_bottom = None

    @property
    def is_pending(self):
        return self._open

    def show(self, stats, players, squads):
        """Open on `players[0]`'s army.

        `players` is [(player, faction keyword)] in board order and `squads`
        is every live Squad - the overlay needs them for the sprites, which
        BattleStats deliberately does not hold: it keys by name so it can
        survive a save/load, and a name cannot be drawn."""
        if not players:
            return False
        self.stats = stats
        self._players = tuple(players)
        self._squads = {s.name: s for s in squads if getattr(s, "name", None)}
        if self.player not in [p for p, _k in self._players]:
            self.player = self._players[0][0]
        self._open = True
        self.scroll = 0
        return True

    def dismiss(self):
        self._open = False
        self.scroll = 0
        self.last_badge_rects = {}

    # ------------------------------------------------------------------- input

    def handle_event(self, event):
        """True when consumed. Only called while open."""
        if not self._open:
            return False
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_by(-event.y * SCROLL_STEP)
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.dismiss()
                return True
            step = _KEY_SCROLL.get(event.key)
            if step is None:
                return False
            if step == "home":
                self.scroll = 0
            elif step == "end":
                self.scroll = self._scroll_max
            else:
                self._scroll_by(step)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            # button == 1 is load-bearing, not tidiness: pygame emits a
            # MOUSEBUTTONDOWN with button 4/5 alongside every MOUSEWHEEL for
            # 1.x compatibility, so dismissing on any button makes the panel
            # impossible to scroll. game/ui/army_rules_overlay.py carries the
            # bug report that taught this.
            if event.button != 1:
                return True
            # The badges are the player switch, so they have to be hit-tested
            # BEFORE the click-anywhere dismiss below - otherwise switching
            # army closes the screen instead.
            for player, rect in self.last_badge_rects.items():
                if rect.collidepoint(event.pos):
                    if player != self.player:
                        self.player = player
                        self.scroll = 0
                    return True
            self.dismiss()
            return True
        return False

    def _scroll_by(self, delta):
        self.scroll = max(0, self.scroll + delta)
        if self._scroll_max:
            self.scroll = min(self.scroll, self._scroll_max)

    # ------------------------------------------------------------------ layout

    def panel_rect(self, screen_rect):
        chrome = 2 * PADDING + button_style.SCROLLBAR_WIDTH + 6
        width = min(max(MIN_WIDTH, int(screen_rect.width * WIDTH_FRACTION)),
                    MAX_TABLE_WIDTH + THUMB_COLUMN + chrome,
                    screen_rect.width - 2 * PADDING)
        height = min(int(screen_rect.height * HEIGHT_FRACTION), screen_rect.height - 2 * PADDING)
        rect = pygame.Rect(0, 0, width, height)
        rect.center = screen_rect.center
        return rect

    def _rows_for(self, key):
        """[(record, squad or None)] for one table of the shown player."""
        if self.stats is None or self.player is None:
            return []
        records = getattr(self.stats, key)(self.player, limit=3)
        return [(r, self._squads.get(r.name)) for r in records]

    def _heading_height(self, heading):
        """How far a section heading advances the cursor.

        ONE definition, read by the height prediction and by the drawing.
        They used to read two - get_height() and the rendered surface's own
        height - and for this bold SysFont those differ by 2px, so the
        prediction came out 6px short over three sections. Font.size() is what
        the render will really measure, without allocating a surface for it."""
        return self.section_font.size(heading)[1] + 6

    def _row_height(self, name, name_width):
        lines = wrap_text(self.font, name, name_width - 8) or [name]
        text_height = len(lines) * (self.font.get_height() + 2)
        return max(THUMB_PX, text_height + 10)

    def _content_height(self, table_width):
        """Predicted height of everything below the header - compared against
        what draw() really laid down (self._last_content_bottom) by the test
        suite, which is how a double-counted gap gets caught."""
        total = 0
        for heading, key, columns, _values in SECTIONS:
            total += self._heading_height(heading)
            rows = self._rows_for(key)
            total += self.label_font.get_height() + 8      # the header row
            if not rows:
                total += self.font.get_height() + 8
            else:
                name_width = self._name_width(table_width, len(columns))
                for record, _squad in rows:
                    total += self._row_height(record.name, name_width) + ROW_GAP
            total += SECTION_GAP
        return total

    def _name_width(self, table_width, column_count):
        """The name column gets whatever the fixed number columns leave.

        Fixed rather than a share on purpose: with a share, a two-column table
        and a three-column one put their last number at a different x, and the
        three sections stop reading as one page. Pinning the number columns
        lands "Points", "Damage stopped" and "Distance" on the same right
        edge."""
        numbers = (column_count - 1) * NUMBER_COLUMN_WIDTH
        return max(160, table_width - THUMB_COLUMN - numbers)

    # ----------------------------------------------------------------- drawing

    def draw(self, surface):
        if not self._open:
            return
        screen_rect = surface.get_rect()
        scrim = pygame.Surface(screen_rect.size, pygame.SRCALPHA)
        scrim.fill((*SCRIM_COLOR, SCRIM_ALPHA))
        surface.blit(scrim, (0, 0))

        rect = self.panel_rect(screen_rect)
        self.last_rect = rect
        pygame.draw.rect(surface, BG_COLOR, rect)
        pygame.draw.rect(surface, BORDER_COLOR, rect, 2)

        self._draw_header(surface, rect)

        body = pygame.Rect(rect.x + PADDING, rect.y + HEADER_HEIGHT + 6,
                           rect.width - 2 * PADDING - button_style.SCROLLBAR_WIDTH - 6,
                           rect.height - HEADER_HEIGHT - FOOTER_HEIGHT - 12)
        content_height = self._content_height(body.width)
        self._scroll_max = max(0, content_height - body.height)
        self.scroll = min(self.scroll, self._scroll_max)

        previous_clip = surface.get_clip()
        surface.set_clip(body.clip(previous_clip) if previous_clip else body)
        y = body.y - self.scroll
        for heading, key, columns, values in SECTIONS:
            y = self._draw_section(surface, body, y, heading, key, columns, values)
        surface.set_clip(previous_clip)
        self._last_content_bottom = y + self.scroll

        track = pygame.Rect(rect.right - PADDING + 4, body.y + 2,
                            button_style.SCROLLBAR_WIDTH, body.height - 4)
        button_style.draw_scrollbar(
            surface, track, self.scroll, self._scroll_max,
            body.height / content_height if content_height else 1.0)

        hint = "click a badge to switch army  |  wheel / PgUp / PgDn to scroll  |  click or ESC to close"
        hint_surf = self.small_font.render(hint, True, DIM_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(center=(rect.centerx, rect.bottom - 14)))

    def _draw_header(self, surface, rect):
        title = self.title_font.render("UNIT STATISTICS", True, TITLE_COLOR)
        surface.blit(title, (rect.x + PADDING, rect.y + 12))

        # The badges double as the player switch, so they are drawn right to
        # left from the panel's edge and their rects are recorded for the
        # click handler.
        self.last_badge_rects = {}
        x = rect.right - PADDING - BADGE_PX
        for player, keyword in reversed(self._players):
            tile = pygame.Rect(x, rect.y + (HEADER_HEIGHT - BADGE_PX) // 2, BADGE_PX, BADGE_PX)
            faction_badge.draw(surface, tile, sprites.faction_logo_path(keyword),
                               player == self.player, keyword=keyword)
            self.last_badge_rects[player] = tile
            x -= BADGE_PX + BADGE_GAP

        if self.player is not None:
            accent = PLAYER_ACCENT_COLORS.get(self.player, DEFAULT_ACCENT_COLOR)
            name = self.section_font.render(self.player, True, accent)
            surface.blit(name, (x + BADGE_PX + BADGE_GAP - 8 - name.get_width(),
                                rect.y + (HEADER_HEIGHT - name.get_height()) // 2))
        pygame.draw.line(surface, BORDER_COLOR,
                         (rect.x + 1, rect.y + HEADER_HEIGHT),
                         (rect.right - 1, rect.y + HEADER_HEIGHT))

    def _draw_section(self, surface, body, y, heading, key, columns, values):
        head = self.section_font.render(heading, True, SECTION_COLOR)
        surface.blit(head, (body.x, y))
        y += self._heading_height(heading)

        rows = self._rows_for(key)
        name_width = self._name_width(body.width, len(columns))
        widths, positions = stat_table.column_layout(
            body.x + THUMB_COLUMN, body.width - THUMB_COLUMN, len(columns),
            first_width=name_width)

        header_height = self.label_font.get_height() + 8
        stat_table.draw_row(surface, widths, positions, y, header_height,
                            list(columns), self.label_font, HEADER_COLOR)
        y += header_height
        pygame.draw.line(surface, TABLE_LINE_COLOR, (body.x, y), (body.right, y))

        if not rows:
            empty = self.font.render(EMPTY_TEXT[key], True, DIM_TEXT_COLOR)
            surface.blit(empty, (body.x + THUMB_COLUMN, y + 4))
            return y + self.font.get_height() + 8 + SECTION_GAP

        for place, (record, squad) in enumerate(rows):
            row_height = self._row_height(record.name, name_width)
            if squad is not None:
                paths = sprites.portrait_paths(squad, limit=1)
                if paths:
                    cell = pygame.Rect(body.x, y + (row_height - THUMB_PX) // 2,
                                       THUMB_PX, THUMB_PX)
                    unit_thumbs.draw_cell(surface, cell, paths[0])
            colour = LEAD_COLOR if place == 0 else TEXT_COLOR
            stat_table.draw_row(surface, widths, positions, y, row_height,
                                [record.name] + list(values(record)), self.font, colour)
            y += row_height + ROW_GAP
        return y + SECTION_GAP
