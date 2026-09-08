"""What a Shooting-phase FRAME costs with T'au selected, through the real loop.

THE REPORT THIS ANSWERS: "wenn man tau spielt ist die shooting phase sehr laggy.
ich denke es liegt an for the greater good. da diese faehigkeit eine unendliche
reichweite hat, muessen alle gegnerischen einheiten auf LOS geprueft werden."

The guess was right and low. Two per-frame sweeps were behind it:

  * game/ui/action_panel.py asks GreaterGoodController.can_use() every frame a
    T'au unit is selected in its own Shooting phase, and can_use() ended in
    eligible_targets() - a full line-of-sight sweep of every one of the squad's
    models against every model of every enemy unit, with no range filter,
    because the printed rule has no range. Measured cold: 4732 ms.
  * The same panel asked arrokon_controller.can_use() and then
    best_available_tier(), and the first ENDS in the second - the same
    has_valid_target() sweep twice per frame, up to 660 ms each.

WHY THIS FILE, AND WHY IT DRIVES main(). Until now this repo had no script that
measured Shooting-phase or line-of-sight cost at all: every figure in CLAUDE.md
(27+ seconds for valid_target_models, ~0.8s for eligible_targets, 1.17 ms per
sight check) was measured ad hoc and then only survived as prose. And the number
a player actually feels is the duration of an ActionPanel.draw() call, which is
not the same thing as the duration of eligible_targets() - the cache only shows
up ACROSS frames, so a self-built board could not show it at all. Hence
measure_render_resolution.py's shape: runpy over selfplay.py's real main() loop.

WHAT IS STAGED, each because the harness will not produce it, and each named
rather than quietly faked (the same three verify_tau_stratagem_buttons.py pays
for, for the same measured reasons):
  * T'au as PLAYER 1. config ships PLAYER2_ARMY = "necrons", and a question
    about the HUMAN's panel would otherwise measure the AI's army and report a
    truthful-looking zero.
  * A SELECTED UNIT, every frame, through the REAL MovementController.select()
    - _draw_movement_ui() draws no unit UI without one.
  * THE PHASE. A T'au roster reaches no phase change in any budget worth
    waiting for. The unit rotation uses a period COPRIME with the five phases;
    sharing one modulus pairs unit i with phase i%5 for ever.

--neutralize restores the WHOLE pre-fix world, not one line of it (error class
16): the LoS memo, the greater_good rewrite and cache, and the panel's double
Arro'kon call. So the before/after pair comes out of one script.

Usage:  python measure_shooting_frame_cost.py [map2] [frames]
        python measure_shooting_frame_cost.py map2 3000 --neutralize
"""

import runpy
import statistics
import sys
import time

import pygame

from game import arrokon_protocol, config, detachments, greater_good, line_of_sight
from game.renderer import Renderer
from game.turn import PHASES, PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT, TurnTracker
from game.ui.action_panel import ActionPanel

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
MIN_FRAMES = 600

state = {
    "frames": 0, "selected": 0, "tracker": None, "rotate": False,
    "panel_ms": [], "panel_shooting_ms": [], "los_calls": 0, "los_per_frame": [],
    "gg_cold": [], "gg_calls": 0, "gg_misses": 0,
    "arrokon_sweeps": 0, "arrokon_calls": 0, "arrokon_ms": [],
    "units": set(), "main_locals": None,
}


# ------------------------------------------------------------- neutralisation

