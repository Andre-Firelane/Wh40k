"""The army-rule and detachment-rule reader, opened from the right panel.

User: "es fehlt noch ein ort, wo man armeeregel und detachment regeln anschauen
kann. ich wuerde vorschlagen, das im game info panel rechts zu platzieren. dort
soll irgendwo ein kleiner link sein 'see army rules' unter den logos und
volkernamen."

Until now those two rules were the only things a player could not read anywhere
in the game. A datasheet's abilities are on the hover card, a mission's text is
on the mission strip, a Stratagem names itself on its own button - but "what
does Battle Focus actually do" and "what does Seer Council grant" existed only
in the engine and in the corpus on disk.

BOTH ARMIES, not just the reader's. Whether the opponent's army rule lets them
charge after Advancing is a fact you need in order to play against it, and it
is not deducible from the board. The reader's own army comes first.

PRINTED TEXT, from game/rules_text.py, for the same reason the unit datacard
shows printed text: a summary written here would be a note about the rule
rather than the rule (user, earlier: "keine selbst generierten varianten").

IT IS A MODAL, and it is drawn over the board rather than inside the panel:
these are several hundred words each - the Aeldari Battle Focus alone is 26
paragraphs - and the right-hand panel is 220px wide. Dismissed by a click
anywhere or by ESC, scrolled with the wheel.

ITS OWN EVENT HANDLING, called from main() BEFORE the state-gated chain: it is
a view, and every view control in that loop is polled or handled early for the
reason CLAUDE.md's error class 15 records five times over.
"""

import pygame

from game import config, rules_text
from game.ui import button_style
from game.ui import rules_body
from game.ui.rules_body import Block, RulesBody

BG_COLOR = (12, 18, 28)
BORDER_COLOR = (90, 160, 205)
SCRIM_COLOR = (0, 0, 0)
SCRIM_ALPHA = 170
TITLE_COLOR = rules_body.TITLE_COLOR
PLAYER_LABEL_COLOR = (150, 195, 225)

# RE-EXPORTED from game/ui/rules_body.py, which owns the typesetting since the
# Stratagem tooltip became its second consumer. Kept as names here so every
# reader and every pixel test that already refers to them is unchanged BY
# CONSTRUCTION rather than by being edited - the same forwarding idiom
# game/selection.py uses for selected_squad.
RULE_NAME_COLOR = rules_body.RULE_NAME_COLOR
TEXT_COLOR = rules_body.TEXT_COLOR
DIM_TEXT_COLOR = rules_body.DIM_TEXT_COLOR
RULE_LINE_COLOR = rules_body.RULE_LINE_COLOR
LABEL_COLOR = rules_body.LABEL_COLOR
STRATAGEM_NAME_COLOR = rules_body.STRATAGEM_NAME_COLOR

WIDTH_FRACTION = 0.62
HEIGHT_FRACTION = 0.82
MIN_WIDTH = 520
#: THE MEASURE, and the cause of "schwer lesbar" that has nothing to do with
#: bold or headings. Before this the panel took 62% of the screen and gave the
#: text every pixel of it: at 1600x900 that is a 937px column, and at the body
#: font's 6.19px average character that is **151 characters per line**.
#: Typographic practice puts a comfortable measure at 45-90. No amount of
#: styling rescues a line the eye cannot track back to the start of.
#: 560px is ~90 characters - the top of that range, chosen so the panel still
#: looks like a document rather than a column of poetry.
MAX_TEXT_WIDTH = 560
PADDING = 22
HEADER_HEIGHT = 44
FOOTER_HEIGHT = 26
SECTION_GAP = rules_body.SECTION_GAP
LINE_GAP = rules_body.LINE_GAP
PARAGRAPH_GAP = rules_body.PARAGRAPH_GAP
HEADING_GAP_ABOVE = rules_body.HEADING_GAP_ABOVE
RULE_GAP = rules_body.RULE_GAP
BULLET_INDENT = rules_body.BULLET_INDENT
LABEL_INDENT = rules_body.LABEL_INDENT
TABLE_VALUE_WIDTH = rules_body.TABLE_VALUE_WIDTH
SCROLL_STEP = 48
#: The keyboard half of scrolling. A page is deliberately not the full panel
#: height - overlapping by one step keeps a line of context across a page turn,
#: which is how every document reader behaves.
PAGE_STEP = SCROLL_STEP * 6
_KEY_SCROLL = {
    pygame.K_DOWN: SCROLL_STEP,
    pygame.K_UP: -SCROLL_STEP,
    pygame.K_PAGEDOWN: PAGE_STEP,
    pygame.K_PAGEUP: -PAGE_STEP,
    pygame.K_SPACE: PAGE_STEP,
    pygame.K_HOME: "home",
    pygame.K_END: "end",
}

