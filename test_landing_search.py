"""The landing-spot search (ai/agent_driver._free_landing_near) and its seam in
_clamp_target_against_friendly_models().

Rule 03.01: a base may move THROUGH friendly models, it may not END on one.
The clamp used to answer an occupied landing by cutting the move at the FIRST
friendly base on the line; now it looks for the nearest legal spot around the
intended point first, and only falls back to the cut when there is none.
Measured on the reported 21-model blob before this existed: 535 truncations in
one move, 445 of them with a free spot within 2" of the intended point.

Every scene here is built by hand on map 2's board dimensions, with terrain
and tokens placed to isolate ONE clause of "legal" at a time - so a failure
names the clause. The engine's own MovementController is used throughout;
nothing is stubbed.

Run: python test_landing_search.py
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver as ad  # noqa: E402
from game import config, maps  # noqa: E402
from game.factions.orks import BATTLEWAGON, BOYZ, GRETCHIN  # noqa: E402
from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.squad import model_terrain_violation  # noqa: E402
from game.terrain import DENSE, Obstacle  # noqa: E402
from game.turn import PHASE_MOVEMENT  # noqa: E402
import testkit as tk  # noqa: E402
from testkit import Checks  # noqa: E402

maps.apply_to_config(maps.get("map2"))
c = Checks("landing-spot search")


def scene(mover_sheet=BOYZ, mover_at=(20.0, 20.0), others=(), obstacles=(), owner="Player 2"):
    """One moving unit (model 0 at `mover_at`, the rest parked far away so
    they are unplaced squadmates and never blockers) plus `others`: a list of
    (datasheet, owner, (x, y)) single-model presences. Returns
    (controller, squad, model, tokens)."""
    squad = tk.build(mover_sheet, owner=owner, name="Mover")
    tk.line_up(squad, x=2.0, y=42.0, spacing=1.4)
    model = squad.models[0]
    model.x_in, model.y_in = mover_at
    tokens = list(squad.models)
    for index, (sheet, other_owner, (x, y)) in enumerate(others):
        other = tk.build(sheet, owner=other_owner, name=f"Other {index}")
        tk.line_up(other, x=2.0, y=2.0 + index * 1.5, spacing=1.4)
        other.models[0].x_in, other.models[0].y_in = x, y
        tokens.append(other.models[0])
    controller = MovementController(
        obstacles=list(obstacles), player_name=owner, turn_tracker=tk._tracker(PHASE_MOVEMENT, owner),
        all_tokens=tokens, board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    controller.select(model)
    if controller.selected_squad is not squad:
        controller.selected_squad = squad
    controller.start_move()
    return controller, squad, model, tokens


def clear_of(point, model, tokens):
    r = model.radius_in
    return all(math.dist(point, (t.x_in, t.y_in)) >= r + t.radius_in + ad._LANDING_OVERLAP_MARGIN_IN
               for t in tokens if t is not model and t.squad is not model.squad)


print("1) an occupied landing lands NEXT to the intended point, not short of it")
mc, squad, boy, tokens = scene(others=[(GRETCHIN, "Player 2", (20.0, 26.0))])
target = (20.0, 26.0)
spot = ad._clamp_target_against_friendly_models(boy, *target, squad, mc, [], caller="pass")
c.true("the clamp no longer returns a point on the line short of the blocker",
       abs(spot[0] - 20.0) > 1e-6 or spot[1] > 25.0)
c.true("the spot is within 1.5\" of the intended point", math.dist(spot, target) <= 1.5 + 1e-6)
c.true("the spot is clear of the friendly blocker by the overlap margin", clear_of(spot, boy, tokens))
c.true("the spot is within the model's remaining move", math.dist(spot, (boy.x_in, boy.y_in)) <= 6.0 + 1e-6)
again = ad._clamp_target_against_friendly_models(boy, *target, squad, mc, [], caller="pass")
c.eq("deterministic: the same board gives the same spot", again, spot)

print("2) a clear landing is returned untouched (the search is not consulted)")
mc, squad, boy, tokens = scene(others=[(GRETCHIN, "Player 2", (24.0, 26.0))])
c.eq("unchanged target", ad._clamp_target_against_friendly_models(boy, 20.0, 26.0, squad, mc, [], caller="pass"),
     (20.0, 26.0))

print("3) nothing free within reach -> the old truncation, unchanged")
wall_of_grots = [(GRETCHIN, "Player 2", (20.0 + dx, 26.0 + dy))
                 for dx in (-2.6, -1.3, 0.0, 1.3, 2.6) for dy in (-2.6, -1.3, 0.0, 1.3, 2.6)]
mc, squad, boy, tokens = scene(others=wall_of_grots)
c.eq("the search itself reports nothing", ad._free_landing_near(boy, (20.0, 26.0), squad, mc, []), None)
cut = ad._clamp_target_against_friendly_models(boy, 20.0, 26.0, squad, mc, [], caller="pass")
c.true("the clamp then cuts the move on the line, short of the first blocker",
       abs(cut[0] - 20.0) < 1e-6 and 20.0 < cut[1] < 26.0)

print("4) the caller's per-model cap is honoured (a short fraction rung stays short)")
mc, squad, boy, tokens = scene(others=[(GRETCHIN, "Player 2", (20.0, 26.0))])
c.eq("with max_travel=1.0 no ring spot 6\" out is reachable",
     ad._free_landing_near(boy, (20.0, 26.0), squad, mc, [], max_travel=1.0), None)
capped = ad._free_landing_near(boy, (20.0, 26.0), squad, mc, [], max_travel=4.6)
c.true("with max_travel=4.6 the spot found is within 4.6\" of the model",
       capped is not None and math.dist(capped, (boy.x_in, boy.y_in)) <= 4.6 + 1e-6)

print("5) rule 13.05: a spot on Dense terrain is not a landing")
# The wall lies BETWEEN the model and the intended point, so the spots just
# short of the point - the ones the search likes best - are on the wall. The
# AI crosses Dense terrain for free (config.WALL_CROSSING_PLAYERS), so transit
# is not what keeps it off: only the end-position rule does.
wall = Obstacle(20.0, 23.7, 20.0, 1.4, DENSE)   # centred: x 10-30, y 23.0-24.4
c.true("scene check: the wall spans the short side of the intended point",
       wall.min_y <= 24.0 <= wall.max_y and wall.min_x <= 20.0 <= wall.max_x)
mc, squad, boy, tokens = scene(others=[(GRETCHIN, "Player 2", (20.0, 26.0))], obstacles=[wall])
spot = ad._free_landing_near(boy, (20.0, 26.0), squad, mc, [])
c.true("a spot is found", spot is not None)
c.true("...and it is not on the wall", spot is not None and not model_terrain_violation(boy, [wall], *spot))
c.true("...which means it had to leave the model's own line (the straight-behind spots are on the wall)",
       spot is not None and (abs(spot[0] - 20.0) > 0.3 or spot[1] > wall.max_y + boy.radius_in - 1e-6))

print("6) rule 09.05: a Normal move may not end within Engagement Range of an ENEMY")
mc, squad, boy, tokens = scene(others=[(STRIKE_TEAM, "Player 1", (20.0, 26.0))])
c.eq("an enemy on the intended point leaves no legal spot within the ring",
     ad._free_landing_near(boy, (20.0, 26.0), squad, mc, []), None)

print("7) rule 09.02: a spot beside a squadmate already placed wins over a nearer one that is not")
mc, squad, boy, tokens = scene(others=[(GRETCHIN, "Player 2", (20.0, 26.0))])
# Where the search lands with NO squadmate placed - then park a squadmate on
# the OTHER side of the intended point, so that spot is out of coherency
# with it while an equally near spot on the anchor's side is not.
# `or (nan, nan)`: under a probe that makes the search return None these
# checks must go RED, not crash the suite (a crash says nothing about WHICH
# assurance broke) - nan fails every comparison below.
alone = ad._free_landing_near(boy, (20.0, 26.0), squad, mc, []) or (math.nan, math.nan)
anchor = squad.models[1]
anchor.x_in, anchor.y_in = 20.0 - 3.5 * (1 if alone[0] >= 20.0 else -1), 24.0
alone_edge = math.dist(alone, (anchor.x_in, anchor.y_in)) - boy.radius_in - anchor.radius_in
c.true("scene check: the unanchored spot is NOT within 1.9\" of the anchor", alone_edge > 1.9)
spot = ad._free_landing_near(boy, (20.0, 26.0), squad, mc, [anchor]) or (math.nan, math.nan)
edge = math.dist(spot, (anchor.x_in, anchor.y_in)) - boy.radius_in - anchor.radius_in
c.true("the chosen spot keeps coherency with the placed squadmate (edge <= 1.9\")", edge <= 1.9 + 1e-6)
c.true("...so it is a different spot from the unanchored one", spot != alone)
c.true("...and no further from the intended point than one ring", math.dist(spot, (20.0, 26.0))
       <= math.dist(alone, (20.0, 26.0)) + ad._LANDING_RING_STEP_IN + 1e-6)

print("8) the A/B switch: a caller in LANDING_SEARCH_OFF_FOR gets the old cut")
mc, squad, boy, tokens = scene(others=[(GRETCHIN, "Player 2", (20.0, 26.0))])
saved = ad.LANDING_SEARCH_OFF_FOR
try:
    ad.LANDING_SEARCH_OFF_FOR = frozenset({"pass"})
    off = ad._clamp_target_against_friendly_models(boy, 20.0, 26.0, squad, mc, [], caller="pass")
    on = ad._clamp_target_against_friendly_models(boy, 20.0, 26.0, squad, mc, [], caller="close-up")
finally:
    ad.LANDING_SEARCH_OFF_FOR = saved
c.true("caller 'pass' switched off -> a point on the line short of the blocker",
       abs(off[0] - 20.0) < 1e-6 and off[1] < 26.0)
c.true("caller 'close-up' still searches", math.dist(on, (20.0, 26.0)) <= 1.5 + 1e-6 and clear_of(on, boy, tokens))

print("8b) the route walker is excluded BY DESIGN (measured - see _LANDING_SEARCH_EXCLUDED)")
c.true("'route' is on the shipped exclusion list", "route" in ad._LANDING_SEARCH_EXCLUDED)
routed = ad._clamp_target_against_friendly_models(boy, 20.0, 26.0, squad, mc, [], caller="route")
c.true("...so caller 'route' gets the old cut, not a re-landing",
       abs(routed[0] - 20.0) < 1e-6 and routed[1] < 26.0)
# The engagement step is the other measured exclusion: the search does not
# know Engagement Range, and on the reported Warbikers pile-in it re-landed a
# model beside its slot and out of range (test_melee_engagement.py section 3).
c.true("...and the engagement step, whose slots the search cannot see",
       "engagement-step" in ad._LANDING_SEARCH_EXCLUDED)
stepped = ad._clamp_target_against_friendly_models(boy, 20.0, 26.0, squad, mc, [], caller="engagement-step")
c.true("...so caller 'engagement-step' gets the old cut too",
       abs(stepped[0] - 20.0) < 1e-6 and stepped[1] < 26.0)
c.true("...while the exclusion list names nothing else that is measured to help",
       ad._LANDING_SEARCH_EXCLUDED == frozenset({"route", "engagement-step"}))

print("8c) stopping short beats sliding sideways at equal distance (the lateral penalty)")
mc, squad, boy, tokens = scene(others=[(GRETCHIN, "Player 2", (20.0, 26.0))])
spot = ad._free_landing_near(boy, (20.0, 26.0), squad, mc, [])
# "On the line" up to the ring's own angular pitch: a ring of 31 points has no
# point at exactly 180 degrees, the nearest two sit 0.13" either side of it.
c.true("with a single blocker ON the intended point the spot lies (all but) on the model's own line, short of it",
       spot is not None and abs(spot[0] - 20.0) <= 0.3 and 20.0 < spot[1] < 26.0)
c.true("the lateral weight is positive (a sideways inch costs more than a straight one)",
       ad._LANDING_LATERAL_WEIGHT > 0)

print("9) a wide base looks further: the Battlewagon boxed in by its own infantry")
mc, squad, wagon, tokens = scene(mover_sheet=BATTLEWAGON, mover_at=(20.0, 20.0),
                                 others=[(GRETCHIN, "Player 2", (20.0, 27.0))])
need = wagon.radius_in + tokens[-1].radius_in
spot = ad._free_landing_near(wagon, (20.0, 27.0), squad, mc, [])
c.true("a base of r %.2f\" needs %.2f\" of clearance - beyond the 2\" default ring" % (wagon.radius_in, need),
       need > ad._LANDING_MAX_RADIUS_IN)
c.true("...and still finds a spot, because the radius scales with the base", spot is not None)
c.true("...clear of the blocker", spot is not None and clear_of(spot, wagon, tokens))

c.finish()
