"""Unit SELECTION as a first-class thing: where it lives, how it is let go of,
and what it looks like on the board.

WHY THIS EXISTS. The engine had a selection STATE but no selection GESTURE. The
same left-press that picked a unit also armed a drag, and a press on empty
ground called select(None) immediately - while that very same press begins a
camera pan (main.py). So every pan threw the selection away. On the board the
whole visual was ONE cyan ring around the ONE model the click landed on, handed
to pygame raw: measured below, that ring lands on about 1.2 real screen pixels
at default zoom, thinner than the base rim it is supposed to sit outside of.
The same defect class as the deployment-zone markings, and for the same reason
it went unnoticed for so long: draw_selected_model and SELECTED_MODEL_COLOR
appeared in NO test in this repo, and nothing drove InputManager with a click on
empty ground.

WHAT IS PINNED HERE:
  1. game/selection.py in isolation
  2. the forwarding properties, INCLUDING the two writers that bypass select()
  3. deselect: a click into the void lets go, a camera pan does not
  4. re-anchoring when the anchor model dies (rather than dropping the pick)
  5. the drawing - one ring per model, widths that follow the render scale
  6. source guards for the three main.py seams a behaviour test cannot reach

test_deployment_zone_markings.py owns the deployment zones' appearance and is
the model for section 5's ratio checks - the units here are ON-SCREEN pixels
throughout, the only unit in which "thicker" means anything.

Run: python test_unit_selection.py
"""

import ast
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((400, 300))

from game import movement, renderer as rmod  # noqa: E402
from game.board import Board  # noqa: E402
from game.input_handler import DRAG_START_THRESHOLD_PX, InputManager  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.turn import TurnTracker  # noqa: E402
from game.renderer import Renderer  # noqa: E402
from game.selection import Selection  # noqa: E402
from game.squad import Squad  # noqa: E402
from game.token import Token  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("unit selection")

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_SRC = open(os.path.join(HERE, "main.py"), encoding="utf-8").read()
INPUT_SRC = open(os.path.join(HERE, "game", "input_handler.py"), encoding="utf-8").read()
RENDERER_SRC = open(os.path.join(HERE, "game", "renderer.py"), encoding="utf-8").read()

PPI = 20.0


class P:
    name = "Probe Model"
    wounds = 1
    fly = False
    hover = False
    transport = False
    character = False
    squad_leader = False


def squad_at(points, owner="Player 1", name=None, radius=0.5):
    models = [
        Token(x_in=float(x), y_in=float(y), radius_in=radius, color=(90, 90, 90), profile=P())
        for x, y in points
    ]
    return Squad(name or f"1 Probe {owner}", models, owner=owner)


# --- 1. game/selection.py on its own ---------------------------------------

print("\n1) the Selection object")

sel = Selection()
c.true("a fresh selection is empty", sel.is_empty)
c.eq("...with nothing anchored", sel.model, None)

sq = squad_at([(1, 1), (2, 1), (3, 1)])
sel.set(sq.models[1])
c.true("set() picks the model's unit", sel.squad is sq)
c.true("...and anchors on that model", sel.model is sq.models[1])
c.true("...so it is no longer empty", not sel.is_empty)

c.true("holds() is identity on the squad", sel.holds(sq))
c.true("...and false for a different unit built the same way", not sel.holds(squad_at([(1, 1)])))
c.true("...and false for None, rather than throwing", not sel.holds(None))

sel.set(None)
c.true("set(None) clears the squad", sel.is_empty)
c.eq("...and the anchor", sel.model, None)

# The edge case select() had inline and this preserves: a token with no squad
# records the anchor but leaves the unit empty, so a stray token cannot make the
# panel believe a unit is picked.
loose = Token(x_in=0.0, y_in=0.0, radius_in=0.5, color=(1, 1, 1), profile=P())
sel.set(loose)
c.true("a squad-less token leaves the unit empty", sel.is_empty)
c.true("...while still recording the anchor", sel.model is loose)
sel.clear()


# --- 2. the forwarding properties ------------------------------------------

print("\n2) MovementController forwards onto it")

mc = MovementController()
c.true("the controller owns a Selection", isinstance(mc.selection, Selection))
c.eq("selected_squad reads through it", mc.selected_squad, None)

mc.select(sq.models[0])
c.true("select() writes the squad", mc.selected_squad is sq)
c.true("select() writes the anchor", mc.selected_model is sq.models[0])
c.true("...and the Selection agrees, i.e. there is ONE copy",
       mc.selection.squad is sq and mc.selection.model is sq.models[0])
