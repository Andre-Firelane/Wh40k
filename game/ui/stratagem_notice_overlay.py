import pygame

from game import config
from game.ui import button_style
from game.ui.text_utils import wrap_text

# User: "immer wenn die KI ein Stratagem benutzt will ich ein prompt haben
# mit der information, welches stratagem gerade benutzt wird, das ich
# wegklicken muss. die überschrift in diesem overlay soll vielettes color
# coding haben, wie die knöpfe." - main.py wires
# game.stratagems.StratagemController.on_stratagem_used to enqueue() below
# only when the acting player is Player 2 (the AI) - a human already knows
# when THEY spend a Stratagem, since they just clicked its button.
OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_WIDTH = 460
BOX_PADDING = 20
BODY_LINE_HEIGHT = 24
BODY_TOP_GAP = 14
HINT_TOP_GAP = 16
BODY_TEXT_COLOR = (225, 225, 225)
HINT_TEXT_COLOR = (185, 185, 185)
# Total vertical space button_style.draw_panel_header()'s fixed-height bar
# actually occupies (rect.y + HEADER_MARGIN as its top, HEADER_BAR_HEIGHT
# tall) plus the small gap it leaves before its own return value - needed
# up front here to size the box, before the header itself is drawn.
HEADER_BLOCK_HEIGHT = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8


class StratagemNoticeOverlay:
    """A modal, must-click-away notice naming whichever Stratagem the AI
    just used - without this, a Stratagem spend during ai_auto_play was
    just a quiet game_log line, easy to miss entirely while auto-play keeps
    running. A queue (not a single slot): a chain of reactive Stratagems
    (Rapid Ingress -> Fire Overwatch, both offered in the same reactive
    window) or a Command Re-roll landing back to back with another
    Stratagem use can enqueue a second notice before the first is even
    dismissed - each one gets read, none silently clobbers another.

    The heading uses the same violet "stratagem" accent as every Stratagem
    button in ActionPanel (game/ui/button_style.py's "stratagem" palette) -
    user: "die überschrift... soll vielettes color coding haben, wie die
    knöpfe" - so a Stratagem spend reads as visually the same "kind of
    thing" everywhere it shows up."""

    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 2, bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._queue = []  # [(player, stratagem_name, cp_cost), ...] - oldest first

    def enqueue(self, player, stratagem):
        self._queue.append((player, stratagem.name, stratagem.cp_cost))

    @property
    def is_pending(self):
        return bool(self._queue)

    def dismiss(self):
        if self._queue:
            self._queue.pop(0)

    def draw(self, surface):
        if not self._queue:
            return
        player, name, cp_cost = self._queue[0]

        cost_text = "free" if cp_cost == 0 else (f"{cp_cost} CP" if cp_cost != 1 else "1 CP")
        body_text = f"{player} uses this Stratagem ({cost_text})."
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
            surface, box_rect, border_color=button_style.BORDER_NORMAL_STRATAGEM,
            bg_color=button_style.BG_NORMAL_STRATAGEM, border_width=2,
        )
        y = button_style.draw_panel_header(
            surface, box_rect, name.upper(), self.heading_font,
            text_color=button_style.TEXT_NORMAL_STRATAGEM, bg_color=button_style.BG_ACTIVE_STRATAGEM,
        )

        for line in body_lines:
            line_surf = self.body_font.render(line, True, BODY_TEXT_COLOR)
            surface.blit(line_surf, line_surf.get_rect(centerx=box_rect.centerx, y=y))
            y += BODY_LINE_HEIGHT

        y += HINT_TOP_GAP
        hint_surf = self.hint_font.render("Click to continue", True, HINT_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(centerx=box_rect.centerx, y=y))
