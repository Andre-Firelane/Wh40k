"""Isolated tests for the pre-game deployment sequence (rule 03.01).

Real controller objects throughout - SetupController, DiceManager,
DecisionManager, TurnTracker, GameState and real datasheets via
game.factions.build_squad - per this project's testing convention. No pygame
display, no API calls.

Run: python test_pregame.py
"""

import random
import sys

from game import config, deployment, formations, maps, pregame
from game.decision import DecisionManager
from game.deployment import DeploymentZone
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BOYZ, DEFF_DREAD, GRETCHIN, STORMBOYZ, TRUKK, WARBIKERS
from game.factions.tau_empire import (
    BREACHER_TEAM,
    DEVILFISH,
    GHOSTKEEL_BATTLESUIT,
    KROOT_CARNIVORES,
    STEALTH_BATTLESUITS,
    STRIKE_TEAM,
)
from game.game_state import GameState
from game.setup import SetupController
from game.squad import squad_has_infiltrators
from game.turn import TurnTracker

PASS, FAIL = [], []


def check(label, condition, detail=""):
    (PASS if condition else FAIL).append(label)
    mark = "ok  " if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f"  -- {detail}" if detail else ""))


def section(title):
    print(f"\n=== {title} ===")


# --------------------------------------------------------------------------
# 1. DeploymentZone geometry
# --------------------------------------------------------------------------
def test_zone_geometry():
    section("DeploymentZone geometry")
    # Map 2 Player 1 zone: center (30, 38), 60 x 12  ->  y in [32, 44]
    zone = DeploymentZone("Player 1", [(30.0, 38.0, 60.0, 12.0)])

    check("contains_point centre", zone.contains_point(30.0, 38.0))
    check("contains_point outside", not zone.contains_point(30.0, 20.0))

    check("contains_circle well inside", zone.contains_circle(30.0, 38.0, 1.0))
    check(
        "contains_circle centre inside but base crossing the edge is REJECTED",
        not zone.contains_circle(30.0, 32.4, 1.0),
        "y=32.4 r=1.0 reaches 31.4, zone starts at 32.0",
    )
    check("contains_circle exactly flush", zone.contains_circle(30.0, 33.0, 1.0))
    check("contains_circle zero radius == contains_point", zone.contains_circle(30.0, 32.0, 0.0))

    check("distance_to_point inside is 0", zone.distance_to_point(30.0, 38.0) == 0.0)
    d = zone.distance_to_point(30.0, 22.0)
    check("distance_to_point straight out", abs(d - 10.0) < 1e-9, f"{d:.3f} (32.0 - 22.0)")
    dc = zone.distance_to_point(-10.0, 22.0)  # diagonal past the corner
    expected = ((0.0 - (-10.0)) ** 2 + (32.0 - 22.0) ** 2) ** 0.5
    check("distance_to_point diagonal past a corner", abs(dc - expected) < 1e-9, f"{dc:.3f}")

    zones = [DeploymentZone("Player 1", [(30.0, 38.0, 60.0, 12.0)]),
             DeploymentZone("Player 2", [(30.0, 6.0, 60.0, 12.0)])]
    check("zone_for finds own", deployment.zone_for(zones, "Player 1").owner == "Player 1")
    check("zone_for unknown owner -> None", deployment.zone_for(zones, "Player 9") is None)
    check("enemy_zones excludes own", [z.owner for z in deployment.enemy_zones(zones, "Player 1")] == ["Player 2"])
    check("enemy_zones on empty list", deployment.enemy_zones((), "Player 1") == [])

    # Both real maps, both zones, a model on the inner edge.
    for key in ("map1", "map2"):
        bm = maps.get(key)
        for owner, rects in bm.zones:
            z = DeploymentZone(owner, rects)
            cx, cy, w, h = rects[0]
            check(f"{key} {owner}: zone centre holds a 1.18\" base", z.contains_circle(cx, cy, 1.18))
            check(f"{key} {owner}: 0.1\" outside the far edge is rejected",
                  not z.contains_circle(cx, cy + h / 2 + 0.1, 0.5))


