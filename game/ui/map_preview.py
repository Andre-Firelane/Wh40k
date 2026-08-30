"""A picture of a battlefield, rendered from the battlefield itself.

User, asking for the map picker: "Da wäre es cool, wenn ein Screenshot der Map
angeboten werden würde. Kriegst du das hin, oder soll ich das machen?" - this
is the answer to the second half. A hand-taken screenshot would be a second
copy of the map, and the first thing it would do is go stale: the terrain in
game/maps.py has been re-measured, straightened and re-picked several times,
and a PNG in Sprites/ would still show whichever version was on screen the day
it was saved. Rendering it means the tile CANNOT disagree with the board.

WHAT IT DRAWS is exactly the board's static layer, through the same Renderer
the game uses: the ground texture, every terrain footprint and wall, both
deployment zones, and the objective markers. No models - nothing is deployed
yet when this screen runs, and the point is the terrain anyway.

IN THE SELECTED BIOME (game/biomes.py). The same screen carries the biome
buttons, so a tile has to answer them - the whole reason those buttons sit
there rather than on a screen of their own is that this is where you can SEE
what a biome looks like before committing to it. Both caches below are keyed
by biome for that reason.

WHAT IT MUST NOT DO is touch config. The map picker runs BEFORE
maps.apply_to_config(), so at preview time config.BOARD_WIDTH_IN still holds
whatever the last run left there - and a preview that wrote the map's own size
into config would decide the battlefield merely by having been LOOKED at. It
does not need to: Renderer takes the Board it draws on as an argument, and
BattleMap.build() reads its own dimensions. Asserted in test_map_select.py
rather than left as a promise.
"""

import pygame

from game import biomes
from game.board import Board
from game.game_state import GameState
from game.renderer import Renderer

# The resolution a map is rendered at before being scaled into a tile. One
# render per map, reused at every size: a tile is a few hundred pixels across
# and re-rendering terrain per size would cost far more than a smoothscale.
RENDER_LONG_SIDE_PX = 640

# BOTH caches are keyed by (map, BIOME), because the biome buttons at the top
# of the picker repaint these tiles - that is the point of putting them on
# that screen rather than somewhere else: you pick a biome and see the
# battlefield in it. Keyed by map alone, the first click would appear to do
# nothing at all.
_rendered = {}   # (map key, biome key) -> full-size Surface
_scaled = {}     # (map key, biome key, box px) -> Surface fitted into that box


def _render(battle_map):
    """The map's static layer at RENDER_LONG_SIDE_PX, drawn once.

    A FRESH Renderer per render, not one shared module-level instance as this
    used to keep. Renderer caches its static layer under a key that starts
    with id(board) - and `board` below is a local that is garbage the moment
    this returns, so rendering the same map again under a different biome can
    be handed a recycled id, match the previous biome's cache entry and blit
    the wrong ground. That is a real collision here (same map, so the board's
    pixel size matches too) and a probabilistic one, which is the worst kind
    to leave in. Construction is a handful of empty dicts, and this runs at
    most once per (map, biome) thanks to _rendered above."""
    renderer = Renderer()
    state = GameState()
    battle_map.build(state)
    ppi = RENDER_LONG_SIDE_PX / max(battle_map.width_in, battle_map.height_in)
    board = Board(battle_map.width_in, battle_map.height_in, ppi)
    surface = pygame.Surface((board.width_px, board.height_px))
    renderer.draw(
        surface, board, (),
        obstacles=state.obstacles,
        deployment_zones=state.deployment_zones,
        terrain_areas=state.terrain_areas,
    )
    renderer.draw_objectives(surface, board, state.objectives, ())
    return surface


def surface_for(battle_map, box_width, box_height=None):
    """This map's preview, scaled to fit a box, aspect kept.

    LETTERBOXED into a box every tile shares, rather than filling each tile:
    the maps are three different shapes (44x60 portrait, 60x44 landscape,
    30x30 square), and tiles whose pictures were each a different height would
    read as a layout accident. Inside a common box, the shape of each board is
    itself part of what the tile tells you - which is the whole reason a
    picture beats a description here."""
    box_width = max(1, int(box_width))
    box_height = box_width if box_height is None else max(1, int(box_height))
    biome_key = biomes.current().key
    key = (battle_map.key, biome_key, box_width, box_height)
    cached = _scaled.get(key)
    if cached is not None:
        return cached
    render_key = (battle_map.key, biome_key)
    if render_key not in _rendered:
        _rendered[render_key] = _render(battle_map)
    full = _rendered[render_key]
    width, height = full.get_size()
    scale = min(box_width / width, box_height / height)
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    scaled = pygame.transform.smoothscale(full, size)
    _scaled[key] = scaled
    return scaled


def clear_cache():
    """Drop both caches - for tests that render at many sizes in one run."""
    _rendered.clear()
    _scaled.clear()
