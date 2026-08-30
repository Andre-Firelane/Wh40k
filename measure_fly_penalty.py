"""Does Take to the Skies (21.03) HELP or HURT a unit whose LEADER is the only
model with FLY?

THE REPORTED CASE, in the user's words: "die necron krieger sind hinten nicht
rausgekommen. sie hatten enorme schwierigkeiten nach vorne zu laufen." In
logs/game_20260826_185516.log the 21-model "2 Necron Warriors 1 + Technomancer"
gained 1.63" / 1.23" / 1.19" of centroid progress toward Central Objective in
three consecutive Movement phases, against a printed 5" move.

THE MECHANISM UNDER TEST. ai/agent_driver.py's _handle_movement() declares 21.03
whenever ANY model in the squad flies:

    use_fly = any(m.profile.fly for m in squad.models)

Rule 19.01 merges the Technomancer (FLY) into the Necron Warriors (no FLY), so
one model in twenty-one turns the policy on for the whole unit.
MovementController.take_to_the_skies() then charges the 2" penalty to EVERY
model in the squad, while clamp_move()'s bypass is gated per model:

    if self.flying_this_move and token.profile.fly:   # game/movement.py

So twenty models pay 2" out of a 5" move and get nothing back, and one model
flies. The policy's own comment says it "can only ever help this squad's own
mobility, at a fixed, small cost" - true for the squad it was written for
(Crisis Battlesuits: every model has FLY), false for a mixed attached unit.

WHAT IS MEASURED. The same unit, the same start, the same goal, with the fly
policy on and off, in two worlds:

  * ALONE on the board. No terrain and no other models are in the way, so
    anything 21.03's bypass could buy is zero BY CONSTRUCTION and the whole
    difference is the penalty. This is the clean read on the mechanism.
  * CROWDED, with Player 2's own army standing where the log says it stood.
    CLAUDE.md's movement section is explicit that the AI's own units are the
    dominant blocker, so this is the honest world - and it is also the one
    where the bypass has something to be worth.

Positions come from the log itself (the [deploy] lines and the last [move
detail] before the phase in question), not from a hand-placed fixture - the
reconstruction that omits the other fourteen units is exactly the systematic
error CLAUDE.md warns about.

Run: python measure_fly_penalty.py
"""
import math
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import config, maps

MAP_KEY = "map2"
LOG = "logs/game_20260826_185516.log"
# The Central Objective, which is what every [move choice] line for this unit
# names as its target point.
GOAL = (30.0, 22.0)
UNIT = "2 Necron Warriors 1 + Technomancer"


def parse_board(path, before_line):
    """Last known position of every unit in the log strictly before
    `before_line` - the board as the AI saw it entering that Movement phase."""
    positions = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            if number >= before_line:
                break
            match = re.search(r"\[deploy\] [^:]+: (.+?) \((?:key|screen|shooter|heavy|assault)\) "
                              r"deployed at \(([-\d.]+),([-\d.]+)\)", line)
            if match:
                positions.setdefault(match.group(1), None)
            if "[move detail]" in line and "final positions:" in line:
                name = line.split("[move detail] ", 1)[1].split(" mode=", 1)[0]
                coords = [(float(a), float(b)) for a, b in
                          re.findall(r"\(([-\d.]+),([-\d.]+)\)",
                                     line.split("final positions:", 1)[1])]
                if coords:
                    positions[name] = coords
    return positions


def centroid(points):
    return (sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points))


def main():
    config.MAP = MAP_KEY
    battle_map = maps.get(MAP_KEY)
    maps.apply_to_config(battle_map)

    from game import attached_units, army_lists
    from game.game_state import GameState
    from game.movement import MovementController
    from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker
    from ai import agent_driver

    # The third Movement phase of the game for this unit (log line 722's move),
    # entered from the board at line 669's turn plan. Any of the three reads the
    # same; this one has the most units already on the table.
    board = parse_board(LOG, before_line=669)
    if UNIT not in board or not board[UNIT]:
        sys.exit(f"no logged positions for {UNIT} before line 669")

    def fresh_army():
        state = GameState()
        squads = []
        army_lists.build_necrons("Player 2", squads.append, state=state)
        merged = attached_units.resolve_all(squads, game_state=state) \
            if hasattr(attached_units, "resolve_all") else squads
        return state, merged

    def place(state, squads, crowded):
        """Put every squad on its logged coordinates. Returns the unit under
        test. When `crowded` is False only that unit is on the table."""
        target = None
        state.tokens = []
        for squad in squads:
            coords = board.get(squad.name)
            if squad.name == UNIT:
                target = squad
            elif not crowded:
                continue
            if not coords:
                continue
            for model, (x_in, y_in) in zip(squad.models, coords):
                model.x_in, model.y_in = x_in, y_in
            state.tokens.extend(squad.models[:len(coords)])
        return target

    def move_once(state, squad, use_fly):
        tracker = TurnTracker(first_player="Player 2")
        tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
        controller = MovementController(
            obstacles=state.obstacles, player_name="Player 2", turn_tracker=tracker,
            all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
            board_height_in=config.BOARD_HEIGHT_IN,
        )
        allow_bulk = not all(m.profile.vehicle for m in squad.models)

        def start_fn():
            controller.start_move()
            if use_fly:
                controller.take_to_the_skies()

        # `use_fly` is forced by the caller here so both worlds can be measured;
        # the real path asks take_to_the_skies_pays(squad).

        before = agent_driver._centroid(squad)
        controller.select(squad.models[0])
        agent_driver._advance_toward(controller, squad, GOAL, start_move_fn=start_fn,
                                     allow_bulk_fallback=allow_bulk, flying=use_fly)
        return before, agent_driver._centroid(squad)

    print(f"map={MAP_KEY}  unit={UNIT}  goal={GOAL}")
    start = centroid(board[UNIT])
    print(f"start centroid ({start[0]:.2f},{start[1]:.2f})  "
          f"distance to goal {math.dist(start, GOAL):.2f}\"")
    flyers = None
    print()
    header = f"{'world':10s} {'21.03':7s} {'gained toward goal':>19s} {'ground covered':>15s}"
    print(header)
    print("-" * len(header))

    results = {}
    for crowded in (False, True):
        for use_fly in (True, False):
            state, squads = fresh_army()
            squad = place(state, squads, crowded)
            if squad is None:
                sys.exit(f"{UNIT} not built by build_necrons")
            if flyers is None:
                flyers = sum(1 for m in squad.models if m.profile.fly)
                print(f"({flyers} of {len(squad.models)} models have FLY)\n")
            before, after = move_once(state, squad, use_fly)
            gained = math.dist(before, GOAL) - math.dist(after, GOAL)
            ground = math.dist(before, after)
            world = "crowded" if crowded else "alone"
            results[(crowded, use_fly)] = (gained, ground)
            print(f"{world:10s} {'ON' if use_fly else 'OFF':7s} "
                  f"{gained:>18.2f}\" {ground:>14.2f}\"")

    print()
    for crowded in (False, True):
        on = results[(crowded, True)][0]
        off = results[(crowded, False)][0]
        world = "crowded" if crowded else "alone"
        verdict = "COSTS" if off > on else "helps"
        print(f"{world:10s}: 21.03 {verdict} {abs(off - on):.2f}\" of progress "
              f"({on:.2f}\" with it, {off:.2f}\" without)")


if __name__ == "__main__":
    main()
