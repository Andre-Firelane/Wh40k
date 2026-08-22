import pygame

from game import config
from game.turn import PHASES
from game.ui import button_style
from game.ui.text_utils import draw_wrapped_text, wrap_text, wrapped_text_height

ROW_HEIGHT = 24
CP_TEXT_COLOR = (150, 190, 255)
MISSION_TEXT_COLOR = (255, 210, 130)
BUTTON_HEIGHT = 34
BUTTON_MARGIN = 10
SECTION_GAP = 14         # vertical gap between the bordered content groups
BOX_INNER_PADDING = 8    # padding between a group's border and its own text


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
        self._button_rect = None

    @property
    def button_rect(self):
        """Where the Next Phase/End Turn button was drawn last frame, or None
        before the first draw. The panel lays out top-down and the button
        follows its content, so this is the only honest answer to "how much of
        the right column does this panel actually need?" - main() reads it to
        keep the log strip below it (see config.LOG_HEIGHT)."""
        return self._button_rect

    def draw(self, surface, rect, turn_tracker, command_points=None, mission_controller=None,
             battle_focus_pool=None, fate_dice_pool=None):
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

        # --- Group 1: Round (bar) / Phase / Active Player ---
        group_top = y
        round_bar_rect = pygame.Rect(content_x, y, content_width, button_style.SUBHEADER_HEIGHT)
        y = round_bar_rect.bottom + 6

        other_lines = [f"{turn_tracker.phase} Phase", f"Active Player: {turn_tracker.active_player}"]
        line_positions = []
        for line in other_lines:
            line_positions.append((line, (content_x, y)))
            y += ROW_HEIGHT

        group1_box = pygame.Rect(
            rect.x + 6, group_top - BOX_INNER_PADDING,
            rect.width - 12, (y - group_top) + BOX_INNER_PADDING,
        )
        button_style.draw_box(surface, group1_box)
        button_style.draw_header_bar(surface, round_bar_rect, f"ROUND {turn_tracker.battle_round}", self.label_font, text_margin=8)
        for line, pos in line_positions:
            line_surf = self.font.render(line, True, config.PANEL_TEXT_COLOR)
            surface.blit(line_surf, pos)
        y += SECTION_GAP

        # --- Group 2: Command Points ---
        if command_points is not None:
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
        if battle_focus_pool is not None and battle_focus_pool.players:
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
        if mission_controller is not None:
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
