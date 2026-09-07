"""Laying out and drawing a run of printed rules text.

WHY ITS OWN MODULE. This started as the middle of
game/ui/army_rules_overlay.py, which was its only consumer. The Stratagem
tooltip (game/ui/stratagem_tooltip.py) is the SECOND, and it wants exactly the
same thing: take the classified lines game/rules_text.py produces and set them
as a document - headings, labelled TRIGGER/EFFECT rows, bullets that hang,
table rows in a column, inline bold. Copying that would be two places
answering "how are printed rules set", which is the drift this repo extracts at
the second consumer rather than later.

WHAT STAYED BEHIND, on purpose. The reader keeps its panel, its scrim, its
scrolling, its header and the block BUILDING (which armies, which detachments,
which order). Those are facts about a modal window, not about typesetting. This
module never draws a frame, never reads the mouse and never knows what a player
is; it is handed blocks, a width and a point, and reports how tall the result
was.

THE ONE RULE ITS CALLERS MUST KEEP: measure with height()/layout() and draw
with draw_block(), never one and a wrapper of the other. Both go through the
same wrapping in game/ui/text_utils.py, and a mis-measure here feeds a scroll
extent - the hazard unit_datacard._ability_height() carries its own comment
about.
"""

import pygame

from game import config
from game.ui.text_utils import draw_rich_text, rich_text_height

# --- colours -----------------------------------------------------------------
TITLE_COLOR = (255, 215, 0)
RULE_NAME_COLOR = (255, 205, 120)
TEXT_COLOR = (215, 232, 245)
DIM_TEXT_COLOR = (140, 165, 185)
RULE_LINE_COLOR = (46, 78, 105)
DEFAULT_ACCENT_COLOR = (90, 160, 205)

#: A LABEL word ("TRIGGER:", "EFFECT:"). Numerically the datacard's
#: ABILITY_LABEL_COLOR, on purpose and not by import: the two screens show
#: printed rules and should read as one system, but a UI module reaching into
#: another for a constant is coupling neither file has needed.
LABEL_COLOR = (150, 195, 225)

#: A Stratagem's own name. Numerically button_style's BORDER_HOVER_STRATAGEM,
#: so the name here and the violet button that spends the CP read as one idea.
#: The test pins the two against each other so they cannot drift apart.
STRATAGEM_NAME_COLOR = (195, 120, 250)

# --- rhythm ------------------------------------------------------------------
#: Between two lines of the SAME printed paragraph.
LINE_GAP = 3
#: Between paragraphs - the corpus's own blank lines.
PARAGRAPH_GAP = 10
#: Above a heading. Space above a heading is what groups it with the text it
#: introduces rather than with the text it follows.
HEADING_GAP_ABOVE = 14
RULE_GAP = 10
SECTION_GAP = 14
#: A wrapped bullet hangs under its own text, not under the dash.
BULLET_INDENT = 14
#: ...and a wrapped "EFFECT: ..." clause under its own sentence.
LABEL_INDENT = 12
#: Where a flattened table row's value is right-aligned, so the values form a
#: COLUMN. Same argument as the mission cards' VP column: a number only reads
#: as a number when it lines up with the others.
TABLE_VALUE_WIDTH = 300


class Block:
    """One drawable line.

    A small record rather than a tuple, because a printed line carries more
    than one fact about itself: its shape, its styled runs, and - for a label
    or a table row - the two halves that get different fonts inside ONE
    wrapped paragraph.

    `text` stays the flat, verbatim string. It is what tests read and what
    makes losslessness checkable against rules_text without either side
    knowing about the other."""

    __slots__ = ("kind", "text", "runs", "label", "cells", "accent", "new_para")

    def __init__(self, kind, text, runs=None, label=None, cells=None,
                 accent=None, new_para=False):
        self.kind = kind
        self.text = text
        self.runs = runs
        self.label = label
        self.cells = cells
        self.accent = accent
        self.new_para = new_para

    def __repr__(self):
        return f"Block({self.kind!r}, {self.text!r})"


def blocks_for(lines):
    """rules_text.RuleLines as drawable blocks - one for one.

    The kinds pass straight through: the classification is a fact about the
    PRINTED text and belongs to whoever reads the corpus, not to whoever paints
    it. This only adds what is a drawing concern - which lines open a new
    paragraph."""
    out = []
    for line in lines or ():
        if not line.text:
            continue
        out.append(Block(line.kind, line.text, runs=line.runs, label=line.label,
                         cells=line.cells, new_para=line.starts_block))
    return out


