import pygame

from game import config
from game.missions import PRIMARY_MISSION_NAME, PRIMARY_MISSION_TEXT
from game.ui.text_utils import draw_wrapped_text, wrapped_text_height

# Layout. A card is now a full-width HORIZONTAL bar, stacked with the others
# and expanding its HEIGHT on hover - user: "Aendere das Layout vielleicht noch
# mal, dass die Missionen doch nicht vertikal an der Leiste haengen, sondern
# horizontal uebereinander geschichtet sind. Wenn ich drueber hovere, fahren
# sie aus wie ein Akkordeon-System. So haben wir viel mehr Platz fuer viel mehr
# Secondary-Missionen."
#
# The previous layout was the other axis: tall 150px cards stacked vertically,
# each animating its WIDTH from a 26px sliver out over the board, with its
# title rendered rotated 90 degrees because a sliver is too narrow to read
# horizontally. That does not scale - four cards already took 648px of height,
# and a Secondary hand has no size limit at all.
CARD_WIDTH = 250
BAR_HEIGHT = 28           # a collapsed card: one readable title row
BAR_GAP = 4               # normal gap between two bars
MIN_BAR_OVERLAP_STEP = 12  # shingled: the least of a bar that stays visible when the hand is too tall to lay out flat
BOTTOM_MARGIN = 26        # gap between the lowest bar and the left panel's own bottom edge
TOP_MARGIN = 12           # the stack never grows above this, it shingles instead
CORNER_RADIUS = 8
SLIDE_LERP = 0.25         # per-frame interpolation factor toward the hover target height (0..1)
CARD_PADDING = 12
TITLE_GAP = 4
BODY_GAP = 6
TEXT_REVEAL_MARGIN = 6    # below (bar + this) don't bother rendering the body mid-slide

CARD_BG_COLOR = (14, 20, 30)
CARD_TITLE_COLOR = (255, 215, 0)
CARD_TEXT_COLOR = (205, 230, 248)
CARD_CATEGORY_COLOR = (170, 220, 245)
CARD_SCORE_COLOR = (255, 230, 170)
CARD_READY_COLOR = (140, 245, 160)   # a Secondary whose cash-in prompt is open right now
CARD_TIMING_COLOR = (135, 160, 185)  # muted: WHEN a Secondary is checked, not a claim that it is met
CARD_DETAIL_COLOR = (255, 205, 120)  # a card's WHEN DRAWN choice (which objective, which unit)

# Same fixed per-player identity color as the objective-control markers on the
# board (renderer.py's OBJECTIVE_COLORS) - duplicated here rather than
# imported, matching this codebase's usual per-module small-constant
# convention. Only the card player's own color is needed now: the opponent's
# two cards are gone from this strip entirely (user: "Dort nimmt bitte die
# Mission von Spieler 2 raus. Die brauche ich an der Stelle nicht.").
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

PRIMARY = "Primary"
SECONDARY = "Secondary"


class _MissionCard:
    def __init__(self, player, category, title, text, status=None, status_color=None,
                 detail=None):
        self.player = player       # whose progress this card is about
        self.category = category   # "Primary"/"Secondary"
        self.title = title
        self.text = text
        self.status = status               # right-aligned on the collapsed bar: "12 pts", "READY - 5 VP", or None
        self.status_color = status_color
        # A card's WHEN DRAWN choice, rendered as its own block under the
        # body. Not appended to `text`: wrap_text() splits on spaces, so an
        # embedded newline would not start a new line at all.
        self.detail = detail
        self.height = float(BAR_HEIGHT)    # animated, collapsed by default


