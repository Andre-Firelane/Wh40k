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

import re


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


def wrap_runs(fonts, runs, max_width, hanging_indent=0):
    """Wraps a sequence of styled RUNS into lines, breaking ACROSS runs.

    A run is `(text, bold)` or `(text, bold, color)`; `fonts` is
    `{False: regular, True: bold}`. Returns `[[(text, bold, color_or_None),
    ...], ...]` - one list per line, each piece carrying the style it must be
    drawn with.

    Why this cannot be wrap_text() called per run: the corpus bolds terms
    mid-sentence ("makes a **Normal** move"), so a line break has to be
    allowed to fall inside a bold run and the widths of neighbouring runs have
    to be measured with DIFFERENT fonts on the same line. Wrapping each run
    separately would put every emphasised word on a line of its own.

    `hanging_indent` narrows every line after the first, for a label whose
    continuation should sit under its own text rather than under its label.

    PIN: for a single unbolded run this agrees with wrap_text() - see
    test_text_utils. The two are kept separate on purpose rather than one
    rewritten in terms of the other: wrap_text() is on the per-frame path in
    renderer.py, game_status_panel and the datacard, and destabilising it to
    save duplication is a bad trade. The pin is what enforces one answer."""
    if max_width <= 0:
        return [[(text, bold, _run_color(run)) for run in runs
                 for text, bold in (run[:2],)]] if runs else []
    lines = []
    current = []
    limit = max_width
    # A line's width is measured per SAME-FONT SEGMENT, as whole strings -
    # not as a sum of per-word measurements. font.size(a) + font.size(b) is
    # not font.size(a + b) (bearing and advance differ), and summing words
    # fits measurably MORE per line than wrap_text() does, which would break
    # the pin below. `head` is every completed segment, `tail` the open one.
    head_width = 0
    tail_text = ""
    tail_bold = False

    def width_with(word, bold):
        """The line's width if `word` were appended - measuring the segment it
        would join as ONE string, which is what wrap_text() does."""
        if bool(bold) == tail_bold:
            return head_width + fonts[tail_bold].size(tail_text + word)[0]
        return (head_width + fonts[tail_bold].size(tail_text)[0]
                + fonts[bool(bold)].size(word)[0])

    def flush():
        nonlocal current, head_width, tail_text, tail_bold, limit
        if current:
            # Trailing whitespace draws nothing and would only widen the line;
            # dropping it is also what makes this agree with wrap_text() piece
            # for piece rather than merely line-break for line-break.
            while current and not current[-1][0].strip():
                current.pop()
        if current:
            lines.append(current)
            current = []
            head_width, tail_text, tail_bold = 0, "", False
            limit = max(1, max_width - hanging_indent)

    def add(text, bold, color):
        nonlocal head_width, tail_text, tail_bold
        if current and bool(bold) != tail_bold:
            head_width += fonts[tail_bold].size(tail_text)[0]
            tail_text = ""
        tail_bold = bool(bold)
        tail_text += text
        current.append((text, bold, color))

    for run in runs or ():
        text, bold = run[0], run[1]
        color = _run_color(run)
        font = fonts[bool(bold)]
        # Keep the run's own spaces: they separate it from its neighbours, and
        # re-joining with " " would double them.
        for word in _words(text):
            if word.isspace():
                if current:
                    add(word, bold, color)
                continue
            if current and width_with(word, bold) > limit:
                flush()
            if not current and font.size(word)[0] > limit:
                for chunk in _break_word(font, word, limit):
                    if current:
                        flush()
                    add(chunk, bold, color)
                continue
            add(word, bold, color)
    flush()
    return lines


def _run_color(run):
    return run[2] if len(run) > 2 else None


def _words(text):
    """Words and the whitespace between them, as separate pieces - so a run
    boundary that falls mid-word ("**Fall Back** move") still measures each
    side with its own font."""
    return [piece for piece in re.split(r"(\s+)", text) if piece]


def draw_rich_text(surface, fonts, runs, color, x, y, max_width,
                   line_height=None, hanging_indent=0):
    """Draws styled runs wrapped to `max_width`; returns the y below the last
    line, like draw_wrapped_text(). A run's own colour wins over `color`."""
    if not runs:
        return y
    step = line_height if line_height is not None else fonts[False].get_height()
    for index, line in enumerate(wrap_runs(fonts, runs, max_width, hanging_indent)):
        pen = x + (hanging_indent if index else 0)
        for text, bold, run_color in line:
            if not text.strip():
                pen += fonts[bool(bold)].size(text)[0]
                continue
            surf = fonts[bool(bold)].render(text, True, run_color or color)
            surface.blit(surf, (pen, y))
            pen += surf.get_width()
        y += step
    return y


def rich_text_height(fonts, runs, max_width, line_height=None, hanging_indent=0):
    """How tall draw_rich_text() will be.

    Both go through wrap_runs(), which is not tidiness: measuring with a
    different wrap than the one that draws is the hazard unit_datacard's
    _ability_height() carries a comment about, and here a mis-measure feeds
    the reader's scroll extent."""
    if not runs:
        return 0
    step = line_height if line_height is not None else fonts[False].get_height()
    return len(wrap_runs(fonts, runs, max_width, hanging_indent)) * step


def split_paragraphs(text):
    """Splits one printed paragraph into sentences, for rendering as separate
    blocks. LOSSLESS: " ".join(result) is always the whitespace-normalised
    input, so not one word changes.

    That guarantee is the whole design. A mission card prints several scoring
    clauses as one run of prose ("End of your turn: 3VP if... Also at the end of
    your turn, 1VP for... From the second battle round..."), which is unreadable
    as a block - user: "so im fliesstext ist die information sehr
    unuebersichtlich". Breaking it at sentence boundaries is the only edit that
    makes it scannable WITHOUT rewording anything, and rewording is exactly what
    was just removed from the datacard ("keine selbst generierten varianten").

    Split after . or ! followed by whitespace and a capital or digit. Measured
    over every mission text in the repo (5 Primary, 17 Secondary): 2-4 pieces
    each, zero lossy. `6"` and `Rounds 1-2` carry no full stop, so neither
    splits."""
    normalised = " ".join(text.split())
    if not normalised:
        return []
    return [piece for piece in re.split(r"(?<=[.!])\s+(?=[A-Z0-9])", normalised) if piece]
