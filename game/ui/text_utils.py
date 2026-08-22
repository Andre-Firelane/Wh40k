"""Shared text layout for every panel/overlay: wrapping that cannot be
defeated by a long string, plus one helper that draws a wrapped block and
reports how tall it turned out.

Both exist for the same reason - a UI that prints DATA (unit names, weapon
names, objective names) cannot know in advance how wide that data is, so
"render one line at a fixed y" is only ever correct until the data grows.
Attached units (rule 19.01) made that concrete: a merged unit's name is
"<bodyguard> + <character>" ("1 Crisis Starscythe Battlesuits 1 + Commander
in Coldstar Battlesuit"), which measured 300px past the 220px left panel.

The rule for callers: never blit a data-carrying string yourself at a
hardcoded y - call draw_wrapped_text() and use its return value for
whatever comes next, so a text that needs two or three lines pushes the
rest of the screen down instead of being drawn over."""


def wrap_text(font, text, max_width):
    """Splits `text` into lines that each fit `max_width`.

    A single word wider than max_width is broken mid-word rather than
    emitted as one overflowing line - without that, wrapping silently
    fails for exactly the inputs it exists for (a long weapon name in a
    narrow table column, a squad name in the reserves cards). Guaranteed:
    every returned line measures <= max_width, unless max_width is too
    small for even one character."""
    if max_width <= 0:
        return [text] if text else []
    lines = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if font.size(word)[0] <= max_width:
            current = word
            continue
        # Doesn't fit on a line of its own at all - break it up. The last
        # piece stays in `current`, so a following short word can still
        # share that line.
        for chunk in _break_word(font, word, max_width):
            if current:
                lines.append(current)
            current = chunk
    if current:
        lines.append(current)
    return lines


def _break_word(font, word, max_width):
    """Hard-breaks one over-long word into max_width-sized pieces. Yields
    at least one piece for a non-empty word (a single character wider than
    max_width is emitted as-is - there is nothing narrower to fall back
    to)."""
    piece = ""
    for char in word:
        if piece and font.size(piece + char)[0] > max_width:
            yield piece
            piece = char
        else:
            piece += char
    if piece:
        yield piece


def draw_wrapped_text(surface, font, text, color, x, y, max_width, line_height=None, centerx=None):
    """Draws `text` wrapped to `max_width` and returns the y just below the
    last line - callers stack whatever comes next off that return value
    (see this module's docstring). `line_height` defaults to the font's own
    height; pass one to match a panel's existing line spacing. With
    `centerx`, lines are centered on it instead of left-aligned at `x`."""
    if not text:
        return y
    step = line_height if line_height is not None else font.get_height()
    for line in wrap_text(font, text, max_width) or [text]:
        line_surf = font.render(line, True, color)
        if centerx is not None:
            surface.blit(line_surf, line_surf.get_rect(centerx=centerx, y=y))
        else:
            surface.blit(line_surf, (x, y))
        y += step
    return y


def wrapped_text_height(font, text, max_width, line_height=None):
    """How tall draw_wrapped_text() will be - for widgets that must size a
    box/row BEFORE drawing into it (datacard tables, modal boxes)."""
    if not text:
        return 0
    step = line_height if line_height is not None else font.get_height()
    return len(wrap_text(font, text, max_width) or [text]) * step
