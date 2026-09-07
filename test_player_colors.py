"""A model's rim colour is a fact about its OWNER, not about the focus.

User: "Die Farben der Spieler sollen nicht mehr wechseln, je nachdem wo der
Fokus ist. Sie sollen konstant bleiben. Spieler 1 - gruen, Spieler 2 - rot."

WHAT WAS WRONG, and it is not "the colours were the wrong way round": the rims
were keyed on `turn_tracker.active_player`, so the two armies TRADED colours
every time that moved. game/turn.py's own docstring calls active_player a
transient "whose decision is this right now" flag - it flips for every defender
save roll and every reactive stratagem, and only `turn_owner` tracks whose turn
it is. So the entire board changed colour twice per shooting attack, and the
one job a rim has - telling the two armies apart at a glance - was the one it
stopped doing.

WHY THIS SUITE EXISTS AT ALL: nothing pinned the rim's relationship to the
active player. test_token_base_fill.py and test_arena_biome.py both touch these
colours, and both pass a single hard-coded "Player 1", so neither could ever
see a swap. That is why a rim keyed on a flag that flips mid-attack survived.

The tautology to avoid here is comparing the renderer against its own table: a
check that reads TOKEN_TEAM_COLORS and then asserts the rim equals
TOKEN_TEAM_COLORS moves both sides of the comparison at once and would pass
with the table set to two identical greys. So the anchors are the two SPOKEN
words - green for Player 1, red for Player 2 - measured as "the green channel
dominates" / "the red channel dominates" on pixels actually on a surface.
"""

import collections
import math
import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

c = Checks("constant player colours")

pygame.init()
screen = pygame.display.set_mode((600, 400))

from game.board import Board          # noqa: E402  (needs a display)
from game import renderer as rmod     # noqa: E402
from game.renderer import Renderer    # noqa: E402
from game.factions.orks import BOYZ   # noqa: E402
from game.factions.aeldari import DIRE_AVENGERS  # noqa: E402

BOARD = Board(60.0, 44.0, 22.0)
BACKDROP = (255, 0, 255)  # a colour the token draw never uses


def token_of(datasheet, owner, name, x=6.0, y=6.0):
    """One RANK-AND-FILE model of the squad, placed at (x, y).

    Deliberately not models[0]: that is often the squad leader, whose rim is a
    fixed gold (SQUAD_LEADER_RING_COLOR) that carries no team colour at all -
    and gold's red channel outruns its green, so a leader would read as "red"
    to the channel test below and this suite would fail against correct art."""
    squad = tk.build(datasheet, owner, name=name)
    model = next(m for m in squad.models
                 if m.profile is None or not m.profile.squad_leader)
    model.x_in, model.y_in = x, y
    return model


def rim_color(surface, token):
    """The colour the base's ring is actually stroked in, read off the screen.

    Sampled around the band one pixel inside the radius (pygame strokes a
    circle INWARD from it) and reduced to the most common colour there, with
    the backdrop and TOKEN_INNER_RING_COLOR excluded - the ring shares that
    band with the darker inner hairline, and at some angles the rounding lands
    on the hairline instead. Measured: on that band the team colour is the
    plurality at 29/64 and 32/64, and one band further in it is not the ring at
    all, which is why the band is not widened."""
    px, py = BOARD.to_px(token.x_in, token.y_in)
    r_px = round(BOARD.in_to_px_len(token.radius_in))
    seen = collections.Counter()
    for i in range(64):
        a = i * math.tau / 64
        x, y = round(px + math.cos(a) * (r_px - 1)), round(py + math.sin(a) * (r_px - 1))
        rgb = tuple(surface.get_at((x, y)))[:3]
        if rgb != BACKDROP and rgb != rmod.TOKEN_INNER_RING_COLOR:
            seen[rgb] += 1
    return seen.most_common(1)[0][0] if seen else None


def render(tokens):
    surface = pygame.Surface((BOARD.width_px, BOARD.height_px))
    surface.fill(BACKDROP)
    Renderer()._draw_tokens(surface, BOARD, list(tokens))
    return surface


def greenish(rgb):
    r, g, b = rgb
    return g > r and g > b


def reddish(rgb):
    r, g, b = rgb
    return r > g and r > b


p1 = token_of(BOYZ, "Player 1", "1 Boyz 1", x=6.0, y=6.0)
p2 = token_of(DIRE_AVENGERS, "Player 2", "2 Dire Avengers 1", x=16.0, y=6.0)


# --------------------------------------------------------------------------
# 1. The two spoken colours, measured on a real surface
# --------------------------------------------------------------------------
print("=== 1. green is Player 1, red is Player 2 ===")

surface = render([p1, p2])
p1_rim = rim_color(surface, p1)
p2_rim = rim_color(surface, p2)

c.true("Player 1's rim is drawn at all", p1_rim is not None)
c.true("Player 2's rim is drawn at all", p2_rim is not None)
c.true("Player 1's rim is GREEN (green channel dominates)", greenish(p1_rim))
c.true("Player 2's rim is RED (red channel dominates)", reddish(p2_rim))

# Both armies are on the board in ONE frame, which is the whole point: under
# the old rule exactly one of them was green at any moment, and which one
# depended on a flag that moves mid-attack. Here both statements hold at once.
c.true("both statements hold in the same frame", greenish(p1_rim) and reddish(p2_rim))

