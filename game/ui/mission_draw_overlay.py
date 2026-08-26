import pygame

from game import config
from game.ui import button_style
from game.ui.text_utils import wrap_text

# User: "am Anfang jeder Runde zieht man ja zwei neue Missionen. Ich moechte,
# dass diese Missionen einmal in einem Overlay angezeigt werden, zum
# Wegklicken, und dann der Link zur linken Leiste hinzugefuegt werden."
#
# Modeled directly on StratagemNoticeOverlay next door - a QUEUE rather than a
# single slot, for the same reason it gives: a second announcement can be
# enqueued before the first is dismissed (here, a When Drawn redraw resolving
# right as the next thing happens), and each one should get read rather than
# silently clobbering the last.
#
# The cards themselves keep living in MissionCardsOverlay on the left; this is
# purely the "here is what you just drew" moment. Deliberately the same plain
# rounded-rect card look as that strip (NOT the chamfered button_style HUD box
# the other notices use for their bodies) so a card reads as the same kind of
# object in both places.
OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_PADDING = 22
CARD_WIDTH = 300
CARD_GAP = 18
CARD_PADDING = 14
CARD_CORNER_RADIUS = 8
CARD_MIN_HEIGHT = 150
HINT_TOP_GAP = 16
TITLE_GAP = 6
BODY_GAP = 8
BODY_LINE_GAP = 2

CARD_BG_COLOR = (14, 20, 30)
CARD_BORDER_COLOR = (200, 165, 70)     # the "a card was dealt" gold, distinct from the strip's per-player accents
CARD_TITLE_COLOR = (255, 215, 0)
CARD_CATEGORY_COLOR = (170, 220, 245)
CARD_TEXT_COLOR = (205, 230, 248)
CARD_DETAIL_COLOR = (255, 205, 120)  # a card's WHEN DRAWN choice - the one line the printed text cannot carry
HINT_TEXT_COLOR = (185, 185, 185)

HEADER_BLOCK_HEIGHT = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8


class MissionDrawOverlay:
    """A modal, must-click-away notice naming the Secondary Mission cards the
    player just drew, shown at the start of their Command phase before the
    cards join the strip on the left."""

    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 2, bold=True)
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.category_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 5, bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._queue = []  # [(player, [card, ...]), ...] - oldest first

    def enqueue(self, player, cards, details=None):
        """Cards are the SecondaryMissionCard objects themselves (name/text are
        read off them), not pre-rendered strings - so a card's wording has one
        source, game/secondary_missions.py."""
        cards = list(cards)
        if cards:
            # details: {card key: one-line description of what this card just
            # picked}. A card whose WHEN DRAWN clause names an objective or a
            # unit is unreadable without it - the printed text says "your
            # tempting target", never WHICH one.
            self._queue.append((player, cards, dict(details or {})))

    @property
    def is_pending(self):
        return bool(self._queue)

    def dismiss(self):
        if self._queue:
            self._queue.pop(0)

    def _card_body_lines(self, card, detail=None):
        lines = wrap_text(self.body_font, card.text, CARD_WIDTH - 2 * CARD_PADDING) or [card.text]
        if detail:
            lines = lines + [""] + (wrap_text(self.body_font, detail, CARD_WIDTH - 2 * CARD_PADDING) or [detail])
        return lines

    def _card_height(self, card, detail=None):
        """Measure-then-draw: every card in one notice is drawn at the SAME
        height (the tallest), so two cards of different text length still read
        as a pair rather than as a layout accident."""
        lines = self._card_body_lines(card, detail)
        return (
            CARD_PADDING
            + self.category_font.get_height() + TITLE_GAP
            + self.title_font.get_height() + BODY_GAP
            + len(lines) * (self.body_font.get_height() + BODY_LINE_GAP)
            + CARD_PADDING
        )

    def draw(self, surface):
        if not self._queue:
            return
        player, cards, details = self._queue[0]

        card_height = max(CARD_MIN_HEIGHT,
                          max(self._card_height(c, details.get(c.key)) for c in cards))
        cards_width = len(cards) * CARD_WIDTH + (len(cards) - 1) * CARD_GAP
        box_width = cards_width + 2 * BOX_PADDING
        box_height = (
            HEADER_BLOCK_HEIGHT + card_height
            + HINT_TOP_GAP + self.hint_font.get_height()
            + BOX_PADDING
        )
        box_rect = pygame.Rect(0, 0, box_width, box_height)
        box_rect.center = surface.get_rect().center

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))

        button_style.draw_box(surface, box_rect, border_color=CARD_BORDER_COLOR,
                              bg_color=button_style.BOX_BG_COLOR, border_width=2)
        heading = "SECONDARY MISSION DRAWN" if len(cards) == 1 else "SECONDARY MISSIONS DRAWN"
        y = button_style.draw_panel_header(
            surface, box_rect, heading, self.heading_font, text_color=CARD_TITLE_COLOR,
        )

        x = box_rect.x + BOX_PADDING
        for card in cards:
            self._draw_card(surface, pygame.Rect(x, y, CARD_WIDTH, card_height), player, card,
                            details.get(card.key))
            x += CARD_WIDTH + CARD_GAP

        y += card_height + HINT_TOP_GAP
        hint_surf = self.hint_font.render("Click to continue", True, HINT_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(centerx=box_rect.centerx, y=y))

    def _draw_card(self, surface, rect, player, card, detail=None):
        pygame.draw.rect(surface, CARD_BG_COLOR, rect, border_radius=CARD_CORNER_RADIUS)
        pygame.draw.rect(surface, CARD_BORDER_COLOR, rect, width=2, border_radius=CARD_CORNER_RADIUS)

        text_x = rect.x + CARD_PADDING
        y = rect.y + CARD_PADDING
        badge = self.category_font.render(f"{player} - SECONDARY", True, CARD_CATEGORY_COLOR)
        surface.blit(badge, (text_x, y))
        y += self.category_font.get_height() + TITLE_GAP

        title = self.title_font.render(card.name.upper(), True, CARD_TITLE_COLOR)
        surface.blit(title, (text_x, y))
        y += self.title_font.get_height() + BODY_GAP

        body_lines = wrap_text(self.body_font, card.text, CARD_WIDTH - 2 * CARD_PADDING) or [card.text]
        for line in body_lines:
            surface.blit(self.body_font.render(line, True, CARD_TEXT_COLOR), (text_x, y))
            y += self.body_font.get_height() + BODY_LINE_GAP
        if detail:
            y += self.body_font.get_height() // 2
            for line in wrap_text(self.body_font, detail, CARD_WIDTH - 2 * CARD_PADDING) or [detail]:
                surface.blit(self.body_font.render(line, True, CARD_DETAIL_COLOR), (text_x, y))
                y += self.body_font.get_height() + BODY_LINE_GAP
