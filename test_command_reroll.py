"""Command Re-roll (15.02) under BOTH halves of rule 15.01.

User report: "ich konnte gerade command reroll in der selben aktiverung 2 mal
einsetzen. einmal bei wound, einmal bei damage", naming the two rules broken:
  1. the same Stratagem can be used only once per phase;
  2. a unit can be targeted by only one Stratagem per phase.

Reproduced in the reported log (logs/game_20260912_225758.log): "Player 1 uses
Command Re-roll" on the Bright Lance wound roll, then "Player 2 spends 1 CP /
Player 2 uses Command Re-roll" on Player 1's own Bright Lance DAMAGE roll.

THE CAUSE, and it is one cause for both rules. CommandRerollController billed
turn_tracker.active_player and passed no target:
  * the save step hands active_player to the defender, and it is still the
    defender on the attacker's Damage roll - so 15.01's (player, Stratagem)
    key was the OPPONENT's, found nothing to refuse, and the opponent paid;
  * with an empty target list, "one Stratagem per unit per phase" could never
    refuse anything either.
The fix puts the unit a roll is made for ON the roll (DiceManager.rolled_for);
Command Re-roll bills its owner and targets it.

Sections:
  1. the reported sequence, end to end through the real ShootingController
  2. a Damage roll is billed to the attacker while the defender is active
  3. a Save roll belongs to the defender whoever is active
  4. Charge and Advance rolls name their own unit
  5. rule 15.01, both halves, on a real StratagemController
  6. 01.07 and fail-closed
  7. the dice panel offers a button only to the side that owns the roll
  8. the AI is asked about ITS rolls, not about whoever is active
  9. source guards
"""
import ast
import io
import os
import sys
from types import SimpleNamespace

import testkit as tk
from game import maps
import game.factions.aeldari as ae
from game import roll_choice
from game.charge import ChargeController
from game.command_points import CommandPointManager
from game.command_reroll import CommandRerollController
from game.dice import (DiceManager, ADVANCE_ROLL, CHARGE_ROLL, DAMAGE_ROLL, HIT_ROLL,
                       SAVE_ROLL, WOUND_ROLL)
from game.game_state import GameState
from game.movement import MovementController
from game.stratagems import Stratagem, StratagemController
from game.turn import PHASES, PHASE_CHARGE, PHASE_MOVEMENT, TurnTracker
from game.weapons import BrightLanceProfile
from ai import agent_driver

maps.apply_to_config(maps.get("map2"))

HUMAN, AI = "Player 1", "Player 2"
failed = []
count = [0]


def ok(label, cond, detail=""):
    count[0] += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label + ("" if cond or not detail else "  -- " + str(detail)))


def ledger(cp=5):
    points = CommandPointManager()
    points.cp[HUMAN] = points.cp[AI] = cp
    return points, StratagemController(command_points=points)


# ------------------------------------------------------------------ scenes

def shot(attacker_owner=HUMAN):
    """One Bright Lance (D6+2) at a Wraithlord - a MULTI-WOUND target, so the
    Damage roll is really rolled - through the real controller."""
    scene = tk.shooting_scene(ae.WAR_WALKERS, ae.WRAITHLORD, attacker_owner=attacker_owner, gap=10.0)
    points, strat = ledger()
    scene.update(points=points, strat=strat,
                 reroll=CommandRerollController(strat, scene["dice"], turn_tracker=scene["turn"]))
    sc = scene["shooting"]
    sc.active_squad = scene["attacker"]
    lance = BrightLanceProfile()
    sc._begin_resolution("verify", lance.name, [(scene["attacker"].models[0], lance)], scene["target"])
    return scene


FACES = {HIT_ROLL: 6, WOUND_ROLL: 6, SAVE_ROLL: 1, DAMAGE_ROLL: 3}


def drive_to(scene, kind, limit=12):
    """Acknowledge rolls with FACES until a roll of `kind` is on the table.
    The faces are written into the pending list itself, which is the same
    list object as last_values - so what resolves is what was set."""
    dm, sc = scene["dice"], scene["shooting"]
    for _ in range(limit):
        if scene["decision"].is_pending:
            return False
        if dm.is_pending and dm.roll_kind == kind:
            return True
        if not dm.is_pending:
            session = sc.damage_session
            if session is not None and getattr(session, "pending_choice", None):
                sc.choose_damage_model(session.pending_choice[0])
                continue
            return False
        face = FACES.get(dm.roll_kind, 6)
        dm.pending_values[:] = [face] * len(dm.pending_values)
        dm.acknowledge()
        sc.on_dice_acknowledged()
    return False


