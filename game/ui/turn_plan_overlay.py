import pygame

from game import config
from game.ui import button_style
from game.ui.text_utils import wrap_text

# User: "ich habe gerade einen test gemacht... ich kann den plan auch nicht
# sehen. der log unten rechts reicht nicht. ich würde den plan gerne
# ausführlicher in einem großen text prompt sehen am anfang des gegnerischen
# zuges nachdem er erstellt wurde." - the existing log-panel line
# (ai/agent_driver.py's _maybe_generate_turn_plan(): "{player} turn plan:
# {turn_intent}") only shows the one-sentence summary and scrolls away with
# everything else. This is a modal, must-click-away overlay - same pattern
# as TurnStartOverlay (dim background, chamfered box, "Click to continue") -
# shown once, right when a NEW plan appears (see main.py's run_ai_action(),
# which detects this by AIMemory.turn_plan's object identity), with the full
# turn_intent AND every squad's own role/target/priority/reason, not just
# the summary sentence.
OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_WIDTH = 640
BOX_PADDING = 20
SECTION_GAP = 14
LINE_GAP = 4
HINT_TOP_GAP = 16
HINT_TEXT_COLOR = (185, 185, 185)
ROLE_TEXT_COLOR = (170, 210, 235)
MAX_BOX_HEIGHT_MARGIN = 40  # keep at least this much clearance to the window edges
HEADER_BLOCK_HEIGHT = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8


class TurnPlanOverlay:
    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1)
        self.role_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2, bold=True)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._plan = None

    def show(self, plan):
        """plan: the sanitized {"turn_intent": str, "unit_plans": {squad:
        {"role", "target", "priority", "reason"}}} dict from
        ai/claude_agent.py's _sanitize_turn_plan() (AIMemory.turn_plan).
        Shown as-is, squads ordered by their own priority (lower first) -
        the same order ai/agent_driver.py's _movement_priority_key() will
        actually move them in."""
        self._plan = plan

    @property
    def is_pending(self):
        return self._plan is not None

    def dismiss(self):
        self._plan = None

    def _layout(self, content_width):
        intent_lines = wrap_text(self.body_font, self._plan["turn_intent"], content_width) or [""]
        entries = sorted(self._plan["unit_plans"].items(), key=lambda item: item[1]["priority"])

        unit_specs = []
        for squad_name, entry in entries:
            detail = entry["target"]
            if entry["reason"]:
                detail = f"{detail} - {entry['reason']}" if detail else entry["reason"]
            detail_lines = wrap_text(self.body_font, detail, content_width - 20) if detail else []
            # An attached unit's name (19.01) plus its role can exceed even
            # this wide box, so the heading line wraps like the detail does.
            role_lines = wrap_text(self.role_font, f"{squad_name}: {entry['role']}", content_width) or [squad_name]
            unit_specs.append((role_lines, detail_lines))
        return intent_lines, unit_specs

    def draw(self, surface):
        if self._plan is None:
            return

        content_width = BOX_WIDTH - 2 * BOX_PADDING
        intent_lines, unit_specs = self._layout(content_width)

        box_height = HEADER_BLOCK_HEIGHT + BOX_PADDING
        box_height += len(intent_lines) * (self.body_font.get_height() + LINE_GAP)
        box_height += SECTION_GAP
        for role_lines, detail_lines in unit_specs:
            box_height += len(role_lines) * (self.role_font.get_height() + LINE_GAP)
            box_height += len(detail_lines) * (self.body_font.get_height() + LINE_GAP)
        box_height += HINT_TOP_GAP + self.hint_font.get_height() + BOX_PADDING
        # A large army's plan can exceed the window - cap the box rather
        # than letting it overflow off-screen (content is still clipped to
        # whatever fits, see the set_clip() call below).
        box_height = min(box_height, surface.get_height() - MAX_BOX_HEIGHT_MARGIN)

        box_rect = pygame.Rect(0, 0, BOX_WIDTH, box_height)
        box_rect.center = surface.get_rect().center

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))

        button_style.draw_box(surface, box_rect, border_width=2)
        y = button_style.draw_panel_header(surface, box_rect, "TURN PLAN", self.heading_font)

        x = box_rect.x + BOX_PADDING
        previous_clip = surface.get_clip()
        surface.set_clip(box_rect)
        for line in intent_lines:
            surf = self.body_font.render(line, True, config.PANEL_TEXT_COLOR)
            surface.blit(surf, (x, y))
            y += self.body_font.get_height() + LINE_GAP

        y += SECTION_GAP
        for role_lines, detail_lines in unit_specs:
            for line in role_lines:
                role_surf = self.role_font.render(line, True, ROLE_TEXT_COLOR)
                surface.blit(role_surf, (x, y))
                y += self.role_font.get_height() + LINE_GAP
            for line in detail_lines:
                detail_surf = self.body_font.render(line, True, HINT_TEXT_COLOR)
                surface.blit(detail_surf, (x + 20, y))
                y += self.body_font.get_height() + LINE_GAP
        surface.set_clip(previous_clip)

        hint_y = min(y + HINT_TOP_GAP, box_rect.bottom - self.hint_font.get_height() - BOX_PADDING // 2)
        hint_surf = self.hint_font.render("Click to continue", True, HINT_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(centerx=box_rect.centerx, y=hint_y))
