"""Two AI behaviours reported after logs/game_20260908_204854.log.

  1. "der grosse necron warrior squad hat den avatar of khaine gecharged. das
     sollte er lieber nicht machen."
     That log's own line 667:
       [charge] 2 Necron Warriors 1 + Technomancer -> 1 Avatar of Khaine 1:
                4" roll, closed to 1.0" (engaged: True)
     and what it bought, four lines later: 2 of 21 models in engagement range,
     Staff of Light and Close Combat Weapon both rolling zero wounds.

  2. "die necrons kommen immer nicht so richtig von ihrem home objective weg.
     sowohl necron warriors als auch immortals klumpen auf dem home objective
     und koennen sich von da aus keine guten schusspositionen erarbeiten."
     Measured off the same log's [move detail] lines, per-turn centroids:
       Necron Warriors + Technomancer   T1 (32,4)  T2 (33,6)  then never again
       Immortals 1 + Plasmancer         T1 (29,9)  then never again
       Immortals 2 + Plasmancer         T1 (13,13) then never again
     - 43 models, two inches of ground in five turns, while every other unit
     in the army advanced.

THE TWO ARE THE SAME STORY. The blob spent turns 4 and 5 locked in the melee
that report 1 is about, so fixing the charge gives report 2 two of its five
turns back on its own.

Every section carries an A/B against the pre-fix behaviour - see
ab_report_20260908.py, which neutralises each half at the source.
"""

import ast
import io
import math
import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from testkit import Checks, GameState, TurnTracker, build_squad, script

from ai import agent_driver, observation
from ai.base import Agent
from game import attached_units, combat_focus, config, geometry, maps
from game.charge import ChargeController
from game.dice import DiceManager
from game.factions import aeldari as ael, necrons as nec
from game.movement import MovementController
from game.turn import PHASE_CHARGE, PHASE_MOVEMENT, PHASES

c = Checks("report 2026-09-08 (the Avatar charge, and the home-objective clump)")

WARRIORS = "2 Necron Warriors 1 + Technomancer"
IMMORTALS = "2 Immortals 1 + Plasmancer"
HOME = "P2 Home Objective"


class Log:
    def __init__(self):
        self.lines = []

    def add(self, line, **kwargs):
        self.lines.append(line)


def necron_blob(name=WARRIORS):
    """The reported unit: 20 Necron Warriors with a Technomancer merged in
    (rule 19.01), which is what the log's 21 models are."""
    body = build_squad(nec.NECRON_WARRIORS, "Player 2", unit_index=1, composition_index=1)
    lead = build_squad(nec.TECHNOMANCER, "Player 2", unit_index=1)
    squad = attached_units.attach(lead, body)
    squad.name = name
    return squad


def immortals(name=IMMORTALS):
    body = build_squad(nec.IMMORTALS, "Player 2", unit_index=1, composition_index=1)
    lead = build_squad(nec.PLASMANCER, "Player 2", unit_index=1)
    squad = attached_units.attach(lead, body)
    squad.name = name
    return squad


def avatar():
    squad = build_squad(ael.AVATAR_OF_KHAINE, "Player 1", unit_index=1)
    squad.name = "1 Avatar of Khaine 1"
    return squad


def dire_avengers():
    squad = build_squad(ael.DIRE_AVENGERS, "Player 1", unit_index=1)
    squad.name = "1 Dire Avengers 1"
    return squad


# ===========================================================================
# 1. the charge is VALUED, and the two numbers separate the reported case
# ===========================================================================
# game/damage_estimate.py's own estimate, reached through the same
# ai/observation.py wrappers the planner is given. Not a new measurement - the
# whole finding is that these numbers already existed and only the planner
# ever saw them.

blob, av, da = necron_blob(), avatar(), dire_avengers()

c.eq("scene check: the reported unit really is 21 models", len(blob.models), 21)

avatar_note = agent_driver._charge_trade_note(blob, av)
avengers_note = agent_driver._charge_trade_note(blob, da)

c.true("the note says what the charge removes", "would remove about" in avatar_note)
c.true("...and what it costs, for as long as the fight lasts",
       "back for as long as the fight lasts" in avatar_note)

