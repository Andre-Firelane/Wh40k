import pygame

from game import config, sprites
from game.turn import PHASES
from game.ui import button_style, faction_badge
from game.ui.text_utils import draw_wrapped_text, wrap_text, wrapped_text_height

ROW_HEIGHT = 24
CP_TEXT_COLOR = (150, 190, 255)
MISSION_TEXT_COLOR = (255, 210, 130)
BATTLE_FOCUS_TEXT_COLOR = (170, 235, 210)  # its own tint so CP/VP/BF stay tellable apart at a glance
BUTTON_HEIGHT = 34
BUTTON_MARGIN = 10
SECTION_GAP = 14         # vertical gap between the bordered content groups
BOX_INNER_PADDING = 8    # padding between a group's border and its own text

# --- faction badge row (top group) ---
#: px, the square tile one faction badge is drawn in.
#:
#: 58 -> 72 on user request ("mach die faction logos ingame in der rechten
#: spalte etwas groesser"). What made the room was the ROUND COUNTER leaving:
#: the two tiles hug the content edges and the bar between them used to fill
#: the middle, so after it moved to the top progress bar there were 84px of
#: dead space there. 72 leaves 56 of them, which still reads as two tiles
#: rather than one pair, and grows the artwork inside from a 50px square to a
#: 64px one (LOGO_BOX - 2 * LOGO_PADDING).
#:
#: THE CEILING IS THE TURN BANNER, not this column: turn_start_overlay's
#: BADGE_BOX (76) is deliberately the bigger of the two - it is a screen-centre
#: showcase with 460px to spend, where this is a reference tile in a 200px
#: column - and test_turn_start_overlay.py pins that ordering. Everything else
#: this touches was measured and has room: the two "see rules" links get
#: WIDER (they are centred under their own tile, see ARMY_RULES_LINK_SHORT_TEXT
#: below), and the 14px the group grows costs the log strip nothing on a 1080
#: screen and leaves it 212px on a 720 one.
LOGO_BOX = 72
LOGO_GAP = 6             # px between a tile and the Round bar sitting between the two
NAME_ROW_HEIGHT = 20     # px reserved for the "P1: AELDARI" line under the tiles
LABEL_MIN_GAP = 10       # px the two labels must keep between them, or the "P1: " prefixes are dropped (see _badge_labels)
# What a faction tile LOOKS like moved to game/ui/faction_badge.py when the
# turn-start banner became its second consumer. Re-exported rather than
# imported at each use site, so every reader of this module - the tests
# included - keeps the names it already had and this panel's pixels are
# unchanged by construction.
LOGO_PADDING = faction_badge.LOGO_PADDING
ACTIVE_BORDER_WIDTH = faction_badge.ACTIVE_BORDER_WIDTH
ACTIVE_GLOW_COLOR = faction_badge.ACTIVE_GLOW_COLOR
MONOGRAM_LENGTH = faction_badge.MONOGRAM_LENGTH
MONOGRAM_COLOR = faction_badge.MONOGRAM_COLOR
MONOGRAM_FONT_SIZES = faction_badge.MONOGRAM_FONT_SIZES

# The "see army rules" link under the badge labels. User: "es fehlt noch ein
# ort, wo man armeeregel und detachment regeln anschauen kann... dort soll
# irgendwo ein kleiner link sein 'see army rules' unter den logos und
# volkernamen."
#
# Drawn as a LINK - small, underlined, in the panel's accent - rather than as a
# button_style button, and that is the point of the wording: a button in this
# column spends something or advances the game ("Next Phase"), while this only
# opens a reader. Making it look like the End Turn button would say it costs
# something.
ARMY_RULES_LINK_TEXT = "see rules"
#: The fallback when a link will not fit under its own badge tile.
#:
#: MEASURED, and the binding constraint is the CENTRING, not the total width:
#: each link is centred under a LOGO_BOX tile whose centre sits LOGO_BOX/2 =
#: 36px from the panel's content edge, so a link may be at most 72px wide
#: including its click padding. The old "see army rules" is 75px + 8px of pad
#: = 83px, which hangs 6px off each side of the panel. "see rules" is 47 + 8
#: = 55px and fits with 17px to spare. Two of the old label WOULD have packed
#: side by side (166px inside a 200px column) - it is where they have to SIT
#: that rules them out.
#:
#: The numbers moved when LOGO_BOX grew from 58 to 72 and the room went UP,
#: not down - a wider tile pushes its own link's centre further from the panel
#: edge. The long label still does not fit (83 > 72), so the wording this
#: constant exists for is unchanged; only the margin it wins by is.
ARMY_RULES_LINK_SHORT_TEXT = "rules"
ARMY_RULES_LINK_COLOR = (130, 190, 235)
ARMY_RULES_LINK_HOVER_COLOR = (190, 230, 255)
ARMY_RULES_LINK_HEIGHT = 18   # px reserved for the link row under the labels
ARMY_RULES_LINK_PAD = 4       # px of slack around the text for an easier click target


