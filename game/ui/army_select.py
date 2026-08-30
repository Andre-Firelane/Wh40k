"""The army selection screen: who plays which of the predefined lists.

User: "ich haette gerne noch, bevor das Pre game losgeht, eine
Auswahlmoeglichkeit fuer die Voelker/listen ... Es soll Spieler 1 und Spieler 2
angezeigt werden, nacheinander, und dann kann man in grossen Kacheln
auswaehlen, welche Liste wer spielen soll. Die Darstellung der Listen wuerde
ich beschraenken auf eine Kachel mit dem Volk name/logo/detachment und dann die
Portraits der einheiten darin, was alles in der Liste drin ist. Wenn man ueber
die Portraits hovert, sieht man noch mal im Detail, was in dem Squad drin
steckt."

TWO STEPS, ONE HUMAN. User: "Aber ich waehle fuer die KI. Die KI soll nicht
selber waehlen." So this is not "a player screen and an AI screen" - the person
at the keyboard answers both steps, and Player 2's list is ASSIGNED to the AI.
Nothing here ever asks an agent anything, which is also why it can run before
one exists.

THE LISTS STAY PREDEFINED. User: "Die Listen sollen auch erstmal predefined
sein. Also, wir brauchen noch keine Listenbaukosten. Das kommt erst viel
spaeter." This screen picks WHO PLAYS WHICH of the three lists in
game/army_lists.py. It is not the army-building flow on CLAUDE.md's
Spaeter-Liste, it costs nothing, and a tile is a fixed list rather than
something to edit.

WHAT A TILE SHOWS, and why it is BUILT rather than described: the faction's
name, badge and detachment, then one portrait per UNIT in the list. The units
come from army_lists.preview_squads(), which calls the same builder main()
calls - so the tile cannot drift from what turns up on the board. A tile with
hand-written unit names would be a second copy of the army list, and drifting
from the real one is the first thing it would do.

ITS OWN LOOP, deliberately. main()'s event chain is a long if/elif over
controller state and has swallowed a keypress five times over (CLAUDE.md's
error class 15); this screen answers exactly one question, before any of those
controllers exist, so it takes the events itself and hands main() an answer.
Everything it needs to decide is a pure method (layout/tile_at/portrait_at/
choose), so the whole screen is testable without a loop at all - run() only
adds the pump.
"""

import math

import pygame

from game import army_lists, attached_units, config, loadout, sprites
from game.ui import button_style, tile_screen as ts
from game.ui.text_utils import draw_wrapped_text, wrap_text

# Everything about the frame - colors, margins, tile geometry, paging - is
# shared with the map picker, see game/ui/tile_screen.py. Only what goes INSIDE
# an army tile lives here.
BG_COLOR = ts.BG_COLOR
TITLE_COLOR = ts.TITLE_COLOR
TEXT_COLOR = ts.TEXT_COLOR
DIM_TEXT_COLOR = ts.DIM_TEXT_COLOR
TILE_BORDER_COLOR = ts.TILE_BORDER_COLOR
RULE_LINE_COLOR = ts.RULE_LINE_COLOR
SECTION_LABEL_COLOR = (150, 195, 225)
CELL_BG_COLOR = (8, 14, 22)
CELL_BORDER_HOVER_COLOR = (255, 215, 0)

MARGIN = ts.MARGIN
TILE_PAD = ts.TILE_PAD
LOGO_PX = 72
CELL_GAP = 8
CELL_CHAMFER = 6
CELL_INSET = 6
# The portrait cell size is DERIVED, not configured: one cell per unit and per
# character, all of them have to fit, and the tile's size depends on the
# window. Tried largest first, and the same size is used by EVERY tile - the
# lists have different numbers of entries, so per-tile sizing would put 150 px
# portraits next to 88 px ones on the same screen. 34 px is the floor: below it
# a portrait says nothing and the tile would be better off with text.
CELL_MAX = 168
CELL_MIN = 34
CELL_STEP = 6

DETAIL_WIDTH = 380
DETAIL_PAD = 12
DETAIL_MOUSE_OFFSET = 20

