import pygame

from game import config, loadout, sprites
from game.ui import button_style
from game.ui.text_utils import wrap_text

# Widened from 170: the portrait column has to come out of either the card's
# text width or the number of cards per row, and the text was already being
# clipped at 170. Splitting the cost between the two keeps roughly a screenful
# of cards while leaving the text readable - pagination below is what makes
# spending a little width affordable at all.
CARD_WIDTH = 195
CARD_MARGIN = 10
CARD_TEXT_PADDING = 8
CARD_PORTRAIT_PX = 56     # side of the portrait cell on the left of a card
CARD_PORTRAIT_GAP = 6
LINE_HEIGHT = 20
CARD_SUBTEXT_COLOR = (140, 175, 200)  # dimmer than PANEL_TEXT_COLOR, for the "N model(s)" line

TAB_WIDTH = 130
TAB_GAP = 8

ARROW_WIDTH = 28          # the two pagination buttons, drawn just inside the content row's ends


class ReservesPanel:
    """Bottom strip: units not yet set up on the battlefield (rule 03.02),
    one card per reserve squad. main.py owns the actual drag gesture
    (mouse-down on a card here, mouse-up on the board calls
    SetupController.start_setup()) - this widget only draws the cards and
    answers "which squad is at this position", mirroring how ActionPanel's
    _buttons/handle_click() split works.

    Reserves used to be listed together with "Player 1 - N model(s)"/
    "Player 2 - N model(s)" baked into every card's own text - with both
    players' units mixed into one row, that was the only way to tell them
    apart, but it also meant a card's text load grew with the owner name
    and easily ran past the tile's edge (User report, with a screenshot of
    "Crisis Starscythe Battlesui[...]" clipped mid-word). Now the panel
    shows only ONE player's reserves at a time (self.active_owner) with a
    Player 1/Player 2 tab pair to switch - cards only need the squad's own
    name + model count, and text is wrapped + clipped so it can never run
    outside its tile regardless of how long a unit's name is.

    More cards than fit in one row are PAGED (self.page) with a </> button
    pair, rather than the row silently ending at the panel's right edge as it
    used to - a unit that has no tile is a unit that cannot be picked up at
    all, which is indistinguishable on screen from not having it in reserve.
    Page size is derived from the actual content width rather than fixed, so
    it stays correct in a resized window and after the arrows take their own
    space."""

    def __init__(self):
        self.header_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.tab_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2, bold=True)
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self.active_owner = "Player 1"
        self.page = 0
        self._card_rects = []  # [(rect, squad), ...]
        self._tab_rects = []  # [(rect, owner), ...]
        self._arrow_rects = []  # [(rect, page_delta), ...]

    def draw(self, surface, rect, reserves, dragging_squad=None, visible=True, filter_by_owner=True):
        """`visible` is a TIMING question, not an availability one - decided
        by the caller (main.py: shown during the Movement phase, where both
        Ingress and Disembark can happen, or while a placement is actively
        in progress; hidden in every other phase, e.g. Command, even if
        `reserves` happens to be non-empty).

        `filter_by_owner` is on by default (only `self.active_owner`'s
        squads are shown/dragged) but main.py turns it off for the one case
        where `reserves` has already been narrowed down to a single, very
        specific squad from outside (Rapid Ingress' reactive window, see
        RapidIngressController.pending_squad) - that squad must stay
        visible/draggable no matter which tab happens to be selected."""
        if not visible:
            # Deliberately NOT config.BACKGROUND_COLOR (the board's green) -
            # that made this strip look like more board, which read as the
            # map being covered/extended rather than a separate, currently-
            # inactive area below it. The dark panel color makes the seam
            # between "board" and "this strip" unambiguous.
            surface.fill(config.PANEL_BG_COLOR, rect)
            self._card_rects = []
            self._tab_rects = []
            self._arrow_rects = []
            return

        surface.fill(config.PANEL_BG_COLOR, rect)
        pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, width=2)

        margin = button_style.HEADER_MARGIN
        tabs_width = 2 * TAB_WIDTH + TAB_GAP
        bar_rect = pygame.Rect(
            rect.x + margin, rect.y + margin,
            rect.width - 2 * margin - tabs_width - TAB_GAP, button_style.HEADER_BAR_HEIGHT,
        )

        showable = [
            squad for squad in reserves
            if squad is not dragging_squad and (not filter_by_owner or squad.owner == self.active_owner)
        ]
        content_width = rect.width - 2 * margin
        per_page, pages = self._paging(content_width, len(showable))
        # Clamped on every draw rather than only when the arrows are clicked:
        # the list shrinks under this widget's feet as units are deployed, so
        # the page it is on can stop existing without any click at all.
        self.page = max(0, min(self.page, pages - 1))
        title = "Reserves" if pages <= 1 else f"Reserves - page {self.page + 1}/{pages}"
        button_style.draw_header_bar(surface, bar_rect, title, self.header_font)

        mouse_pos = pygame.mouse.get_pos()
        mouse_down = pygame.mouse.get_pressed()[0]
        self._tab_rects = []
        tab_x = rect.right - margin - tabs_width
        for owner in ("Player 1", "Player 2"):
            tab_rect = pygame.Rect(tab_x, rect.y + margin, TAB_WIDTH, button_style.HEADER_BAR_HEIGHT)
            hovered = tab_rect.collidepoint(mouse_pos)
            active = owner == self.active_owner
            drawn_rect = button_style.draw_button(
                surface, tab_rect, owner, self.tab_font,
                hovered=hovered, pressed=hovered and mouse_down,
                accent="confirm" if active else None,
            )
            self._tab_rects.append((drawn_rect, owner))
            tab_x += TAB_WIDTH + TAB_GAP

        content_rect = pygame.Rect(
            rect.x + margin, bar_rect.bottom + 8,
            rect.width - 2 * margin, rect.bottom - (bar_rect.bottom + 8) - margin,
        )

        self._card_rects = []
        self._arrow_rects = []

        row_rect = content_rect
        if pages > 1:
            for label, delta, at_left in (("<", -1, True), (">", 1, False)):
                arrow_rect = pygame.Rect(
                    content_rect.x if at_left else content_rect.right - ARROW_WIDTH,
                    content_rect.y, ARROW_WIDTH, content_rect.height,
                )
                hovered = arrow_rect.collidepoint(mouse_pos)
                drawn = button_style.draw_button(
                    surface, arrow_rect, label, self.tab_font,
                    hovered=hovered, pressed=hovered and mouse_down,
                )
                self._arrow_rects.append((drawn, delta))
            row_rect = content_rect.inflate(-2 * (ARROW_WIDTH + CARD_MARGIN), 0)

        page_squads = showable[self.page * per_page:(self.page + 1) * per_page]
        card_x = row_rect.x
        for squad in page_squads:
            card_rect = pygame.Rect(card_x, row_rect.y, CARD_WIDTH, row_rect.height)
            self._draw_card(surface, card_rect, squad)
            self._card_rects.append((card_rect, squad))
            card_x += CARD_WIDTH + CARD_MARGIN

        if not showable:
            hint = f"No units in reserve for {self.active_owner}."
            hint_surf = self.font.render(hint, True, CARD_SUBTEXT_COLOR)
            surface.blit(hint_surf, (content_rect.x, content_rect.y))

    @staticmethod
    def _paging(content_width, count):
        """(cards per page, number of pages) for `count` cards in a row this
        wide. The arrows only take their own width off once it is settled that
        there will BE arrows - otherwise a list that fits exactly would lose a
        card to buttons it does not need, and then need them."""
        def fits(width):
            return max(1, (width + CARD_MARGIN) // (CARD_WIDTH + CARD_MARGIN))

        if count <= fits(content_width):
            return max(1, count), 1
        per_page = fits(content_width - 2 * (ARROW_WIDTH + CARD_MARGIN))
        return per_page, max(1, -(-count // per_page))

    def _draw_card(self, surface, card_rect, squad):
        """One reserve tile: portrait on the left, text on the right.

        The portrait is the fastest way to tell two tiles apart - the name
        ("1 Kroot Carnivores 2") and the loadout below it both have to be
        READ, and this strip is where a unit is picked up, both for an Ingress
        move (20.04) and for pre-game deployment (03.01). Everything that does
        not fit is cut off by the clip rather than overflowing the tile."""
        button_style.draw_box(surface, card_rect)

        clip_rect = card_rect.inflate(-4, -4)
        previous_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        text_x = card_rect.x + CARD_TEXT_PADDING
        text_width = card_rect.width - 2 * CARD_TEXT_PADDING
        portrait_paths = sprites.portrait_paths(squad, limit=1)
        if portrait_paths:
            cell = pygame.Rect(
                card_rect.x + CARD_TEXT_PADDING, 0, CARD_PORTRAIT_PX, CARD_PORTRAIT_PX,
            )
            cell.centery = card_rect.centery
            art = sprites.fitted_surface(portrait_paths[0], CARD_PORTRAIT_PX)
            surface.blit(art, art.get_rect(center=cell.center))
            text_x = cell.right + CARD_PORTRAIT_GAP
            text_width = card_rect.right - CARD_TEXT_PADDING - text_x

        text_y = card_rect.y + CARD_TEXT_PADDING
        for line in wrap_text(self.font, squad.name, text_width) or [squad.name]:
            line_surf = self.font.render(line, True, config.PANEL_TEXT_COLOR)
            surface.blit(line_surf, (text_x, text_y))
            text_y += LINE_HEIGHT
        count_surf = self.font.render(f"{len(squad.models)} model(s)", True, CARD_SUBTEXT_COLOR)
        surface.blit(count_surf, (text_x, text_y + 2))
        text_y += LINE_HEIGHT + 2
        # The unit's equipment, so two cards off the same datasheet are
        # distinguishable - a name like "1 Kroot Carnivores 2" says nothing
        # about what it is carrying.
        wrapped_lines = [
            wrapped
            for line in loadout.loadout_lines(squad)
            for wrapped in (wrap_text(self.font, line, text_width) or [line])
        ]
        for wrapped in wrapped_lines:
            # Stop BEFORE a line that would only partly fit: a glyph sliced
            # in half by the clip reads as a rendering bug, whereas a line
            # that simply is not there reads as "the tile is full".
            if text_y + self.font.get_height() > clip_rect.bottom:
                break
            line_surf = self.font.render(wrapped, True, CARD_SUBTEXT_COLOR)
            surface.blit(line_surf, (text_x, text_y))
            text_y += LINE_HEIGHT - 4
        surface.set_clip(previous_clip)

    def handle_click(self, pos):
        """Tab and pagination clicks - returns True if one was hit (so main.py
        knows not to also treat this click as a card pick-up via squad_at())."""
        for tab_rect, owner in self._tab_rects:
            if tab_rect.collidepoint(pos):
                if owner != self.active_owner:
                    # The other player's list is a different length, so the
                    # page number would mean something else there.
                    self.page = 0
                self.active_owner = owner
                return True
        for arrow_rect, delta in self._arrow_rects:
            if arrow_rect.collidepoint(pos):
                # Only floored here; the ceiling is draw()'s job, which is the
                # one place that knows how many pages there currently are.
                self.page = max(0, self.page + delta)
                return True
        return False

    def squad_at(self, pos):
        for rect, squad in self._card_rects:
            if rect.collidepoint(pos):
                return squad
        return None
