"""The battlefield picker: which map this battle is fought on.

User: "Vor der Fraktion würde ich jetzt allerdings gerne noch die Map
auswählen. Da wäre es cool, wenn ein Screenshot der Map angeboten werden
würde." So it runs FIRST - before the army lists, and long before rule 03.01's
pre-game sequence - because everything downstream depends on it: the board
size goes into config, the deployment zones and terrain come from it, and on a
small board the map decides which units are even fielded
(BattleMap.army_roster).

The tile is the map's own picture, rendered from the map rather than
screenshotted (see game/ui/map_preview.py for why), plus its name, its
dimensions and what is actually on it.

AND THE BIOME, on three buttons across the top (User: "es gibt jetzt 3 biome.
kannst du bei der map auswahl bitte ganz oben noch 3 knoepfe reinpacken, ueber
die man sein biom waehlen kann?"). They belong on THIS screen and not on one
of their own because the tiles below them are pictures of the board: clicking
a biome repaints all of them, so the choice is made by looking at it rather
than by reading three words. Purely cosmetic - see game/biomes.py; the map
buttons decide the game, these decide what it is painted in.

They sit INSIDE the header bar rather than in a strip of their own so the
tiles keep their full height - the previews size their box from whatever is
left over, and a row above them would shrink every board picture on the
screen. Drawn here rather than in tile_screen.py because the army picker has
no use for them, and this repo extracts at the SECOND consumer, not the first.

Frame, paging and loop are shared with the army picker - see
game/ui/tile_screen.py. Only the tile content lives here.
"""

import pygame

from game import biomes, config, maps
from game.game_state import GameState
from game.ui import button_style, map_preview, tile_screen as ts
from game.ui.text_utils import wrap_text

TITLE_COLOR = ts.TITLE_COLOR
TEXT_COLOR = ts.TEXT_COLOR
DIM_TEXT_COLOR = ts.DIM_TEXT_COLOR
ACCENT_COLOR = (120, 190, 150)   # a colour of its own, so the map step is not mistaken for a player's

TILE_PAD = ts.TILE_PAD
PREVIEW_BORDER_COLOR = (70, 100, 130)
PREVIEW_BG_COLOR = (6, 10, 16)

# The biome row, right-aligned inside the header bar. Measured rather than
# guessed: the heading and its hint line end 382 px in at every window size
# (they are fixed strings), and the row below is 3*150 + 2*10 + a label, so it
# clears them by ~380 px even on a 1280-wide window - the narrowest this game
# is run at. The buttons are vertically centred in the bar.
BIOME_BUTTON_WIDTH = 150
BIOME_BUTTON_HEIGHT = 38
BIOME_BUTTON_GAP = 10
BIOME_LABEL_GAP = 16


class _Tile:
    def __init__(self, battle_map, rect, preview_rect):
        self.battle_map = battle_map
        self.rect = rect
        self.preview_rect = preview_rect


