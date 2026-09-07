"""Isolated tests for the pre-game deployment sequence (rule 03.01).

Real controller objects throughout - SetupController, DiceManager,
DecisionManager, TurnTracker, GameState and real datasheets via
game.factions.build_squad - per this project's testing convention. No pygame
display, no API calls.

Run: python test_pregame.py
"""

import io
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
from game.terrain import DENSE
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
# 6b. The deployment overlay deliberately does not paint model overlap
# --------------------------------------------------------------------------
def test_overlay_hides_model_overlap():
    section("Deployment overlay: the other-models term is not painted")
    battle_map, state, setup, dice, decisions, tt, ctrl, started = _build_scene("map2")
    strike = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
    kroot = build_squad(KROOT_CARNIVORES, "Player 1", name="1 Kroot Carnivores 1")
    stealth = build_squad(STEALTH_BATTLESUITS, "Player 1", name="1 Stealth Battlesuits 1")
    boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    ctrl.start({"Player 1": [strike, kroot, stealth], "Player 2": [boyz]})

    p1_zone = deployment.zone_for(state.deployment_zones, "Player 1")
    cx, cy, w, h = p1_zone.rects[0]

    # A friendly model already standing in the middle of the zone - exactly
    # the "roter Bereich um meine Einheiten" the user pointed at.
    neighbour = kroot.models[0]
    neighbour.x_in, neighbour.y_in = cx, cy
    state.add_token(neighbour)

    token = strike.models[0]
    forbidden_r = token.radius_in + neighbour.radius_in

    check("the RULE still refuses a spot on top of another model",
          not ctrl.position_valid(strike, token, cx, cy))
    check("the OVERLAY paints that same spot as legal",
          ctrl.overlay_position_valid(strike, token, cx, cy))
    just_outside = cx + forbidden_r + 0.01
    check("both agree once the bases no longer touch",
          ctrl.position_valid(strike, token, just_outside, cy)
          and ctrl.overlay_position_valid(strike, token, just_outside, cy),
          f"{forbidden_r:.3f} = {token.radius_in:.3f} + {neighbour.radius_in:.3f}")

    # The rule's own boundary is unchanged - it only stops being DRAWN.
    lo, hi = 0.0, 5.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if ctrl.position_valid(strike, token, cx + mid, cy):
            hi = mid
        else:
            lo = mid
    check("the enforced exclusion radius is still base+base",
          abs(hi - forbidden_r) < 1e-3, f"{hi:.3f} vs {forbidden_r:.3f}")
    check("the overlay has no exclusion around it at all",
          all(ctrl.overlay_position_valid(strike, token, cx + d, cy)
              for d in (0.0, 0.25, 0.5, forbidden_r / 2, forbidden_r - 0.01)))

    # Everything the overlay still HAS to paint - the invisible half.
    check("overlay still refuses the enemy deployment zone",
          not ctrl.overlay_position_valid(strike, token, cx, 6.0))
    check("overlay still refuses no man's land",
          not ctrl.overlay_position_valid(strike, token, cx, config.BOARD_HEIGHT_IN / 2))
    check("overlay still refuses off the board edge",
          not ctrl.overlay_position_valid(strike, token, 0.1, cy))

    dense = [o for o in state.obstacles
             if o.category == DENSE
             and p1_zone.contains_point((o.min_x + o.max_x) / 2, (o.min_y + o.max_y) / 2)]
    check("map2 has Dense terrain inside Player 1's zone to test against", bool(dense))
    if dense:
        wall = dense[0]
        wx, wy = (wall.min_x + wall.max_x) / 2, (wall.min_y + wall.max_y) / 2
        check("overlay still refuses Dense terrain (13.05)",
              not ctrl.overlay_position_valid(strike, token, wx, wy),
              f"wall at ({wx:.1f},{wy:.1f})")
        clear_y = wy + wall.height_in / 2 + token.radius_in + 1.0
        check("...and allows clear ground next to it, so that was terrain not the zone",
              ctrl.overlay_position_valid(strike, token, wx, clear_y))

    # 24.20's two bubbles are NOT the overlap term and must survive.
    itoken = stealth.models[0]
    p2_zone = deployment.zone_for(state.deployment_zones, "Player 2")
    edge = p2_zone.rects[0][1] + p2_zone.rects[0][3] / 2
    check("overlay still refuses INFILTRATORS 4in from the enemy zone",
          not ctrl.overlay_position_valid(stealth, itoken, cx, edge + 4.0))
    far_y = edge + INFILTRATORS_TEST_MARGIN
    check("overlay allows INFILTRATORS beyond the 8in line",
          ctrl.overlay_position_valid(stealth, itoken, cx, far_y))
    for i, model in enumerate(boyz.models):
        model.x_in, model.y_in = cx + i * 1.2, far_y + 2.0
        state.add_token(model)
    check("overlay still paints the 8in bubble around ENEMY MODELS (24.20)",
          not ctrl.overlay_position_valid(stealth, itoken, cx, far_y))
    for model in boyz.models:
        state.tokens.remove(model)

    # ...and the rule is still enforced twice over, so nothing illegal can be
    # committed just because it is no longer painted. Driven through
    # SetupController directly with the validator start_deployment() hands it,
    # so the check does not depend on which side wins the roll-off.
    setup.start_setup(
        strike, cx + 8.0, cy, on_cancel=lambda squad: None,
        extra_check=ctrl._extra_check,
        placement_validator=lambda token, x, y: ctrl.position_valid(strike, token, x, y),
    )
    dragged = setup.setting_up_squad.models[0]
    landed_x, landed_y = setup.clamp_drag(dragged, cx, cy)
    gap = ((landed_x - cx) ** 2 + (landed_y - cy) ** 2) ** 0.5
    check("clamp_drag still refuses to drop a model onto its neighbour",
          gap >= forbidden_r - 0.2, f"landed {gap:.2f} away, needs {forbidden_r:.2f}")
    for model in setup.setting_up_squad.models:
        model.x_in, model.y_in = cx, cy
    setup.confirm_setup()
    check("confirm_setup still rejects an overlapping placement",
          setup.setting_up_squad is strike and setup.errors != [],
          "; ".join(setup.errors))
    setup.cancel_setup()


