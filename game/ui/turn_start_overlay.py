import pygame

from game import config
from game.ui import button_style

# User: "ich will ein overlay, wenn ein neuer zug beginnt, das man
# wegklicken muss. einfach mit 'Player X Turn Y'." - a modal, must-click-away
# banner shown once at the start of EVERY player turn (both players,
# including the very first turn of the game - see main.py's
# previous_turn_owner init), naming whichever player's turn it now is and
# how many turns THAT player has had so far (TurnTracker.turn_number_for(),
# the same per-player counter rule 13.09/Hidden already uses - not the
# shared battle_round, which covers both players' turns at once).
#
# Deliberately the plainest possible overlay (User: "einfach") - no queue
# like StratagemNoticeOverlay (there's only ever one "current" turn at a
# time, nothing can enqueue a second one before the first is dismissed) and
# the DEFAULT button_style palette (this isn't a Stratagem spend, so it
# doesn't get the violet accent - see DecisionOverlay's is_stratagem for
# that one).
OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_WIDTH = 460
BOX_PADDING = 20
HINT_TOP_GAP = 16
HINT_TEXT_COLOR = (185, 185, 185)
HEADER_BLOCK_HEIGHT = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8


class TurnStartOverlay:
    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._text = None

    def show(self, player, turn_number):
        self._text = f"{player} Turn {turn_number}"

    @property
    def is_pending(self):
        return self._text is not None

    def dismiss(self):
        self._text = None

    def draw(self, surface):
        if self._text is None:
            return

        box_height = HEADER_BLOCK_HEIGHT + HINT_TOP_GAP + self.hint_font.get_height() + BOX_PADDING
        box_rect = pygame.Rect(0, 0, BOX_WIDTH, box_height)
        box_rect.center = surface.get_rect().center

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))

        button_style.draw_box(surface, box_rect, border_width=2)
        y = button_style.draw_panel_header(surface, box_rect, self._text.upper(), self.heading_font)

        y += HINT_TOP_GAP
        hint_surf = self.hint_font.render("Click to continue", True, HINT_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(centerx=box_rect.centerx, y=y))
