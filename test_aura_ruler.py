"""The range ruler: the Aura toggle, its radius radio, and what it draws.

User: "neues Tool unten links. es gibt einen Aura toggle. wenn man den
aktiviert erscheinen weitere knoepfe die wie Radio Buttons funktionieren. 3" 6"
9" 12" 15" 18" 24" 36". wenn man einen dieser knoepfe aktiviert, dann wird bei
angewaehlten modellen die entsprechende Aura subtil angezeigt. optisch wie die
deathguard Aura, aber in weiss. das hilft bei Reichweiten. Aura toggle off
zeigt dann keine [Auren] mehr an. wichtig. es sollen immer nur die auren der
ausgewaehlten Modelle angezeigt werden."

  1. game/aura_ruler.py - two controls, one answer.
  2. the toolbar         - the toggle, and a radio that exists only while it is on.
  3. the drawing         - a flat white union, measured against the aura it copies.
  4. SCOPE               - the selected unit and nothing else, which is the
                           requirement the user marked "wichtig".
  5. the wiring in main.py.

Run: python test_aura_ruler.py
"""

import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1600, 900))

from game import aura_ruler, config  # noqa: E402
from game.board import Board  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.renderer import (  # noqa: E402
    CONTAGION_AURA_ALPHA, CONTAGION_AURA_COLOR, RANGE_AURA_ALPHA,
    RANGE_AURA_COLOR, Renderer,
)
from game.squad import Squad  # noqa: E402
from game.token import Token  # noqa: E402
from game.turn import TurnTracker  # noqa: E402
from game.ui.action_panel import ActionPanel, RADIO_HEIGHT  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("range ruler")

PANEL_H = 900
GROUND = (26, 32, 42)          # the arena biome's own ground, which is the default
PPI = 20.0


class _P:
    name = "Probe"
    wounds = 1
    fly = hover = transport = character = squad_leader = False


def _squad(name, points, radius=0.5):
    models = [Token(x_in=float(x), y_in=float(y), radius_in=radius,
                    color=(1, 1, 1), profile=_P())
              for x, y in points]
    squad = Squad(name, models, owner="Player 1")
    for model in models:
        model.squad = squad
    return squad


def _toolbar():
    """Just the bottom-left strip, and the rects it registered."""
    move = MovementController(turn_tracker=TurnTracker(), all_tokens=[],
                              dice_manager=DiceManager(), obstacles=[])
    panel = ActionPanel()
    surface = pygame.Surface((config.LEFT_PANEL_WIDTH, PANEL_H))
    surface.fill((0, 0, 0))
    panel._buttons = []
    panel._mouse_pos = (-1, -1)
    panel._mouse_down = False
    rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, PANEL_H)
    panel._draw_global_toolbar(surface, rect, move)
    return surface, list(panel._buttons), rect


def _radio_rows(rows):
    return [(r, cb) for r, cb in rows if r.height == RADIO_HEIGHT]


def _frame(renderer, board, squad, radius):
    surface = pygame.Surface((board.width_px, board.height_px))
    surface.fill(GROUND)
    renderer.draw_range_aura(surface, board, squad, radius)
    return surface


def _tinted(surface, step=3):
    return sum(1 for x in range(0, surface.get_width(), step)
               for y in range(0, surface.get_height(), step)
               if surface.get_at((x, y))[:3] != GROUND)


def _read(path):
    return io.open(path, encoding="utf-8").read()


# --------------------------------------------------------------------------
# 1. the module
# --------------------------------------------------------------------------
print("\n=== 1. two controls, one answer ===")

c.eq("the eight radii the user named, in that order",
     list(aura_ruler.RADII_IN), [3, 6, 9, 12, 15, 18, 24, 36])
c.true("the default radius is one of them", aura_ruler.DEFAULT_RADIUS_IN in aura_ruler.RADII_IN)

aura_ruler.set_enabled(False)
aura_ruler.set_radius(aura_ruler.DEFAULT_RADIUS_IN)
# active_radius() is the ONE question anything drawing asks, so the toggle and
# the radio cannot come to different conclusions about what is on screen.
c.eq("off: nothing to draw", aura_ruler.active_radius(), None)
aura_ruler.toggle()
c.true("the toggle turns it on", aura_ruler.is_enabled())
c.eq("...and the radius is the one that was already picked",
     aura_ruler.active_radius(), aura_ruler.DEFAULT_RADIUS_IN)