def map_facts(battle_map):
    """(deployment line, contents line) for one map, counted off the BUILT
    board rather than written down beside it - the same reason an army tile
    builds its list instead of describing it. A map whose terrain is
    re-measured updates its own tile.

    Deliberately not the board size: the map's own name already carries that
    ("Take Cover (44\"x60\", portrait)"), and repeating it wastes the line. How
    deep the zones are and how much open ground lies between them is the thing
    a picture does not tell you and that decides how fast the armies meet."""
    state = GameState()
    battle_map.build(state)
    blocking = sum(1 for o in state.obstacles if getattr(o, "blocks_line_of_sight", False))

    # Both numbers are measured off the built zones rather than read out of a
    # rectangle, because a zone need not BE a rectangle - map 3 deploys in
    # opposite corners with the middle bitten out. Written as one definition
    # each rather than a rectangle case plus a shape case: for the two band
    # maps these reproduce exactly the numbers the rectangle arithmetic gave
    # (18"/24" and 12"/20"), and they keep meaning something for any shape.
    #
    #   depth         - how far from the nearest board edge a zone reaches.
    #                   For a band across the table that IS its depth.
    #   no man's land - the shortest distance between the two zones, i.e. the
    #                   ground the armies have to cross to meet.
    step = 0.5
    xs = [i * step for i in range(int(battle_map.width_in / step) + 1)]
    ys = [j * step for j in range(int(battle_map.height_in / step) + 1)]
    depth = 0.0
    points = {}
    for zone in state.deployment_zones:
        inside = [(x, y) for x in xs for y in ys if zone.contains_point(x, y)]
        points[zone.owner] = inside
        for x, y in inside:
            depth = max(depth, min(x, battle_map.width_in - x, y, battle_map.height_in - y))
    no_mans_land = 0.0
    zones = list(state.deployment_zones)
    if len(zones) >= 2 and all(points.get(z.owner) for z in zones[:2]):
        # The TRUE closest approach, as a nearest-point search between the two
        # sampled zones - deliberately not zone.distance_to_point(), which for
        # a shape built as an intersection measures to the nearest constraint
        # LINE and so understates the gap outside a corner (see game/shapes.py).
        # On map 3 that difference is 6.5" against the real 16.6".
        # Sampled at 1" rather than the 0.5" the depth uses: this is a product
        # of two point sets, and the band maps' zone edges land on whole
        # inches anyway, so their numbers stay exact.
        coarse = {owner: [(x, y) for (x, y) in pts
                          if x == int(x) and y == int(y)]
                  for owner, pts in points.items()}
        a_pts = coarse[zones[0].owner] or points[zones[0].owner]
        b_pts = coarse[zones[1].owner] or points[zones[1].owner]
        best = None
        for ax, ay in a_pts:
            for bx, by in b_pts:
                d2 = (ax - bx) ** 2 + (ay - by) ** 2
                if best is None or d2 < best:
                    best = d2
        no_mans_land = round(best ** 0.5, 1)
    deployment = f'zones {depth:g}" deep  |  {no_mans_land:g}" of no man\'s land'
    contents = (f"{len(state.obstacles)} terrain features "
                f"({blocking} block line of sight)  |  {len(state.objectives)} objectives")
    return deployment, contents