# --------------------------------------------------------------------------
# 2. Battle formations legality
# --------------------------------------------------------------------------
def test_formations():
    section("Declare Battle Formations legality (18.01 / 20.01)")
    devilfish = build_squad(DEVILFISH, "Player 1", name="Devilfish", x_in=10, y_in=10)
    devilfish_token = devilfish.models[0]
    breachers = build_squad(BREACHER_TEAM, "Player 1", name="Breachers")
    kroot = build_squad(KROOT_CARNIVORES, "Player 1", name="Kroot")
    ghostkeel = build_squad(GHOSTKEEL_BATTLESUIT, "Player 1", name="Ghostkeel")

    check("Breachers may embark in a Devilfish", formations.embark_errors(breachers, devilfish_token) == [])
    kroot_errors = formations.embark_errors(kroot, devilfish_token)
    check("Kroot are excluded from a Devilfish", kroot_errors != [], "; ".join(kroot_errors))
    gk_errors = formations.embark_errors(ghostkeel, devilfish_token)
    check("Ghostkeel (BATTLESUIT, not INFANTRY) excluded", gk_errors != [], "; ".join(gk_errors))

    trukk = build_squad(TRUKK, "Player 2", name="Trukk", x_in=10, y_in=10)
    trukk_token = trukk.models[0]
    boyz = build_squad(BOYZ, "Player 2", name="Boyz")
    check("Boyz fit in a Trukk", formations.embark_errors(boyz, trukk_token) == [])
    boyz2 = build_squad(BOYZ, "Player 2", name="Boyz 2")
    over = formations.embark_errors(boyz2, trukk_token, already_assigned=[boyz])
    check("A second Boyz mob overflows the Trukk", over != [], "; ".join(over))

    # MEGA ARMOUR costs 2 (rule 18.01) - proven by comparing the cost of the
    # same model count with and without the flag.
    from game.factions.orks import MEGANOBZ
    meganobz = build_squad(MEGANOBZ, "Player 2", name="Meganobz")
    cost = formations.transport_capacity_used(trukk_token, [meganobz])
    check("MEGA ARMOUR models cost 2 capacity each",
          cost == 2 * len(meganobz.models), f"{cost} for {len(meganobz.models)} models")

    check("A TRANSPORT cannot embark within another", formations.embark_errors(trukk, trukk_token) != [])

    # Reserve limits (20.01)
    class _U:
        def __init__(self, name, points):
            self.name, self.points = name, points

    army = [_U(f"u{i}", 100) for i in range(6)]
    check("3 of 6 units in reserve is legal", formations.reserve_limit_errors(army, army[:3]) == [])
    errs = formations.reserve_limit_errors(army, army[:4])
    check("4 of 6 units in reserve is refused", any("half your units" in e for e in errs), "; ".join(errs))

    skewed = [_U("cheap", 10), _U("cheap2", 10), _U("expensive", 500), _U("cheap3", 10)]
    errs = formations.reserve_limit_errors(skewed, [skewed[2]])
    check("1 of 4 units but >half the points is refused",
          any("points" in e for e in errs), "; ".join(errs))

    unpriced = [_U("a", None), _U("b", 100), _U("c", 100), _U("d", 100)]
    errs = formations.reserve_limit_errors(unpriced, [unpriced[1]])
    check("an unpriced unit skips the points half entirely", errs == [], "; ".join(errs))

    check("can_add_to_reserves says no at the cap",
          not formations.can_add_to_reserves(army[3], army, army[:3]))
    check("can_add_to_reserves says yes below it",
          formations.can_add_to_reserves(army[2], army, army[:2]))


