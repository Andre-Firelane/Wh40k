"""Engagement slots (ai/agent_driver._engagement_slots and its filter): the
standing room a charge, a pile-in and a consolidate hand their models.

Part of the AI-movement review of 2026-09-09. The ring used to be sampled one
base apart (2r+0.1" along the arc AND in depth), which for a 1.57"-base C'tan
meant six slots on a ring 19" round, and nothing said whether a slot was on a
wall, on another unit or inside a third unit's Engagement Range - every such
slot burned one of the _ENGAGEMENT_SLOT_TRIES for nothing. The two reported
charges were physically possible (brute-forced on the log's own boards: 87 and
5 legal engaged end spots within the roll) and both failed from every
approach; the legal spots lay BETWEEN the slots.

Now: a fixed arc pitch and ring depth (_ENGAGEMENT_ARC_STEP_IN,
_ENGAGEMENT_RING_STEP_IN), a `legal` filter that asks what try_commit_segment()
and check_charge_engagement() will ask later (13.05, tokens, disallowed
engagement, the board edge), an angular de-dupe in _ranked_free_slots() so the
limited tries are spent on DIFFERENT places, and one ring per target for the
whole charge ladder instead of one per approach.

Real MovementController objects, real datasheets, map2 dimensions.

Run: python test_charge_slots.py
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
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance, max_model_radius, model_terrain_violation  # noqa: E402
from game.terrain import DENSE, Obstacle  # noqa: E402
from game.turn import PHASE_CHARGE  # noqa: E402
import testkit as tk  # noqa: E402
from testkit import Checks  # noqa: E402

maps.apply_to_config(maps.get("map2"))
c = Checks("engagement slots")


def scene(defenders=1, others=(), obstacles=(), target_at=(20.0, 26.0)):
    """Player 2 Boyz at y=20 below a Player 1 Strike Team at `target_at`.
    `others`: (sheet, owner, (x, y)) extra single models on the board."""
    squad = tk.build(BOYZ, owner="Player 2", name="Chargers")
    squad.models = squad.models[:5]
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = 17.0 + i * 1.5, 20.0
    target = tk.build(STRIKE_TEAM, owner="Player 1", name="Target")
    target.models = target.models[:defenders]
    for i, m in enumerate(target.models):
        m.x_in, m.y_in = target_at[0] + i * 1.3, target_at[1]
    tokens = list(squad.models) + list(target.models)
    extra = []
    for index, (sheet, owner, (x, y)) in enumerate(others):
        other = tk.build(sheet, owner=owner, name=f"Other {index}")
        other.models = other.models[:1]
        other.models[0].x_in, other.models[0].y_in = x, y
        tokens.append(other.models[0])
        extra.append(other)
    mc = MovementController(obstacles=list(obstacles), player_name="Player 2",
                            turn_tracker=tk._tracker(PHASE_CHARGE, "Player 2"), all_tokens=tokens,
                            board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN)
    return mc, squad, target, extra, tokens


def charge_filter(mc, squad, target):
    return ad._engagement_slot_filter(squad, mc, ad._charge_keep_out(squad, target, mc.all_tokens))


# ================================================================= 1. density
print("1) the ring is sampled by length, not by base")
mc, squad, target, _x, tokens = scene()
r = max_model_radius(squad)
enemy = target.models[0]
ring = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN)
inner = ad.CHARGE_TARGET_CLEARANCE_IN + r + enemy.radius_in
inner_ring = [s for s in ring if abs(math.dist((s[0], s[1]), (enemy.x_in, enemy.y_in)) - inner) < 1e-6]
c.true(f"the inner ring holds at least one slot per {ad._ENGAGEMENT_ARC_STEP_IN}\" of arc "
       f"({len(inner_ring)} on {2 * math.pi * inner:.1f}\")",
       len(inner_ring) >= int(2 * math.pi * inner / ad._ENGAGEMENT_ARC_STEP_IN) - 1)
# slot[2] is the slot's EDGE distance to the nearest target model: the inner
# ring stands at the charge's clearance (1.0"), the outer at Engagement Range.
depths = sorted({round(s[2], 2) for s in ring})
c.eq("three ring depths for a charge: at clearance, +0.5, +1.0 (up to Engagement Range)",
     depths, [ad.CHARGE_TARGET_CLEARANCE_IN, ad.CHARGE_TARGET_CLEARANCE_IN + 0.5, ENGAGEMENT_RANGE_IN])
old_ring = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN, arc_step_in=2 * r + 0.1)
c.true(f"...against {len(old_ring)} slots at the old one-base pitch", len(ring) >= 2 * len(old_ring))
c.true("slots never sit inside the enemy formation (closer than clearance to any target model)",
       all(min(math.dist((s[0], s[1]), (e.x_in, e.y_in)) for e in target.models) >= inner - 0.05 - 1e-9
           for s in ring))
c.true("tightest first: the list starts at clearance and ends at Engagement Range",
       abs(ring[0][2] - ad.CHARGE_TARGET_CLEARANCE_IN) < 1e-6 and abs(ring[-1][2] - ENGAGEMENT_RANGE_IN) < 1e-6)

# ================================================================= 2. legality
print("2) the filter asks what the move will be asked later")
wall = Obstacle(23.5, 26.0, 3.0, 8.0, DENSE)   # centred: x 22-25, y 22-30 - the east side of the ring
mc, squad, target, _x, tokens = scene(obstacles=[wall])
legal = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN, legal=charge_filter(mc, squad, target))
raw = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN)
probe = max(squad.models, key=lambda m: m.radius_in)
c.true("rule 13.05: no legal slot has its base on the Dense wall",
       legal and not any(model_terrain_violation(probe, [wall], s[0], s[1]) for s in legal))
c.true("...while the raw ring did offer such slots",
       any(model_terrain_violation(probe, [wall], s[0], s[1]) for s in raw))
c.true("...and the west side of the ring is still there", any(s[0] < 20.0 for s in legal))

# A third enemy unit beside the target: a CHARGE may not end within Engagement
# Range of it (11.04), a pile-in may (12.03 has no such clause).
mc, squad, target, extra, tokens = scene(others=[(GRETCHIN, "Player 1", (16.5, 26.0))])
third = extra[0]
charge_legal = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN,
                                    legal=charge_filter(mc, squad, target))
pile_legal = ad._engagement_slots(target, r, ad.PILE_IN_CLEARANCE_IN,
                                  legal=ad._engagement_slot_filter(squad, mc, set()))


def engaged_with(slot, other):
    return math.dist((slot[0], slot[1]), (other.x_in, other.y_in)) - r - other.radius_in <= ENGAGEMENT_RANGE_IN


c.true("a charge's ring keeps clear of the third unit's Engagement Range",
       charge_legal and not any(engaged_with(s, third.models[0]) for s in charge_legal))
c.true("a pile-in's ring does not (rule 12.03 forbids nothing there)",
       any(engaged_with(s, third.models[0]) for s in pile_legal))
c.true("neither ring overlaps the third unit's base",
       not any(math.dist((s[0], s[1]), (third.models[0].x_in, third.models[0].y_in))
               < r + third.models[0].radius_in for s in charge_legal + pile_legal))

# A FRIENDLY unit on the ring is not standing room either; the charging
# squad's own models are (they are the ones about to move).
mc, squad, target, extra, tokens = scene(others=[(GRETCHIN, "Player 2", (20.0, 23.0))])
friend = extra[0].models[0]
legal = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN, legal=charge_filter(mc, squad, target))
c.true("no legal slot overlaps a friendly unit's base",
       not any(math.dist((s[0], s[1]), (friend.x_in, friend.y_in)) < r + friend.radius_in for s in legal))
# A squadmate parked exactly on the inner ring's southern slot - in a scene
# of its own, or the friendly unit above would be what blocks that slot.
mc, squad, target, _x, tokens = scene()
on_ring = (20.0, 26.0 - inner)
squad.models[0].x_in, squad.models[0].y_in = on_ring
legal2 = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN, legal=charge_filter(mc, squad, target))
c.true("scene check: that point IS a ring slot",
       any(math.dist((s[0], s[1]), on_ring) < 0.3 for s in raw))
c.true("a squadmate on the ring does NOT remove slots (it is about to move)",
       any(math.dist((s[0], s[1]), on_ring) < 0.3 for s in legal2))

# The board edge.
mc, squad, target, _x, tokens = scene(target_at=(1.2, 26.0))
legal = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN, legal=charge_filter(mc, squad, target))
c.true("no legal slot puts a base over the board edge", legal and all(s[0] >= r - 1e-9 for s in legal))

# ================================================================== 3. de-dupe
print("3) the ranked list spends its tries on different places")
mc, squad, target, _x, tokens = scene()
model = squad.models[2]
legal = ad._engagement_slots(target, r, ad.CHARGE_TARGET_CLEARANCE_IN, legal=charge_filter(mc, squad, target))
mc.select(model)
mc.start_charge_move(9.0, [target])
picked = ad._ranked_free_slots(model, legal, [], 9.0, squad=squad)
c.eq("at most _ENGAGEMENT_SLOT_TRIES slots come back", len(picked), ad._ENGAGEMENT_SLOT_TRIES)
gap = 2 * model.radius_in + 0.05
c.true("...every pair at least one base apart",
       all(math.dist((a[0], a[1]), (b[0], b[1])) >= gap - 1e-9
           for i, a in enumerate(picked) for b in picked[i + 1:]))
c.true("...tightest first: the first slot is at clearance",
       abs(picked[0][2] - ad.CHARGE_TARGET_CLEARANCE_IN) < 1e-6)
c.true("...and the whole list is reachable within the budget",
       all(math.dist((s[0], s[1]), (model.x_in, model.y_in)) <= 9.0 for s in picked))
far = ad._ranked_free_slots(model, legal, [], 1.0, squad=squad)
c.eq("a budget that reaches no slot returns none", far, [])

# ============================================= 4. the charge ends where it may
print("4) a charge beside a third unit ends engaged with the target only")
mc, squad, target, extra, tokens = scene(others=[(GRETCHIN, "Player 1", (16.5, 26.0))])
third = extra[0].models[0]
mc.select(squad.models[0])
mc.start_charge_move(8.0, [target])
ad._charge_per_model(mc, squad, target, 8.0)
engaged = [m for m in squad.models if any(edge_distance(m, e) <= ENGAGEMENT_RANGE_IN for e in target.models)]
c.true(f"the charge reaches the target ({len(engaged)} of 5 engaged)", len(engaged) >= 1)
c.true("no model ends within Engagement Range of the third unit",
       not any(edge_distance(m, third) <= ENGAGEMENT_RANGE_IN for m in squad.models))
c.eq("and the unit is coherent", squad.check_coherency(), [])

# ============================================================ 5. at the source
print("5) guards at the source")
driver = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()
ladder = driver[driver.index("def _run_charge_attempts("):driver.index("def _log_charge_geometry(")]
c.eq("the ladder builds the ring exactly once", ladder.count("_engagement_slots("), 1)
c.true("...with the charge's own keep-out", "_charge_keep_out(squad, target, movement_controller.all_tokens)" in ladder)
c.true("...and hands it to the routed approach", "_charge_along_route(movement_controller, squad, target, max_distance, slots=slots)" in ladder)
c.true("...and to every swept approach", "approach_angle_deg=angle, detour_fraction=detour, slots=slots)" in ladder)
spread = driver[driver.index("def _spread_into_engagement("):driver.index("def _engagement_step(")]
c.true("the spread builds a ring only when none was handed down", "    if slots is None:\n" in spread)
c.true("...filtered for the OPEN move's keep-out", "_keep_out_for_open_move(squad, movement_controller)" in spread)
filt = driver[driver.index("def _engagement_slot_filter("):driver.index("def _engagement_slots(")]
for needle, why in (("formation_layout.on_board(x, y, r)", "the board edge"),
                    ("model_terrain_violation(probe, dense, x, y)", "rule 13.05"),
                    ("ENGAGEMENT_RANGE_IN + _LANDING_OVERLAP_MARGIN_IN", "the keep-out engagement range"),
                    ("not t.is_dead()", "dead models are not blockers")):
    c.true(f"the filter asks {why}", needle in filt)
geometry = driver[driver.index("def _log_charge_geometry("):driver.index("def _handle_charge(")]
c.true("[charge geometry] reports the LEGAL count", "legal)" in geometry and "_engagement_slot_filter(" in geometry)
c.true("...and _handle_charge hands it the controller to do so",
       "_log_charge_geometry(game_log, squad, target, charge_controller.max_distance,\n                                 movement_controller=movement_controller)" in driver)

c.finish()
