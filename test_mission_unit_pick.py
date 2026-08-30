"""Picking a unit by CLICKING IT ON THE BOARD, and the objective names that
make the prompt readable.

User: "Bei Burden of Trust muss immer links in der Spalte das Objective genannt
werden, um das es gerade geht, und ich muss auf der Map mein Einheit anklicken.
Dafuer brauchen die Objectives auch sinnvolle Namen."

Two halves, and they only work together: the panel names the objective, the
board takes the click.

The wiring half is a SOURCE guard on purpose. A board click has to be caught
ahead of main.py's generic board branch or it is swallowed by the camera
handler - that is CLAUDE.md's error class 15, recorded five times, and every
one of those bugs had a class that worked perfectly in isolation. Only the
ORDER of the branches can be wrong, so only the order is worth asserting.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()

import testkit as tk  # noqa: E402
from game import config, maps, secondary_missions as sm  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.objectives import is_within_range_of_objective  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402
from game.factions import aeldari as ae  # noqa: E402

checks = tk.Checks("Mission unit pick")

config.SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)


# --- 1. every objective has a name a player can act on ---
print("--- 1. objective names ---")

# User: "Dafuer brauchen die Objectives auch sinnvolle Namen, wie z. B.
# HomeObjective oder CentralObjective oder Objective East, West oder
# Northeast usw." The compass names are checked against each objective's
# MEASURED centre, not just spelled out - a name that points the wrong way is
# worse than the old "No Man's Land (W)" was.
EXPECTED = {
    "map1": ["P2 Home Objective", "Objective Northeast", "Central Objective",
             "P1 Home Objective", "Objective Southwest"],
    "map2": ["P2 Home Objective", "Objective West", "Central Objective",
             "P1 Home Objective", "Objective East"],
    # Six, in three mirror pairs, and no central one: the middle of this board
    # is the 9" circle both deployment zones give up, and the two objectives
    # nearest the centre sit inside it - which is what makes them No Man's
    # Land despite standing in a quadrant that is otherwise somebody's zone.
    "map3": ["Objective Northwest", "Objective Southeast", "P2 Home Objective",
             "P1 Home Objective", "Objective East", "Objective West"],
}
COMPASS = {"North": ("y", "<"), "South": ("y", ">"), "West": ("x", "<"), "East": ("x", ">")}

for key, names in EXPECTED.items():
    battle_map = maps.MAPS[key]
    maps.apply_to_config(battle_map)
    board = GameState()
    battle_map.build(board)
    checks.eq(f"{key}: the objective names", [o.name for o in board.objectives], names)
    checks.eq(f"{key}: every name is unique", len(set(names)), len(names))
    for objective in board.objectives:
        checks.eq(f"{key}: '{objective.name}' does not read like debug output",
                  "No Man's Land" in objective.name, False)
        cx, cy = sm.objective_centre(objective)
        mid_x, mid_y = config.BOARD_WIDTH_IN / 2.0, config.BOARD_HEIGHT_IN / 2.0
        for word, (axis, direction) in COMPASS.items():
            if word not in objective.name:
                continue
            value, middle = (cx, mid_x) if axis == "x" else (cy, mid_y)
            ok = value < middle if direction == "<" else value > middle
            checks.true(f"{key}: '{objective.name}' really lies that way", ok)
    # "Central" should be the one nearest the middle of the board.
    central = next((o for o in board.objectives if "Central" in o.name), None)
    if central is not None:
        def from_centre(objective):
            ox, oy = sm.objective_centre(objective)
            return ((ox - config.BOARD_WIDTH_IN / 2.0) ** 2
                    + (oy - config.BOARD_HEIGHT_IN / 2.0) ** 2) ** 0.5
        checks.eq(f"{key}: the Central Objective really is the most central",
                  min(board.objectives, key=from_centre).name, central.name)

# The rename must not have broken the card that reads objectives by geometry.
maps.apply_to_config(maps.MAPS["map2"])
BOARD = GameState()
maps.MAPS["map2"].build(BOARD)
ctx = sm.MissionContext("Player 1", objectives=BOARD.objectives,
                        deployment_zones=BOARD.deployment_zones)
checks.eq("No Man's Land is still found by GEOMETRY, not by name",
          sorted(o.name for o in sm.no_mans_land_objectives(ctx)),
          ["Central Objective", "Objective East", "Objective West"])


# --- 2. the pick request itself ---
print("--- 2. the request ---")

CENTRAL = next(o for o in BOARD.objectives if o.name == "Central Objective")
WEST = next(o for o in BOARD.objectives if o.name == "Objective West")


def unit_on(objective, name, offset=0.0):
    ox, oy = sm.objective_centre(objective)
    squad = tk.build(ae.RANGERS, owner="Player 1", name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = ox + i * 1.2 + offset, oy
    return squad


here = unit_on(CENTRAL, "1 Rangers HERE")
far = unit_on(CENTRAL, "1 Rangers FAR", offset=40.0)

ctrl = sm.SecondaryMissionController(player="Player 1")
ctrl.set_tokens_source(lambda: list(here.models) + list(far.models))
checks.eq("nothing pending to start with", ctrl.pending_pick, None)
checks.eq("...so the controller is idle", ctrl.is_busy, False)

taken, skipped = [], []
ctrl.request_unit_pick(
    prompt="click the unit that guards this objective.",
    subject=CENTRAL.name, eligible=[here],
    on_pick=taken.append, on_skip=lambda: skipped.append(True),
    skip_label="No guard here",
)
checks.true("an open request makes the controller busy", ctrl.is_busy)
checks.eq("the request names its objective", ctrl.pending_pick["subject"], CENTRAL.name)
checks.true("only the eligible unit is eligible", ctrl.pick_is_eligible(here))
checks.eq("...and nothing else is", ctrl.pick_is_eligible(far), False)

checks.eq("clicking an ineligible unit does nothing", ctrl.choose_picked_unit(far), False)
checks.eq("...it does not resolve", taken, [])
checks.true("...and the request stays open", ctrl.pending_pick is not None)
checks.true("clicking the eligible one takes", ctrl.choose_picked_unit(here))
checks.eq("...and hands it to the callback", taken, [here])
checks.eq("...and closes the request", ctrl.pending_pick, None)
checks.eq("the controller is idle again", ctrl.is_busy, False)
checks.eq("a click with nothing pending is harmless", ctrl.choose_picked_unit(here), False)

# The way out.
ctrl.request_unit_pick("pick one.", WEST.name, [here], taken.append,
                       on_skip=lambda: skipped.append(True), skip_label="No guard here")
ctrl.skip_pick()
checks.eq("skipping fires the skip callback", skipped, [True])
checks.eq("...and closes the request", ctrl.pending_pick, None)
ctrl.skip_pick()
checks.eq("skipping with nothing pending is harmless", len(skipped), 1)


# --- 3. the left panel names the objective ---
print("--- 3. the panel ---")

SURFACE = pygame.Surface((1920, 1080))
LEFT_PANEL = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 944)
movement = MovementController(obstacles=BOARD.obstacles, all_tokens=list(here.models),
                              board_width_in=60, board_height_in=44)

# Only the pick screen is exercised here: with no pick pending the dispatch
# falls through to branches that need the game's other controllers, and
# standing those up would be testing the panel, not this feature.
ctrl.request_unit_pick("click the unit that guards this objective.", CENTRAL.name,
                       [here], taken.append, on_skip=lambda: None,
                       skip_label="No guard here")
panel = ActionPanel()
panel.draw(SURFACE, LEFT_PANEL, movement, None, secondary_mission_controller=ctrl)
checks.true("the pick screen draws buttons", bool(panel._buttons))

# The panel is the ONLY place that can say which objective this is about, so
# that it does is worth asserting against the rendered pixels rather than
# against the string it was handed. Rendered twice - once with the objective in
# the request, once with a different one - and the surfaces must differ.
def render(subject):
    ctrl.pending_pick["subject"] = subject
    surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 944))
    ActionPanel().draw(surface, pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 944),
                       movement, None, secondary_mission_controller=ctrl)
    return pygame.image.tostring(surface, "RGB")


checks.true("the panel draws the objective's NAME, not a placeholder",
            render(CENTRAL.name) != render(WEST.name))

# The skip button really is wired to skip_pick(), not merely drawn.
ctrl.pending_pick["subject"] = CENTRAL.name
panel = ActionPanel()
panel.draw(SURFACE, LEFT_PANEL, movement, None, secondary_mission_controller=ctrl)
skip_button = next((cb for _r, cb in panel._buttons if cb == ctrl.skip_pick), None)
checks.true("the panel's button calls skip_pick()", skip_button is not None)
ctrl.pending_pick = None


# --- 4. wiring: the click is caught BEFORE the board swallows it ---
print("--- 4. wiring ---")

MAIN = io.open("main.py", encoding="utf-8").read()

branch = "elif secondary_mission_controller.pending_pick:"
checks.eq("main.py has exactly one branch for it", MAIN.count(branch), 1)


def at(needle):
    """Position of `needle`, or None. .find() rather than .index() so a source
    guard REPORTS what is missing instead of dying on a traceback - which is
    exactly backwards when the point of an A/B probe is to show which
    assurances the pre-fix world loses."""
    position = MAIN.find(needle)
    return None if position < 0 else position


def before(a, b):
    pos_a, pos_b = at(a), at(b)
    return pos_a is not None and pos_b is not None and pos_a < pos_b


# THE point of this suite. A click on the board reaches main.py's generic board
# branch unless something ahead of it claims the click first.
board_branch = "elif board_rect_screen.collidepoint(event.pos):"
checks.true("the pick branch comes BEFORE the generic board handling",
            before(branch, board_branch))
# ...and it must still sit behind the modal notices and the decision overlay,
# which genuinely outrank it.
for earlier in ("elif turn_start_overlay.is_pending:", "elif decision_manager.is_pending:",
                "elif dice_manager.is_pending:"):
    checks.true(f"...but after {earlier.split('.')[0][5:]}", before(earlier, branch))

checks.true("the branch resolves a board click to a squad",
            "secondary_mission_controller.choose_picked_unit(clicked.squad)" in MAIN)
_start = at(branch)
checks.true("and routes left-panel clicks to the panel",
            _start is not None
            and MAIN[_start:_start + 1600].count("action_panel.handle_click(event.pos)") == 1)

# The panel needs the controller, through all three stages of its call chain.
PANEL = io.open("game/ui/action_panel.py", encoding="utf-8").read()
checks.eq("main.py hands the controller to the panel",
          MAIN.count("secondary_mission_controller=secondary_mission_controller"), 1)
# Three stages now, not two: draw() -> _draw_dispatch() -> _draw_movement_ui(),
# because the ACTION buttons live on the per-unit movement screen.
checks.eq("the panel forwards it down both stages of the chain",
          PANEL.count("secondary_mission_controller=secondary_mission_controller"), 2)
checks.eq("all three stages declare it",
          PANEL.count("secondary_mission_controller=None"), 3)
checks.true("the dispatch branches on it",
            "if secondary_mission_controller is not None and secondary_mission_controller.pending_pick:"
            in PANEL)
# It has to own the panel outright, or the objective is never named.
# Compared against the pre-game BRANCH, not the bare parameter name - every
# controller appears in the signature first, so a name-only comparison would
# measure the argument list instead of the dispatch order.
dispatch = PANEL[PANEL.index("def _draw_dispatch("):]
body = dispatch[dispatch.index('"""', dispatch.index('"""') + 3):]
checks.true("the pick screen is the FIRST branch in the dispatch",
            body.index("secondary_mission_controller.pending_pick")
            < body.index("pregame_controller.is_active"))

# An open pick blocks the phase from advancing - it is a decision the human
# still owes, exactly like an open scoring prompt.
checks.true("an open pick blocks the phase advance",
            "or secondary_mission_controller.is_busy" in MAIN)

checks.finish()