# --------------------------------------------------------------------------
# 6c. Wiring: main.py must actually use the overlay predicate
# --------------------------------------------------------------------------
def test_overlay_wiring():
    section("Wiring: main.py routes the deployment overlay through it")
    source = io.open("main.py", encoding="utf-8").read()

    check("main.py calls overlay_position_valid",
          "pregame_controller.overlay_position_valid(" in source)
    deploy_branch = source.find("elif pregame_controller.is_deploying(placement_squad):")
    generic_branch = source.find("elif placement_squad is setup_controller.setting_up_squad:")
    check("the deployment branch exists", deploy_branch != -1)
    check("it is tested BEFORE the generic PLACING branch it specialises",
          deploy_branch != -1 and generic_branch != -1 and deploy_branch < generic_branch,
          f"deploy at {deploy_branch}, generic at {generic_branch}")

    # The relaxation is for DRAWING only: everything that decides whether a
    # placement may stand keeps the full predicate.
    ai_source = io.open("ai/deployment_ai.py", encoding="utf-8").read()
    check("the AI's placer still probes the strict predicate",
          "pregame_ctrl.position_valid(squad, model, px, py)" in ai_source
          and "overlay_position_valid" not in ai_source)
    setup_source = io.open("game/setup.py", encoding="utf-8").read()
    check("clamp_drag/apply_group_drag/arrange_as_block go through placement_validator()",
          setup_source.count("valid = self.placement_validator(") == 3,
          f"found {setup_source.count('valid = self.placement_validator(')}")
    check("no ingress/disembark path opts into the relaxation",
          "ignore_model_overlap" not in io.open("game/ingress.py", encoding="utf-8").read()
          and "ignore_model_overlap" not in io.open("game/transport.py", encoding="utf-8").read())



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
    # ai_players PASSED EXPLICITLY. Its default used to be ("Player 2",) and
    # is now (), so a caller that forgets it resolves nothing - which is the
    # point of the flip: forgetting is now a loud no-op instead of the AI
    # silently taking a human's move. Every call in this block names it, and
    # the human-unit check below would otherwise pass for the wrong reason.
    moved = deployment_ai.resolve_scouts(
        ctrl, kroot, "scout_move", 7.0, movement_controller=mc,
        objectives=state.objectives, ai_players=("Player 2",),
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
        objectives=state.objectives, ai_players=("Player 2",),
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
    took = deployment_ai.resolve_scouts(ctrl, koptas, "reserve_redeploy", 7.0,
                                       ai_players=("Player 2",))
    check("a [DEEP STRIKE] unit does not redeploy out of reserves",
          not took and koptas in state.reserves)

    # A human-owned unit is never touched by the AI resolver.
    human_kroot = build_squad(KROOT_CARNIVORES, "Player 1", name="1 Kroot Carnivores 1")
    check("the AI leaves a human unit's Scouts option alone",
          not deployment_ai.resolve_scouts(
              ctrl, human_kroot, "scout_move", 7.0, movement_controller=mc,
              objectives=state.objectives, ai_players=("Player 2",),
          ))

    check("the DEDICATED TRANSPORT branch reports empty (unreachable today)",
          scouts.eligible_transports_for_scout_move(ctrl, "Player 2") == [])


def test_hotseat_formations():
    """AI MODE OFF: both armies are declared at one keyboard.

    Reported: "und ausserdem geht es ohne angeschalteten KI-Modus direkt vor
    beginn der aufstellung nicht weiter. es gibt keinen knopf mit dem man den
    roll fuer attacker/defender ausloesen koennte."

    The roll-off was never the problem - it opens by itself once BOTH owners
    have declared. What could not happen was Player 2's declaration:
    PregameController was built with the default human_player "Player 1"
    (main() never passed it one), and the panel offered that owner's units and
    nobody else's. So the step sat on "Waiting for your opponent..." for an
    opponent who, with the AI switched off, was the person holding the mouse.
    """
    section("Hotseat: both armies declared by hand")
    # This suite runs headless without pygame imported at all; the panel half
    # below needs a display and fonts.
    import pygame
    pygame.display.init()
    pygame.font.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))
    from game.ui.action_panel import ActionPanel

    # --- the controller half ------------------------------------------
    _bm, _state, _setup, dice, _dec, _tt, ctrl, _started = _build_scene()
    p1, p2 = _p1_army(), _p2_army()
    ctrl.human_players = ("Player 1", "Player 2")
    ctrl.start({"Player 1": p1, "Player 2": p2})

    check("the step opens on a human", ctrl.first_human() == "Player 1")
    check("both owners owe a declaration",
          ctrl.humans_with_undeclared_units() == ["Player 1", "Player 2"])

    for squad in p1:
        ctrl.declare(squad, pregame.DEPLOY)
    ctrl.finish_formations_for("Player 1")
    check("one army declared is NOT enough to start the roll-off",
          ctrl.state == pregame.FORMATIONS)
    check("...and the SECOND army is now the one that owes it",
          ctrl.humans_with_undeclared_units() == ["Player 2"])

    for squad in p2:
        ctrl.declare(squad, pregame.DEPLOY)
    ctrl.finish_formations_for("Player 2")
    check("both armies declared begins the deployment roll-off",
          ctrl.state == pregame.DEPLOY_ROLLOFF)
    check("...and it really asks for a die", dice.is_pending)

    # --- the PANEL half, which is where the dead end actually was ------
    # The controller could always be TOLD about a second owner; what could not
    # happen was being OFFERED one, so this drives the real ActionPanel.
    _bm2, _s2, _setup2, _d2, _dec2, _tt2, ctrl2, _st2 = _build_scene()
    q1, q2 = _p1_army(), _p2_army()
    ctrl2.human_players = ("Player 1", "Player 2")
    ctrl2.start({"Player 1": q1, "Player 2": q2})
    panel = ActionPanel()
    surface = pygame.Surface((260, 900))
    rect = pygame.Rect(0, 0, 260, 900)

    def _buttons_drawn(controller):
        """How many declaration buttons the REAL panel puts up right now.

        _draw_pregame_formations() directly rather than draw(): the public
        entry takes forty-odd collaborators positionally (the narrative this
        file carries), and the branch that had the defect is this one."""
        panel._buttons = []
        panel._draw_pregame_formations(surface, rect, controller, 200, 10)
        return len(panel._buttons)

    check("the panel offers the first army's units", _buttons_drawn(ctrl2) > 0)
    for squad in q1:
        ctrl2.declare(squad, pregame.DEPLOY)
    ctrl2.finish_formations_for("Player 1")
    check("...and still offers buttons once that army is done - for the OTHER one",
          _buttons_drawn(ctrl2) > 0)
    check("...which is really Player 2's turn to declare",
          ctrl2.humans_with_undeclared_units() == ["Player 2"])
    for squad in q2:
        ctrl2.declare(squad, pregame.DEPLOY)
    ctrl2.finish_formations_for("Player 2")
    check("...and the roll-off begins from the panel path too",
          ctrl2.state == pregame.DEPLOY_ROLLOFF)

    # --- the pre-fix world ---------------------------------------------
    # One human, which is what main() used to leave the default at: the second
    # army is nobody's to declare, and the roll-off never begins.
    _bm3, _s3, _setup3, _d3, _dec3, _tt3, ctrl3, _st3 = _build_scene()
    r1, r2 = _p1_army(), _p2_army()
    ctrl3.human_players = ("Player 1",)
    ctrl3.start({"Player 1": r1, "Player 2": r2})
    for squad in r1:
        ctrl3.declare(squad, pregame.DEPLOY)
    ctrl3.finish_formations_for("Player 1")
    check("with one human the second army is nobody's to declare",
          ctrl3.humans_with_undeclared_units() == [])
    check("...and the pre-game stops before the roll-off - the reported dead end",
          ctrl3.state == pregame.FORMATIONS)
    panel._buttons = []
    panel._draw_pregame_formations(surface, rect, ctrl3, 200, 10)
    check("...with the panel showing no button at all to get past it",
          panel._buttons == [])


