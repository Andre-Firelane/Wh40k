"""Runtime proof through the REAL main() loop that the AI's units cross Dense
terrain and are charged NOTHING for it.

"Built but never FED" has hit this repo seven times, and a config constant is
the easiest thing of all to set and never have read. So this drives
selfplay.py's real main() loop with spies on the two seams the house rule
lives at - Obstacle.blocks_movement_for() (the permission) and
MovementController._finalize_segment() (the price) - and reports, for
COMMITTED segments only:

  * how many of the AI's segments actually crossed a wall,
  * what the toll took off them (must be 0.0),
  * how many segments a wall stopped outright (must be 0),
  * and, as the control, that the HUMAN's models are still blocked.

The last one matters: "every unit crosses for free" would also be true of a
build that lifted the rule for everybody, which is not what was asked for
("für mich als menschlicher spieler soll alles so bleiben").

NOTHING IS STAGED. Movement is the one thing a MockAgent run does on every
turn of every game, so this is the rare question that is measurable passively.

Harness trap this walks into deliberately (documented in CLAUDE.md): importing
selfplay runs nothing, because of its __main__ guard - so it goes through
runpy with run_name="__main__".

Usage:  python verify_wall_crossing_free.py [map2]
        python verify_wall_crossing_free.py map2 --neutralize   # toll back at 3.0
"""

import random
import runpy
import sys

from game import config, geometry
from game.movement import MovementController
from game.terrain import DENSE, Obstacle, may_cross_walls
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker

# SEEDED, and it is not cosmetic: a self-play run either gets its movement
# phases going or stalls on the first prompt it cannot answer (the documented
# harness limit). Measured over four seeds at 9000 frames, committed AI
# segments came out 1207 / 1248 / 338 / 1 - so an unseeded pair of runs would
# compare two different games and the A/B would mean nothing. Seed 1 is one of
# the productive ones; any seed works as long as BOTH halves use it.
random.seed(1)

# FIELDS THE ORKS AS THE AI, deliberately. config ships the Necrons as
# Player 2, and that list is almost all INFANTRY - measured, a 9000-frame run
# produced 111 wall crossings and every one of them was by a model rule 13.06
# already let through for free, so the toll could be 0 or 3.0 and the run came
# out byte-identical. The toll only ever applied to the OTHER 117 models of
# the shipped rosters, so the A/B needs an army that has some: the Orks bring
# the Battlewagon, Trukk, Deff Dread and Warbikers, and they are the army
# measure_crowded_movement.py has always used as the movement baseline.
config.PLAYER2_ARMY = "orks"

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")
    # The faithful pre-fix world is exactly one number: the permission half is
    # untouched, only the price comes back.
    config.WALL_CROSSING_COST_IN = 3.0

# The board main() built, captured from the mover itself. Used for the human
# control below: a self-play run only ever MOVES the AI, so "the human is still
# blocked" cannot be counted passively - the question is put to the live board
# and the live models instead, which is the only half that is staged here.
live = {"obstacles": None, "tokens": None, "forced": False}

stats = {
    "toll_seam_asked": 0,
    "ai_segments": 0,
    "ai_segments_crossing_a_wall": 0,
    "crossings_by_a_model_13_06_lets_through": 0,
    "crossings_by_a_model_that_USED_to_pay": 0,
    "toll_paid_total_in": 0.0,
    "segments_a_wall_stopped": 0,
    "ai_models_walls_let_through": 0,
    "ai_models_walls_blocked": 0,
    "human_models_walls_let_through": 0,
    "human_models_walls_blocked": 0,
}

# --- the permission seam ---------------------------------------------------
_real_blocks = Obstacle.blocks_movement_for


def blocks_movement_for(self, model):
    out = _real_blocks(self, model)
    if self.category == DENSE:
        side = "ai" if may_cross_walls(model) else "human"
        stats[f"{side}_models_walls_" + ("blocked" if out else "let_through")] += 1
    return out


Obstacle.blocks_movement_for = blocks_movement_for

# --- the price seam --------------------------------------------------------
_real_finalize = MovementController._finalize_segment
_real_toll = MovementController._wall_toll


def _wall_toll(self, token, origin, requested, remaining):
    toll, walls_block = _real_toll(self, token, origin, requested, remaining)
    if may_cross_walls(token):
        # Liveness: a toll of 0.00" proves nothing unless the seam that would
        # charge it was actually on the path the AI took.
        stats["toll_seam_asked"] += 1
    if may_cross_walls(token) and walls_block:
        profile = getattr(token, "profile", None)
        if profile is not None and not profile.can_move_through_dense_terrain:
            stats["segments_a_wall_stopped"] += 1
    return toll, walls_block


