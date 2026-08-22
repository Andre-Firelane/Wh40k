import pygame

from game import config
from game.ui import button_style
from game.ui.text_utils import wrap_text

OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_BG_COLOR = (25, 25, 25)
BOX_BORDER_COLOR = (255, 215, 0)
PROMPT_COLOR = (255, 255, 255)
PLAYER_COLOR = (255, 215, 0)
BUTTON_BG_COLOR = (45, 45, 45)
BUTTON_BORDER_COLOR = (120, 120, 120)
BUTTON_TEXT_COLOR = (255, 255, 255)
# User: "der violette color code für stratagems muss sich auch in den
# überschriften wiederfinden, wenn das spiel mit einem confirmation overlay
# unterbricht, zb für Abwehrfeuer oder Heroic Intervention" - when this
# break point exists because a Stratagem is being offered/resolved
# (DecisionManager.is_stratagem, see its own docstring for exactly which
# ones), the box border and the "{player} - Decision" heading swap to the
# same violet accent already used for Stratagem buttons
# (game/ui/button_style.py's "stratagem" palette) and StratagemNoticeOverlay,
# instead of this overlay's own plain gold - everything else (prompt/option
# button styling) is left as-is, since only the heading was asked for.
STRATAGEM_BOX_BORDER_COLOR = button_style.BORDER_NORMAL_STRATAGEM
STRATAGEM_PLAYER_COLOR = button_style.TEXT_NORMAL_STRATAGEM

BOX_WIDTH = 420
PLAYER_LINE_HEIGHT = 26
PROMPT_LINE_HEIGHT = 20
BUTTON_HEIGHT = 36        # minimum - an option button grows to fit its wrapped label
BUTTON_LINE_HEIGHT = 22
BUTTON_TEXT_PADDING = 10
BUTTON_GAP = 10
BOX_PADDING = 20


class DecisionOverlay:
    """Renders the DecisionManager's pending decision (if any) as a modal
    box dimming the whole screen - the player must pick one of the offered
    options before anything else can happen."""

    def __init__(self):
        self.player_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.prompt_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        self.button_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self._button_rects = []

    def draw(self, surface, decision_manager):
        self._button_rects = []
        if not decision_manager.is_pending:
            return

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))

        content_width = BOX_WIDTH - 2 * BOX_PADDING
        prompt_lines = wrap_text(self.prompt_font, decision_manager.prompt, content_width)
        # An option's label carries data (unit names, CP cost) - e.g.
        # "Heroic Intervention: 1 Crisis Starscythe Battlesuits 1 + Commander
        # in Coldstar Battlesuit (1 CP)" for an attached unit (19.01), which
        # ran 146px past this box as one centered line. Each option is
        # wrapped and its button grown to fit, and the box height is summed
        # from those actual heights rather than options x BUTTON_HEIGHT.
        option_lines = [
            wrap_text(self.button_font, option["label"], content_width - 2 * BUTTON_TEXT_PADDING) or [option["label"]]
            for option in decision_manager.options
        ]
        option_heights = [
            max(BUTTON_HEIGHT, len(lines) * BUTTON_LINE_HEIGHT + 2 * BUTTON_TEXT_PADDING)
            for lines in option_lines
        ]
        player_lines = PLAYER_LINE_HEIGHT if decision_manager.player else 0
        box_height = (
            2 * BOX_PADDING
            + player_lines
            + len(prompt_lines) * PROMPT_LINE_HEIGHT
            + sum(height + BUTTON_GAP for height in option_heights)
        )
        box_rect = pygame.Rect(0, 0, BOX_WIDTH, box_height)
        box_rect.center = surface.get_rect().center
        border_color = STRATAGEM_BOX_BORDER_COLOR if decision_manager.is_stratagem else BOX_BORDER_COLOR
        player_color = STRATAGEM_PLAYER_COLOR if decision_manager.is_stratagem else PLAYER_COLOR
        pygame.draw.rect(surface, BOX_BG_COLOR, box_rect)
        pygame.draw.rect(surface, border_color, box_rect, width=2)

        y = box_rect.y + BOX_PADDING
        if decision_manager.player:
            player_surf = self.player_font.render(f"{decision_manager.player} - Decision", True, player_color)
            surface.blit(player_surf, (box_rect.x + BOX_PADDING, y))
            y += PLAYER_LINE_HEIGHT

        for line in prompt_lines:
            line_surf = self.prompt_font.render(line, True, PROMPT_COLOR)
            surface.blit(line_surf, (box_rect.x + BOX_PADDING, y))
            y += PROMPT_LINE_HEIGHT

        y += BUTTON_GAP
        for lines, height in zip(option_lines, option_heights):
            btn_rect = pygame.Rect(box_rect.x + BOX_PADDING, y, content_width, height)
            pygame.draw.rect(surface, BUTTON_BG_COLOR, btn_rect)
            pygame.draw.rect(surface, BUTTON_BORDER_COLOR, btn_rect, width=1)
            line_y = btn_rect.y + (height - len(lines) * BUTTON_LINE_HEIGHT) // 2
            for line in lines:
                label_surf = self.button_font.render(line, True, BUTTON_TEXT_COLOR)
                surface.blit(label_surf, label_surf.get_rect(centerx=btn_rect.centerx, y=line_y))
                line_y += BUTTON_LINE_HEIGHT
            self._button_rects.append(btn_rect)
            y += height + BUTTON_GAP

    def handle_click(self, pos):
        for i, rect in enumerate(self._button_rects):
            if rect.collidepoint(pos):
                return i
        return None
