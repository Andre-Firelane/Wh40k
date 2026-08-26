"""SCOUTS (24.31/24.32): the HUMAN's half of the pre-battle move.

THE BUG THIS EXISTS FOR, reported by the user twice in the same words as the
Fade Back and Path of the Outcast reports - "die KI laesst mich nicht ... sie
macht einfach weiter" - but with a completely different cause, which is why
those two fixes did not cover it.

deployment_ai.resolve_scouts() returns False for a unit it does not own, and
its docstring says that means "a human's Scouts unit is left to the human".
Nothing implemented the other half. ScoutsStep._resolve_next() read False as
"declined", popped the unit, and drained the entire queue in ONE synchronous
loop - so a human's Striking Scorpions were logged as declining a move they
were never offered, and the pre-game walked straight past it.

A comment promising a behaviour that no code performs is the same class of
defect as a controller that is built and never fed (which this project has now
hit twice). So the checks below are about the PAUSE: does the queue actually
stop, is the choice actually raised, and does every way out of it resume.
"""

import testkit as tk
from testkit import Checks, GameState, options_of, pick_option
from ai import deployment_ai
from game import scouts
from game.decision import DecisionManager
from game.factions import aeldari as ae
from game.factions.datasheet import build_squad
from game.movement import MovementController

c = Checks("Scouts - the human's move")

HUMAN, AI = "Player 1", "Player 2"


class FakePregame:
    """Only the one method ScoutsStep calls, so "did the pre-game move on"
    is directly observable rather than inferred."""

    def __init__(self):
        self.finished = False

    def finish_prebattle_abilities(self):
        self.finished = True


def scene(owner=HUMAN, sheet=ae.STRIKING_SCORPIONS, name=None, wire_human=True):
    state = GameState()
    squad = build_squad(sheet, owner, name=name or f"{owner[-1]} {sheet.name} 1")
    tk.line_up(squad, x=20.0, y=20.0)
    state.tokens = list(squad.models)
    mc = MovementController(all_tokens=state.tokens)
    dm = DecisionManager()
    step = scouts.ScoutsStep(
        movement_controller=mc, game_log=tk.Log(),
        on_resolve=lambda pre, sq, br, d: deployment_ai.resolve_scouts(pre, sq, br, d),
        decision_manager=dm if wire_human else None,
        human_players=(HUMAN,) if wire_human else (),
    )
    mc.on_scout_move_finished = step.on_scout_move_finished
    pre = FakePregame()
    step._pregame = pre
    step._queue = [(squad, "scout_move")]
    return dict(state=state, squad=squad, mc=mc, dm=dm, step=step, pre=pre)


# --- 1. the unit really does have the ability -------------------------------
print("--- 1. the premise ---")

scorpions = build_squad(ae.STRIKING_SCORPIONS, HUMAN, name="1 Striking Scorpions 1")
c.eq("Striking Scorpions print SCOUTS 7in", scouts.scout_distance(scorpions), 7)
c.eq("the AI declines to touch a unit it does not own - which is correct, and "
     "was the whole trap: 'declined by the AI' is not 'declined by the human'",
     deployment_ai.resolve_scouts(None, scorpions, "scout_move", 7.0), False)


# --- 2. the queue PAUSES for a human ----------------------------------------
print("--- 2. the pause ---")

s = scene()
s["step"]._resolve_next()
c.eq("the pre-game does NOT advance past a human's Scouts unit", s["pre"].finished, False)
c.eq("...the step reports itself pending", s["step"].is_pending, True)
c.eq("...and a real choice is raised", s["dm"].is_pending, True)
c.eq("with both ways out offered", options_of(s["dm"]),
     ['Scout Move (up to 7")', "Decline"])


# --- 3. taking the move ------------------------------------------------------
print("--- 3. taking it ---")

s = scene()
s["step"]._resolve_next()
pick_option(s["dm"], "Scout Move")
c.eq("choosing it opens a real scout move", s["mc"].move_mode, "scout")
c.eq("...on the right unit", s["mc"].selected_squad is s["squad"], True)
c.eq("...and the pre-game is STILL waiting while the human drags",
     s["pre"].finished, False)
s["mc"].confirm_move()
c.eq("confirming resumes the queue", s["pre"].finished, True)
c.eq("...and clears the pending slot", s["step"].is_pending, False)


# --- 4. every other way out also resumes ------------------------------------
print("--- 4. declining and cancelling ---")

s = scene()
s["step"]._resolve_next()
pick_option(s["dm"], "Decline")
c.eq("declining resumes the queue", s["pre"].finished, True)
c.eq("...and moves nothing", s["mc"].move_mode, None)

# A CANCELLED move is the one that would strand the pre-game if the hook only
# fired on confirm - the human opens the move, changes their mind, and nothing
# would ever pop the unit.
s = scene()
s["step"]._resolve_next()
pick_option(s["dm"], "Scout Move")
c.eq("a cancelled move still ends it", (s["mc"].cancel_move(), s["pre"].finished)[1], True)
c.eq("...and the models are back where they started", s["step"].is_pending, False)


