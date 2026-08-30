import pygame

from game import config
from game.ui import button_style
from game.ui.text_utils import wrap_text

# User: "gib mal bitte ine warnung aus, die ich wegklicken muss, wenn ich
# auf end turn klicke, obwohl ich noch mit einheiten im nahkampf kaempfen
# koennte" - same must-click-away pattern as
# game/ui/stratagem_notice_overlay.py and waaagh_notice_overlay.py, wired
# from main.py's "Next Phase"/"End Turn" click handler.
#
# The "danger" red accent, not the violet reserved for Stratagem spends nor
# the green that means "a friendly buff just activated": this is the one
# overlay in the set that exists to say something is about to go WRONG.
OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_WIDTH = 500
BOX_PADDING = 20
BODY_LINE_HEIGHT = 24
UNIT_LINE_HEIGHT = 22
UNIT_TOP_GAP = 10
HINT_TOP_GAP = 16
BODY_TEXT_COLOR = (225, 225, 225)
UNIT_TEXT_COLOR = (255, 205, 205)
HINT_TEXT_COLOR = (185, 185, 185)
HEADER_BLOCK_HEIGHT = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8


class FightWarningOverlay:
    """A modal, must-click-away warning that ending the turn right now
    forfeits melee attacks the player still has coming (rule 12.04).

    Deliberately a WARNING, not a lock. This engine never forces a player
    to fight, and turning "End Turn" into something you cannot click while
    an engaged unit refuses to swing would be a much larger change than the
    one asked for - so the click that raises this warning is spent on it,
    and clicking End Turn again goes through. main.py owns that
    once-per-phase bookkeeping through warn_once()/reset() below, because
    "has this already been said this phase" is a property of the warning,
    not of the fight.

    A single slot, not a queue like its two siblings: it can only ever be
    raised by a click the human just made, and that click cannot be made
    again until this one is dismissed."""

    def __init__(self):
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 2, bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.unit_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._names = None    # unit names still owed a fight, or None when nothing is showing
        self._warned = False  # already warned once for the current phase

    @property
    def is_pending(self):
        return self._names is not None

    def warn_once(self, unit_names):
        """Raise the warning for `unit_names` and return True, unless it has
        already been raised since the last reset() - in which case nothing is
        shown and False comes back, which is main.py's cue to let the turn
        actually end.

        One warning per phase: after being told, a player who clicks End Turn
        again means it. Warning a second time would just be in the way of a
        decision already made."""
        if self._warned or not unit_names:
            return False
        self._names = list(unit_names)
        self._warned = True
        return True

    def dismiss(self):
        self._names = None

    def reset(self):
        """Called from main.py's advance_turn_phase() - the one place a phase
        ever changes. Without this the warning would fire once per BATTLE
        instead of once per Fight phase (this repo's own rule: a "deferred
        until X" note needs a point at X that clears it)."""
        self._names = None
        self._warned = False

    def draw(self, surface):
        if self._names is None:
            return
        names = self._names

        count = len(names)
        body_text = (
            f"{count} of your units can still fight in melee this phase. "
            "Ending the turn now gives up their attacks."
        )
        text_max_width = BOX_WIDTH - 2 * BOX_PADDING
        body_lines = wrap_text(self.body_font, body_text, text_max_width) or [body_text]
        unit_lines = []
        for name in names:
            unit_lines.extend(wrap_text(self.unit_font, f"- {name}", text_max_width) or [name])

        box_height = (
            HEADER_BLOCK_HEIGHT
            + len(body_lines) * BODY_LINE_HEIGHT
            + UNIT_TOP_GAP + len(unit_lines) * UNIT_LINE_HEIGHT
            + HINT_TOP_GAP + self.hint_font.get_height()
            + BOX_PADDING
        )
        box_rect = pygame.Rect(0, 0, BOX_WIDTH, box_height)
        box_rect.center = surface.get_rect().center

        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM_COLOR)
        surface.blit(dim, (0, 0))

        button_style.draw_box(
            surface, box_rect, border_color=button_style.BORDER_NORMAL_DANGER,
            bg_color=button_style.BG_NORMAL_DANGER, border_width=2,
        )
        y = button_style.draw_panel_header(
            surface, box_rect, "STILL IN COMBAT", self.heading_font,
            text_color=button_style.TEXT_NORMAL_DANGER, bg_color=button_style.BG_ACTIVE_DANGER,
        )

        for line in body_lines:
            line_surf = self.body_font.render(line, True, BODY_TEXT_COLOR)
            surface.blit(line_surf, line_surf.get_rect(centerx=box_rect.centerx, y=y))
            y += BODY_LINE_HEIGHT

        y += UNIT_TOP_GAP
        for line in unit_lines:
            line_surf = self.unit_font.render(line, True, UNIT_TEXT_COLOR)
            surface.blit(line_surf, line_surf.get_rect(centerx=box_rect.centerx, y=y))
            y += UNIT_LINE_HEIGHT

        y += HINT_TOP_GAP
        hint_surf = self.hint_font.render(
            "Click to go back - click End Turn again to end it anyway", True, HINT_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(centerx=box_rect.centerx, y=y))
