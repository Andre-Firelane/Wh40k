"""The HUMAN's Scout Move (24.32) needs a Confirm button, and the pre-game panel
was swallowing it.

User report: "nach meinem scout move kann ich nicht bestaetigen. es gibt keinen
knopf."

Everything else in that flow already worked, which is what made it hard to see
from the engine side: game/scouts.py raises the choice, MovementController runs
the move, dragging goes through InputManager, and main.py's event chain already
routes a left-panel click to ActionPanel.handle_click(). The one missing piece
was a DRAWN button - _draw_dispatch()'s very first gate hands the whole panel to
_draw_pregame_ui() while rule 03.01 is running, and its PREBATTLE_ABILITIES
branch prints "Resolving pre-battle abilities..." and nothing else. So the move
could be made and never finished, and the pre-game could not be resumed at all.

Same shape as this project's other "the funnel is not the one it looks like"
bugs: a screen unreachable behind a state gate, invisible to any test that
drives the controller directly. Hence checks on what the PANEL actually offers,
through the real ActionPanel, not on what MovementController would accept.
"""
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from game import config, movement, pregame, shooting
from game.dice import DiceManager
from game.factions import aeldari as ae
from game.factions.datasheet import build_squad
from game.movement import MovementController
from game.turn import TurnTracker
from game.ui.action_panel import ActionPanel

c = tk.Checks("Scout Move - the human's Confirm button")


def section(title):
    print(f"\n--- {title} ---")


pygame.init()
pygame.display.set_mode((1200, 800))

HUMAN = "Player 1"


class StubPregame:
    """Only what ActionPanel's gate and its pre-game screen read. A stub rather
    than a real PregameController because the question here is what the PANEL
    does when the pre-game says "I am active and in the abilities step" - not
    how the pre-game got there (game/scouts.py covers that)."""

    is_active = True
    state = pregame.PREBATTLE_ABILITIES
    human_player = HUMAN
    active_player = HUMAN

    def army(self, owner):
        return []


def scene():
    state = tk.GameState()
    squad = build_squad(ae.RANGERS, HUMAN, name="1 Rangers 1")
    tk.line_up(squad, x=20.0, y=20.0)
    state.tokens = list(squad.models)
    turn = TurnTracker(deferred_start=True)   # rule 03.01: battle round 0
    dice = DiceManager()
    mover = MovementController(all_tokens=state.tokens, turn_tracker=turn, dice_manager=dice)
    shooter = shooting.ShootingController(turn_tracker=turn, all_tokens=state.tokens, dice_manager=dice)
    return state, squad, turn, mover, shooter


def button_names(panel, surface, rect, mover, shooter, pregame_controller):
    panel.draw(surface, rect, mover, shooter, pregame_controller=pregame_controller)
    return [getattr(callback, "__name__", repr(callback)) for _, callback in panel._buttons]


panel = ActionPanel()
surface = pygame.Surface((1200, 800))
rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 700)


# ------------------------------------------------- 1. the reported case
section("1. a scout move during the pre-game")

state, squad, turn, mover, shooter = scene()
mover.start_scout_move(squad, 6.0)
c.eq("the move really is under way", mover.state, movement.MOVING)
c.eq("...in its own mode", mover.move_mode, "scout")

names = button_names(panel, surface, rect, mover, shooter, StubPregame())
c.true("Confirm is offered", any("confirm_move" in n for n in names))
c.true("Cancel is offered too", any("cancel_move" in n for n in names))
# Rule 24.32 grants "a Normal move of up to X inches" - not an Advance. The
# button would have appeared the moment the gate stopped swallowing this
# screen, and MovementController.start_run() would have added a D6 to it.
c.true("Advance is NOT offered", not any("start_run" in n for n in names))

# The Confirm has to be the one that ENDS the scout move, or the pre-game
# stays parked: MovementController.confirm_move() is what fires
# on_scout_move_finished, which is what resumes ScoutsStep's queue.
confirm = next((cb for r, cb in panel._buttons
                if getattr(cb, "__name__", "") == "confirm_move"), None)
c.true("Confirm routes to the movement controller",
       confirm is not None and getattr(confirm, "__self__", None) is mover)
resumed = []
mover.on_scout_move_finished = resumed.append
if confirm is not None:
    confirm()
c.eq("confirming ends the scout move and resumes the queue", len(resumed), 1)
c.eq("...naming the unit that moved", resumed[0].name if resumed else None, squad.name)


# -------------------------------------------- 2. the pre-game still owns idle
section("2. the pre-game keeps the panel when no move is in progress")

state, squad, turn, mover, shooter = scene()
names = button_names(panel, surface, rect, mover, shooter, StubPregame())
c.true("no movement buttons leak into the abilities step",
       not any("confirm_move" in n or "cancel_move" in n for n in names))
# The gate yields on movement.MOVING specifically, so the pre-game's own
# screens (formations, deploying) are untouched - checked at the source,
# because a stub cannot prove which branch drew.
panel_src = io.open("game/ui/action_panel.py", encoding="utf-8").read()
c.eq("the gate is the pre-game's, and yields for an in-progress move",
     panel_src.count("pregame_controller.is_active\n            and movement_controller.state != movement.MOVING"), 1)
c.eq("...and there is exactly one such gate",
     panel_src.count("pregame_controller.is_active"), 1)


# ------------------------------------------------ 3. can_advance(), one answer
section("3. can_advance() is the single definition")

state, squad, turn, mover, shooter = scene()

# The Movement phase's own move is the ONE mode that can become an Advance.
turn.start_battle(HUMAN)
while turn.phase != "Movement":
    turn.advance_phase()
mover.select(squad.models[0])
mover.start_move()
c.eq("an ordinary Movement-phase move has no named mode", mover.move_mode, None)
c.true("...and can Advance", mover.can_advance())
c.true("...so the button is offered",
       any("start_run" in n for n in button_names(panel, surface, rect, mover, shooter, None)))

# Every named mode is either not a move that can Advance at all, or a move
# something else granted whose printed text says "a Normal move".
for mode in ("scout", "charge", "pile_in", "consolidate", "surge", "fall_back",
             "torchstar", "tactical_acumen", "battle_focus", "path_of_the_outcast",
             "retro_thrusters"):
    mover.move_mode = mode
    c.true(f"{mode!r} cannot Advance", not mover.can_advance())
mover.move_mode = None

# ...and the panel asks that question instead of keeping its own list, which is
# how "scout" came to be missing from it in the first place.
c.eq("the panel reads can_advance()", panel_src.count("movement_controller.can_advance()"), 1)
c.eq("...and keeps no negated-mode list of its own",
     panel_src.count("not is_torchstar  # the stratagem grants"), 0)

# start_run() reads the same answer, so the rule is not UI-only.
move_src = io.open("game/movement.py", encoding="utf-8").read()
run_i = move_src.index("def start_run(self):")
c.true("start_run() gates on can_advance()",
       "if not self.can_advance():" in move_src[run_i:run_i + 200])

# And it really refuses: a scout move handed to start_run() must not grow a D6.
state, squad, turn, mover, shooter = scene()
mover.start_scout_move(squad, 6.0)
before = dict(mover.remaining_range)
mover.start_run()
c.true("start_run() does nothing to a scout move", not mover.run_used)
c.eq("...and adds no distance", mover.remaining_range, before)


c.finish()
