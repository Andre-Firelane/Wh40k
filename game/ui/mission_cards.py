import pygame

from game import config
from game.missions import PRIMARY_MISSION_NAME, PRIMARY_MISSION_TEXT
from game.ui.text_utils import draw_wrapped_text, split_paragraphs, wrapped_text_height

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
#
# WIDTH and TEXT SIZE are both up from the first version (250px / FONT_SIZE-4),
# and the info block is laid out in two real columns - user: "auch auf den
# missionskarten. die sind gerade sehr schwer lesbar. die sollten etwas
# aufgeraeumter und besser lesbarer sein."
#
# The measured cause was not the size alone. The info rows were single strings
# with their value pushed across by spaces ("WHEN     end of your turn"), which
# only lines up in a monospace font - and config.FONT_NAME is None, pygame's
# proportional default ("WWWW" 37px, "iiii" 12px). On top of that wrap_text()
# splits on spaces, so the one row long enough to wrap (measured 323px against
# a 226px card) lost its indent entirely and read as a new sentence. Hence
# info_rows(): the label gets its own column and the value wraps inside the
# other one, so a wrapped continuation still lines up under its own value.
#
# Widened again for the SCORING TABLE (user: "vielleicht eine kleine tablle /
# Was | Wann | VP"). Three columns need the room: the WHEN column carries "end
# of your Command phase, round 2 onward", and squeezing that into 150px turned
# every row into four lines.
CARD_WIDTH = 360
BAR_HEIGHT = 30           # a collapsed card: one readable title row
BAR_GAP = 4               # normal gap between two bars
MIN_BAR_OVERLAP_STEP = 12  # shingled: the least of a bar that stays visible when the hand is too tall to lay out flat
BOTTOM_MARGIN = 26        # gap between the lowest bar and the left panel's own bottom edge
TOP_MARGIN = 12           # the stack never grows above this, it shingles instead
CORNER_RADIUS = 8
SLIDE_LERP = 0.25         # per-frame interpolation factor toward the hover target height (0..1)
CARD_PADDING = 12
TITLE_GAP = 4
BODY_GAP = 6
LINE_SPACING = 3          # extra leading inside a wrapped paragraph
INFO_LABEL_WIDTH = 78     # left column of the info block
INFO_COLUMN_GAP = 6
INFO_ROW_GAP = 3
RULE_INSET = 2            # how far a separator line sits inside the padding
# The scoring table: WHAT | WHEN | VP. VP is right-aligned in a fixed column so
# the numbers line up as a column of numbers, which is the point of a table.
SCORE_WHAT_WIDTH = 76
SCORE_VP_WIDTH = 52
SCORE_HEADER_GAP = 3
PARAGRAPH_GAP = 5         # between two sentences of the printed prose
TEXT_REVEAL_MARGIN = 6    # below (bar + this) don't bother rendering the body mid-slide

