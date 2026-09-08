"""game/line_of_sight.py: the "last blocker first" reordering, proved lossless.

WHY THIS FILE EXISTS. Until now there was NO suite for game/line_of_sight.py at
all - it was only ever touched sideways (test_hidden.py, test_rotated_terrain.py,
test_map3_crucible.py), and CLAUDE.md's claim that the bounding-box prefilter was
"per 400 Fuzz-Vergleichen belegt" had no file behind it. That is how a 4.7-second
per-frame sweep in the Shooting phase (the T'au "For the Greater Good" report)
could sit in the hottest path in the engine unnoticed. This makes the claim true
for the first time, and covers the new _first_blocker() memo with it.

WHAT IS UNDER TEST. _first_blocker() tests the blocker that stopped the PREVIOUS
point pair before walking the candidate lists again. That is a pure reordering of
an OR over side-effect-free predicates, so it cannot change an answer - and "it
cannot" is exactly the kind of claim this repo makes people prove. The reference
implementation below is the pre-memo code, verbatim: three any() checks in list
order, with the three prefilters left IN (they are not what is on trial here).

THE FUZZ HAS TO SEE BOTH OUTCOMES. A sweep that returns True 400 times has
measured nothing - the same finding that three of 26 probes were in the T'au
audit. Section 2 asserts a real share of each outcome per map, so a board setup
that accidentally stopped producing blocked sightlines would fail loudly instead
of passing vacuously.

Sections
  1. _first_blocker: what it returns, and the memo hit/miss on its own
  2. Fuzz equivalence vs the pre-memo reference, on all three shipped maps
  3. model_fully_visible: the same equivalence for the all() half (Benefit of Cover)
  4. Determinism: no state survives a call, and list order does not matter
"""
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from testkit import Checks, GameState

from game import config, line_of_sight as L, maps

c = Checks("line of sight")


class Squad:
    """Just enough for _blocking_models()/_owner_of(): a name and an owner."""

    def __init__(self, owner, name):
        self.owner = owner
        self.name = name


class Model:
    def __init__(self, x, y, radius, squad=None):
        self.x_in, self.y_in, self.radius_in, self.squad = x, y, radius, squad

    def is_dead(self):
        return False


# ---------------------------------------------------------------- reference

def _reference_has_line_of_sight(a, b, obstacles, all_tokens=(), terrain_areas=(),
                                 sample_points=L.SAMPLE_POINTS):
    """The pre-memo answer, verbatim: for every point pair, walk each candidate
    list from the front. The three prefilters stay - they are older, separately
    argued, and not what this file is testing."""
    points_a = L._circle_points(a.x_in, a.y_in, a.radius_in, sample_points)
    points_b = L._circle_points(b.x_in, b.y_in, b.radius_in, sample_points)
    box = L._bounding_box(a, b)
    obstacles = L._relevant_obstacles(obstacles, box)
    blockers = L._relevant_models(L._blocking_models(a, b, all_tokens), box)
    obscuring_areas = L._obscuring_areas_between(terrain_areas, a, b)
    for pa in points_a:
        for pb in points_b:
            if any(L._blocked_by_obstacle(pa, pb, o) for o in obstacles):
                continue
            if any(L._blocked_by_model(pa, pb, m) for m in blockers):
                continue
            if any(area.crosses_segment(pa, pb) for area in obscuring_areas):
                continue
            return True
    return False


def _reference_model_fully_visible(observer, target, obstacles, all_tokens=(), terrain_areas=()):
    points_a = L._circle_points(observer.x_in, observer.y_in, observer.radius_in)
    facing = L._facing_points(observer, target)
    if not facing:
        return False
    box = L._bounding_box(observer, target)
    obstacles = L._relevant_obstacles(obstacles, box)
    blockers = L._relevant_models(L._blocking_models(observer, target, all_tokens), box)
    areas = L._obscuring_areas_between(terrain_areas, observer, target)

    def reachable(point):
        for origin in points_a:
            if any(L._blocked_by_obstacle(origin, point, o) for o in obstacles):
                continue
            if any(L._blocked_by_model(origin, point, m) for m in blockers):
                continue
            if any(area.crosses_segment(origin, point) for area in areas):
                continue
            return True
        return False

    return all(reachable(pb) for pb in facing)