if NEUTRALIZE:
    # 1. line_of_sight: no memo, three any() checks walked from the front.
    def _pre_fix_has_line_of_sight(a, b, obstacles, all_tokens=(), terrain_areas=(),
                                   sample_points=line_of_sight.SAMPLE_POINTS):
        pa = line_of_sight._circle_points(a.x_in, a.y_in, a.radius_in, sample_points)
        pb_list = line_of_sight._circle_points(b.x_in, b.y_in, b.radius_in, sample_points)
        box = line_of_sight._bounding_box(a, b)
        obs = line_of_sight._relevant_obstacles(obstacles, box)
        blockers = line_of_sight._relevant_models(
            line_of_sight._blocking_models(a, b, all_tokens), box)
        areas = line_of_sight._obscuring_areas_between(terrain_areas, a, b)
        for p1 in pa:
            for p2 in pb_list:
                if any(line_of_sight._blocked_by_obstacle(p1, p2, o) for o in obs):
                    continue
                if any(line_of_sight._blocked_by_model(p1, p2, m) for m in blockers):
                    continue
                if any(area.crosses_segment(p1, p2) for area in areas):
                    continue
                return True
        return False

    line_of_sight.has_line_of_sight = _pre_fix_has_line_of_sight
    greater_good.line_of_sight.has_line_of_sight = _pre_fix_has_line_of_sight

    # 2. greater_good: set order, expensive test first, no short circuit, no cache.
    def _pre_fix_eligible_targets(self, squad):
        if squad is None:
            return []
        enemies = {t.squad for t in self.all_tokens
                   if t.squad is not None and t.squad.owner != squad.owner}
        last = (self.shooting_controller.last_ranged_attack_turn
                if self.shooting_controller is not None else {})
        out = []
        for enemy in enemies:
            if self.is_spotted(enemy):
                continue
            if any(
                greater_good.line_of_sight.has_line_of_sight(
                    f, d, self.obstacles, self.all_tokens, self.terrain_areas)
                and greater_good.status_effects.is_detectable(
                    d, squad, self.terrain_areas, self.turn_tracker, last)
                for f in squad.models for d in enemy.models
            ):
                out.append(enemy)
        return out

    greater_good.GreaterGoodController.eligible_targets = _pre_fix_eligible_targets
    greater_good.GreaterGoodController.any_eligible_target = (
        lambda self, squad: bool(self.eligible_targets(squad)))

    # 3. arrokon: no cache, and the panel asks twice (restored at the panel below).
    def _pre_fix_best_tier(self, squad):
        targets = self.qualifying_target_squads(squad)
        return max((arrokon_protocol.sustained_hits_for_target(t) for t in targets), default=0)

    arrokon_protocol.ArrokonProtocolController.best_available_tier = _pre_fix_best_tier


# ------------------------------------------------------------------ instruments

_real_los = line_of_sight.has_line_of_sight


def counting_los(*a, **k):
    state["los_calls"] += 1
    return _real_los(*a, **k)


line_of_sight.has_line_of_sight = counting_los
greater_good.line_of_sight.has_line_of_sight = counting_los

_real_gg_can_use = greater_good.GreaterGoodController.can_use


def gg_can_use(self, squad, shooting_controller):
    before = state["los_calls"]
    start = time.perf_counter()
    out = _real_gg_can_use(self, squad, shooting_controller)
    elapsed = (time.perf_counter() - start) * 1000.0
    state["gg_calls"] += 1
    if state["los_calls"] > before:          # a real sweep, i.e. a cache miss
        state["gg_misses"] += 1
        state["gg_cold"].append(elapsed)
    return out


greater_good.GreaterGoodController.can_use = gg_can_use

_real_qualifying = arrokon_protocol.ArrokonProtocolController._qualifying


def counting_qualifying(self, squad, by_tier):
    state["arrokon_sweeps"] += 1
    return _real_qualifying(self, squad, by_tier)


arrokon_protocol.ArrokonProtocolController._qualifying = counting_qualifying

_real_tier = arrokon_protocol.ArrokonProtocolController.best_available_tier


def timed_tier(self, squad):
    start = time.perf_counter()
    out = _real_tier(self, squad)
    state["arrokon_ms"].append((time.perf_counter() - start) * 1000.0)
    state["arrokon_calls"] += 1
    return out


arrokon_protocol.ArrokonProtocolController.best_available_tier = timed_tier

_real_panel_draw = ActionPanel.draw


def panel_draw(self, *a, **k):
    before_los = state["los_calls"]
    start = time.perf_counter()
    out = _real_panel_draw(self, *a, **k)
    elapsed = (time.perf_counter() - start) * 1000.0
    state["panel_ms"].append(elapsed)
    state["los_per_frame"].append(state["los_calls"] - before_los)
    tracker = state.get("tracker")
    if tracker is not None and tracker.phase == PHASE_SHOOTING:
        state["panel_shooting_ms"].append(elapsed)
    return out


ActionPanel.draw = panel_draw