# --------------------------------------------------------------------------
# 3. RollOff, including the tie loop
# --------------------------------------------------------------------------
def test_rolloff():
    section("Roll-off (03.01) incl. tie re-rolls")
    dice = DiceManager()
    resolved = []
    ro = pregame.RollOff(dice, ("Player 1", "Player 2"), "Test roll-off",
                         on_resolved=resolved.append)

    scripted = [3, 3, 5, 5, 6, 2]  # two ties, then P1 wins
    original = random.randint
    random.randint = lambda a, b: scripted.pop(0) if scripted else original(a, b)
    try:
        ro.start()
        guard = 0
        while ro.active and guard < 50:
            guard += 1
            dice.acknowledge()
            ro.on_dice_acknowledged()
    finally:
        random.randint = original

    check("a tie re-rolls until it resolves", resolved == ["Player 1"], f"{resolved}")
    check("the tie loop consumed all three rounds", not scripted, f"left: {scripted}")
    check("rolloff records both results", set(ro.results) == {"Player 1", "Player 2"})

    # Liveness cap
    dice2 = DiceManager()
    resolved2 = []
    ro2 = pregame.RollOff(dice2, ("Player 1", "Player 2"), "Endless",
                          on_resolved=resolved2.append)
    random.randint = lambda a, b: 4  # permanent tie
    try:
        ro2.start()
        guard = 0
        while ro2.active and guard < 500:
            guard += 1
            dice2.acknowledge()
            ro2.on_dice_acknowledged()
    finally:
        random.randint = original
    check("a permanent tie is stopped by the liveness cap", not ro2.active and resolved2 != [],
          f"attempts={ro2._attempts}, winner={resolved2}")

    # roll_kind stays None so Command Re-roll (15.02) cannot target a roll-off
    dice3 = DiceManager()
    ro3 = pregame.RollOff(dice3, ("Player 1", "Player 2"), "Kind check")
    ro3.start()
    check("roll_kind is None (not Command Re-rollable)", dice3.roll_kind is None)


# --------------------------------------------------------------------------
# 4. TurnTracker deferred start
# --------------------------------------------------------------------------
def test_turn_tracker():
    section("TurnTracker deferred start")
    lines = []

    class _Log:
        def add(self, message, file_only=False):
            lines.append(message)

    tt = TurnTracker(game_log=_Log(), deferred_start=True)
    check("deferred tracker is not started", not tt.started)
    check("deferred tracker sits at battle round 0", tt.battle_round == 0)
    check("deferred tracker logs nothing up front", lines == [], f"{lines}")

    tt.start_battle("Player 2")
    check("start_battle sets the first player", tt.first_player == "Player 2")
    check("start_battle sets turn_owner", tt.turn_owner == "Player 2")
    check("start_battle sets active_player", tt.active_player == "Player 2")
    check("start_battle moves to round 1", tt.battle_round == 1)
    check("start_battle resets the phase", tt.phase == "Command")
    check("start_battle counts the first turn", tt.turn_number_for("Player 2") == 1)
    check("start_battle logs the two opening lines", len(lines) == 2, f"{lines}")

    before = list(lines)
    tt.start_battle("Player 1")
    check("start_battle is refused once started",
          tt.first_player == "Player 2" and lines == before)

    normal = TurnTracker(game_log=_Log())
    check("a normal tracker still starts immediately",
          normal.started and normal.battle_round == 1 and normal.turn_owner == "Player 1")

    # Ingress is dead during the pre-game with no extra check anywhere.
    from game.ingress import INGRESS_MIN_BATTLE_ROUND
    check("battle_round 0 < INGRESS_MIN_BATTLE_ROUND blocks Ingress for free",
          0 < INGRESS_MIN_BATTLE_ROUND)


# --------------------------------------------------------------------------
# 5. The full sequence against a real map
# --------------------------------------------------------------------------
def _build_scene(map_key="map2"):
    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    setup = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    dice = DiceManager()
    decisions = DecisionManager()
    tt = TurnTracker(deferred_start=True)
    started = []
    ctrl = pregame.PregameController(
        state, setup, dice, decisions, turn_tracker=tt,
        on_battle_start=lambda p: (tt.start_battle(p), started.append(p)),
    )
    return battle_map, state, setup, dice, decisions, tt, ctrl, started


def _p1_army():
    return [
        build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1"),
        build_squad(KROOT_CARNIVORES, "Player 1", name="1 Kroot Carnivores 1"),
        build_squad(GHOSTKEEL_BATTLESUIT, "Player 1", name="1 Ghostkeel 1"),
        build_squad(STEALTH_BATTLESUITS, "Player 1", name="1 Stealth Battlesuits 1"),
    ]