# Same fixed per-player identity colours the mission strip and the board's
# objective markers use, so a block reads as "this is Player 1's" from the
# accent alone. Duplicated rather than imported, matching this codebase's
# usual per-module small-constant convention.
PLAYER_ACCENT_COLORS = {
    "Player 1": (70, 140, 230),
    "Player 2": (220, 60, 60),
}
DEFAULT_ACCENT_COLOR = (90, 160, 205)


class ArmyRulesOverlay:
    """Click-away reader for both armies' army rule and detachment rules."""

    def __init__(self):
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.body = RulesBody()
        # Forwarded so the pixel tests and this file's own draw() keep naming
        # the fonts they always did.
        self.player_font = self.body.player_font
        self.rule_font = self.body.rule_font
        self.heading_font = self.body.heading_font
        self.font = self.body.font
        self.bold_font = self.body.bold_font
        self.small_font = self.body.small_font
        self.body_fonts = self.body.body_fonts
        self._blocks = []
        self.scroll = 0
        self._scroll_max = 0
        self.last_rect = None
        #: The wrapped layout, cached per text width. Rebuilt only when the
        #: content or the column width changes - it used to be recomputed
        #: twice per block per frame (once to measure, once to draw).
        self._layout = None
        self._layout_width = None
        self._player = None
        #: Written while drawing, so a test can compare the PREDICTION
        #: (_content_height) against what was actually laid down. That exact
        #: comparison found a real double-counted-gap bug in the mission
        #: cards, and the gap bookkeeping here is more complicated than that.
        self._last_content_bottom = 0

    # ------------------------------------------------------------- opening

    @property
    def is_pending(self):
        return bool(self._blocks)

    def show(self, armies, player):
        """Open on ONE player's rules. `armies` is {player: army-list key},
        exactly what main() already holds; `player` is whose link was clicked.

        The full mapping is still passed rather than a single key, so this
        keeps owning the lookup and the tested "a key this build does not
        know opens nothing" degradation.

        Returns False and opens nothing when there is nothing to show - a
        harness with no army selection, say. An empty modal that has to be
        clicked away is worse than no link at all."""
        blocks = _build_blocks(armies, player)
        if not blocks:
            return False
        self._blocks = blocks
        self._player = player
        self.scroll = 0
        self._invalidate()
        return True

    def dismiss(self):
        self._blocks = []
        self._player = None
        self.scroll = 0
        self._scroll_max = 0
        self._invalidate()

    def _invalidate(self):
        self._layout = None
        self._layout_width = None

    def handle_event(self, event):
        """One event while open. True if it was consumed.

        The wheel and the keyboard scroll; ESC and a LEFT click dismiss. A left
        click ANYWHERE closes it, inside the panel included: there is nothing to
        click in here, so making the player find the edge would be a puzzle
        rather than a control.

        THE `button == 1` IS THE WHOLE OF A REPORTED BUG, not tidiness. pygame
        keeps pygame 1.x compatibility by ALSO emitting MOUSEBUTTONDOWN with
        button 4 (wheel up) / 5 (wheel down) alongside every MOUSEWHEEL, so one
        physical notch arrives as TWO events. Dismissing on any button therefore
        scrolled and closed in the same frame - and because dismiss() resets
        `scroll`, the reader could not be scrolled at all. User: "ich konnte das
        Fenster nicht scrollen. beim scrollen ging das Fenster wieder zu", and
        on being asked: "Das sollen 2 verschiedene Eingaben sein."

        This was the only handler in the repo without the check - army_select,
        game_menu, map_select and every notice branch in main.py all gate on
        button 1. No test saw it because they all send {"button": 1} and a bare
        synthetic MOUSEWHEEL, which is not the pair pygame actually delivers."""
        if not self.is_pending:
            return False
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_by(-getattr(event, "y", 0) * SCROLL_STEP)
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.dismiss()
                return True
            # A second way in, because these texts are hundreds of words and a
            # view control with exactly one route is one swallowed event away
            # from unusable - the same reasoning the army-select pager gives
            # for offering buttons, arrow keys AND the wheel.
            step = _KEY_SCROLL.get(event.key)
            if step is not None:
                if step == "home":
                    self.scroll = 0
                elif step == "end":
                    self.scroll = self._scroll_max
                else:
                    self._scroll_by(step)
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.dismiss()
            return True
        return False

    def _scroll_by(self, delta):
        """The lower bound always; the upper one only once it is REAL.

        `_scroll_max` is measured against the panel the draw pass sizes, so it
        is still 0 before the first frame - clamping against it then would
        swallow a wheel event that arrived in the same frame the reader opened.
        draw() clamps again every frame and owns what actually reaches the
        screen, so this only has to avoid going negative."""
        scroll = self.scroll + delta
        if self._scroll_max > 0:
            scroll = min(scroll, self._scroll_max)
        self.scroll = max(0, scroll)

    # ------------------------------------------------------------- drawing

    def panel_rect(self, screen_rect):
        """The panel, WIDTH-CAPPED to a readable measure.

        The cap is the point: without it the panel takes 62% of the screen and
        hands the text all of it, which at 1600x900 is 151 characters a line -
        roughly twice what is comfortable to read, and unfixable by styling.
        The panel stays as tall as before; only the column narrows."""
        chrome = 2 * PADDING + button_style.SCROLLBAR_WIDTH + 6
        width = max(MIN_WIDTH, int(screen_rect.width * WIDTH_FRACTION))
        width = min(width, MAX_TEXT_WIDTH + chrome)
        width = min(width, screen_rect.width - 2 * PADDING)
        height = min(int(screen_rect.height * HEIGHT_FRACTION),
                     screen_rect.height - 2 * PADDING)
        rect = pygame.Rect(0, 0, width, height)
        rect.center = screen_rect.center
        return rect

    def _text_width(self, rect):
        return rect.width - 2 * PADDING - button_style.SCROLLBAR_WIDTH - 6

    # ------------------------------------------------------- layout / style

    def _layout_for(self, rect):
        """[(block, y, height)] plus the total, wrapped once per width.

        Cached: this used to run on every frame from _content_height() and
        then again from draw(), so every block was wrapped twice a frame.
        The typesetting itself belongs to RulesBody - see game/ui/rules_body.py
        for why it is not in here any more."""
        width = self._text_width(rect)
        if self._layout is not None and self._layout_width == width:
            return self._layout
        self._layout = self.body.layout(self._blocks, width)
        self._layout_width = width
        return self._layout

    def _content_height(self, rect):
        return self._layout_for(rect)[1]

    def _draw_block(self, surface, block, rect, y, width):
        self.body.draw_block(surface, block, rect.x + PADDING, y, width,
                             rect.right - PADDING)

    def draw(self, surface):
        if not self.is_pending:
            return
        screen_rect = surface.get_rect()
        scrim = pygame.Surface(screen_rect.size, pygame.SRCALPHA)
        scrim.fill((*SCRIM_COLOR, SCRIM_ALPHA))
        surface.blit(scrim, (0, 0))

        rect = self.panel_rect(screen_rect)
        self.last_rect = rect.copy()
        pygame.draw.rect(surface, BG_COLOR, rect)
        pygame.draw.rect(surface, BORDER_COLOR, rect, width=2)

        title = self.title_font.render("ARMY RULES & DETACHMENTS", True, TITLE_COLOR)
        surface.blit(title, (rect.x + PADDING, rect.y + 10))
        if self._player:
            # Whose rules these are, in their own accent - with two links the
            # answer is no longer "both", so it has to be said.
            who = self.small_font.render(
                self._player.upper(), True,
                PLAYER_ACCENT_COLORS.get(self._player, DEFAULT_ACCENT_COLOR))
            surface.blit(who, who.get_rect(right=rect.right - PADDING,
                                           centery=rect.y + 10 + title.get_height() // 2))
        pygame.draw.line(surface, RULE_LINE_COLOR,
                         (rect.x + PADDING, rect.y + HEADER_HEIGHT),
                         (rect.right - PADDING, rect.y + HEADER_HEIGHT))

        body = pygame.Rect(rect.x + 1, rect.y + HEADER_HEIGHT + 6, rect.width - 2,
                           rect.height - HEADER_HEIGHT - 6 - FOOTER_HEIGHT)
        entries, content_height = self._layout_for(rect)
        self._scroll_max = max(0, content_height - body.height)
        self.scroll = max(0, min(self.scroll, self._scroll_max))

        prev_clip = surface.get_clip()
        surface.set_clip(body.clip(prev_clip) if prev_clip else body)
        width = self._text_width(rect)
        top = body.y - self.scroll
        for block, offset, height in entries:
            y = top + offset
            if y + height < body.y or y > body.bottom:
                continue   # off-screen: the layout already knows where it sits
            self._draw_block(surface, block, rect, y, width)
        self._last_content_bottom = top + content_height
        surface.set_clip(prev_clip)

        if self._scroll_max > 0:
            track = pygame.Rect(rect.right - PADDING + 4, body.y + 2,
                                button_style.SCROLLBAR_WIDTH, body.height - 4)
            button_style.draw_scrollbar(surface, track, self.scroll, self._scroll_max,
                                        body.height / float(content_height))

        hint = "wheel / PgUp / PgDn / Home / End to scroll  |  click or ESC to close"
        hint_surf = self.small_font.render(hint, True, DIM_TEXT_COLOR)
        surface.blit(hint_surf, hint_surf.get_rect(
            centerx=rect.centerx, bottom=rect.bottom - 6))


def _build_blocks(armies, player):
    """[Block] for ONE player's army rule and detachment rules.

    ONE ARMY, and that reverses this file's original loudest argument ("BOTH
    ARMIES, not just the reader's"). The reason it changed is not that the
    argument was wrong - you do need the opponent's rules, and they are still
    one click away, under THEIR badge. It is that there are two links now, so
    reaching your own no longer means scrolling past theirs. Measured on the
    shipped lists: both armies together are 1232px of content in a 662px
    window; the Necron half alone needs no scrolling at all.

    User: "außerdem sollten dort 2 links sein einer für Spieler 1 und einer
    für Spieler 2"."""
    from game import army_lists

    if not armies or player not in armies:
        return []
    try:
        entry = army_lists.get(armies[player])
    except (KeyError, SystemExit, ValueError):
        return []   # a key this build does not know: open nothing rather than crash

    accent = PLAYER_ACCENT_COLORS.get(player, DEFAULT_ACCENT_COLOR)
    blocks = [Block("player", f"{player} - {entry.name}", accent=accent),
              Block("rule", f"ARMY RULE: {entry.army_rule}")]
    blocks.extend(_rule_blocks(
        rules_text.army_rule_blocks(entry.faction_keyword, entry.army_rule)))

    for detachment in entry.detachments:
        rule_name, lines = rules_text.detachment_rule_blocks(
            entry.faction_keyword, detachment)
        heading = f"DETACHMENT: {detachment}"
        if rule_name:
            heading += f" - {rule_name}"
        blocks.append(Block("gap", ""))
        blocks.append(Block("rule", heading))
        blocks.extend(_rule_blocks(lines))
        blocks.extend(_stratagem_blocks(
            rules_text.detachment_stratagems(entry.faction_keyword, detachment)))
    return blocks


def _stratagem_blocks(stratagems):
    """A detachment's printed Stratagems, under their own sub-heading.

    User: "was noch fehlt sind die Infos zu den detachment stratagems. die
    gehören zum einen in die Army Rules overlays." The reader used to stop at
    the detachment RULE and say so in rules_text's docstring ("those are pages
    of text that belong on a screen of their own") - this is that screen, and
    the measure fix that came with the two links is what makes the pages
    readable enough to belong here.

    Each Stratagem keeps its own "### " heading (name plus CP), so the reader's
    heading style already groups them; only the "STRATAGEMS" divider is added,
    because without it a Stratagem name reads as another clause of the
    detachment rule above it."""
    if not stratagems:
        return []
    out = [Block("heading", "STRATAGEMS", new_para=True)]
    for stratagem in stratagems:
        out.append(Block("stratagem", stratagem.heading, new_para=True))
        out.extend(_rule_blocks(stratagem.lines))
    return out


def _rule_blocks(lines):
    """A rule's printed lines as blocks, with the "nothing printed" note.

    The conversion itself is rules_body.blocks_for(); what stays here is the
    note, which is a READER decision: a rule with no corpus entry is a gap in
    the snapshot, and a silently empty block reads as "this rule does
    nothing"."""
    out = rules_body.blocks_for(lines)
    if not out:
        out.append(Block("note", "(no printed text in the rules corpus)"))
    return out


def _stratagem_blocks(stratagems):
    """A detachment's printed Stratagems, under their own sub-heading.

    User: "was noch fehlt sind die Infos zu den detachment stratagems. die
    gehören zum einen in die Army Rules overlays." The reader used to stop at
    the detachment RULE and say so in rules_text's docstring ("those are pages
    of text that belong on a screen of their own") - this is that screen, and
    the measure fix that came with the two links is what makes the pages
    readable enough to belong here.

    Each Stratagem keeps its own "### " heading (name plus CP), so the reader's
    heading style already groups them; only the "STRATAGEMS" divider is added,
    because without it a Stratagem name reads as another clause of the
    detachment rule above it."""
    if not stratagems:
        return []
    out = [Block("heading", "STRATAGEMS", new_para=True)]
    for stratagem in stratagems:
        out.append(Block("stratagem", stratagem.heading, new_para=True))
        out.extend(_rule_blocks(stratagem.lines))
    return out


def _rule_blocks(lines):
    """rules_text.RuleLines as drawable blocks - one for one.

    The kinds pass straight through: the classification is a fact about the
    PRINTED text and belongs to whoever reads the corpus, not to whoever
    paints it. This function only adds what is a drawing concern - which lines
    open a new paragraph, and the note for a rule the corpus does not carry."""
    out = []
    for line in lines or ():
        text = line.text
        if not text:
            continue
        out.append(Block(line.kind, text, runs=line.runs, label=line.label,
                         cells=line.cells, new_para=line.starts_block))
    if not out:
        # Said out loud rather than left blank: a rule with no corpus entry is
        # a gap in the snapshot, and a silently empty block reads as "this
        # rule does nothing".
        out.append(Block("note", "(no printed text in the rules corpus)"))
    return out
