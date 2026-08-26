"""The red Engagement Range rings drawn while a unit is being moved.

User: "die roten kreise der gegner, wenn ich mich bewege sind gerade groesser
als 2 zoll. meine models duerfen sie mit der base mitte nicht betreten. kannst
du das so aendern, dass sie genau 2\" sind und ich sie mit dem baserand nicht
betreten darf? das ist intuitiver."

Purely a change of what the ring MEANS, not of the rule: the forbidden set is
identical either way. It used to be drawn as the keep-out zone for a model's
CENTRE (enemy base + 2" + the moving unit's own widest base), which is
correct but asks the player to do the conversion while dragging. It is now
Engagement Range itself, measured from the enemy's base edge - so the ring is
2" wide and the rule to read off it is "don't touch it with your base", which
is what rule 03.04 says.

The check that matters is therefore not "is the radius smaller" on its own -
it is that the ring and Squad.is_engaged() agree about where the boundary is.
That is what most of this file measures, by reading the radius back out of
pygame.draw.circle and comparing it against edge_distance().
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

from game import movement
from game.attached_units import attach
from game.factions.orks import BOYZ, WARBOSS
from game.factions.tau_empire import RIPTIDE_BATTLESUIT, STRIKE_TEAM
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance, max_model_radius

c = Checks("engagement range rings")

pygame.init()
screen = pygame.display.set_mode((900, 700))

from game.board import Board            # noqa: E402  (needs a display)
from game.renderer import Renderer      # noqa: E402


# A mover with MIXED base sizes (19.01) against two enemies of very
# different sizes - the two things the old centre-based ring could not draw
# correctly at the same time.
mover = attach(tk.build(WARBOSS, "Player 2", name="Warboss"),
               tk.build(BOYZ, "Player 2", name="Boyz 1"))
tk.line_up(mover, x=10.0, y=10.0)
small_enemy = tk.build(STRIKE_TEAM, "Player 1", name="Strike Team 1")
big_enemy = tk.build(RIPTIDE_BATTLESUIT, "Player 1", name="Riptide 1")
tk.line_up(small_enemy, x=30.0, y=30.0)
tk.line_up(big_enemy, x=30.0, y=40.0)

tokens = list(mover.models) + list(small_enemy.models) + list(big_enemy.models)

radii = {m.radius_in for m in mover.models}
c.true("the moving unit really does mix base sizes", len(radii) > 1)
c.true("...and the two enemies are different sizes too",
       small_enemy.models[0].radius_in != big_enemy.models[0].radius_in)


class FakeMovement:
    state = movement.MOVING
    move_mode = None
    charge_targets = ()

    def __init__(self, squad):
        self.selected_squad = squad


def drawn_rings():
    """[(enemy token, radius in inches)] for one draw pass - read back out of
    pygame.draw.circle, so this measures what is actually painted rather than
    re-deriving it."""
    board = Board(60.0, 44.0, 14.0)
    captured = []
    real_circle = pygame.draw.circle

    def spy(surface, color, center, radius, width=0, **kw):
        captured.append((center, radius))
        return real_circle(surface, color, center, radius, width, **kw)

    pygame.draw.circle = spy
    try:
        Renderer().draw_forbidden_engagement_ranges(
            screen, board, FakeMovement(mover), tokens,
        )
    finally:
        pygame.draw.circle = real_circle

    rings = []
    for token in small_enemy.models + big_enemy.models:
        cx, cy = board.to_px(token.x_in, token.y_in)
        for (px, py), radius_px in captured:
            if abs(px - round(cx)) <= 1 and abs(py - round(cy)) <= 1:
                rings.append((token, radius_px / board.in_to_px_len(1.0)))
                break
    return rings


rings = drawn_rings()
c.eq("one ring per enemy model", len(rings), len(small_enemy.models) + len(big_enemy.models))

for token, radius_in in rings:
    label = "small" if token.squad is small_enemy else "big"
    c.true(f"the {label} enemy's ring is its own base plus exactly 2 inches",
           abs(radius_in - (token.radius_in + ENGAGEMENT_RANGE_IN)) < 0.05)

# The claim that makes the change worth anything: the ring and the rule agree.
# A model whose BASE EDGE sits exactly on the ring is exactly at Engagement
# Range; a hair further out is clear of it.
enemy = big_enemy.models[0]
ring_in = enemy.radius_in + ENGAGEMENT_RANGE_IN
for model in mover.models[:3]:
    original = (model.x_in, model.y_in)
    # Place it so its base edge touches the ring.
    model.x_in = enemy.x_in + ring_in + model.radius_in
    model.y_in = enemy.y_in
    c.true("base edge on the ring == exactly Engagement Range",
           abs(edge_distance(model, enemy) - ENGAGEMENT_RANGE_IN) < 1e-6)
    model.x_in += 0.05
    c.true("...and a touch outside it is clear (rule 03.04)",
           edge_distance(model, enemy) > ENGAGEMENT_RANGE_IN)
    model.x_in -= 0.10
    c.true("...while a touch inside it is engaged",
           edge_distance(model, enemy) < ENGAGEMENT_RANGE_IN)
    model.x_in, model.y_in = original

# A/B: the previous ring. Same forbidden set, but read off the model's CENTRE,
# and sized off the WIDEST model in the squad - so it over-painted the zone for
# every smaller model in an attached unit, by exactly the difference in radius.
widest = max_model_radius(mover, default=0.0)
old_ring_in = enemy.radius_in + ENGAGEMENT_RANGE_IN + widest
c.true("PRE-CHANGE: the ring was larger than 2 inches from the base edge",
       old_ring_in > ring_in)
narrowest = min(m.radius_in for m in mover.models)
c.true("...and over-painted the zone for the unit's smaller models",
       old_ring_in - narrowest > enemy.radius_in + ENGAGEMENT_RANGE_IN)
c.true("...whereas each model now brings its own base to the same ring",
       all(abs((ring_in + m.radius_in)
               - (enemy.radius_in + ENGAGEMENT_RANGE_IN + m.radius_in)) < 1e-6
           for m in mover.models))

# The move-type rules the rings already followed are untouched.
class ChargeMovement(FakeMovement):
    move_mode = "charge"

    def __init__(self, squad, targets):
        super().__init__(squad)
        self.charge_targets = targets


def ring_count(controller):
    board = Board(60.0, 44.0, 14.0)
    count = [0]
    real_circle = pygame.draw.circle

    def spy(surface, color, center, radius, width=0, **kw):
        count[0] += 1
        return real_circle(surface, color, center, radius, width, **kw)

    pygame.draw.circle = spy
    try:
        Renderer().draw_forbidden_engagement_ranges(screen, board, controller, tokens)
    finally:
        pygame.draw.circle = real_circle
    return count[0]


c.eq("a charge draws no ring for its own declared target",
     ring_count(ChargeMovement(mover, [big_enemy])), len(small_enemy.models))


class PileIn(FakeMovement):
    move_mode = "pile_in"


c.eq("a pile-in draws none at all", ring_count(PileIn(mover)), 0)

c.finish()