c.eq("state follows", mc.state, movement.SELECTED)

mc.select(None)
c.true("select(None) clears both", mc.selected_squad is None and mc.selected_model is None)
c.eq("...and drops to IDLE", mc.state, movement.IDLE)

# The two places that assign the field DIRECTLY, bypassing select() entirely:
# MovementController.start_scout_move() (deliberately, per its own docstring)
# and game/torchstar_gambit.py. Any invariant put inside select() was already
# not universal because of them - a property is, which is the whole reason the
# pair is exposed this way instead of being renamed at ~25 call sites.
mc.selected_squad = sq
c.true("a DIRECT squad write still lands in the Selection", mc.selection.squad is sq)
mc.selected_model = sq.models[2]
c.true("a DIRECT anchor write still lands in the Selection", mc.selection.model is sq.models[2])
c.true("start_scout_move() still assigns it directly",
       "self.selected_squad = squad" in open(
           os.path.join(HERE, "game", "movement.py"), encoding="utf-8").read())
c.true("...and so does torchstar_gambit",
       "movement_controller.selected_squad = squad" in open(
           os.path.join(HERE, "game", "torchstar_gambit.py"), encoding="utf-8").read())


# --- 3. deselect: a click lets go, a pan does not --------------------------

print("\n3) letting go of a unit")

board = Board(40.0, 30.0, PPI)


def press_release(im, mc_, tokens, down_px, up_px):
    im.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": down_px, "button": 1}),
                    tokens, board, mc_, None)
    im.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": up_px}), tokens, board, mc_, None)
    im.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": up_px, "button": 1}),
                    tokens, board, mc_, None)


mine = squad_at([(5, 5), (6, 5)], owner="Player 1")
theirs = squad_at([(30, 20)], owner="Player 2", name="2 Probe")
tokens = list(mine.models) + list(theirs.models)
# A real TurnTracker, because can_select() short-circuits to True without one -
# so the "an enemy model changes nothing" check below would otherwise pass an
# enemy straight through and prove the opposite of what it says.
mc = MovementController(all_tokens=tokens, turn_tracker=TurnTracker(first_player="Player 1"))
im = InputManager()
c.true("the harness really can refuse an enemy unit", not mc.can_select(theirs))

on_model = (int(5 * PPI), int(5 * PPI))
void = (int(20 * PPI), int(10 * PPI))

press_release(im, mc, tokens, on_model, on_model)
c.true("clicking a model picks its unit", mc.selected_squad is mine)

# THE REPORTED ANNOYANCE: this press also begins a camera pan in main.py, so
# deselecting on the press meant every pan lost the selection.
far = (void[0] + 40, void[1] + 25)
press_release(im, mc, tokens, void, far)
c.true("a press on empty ground that TRAVELS is a pan - the pick survives",
       mc.selected_squad is mine)

press_release(im, mc, tokens, void, void)
c.true("a press on empty ground that does NOT travel is a click - the pick is let go",
       mc.selected_squad is None)

# The threshold is the same one the auto-move-on-drag gesture already uses, so
# the two gestures cannot disagree about what counts as a drag. Measured from
# both sides of it.
press_release(im, mc, tokens, on_model, on_model)
just_inside = (void[0] + DRAG_START_THRESHOLD_PX - 1, void[1])
press_release(im, mc, tokens, void, just_inside)
c.true(f"a wobble under {DRAG_START_THRESHOLD_PX}px still counts as a click",
       mc.selected_squad is None)

press_release(im, mc, tokens, on_model, on_model)
just_outside = (void[0] + DRAG_START_THRESHOLD_PX + 1, void[1])
press_release(im, mc, tokens, void, just_outside)
c.true(f"...and one over {DRAG_START_THRESHOLD_PX}px does not",
       mc.selected_squad is mine)

# An ENEMY model is not empty ground: select() refuses it (can_select), and no
# void press is armed, so the existing pick survives. Unchanged behaviour,
# pinned because the new branch sits right next to it.
enemy_px = (int(30 * PPI), int(20 * PPI))
press_release(im, mc, tokens, enemy_px, enemy_px)
c.true("clicking an enemy model changes nothing", mc.selected_squad is mine)