#: The placeholder tile's text. Re-exported (not re-implemented) so this
#: module and the banner cannot disagree about what a faction is called when
#: its art is missing.
_faction_monogram = faction_badge.monogram


class GameStatusPanel:
    """Right panel: overview of the game's overall state - battle round,
    current phase, whose turn it is, each player's Command Points, each
    player's mission points (Primary/Secondary/Total - see game/missions.py),
    and the Next Phase/End Turn button (moved here from the old top banner,
    which now only shows the Regaining Coherency warning - see
    PlayerBanner). The old hover-info content (a model's stats/weapons)
    moved to UnitDatacardOverlay (Ctrl+hover), since that's a per-model
    lookup rather than always-visible game state."""

    def __init__(self):
        self.header_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.label_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2, bold=True)
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        self.button_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1, bold=True)
        self.badge_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4, bold=True)
        self._button_rect = None
        self._army_rules_rects = []   # [(player, rect)] from the last frame
        # The same typesetting the army rules reader and the stratagem tooltip
        self.link_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4)

    @property
    def button_rect(self):
        """Where the Next Phase/End Turn button was drawn last frame, or None
        before the first draw. The panel lays out top-down and the button
        follows its content, so this is the only honest answer to "how much of
        the right column does this panel actually need?" - main() reads it to
        keep the log strip below it (see config.LOG_HEIGHT)."""
        return self._button_rect

    @property
    def army_rules_rects(self):
        """[(player, rect)] for the rules links drawn last frame, [] when none
        were. They hang off the badge row, so a game with no badges (a
        hand-built squad with no datasheet) has no links either - there would
        be no faction to look rules up for."""
        return list(self._army_rules_rects)

    def army_rules_player_at(self, pos):
        """WHICH player's rules link `pos` hit, or None.

        Renamed from handle_army_rules_click(), which returned a bool: with
        one link per player the answer is no longer yes/no, and keeping the
        old name while changing what the value MEANS is the silent drift this
        repo renames to avoid (error class 11).

        Still a method of its own rather than a second return value from
        handle_click(): the two answers mean completely different things to
        main(), and a caller that conflated them would advance the phase when
        the player asked to read a rule."""
        for player, rect in self._army_rules_rects:
            if rect.collidepoint(pos):
                return player
        return None

    def _link_text(self, half_width):
        """The link label, shortened if it would hang off the panel.

        `half_width` is how far a link may reach either side of its tile's
        centre - LOGO_BOX/2, since the tiles hug the content edges. Same
        degrade-on-measurement shape as _badge_labels() above, and measured
        for the same reason: the label that fits one centred link does not
        necessarily fit one centred under each tile."""
        for text in (ARMY_RULES_LINK_TEXT, ARMY_RULES_LINK_SHORT_TEXT):
            if self.link_font.size(text)[0] + 2 * ARMY_RULES_LINK_PAD <= 2 * half_width:
                return text
        return ARMY_RULES_LINK_SHORT_TEXT

    def _status_lines(self, turn_tracker, badges):
        """The plain text rows at the bottom of the first group.

        The "Active Player" row is dropped when badges are being drawn: the
        highlighted frame around one of them says exactly the same thing,
        and replacing that line was the point of the change. Without badges
        it stays, because nothing else would be saying it."""
        lines = [f"{turn_tracker.phase} Phase"]
        if badges is None:
            lines.append(f"Active Player: {turn_tracker.active_player}")
        return lines

    def _score_columns(self, badges, command_points, mission_controller, battle_focus_pool=None):
        """The per-player score rows for the compact two-column layout:
        [(player, [(text, color), ...]), ...] left to right.

        User request: "die Command Points und Mission Points koennten auch
        nebeneinander in den Spalten stehen / abgekuerzt zu CP: 1 / VP: 24" -
        so each player gets a short column under their own badge instead of
        two full-width groups that repeat both player names. Only reachable
        WITH badges, because the badge above a column is what says whose
        column it is; without them the panel keeps the old labelled rows.

        Note this drops the Primary/Secondary split the long form spells out
        ("24 pts (P 12 / S 12)") - the totals are what the abbreviation asked
        for. The split is still one row away if it turns out to be missed.

        Battle Focus tokens (the Aeldari army rule) join the same column as a
        third row - user: "Battle FOcus kann auch mit in die CP/VP spalte /
        mit BF abkuerzen". Only for a player the pool actually names, so an
        Ork column does not grow an empty "BF: 0" row next to an Aeldari one,
        and a battle with no ASURYANI army has no such row at all."""
        columns = []
        for player, _, _ in badges:
            rows = []
            if command_points is not None:
                rows.append((f"CP: {command_points.cp.get(player, 0)}", CP_TEXT_COLOR))
            if mission_controller is not None and player in mission_controller.primary_points:
                rows.append((f"VP: {mission_controller.total_points(player)}", MISSION_TEXT_COLOR))
            if battle_focus_pool is not None and player in battle_focus_pool.players:
                rows.append((f"BF: {battle_focus_pool.tokens.get(player, 0)}",
                             BATTLE_FOCUS_TEXT_COLOR))
            columns.append((player, rows))
        return columns if any(rows for _, rows in columns) else []

    def _badge_row(self, turn_tracker, player_factions):
        """The two players' faction badges, left to right, or None when this
        game can't show them.

        Returns [(player, faction_keyword, logo_path_or_None), ...] in a
        stable player order, and only when every player's FACTION IS KNOWN -
        the art is optional, and a player whose faction has no logo file gets
        a monogram tile instead (see _draw_badge / _faction_monogram).

        This gate used to require ART for both players, and that turned out
        to be the wrong all-or-nothing: user, seeing the panel during an
        Aeldari-vs-Death-Guard game ("das rechte panel sieht wieder
        zurueckgesetzt aus. das hatten wir mal ueberarbeitet ua. mit logos
        der fraktionen"). Death Guard is the one built faction with no badge
        file, so ONE missing image collapsed the whole group back to its
        pre-rework text form - and with it the gold active-player frame and
        the compact CP/VP/BF columns, which have nothing to do with logos.
        The old reasoning ("a half-filled row reads worse than the line it
        replaced") was about an EMPTY tile; a monogram tile is neither empty
        nor half-drawn, so it is not the trade that argument weighed.

        A missing KEYWORD still falls the group back to text, and for the
        same reason it always did: without one there is nothing to draw AND
        nothing to write, so the tile really would be empty. That is the case
        for a hand-built Squad with no datasheet (see faction_keyword_of).

        Player order comes from turn_tracker.player_turn_count rather than
        from `player_factions`: the tracker holds both player names for the
        whole battle in a fixed order, while the faction mapping is derived
        from whatever units exist and would put whoever was found first on
        the left."""
        if not player_factions:
            return None
        players = sorted(turn_tracker.player_turn_count)
        row = []
        for player in players:
            keyword = player_factions.get(player)
            if keyword is None:
                return None
            row.append((player, keyword, sprites.faction_logo_path(keyword)))
        return row or None

    def _badge_labels(self, row, available_width):
        """Text under the tiles, one label per player.

        Prefers "P1: AELDARI" and drops the "P1: " prefix when the two labels
        would not fit side by side with a clear gap between them (two T'AU
        EMPIRE armies is the case that runs out of room). Dropping it costs
        little: which side a player is on, plus the highlighted frame and
        the gold label on the active one, already say who is who."""
        prefixed = []
        for index, (player, keyword, _) in enumerate(row):
            short = f"P{index + 1}" if player.startswith("Player ") else player
            prefixed.append(f"{short}: {keyword}")
        if sum(self.badge_font.size(text)[0] for text in prefixed) <= available_width - LABEL_MIN_GAP:
            return prefixed
        return [keyword for _, keyword, _ in row]

    def _monogram_font(self, text, box_px):
        """Kept as a method because the panel's own tests drive it; the search
        and its cache live in game/ui/faction_badge.py, which is the one place
        that decides how a tile is lettered."""
        return faction_badge.font_for(text, box_px)

    def _draw_badge(self, surface, tile_rect, logo_path, active, keyword=None):
        """One faction badge - see game/ui/faction_badge.draw().

        Whose frame lights up is turn_tracker.active_player, exactly the value
        the replaced "(Active)" line showed - the transient "whose decision is
        this right now" flag, NOT turn_owner (see game/turn.py). It flipping
        mid-turn onto the defender during a save roll is the intended reading
        here: this marks who the game is waiting on. The turn-start banner
        passes a different answer to the same flag, which is why the shared
        function takes it rather than working it out."""
        faction_badge.draw(surface, tile_rect, logo_path, active, keyword)

    def draw(self, surface, rect, turn_tracker, command_points=None, mission_controller=None,
             battle_focus_pool=None, fate_dice_pool=None, player_factions=None):
        surface.fill(config.PANEL_BG_COLOR, rect)
        pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, width=2)

        # The MENU button shares this header row, at its right end (user:
        # "ausserdem haette ich den 'Menu' Knopf gerne oben rechts in der
        # rechten spalte neben der Game Status ueberschrift"). The bar is
        # SHORTENED by exactly the room that button takes, and both halves of
        # that arithmetic live in button_style - this panel only says that the
        # room is reserved, it does not work out how much.
        button_style.draw_panel_header(surface, rect, "Game Status", self.header_font,
                                       reserve_right=button_style.header_button_reserve())

        content_x = rect.x + 10
        content_width = rect.width - 20
        y = rect.y + 50

        # User feedback ("es sieht noch etwas dröge aus... Trennlinien,
        # Umrandungen, Turncounter mit Balken hinterlegen wie Überschrift"):
        # a thin separator line under the "Game Status" title bar, each
        # content group wrapped in its own bordered/chamfered box (same
        # button_style.draw_box() language as every other box in this game -
        # message boxes, log entries, etc.), and the Round counter gets a
        # colored bar behind it exactly like a header (draw_header_bar,
        # same look as the "Game Status" title itself) instead of being
        # plain text. A box's exact height depends on what's drawn inside
        # it, so each group is laid out top-down first (nothing blitted
        # yet) and only then wrapped in a box - same "measure, then draw
        # the frame, then draw the content on top" order as DicePanel's
        # backdrop.
        pygame.draw.line(surface, config.PANEL_BORDER_COLOR, (rect.x, y), (rect.right, y), width=2)
        y += SECTION_GAP

        # --- Group 1: who is playing (faction badges) / Round / Phase ---
        # User request, with a layout sketch: one faction badge per player
        # with the Round counter between them, and the active player picked
        # out by a highlighted frame around their badge instead of an
        # "(Active)" line underneath. The Round counter keeps the colored
        # bar behind it that earlier feedback asked for ("Turncounter mit
        # Balken hinterlegen wie Überschrift") - it just moves into the gap
        # between the badges and centers its text there, rather than
        # spanning the panel.
        #
        # Same "lay the group out top-down first, then wrap it in a box, then
        # blit the content on top" order as every other group here, because
        # draw_box() fills and a box measured after the fact would paint over
        # what it is framing.
        badges = self._badge_row(turn_tracker, player_factions)
        group_top = y
        badge_positions = []
        label_positions = []

        if badges is not None:
            tile_y = y
            left_tile = pygame.Rect(content_x, tile_y, LOGO_BOX, LOGO_BOX)
            right_tile = pygame.Rect(content_x + content_width - LOGO_BOX, tile_y, LOGO_BOX, LOGO_BOX)
            y = tile_y + LOGO_BOX + 4

            labels = self._badge_labels(badges, content_width)
            for tile, (player, keyword, path), label in zip((left_tile, right_tile), badges, labels):
                active = player == turn_tracker.active_player
                badge_positions.append((tile, path, active, keyword))
                text_surf = self.badge_font.render(
                    label, True,
                    config.PANEL_HEADER_COLOR if active else config.PANEL_TEXT_COLOR,
                )
                # Each label hugs the outer edge under its own tile, so the
                # two grow toward the middle and meet there in the worst case
                # instead of overrunning the panel.
                if tile is left_tile:
                    label_positions.append((text_surf, (content_x, y)))
                else:
                    label_positions.append((text_surf, (content_x + content_width - text_surf.get_width(), y)))
            y += NAME_ROW_HEIGHT
            # ONE LINK PER PLAYER, each centred under its OWN badge, because
            # each now opens only that player's rules. User: "außerdem sollten
            # dort 2 links sein einer für Spieler 1 und einer für Spieler 2".
            #
            # The label had to shorten to fit: two "see army rules" (75px
            # each) plus their padding overrun the 220px panel by 3px, and
            # they would collide long before that on a narrower one. The badge
            # above already says which player it is, so the link does not
            # repeat it. Laid out here with the rest of the group so the box
            # below grows to include it.
            self._army_rules_rects = []
            link_text = self._link_text(LOGO_BOX / 2)
            link_surf = self.link_font.render(link_text, True, ARMY_RULES_LINK_COLOR)
            for tile, (player, _keyword, _path) in zip((left_tile, right_tile), badges):
                link_rect = link_surf.get_rect(centerx=tile.centerx, y=y)
                self._army_rules_rects.append(
                    (player, link_rect.inflate(2 * ARMY_RULES_LINK_PAD,
                                               2 * ARMY_RULES_LINK_PAD)))
            y += ARMY_RULES_LINK_HEIGHT
        else:
            # No badge art for both players: fall back to the plain
            # "Active Player" line, which is what this group was before.
            # No link either - without a faction there is nothing to look up.
            self._army_rules_rects = []

        line_positions = []
        for line in self._status_lines(turn_tracker, badges):
            line_positions.append((line, (content_x, y)))
            y += ROW_HEIGHT

        group1_box = pygame.Rect(
            rect.x + 6, group_top - BOX_INNER_PADDING,
            rect.width - 12, (y - group_top) + BOX_INNER_PADDING,
        )
        button_style.draw_box(surface, group1_box)
        # THE ROUND NUMBER IS NOT DRAWN HERE ANY MORE. User: "fuer die Anzeige
        # der aktuellen runde haette ich gerne anstatt der Zahl einen schoenen
        # Fortschrittsbalken am oberen Bildschirmrand" - see
        # game/ui/round_progress_bar.py, which says the round, whose turn it is
        # and how far the battle has got, all at once. What stood here was a
        # header bar reading "ROUND 3", squeezed into the gap between the two
        # badge tiles; with its text gone it would have been an empty frame,
        # so the bar went with the number rather than being left to say
        # nothing. The phase row below is untouched.
        for tile, path, active, keyword in badge_positions:
            self._draw_badge(surface, tile, path, active, keyword)
        for text_surf, pos in label_positions:
            surface.blit(text_surf, pos)
        if self._army_rules_rects:
            # Underlined and brightening on hover - the two things that say
            # "this is clickable" without borrowing the button look.
            mouse_pos = pygame.mouse.get_pos()
            link_text = self._link_text(LOGO_BOX / 2)
            for _player, link_rect in self._army_rules_rects:
                hovered = link_rect.collidepoint(mouse_pos)
                color = ARMY_RULES_LINK_HOVER_COLOR if hovered else ARMY_RULES_LINK_COLOR
                link_surf = self.link_font.render(link_text, True, color)
                link_pos = link_surf.get_rect(
                    centerx=link_rect.centerx, y=link_rect.y + ARMY_RULES_LINK_PAD)
                surface.blit(link_surf, link_pos)
                pygame.draw.line(surface, color, (link_pos.x, link_pos.bottom),
                                 (link_pos.right, link_pos.bottom))
        for line, pos in line_positions:
            line_surf = self.font.render(line, True, config.PANEL_TEXT_COLOR)
            surface.blit(line_surf, pos)
        y += SECTION_GAP

        # --- Group 2: Command Points / Mission Points ---
        # With badges these two collapse into one box of per-player columns
        # sitting under the badge that names each column (user request); the
        # long, labelled form below is what a game without badges still gets.
        score_columns = (
            self._score_columns(badges, command_points, mission_controller, battle_focus_pool)
            if badges is not None else []
        )
        if score_columns:
            group_top = y
            column_rows = []
            row_count = max(len(rows) for _, rows in score_columns)
            for index, (player, rows) in enumerate(score_columns):
                for row_index, (text, color) in enumerate(rows):
                    text_surf = self.font.render(text, True, color)
                    row_y = y + row_index * ROW_HEIGHT
                    if index == 0:
                        column_rows.append((text_surf, (content_x, row_y)))
                    else:
                        column_rows.append((text_surf, (content_x + content_width - text_surf.get_width(), row_y)))
            y += row_count * ROW_HEIGHT

            scores_box = pygame.Rect(
                rect.x + 6, group_top - BOX_INNER_PADDING,
                rect.width - 12, (y - group_top) + BOX_INNER_PADDING,
            )
            button_style.draw_box(surface, scores_box)
            for text_surf, pos in column_rows:
                surface.blit(text_surf, pos)
            y += SECTION_GAP

        if command_points is not None and not score_columns:
            group_top = y
            label_pos = (content_x, y)
            y += ROW_HEIGHT
            cp_line = "  |  ".join(f"{player}: {cp}" for player, cp in command_points.cp.items())
            cp_pos = (content_x, y)
            y += ROW_HEIGHT

            group2_box = pygame.Rect(
                rect.x + 6, group_top - BOX_INNER_PADDING,
                rect.width - 12, (y - group_top) + BOX_INNER_PADDING,
            )
            button_style.draw_box(surface, group2_box)
            label_surf = self.label_font.render("Command Points:", True, config.PANEL_TEXT_COLOR)
            surface.blit(label_surf, label_pos)
            cp_surf = self.font.render(cp_line, True, CP_TEXT_COLOR)
            surface.blit(cp_surf, cp_pos)
            y += SECTION_GAP

        # --- Group 2b: Battle Focus tokens (Aeldari army rule) ---
        # Drawn only when an ASURYANI army is actually in the battle, so this
        # is invisible in every game without one rather than a permanent
        # "0 tokens" row. The pool leaves `players` empty until it finds one
        # (see game/battle_focus.py's qualifying_players()), which makes that
        # the same question as "does this rule apply at all".
        #
        # This is the LONG form, for a game without faction badges. With them
        # the tokens are a "BF: n" row inside that player's own score column
        # instead (see _score_columns) - drawing both would say it twice.
        if battle_focus_pool is not None and battle_focus_pool.players and not score_columns:
            group_top = y
            label_pos = (content_x, y)
            y += ROW_HEIGHT
            token_line = "  |  ".join(
                f"{player}: {battle_focus_pool.tokens.get(player, 0)}"
                for player in battle_focus_pool.players
            )
            token_pos = (content_x, y)
            y += ROW_HEIGHT

            bf_box = pygame.Rect(
                rect.x + 6, group_top - BOX_INNER_PADDING,
                rect.width - 12, (y - group_top) + BOX_INNER_PADDING,
            )
            button_style.draw_box(surface, bf_box)
            label_surf = self.label_font.render("Battle Focus:", True, config.PANEL_TEXT_COLOR)
            surface.blit(label_surf, label_pos)
            token_surf = self.font.render(token_line, True, CP_TEXT_COLOR)
            surface.blit(token_surf, token_pos)
            y += SECTION_GAP

        # --- Group 2c: Fate dice (Aeldari Seer Council, Strands of Fate) ---
        # User: "die würfel müssen permanent irgendwo sichtbar sein. am besten
        # in der rechten spalte / genauso wie das agile manouver konto" - so it
        # sits here beside the Battle Focus tokens rather than in the dice
        # panel, which is for a roll being resolved right now. A Fate die is
        # kept for the whole battle instead.
        #
        # Each row names the ONE stratagem its face can discount (user: "wäre
        # gut, wenn neben den würfeln stehen würde, für welches stratagem der
        # steht"), read straight from the rule's own table via
        # summary_rows(), so the display cannot disagree with what a die is
        # actually worth. Wrapped rather than blitted at a fixed y: a stratagem
        # name is a data-driven string in a 220px panel, which is exactly the
        # case game/ui/text_utils.py exists for.
        rows_by_player = []
        if fate_dice_pool is not None:
            for player in fate_dice_pool.players:
                rows_by_player.append((player, fate_dice_pool.summary_rows(player)))
        if rows_by_player:
            multi = len(rows_by_player) > 1

            def fate_lines():
                """(is_heading, text) for the whole group, so the height can be
                measured before the box is drawn and the text drawn once
                after - the same order the groups above use, which matters
                because draw_box() fills."""
                for player, rows in rows_by_player:
                    yield True, (f"Fate Dice ({player}):" if multi else "Fate Dice:")
                    if not rows:
                        yield False, "all spent"
                        continue
                    for value, count, stratagem in rows:
                        prefix = f"{value}" + (f" x{count}" if count > 1 else "")
                        yield False, f"{prefix}  {stratagem}"

            group_top = y
            height = 0
            for is_heading, text in fate_lines():
                height += ROW_HEIGHT if is_heading else wrapped_text_height(
                    self.font, text, content_width, line_height=ROW_HEIGHT,
                )
            fate_box = pygame.Rect(
                rect.x + 6, group_top - BOX_INNER_PADDING,
                rect.width - 12, height + BOX_INNER_PADDING,
            )
            button_style.draw_box(surface, fate_box)

            for is_heading, text in fate_lines():
                if is_heading:
                    surface.blit(self.label_font.render(text, True, config.PANEL_TEXT_COLOR), (content_x, y))
                    y += ROW_HEIGHT
                else:
                    y = draw_wrapped_text(
                        surface, self.font, text, CP_TEXT_COLOR,
                        content_x, y, content_width, line_height=ROW_HEIGHT,
                    )
            y += SECTION_GAP

        # --- Group 3: Mission Points (Primary/Secondary/Total per player -
        # see game/missions.py; the mission cards themselves, describing
        # WHAT the two missions are, live in MissionCardsOverlay instead,
        # since that's read-on-hover reference text, not always-visible
        # game state) ---
        if mission_controller is not None and not score_columns:
            group_top = y
            label_pos = (content_x, y)
            y += ROW_HEIGHT
            line_positions = []
            for player in sorted(mission_controller.primary_points.keys()):
                primary = mission_controller.primary_points[player]
                secondary = mission_controller.secondary_points[player]
                total = mission_controller.total_points(player)
                line = f"{player}: {total} pts (P {primary} / S {secondary})"
                for wrapped in wrap_text(self.font, line, content_width):
                    line_positions.append((wrapped, (content_x, y)))
                    y += ROW_HEIGHT

            group3_box = pygame.Rect(
                rect.x + 6, group_top - BOX_INNER_PADDING,
                rect.width - 12, (y - group_top) + BOX_INNER_PADDING,
            )
            button_style.draw_box(surface, group3_box)
            label_surf = self.label_font.render("Mission Points:", True, config.PANEL_TEXT_COLOR)
            surface.blit(label_surf, label_pos)
            for line, pos in line_positions:
                line_surf = self.font.render(line, True, MISSION_TEXT_COLOR)
                surface.blit(line_surf, pos)
            y += SECTION_GAP

        pygame.draw.line(surface, config.PANEL_BORDER_COLOR, (rect.x, y), (rect.right, y), width=2)
        y += SECTION_GAP - 4

        button_rect = pygame.Rect(rect.x + BUTTON_MARGIN, y, rect.width - 2 * BUTTON_MARGIN, BUTTON_HEIGHT)
        # User: the button should already name the phase it leads to,
        # instead of a bare "Next Phase" that leaves you guessing - Fight
        # is the last phase (rule 07.02), so from there this ends the turn
        # instead of advancing to a next phase within the same turn.
        label = "End Turn" if turn_tracker.is_last_phase else f"Next Phase: {PHASES[turn_tracker.phase_index + 1]}"
        mouse_pos = pygame.mouse.get_pos()
        hovered = button_rect.collidepoint(mouse_pos)
        pressed = hovered and pygame.mouse.get_pressed()[0]
        self._button_rect = button_style.draw_button(
            surface, button_rect, label, self.button_font, hovered=hovered, pressed=pressed, accent="confirm",
        )


    def handle_click(self, pos):
        return self._button_rect is not None and self._button_rect.collidepoint(pos)
