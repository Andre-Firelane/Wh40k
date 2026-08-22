"""Disembark placement shape: a CLUMP on one side of the transport, not a ring
around it (rule 18.04/18.05, ai/agent_driver.py's _disembark_pack_positions()).

Why this file exists
--------------------
Reported: "untersuche mal bitte, warum die beast snagga boys gerade den charge
move nicht durchgefuehrt haben. der wurf hat locker gereicht."
(logs/game_20260816_122550.log, 11 Beast Snagga Boyz + Beastboss off a Kill Rig
at (15,15), 2.93" gap to a Ghostkeel, 7" roll, failed at all 13 approaches.)

Diagnosed cause, and it is a SHAPE problem rather than a charge problem:

  * the legal ground for a disembark is an ANNULUS around the hull. Walking it
    ring-by-ring fills the nearest arc all the way round before touching any of
    the depth, so the unit comes out as a thin band wrapped about the transport
    - a CHAIN in coherency-graph terms;
  * measured on the reported case that chain had 5 bridge edges, the tightest
    with 0.57" of slack. Any single one of them splits the unit;
  * the charge opens with a rigid translation (_run_phase_one()), which is
    coherency-safe ONLY while every model makes the identical step. One model
    stepped over a wall by the step-over ladder's 0.8", that model was a
    bridge, the unit split, and _run_phase_one() answered by shortening the
    shared offset for everybody to 0.48". Final gap 2.44" - a charge a plain
    rigid step completes at 1.00".

User's diagnosis, which is what this file encodes: "das kernproblem ist die
ringplatzierung bei disembark. vor allem bei grossen transportern. eine
klumpenformation waere robuster im nachgang. dabei die 3" auch ausnutzen."

What is asserted
----------------
Not "the placement is legal" - it always was. The properties that actually
decide whether the NEXT move survives:

  * zero bridge edges (no single point of failure), and
  * the unit stays coherent after any one model drifts off a shared step,
    which is the exact disturbance that killed the reported charge.

Every scenario is checked BOTH ways: the new clump and a local copy of the old
ring ordering. Without the A/B a green run would only prove the scenarios are
easy, not that the change is what makes them pass.

Run: python test_disembark_clump.py
"""
import math

from game import maps, config
from game.game_state import GameState
from game.factions import build_squad
from game.factions.orks import (BEAST_SNAGGA_BOYZ, BEASTBOSS, FLASH_GITZ,
                                KILL_RIG, BOYZ, TRUKK)
from game.factions.tau_empire import GHOSTKEEL_BATTLESUIT, DEVILFISH
from game import attached_units
from game.setup import SetupController
from game.squad import edge_distance, COHERENCY_RANGE_IN, MAX_SPREAD_IN
from ai import agent_driver

BATTLE_MAP = maps.get("map2")
maps.apply_to_config(BATTLE_MAP)
_TERRAIN_SCENE = GameState()
BATTLE_MAP.build(_TERRAIN_SCENE)
OBSTACLES = [f for a in _TERRAIN_SCENE.terrain_areas for f in a.features]

DISEMBARK_DISTANCE_IN = 3.0

checks, failures = 0, []


def ok(label, cond):
    global checks
    checks += 1
    if not cond:
        failures.append(label)
    print(("  [ok  ] " if cond else "  [FAIL] ") + label)


# --------------------------------------------------------------------- board

GHOSTKEEL_AT = (5.54, 17.28)
FLASH_GITZ_AT = [(15.45, 12.14), (13.22, 11.54), (17.78, 14.19)]

# Everything that was actually standing near the Kill Rig when the reported
# disembark happened - both are needed: the Flash Gitz clamp squadmates short,
# the terrain is what the step-over ladder trips on.
REPORTED_NEIGHBOURS = [
    (FLASH_GITZ, "Player 2", FLASH_GITZ_AT),
    (GHOSTKEEL_BATTLESUIT, "Player 1", [GHOSTKEEL_AT]),
    (DEVILFISH, "Player 1", [(6.29, 21.65)]),
]

