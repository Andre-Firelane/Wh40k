"""The full printed text of a Stratagem, shown after resting on its button.

User: "zum anderen sollte das stratagems vollständig angezeigt werden wenn man
ein paar Sekunden über einen stratagems Knopf hovert."

WHAT IT SOLVES. A Stratagem button is 220px wide, so its label can only be the
name, the cost and at best a half-line summary ("Sudden Storm (1 CP) - ranged
weapons gain [ASSAULT] this turn"). The WHEN/TARGET/EFFECT that decide whether
it is legal right now have nowhere to go. They are in the corpus, and since
the army-rules reader learned to set printed rules properly they can simply be
set here too.

DWELL, NOT HOVER. The panel is a column of buttons a player is moving across on
the way to clicking one; a tooltip that appeared on contact would flash
constantly. STRATAGEM_TIP_DELAY_MS of resting is what turns "passing over" into
"asking about". The timing lives on ActionPanel (it owns the buttons and the
mouse sample); this module owns only what the box looks like.

DRAWN FROM main(), NOT FROM THE PANEL, and that is a z-order decision: the
panel draws before the mission strip, which slides out over the board from the
panel's own edge and would paint across a box that had been drawn earlier. Here
it lands in the same tier as the hover datacard, which is the other thing that
opens by resting the cursor.

TYPESET BY game/ui/rules_body.py - the same code the reader uses, because "how
are printed rules set" must have one answer or the two screens drift apart.
"""

import pygame

from game import config, rules_text
from game.ui import button_style, rules_body
from game.ui.rules_body import RulesBody

BG_COLOR = (14, 8, 22)          # the stratagem accent's own dark ground
BORDER_COLOR = (150, 70, 210)   # button_style.BORDER_NORMAL_STRATAGEM
TITLE_COLOR = rules_body.STRATAGEM_NAME_COLOR
DIM_TEXT_COLOR = rules_body.DIM_TEXT_COLOR

PADDING = 12
#: Narrower than the reader's 560px: this is a box beside a cursor, not a
#: document. A Stratagem is four short clauses, so the measure can be tighter
#: without the ragged look a long paragraph would get.
TEXT_WIDTH = 400
#: Clear of the cursor, the same offset the hover datacard uses.
MOUSE_OFFSET = 18
SCREEN_MARGIN = 8


class StratagemTooltip:
    """The box. Told a name, it finds the printed text and draws it."""

    def __init__(self):
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.body = RulesBody()
        self.last_rect = None
        self._cache = {}

    def blocks_for(self, faction_keyword, detachments, name):
        """The Stratagem's printed lines as blocks, or [] if the corpus has no
        entry under that name.

        Cached per (faction, detachments, name): this is asked once per frame
        for as long as the box is open, and it re-reads and re-parses a corpus
        file otherwise. The files do not change while the game runs - the same
        argument rules_text.abilities_for()'s own cache makes."""
        key = (faction_keyword, tuple(detachments or ()), name)
        if key not in self._cache:
            stratagem = rules_text.stratagem_named(faction_keyword, detachments, name)
            blocks = []
            if stratagem is not None:
                blocks = [rules_body.Block("stratagem", stratagem.heading)]
                blocks.extend(rules_body.blocks_for(stratagem.lines))
            self._cache[key] = blocks
        return self._cache[key]

    def size_for(self, blocks):
        if not blocks:
            return (0, 0)
        height = self.body.height(blocks, TEXT_WIDTH)
        return (TEXT_WIDTH + 2 * PADDING, height + 2 * PADDING)

    def draw(self, surface, faction_keyword, detachments, name, mouse_pos,
             anchor_rect=None):
        """Draw the box for `name`; returns its rect, or None if nothing was
        drawn. Nothing is drawn when the corpus has no entry - a box saying
        nothing is worse than no box, and the button's own label already says
        what it costs."""
        blocks = self.blocks_for(faction_keyword, detachments, name)
        if not blocks:
            self.last_rect = None
            return None
        width, height = self.size_for(blocks)
        screen_rect = surface.get_rect()
        rect = pygame.Rect(0, 0, width, height)
        # Beside the BUTTON rather than the cursor when one is known: the box
        # is wider than the panel, so hanging it off the cursor would put it
        # half over the buttons it is describing.
        rect.topleft = ((anchor_rect.right + MOUSE_OFFSET) if anchor_rect
                        else (mouse_pos[0] + MOUSE_OFFSET),
                        anchor_rect.top if anchor_rect else mouse_pos[1] + MOUSE_OFFSET)
        rect = self._keep_on_screen(rect, screen_rect)
        self.last_rect = rect.copy()

        pygame.draw.rect(surface, BG_COLOR, rect)
        pygame.draw.rect(surface, BORDER_COLOR, rect, width=2)

        prev_clip = surface.get_clip()
        surface.set_clip(rect.clip(prev_clip) if prev_clip else rect)
        entries, _total = self.body.layout(blocks, TEXT_WIDTH)
        for block, offset, _block_height in entries:
            self.body.draw_block(surface, block, rect.x + PADDING,
                                 rect.y + PADDING + offset, TEXT_WIDTH,
                                 rect.right - PADDING)
        surface.set_clip(prev_clip)
        return rect

    def _keep_on_screen(self, rect, screen_rect):
        """Flip to the other side rather than just clamping, so the box never
        covers the button it belongs to. Same reasoning army_select's detail
        card writes out."""
        if rect.right > screen_rect.right - SCREEN_MARGIN:
            rect.right = screen_rect.right - SCREEN_MARGIN
        if rect.left < SCREEN_MARGIN:
            rect.left = SCREEN_MARGIN
        if rect.bottom > screen_rect.bottom - SCREEN_MARGIN:
            rect.bottom = screen_rect.bottom - SCREEN_MARGIN
        if rect.top < SCREEN_MARGIN:
            rect.top = SCREEN_MARGIN
        return rect