# -------------------------------------------------------------------- boards

def board(map_key):
    battle_map = maps.get(map_key)
    maps.apply_to_config(battle_map)
    state = GameState()
    battle_map.build(state)
    return state


BOARDS = {key: board(key) for key in ("map1", "map2", "map3")}
# Re-apply one map so config is left in a known state for anything that reads it
# after this module (the suites run in one process under run_tests.py).
maps.apply_to_config(maps.get("map2"))

RADII = (0.49, 0.63, 1.05, 2.1)


def fuzz_scene(rng, state):
    """Two tokens plus 0-6 other models on a REAL board. The extra models get
    real Squad stand-ins with mixed owners, so _blocking_models()' per-pair
    exclusions (own unit, own army by house rule) are actually exercised - a
    fuzz with squad=None everywhere would never test them."""
    width, height = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
    mine, theirs = Squad("Player 1", "A"), Squad("Player 2", "B")
    a = Model(rng.uniform(1, width - 1), rng.uniform(1, height - 1), rng.choice(RADII), mine)
    b = Model(rng.uniform(1, width - 1), rng.uniform(1, height - 1), rng.choice(RADII), theirs)
    extras = [
        Model(rng.uniform(1, width - 1), rng.uniform(1, height - 1), rng.choice(RADII),
              rng.choice([mine, theirs, Squad("Player 2", "C"), None]))
        for _ in range(rng.randint(0, 6))
    ]
    return a, b, [a, b] + extras


# ============ 1. _first_blocker on its own ============

_state = BOARDS["map2"]
maps.apply_to_config(maps.get("map2"))
# Deliberately NOT obstacles[0]: rule 13.03/13.04 means Exposed/Light pieces do
# not block sight at all (14 of map2's 29 do), and picking one of those would
# make every check in this section pass for the wrong reason.
_wall = next(o for o in _state.obstacles if o.blocks_line_of_sight)
_p1 = (_wall.min_x - 2.0, (_wall.min_y + _wall.max_y) / 2.0)
_p2 = (_wall.max_x + 2.0, (_wall.min_y + _wall.max_y) / 2.0)

_hit = L._first_blocker(_p1, _p2, [_wall], [], [])
c.true("a segment through an obstacle reports that obstacle",
       _hit is not None and _hit[0] == L.OBSTACLE and _hit[1] is _wall)
c.eq("a clear segment reports nothing",
     L._first_blocker((0.5, 0.5), (0.6, 0.5), [_wall], [], []), None)

# The memo is tested first, and it is the same answer either way.
c.eq("a memo that still blocks is returned without walking the lists",
     L._first_blocker(_p1, _p2, [], [], [], memo=(L.OBSTACLE, _wall)), (L.OBSTACLE, _wall))
c.eq("a memo that no longer blocks falls through to the lists",
     L._first_blocker((0.5, 0.5), (0.6, 0.5), [], [], [], memo=(L.OBSTACLE, _wall)), None)

_blocker_model = Model((_p1[0] + _p2[0]) / 2.0, _p1[1], 1.0)
c.true("a model in the way is reported as a MODEL",
       L._first_blocker(_p1, _p2, [], [_blocker_model], [])[0] == L.MODEL)
c.true("obstacles are still checked before models (printed order is unchanged)",
       L._first_blocker(_p1, _p2, [_wall], [_blocker_model], [])[0] == L.OBSTACLE)


# ============ 2. fuzz equivalence, has_line_of_sight ============