class MapSelectScreen(ts.Paged):
    """One step: pick the battlefield. `default` only seeds which map the
    screen opens on; there is nothing to pre-select visually, because a click
    ends the screen immediately."""

    def __init__(self, default=None, battle_maps=None):
        self.init_paging(battle_maps if battle_maps is not None else list(maps.MAPS.values()))
        self.default = default
        self.chosen = None
        self.cancelled = False
        self.hovered_tile = None
        self.tiles = []
        self.prev_rect = None
        self.next_rect = None
        self.biome_rects = {}   # biome key -> its button rect, set by layout()
        self.fonts = ts.make_fonts()
        self._facts = {}

    # -- state ------------------------------------------------------------
    @property
    def done(self):
        return self.cancelled or self.chosen is not None

    def facts(self, battle_map):
        if battle_map.key not in self._facts:
            self._facts[battle_map.key] = map_facts(battle_map)
        return self._facts[battle_map.key]

    @property
    def biome(self):
        """The biome currently painted on the tiles - read straight off the
        live setting rather than mirrored into a field of its own, so the
        picker cannot come to disagree with what the renderer will use."""
        return biomes.current().key

    def choose_biome(self, biome_key):
        """Repaint the battlefields in this biome. Returns False for a key
        that changes nothing, so a caller can tell a real click from a
        repeated one.

        THIS WRITES config.BIOME, and that is deliberate rather than sloppy -
        it is the same thing the army picker does to PLAYER1_ARMY/
        PLAYER2_ARMY, and this screen is the picker for this setting. Note it
        is NOT the rule game/ui/map_preview.py's docstring lays down: what
        that forbids is a PREVIEW writing the board's dimensions, i.e.
        deciding the battlefield merely by having been looked at. Nothing is
        decided here by looking - only by clicking - and a biome decides
        nothing about the game in any case; it is the paint.

        Writing it live is also what makes the tiles answer: the previews and
        the renderer both read the setting, so there is one answer to "which
        biome", not a chosen one and a drawn one."""
        if biome_key not in biomes.BIOMES_BY_KEY or biome_key == self.biome:
            return False
        config.BIOME = biome_key
        return True

    def choose(self, battle_map):
        self.chosen = battle_map
        return True

    def turn_page(self, delta):
        if not super().turn_page(delta):
            return False
        self.hovered_tile = None
        self.tiles = []
        return True

    # -- layout -----------------------------------------------------------
    def _text_height(self):
        """Room under the picture: name, size line, contents line."""
        return (self.fonts["name"].get_height()
                + self.fonts["body"].get_height()
                + self.fonts["small"].get_height() + 22)

    def biome_layout(self, screen_rect):
        """Rect per biome button, right-aligned inside the header bar, in
        BIOMES order. Laid out here rather than while drawing so a click can
        be hit-tested before the first frame is on screen - the event handler
        calls layout() and then asks, exactly like it does for the tiles."""
        bar = ts.header_bar(screen_rect)
        y = bar.y + (bar.height - BIOME_BUTTON_HEIGHT) // 2
        total = (len(biomes.BIOMES) * BIOME_BUTTON_WIDTH
                 + (len(biomes.BIOMES) - 1) * BIOME_BUTTON_GAP)
        x = bar.right - ts.MARGIN - total
        rects = {}
        for biome in biomes.BIOMES:
            rects[biome.key] = pygame.Rect(x, y, BIOME_BUTTON_WIDTH, BIOME_BUTTON_HEIGHT)
            x += BIOME_BUTTON_WIDTH + BIOME_BUTTON_GAP
        self.biome_rects = rects
        return rects

    def layout(self, screen_rect):
        self.biome_layout(screen_rect)
        area = ts.tile_area(screen_rect)
        per_page = self.fit_page(area.width)
        page = self.page_items
        tile_width = (area.width - ts.TILE_GAP * (per_page - 1)) // per_page

        # ONE preview box for every tile - same width, same height - filling
        # whatever is left once the text has its room. Each board is
        # letterboxed inside it (see map_preview.surface_for), so a portrait
        # board and a landscape one line up instead of each setting its own
        # height, and the difference in shape stays visible.
        box_width = max(40, tile_width - 2 * TILE_PAD)
        box_height = max(40, area.height - self._text_height() - 2 * TILE_PAD)
        tile_height = min(area.height, box_height + self._text_height() + 2 * TILE_PAD)

        rects = ts.tile_rects(area, per_page, len(page), tile_height)
        self.tiles = []
        for battle_map, rect in zip(page, rects):
            preview_rect = pygame.Rect(0, 0, box_width, box_height)
            preview_rect.midtop = (rect.centerx, rect.y + TILE_PAD)
            self.tiles.append(_Tile(battle_map, rect, preview_rect))
        return self.tiles

    # -- hit tests --------------------------------------------------------
    def tile_at(self, pos):
        for index, tile in enumerate(self.tiles):
            if tile.rect.collidepoint(pos):
                return index
        return None

    def biome_at(self, pos):
        for key, rect in self.biome_rects.items():
            if rect.collidepoint(pos):
                return key
        return None

    def track_pointer(self, pos):
        self.hovered_tile = self.tile_at(pos)

    def handle_event(self, event, screen_rect):
        if event.type == pygame.QUIT:
            self.cancelled = True
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.cancelled = True
            return False
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.turn_page(-1 if event.key == pygame.K_LEFT else 1)
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.turn_page(-1 if getattr(event, "y", 0) > 0 else 1)
            return True
        if event.type == pygame.MOUSEMOTION:
            self.layout(screen_rect)
            self.track_pointer(event.pos)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.layout(screen_rect)
            # The biome row is asked FIRST. It does not overlap the tiles
            # geometrically - it is up in the header and they are below it -
            # but ordering it explicitly is the cheap half of CLAUDE.md error
            # class 15, which this repo has paid for five times: a control
            # that only answers when nothing above it happened to match is one
            # refactor away from never answering. Picking a biome is NOT
            # picking a map, so this returns instead of falling through.
            biome_key = self.biome_at(event.pos)
            if biome_key is not None:
                self.choose_biome(biome_key)
                return True
            for rect, delta in ((self.prev_rect, -1), (self.next_rect, 1)):
                if rect is not None and rect.collidepoint(event.pos):
                    self.turn_page(delta)
                    return True
            index = self.tile_at(event.pos)
            if index is not None:
                self.choose(self.tiles[index].battle_map)
            return not self.done
        return True

    # -- drawing ----------------------------------------------------------
    def draw(self, surface, mouse_pos=None):
        screen_rect = surface.get_rect()
        surface.fill(ts.BG_COLOR)
        self.layout(screen_rect)
        if mouse_pos is not None:
            self.track_pointer(mouse_pos)
        ts.draw_header(
            surface, screen_rect, self.fonts, "CHOOSE THE BATTLEFIELD",
            "Click a map to play on it. The armies come next.", ACCENT_COLOR,
        )
        self._draw_biome_row(surface, screen_rect, mouse_pos)
        for index, tile in enumerate(self.tiles):
            self._draw_tile(surface, tile, hovered=(index == self.hovered_tile))
        self.prev_rect, self.next_rect = ts.draw_footer(
            surface, screen_rect, self.fonts, self.page, self.page_count)[1:]

    def _draw_biome_row(self, surface, screen_rect, mouse_pos=None):
        """The three biome buttons, plus the word BIOME so a first-time player
        knows what they are - unlabelled, "CITY / DESERT / FOREST" beside a map
        list reads as three more maps.

        The selected one is drawn PRESSED (button_style's active palette), not
        merely differently coloured: this is a three-way toggle where one is
        always on, and "pressed" is the state the shared button already has for
        exactly that. Nothing else on this screen has a persistent state, so it
        cannot be confused with a hover."""
        rects = self.biome_layout(screen_rect)
        mouse = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
        selected = self.biome

        first = rects[biomes.BIOMES[0].key]
        label = self.fonts["label"].render("BIOME", True, ACCENT_COLOR)
        surface.blit(label, label.get_rect(
            right=first.left - BIOME_LABEL_GAP, centery=first.centery))

        for biome in biomes.BIOMES:
            rect = rects[biome.key]
            button_style.draw_button(
                surface, rect, biome.name, self.fonts["label"],
                hovered=rect.collidepoint(mouse),
                pressed=(biome.key == selected),
            )
        return rects

    def _draw_tile(self, surface, tile, hovered=False):
        ts.draw_tile_frame(surface, tile.rect, hovered=hovered)

        # The picture, letterboxed inside its square box (see
        # map_preview.surface_for) on its own dark plate, so a portrait board
        # and a landscape one both read as "a board" rather than as two
        # differently cropped images.
        pygame.draw.rect(surface, PREVIEW_BG_COLOR, tile.preview_rect)
        art = map_preview.surface_for(
            tile.battle_map, tile.preview_rect.width, tile.preview_rect.height)
        surface.blit(art, art.get_rect(center=tile.preview_rect.center))
        pygame.draw.rect(surface, PREVIEW_BORDER_COLOR, tile.preview_rect, width=1)

        deployment_line, contents_line = self.facts(tile.battle_map)
        text_width = tile.rect.width - 2 * TILE_PAD
        y = tile.preview_rect.bottom + 12
        # The map's own name, which carries the layout it was built from ("Take
        # Cover"), wrapped rather than clipped - a narrow tile still has to
        # show the whole thing.
        for line in wrap_text(self.fonts["name"], tile.battle_map.name, text_width) or [""]:
            surf = self.fonts["name"].render(line, True, TITLE_COLOR)
            surface.blit(surf, surf.get_rect(centerx=tile.rect.centerx, y=y))
            y += self.fonts["name"].get_height()
        for font, text, color in ((self.fonts["body"], deployment_line, TEXT_COLOR),
                                  (self.fonts["small"], contents_line, DIM_TEXT_COLOR)):
            surf = font.render(text, True, color)
            surface.blit(surf, surf.get_rect(centerx=tile.rect.centerx, y=y + 2))
            y += font.get_height() + 2

    # -- the loop ---------------------------------------------------------
    def run(self, screen, clock=None):
        """Pump events until a map is picked. Returns its key, or None if the
        player quit out of the screen - which main() treats as "close the
        program", the same as ESC anywhere else in fullscreen."""
        ts.run_screen(screen, self, clock)
        return None if self.cancelled else self.chosen.key