class RulesBody:
    """Fonts plus the per-kind style, measure and draw of a list of Blocks."""

    def __init__(self):
        self.player_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 2, bold=True)
        self.rule_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 1, bold=True)
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3)
        self.bold_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3, bold=True)
        self.small_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 5)
        #: What draw_rich_text() switches between for an inline **bold** run -
        #: 48% of the corpus's lines carry one.
        self.body_fonts = {False: self.font, True: self.bold_font}

    # ----------------------------------------------------------------- style

    def style(self, block):
        """(fonts, colour, hanging indent) for a block. `fonts` is the
        {bold: font} pair draw_rich_text() switches between."""
        kind = block.kind
        if kind == "player":
            return {False: self.player_font, True: self.player_font}, \
                block.accent or DEFAULT_ACCENT_COLOR, 0
        if kind == "rule":
            return {False: self.rule_font, True: self.rule_font}, RULE_NAME_COLOR, 0
        if kind == "heading":
            return {False: self.heading_font, True: self.heading_font}, RULE_NAME_COLOR, 0
        if kind == "stratagem":
            return {False: self.heading_font, True: self.heading_font}, \
                STRATAGEM_NAME_COLOR, 0
        if kind in ("subtitle", "note"):
            # A Stratagem's "*Seer Council - Strategic Ploy Stratagem*" line
            # classifies it rather than saying what it does, so it is dim and
            # small - as is the "no printed text" note.
            return {False: self.small_font, True: self.small_font}, DIM_TEXT_COLOR, 0
        if kind == "label":
            return self.body_fonts, TEXT_COLOR, LABEL_INDENT
        return self.body_fonts, TEXT_COLOR, 0

    def gap_above(self, block, previous):
        """Vertical rhythm: the corpus's own paragraph breaks reaching the
        screen, plus air above a heading so it groups with what it introduces
        rather than with what it follows."""
        if previous is None:
            return 0
        if block.kind == "gap" or previous.kind == "gap":
            return 0
        if block.kind == "player":
            return SECTION_GAP
        if block.kind == "rule":
            return RULE_GAP
        if block.kind in ("heading", "stratagem"):
            return HEADING_GAP_ABOVE
        if previous.kind in ("player", "rule", "stratagem"):
            return LINE_GAP
        return PARAGRAPH_GAP if block.new_para else LINE_GAP

    def runs_for(self, block):
        """The styled runs a block is drawn from.

        A label is ONE wrapped paragraph whose first run happens to be bold and
        differently coloured - not two draws - because splitting it would wrap
        the label and its sentence independently and lose the hang."""
        if block.kind == "label":
            return [(f"{block.label}: ", True, LABEL_COLOR)] + list(block.runs or ())
        if block.kind == "bullet":
            return list(block.runs or ())
        return list(block.runs or ()) or [(block.text, False)]

    def indent_of(self, block):
        return BULLET_INDENT if block.kind == "bullet" else 0

    def line_height(self, block):
        fonts, _colour, _indent = self.style(block)
        return fonts[False].get_height() + LINE_GAP + 2

    # --------------------------------------------------------------- measure

    def block_height(self, block, width):
        if block.kind == "gap":
            return SECTION_GAP
        if block.kind == "table":
            return self.font.get_height() + LINE_GAP
        fonts, _colour, indent = self.style(block)
        return rich_text_height(
            fonts, self.runs_for(block), width - self.indent_of(block),
            line_height=self.line_height(block), hanging_indent=indent)

    def layout(self, blocks, width):
        """[(block, y offset, height)] plus the total height."""
        entries = []
        y = 0
        previous = None
        for block in blocks:
            y += self.gap_above(block, previous)
            height = self.block_height(block, width)
            entries.append((block, y, height))
            y += height
            previous = block
        return entries, y

    def height(self, blocks, width):
        return self.layout(blocks, width)[1]

    # ------------------------------------------------------------------ draw

    def draw_block(self, surface, block, x, y, width, right):
        """One block, in the shape the printed page gives it. `right` is where
        a full-width hairline ends - the panel's inner edge, not the text
        column's, because a rule reads as a separator only when it spans."""
        if block.kind == "gap":
            pygame.draw.line(surface, RULE_LINE_COLOR,
                             (x, y + SECTION_GAP // 2), (right, y + SECTION_GAP // 2))
            return
        fonts, colour, indent = self.style(block)
        line_height = self.line_height(block)

        if block.kind == "table":
            # Label left, value right-aligned in a fixed column, so the values
            # read as a COLUMN of numbers instead of as prose.
            label, value = block.cells
            surface.blit(self.font.render(label, True, TEXT_COLOR), (x, y))
            value_surf = self.bold_font.render(value, True, RULE_NAME_COLOR)
            surface.blit(value_surf, value_surf.get_rect(
                right=x + min(width, TABLE_VALUE_WIDTH), y=y))
            return

        if block.kind == "bullet":
            surface.blit(self.font.render("-", True, DIM_TEXT_COLOR), (x, y))

        draw_rich_text(surface, fonts, self.runs_for(block), colour,
                       x + self.indent_of(block), y, width - self.indent_of(block),
                       line_height=line_height, hanging_indent=indent)

        if block.kind in ("heading", "stratagem"):
            # A hairline UNDER a heading does the grouping work a size step
            # cannot here: the default font offers about 1px between these
            # sizes, so weight, colour, space and a rule carry the hierarchy.
            rule_y = y + rich_text_height(
                fonts, self.runs_for(block), width, line_height=line_height) - LINE_GAP
            pygame.draw.line(surface, RULE_LINE_COLOR, (x, rule_y), (right, rule_y))
