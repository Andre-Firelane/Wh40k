import pygame

from game import config
from game.turn import PHASE_COMMAND
from game.ui.text_utils import wrap_text

BG_COLOR = (15, 15, 15)
WARNING_COLOR = (230, 90, 90)
TEXT_PADDING = 16


class PlayerBanner:
    """Top strip - used to show Round/Phase/turn, Command Points, and the
    Next Phase/End Turn button, all of which have moved to GameStatusPanel
    on the right. What's left here are the "why can't I advance the phase"
    warnings - "Regaining Coherency" (blocks ending the turn) and, since a
    user report that this had NO visual feedback at all ("das fehlt
    momentan noch komplett"), a mandatory Battle-Shock roll (rule 08.03,
    blocks leaving the Command phase) - both stay prominent across the full
    window width since they block everything else until resolved. Draws
    nothing (and takes up no visual space, since the board/panels already
    rendered underneath) when neither applies."""

    def __init__(self):
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)

    def draw(self, surface, coherency_enforcer=None, battle_shock_controller=None, turn_tracker=None, all_tokens=None):
        pending_squad = coherency_enforcer.pending_squad if coherency_enforcer is not None else None

        text = None
        if pending_squad is not None:
            text = f"Regaining Coherency: remove a model from {pending_squad.name}"
        elif (
            battle_shock_controller is not None and turn_tracker is not None
            and turn_tracker.phase == PHASE_COMMAND
        ):
            pending_squads = battle_shock_controller.pending_required_rolls(
                all_tokens if all_tokens is not None else [], turn_tracker.active_player,
            )
            if pending_squads:
                names = ", ".join(squad.name for squad in pending_squads)
                text = f"Battle-Shock roll required before leaving the Command phase: {names}"

        if text is None:
            return

        # Both warnings name UNITS, and one of them names every unit that
        # still owes a roll - with attached units (19.01) that list outgrew
        # the window as a single centered line. The strip grows in height
        # instead of running off both edges; it's drawn over the board and
        # isn't part of any layout, so growing it costs nothing (see
        # main.py - PLAYER_BANNER_HEIGHT is this strip's MINIMUM).
        line_height = self.font.get_height() + 2
        lines = wrap_text(self.font, text, surface.get_width() - 2 * TEXT_PADDING) or [text]
        height = max(config.PLAYER_BANNER_HEIGHT, len(lines) * line_height + 8)
        rect = pygame.Rect(0, 0, surface.get_width(), height)
        pygame.draw.rect(surface, BG_COLOR, rect)
        line_y = rect.y + (height - len(lines) * line_height) // 2
        for line in lines:
            line_surf = self.font.render(line, True, WARNING_COLOR)
            surface.blit(line_surf, line_surf.get_rect(centerx=rect.centerx, y=line_y))
            line_y += line_height
