"""THE LAST TURN END: can a Secondary card whose only instant IS the end of the
battle actually pay?

Three of the seventeen Tactical cards score at exactly one moment - "the end of
your opponent's turn in the final battle round" (Beacon, Burden of Trust,
Defend Stronghold). Whenever the card player takes the FIRST turn of the round,
that moment is the last turn end of the whole battle, and main.py used to raise
the result box in the same advance_turn_phase() that opened the card's scoring
PROMPT. That cost the card twice over:

  - BattleEndOverlay.show() FREEZES the numbers it displays, so the final score
    was missing the VP;
  - _front_notice() puts that overlay ahead of the decision box, and main.py
    draws the decision overlay only when _front_notice() is None - so the
    prompt behind it could never be answered either.

Reported as "defend stronghold wurde mir nicht zugerechnet, obwohl ich meine
homeobjective die ganze zeit hatte".

WHY IT HAD NO TEST. test_secondary_missions.py owns the CARDS and never touches
main.py's ordering; the smokes never reach round 5. The failure needs both
halves in one place, which is what this suite is - and why it drives the real
BattleEndOverlay rather than a stub, since the frozen snapshot is half the
defect.

NAMED LIMIT, so nobody reads more into section 2 than is there. Its
check_battle_end() is main.py's gate in SHAPE, not main.py's own closure -
_check_battle_end() is defined inside main(), which no suite runs. So section 2
proves the CONTRACT (hold, answer, then freeze a score that includes the card)
and section 4 proves main.py follows it, by AST rather than by name count. No
runtime probe: reaching the last turn end takes a full five rounds, and a
MockAgent selfplay run manages roughly seven phase changes in three thousand
frames against the fifty a battle needs - measured, not assumed.

A/B at the source (ab_per_unit_offer.py): drop "and not
decision_manager.is_pending" from _check_battle_end() -> section 4 falls; drop
the per-frame call -> it falls too; drop both -> three checks fall.
"""

import ast
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((320, 240))

import testkit as tk  # noqa: E402
from game import config, maps, secondary_missions as sm  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.missions import BATTLE_ROUNDS, MissionController  # noqa: E402
from game.turn import TurnTracker  # noqa: E402
from game.ui.battle_end_overlay import BattleEndOverlay  # noqa: E402
from game.factions import aeldari as ae  # noqa: E402

checks = tk.Checks("Final-round Secondary scoring")

config.SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)


# --- 1. Which cards live on this instant ----------------------------------
print("\n1. The cards whose only instant is the last turn end")

# Every card OBJECT the module defines, not just the ones the deck deals:
# Burden of Trust is built and deliberately withheld from ALL_CARDS, and it
# carries this timing too - so a set read off the deck would quietly cover two
# of the three.
ALL_BUILT = [v for v in vars(sm).values() if isinstance(v, sm.SecondaryMissionCard)]
FINAL_ROUND_CARDS = [c for c in ALL_BUILT
                     if c.timing == sm.TIMING_END_OF_OPPONENT_TURN_FINAL_ROUND]
# A NAMED SET, not a count: a fourth card put on this timing inherits the
# ordering problem, and has to move this line to get in.
checks.eq("three cards score at the end of the enemy's final turn",
          sorted(c.key for c in FINAL_ROUND_CARDS),
          ["beacon", "burden_of_trust", "defend_stronghold"])
checks.eq("...two of them are actually dealt",
          sorted(c.key for c in FINAL_ROUND_CARDS if c in sm.ALL_CARDS),
          ["beacon", "defend_stronghold"])
checks.true("...and the collapsed bar tells the player which round that is",
            "round %d" % BATTLE_ROUNDS in sm.TIMING_LABELS[
                sm.TIMING_END_OF_OPPONENT_TURN_FINAL_ROUND])


# --- 2. A card genuinely complete, at the last turn end -------------------
print("\n2. Defend Stronghold, held all battle, at the last turn end")

bmap = maps.get("map2")
maps.apply_to_config(bmap)
board = GameState()
bmap.build(board)

HOME = sm.own_home_objective(sm.MissionContext(
    "Player 1", objectives=board.objectives, deployment_zones=board.deployment_zones))
checks.true("map2 gives Player 1 a home objective", HOME is not None)


class _Silent:
    def enqueue(self, player, cards, details=None):
        pass


def scene(cards, holder="Player 1"):
    """The real controller, the real ledger and the real result overlay, with
    one friendly unit on the home objective and no enemy in the zone - so the
    card is worth its full 5 VP rather than merely non-zero."""
    HOME.controlled_by = holder
    HOME.secured_by = None
    mine = tk.build(ae.RANGERS, owner="Player 1", name="1 Rangers 1")
    cx, cy = sm.objective_centre(HOME)
    for i, model in enumerate(mine.models):
        model.x_in, model.y_in = cx + i * 1.2, cy
    log = tk.Log()
    mission = MissionController(game_log=log)
    decision = DecisionManager()
    turn = TurnTracker(game_log=tk.Log())
    ctrl = sm.SecondaryMissionController(
        player="Player 1", mission_controller=mission,
        command_points=CommandPointManager(game_log=log),
        decision_manager=decision, turn_tracker=turn, game_log=log,
        draw_overlay=_Silent(), cards=list(cards))
    tokens = list(mine.models)
    ctrl.set_tokens_source(lambda: tokens)
    ctrl.set_objectives_source(lambda: board.objectives)
    ctrl.set_zones_source(lambda: board.deployment_zones)
    ctrl.draw_at_command_phase("Player 1", 2)
    return ctrl, mission, decision, BattleEndOverlay(), tokens