SCENARIOS = [
    # label, transport, cargo, cargo leader, transport position, neighbours
    ("reported: Kill Rig (15,15), 11 Beast Snagga",
     KILL_RIG, BEAST_SNAGGA_BOYZ, BEASTBOSS, (15.00, 15.00), REPORTED_NEIGHBOURS),
    # The four spots CLAUDE.md records for earlier disembark reports - a change
    # to this geometry must not quietly lose one of them.
    ("historic: Trukk (21.70,23.20), 10 Boyz", TRUKK, BOYZ, None, (21.70, 23.20), []),
    ("historic: Trukk corner (3,3), 10 Boyz", TRUKK, BOYZ, None, (3.00, 3.00), []),
    ("historic: Trukk mid-board (30,22), 10 Boyz", TRUKK, BOYZ, None, (30.00, 22.00), []),
    ("historic: Trukk left edge (1.5,20), 10 Boyz", TRUKK, BOYZ, None, (1.50, 20.00), []),
]


def make_scene(transport_sheet, cargo_sheet, leader_sheet, transport_xy, neighbours):
    """Real GameState/SetupController, real terrain - only the cargo is held
    back, since it is what is about to be placed."""
    state = GameState()
    transport = build_squad(transport_sheet, "Player 2", name="transport")
    transport.models[0].x_in, transport.models[0].y_in = transport_xy

    squads = [transport]
    for sheet, owner, points in neighbours:
        squad = build_squad(sheet, owner, name=f"neighbour{len(squads)}")
        squad.models = squad.models[:len(points)]
        for model, point in zip(squad.models, points):
            model.x_in, model.y_in = point
        squads.append(squad)

    state.tokens = [m for s in squads for m in s.models]
    for area in _TERRAIN_SCENE.terrain_areas:
        state.terrain_areas.append(area)

    setup = SetupController(
        game_state=state, obstacles=OBSTACLES, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    cargo = build_squad(cargo_sheet, "Player 2", name="cargo")
    if leader_sheet is not None:
        attached_units.attach(build_squad(leader_sheet, "Player 2", name="leader"), cargo)
    return state, transport.models[0], cargo, setup


# --------------------------------------------------- the OLD ring ordering
# Kept here rather than behind a flag in the engine: an A/B needs the old
# behaviour, and the engine should not carry a switch that only a test sets.

def ring_positions(squad, transport_token, max_distance_in, all_tokens,
                   angle_offset=0.0, setup_controller=None):
    """Exactly _disembark_pack_positions(), except the candidates are walked
    ring-by-ring (nearest arc first, angles ordered toward the facing) instead
    of outward from a drop point. Same slots, same per-model checks."""
    n = len(squad.models)
    smallest = min(m.radius_in for m in squad.models)
    inner = transport_token.radius_in + smallest + 0.05
    outer = transport_token.radius_in + smallest + max_distance_in
    step = max(0.35, 2 * smallest + 0.1)

    enemy_models = ([] if setup_controller.allows_engaged else [
        t for t in all_tokens if t.squad is not None and t.squad.owner != squad.owner])

    nearest = agent_driver._nearest_enemy_squad(squad, all_tokens)
    if nearest is not None:
        ncx, ncy = agent_driver._centroid(nearest)
        dx, dy = ncx - transport_token.x_in, ncy - transport_token.y_in
        dist = math.hypot(dx, dy)
        base_angle = (math.atan2(dy, dx) if dist > 1e-9 else -math.pi / 2) + angle_offset
    else:
        base_angle = -math.pi / 2 + angle_offset

    candidates = []
    radius = inner
    while radius <= outer + 1e-9:
        capacity = max(1, int((2 * math.pi * radius) / step))
        astep = 2 * math.pi / capacity
        angles = sorted((base_angle + k * astep for k in range(capacity)),
                        key=lambda a: abs((a - base_angle + math.pi) % (2 * math.pi) - math.pi))
        candidates.extend((radius,
                           transport_token.x_in + radius * math.cos(a),
                           transport_token.y_in + radius * math.sin(a)) for a in angles)
        radius += step

    order = sorted(range(n), key=lambda i: -squad.models[i].radius_in)
    chosen, placed = {}, []
    for index in order:
        model = squad.models[index]
        for (radius, x, y) in candidates:
            edge = radius - model.radius_in - transport_token.radius_in
            if edge < 0.05 or edge > max_distance_in:
                continue
            if not agent_driver._on_board(x, y, model.radius_in):
                continue
            if not setup_controller.position_valid(model, x, y, squad=squad):
                continue
            if any(math.hypot(x - e.x_in, y - e.y_in) - model.radius_in - e.radius_in
                   <= agent_driver.ENGAGEMENT_RANGE_IN for e in enemy_models):
                continue
            if any(math.hypot(x - px, y - py) < model.radius_in + pr + 0.05
                   for px, py, pr in placed):
                continue
            if placed and not any(math.hypot(x - px, y - py) <= COHERENCY_RANGE_IN + model.radius_in + pr
                                  for px, py, pr in placed):
                continue
            chosen[index] = (x, y)
            placed.append((x, y, model.radius_in))
            break
    for index in range(n):
        chosen.setdefault(index, (transport_token.x_in + outer * math.cos(base_angle),
                                  transport_token.y_in + outer * math.sin(base_angle)))
    return [chosen[i] for i in range(n)]


# ------------------------------------------------------------------ metrics

def _adjacency(squad):
    models = squad.models
    return [[j for j in range(len(models))
             if j != i and edge_distance(models[i], models[j]) <= COHERENCY_RANGE_IN]
            for i in range(len(models))]


def bridge_count(squad):
    """Coherency-graph edges whose loss splits the unit. Each one is a single
    point of failure for every later move (rule 09.02) - this is the number the
    reported charge died on. None if the unit is already disconnected."""
    adj = _adjacency(squad)
    n = len(adj)

    def connected(skip):
        seen, stack = {0}, [0]
        while stack:
            cur = stack.pop()
            for j in adj[cur]:
                if j in seen or (min(cur, j), max(cur, j)) == skip:
                    continue
                seen.add(j)
                stack.append(j)
        return len(seen) == n

    if not connected((-1, -1)):
        return None
    edges = {(min(i, j), max(i, j)) for i in range(n) for j in adj[i]}
    return sum(1 for e in edges if not connected(e))


def drift_survival(squad, drift_in):
    """Share of "one model deviates from the shared step" disturbances after
    which the unit is still coherent - the exact failure mode, swept over every
    model and eight directions."""
    models = squad.models
    base = [(m.x_in, m.y_in) for m in models]
    survived = total = 0
    for k in range(len(models)):
        for eighth in range(8):
            angle = eighth * math.pi / 4
            for model, point in zip(models, base):
                model.x_in, model.y_in = point
            models[k].x_in += drift_in * math.cos(angle)
            models[k].y_in += drift_in * math.sin(angle)
            total += 1
            if not squad.check_coherency():
                survived += 1
    for model, point in zip(models, base):
        model.x_in, model.y_in = point
    return survived / total


def place(place_fn, scenario):
    """Sweep the facings the way _place_disembarked_squad() does and report the
    first layout that would confirm, plus how many facings would."""
    _label, transport_sheet, cargo_sheet, leader_sheet, xy, neighbours = scenario
    good_facings, first = 0, None
    for offset in agent_driver._DISEMBARK_FACINGS:
        state, transport_token, cargo, setup = make_scene(
            transport_sheet, cargo_sheet, leader_sheet, xy, neighbours)
        positions = place_fn(cargo, transport_token, DISEMBARK_DISTANCE_IN,
                             state.tokens, offset, setup_controller=setup)
        for model, point in zip(cargo.models, positions):
            model.x_in, model.y_in = point
        furthest = max(edge_distance(m, transport_token) for m in cargo.models)
        legal = (not cargo.check_coherency()
                 and furthest <= DISEMBARK_DISTANCE_IN
                 and all(setup.position_valid(m, m.x_in, m.y_in, squad=cargo)
                         for m in cargo.models))
        if legal:
            good_facings += 1
            if first is None:
                first = dict(
                    squad=cargo, transport=transport_token, furthest=furthest,
                    spread=max(edge_distance(a, b) for a in cargo.models for b in cargo.models),
                    bridges=bridge_count(cargo),
                    drift08=drift_survival(cargo, 0.8),
                    drift12=drift_survival(cargo, 1.2),
                )
    return good_facings, first


# -------------------------------------------------------------------- tests

print("=" * 78)
print("1. the clump places legally everywhere the ring did")
print("=" * 78)
clump_results = {}
for scenario in SCENARIOS:
    label = scenario[0]
    facings, first = place(agent_driver._disembark_pack_positions, scenario)
    clump_results[label] = (facings, first)
    ok(f"{label}: every facing confirms ({facings}/8)", facings == len(agent_driver._DISEMBARK_FACINGS))
    if first is None:
        continue
    ok(f"{label}: every model inside the {DISEMBARK_DISTANCE_IN}\" limit "
       f"(furthest {first['furthest']:.2f}\")", first["furthest"] <= DISEMBARK_DISTANCE_IN)
    ok(f"{label}: spread {first['spread']:.2f}\" is inside rule 09.02's {MAX_SPREAD_IN}\"",
       first["spread"] <= MAX_SPREAD_IN)

print()
print("=" * 78)
print("2. no single point of failure - the property the charge needed")
print("=" * 78)
for scenario in SCENARIOS:
    label = scenario[0]
    _facings, first = clump_results[label]
    ok(f"{label}: 0 bridge edges (got {first['bridges']})", first["bridges"] == 0)

print()
print("=" * 78)
print("3. survives the disturbance that killed the reported charge")
print("=" * 78)
for scenario in SCENARIOS:
    label = scenario[0]
    _facings, first = clump_results[label]
    ok(f"{label}: coherent after a 0.8\" drift in {first['drift08']:.0%} of cases (>=95%)",
       first["drift08"] >= 0.95)
    ok(f"{label}: coherent after a 1.2\" drift in {first['drift12']:.0%} of cases (>=95%)",
       first["drift12"] >= 0.95)

print()
print("=" * 78)
print("4. A/B: the OLD ring ordering really is what those numbers came from")
print("=" * 78)
reported = SCENARIOS[0]
ring_facings, ring_first = place(ring_positions, reported)
ok("ring: the reported case still PLACES legally (it always did)",
   ring_facings == len(agent_driver._DISEMBARK_FACINGS))
ok(f"ring: but the reported case is a chain - {ring_first['bridges']} bridge edge(s), "
   "so the assertions above are not just easy scenarios",
   ring_first["bridges"] is not None and ring_first["bridges"] > 0)
ok(f"ring: and it is measurably more fragile at 1.2\" drift "
   f"({ring_first['drift12']:.0%} vs clump {clump_results[reported[0]][1]['drift12']:.0%})",
   ring_first["drift12"] < clump_results[reported[0]][1]["drift12"])

print()
print("=" * 78)
print("5. the block grows on the side it faces, away from the transport")
print("=" * 78)
# The other half of "eine klumpenformation ... dabei die 3\" auch ausnutzen":
# the transport must end up OUTSIDE the formation, not in the middle of it,
# because _run_phase_one()'s rigid step has to get past it.
state, transport_token, cargo, setup = make_scene(*SCENARIOS[0][1:])
positions = agent_driver._disembark_pack_positions(
    cargo, transport_token, DISEMBARK_DISTANCE_IN, state.tokens, 0.0, setup_controller=setup)
for model, point in zip(cargo.models, positions):
    model.x_in, model.y_in = point
cx = sum(m.x_in for m in cargo.models) / len(cargo.models)
cy = sum(m.y_in for m in cargo.models) / len(cargo.models)
offset_from_hull = math.hypot(cx - transport_token.x_in, cy - transport_token.y_in)
ok(f"the squad's centroid sits clear of the hull ({offset_from_hull:.2f}\" out, "
   f"hull radius {transport_token.radius_in:.2f}\")",
   offset_from_hull > transport_token.radius_in)
# A ring is centred ON the transport; a clump is not. This is the number that
# distinguishes them, so it is asserted rather than described.
ring_positions_out = ring_positions(cargo, transport_token, DISEMBARK_DISTANCE_IN,
                                    state.tokens, 0.0, setup_controller=setup)
rx = sum(p[0] for p in ring_positions_out) / len(ring_positions_out)
ry = sum(p[1] for p in ring_positions_out) / len(ring_positions_out)
ring_offset = math.hypot(rx - transport_token.x_in, ry - transport_token.y_in)
ok(f"and further out than the ring's centroid did ({offset_from_hull:.2f}\" vs {ring_offset:.2f}\")",
   offset_from_hull > ring_offset)

print()
print("=" * 78)
print(f"passed {checks - len(failures)}, failed {len(failures)}")
for f in failures:
    print("  FAIL:", f)
raise SystemExit(1 if failures else 0)