aura_ruler.set_radius(12)
c.eq("picking a radius changes what is drawn", aura_ruler.active_radius(), 12)
aura_ruler.toggle()
c.eq("...and turning it off draws nothing again", aura_ruler.active_radius(), None)
# The radius SURVIVES the toggle: coming back should return to the distance you
# were reading, not to a default.
c.eq("...while remembering the radius", aura_ruler.radius_in(), 12)
aura_ruler.toggle()
c.eq("...which is what comes back", aura_ruler.active_radius(), 12)

c.true("a radius that is not on the radio is refused", aura_ruler.set_radius(7) is False)
c.eq("...and changes nothing", aura_ruler.radius_in(), 12)
c.true("a real one is accepted", aura_ruler.set_radius(36) is True)


# --------------------------------------------------------------------------
# 2. the toolbar
# --------------------------------------------------------------------------
print("\n=== 2. the toolbar ===")

aura_ruler.set_enabled(False)
aura_ruler.set_radius(6)
_surf_off, rows_off, panel_rect = _toolbar()
c.eq("with the ruler off there is no radio at all", len(_radio_rows(rows_off)), 0)
# Same convention the pager and confirm button in tile_screen follow: no chrome
# for a control that cannot do anything. Eight dead buttons under an off switch
# would be eight things to explain.
c.eq("...just the two toggles", len(rows_off), 2)

aura_ruler.set_enabled(True)
_surf_on, rows_on, panel_rect = _toolbar()
radio = _radio_rows(rows_on)
c.eq("turning it on reveals one button per radius", len(radio), len(aura_ruler.RADII_IN))
c.eq("...and the toggles are still there", len(rows_on) - len(radio), 2)

c.true("every radio button is inside the panel",
       all(panel_rect.contains(r) for r, _ in radio))
_pairs = [(radio[i][0], radio[j][0]) for i in range(len(radio)) for j in range(i + 1, len(radio))]
c.true("no two overlap", not any(a.colliderect(b) for a, b in _pairs))
c.true("the strip stays pinned to the panel's bottom",
       max(r.bottom for r, _ in rows_on) <= panel_rect.bottom)
c.true("...and the radio does not sit on top of a toggle",
       not any(t.colliderect(rr) for t, _ in rows_on if t.height != RADIO_HEIGHT
               for rr, _ in radio))
# The strip grows DOWNWARD from a line it draws itself, so turning the ruler on
# must not push the toggles off the top of the panel either.
c.true("the whole strip still fits", min(r.y for r, _ in rows_on) >= panel_rect.y)

# EACH button picks ITS OWN radius. Worth its own check: the obvious way to
# build eight callbacks in a loop captures the loop variable, and then all
# eight would set 36.
for rect, callback in radio:
    callback()
picked = []
for rect, callback in radio:
    callback()
    picked.append(aura_ruler.radius_in())
c.eq("each button selects its own radius", picked, list(aura_ruler.RADII_IN))

# It is a RADIO: exactly one live at a time.
aura_ruler.set_radius(9)
c.eq("...and only one is live", sum(1 for r in aura_ruler.RADII_IN
                                   if r == aura_ruler.radius_in()), 1)

# The live one is drawn PRESSED - the same thing the map screen's biome row
# does for a many-way switch, so no second visual language is invented.
def _cell_ink(surface, rect):
    return sum(sum(surface.get_at((x, y))[:3])
               for x in range(rect.x + 3, rect.right - 3)
               for y in range(rect.y + 3, rect.bottom - 3))


aura_ruler.set_radius(3)
surf_a, rows_a, _ = _toolbar()
aura_ruler.set_radius(36)
surf_b, rows_b, _ = _toolbar()
first_rect = _radio_rows(rows_a)[0][0]
c.true("the selected button looks different from the same button unselected",
       _cell_ink(surf_a, first_rect) != _cell_ink(surf_b, first_rect))


# --------------------------------------------------------------------------
# 3. the drawing
# --------------------------------------------------------------------------
print("\n=== 3. a flat white union ===")

board = Board(40.0, 30.0, PPI)
renderer = Renderer()
one = _squad("Picked", [(10, 10)])

c.eq("white, as asked for", RANGE_AURA_COLOR, (255, 255, 255))
c.true("...and fainter than the aura it copies", RANGE_AURA_ALPHA < CONTAGION_AURA_ALPHA)


def _contrast(a, b):
    return sum(abs(a[i] - b[i]) for i in range(3)) / 3.0


def _blend(bg, colour, alpha):
    weight = alpha / 255.0
    return tuple(round(bg[i] * (1 - weight) + colour[i] * weight) for i in range(3))