# ============================================= 1. the reported sequence
print("\n1) Wound, then Damage, in ONE activation - the report")
s = shot()
ok("the fixture reaches the Wound roll", drive_to(s, WOUND_ROLL))
ok("the Wound roll is made for the attacker", s["dice"].rolled_for is s["attacker"])
ok("Command Re-roll is offered on it", s["reroll"].can_use() is True)
s["reroll"].start()
ok("...and billed to the attacker", (s["points"].cp[HUMAN], s["points"].cp[AI]) == (4, 5),
   s["points"].cp)
ok("the fixture reaches the Damage roll of the same attack", drive_to(s, DAMAGE_ROLL))
# LIVENESS: this is the state the report came from. If the save step stopped
# handing active_player to the defender, this section would pass without
# measuring the bug at all.
ok("precondition: the defender is the active player at the Damage roll",
   s["turn"].active_player == AI, s["turn"].active_player)
ok("the Damage roll is still the ATTACKER's", s["reroll"].roll_owner() == HUMAN, s["reroll"].roll_owner())
ok("rule 1: Command Re-roll is NOT offered a second time this phase", s["reroll"].can_use() is False)
ok("...and the reason is 15.01's once-per-phase clause",
   s["strat"].refusal(HUMAN, s["reroll"]._stratagem, [s["attacker"]]) == "already used this phase (15.01)",
   s["strat"].refusal(HUMAN, s["reroll"]._stratagem, [s["attacker"]]))
s["reroll"].start()
ok("pressing it anyway spends nothing - and NOT the opponent's CP (the log's 'Player 2 spends 1 CP')",
   (s["points"].cp[HUMAN], s["points"].cp[AI]) == (4, 5), s["points"].cp)

# ============================= 2. a Damage roll is billed to the attacker
print("\n2) a Damage roll alone: the attacker pays although the defender is active")
s = shot()
ok("the fixture reaches the Damage roll", drive_to(s, DAMAGE_ROLL))
ok("precondition: the defender is active", s["turn"].active_player == AI)
ok("Command Re-roll is offered to the attacker", s["reroll"].can_use() and s["reroll"].roll_owner() == HUMAN)
s["reroll"].start()
ok("the attacker pays, the defender does not", (s["points"].cp[HUMAN], s["points"].cp[AI]) == (4, 5),
   s["points"].cp)
ok("rule 2: the attacking UNIT is recorded as this phase's Stratagem target",
   (HUMAN, s["attacker"]) in s["strat"].targeted_this_phase)
ok("...and the Stratagem under the attacker's key", (HUMAN, "Command Re-roll") in s["strat"].used_this_phase)
ok("nothing is booked under the defender's key",
   not any(p == AI for p, _n in s["strat"].used_this_phase))

# =================================== 3. a Save roll belongs to the defender
print("\n3) a Save roll belongs to the defender, whoever is active")
s = shot()
ok("the fixture reaches the Save roll", drive_to(s, SAVE_ROLL))
ok("the Save roll is made for the TARGET", s["dice"].rolled_for is s["target"])
s["turn"].set_active(HUMAN)   # focus elsewhere must not move the bill
ok("the defender owns it even with the attacker active", s["reroll"].roll_owner() == AI)
s["reroll"].start()
ok("the defender pays", (s["points"].cp[HUMAN], s["points"].cp[AI]) == (5, 4), s["points"].cp)
ok("the defending unit is the recorded target", (AI, s["target"]) in s["strat"].targeted_this_phase)

# ======================================= 4. Charge and Advance name their unit
print("\n4) Charge and Advance rolls are made for the moving unit")
st = GameState()
charger = tk.build(ae.FIRE_DRAGONS, AI, name="2 Fire Dragons 1")
foe = tk.build(ae.WRAITHLORD, HUMAN, name="1 Wraithlord 1")
tk.line_up(charger, y=20.0)
tk.line_up(foe, y=26.0)
for squad in (charger, foe):
    for model in squad.models:
        st.add_token(model)
