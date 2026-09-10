"""How a column table is laid out and drawn.

Extracted at the SECOND consumer, which is this repo's standing rule. The
arithmetic lived privately inside UnitDatacardOverlay - it is what draws the
M/WS/BS/T/W/Ld/Sv/OC stat block and the Ranged/Melee weapon tables on the
hover datacard - and game/ui/unit_stats_overlay.py's three resume tables ask
exactly the same two questions: where do the columns start, and how is one row
of values put into them.

game/ui/unit_datacard.py DELEGATES to these and keeps its own constants, so
every pixel it draws is unchanged by construction and its pixel tests did not
have to move.

DELIBERATELY NOT ABSORBED, though both look like tables from a distance:

  mission_cards._draw_scoring()  three columns with a RIGHT-aligned VP column
                                 and per-row wrapping in the middle one
  rules_body's "table" block     two cells, no wrapping, a fixed 300px value
                                 column

Those are different shapes answering different questions. Folding them in here
would be a unification with no second consumer behind it - which is how a
helper ends up with a flag per caller.
"""

import pygame

from game.ui.text_utils import wrap_text


def column_layout(x, width, column_count, first_width=None):
    """(widths, positions) for `column_count` columns filling `width` from `x`.

    `first_width` pins the first column - the name column, which holds text
    rather than a number and needs the room. The rest divide what is left
    evenly. Without it every column is the same width.

    Floats, not ints: rounding each column before laying the next one out is
    what makes the last separator drift away from the table's right edge."""
    if first_width is not None and column_count > 1:
        other = (width - first_width) / (column_count - 1)
        widths = [first_width] + [other] * (column_count - 1)
    else:
        widths = [width / column_count] * column_count
    positions = []
    at = x
    for w in widths:
        positions.append(at)
        at += w
    return widths, positions


def draw_row(surface, widths, positions, row_y, row_height, values, font, color):
    """One row of values: column 0 left-aligned and wrapped, the rest centred.

    That split is the whole point of the shape - column 0 holds a name, which
    is long and reads left-to-right, and every other column holds a short
    number, which reads as a column only when it is centred under its header."""
    for i, (w, x, val) in enumerate(zip(widths, positions, values)):
        if i == 0:
            lines = wrap_text(font, val, w - 8) or [val]
            line_height = font.get_height() + 2
            line_y = row_y + (row_height - len(lines) * line_height) // 2
            for line in lines:
                surface.blit(font.render(line, True, color), (x + 4, line_y))
                line_y += line_height
        else:
            val_surf = font.render(val, True, color)
            surface.blit(val_surf, val_surf.get_rect(center=(x + w / 2, row_y + row_height // 2)))


def draw_grid(surface, table_rect, positions, color, header_bottom=None):
    """The frame, the vertical separators, and optionally the rule under a
    header row.

    The first position is skipped: it is the table's own left edge, which the
    frame already drew."""
    pygame.draw.rect(surface, color, table_rect, width=1)
    if header_bottom is not None:
        pygame.draw.line(surface, color, (table_rect.x, header_bottom),
                         (table_rect.right, header_bottom))
    for x in positions[1:]:
        pygame.draw.line(surface, color, (x, table_rect.y), (x, table_rect.bottom))
