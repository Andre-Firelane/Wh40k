"""Tests for the "Place as Block" placement toggle.

Real SetupController / GameState / InputManager objects and real datasheets.
No pygame display beyond what InputManager needs for key modifiers.

Run: python test_block_placement.py
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from game import config, deployment, formation_layout, maps, pregame, setup as setup_module
from game.board import Board
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BOYZ, GRETCHIN, MEGANOBZ
from game.factions.tau_empire import GHOSTKEEL_BATTLESUIT, STRIKE_TEAM
from game.game_state import GameState
from game.input_handler import InputManager
from game.movement import MovementController
from game.setup import SetupController
from game.turn import TurnTracker

PASS, FAIL = [], []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  [{'ok  ' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def section(title):
    print(f"\n=== {title} ===")


def _scene(map_key="map2"):
    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    setup = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    return battle_map, state, setup


def _spread(squad):
    pts = [(m.x_in, m.y_in) for m in squad.models]
    return max(
        (((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5)
        for a in pts for b in pts
    ) if len(pts) > 1 else 0.0


def test_block_layout():
    section("Block layout on drop")
    battle_map, state, setup = _scene()
    zone = deployment.zone_for(state.deployment_zones, "Player 2")
    cx, cy, w, h = zone.rects[0]

    squad = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    setup.block_placement_enabled = False
    setup.start_setup(squad, cx, cy, on_cancel=lambda s: None)
    stacked = {(round(m.x_in, 3), round(m.y_in, 3)) for m in squad.models}
    check("toggle OFF still stacks every model on the drop point", len(stacked) == 1, f"{len(stacked)} distinct")
    check("...and that stack is illegal (overlap), as before",
          bool(squad.check_model_overlap(state.tokens)))
    setup.cancel_setup()

    squad2 = build_squad(BOYZ, "Player 2", name="2 Boyz 2")
    setup.block_placement_enabled = True
    setup.start_setup(squad2, cx, cy, on_cancel=lambda s: None)
    spots = {(round(m.x_in, 3), round(m.y_in, 3)) for m in squad2.models}
    check("toggle ON gives every model its own spot", len(spots) == len(squad2.models),
          f"{len(spots)} of {len(squad2.models)}")
    check("the block is immediately coherent (09.02)", not squad2.check_coherency(),
          "; ".join(squad2.check_coherency()))
    check("no model overlaps another", not squad2.check_model_overlap(state.tokens))
    check("no model stands on dense terrain", not squad2.check_terrain(state.obstacles))
    check("the block stays inside the 9\" spread limit", _spread(squad2) <= 9.0, f"{_spread(squad2):.2f}\"")
    setup.confirm_setup()
    check("a block drop confirms with no adjustment at all",
          setup.state == setup_module.IDLE and not setup.errors,
          "; ".join(setup.errors))

    # Mixed base sizes (19.01 attached units) - the widest model picks first.
    battle_map, state, setup = _scene()
    meganobz = build_squad(MEGANOBZ, "Player 2", name="2 Meganobz 1")
    setup.start_setup(meganobz, cx, cy, on_cancel=lambda s: None)
    check("a MEGA ARMOUR unit blocks out legally too",
          not meganobz.check_coherency() and not meganobz.check_model_overlap(state.tokens))
    setup.cancel_setup()

    # A single-model unit is a degenerate case worth pinning.
    ghostkeel = build_squad(GHOSTKEEL_BATTLESUIT, "Player 1", name="1 Ghostkeel 1")
    p1 = deployment.zone_for(state.deployment_zones, "Player 1")
    setup.start_setup(ghostkeel, p1.rects[0][0], p1.rects[0][1], on_cancel=lambda s: None)
    check("a one-model unit lands on the drop point exactly",
          abs(ghostkeel.models[0].x_in - p1.rects[0][0]) < 1e-6
          and abs(ghostkeel.models[0].y_in - p1.rects[0][1]) < 1e-6)
    setup.cancel_setup()


def test_block_respects_validator():
    section("Block layout obeys the placement validator (03.01 zone)")
    battle_map, state, setup = _scene()
    tt = TurnTracker(deferred_start=True)
    ctrl = pregame.PregameController(state, setup, DiceManager(), DecisionManager(), turn_tracker=tt)
    squad = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    ctrl.start({"Player 1": [], "Player 2": [squad]})
    ctrl._pending["Player 2"] = [squad]
    ctrl.state = pregame.DEPLOYING
    ctrl.active_player = "Player 2"

    zone = deployment.zone_for(state.deployment_zones, "Player 2")
    cx, cy, w, h = zone.rects[0]
    # Drop right on the FORWARD edge of the zone: a naive block would spill out.
    front_y = cy + h / 2 - 1.0
    check("start_deployment accepts the drop", ctrl.start_deployment(squad, cx, front_y))
    inside = [zone.contains_circle(m.x_in, m.y_in, m.radius_in) for m in squad.models]
    check("every model of the block stays wholly inside its own zone",
          all(inside), f"{sum(inside)}/{len(inside)} inside")
    check("the block is still coherent at the zone edge", not squad.check_coherency())
    check("it confirms without a single manual adjustment", ctrl.confirm_deployment(),
          "; ".join(ctrl.errors))


def test_group_drag():
    section("Rigid block drag")
    battle_map, state, setup = _scene()
    zone = deployment.zone_for(state.deployment_zones, "Player 2")
    cx, cy, w, h = zone.rects[0]
    squad = build_squad(STRIKE_TEAM, "Player 2", name="2 Strike Team 1")
    setup.start_setup(squad, cx, cy, on_cancel=lambda s: None)

    before = [(m.x_in, m.y_in) for m in squad.models]
    spread_before = _spread(squad)
    setup.begin_drag()
    setup.apply_group_drag(3.0, 0.0)
    after = [(m.x_in, m.y_in) for m in squad.models]

    offsets = {(round(a[0] - b[0], 4), round(a[1] - b[1], 4)) for a, b in zip(after, before)}
    check("every model moved by the SAME offset (rigid, no shear)",
          len(offsets) == 1, f"{offsets}")
    check("the offset is the requested one", offsets == {(3.0, 0.0)}, f"{offsets}")
    check("spread is unchanged, so coherency is invariant",
          abs(_spread(squad) - spread_before) < 1e-9)
    check("the dragged block is still coherent", not squad.check_coherency())

    # Repeated drags measure from the SNAPSHOT, not cumulatively.
    setup.apply_group_drag(3.0, 0.0)
    again = [(m.x_in, m.y_in) for m in squad.models]
    check("a second apply_group_drag with the same delta does not double it",
          all(abs(a[0] - b[0]) < 1e-9 for a, b in zip(again, after)))

    # Dragging into the board edge is clamped for the WHOLE block, not sheared.
    setup.begin_drag()
    setup.apply_group_drag(0.0, -1000.0)
    edge = [(m.x_in, m.y_in) for m in squad.models]
    edge_offsets = {round(a[1] - b[1], 4) for a, b in zip(edge, again)}
    check("a drag off the board clamps the block rigidly",
          len(edge_offsets) == 1, f"{edge_offsets}")
    check("...and every model is still on the board",
          all(m.radius_in <= m.x_in <= config.BOARD_WIDTH_IN - m.radius_in
              and m.radius_in <= m.y_in <= config.BOARD_HEIGHT_IN - m.radius_in
              for m in squad.models))
    check("...and it is still coherent afterwards", not squad.check_coherency())

    # A drag that cannot move at all leaves the block exactly where it was.
    frozen = [(m.x_in, m.y_in) for m in squad.models]
    setup.begin_drag()
    setup.apply_group_drag(0.0, -1000.0)
    check("a fully blocked drag is a no-op, not a scramble",
          all(abs(a[0] - b[0]) < 0.2 and abs(a[1] - b[1]) < 0.2
              for a, b in zip([(m.x_in, m.y_in) for m in squad.models], frozen)))
    setup.cancel_setup()


def test_input_routing():
    section("InputManager routing (block drag vs single model vs SHIFT)")
    pygame.init()
    pygame.display.set_mode((320, 240))
    battle_map, state, setup = _scene()
    zone = deployment.zone_for(state.deployment_zones, "Player 2")
    cx, cy, w, h = zone.rects[0]
    squad = build_squad(STRIKE_TEAM, "Player 2", name="2 Strike Team 1")
    setup.start_setup(squad, cx, cy, on_cancel=lambda s: None)

    board = Board(config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN, config.PIXELS_PER_INCH)
    tt = TurnTracker(deferred_start=True)
    mc = MovementController(
        state.obstacles, all_tokens=state.tokens, turn_tracker=tt,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    im = InputManager()

    def px(model):
        return (int(model.x_in * config.PIXELS_PER_INCH), int(model.y_in * config.PIXELS_PER_INCH))

    def drag(model, dx_in, dy_in):
        start = px(model)
        end = (int(start[0] + dx_in * config.PIXELS_PER_INCH),
               int(start[1] + dy_in * config.PIXELS_PER_INCH))
        im.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": start, "button": 1}),
                        state.tokens, board, mc, setup)
        was_group = im.dragging_setup_group
        im.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": end}),
                        state.tokens, board, mc, setup)
        im.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": end, "button": 1}),
                        state.tokens, board, mc, setup)
        return was_group

    target = squad.models[0]
    before = [(m.x_in, m.y_in) for m in squad.models]
    was_group = drag(target, 2.0, 0.0)
    after = [(m.x_in, m.y_in) for m in squad.models]
    moved = sum(1 for a, b in zip(after, before) if abs(a[0] - b[0]) > 1e-6 or abs(a[1] - b[1]) > 1e-6)
    check("block mode ON: the drag is routed as a block drag", was_group)
    check("block mode ON: the whole unit moved", moved == len(squad.models), f"{moved} moved")
    check("block mode ON: nothing was committed through MovementController",
          squad not in mc.moved_squad_ids)
    check("block mode ON: the drag flag is cleared on release", not im.dragging_setup_group)

    # SHIFT held -> single model, even with the toggle on.
    before = [(m.x_in, m.y_in) for m in squad.models]
    target = squad.models[0]
    start = px(target)
    end = (int(start[0] + 1.0 * config.PIXELS_PER_INCH), start[1])
    original_get_mods = pygame.key.get_mods
    pygame.key.get_mods = lambda: pygame.KMOD_LSHIFT
    try:
        im.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": start, "button": 1}),
                        state.tokens, board, mc, setup)
        shift_group = im.dragging_setup_group
        im.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": end}),
                        state.tokens, board, mc, setup)
        im.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": end, "button": 1}),
                        state.tokens, board, mc, setup)
    finally:
        pygame.key.get_mods = original_get_mods
    after = [(m.x_in, m.y_in) for m in squad.models]
    moved = sum(1 for a, b in zip(after, before) if abs(a[0] - b[0]) > 1e-6 or abs(a[1] - b[1]) > 1e-6)
    check("SHIFT overrides the toggle for one drag", not shift_group)
    check("SHIFT moves exactly one model", moved == 1, f"{moved} moved")

    # Toggle off -> single model, as before this feature existed.
    setup.block_placement_enabled = False
    before = [(m.x_in, m.y_in) for m in squad.models]
    was_group = drag(squad.models[1], 1.0, 0.0)
    after = [(m.x_in, m.y_in) for m in squad.models]
    moved = sum(1 for a, b in zip(after, before) if abs(a[0] - b[0]) > 1e-6 or abs(a[1] - b[1]) > 1e-6)
    check("block mode OFF: single-model drag, unchanged behaviour",
          not was_group and moved == 1, f"group={was_group}, moved={moved}")
    setup.block_placement_enabled = True
    setup.cancel_setup()


def test_toggle_semantics():
    section("Toggle semantics")
    battle_map, state, setup = _scene()
    start = setup.block_placement_enabled
    setup.toggle_block_placement()
    check("toggle flips", setup.block_placement_enabled is not start)
    setup.toggle_block_placement()
    check("toggle flips back", setup.block_placement_enabled is start)

    zone = deployment.zone_for(state.deployment_zones, "Player 2")
    cx, cy, w, h = zone.rects[0]
    squad = build_squad(GRETCHIN, "Player 2", name="2 Gretchin 1")
    setup.start_setup(squad, cx, cy, on_cancel=lambda s: None)
    placed = [(m.x_in, m.y_in) for m in squad.models]
    setup.toggle_block_placement()
    check("toggling mid-placement does not rearrange what is already placed",
          [(m.x_in, m.y_in) for m in squad.models] == placed)
    setup.cancel_setup()
    check("cancel still removes every model from the board",
          not any(m in state.tokens for m in squad.models))

    # Toggle flipped ON mid-placement over a still-STACKED squad: the block's
    # origin is illegal (everything overlaps), so bisecting from it would find
    # no legal fraction and freeze the unit. It has to follow the cursor
    # instead - clamp_drag()'s third case, for the same reason.
    setup.block_placement_enabled = False
    stacked = build_squad(GRETCHIN, "Player 2", name="2 Gretchin 2")
    setup.start_setup(stacked, cx, cy, on_cancel=lambda s: None)
    check("precondition: the squad really is stacked and illegal",
          bool(stacked.check_model_overlap(state.tokens)))
    setup.block_placement_enabled = True
    setup.begin_drag()
    before = [(m.x_in, m.y_in) for m in stacked.models]
    setup.apply_group_drag(2.0, 0.0)
    after = [(m.x_in, m.y_in) for m in stacked.models]
    check("a drag from an ILLEGAL stack still moves (no freeze)",
          all(abs(a[0] - b[0] - 2.0) < 1e-6 for a, b in zip(after, before)),
          f"{[round(a[0] - b[0], 3) for a, b in zip(after, before)][:3]}")
    setup.cancel_setup()


def test_ai_path_unchanged():
    section("The AI's own packer still behaves identically")
    from ai import agent_driver
    battle_map, state, setup = _scene()
    squad = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    positions = agent_driver._ingress_pack_positions(squad, 20.0, 6.0, state.tokens)
    check("_ingress_pack_positions returns one spot per model",
          len(positions) == len(squad.models))
    distinct = len({(round(x, 3), round(y, 3)) for x, y in positions})
    check("...all distinct on open ground", distinct == len(squad.models), f"{distinct}")
    check("...and it delegates to the shared packer",
          agent_driver.formation_layout is formation_layout)

    # The shared helper's own facing default.
    ang = formation_layout.away_from_board_centre(20.0, 6.0)
    check("away_from_board_centre points away from the middle", ang < 0, f"{ang:.2f} rad")


def test_other_placement_flows():
    """Block placement is on by default, so it also affects the two OTHER
    flows that go through start_setup(): a human disembark (18.04/18.05) and a
    human Ingress move (20.04). Both hand start_setup() their own full
    validator, so the block has to come out inside THEIR constraints too - the
    disembark distance cap and Ingress's >8"-from-enemies rule. That is the
    whole point of routing the packer through placement_validator() rather
    than through plain geometry."""
    section("The other placement flows (disembark 18.04, ingress 20.04)")
    from game.ingress import IngressController
    from game.transport import DISEMBARK_DISTANCE_IN, TACTICAL, TransportController
    from game.factions.orks import TRUKK
    from game.squad import edge_distance

    battle_map, state, setup = _scene()
    zone = deployment.zone_for(state.deployment_zones, "Player 2")
    cx, cy, w, h = zone.rects[0]
    tt = TurnTracker()
    mc = MovementController(
        state.obstacles, all_tokens=state.tokens, turn_tracker=tt,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    ingress_for_transport = IngressController(
        setup, state, state.tokens, turn_tracker=tt,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    transport_ctrl = TransportController(
        setup, state, state.tokens, mc, ingress_for_transport, DiceManager(),
        turn_tracker=tt,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )

    trukk = build_squad(TRUKK, "Player 2", name="2 Trukk 1", x_in=cx, y_in=cy)
    trukk_token = trukk.models[0]
    state.add_token(trukk_token)
    boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    boyz.embarked_in = trukk_token
    state.embarked_squads.append(boyz)

    # The mode is forced by what the TRANSPORT did this phase (18.04 BEFORE
    # MOVING), not chosen - an unmoved Trukk gives a Tactical disembark.
    transport_ctrl.start_disembark(boyz)
    if setup.state != setup_module.PLACING:
        check("a tactical disembark starts placing", False, f"state={setup.state}")
    else:
        mode = transport_ctrl._disembark_mode
        check("a tactical disembark starts placing", mode == TACTICAL, f"mode={mode}")
        cap = DISEMBARK_DISTANCE_IN[mode]
        far = max(edge_distance(m, trukk_token) for m in boyz.models)
        check("the block comes out inside the disembark distance cap (18.04)",
              far <= cap + 1e-6, f'{far:.2f}" of {cap:g}"')
        check("...coherent, with no dragging at all", not boyz.check_coherency(),
              "; ".join(boyz.check_coherency()))
        check("...and with no model overlapping another",
              not boyz.check_model_overlap(state.tokens))
        check("...so it confirms straight away",
              transport_ctrl.confirm_disembark() is not False and setup.state == setup_module.IDLE,
              "; ".join(setup.errors))

    # Ingress: >8" from every enemy model AND within 6" of a board edge.
    battle_map, state, setup = _scene()
    tt2 = TurnTracker()
    tt2.battle_round = 2  # rule 20.03: reserves arrive from round 2
    ingress = IngressController(
        setup, state, state.tokens, turn_tracker=tt2,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    enemy = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
    for i, model in enumerate(enemy.models):
        model.x_in, model.y_in = 20.0 + (i % 5) * 1.6, 22.0
        state.add_token(model)
    reserve = build_squad(GRETCHIN, "Player 2", name="2 Gretchin 1")
    state.add_reserve_squad(reserve)

    ingress.start_ingress(reserve, 20.0, 2.0)  # near the bottom edge, far from the enemy
    if setup.state != setup_module.PLACING:
        check("an ingress move starts placing", False, f"state={setup.state}")
    else:
        check("an ingress move starts placing", True)
        nearest = min(edge_distance(m, e) for m in reserve.models for e in enemy.models)
        check("the block keeps rule 20.04's >8\" from every enemy model",
              nearest > 8.0, f'{nearest:.2f}"')
        check("...coherent with no dragging", not reserve.check_coherency())
        ingress.confirm_ingress()
        check("...and it confirms straight away", setup.state == setup_module.IDLE,
              "; ".join(setup.errors))


def main():
    test_block_layout()
    test_block_respects_validator()
    test_group_drag()
    test_input_routing()
    test_toggle_semantics()
    test_other_placement_flows()
    test_ai_path_unchanged()
    print(f"\n{'=' * 60}\npassed {len(PASS)}, failed {len(FAIL)}")
    for name in FAIL:
        print(f"  FAILED: {name}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