tt = TurnTracker()
tt.phase_index = PHASES.index(PHASE_CHARGE)
tt.turn_owner = AI
tt.set_active(AI)
dm = DiceManager()
mc = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens, dice_manager=dm)
cc = ChargeController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, movement_controller=mc)
cc.declare_charge(charger)
ok("a Charge roll is on the table", dm.is_pending and dm.roll_kind == CHARGE_ROLL, dm.roll_kind)
ok("...made for the charger", dm.rolled_for is charger)
points, strat = ledger()
cr = CommandRerollController(strat, dm, turn_tracker=tt)
tt.set_active(HUMAN)
cr.start()
ok("the charger's owner pays although another player is active",
   (points.cp[HUMAN], points.cp[AI]) == (5, 4), points.cp)

st = GameState()
mover = tk.build(ae.FIRE_DRAGONS, HUMAN, name="1 Fire Dragons 1")
tk.line_up(mover, y=20.0)
for model in mover.models:
    st.add_token(model)
tt = TurnTracker()
tt.phase_index = PHASES.index(PHASE_MOVEMENT)
tt.turn_owner = HUMAN
tt.set_active(HUMAN)
dm = DiceManager()
mc = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens, dice_manager=dm)
mc.select(mover.models[0])
mc.start_move()
mc.start_run()
ok("an Advance roll is on the table", dm.is_pending and dm.roll_kind == ADVANCE_ROLL, dm.roll_kind)
ok("...made for the advancing unit", dm.rolled_for is mover)

# ============================================= 5. rule 15.01, both halves
print("\n5) rule 15.01 on a real StratagemController")
x = tk.build(ae.FIRE_DRAGONS, HUMAN, name="1 Fire Dragons 1")
y = tk.build(ae.WAR_WALKERS, HUMAN, name="1 War Walkers 1")
z = tk.build(ae.WRAITHLORD, AI, name="2 Wraithlord 1")
other = Stratagem(name="Some Other Stratagem", cp_cost=1, effect=lambda *_a: None)


def roll_for(dm, unit, kind=HIT_ROLL):
    dm.roll(count=2, sides=6, label="Hit Roll", roll_kind=kind, success_threshold=4, rolled_for=unit)


# (a) Command Re-roll first, then another Stratagem on the same unit
points, strat = ledger()
dm = DiceManager()
cr = CommandRerollController(strat, dm)
roll_for(dm, x)
cr.start()
if cr.selecting_die:
    cr.choose_die(0)
ok("(a) the Command Re-roll went through", points.cp[HUMAN] == 4, points.cp)
refusal = strat.refusal(HUMAN, other, [x])
ok("(a) rule 2: another Stratagem on the SAME unit is refused this phase",
   refusal is not None and "already targeted" in refusal, refusal)
ok("(a) ...while a different unit may still be targeted", strat.can_use(HUMAN, other, [y]))

# (b) another Stratagem first, then Command Re-roll on that unit's roll
points, strat = ledger()
dm = DiceManager()
cr = CommandRerollController(strat, dm)
strat.use(HUMAN, other, [x])
roll_for(dm, x)
ok("(b) rule 2: Command Re-roll on a unit already targeted this phase is refused", cr.can_use() is False)
roll_for(dm, y)
ok("(b) ...but offered on another unit's roll", cr.can_use() is True)

# (c) rule 1 across units, and across players
points, strat = ledger()
dm = DiceManager()
cr = CommandRerollController(strat, dm)
roll_for(dm, x)
cr.start()
if cr.selecting_die:
    cr.choose_die(0)
roll_for(dm, y)
ok("(c) rule 1: not a second time this phase, even for a different unit", cr.can_use() is False)
roll_for(dm, z)
ok("(c) ...while the opponent may still use THEIR Command Re-roll on their own unit", cr.can_use() is True)
strat.reset_phase()
roll_for(dm, y)
ok("(c) a new phase clears both halves", cr.can_use() is True)

# ============================================= 6. 01.07 and fail-closed
print("\n6) battle-shocked units and rolls with no unit")
points, strat = ledger()
dm = DiceManager()
cr = CommandRerollController(strat, dm)
x.battle_shocked = True
roll_for(dm, x)
ok("rule 01.07: a battle-shocked unit's roll cannot be Command Re-rolled", cr.can_use() is False)
x.battle_shocked = False
dm.roll(count=2, sides=6, label="Hit Roll", roll_kind=HIT_ROLL, success_threshold=4)
ok("a re-rollable roll that names no unit is NOT offered (no guessing an account)", cr.can_use() is False)
cr.start()
ok("...and pressing it spends nothing", (points.cp[HUMAN], points.cp[AI]) == (5, 5), points.cp)