def _finalize_segment(self, token):
    if live["forced"]:
        # The staged segment at the bottom goes through this same seam. Counting
        # it would mix a question this script ASKED into the tally of what the
        # game DID, and the two must not be read as one number.
        return _real_finalize(self, token)
    live["obstacles"] = self.obstacles
    live["tokens"] = self.all_tokens
    origin = self.last_waypoint.get(token.id)
    before = self.remaining_range.get(token.id, 0.0)
    _real_finalize(self, token)
    if origin is None or not may_cross_walls(token):
        return
    stats["ai_segments"] += 1
    walls = [o for o in self.obstacles if o.category == DENSE]
    end = (token.x_in, token.y_in)
    moved = ((end[0] - origin[0]) ** 2 + (end[1] - origin[1]) ** 2) ** 0.5
    if moved < 1e-9 or not walls:
        return
    # Did this COMMITTED segment really pass through a wall? Asked of the
    # geometry the mover itself uses, not of the toll bookkeeping - otherwise
    # a toll of zero would make the question answer itself.
    if geometry.max_unblocked_fraction(origin, end, walls,
                                       inflate_radius=token.radius_in) < 1.0:
        stats["ai_segments_crossing_a_wall"] += 1
        # WHICH model crossed is the whole point: rule 13.06 always let
        # INFANTRY/BEASTS through for nothing, so a run whose crossings are
        # all infantry cannot tell the two worlds apart no matter how the
        # toll is set. Counted so the A/B says so instead of looking clean.
        profile = getattr(token, "profile", None)
        free = profile is None or profile.can_move_through_dense_terrain
        stats["crossings_by_a_model_13_06_lets_through" if free
              else "crossings_by_a_model_that_USED_to_pay"] += 1
        after = self.remaining_range.get(token.id, 0.0)
        stats["toll_paid_total_in"] += max(0.0, before - moved - after)


MovementController._wall_toll = _wall_toll
MovementController._finalize_segment = _finalize_segment

sys.argv = ["selfplay.py"] + sys.argv[1:]
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- wall crossing spy" + (" (NEUTRALIZED: toll back at 3.0)" if NEUTRALIZE else "")
      + " ---")
print(f"  WALL_CROSSING_COST_IN            {config.WALL_CROSSING_COST_IN}")
for key, value in stats.items():
    if isinstance(value, float):
        print(f"  {key:32} {value:.2f}\"")
    else:
        print(f"  {key:32} {value}")
# --- the control: the human plays the printed rules, unchanged --------------
obstacles, tokens = live["obstacles"], live["tokens"]
if obstacles and tokens:
    walls = [o for o in obstacles if o.category == DENSE]
    for owner in ("Player 1", "Player 2"):
        side = "human" if owner == "Player 1" else "ai"
        for token in tokens:
            squad = getattr(token, "squad", None)
            if getattr(squad, "owner", None) != owner:
                continue
            if any(w.blocks_movement_for(token) for w in walls):
                print(f"  [control] {owner:9} {token.profile.name:28} BLOCKED by a wall")
            else:
                print(f"  [control] {owner:9} {token.profile.name:28} passes")
            break

# --- the forced probe: one PAYING model, one real wall ----------------------
# Passively, a committed crossing by a model the toll applied to is rare: over
# five seeds at 9000 frames this run produced 0 of them (the AI's vehicles
# spend most of a self-play game nowhere near a wall). A passive counter would
# therefore report 0 and look like a pass. So the LAST thing this does is put
# the question directly: take a model off the live board that rule 13.06 would
# have stopped, stand it in front of a wall main() actually built, and drive
# one segment across it through a real MovementController. Only the position
# is staged - the model, the wall, the controller and the rule are the real
# ones, and the run is over, so nothing is disturbed.
if obstacles and tokens:
    walls = [o for o in obstacles if o.category == DENSE]
    payer = next(
        (t for t in tokens
         if may_cross_walls(t)
         and getattr(t, "profile", None) is not None
         and not t.profile.can_move_through_dense_terrain),
        None)
    if payer is None or not walls:
        print("  [forced] no paying AI model or no wall on the live board")
    else:
        wall = walls[0]
        live["forced"] = True
        tracker = TurnTracker(first_player=payer.squad.owner)
        tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
        payer.x_in = wall.x_in
        payer.y_in = wall.min_y - payer.radius_in - 0.5
        goal = (wall.x_in, wall.max_y + payer.radius_in + 2.0)
        mc = MovementController(obstacles=obstacles, player_name=payer.squad.owner,
                                turn_tracker=tracker, all_tokens=[payer],
                                board_width_in=config.BOARD_WIDTH_IN,
                                board_height_in=config.BOARD_HEIGHT_IN)
        mc.select(payer)
        mc.start_move()
        budget = mc.remaining_range.get(payer.id, 0.0)
        start = (payer.x_in, payer.y_in)
        x, y = mc.clamp_move(payer, goal[0], goal[1])
        payer.x_in, payer.y_in = x, y
        mc.try_commit_segment(payer)
        moved = ((payer.x_in - start[0]) ** 2 + (payer.y_in - start[1]) ** 2) ** 0.5
        left = mc.remaining_range.get(payer.id, 0.0)
        cleared = payer.y_in - payer.radius_in > wall.max_y
        print(f"  [forced] {payer.profile.name} ({payer.squad.owner}) at a real wall:"
              f" budget {budget:.2f}\", moved {moved:.2f}\", left {left:.2f}\","
              f" toll {max(0.0, budget - moved - left):.2f}\","
              f" cleared the wall: {cleared}")

crossed = stats["ai_segments_crossing_a_wall"]
if crossed:
    print(f"  average toll per crossing        "
          f"{stats['toll_paid_total_in'] / crossed:.2f}\"")
else:
    print("  passive tally INCONCLUSIVE: no committed AI segment crossed a wall in"
          " this run - which is why the forced probe above exists")