# The separation itself, which is the reason the note is worth printing.
avatar_kills = observation.expected_kills(blob, av, melee=True)["models_killed_per_turn"]
avengers_kills = observation.expected_kills(blob, da, melee=True)["models_killed_per_turn"]
c.eq("charging the Avatar removes no models at all", avatar_kills, 0.0)
c.true("...while the same unit charging Dire Avengers removes several",
       avengers_kills >= 3.0)
c.true("the Avatar's counter-swing is worth many times the charge",
       observation.damage_value(av, blob, melee=True)
       > 10 * observation.damage_value(blob, av, melee=True))

# Both halves reach the text, in the units a reader can check.
c.true("the reported charge's note reads as 0.0 models",
       "about 0.0 of its models" in avatar_note)
c.true("...and the contrasting one does not",
       "about 0.0 of its models" not in avengers_note)

# An unvaluable pairing gets no note rather than a zero that would read as
# "this charge is worthless".
empty = necron_blob("2 Necron Warriors 9")
empty.models = []
c.eq("a unit with no models gets no note at all",
     agent_driver._charge_trade_note(empty, av), "")


# ===========================================================================
# 2. INFORMED, NOT WITHHELD - and that was the measurement's own verdict
# ===========================================================================
# A second withholding block was built and measured first. Over the two AI
# armies against every shipped enemy list the share of a target that a charge
# removes runs continuously - 0.01, 0.02, 0.03 (the reported case), 0.04,
# 0.05, 0.06, 0.07, 0.08 - with the cheap-screen charges that tie up a gun
# line sitting in the same range as the hopeless ones. A threshold there falls
# inside an overlap, which is precisely what _shooting_specialist_charge_block()
# rejected a per-target ratio FOR. So the option stays on the list.

c.eq("the reported unit is still not a shooting specialist (1.1x, under 1.4)",
     combat_focus.is_shooting_specialist(blob), False)
c.eq("...so the existing block does not fire on it, and is not asked to",
     agent_driver._shooting_specialist_charge_block(blob), None)

src = io.open("ai/agent_driver.py", encoding="utf-8").read()
tree = ast.parse(src)
calls = [n for n in ast.walk(tree)
         if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
         and n.func.id == "_charge_trade_note"]
c.eq("the note is used from exactly two places - declaring, and picking a target",
     len(calls), 2)


# ===========================================================================
# 3. it reaches the OPTION the tactical layer is shown
# ===========================================================================
# The gap this closes: ai/observation.py's squad_summary() carries no
# valuation of any kind, so the whole basis for this decision is the option's
# own text. Driven through the real _handle_charge() rather than asserted from
# the helper, because a helper nothing calls is this repo's most-repeated bug.

class RecordingAgent(Agent):
    """Takes the charge, and keeps every option list it was shown."""

    def __init__(self):
        self.seen = []

    def plan_turn(self, *args, **kwargs):
        return {}

    def decide(self, obs):
        self.seen.append(list(obs["available_actions"]))
        for index, action in enumerate(obs["available_actions"]):
            if action.get("type") in ("declare_charge", "charge_target"):
                return index
        return 0