# Clicking a DIFFERENT own unit still switches, rather than needing a deselect
# first.
other = squad_at([(12, 12)], owner="Player 1", name="1 Probe Other")
tokens.extend(other.models)
other_px = (int(12 * PPI), int(12 * PPI))
press_release(im, mc, tokens, other_px, other_px)
c.true("clicking another of your units switches to it", mc.selected_squad is other)

c.true("no void press is left armed after a release", im._void_press_px is None)


# --- 4. the anchor model dies ----------------------------------------------

print("\n4) re-anchoring instead of dropping the pick")

sq2 = squad_at([(1, 1), (2, 1), (3, 1)])
mc = MovementController()
mc.select(sq2.models[0])
sq2.models[0].current_wounds = 0

# The premise: remove_dead_models() runs once per frame, so the corpse is still
# in squad.models when this fires. `not squad.models` is the wrong liveness
# test here and only becomes true a frame later (Fehlerklasse 12).
c.eq("the corpse is still listed when this runs", len(sq2.models), 3)
c.true("reanchor() reports that it did something", mc.selection.reanchor())
c.true("the unit is still picked", mc.selected_squad is sq2)
c.true("...anchored on a LIVE model", not mc.selected_model.is_dead())
c.true("...which is not the corpse", mc.selected_model is not sq2.models[0])
c.true("a live anchor is left alone", not mc.selection.reanchor())

for m in sq2.models:
    m.current_wounds = 0
mc.selection.model = sq2.models[1]
c.true("a wiped unit reanchors to nothing", mc.selection.reanchor())
c.true("...clearing the pick entirely", mc.selection.is_empty)

mc.selection.clear()
c.true("an empty selection is a no-op", not mc.selection.reanchor())


# --- 5. what it looks like --------------------------------------------------

print("\n5) drawn as a UNIT, at widths that follow the render scale")


def selection_layer(sel_, render_scale=1.0):
    """Just the selection overlay, on black - so ground art and terrain cannot
    contribute a pixel to a width measurement."""
    surface = pygame.Surface((board.width_px, board.height_px))
    surface.fill((0, 0, 0))
    Renderer(render_scale=render_scale).draw_selection(surface, board, sel_)
    return surface


def ring_run(surface, model, from_radius_px):
    """How many consecutive lit pixels there are scanning outward along +x from
    `from_radius_px` past the model's centre - i.e. the stroke thickness."""
    cx, cy = board.to_px(model.x_in, model.y_in)
    run = 0
    started = False
    for step in range(0, 60):
        x = int(round(cx + from_radius_px + step))
        if not (0 <= x < surface.get_width()):
            break
        r, g, b = surface.get_at((x, int(round(cy))))[:3]
        lit = (b > 40 and b > r)
        if lit:
            started = True
            run += 1
        elif started:
            break
    return run


wide = squad_at([(6, 6), (12, 6), (18, 6)])
sel = Selection()
sel.set(wide.models[0])

surf = selection_layer(sel, render_scale=1.0)
base_r = board.in_to_px_len(wide.models[0].radius_in)

# One ring per model - the whole point. The anchor is models[0]; the other two
# carry only the dimmer unit outline, which is what proves the outline is drawn
# per MODEL and not just around the clicked one.
outline_runs = [ring_run(surf, m, base_r) for m in wide.models[1:]]
c.true(f"every non-anchor model gets a ring too {outline_runs}", all(r > 0 for r in outline_runs))
c.true("the anchor model gets one as well", ring_run(surf, wide.models[0], base_r) > 0)

# The anchor is the BRIGHTER of the two, because line of sight is measured from
# it. Sampled on the ring itself, not averaged over the model.
def ring_pixel(surface, model):
    """The brightest lit pixel on the ring, found by scanning outward from the
    base rim rather than sampling one predicted coordinate: pygame draws a
    stroked circle as the annulus INSIDE its radius, so the exact radius is the
    outer edge and a point sample there lands on background as often as not.
    The first version of this did exactly that and read (0, 0, 0) off a ring
    that was demonstrably drawn."""
    cx, cy = board.to_px(model.x_in, model.y_in)
    base = board.in_to_px_len(model.radius_in)
    best = (0, 0, 0)
    for step in range(0, 40):
        x = int(round(cx + base + step))
        if not (0 <= x < surface.get_width()):
            break
        px = surface.get_at((x, int(round(cy))))[:3]
        if sum(px) > sum(best):
            best = px
    return best