# ============================= 7. the dice panel offers only to the owner
print("\n7) dice-panel buttons belong to the side that owns the roll")


class _Activation:
    selecting_die = False

    def __init__(self, owner):
        self.owner = owner

    def can_use(self):
        return True

    def roll_owner(self):
        return self.owner

    def panel_label(self):
        return "Targeting Array"

    def start(self):
        pass

    def cancel_selection(self):
        pass


class _Six:
    selecting_die = False

    def __init__(self, sources):
        self._sources = sources

    def available_sources(self):
        return self._sources

    def label_for(self, source):
        return "six:%s" % source

    def start(self, source):
        pass

    def cancel_selection(self):
        pass


def keys(actions):
    return [o.key for o in actions]


humans = {HUMAN}
points, strat = ledger()
dm = DiceManager()
cr = CommandRerollController(strat, dm)
roll_for(dm, z)
ok("an AI unit's roll: Command Re-roll is usable by its owner", cr.can_use() is True)
ok("...but the human's panel draws NO button for it",
   roll_choice.COMMAND_REROLL not in keys(roll_choice.ability_actions(cr, None, None, human_players=humans)[1]))
ok("...and without a human view (the stub suites) the button is unchanged",
   roll_choice.COMMAND_REROLL in keys(roll_choice.ability_actions(cr, None, None)[1]))
roll_for(dm, x)
ok("a human unit's roll: the button is drawn",
   roll_choice.COMMAND_REROLL in keys(roll_choice.ability_actions(cr, None, None, human_players=humans)[1]))
ok("Targeting Array / Crystal Matrix: not drawn on the AI's attack",
   roll_choice.ACTIVATION_REROLL not in keys(
       roll_choice.ability_actions(None, _Activation(AI), None, human_players=humans)[1]))
ok("...drawn on the human's", roll_choice.ACTIVATION_REROLL in keys(
    roll_choice.ability_actions(None, _Activation(HUMAN), None, human_players=humans)[1]))
labels = [o.label for o in roll_choice.ability_actions(
    None, None, _Six([("shrine", x, None), ("fates", z, None)]), human_players=humans)[1]]
ok("unmodified-six abilities: only the human unit's source is drawn", labels == ["six:shrine"], labels)

# ============================= 8. the AI is asked about ITS rolls
print("\n8) the AI decides about the rolls it owns")


class _CountingAgent:
    """Any use counts as being asked; it then raises, so nothing is spent."""

    def __init__(self):
        self.__dict__["touched"] = 0

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        self.__dict__["touched"] += 1
        raise RuntimeError("the agent was asked (%s)" % name)


def ask_ai(owner_unit, active):
    points, strat = ledger()
    dm = DiceManager()
    cr = CommandRerollController(strat, dm)
    tt = TurnTracker()
    tt.set_active(active)
    roll_for(dm, owner_unit)
    dm.pending_values[:] = [1, 1]
    agent = _CountingAgent()
    try:
        handled = agent_driver._maybe_command_reroll(
            agent, agent_driver.AIMemory(), cr, tt, SimpleNamespace(tokens=[]), AI, None)
    except Exception:                                  # noqa: BLE001 - the agent raises by design
        handled = None
    return agent.touched, handled, points


touched, handled, points = ask_ai(x, active=AI)
ok("the human's roll while the AI is active: the AI is not asked", touched == 0 and handled is False,
   (touched, handled))
ok("...and the human's CP are untouched", points.cp[HUMAN] == 5)
touched, handled, points = ask_ai(z, active=HUMAN)
ok("the AI's own roll while the human is active (its Damage roll after a save): the AI is asked",
   touched > 0, (touched, handled))

# ============================================= 9. source guards
print("\n9) source guards")
REROLLABLE = {"ADVANCE_ROLL", "CHARGE_ROLL", "DAMAGE_ROLL", "HAZARD_ROLL", "HIT_ROLL",
              "SAVE_ROLL", "WOUND_ROLL", "ATTACKS_ROLL"}