class MissionCardsOverlay:
    """The mission strip on the left: the card player's own Primary, then
    every Secondary Mission card currently in their hand.

    Each card is a full-width bar showing its category, name and - the point of
    keeping it visible at all times - its status: the Primary's running score,
    or a highlighted READY marker on a Secondary whose condition is currently
    met. Hovering one animates its height open to reveal the printed text; the
    others stay bars. That is the accordion the user asked for, and unlike the
    old sliver-and-rotated-title layout it stays readable no matter how many
    cards are in hand.

    Anchored bottom-up against the left Actions panel's right border, as
    before. When the hand grows past the available height the bars SHINGLE -
    the gap goes negative and they overlap, each still showing its own title
    row - which is what makes an unbounded hand ("Ich kann so viele secondary
    Missionen auf der Hand haben, wie ich moechte") work without paging.

    Deliberately plain rounded rects, NOT the game's chamfered button_style HUD
    look - the user asked for rounded corners here, a distinct "mission card"
    look.

    DRAW-ONLY, on purpose. These cards sit at x >= left_panel_rect.right, i.e.
    inside board_rect_screen - a click on one falls through main.py's
    state-gated event chain to the board branch. Every choice a card offers
    (cash in, discard for CP) is a DecisionManager prompt instead; see
    game/secondary_missions.py's own docstring.

    GameStatusPanel's Mission Points group remains the always-visible numeric
    summary for BOTH players; this strip is the card player's own detail."""

    def __init__(self):
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1, bold=True)
        self.category_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 5, bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4)
        self.status_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4, bold=True)
        self._cards = []          # rebuilt every frame from live state - see _build_cards()
        self._heights = {}        # card key -> animated height, so it survives the rebuild

    # ------------------------------------------------------------- contents

    def _build_cards(self, player, mission_controller, secondary_controller):
        """One bar per mission actually in play for `player`, built from live
        state rather than from a hard-coded list: the hand changes every round,
        so a fixed card list would go stale the moment a card is drawn or
        discarded."""
        cards = []
        primary_points = 0
        if mission_controller is not None:
            primary_points = mission_controller.primary_points.get(player, 0)
        cards.append(_MissionCard(
            player, PRIMARY, PRIMARY_MISSION_NAME, PRIMARY_MISSION_TEXT,
            status=f"{primary_points} pts", status_color=CARD_SCORE_COLOR,
        ))
        if secondary_controller is None:
            return cards
        # A Secondary's bar shows WHEN it is checked ("end of your turn"), and
        # switches to a highlighted READY only while its cash-in prompt is
        # actually open.
        #
        # It deliberately does NOT show a live "would this score if the turn
        # ended now" snapshot. That was the first version, and it was wrong -
        # user: "mir ist aufgefallen, dass ich gerade Center Ground mitten im
        # Zug schon erfuellt habe... Center Ground wird erst am Ende meines
        # Zuges erfuellt." A card is measured at its own printed instant and at
        # no other, so holding the centre in the Movement phase is a position,
        # not a score, and a bar claiming otherwise invites exactly the move
        # that gives it away before the turn ends.
        offered = secondary_controller.offered_now()
        for card in secondary_controller.hand:
            vp = offered.get(id(card))
            if vp:
                status, color = f"READY - {vp} VP", CARD_READY_COLOR
            else:
                status, color = card.timing_label, CARD_TIMING_COLOR
            # A card whose WHEN DRAWN clause picked something (A Tempting
            # Target's objective) carries that choice as its own block under
            # the body - its printed text says "your tempting target" and never
            # WHICH one, so without this the card cannot be played.
            cards.append(_MissionCard(
                player, SECONDARY, card.name, card.text,
                status=status, status_color=color,
                detail=secondary_controller.detail_for(card),
            ))
        return cards

    @staticmethod
    def _key(index, card):
        # Index included: the same mission can never be in hand twice with the
        # current deck, but keying on the name alone would silently share one
        # animation between duplicates if that ever changed.
        return (index, card.category, card.title)

    # -------------------------------------------------------------- layout

    def _tops(self, left_panel_rect, cards):
        """Top edge per card, laid out BOTTOM-UP from just above the left
        panel's own bottom edge, using each card's CURRENT animated height (an
        expanded card pushes the ones above it up - that is the accordion).

        If the stack would run off the top of the panel the gap goes negative
        and the bars shingle, clamped so each one still shows
        MIN_BAR_OVERLAP_STEP of itself. Only then can the topmost card be
        pushed above TOP_MARGIN, and only for a hand far larger than the screen
        can hold."""
        n = len(cards)
        if n == 0:
            return []
        heights = [max(BAR_HEIGHT, c.height) for c in cards]
        available = left_panel_rect.bottom - BOTTOM_MARGIN - (left_panel_rect.top + TOP_MARGIN)
        total = sum(heights) + BAR_GAP * (n - 1)
        gap = float(BAR_GAP)
        if total > available and n > 1:
            # Distribute the overflow as overlap between consecutive bars.
            gap = (available - sum(heights)) / (n - 1)
            gap = max(gap, MIN_BAR_OVERLAP_STEP - min(heights))
        tops = [0.0] * n
        bottom = float(left_panel_rect.bottom - BOTTOM_MARGIN)
        for i in range(n - 1, -1, -1):
            tops[i] = bottom - heights[i]
            # MINUS: laying out bottom-up, the next card's bottom edge sits a
            # gap ABOVE this one's top. A negative gap is what makes the bars
            # shingle, and getting this sign wrong spreads them apart instead.
            bottom = tops[i] - gap
        return tops

    def _rects(self, left_panel_rect, cards):
        tops = self._tops(left_panel_rect, cards)
        return [
            pygame.Rect(left_panel_rect.right, round(top), CARD_WIDTH,
                        round(max(BAR_HEIGHT, card.height)))
            for card, top in zip(cards, tops)
        ]

    def _full_height(self, card):
        """The height this card wants when expanded - measured from its own
        wrapped text, so a long mission does not get clipped and a short one
        does not leave a hole."""
        text_width = CARD_WIDTH - 2 * CARD_PADDING
        line_height = self.body_font.get_height() + 2
        height = (BAR_HEIGHT + BODY_GAP
                  + wrapped_text_height(self.body_font, card.text, text_width,
                                        line_height=line_height))
        if card.detail:
            height += BODY_GAP + wrapped_text_height(
                self.body_font, card.detail, text_width, line_height=line_height)
        return float(height + CARD_PADDING)

    # ---------------------------------------------------------------- draw

    def draw(self, surface, left_panel_rect, mission_controller=None,
             secondary_controller=None, player=None, mouse_pos=None):
        """`player` defaults to the secondary controller's own player, else to
        the first player configured for the card deck, else Player 1 - so the
        strip always shows somebody's Primary even with the deck switched off
        (as the headless harnesses do)."""
        if player is None:
            if secondary_controller is not None:
                player = secondary_controller.player
            else:
                deck_players = config.SECONDARY_MISSION_CARD_PLAYERS
                player = deck_players[0] if deck_players else "Player 1"

        cards = self._build_cards(player, mission_controller, secondary_controller)
        # Carry each card's animated height across the per-frame rebuild, and
        # drop the entries of cards that have left the hand so the dict cannot
        # grow for the whole battle.
        heights = {}
        for index, card in enumerate(cards):
            key = self._key(index, card)
            card.height = self._heights.get(key, float(BAR_HEIGHT))
            heights[key] = card.height
        self._heights = heights
        self._cards = cards
        if not cards:
            return

        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        rects = self._rects(left_panel_rect, cards)
        # Hit-test against the CURRENT rects, topmost (last drawn) first: when
        # bars shingle they overlap, and the one drawn on top is the one the
        # cursor is actually pointing at.
        hovered_index = None
        for index in range(len(rects) - 1, -1, -1):
            if rects[index].collidepoint(mouse_pos):
                hovered_index = index
                break

        for index, card in enumerate(cards):
            target = self._full_height(card) if index == hovered_index else float(BAR_HEIGHT)
            card.height += (target - card.height) * SLIDE_LERP
            if abs(card.height - target) < 0.5:
                card.height = target  # snap once close enough to stop the float drifting forever
            self._heights[self._key(index, card)] = card.height

        # Re-laid out after the animation step so this frame draws the heights
        # it just computed, and drawn in order so a lower (later) bar overlaps
        # the one above it - which is what makes a shingled stack read as a
        # stack of cards rather than as a broken layout.
        rects = self._rects(left_panel_rect, cards)
        for index, card in enumerate(cards):
            self._draw_card(surface, rects[index], card, index == hovered_index)

    def _draw_card(self, surface, rect, card, hovered):
        accent = PLAYER_ACCENT_COLORS.get(card.player)
        if accent is not None:
            border_color = PLAYER_ACCENT_HOVER_COLORS[card.player] if hovered else accent
        else:
            border_color = DEFAULT_ACCENT_HOVER_COLOR if hovered else DEFAULT_ACCENT_COLOR
        pygame.draw.rect(surface, CARD_BG_COLOR, rect, border_radius=CORNER_RADIUS)
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=CORNER_RADIUS)

        prev_clip = surface.get_clip()
        surface.set_clip(rect)

        text_x = rect.x + CARD_PADDING
        text_width = rect.width - 2 * CARD_PADDING

        # The collapsed bar's one row: category tag, title, and the status on
        # the right. Drawn for every card, expanded or not - it is the row the
        # card is identified by, and it must not jump when the card opens.
        tag = card.category[0].upper()  # "P"/"S" - a full "SECONDARY" would eat the title's room
        tag_surf = self.category_font.render(tag, True, accent or CARD_CATEGORY_COLOR)
        surface.blit(tag_surf, (text_x, rect.y + (BAR_HEIGHT - self.category_font.get_height()) // 2))
        title_x = text_x + tag_surf.get_width() + 6

        status_surf = None
        if card.status:
            status_surf = self.status_font.render(
                card.status, True, card.status_color or CARD_SCORE_COLOR)
        status_width = (status_surf.get_width() + 8) if status_surf is not None else 0
        title_room = max(10, rect.right - CARD_PADDING - status_width - title_x)
        title_surf = self.title_font.render(card.title, True, CARD_TITLE_COLOR)
        if title_surf.get_width() > title_room:
            title_surf = title_surf.subsurface(
                pygame.Rect(0, 0, title_room, title_surf.get_height())).copy()
        surface.blit(title_surf, (title_x, rect.y + (BAR_HEIGHT - title_surf.get_height()) // 2))
        if status_surf is not None:
            surface.blit(status_surf, (
                rect.right - CARD_PADDING - status_surf.get_width(),
                rect.y + (BAR_HEIGHT - status_surf.get_height()) // 2,
            ))

        if rect.height >= BAR_HEIGHT + TEXT_REVEAL_MARGIN:
            # Expanded (or far enough into the slide for the body to be worth
            # rendering): a separator under the bar row, then the printed text.
            body_y = rect.y + BAR_HEIGHT
            pygame.draw.line(surface, border_color,
                             (rect.x + CARD_PADDING, body_y), (rect.right - CARD_PADDING, body_y))
            y = draw_wrapped_text(
                surface, self.body_font, card.text, CARD_TEXT_COLOR,
                text_x, body_y + BODY_GAP, text_width,
                line_height=self.body_font.get_height() + 2,
            )
            if card.detail:
                draw_wrapped_text(
                    surface, self.body_font, card.detail, CARD_DETAIL_COLOR,
                    text_x, y + BODY_GAP, text_width,
                    line_height=self.body_font.get_height() + 2,
                )

        surface.set_clip(prev_clip)