def _p2_army():
    return [
        build_squad(GRETCHIN, "Player 2", name="2 Gretchin 1"),
        build_squad(BOYZ, "Player 2", name="2 Boyz 1"),
        build_squad(STORMBOYZ, "Player 2", name="2 Stormboyz 1"),
        build_squad(DEFF_DREAD, "Player 2", name="2 Deff Dread 1"),
    ]


def _drain_dice(ctrl, dice, limit=200):
    guard = 0
    while dice.is_pending and guard < limit:
        guard += 1
        dice.acknowledge()
        ctrl.on_dice_acknowledged()


def _auto_place(ctrl, setup, squad, zone):
    """Place a squad in a compact block inside its zone. Deliberately dumb -
    this test is about the SEQUENCE, not about placement quality (that is
    ai/agent_driver.py's _auto_deploy_squad and its own tests).

    A block rather than a line because rule 09.02 caps a unit at 9" between
    any two models, which a 10-model line at 1.6" spacing already breaks."""
    cx, cy, w, h = zone.rects[0]
    per_row = 4
    step = 1.6
    for attempt in range(400):
        ox = cx - w / 2 + 3.0 + (attempt % 25) * (w - 6.0) / 25.0
        oy = cy - h / 2 + 2.0 + (attempt // 25) * 1.7
        if not ctrl.start_deployment(squad, ox, oy):
            return False
        for i, model in enumerate(squad.models):
            model.x_in, model.y_in = setup.clamp_position(
                model, ox + (i % per_row) * step, oy + (i // per_row) * step
            )
        if ctrl.confirm_deployment():
            return True
        ctrl.cancel_deployment()
    return False


def test_full_sequence():
    section("Full pre-game sequence (map2)")
    battle_map, state, setup, dice, decisions, tt, ctrl, started = _build_scene("map2")
    p1, p2 = _p1_army(), _p2_army()
    ctrl.start({"Player 1": p1, "Player 2": p2})

    check("starts in FORMATIONS", ctrl.state == pregame.FORMATIONS)
    check("nothing is on the battlefield yet", state.tokens == [])

    # Player 1 declares one unit into reserves, the rest deploy.
    ctrl.declare(p1[3], pregame.RESERVES)
    ctrl.finish_formations_for("Player 1")
    ctrl.finish_formations_for("Player 2")

    check("the reserved unit is in game_state.reserves", p1[3] in state.reserves)
    check("P1 has 3 units to place", len(ctrl.pending_units("Player 1")) == 3)
    check("P2 has 4 units to place", len(ctrl.pending_units("Player 2")) == 4)
    check("formations rolls straight into the deployment roll-off",
          ctrl.state == pregame.DEPLOY_ROLLOFF)
    check("a die is on the table", dice.is_pending)

    _drain_dice(ctrl, dice)
    check("roll-off resolved", ctrl.rolloff.winner is not None, f"winner={ctrl.rolloff.winner}")

    if decisions.is_pending:
        decisions.choose(0)  # human won: "I place first"
    check("now DEPLOYING", ctrl.state == pregame.DEPLOYING, f"state={ctrl.state}")

    zones = {z.owner: z for z in state.deployment_zones}
    order = []
    guard = 0
    while ctrl.state == pregame.DEPLOYING and guard < 40:
        guard += 1
        owner = ctrl.active_player
        pending = ctrl.pending_units(owner)
        if not pending:
            break
        squad = pending[0]
        order.append(owner)
        if not _auto_place(ctrl, setup, squad, zones[owner]):
            check(f"could place {squad.name}", False, "no legal spot found by the dumb placer")
            return

    check("every unit got placed", not ctrl.pending_units(), f"{[s.name for s in ctrl.pending_units()]}")
    check("deployment alternated", order[:4] == [order[0], ctrl._other(order[0])] * 2, f"{order}")
    check("the side with more units drained the rest at the end",
          order[-1] == "Player 2", f"{order}")

    _drain_dice(ctrl, dice)
    check("battle started", ctrl.state == pregame.DONE and started, f"state={ctrl.state}")
    check("first player was decided by the roll-off",
          started and started[0] in ("Player 1", "Player 2"), f"{started}")
    check("TurnTracker is now running", tt.started and tt.battle_round == 1)
    check("the first player owns the turn", tt.turn_owner == started[0])

    on_board = {t.squad for t in state.tokens}
    check("7 units on the battlefield", len(on_board) == 7, f"{len(on_board)}")
    for squad in p1 + p2:
        placed = squad in on_board
        reserved = squad in state.reserves
        embarked = squad in state.embarked_squads
        if not (placed or reserved or embarked):
            check(f"{squad.name} accounted for", False, "vanished")
            return
    check("no unit was lost between the lists", True)

    for squad in p1 + p2:
        if squad in on_board:
            zone = zones[squad.owner]
            inside = all(zone.contains_circle(m.x_in, m.y_in, m.radius_in) for m in squad.models)
            if not inside:
                check(f"{squad.name} is wholly within its zone", False)
                return
    check("every deployed unit is wholly within its own zone", True)
    check("no deployed unit broke coherency",
          all(not s.check_coherency() for s in on_board))
    return ctrl, state, setup, p1, p2


# --------------------------------------------------------------------------
# 6. Zone enforcement + INFILTRATORS predicate
# --------------------------------------------------------------------------
def test_placement_predicate():
    section("Placement predicate: zone (03.01) and INFILTRATORS (24.20)")
    battle_map, state, setup, dice, decisions, tt, ctrl, started = _build_scene("map2")
    strike = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
    stealth = build_squad(STEALTH_BATTLESUITS, "Player 1", name="1 Stealth Battlesuits 1")
    boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    ctrl.start({"Player 1": [strike, stealth], "Player 2": [boyz]})

    check("Stealth Battlesuits have INFILTRATORS", squad_has_infiltrators(stealth))
    check("Strike Team does not", not squad_has_infiltrators(strike))

    p1_zone = deployment.zone_for(state.deployment_zones, "Player 1")
    cx, cy, w, h = p1_zone.rects[0]
    token = strike.models[0]

    check("a normal unit may stand in its own zone",
          ctrl.position_valid(strike, token, cx, cy))
    check("a normal unit may NOT stand in no man's land",
          not ctrl.position_valid(strike, token, cx, config.BOARD_HEIGHT_IN / 2))
    check("a normal unit may NOT stand in the enemy zone",
          not ctrl.position_valid(strike, token, cx, 6.0))

    itoken = stealth.models[0]
    p2_zone = deployment.zone_for(state.deployment_zones, "Player 2")
    edge = p2_zone.rects[0][1] + p2_zone.rects[0][3] / 2  # y=12 on map2
    check("INFILTRATORS: 4\" from the enemy zone is refused",
          not ctrl.position_valid(stealth, itoken, cx, edge + 4.0))
    far_y = edge + INFILTRATORS_TEST_MARGIN
    check("INFILTRATORS: >8\" from the enemy zone is allowed",
          ctrl.position_valid(stealth, itoken, cx, far_y), f"y={far_y}")
    check("INFILTRATORS may stand OUTSIDE its own deployment zone",
          not p1_zone.contains_circle(cx, far_y, itoken.radius_in))

    # ...and must still clear enemy MODELS by 8".
    for i, model in enumerate(boyz.models):
        model.x_in, model.y_in = cx + i * 1.2, far_y + 2.0
        state.add_token(model)
    check("INFILTRATORS: blocked by an enemy unit 2\" away",
          not ctrl.position_valid(stealth, itoken, cx, far_y))
    for model in boyz.models:
        model.x_in, model.y_in = cx + 100, far_y  # far off
    check("INFILTRATORS: allowed again once the enemy is far away",
          ctrl.position_valid(stealth, itoken, cx, far_y))

    # A/B counter-proof: with the INFILTRATORS branch disabled, the spot
    # outside the zone must be rejected - i.e. these tests exercise 24.20 and
    # not something else.
    original = pregame.squad_has_infiltrators
    pregame.squad_has_infiltrators = lambda s: False
    try:
        check("A/B: without the 24.20 branch the same spot is refused",
              not ctrl.position_valid(stealth, itoken, cx, far_y))
    finally:
        pregame.squad_has_infiltrators = original


INFILTRATORS_TEST_MARGIN = 10.0  # comfortably beyond the 8" limit


# --------------------------------------------------------------------------
# 7. set_up_this_turn must not leak into battle round 1
# --------------------------------------------------------------------------
def test_set_up_this_turn():
    section("set_up_this_turn does not leak into round 1")
    battle_map, state, setup, dice, decisions, tt, ctrl, started = _build_scene("map2")
    strike = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
    boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")

    cleared = []

    def begin_battle(first_player):
        # exactly what main.py's begin_battle() must do
        for squad in (strike, boyz):
            squad.set_up_this_turn = False
        cleared.append(first_player)
        tt.start_battle(first_player)

    ctrl.on_battle_start = begin_battle
    ctrl.start({"Player 1": [strike], "Player 2": [boyz]})
    ctrl.finish_formations_for("Player 1")
    ctrl.finish_formations_for("Player 2")
    _drain_dice(ctrl, dice)
    if decisions.is_pending:
        decisions.choose(0)

    zones = {z.owner: z for z in state.deployment_zones}
    guard = 0
    while ctrl.state == pregame.DEPLOYING and guard < 10:
        guard += 1
        owner = ctrl.active_player
        pending = ctrl.pending_units(owner)
        if not pending:
            break
        _auto_place(ctrl, setup, pending[0], zones[owner])

    check("both units were set up (so the flag was set)",
          strike.models[0] in state.tokens and boyz.models[0] in state.tokens)
    _drain_dice(ctrl, dice)
    check("battle started", cleared, f"{cleared}")
    check("set_up_this_turn cleared on every unit",
          not strike.set_up_this_turn and not boyz.set_up_this_turn,
          "rule 18.02 would block embarking and 24.16 would strip [HEAVY] otherwise")


# --------------------------------------------------------------------------
# 8. SCOUTS 24.31 / SCOUT MOVE 24.32
# --------------------------------------------------------------------------
def test_scouts():
    section("SCOUTS 24.31 / SCOUT MOVE 24.32")
    from ai import deployment_ai
    from game import movement as movement_module
    from game import scouts
    from game.movement import MovementController

    kroot = build_squad(KROOT_CARNIVORES, "Player 2", name="2 Kroot Carnivores 1")
    boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    check("Kroot Carnivores have Scouts 7\"", scouts.scout_distance(kroot) == 7.0)
    check("Boyz have no Scouts", scouts.scout_distance(boyz) is None)
    check("has_scouts agrees", scouts.has_scouts(kroot) and not scouts.has_scouts(boyz))

    battle_map, state, setup, dice, decisions, tt, ctrl, started = _build_scene("map2")
    p2_zone = deployment.zone_for(state.deployment_zones, "Player 2")
    cx, cy, w, h = p2_zone.rects[0]

    # Kroot wholly inside their own zone -> the scout-move branch.
    for i, model in enumerate(kroot.models):
        model.x_in, model.y_in = cx - 6 + (i % 5) * 1.6, cy + (i // 5) * 1.6
        state.add_token(model)
    ctrl.start({"Player 1": [], "Player 2": [kroot]})
    eligible = scouts.eligible_units(ctrl, "Player 2")
    check("a unit wholly within its own zone gets the scout_move branch",
          eligible and eligible[0][1] == "scout_move", f"{[(s.name, b) for s, b in eligible]}")

    # ...and NOT once it is outside the zone.
    saved = [(m.x_in, m.y_in) for m in kroot.models]
    for model in kroot.models:
        model.y_in = config.BOARD_HEIGHT_IN / 2
    check("a unit outside its own zone gets no option at all",
          scouts.eligible_units(ctrl, "Player 2") == [])
    for model, (x, y) in zip(kroot.models, saved):
        model.x_in, model.y_in = x, y

    # The real move, aimed at an objective, with an enemy far away.
    enemy = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
    for i, model in enumerate(enemy.models):
        model.x_in, model.y_in = 5.0 + i * 1.6, config.BOARD_HEIGHT_IN - 4.0
        state.add_token(model)

    mc = MovementController(
        state.obstacles, all_tokens=state.tokens, turn_tracker=tt,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    before = (sum(m.x_in for m in kroot.models) / len(kroot.models),
              sum(m.y_in for m in kroot.models) / len(kroot.models))
    moved = deployment_ai.resolve_scouts(
        ctrl, kroot, "scout_move", 7.0, movement_controller=mc,
        objectives=state.objectives,
    )
    after = (sum(m.x_in for m in kroot.models) / len(kroot.models),
             sum(m.y_in for m in kroot.models) / len(kroot.models))
    travelled = ((after[0] - before[0]) ** 2 + (after[1] - before[1]) ** 2) ** 0.5
    check("the AI takes its scout move", moved, f"{before} -> {after}")
    check("it travels no further than Scouts 7\"", travelled <= 7.0 + 1e-6, f"{travelled:.2f}\"")
    check("it actually moved", travelled > 0.5, f"{travelled:.2f}\"")
    check("coherency survives the scout move", not kroot.check_coherency())
    check("it ends >8\" from all enemy units",
          not kroot.check_scout_move_clearance(state.tokens))

    # The bug the plan flagged: a scout move must NOT count as this turn's move.
    check("a scout move does not consume the Movement-phase move (09.02)",
          kroot not in mc.moved_squad_ids)
    check("a scout move does not record >3\" travel (keeps [HEAVY], 24.16)",
          mc.moved_distance_this_turn.get(id(kroot), 0) == 0
          or kroot not in mc.moved_squad_ids)

    # ...and the after-move condition is really enforced: put an enemy right in
    # front of the objective the Kroot are heading for.
    for model, (x, y) in zip(kroot.models, saved):
        model.x_in, model.y_in = x, y
    for i, model in enumerate(enemy.models):
        model.x_in, model.y_in = before[0] + (i % 5) * 1.6, before[1] + 3.0
    blocked = deployment_ai.resolve_scouts(
        ctrl, kroot, "scout_move", 7.0, movement_controller=mc,
        objectives=state.objectives,
    )
    ended = [(m.x_in, m.y_in) for m in kroot.models]
    check("a scout move into an enemy's 8\" bubble is refused or shortened",
          (not blocked) or not kroot.check_scout_move_clearance(state.tokens),
          f"moved={blocked}")
    check("a refused scout move leaves the unit where it started",
          blocked or ended == saved)

    # A DEEP STRIKE reserve unit keeps its reserve arrival rather than
    # redeploying (24.09 beats 24.31's first branch).
    from game.factions.orks import DEFFKOPTAS
    koptas = build_squad(DEFFKOPTAS, "Player 2", name="2 Deffkoptas 1")
    state.add_reserve_squad(koptas)
    took = deployment_ai.resolve_scouts(ctrl, koptas, "reserve_redeploy", 7.0)
    check("a [DEEP STRIKE] unit does not redeploy out of reserves",
          not took and koptas in state.reserves)

    # A human-owned unit is never touched by the AI resolver.
    human_kroot = build_squad(KROOT_CARNIVORES, "Player 1", name="1 Kroot Carnivores 1")
    check("the AI leaves a human unit's Scouts option alone",
          not deployment_ai.resolve_scouts(
              ctrl, human_kroot, "scout_move", 7.0, movement_controller=mc,
              objectives=state.objectives,
          ))

    check("the DEDICATED TRANSPORT branch reports empty (unreachable today)",
          scouts.eligible_transports_for_scout_move(ctrl, "Player 2") == [])


def main():
    test_zone_geometry()
    test_formations()
    test_rolloff()
    test_turn_tracker()
    test_full_sequence()
    test_placement_predicate()
    test_set_up_this_turn()
    test_scouts()

    print(f"\n{'=' * 60}")
    print(f"passed {len(PASS)}, failed {len(FAIL)}")
    for name in FAIL:
        print(f"  FAILED: {name}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

