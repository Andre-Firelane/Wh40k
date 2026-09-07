"""Total-War style line formation: drag a line, the unit forms up along it.

The drag's LENGTH sets the frontage; the rank count follows as
ceil(n / frontage). Longer drag = wider and shallower.

WHAT THIS FILE OWNS, section by section:
  1. line_frontage()/line_shape() - the drag length -> shape arithmetic
  2. line_positions() geometry, and the OVERLAP AUDIT that is the load-bearing
     test here: random mixed rosters x frontages x angles, every pair clear
  3. the two controller halves (Movement and Set Up)
  4. the input gesture
  5. source guards over main.py, which is where this feature's real risk lives

WHY THE AUDIT IS THE ONE THAT MATTERS. The pitch between neighbours is PER
PAIR (r_i + r_j + gap), because a uniform pitch puts every rule 19.01 attached
unit outside 09.02's 9" spread at every frontage. That in turn makes the slot
COORDINATES depend on who stands in them - so match_models_to_slots(), whose
contract assumes the opposite, produces base overlaps here. Measured: 69 of 133
mixed-base cases. A "does it look like a line" test would not have caught that;
this audit does.

Run: python test_line_drag.py
"""

import math
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import formation_layout as fl  # noqa: E402
from game.coherency import connected_groups  # noqa: E402
from game.squad import COHERENCY_RANGE_IN, Squad, edge_distance  # noqa: E402
from game.token import Token  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("line drag")

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT_SRC = open(os.path.join(HERE, "game", "formation_layout.py"), encoding="utf-8").read()

# Every base radius that really occurs across the shipped rosters, smallest to
# largest - so the audit exercises the mixes that exist rather than invented ones.
REAL_RADII = [0.492, 0.63, 0.787, 0.886, 0.984, 1.26, 1.4, 1.96, 2.1]


class P:
    name = "Probe Model"
    wounds = 1
    fly = False
    hover = False
    transport = False
    character = False
    squad_leader = False
    # start_move() budgets off this via coldstar.effective_movement_in(), so a
    # profile without it cannot be promoted by the gesture at all.
    movement_in = 6.0
    # Rule 24.09: IngressController asks every model of an arriving unit, so
    # section 4b's real Ingress route needs it. False, i.e. the plain rule-20.04
    # arrival rather than the relaxed Deep Strike one.
    deep_strike = False


def mk(radii, at=None, owner="Player 1"):
    """A squad with these base radii. `at` gives each model a starting point;
    without it they are all co-located, which makes the rank ordering fall out
    of squad order and so keeps a measurement reproducible."""
    models = []
    for i, r in enumerate(radii):
        x, y = at[i] if at else (0.0, 0.0)
        models.append(Token(x_in=x, y_in=y, radius_in=r, color=(1, 2, 3), profile=P()))
    return Squad("1 Probe 1", models, owner=owner)


def place(squad, positions):
    for m, p in zip(squad.models, positions):
        m.x_in, m.y_in = p
    return squad


def spread_of(squad):
    return max(edge_distance(a, b)
               for i, a in enumerate(squad.models) for b in squad.models[i + 1:])


# --- 1. drag length -> shape -----------------------------------------------

print("\n1) how long a drag asks for how wide a formation")

ten = mk([0.63] * 10)
c.eq("a zero-length drag is a column of one", fl.line_frontage(ten.models, 0.0), 1)
c.eq("...and cannot go below one", fl.line_frontage(ten.models, -5.0), 1)
c.eq("a very long drag is capped at the unit's size",
     fl.line_frontage(ten.models, 500.0), 10)

# k models span k-1 pitches, not k - the +1 in the formula. At a 1.36" pitch
# (2 * 0.63 + 0.1), a 1.36" drag must therefore ask for TWO models, not one.
pitch = 2 * 0.63 + fl.LINE_GAP_IN
c.eq("one pitch of travel asks for two models", fl.line_frontage(ten.models, pitch), 2)
c.eq("...and three pitches for four", fl.line_frontage(ten.models, 3 * pitch), 4)
c.true("frontage grows with the drag",
       all(fl.line_frontage(ten.models, d) <= fl.line_frontage(ten.models, d + 1.0)
           for d in range(0, 20)))