CARD_BG_COLOR = (14, 20, 30)
CARD_TITLE_COLOR = (255, 215, 0)
CARD_TEXT_COLOR = (205, 230, 248)
CARD_CATEGORY_COLOR = (170, 220, 245)
CARD_SCORE_COLOR = (255, 230, 170)
CARD_READY_COLOR = (140, 245, 160)   # a Secondary whose cash-in prompt is open right now
CARD_TIMING_COLOR = (135, 160, 185)  # muted: WHEN a Secondary is checked, not a claim that it is met
CARD_DETAIL_COLOR = (255, 205, 120)  # a card's WHEN DRAWN choice (which objective, which unit)
CARD_INFO_COLOR = (150, 195, 225)    # the facts the printed prose does not carry - timing, action, draw clause
CARD_INFO_LABEL_COLOR = (120, 155, 185)  # the label column, one step back from its own value
TITLE_RULE_COLOR = (52, 70, 90)      # hairline between the metadata, the printed text, and the detail

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
                 detail=None, info=(), scoring=()):
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
        # (LABEL, value) rows shown above the body - see
        # SecondaryMissionCard.info_rows(). The timing is the one that was
        # genuinely missing: it lives on the collapsed bar, so opening a card
        # used to HIDE it.
        self.info = [tuple(row) for row in info]
        # (WHAT, WHEN, VP) triples - the little rate card. Its own list rather
        # than three-column `info` rows, because these are a different KIND of
        # row: `info` is one-off facts about the card, this repeats per scoring
        # box and is the only place the VP appear outside the prose.
        self.scoring = [tuple(row) for row in scoring]
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
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3)
        self.info_label_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 5, bold=True)
        self.status_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4, bold=True)
        self._cards = []          # rebuilt every frame from live state - see _build_cards()
        self._heights = {}        # card key -> animated height, so it survives the rebuild
        self._last_content_bottom = None  # y the last expanded card's content really reached

    # ------------------------------------------------------------- contents

    def _build_cards(self, player, mission_controller, secondary_controller,
                     primary_controller=None):
        """One bar per mission actually in play for `player`, built from live
        state rather than from a hard-coded list: the hand changes every round,
        so a fixed card list would go stale the moment a card is drawn or
        discarded."""
        cards = []
        primary_points = 0
        if mission_controller is not None:
            primary_points = mission_controller.primary_points.get(player, 0)
        # WHICH Primary is on the strip depends on the player: whoever runs a
        # Force Disposition Primary (config.PRIMARY_MISSION_CARD_PLAYERS) sees
        # that card, everyone else still sees "Hold the Line". Read off the
        # controller rather than off the module constants, because the answer
        # is a property of the army list and changes with it.
        #
        # A Primary bar carries the same detail line and info rows a Secondary
        # does. It needs them more, in fact: its several boxes each have their
        # own instant and round band, and none of that survives into the
        # paragraph of prose below.
        #
        # `primary_controller.player == player` is not belt and braces: the
        # strip's own `player` falls back through the Secondary deck and then
        # through config, so the two CAN differ - and showing one player's
        # mission under the other's heading is worse than showing none.
        owns_it = (primary_controller is not None
                   and primary_controller.player == player
                   and primary_controller.plays_card)
        mission = primary_controller.mission if owns_it else None
        if owns_it and mission:
            cards.append(_MissionCard(
                player, PRIMARY, mission.name, mission.text,
                status=f"{primary_points} pts", status_color=CARD_SCORE_COLOR,
                detail=primary_controller.detail(),
                info=mission.info_rows(),
                scoring=mission.scoring_rows(),
            ))
        else:
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
                info=card.info_rows(),
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

    def _line_height(self):
        """Leading inside a wrapped paragraph. Up from +2 to +LINE_SPACING:
        the body font grew, and tightly-set small text over a dark card is
        most of what "schwer lesbar" describes."""
        return self.body_font.get_height() + LINE_SPACING

    def _info_value_width(self):
        return CARD_WIDTH - 2 * CARD_PADDING - INFO_LABEL_WIDTH - INFO_COLUMN_GAP

    def _info_height(self, card):
        """Height of the two-column info block, measured against the SAME
        wrapping _draw_info() uses - a value that needs two lines has to push
        the body down, not be drawn over it."""
        if not card.info:
            return 0
        line_height = self._line_height()
        height = 0
        for label, value in card.info:
            rows = max(
                wrapped_text_height(self.body_font, value, self._info_value_width(),
                                    line_height=line_height),
                line_height,
            )
            height += rows + INFO_ROW_GAP
        return height

    def _score_when_width(self):
        return (CARD_WIDTH - 2 * CARD_PADDING - SCORE_WHAT_WIDTH - SCORE_VP_WIDTH
                - 2 * INFO_COLUMN_GAP)

    def _scoring_height(self, card):
        """Height of the WHAT | WHEN | VP table, measured against the SAME
        wrapping _draw_scoring() uses - the WHEN cell is the one that wraps, and
        a row measured as one line while it draws three overruns everything
        below it."""
        if not card.scoring:
            return 0
        line_height = self._line_height()
        height = self.info_label_font.get_height() + SCORE_HEADER_GAP
        for _what, when, _vp in card.scoring:
            height += max(
                wrapped_text_height(self.body_font, when, self._score_when_width(),
                                    line_height=line_height),
                line_height,
            ) + INFO_ROW_GAP
        return height

    def _paragraphs(self, card):
        """The printed text as separate sentences. LOSSLESS - see
        text_utils.split_paragraphs(); not one word changes, they are only set
        as separate blocks so the scoring clauses can be told apart."""
        return split_paragraphs(card.text)

    def _prose_height(self, card):
        text_width = CARD_WIDTH - 2 * CARD_PADDING
        line_height = self._line_height()
        paragraphs = self._paragraphs(card)
        height = sum(wrapped_text_height(self.body_font, p, text_width,
                                         line_height=line_height)
                     for p in paragraphs)
        return height + PARAGRAPH_GAP * max(0, len(paragraphs) - 1)

    def _full_height(self, card):
        """The height this card wants when expanded - measured from its own
        wrapped text, so a long mission does not get clipped and a short one
        does not leave a hole."""
        text_width = CARD_WIDTH - 2 * CARD_PADDING
        line_height = self._line_height()
        height = BAR_HEIGHT + BODY_GAP
        # Both blocks end with a trailing INFO_ROW_GAP inside their own height,
        # and the drawing spends it as part of the run-up to the separator rule
        # (`y += BODY_GAP - INFO_ROW_GAP`, then the rule, then BODY_GAP). Adding
        # two full BODY_GAPs here instead double-counted it and left the card
        # 3px too tall per block - harmless on screen, but it means the
        # prediction and the drawing disagree, and that is the one thing this
        # layout cannot afford (see _last_content_bottom).
        block_gap = BODY_GAP + BODY_GAP - INFO_ROW_GAP
        if card.info:
            # info block, then a separator rule
            height += self._info_height(card) + block_gap
        if card.scoring:
            # scoring table, then a separator rule before the printed prose
            height += self._scoring_height(card) + block_gap
        height += self._prose_height(card)
        if card.detail:
            height += BODY_GAP + BODY_GAP + wrapped_text_height(
                self.body_font, card.detail, text_width, line_height=line_height)
        return float(height + CARD_PADDING)

    # ---------------------------------------------------------------- draw

    def draw(self, surface, left_panel_rect, mission_controller=None,
             secondary_controller=None, player=None, mouse_pos=None,
             primary_controller=None):
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

        cards = self._build_cards(player, mission_controller, secondary_controller,
                                  primary_controller)
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
            line_height = self._line_height()
            y = body_y + BODY_GAP
            if card.info:
                y = self._draw_info(surface, rect, text_x, y, card, line_height)
                # A rule between the metadata and the PRINTED text. Without it
                # the two run together as one block of prose, which is what
                # made the card hard to skim: a player looking for "when does
                # this score" had to read the mission text to find out where
                # the answer stopped.
                y += BODY_GAP - INFO_ROW_GAP
                pygame.draw.line(
                    surface, TITLE_RULE_COLOR,
                    (rect.x + CARD_PADDING + RULE_INSET, y),
                    (rect.right - CARD_PADDING - RULE_INSET, y))
                y += BODY_GAP
            if card.scoring:
                y = self._draw_scoring(surface, rect, text_x, y, card, line_height)
                y += BODY_GAP - INFO_ROW_GAP
                pygame.draw.line(
                    surface, TITLE_RULE_COLOR,
                    (rect.x + CARD_PADDING + RULE_INSET, y),
                    (rect.right - CARD_PADDING - RULE_INSET, y))
                y += BODY_GAP
            # The printed text, one block per sentence. Same words, set apart -
            # user: "so im fliesstext ist die information sehr unuebersichtlich".
            for index, paragraph in enumerate(self._paragraphs(card)):
                if index:
                    y += PARAGRAPH_GAP
                y = draw_wrapped_text(
                    surface, self.body_font, paragraph, CARD_TEXT_COLOR,
                    text_x, y, text_width, line_height=line_height,
                )
            if card.detail:
                y += BODY_GAP
                pygame.draw.line(
                    surface, TITLE_RULE_COLOR,
                    (rect.x + CARD_PADDING + RULE_INSET, y),
                    (rect.right - CARD_PADDING - RULE_INSET, y))
                y = draw_wrapped_text(
                    surface, self.body_font, card.detail, CARD_DETAIL_COLOR,
                    text_x, y + BODY_GAP, text_width, line_height=line_height,
                )
            # Where the content actually ended. _full_height() predicts this
            # BEFORE drawing, and if the two disagree the card silently clips
            # its own last line - the failure this layout is most exposed to,
            # because a wrapped info value changes the height of everything
            # below it. Recorded rather than recomputed so a test can compare
            # the prediction against the drawing.
            self._last_content_bottom = y

        surface.set_clip(prev_clip)

    def _draw_info(self, surface, rect, text_x, y, card, line_height):
        """The metadata block as two real columns: LABEL on the left, value
        wrapped in its own column on the right.

        This replaces space-padded single strings, which never lined up (the
        default font is proportional) and whose one long row lost its indent
        entirely when it wrapped. Now a wrapped continuation stays inside the
        value column, so the block reads as a table."""
        value_x = text_x + INFO_LABEL_WIDTH + INFO_COLUMN_GAP
        value_width = self._info_value_width()
        for label, value in card.info:
            label_surf = self.info_label_font.render(label, True, CARD_INFO_LABEL_COLOR)
            # Baselines: the label font is smaller than the value font, so it
            # is nudged down to sit on the value's first line rather than
            # floating above it.
            surface.blit(label_surf, (
                text_x, y + max(0, (self.body_font.get_height()
                                    - self.info_label_font.get_height()) // 2)))
            end_y = draw_wrapped_text(
                surface, self.body_font, value, CARD_INFO_COLOR,
                value_x, y, value_width, line_height=line_height,
            )
            y = max(end_y, y + line_height) + INFO_ROW_GAP
        return y

    def _draw_scoring(self, surface, rect, text_x, y, card, line_height):
        """The WHAT | WHEN | VP table, with a header row.

        The header is what makes it read as a table rather than as three more
        metadata rows - and the VP column is right-aligned in a fixed column so
        the numbers form a column of numbers, which is the entire reason for
        pulling them out of the prose."""
        when_x = text_x + SCORE_WHAT_WIDTH + INFO_COLUMN_GAP
        vp_right = rect.right - CARD_PADDING

        for label, x in (("WHAT", text_x), ("WHEN", when_x)):
            surface.blit(self.info_label_font.render(label, True, CARD_INFO_LABEL_COLOR), (x, y))
        vp_head = self.info_label_font.render("VP", True, CARD_INFO_LABEL_COLOR)
        surface.blit(vp_head, (vp_right - vp_head.get_width(), y))
        y += self.info_label_font.get_height() + SCORE_HEADER_GAP
        pygame.draw.line(surface, TITLE_RULE_COLOR,
                         (text_x, y - 2), (vp_right, y - 2))

        for what, when, vp in card.scoring:
            what_surf = self.body_font.render(what, True, CARD_INFO_COLOR)
            surface.blit(what_surf, (text_x, y))
            end_y = draw_wrapped_text(
                surface, self.body_font, when, CARD_TIMING_COLOR,
                when_x, y, self._score_when_width(), line_height=line_height,
            )
            vp_surf = self.body_font.render(vp, True, CARD_SCORE_COLOR)
            surface.blit(vp_surf, (vp_right - vp_surf.get_width(), y))
            y = max(end_y, y + line_height) + INFO_ROW_GAP
        return y
