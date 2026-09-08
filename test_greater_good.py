"""GreaterGoodController.eligible_targets(): the rule, and the two views on it.

WHY THIS FILE EXISTS. eligible_targets() had NO direct test - it was only ever
touched indirectly through can_use() in test_report_20260816.py, which is how a
4732 ms per-frame sweep (the T'au "the shooting phase is very laggy" report)
could live in the panel path unnoticed. This file owns the rule itself, the
lossless rewrite that made it fast, and the cache that keeps it fast.

WHAT CHANGED, AND WHY EACH PART IS LOSSLESS.
  * is_detectable() moved to the LEFT of the sight check and is now computed
    once per defender instead of once per (friendly, defender) pair. Both
    predicates are side-effect-free, so `A and B` may be reordered.
  * eligible_targets() became a generator with two views: the list, and
    any_eligible_target()'s short circuit. One definition, so they cannot drift
    - and section 3 fuzzes them against each other anyway.
  * enemy units are walked NEAREST FIRST. That used to be set-iteration order,
    i.e. not stable between runs.

Sections
  1. The rule itself: visibility, already-Spotted, and the reported Hidden case
  2. Equivalence with the pre-rewrite implementation, over fuzzed boards
  3. The two views agree, on every one of those boards
  4. The cache: ~200 mutations, each against a freshly computed answer
  5. The named divergence from shooting.py's detection range, pinned
"""
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from testkit import (Checks, GameState, TurnTracker, Log, build,
                     PHASES, PHASE_SHOOTING)

from game import config, line_of_sight, maps, status_effects
from game.greater_good import GreaterGoodController
from game.factions.tau_empire import STRIKE_TEAM, CRISIS_SUNFORGE
from game.factions.orks import BATTLEWAGON, BOYZ

c = Checks("For The Greater Good targets")

maps.apply_to_config(maps.get("map2"))
BOARD = GameState()
maps.get("map2").build(BOARD)
OBSTACLES, AREAS = BOARD.obstacles, BOARD.terrain_areas


def line_up(squad, x, y, dx=1.2):
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * dx, y