# "subtil" as a NUMBER rather than an opinion: on the ground the game actually
# opens on (the arena biome), the white ruler must be visible at all, and must
# not shout louder than the Death Guard aura does on its own best ground.
white_here = _contrast(GROUND, _blend(GROUND, RANGE_AURA_COLOR, RANGE_AURA_ALPHA))
green_best = max(_contrast(g, _blend(g, CONTAGION_AURA_COLOR, CONTAGION_AURA_ALPHA))
                 for g in (GROUND, (231, 222, 205), (96, 96, 96), (60, 72, 52)))
c.true("it is visible on the default ground", white_here > 8)
c.true("...and no louder than the aura it is modelled on", white_here <= green_best)

blank = _frame(renderer, board, one, 6)
c.true("a selected unit gets an aura", _tinted(blank) > 0)
c.true("a bigger radius covers more ground",
       _tinted(_frame(renderer, board, one, 12)) > _tinted(_frame(renderer, board, one, 6)))

# The edge is measured from the BASE, like the engagement ring and the
# contagion aura - this game measures base to base.
cx, cy = board.to_px(10, 10)
edge = board.in_to_px_len(0.5 + 6)
surface = _frame(renderer, board, one, 6)
c.true("just inside the ring is tinted",
       surface.get_at((round(cx + edge - 4), round(cy)))[:3] != GROUND)
c.true("just outside it is not",
       surface.get_at((round(cx + edge + 4), round(cy)))[:3] == GROUND)

# The union is FLAT. Two overlapping models must not make a brighter patch:
# being within 6" of two models is the same as being within 6" of one, and a
# patchwork of hotspots would say something the rule does not.
pair = _frame(renderer, board, _squad("Pair", [(10, 10), (10.6, 10)]), 6)
c.eq("overlapping models do not stack into a hotspot",
     pair.get_at((round(cx), round(cy)))[:3], pair.get_at((round(cx) + 6, round(cy)))[:3])

# The overlay is shared and set_alpha persists on it, so it has to be reset -
# otherwise the next user of that surface inherits a fade it never asked for.
overlay = renderer._reusable_overlay("range_aura", (board.width_px, board.height_px))
c.eq("the shared overlay is left without a fade", overlay.get_alpha(), None)


# --------------------------------------------------------------------------
# 4. SCOPE - the half the user marked "wichtig"
# --------------------------------------------------------------------------
print("\n=== 4. only the selected unit ===")

c.eq("no selection, no aura", _tinted(_frame(renderer, board, None, 6)), 0)
c.eq("selected but the ruler is off, no aura", _tinted(_frame(renderer, board, one, None)), 0)
c.eq("...and a radius of 0 is not a ruler either",
     _tinted(_frame(renderer, board, one, 0)), 0)

# An UNSELECTED unit standing on the same board gets nothing. This is the
# requirement in the report, so it is measured at that unit's own position
# rather than inferred from a total.
other_x, other_y = board.to_px(30, 20)
surface = _frame(renderer, board, one, 6)
c.eq("another unit on the board has no aura of its own",
     surface.get_at((round(other_x), round(other_y)))[:3], GROUND)

# A unit whose models are all dead draws nothing - remove_dead_models() runs
# once a frame, so a casualty is still in squad.models when this is reached.
dead = _squad("Dead", [(10, 10)])
for model in dead.models:
    model.current_wounds = 0
c.eq("a wiped unit draws nothing", _tinted(_frame(renderer, board, dead, 6)), 0)
half = _squad("Half", [(10, 10), (10.0, 20.0)])
half.models[1].current_wounds = 0
alive_only = _frame(renderer, board, half, 6)
dx, dy = board.to_px(10.0, 20.0)
c.eq("...and a casualty inside a living unit draws none either",
     alive_only.get_at((round(dx), round(dy)))[:3], GROUND)
c.true("...while its living squadmates still do",
       alive_only.get_at((round(cx), round(cy)))[:3] != GROUND)


# --------------------------------------------------------------------------
# 4b. ONE model, not the whole blob
# --------------------------------------------------------------------------
print("\n=== 4b. the clicked model only ===")

# User: "die Aura Funktion zeigt momentan fuer jedes Modell im Squad die Aura
# an. wenn ich ein spezifisches Modell anklicke soll nur die Aura dieses
# Modells angezeigt werden."
#
# The union of twenty rings answers "could ANY of us reach it", which is rarely
# the question being asked - a weapon range, an aura's reach or a charge all
# belong to ONE model, from where that model stands.