anchor_px = ring_pixel(surf, wide.models[0])
outline_px = ring_pixel(surf, wide.models[1])
c.true(f"the anchor ring is brighter than the unit outline {anchor_px} vs {outline_px}",
       sum(anchor_px) > sum(outline_px))
c.true("...and both are the same hue family (blue-green, not the target orange)",
       anchor_px[2] > anchor_px[0] and outline_px[2] > outline_px[0])

# THE FIX. Both widths are on-screen pixels and go through _ring_width(), so
# tripling the board's render resolution has to triple the drawn stroke - the
# thing that was NOT true before, and the reason the ring was invisible.
plain = selection_layer(sel, render_scale=1.0)
scaled = selection_layer(sel, render_scale=3.0)
p_run = ring_run(plain, wide.models[1], base_r)
s_run = ring_run(scaled, wide.models[1], base_r)
c.true(f"the outline stroke follows the render scale ({p_run} -> {s_run})",
       p_run > 0 and abs(s_run - 3 * p_run) <= 2)

c.true("the outline width goes through _ring_width()",
       "width = self._ring_width(width_px)" in RENDERER_SRC)
c.true("...and the bump through _ring_bump()",
       "bump = self._ring_bump(bump_px)" in RENDERER_SRC)
c.true("...and the anchor ring through both",
       "width=self._ring_width(SELECTION_ANCHOR_WIDTH_PX)" in RENDERER_SRC
       and "self._ring_bump(SELECTION_ANCHOR_BUMP_PX)" in RENDERER_SRC)
c.true("no raw width=3 is handed to the selection any more",
       "SELECTED_MODEL_COLOR, (round(px), round(py)), round(r_px), width=3" not in RENDERER_SRC)

# NO NAME ON THE BOARD any more (User: "Entferne das Label, das den Squad
# namen anzeigt, wenn man eine Einheit auswaehlt. das label stoert auf dem
# spielfeld"). It moved to the left column's own selection box - see
# test_selection_header.py, which is where "the same string as the panel" is
# now asserted.
#
# THIS CHECK IS THE FLIPPED VERSION OF THE ONE THAT USED TO STAND HERE, and it
# keeps that one's hard-won geometry: the band has to be STRICTLY above the
# topmost ring pixel, or the rings leak into it and the check answers a
# question about rings instead of about a plate. The first version of the old
# check sampled 30 rows above the base rim, the rings reach up to
# rim - anchor_bump, and its A/B probe for "no label" came back 66/66 - a
# finding about the test, not about the code. Reused as-is, because "nothing is
# up there" is only worth anything if "up there" excludes the rings.
named = squad_at([(10, 10), (11, 10)], name="1 Storm Guardians 1")
sel2 = Selection()
sel2.set(named.models[0])
lbl = selection_layer(sel2, render_scale=1.0)
rim_top = board.to_px(10, 10)[1] - board.in_to_px_len(0.5)
ring_ceiling = int(rim_top - max(rmod.SELECTION_ANCHOR_BUMP_PX,
                                rmod.SELECTION_OUTLINE_BUMP_PX)) - 1
lit_above_rings = sum(
    1
    for y in range(0, max(1, ring_ceiling))
    for x in range(lbl.get_width())
    if sum(lbl.get_at((x, y))[:3]) > 0
)
c.eq(f"no label plate over the board any more ({lit_above_rings} px above the rings)",
     lit_above_rings, 0)
# The counter-check, without which the line above would also pass on a
# selection that drew nothing at all: the rings themselves are still there.
lit_rings = sum(
    1
    for y in range(max(1, ring_ceiling), lbl.get_height())
    for x in range(lbl.get_width())
    if sum(lbl.get_at((x, y))[:3]) > 0
)
c.true(f"...but the rings still are ({lit_rings} px)", lit_rings > 50)
c.true("draw_selection no longer calls the label helper",
       "_draw_selection_label" not in
       RENDERER_SRC.split("def draw_selection(")[1].split("def draw_placement_identity(")[0])

# The generalisation: the coherency-removal highlight was this same loop, and
# is now the second consumer rather than a thirteenth near-identical copy.
c.true("coherency removal goes through the shared outline",
       "def draw_coherency_removal_highlight" in RENDERER_SRC
       and "self.draw_squad_outline(" in RENDERER_SRC)
c.eq("draw_squad_outline is defined exactly once",
     RENDERER_SRC.count("def draw_squad_outline("), 1)


# --- 6. the main.py seams --------------------------------------------------

