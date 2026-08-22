"""Tests for showing each unit's and each TRANSPORT's equipment in the
pre-game Declare Battle Formations step.

The question these answer: with two transports on the table, can the player
tell WHICH one a button means, and see what it carries? And with two units off
one datasheet, can they tell which unit the step is currently asking about?

Run: python test_loadout_display.py
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from game import config, formations, loadout, maps, pregame
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import (
    BOYZ,
    BOYZ_BIG_CHOPPA_TO_POWER_KLAW,
    GRETCHIN,
    MEGANOBZ,
    TRUKK,
)
from game.factions.tau_empire import (
    DEVILFISH,
    DEVILFISH_SEEKER_MISSILE_OPTION,
    STRIKE_TEAM,
)
from game.game_state import GameState
from game.movement import MovementController
from game.setup import SetupController
from game.turn import TurnTracker
from game.ui.action_panel import ActionPanel

PASS, FAIL = [], []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  [{'ok  ' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def section(title):
    print(f"\n=== {title} ===")


# --------------------------------------------------------------------------
# 1. loadout.py itself
# --------------------------------------------------------------------------
def test_loadout_text():
    section("game/loadout.py")
    boyz = build_squad(
        BOYZ, "Player 2", choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}},
        name="2 Boyz 1",
    )
    lines = loadout.loadout_lines(boyz)
    print("      " + "\n      ".join(lines))
    check("a mixed unit is grouped by model line", len(lines) == 2, f"{len(lines)} lines")
    check("the leader's swapped weapon is visible",
          any("Power Klaw" in l for l in lines), "; ".join(lines))
    check("the rank and file carry a count", any(l.startswith("9x") for l in lines),
          "; ".join(lines))

    trukk = build_squad(TRUKK, "Player 2", name="2 Trukk 1")
    single = loadout.loadout_lines(trukk)
    check("a one-model unit gets no \"1x\" prefix",
          single and not single[0].startswith("1x"), f"{single}")

    # Weapon counts survive - the thing ai/observation.py's summary drops.
    df = build_squad(
        DEVILFISH, "Player 1", choices={"Devilfish": {DEVILFISH_SEEKER_MISSILE_OPTION: 1}},
        name="1 Devilfish",
    )
    desc = loadout.transport_description(df.models[0])
    print(f"      {desc}")
    check("duplicate weapons are counted, not deduped away", "2x" in desc, desc)
    check("a chosen wargear option shows up", "Seeker Missile" in desc, desc)
    check("the transport is named by its UNIT, not its profile",
          desc.startswith("1 Devilfish"), desc)

    # Gear (drones) leaves no trace in weapons for Shield/Guardian - the whole
    # reason Token.gear_names was added.
    with_drones = build_squad(
        STRIKE_TEAM, "Player 1",
        gear={"Fire Warrior Shas'ui": ["Guardian Drone", "Shield Drone"]},
        name="1 Strike Team 1",
    )
    without = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 2")
    a, b = loadout.loadout_summary(with_drones), loadout.loadout_summary(without)
    check("two units differing ONLY by drones are distinguishable", a != b)
    check("...and the drones are named", "Guardian Drone" in a and "Shield Drone" in a, a)
    check("...while the one without says nothing about drones",
          "Drone" not in b, b)

    # A wiped-out unit must still be describable.
    for model in without.models:
        model.current_wounds = 0
    check("a destroyed unit is still describable", bool(loadout.loadout_lines(without)))

    empty = build_squad(GRETCHIN, "Player 2", name="2 Gretchin 1")
    empty.models = []
    check("an empty unit degrades gracefully", loadout.loadout_summary(empty) == "no weapons")


# --------------------------------------------------------------------------
# 2. The Formations screen with TWO differently equipped transports
# --------------------------------------------------------------------------
def _scene_with_two_transports():
    """The demo scene's two Trukks are wargear-identical (the TRUKK datasheet
    has no options at all), so a difference is injected by hand here - the
    point is that the UI shows whatever difference exists, not that this
    particular pair differs."""
    battle_map = maps.apply_to_config(maps.get("map2"))
    state = GameState()
    battle_map.build(state)
    setup = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    tt = TurnTracker(deferred_start=True)
    ctrl = pregame.PregameController(
        state, setup, DiceManager(), DecisionManager(), turn_tracker=tt,
        human_player="Player 2",
    )

    trukk1 = build_squad(TRUKK, "Player 2", name="2 Trukk 1", x_in=10, y_in=6)
    trukk2 = build_squad(TRUKK, "Player 2", name="2 Trukk 2", x_in=20, y_in=6)
    # Give Trukk 2 a second Big Shoota so the two really differ.
    from game.factions.orks import BigShootaProfile
    trukk2.models[0].weapons.append(BigShootaProfile())

    boyz = build_squad(
        BOYZ, "Player 2", choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}},
        name="2 Boyz 1",
    )
    meganobz = build_squad(MEGANOBZ, "Player 2", composition_index=1, name="2 Meganobz 1")

    units = [trukk1, trukk2, boyz, meganobz]
    ctrl.start(
        {"Player 1": [], "Player 2": units},
        transport_tokens=[trukk1.models[0], trukk2.models[0]],
    )
    return state, setup, tt, ctrl, trukk1, trukk2, boyz, meganobz


def _render(panel, ctrl, setup, mc, height=900):
    surf = pygame.Surface((config.LEFT_PANEL_WIDTH, height))
    rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, height)
    panel.draw(surf, rect, mc, None, setup_controller=setup, pregame_controller=ctrl)
    return surf


def _button_labels(panel):
    return [getattr(cb, "__name__", getattr(cb, "__qualname__", "?")) for _, cb in panel._buttons]


def test_formations_screen():
    section("Formations screen: two transports, told apart")
    pygame.init()
    pygame.display.set_mode((320, 240))
    state, setup, tt, ctrl, trukk1, trukk2, boyz, meganobz = _scene_with_two_transports()
    mc = MovementController(
        state.obstacles, all_tokens=state.tokens, turn_tracker=tt,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    panel = ActionPanel()

    d1 = loadout.transport_description(trukk1.models[0])
    d2 = loadout.transport_description(trukk2.models[0])
    print(f"      {d1}\n      {d2}")
    check("the two transports produce DIFFERENT descriptions", d1 != d2, f"{d1!r} vs {d2!r}")
    check("each names its own unit", "2 Trukk 1" in d1 and "2 Trukk 2" in d2)

    # Walk the step to the Boyz, which is the unit that can actually embark.
    guard = 0
    while ctrl.current_formation_unit("Player 2") is not boyz and guard < 10:
        guard += 1
        ctrl.declare(ctrl.current_formation_unit("Player 2"), pregame.DEPLOY)
    check("the step reaches a unit that can embark",
          ctrl.current_formation_unit("Player 2") is boyz)

    _render(panel, ctrl, setup, mc)
    labels = _button_labels(panel)
    embark_buttons = [l for l in labels if l == "run"]
    check("both transports are offered", len(embark_buttons) >= 2,
          f"{len(embark_buttons)} declare buttons among {labels}")

    # Fill Trukk 1 so it can no longer take the Boyz, and check it is still
    # LISTED (with a reason) rather than silently vanishing.
    ctrl.declare(meganobz, pregame.EMBARK, transport_token=trukk1.models[0])
    problems = formations.embark_errors(
        boyz, trukk1.models[0], ctrl.squads_assigned_to(trukk1.models[0])
    )
    check("a loaded transport really is full for the Boyz", bool(problems), "; ".join(problems))
    before = len(_button_labels(panel))
    _render(panel, ctrl, setup, mc)
    after = _button_labels(panel)
    check("the full transport's BUTTON is gone (illegal stays unclickable)",
          len([l for l in after if l == "run"]) == len(embark_buttons) - 1,
          f"{after}")
    check("...and its capacity message names the shortfall",
          "room for" in problems[0], problems[0])
    check("...naming the specific transport, not just \"Trukk\"",
          "2 Trukk 1" in problems[0], problems[0])
    check("the assigned cargo is recoverable for display",
          ctrl.squads_assigned_to(trukk1.models[0]) == [meganobz])
    used = formations.transport_capacity_used(trukk1.models[0], [meganobz])
    check("MEGA ARMOUR cargo counts double in the capacity readout",
          used == 2 * len(meganobz.models), f"{used} for {len(meganobz.models)} models")


# --------------------------------------------------------------------------
# 3. No text runs out of the panel
# --------------------------------------------------------------------------
def test_no_overflow():
    section("Nothing overflows the 220px panel")
    pygame.init()
    pygame.display.set_mode((320, 240))
    state, setup, tt, ctrl, trukk1, trukk2, boyz, meganobz = _scene_with_two_transports()
    mc = MovementController(
        state.obstacles, all_tokens=state.tokens, turn_tracker=tt,
        board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN,
    )
    panel = ActionPanel()

    from game.ui.text_utils import wrap_text
    max_width = config.LEFT_PANEL_WIDTH - 20
    worst = []
    for squad in (trukk1, trukk2, boyz, meganobz):
        for line in loadout.loadout_lines(squad):
            for wrapped in wrap_text(panel.font, line, max_width):
                worst.append((panel.font.size(wrapped)[0], wrapped))
    for token in (trukk1.models[0], trukk2.models[0]):
        text = loadout.transport_description(token)
        for wrapped in wrap_text(panel.font, text, max_width):
            worst.append((panel.font.size(wrapped)[0], wrapped))
    worst.sort(reverse=True)
    check("every wrapped loadout line fits the panel width",
          all(w <= max_width for w, _ in worst),
          f"widest {worst[0][0]}px of {max_width}px: {worst[0][1]!r}")

    # And the screens actually render at realistic panel heights.
    for height in (900, 700, 500):
        _render(panel, ctrl, setup, mc, height)
        check(f"formations screen renders at h={height}", True)

    # The placement screen too (it now carries a loadout block).
    zone_x, zone_y = 20.0, 6.0
    ctrl.declare(boyz, pregame.DEPLOY)
    for squad in ctrl.army("Player 2"):
        ctrl.declare(squad, pregame.DEPLOY)
    ctrl.finish_formations_for("Player 2")
    ctrl.finish_formations_for("Player 1")
    ctrl.state = pregame.DEPLOYING
    ctrl.active_player = "Player 2"
    ctrl._pending["Player 2"] = [boyz]
    if ctrl.start_deployment(boyz, zone_x, zone_y):
        _render(panel, ctrl, setup, mc)
        check("the placement screen renders with a loadout block", True)
    else:
        check("the placement screen renders with a loadout block", False, "start_deployment refused")


def main():
    test_loadout_text()
    test_formations_screen()
    test_no_overflow()
    print(f"\n{'=' * 60}\npassed {len(PASS)}, failed {len(FAIL)}")
    for name in FAIL:
        print(f"  FAILED: {name}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