SECTION_LABEL_HEIGHT = 22
SECTION_GAP = 12
CHARACTERS = "CHARACTERS"
SQUADS = "SQUADS"


def _datasheet_label(item):
    """What to call a unit or an AttachedComponent on this screen.

    The DATASHEET name ("Farseer"), not the squad name ("1 Farseer 1"). The
    squad name is an identifier - it carries the owner's digit and a copy
    number so the AI, the map rosters and a saved scene can key on it - and
    none of that helps someone reading a tile, where every unit belongs to the
    same player anyway. Falls back to the squad/component name for anything
    not built from a datasheet, so a hand-built test squad still gets a
    label."""
    datasheet = getattr(item, "datasheet", None)
    return getattr(datasheet, "name", None) or getattr(item, "name", "?")


def detachment_summary(entry):
    """The detachments this list fields, and their total Detachment Points.

    Written here rather than on ArmyList because it is a display concern, and
    it is one function because the header and the tile must not disagree about
    what a list brings."""
    from game import detachments as detachments_module
    names = list(entry.detachments)
    if not names:
        return "no detachment"
    points = detachments_module.points_for(entry.key)
    return "%s (%d DP)" % (" + ".join(names), points)


class _Entry:
    """One picture in a tile: either a unit, or one component of an attached
    unit (19.01).

    Not one per unit any more. User: "hier wuerde ich tatsaechlich in diesem
    Screen die Charaktere von den Squads trennen, weil jetzt sieht man auf dem
    ersten Blick schlecht, welche Squads da in der Liste sind." An attached
    unit is ONE unit and its portrait is its CHARACTER (sprites.py leads with
    the most expensive one on purpose), so a list of five attached units used
    to show five characters and none of the mobs they lead - which is exactly
    the "which squads are in there" question a tile exists to answer."""

    def __init__(self, label, models, squad, is_character, partners=()):
        self.label = label          # the component's or the unit's own name
        self.models = list(models)
        self.squad = squad          # the unit it is part of, for the hover card's context
        self.is_character = is_character
        self.partners = list(partners)  # the other side of the attachment, by name
        self.path = None            # portrait, filled in during layout

    @property
    def points(self):
        return getattr(self.squad, "points", None)


class _Tile:
    """One army list's card: where it is, and what it draws."""

    def __init__(self, entry, rect, squads, characters, units):
        self.entry = entry          # army_lists.ArmyList
        self.rect = rect
        self.squads = squads
        self.characters = characters  # [_Entry]
        self.units = units            # [_Entry]
        self.cells = []             # [(pygame.Rect, _Entry)] - flat, for hit tests
        self.section_labels = []    # [(title, pygame.Rect)]