for map_key in ("map1", "map2", "map3"):
    state = BOARDS[map_key]
    maps.apply_to_config(maps.get(map_key))
    rng = random.Random(20260908)
    mismatches, blocked, clear = 0, 0, 0
    for _ in range(400):
        a, b, tokens = fuzz_scene(rng, state)
        sample_points = rng.choice([6, L.SAMPLE_POINTS])  # 6 is main.py's highlight value
        got = L.has_line_of_sight(a, b, state.obstacles, tokens, state.terrain_areas, sample_points)
        want = _reference_has_line_of_sight(a, b, state.obstacles, tokens,
                                            state.terrain_areas, sample_points)
        if got != want:
            mismatches += 1
        if want:
            clear += 1
        else:
            blocked += 1
    c.eq(f"{map_key}: the memo changes no answer (400 fuzz boards)", mismatches, 0)
    # Without this the section would pass on a fuzz that only ever produced one
    # outcome - it would have measured nothing at all.
    c.true(f"{map_key}: the fuzz really saw both outcomes ({blocked} blocked / {clear} clear)",
           blocked >= 40 and clear >= 40)

_rotated = [o for o in BOARDS["map3"].obstacles if abs(getattr(o, "angle_deg", 0.0)) > 1e-9]
c.true("map3 really contributes rotated obstacles to the fuzz above", len(_rotated) >= 8)


# ============ 3. fuzz equivalence, model_fully_visible (Benefit of Cover) ============

# Its all() has no early exit on success, so "one wall hides every facing point"
# is its expensive case AND the one the memo is worth most on - a separate fuzz,
# because two entry points are two places to get the wiring wrong.
for map_key in ("map2", "map3"):
    state = BOARDS[map_key]
    maps.apply_to_config(maps.get(map_key))
    rng = random.Random(4242)
    mismatches, full, partial = 0, 0, 0
    for _ in range(200):
        a, b, tokens = fuzz_scene(rng, state)
        got = L.model_fully_visible(a, b, state.obstacles, tokens, state.terrain_areas)
        want = _reference_model_fully_visible(a, b, state.obstacles, tokens, state.terrain_areas)
        if got != want:
            mismatches += 1
        if want:
            full += 1
        else:
            partial += 1
    c.eq(f"{map_key}: model_fully_visible unchanged (200 fuzz boards)", mismatches, 0)
    c.true(f"{map_key}: that fuzz saw both outcomes ({full} full / {partial} not)",
           full >= 20 and partial >= 20)


# ============ 4. determinism ============

maps.apply_to_config(maps.get("map2"))
state = BOARDS["map2"]
rng = random.Random(7)
_repeat_mismatches, _order_mismatches = 0, 0
for _ in range(60):
    a, b, tokens = fuzz_scene(rng, state)
    first = L.has_line_of_sight(a, b, state.obstacles, tokens, state.terrain_areas)
    if L.has_line_of_sight(a, b, state.obstacles, tokens, state.terrain_areas) != first:
        _repeat_mismatches += 1
    shuffled = list(state.obstacles)
    rng.shuffle(shuffled)
    if L.has_line_of_sight(a, b, shuffled, tokens, state.terrain_areas) != first:
        _order_mismatches += 1
c.eq("asking twice gives the same answer (no memo survives a call)", _repeat_mismatches, 0)
c.eq("shuffling the obstacle list changes no answer", _order_mismatches, 0)

# The pair-dependent exclusions the memo must never cross (see _first_blocker's
# docstring). Both are properties of the CALL, so they have to keep holding.
_mine = Squad("Player 1", "mine")
_obs = Model(10.0, 10.0, 0.63, _mine)
_tgt = Model(14.0, 10.0, 0.63, Squad("Player 2", "theirs"))
_friend = Model(12.0, 10.0, 1.2, _mine)
c.true("a friendly model still never blocks (house rule)",
       L.has_line_of_sight(_obs, _tgt, [], [_obs, _tgt, _friend], []))
_enemy_screen = Model(12.0, 10.0, 1.2, Squad("Player 2", "screen"))
c.true("an enemy model still does block",
       not L.has_line_of_sight(_obs, _tgt, [], [_obs, _tgt, _enemy_screen], []))

c.finish()
