"""A must-click-away notice that the AI has stopped answering.

User: "momentan stürzt das Spiel ab, wenn KI Modus an ist und die Verbindung
verloren geht oder api Fehler oder Guthaben leer. besser wäre eine Meldung
'Connection lost' und das Spiel geht aber ohne KI weiter."

WHY A MODAL AND NOT A LOG LINE. The game keeps running afterwards, and it
looks exactly like a game where the AI is thinking - a board that stops moving
with no explanation. Everything else in this loop that changes what the player
must do announces itself the same way (see game/ui/stratagem_notice_overlay.py
and game/ui/waaagh_notice_overlay.py), and this changes it more than any of
them: from here on the human is playing both sides.

IT SAYS WHAT TO DO NEXT, not just what broke. "Connection lost" alone leaves a
player waiting for it to come back; the second line is the one that matters -
the battle continues and they now advance the AI's phases themselves.

THE DANGER ACCENT, not the Stratagem violet or the confirm green: this is the
one notice in the game that reports something going wrong rather than something
happening.
"""

import pygame

from game import config
from game.ui import button_style
from game.ui.text_utils import wrap_text

OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_WIDTH = 460
BOX_PADDING = 20
BODY_LINE_HEIGHT = 24
BODY_TOP_GAP = 14
HINT_TOP_GAP = 16
BODY_TEXT_COLOR = (235, 225, 225)
REASON_TEXT_COLOR = (235, 170, 170)
HINT_TEXT_COLOR = (185, 185, 185)
HEADER_BLOCK_HEIGHT = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8

HEADING = "CONNECTION LOST"
BODY = ("The AI could not be reached, so it has stopped playing. "
        "The battle continues - you now take its turns as well.")


class AIOfflineOverlay:
    """Shown ONCE, the first time the agent goes offline.

    A single slot rather than the queue its two sibling notices use, and that
    is the difference that matters: a Stratagem spend or a Waaagh! can happen
    again, while "the AI stopped" is one event whose every repetition is the
    same event. ai/connection.py latches the first failure for exactly the same
    reason; this is that latch made visible."""

    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 2, bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._reason = None
        self._pending = False
        self._shown = False

    def show(self, reason=None):
        """Raise the notice. A no-op after the first time, so a loop that keeps
        noticing the AI is offline cannot keep re-raising it."""
        if self._shown:
            return False
        self._shown = True
        self._pending = True
        self._reason = reason
        return True

    @property
    def is_pending(self):
        return self._pending

    def dismiss(self):
        self._pending = False

    def reset(self):
        """For a new battle in the same process (main() is one battle, run() is
        the application - see the Game Menu). The connection latch itself is
        deliberately NOT reset there; this only forgets that it was announced."""
        self._reason = None
        self._pending = False
        self._shown = False

    def _lines(self, surface_width):
        text_width = BOX_WIDTH - 2 * BOX_PADDING
        body = wrap_text(self.body_font, BODY, text_width)
        reason = wrap_text(self.body_font, f"({self._reason})", text_width) \
            if self._reason else []
        return body, reason

    def draw(self, surface):
        if not self._pending:
            return
        screen_rect = surface.get_rect()
        dim = pygame.Surface(screen_rect.size, pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))

        body, reason = self._lines(screen_rect.width)
        hint_surf = self.hint_font.render("Click anywhere to continue", True, HINT_TEXT_COLOR)
        height = (HEADER_BLOCK_HEIGHT + BODY_TOP_GAP
                  + (len(body) + len(reason)) * BODY_LINE_HEIGHT
                  + HINT_TOP_GAP + hint_surf.get_height() + BOX_PADDING)
        box = pygame.Rect(0, 0, BOX_WIDTH, height)
        box.center = screen_rect.center

        button_style.draw_box(
            surface, box, border_color=button_style.BORDER_NORMAL_DANGER,
            bg_color=button_style.BG_NORMAL_DANGER, border_width=2,
        )
        y = button_style.draw_panel_header(
            surface, box, HEADING, self.heading_font,
            text_color=button_style.TEXT_NORMAL_DANGER,
            bg_color=button_style.BG_ACTIVE_DANGER,
        ) + BODY_TOP_GAP
        for line in body:
            surf = self.body_font.render(line, True, BODY_TEXT_COLOR)
            surface.blit(surf, surf.get_rect(centerx=box.centerx, y=y))
            y += BODY_LINE_HEIGHT
        for line in reason:
            surf = self.body_font.render(line, True, REASON_TEXT_COLOR)
            surface.blit(surf, surf.get_rect(centerx=box.centerx, y=y))
            y += BODY_LINE_HEIGHT
        y += HINT_TOP_GAP
        surface.blit(hint_surf, hint_surf.get_rect(centerx=box.centerx, y=y))
