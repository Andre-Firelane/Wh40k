"""The slot-first charge approach (ai/agent_driver._charge_slot_first): the
charge as a player makes it - pick the spot, route the lead there, bring the
rest up behind it, then spread into the fight.

Part of the AI-movement review of 2026-09-09. The thirteen swept approaches
all begin by shoving the whole formation rigidly toward the nearest own/enemy
pair; when that line ends on a wall or inside a third unit's Engagement
Range, every approach loses most of the roll before phase 2 starts. Measured
on measure_charge_scenes.py (100 hard scenes on real map2 terrain, every one
possible by brute force): the ladder without this approach completed 92 and
with it 96, and with the follow-up spread pass and the ring from base contact
put 365 models into the fight against 339.

Real MovementController objects, real datasheets, map2 dimensions; the
ladder itself is driven the way measure_reported_moves.py drives it.

Run: python test_charge_slot_first.py
"""
import io
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from ai import agent_driver as ad  # noqa: E402
from game import config, maps  # noqa: E402
from game.factions.orks import BOYZ, GRETCHIN  # noqa: E402
from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance, max_model_radius  # noqa: E402
from game.terrain import DENSE, Obstacle  # noqa: E402
from game.turn import PHASE_CHARGE  # noqa: E402
import testkit as tk  # noqa: E402
from testkit import Checks  # noqa: E402

maps.apply_to_config(maps.get("map2"))
c = Checks("slot-first charge")


