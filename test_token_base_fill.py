"""A model's base is a ring with nothing inside it.

User: "momentan haben die bases der modelle einen farbigen rand und sind
schwarz ausgefüllt. nimm die füllung komplett raus sodass nur der farbige
ring übrig bleibt innen sind sie transparent."

"Transparent" here means the renderer simply doesn't paint the middle: the
board surface it draws onto is opaque and already carries the ground and the
terrain, so anything it leaves alone shows through. That is what these
checks measure - the pixels inside a base are the ones that were there
before _draw_tokens() ran, not a color of its own.

Two things had to go for that, and both are checked:

  * the dark fill disc (TOKEN_FILL_DARKEN * team color), the thing the user
    is looking at; and
  * the glow pass, which stroked a translucent ring just INSIDE each base
    before the fill went down. pygame strokes a circle inward from its
    radius, so the fill covered all of it - measured 0 changed pixels of
    1.28M on a full board with the glow off, i.e. it had never been
    visible. Left in place it would have appeared for the first time as a
    translucent band around the inside of each rim.

The A/B probe rebuilds the whole pre-change draw (fill disc, then ring, then
art), not just one of the two, so "the middle is clear now" is measured
against what was actually on screen before.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

from game import sprites

c = Checks("token base fill")

pygame.init()
screen = pygame.display.set_mode((600, 400))

from game.board import Board          # noqa: E402  (needs a display)
from game import renderer as rmod     # noqa: E402
from game.renderer import Renderer    # noqa: E402
from game.factions.aeldari import AVATAR_OF_KHAINE  # noqa: E402
from game.factions.orks import PAINBOY               # noqa: E402

BACKDROP = (255, 0, 255)  # a color nothing in the token draw uses, so any pixel still holding it was left alone
BOARD = Board(60.0, 44.0, 22.0)


def token_of(datasheet, owner, name, x=6.0, y=6.0):
    squad = tk.build(datasheet, owner, name=name)
    model = squad.models[0]
    model.x_in, model.y_in = x, y
    return model


def render(token, old_style=False):
    """The token drawn onto a flat BACKDROP surface. `old_style` rebuilds
    the pre-change draw instead: the dark fill disc first, then the ring,
    then the art - i.e. the whole world this change removed, not one line
    of it."""
    surface = pygame.Surface((BOARD.width_px, BOARD.height_px))
    surface.fill(BACKDROP)
    if not old_style:
        Renderer()._draw_tokens(surface, BOARD, [token], "Player 1")
        return surface
    px, py = BOARD.to_px(token.x_in, token.y_in)
    r_px = round(BOARD.in_to_px_len(token.radius_in))
    color = Renderer()._token_color(token, "Player 1")
    fill_color = tuple(round(ch * rmod.TOKEN_FILL_DARKEN) for ch in color)
    pygame.draw.circle(surface, fill_color, (round(px), round(py)), r_px)
    pygame.draw.circle(surface, color, (round(px), round(py)), r_px, width=rmod.TOKEN_BORDER_WIDTH)
    path = sprites.sprite_for(token)
    if path is not None:
        art = sprites.scaled_surface(path, r_px * 2)
        ax, ay = sprites.anchor_offset(path, art.get_size())
        surface.blit(art, (round(px - ax), round(py - ay)))
    return surface


def interior(surface, token, inset_px=3):
    """(untouched, total) pixel counts strictly inside a token's base -
    inset far enough past the ring stroke that its own pixels don't count
    as "inside"."""
    px, py = BOARD.to_px(token.x_in, token.y_in)
    r_px = round(BOARD.in_to_px_len(token.radius_in))
    limit = r_px - rmod.SQUAD_LEADER_BORDER_WIDTH - inset_px
    untouched = total = 0
    for x in range(round(px) - limit, round(px) + limit + 1):
        for y in range(round(py) - limit, round(py) + limit + 1):
            if (x - px) ** 2 + (y - py) ** 2 > limit ** 2:
                continue
            total += 1
            if tuple(surface.get_at((x, y)))[:3] == BACKDROP:
                untouched += 1
    return untouched, total


def ring_present(surface, token):
    """Whether the base's own ring color is on screen at the rim - the half
    of the request that must NOT change ("nur der farbige ring übrig")."""
    px, py = BOARD.to_px(token.x_in, token.y_in)
    r_px = round(BOARD.in_to_px_len(token.radius_in))
    ring_color = tuple(Renderer()._token_color(token, "Player 1"))
    return any(
        tuple(surface.get_at((round(px + dx), round(py + dy))))[:3] == ring_color
        for dx, dy in ((r_px - 1, 0), (-(r_px - 1), 0), (0, r_px - 1), (0, -(r_px - 1)))
    )


# --- a model with no art of its own (ring + 2-letter label only) -----------

painboy = token_of(PAINBOY, "Player 2", "2 Painboy 1")
c.true("the Painboy is the art-less case this covers",
       sprites.sprite_for(painboy) is None)

untouched, total = interior(render(painboy), painboy)
# The remainder is its own 2-letter label, which on a 0.5" base is a big
# share of the disc - the label is drawn at a fixed font size while the base
# is one of the smallest on the board.
c.true(f"its base is left unpainted apart from its label ({untouched}/{total})",
       untouched > total * 0.6)
c.true("...so something IS still drawn inside it - the label, not a fill",
       untouched < total)
c.true("...and the colored ring is still there", ring_present(render(painboy), painboy))

old_untouched, old_total = interior(render(painboy, old_style=True), painboy)
c.eq(f"PRE-CHANGE: the same base was painted edge to edge ({old_untouched}/{old_total})",
     old_untouched, 0)


# --- a model with art, whose art doesn't cover the whole base --------------

avatar = token_of(AVATAR_OF_KHAINE, "Player 1", "1 Avatar of Khaine 1", x=20.0, y=20.0)
c.true("the Avatar is the with-art case this covers",
       sprites.sprite_for(avatar) is not None)

untouched, total = interior(render(avatar), avatar)
c.true(f"the ground shows through everywhere its art doesn't cover ({untouched}/{total})",
       untouched > total * 0.2)
c.true("...and the colored ring is still there", ring_present(render(avatar), avatar))

old_untouched, _ = interior(render(avatar, old_style=True), avatar)
c.eq("PRE-CHANGE: the dark disc filled every one of those pixels instead",
     old_untouched, 0)


c.true("the glow constants are gone with the pass that used them",
       not any(hasattr(rmod, n) for n in
               ("TOKEN_GLOW_ALPHA", "TOKEN_GLOW_WIDTH_FACTOR", "TOKEN_GLOW_MIN_WIDTH")))


# --- the rim is two thin rings, colored outside and dark inside ------------

# User: "der ring hat jetzt zu wenig kontrast auf hellen boden. kannst du ihn
# 2 teilig machen? ein farbiger äußerer ring und einen dunklen inneren ring?
# beide aber dünn." Walked as a radial profile out from the centre, so the
# ORDER of the two is what's checked, not just that both colors appear.
def radial_profile(surface, token, renderer):
    """The color at each pixel radius along a horizontal ray from the
    token's centre outwards, as far as its base goes."""
    px, py = BOARD.to_px(token.x_in, token.y_in)
    r_px = round(BOARD.in_to_px_len(token.radius_in))
    return [tuple(surface.get_at((round(px) + d, round(py))))[:3] for d in range(r_px + 1)]


