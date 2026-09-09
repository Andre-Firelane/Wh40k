import pygame

from game import config, decline_option
from game.ui import button_style, unit_thumbs
from game.ui.text_utils import wrap_text

OVERLAY_DIM_COLOR = (0, 0, 0, 160)
BOX_BG_COLOR = (25, 25, 25)
BOX_BORDER_COLOR = (255, 215, 0)
PROMPT_COLOR = (255, 255, 255)
PLAYER_COLOR = (255, 215, 0)
# The ordinary option, in the same BLUE every other button in this HUD wears
# when a press costs nothing (user: "bei normalen overlays habe ich jetzt
# meiste einen grauen knopf und einen roten decline knopf. aendere die grauen
# knoepfe in blau"). It was a flat grey of its own, which said nothing: this
# box carries ~90 of the game's break points, so the one place a decision
# actually FALLS was the only place with no colour code at all - the red half
# of that pair was fixed for the same reason one report earlier.
#
# Taken from button_style, not written again here, for exactly the reason the
# decline colours below are: the modal box and ActionPanel must not end up
# with two different blues meaning one thing. Same flat rectangle as before -
# only the palette moves, since the shape was not what was asked about.
BUTTON_BG_COLOR = button_style.BG_NORMAL
BUTTON_BORDER_COLOR = button_style.BORDER_NORMAL
BUTTON_TEXT_COLOR = button_style.TEXT_NORMAL
# The "no" option, in the same red the left panel has always used for Cancel
# and Decline (user: "Decline Buttons auch in den overlays rot einfaerben").
# Taken from button_style rather than written again here, so the modal box and
# ActionPanel cannot end up with two different reds meaning one thing - which
# one an option is comes from game/decline_option.py, likewise the one
# definition. It stays THIS overlay's flat rectangle, not draw_button()'s
# chamfered HUD body: the box's option buttons are a list of answers and
# changing their shape was not what was asked for.
DECLINE_BG_COLOR = button_style.BG_NORMAL_DANGER
DECLINE_BORDER_COLOR = button_style.BORDER_NORMAL_DANGER
DECLINE_TEXT_COLOR = button_style.TEXT_NORMAL_DANGER
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
# ... and the same idea one colour over for an Aeldari Agile Manoeuvre, which
# spends a Battle Focus token rather than CP - user: "colorcode für agile
# manouvers ist momentan lila wie stratagems. soll aber türkis sein. (buttons,
# überschriften)". "Überschriften" is this heading; the buttons are
# ActionPanel's, and both read button_style's "battle_focus" palette so the
# panel and the overlay cannot drift apart.
STRATAGEM_BOX_BORDER_COLOR = button_style.BORDER_NORMAL_STRATAGEM
STRATAGEM_PLAYER_COLOR = button_style.TEXT_NORMAL_STRATAGEM

# (border, heading) per DecisionManager.accent - ONE table, so a fourth
# category is a row here rather than another branch at the draw site.
ACCENT_COLORS = {
    None: (BOX_BORDER_COLOR, PLAYER_COLOR),
    "stratagem": (STRATAGEM_BOX_BORDER_COLOR, STRATAGEM_PLAYER_COLOR),
    "battle_focus": (button_style.BORDER_NORMAL_BATTLE_FOCUS,
                     button_style.TEXT_NORMAL_BATTLE_FOCUS),
}

BOX_WIDTH = 420
THUMB_GAP = 10  # between the thumbnail row and the prompt text under it
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

    def draw(self, surface, decision_manager, squads=(), board_pick=False):
        """`squads` is every unit in the game (GameState.all_squads()) - the
        ones this prompt actually talks about are picked out of its own text
        and shown as thumbnails above it. User: "der text ist mir zu
        unübersichtlich ... ich fände die portraits überall gut, wo von
        einheiten gesprochen wird." Optional: passing nothing just draws the
        box as before.

        `board_pick` is game/unit_pick.py's verdict that this decision is
        answered by CLICKING A UNIT ON THE BOARD. Then this overlay draws
        NOTHING - not a smaller box, nothing: it dims the whole window and
        would sit on top of the very units the player has to see and click, and
        the left panel carries the prompt instead (ActionPanel's
        _draw_unit_pick_ui, the arrangement Burden of Trust already used).

        Drawn-nothing still has to run: _button_rects is cleared FIRST, so last
        frame's option buttons cannot keep swallowing clicks behind a picture
        that is no longer on screen. That is why main.py calls this either way
        rather than skipping the call."""
        self._button_rects = []
        if not decision_manager.is_pending or board_pick:
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
        # The units this prompt is about, drawn above its text. Measured
        # first because the box has to be sized before anything is placed in
        # it - see unit_thumbs.row_size().
        named = unit_thumbs.squads_named_in(decision_manager.prompt, squads)
        thumb_paths, _thumb_w, thumb_h = unit_thumbs.row_size(named, content_width)
        box_height = (
            2 * BOX_PADDING
            + player_lines
            + (thumb_h + THUMB_GAP if thumb_paths else 0)
            + len(prompt_lines) * PROMPT_LINE_HEIGHT
            + sum(height + BUTTON_GAP for height in option_heights)
        )
        box_rect = pygame.Rect(0, 0, BOX_WIDTH, box_height)
        box_rect.center = surface.get_rect().center
        border_color, player_color = ACCENT_COLORS.get(
            getattr(decision_manager, "accent", None), ACCENT_COLORS[None])
        pygame.draw.rect(surface, BOX_BG_COLOR, box_rect)
        pygame.draw.rect(surface, border_color, box_rect, width=2)

        y = box_rect.y + BOX_PADDING
        if decision_manager.player:
            player_surf = self.player_font.render(f"{decision_manager.player} - Decision", True, player_color)
            surface.blit(player_surf, (box_rect.x + BOX_PADDING, y))
            y += PLAYER_LINE_HEIGHT

        if thumb_paths:
            y = unit_thumbs.draw_row(
                surface, named, box_rect.x + BOX_PADDING, y, content_width, gap_below=THUMB_GAP,
            )

        for line in prompt_lines:
            line_surf = self.prompt_font.render(line, True, PROMPT_COLOR)
            surface.blit(line_surf, (box_rect.x + BOX_PADDING, y))
            y += PROMPT_LINE_HEIGHT

        y += BUTTON_GAP
        for option, lines, height in zip(decision_manager.options, option_lines, option_heights):
            declines = decline_option.is_decline(option["label"])
            bg = DECLINE_BG_COLOR if declines else BUTTON_BG_COLOR
            border = DECLINE_BORDER_COLOR if declines else BUTTON_BORDER_COLOR
            text_color = DECLINE_TEXT_COLOR if declines else BUTTON_TEXT_COLOR
            btn_rect = pygame.Rect(box_rect.x + BOX_PADDING, y, content_width, height)
            pygame.draw.rect(surface, bg, btn_rect)
            pygame.draw.rect(surface, border, btn_rect, width=1)
            line_y = btn_rect.y + (height - len(lines) * BUTTON_LINE_HEIGHT) // 2
            for line in lines:
                label_surf = self.button_font.render(line, True, text_color)
                surface.blit(label_surf, label_surf.get_rect(centerx=btn_rect.centerx, y=line_y))
                line_y += BUTTON_LINE_HEIGHT
            self._button_rects.append(btn_rect)
            y += height + BUTTON_GAP

    def handle_click(self, pos):
        for i, rect in enumerate(self._button_rects):
            if rect.collidepoint(pos):
                return i
        return None
