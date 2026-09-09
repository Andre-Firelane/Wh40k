"""The objective info icon and the label it opens on hover.

User: "NameError: name 'rect' is not defined ... beim hovern ueber das
objective info icon". Renderer.draw_objectives() draws every objective's
outline and a small "i" badge; hovering that badge opens a label with the
objective's name, who controls it and each side's Objective Control. The
rotated-outline work renamed that method's local `rect` to `outline_rect` and
left two reads in the hover branch behind, so the label crashed the game the
first time anyone pointed at an icon.

WHY IT SURVIVED: nothing in this repo drew an objective at all. 13 600 checks,
and draw_objectives() appeared in exactly one of them - a source guard that
does not call it. A branch that only runs while the cursor is inside a
9-pixel circle is not reached by any behaviour test that does not deliberately
put it there, which is what this file does.

test_event_chain_wiring.py section 1b is the other half and the general one: no
function in game/ or ai/ may read a name nothing binds. That sweep finds this
class anywhere; this file pins THIS branch's behaviour - both are needed,
because a source guard cannot say the label is right, only that it can run.

Run: python test_objective_hover_label.py
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((400, 300))

from game import config, maps  # noqa: E402
from game.board import Board  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.renderer import Renderer, objective_outline_points  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("objective hover label")

_ORIGINAL_BIOME = config.BIOME


def scene(map_key):
    battle_map = maps.get(map_key)
    state = GameState()
    battle_map.build(state)
    board = Board(battle_map.width_in, battle_map.height_in, 30.0)
    return state, board


def icon_centre(renderer, board, objective, surface):
    """Where draw_objectives() puts this objective's badge - derived the same
    way it does, so the probe cannot drift onto a spot the icon left."""
    points = objective_outline_points(board, objective.terrain_area)
    radius = max(9, renderer.label_font.get_height() // 2 + 2)
    anchor = min(points, key=lambda p: p[0] + p[1])
    bounds = pygame.Rect(0, 0, radius * 2, radius * 2)
    bounds.center = anchor
    return renderer._clamp_rect_to_surface(bounds, surface).center


def draw(state, board, hover=None):
    """(renderer, surface, error) - NEVER raises.

    The whole subject of this file is a branch that throws, so a probe that
    lets it propagate would end the run at the first failure and hide every
    check after it. Third time this repo has learned that a guard must go RED
    rather than crash (see the str.index()/find() note in CLAUDE.md), so the
    exception is caught here once and turned into a value every section can
    assert on."""
    surface = pygame.Surface((board.width_px, board.height_px))
    renderer = Renderer()
    try:
        renderer.draw_objectives(surface, board, state.objectives, state.tokens,
                                 hover_native_px=hover)
    except Exception as exc:                          # noqa: BLE001 - that IS the check
        return renderer, surface, f"{type(exc).__name__}: {exc}"
    return renderer, surface, None


# --- 1. the reported crash, on every map and every objective ---------------

# EVERY objective, not one: map3's are rotated, and the rotated branch is the
# one whose rename left the stale name behind. A single sample could easily
# have picked an axis-aligned piece and passed.
def hover_failures(state, board):
    renderer, surface, _ = draw(state, board)
    out = []
    for objective in state.objectives:
        _, _, error = draw(state, board,
                           hover=icon_centre(renderer, board, objective, surface))
        if error:
            out.append(f"{objective.name}: {error}")
    return out


for map_key in ("map1", "map2", "map3", "map4"):
    state, board = scene(map_key)
    c.eq(f"{map_key}: hovering every objective's icon draws its label "
         f"({len(state.objectives)} objectives)", hover_failures(state, board), [])

# ...and under the drawn biome too, which is what the game now opens on: the
# label is drawn onto the board surface, over whatever the ground put there.
config.BIOME = "arena"
state, board = scene("map2")
c.eq("...and in the arena biome, the one the game ships on",
     hover_failures(state, board), [])
config.BIOME = _ORIGINAL_BIOME


# --- 2. hovering actually CHANGES something --------------------------------

# Without this the section above would pass on a draw_objectives() that ignored
# hover_native_px entirely - a branch that never runs cannot crash either.
state, board = scene("map2")
renderer, plain, _ = draw(state, board)
objective = state.objectives[0]
centre = icon_centre(renderer, board, objective, plain)
hovered_renderer, hovered, hover_error = draw(state, board, hover=centre)
c.eq("the hovered draw completes at all", hover_error, None)


def changed_pixels(a, b):
    count = 0
    for y in range(0, a.get_height(), 2):
        for x in range(0, a.get_width(), 2):
            if a.get_at((x, y)) != b.get_at((x, y)):
                count += 1
    return count


c.true("hovering the icon paints something that was not there before",
       changed_pixels(plain, hovered) > 20)
_, elsewhere, _ = draw(state, board, hover=(board.width_px - 2, board.height_px - 2))
c.eq("...and a cursor nowhere near an icon paints nothing extra",
     changed_pixels(plain, elsewhere), 0)
c.eq("...nor does no cursor at all", changed_pixels(plain, draw(state, board)[1]), 0)

# The label is anchored ABOVE the objective's own outline, which is the thing
# `rect` used to be read for. Measured as "the new pixels sit above the icon",
# so a label pinned to the wrong shape shows up as a position, not a crash.
top_band = pygame.Surface((board.width_px, max(1, centre[1])))
top_band.blit(hovered, (0, 0))
plain_band = pygame.Surface(top_band.get_size())
plain_band.blit(plain, (0, 0))
c.true("...and the label opens above the icon it belongs to",
       changed_pixels(plain_band, top_band) > 10)


# --- 3. the label says what it is for --------------------------------------

# Cheap, and it is the reason the branch exists at all: the name is the only
# place a player is told WHICH objective this is (game/maps.py's sprechende
# Namen), and the control line is the only place the OC totals are visible.
c.true("every objective has a name for the label to show",
       all(o.name for o in state.objectives))
c.true("...and level_of_control() answers for an empty board without raising",
       isinstance(state.objectives[0].level_of_control(state.tokens), dict))

c.finish()
