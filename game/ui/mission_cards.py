import pygame

from game import config
from game.missions import (
    PRIMARY_MISSION_NAME, PRIMARY_MISSION_TEXT, SECONDARY_MISSION_NAME, SECONDARY_MISSION_TEXT,
)
from game.ui.text_utils import draw_wrapped_text

CARD_WIDTH = 250
CARD_HEIGHT = 150  # tall enough for the player/category badge + title + wrapped body + score line together
CARD_PEEK_WIDTH = 26      # visible sliver width while collapsed - just enough to notice it's there
CARD_GAP = 10             # vertical gap between the two cards of the SAME player's cluster
CLUSTER_GAP = 28          # extra vertical gap between one player's pair of cards and the other player's
BOTTOM_MARGIN = 26        # gap between the lowest card and the left panel's own bottom edge
CORNER_RADIUS = 8
SLIDE_LERP = 0.25         # per-frame interpolation factor toward the hover target width (0..1)
TEXT_REVEAL_THRESHOLD = CARD_WIDTH - 20  # below this width, mid-slide, don't bother rendering squeezed text

CARD_BG_COLOR = (14, 20, 30)
CARD_TITLE_COLOR = (255, 215, 0)
CARD_TEXT_COLOR = (205, 230, 248)
CARD_CATEGORY_COLOR = (170, 220, 245)
CARD_SCORE_COLOR = (255, 230, 170)

# Same fixed per-player identity colors as the objective-control markers on
# the board (renderer.py's OBJECTIVE_COLORS) - duplicated here rather than
# imported, matching this codebase's usual per-module small-constant
# convention (see e.g. the several separate _other_player() helpers) - so a
# player's mission cards read as visually theirs at a glance, collapsed or
# not, purely via border color.
PLAYER_ACCENT_COLORS = {
    "Player 1": (70, 140, 230),   # blue
    "Player 2": (220, 60, 60),    # red
}
PLAYER_ACCENT_HOVER_COLORS = {
    "Player 1": (140, 195, 255),
    "Player 2": (255, 120, 120),
}
DEFAULT_ACCENT_COLOR = (90, 160, 205)
DEFAULT_ACCENT_HOVER_COLOR = (140, 210, 255)


class _MissionCard:
    def __init__(self, player, category, title, text):
        self.player = player       # "Player 1"/"Player 2" - which player's progress this card is about
        self.category = category   # "Primary"/"Secondary" - only shown once expanded
        self.title = title          # the mission's own name - shown expanded, and rotated while collapsed
        self.text = text
        self.width = CARD_PEEK_WIDTH  # animated float, collapsed by default


