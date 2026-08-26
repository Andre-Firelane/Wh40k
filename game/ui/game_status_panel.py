import pygame

from game import config, sprites
from game.turn import PHASES
from game.ui import button_style
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
LOGO_BOX = 58            # px, the square tile one faction badge is drawn in
LOGO_PADDING = 4         # px between that tile's frame and the artwork inside it
LOGO_GAP = 6             # px between a tile and the Round bar sitting between the two
NAME_ROW_HEIGHT = 20     # px reserved for the "P1: AELDARI" line under the tiles
LABEL_MIN_GAP = 10       # px the two labels must keep between them, or the "P1: " prefixes are dropped (see _badge_labels)
ACTIVE_BORDER_WIDTH = 3  # the active player's tile gets a thicker frame, see _draw_badge()
ACTIVE_GLOW_COLOR = (120, 100, 20)  # dim gold ring just outside that frame, so it reads as a glow rather than a hard outline


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

    @property
    def button_rect(self):
        """Where the Next Phase/End Turn button was drawn last frame, or None
        before the first draw. The panel lays out top-down and the button
        follows its content, so this is the only honest answer to "how much of
        the right column does this panel actually need?" - main() reads it to
        keep the log strip below it (see config.LOG_HEIGHT)."""
        return self._button_rect


    def _status_lines(self, turn_tracker, badges):
        """The plain text rows under the Round counter.

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

        Returns [(player, faction_keyword, logo_path), ...] in a stable
        player order, and only when EVERY player has art to show. A row with
        one tile filled and one empty reads worse than the plain "Active
        Player: X" line it replaces, so a faction with no entry in
        sprites.FACTION_LOGO_KEYS (or no file for it) falls the whole group
        back to that text instead - same "missing art is fine, and never
        half-drawn" convention the rest of the sprite lookup uses.

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
            path = sprites.faction_logo_path(keyword) if keyword is not None else None
            if path is None:
                return None
            row.append((player, keyword, path))
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

    def _draw_badge(self, surface, tile_rect, logo_path, active):
        """One faction badge: the artwork inside a chamfered tile, framed in
        the panel's usual cyan - or in the header gold, thicker and doubled
        for a glow, when this is the active player. That frame is what
        replaced the "(Active)" line of text (user request), so it has to be
        readable at a glance rather than a subtle tint.

        Whose frame lights up is turn_tracker.active_player, exactly the
        value the replaced line showed - the transient "whose decision is
        this right now" flag, NOT turn_owner (see game/turn.py). It flipping
        mid-turn onto the defender during a save roll is the intended
        reading here: this marks who the game is waiting on."""
        # Outer ring first, tile on top of it: draw_box() fills as well as
        # outlines, so drawing the larger one second would paint over the
        # tile it is supposed to sit around.
        if active:
            button_style.draw_box(
                surface, tile_rect.inflate(4, 4), chamfer=5,
                border_color=ACTIVE_GLOW_COLOR, border_width=1,
            )
        border = config.PANEL_HEADER_COLOR if active else button_style.BOX_BORDER_COLOR
        button_style.draw_box(
            surface, tile_rect, chamfer=4, border_color=border,
            border_width=ACTIVE_BORDER_WIDTH if active else 1,
        )
        art = sprites.fitted_surface(logo_path, tile_rect.width - 2 * LOGO_PADDING)
        surface.blit(art, art.get_rect(center=tile_rect.center))

    def draw(self, surface, rect, turn_tracker, command_points=None, mission_controller=None,
             battle_focus_pool=None, fate_dice_pool=None, player_factions=None):
        surface.fill(config.PANEL_BG_COLOR, rect)
        pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, width=2)

        button_style.draw_panel_header(surface, rect, "Game Status", self.header_font)

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
        round_bar_rect = None

        if badges is not None:
            tile_y = y
            left_tile = pygame.Rect(content_x, tile_y, LOGO_BOX, LOGO_BOX)
            right_tile = pygame.Rect(content_x + content_width - LOGO_BOX, tile_y, LOGO_BOX, LOGO_BOX)
            bar_x = left_tile.right + LOGO_GAP
            round_bar_rect = pygame.Rect(
                bar_x, tile_y + (LOGO_BOX - button_style.SUBHEADER_HEIGHT) // 2,
                (right_tile.left - LOGO_GAP) - bar_x, button_style.SUBHEADER_HEIGHT,
            )
            y = tile_y + LOGO_BOX + 4

            labels = self._badge_labels(badges, content_width)
            for tile, (player, _, path), label in zip((left_tile, right_tile), badges, labels):
                active = player == turn_tracker.active_player
                badge_positions.append((tile, path, active))
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
        else:
            # No badge art for both players: fall back to the plain bar plus
            # an "Active Player" line, which is what this group was before.
            round_bar_rect = pygame.Rect(content_x, y, content_width, button_style.SUBHEADER_HEIGHT)
            y = round_bar_rect.bottom + 6

        line_positions = []
        for line in self._status_lines(turn_tracker, badges):
            line_positions.append((line, (content_x, y)))
            y += ROW_HEIGHT

        group1_box = pygame.Rect(
            rect.x + 6, group_top - BOX_INNER_PADDING,
            rect.width - 12, (y - group_top) + BOX_INNER_PADDING,
        )
        button_style.draw_box(surface, group1_box)
        round_label = f"ROUND {turn_tracker.battle_round}"
        if badges is not None:
            # The bar is only as wide as the gap between the two badges, so a
            # long round number falls back to the short form rather than
            # spilling over the tiles.
            if self.label_font.size(round_label)[0] > round_bar_rect.width - 6:
                round_label = f"RND {turn_tracker.battle_round}"
            button_style.draw_header_bar(surface, round_bar_rect, round_label, self.label_font, center=True)
        else:
            button_style.draw_header_bar(surface, round_bar_rect, round_label, self.label_font, text_margin=8)
        for tile, path, active in badge_positions:
            self._draw_badge(surface, tile, path, active)
        for text_surf, pos in label_positions:
            surface.blit(text_surf, pos)
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
