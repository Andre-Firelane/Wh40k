import pygame

from game import config
from game.missions import BATTLE_ROUNDS
from game.ui import button_style

# Rule 07.01: the battle lasts BATTLE_ROUNDS rounds and then it is over - user:
# "das spiel soll nach runde 5 enden". Until this existed, TurnTracker simply
# kept counting and the game ran on forever, which is what its own docstring
# used to say out loud.
#
# Shaped like StratagemNoticeOverlay next door, with two differences that
# follow from what it is: it is a SLOT rather than a queue (a battle ends
# once), and dismissing it does not make it go away for good - nothing can
# advance afterwards anyway, so the click is only there to let you look at the
# final board rather than to trap you behind a box.
OVERLAY_DIM_COLOR = (0, 0, 0, 190)
BOX_WIDTH = 460
BOX_PADDING = 24
ROW_HEIGHT = 26
HEADING_GAP = 10
HINT_TOP_GAP = 18

BORDER_COLOR = (200, 165, 70)
HEADING_COLOR = (255, 215, 0)
TEXT_COLOR = (225, 230, 240)
WINNER_COLOR = (140, 245, 160)
HINT_COLOR = (185, 185, 185)

HEADER_BLOCK_HEIGHT = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8


class BattleEndOverlay:
    """The final score, shown once the last battle round has been played."""

    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 2, bold=True)
        self.row_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.detail_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._result = None   # [(player, primary, secondary, total), ...]
        self._shown = False   # the battle only ends once
        self.is_pending = False

    def show(self, mission_controller, players=("Player 1", "Player 2")):
        """Raise the overlay, once. Idempotent: main.py checks the tracker
        every frame, so this is reached on every frame after the battle ends."""
        if self._shown or mission_controller is None:
            return
        self._shown = True
        self.is_pending = True
        self._result = [
            (player,
             mission_controller.primary_points.get(player, 0),
             mission_controller.secondary_points.get(player, 0),
             mission_controller.total_points(player))
            for player in players
        ]

    def dismiss(self):
        """A click puts the box away so the final board can be looked at. It
        does NOT resume anything - the battle is over either way."""
        self.is_pending = False

    def _winner(self):
        if not self._result:
            return None
        best = max(row[3] for row in self._result)
        leaders = [row[0] for row in self._result if row[3] == best]
        return leaders[0] if len(leaders) == 1 else None

    def draw(self, surface):
        if not self.is_pending or not self._result:
            return
        rows = len(self._result)
        box_height = (
            HEADER_BLOCK_HEIGHT
            + self.heading_font.get_height() + HEADING_GAP
            + rows * (ROW_HEIGHT + self.detail_font.get_height() + 4)
            + HINT_TOP_GAP + self.hint_font.get_height()
            + BOX_PADDING
        )
        box_rect = pygame.Rect(0, 0, BOX_WIDTH, box_height)
        box_rect.center = surface.get_rect().center

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))
        button_style.draw_box(surface, box_rect, border_color=BORDER_COLOR,
                              bg_color=button_style.BOX_BG_COLOR, border_width=2)
        y = button_style.draw_panel_header(
            surface, box_rect, f"BATTLE OVER - {BATTLE_ROUNDS} ROUNDS PLAYED",
            self.heading_font, text_color=HEADING_COLOR,
        )

        winner = self._winner()
        headline = f"{winner} wins" if winner else "Draw"
        surf = self.heading_font.render(headline, True, WINNER_COLOR if winner else TEXT_COLOR)
        surface.blit(surf, surf.get_rect(centerx=box_rect.centerx, y=y))
        y += self.heading_font.get_height() + HEADING_GAP

        left = box_rect.x + BOX_PADDING
        for player, primary, secondary, total in self._result:
            colour = WINNER_COLOR if player == winner else TEXT_COLOR
            line = self.row_font.render(f"{player}: {total} VP", True, colour)
            surface.blit(line, (left, y))
            y += ROW_HEIGHT
            # The split is shown because the two halves came from completely
            # different places - objectives held round after round versus
            # Secondary cards cashed in - and the total alone hides that.
            detail = self.detail_font.render(
                f"    Primary {primary}  ·  Secondary {secondary}", True, HINT_COLOR)
            surface.blit(detail, (left, y))
            y += self.detail_font.get_height() + 4

        y += HINT_TOP_GAP
        hint = self.hint_font.render("Click to view the final board", True, HINT_COLOR)
        surface.blit(hint, hint.get_rect(centerx=box_rect.centerx, y=y))
