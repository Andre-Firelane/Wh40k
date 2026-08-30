"""Rule 07.01: the battle lasts five battle rounds and then it is over.

User: "das spiel soll nach runde 5 enden". Until this, TurnTracker's own
docstring said the opposite out loud - "without missions, battle_round simply
keeps incrementing; nothing ends the battle automatically yet" - so a game ran
on forever and the Secondary cards that key on the final round (Beacon) had a
last round that never arrived in practice.

Two things are worth pinning beyond "it stops":

  - the counter STAYS on the last round rather than rolling into a phantom
    round 6. Everything that asks "which round is it" (Beacon's timing, the
    AI's scoring-turns-left, the status panel) then keeps reporting the round
    that was actually played.
  - the end is gated in ONE place, `_has_unresolved_declaration()`, which both
    the human's "Next Phase" button and the AI already read. A second opinion
    would be the drift this codebase keeps consolidating away.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()

import testkit as tk  # noqa: E402
from game.missions import BATTLE_ROUNDS, MissionController  # noqa: E402
from game.turn import PHASES, TurnTracker  # noqa: E402
from game.ui.battle_end_overlay import BattleEndOverlay  # noqa: E402

checks = tk.Checks("Battle end")


def played_out(first_player="Player 1"):
    """Run a whole battle through the tracker, returning it and how many turns
    it took."""
    tracker = TurnTracker(first_player=first_player, game_log=tk.Log())
    turns, guard = 0, 0
    while not tracker.battle_over and guard < 200:
        for _ in range(len(PHASES)):
            tracker.advance_phase()
            if tracker.battle_over:
                break
        turns += 1
        guard += 1
    return tracker, turns


# --- 1. the battle ends, after the right number of turns ---
print("--- 1. it ends ---")

tracker, turns = played_out()
checks.true("the battle ends on its own", tracker.battle_over)
checks.eq("after both players have taken every round", turns, BATTLE_ROUNDS * 2)
# THE detail: the counter stays on the last round rather than rolling over.
checks.eq("the round counter stays on the final round", tracker.battle_round, BATTLE_ROUNDS)
checks.eq("...it does NOT roll into a phantom extra round",
          tracker.battle_round, BATTLE_ROUNDS)

# Nothing moves afterwards, however hard it is pushed.
frozen = (tracker.battle_round, tracker.phase, tracker.turn_owner, tracker.active_player)
for _ in range(20):
    tracker.advance_phase()
checks.eq("further phase advances change nothing",
          (tracker.battle_round, tracker.phase, tracker.turn_owner, tracker.active_player),
          frozen)

# It ends after the SECOND player's turn of the last round, whoever went first.
for first in ("Player 1", "Player 2"):
    tracker2, turns2 = played_out(first)
    second = "Player 2" if first == "Player 1" else "Player 1"
    checks.eq(f"{first} first: still {BATTLE_ROUNDS * 2} turns", turns2, BATTLE_ROUNDS * 2)
    checks.eq(f"{first} first: the last turn belonged to {second}",
              tracker2.turn_owner, second)

# A fresh tracker is not over, and a deferred one is not over either.
checks.eq("a new battle is not over", TurnTracker(game_log=tk.Log()).battle_over, False)
deferred = TurnTracker(game_log=tk.Log(), deferred_start=True)
checks.eq("a pre-game tracker is not over", deferred.battle_over, False)
deferred.start_battle("Player 1")
checks.eq("...nor once the battle actually starts", deferred.battle_over, False)
checks.eq("...and it starts on round 1", deferred.battle_round, 1)


# --- 2. the final-score overlay ---
print("--- 2. the result ---")

mission = MissionController(game_log=tk.Log())
mission.primary_points["Player 1"], mission.secondary_points["Player 1"] = 18, 12
mission.primary_points["Player 2"], mission.secondary_points["Player 2"] = 21, 4

overlay = BattleEndOverlay()
checks.eq("nothing is shown before the battle ends", overlay.is_pending, False)
overlay.draw(pygame.Surface((800, 600)))  # a no-op, not a crash

overlay.show(mission)
checks.true("the end of the battle raises it", overlay.is_pending)
result = {row[0]: row for row in overlay._result}
checks.eq("Player 1's total", result["Player 1"][3], 30)
checks.eq("Player 2's total", result["Player 2"][3], 25)
# The split is carried, not just the total - the two halves come from entirely
# different places and the total alone hides that.
checks.eq("...with the Primary/Secondary split", result["Player 1"][1:3], (18, 12))
checks.eq("the winner is the higher total", overlay._winner(), "Player 1")
overlay.draw(pygame.Surface((1920, 1080)))

# Shown ONCE: main.py checks the tracker every frame, so show() is reached on
# every frame after the battle ends and must not resurrect a dismissed box.
overlay.dismiss()
checks.eq("a click puts it away", overlay.is_pending, False)
overlay.show(mission)
checks.eq("...and it does not come back every frame", overlay.is_pending, False)

# An equal score is a draw, not a win for whoever is listed first.
drawn = MissionController(game_log=tk.Log())
drawn.primary_points["Player 1"] = drawn.primary_points["Player 2"] = 10
tie = BattleEndOverlay()
tie.show(drawn)
checks.eq("an equal score is a draw", tie._winner(), None)
tie.draw(pygame.Surface((1920, 1080)))

# The Secondary half counts toward the result, not just the Primary.
secondary_wins = MissionController(game_log=tk.Log())
secondary_wins.primary_points["Player 1"] = 10
secondary_wins.secondary_points["Player 1"] = 15
secondary_wins.primary_points["Player 2"] = 20
close = BattleEndOverlay()
close.show(secondary_wins)
checks.eq("Secondary VP decide the winner too", close._winner(), "Player 1")


# --- 3. wiring ---
print("--- 3. wiring ---")

MAIN = io.open("main.py", encoding="utf-8").read()
TURN = io.open("game/turn.py", encoding="utf-8").read()

checks.true("the tracker owns the end condition", "self.battle_over = True" in TURN)
checks.true("...and refuses to advance afterwards",
            "if self.battle_over:" in TURN)
checks.true("...measured against the missions' own round count",
            "self.battle_round >= BATTLE_ROUNDS" in TURN)

checks.eq("main.py builds the overlay once", MAIN.count("battle_end_overlay = BattleEndOverlay()"), 1)
checks.eq("and raises it from one place", MAIN.count("battle_end_overlay.show(mission_controller)"), 1)
checks.true("checked as part of advancing the phase", "_check_battle_end()" in MAIN)

# ONE gate, read by both the human's button and the AI - a second opinion is
# exactly the drift this codebase keeps removing.
gate = MAIN[MAIN.index("def _has_unresolved_declaration"):]
gate = gate[:gate.index("\n    def ")]
checks.true("the shared phase-advance gate stops on it", "turn_tracker.battle_over" in gate)

# It has to outrank every other notice: nothing behind it can be acted on.
# Sliced down to the TUPLE, not the whole function: the comment above it names
# several overlays too, and comparing against those measures prose rather than
# priority.
front = MAIN[MAIN.index("def _front_notice():"):]
front = front[:front.index("def _check_battle_end():")]
tuple_src = front[front.index("for overlay in ("):front.index("if overlay.is_pending")]
checks.true("the result overlay is in the notice tuple", "battle_end_overlay" in tuple_src)
others = [n for n in ("fight_warning_overlay", "turn_start_overlay", "turn_plan_overlay",
                      "mission_draw_overlay", "stratagem_notice_overlay",
                      "waaagh_notice_overlay") if n in tuple_src]
checks.true("the tuple really lists the other notices", len(others) >= 4)
checks.true("...and the result overlay comes first in it",
            all(tuple_src.index("battle_end_overlay") < tuple_src.index(n) for n in others))
checks.eq("and a click dismisses it", MAIN.count("battle_end_overlay.dismiss()"), 1)

checks.finish()
