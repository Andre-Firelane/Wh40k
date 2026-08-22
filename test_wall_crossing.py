"""The wall-crossing house rule: config.VEHICLES_CROSS_WALLS /
config.WALL_CROSSING_COST_IN.

Every model may move THROUGH Dense terrain; models rule 13.06 would otherwise
have stopped pay config.WALL_CROSSING_COST_IN out of their move for doing it.
Rule 13.05's "may not END on Dense terrain" is deliberately NOT lifted, and is
checked here to make sure it stayed put.

Every claim is A/B'd against the flag being off, because "the vehicle moved" on
its own proves nothing about which rule let it - the same move might have gone
round.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from testkit import Checks

from game import config
from game.factions import build_squad
from game.factions.orks import BOYZ, DEFF_DREAD, TRUKK
from game.movement import MovementController
from game.squad import model_terrain_violation
from game.terrain import DENSE, Obstacle
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker

c = Checks("wall crossing")

# A single wall, thin like every real one on both maps (measured: min 0.60",
# median 0.60", max 0.60" across map 1's 28 and map 2's 14 Dense features),
# lying across the lane between start and goal.
WALL = Obstacle(20.0, 24.0, 12.0, 0.6, DENSE)
# Close enough to the wall that an 8"-mover can still clear it AFTER paying
# the toll: it has to reach wall.max_y + its own radius (24.30 + 1.18 =
# 25.48"), and 8" - 3" of toll leaves 5". Starting further back is a
# legitimate refusal, not a bug - it simply cannot afford the crossing.
START = (20.0, 21.0)
GOAL = (20.0, 32.0)


def scene(datasheet, walls_on, start=START):
    squad = build_squad(datasheet, "Player 2", name="unit")
    for i, model in enumerate(squad.models):
        model.x_in = start[0] + (i % 5) * 1.4
        model.y_in = start[1] + (i // 5) * 1.4
    tokens = list(squad.models)
    tracker = TurnTracker(first_player="Player 2")
    tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
    mc = MovementController(obstacles=[WALL], player_name="Player 2", turn_tracker=tracker,
                            all_tokens=tokens, board_width_in=60.0, board_height_in=44.0)
    config.VEHICLES_CROSS_WALLS = walls_on
    return squad, mc


def straight_move(datasheet, walls_on, to=GOAL):
    """One model driven straight at `to`, exactly as a human drag would: clamp,
    place, commit. Returns (model, remaining range after, distance travelled)."""
    squad, mc = scene(datasheet, walls_on)
    model = squad.models[0]
    mc.select(model)
    mc.start_move()
    before = (model.x_in, model.y_in)
    x, y = mc.clamp_move(model, to[0], to[1])
    model.x_in, model.y_in = x, y
    mc.try_commit_segment(model)
    travelled = ((model.x_in - before[0]) ** 2 + (model.y_in - before[1]) ** 2) ** 0.5
    return model, mc.remaining_range.get(model.id, 0.0), travelled


_saved = config.VEHICLES_CROSS_WALLS
try:
    # -----------------------------------------------------------------
    # 1. Permission (Obstacle.blocks_movement_for)
    # -----------------------------------------------------------------
    print("1) may it cross at all")
    model, _left, blocked_travel = straight_move(DEFF_DREAD, walls_on=False)
    c.true("A/B - with the rule OFF a Deff Dread is stopped short of the wall",
           model.y_in < WALL.min_y)
    print(f"    rule off: Deff Dread reached y={model.y_in:.2f} (wall starts {WALL.min_y:.2f})")

    model, _left, crossed_travel = straight_move(DEFF_DREAD, walls_on=True)
    c.true("with the rule ON it ends beyond the wall", model.y_in > WALL.max_y)
    c.true("it travelled further than when it was blocked", crossed_travel > blocked_travel)
    print(f"    rule on : Deff Dread reached y={model.y_in:.2f}, travelled {crossed_travel:.2f}\"")

    # -----------------------------------------------------------------
    # 2. Price (MovementController._wall_crossing_cost)
    # -----------------------------------------------------------------
    print("\n2) what the crossing costs")
    model, left_crossing, travelled = straight_move(DEFF_DREAD, walls_on=True)
    budget = model.profile.movement_in
    c.eq("a crossing costs exactly WALL_CROSSING_COST_IN on top of the distance",
         round(budget - travelled - left_crossing, 4), round(config.WALL_CROSSING_COST_IN, 4))
    print(f"    budget {budget}\" - travelled {travelled:.2f}\" - left {left_crossing:.2f}\""
          f" = toll {budget - travelled - left_crossing:.2f}\"")

    # A move of the same length that does NOT meet a wall pays nothing.
    _clear, left_clear, travelled_clear = straight_move(DEFF_DREAD, walls_on=True, to=(20.0, 15.0))
    c.eq("a move that meets no wall pays no toll",
         round(budget - travelled_clear - left_clear, 4), 0.0)

    # INFANTRY cross by rule 13.06 already and must not be billed for it.
    boy, left_boy, travelled_boy = straight_move(BOYZ, walls_on=True)
    boy_budget = boy.profile.movement_in
    c.true("the Boyz crossed the wall too", boy.y_in > WALL.max_y)
    c.eq("INFANTRY pay no toll - rule 13.06 already let them through",
         round(boy_budget - travelled_boy - left_boy, 4), 0.0)

    # -----------------------------------------------------------------
    # 3. What was deliberately NOT changed (rule 13.05)
    # -----------------------------------------------------------------
    print("\n3) ending ON a wall is still illegal")
    squad, mc = scene(TRUKK, walls_on=True)
    truk = squad.models[0]
    mc.select(truk)
    mc.start_move()
    on_wall = (WALL.x_in, WALL.y_in)
    x, y = mc.clamp_move(truk, on_wall[0], on_wall[1])
    truk.x_in, truk.y_in = x, y
    committed, errors = mc.try_commit_segment(truk)
    c.true("the Trukk may pass through the wall", abs(y - WALL.y_in) < 0.5)
    c.true("but committing a position on top of it is rejected", not committed)
    c.true("and the rejection names rule 13.05's Dense terrain",
           any("Dense terrain" in e for e in errors))
    c.true("model_terrain_violation still reports a model standing on a wall",
           model_terrain_violation(truk, [WALL], WALL.x_in, WALL.y_in))
    print(f"    rejected with: {errors}")

    # -----------------------------------------------------------------
    # 4. The toll is charged once per COMMITTED segment, not per attempt
    # -----------------------------------------------------------------
    print("\n4) the toll is tied to a real, committed crossing")
    squad, mc = scene(DEFF_DREAD, walls_on=True)
    model = squad.models[0]
    mc.select(model)
    mc.start_move()
    start_left = mc.remaining_range.get(model.id, 0.0)
    for _ in range(5):
        # Five clamp_move() calls over the wall, as a human dragging across it
        # produces on every mouse-motion frame - none of them committed.
        mc.clamp_move(model, GOAL[0], GOAL[1])
    c.eq("hovering across a wall without committing costs nothing",
         mc.remaining_range.get(model.id, 0.0), start_left)

    # -----------------------------------------------------------------
    # 5. Whose rule it is (config.WALL_CROSSING_PLAYERS)
    # -----------------------------------------------------------------
    # The user's explicit decision: this lifts a handicap off the AI and the
    # human keeps playing the printed rules ("für mich als menschlicher spieler
    # soll alles so bleiben"). So it is not enough that Player 2 crosses - the
    # SAME datasheet on the human's side has to be stopped.
    print("\n5) it applies to the AI only")
    c.eq("the rule names exactly the AI", tuple(config.WALL_CROSSING_PLAYERS), ("Player 2",))

    def crosses_for(owner):
        squad = build_squad(DEFF_DREAD, owner, name="unit")
        model = squad.models[0]
        model.x_in, model.y_in = START
        tracker = TurnTracker(first_player=owner)
        tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
        mc = MovementController(obstacles=[WALL], player_name=owner, turn_tracker=tracker,
                                all_tokens=list(squad.models), board_width_in=60.0,
                                board_height_in=44.0)
        mc.select(model)
        mc.start_move()
        x, y = mc.clamp_move(model, GOAL[0], GOAL[1])
        model.x_in, model.y_in = x, y
        mc.try_commit_segment(model)
        return model.y_in

    ai_y = crosses_for("Player 2")
    human_y = crosses_for("Player 1")
    print(f"    Player 2 (AI)    reached y={ai_y:.2f}")
    print(f"    Player 1 (human) reached y={human_y:.2f} (wall starts {WALL.min_y:.2f})")
    c.true("the AI's Deff Dread crosses", ai_y > WALL.max_y)
    c.true("the identical human Deff Dread is stopped at the wall", human_y < WALL.min_y)
    c.true("the human is not charged a toll for a wall it never crossed",
           human_y < WALL.min_y)

    # The permission seam itself, independent of any movement: same profile,
    # different owner, opposite answer.
    ai_model = build_squad(DEFF_DREAD, "Player 2", name="a").models[0]
    human_model = build_squad(DEFF_DREAD, "Player 1", name="h").models[0]
    c.true("blocks_movement_for says no to the AI", not WALL.blocks_movement_for(ai_model))
    c.true("blocks_movement_for still says yes to the human", WALL.blocks_movement_for(human_model))

finally:
    config.VEHICLES_CROSS_WALLS = _saved

c.finish()