# --- 5. the AI's own units are untouched by any of this ---------------------
print("--- 5. the AI side is unchanged ---")

ai_scene = scene(owner=AI, sheet=ae.SHROUD_RUNNERS, name="2 Shroud Runners 1")
ai_scene["step"]._resolve_next()
c.eq("an AI unit is never offered to the human",
     ai_scene["dm"].is_pending, False)
c.eq("...and the queue drains without pausing", ai_scene["step"].is_pending, False)

# ...and with no human wired at all (a headless harness), the old behaviour
# stands: nothing pauses, which is what keeps every existing caller working.
bare = scene(wire_human=False)
bare["step"]._resolve_next()
c.eq("with no decision_manager the step declines rather than hanging",
     (bare["pre"].finished, bare["step"].is_pending), (True, False))


# --- 6. A/B: the fix is what does it ----------------------------------------
print("--- 6. A/B ---")

s = scene()
_offer = scouts.ScoutsStep._offer_to_human
try:
    scouts.ScoutsStep._offer_to_human = lambda self, squad, branch, distance: False
    s["step"]._resolve_next()
    c.eq("A/B: without the human offer the pre-game walks straight past it - "
         "exactly the reported bug",
         (s["pre"].finished, s["dm"].is_pending), (True, False))
finally:
    scouts.ScoutsStep._offer_to_human = _offer

s2 = scene()
s2["step"]._resolve_next()
c.eq("...and restored, it waits again",
     (s2["pre"].finished, s2["dm"].is_pending), (False, True))


# --- 7. the wiring reaches main.py ------------------------------------------
print("--- 7. wiring ---")

import pathlib
_main = pathlib.Path("main.py").read_text(encoding="utf-8")
c.true("ScoutsStep is given a decision_manager", "decision_manager=decision_manager," in _main)
c.true("...and told who the human is", 'human_players=("Player 1",)' in _main)
c.true("...and the move-finished hook is connected",
       "movement_controller.on_scout_move_finished = (" in _main)

# --- 8. the printed eligibility, and why an INFILTRATORS unit is refused ----
print("--- 8. 24.31/24.32 eligibility ---")

# User-supplied printed text, which settles this - it says "wholly within your
# deployment zone" TWICE, once as 24.31's second bullet and again as 24.32's
# own ELIGIBLE IF. So a unit outside its zone genuinely cannot scout, and the
# Striking Scorpions reported as "not offered" were correctly refused rather
# than skipped by a bug. What WAS wrong is that nothing said so.
from game import deployment
from game.squad import SCOUT_MOVE_MIN_ENEMY_DISTANCE_IN


class FakeState:
    def __init__(self, zones):
        self.deployment_zones = zones
        self.reserves = []


class FakePregameArmy:
    def __init__(self, state, squads):
        self.game_state = state
        self._squads = squads

    def army(self, owner):
        return [s for s in self._squads if s.owner == owner]


zone_state = GameState()
scorp = build_squad(ae.STRIKING_SCORPIONS, HUMAN, name="1 Striking Scorpions 9")
tk.line_up(scorp, x=20.0, y=20.0)
zones = getattr(zone_state, "deployment_zones", ())
c.true("Striking Scorpions print BOTH Scouts and Infiltrators - the pairing "
       "that makes the printed conditions collide",
       scouts.has_scouts(scorp)
       and any(m.profile.infiltrators for m in scorp.models))

log = tk.Log()
pre = FakePregameArmy(FakeState(zones), [scorp])
offered = scouts.eligible_units(pre, HUMAN, log)
c.eq("a unit outside its deployment zone is offered no scout move (24.32's "
     "own ELIGIBLE IF)", offered, [])
c.true("...and the reason is LOGGED rather than silent - which is the half "
       "that actually looked like a bug",
       log.has("NOT wholly within its deployment zone"))
c.true("...naming INFILTRATORS, so the pairing that causes it is explicit",
       log.has("INFILTRATORS"))

c.eq("24.32 AFTER MOVING: more than 8in horizontally from all enemy units",
     SCOUT_MOVE_MIN_ENEMY_DISTANCE_IN, 8.0)
# ...and the same unit IS offered one once it is inside a zone that contains
# it - the exclusion is about the POSITION, not about the datasheet.
class WholeBoardZone:
    owner = HUMAN

    def contains_circle(self, x_in, y_in, r_in):
        return True


inside = FakePregameArmy(FakeState([WholeBoardZone()]), [scorp])
c.eq("the very same unit IS offered a scout move once it is inside its zone - "
     "so the refusal is about POSITION, not about the datasheet",
     [b for _, b in scouts.eligible_units(inside, HUMAN)], ["scout_move"])

c.finish()