def scene(chargers=5, charger_at=(17.0, 20.0), target_at=(20.0, 28.0), others=(), obstacles=()):
    squad = tk.build(BOYZ, owner="Player 2", name="Chargers")
    squad.models = squad.models[:chargers]
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = charger_at[0] + (i % 5) * 1.5, charger_at[1] - (i // 5) * 1.5
    target = tk.build(STRIKE_TEAM, owner="Player 1", name="Target")
    target.models = target.models[:3]
    for i, m in enumerate(target.models):
        m.x_in, m.y_in = target_at[0] + i * 1.3, target_at[1]
    tokens = list(squad.models) + list(target.models)
    extra = []
    for index, (sheet, owner, positions) in enumerate(others):
        other = tk.build(sheet, owner=owner, name=f"Other {index}")
        other.models = other.models[:len(positions)]
        for m, (x, y) in zip(other.models, positions):
            m.x_in, m.y_in = x, y
            tokens.append(m)
        extra.append(other)
    mc = MovementController(obstacles=list(obstacles), player_name="Player 2",
                            turn_tracker=tk._tracker(PHASE_CHARGE, "Player 2"), all_tokens=tokens,
                            board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN)
    return mc, squad, target, extra


def open_charge(mc, squad, target, roll):
    mc.select(squad.models[0])
    if mc.selected_squad is not squad:
        mc.selected_squad = squad
    mc.start_charge_move(roll, [target])


def ring(mc, squad, target):
    return ad._engagement_slots(target, max_model_radius(squad), ad._CHARGE_RING_INNER_EDGE_IN,
                                legal=ad._engagement_slot_filter(squad, mc, ad._charge_keep_out(squad, target, mc.all_tokens)))


def engaged(squad, target):
    return [m for m in squad.models if any(edge_distance(m, e) <= ENGAGEMENT_RANGE_IN for e in target.models)]


def positions(squad):
    return [(round(m.x_in, 4), round(m.y_in, 4)) for m in squad.models]


# ================================================= 1. the reported form: a wall
print("1) a Dense wall on the straight line: the lead routes round it")
# The wall covers the direct line from the chargers to the target; its ends
# are open. The rigid shove ends ON the wall (13.05) from every straight-ish
# direction; a route round the end fits the roll.
wall = Obstacle(21.0, 24.0, 10.0, 1.2, DENSE)   # centred: x 16-26, y 23.4-24.6
mc, squad, target, _x = scene(obstacles=[wall])
open_charge(mc, squad, target, 9.0)
before = positions(squad)
slots = ring(mc, squad, target)
c.true("scene check: the ring is legal and non-empty", len(slots) > 20
       and all(not ad.model_terrain_violation(squad.models[0], [wall], s[0], s[1]) for s in slots))
landed = ad._charge_slot_first(mc, squad, target, 9.0, slots)
c.true("the approach lands", landed)
c.true("...with at least one model engaged", len(engaged(squad, target)) >= 1)
c.eq("...and the unit connected (rule 09.02)", squad.check_coherency(), [])
c.true("...nobody standing on the wall (rule 13.05)",
       not any(ad.model_terrain_violation(m, [wall]) for m in squad.models))
c.true("...and every model moved by a legal amount (<= the roll)",
       all(math.dist(b, (m.x_in, m.y_in)) <= 9.0 + 1e-6 for b, m in zip(before, squad.models)))
mc.confirm_move()
c.eq("the engine confirms it", mc.errors, [])

# ============================================ 2. followers keep the unit whole
print("2) followers that reach no slot of their own trail the placed set")
mc, squad, target, _x = scene(chargers=10, charger_at=(15.0, 21.0), target_at=(19.0, 29.0))
open_charge(mc, squad, target, 7.0)
slots = ring(mc, squad, target)
landed = ad._charge_slot_first(mc, squad, target, 7.0, slots)
c.true("ten Boyz land", landed)
c.eq("...connected", squad.check_coherency(), [])
fight = engaged(squad, target)
c.true(f"...with several in the fight ({len(fight)} of 10)", len(fight) >= 3)
rear = [m for m in squad.models if m not in fight]
c.true("...and every model out of the fight within 2\" of a squadmate",
       all(any(edge_distance(m, o) <= 2.0 for o in squad.models if o is not m) for m in rear))

# ================================== 2b. a follower's step must keep the link
print("2b) a follower's legal step that breaks the link is undone, and it trails instead")
# Two target models 8" apart. The lead takes the near one; the follower stands
# nearest to the FAR one, so the tightest-first ranking hands it a slot there
# first - legal, in range, and 6" from the lead. That step must be undone and
# the follower sent to a slot beside the lead instead; without the per-step
# link check it would sit at the far model and the whole approach would fail
# on the final coherency check.
# The LEAD is the model nearest the target unit (no melee character here), so
# it stands a little closer to its model than the follower does to the far one.
mc, squad, target, _x = scene(chargers=2, charger_at=(20.0, 24.5), target_at=(20.0, 28.0))
squad.models[1].x_in, squad.models[1].y_in = 27.0, 24.0
target.models = target.models[:2]
target.models[1].x_in, target.models[1].y_in = 28.0, 28.0
mc.all_tokens[:] = list(squad.models) + list(target.models)
open_charge(mc, squad, target, 8.0)
slots = ring(mc, squad, target)
follower = squad.models[1]
c.true("scene check: the other model is the lead (nearest to the target unit)",
       edge_distance(squad.models[0], target.models[0]) < edge_distance(follower, target.models[1]))
first = ad._ranked_free_slots(follower, slots, [], 8.0, must_close_to_1in=True, squad=squad)[0]
c.true("scene check: the follower's first-ranked slot is beside the FAR model",
       math.dist((first[0], first[1]), (28.0, 28.0)) < math.dist((first[0], first[1]), (20.0, 28.0)))
landed = ad._charge_slot_first(mc, squad, target, 8.0, slots)
c.true("the approach lands", landed)
c.eq("...connected", squad.check_coherency(), [])
c.true("...with the follower beside the LEAD's model, not the far one",
       math.dist((follower.x_in, follower.y_in), (20.0, 28.0)) < math.dist((follower.x_in, follower.y_in), (28.0, 28.0)))

# ===================================== 3. the spread pass is what fills the ring
print("3) after landing, the spread pass pulls the rest into the fight")
calls = []
real_spread = ad._spread_into_engagement


def counting_spread(*a, **k):
    calls.append(len(engaged(a[1], a[2])))
    result = real_spread(*a, **k)
    calls.append(len(engaged(a[1], a[2])))
    return result


ad._spread_into_engagement = counting_spread
try:
    mc, squad, target, _x = scene(chargers=10, charger_at=(15.0, 21.0), target_at=(19.0, 29.0))
    open_charge(mc, squad, target, 7.0)
    landed = ad._charge_slot_first(mc, squad, target, 7.0, ring(mc, squad, target))
finally:
    ad._spread_into_engagement = real_spread
c.true("the spread phase runs once the unit is connected", landed and len(calls) == 2)
# What it adds is measured in aggregate, not on one scene: on
# measure_charge_scenes.py's 100 hard scenes the approach put 273 models into
# the fight without this pass and 365 with it (365 against the sweep's 339).
# Here it may find nothing left to add; it must never take an engaged model
# away (every step keeps the baseline of 0 coherency errors).
c.true(f"...and never loses engaged models ({calls[0] if calls else '-'} -> {calls[1] if calls else '-'})",
       len(calls) == 2 and calls[1] >= calls[0])

# ============================================== 4. a bystander is not touched
print("4) a third unit beside the target: the route ends clear of its Engagement Range")
mc, squad, target, extra = scene(others=[(GRETCHIN, "Player 1", [(23.5, 26.0), (24.7, 26.0), (25.9, 26.0)])])
third = extra[0]
open_charge(mc, squad, target, 9.0)
landed = ad._charge_slot_first(mc, squad, target, 9.0, ring(mc, squad, target))
c.true("the approach lands beside a bystander", landed)
c.true("...with nobody within Engagement Range of it",
       not any(edge_distance(m, b) <= ENGAGEMENT_RANGE_IN for m in squad.models for b in third.models))
mc.confirm_move()
c.eq("...and the engine confirms it", mc.errors, [])

# ======================================================= 5. failure is clean
print("5) when it cannot land, it puts everything back")
box = Obstacle(21.3, 28.4, 20.0, 6.2, DENSE)   # the target parked inside a Dense box
mc, squad, target, _x = scene(obstacles=[box])
open_charge(mc, squad, target, 9.0)
before = positions(squad)
ranges = dict(mc.remaining_range)
slots = ring(mc, squad, target)
c.eq("scene check: the ring has no legal slot at all", slots, [])
c.eq("no slots -> no landing", ad._charge_slot_first(mc, squad, target, 9.0, slots), False)
c.eq("...and nothing moved", positions(squad), before)
c.eq("...and no budget was spent", dict(mc.remaining_range), ranges)
mc.cancel_move()
mc2, squad2, target2, _x = scene(charger_at=(17.0, 8.0), target_at=(20.0, 28.0))
open_charge(mc2, squad2, target2, 6.0)
before = positions(squad2)
c.eq("a roll that reaches no slot -> no landing",
     ad._charge_slot_first(mc2, squad2, target2, 6.0, ring(mc2, squad2, target2)), False)
c.eq("...and nothing moved", positions(squad2), before)
c.eq("a closed move -> no landing", ad._charge_slot_first(mc2, squad2, target2, 6.0, []), False)

# ================================================ 6. the ladder tries it first
print("6) the ladder: slot-first first, then the sweep as before")
mc, squad, target, _x = scene(obstacles=[wall])
roll = 9.0


def reopen():
    open_charge(mc, squad, target, roll)


reopen()
attempts = []
real_slot_first = ad._charge_slot_first
real_per_model = ad._charge_per_model
ad._charge_slot_first = lambda *a, **k: (attempts.append("slot-first"), real_slot_first(*a, **k))[1]
ad._charge_per_model = lambda *a, **k: (attempts.append("sweep"), real_per_model(*a, **k))[1]
try:
    ok, errors = ad._run_charge_attempts(mc, squad, target, roll, reopen=reopen, confirm=mc.confirm_move)
finally:
    ad._charge_slot_first = real_slot_first
    ad._charge_per_model = real_per_model
c.true("the wall charge completes through the real ladder", ok is True)
c.eq("...on the first approach, which is slot-first", attempts, ["slot-first"])
c.true("...leaving the unit engaged and connected",
       len(engaged(squad, target)) >= 1 and squad.check_coherency() == [])

# ================================================================ 7. source
print("7) guards at the source")
driver = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()
ladder = driver[driver.index("def _run_charge_attempts("):driver.index("def _log_charge_geometry(")]
c.true("slot-first is the first rung", 'for attempt in ["slot-first"] + (["route"] if routed_first else []) + approaches:' in ladder)
c.true("...and is not gated on walls", "if attempt == \"slot-first\":\n            _charge_slot_first(" in ladder)
c.true("the charge ring starts at base contact", "_CHARGE_RING_INNER_EDGE_IN = PILE_IN_CLEARANCE_IN" in driver
       and "target, max_model_radius(squad), _CHARGE_RING_INNER_EDGE_IN," in ladder)
body = driver[driver.index("def _charge_slot_first("):driver.index("def _run_charge_attempts(")]
c.true("routes with enemy BASES as blockers, not padded ranges (measured)",
       "pathfinding.enemy_models_for(candidate_lead, movement_controller.all_tokens)" in body
       and "_engagement_padded_models(" not in body)
c.true("re-lands a refused waypoint through the landing search", 'caller="charge-route"' in body)
c.true("followers walk routed steps and must touch the placed set",
       "def routed_step(model, goal, budget):" in body and "touches_placed(model)" in body)
c.true("the spread pass runs after the unit is connected",
       "_spread_into_engagement(movement_controller, squad, target_squad, CHARGE_TARGET_CLEARANCE_IN,\n                            True, 0, close_in_pairs, slots=slots)" in body)
c.true("failure restores the snapshot", body.count("_restore_positions(movement_controller, squad, snapshot)") >= 2)

c.finish()
