import pygame

from game import config
from game import game_log as game_log_module
from game.ui import button_style
from game.ui.text_utils import wrap_text

LINE_HEIGHT = 18
HEADER_HEIGHT = 40  # room for draw_panel_header()'s title + glow bar (was 30, plain title-only)
MARGIN = 10
BOX_PADDING = 6
BOX_GAP = 6

FILTER_ROW_HEIGHT = 24
FILTER_GAP = 4
FILTER_PADDING_X = 8
SCROLL_LINES = 2  # entries moved per wheel notch

ALL_FILTER = None  # the "show everything" chip's key


class LogPanel:
    """The game log, on the right. Every entry gets its own bordered box -
    always the same look, and the message text is clipped to the box's
    inner rect as a second line of defence. wrap_text() now hard-breaks a
    word too long for one line (it used to emit such a word as one
    overflowing line, which is what this clip was originally guarding
    against), so the clip should no longer have anything to cut off.

    FILTERED and SCROLLABLE, on request ("das log unten rechts so wie es
    momentan ist, bringt mir nicht viel. ich möchte dort lieber von mir
    ausgesuchte sachen sehen, anstatt alles" / "außerdem möchte ich im log
    scrollen können"). The chips across the top come from
    game_log.CATEGORIES, so a new filter is a row in that table plus tagging
    the add() calls that belong to it - nothing here has to change.

    Both controls are pure VIEW state and live here rather than in the game
    state: nothing about which lines are on screen can affect a rule, so main()
    handles their input in its early, ungated event branches (next to the wheel
    zoom) instead of the state-gated chain further down, and clicking a chip
    while a dice roll is pending works exactly as it does at any other time."""

    def __init__(self):
        self.header_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self.chip_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3, bold=True)
        self.filter = ALL_FILTER
        # How many of the newest matching entries are scrolled past. 0 means
        # "pinned to the newest", which is the old behaviour and the default.
        self.scroll = 0
        self._chips = []       # (filter key, rect), rebuilt every draw
        self._visible_count = 0
        self._shown_count = 0  # how many boxes actually fit last draw

    # ---------------------------------------------------------------- input

    def handle_click(self, pos):
        """A click anywhere in the panel. True if it hit a filter chip."""
        for key, rect in self._chips:
            if rect.collidepoint(pos):
                if self.filter != key:
                    self.filter = key
                    self.scroll = 0  # a new filter has its own newest entry
                return True
        return False

    def handle_scroll(self, wheel_y):
        """Wheel up (positive) goes back through history, down returns to the
        newest. Clamped so the oldest matching entry is the far end - scrolling
        into empty space above the log reads as the panel being broken."""
        self.scroll = max(0, min(self._max_scroll(), self.scroll + wheel_y * SCROLL_LINES))

    def _max_scroll(self):
        return max(0, self._visible_count - max(1, self._shown_count))

    @property
    def is_scrolled(self):
        return self.scroll > 0

    # ----------------------------------------------------------------- draw

    def _matching(self, game_log):
        if self.filter is ALL_FILTER:
            return list(game_log.entries)
        return [e for e in game_log.entries if getattr(e, "category", None) == self.filter]

    def draw(self, surface, rect, game_log):
        surface.fill(config.PANEL_BG_COLOR, rect)
        pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, width=2)

        entries = self._matching(game_log)
        # Adding entries while scrolled back would slide the view forward under
        # the reader, since `scroll` counts from the newest end. Absorbing the
        # growth keeps the same lines on screen; at scroll 0 it stays pinned to
        # the newest, which is what "not scrolled" should mean.
        if self.scroll > 0 and len(entries) > self._visible_count:
            self.scroll += len(entries) - self._visible_count
        self._visible_count = len(entries)
        self.scroll = min(self.scroll, self._max_scroll())

        title = "Log" if self.filter is ALL_FILTER else \
            f"Log - {game_log_module.CATEGORY_LABELS.get(self.filter, self.filter)}"
        if self.is_scrolled:
            title += f"  (+{self.scroll} newer)"
        button_style.draw_panel_header(surface, rect, title, self.header_font)

        filter_bottom = self._draw_filters(surface, rect, game_log)

        inner_rect = pygame.Rect(
            rect.x + MARGIN, filter_bottom,
            rect.width - 2 * MARGIN, rect.bottom - MARGIN - filter_bottom,
        )
        if inner_rect.height <= 0:
            self._shown_count = 0
            return
        max_text_width = inner_rect.width - 2 * BOX_PADDING

        if not entries:
            note = "nothing logged under this filter yet" if self.filter is not ALL_FILTER else ""
            if note:
                for i, line in enumerate(wrap_text(self.font, note, max_text_width)):
                    surface.blit(self.font.render(line, True, config.PANEL_BORDER_COLOR),
                                 (inner_rect.x, inner_rect.y + i * LINE_HEIGHT))
            self._shown_count = 0
            return

        newest_first = list(reversed(entries))[self.scroll:]

        boxes = []  # newest first: (box_rect, lines)
        bottom = inner_rect.bottom
        for message in newest_first:
            lines = wrap_text(self.font, message, max_text_width) or [message]
            box_height = len(lines) * LINE_HEIGHT + 2 * BOX_PADDING
            top = bottom - box_height
            if top < inner_rect.y:
                break
            boxes.append((pygame.Rect(inner_rect.x, top, inner_rect.width, box_height), lines))
            bottom = top - BOX_GAP
        self._shown_count = len(boxes)

        for box_rect, lines in reversed(boxes):  # draw oldest-to-newest, top-to-bottom
            button_style.draw_box(surface, box_rect)

            clip_rect = box_rect.inflate(-2, -2)
            previous_clip = surface.get_clip()
            surface.set_clip(clip_rect)
            text_y = box_rect.y + BOX_PADDING
            for line in lines:
                line_surf = self.font.render(line, True, config.PANEL_TEXT_COLOR)
                surface.blit(line_surf, (box_rect.x + BOX_PADDING, text_y))
                text_y += LINE_HEIGHT
            surface.set_clip(previous_clip)

    def _draw_filters(self, surface, rect, game_log):
        """The chip row under the header. Returns the y the entries start at.

        Each chip carries how many entries currently match it, so an empty
        filter is visibly empty rather than looking like a bug - the same
        reason the empty-state line above says which filter is on."""
        counts = {}
        for entry in game_log.entries:
            key = getattr(entry, "category", None)
            counts[key] = counts.get(key, 0) + 1

        chips = [(ALL_FILTER, f"All ({len(game_log.entries)})")]
        for key, label, _why in game_log_module.CATEGORIES:
            chips.append((key, f"{label} ({counts.get(key, 0)})"))

        self._chips = []
        x = rect.x + MARGIN
        y = rect.y + HEADER_HEIGHT
        row_bottom = y + FILTER_ROW_HEIGHT
        for key, label in chips:
            selected = (key == self.filter)
            text = self.chip_font.render(
                label, True,
                button_style.TEXT_ACTIVE if selected else button_style.TEXT_NORMAL)
            width = text.get_width() + 2 * FILTER_PADDING_X
            if x + width > rect.right - MARGIN and self._chips:
                # Wrap onto another row rather than running off the panel - the
                # chip has to stay clickable, and its rect is what makes it so.
                x = rect.x + MARGIN
                y = row_bottom + FILTER_GAP
                row_bottom = y + FILTER_ROW_HEIGHT
            chip_rect = pygame.Rect(x, y, min(width, rect.width - 2 * MARGIN), FILTER_ROW_HEIGHT)
            button_style.draw_box(
                surface, chip_rect,
                bg_color=button_style.BG_ACTIVE if selected else button_style.BG_NORMAL,
                border_color=button_style.BORDER_ACTIVE if selected else button_style.BORDER_NORMAL,
            )
            surface.blit(text, text.get_rect(center=chip_rect.center))
            self._chips.append((key, chip_rect))
            x += chip_rect.width + FILTER_GAP
            row_bottom = max(row_bottom, chip_rect.bottom)

        return row_bottom + FILTER_GAP
