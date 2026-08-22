import pygame

from game import config
from game.ui import button_style
from game.ui.text_utils import wrap_text

# User: "ich will außerdem, dass ein prompt erscheint, das ich weg klicken
# muss, wenn ein waagh ausgerufen wird." - same must-click-away pattern as
# game/ui/stratagem_notice_overlay.py's own StratagemNoticeOverlay, wired
# from game.waaagh.WaaaghController.on_called only when the caller is
# Player 2 (the AI) - a human already knows when THEY call a Waaagh!,
# they'd have just clicked its own button (once one exists - see
# game/factions/orks.py's own note on that still-missing UI hook).
#
# The "confirm" green accent, not "stratagem" violet - a Waaagh! costs no
# CP, so it isn't a Stratagem (button_style.py's own color code reserves
# violet specifically for CP-spending Stratagem buttons); green also reads
# as "a friendly army-wide buff just activated", and happens to be the
# thematic Ork color.
OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_WIDTH = 460
BOX_PADDING = 20
BODY_LINE_HEIGHT = 24
BODY_TOP_GAP = 14
HINT_TOP_GAP = 16
BODY_TEXT_COLOR = (225, 225, 225)
HINT_TEXT_COLOR = (185, 185, 185)
HEADER_BLOCK_HEIGHT = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8


class WaaaghNoticeOverlay:
    """A modal, must-click-away notice that `player` just called a Waaagh! -
    without this, it was just a quiet game_log line, easy to miss entirely
    while ai_auto_play keeps running (same gap StratagemNoticeOverlay was
    built to close for Stratagem spends). A queue, not a single slot, for
    the same reason StratagemNoticeOverlay uses one - though a Waaagh! can
    only ever be called once per player per battle, so in practice this
    queue never holds more than one entry at a time."""

    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 2, bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._queue = []  # [player, ...] - oldest first

    def enqueue(self, player):
        self._queue.append(player)

    @property
    def is_pending(self):
        return bool(self._queue)

    def dismiss(self):
        if self._queue:
            self._queue.pop(0)

    def draw(self, surface):
        if not self._queue:
            return
        player = self._queue[0]

        body_text = (
            f"{player} calls a WAAAGH! Until the start of their next Command phase: their units with this "
            "ability can charge after Advancing, get +1 Strength/+1 Attacks on melee weapons, and have a 5+ "
            "invulnerable save."
        )
        text_max_width = BOX_WIDTH - 2 * BOX_PADDING
        body_lines = wrap_text(self.body_font, body_text, text_max_width) or [body_text]

        box_height = (
            HEADER_BLOCK_HEIGHT
            + len(body_lines) * BODY_LINE_HEIGHT
            + HINT_TOP_GAP + self.hint_font.get_height()
            + BOX_PADDING
        )
        box_rect = pygame.Rect(0, 0, BOX_WIDTH, box_height)
        box_rect.center = surface.get_rect().center

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))

        button_style.draw_box(
            surface, box_rect, border_color=button_style.BORDER_NORMAL_CONFIRM,
            bg_color=button_style.BG_NORMAL_CONFIRM, border_width=2,
        )
        y = button_style.draw_panel_header(
            surface, box_rect, "WAAAGH!", self.heading_font,
            text_color=button_style.TEXT_NORMAL_CONFIRM, bg_color=button_style.BG_ACTIVE_CONFIRM,
        )

        for line in body_lines:
            line_surf = self.body_font.render(line, True, BODY_TEXT_COLOR)
            surface.blit(line_surf, line_surf.get_rect(centerx=box_rect.centerx, y=y))
            y += BODY_LINE_HEIGHT

        y += HINT_TOP_GAP
        hint_surf = self.hint_font.render("Click to continue", True, HINT_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(centerx=box_rect.centerx, y=y))