# THE COLOUR COMES FROM THE OWNER AND NOTHING ELSE. Same datasheet, same
# sprite, same base - only the owner differs - so this rules out the rim
# picking up its hue from the art or the profile, which is the reading under
# which the two checks above would pass without the owner mattering at all.
same_a = token_of(BOYZ, "Player 1", "1 Boyz 2", x=26.0, y=6.0)
same_b = token_of(BOYZ, "Player 2", "2 Boyz 1", x=36.0, y=6.0)
twins = render([same_a, same_b])
c.true("one datasheet under two owners: green for Player 1",
       greenish(rim_color(twins, same_a)))
c.true("...red for Player 2", reddish(rim_color(twins, same_b)))
c.true("...so the owner is what decides",
       rim_color(twins, same_a) != rim_color(twins, same_b))


# --------------------------------------------------------------------------
# 2. Nothing about the game state can move them
# --------------------------------------------------------------------------
print("\n=== 2. constant, whatever is happening ===")

# The strongest form this can take now: _token_color takes ONE argument, so
# there is no game state left to pass it. A signature check is stronger than
# any number of "call it in two states and compare" cases, because it rules
# out a state that the test did not think to construct.
import inspect  # noqa: E402

params = list(inspect.signature(Renderer._token_color).parameters)
c.eq("_token_color asks only about the token", params, ["self", "token"])

src = open(r"c:\Users\Andre\Desktop\WH40\game\renderer.py", encoding="utf-8").read()
c.true("...and the module no longer keys a colour on active_player",
       "active_player" not in src.split("TOKEN_TEAM_COLORS = {")[1])

# The rim survives a swap of who is deciding, put the only way it still can be:
# the same token rendered twice, with the turn tracker moved in between. The
# renderer never sees it, which is exactly the assurance.
from game.turn import TurnTracker  # noqa: E402

tracker = TurnTracker(first_player="Player 1")
before = rim_color(render([p1, p2]), p1)
tracker.set_active("Player 2")           # e.g. a defender's save roll
after = rim_color(render([p1, p2]), p1)
c.eq("a defender's save does not repaint the board", after, before)
c.eq("...and the tracker really did move", tracker.active_player, "Player 2")
c.eq("...while turn_owner did not", tracker.turn_owner, "Player 1")


# --------------------------------------------------------------------------
# 3. The rims and the deployment-zone lines now agree
# --------------------------------------------------------------------------
print("\n=== 3. one story about which colour is whose ===")

# DEPLOYMENT_ZONE_LINE_COLORS has been owner-keyed since it was written, and
# says the same two words. Before this change the two disagreed on every frame
# where the focus was not on Player 1 - the zone line stayed green while the
# models inside it went red. Checked as agreement between the two tables rather
# than against literals, so the pair cannot drift apart.
zone = rmod.DEPLOYMENT_ZONE_LINE_COLORS
for player in ("Player 1", "Player 2"):
    rim = rmod.TOKEN_TEAM_COLORS[player]
    line = zone[player][:3]
    c.true(f"{player}: rim and zone line are the same hue family",
           (greenish(rim) and greenish(line)) or (reddish(rim) and reddish(line)))

# They are still DIFFERENT SHADES, which the renderer's own comment calls for -
# one is a ring on a model, the other a line on the ground, and collapsing them
# would delete a deliberate distinction.
c.true("...but not the same colour",
       all(rmod.TOKEN_TEAM_COLORS[p] != zone[p][:3] for p in ("Player 1", "Player 2")))

# Both known players are in the table; an unknown owner falls back to the
# token's own colour rather than inventing a third team colour.
c.eq("the table covers both players", sorted(rmod.TOKEN_TEAM_COLORS), ["Player 1", "Player 2"])
stray = token_of(BOYZ, "Player 3", "3 Boyz 1")
c.eq("an unknown owner keeps its own colour",
     tuple(Renderer()._token_color(stray)), tuple(stray.color))


# --------------------------------------------------------------------------
# 4. Embarked passenger icons follow the same rule
# --------------------------------------------------------------------------
print("\n=== 4. the same colour inside a transport ===")

# draw_embarked_passengers() read the same flag through the same helper, so it
# swapped along with everything else. It has no active player left either.
params = list(inspect.signature(Renderer.draw_embarked_passengers).parameters)
c.eq("draw_embarked_passengers takes no active player", params,
     ["self", "surface", "board", "tokens", "embarked_squads"])
params = list(inspect.signature(Renderer._draw_embarked_icon).parameters)
c.eq("...nor does the icon it draws", params,
     ["self", "surface", "model", "squad", "cx", "cy", "r_px"])

# And Renderer.draw() - the one main.py calls positionally - no longer has a
# parameter sitting between `obstacles` and `deployment_zones`. Left in place
# as a dead argument it would be error class 22 waiting to happen.
params = list(inspect.signature(Renderer.draw).parameters)
c.eq("Renderer.draw()'s positional args are unchanged apart from the drop",
     params[:5], ["self", "surface", "board", "tokens", "obstacles"])
c.true("...and active_player is gone from it", "active_player" not in params)

main_src = open(r"c:\Users\Andre\Desktop\WH40\main.py", encoding="utf-8").read()
c.true("main.py does not still hand the renderer an active player",
       "state.obstacles, turn_tracker.active_player" not in main_src)

c.finish()