if NEUTRALIZE:
    # The reported panel shape: can_use() AND best_available_tier(), same frame.
    # Done by wrapping the panel rather than editing it, so the file on disk is
    # untouched and the two runs differ only in this process.
    _panel_after_fix = ActionPanel.draw

    def double_asking_panel(self, *a, **k):
        controller = k.get("arrokon_controller")
        squad = None
        move = k.get("movement_controller")
        if move is not None:
            squad = getattr(move, "selected_squad", None)
        if controller is not None and squad is not None:
            controller.can_use(squad)            # the first sweep the panel used to do
        return _panel_after_fix(self, *a, **k)

    ActionPanel.draw = double_asking_panel


# ----------------------------------------------------------------- staging

SETTINGS = ("RETALIATION_CADRE_PLAYERS", "KAUYON_PLAYERS")
_real_apply = detachments.apply_to_config


def apply_to_config(*a, **k):
    out = _real_apply(*a, **k)
    for name in SETTINGS:
        setattr(config, name, (HUMAN,))
    return out


detachments.apply_to_config = apply_to_config

_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *a, **k):
    _real_tracker_init(self, *a, **k)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

_ORDER = (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT)
_real_flip = pygame.display.flip


def _main_locals():
    """main()'s own frame, walked up from a hook that runs inside it. Same
    trick as measure_render_resolution.py: every controller in this game is a
    local of that 4000-line function, so there is no other way to ask the LIVE
    objects anything."""
    frame = sys._getframe(1)
    while frame is not None:
        if "turn_tracker" in frame.f_locals and "greater_good_controller" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