def scene(with_terrain=True):
    """A T'au observer and two enemy units on the real map2 board."""
    state = GameState()
    strike = build(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
    wagon = build(BATTLEWAGON, "Player 2", name="2 Battlewagon 1")
    boyz = build(BOYZ, "Player 2", name="2 Boyz 1")
    line_up(strike, 10.0, 20.0)
    line_up(wagon, 14.0, 20.0)
    line_up(boyz, 45.0, 20.0)
    for sq in (strike, wagon, boyz):
        for m in sq.models:
            state.add_token(m)
    gg = GreaterGoodController(
        all_tokens=state.tokens,
        obstacles=OBSTACLES if with_terrain else [],
        terrain_areas=AREAS if with_terrain else [],
        turn_tracker=TurnTracker(first_player="Player 1"),
        game_log=Log(),
    )
    return state, gg, strike, wagon, boyz


# ============ 1. the rule itself ============

state, gg, strike, wagon, boyz = scene(with_terrain=False)
targets = gg.eligible_targets(strike)
c.true("an enemy unit in the open, 4 inches away, is a legal mark", wagon in targets)

gg.spotted_by[wagon] = strike
c.true("a unit already Spotted this phase is not offered again",
       wagon not in gg.eligible_targets(strike))
gg.spotted_by.clear()

c.eq("no squad, no targets", gg.eligible_targets(None), [])
c.true("a friendly unit is never a target", strike not in gg.eligible_targets(strike))

# The reported bug this rule's is_detectable() call exists for: "marker + hidden
# intagiert nicht richtig. um etwas zu markieren muss man das ziel auch sehen
# koennen". A Hidden unit beyond its detection range is not markable even when
# raw line of sight exists - so making that check CHEAPER must not make it weaker.
state2, gg2, strike2, wagon2, boyz2 = scene(with_terrain=False)
def with_detectable(value_fn):
    """Run eligible_targets() with is_detectable() replaced - the only way to
    exercise rule 13.09's half without hand-building Dense terrain around a
    unit, and it isolates exactly the term under test."""
    import game.greater_good as gg_mod
    original = gg_mod.status_effects.is_detectable
    gg_mod.status_effects.is_detectable = value_fn
    try:
        return gg2.eligible_targets(strike2)
    finally:
        gg_mod.status_effects.is_detectable = original


c.eq("an undetectable board offers nothing, however clear the sightline",
     with_detectable(lambda *a, **k: False), [])
c.true("...and a detectable one does", len(with_detectable(lambda *a, **k: True)) >= 1)
# The pair is the point: together they prove is_detectable is still CONSULTED
# after moving to the front of the conjunction. Either check alone would pass on
# a board where the sightline decided everything.


# ============ 2. equivalence with the pre-rewrite implementation ============

def reference_eligible_targets(ctrl, squad):
    """The pre-rewrite body, verbatim: set iteration, the expensive check on
    the left of the `and`, is_detectable recomputed per (friendly, defender)."""
    if squad is None:
        return []
    enemy_squads = {
        t.squad for t in ctrl.all_tokens
        if t.squad is not None and t.squad.owner != squad.owner
    }
    last = ctrl.shooting_controller.last_ranged_attack_turn if ctrl.shooting_controller is not None else {}
    result = []
    for enemy in enemy_squads:
        if ctrl.is_spotted(enemy):
            continue
        if any(
            line_of_sight.has_line_of_sight(f, d, ctrl.obstacles, ctrl.all_tokens, ctrl.terrain_areas)
            and status_effects.is_detectable(d, squad, ctrl.terrain_areas, ctrl.turn_tracker, last)
            for f in squad.models
            for d in enemy.models
        ):
            result.append(enemy)
    return result


rng = random.Random(20260908)
mismatches, view_mismatches, empty, non_empty = 0, 0, 0, 0
for _ in range(200):
    state, gg, strike, wagon, boyz = scene()
    for sq in (strike, wagon, boyz):
        line_up(sq, rng.uniform(2, config.BOARD_WIDTH_IN - 8), rng.uniform(2, config.BOARD_HEIGHT_IN - 2))
    if rng.random() < 0.3:
        gg.spotted_by[rng.choice([wagon, boyz])] = strike
    got = set(gg.eligible_targets(strike))
    want = set(reference_eligible_targets(gg, strike))
    if got != want:
        mismatches += 1
    # Section 3, folded into the same loop so it sees the same boards.
    if gg.any_eligible_target(strike) != bool(want):
        view_mismatches += 1
    if want:
        non_empty += 1
    else:
        empty += 1

c.eq("the rewrite changes no answer (200 fuzz boards)", mismatches, 0)
c.eq("any_eligible_target agrees with the list on every one of them", view_mismatches, 0)
# Without this the section would pass on a fuzz where nothing was ever visible.
c.true(f"the fuzz saw both outcomes ({non_empty} with targets / {empty} without)",
       non_empty >= 20 and empty >= 20)


# ============ 4. the cache ============

# A cache test is only worth the lines if its mutations actually CHANGE the
# answer - the first version of this section moved models by +-9 inches on open
# ground, where the Battlewagon stayed markable throughout, so three probes that
# gutted the key sailed through it. So the two positions are MEASURED, not
# guessed: one from which the observer can mark, one from which it cannot.
state, gg, strike, wagon, boyz = scene()
line_up(boyz, 200.0, 200.0)          # parked off the interesting board


def markable_now():
    gg._any_target_cache_key = None
    return gg.any_eligible_target(strike)


SEEN = HIDDEN = None
for _x in range(2, 58, 2):
    for _y in range(2, 42, 2):
        line_up(wagon, float(_x), float(_y))
        if markable_now():
            SEEN = SEEN or (float(_x), float(_y))
        else:
            HIDDEN = HIDDEN or (float(_x), float(_y))
    if SEEN and HIDDEN:
        break
c.true(f"the board really offers both a markable and an unmarkable spot ({SEEN} / {HIDDEN})",
       SEEN is not None and HIDDEN is not None)

rng = random.Random(31337)
stale, flips, previous = 0, 0, None
for i in range(200):
    kind = i % 5
    if kind == 0:                                   # a move that crosses the line
        line_up(wagon, *(SEEN if rng.random() < 0.5 else HIDDEN))
    elif kind == 1:                                 # a model dies this frame
        for m in wagon.models:
            m.current_wounds = 0
    elif kind == 2:                                 # ...and is back next round
        line_up(wagon, *SEEN)
        for m in wagon.models:
            m.current_wounds = m.profile.wounds
    elif kind == 3:                                 # someone marks it
        gg.spotted_by[wagon] = strike
    else:
        gg.spotted_by.clear()

    cached = gg.any_eligible_target(strike)
    gg._any_target_cache_key = None                 # force the honest recomputation
    fresh = gg.any_eligible_target(strike)
    if cached != fresh:
        stale += 1
    if previous is not None and fresh != previous:
        flips += 1
    previous = fresh

c.eq("the cache never answers stale (200 board mutations)", stale, 0)
c.true(f"...and those mutations really moved the answer ({flips} flips)", flips >= 20)

# The two key terms the board mutations above cannot reach, isolated instead of
# approximated: both feed status_effects.is_hidden(), which the fuzz boards have
# no Dense terrain to trigger. Stubbing is_detectable to depend on exactly one
# of them is the only way to ask whether that term is carrying its weight.
import game.greater_good as _gg_mod

state, gg, strike, wagon, boyz = scene()
_real_detectable = _gg_mod.status_effects.is_detectable
try:
    _gg_mod.status_effects.is_detectable = (
        lambda *a, **k: gg.turn_tracker.battle_round % 2 == 0)
    gg.turn_tracker.battle_round = 2
    _even = gg.any_eligible_target(strike)
    gg.turn_tracker.battle_round = 3
    _odd = gg.any_eligible_target(strike)
    c.true("a new battle round is seen by the cache", _even != _odd)

    class _FakeShooting:
        last_ranged_attack_turn = {}

    gg.shooting_controller = _FakeShooting()
    _gg_mod.status_effects.is_detectable = (
        lambda *a, **k: len(gg.shooting_controller.last_ranged_attack_turn) > 0)
    _before = gg.any_eligible_target(strike)
    gg.shooting_controller.last_ranged_attack_turn[wagon] = 1
    _after = gg.any_eligible_target(strike)
    c.true("a unit that has now shot (13.09 ends Hidden) is seen by the cache",
           _before != _after)
finally:
    _gg_mod.status_effects.is_detectable = _real_detectable

# And it really is a cache, not a pass-through: a second ask does no sight work.
# Asked through can_use(), which is what the panel calls every frame - going
# straight to any_eligible_target() would leave can_use() free to bypass it.
state, gg, strike, wagon, boyz = scene()
line_up(wagon, *SEEN)
gg.turn_tracker.phase_index = PHASES.index(PHASE_SHOOTING)


class _NoShots:
    shot_squad_ids = set()
    last_ranged_attack_turn = {}


calls = [0]
_real_los = line_of_sight.has_line_of_sight


def counting(*a, **k):
    calls[0] += 1
    return _real_los(*a, **k)


_gg_mod.line_of_sight.has_line_of_sight = counting
try:
    c.true("the scene really lets can_use() reach its expensive last clause",
           gg.can_use(strike, _NoShots()))
    first = calls[0]
    calls[0] = 0
    for _ in range(30):
        gg.can_use(strike, _NoShots())
    repeat = calls[0]
finally:
    _gg_mod.line_of_sight.has_line_of_sight = _real_los

c.true(f"the first can_use() really does the work ({first} sight checks)", first > 0)
c.eq("30 more can_use() calls on an unchanged board do none", repeat, 0)


# ============ 5. the named divergence, pinned ============

# game/detection_range.py records that eligible_targets() calls is_detectable()
# WITHOUT prey_marks/unmasking, so it measures a different detection range than
# shooting.py does. The rewrite left that alone deliberately; this pins it so
# closing it stays a decision rather than a side effect.
import ast
import inspect
import textwrap

_src = textwrap.dedent(inspect.getsource(GreaterGoodController._eligible_targets))
# By AST, not by substring: the comment at the call site NAMES both keywords in
# order to explain why they are absent, so a substring guard would match its own
# explanation and pass no matter what the code did. That exact shape has cost
# this repo four separate findings.
_kwargs = set()
_found = 0
for _node in ast.walk(ast.parse(_src)):
    if isinstance(_node, ast.Call) and getattr(_node.func, "attr", None) == "is_detectable":
        _found += 1
        _kwargs |= {kw.arg for kw in _node.keywords}
c.eq("_eligible_targets calls is_detectable exactly once", _found, 1)
c.eq("...and passes it no prey_marks/unmasking (the divergence stays open)",
     sorted(_kwargs & {"prey_marks", "unmasking"}), [])
c.true("...and the divergence is named at the call site",
       "detection_range" in _src)

c.finish()