def check_battle_end(overlay, mission, decision, battle_over=True):
    """main.py's _check_battle_end(), in shape: the result waits while any
    question is still open."""
    if battle_over and not decision.is_pending:
        overlay.show(mission)


ctrl, mission, decision, overlay, tokens = scene([sm.DEFEND_STRONGHOLD])
checks.eq("the card is in hand from round 2",
          [c.name for c in ctrl.hand], ["Defend Stronghold"])
checks.eq("it is worth its full 5 VP on this board",
          sm._defend_stronghold(sm.MissionContext(
              "Player 1", tokens=tokens, objectives=board.objectives,
              deployment_zones=board.deployment_zones)),
          sm.DEFEND_STRONGHOLD_CLEAR_VP)

# main.py's advance_turn_phase(): begin_end_of_turn() first, _check_battle_end()
# a few hundred lines later in the SAME call.
ctrl.begin_end_of_turn("Player 2", battle_round=BATTLE_ROUNDS)
checks.true("the last turn end opens the scoring prompt", decision.is_pending)
check_battle_end(overlay, mission, decision)
checks.eq("...and the result is held back while it is open", overlay.is_pending, False)
checks.eq("...so nothing has been frozen yet", overlay._result, None)

labels = [o["label"] for o in decision.options]
scoring = next(l for l in labels if l.startswith("Score"))
decision.choose(labels.index(scoring))
checks.eq("answering it credits the ledger",
          mission.secondary_points.get("Player 1", 0), sm.DEFEND_STRONGHOLD_CLEAR_VP)

# The per-frame call near the bottom of main()'s loop.
check_battle_end(overlay, mission, decision)
checks.true("the result appears the frame after", overlay.is_pending)
checks.eq("...and the score it froze INCLUDES the card",
          [row for row in overlay._result if row[0] == "Player 1"][0][2],
          sm.DEFEND_STRONGHOLD_CLEAR_VP)
checks.eq("...and the card is spent", ctrl.hand, [])


# --- 3. The gate does not stall an ordinary ending ------------------------
print("\n3. A battle with nothing left to answer still ends at once")

# Without this the fix would trade one silent failure for another: a result box
# that waits for a question nobody asked.
ctrl2, mission2, decision2, overlay2, _ = scene([sm.DEFEND_STRONGHOLD], holder="Player 2")
ctrl2.begin_end_of_turn("Player 2", battle_round=BATTLE_ROUNDS)
checks.eq("an unachieved card asks nothing", decision2.is_pending, False)
check_battle_end(overlay2, mission2, decision2)
checks.true("...so the result comes up in the same call", overlay2.is_pending)

# And a battle still running is not ended by the per-frame call either.
ctrl3, mission3, decision3, overlay3, _ = scene([sm.DEFEND_STRONGHOLD])
check_battle_end(overlay3, mission3, decision3, battle_over=False)
checks.eq("a battle still running raises nothing", overlay3.is_pending, False)


# --- 4. main.py really is wired that way ----------------------------------
print("\n4. main.py's own ordering")

main_src = io.open("main.py", encoding="utf-8").read()
gate = main_src[main_src.index("def _check_battle_end():"):]
gate = gate[:gate.index("def advance_turn_phase():")]
checks.true("_check_battle_end holds off while a decision is open",
            "turn_tracker.battle_over and not decision_manager.is_pending" in gate)
checks.true("...and still scores the Primary's final box before showing",
            gate.index("primary_mission_controller.score_end_of_battle()")
            < gate.index("battle_end_overlay.show(mission_controller)"))

# TWO call sites, and neither alone is enough: the one in advance_turn_phase()
# can now only ever hold, and the per-frame one alone would show the result a
# frame late in every battle.
# Counted through the AST, not with str.count(): the name also appears in its
# own def line and in a comment, and a guard that counts MENTIONS is the exact
# weakness this repo has already been bitten by twice.
_calls = [n for n in ast.walk(ast.parse(main_src))
          if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
          and n.func.id == "_check_battle_end"]
checks.eq("it is called twice", len(_calls), 2)
turn_end_marker = "        # Rule 07.01: did that turn end the battle?\n        _check_battle_end()"
checks.true("one call is at the turn end", turn_end_marker in main_src)
frame_marker = "        _check_battle_end()\n\n        # `turn_tracker.started` gates the whole block"
checks.true("...and the other is polled per frame, outside the event chain",
            frame_marker in main_src)

# The reason the gate is needed at all: this overlay owns the screen, and the
# decision box waits behind every notice.
front = main_src[main_src.index("def _front_notice():"):]
front = front[:front.index("def _check_battle_end():")]
checks.true("battle_end_overlay leads the notice order",
            front.index("battle_end_overlay") < front.index("mission_draw_overlay"))

checks.finish()