print("\n6) wiring a behaviour test cannot reach")

# ESC is a LADDER now: deselect first, then the recorded fullscreen quit.
c.true("ESC is no longer gated on fullscreen alone",
       "elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:" in MAIN_SRC)
c.true("...it deselects when something is picked",
       "if movement_controller.selected_squad is not None:\n                    movement_controller.select(None)" in MAIN_SRC)
# The lower rung is the GAME MENU now. Quitting is not gone - it moved into
# the menu's own Quit entry, and with it two changes worth naming: it takes one
# press more, and it works in a WINDOW too, where ESC used to do nothing at all
# (user: "im spiel oeffnet ein druck auf ESC das menue"). Pinned in both
# directions so neither half can drift back.
c.true("...and the lower rung opens the game menu",
       re.search(r"elif movement_controller\.selected_squad is not None:\s*\n"
                 r"\s*movement_controller\.select\(None\)\s*\n"
                 r"(\s*\n)?(\s*#[^\n]*\n)*\s*else:\s*\n"
                 r"(\s*#[^\n]*\n)*\s*_open_game_menu\(\)", MAIN_SRC) is not None)
c.true("...and ESC no longer ends the process on its own",
       "elif fullscreen:\n                    running = False" not in MAIN_SRC)
esc_i = MAIN_SRC.index("event.key == pygame.K_ESCAPE")
chain_i = MAIN_SRC.index("if event.type == pygame.QUIT:")
first_state_gate = MAIN_SRC.index("elif fight_warning_overlay.is_pending:")
c.true("ESC still sits above every controller-state gate, so nothing can swallow it",
       chain_i < esc_i < first_state_gate)

# The death sweep re-anchors rather than dropping the pick.
c.true("the sweep calls reanchor()",
       "movement_controller.selection.reanchor()" in MAIN_SRC)
c.true("...and only falls back to select(None) for a wiped unit",
       "if movement_controller.selected_squad is None:" in MAIN_SRC)

# The renderer is handed the Selection, not a lone model.
c.true("main.py draws the selection, not the selected model",
       "renderer.draw_selection(board_surface, board, movement_controller.selection)" in MAIN_SRC)
c.eq("draw_selected_model is gone entirely", MAIN_SRC.count("draw_selected_model"), 0)

# And the deselect really is deferred to the release rather than the press.
c.true("the press on empty ground arms, it does not deselect",
       "self._void_press_px = event.pos" in INPUT_SRC)
# Located by the BRANCH, not by the first mention of the word: splitting on
# "MOUSEBUTTONUP" broke the moment a docstring elsewhere in the file mentioned
# it (the line-drag poll explains what a lost MOUSEBUTTONUP would do). Same
# trap as counting a name instead of a call expression.
_release_branch = INPUT_SRC.split(
    "elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:")[-1]
c.true("...and the release is what calls select(None)",
       "movement_controller.select(None)" in _release_branch)
c.eq("select(None) is called from exactly one place in the input handler",
     INPUT_SRC.count("movement_controller.select(None)"), 1)


# --- 7. the three places that had to say WHICH unit ------------------------

print("\n7) naming the subject where it was missing")

from game import config as gconfig  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.shooting import ShootingController  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402
from game.ui.reserves_panel import CARD_WIDTH, ReservesPanel  # noqa: E402


class _StubPregame:
    is_active = False
    selected_unit = None

    def army(self, owner):
        return []


# (a) the left panel with NOTHING picked. It used to be the header and the
#     toggle strip over 220 px of nothing - the same blank column a click into
#     the void now produces deliberately, which read as the game having stopped.
panel = ActionPanel()
psurf = pygame.Surface((gconfig.LEFT_PANEL_WIDTH, 700))
prect = pygame.Rect(0, 0, gconfig.LEFT_PANEL_WIDTH, 700)
pturn = TurnTracker(deferred_start=True)
pdice = DiceManager()
pmover = MovementController(all_tokens=[], turn_tracker=pturn, dice_manager=pdice)
pshoot = ShootingController(turn_tracker=pturn, all_tokens=[], dice_manager=pdice)

