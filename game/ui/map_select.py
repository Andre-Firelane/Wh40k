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

Frame, paging and loop are shared with the army picker - see
game/ui/tile_screen.py. Only the tile content lives here.
"""

import pygame

from game import maps
from game.game_state import GameState
from game.ui import map_preview, tile_screen as ts
from game.ui.text_utils import wrap_text

TITLE_COLOR = ts.TITLE_COLOR
TEXT_COLOR = ts.TEXT_COLOR
DIM_TEXT_COLOR = ts.DIM_TEXT_COLOR
ACCENT_COLOR = (120, 190, 150)   # a colour of its own, so the map step is not mistaken for a player's

TILE_PAD = ts.TILE_PAD
PREVIEW_BORDER_COLOR = (70, 100, 130)
PREVIEW_BG_COLOR = (6, 10, 16)


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

    depth = 0.0
    across_y = True
    for zone in state.deployment_zones:
        for x_in, y_in, w_in, h_in in getattr(zone, "rects", ()) or ():
            depth = max(depth, min(w_in, h_in))
            across_y = h_in <= w_in
    board = battle_map.height_in if across_y else battle_map.width_in
    no_mans_land = max(0.0, board - 2 * depth)
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

    def layout(self, screen_rect):
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
        for index, tile in enumerate(self.tiles):
            self._draw_tile(surface, tile, hovered=(index == self.hovered_tile))
        self.prev_rect, self.next_rect = ts.draw_footer(
            surface, screen_rect, self.fonts, self.page, self.page_count)[1:]

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