def charge_scene(attacker, defender, gap_in=6.0):
    """The reported matchup on the real board: the AI's Charge phase, a real
    controller stack, and the enemy a short roll away."""
    battle_map = maps.apply_to_config(maps.get("map2"))
    state = GameState()
    battle_map.build(state)
    for i, model in enumerate(attacker.models):
        model.x_in, model.y_in = 26.0 + (i % 7) * 1.5, 20.0 + (i // 7) * 1.5
        state.add_token(model)
    # Clear of engagement range (rule 03.04) - a unit already engaged cannot
    # declare a charge at all, which is what the first version of this scene
    # measured instead of the option text.
    for i, model in enumerate(defender.models):
        model.x_in, model.y_in = 26.0 + i * 1.5, 20.0 + 3.0 + gap_in
        state.add_token(model)
    turn = TurnTracker()
    turn.started = True
    turn.battle_round = 2
    turn.phase_index = PHASES.index(PHASE_CHARGE)
    turn.turn_owner = turn.active_player = "Player 2"
    dice = DiceManager()
    move = MovementController(all_tokens=state.tokens, obstacles=state.obstacles,
                              turn_tracker=turn, board_width_in=config.BOARD_WIDTH_IN,
                              board_height_in=config.BOARD_HEIGHT_IN)
    charge = ChargeController(dice_manager=dice, turn_tracker=turn,
                              all_tokens=state.tokens, movement_controller=move)
    return dict(state=state, attacker=attacker, defender=defender, turn=turn,
                dice=dice, movement=move, charge=charge)


scene = charge_scene(necron_blob(), avatar())
c.true("scene check: the charge really is on offer", scene["charge"].can_declare_charge(scene["attacker"]))

agent = RecordingAgent()
log = Log()
script(*([3] * 40))
for _ in range(6):
    if not agent_driver._handle_charge(
            agent, agent_driver.AIMemory(), "Player 2", scene["state"].tokens,
            scene["charge"], scene["movement"], None, game_log=log):
        break
    if scene["dice"].pending_values:
        scene["dice"].acknowledge()
        scene["charge"].on_dice_acknowledged()

declare_texts = [a["description"] for options in agent.seen for a in options
                 if a.get("type") == "declare_charge"]
c.true("the tactical layer was actually asked", bool(declare_texts))
if declare_texts:
    text = declare_texts[0]
    c.true("the declare option still carries the odds it always did",
           "chance)" in text and "2D6" in text)
    c.true("...and NOW carries the trade as well", "would remove about" in text)
    c.true("...naming the counter-swing in points a turn",
           "pts/turn of this squad back" in text)


# ===========================================================================
# 4. the target choice carries it per target
# ===========================================================================
# Two reachable enemies read as interchangeable when the option is just their
# names. On the reported board they were worth 57 and 7.5 points a turn.

blob2 = necron_blob("2 Necron Warriors 2")
both = charge_scene(blob2, avatar())
extra = dire_avengers()
for i, model in enumerate(extra.models):
    model.x_in, model.y_in = 40.0 + i * 1.5, 20.0 + 3.0 + 6.0
    both["state"].add_token(model)

agent2 = RecordingAgent()
script(*([6] * 40))
for _ in range(6):
    if not agent_driver._handle_charge(
            agent2, agent_driver.AIMemory(), "Player 2", both["state"].tokens,
            both["charge"], both["movement"], None, game_log=Log()):
        break
    if both["dice"].pending_values:
        both["dice"].acknowledge()
        both["charge"].on_dice_acknowledged()

target_texts = [a["description"] for options in agent2.seen for a in options
                if a.get("type") == "charge_target"]
if target_texts:
    c.true("every charge_target option says what that target costs",
           all("would remove about" in t for t in target_texts))
    avatar_options = [t for t in target_texts if "Avatar" in t]
    c.true("...and the Avatar's says it removes none of it",
           bool(avatar_options) and all("about 0.0 of its models" in t for t in avatar_options))
else:
    # Not a silent pass: if no two-target choice arose, say so rather than
    # scoring a check that measured nothing.
    c.true("a two-target choice was reached (otherwise this section measures nothing)", False)


# ===========================================================================
# 5. the home objective: a threat sets the bar, it does not switch the pass off
# ===========================================================================
# Rebuilt from the reported log's own coordinates at the turn the blob froze -
# line 328's [move detail] for the blob, line 117's for the Immortals, and the
# Avatar where line 630 leaves it.

BLOB_AT = [(29.69, 4.37), (33.88, 5.58), (31.13, 4.58), (34.02, 7.00), (34.26, 9.38),
           (36.69, 9.21), (29.91, 2.84), (28.47, 4.02), (31.08, 3.31), (36.30, 5.15),
           (28.03, 6.14), (36.22, 6.73), (30.26, 5.50), (36.32, 8.00), (31.36, 6.14),
           (32.35, 7.00), (34.49, 11.83), (26.91, 5.56), (33.39, 4.41), (37.25, 5.99),
           (35.36, 13.57)]
IMMORTALS_AT = [(29.86, 7.34), (28.93, 8.41), (27.53, 9.24), (30.81, 8.17), (28.16, 7.40),
                (30.65, 9.43), (32.08, 8.24), (26.80, 7.82), (31.93, 11.41), (25.53, 7.78),
                (25.54, 10.09)]
AVATAR_AT = [(34.07, 18.40)]
# Its own army, where the log leaves it - the Canoptek Wraiths and the C'tan
# are directly in front of the blob, and leaving them out changes the answer:
# without them the same order moves it 2.68" instead of 0.00".
WRAITHS_AT = [(29.17, 16.13), (30.91, 14.00), (32.01, 15.65)]
CTAN_AT = [(37.29, 11.86)]


def reported_board():
    battle_map = maps.apply_to_config(maps.get("map2"))
    state = GameState()
    battle_map.build(state)
    squads = {}
    wraiths = build_squad(nec.CANOPTEK_WRAITHS, "Player 2", unit_index=1)
    wraiths.name = "2 Canoptek Wraiths 1"
    ctan = build_squad(nec.CTAN_SHARD_OF_THE_VOID_DRAGON, "Player 2", unit_index=1)
    ctan.name = "2 C'tan Shard of the Void Dragon 1"
    for squad, at in ((necron_blob(), BLOB_AT), (immortals(), IMMORTALS_AT),
                      (wraiths, WRAITHS_AT), (ctan, CTAN_AT), (avatar(), AVATAR_AT)):
        squad.models = squad.models[:len(at)]
        for model, (x, y) in zip(squad.models, at):
            model.x_in, model.y_in = x, y
            state.tokens.append(model)
        squads[squad.name] = squad
    turn = TurnTracker(first_player="Player 2")
    turn.battle_round = 3
    turn.phase_index = PHASES.index(PHASE_MOVEMENT)
    return state, turn, squads


def reported_plan():
    """The turn plan the log printed at line 605-608, in shape."""
    return {"summary": "reported", "unit_plans": {
        IMMORTALS: {"role": "hold", "position": (30.0, 7.0), "target": None,
                    "priority": 5, "reason": "Sits on P2 Home Objective already controlled by us."},
        WARRIORS: {"role": "hold", "position": (34.0, 8.0), "target": None, "priority": 5,
                   "reason": ("Second unit on P2 Home Objective is redundant with Immortals 1 "
                              "already holding it - reposition slightly toward Central.")},
    }}


state, turn, squads = reported_board()
threats = dict((o.name, t) for o, t in agent_driver._held_objectives(state, "Player 2"))
c.true("scene check: the home objective really is ours", HOME in threats)
c.eq("scene check: the Avatar within 12\" is worth 5 OC", threats.get(HOME), 5)

# Both units are on it, which is what the report describes.
garrisons = agent_driver._planned_garrisons(reported_plan(), squads, state, "Player 2")
c.eq("the plan really does park both units on the home objective",
     sorted(s.name for s in garrisons.get(HOME, [])), sorted([IMMORTALS, WARRIORS]))

# The Immortals hold it on their own, by rule 14.02's own arithmetic.
from game.objective_control import effective_oc  # noqa: E402 - read beside its use
immortals_oc = sum(effective_oc(m) for m in squads[IMMORTALS].models)
blob_oc = sum(effective_oc(m) for m in squads[WARRIORS].models)
c.true("the Immortals alone out-control the threat", immortals_oc > threats[HOME])
c.true("...so all of the blob's Objective Control is surplus", blob_oc > 0)

plan = reported_plan()
log = Log()
agent_driver._validate_turn_plan(plan, "Player 2", state, turn, game_log=log)
c.eq("the blob is freed to advance", plan["unit_plans"][WARRIORS]["role"], "advance")
c.eq("...and its garrison coordinate is dropped", plan["unit_plans"][WARRIORS]["position"], None)
c.eq("the Immortals keep the objective", plan["unit_plans"][IMMORTALS]["role"], "hold")
c.eq("...and keep their position", plan["unit_plans"][IMMORTALS]["position"], (30.0, 7.0))
c.true("the correction says which unit holds it and why",
       any("14.01-14.02" in line and IMMORTALS in line for line in log.lines))
# Error class 4: the reason has to move with the role, or the tactical layer
# obeys the sentence instead of the field.
c.true("the freed unit's reason no longer argues for garrisoning",
       "redundant" not in plan["unit_plans"][WARRIORS]["reason"])
c.true("...and tells it to go and do something",
       "forward" in plan["unit_plans"][WARRIORS]["reason"].lower())


# ===========================================================================
# 6. the freed unit can actually GO somewhere - the other half of the report
# ===========================================================================
# "0 inches moved" is also what a fix that frees a unit into a corner looks
# like, so the ground is measured rather than assumed.

state, turn, squads = reported_board()
blob3 = squads[WARRIORS]
move = MovementController(all_tokens=state.tokens, obstacles=state.obstacles, turn_tracker=turn,
                          board_width_in=config.BOARD_WIDTH_IN,
                          board_height_in=config.BOARD_HEIGHT_IN)
move.select(blob3.models[0])
before = agent_driver._centroid(blob3)
CENTRAL = (30.0, 22.0)
agent_driver._advance_toward(move, blob3, CENTRAL)
after = agent_driver._centroid(blob3)
gained = math.dist(before, CENTRAL) - math.dist(after, CENTRAL)
c.true(f"ordered at the Central Objective the blob really advances (got {gained:.2f}\")",
       gained > 2.0)
c.eq("...and is still a single coherent unit (rule 09.02)", blob3.check_coherency(), [])

# And the order it was actually given - a point inside its own formation -
# is the one that moves nothing. This is the measurement behind section 7.
state, turn, squads = reported_board()
blob4 = squads[WARRIORS]
move = MovementController(all_tokens=state.tokens, obstacles=state.obstacles, turn_tracker=turn,
                          board_width_in=config.BOARD_WIDTH_IN,
                          board_height_in=config.BOARD_HEIGHT_IN)
move.select(blob4.models[0])
before = agent_driver._centroid(blob4)
agent_driver._advance_toward(move, blob4, (34.0, 8.0))
c.eq("a point inside its own formation moves it nothing at all",
     round(math.dist(before, agent_driver._centroid(blob4)), 2), 0.0)


# ===========================================================================
# 7. an ACTIVE order onto the unit's own middle is dropped; a passive one is not
# ===========================================================================

def plan_with(role, position):
    return {"summary": "s", "unit_plans": {
        WARRIORS: {"role": role, "position": position, "target": None,
                   "priority": 5, "reason": "go there"}}}


INSIDE = (34.0, 8.0)      # measured above: 1.97" from the centroid, inside the hull
OUTSIDE = (30.0, 22.0)    # the Central Objective, well clear of the formation

state, turn, squads = reported_board()
c.true("scene check: the ordered point really is inside the formation",
       geometry.point_inside_hull(INSIDE, [(m.x_in, m.y_in) for m in squads[WARRIORS].models]))
c.eq("...and the far one is not",
     geometry.point_inside_hull(OUTSIDE, [(m.x_in, m.y_in) for m in squads[WARRIORS].models]),
     False)

state, turn, squads = reported_board()
active = plan_with("advance", INSIDE)
agent_driver._validate_turn_plan(active, "Player 2", state, turn, game_log=Log())
c.eq("an ACTIVE order onto its own middle is dropped",
     active["unit_plans"][WARRIORS]["position"], None)
c.eq("...and the role is left alone - this pass has no rule saying it must leave",
     active["unit_plans"][WARRIORS]["role"], "advance")

state, turn, squads = reported_board()
passive = plan_with("hold", INSIDE)
agent_driver._validate_turn_plan(passive, "Player 2", state, turn, game_log=Log())
c.eq("a PASSIVE order to stand where it stands is kept - that is a real order",
     passive["unit_plans"][WARRIORS]["position"], INSIDE)

state, turn, squads = reported_board()
far = plan_with("advance", OUTSIDE)
agent_driver._validate_turn_plan(far, "Player 2", state, turn, game_log=Log())
c.true("a genuine move order is untouched",
       far["unit_plans"][WARRIORS]["position"] is not None)


# ===========================================================================
# 8. the hull helper, and the one definition behind it
# ===========================================================================
# game/renderer.py had it privately while it was the only caller; it draws the
# objective outlines with it. ai/agent_driver.py cannot import that module
# (pygame, per-frame draw path), so it moved to game/geometry.py and the
# renderer re-exports it - which is what keeps every objective-outline pixel
# test unchanged by construction.

from game import renderer  # noqa: E402 - imported here for the identity check
c.true("the renderer's hull IS the shared one, not a copy",
       renderer._convex_hull is geometry.convex_hull)

square = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]
c.true("a point in the middle is inside", geometry.point_inside_hull((2.0, 2.0), square))
c.eq("a point outside is outside", geometry.point_inside_hull((5.0, 2.0), square), False)
c.true("a point exactly on the boundary counts as arrived",
       geometry.point_inside_hull((4.0, 2.0), square))
c.eq("two models cannot stand AROUND anything",
     geometry.point_inside_hull((1.0, 0.0), [(0.0, 0.0), (2.0, 0.0)]), False)
c.eq("nor can one", geometry.point_inside_hull((0.0, 0.0), [(0.0, 0.0)]), False)

c.finish()
