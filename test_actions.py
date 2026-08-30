"""Rule 16.01 (PERFORMING ACTIONS) - game/actions.py, the generic framework,
plus its first user: the Secondary Mission card "Cleanse".

This engine had no Actions concept at all until this card needed one, so the
whole rule is transcribed here from the core rulebook text the user supplied
and every clause of it gets its own check. Three parts are easy to build and
easy to get subtly wrong:

  - the SEVEN start-eligibility conditions. Each is checked on its own, with
    the others satisfied, so a missing one cannot hide behind a passing sibling.
  - the two LOCKS. "Not eligible to shoot" carries a TITANIC exception,
    "not eligible to declare a charge" does not - the asymmetry is printed and
    is pinned below. Both survive the action being cancelled by a move: the
    unit still STARTED one this turn, which is what the rule keys on.
  - the CANCELLATION clause. A move stops an action completing, EXCEPT a
    pile-in or a consolidation. Passing the move's own kind by name rather
    than inferring it is what makes those two exceptions real.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from game import config, maps, secondary_missions as sm  # noqa: E402
from game.actions import ActionController, start_eligibility  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING  # noqa: E402
from game.factions import aeldari as ae  # noqa: E402

checks = tk.Checks("Actions (16.01)")

config.SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)
_map = maps.MAPS["map2"]
maps.apply_to_config(_map)
board = GameState()
_map.build(board)
CENTRAL = next(o for o in board.objectives if o.name == "Central Objective")
WEST = next(o for o in board.objectives if o.name == "Objective West")
MY_HOME = next(o for o in board.objectives if o.name == "P1 Home Objective")


def unit_on(objective, name, owner="Player 1"):
    ox, oy = sm.objective_centre(objective)
    squad = tk.build(ae.RANGERS, owner=owner, name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = ox + i * 1.2, oy
    return squad


def mission_ctx(tokens):
    return sm.MissionContext("Player 1", tokens=tokens, objectives=board.objectives,
                             deployment_zones=board.deployment_zones)


def controller(tokens, movement_controller=None):
    return ActionController(tokens_source=lambda: tokens, game_log=tk.Log(),
                            movement_controller=movement_controller)


# --- 1. the seven start-eligibility conditions ---
print("--- 1. start eligibility ---")

squad = unit_on(CENTRAL, "1 Rangers A")
tokens = list(squad.models)
ok, reason = start_eligibility(squad, tokens)
checks.true("a clean unit is eligible", ok)
checks.eq("...with no reason to refuse", reason, None)


def refusal(mutate, restore=None):
    mutate()
    result = start_eligibility(squad, tokens)
    if restore:
        restore()
    return result


ok, reason = refusal(lambda: setattr(squad, "battle_shocked", True),
                     lambda: setattr(squad, "battle_shocked", False))
checks.eq("battle-shocked is refused", ok, False)
checks.true("...and says why", "battle-shock" in (reason or ""))

ok, reason = refusal(lambda: setattr(squad, "fell_back_this_turn", True),
                     lambda: setattr(squad, "fell_back_this_turn", False))
checks.eq("Fell Back this turn is refused", ok, False)
checks.true("...and says why", "Fell Back" in (reason or ""))

# Not on the battlefield: the token list is the board, so a unit absent from it
# is off it. Both halves of the condition are checked - an emptied unit too.
ok, _ = start_eligibility(squad, [])
checks.eq("a unit not on the battlefield is refused", ok, False)
wiped = unit_on(CENTRAL, "1 Rangers Z")
wiped.models[:] = []
checks.eq("a wiped-out unit is refused", start_eligibility(wiped, tokens)[0], False)

# OC 0 - the Heavy Weapon Platform is the engine's own OC 0 model, so this uses
# a real datasheet rather than a doctored profile.
platform = tk.build(ae.GUARDIAN_DEFENDERS, owner="Player 1", name="1 Guardian Defenders 1")
oc_zero = [m for m in platform.models if m.profile.oc <= 0]
checks.true("the roster really has an OC 0 model", bool(oc_zero))
solo = unit_on(CENTRAL, "1 Platform 1")
solo.models[:] = oc_zero[:1]
checks.eq("an OC 0 unit is refused", start_eligibility(solo, list(solo.models))[0], False)

# Engaged (03.04). Built by putting an enemy model in engagement range.
enemy = unit_on(CENTRAL, "2 Rangers 1", owner="Player 2")
for model in enemy.models:
    model.x_in, model.y_in = squad.models[0].x_in + 0.5, squad.models[0].y_in
ok, reason = start_eligibility(squad, tokens + list(enemy.models))
checks.eq("an engaged unit is refused", ok, False)
checks.true("...and says why", "engaged" in (reason or ""))
for model in enemy.models:
    model.x_in += 40  # out of the way again

# Advanced this turn - read from the movement controller, the same set
# game/charge.py already consults.
class FakeMovement:
    def __init__(self, advanced=()):
        self.advanced_squad_ids = set(advanced)


ok, reason = start_eligibility(squad, tokens, FakeMovement([squad]))
checks.eq("a unit that Advanced is refused", ok, False)
checks.true("...and says why", "Advanced" in (reason or ""))
checks.true("a unit that did not Advance is fine",
            start_eligibility(squad, tokens, FakeMovement())[0])

# Already started an action this turn.
ac = controller(tokens)
ac.start(sm.CLEANSE_ACTION, squad, CENTRAL, mission_ctx(tokens))
ok, reason = start_eligibility(squad, tokens, None, ac.states)
checks.eq("a second action in the same turn is refused", ok, False)
checks.true("...and says why", "already started" in (reason or ""))


# --- 2. the two locks, and their printed asymmetry ---
print("--- 2. the locks ---")

ac = controller(tokens)
checks.eq("before starting, nothing is locked", ac.blocks_shooting(squad), False)
ac.start(sm.CLEANSE_ACTION, squad, CENTRAL, mission_ctx(tokens))
checks.true("a unit performing an action cannot shoot", ac.blocks_shooting(squad))
checks.true("...nor declare a charge", ac.blocks_charge(squad))

# Both locks last "until the end of the turn" and key on having STARTED an
# action - so a move that cancels the action does NOT hand the shooting back.
ac.notify_move(squad, None)
checks.true("a cancelled action still blocks shooting", ac.blocks_shooting(squad))
checks.true("...and still blocks the charge", ac.blocks_charge(squad))
ac.reset_for_turn()
checks.eq("the end of the turn clears both", ac.blocks_shooting(squad), False)

# The asymmetry: the shooting lock excludes TITANIC, the charge lock does not.
# No datasheet here carries the keyword, so it is set on a throwaway profile
# copy - the point is that the code reads it, not that a unit has it.
titanic = unit_on(CENTRAL, "1 Titan 1")
titanic.models[0].profile = type("T", (type(titanic.models[0].profile),), {"titanic": True})()
ac2 = controller(list(titanic.models))
ac2.start(sm.CLEANSE_ACTION, titanic, CENTRAL, mission_ctx(list(titanic.models)))
checks.eq("a TITANIC unit may still shoot", ac2.blocks_shooting(titanic), False)
checks.true("but still may not charge", ac2.blocks_charge(titanic))


# --- 3. cancellation: which moves break an action ---
print("--- 3. cancellation ---")


def after_move(move_kind):
    squad_ = unit_on(CENTRAL, "1 Rangers M")
    toks = list(squad_.models)
    CENTRAL.controlled_by = "Player 1"
    ctrl = controller(toks)
    ctrl.start(sm.CLEANSE_ACTION, squad_, CENTRAL, mission_ctx(toks))
    if move_kind is not False:
        ctrl.notify_move(squad_, move_kind)
    return len(ctrl.resolve_end_of_turn("Player 1", mission_ctx(toks)))


checks.eq("no move at all: completes", after_move(False), 1)
checks.eq("a Normal move cancels it", after_move(None), 0)
checks.eq("a charge move cancels it", after_move("charge"), 0)
checks.eq("a Fall Back move cancels it", after_move("fall_back"), 0)
# The two printed exceptions.
checks.eq("a PILE-IN does not cancel it", after_move("pile_in"), 1)
checks.eq("a CONSOLIDATION does not cancel it", after_move("consolidate"), 1)


# --- 4. Cleanse's own five lines ---
print("--- 4. the Cleanse action ---")

checks.eq("STARTS in the Shooting phase", sm.CLEANSE_ACTION.starts, PHASE_SHOOTING)

on_central = unit_on(CENTRAL, "1 Rangers A")
on_home = unit_on(MY_HOME, "1 Rangers H")
far = unit_on(CENTRAL, "1 Rangers F")
for model in far.models:
    model.x_in += 40
all_tokens = list(on_central.models) + list(on_home.models) + list(far.models)
ctx = mission_ctx(all_tokens)

# UNITS: "One friendly unit within range of an objective (excl. your home
# objective)". Singular possessive - the ENEMY's home objective is fair game.
checks.true("a unit on a non-home objective qualifies", sm.cleanse_units(on_central, ctx))
checks.eq("a unit on YOUR OWN home objective does not", sm.cleanse_units(on_home, ctx), False)
checks.eq("a unit near no objective does not", sm.cleanse_units(far, ctx), False)
enemy_home = next(o for o in board.objectives if o.name == "P2 Home Objective")
on_enemy_home = unit_on(enemy_home, "1 Rangers E")
checks.true("but the ENEMY's home objective is a legal target",
            sm.cleanse_units(on_enemy_home, mission_ctx(list(on_enemy_home.models))))

# USE LIMIT: "Unlimited. Each unit must be within range of a different
# objective." - a cap on the TARGET, not on the number of actions.
second = unit_on(CENTRAL, "1 Rangers B")
tokens2 = list(on_central.models) + list(second.models)
ctrl = controller(tokens2)
ctrl.start(sm.CLEANSE_ACTION, on_central, CENTRAL, mission_ctx(tokens2))
checks.eq("a second unit cannot take the same objective",
          sm.cleanse_use_limit(ctrl.states, second, CENTRAL, mission_ctx(tokens2)), False)
checks.true("but may take a different one",
            sm.cleanse_use_limit(ctrl.states, second, WEST, mission_ctx(tokens2)))
checks.eq("and there is no cap on how many actions run at once",
          sm.CLEANSE_ACTION.use_limit_allows(ctrl.states, second, WEST, mission_ctx(tokens2)), True)

# COMPLETES: "End of your turn, if that unit controls that objective."
def completes(control, move_away=False):
    squad_ = unit_on(CENTRAL, "1 Rangers C")
    toks = list(squad_.models)
    CENTRAL.controlled_by = control
    ctrl_ = controller(toks)
    state = ctrl_.start(sm.CLEANSE_ACTION, squad_, CENTRAL, mission_ctx(toks))
    if move_away:
        for model in squad_.models:
            model.x_in += 40
    return sm.cleanse_completes(state, mission_ctx(toks))


checks.true("completes while you control the objective", completes("Player 1"))
checks.eq("not if the enemy controls it", completes("Player 2"), False)
checks.eq("not if nobody controls it", completes(None), False)
checks.eq("not if the unit is no longer in range", completes("Player 1", move_away=True), False)
CENTRAL.controlled_by = "Player 1"


# --- 5. the card: 2 VP for one, 5 for two or more ---
print("--- 5. the Cleanse card ---")


def cleanse_vp(count):
    return sm._cleanse(sm.MissionContext(
        "Player 1", card_state={"cleansed_this_turn": [CENTRAL] * count}))


checks.eq("nothing cleansed: nothing", cleanse_vp(0), 0)
checks.eq("one objective: 2 VP", cleanse_vp(1), sm.CLEANSE_ONE_VP)
checks.eq("two objectives: 5 VP", cleanse_vp(2), sm.CLEANSE_MANY_VP)
checks.eq("three: still 5 VP", cleanse_vp(3), sm.CLEANSE_MANY_VP)
checks.true("Cleanse scores at the end of YOUR turn",
            sm.CLEANSE.scores_at(sm.MissionContext("Player 1", ending_player="Player 1")))
checks.true("it is the first card that needs an action", sm.CLEANSE.requires_action)
checks.true("and it carries the definition", sm.CLEANSE.action is sm.CLEANSE_ACTION)
# "If you have Plunder active" - this was a documented no-op while Plunder did
# not exist, pinned so that adding it would be a VISIBLE change here. It was:
# the two lines below are the flipped versions of that pin.
checks.true("Plunder now ships in the deck",
            any(c.key == "plunder" for c in sm.ALL_CARDS))
checks.true("so Cleanse's clause is live when Plunder is in hand",
            sm.CLEANSE.when_drawn_may_redraw(
                sm.MissionContext("Player 1", hand=[sm.PLUNDER])))
checks.eq("...and still inert when it is not",
          sm.CLEANSE.when_drawn_may_redraw(
              sm.MissionContext("Player 1", hand=[sm.CENTRE_GROUND])), False)
# The mirror: Plunder offers to step aside for Cleanse in the same way, and
# both are Objective Action cards - a hand never has to carry both.
checks.true("Plunder prints the mirror clause",
            sm.PLUNDER.when_drawn_may_redraw(
                sm.MissionContext("Player 1", hand=[sm.CLEANSE])))
checks.true("both are Objective Action cards",
            sm.PLUNDER.requires_action and sm.CLEANSE.requires_action)
# Their COMPLETES lines differ, which is the whole reason 16.01 needed an
# immediate path at all.
checks.true("Plunder completes immediately", sm.PLUNDER_ACTION.completes_immediately)
checks.eq("Cleanse completes at the end of the turn",
          sm.CLEANSE_ACTION.completes_immediately, False)


# --- 6. end to end, through the real controllers ---
print("--- 6. end to end ---")

from game.command_points import CommandPointManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.missions import MissionController  # noqa: E402
from game.turn import TurnTracker  # noqa: E402

a = unit_on(CENTRAL, "1 Rangers A")
b = unit_on(WEST, "1 Rangers B")
toks = list(a.models) + list(b.models)
for objective in board.objectives:
    objective.controlled_by = "Player 1"

log = tk.Log()
decision = DecisionManager()
actions = ActionController(tokens_source=lambda: toks, game_log=log)
mission = MissionController(game_log=log)
ctrl = sm.SecondaryMissionController(
    player="Player 1", mission_controller=mission,
    command_points=CommandPointManager(game_log=log), decision_manager=decision,
    turn_tracker=TurnTracker(game_log=tk.Log()), game_log=log, cards=[sm.CLEANSE])
ctrl.set_tokens_source(lambda: toks)
ctrl.set_objectives_source(lambda: board.objectives)
ctrl.set_zones_source(lambda: board.deployment_zones)
ctrl.set_action_controller(actions)
ctrl.hand = [sm.CLEANSE]

# Actions are PANEL BUTTONS, not a prompt. You pick the unit by selecting it,
# and the target by which button you press. User: "eigentlich sollte das kein
# prompt sein. actions sollten einfach links bei den aktionen auftauchen."
#
# The first version opened a DecisionManager chain at the start of the Shooting
# phase and marched the player through the eligible units in name order - so
# you could say WHETHER to act but never WITH WHOM, and with a once-per-turn
# action the first unit alphabetically simply took it.
turn_tracker = TurnTracker(game_log=tk.Log())
turn_tracker.phase_index = PHASES.index(PHASE_SHOOTING)
turn_tracker.turn_owner = "Player 1"
ctrl.turn_tracker = turn_tracker

offers_a = ctrl.available_actions_for(a)
offers_b = ctrl.available_actions_for(b)
checks.true("the unit standing on the central objective is offered it",
            any(CENTRAL.name in label for label, _a, _t in offers_a))
checks.true("and the other unit is offered ITS objective",
            any(WEST.name in label for label, _a, _t in offers_b))
checks.eq("nothing is asked - no prompt is opened", decision.is_pending, False)
checks.true("every offer names the action", all("Cleanse" in label for label, _a, _t in offers_a))

# Starting one is a direct call, and it is the SELECTED unit that acts.
label, action_def, target = next((o for o in offers_b if WEST.name in o[0]), (None, None, None))
checks.true("the second unit's own offer can be started", action_def is not None)
ctrl.start_action(action_def, b, target)
checks.eq("one action is running", len(actions.states), 1)
checks.eq("...started by the unit that was chosen", actions.states[0].squad.name, b.name)
checks.true("...on the target that was chosen", actions.states[0].target is WEST)

# USE LIMIT: Cleanse forbids the SAME objective twice, so the other unit is
# still offered its own - unlike a once-per-turn action, which would now be
# spent.
offers_a_now = ctrl.available_actions_for(a)
checks.true("the other unit can still act on a DIFFERENT objective",
            any(CENTRAL.name in label for label, _a, _t in offers_a_now))
checks.eq("...but not on the one already taken",
          any(WEST.name in label for label, _a, _t in offers_a_now), False)
label, action_def, target = next(o for o in offers_a_now if CENTRAL.name in o[0])
ctrl.start_action(action_def, a, target)
checks.eq("two actions are running", len(actions.states), 2)

# A unit that has started one is not offered another this turn (16.01).
checks.eq("a unit that already acted is offered nothing more",
          ctrl.available_actions_for(a), [])

ctrl.begin_end_of_turn("Player 1", battle_round=2)
checks.eq("both completed", len(ctrl.card_state["cleanse"]["cleansed_this_turn"]), 2)
checks.true("which opens the scoring prompt", decision.is_pending)
tk.pick_option(decision, "Score 5")
checks.eq("paying the two-or-more tier",
          mission.secondary_points.get("Player 1", 0), sm.CLEANSE_MANY_VP)

# Nothing is offered outside the action's own STARTS phase, or on the
# opponent's turn.
ctrl3 = sm.SecondaryMissionController(player="Player 1", cards=[sm.CLEANSE],
                                      turn_tracker=turn_tracker)
ctrl3.set_tokens_source(lambda: toks)
ctrl3.set_objectives_source(lambda: board.objectives)
ctrl3.set_zones_source(lambda: board.deployment_zones)
ctrl3.set_action_controller(ActionController(tokens_source=lambda: toks))
ctrl3.hand = [sm.CLEANSE]
checks.true("in your own Shooting phase there are offers",
            bool(ctrl3.available_actions_for(a)))
turn_tracker.turn_owner = "Player 2"
checks.eq("on the opponent's turn there are none", ctrl3.available_actions_for(a), [])
turn_tracker.turn_owner = "Player 1"
turn_tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
checks.eq("in the wrong phase there are none", ctrl3.available_actions_for(a), [])
turn_tracker.phase_index = PHASES.index(PHASE_SHOOTING)


# --- 7. wiring: the locks and hooks really exist in main.py ---
print("--- 7. wiring ---")

MAIN = io.open("main.py", encoding="utf-8").read()
checks.eq("main.py builds one ActionController",
          MAIN.count("action_controller = ActionController("), 1)
checks.true("the mission deck is given it",
            "secondary_mission_controller.set_action_controller(action_controller)" in MAIN)
checks.true("shooting reads the lock",
            "shooting_controller.action_controller = action_controller" in MAIN)
checks.true("charge reads the lock",
            "charge_controller.action_controller = action_controller" in MAIN)
checks.true("movement reports its moves",
            "movement_controller.action_controller = action_controller" in MAIN)
checks.true("and it knows about Advance moves",
            "action_controller.movement_controller = movement_controller" in MAIN)
# Actions are offered as PANEL BUTTONS for the selected unit, so what main.py
# has to do is hand the panel the controller - there is no phase hook any more.
checks.eq("main.py hands the mission controller to the panel",
          MAIN.count("secondary_mission_controller=secondary_mission_controller"), 1)
checks.eq("and no phase hook opens an action prompt",
          "offer_actions_at_shooting_phase(" in MAIN, False)
PANEL = io.open("game/ui/action_panel.py", encoding="utf-8").read()
checks.true("the panel asks which actions the selected unit could start",
            "secondary_mission_controller.available_actions_for(squad)" in PANEL)
checks.true("and its buttons start them",
            "secondary_mission_controller.start_action(a, sq, t)" in PANEL)
checks.true("and the turn ends by clearing it",
            "action_controller.reset_for_turn()" in MAIN)

# The reset must come AFTER the missions have resolved, or this turn's actions
# are thrown away before anything counts them.
end_block = MAIN[MAIN.index("if ending_player is not None:"):]
end_block = end_block[:end_block.index("if turn_tracker.phase == PHASE_COMMAND:")]
checks.true("the reset happens after the end-of-turn scoring",
            end_block.index("begin_end_of_turn(") < end_block.index("reset_for_turn()"))

# The two engine gates must actually consult it, not just hold a reference.
SHOOTING = io.open("game/shooting.py", encoding="utf-8").read()
CHARGE = io.open("game/charge.py", encoding="utf-8").read()
MOVEMENT = io.open("game/movement.py", encoding="utf-8").read()
checks.true("can_shoot() asks the controller",
            "self.action_controller.blocks_shooting(squad)" in SHOOTING)
checks.true("can_declare_charge() asks the controller",
            "self.action_controller.blocks_charge(squad)" in CHARGE)
checks.true("confirm_move() reports the move KIND, not just the move",
            "self.action_controller.notify_move(self.selected_squad, self.move_mode)" in MOVEMENT)

checks.finish()