blob = _squad("Blob", [(6, 6), (12, 6), (18, 6), (24, 6), (30, 6)])
anchor = blob.models[2]

whole = _tinted(_frame(renderer, board, blob, 6))
picked_surface = pygame.Surface((board.width_px, board.height_px))
picked_surface.fill(GROUND)
renderer.draw_range_aura(picked_surface, board, blob, 6, model=anchor)
picked = _tinted(picked_surface)

c.true("the blob really has several models", len(blob.models) > 1)
c.true("ringing the clicked model covers far less than ringing the unit",
       0 < picked < whole / 2)
# Measured AT the models rather than as a total, so "less ink" cannot pass for
# "the right model".
ax, ay = board.to_px(anchor.x_in, anchor.y_in)
c.true("...centred on the model that was clicked",
       picked_surface.get_at((round(ax), round(ay)))[:3] != GROUND)
for other in blob.models:
    if other is anchor:
        continue
    ox, oy = board.to_px(other.x_in, other.y_in)
    if (abs(other.x_in - anchor.x_in) > 6 + 2 * other.radius_in):
        c.eq(f"...and a squadmate {abs(other.x_in - anchor.x_in):.0f}\" away has none",
             picked_surface.get_at((round(ox), round(oy)))[:3], GROUND)

# A model of ANOTHER unit is not an anchor for this one. The selection can be
# set without a model (start_scout_move, torchstar_gambit write selected_squad
# straight), which leaves the PREVIOUS pick's model behind - honouring that
# would put the ruler on a unit nobody is looking at.
stray = _squad("Stray", [(35, 25)])
stale_surface = pygame.Surface((board.width_px, board.height_px))
stale_surface.fill(GROUND)
renderer.draw_range_aura(stale_surface, board, blob, 6, model=stray.models[0])
sx, sy = board.to_px(35, 25)
c.eq("a stale anchor from another unit does not move the ruler",
     stale_surface.get_at((round(sx), round(sy)))[:3], GROUND)
c.eq("...it falls back to the unit it was given",
     _tinted(stale_surface), whole)

# No anchor at all is the same fallback, so the paths that never set one keep
# exactly the behaviour they had.
c.eq("no anchor rings the whole unit, as before",
     _tinted(_frame(renderer, board, blob, 6)), whole)

# A dead anchor draws nothing rather than ringing a corpse - remove_dead_models()
# runs once a frame, so it is still in squad.models when this is reached.
anchor.current_wounds = 0
dead_surface = pygame.Surface((board.width_px, board.height_px))
dead_surface.fill(GROUND)
renderer.draw_range_aura(dead_surface, board, blob, 6, model=anchor)
c.eq("a dead anchor draws nothing", _tinted(dead_surface), 0)
anchor.current_wounds = anchor.profile.wounds


# --------------------------------------------------------------------------
# 5. the wiring
# --------------------------------------------------------------------------
print("\n=== 5. wiring ===")

main_src = _read("main.py")
panel_src = _read("game/ui/action_panel.py")

c.true("main.py draws the ruler", "renderer.draw_range_aura(" in main_src)
# The SELECTED unit, and the one question that answers both halves.
c.true("...for the selected unit",
       "movement_controller.selected_squad,\n            aura_ruler.active_radius()," in main_src)
# ...ANCHORED on the model that was clicked. Pinned as the argument itself,
# because passing it is the entire fix: a regression that dropped it would
# leave every behaviour check in section 4b green (they call the renderer
# directly) while the game went back to ringing the whole blob.
c.true("...anchored on the clicked model",
       "model=movement_controller.selected_model" in main_src)
c.true("...next to the aura it is modelled on",
       main_src.index("draw_contagion_aura(") < main_src.index("draw_range_aura("))
# Under the models: it is a fact about the ground, not a tint on the miniatures.
c.true("...under the models", main_src.index("draw_range_aura(")
       < main_src.index("draw_embarked_passengers("))
c.true("the panel offers the toggle", '("Aura", aura_ruler.is_enabled(), aura_ruler.toggle)' in panel_src)
c.true("...and the radio only while it is on",
       "if aura_ruler.is_enabled() else 0" in panel_src)
# Rows are derived, so a ninth radius cannot fall off the bottom of the panel.
c.true("the radio's row count follows the list", "len(aura_ruler.RADII_IN)" in panel_src)
c.eq("there is one definition of what to draw", main_src.count("aura_ruler.active_radius()"), 1)

c.finish()