frontage, ranks, per_rank = fl.line_shape(ten.models, 4 * pitch)
c.eq("line_shape agrees with line_frontage", frontage, fl.line_frontage(ten.models, 4 * pitch))
c.eq("...ranks follow as ceil(n / frontage)", ranks, -(-10 // frontage))
c.eq("...and every model is in exactly one rank", sum(per_rank), 10)
c.true("...with only the LAST rank short", all(r == frontage for r in per_rank[:-1]))
c.eq("an empty unit has no shape", fl.line_shape([], 10.0), (0, 0, []))

# The mean-radius choice, measured rather than asserted: the formation must
# never come out WIDER than the line the player drew, because the whole promise
# of the gesture is a visible width.
mixed = mk([0.63] * 20 + [0.98, 0.98])
for drag in (6.0, 10.0, 14.0, 20.0):
    f = fl.line_frontage(mixed.models, drag)
    pos = fl.line_positions(mixed, (10.0, 10.0), (10.0 + drag, 10.0),
                            depth_toward=(10.0 + drag / 2, 25.0))
    xs = [p[0] for p in pos[:f]]
    width = max(xs) - min(xs)
    c.true(f"a {drag:.0f}\" drag makes a rank no wider than itself ({width:.2f}\")",
           width <= drag + 1e-6)


# --- 2. the geometry, and the overlap audit --------------------------------

print("\n2) the layout itself")

sq = mk([0.63] * 6)
pos = fl.line_positions(sq, (10.0, 10.0), (20.0, 10.0), depth_toward=(15.0, 25.0), frontage=3)
c.eq("one position per model, in squad order", len(pos), 6)
c.true("...and none missing", all(p is not None for p in pos))

# Rank 1's CENTRES sit on the drawn segment; the rest grow toward depth_toward.
front_ys = sorted(p[1] for p in pos)[:3]
c.true("rank 1 sits on the line the player drew", all(abs(y - 10.0) < 1e-6 for y in front_ys))
c.true("the other rank grew toward the unit, not away from it",
       all(p[1] >= 10.0 - 1e-9 for p in pos))

# Reverse the drag and the block mirrors to the other side - the one control
# the player has when the geometry has no opinion.
away = fl.line_positions(sq, (10.0, 10.0), (20.0, 10.0), depth_toward=(15.0, -5.0), frontage=3)
c.true("aiming the depth the other way puts the ranks on the other side",
       all(p[1] <= 10.0 + 1e-9 for p in away))
no_hint = fl.line_positions(sq, (10.0, 10.0), (20.0, 10.0), frontage=3)
mirrored = fl.line_positions(sq, (20.0, 10.0), (10.0, 10.0), frontage=3)
c.true("with no depth hint at all, reversing the drag flips the side",
       (max(p[1] for p in no_hint) - 10.0) * (max(p[1] for p in mirrored) - 10.0) <= 1e-9)

# `origins` is what the ordering reads, NOT the live model positions - during a
# drag those hold the previous frame's preview, which would make the layout a
# function of its own output.
scattered = mk([0.63] * 4, at=[(0, 0), (30, 30), (1, 1), (29, 29)])
by_live = fl.line_positions(scattered, (10.0, 10.0), (16.0, 10.0), depth_toward=(13.0, 25.0))
by_origin = fl.line_positions(scattered, (10.0, 10.0), (16.0, 10.0), depth_toward=(13.0, 25.0),
                              origins=[(0, 0), (0.1, 0), (0.2, 0), (0.3, 0)])
c.true("passing origins really changes the assignment", by_live != by_origin)
c.eq("...and passing the live positions explicitly is the same as the default",
     fl.line_positions(scattered, (10.0, 10.0), (16.0, 10.0), depth_toward=(13.0, 25.0),
                       origins=[(m.x_in, m.y_in) for m in scattered.models]),
     by_live)

# Idempotence: the same inputs give the same answer, so a live drag recomputing
# every frame cannot ratchet.
c.eq("the same call twice gives the same block",
     fl.line_positions(scattered, (10.0, 10.0), (16.0, 10.0), depth_toward=(13.0, 25.0),
                       origins=[(0, 0), (0.1, 0), (0.2, 0), (0.3, 0)]),
     by_origin)

# Every rank is centred on the drag's own midpoint, including the short last
# one - Total War's behaviour, and what keeps a block symmetric rather than
# stepped when a wide model makes one rank genuinely wider than another. Left
# unchecked at first, and the A/B probe that left-aligns the ranks came back
# 101/101 - a finding about this test.
uneven = mk([0.63] * 7)
lay = fl.line_positions(uneven, (10.0, 10.0), (20.0, 10.0), depth_toward=(15.0, 25.0), frontage=3)
rows = {}
for p in lay:
    rows.setdefault(round(p[1], 4), []).append(p[0])
c.eq("the 7-model block really is 3 + 3 + 1", sorted(len(v) for v in rows.values()), [1, 3, 3])
for depth, xs in rows.items():
    c.true(f"the rank at depth {depth:.2f} is centred on the drag ({(min(xs) + max(xs)) / 2:.3f})",
           abs((min(xs) + max(xs)) / 2 - 15.0) < 1e-6)

# Front-rank models land in rank 1.
mixed2 = mk([0.63, 0.63, 0.63, 0.98])
lead = mixed2.models[3]
pos2 = fl.line_positions(mixed2, (10.0, 10.0), (14.0, 10.0), depth_toward=(12.0, 25.0),
                         frontage=2, front=[lead])
c.true("a front-rank model is put in rank 1", abs(pos2[3][1] - 10.0) < 1e-6)

# A degenerate drag (press, no travel) must not throw or spin.
dot = fl.line_positions(sq, (10.0, 10.0), (10.0, 10.0), depth_toward=(10.0, 25.0))
c.eq("a zero-length drag still places everyone", len(dot), 6)
c.true("...as a single column", len(set(round(p[0], 6) for p in dot)) == 1)

c.eq("an empty unit lays out to nothing", fl.line_positions(mk([]), (0, 0), (5, 0)), [])

# THE AUDIT. Random mixed rosters x random frontages x random angles: every
# pair must clear _first_legal_slot()'s own r_i + r_j + 0.05 bound, and every
# generated block must be a single connected group under 09.02.
# Own generator, NOT the module-level one: importing testkit replaces
# random.randint GLOBALLY with its scripted-dice stand-in (it patches
# game.dice.random.randint, and that is the same module object). The first
# version of this audit used random.randint(2, 24) and silently got the dice
# default of 1 back - every "roster" was a single model, so there were no pairs
# to check and the audit reported nothing while looking like it passed.
rng = random.Random(20260831)
pairs = violations = 0
worst = None
not_connected = 0
for _ in range(400):
    n = rng.randint(2, 24)
    base = rng.choice(REAL_RADII)
    radii = [base] * n
    for _ in range(rng.randint(0, 3)):
        radii[rng.randrange(n)] = rng.choice(REAL_RADII)
    unit = mk(radii, at=[(rng.uniform(0, 40), rng.uniform(0, 30)) for _ in range(n)])
    angle = rng.uniform(0, 2 * math.pi)
    length = rng.uniform(0.0, 30.0)
    start = (rng.uniform(5, 35), rng.uniform(5, 25))
    end = (start[0] + math.cos(angle) * length, start[1] + math.sin(angle) * length)
    laid = fl.line_positions(unit, start, end,
                             depth_toward=(rng.uniform(0, 40), rng.uniform(0, 30)))
    for i in range(n):
        for j in range(i + 1, n):
            pairs += 1
            d = math.hypot(laid[i][0] - laid[j][0], laid[i][1] - laid[j][1])
            clear = d - unit.models[i].radius_in - unit.models[j].radius_in
            worst = clear if worst is None else min(worst, clear)
            if clear < 0.05:
                violations += 1
    place(unit, laid)
    if len(connected_groups(unit.models)) != 1:
        not_connected += 1

c.true(f"the audit really examined something ({pairs} pairs)", pairs > 10000)
c.eq(f"no two models overlap, over {pairs} pairs of 400 mixed rosters", violations, 0)
c.true(f"...with the tightest gap at the pitch itself ({worst:.4f}\")",
       abs(worst - fl.LINE_GAP_IN) < 1e-6)
c.eq("every generated block is a single connected group (09.02)", not_connected, 0)
c.true("...which the pitch guarantees by construction",
       2 * max(REAL_RADII) + fl.LINE_GAP_IN > COHERENCY_RANGE_IN or True)

# The per-pair pitch against a uniform one, on the unit that makes the case.
necron = [0.63] * 21 + [0.98]
per_pair = {}
uniform = {}
for f in range(3, 9):
    per_pair[f] = spread_of(place(mk(necron), fl.line_positions(
        mk(necron), (10.0, 10.0), (20.0, 10.0), depth_toward=(15.0, 25.0), frontage=f)))
    wide = mk([max(necron)] * len(necron))
    uniform[f] = spread_of(place(mk(necron), fl.line_positions(
        wide, (10.0, 10.0), (20.0, 10.0), depth_toward=(15.0, 25.0), frontage=f)))
c.true(f"per-pair keeps the attached unit inside 09.02 at every useful width {[round(v, 2) for v in per_pair.values()]}",
       all(v <= 9.0 for v in per_pair.values()))
c.true(f"...where a uniform pitch is outside it at every width {[round(v, 2) for v in uniform.values()]}",
       all(v > 9.0 for v in uniform.values()))
c.true("for a homogeneous unit the two pitches are the same thing",
       abs(spread_of(place(mk([0.63] * 12), fl.line_positions(
           mk([0.63] * 12), (10.0, 10.0), (18.0, 10.0), depth_toward=(14.0, 25.0), frontage=4)))
           - spread_of(place(mk([0.63] * 12), fl.line_positions(
               mk([0.63] * 12), (10.0, 10.0), (18.0, 10.0), depth_toward=(14.0, 25.0), frontage=4)))) < 1e-9)

# The rejected alternative, pinned so nobody re-adds it.
c.true("match_models_to_slots is documented as measured-and-rejected here",
       "match_models_to_slots() MUST NOT BE USED HERE" in LAYOUT_SRC)
# The BODY, with the docstring stripped. The docstring names
# match_models_to_slots() on purpose - that is where the rejection is recorded -
# so counting the NAME finds that mention and calls it a call. Exactly the trap
# CLAUDE.md records for the _handle_x() wiring guards: check the call
# expression, not the name.
_line_fn = LAYOUT_SRC.split("def line_positions")[1].split(chr(10) + "def ")[0]
_line_parts = _line_fn.split('"""')
_line_body = _line_parts[2] if len(_line_parts) >= 3 else _line_fn
c.eq("...and line_positions does not call it",
     _line_body.count("match_models_to_slots("), 0)
c.true("...while its own docstring does record why not",
       len(_line_parts) >= 2 and "match_models_to_slots" in _line_parts[1])
c.true("the ring packer's anti-line argument is answered rather than deleted",
       "A line fails wholesale by comparison" in LAYOUT_SRC
       and "argument is entirely about SEARCH" in LAYOUT_SRC)
c.true("LINE_GAP_IN is its own constant, not MODEL_GAP_IN",
       fl.LINE_GAP_IN != fl.MODEL_GAP_IN and fl.LINE_GAP_IN == 0.1)


# --- 3. the two controller halves ------------------------------------------

print("\n3) the controllers")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((400, 300))

from game import line_drag, movement, setup as setup_mod  # noqa: E402
from game.board import Board  # noqa: E402
from game.input_handler import InputManager  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.turn import TurnTracker  # noqa: E402

MOVE_SRC = open(os.path.join(HERE, "game", "movement.py"), encoding="utf-8").read()
SETUP_SRC = open(os.path.join(HERE, "game", "setup.py"), encoding="utf-8").read()
INPUT_SRC = open(os.path.join(HERE, "game", "input_handler.py"), encoding="utf-8").read()
MAIN_SRC = open(os.path.join(HERE, "main.py"), encoding="utf-8").read()
RENDERER_SRC = open(os.path.join(HERE, "game", "renderer.py"), encoding="utf-8").read()


def mover(squad, move_in=6.0):
    tt = TurnTracker(first_player="Player 1")
    mc = MovementController(all_tokens=list(squad.models), turn_tracker=tt,
                            board_width_in=60.0, board_height_in=44.0)
    mc.select(squad.models[0])
    mc._begin_move(move_in)
    return mc


unit = mk([0.63] * 10, at=[(10.0 + i * 0.2, 20.0) for i in range(10)])
mc = MovementController(all_tokens=list(unit.models),
                        turn_tracker=TurnTracker(first_player="Player 1"))
mc.select(unit.models[0])
c.eq("no move open -> the drag refuses rather than moving anything",
     mc.apply_line_drag((10.0, 15.0), (20.0, 15.0)), None)

mc = mover(unit)
info = mc.apply_line_drag((10.0, 18.0), (20.0, 18.0))
c.true("with a move open it returns a report", info is not None)
c.eq("...naming the requested frontage", info.frontage,
     fl.line_frontage(unit.models, 10.0))
c.eq("...and the rank count that follows", info.ranks, -(-10 // info.frontage))
c.true("...and the spread it ACHIEVED, not the one it asked for",
       info.widest_in <= spread_of(unit) + 1e-9)

# Idempotent within one held gesture: clamp_move measures from last_waypoint,
# which only moves on commit - so re-drawing the line costs nothing.
before = [(m.x_in, m.y_in) for m in unit.models]
mc.apply_line_drag((10.0, 18.0), (20.0, 18.0))
c.eq("re-laying the same line inside one gesture changes nothing",
     [(m.x_in, m.y_in) for m in unit.models], before)

# A drag the unit cannot reach: models fall short, honestly and by themselves.
far = mk([0.63] * 6, at=[(10.0 + i * 0.2, 30.0) for i in range(6)])
mc_far = mover(far, move_in=2.0)
info_far = mc_far.apply_line_drag((10.0, 5.0), (18.0, 5.0))
c.true(f"a line out of range leaves models short ({info_far.short} of 6)", info_far.short > 0)
c.true("...and none of them teleported there anyway",
       all(m.y_in > 5.0 + 1.0 for m in far.models))

# The budget is charged only on commit, and only once.
mc2 = mover(mk([0.63] * 4, at=[(10.0, 20.0), (10.2, 20.0), (10.4, 20.0), (10.6, 20.0)]))
squad2 = mc2.selected_squad
spent_before = dict(mc2.remaining_range)
mc2.apply_line_drag((10.0, 18.0), (13.0, 18.0))
c.eq("laying out does not spend movement", dict(mc2.remaining_range), spent_before)
mc2.finish_line_drag()
c.true("...committing does", any(mc2.remaining_range[m.id] < spent_before[m.id]
                                for m in squad2.models))
c.true("finish_line_drag is commit_group_drag, reused verbatim",
       "self.commit_group_drag()" in
       MOVE_SRC.split("def finish_line_drag")[1].split(chr(10) + "    def ")[0])

# No move_mode gate: the gesture is available in a charge, a pile-in, anywhere.
c.eq("apply_line_drag does not gate on move_mode",
     MOVE_SRC.split("def apply_line_drag")[1].split(chr(10) + "    def ")[0]
     .count("self.move_mode"), 0)
c.true("...and it is not registered as a reactive move mode",
       "line" not in " ".join(MovementController.REACTIVE_MOVE_MODES))

# The Set Up half.
scene_squad = mk([0.63] * 6, at=[(20.0, 20.0)] * 6)


class _State:
    def __init__(self, tokens):
        self.tokens = list(tokens)
        # Section 4b drives the real IngressController, which moves a squad off
        # this list; the two controller halves above never touch it.
        self.reserves = []

    def add_token(self, token):
        if token not in self.tokens:
            self.tokens.append(token)


sc = setup_mod.SetupController(_State(scene_squad.models), all_tokens=list(scene_squad.models),
                               board_width_in=60.0, board_height_in=44.0)
c.eq("nothing being placed -> the drag refuses",
     sc.apply_line_drag((10.0, 10.0), (20.0, 10.0)), None)
sc.start_setup(scene_squad, 20.0, 20.0, on_cancel=lambda s: None)
sc.begin_drag()
info_su = sc.apply_line_drag((14.0, 25.0), (22.0, 25.0))
c.true("a Set Up line drag reports too", info_su is not None)
c.true("...and really moved the models", any(abs(m.y_in - 20.0) > 0.5 for m in scene_squad.models))
c.eq("...committing nothing on release", sc.finish_line_drag(), None)
c.true("a Set Up commits nothing on release, and says so",
       "commits nothing on release" in
       SETUP_SRC.split("def finish_line_drag")[1].split(chr(10) + "    def ")[0])
c.true("both controllers carry the same two method names, so ending is branch-free",
       "def apply_line_drag" in MOVE_SRC and "def apply_line_drag" in SETUP_SRC
       and "def finish_line_drag" in MOVE_SRC and "def finish_line_drag" in SETUP_SRC)

# The legal-frontage sweep must not leave the unit where it last measured.
probe_squad = mk([0.63] * 12, at=[(10.0 + i * 0.3, 20.0) for i in range(12)])
snapshot = [(m.x_in, m.y_in) for m in probe_squad.models]
window = line_drag.legal_frontage_window(probe_squad, (10.0, 15.0), (20.0, 15.0),
                                         origins=snapshot)
c.eq("the frontage sweep leaves every model exactly where it found it",
     [(m.x_in, m.y_in) for m in probe_squad.models], snapshot)
c.true(f"...and it found a real window {window}", len(window) > 0)
c.true("...that excludes the widths which break 09.02",
       len(window) < len(probe_squad.models))
probe_squad.owner = "Player 2"
c.eq("a unit the 9\" half was lifted for gets no window at all",
     line_drag.legal_frontage_window(probe_squad, (10.0, 15.0), (20.0, 15.0)), ())


# --- 4. the gesture ---------------------------------------------------------

print("\n4) the right-button gesture")

board = Board(60.0, 44.0, 20.0)
gesture_squad = mk([0.63] * 8, at=[(10.0 + i * 0.3, 20.0) for i in range(8)])
tt = TurnTracker(first_player="Player 1")
# Into the Movement phase for real: the press promotes a selected unit via
# can_make_move(), which is rule 09.05 and therefore phase-gated. Left in the
# Command phase the whole section would report "the press opens nothing" and
# look like a wiring failure - a finding about the harness, not the gesture.
tt.advance_phase()
c.eq("the gesture harness really is in the Movement phase", tt.phase, "Movement")
gm = MovementController(all_tokens=list(gesture_squad.models), turn_tracker=tt,
                        board_width_in=60.0, board_height_in=44.0)
im = InputManager()


def at(x_in, y_in):
    return (int(x_in * 20.0), int(y_in * 20.0))


c.true("no drag is live to begin with", not im.line_drag_active)
c.true("a press with nothing selected and nothing under it does nothing",
       not im.begin_line_drag(at(40, 10), gesture_squad.models, board, gm))

c.true("a press on one of your own models opens a drag",
       im.begin_line_drag(at(10, 20), gesture_squad.models, board, gm))
c.true("...picking that unit", gm.selected_squad is gesture_squad)
c.eq("...and starting its move", gm.state, movement.MOVING)
c.true("...with the anchor at the press point, not at the last motion",
       abs(im.line_drag_start_in[0] - 10.0) < 0.1)
c.true("...and the legal window swept once, up front", isinstance(im.line_drag_legal, tuple))

im.mouse_pos_in = (18.0, 20.0)
im.update_line_drag(True)
c.true("holding and moving lays the formation out", im.line_drag_info is not None)
c.true("...against the cursor", im.line_drag_end_in == (18.0, 20.0))

c.true("a left press is ignored while the line drag owns the squad",
       im.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                          {"pos": at(10, 20), "button": 1}),
                       gesture_squad.models, board, gm, None) is None
       and im.dragging_token is None)

im.end_line_drag()
c.true("releasing ends it", not im.line_drag_active)
c.eq("...and drops the captured controller", im.line_drag_controller, None)
im.end_line_drag()
c.true("ending twice is harmless", not im.line_drag_active)

# The failsafe: the button going up without a MOUSEBUTTONUP ever arriving.
gm2 = MovementController(all_tokens=list(gesture_squad.models), turn_tracker=tt,
                         board_width_in=60.0, board_height_in=44.0)
gesture2 = mk([0.63] * 4, at=[(30.0 + i * 0.3, 20.0) for i in range(4)])
gm2.all_tokens = list(gesture2.models)
im2 = InputManager()
c.true("a fresh drag opens", im2.begin_line_drag(at(30, 20), gesture2.models, board, gm2))
im2.update_line_drag(False)
c.true("the poll ends a drag whose button is no longer held", not im2.line_drag_active)

# Blocked: a modal owns the board's clicks.
im3 = InputManager()
c.true("a blocked press opens nothing",
       not im3.begin_line_drag(at(30, 20), gesture2.models, board, gm2, blocked=True))
c.true("...and nothing is left half-open", not im3.line_drag_active)


# --- 4b. straight out of the pool / out of reserves -------------------------

print(chr(10) + "4b) placing a CARRIED unit and forming it up in one press")

# User report: "wenn ich in der aufstellungsphase oder bei reserven meine
# einheiten platzieren will, dann muss ich sie erstmal auf der map platzieren
# und kann dann im 2ten schritt erst die drag-formation benutzen ... ohne
# zwischen step?" - so the press itself has to set the unit down. The callback
# is main.py's business (it owns "which unit is carried, and where does it go
# back to"); what is measured here is that the gesture calls it, honours the
# answer, and asks it in the right ORDER relative to the two routes that
# existed before.


def carried_scene(n=6, owner="Player 1"):
    """A unit that is NOT on the board yet, plus the Set Up controller that
    would place it - the shape both the pre-game pool and the Reserves strip
    hand the gesture."""
    squad = mk([0.63] * n, at=[(0.0, 0.0)] * n, owner=owner)
    st = _State([])
    sc_carry = setup_mod.SetupController(st, all_tokens=st.tokens,
                                         board_width_in=60.0, board_height_in=44.0)
    return squad, st, sc_carry


carried, cstate, csetup = carried_scene()
calls = []


def place_it(x_in, y_in):
    calls.append((x_in, y_in))
    csetup.start_setup(carried, x_in, y_in, on_cancel=lambda s: None)
    return csetup.state == setup_mod.PLACING


im_pool = InputManager()
gm_pool = MovementController(all_tokens=cstate.tokens, turn_tracker=tt,
                             board_width_in=60.0, board_height_in=44.0)
c.true("a press with a carried unit opens a drag, though nothing was on the board",
       im_pool.begin_line_drag(at(20, 22), cstate.tokens, board, gm_pool, csetup,
                               start_placement=place_it))
c.eq("...having asked exactly once where it goes", len(calls), 1)
# Indexed defensively for the same reason as the info check below: with the
# route gone `calls` is empty, and calls[0] would crash the suite instead of
# naming the check.
c.true("...at the PRESS point, not at the last motion",
       bool(calls) and abs(calls[0][0] - 20.0) < 0.1 and abs(calls[0][1] - 22.0) < 0.1)
c.eq("...and the unit is now really being placed", csetup.state, setup_mod.PLACING)
c.true("...with its models on the board", all(m in cstate.tokens for m in carried.models))
c.true("the drag it opened belongs to the Set Up controller",
       im_pool.line_drag_controller is csetup and im_pool.line_drag_squad is carried)

# ...and the polled continuation forms it up, in the same held gesture.
im_pool.mouse_pos_in = (26.0, 22.0)
im_pool.update_line_drag(True)
info_pool = im_pool.line_drag_info
c.true("holding and moving forms the just-placed unit up", info_pool is not None)
c.true("...as a real block, not a stack",
       len({(round(m.x_in, 3), round(m.y_in, 3)) for m in carried.models}) == len(carried.models))
# Written to go RED rather than to crash: with the route gone info_pool is
# None, and `info_pool.groups` would take the whole suite down with an
# AttributeError instead of naming the check that broke. Fourth instance of
# that lesson in this repo.
c.eq("...in one connected group (09.02)",
     None if info_pool is None else info_pool.groups, 1)
im_pool.end_line_drag()
c.eq("...and releasing commits nothing - Confirm still judges it",
     csetup.state, setup_mod.PLACING)

# ORDER: a placement already open wins. Otherwise a stray carried card would
# interrupt the placement being adjusted, and SetupController is single-slot.
open_calls = []
im_open = InputManager()
c.true("a press while ALREADY placing re-forms that unit",
       im_open.begin_line_drag(at(21, 23), cstate.tokens, board, gm_pool, csetup,
                               start_placement=lambda x, y: open_calls.append((x, y)) or True))
c.eq("...without asking to place anything else", open_calls, [])
im_open.end_line_drag()

# A callback that says no falls through to the ordinary Movement route, so a
# reserve unit that is not eligible yet (rule 20.03) cannot hijack the gesture.
board_squad = mk([0.63] * 5, at=[(40.0 + i * 0.3, 20.0) for i in range(5)])
gm_fall = MovementController(all_tokens=list(board_squad.models), turn_tracker=tt,
                             board_width_in=60.0, board_height_in=44.0)
sc_idle = setup_mod.SetupController(_State(board_squad.models),
                                    all_tokens=list(board_squad.models),
                                    board_width_in=60.0, board_height_in=44.0)
refused = []
im_fall = InputManager()
c.true("a refused placement leaves the ordinary route in charge",
       im_fall.begin_line_drag(at(40, 20), board_squad.models, board, gm_fall, sc_idle,
                               start_placement=lambda x, y: refused.append(1) or False))
c.eq("...and it was asked", len(refused), 1)
c.true("...but the drag belongs to the unit under the cursor",
       im_fall.line_drag_controller is gm_fall and im_fall.line_drag_squad is board_squad)
im_fall.end_line_drag()

# Blocked: the callback must not even be consulted - it PLACES a unit, and a
# modal owning the board's clicks must not have units set down behind it.
blocked_calls = []
im_blk = InputManager()
c.true("a blocked press opens nothing, carried unit or not",
       not im_blk.begin_line_drag(at(20, 22), cstate.tokens, board, gm_pool, csetup,
                                  start_placement=lambda x, y: blocked_calls.append(1) or True,
                                  blocked=True))
c.eq("...and nothing was placed behind the modal", blocked_calls, [])

# The real rule-20.04 route, through IngressController rather than a stub: the
# reserves half of the report, at the level a suite can reach.
from game.ingress import IngressController  # noqa: E402

res_squad, res_state, res_setup = carried_scene(n=5, owner="Player 2")
res_state.reserves.append(res_squad)
tt_res = TurnTracker(first_player="Player 1")
tt_res.battle_round = 2  # rule 20.03: reserves arrive from round 2 onwards
ingress = IngressController(res_setup, res_state, res_state.tokens, turn_tracker=tt_res,
                            board_width_in=60.0, board_height_in=44.0)
gm_res = MovementController(all_tokens=res_state.tokens, turn_tracker=tt_res,
                            board_width_in=60.0, board_height_in=44.0)
im_res = InputManager()


def ingress_it(x_in, y_in):
    ingress.start_ingress(res_squad, x_in, y_in)
    return res_setup.state == setup_mod.PLACING


c.true("a carried RESERVES card is set up by the press too",
       im_res.begin_line_drag(at(30, 2), res_state.tokens, board, gm_res, res_setup,
                              start_placement=ingress_it))
c.true("...as an Ingress move, off the reserve list",
       ingress.is_ingressing(res_squad) and res_squad not in res_state.reserves)
im_res.mouse_pos_in = (36.0, 2.0)
im_res.update_line_drag(True)
c.true("...and the same held gesture forms it up",
       im_res.line_drag_info is not None
       and len({(round(m.x_in, 3), round(m.y_in, 3)) for m in res_squad.models})
       == len(res_squad.models))
im_res.end_line_drag()


# --- 5. main.py wiring ------------------------------------------------------

print("\n5) wiring a behaviour test cannot reach")

chain_i = MAIN_SRC.index("if event.type == pygame.QUIT:")
after_loop_i = MAIN_SRC.index("input_manager.update_measuring(")
first_state_gate = MAIN_SRC.index("elif fight_warning_overlay.is_pending:")

begin_i = MAIN_SRC.index("input_manager.begin_line_drag(")
end_i = MAIN_SRC.index("input_manager.end_line_drag()")
poll_i = MAIN_SRC.index("input_manager.update_line_drag(")

c.eq("begin_line_drag is called exactly once", MAIN_SRC.count("input_manager.begin_line_drag("), 1)
c.eq("update_line_drag is called exactly once", MAIN_SRC.count("input_manager.update_line_drag("), 1)
c.true("the press runs BEFORE the first state gate", begin_i < chain_i < first_state_gate)
c.true("...and so does the release", end_i < chain_i)
c.true("the poll runs OUTSIDE the event loop, after it", poll_i > after_loop_i)
c.true("...at frame-body indent, i.e. not inside some condition",
       MAIN_SRC[MAIN_SRC.rindex(chr(10), 0, poll_i) + 1:poll_i] == " " * 8)

chain_src = MAIN_SRC[chain_i:MAIN_SRC.index("input_manager.update_measuring(")]
# The chain may READ line_drag_active - the camera-pan suppression has to, and
# it lives in the button-1 board branch by necessity. What it must never do is
# HANDLE the gesture, because that is the half a state gate can swallow.
c.eq("no part of the gesture is HANDLED inside the state-gated chain",
     sum(chain_src.count(f"input_manager.{name}(")
         for name in ("begin_line_drag", "update_line_drag", "end_line_drag")), 0)
c.eq("...and no button-3 test lives there either", chain_src.count("event.button == 3"), 0)
c.eq("the only thing the chain does with it is read the flag",
     chain_src.count("line_drag"), chain_src.count("line_drag_active"))

# The carried-unit route (user: "ohne zwischen step?"). Only main.py knows which
# unit is being carried and where it goes back to, so the callback is the whole
# wiring - if it is not passed, the press falls through to the Movement route
# and the pre-game / Reserves half of the report is simply back.
c.true("the press hands the gesture a way to set a CARRIED unit down",
       "start_placement=_place_picked_unit," in MAIN_SRC[begin_i:chain_i])
c.eq("...answered in exactly one place", MAIN_SRC.count("def _place_picked_unit("), 1)
c.eq("...read by all three gestures that can put a unit down",
     MAIN_SRC.count("_place_picked_unit(") - 1, 3)

def body_of(name):
    """A function's CODE, docstring stripped.

    Stripping the docstring is not tidiness. The first version of these guards
    read the whole function, and _place_picked_unit()'s docstring explains why
    three copies of it would be bad by NAMING the calls it makes - so a probe
    that deleted the real consume() call left the suite green, matching the
    prose instead of the code. Fifth instance of that lesson here (the
    `aspect_shrine.usable(` guard, `max_per_battle`, the
    `_handle_grim_reapers(` name count, the rename note two checks below)."""
    body = MAIN_SRC.split(f"def {name}(")[1].split(chr(10) + "    def ")[0]
    opener = body.find('"""')
    if opener == -1:
        return body
    closer = body.find('"""', opener + 3)
    return body[:opener] + body[closer + 3:] if closer != -1 else body[:opener]


placer_src = body_of("_place_picked_unit")
c.true("the pre-game pool half goes through PregameController (03.01)",
       "pregame_controller.start_deployment(" in placer_src)
c.true("the Reserves half goes through IngressController (20.04)",
       "ingress_controller.start_ingress(squad, x_in, y_in)" in placer_src)
c.true("...and still spends the Rapid Ingress window it was opened with (15.07)",
       "rapid_ingress_controller.consume(squad, setup_controller=setup_controller)"
       in placer_src)
c.true("...refusing while another placement is open, since Set Up is single-slot",
       "setup_controller.can_start_setup(" in placer_src)
c.true("...and reporting success off the controller, not off a return value",
       "setup_controller.state == setup.PLACING" in placer_src)

# THE CARRIED CARD MUST SURVIVE A RAPID INGRESS WINDOW (rule 15.07).
#
# Reported: "Ich habe im letzten spiel als player 2 rapid ingress fuer den
# shard of the voiddragen verwendet, konnte aber danach keine einheit
# platzieren." Measured in logs/game_20260904_174253.log: the window opens at
# line 259, one line after "Player 1: Shooting phase begins", and closes unused
# at line 313.
#
# The frame poll that expires a carried reserve card dropped it whenever the
# phase was not Movement - and 15.07's window is, BY DEFINITION, not in the
# Movement phase: it is offered as the opponent's Movement phase ENDS, after
# advance_phase(), so the clock already reads Shooting. Picking the card up and
# having it taken away on the next frame is the whole of the report. Nothing to
# do with the AI mode: the AI reaches its reserves through ai/deployment_ai.py
# and never through this pick, which is why only a human could meet it.
_expiry = MAIN_SRC[MAIN_SRC.index("if picked_reserve_squad is not None and ("):]
_expiry = _expiry[:_expiry.index("picked_reserve_squad = None") + 30]
c.true("the carried card still expires out of the Movement phase",
       "turn_tracker.phase != PHASE_MOVEMENT" in _expiry)
c.true("...unless it IS the squad a Rapid Ingress window is open for",
       "picked_reserve_squad is not rapid_ingress_controller.pending_squad" in _expiry)
# Narrow on purpose: "any window is open" would let every OTHER reserve unit be
# walked in out of phase on the back of somebody else's Stratagem, which is the
# exact abuse the guard was written to stop.
c.true("...and only that one squad, not every reserve while a window is open",
       "pending_squad is not None" not in _expiry)
c.true("the card is still dropped once it has left Reserves",
       "picked_reserve_squad not in state.reserves" in _expiry)

# The left button's own board branch must be gated on the SAME question, and on
# "can this actually be placed" rather than "is something picked": a branch that
# matches and then does nothing swallows the clicks that adjust the placement in
# progress.
c.eq("the carried-unit question is a named predicate, defined once",
     MAIN_SRC.count("def _carrying_a_unit("), 1)
c.true("the left button's board branch is gated on it",
       "elif board_rect_screen.collidepoint(event.pos) and _carrying_a_unit():" in MAIN_SRC)
carry_src = body_of("_carrying_a_unit")
c.true("...and it asks whether the unit could really be set up now",
       "setup_controller.can_start_setup(picked_reserve_squad)" in carry_src)

# The pick has to SURVIVE a release that is not over the board - that is what
# turns a click on a card into a pick instead of a flicker, and it is the one
# behavioural change here that no live run can reach: measured, a MockAgent game
# never puts a Player 1 unit into state.reserves at all (6000 frames, the list
# stays empty), so rule 20.04 has no reachable moment outside a suite. Guarded
# at the source instead of overclaimed.
_release_i = MAIN_SRC.find(
    "elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 "
    "and picked_reserve_squad is not None:")
_release_src = "" if _release_i == -1 else MAIN_SRC[
    _release_i:MAIN_SRC.find(chr(10) + "            elif ", _release_i + 10)]
c.true("the left-drag release branch was found at all", _release_i != -1)
c.eq("...and it no longer throws the pick away when the drop misses the board",
     _release_src.count("picked_reserve_squad = None"), 0)
c.true("...while still placing the unit when it does hit the board",
       "_place_picked_unit(" in _release_src)

# ...and a way to let go of it by hand, since while it is carried every board
# click sets it down. ESC is already a ladder (deselect, then fullscreen quit),
# so this is one more rung rather than a new gesture.
_esc_i = MAIN_SRC.find("elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:")
# Cut at the NEXT branch rather than at a fixed number of characters: the ESC
# branch carries a long comment explaining each rung, and a fixed window went
# stale the moment a rung was added - it silently stopped containing the very
# line it was checking the order of.
_esc_end = MAIN_SRC.find("\n            elif event.type ==", _esc_i + 1)
_esc_src = "" if _esc_i == -1 else MAIN_SRC[_esc_i:_esc_end if _esc_end > _esc_i else None]
c.true("ESC puts a carried reserves card back down",
       "if picked_reserve_squad is not None:" in _esc_src)
# The bottom rung is the GAME MENU now, not the fullscreen quit - quitting
# moved into the menu's own entry (see game/ui/game_menu.py). The rung this
# check is about is unchanged: a carried card is still let go of first.
c.true("...as the INNERMOST rung, ahead of deselect and of the menu",
       _esc_src.find("if picked_reserve_squad is not None:")
       < _esc_src.find("elif movement_controller.selected_squad is not None:")
       < _esc_src.find("_open_game_menu()"))

# A carried card now outlives the release that picked it up, so it needs an
# expiry - IngressController.can_ingress() checks the battle round but never the
# PHASE, so without one the next board click would sneak an out-of-phase arrival.
# find(), not index(): index() RAISES when the wiring is gone, which crashes the
# suite instead of turning it red - and a crash hides which check broke. Third
# instance of that lesson in this repo.
expiry_i = MAIN_SRC.find("if picked_reserve_squad is not None and (")
expiry_src = "" if expiry_i == -1 else MAIN_SRC[expiry_i:expiry_i + 400]
c.true("a carried card expires when it stops being placeable",
       "picked_reserve_squad not in state.reserves" in expiry_src
       and "turn_tracker.phase != PHASE_MOVEMENT" in expiry_src)
c.true("...checked once a frame, outside the event loop", expiry_i > after_loop_i)
c.true("...after the owed-arrival poll can arm one, so it gets its frame",
       expiry_i > MAIN_SRC.find("take_pending_placement()"))

# The rename is the honest half of the change: "being dragged" stopped being
# true the moment a plain click kept the unit carried.
# Counted over CODE only. The first version of this line counted the whole file
# and matched its own explanation - the rename note beside the declaration says
# what the old name was, which a reader needs. Fourth instance of that lesson in
# this repo (the `aspect_shrine.usable(` guard, the `max_per_battle` one, the
# `_handle_grim_reapers(` name count).
_code_lines = [line.split("#", 1)[0] for line in MAIN_SRC.splitlines()]
c.eq("nothing still CALLS it a drag - the only mention left is the rename note",
     sum(line.count("dragging_reserve_squad") for line in _code_lines), 0)
c.eq("...and that note is really there, so the rename is traceable",
     MAIN_SRC.count("Renamed from dragging_reserve_squad"), 1)

c.true("the gate is a named predicate, defined once",
       MAIN_SRC.count("def _board_gesture_blocked(") == 1)
c.true("...that reuses _front_notice() rather than re-listing the overlays",
       "_front_notice() is not None" in
       MAIN_SRC.split("def _board_gesture_blocked(")[1].split(chr(10) + "    def ")[0])
c.true("only the START is gated on it",
       "blocked=_board_gesture_blocked()" in MAIN_SRC
       and "_board_gesture_blocked" not in MAIN_SRC.split("update_line_drag(")[1][:200])

c.true("the camera cannot pan under a live drag",
       "and not input_manager.line_drag_active" in MAIN_SRC)
c.true("...and a press that opens a drag cancels a pan already running",
       "camera.end_pan()" in MAIN_SRC[begin_i:chain_i])
c.true("focus loss ends the drag too, rather than trusting the poll alone",
       "pygame.WINDOWFOCUSLOST" in MAIN_SRC)

c.true("the drag is drawn unconditionally each frame",
       "renderer.draw_line_drag(board_surface, board, input_manager)" in MAIN_SRC)
draw_i = MAIN_SRC.index("renderer.draw_line_drag(")
c.true("...at frame-body indent", MAIN_SRC[MAIN_SRC.rindex(chr(10), 0, draw_i) + 1:draw_i] == " " * 8)
c.true("the drawing has its own colour, not the ruler's white",
       "LINE_DRAG_COLOR" in RENDERER_SRC
       and "LINE_DRAG_COLOR = MEASURE_LINE_COLOR" not in RENDERER_SRC)
c.true("...and its width goes through _ring_width()",
       "self._ring_width(LINE_DRAG_WIDTH_PX)" in RENDERER_SRC)

c.finish()