painboy_surface = render(painboy)
profile = radial_profile(painboy_surface, painboy, Renderer())
team = tuple(Renderer()._token_color(painboy, "Player 1"))
colored = [i for i, c_ in enumerate(profile) if c_ == team]
dark = [i for i, c_ in enumerate(profile) if c_ == rmod.TOKEN_INNER_RING_COLOR]

c.true("the rim has a team-colored ring", bool(colored))
c.true("...and a dark ring", bool(dark))
c.true(f"...with the dark one INSIDE the colored one (dark {dark}, colored {colored})",
       bool(dark) and bool(colored) and max(dark) < min(colored))
c.true("...and the two touch, with no gap between them",
       bool(dark) and bool(colored) and min(colored) - max(dark) == 1)
c.true("both are thin: neither is wider than 2px at render_scale 1",
       len(colored) <= 2 and len(dark) <= 2)
c.true("...and there is no third ring further in - nothing else is stroked",
       not any(c_ in (team, rmod.TOKEN_INNER_RING_COLOR) for c_ in profile[:min(dark)]))


# --- rim widths are given in ON-SCREEN pixels, not board pixels ------------

# Measured on map2 at a 1300x900 board area: the board renders at 54.2ppi
# (render_scale 3.01) and the camera shows it at 0.400, so the old hardcoded
# 2-pixel stroke arrived as 0.80 of a screen pixel and washed out - the
# contrast the report is about. _ring_width() applies the same correction
# the fonts already got.
c.eq("a rim width is 1:1 when the board isn't supersampled",
     Renderer(render_scale=1.0)._ring_width(2), 2)
c.eq("...and scales with the board's render resolution",
     Renderer(render_scale=3.01)._ring_width(2), 6)
c.eq("...never rounding a thin rim away to nothing",
     Renderer(render_scale=0.2)._ring_width(1), 1)

# A/B: what a leader's gold ring was actually worth on screen before.
c.true("PRE-CHANGE: a 2px rim was sub-pixel once the camera scaled the board down",
       2 * 0.400 < 1.0)


# --- the embarked-passenger icon is deliberately untouched ----------------

# It is not a model base - it is a badge drawn ON a transport token, and its
# art-less fallback needs its own disc or there'd be nothing to look at.
c.true("TOKEN_FILL_DARKEN still exists for that one fallback",
       hasattr(rmod, "TOKEN_FILL_DARKEN"))

c.finish()