sites, missing, wrong = 0, [], []
for root, _dirs, files in os.walk("game"):
    for name in sorted(files):
        if not name.endswith(".py"):
            continue
        path = os.path.join(root, name)
        src = io.open(path, encoding="utf-8").read()
        for call in ast.walk(ast.parse(src)):
            if not isinstance(call, ast.Call):
                continue
            kw = {k.arg: k.value for k in call.keywords if k.arg}
            if "roll_kind" not in kw:
                continue
            kinds = {n.id for n in ast.walk(kw["roll_kind"]) if isinstance(n, ast.Name)} & REROLLABLE
            if not kinds:
                continue
            sites += 1
            where = "%s:%d" % (path, call.lineno)
            if "rolled_for" not in kw or (isinstance(kw["rolled_for"], ast.Constant)
                                          and kw["rolled_for"].value is None):
                # A literal None is not naming a unit - it is the old bug
                # spelled out, and would pass a presence check.
                missing.append(where)
                continue
            # Where the call names both sides, the unit must be the right one:
            # a save for the target, everything else for the attacker.
            mine = ast.get_source_segment(src, kw["rolled_for"])
            if kinds == {"SAVE_ROLL"} and "target_squad" in kw:
                if mine != ast.get_source_segment(src, kw["target_squad"]):
                    wrong.append(where + " (a save is made for the target)")
            elif "SAVE_ROLL" not in kinds and "attacker_squad" in kw:
                if mine != ast.get_source_segment(src, kw["attacker_squad"]):
                    wrong.append(where + " (made for the attacker)")
ok("liveness: the sweep finds the re-rollable roll sites", sites >= 20, sites)
ok("every re-rollable roll in game/ names the unit it is made for", not missing, missing)
ok("...and names the RIGHT side where the call shows both", not wrong, wrong)

src = io.open(os.path.join("game", "dice_notation.py"), encoding="utf-8").read()
forwarded = [c for c in ast.walk(ast.parse(src)) if isinstance(c, ast.Call)
             and isinstance(c.func, ast.Attribute) and c.func.attr == "roll"
             and any(k.arg == "rolled_for" and isinstance(k.value, ast.Name) and k.value.id == "rolled_for"
                     for k in c.keywords)]
ok("DiceNotationRoll hands rolled_for on to the dice manager", bool(forwarded))

tree = ast.parse(io.open(os.path.join("game", "command_reroll.py"), encoding="utf-8").read())
ok("command_reroll.py never reads active_player",
   not any(isinstance(n, ast.Attribute) and n.attr == "active_player" for n in ast.walk(tree)))
strat_calls = [c for c in ast.walk(tree) if isinstance(c, ast.Call)
               and isinstance(c.func, ast.Name) and c.func.id == "Stratagem"]
ok("its Stratagem no longer opts out of rule 2 (no allow_repeat_target)",
   len(strat_calls) == 1 and not any(k.arg == "allow_repeat_target" for k in strat_calls[0].keywords))
ledger_calls = [c for c in ast.walk(tree) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr in ("can_use", "use")
                and isinstance(c.func.value, ast.Attribute) and c.func.value.attr == "stratagem_controller"]
ok("both ledger calls hand the unit in as the target",
   len(ledger_calls) == 2 and all(len(c.args) >= 3 and isinstance(c.args[2], ast.List)
                                   and len(c.args[2].elts) == 1 for c in ledger_calls),
   len(ledger_calls))

tree = ast.parse(io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read())
fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_maybe_command_reroll"), None)
compares = [n for n in ast.walk(fn) if isinstance(n, ast.Compare)] if fn is not None else []
ok("the AI path compares the roll's owner",
   any(isinstance(c.left, ast.Call) and isinstance(c.left.func, ast.Attribute)
       and c.left.func.attr == "roll_owner" for c in compares))
ok("...and no comparison in it reads active_player",
   not any(isinstance(n, ast.Attribute) and n.attr == "active_player"
           for c in compares for n in ast.walk(c)))

tree = ast.parse(io.open("main.py", encoding="utf-8").read())
fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_frame_dice_actions"), None)
calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
         and c.func.attr == "ability_actions"] if fn is not None else []
ok("main.py hands the dice panel the live human view",
   len(calls) == 1 and any(k.arg == "human_players" and isinstance(k.value, ast.Name)
                           and k.value.id == "human_players" for k in calls[0].keywords))

print("\n%d/%d checks passed" % (count[0] - len(failed), count[0]))
if failed:
    print("FAILED:")
    for label in failed:
        print("  - " + label)
sys.exit(1 if failed else 0)