psurf.fill((0, 0, 0))
panel.draw(psurf, prect, pmover, pshoot, pregame_controller=_StubPregame())
c.eq("nothing is picked for this render", pmover.selected_squad, None)
# A band below the "Actions" header and well above the bottom toolbar, so only
# the new hint text can contribute to it.
# The x range skips the panel's own 2px border, which otherwise contributes
# about four pixels on EVERY row - enough on its own to clear any sensible
# threshold, so the first version of this passed with the hint removed and the
# A/B probe came back 75/75. A finding about this test, not about the panel.
hint_px = sum(
    1
    for y in range(38, 130)
    for x in range(6, prect.width - 6)
    if psurf.get_at((x, y))[:3] != tuple(gconfig.PANEL_BG_COLOR[:3])
)
c.true(f"the empty panel says something instead of nothing ({hint_px} px)", hint_px > 100)

# (b) the reserves strip marks the card the player picked up. It only ever knew
#     which card was being DRAGGED, so the chosen one looked like its
#     neighbours.
rpanel = ReservesPanel()
rrect = pygame.Rect(0, 0, 900, 150)
pool = [squad_at([(1, 1)], name="1 Alpha 1"), squad_at([(2, 2)], name="1 Beta 1")]


def reserves_pixels(selected):
    surf = pygame.Surface((rrect.width, rrect.height))
    surf.fill((0, 0, 0))
    ReservesPanel().draw(surf, rrect, pool, selected_squad=selected)
    return surf


plain_cards = reserves_pixels(None)
marked_cards = reserves_pixels(pool[0])
differing = sum(
    1
    for y in range(rrect.height)
    for x in range(rrect.width)
    if plain_cards.get_at((x, y))[:3] != marked_cards.get_at((x, y))[:3]
)
c.true(f"the picked card is drawn differently ({differing} px differ)", differing > 100)
# ...and only THAT card: the second one must be pixel-identical either way, or
# the marker is really a whole-strip change and says nothing about which card.
second_card_x = range(CARD_WIDTH + 40, min(rrect.width, 2 * CARD_WIDTH + 30))
second_differs = sum(
    1
    for y in range(rrect.height)
    for x in second_card_x
    if plain_cards.get_at((x, y))[:3] != marked_cards.get_at((x, y))[:3]
)
c.eq("...and the card next to it is untouched", second_differs, 0)

# (c) the board during a Set Up. Rule 03.01 drew only the green/red legality
#     mask - nothing said which models it belonged to.
place = squad_at([(20, 15), (21, 15)], name="1 Dire Avengers 1")
psurface = pygame.Surface((board.width_px, board.height_px))
psurface.fill((0, 0, 0))
Renderer(render_scale=1.0).draw_placement_identity(psurface, board, place)
lit = sum(
    1
    for y in range(board.height_px)
    for x in range(board.width_px)
    if sum(psurface.get_at((x, y))[:3]) > 0
)
c.true(f"the unit being placed is outlined and named ({lit} px)", lit > 200)
c.true("...through the same shared outline as a selection",
       "def draw_placement_identity" in RENDERER_SRC
       and RENDERER_SRC.split("def draw_placement_identity")[1].split("def ")[0]
       .count("self.draw_squad_outline(") == 1)

# ...and it is wired only for a unit actually standing on the board.
#
# Checked as a CALL EXPRESSION rather than as one literal line: the call grew a
# keyword (placing_models, for rule 01.02.03's partial placement) and wrapped
# over four lines, and a pin that matches formatting goes red for a reformat
# while staying green for a dropped argument - this repo's error class 24.
_PLACEMENT_CALL = [
    node for node in ast.walk(ast.parse(MAIN_SRC))
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and node.func.attr == "draw_placement_identity"
]
c.eq("main.py draws it during a Set Up, once", len(_PLACEMENT_CALL), 1)
c.eq("...for the placement squad, on the board surface",
     [ast.unparse(a) for a in _PLACEMENT_CALL[0].args],
     ["board_surface", "board", "placement_squad"])
# The SUBSET, so a return says which models are the new ones - see
# game/renderer.py's draw_returning_models().
c.eq("...and hands it the models a partial placement owns",
     [kw.arg for kw in _PLACEMENT_CALL[0].keywords], ["placing_models"])
c.true("...only when the placement really is a partial one",
       "setup_controller.is_partial" in ast.unparse(_PLACEMENT_CALL[0]))
c.true("...gated on the placement really being under way",
       "placement_squad is setup_controller.setting_up_squad\n                    and setup_controller.state == setup.PLACING" in MAIN_SRC)
c.true("main.py tells the reserves strip which card is picked",
       "selected_squad=pregame_controller.selected_unit," in MAIN_SRC)

c.finish()