class ArmySelectScreen(ts.Paged):
    """Ask, one player at a time, which list that player fields.

    `defaults` seeds the highlighted list per player (config.PLAYER1_ARMY /
    PLAYER2_ARMY) so the screen opens on what a run without it would have
    fielded. Both players may pick the SAME list: squad names carry the owner's
    digit (army_lists.unit_name()), so a mirror match is two distinct armies
    everywhere it matters."""

    def __init__(self, defaults=None, players=("Player 1", "Player 2"), lists=None):
        self.players = tuple(players)
        self.init_paging(lists if lists is not None else army_lists.ARMY_LISTS)
        self.defaults = dict(defaults or {})
        self.step = 0
        self.choices = {}
        self.cancelled = False
        self.hovered_tile = None    # index into self.tiles
        self.hovered_entry = None   # the _Entry under the cursor, if any
        self.tiles = []
        self.back_rect = None
        self.prev_rect = None
        self.next_rect = None
        self._preview_cache = {}
        self._entry_cache = {}
        fonts = ts.make_fonts()
        self.fonts = fonts
        self.title_font = fonts["title"]
        self.subtitle_font = fonts["subtitle"]
        self.name_font = fonts["name"]
        self.label_font = fonts["label"]
        self.font = fonts["body"]
        self.small_font = fonts["small"]

    # -- state ------------------------------------------------------------
    @property
    def current_player(self):
        """Whose turn it is to be given a list, or None once both have one."""
        return self.players[self.step] if self.step < len(self.players) else None

    @property
    def done(self):
        return self.cancelled or self.step >= len(self.players)

    def turn_page(self, delta):
        """Page, and drop the hover with it - the tile under the cursor is
        gone once the page has changed."""
        if not super().turn_page(delta):
            return False
        self.hovered_tile = None
        self.hovered_entry = None
        self.tiles = []
        return True

    def preview(self, key, owner):
        """This list, built for this owner - cached, because the screen asks
        for it every frame it draws and building an army is not free.

        Per OWNER and not once per list: a squad's name starts with the
        owner's digit, and the hover detail shows that name."""
        cache_key = (key, owner)
        if cache_key not in self._preview_cache:
            self._preview_cache[cache_key] = army_lists.preview_squads(key, owner)
        return self._preview_cache[cache_key]

    def choose(self, key):
        """Give the current player this list and move on."""
        player = self.current_player
        if player is None:
            return False
        army_lists.get(key)  # refuses an unknown key loudly rather than storing it
        self.choices[player] = key
        self.step += 1
        self.hovered_tile = None
        self.hovered_entry = None
        self.tiles = []
        return True

    def back(self):
        """Undo the previous step - a misclick on Player 1 should not mean
        restarting the program."""
        if self.step == 0:
            return False
        self.step -= 1
        self.choices.pop(self.players[self.step], None)
        self.hovered_tile = None
        self.hovered_entry = None
        self.tiles = []
        return True

    # -- layout -----------------------------------------------------------
    def entries_for(self, key, owner):
        """(characters, units) for this list - the two groups a tile draws.

        An attached unit (19.01) contributes its leader/support components to
        the first group and its bodyguard to the second, so a Farseer-led
        Guardian mob shows up as a Farseer AND as Guardian Defenders. A unit
        that was never attached goes in whole, to whichever group its models'
        CHARACTER keyword puts it in - which is what keeps a lone Illuminor
        Szeras out of the squad column."""
        cache_key = (key, owner)
        if cache_key in self._entry_cache:
            return self._entry_cache[cache_key]

        characters, units = [], []
        for squad in self.preview(key, owner):
            components = attached_units.components(squad)
            if not components:
                is_character = bool(squad.models) and all(
                    m.profile.character for m in squad.models)
                entry = _Entry(_datasheet_label(squad), squad.models, squad, is_character)
                (characters if is_character else units).append(entry)
                continue
            for component in components:
                partners = [_datasheet_label(c) for c in components if c is not component]
                entry = _Entry(_datasheet_label(component), component.starting_models, squad,
                               component.is_leader_or_support, partners)
                (characters if component.is_leader_or_support else units).append(entry)

        for entry in characters + units:
            paths = sprites.models_portrait_paths(entry.models, limit=1)
            entry.path = paths[0] if paths else None
        self._entry_cache[cache_key] = (characters, units)
        return characters, units

    def layout(self, screen_rect):
        """Place this page's tiles (and their portrait cells) inside the
        screen, and return them.

        Recomputed per draw rather than cached: it depends on the step (whose
        army the previews are built for), on the page, and on the window size,
        and it is a few dozen rects."""
        player = self.current_player
        if player is None:
            self.tiles = []
            return self.tiles

        area = ts.tile_area(screen_rect)
        per_page = self.fit_page(area.width)
        page_lists = self.page_items
        tile_width = (area.width - ts.TILE_GAP * (per_page - 1)) // per_page

        # The cell size is worked out from EVERY list, not just this page's, so
        # paging does not resize the portraits under the cursor. The tile
        # HEIGHT is this page's own, so a page of short lists is not left
        # carrying a page of long lists' empty space.
        all_entries = [self.entries_for(item.key, player) for item in self.items]
        cell_px, columns = self._cell_size(tile_width, all_entries, area.height)
        page_entries = [self.entries_for(item.key, player) for item in page_lists]
        character_rows = max((math.ceil(len(chars) / columns) for chars, _u in page_entries),
                             default=0)
        unit_rows = max((math.ceil(len(units) / columns) for _c, units in page_entries), default=0)
        tile_height = min(
            area.height,
            self._header_height()
            + self._grid_height(character_rows, unit_rows, cell_px) + TILE_PAD,
        )

        rects = ts.tile_rects(area, per_page, len(page_lists), tile_height)
        tiles = []
        for list_entry, rect in zip(page_lists, rects):
            characters, units = self.entries_for(list_entry.key, player)
            tile = _Tile(list_entry, rect, self.preview(list_entry.key, player), characters, units)
            self._lay_out_sections(tile, cell_px, columns, character_rows)
            tiles.append(tile)
        self.tiles = tiles
        return tiles

    def _header_height(self):
        """How much of a tile the badge, name, detachment and summary take,
        measured off the fonts rather than guessed - the grid starts below it
        and the tile's height is built from it."""
        return TILE_PAD + max(LOGO_PX, 3 * self.font.get_height() + 26) + 18

    def _grid_height(self, character_rows, unit_rows, cell_px):
        """How tall the two labelled sections are together."""
        height = 0
        for rows in (character_rows, unit_rows):
            if rows <= 0:
                continue
            if height:
                height += SECTION_GAP
            height += SECTION_LABEL_HEIGHT + rows * (cell_px + CELL_GAP) - CELL_GAP
        return height

    def _grid_top(self, tile):
        """Where a tile's first section starts: below the badge/name header."""
        return tile.rect.y + self._header_height()

    def _cell_size(self, tile_width, entries_per_list, available_height):
        """(cell px, columns) - the largest square that still fits every list's
        two sections into one tile, tried from CELL_MAX down."""
        inner_width = tile_width - 2 * TILE_PAD
        budget = available_height - self._header_height() - TILE_PAD
        if not entries_per_list or inner_width <= 0 or budget <= 0:
            return CELL_MIN, 1
        for candidate in range(CELL_MAX, CELL_MIN - 1, -CELL_STEP):
            columns = max(1, (inner_width + CELL_GAP) // (candidate + CELL_GAP))
            # The CHARACTER rows are RESERVED at the page maximum for every
            # tile (see _lay_out_sections), so a tile is as tall as
            # "everyone's character rows + ITS OWN squad rows" - not as its own
            # two sections added up. Sizing on the latter under-measures
            # exactly the tile with few characters and many squads, and the
            # tile height then gets clamped to the area while its cells spill
            # out the bottom.
            #
            # This was latent for a while: with seven Aeldari characters and
            # thirteen squads that list's own total happened to equal the Orks
            # tile's real need, so the wrong formula produced the right number.
            # Giving the Aeldari leaders their CHARACTER keyword moved one unit
            # between the two sections and the coincidence broke.
            reserved_character_rows = max(
                math.ceil(len(chars) / columns) for chars, _units in entries_per_list
            )
            worst = max(
                self._grid_height(reserved_character_rows,
                                  math.ceil(len(units) / columns), candidate)
                for _chars, units in entries_per_list
            )
            if worst <= budget:
                return candidate, columns
        return CELL_MIN, max(1, (inner_width + CELL_GAP) // (CELL_MIN + CELL_GAP))

    def _lay_out_sections(self, tile, cell_px, columns, character_rows):
        """Fill tile.cells and tile.section_labels.

        `character_rows` is the PAGE's maximum rather than this tile's, so the
        SQUADS label sits at the same height in every tile - two lists with
        different numbers of characters would otherwise stagger their section
        headers and the split would read as noise instead of as structure."""
        # Centred horizontally: the column count is shared by all tiles and the
        # cell size is derived, so a tile whose list is one row short would
        # otherwise sit against its left edge with a visible gap on the right.
        grid_width = columns * (cell_px + CELL_GAP) - CELL_GAP
        left = tile.rect.x + max(TILE_PAD, (tile.rect.width - grid_width) // 2)
        label_left = tile.rect.x + TILE_PAD

        cells, labels = [], []
        y = self._grid_top(tile)
        for title, entries, reserved_rows in ((CHARACTERS, tile.characters, character_rows),
                                              (SQUADS, tile.units, None)):
            rows = math.ceil(len(entries) / columns) if entries else 0
            if reserved_rows is not None:
                rows = max(rows, reserved_rows)
            if rows <= 0:
                continue
            labels.append((title, pygame.Rect(label_left, y,
                                              tile.rect.width - 2 * TILE_PAD,
                                              SECTION_LABEL_HEIGHT)))
            top = y + SECTION_LABEL_HEIGHT
            for index, entry in enumerate(entries):
                row, column = divmod(index, columns)
                cells.append((pygame.Rect(left + column * (cell_px + CELL_GAP),
                                          top + row * (cell_px + CELL_GAP),
                                          cell_px, cell_px), entry))
            y = top + rows * (cell_px + CELL_GAP) - CELL_GAP + SECTION_GAP
        tile.cells = cells
        tile.section_labels = labels

    # -- hit tests --------------------------------------------------------
    def tile_at(self, pos):
        """Index of the tile under `pos`, or None."""
        for index, tile in enumerate(self.tiles):
            if tile.rect.collidepoint(pos):
                return index
        return None

    def portrait_at(self, pos):
        """The _Entry whose portrait is under `pos`, or None - what the hover
        detail card describes. An entry, not a unit: a tile splits an attached
        unit into its character and its squad, and the card describes whichever
        half is actually under the cursor."""
        for tile in self.tiles:
            if not tile.rect.collidepoint(pos):
                continue
            for rect, entry in tile.cells:
                if rect.collidepoint(pos):
                    return entry
        return None

    def track_pointer(self, pos):
        self.hovered_tile = self.tile_at(pos)
        self.hovered_entry = self.portrait_at(pos)

    def handle_event(self, event, screen_rect):
        """One event. Returns True while the screen still wants the loop."""
        if event.type == pygame.QUIT:
            self.cancelled = True
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            # Same meaning ESC has everywhere else in fullscreen: quit. Going
            # back a step is the Back button / right-click, so the two are not
            # competing for one key.
            self.cancelled = True
            return False
        if event.type == pygame.MOUSEMOTION:
            self.layout(screen_rect)
            self.track_pointer(event.pos)
            return True
        # Paging, for when there are more lists than one screen of tiles. Three
        # ways in on purpose: the two buttons for the mouse, the arrow keys,
        # and the wheel - none of them can be swallowed here, because this
        # screen is not the state-gated chain main() uses (error class 15).
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.turn_page(-1 if event.key == pygame.K_LEFT else 1)
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.turn_page(-1 if getattr(event, "y", 0) > 0 else 1)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.back()
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.layout(screen_rect)
            for rect, delta in ((self.prev_rect, -1), (self.next_rect, 1)):
                if rect is not None and rect.collidepoint(event.pos):
                    self.turn_page(delta)
                    return True
            if self.back_rect is not None and self.back_rect.collidepoint(event.pos):
                self.back()
                return True
            index = self.tile_at(event.pos)
            if index is not None:
                self.choose(self.tiles[index].entry.key)
            return not self.done
        return True

    # -- drawing ----------------------------------------------------------
    def draw(self, surface, mouse_pos=None):
        screen_rect = surface.get_rect()
        surface.fill(BG_COLOR)
        self.layout(screen_rect)
        if mouse_pos is not None:
            self.track_pointer(mouse_pos)
        self._draw_header(surface, screen_rect)
        for index, tile in enumerate(self.tiles):
            self._draw_tile(surface, tile, hovered=(index == self.hovered_tile))
        self._draw_footer(surface, screen_rect)
        if self.hovered_entry is not None and mouse_pos is not None:
            self._draw_detail(surface, self.hovered_entry, mouse_pos)

    def hint(self):
        """The line under the title.

        A method rather than an inline string because the second step's wording
        is a user requirement, not decoration: the person at the keyboard picks
        the AI's list as well ("Aber ich waehle fuer die KI. Die KI soll nicht
        selber waehlen"), and that is the one thing about this screen that
        could otherwise be misread. Pinned as such in test_army_select.py."""
        if self.current_player == self.players[0]:
            return "Click a list to field it. Hover a portrait for that unit's loadout."
        return ("You pick the AI's list too - it never chooses its own. "
                "Right-click or Back to redo Player 1.")

    def _draw_header(self, surface, screen_rect):
        player = self.current_player
        notes = []
        for done_player in self.players:
            key = self.choices.get(done_player)
            if key is None:
                continue
            entry = army_lists.get(key)
            notes.append((f"{done_player}: {entry.name} ({detachment_summary(entry)})",
                          ts.PLAYER_ACCENT_COLORS.get(done_player, TEXT_COLOR)))
        ts.draw_header(
            surface, screen_rect, self.fonts,
            f"{player} - CHOOSE ARMY LIST" if player else "ARMY LISTS CHOSEN",
            self.hint(),
            ts.PLAYER_ACCENT_COLORS.get(player, ts.DEFAULT_ACCENT_COLOR),
            notes=notes,
        )

    def _draw_tile(self, surface, tile, hovered=False):
        entry = tile.entry
        rect = tile.rect
        ts.draw_tile_frame(surface, rect, hovered=hovered)

        # Badge. Missing art is fine (sprites.py's convention throughout), and
        # the name carries the identity either way.
        text_x = rect.x + TILE_PAD
        logo_path = sprites.faction_logo_path(entry.faction_keyword)
        if logo_path is not None:
            art = sprites.fitted_surface(logo_path, LOGO_PX)
            surface.blit(art, art.get_rect(center=(rect.x + TILE_PAD + LOGO_PX // 2,
                                                   rect.y + TILE_PAD + LOGO_PX // 2)))
            text_x += LOGO_PX + 14

        y = rect.y + TILE_PAD
        text_width = rect.right - TILE_PAD - text_x
        for line in wrap_text(self.name_font, entry.name, text_width) or [entry.name]:
            surface.blit(self.name_font.render(line, True, TITLE_COLOR), (text_x, y))
            y += self.name_font.get_height()
        # EVERY detachment the list declares, with what they cost: a list may
        # field several, and they belong to the list rather than being chosen
        # later, so the tile is the only place they are ever shown.
        surface.blit(self.font.render(detachment_summary(entry), True, TEXT_COLOR),
                     (text_x, y + 2))
        y += self.font.get_height() + 4
        surface.blit(self.small_font.render(entry.army_rule, True, DIM_TEXT_COLOR), (text_x, y + 2))

        # What the list actually is, counted off the built units rather than
        # written down next to them. Points come from the published lists
        # (Squad.points); a list with an untranscribed entry says so instead of
        # quoting a total that quietly left it out.
        models = sum(len(s.models) for s in tile.squads)
        priced = [s.points for s in tile.squads if s.points is not None]
        summary = f"{len(tile.squads)} units | {models} models"
        if len(priced) == len(tile.squads):
            summary += f" | {sum(priced)} pts"
        else:
            summary += f" | {sum(priced)} pts (+{len(tile.squads) - len(priced)} unpriced)"
        grid_top = self._grid_top(tile)
        surface.blit(self.label_font.render(summary, True, TEXT_COLOR),
                     (rect.x + TILE_PAD, grid_top - self.label_font.get_height() - 8))
        pygame.draw.line(surface, RULE_LINE_COLOR,
                         (rect.x + TILE_PAD, grid_top - 4), (rect.right - TILE_PAD, grid_top - 4))

        # CHARACTERS / SQUADS, each under its own label. Without the split a
        # list of attached units showed five characters and none of the mobs
        # they lead, because an attached unit is one unit and its portrait is
        # its character - user: "jetzt sieht man auf dem ersten Blick schlecht,
        # welche Squads da in der Liste sind".
        for title, label_rect in tile.section_labels:
            count = len(tile.characters if title == CHARACTERS else tile.units)
            surface.blit(self.small_font.render(f"{title}  ({count})", True, SECTION_LABEL_COLOR),
                         (label_rect.x, label_rect.y + 2))
            line_y = label_rect.y + SECTION_LABEL_HEIGHT - 5
            text_width = self.small_font.size(f"{title}  ({count})")[0]
            pygame.draw.line(surface, RULE_LINE_COLOR,
                             (label_rect.x + text_width + 10, line_y), (label_rect.right, line_y))

        for cell_rect, cell_entry in tile.cells:
            cell_hovered = cell_entry is self.hovered_entry
            button_style.draw_box(
                surface, cell_rect, chamfer=CELL_CHAMFER, bg_color=CELL_BG_COLOR,
                border_color=CELL_BORDER_HOVER_COLOR if cell_hovered else TILE_BORDER_COLOR,
                border_width=2 if cell_hovered else 1,
            )
            if cell_entry.path is not None:
                art = sprites.fitted_surface(cell_entry.path, cell_rect.width - CELL_INSET * 2)
                surface.blit(art, art.get_rect(center=cell_rect.center))

    def _draw_footer(self, surface, screen_rect):
        self.back_rect, self.prev_rect, self.next_rect = ts.draw_footer(
            surface, screen_rect, self.fonts, self.page, self.page_count,
            back_label="Back" if self.step > 0 and not self.done else None,
        )

    def _detail_lines(self, entry):
        """What a hovered portrait is made of: its model lines with counts and
        weapons, straight out of game/loadout.py - the same description the
        pre-game's transport buttons use, so a unit reads the same wherever it
        is talked about.

        For half of an attached unit it also names the other half. Without that
        the split loses information the un-split tile had: "Farseer" and
        "Guardian Defenders" as two separate pictures do not say that they are
        one unit on the table (19.01), and that is a fact about the army list,
        not a detail."""
        header = [entry.label]
        second = f"{len(entry.models)} model" + ("" if len(entry.models) == 1 else "s")
        if entry.points is not None:
            second += f" | {entry.points} pts (unit)"
        header.append(second)
        lines = loadout.model_loadout_lines(entry.models)
        if entry.partners:
            joined = ", ".join(entry.partners)
            lines = lines + [
                ("Leads " if entry.is_character else "Led by ") + joined + " - one unit (19.01)"]
        return header, lines

    def _draw_detail(self, surface, entry, mouse_pos):
        header, lines = self._detail_lines(entry)
        text_width = DETAIL_WIDTH - 2 * DETAIL_PAD
        line_height = self.font.get_height() + 2

        height = DETAIL_PAD * 2
        height += self.label_font.get_height() + 2
        height += self.small_font.get_height() + 8
        for line in lines:
            height += max(1, len(wrap_text(self.font, line, text_width))) * line_height + 2

        box = pygame.Rect(0, 0, DETAIL_WIDTH, height)
        box.topleft = (mouse_pos[0] + DETAIL_MOUSE_OFFSET, mouse_pos[1] + DETAIL_MOUSE_OFFSET)
        screen_rect = surface.get_rect()
        # Kept on screen the same way the Ctrl+hover datacard is: flipped to
        # the other side of the cursor rather than clamped onto it, so the card
        # never covers the portrait it describes.
        if box.right > screen_rect.right:
            box.right = mouse_pos[0] - DETAIL_MOUSE_OFFSET
        if box.bottom > screen_rect.bottom:
            box.bottom = max(screen_rect.top, mouse_pos[1] - DETAIL_MOUSE_OFFSET)
        box.top = max(screen_rect.top, box.top)
        box.left = max(screen_rect.left, box.left)

        button_style.draw_box(surface, box, chamfer=CELL_CHAMFER, bg_color=(14, 22, 34),
                              border_color=CELL_BORDER_HOVER_COLOR, border_width=2)
        y = box.y + DETAIL_PAD
        surface.blit(self.label_font.render(header[0], True, TITLE_COLOR), (box.x + DETAIL_PAD, y))
        y += self.label_font.get_height() + 2
        surface.blit(self.small_font.render(header[1], True, DIM_TEXT_COLOR), (box.x + DETAIL_PAD, y))
        y += self.small_font.get_height() + 8
        for line in lines:
            y = draw_wrapped_text(surface, self.font, line, TEXT_COLOR,
                                  box.x + DETAIL_PAD, y, text_width, line_height=line_height) + 2

    # -- the loop ---------------------------------------------------------
    def run(self, screen, clock=None):
        """Pump events until both players have a list. Returns
        {player -> army key}, or None if the player quit out of the screen -
        which main() treats as "close the program", the same as ESC anywhere
        else in fullscreen."""
        ts.run_screen(screen, self, clock)
        return None if self.cancelled else dict(self.choices)