def flip(*a, **k):
    if state.get("main_locals") is None:
        found = _main_locals()
        if found:
            state["main_locals"] = found
    tracker = state.get("tracker")
    if tracker is not None and getattr(tracker, "started", True):
        phase = _ORDER[(state["frames"] // 40) % len(_ORDER)]
        tracker.phase_index = PHASES.index(phase)
        tracker.turn_owner = HUMAN
        tracker.set_active(HUMAN)
        tracker.battle_round = 3
    if state["frames"] % 17 == 0:            # coprime with the five phases
        state["rotate"] = True
    state["frames"] += 1
    return _real_flip(*a, **k)


pygame.display.flip = flip

_real_move_range = Renderer.draw_move_range


def draw_move_range(self, surface, board, movement_controller):
    squads = []
    for token in movement_controller.all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is not None and squad.owner == HUMAN and squad not in squads:
            squads.append(squad)
    if squads and (state.pop("rotate", False) or movement_controller.selected_squad is None):
        movement_controller.select(squads[(state["frames"] // 17) % len(squads)].models[0])
    if movement_controller.selected_squad is not None:
        state["selected"] += 1
        state["units"].add(movement_controller.selected_squad.name)
    return _real_move_range(self, surface, board, movement_controller)


Renderer.draw_move_range = draw_move_range

_argv = sys.argv[1:] or ["map2", "1600"]
sys.argv = ["selfplay.py"] + _argv
config.PLAYER1_ARMY = "tau"
config.ARMY_SELECT = False

runpy.run_module("selfplay", run_name="__main__")


# ------------------------------------------------------------------- report

def stats(values):
    if not values:
        return "        -"
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    return "%8.2f ms  (median %7.2f, p95 %8.2f, max %8.2f)" % (
        statistics.mean(values), statistics.median(values), p95, max(values))


print()
print("--- Shooting-phase frame cost" + (" (NEUTRALIZED = pre-fix world)" if NEUTRALIZE else "") + " ---")
print("  map / frames              : %s / %d" % (_argv[0], state["frames"]))
print("  frames with a selection   : %d   (%d distinct units)" % (state["selected"], len(state["units"])))
print()
print("  ActionPanel.draw, all     : %s" % stats(state["panel_ms"]))
print("  ActionPanel.draw, SHOOTING: %s" % stats(state["panel_shooting_ms"]))
# Per PANEL frame, i.e. inside ActionPanel.draw() only. The process total is
# far larger and mostly the AI's own targeting - counting that here would read
# as panel cost and be wrong by an order of magnitude.
print("  sight checks per panel frame: mean %.1f, max %d   (process total %d, mostly the AI)" % (
    (statistics.mean(state["los_per_frame"]) if state["los_per_frame"] else 0.0),
    (max(state["los_per_frame"]) if state["los_per_frame"] else 0),
    state["los_calls"]))
print()
# NOT a cache hit rate. can_use() has seven cheap gates in front of the sweep
# (phase, owner, battle-shocked, already an Observer, already shot, has the
# ability at all, can shoot at all), and most calls stop at one of them - so
# "reached the sweep" is the honest name, and the cached/uncached split is
# measured separately below on a unit that really does reach it.
print("  greater_good.can_use      : %d calls, %d reached the expensive clause" % (
    state["gg_calls"], state["gg_misses"]))
print("     cost when it does      : %s" % stats(state["gg_cold"]))
if state["gg_misses"] < 2:
    print("     (too few to draw a line from - which is why the STAGED figure")
    print("      below exists; the rotation lands on that clause about once)")
print()
if state["arrokon_calls"]:
    print("  arrokon best_available_tier: %d calls, %d underlying sweeps (%.2f per call)" % (
        state["arrokon_calls"], state["arrokon_sweeps"],
        state["arrokon_sweeps"] / state["arrokon_calls"]))
    print("     cost per call          : %s" % stats(state["arrokon_ms"]))
else:
    # Named, not silently zero: its TARGET line wants a BATTLESUIT unit that has
    # not shot, in its own Shooting phase, with a 6+ model enemy it could legally
    # shoot - the rotation does not reliably line all four up. The one-sweep
    # claim is pinned by test_arrokon_protocol.py section 8's counter instead.
    print("  arrokon best_available_tier: never reached its own gates in this run")
    print("     (its TARGET needs a BATTLESUIT that has not shot, in its own")
    print("      Shooting phase, with a 6+ model enemy in range - see")
    print("      test_arrokon_protocol.py section 8 for the one-sweep counter)")


# ------------------------------------------------- the reported unit, STAGED
#
# The passive numbers above are honest but thin: over 1600 frames the rotation
# lands a For-The-Greater-Good unit on the expensive clause about once, so the
# figure that answers the report rests on a single sample. This asks the
# question directly, on the unit the report is about, the way
# verify_sudden_storm_wiring.py stages its Advance rather than waiting 14 000
# frames for one. Everything measured is the REAL controller against the REAL
# board main() built; only WHICH question gets asked is arranged.
locals_ = state.get("main_locals") or {}
gg_ctrl = locals_.get("greater_good_controller")
tokens = locals_.get("state").tokens if locals_.get("state") is not None else None
if gg_ctrl is not None and tokens:
    from game.squad import squad_has_greater_good

    squads = []
    for token in tokens:
        squad = getattr(token, "squad", None)
        if (squad is not None and squad.owner == HUMAN and squad not in squads
                and squad_has_greater_good(squad)):
            squads.append(squad)
    if squads:
        biggest = max(squads, key=lambda s: len(s.models))
        enemies = {getattr(t, "squad", None) for t in tokens}
        enemies = {e for e in enemies if e is not None and e.owner != HUMAN}
        gg_ctrl._any_target_cache_key = None
        before = state["los_calls"]
        t0 = time.perf_counter()
        gg_ctrl.any_eligible_target(biggest)
        cold = (time.perf_counter() - t0) * 1000.0
        sweep_calls = state["los_calls"] - before

        t0 = time.perf_counter()
        for _ in range(60):
            gg_ctrl.any_eligible_target(biggest)
        warm = (time.perf_counter() - t0) * 1000.0 / 60.0

        print()
        print("  STAGED, on the reported unit:")
        print("     %s (%d models) vs %d enemy units"
              % (biggest.name, len(biggest.models), len(enemies)))
        print("     first ask (cold)       : %8.1f ms   (%d sight checks)" % (cold, sweep_calls))
        print("     every frame after      : %8.3f ms   <- what the player feels"
              % warm)

if state["selected"] == 0:
    print("  INCONCLUSIVE: no unit was ever selected, so no unit UI was drawn")
    raise SystemExit(2)
if state["frames"] < MIN_FRAMES:
    print("  INCONCLUSIVE: fewer than %d frames" % MIN_FRAMES)
    raise SystemExit(2)
if not state["panel_shooting_ms"]:
    print("  INCONCLUSIVE: the Shooting phase was never reached with the panel drawn")
    raise SystemExit(2)
raise SystemExit(0)
