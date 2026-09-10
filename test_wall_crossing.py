"""The wall-crossing house rule: config.VEHICLES_CROSS_WALLS /
config.WALL_CROSSING_COST_IN.

Every model the AI owns may move THROUGH Dense terrain, and since the toll went
to zero it does so for nothing - the permission was always keyword-blind, and
now the price is too ("darf sie ALLE einheiten durch waende bewegen"). Rule
13.05's "may not END on Dense terrain" is deliberately NOT lifted, and is
checked here to make sure it stayed put.

Section 2 comes in two halves on purpose. 2a pins what SHIPS (a crossing is
free, and no wall can stop an AI model any more) and does it by running the
same scene at both toll values, because at a toll of zero "budget - travelled
- left == WALL_CROSSING_COST_IN" is 0 == 0 and would pass with the machinery
deleted. 2b keeps the machinery honest by exercising it at an explicit
non-zero toll, so the value can go back to 3.0 in one line.

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
from game.terrain import DENSE, WALL_THICKNESS_IN, Obstacle
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker

c = Checks("wall crossing")

# A single wall, thin like every real one on all four maps - built FROM the
# shared constant rather than from a literal, so it cannot drift away from
# the boards it stands in for the way its own hardcoded 0.6 just did when
# the walls were halved. Measured: min = median = max = WALL_THICKNESS_IN
# across map 1's 28, map 2's 14, map 3's 20 and map 4's 16 Dense features.
# It lies across the lane between start and goal.
WALL = Obstacle(20.0, 24.0, 12.0, WALL_THICKNESS_IN, DENSE)
# Close enough to the wall that an 8"-mover still clears it even while section
# 2b has the toll switched back on: it has to reach wall.max_y + its own radius
# (24.15 + 1.18 = 25.33", the wall being half as thick as it used to be), and
# 8" - 3" of toll leaves 5". At the shipped toll of 0 it simply walks the
# full 8".
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
    # 2a. What SHIPS: a crossing is free, for every unit the AI owns
    # -----------------------------------------------------------------
    # The user's decision, and the point of it: the permission half was always
    # keyword-blind (it ends in `not may_cross_walls(model)`, an OWNER answer),
    # but the PRICE was not - INFANTRY crossed for nothing while a Windrider, a
    # War Walker or a Deff Dread paid. Measured over all ten shipped lists, 584
    # of Player 2's 701 models crossed free and 117 paid. Now nobody pays.
    print("\n2a) the shipped price of a crossing is nothing")
    c.eq("the shipped toll is zero", config.WALL_CROSSING_COST_IN, 0.0)

    model, left_free, travelled_free = straight_move(DEFF_DREAD, walls_on=True)
    budget = model.profile.movement_in
    c.eq("a VEHICLE that crosses a wall is charged nothing for it",
         round(budget - travelled_free - left_free, 4), 0.0)
    c.eq("so it spends its whole move on GROUND",
         round(travelled_free, 4), round(budget, 4))
    print(f"    budget {budget}\" - travelled {travelled_free:.2f}\""
          f" - left {left_free:.2f}\" = toll {budget - travelled_free - left_free:.2f}\"")

    # NOT a tautology: at a toll of zero "cost == WALL_CROSSING_COST_IN" is
    # 0 == 0 and would hold with the machinery deleted. So run the SAME scene
    # at the old 3.0 and require a different outcome.
    config.WALL_CROSSING_COST_IN = 3.0
    try:
        _paid, left_paid, travelled_paid = straight_move(DEFF_DREAD, walls_on=True)
    finally:
        config.WALL_CROSSING_COST_IN = 0.0
    c.true("A/B - at the old 3\" toll the same Deff Dread covered less ground",
           travelled_paid < travelled_free - 0.5)
    print(f"    A/B at a 3\" toll: travelled {travelled_paid:.2f}\""
          f" against {travelled_free:.2f}\" free")

    # The affordability gate goes with it, and nothing else replaces it: below
    # the toll a wall used to block the crossing outright (46 hits over
    # measure_crowded_movement.py map2). Staged on a model that has already
    # spent most of its move - exactly the state it is in mid-drag.
    def crosses_on_a_short_budget(cost, spare=0.5):
        config.WALL_CROSSING_COST_IN = cost
        try:
            squad, mc = scene(DEFF_DREAD, walls_on=True, start=(20.0, 22.5))
            short = squad.models[0]
            mc.select(short)
            mc.start_move()
            needed = (WALL.max_y + short.radius_in) - short.y_in
            mc.remaining_range[short.id] = needed + spare
            x, y = mc.clamp_move(short, GOAL[0], GOAL[1])
            short.x_in, short.y_in = x, y
            mc.try_commit_segment(short)
        finally:
            config.WALL_CROSSING_COST_IN = 0.0
        return short.y_in - short.radius_in > WALL.max_y, needed

    crossed_free, needed = crosses_on_a_short_budget(0.0)
    crossed_paying, _ = crosses_on_a_short_budget(3.0)
    c.true("enough left to clear the wall but not to pay a 3\" toll: it crosses",
           crossed_free)
    c.true("A/B - at the old toll that same model was stopped at the wall",
           not crossed_paying)
    print(f"    needed {needed:.2f}\" to clear it, had {needed + 0.5:.2f}\":"
          f" free={crossed_free}, at a 3\" toll={crossed_paying}")

    # -----------------------------------------------------------------
    # 2b. The MECHANISM, kept alive at a non-zero toll so it cannot rot
    # -----------------------------------------------------------------
    # WALL_CROSSING_COST_IN is a knob the user has now set twice. Shipping it
    # at 0 must not quietly turn _wall_toll() into unreachable code, or putting
    # 3.0 back would be a rebuild instead of a one-line edit.
    print("\n2b) the toll machinery still works when switched on")
    config.WALL_CROSSING_COST_IN = 3.0
    try:
        model, left_crossing, travelled = straight_move(DEFF_DREAD, walls_on=True)
        budget = model.profile.movement_in
        c.eq("a crossing costs exactly WALL_CROSSING_COST_IN on top of the distance",
             round(budget - travelled - left_crossing, 4),
             round(config.WALL_CROSSING_COST_IN, 4))
        print(f"    budget {budget}\" - travelled {travelled:.2f}\""
              f" - left {left_crossing:.2f}\""
              f" = toll {budget - travelled - left_crossing:.2f}\"")

        # A move of the same length that does NOT meet a wall pays nothing.
        _clear, left_clear, travelled_clear = straight_move(DEFF_DREAD, walls_on=True,
                                                            to=(20.0, 15.0))
        c.eq("a move that meets no wall pays no toll",
             round(budget - travelled_clear - left_clear, 4), 0.0)

        # INFANTRY cross by rule 13.06 already and must not be billed for it.
        boy, left_boy, travelled_boy = straight_move(BOYZ, walls_on=True)
        boy_budget = boy.profile.movement_in
        c.true("the Boyz crossed the wall too", boy.y_in > WALL.max_y)
        c.eq("INFANTRY pay no toll - rule 13.06 already let them through",
             round(boy_budget - travelled_boy - left_boy, 4), 0.0)
        c.true("and at a non-zero toll the VEHICLE beside them DOES pay",
               budget - travelled - left_crossing > 0.0)
    finally:
        config.WALL_CROSSING_COST_IN = 0.0

    # Shipped, the two are finally on the same footing - the thing "ALLE
    # einheiten" was asked for.
    boy, left_boy, travelled_boy = straight_move(BOYZ, walls_on=True)
    c.eq("shipped: INFANTRY and VEHICLE pay the same to cross - nothing",
         (round(boy.profile.movement_in - travelled_boy - left_boy, 4),
          round(budget - travelled_free - left_free, 4)),
         (0.0, 0.0))

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
