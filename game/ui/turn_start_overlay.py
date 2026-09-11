import pygame

from game import config, sprites
from game.ui import button_style, faction_badge

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

# --- the faction badge (user: "baue dort bitte auch das fraktions Logo ein") ---
#
# Its OWN size, not the Game Status panel's LOGO_BOX. That 72 px is sized for a
# 200 px column; this banner sits at the centre of the screen with 460 px to
# spend and is on screen for one click, so it can afford to be read at a
# glance. game/ui/faction_badge.py takes the tile RECT rather than a size for
# exactly this reason.
#
# The two are CLOSER than they were - the panel's tile grew from 58 to 72 when
# the round counter freed the middle of that column - but the ordering is the
# design statement (showcase vs. reference tile), not the margin, and
# test_turn_start_overlay.py pins it. This is the ceiling the panel's constant
# is measured against, so growing that one further means growing this one too.
BADGE_BOX = 76
BADGE_TOP_GAP = 4        # px between the box's top padding and the tile
BADGE_BOTTOM_GAP = 10    # px between the tile and the heading bar under it


class TurnStartOverlay:
    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._text = None
        self._keyword = None
        self._logo_path = None

    def show(self, player, turn_number, faction_keyword=None):
        """`faction_keyword` is which army this player fields, or None.

        Resolved to a logo HERE rather than at draw time, because the banner
        stands until it is clicked and the answer cannot change under it: the
        turn it names belongs to one player with one army. None simply draws
        the banner as it always was - a hand-built squad has no datasheet and
        therefore no faction, and an empty framed square would read as art that
        failed to load rather than as a badge."""
        self._text = f"{player} Turn {turn_number}"
        self._keyword = faction_keyword
        self._logo_path = (sprites.faction_logo_path(faction_keyword)
                           if faction_keyword else None)

    @property
    def is_pending(self):
        return self._text is not None

    def dismiss(self):
        self._text = None
        self._keyword = None
        self._logo_path = None

    def draw(self, surface):
        if self._text is None:
            return

        # The tile is only RESERVED when it would show something: an empty
        # square is worse than no square, and the box must not grow around one.
        badge = faction_badge.has_content(self._logo_path, self._keyword)
        badge_block = BADGE_TOP_GAP + BADGE_BOX + BADGE_BOTTOM_GAP if badge else 0
        box_height = (badge_block + HEADER_BLOCK_HEIGHT + HINT_TOP_GAP
                      + self.hint_font.get_height() + BOX_PADDING)
        box_rect = pygame.Rect(0, 0, BOX_WIDTH, box_height)
        box_rect.center = surface.get_rect().center

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))

        button_style.draw_box(surface, box_rect, border_width=2)
        header_rect = box_rect
        if badge:
            tile = pygame.Rect(0, 0, BADGE_BOX, BADGE_BOX)
            tile.centerx = box_rect.centerx
            tile.y = box_rect.y + BADGE_TOP_GAP
            # ABOVE the heading and centred, not beside it: the heading is a
            # full-width bar (draw_panel_header), so there is no side to put a
            # tile on without either overlapping it or making the bar shorter
            # than every other header in the game.
            #
            # active=True: this banner names ONE player, and it is theirs. The
            # panel passes the same flag for the transient "who is the game
            # waiting on" - two questions, one answer per caller, which is why
            # faction_badge.draw() is handed it rather than deriving it.
            faction_badge.draw(surface, tile, self._logo_path, True, self._keyword)
            # The header is laid out against a rect that starts BELOW the tile:
            # draw_panel_header() measures from its rect's top, so shifting the
            # rect is what moves the bar without teaching it about badges.
            header_rect = pygame.Rect(box_rect.x, tile.bottom + BADGE_BOTTOM_GAP,
                                      box_rect.width, box_rect.height)
        y = button_style.draw_panel_header(surface, header_rect, self._text.upper(), self.heading_font)

        y += HINT_TOP_GAP
        hint_surf = self.hint_font.render("Click to continue", True, HINT_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(centerx=box_rect.centerx, y=y))
