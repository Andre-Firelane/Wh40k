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

import runpy
import sys

from game import config, geometry
from game.movement import MovementController
from game.terrain import DENSE, Obstacle, may_cross_walls

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
live = {"obstacles": None, "tokens": None}

stats = {
    "toll_seam_asked": 0,
    "ai_segments": 0,
    "ai_segments_crossing_a_wall": 0,
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

crossed = stats["ai_segments_crossing_a_wall"]
if crossed:
    print(f"  average toll per crossing        "
          f"{stats['toll_paid_total_in'] / crossed:.2f}\"")
else:
    print("  INCONCLUSIVE: no committed AI segment crossed a wall in this run")