class MissionCardsOverlay:
    """User-supplied UI: rounded-corner reference cards, one Primary and one
    Secondary per player (both players run the identical two missions - see
    game/missions.py - only their progress differs) - "ich muss die
    Missionen von beiden Spielern sehen können... optisch voneinander
    getrennt eigene und gegnerische Missionen aufreihen". The four cards
    stack bottom-up in two clusters (Player 1's pair, then Player 2's pair,
    with an extra CLUSTER_GAP between them and each player's own accent
    color on the border) so they read as two clearly separate groups
    instead of one undifferentiated pile - "leicht hinter dem linken Panel
    ziemlich weit unten hervorlucken... wenn man über die Karten hovert
    sollen sie rausgleiten" still applies per-card: each is anchored with
    its left edge flush against the left Actions panel's own right border,
    animating its own width between a thin collapsed sliver and its full
    readable width depending on whether the mouse is over it.

    Deliberately plain rounded rects (pygame.draw.rect(..., border_radius=)),
    NOT the game's usual chamfered button_style.draw_box() HUD look - the
    user specifically asked for rounded corners here, a distinct "mission
    card" look.

    GameStatusPanel's own Mission Points group remains the always-visible
    summary of every player's totals at a glance; these cards are the
    hover-to-read detail per player/mission, now including that specific
    mission's own current score once expanded."""

    def __init__(self):
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1, bold=True)
        self.collapsed_title_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4, bold=True)
        self.category_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 5, bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4)
        self.score_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3, bold=True)
        # Bottom-up order: Player 2's pair sits closest to the panel's own
        # bottom edge, Player 1's pair directly above it (matches
        # GameStatusPanel/CommandPointManager's usual "Player 1 first"
        # reading order, just laid out upward instead of left-to-right).
        self._cards = [
            _MissionCard("Player 1", "Primary", PRIMARY_MISSION_NAME, PRIMARY_MISSION_TEXT),
            _MissionCard("Player 1", "Secondary", SECONDARY_MISSION_NAME, SECONDARY_MISSION_TEXT),
            _MissionCard("Player 2", "Primary", PRIMARY_MISSION_NAME, PRIMARY_MISSION_TEXT),
            _MissionCard("Player 2", "Secondary", SECONDARY_MISSION_NAME, SECONDARY_MISSION_TEXT),
        ]

    def _card_tops(self, left_panel_rect):
        """Fixed y-position (top edge) per card index - independent of any
        card's current animated width, since every card is always anchored
        at left_panel_rect.right regardless of how wide it currently is.
        Computed bottom-up so the LAST card in self._cards sits closest to
        left_panel_rect's own bottom edge; a CLUSTER_GAP (wider than the
        normal CARD_GAP) is inserted right where the player identity
        changes between two adjacent cards, visually splitting the stack
        into its two per-player groups."""
        n = len(self._cards)
        tops = [None] * n
        bottom = left_panel_rect.bottom - BOTTOM_MARGIN
        for i in range(n - 1, -1, -1):
            top = bottom - CARD_HEIGHT
            tops[i] = top
            if i == 0:
                break
            gap = CARD_GAP if self._cards[i - 1].player == self._cards[i].player else CLUSTER_GAP
            bottom = top - gap
        return tops

    def _card_rect(self, index, left_panel_rect, width, tops=None):
        top = (tops or self._card_tops(left_panel_rect))[index]
        return pygame.Rect(left_panel_rect.right, top, width, CARD_HEIGHT)

    def draw(self, surface, left_panel_rect, mission_controller=None):
        mouse_pos = pygame.mouse.get_pos()
        tops = self._card_tops(left_panel_rect)
        for index, card in enumerate(self._cards):
            hovered = self._card_rect(index, left_panel_rect, card.width, tops).collidepoint(mouse_pos)
            target_width = CARD_WIDTH if hovered else CARD_PEEK_WIDTH
            card.width += (target_width - card.width) * SLIDE_LERP
            if abs(card.width - target_width) < 0.5:
                card.width = target_width  # snap once close enough to stop the float drifting forever
            rect = self._card_rect(index, left_panel_rect, card.width, tops)
            self._draw_card(surface, rect, card, hovered, mission_controller)

    def _draw_card(self, surface, rect, card, hovered, mission_controller):
        accent_colors = PLAYER_ACCENT_COLORS.get(card.player)
        if accent_colors is not None:
            border_color = PLAYER_ACCENT_HOVER_COLORS[card.player] if hovered else accent_colors
        else:
            border_color = DEFAULT_ACCENT_HOVER_COLOR if hovered else DEFAULT_ACCENT_COLOR
        pygame.draw.rect(surface, CARD_BG_COLOR, rect, border_radius=CORNER_RADIUS)
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=CORNER_RADIUS)

        prev_clip = surface.get_clip()
        surface.set_clip(rect)

        if rect.width < TEXT_REVEAL_THRESHOLD:
            # Collapsed (or still mid-slide) - too narrow for the normal
            # horizontal layout to read, but the user still wants the
            # mission's name visible even collapsed: rendered horizontally
            # then rotated 90 degrees (top-to-bottom) and centered in the
            # sliver, instead of leaving it blank until fully expanded. The
            # player-colored border (see above) is what actually tells two
            # same-category collapsed cards ("Hold the Line" appears twice,
            # once per player) apart from each other at a glance.
            title_surf = self.collapsed_title_font.render(card.title, True, CARD_TITLE_COLOR)
            rotated_surf = pygame.transform.rotate(title_surf, -90)
            surface.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))
            surface.set_clip(prev_clip)
            return

        text_x = rect.x + 14
        text_y = rect.y + 10
        badge_color = accent_colors if accent_colors is not None else CARD_CATEGORY_COLOR
        # Badge and title wrap like the body text does - a mission's name is
        # data too, and this card is narrower than the body text's own
        # wrapping width suggests while it's still mid-slide.
        text_width = rect.width - 28
        text_y = draw_wrapped_text(
            surface, self.category_font, f"{card.player} · {card.category.upper()}", badge_color,
            text_x, text_y, text_width, line_height=self.category_font.get_height() + 2,
        ) + 2
        text_y = draw_wrapped_text(
            surface, self.title_font, card.title, CARD_TITLE_COLOR,
            text_x, text_y, text_width, line_height=self.title_font.get_height() + 2,
        ) + 4
        text_y = draw_wrapped_text(
            surface, self.body_font, card.text, CARD_TEXT_COLOR,
            text_x, text_y, text_width, line_height=self.body_font.get_height() + 2,
        )

        if mission_controller is not None:
            if card.category == "Primary":
                points = mission_controller.primary_points.get(card.player, 0)
            else:
                points = mission_controller.secondary_points.get(card.player, 0)
            text_y += 4
            score_surf = self.score_font.render(f"Score: {points} pts", True, CARD_SCORE_COLOR)
            surface.blit(score_surf, (text_x, text_y))

        surface.set_clip(prev_clip)
