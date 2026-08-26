"""Unit thumbnails wherever a screen talks ABOUT a unit.

User: "ich fände die portraits überall gut, wo von einheiten gesprochen wird.
in allen overlays" - after a Psychic Shield prompt that read "2 Deff Dread 1
has targeted 1 Guardian Defenders 1 + Farseer + Warlock Conclave. Until the
end of the phase..." and had to be parsed word by word to work out which two
units it meant ("der text ist mir zu unübersichtlich").

Two pieces, deliberately separate:

  draw_cell()          - the chamfered thumbnail cell itself. One definition,
                         because the Actions panel, the dice panel and every
                         overlay have to draw a unit the SAME way or the
                         player has to learn each screen's own idea of it.
  squads_named_in()    - which units a prompt string is talking about.

The second one is a string scan, which is normally the wrong tool - this
repo has already been bitten by matching sprite art on a name SUBSTRING. It
is sound here for a reason that does not generalise: these prompts are built
by interpolating `squad.name` itself, so the names in them are whole, exact
and unique, and the scan looks for those exact strings rather than guessing
at a key. The one hazard left is a name that is a prefix of another ("2 Boyz
1" inside "2 Boyz 1 + Warboss"), which is handled by matching longest-first
and consuming the match.

The alternative was to add a `squads=` argument to DecisionManager.request()
and fill it in at all 46 call sites. That is more precise per call site and
was rejected on coverage: the point of the request is that it applies
everywhere, and 46 hand-edits is 46 chances to leave one out - including
every one added later. A caller that wants to be explicit can still pass its
own squads straight to draw_row().
"""

import pygame

from game import sprites
from game.ui import button_style

BOX_PX = 46            # side of one thumbnail cell
BOX_INSET = 8          # art is fitted this much smaller than its cell
BOX_CHAMFER = 6
BOX_BG_COLOR = (8, 14, 22)  # a shade darker than button_style.BOX_BG_COLOR, so art reads as inset
GAP = 4                # between two cells of the SAME unit
UNIT_GAP = 14          # between one unit's cells and the next unit's
MAX_PER_UNIT = 2       # thumbnails per unit - see sprites.portrait_paths()


def draw_cell(surface, rect, path):
    """One thumbnail: the chamfered cell, with the art centred inside it."""
    button_style.draw_box(surface, rect, chamfer=BOX_CHAMFER, bg_color=BOX_BG_COLOR)
    art = sprites.fitted_surface(path, rect.width - BOX_INSET)
    surface.blit(art, art.get_rect(center=rect.center))


def groups_for(squads, per_unit=MAX_PER_UNIT):
    """One list of thumbnails PER unit, in order, deduped across all of them.

    Grouped rather than flattened so the row can space units further apart
    than the two thumbnails of a single attached unit (19.01) - otherwise
    "one Deff Dread and one Farseer-led Guardian mob" reads as three
    unrelated pictures instead of one and two.

    Deduped ACROSS units on purpose: two Gretchin squads in the same prompt
    would otherwise show the same picture twice and say nothing, and the
    prompt already names them both."""
    groups, seen = [], set()
    for squad in squads:
        group = []
        for path in sprites.portrait_paths(squad, limit=per_unit):
            if path not in seen:
                seen.add(path)
                group.append(path)
        if group:
            groups.append(group)
    return groups


def _laid_out(groups, box_px):
    """[(path, x offset)] for these groups, and the total width."""
    placed, x = [], 0
    for i, group in enumerate(groups):
        if i:
            x += UNIT_GAP
        for j, path in enumerate(group):
            if j:
                x += GAP
            placed.append((path, x))
            x += box_px
    return placed, x


def row_size(squads, max_width, box_px=BOX_PX, per_unit=MAX_PER_UNIT):
    """(placed thumbnails, width, height) for a single row.

    Measured separately from drawing because a box that has to hold this row
    needs its height before it can be positioned - the same
    measure-then-draw split game/ui/text_utils.py's wrapped_text_height()
    exists for. Whole units are dropped from the end rather than cut in half
    when the row will not fit, so what is shown is always some number of
    complete units."""
    groups = groups_for(squads, per_unit=per_unit)
    while groups:
        placed, width = _laid_out(groups, box_px)
        if width <= max_width:
            return placed, width, box_px
        groups.pop()
    return [], 0, 0


def draw_row(surface, squads, x, y, max_width, box_px=BOX_PX, per_unit=MAX_PER_UNIT, gap_below=8):
    """Draws the row left-aligned at (x, y) and returns the y below it -
    unchanged (and nothing drawn) when there is no art, the same "missing art
    is fine" convention sprites.sprite_for() has."""
    placed, _width, height = row_size(squads, max_width, box_px=box_px, per_unit=per_unit)
    if not placed:
        return y
    for path, offset in placed:
        draw_cell(surface, pygame.Rect(x + offset, y, box_px, box_px), path)
    return y + height + gap_below


def squads_named_in(text, squads):
    """The units `text` names, in the order their names appear in it.

    Longest name first so a unit whose name is a prefix of another's cannot
    steal the match ("2 Boyz 1" is a prefix of "2 Boyz 1 + Warboss"), and
    each match is blanked out of the working copy so a shorter name cannot
    then match the leftovers of a longer one it sits inside."""
    if not text:
        return []
    remaining = text
    found = []
    for squad in sorted(squads, key=lambda s: -len(s.name or "")):
        name = squad.name or ""
        if not name:
            continue
        at = remaining.find(name)
        if at < 0:
            continue
        found.append((at, squad))
        remaining = remaining[:at] + " " * len(name) + remaining[at + len(name):]
    return [squad for _at, squad in sorted(found, key=lambda pair: pair[0])]