# --------------------------------------------------------------------------
# 9. The battle starts EXACTLY once (rule 03.01's hand-offs)
# --------------------------------------------------------------------------
class _ResumingStep:
    """A pre-battle / redeploy step in the shape four shipped ones really have:
    it finishes synchronously by CALLING on_done, and then answers False -
    "nothing to do".

    Not invented for this test: fated_hero.FatedHeroController._next() and
    enh_strike_swiftly.StrikeSwiftlyStep._next_player() both end
    `done(); return False`, and test_wraith_constructs.py pins exactly that
    pair of facts. enh_solid_image_projection.py's _apply() documents the
    opposite reading of the same protocol. The controller has to survive both."""

    def __init__(self):
        self.starts = 0

    def start(self, pregame_controller, on_done=None):
        self.starts += 1
        if on_done is not None:
            on_done()
        return False


def test_battle_starts_once():
    section("The battle starts exactly once")

    class _Log:
        def __init__(self):
            self.lines = []

        def add(self, message, file_only=False, category=None):
            self.lines.append(message)

    log = _Log()
    battle_map, state, setup, dice, decisions, tt, ctrl, started = _build_scene("map2")
    ctrl.game_log = log
    p1, p2 = _p1_army(), _p2_army()

    # Two pre-battle steps and one redeploy step, all of the hazardous shape.
    steps = [_ResumingStep(), _ResumingStep()]
    ctrl.prebattle_steps.extend(steps)
    redeploy = _ResumingStep()
    ctrl.redeploy_step = redeploy

    # Spy on the Pre-battle Abilities hand-back directly. Without it the only
    # visible symptom of a double-walked queue is the battle starting twice -
    # which _begin_battle()'s own guard would hide, and then a probe on the
    # driver would look harmless while the driver was broken.
    finishes = []
    _real_finish = ctrl.finish_prebattle_abilities

    def _counting_finish():
        finishes.append(1)
        return _real_finish()

    ctrl.finish_prebattle_abilities = _counting_finish

    ctrl.start({"Player 1": p1, "Player 2": p2})
    ctrl.finish_formations_for("Player 1")
    ctrl.finish_formations_for("Player 2")
    _drain_dice(ctrl, dice)
    if decisions.is_pending:
        decisions.choose(0)  # human won the roll-off: "I place first"
    guard = 0
    while ctrl.state == pregame.DEPLOYING and guard < 40:
        guard += 1
        squad = (ctrl.pending_units(ctrl.active_player) or [None])[0]
        if squad is None:
            break
        zone = deployment.zone_for(state.deployment_zones, ctrl.active_player)
        if not _auto_place(ctrl, setup, squad, zone):
            ctrl.give_up_on(squad)
    _drain_dice(ctrl, dice)

    check("the pre-game reached DONE", ctrl.state == pregame.DONE, ctrl.state)
    # The reported symptom: on_battle_start hands out Core CP and scores the
    # first Command phase's Primary (main.py's begin_battle), so a second call
    # is a whole extra round of VP before a model has moved.
    check("the battle starts exactly ONCE", len(started) == 1, f"{started}")
    check("deployment completes once", 
          log.lines.count("Pre-battle: deployment complete.") == 1,
          f"{log.lines.count('Pre-battle: deployment complete.')}")
    check("one first-turn roll-off, not three",
          log.lines.count(
              "Pre-battle: roll off to decide who takes the first turn (rule 03.01).") == 1)
    # Each hand-off is entered once - the queue is not re-walked behind the
    # step that already drained it.
    check("each pre-battle step starts once",
          [s.starts for s in steps] == [1, 1], f"{[s.starts for s in steps]}")
    check("the redeploy hook starts once", redeploy.starts == 1, f"{redeploy.starts}")
    check("the Pre-battle Abilities step hands back once, not once per step",
          len(finishes) == 1, f"{len(finishes)}")

    # The backstop, independent of who called: once the pre-game is DONE,
    # beginning the battle again pays nothing.
    ctrl.finish_prebattle_abilities()
    ctrl._begin_battle()
    check("_begin_battle() is idempotent", len(started) == 1, f"{started}")

    # And the hazard is real rather than modelled: a shipped step behaves this
    # way, so the enforcement has to live in the controller.
    from game import fated_hero

    class _EmptyState:
        tokens = []

    fired = []
    real_step = fated_hero.FatedHeroController(game_state=_EmptyState())
    returned = real_step.start(None, lambda: fired.append(1))
    check("a shipped step really does fire on_done and answer False",
          returned is False and len(fired) == 1, f"{returned} {fired}")

    # main.py's _RedeployChain composes two steps behind the ONE redeploy slot
    # and hands the second the first's on_done - the same protocol, and a
    # shipped link (prince_of_corsairs.py) takes the hazardous reading of it.
    # Source-guarded because the chain is a local class inside main(), which no
    # unit test can reach.
    main_src = io.open("main.py", encoding="utf-8").read()
    check("main.py's redeploy chain uses the one-shot continuation",
          "nxt = pregame.Resume(" in main_src)
    check("...and reads whether it already fired",
          "or nxt.fired:" in main_src)


def main():
    test_hotseat_formations()
    test_zone_geometry()
    test_formations()
    test_rolloff()
    test_turn_tracker()
    test_full_sequence()
    test_placement_predicate()
    test_overlay_hides_model_overlap()
    test_overlay_wiring()
    test_set_up_this_turn()
    test_scouts()
    test_battle_starts_once()

    print(f"\n{'=' * 60}")
    print(f"passed {len(PASS)}, failed {len(FAIL)}")
    for name in FAIL:
        print(f"  FAILED: {name}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

