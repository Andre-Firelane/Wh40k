"""Regression tests for the three causes behind the reported turn
(logs/game_20260804_224335.log). Each case uses the numbers from that log."""
import sys

from game import maps, config, pathfinding
from game.game_state import GameState
from game.factions import build_squad
from game.factions.orks import DEFF_DREAD, BOYZ, DEFFKOPTAS, TANKBUSTAS
from game.movement import MovementController
from game.turn import TurnTracker
from ai import agent_driver

m = maps.get('map2'); maps.apply_to_config(m)
checks, failed = 0, []
def ok(label, cond):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label)

def fresh_state():
    st = GameState(); m.build(st); return st

# ---------------------------------------------------------------- 1. routing
print("\n1) find_route no longer depends on grid phase (Deff Dread at the ruin)")
st = fresh_state()
dread = build_squad(DEFF_DREAD, "Player 2", name="2 Deff Dread 1")
d = dread.models[0]; d.x_in, d.y_in = 26.70, 15.94
blocking = pathfinding.blocking_obstacles_for(d, st.obstacles)
routes = {b: pathfinding.find_route((d.x_in, d.y_in), (30.0, 22.0), d.radius_in, b,
                                    blocking, [], config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
          for b in (6, 8, 10, 12, 14, 20)}
ok("a route is found at every budget (was None for 6-12)", all(routes.values()))
ok("the real 8\" move gets a route", routes[8] is not None)
# The first leg must be legal from where the model truly stands.
first = routes[8][0]
ok("first leg is clear from the true position",
   pathfinding._direct_line_clear((d.x_in, d.y_in), first, blocking, [], d.radius_in))

print("\n   no route ever crosses terrain the mover cannot cross")
# The property the start-cell substitution has to preserve: a route may now be
# returned where none was before, but every leg of it must still be walkable
# for this mover - including the new first leg out of the blocked start cell.
probe = build_squad(DEFF_DREAD, "Player 2", name="probe")
p = probe.models[0]
bl = pathfinding.blocking_obstacles_for(p, st.obstacles)
bad, tested, found = [], 0, 0
for sx in range(2, 59, 3):
    for sy in range(2, 43, 3):
        p.x_in, p.y_in = float(sx), float(sy)
        for goal in ((30.0, 22.0), (5.0, 40.0), (55.0, 8.0)):
            tested += 1
            route = pathfinding.find_route((p.x_in, p.y_in), goal, p.radius_in, 10.0, bl, [],
                                           config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
            if not route:
                continue
            found += 1
            prev = (p.x_in, p.y_in)
            for point in route:
                if not pathfinding._direct_line_clear(prev, point, bl, [], p.radius_in):
                    bad.append(((sx, sy), goal, prev, point))
                prev = point
print(f"      {found} routes returned over {tested} queries, {len(bad)} with an illegal leg")
# Measured: all 10 of those start from a cell the grid already considered
# unblocked, so the old code produced the identical path - a pre-existing
# string-pull weakness (harmless downstream: try_commit_segment() clamps such a
# leg rather than honouring it), not something the substitution introduced.
# What must hold is that substituting a start cell adds none of its own.
from_substituted = []
for (sx, sy), goal, prev, point in bad:
    grid = pathfinding._Grid((float(sx), float(sy)), goal, p.radius_in, 10.0, bl, [],
                             config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN, 1.0)
    if grid.is_blocked(grid.start_cell):
        from_substituted.append(((sx, sy), goal))
print(f"      of those, {len(from_substituted)} come from a substituted start cell")
ok("the start-cell substitution introduces no illegal leg", not from_substituted)

# --------------------------------------------------------------- 2. movement
print("\n2) the Deff Dread actually advances (reported: stuck at the wall)")
st = fresh_state()
dread = build_squad(DEFF_DREAD, "Player 2", name="2 Deff Dread 1")
d = dread.models[0]; d.x_in, d.y_in = 26.70, 15.94
st.tokens.extend(dread.models)
tracker = TurnTracker(first_player="Player 2"); tracker.phase_index = 1
mc = MovementController(obstacles=st.obstacles, turn_tracker=tracker, all_tokens=st.tokens,
                        player_name="Player 2", board_width_in=config.BOARD_WIDTH_IN,
                        board_height_in=config.BOARD_HEIGHT_IN)
mc.select(d)
moved = agent_driver._advance_toward(mc, dread, (30.0, 22.0))
travelled = ((d.x_in - 26.70) ** 2 + (d.y_in - 15.94) ** 2) ** 0.5
print(f"      final ({d.x_in:.2f},{d.y_in:.2f}), travelled {travelled:.2f}\"")
ok("it moves instead of standing still", moved and travelled > 1.0)
ok("it gets through the ruin doorway (y past the 17.7\" wall)", d.y_in > 17.7)

print("\n   a genuinely boxed-in unit reports FAILURE instead of a 0\" 'move'")


def boxed_in_dread():
    """The reported Deff Dread with its own Boyz parked across its only lane,
    exactly where the log left them."""
    st = fresh_state()
    dread = build_squad(DEFF_DREAD, "Player 2", name="2 Deff Dread 1")
    d = dread.models[0]; d.x_in, d.y_in = 26.70, 15.94
    boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    for i, t in enumerate(boyz.models):
        t.x_in, t.y_in = [(28.97,15.69),(30.47,15.69),(31.97,15.69),(33.47,15.69),(34.97,15.69),
                          (28.97,13.69),(30.47,13.69),(31.97,13.69),(33.47,13.69),(34.97,13.69)][i]
    st.tokens.extend(dread.models + boyz.models)
    tracker = TurnTracker(first_player="Player 2"); tracker.phase_index = 1
    mc = MovementController(obstacles=st.obstacles, turn_tracker=tracker, all_tokens=st.tokens,
                            player_name="Player 2", board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    mc.select(d)
    res = agent_driver._advance_toward(mc, dread, (30.0, 22.0))
    return d, res


# The subject here is _advance_toward()'s false-success guard: a squad that
# cannot move must report failure rather than "succeed" at 0.00". That needs a
# squad that genuinely cannot move, and under config.VEHICLES_CROSS_WALLS this
# one CAN - the ruin wall that used to seal it in is now crossable. So the
# rule is pinned off for this one assertion, and the case it used to describe
# is asserted separately just below, where it is now a fix rather than a trap.
_walls = config.VEHICLES_CROSS_WALLS
config.VEHICLES_CROSS_WALLS = False
try:
    d, res = boxed_in_dread()
    stayed = abs(d.x_in - 26.70) < 0.01 and abs(d.y_in - 15.94) < 0.01
    ok("returns False when it truly cannot move (was True at 0.00\")", stayed and not res)
finally:
    config.VEHICLES_CROSS_WALLS = _walls

print("\n   ...and with the wall-crossing house rule on, that same Dread gets out")
d, res = boxed_in_dread()
travelled = ((d.x_in - 26.70) ** 2 + (d.y_in - 15.94) ** 2) ** 0.5
print(f"      final ({d.x_in:.2f},{d.y_in:.2f}), travelled {travelled:.2f}\"")
ok("config.VEHICLES_CROSS_WALLS frees the boxed-in Deff Dread", res and travelled > 1.0)

# --------------------------------------------------------------- 3. reserves
print("\n3) reserve orders are no longer clamped from phantom coordinates")
st = fresh_state()
kop = build_squad(DEFFKOPTAS, "Player 2", name="2 Deffkoptas 1")
tank = build_squad(TANKBUSTAS, "Player 2", name="2 Tankbustas 1")
st.reserves.extend([kop, tank])
tracker = TurnTracker(first_player="Player 2"); tracker.battle_round = 2
plan = {"unit_plans": {
    "2 Deffkoptas 1": {"role": "reserve_commit", "position": (49.0, 25.0)},
    "2 Tankbustas 1": {"role": "reserve_commit", "position": (15.0, 35.0)},
}}
agent_driver._validate_turn_plan(plan, "Player 2", st, tracker)
kp = plan["unit_plans"]["2 Deffkoptas 1"]["position"]
tp = plan["unit_plans"]["2 Tankbustas 1"]["position"]
print(f"      Deffkoptas {kp}   Tankbustas {tp}")
ok("Deffkoptas keep (49,25) (was clamped to (11,5))", kp == (49.0, 25.0))
ok("Tankbustas keep (15,35) (was clamped to (2,6))", tp == (15.0, 35.0))
ok("deep strike is available to the Deffkoptas",
   all(getattr(t.profile, "deep_strike", False) for t in kop.models))

print("\n   an ON-BOARD unit is still clamped (the rule that was right stays)")
st = fresh_state()
boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
for i, t in enumerate(boyz.models):
    t.x_in, t.y_in = 10.0 + 1.5 * (i % 5), 6.0 + 2.0 * (i // 5)
st.tokens.extend(boyz.models)
plan = {"unit_plans": {"2 Boyz 1": {"role": "advance", "position": (50.0, 40.0)}}}
agent_driver._validate_turn_plan(plan, "Player 2", st, TurnTracker(first_player="Player 2"))
bp = plan["unit_plans"]["2 Boyz 1"]["position"]
ok("a 45\" order for a 6\" move is still shortened", bp != (50.0, 40.0))

# ------------------------------------------------------- 4. colliding orders
# Used to be REPORTED to the planner. It is now separated deterministically
# instead - same protection, without the re-plan that measurably cost the army
# its WAAAGH turn (see test_plan_churn.py). What has to survive is the outcome:
# the two orders must not still be on top of each other afterwards.
print("\n4) two squads ordered to the same spot are separated, not re-planned")
st = fresh_state()
dread = build_squad(DEFF_DREAD, "Player 2", name="2 Deff Dread 1")
dread.models[0].x_in, dread.models[0].y_in = 26.70, 15.94
boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
for i, t in enumerate(boyz.models):
    t.x_in, t.y_in = 28.0 + 1.5 * (i % 5), 12.0 + 2.0 * (i // 5)
st.tokens.extend(dread.models + boyz.models)
clash = {"unit_plans": {"2 Deff Dread 1": {"role": "advance", "position": (30.0, 22.0), "priority": 1},
                        "2 Boyz 1": {"role": "advance", "position": (31.0, 21.0), "priority": 2}}}
probs = agent_driver._problems_for_the_planner(clash, "Player 2", st)
print("     ", probs)
ok("the 1.4\" collision no longer costs a re-plan",
   not any("cannot both stand there" in p for p in probs))
agent_driver._validate_turn_plan(clash, "Player 2", st, TurnTracker(first_player="Player 2"))
a = clash["unit_plans"]["2 Deff Dread 1"]["position"]
b = clash["unit_plans"]["2 Boyz 1"]["position"]
gap = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
print(f"      Deff Dread {a[0]:.1f},{a[1]:.1f}   Boyz {b[0]:.1f},{b[1]:.1f}   {gap:.1f}\" apart")
ok("the higher-priority Deff Dread keeps the doorway spot", (round(a[0], 2), round(a[1], 2)) == (30.0, 22.0))
ok("the Boyz are moved off it (was 1.4\")", gap > 1.4 + 1.0)
# Through the separation pass alone, not the whole validator: (40,21) is 10"
# from a 6"-move squad, so the validator's reach CLAMP would move it and the
# check would pass for the wrong reason.
apart = {"unit_plans": {"2 Deff Dread 1": {"role": "advance", "position": (30.0, 22.0), "priority": 1},
                        "2 Boyz 1": {"role": "advance", "position": (40.0, 21.0), "priority": 2}}}
by_squad = {"2 Deff Dread 1": dread, "2 Boyz 1": boyz}
ok("well-separated orders are left exactly where they were",
   not agent_driver._separate_colliding_positions(apart, by_squad)
   and apart["unit_plans"]["2 Boyz 1"]["position"] == (40.0, 21.0))

# ------------------------------------------- 5. LONE OPERATIVE vs the ORDERED SPOT
# User, on logs/game_20260808_213013.log:617: "wenn der plan war, den ghostkeel
# zu beschiessen, dann war der plan falsch, denn der ghostkeel hat lone op."
#   2 Deffkoptas 1: advance -> 1 Ghostkeel Battlesuit 1 @(26,8)
#   ("... move up within 24in to shoot it while staying out of easy charge range")
# The Ghostkeel was at (26.45,23.79), i.e. 14" from the ordered spot, and rule
# 24.24 caps it at 12". The existing check asks whether the target can be
# reached AT ALL (16.00" away, 12" of movement - yes), so only the position
# makes the order impossible.
print("\n5) LONE OPERATIVE (24.24) is judged from the ORDERED position too")
from game import status_effects
from game.factions.tau_empire import GHOSTKEEL_BATTLESUIT

st = fresh_state()
koptas = build_squad(DEFFKOPTAS, "Player 2", name="2 Deffkoptas 1")
koptas.models = koptas.models[:3]
for mo, (x, y) in zip(koptas.models, [(20.0, 4.0), (22.2, 4.0), (21.1, 5.9)]):
    mo.x_in, mo.y_in = x, y
gk = build_squad(GHOSTKEEL_BATTLESUIT, "Player 1", name="1 Ghostkeel Battlesuit 1")
gk.models[0].x_in, gk.models[0].y_in = 26.45, 23.79
st.tokens = list(koptas.models) + list(gk.models)
st.embarked_squads = []
lone = status_effects.lone_operative_range(gk)
print(f"      LONE OPERATIVE {lone:.0f}\"; squad->target {koptas.min_distance_to(gk):.2f}\","
      f" ordered spot->target {agent_driver._distance_from_squad_to_point(gk, (26.0, 8.0)):.2f}\"")
ok("the old check alone would NOT fire (the target is reachable this turn)",
   koptas.min_distance_to(gk) - min(mo.profile.movement_in for mo in koptas.models) <= lone)


def kopta_plan(spot):
    return {"unit_plans": {"2 Deffkoptas 1": {
        "role": "advance", "target": "1 Ghostkeel Battlesuit 1", "position": spot,
        "priority": 1, "reason": "shoot it"}}}


by_name = {s.name: s for s in agent_driver._all_squads(st.tokens)}
bad = agent_driver._unshootable_from_position_problems(kopta_plan((26.0, 8.0)), by_name, st)
print("      ", bad)
ok("the reported order is sent back to the planner",
   any("LONE OPERATIVE" in p and "cannot be shot at from there" in p for p in bad))

plan = kopta_plan((26.0, 8.0))
agent_driver._validate_turn_plan(plan, "Player 2", st, None)
entry = plan["unit_plans"]["2 Deffkoptas 1"]
ok("the backstop drops the impossible target", entry.get("target") is None)
ok("the backstop leaves the achievable position alone", entry.get("position") == (26.0, 8.0))

# Counter-check: a spot INSIDE the 12" is a perfectly good order and must survive.
good_spot = (26.0, 16.0)
ok("a spot inside the LONE OPERATIVE range is not flagged",
   not agent_driver._unshootable_from_position_problems(kopta_plan(good_spot), by_name, st))
plan_ok = kopta_plan(good_spot)
agent_driver._validate_turn_plan(plan_ok, "Player 2", st, None)
ok("a legal shooting order keeps its target",
   plan_ok["unit_plans"]["2 Deffkoptas 1"].get("target") == "1 Ghostkeel Battlesuit 1")

# And a target WITHOUT the ability is never touched by this rule.
ok("a target without LONE OPERATIVE is not flagged",
   not agent_driver._unshootable_from_position_problems(
       {"unit_plans": {"2 Deffkoptas 1": {"role": "advance", "target": "2 Deffkoptas 1",
                                          "position": (50.0, 40.0), "priority": 1,
                                          "reason": "x"}}}, by_name, st))

print(f"\n{checks - len(failed)}/{checks} checks passed")

# ------------------------------------------- 5. models left standing at 0.00"
# User report on the 20-strong Boyz mob: "warum bewegen sich nicht alle boyz die
# maximale distanz? warum bleiben einzelne modelle hinten stehen, waehrend
# andere nach vorne laufen. als mensch wuerde ich doch modell fuer modell
# bewegen und versuchen jedes einzelne modell so weit wie moeglich nach vorne zu
# verschieben."
#
# Measured on that unit before the fix: of 136 segment commits in one move, 35
# were rejected, EVERY one of them for "cannot end their move on top of"
# another model, and those models had aimed 4.38" on average and got 0.00".
# clamp_move() does not stop a model at a FRIENDLY base (rule 03.01 allows
# moving through one, only not ending on it), so the position it returns can be
# on top of a squadmate - and try_commit_segment() then snaps the whole segment
# back to the start. See _advance_model_toward().
print("\n5) a model whose target is occupied advances as far as it legally can")

from game.factions.orks import BOYZ_BIG_CHOPPA_TO_POWER_KLAW, PAINBOY, WARBOSS
from game import attached_units
from game.squad import min_model_movement
from game.turn import PHASES, PHASE_MOVEMENT

st = fresh_state()
mob = build_squad(BOYZ, "Player 2", composition_index=1,
                  choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}}, name="2 Boyz 1")
mob = attached_units.attach(build_squad(WARBOSS, "Player 2", name="2 Warboss 1"), mob, game_state=st)
mob = attached_units.attach(build_squad(PAINBOY, "Player 2", name="2 Painboy 1"), mob, game_state=st)
# A deep block, and a DIAGONAL destination. Both matter: packed tight, the
# formation slots of the rear models land where their squadmates are still
# standing, and moving at an angle rather than straight ahead is what makes
# those slots collide in the first place. Swept before settling on it - the
# same block sent straight forward leaves nobody behind even before the fix,
# so a test built on that scene would have proved nothing.
for i, model in enumerate(mob.models):
    model.x_in, model.y_in = 20.0 + (i % 5) * 1.35, 8.0 + (i // 5) * 1.35
st.tokens = list(mob.models)
GOAL = (28.0, 26.0)


def one_move():
    start = [(mo.x_in, mo.y_in) for mo in mob.models]
    tt = TurnTracker(first_player="Player 2")
    tt.phase_index = PHASES.index(PHASE_MOVEMENT)
    mc = MovementController(obstacles=st.obstacles, player_name="Player 2", turn_tracker=tt,
                            all_tokens=st.tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    mc.select(mob.models[0])
    agent_driver._advance_toward(mc, mob, GOAL)
    moved = [((mo.x_in - x) ** 2 + (mo.y_in - y) ** 2) ** 0.5
             for mo, (x, y) in zip(mob.models, start)]
    for mo, (x, y) in zip(mob.models, start):
        mo.x_in, mo.y_in = x, y
    return moved


def single_shot(mc, model, target_x, target_y, _tries_left=0):
    """A/B: the pre-fix behaviour - one attempt, and a refusal costs the whole
    segment rather than shortening it."""
    before = (model.x_in, model.y_in)
    nx, ny = mc.clamp_move(model, target_x, target_y)
    model.x_in, model.y_in = nx, ny
    mc.try_commit_segment(model)
    return (model.x_in, model.y_in) != before


real = agent_driver._advance_model_toward
agent_driver._advance_model_toward = single_shot
before_moved = one_move()
agent_driver._advance_model_toward = real
after_moved = one_move()

stuck_before = sum(1 for d in before_moved if d < 0.5)
stuck_after = sum(1 for d in after_moved if d < 0.5)
print(f"    A/B (pre-fix): {stuck_before} of {len(before_moved)} models moved under 0.5\""
      f"  (min {min(before_moved):.2f}\")")
print(f"    now:           {stuck_after} of {len(after_moved)} models moved under 0.5\""
      f"  (min {min(after_moved):.2f}\")")
ok("A/B - the reported scene really does leave models standing still",
   stuck_before >= 3)
ok("no model is left at a standstill any more", stuck_after == 0)
ok("...and every one of them actually advanced", min(after_moved) > 0.5)
ok("the unit is still coherent afterwards (rule 09.02)", not mob.check_coherency())
ok("nobody moved further than its Movement characteristic",
   max(after_moved) <= min_model_movement(mob) + 1e-6)

# The point is not only that nobody stands still - it is that the inches get
# used. "die maximale bewegungsreichweite auszureizen in bestimmten situationen
# ist essentiell... da darf kein zoll liegengelassen werden": whether move+charge
# reaches (rule 11.04), how many models end up in line of sight and how many
# stand on an objective all turn on the last inch, so the unit's total movement
# is a first-class check rather than a nice-to-have.
budget = min_model_movement(mob)
share_before = sum(before_moved) / (len(before_moved) * budget)
share_after = sum(after_moved) / (len(after_moved) * budget)
print(f"    movement actually used: {100 * share_before:.0f}% -> {100 * share_after:.0f}% of the unit's total")
ok("the unit as a whole uses MORE of its movement, not less",
   share_after > share_before)
ok("...and it uses most of what it has", share_after > 0.75)

if failed:
    print("FAILED:"); [print("  -", f) for f in failed]
# Exit non-zero on failure, like every other suite here. Without this the file
# printed "FAILED" and still exited 0, so a sweep that trusts exit codes - which
# is how these are run - reported it green while a check was broken.
sys.exit(1 if failed else 0)
