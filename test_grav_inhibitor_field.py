"""Tests for Retaliation Cadre's Grav-Inhibitor Field stratagem
(game/grav_inhibitor_field.py).

RULE (user-supplied): 1CP, Strategic Ploy. WHEN your opponent's Charge phase,
just after an enemy unit has declared a charge. TARGET one T'AU EMPIRE
BATTLESUIT unit from your army that was selected as a target of that charge.
EFFECT that enemy unit must immediately take a Battle-shock test, and you roll
one D6 per model in it: for each 6 it suffers 1 mortal wound.

The effect is small; the TIMING is where this can go wrong, so that is what
the checks concentrate on:

  * the charge move must be DEFERRED behind the whole two-roll sequence and
    then actually resume - both when the stratagem is used and when it is
    declined;
  * the two rolls must sequence (DiceManager holds one at a time), with the
    Battle-Shock test resolving through the real BattleShockController;
  * rule 06.02's "the defending player chooses" - the mortal wounds land on
    the CHARGING unit, so that choice belongs to the charging player, not to
    whoever spent the CP;
  * and if those wounds wipe the charging unit out, the charge must finish
    cleanly rather than leaving a move open on a unit that is gone.

Uses real ChargeController/MovementController/BattleShockController/
StratagemController/CommandPointManager/DecisionManager/GameState objects and
real datasheets, with scripted dice.

Run: python test_grav_inhibitor_field.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import dice as dice_mod
from game import maps
from game.battle_shock import BattleShockController
from game.charge import DECLARING_TARGETS, IDLE, ChargeController
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BOYZ, GRETCHIN
from game.factions.tau_empire import CRISIS_STARSCYTHE, STRIKE_TEAM
from game.game_state import GameState
from game.grav_inhibitor_field import (GRAV_INHIBITOR_CP_COST, GravInhibitorFieldController,
                                       alive_models)
from game.movement import MovementController
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_CHARGE, PHASE_SHOOTING, TurnTracker

# Retaliation Cadre must be DECLARED for this suite: its rule and all six of
# its Stratagems gate on config.RETALIATION_CADRE_PLAYERS, which is empty until
# an army list that fields the detachment is chosen. Set here so the subject of
# these checks actually applies - the same precondition
# test_death_guard_stratagems.py's `detachment_on` exists for.
from game import config as _config  # noqa: E402
_config.RETALIATION_CADRE_PLAYERS = ("Player 1", "Player 2")

m = maps.get("map2")
maps.apply_to_config(m)

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(f"  {'OK  ' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")


# --------------------------------------------------------------- scripted dice
_scripted = []
_default = [None]


def _scripted_randint(low, high):
    if _scripted:
        return _scripted.pop(0)
    return high if _default[0] is None else _default[0]


dice_mod.random.randint = _scripted_randint


def script(*values, default=None):
    _scripted[:] = list(values)
    _default[0] = default


def scene(defender_sheet=CRISIS_STARSCYTHE, charger_sheet=GRETCHIN, cp=3,
          phase=PHASE_CHARGE, charger_models=None):
    """Player 2's unit declares a charge on Player 1's Battlesuits, 4" away -
    close enough to charge, far enough not to start engaged."""
    st = GameState()
    charging = build_squad(charger_sheet, "Player 2", name="2 Chargers 1")
    defender = build_squad(defender_sheet, "Player 1", name="1 Suits 1")
    if charger_models is not None:
        charging.models = charging.models[:charger_models]
    for i, mdl in enumerate(charging.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 20.0
        st.add_token(mdl)
    for i, mdl in enumerate(defender.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 2.4, 24.0
        st.add_token(mdl)

    tt = TurnTracker()
    tt.started = True
    tt.battle_round = 2
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = tt.active_player = "Player 2"  # the CHARGING player's own phase

    cps = CommandPointManager()
    cps.cp["Player 1"] = cp
    cps.cp["Player 2"] = cp
    strat = StratagemController(command_points=cps)
    dm = DiceManager()
    dec = DecisionManager()
    mc = MovementController(all_tokens=st.tokens, obstacles=st.obstacles, turn_tracker=tt,
                            board_width_in=m.width_in, board_height_in=m.height_in)
    bs = BattleShockController(dice_manager=dm, turn_tracker=tt)
    cc = ChargeController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, movement_controller=mc)
    gi = GravInhibitorFieldController(strat, dice_manager=dm, battle_shock_controller=bs,
                                      decision_manager=dec, turn_tracker=tt)
    cc.on_charge_declared = gi.maybe_offer
    return dict(state=st, charging=charging, defender=defender, turn=tt, cps=cps, strat=strat,
                dice=dm, decision=dec, movement=mc, shock=bs, charge=cc, grav=gi)


def declare(sc, roll=(4, 4)):
    """Drive a real charge declaration up to (but not through) the move."""
    script(*roll)
    sc["charge"].declare_charge(sc["charging"])
    sc["dice"].acknowledge()
    sc["charge"].on_dice_acknowledged()
    sc["charge"].toggle_charge_target(sc["defender"])
    sc["movement"].selected_squad = sc["charging"]
    return sc["charge"].max_distance


def ack(sc):
    """One click on the dice tray, in main.py's own order."""
    sc["dice"].acknowledge()
    sc["shock"].on_dice_acknowledged()
    sc["grav"].on_dice_acknowledged()


# ============================================== 1. the trigger and the defer
print("\n1) the trigger point, and deferring the charge move behind it")

sc = scene()
dist = declare(sc)
check("a real charge is declared", sc["charge"].state == DECLARING_TARGETS
      and sc["defender"] in sc["charge"].charge_targets, f'{dist}"')
check("the offer is opened at begin_charge_move()",
      sc["charge"].begin_charge_move() is None and sc["decision"].is_pending)
check("and it belongs to the DEFENDER", sc["decision"].player == "Player 1", str(sc["decision"].player))
check("the charge move has NOT started yet", sc["movement"].move_mode is None,
      str(sc["movement"].move_mode))
prompt = sc["decision"].prompt or ""
check("the prompt quotes the dice count and expected wounds",
      f"{len(alive_models(sc['charging']))}D6" in prompt and "expected" in prompt, prompt[:130])
check("it is flagged as a stratagem prompt", sc["decision"].is_stratagem)

# Declining must cost nothing and must still let the charge happen.
sc["decision"].choose(1)
check("declining spends no CP", sc["cps"].cp["Player 1"] == 3, str(sc["cps"].cp["Player 1"]))
check("and the charge move resumes", sc["movement"].move_mode == "charge")

# Nothing eligible -> no offer, no deferral at all.
sc = scene(defender_sheet=STRIKE_TEAM)
declare(sc)
sc["charge"].begin_charge_move()
check("a non-BATTLESUIT target gets no offer", not sc["decision"].is_pending)
check("and the charge move starts immediately", sc["movement"].move_mode == "charge")


# ================================================ 2. the two-roll sequence
print("\n2) Battle-Shock test, then one D6 per model")

sc = scene(charger_models=6)
declare(sc)
sc["charge"].begin_charge_move()
script(1, 1)  # a hopeless Battle-Shock test
sc["decision"].choose(0)  # use it
check("using it spends exactly 1 CP", sc["cps"].cp["Player 1"] == 3 - GRAV_INHIBITOR_CP_COST,
      str(sc["cps"].cp["Player 1"]))
check("the Battle-Shock test is on the table first",
      sc["dice"].is_pending and "Battle-Shock" in (sc["dice"].label or ""), sc["dice"].label or "")
check("it is the CHARGING unit taking it", sc["shock"].rolling_squad is sc["charging"])
check("the charge move is still deferred", sc["movement"].move_mode is None)

script(6, 6, 1, 1, 1, 1)  # 6 models -> two 6s -> 2 mortal wounds
ack(sc)
check("the test resolved through the real BattleShockController",
      sc["charging"].battle_shocked, "rolled 1,1 vs Ld")
check("the D6-per-model roll is queued behind it",
      sc["dice"].is_pending and len(sc["dice"].pending_values) == 6,
      f"{len(sc['dice'].pending_values)} dice")

before = len(alive_models(sc["charging"]))
ack(sc)
check("each 6 becomes a mortal wound to allocate", sc["grav"].pending_damage_choice is not None)
# Rule 06.02: the wounds land on the CHARGING unit, so the pick is theirs.
check("the allocation belongs to the charging player (rule 06.02)",
      sc["turn"].active_player == "Player 2", sc["turn"].active_player)
check("and the candidates are that unit's own models",
      all(mdl in sc["charging"].models for mdl in sc["grav"].pending_damage_choice))

guard = 0
while sc["grav"].pending_damage_choice is not None and guard < 20:
    sc["grav"].choose_damage_model(sc["grav"].pending_damage_choice[0])
    guard += 1
check("2 mortal wounds killed 2 one-wound models", len(alive_models(sc["charging"])) == before - 2,
      f"{before} -> {len(alive_models(sc['charging']))}")
check("and the charge move resumes once everything is resolved",
      sc["movement"].move_mode == "charge")
check("nothing is left busy", not sc["grav"].is_busy)
check("the active player is back to the charging side",
      sc["turn"].active_player == "Player 2")

# No 6s: the sequence still has to hand the charge back.
sc = scene(charger_models=4)
declare(sc)
sc["charge"].begin_charge_move()
script(1, 1)
sc["decision"].choose(0)
script(1, 2, 3, 4)
ack(sc)   # battle-shock resolved, D6 roll queued
ack(sc)   # no 6s
check("a roll with no 6s inflicts nothing", len(alive_models(sc["charging"])) == 4)
check("and still resumes the charge", sc["movement"].move_mode == "charge" and not sc["grav"].is_busy)


# ======================================= 3. the charging unit is destroyed
print("\n3) if the mortal wounds wipe the charging unit out")

sc = scene(charger_models=2)
declare(sc)
sc["charge"].begin_charge_move()
script(1, 1)
sc["decision"].choose(0)
script(6, 6)  # both models' worth of mortal wounds
ack(sc)
ack(sc)
guard = 0
while sc["grav"].pending_damage_choice is not None and guard < 20:
    sc["grav"].choose_damage_model(sc["grav"].pending_damage_choice[0])
    guard += 1
check("the charging unit is wiped out", not alive_models(sc["charging"]),
      f"{len(alive_models(sc['charging']))} alive")
check("no charge move is opened on it", sc["movement"].move_mode is None)
check("and the charge attempt is finished, not left hanging", sc["charge"].state == IDLE)


# ================================================== 4. WHEN / TARGET clauses
print("\n4) WHEN / TARGET clauses")

sc = scene()
check("a charge on a BATTLESUIT unit qualifies", sc["grav"].can_offer(sc["charging"], sc["defender"]))
check("a friendly 'charger' does not", not sc["grav"].can_offer(sc["defender"], sc["defender"]))

sc["turn"].phase_index = PHASES.index(PHASE_SHOOTING)
check("outside the Charge phase it does not", not sc["grav"].can_offer(sc["charging"], sc["defender"]))
sc["turn"].phase_index = PHASES.index(PHASE_CHARGE)

sc["defender"].battle_shocked = True
check("a battle-shocked target is blocked (rule 01.07)",
      not sc["grav"].can_offer(sc["charging"], sc["defender"]))
sc["defender"].battle_shocked = False

sc["cps"].cp["Player 1"] = 0
check("no CP, no offer", not sc["grav"].can_offer(sc["charging"], sc["defender"]))
sc["cps"].cp["Player 1"] = 3

check("a non-BATTLESUIT target is refused",
      not sc["grav"].can_offer(sc["charging"], build_squad(STRIKE_TEAM, "Player 1", name="strike")))

# Rule 15.01: once per phase.
sc = scene(charger_models=3)
declare(sc)
sc["charge"].begin_charge_move()
script(1, 1)
sc["decision"].choose(0)
script(1, 1, 1)
ack(sc)
ack(sc)
check("first use resolved", not sc["grav"].is_busy)
check("a second charge the same phase gets no offer",
      not sc["grav"].can_offer(build_squad(BOYZ, "Player 2", name="2 More 1"), sc["defender"]))
sc["strat"].reset_phase()
check("but does once the phase turns over",
      sc["grav"].can_offer(sc["charging"], sc["defender"]))


# ================================ 5. it must not disrupt the charging player
print("\n5) the declaration is asked about ONCE, and the AI's charge survives it")

# ai/agent_driver.py re-calls begin_charge_move() for every retry of a failed
# approach (up to 13). A DECLINED offer leaves rule 15.01's ledger untouched,
# so without a memo the same declaration would re-prompt on every one of them.
sc = scene()
declare(sc)
sc["charge"].begin_charge_move()
check("asked once", sc["decision"].is_pending)
sc["decision"].choose(1)  # decline
sc["movement"].cancel_move()
opened = 0
for _ in range(5):
    sc["charge"].begin_charge_move()
    if sc["decision"].is_pending:
        opened += 1
        sc["decision"].choose(1)
    sc["movement"].cancel_move()
check("and NOT re-asked on the approach retries", opened == 0, f"{opened} extra prompts")

# The AI drives exactly this path. Its charge must survive the deferral rather
# than confirming a move that never opened (which would burn the charge).
from ai.agent_driver import AIMemory, _handle_charge
from ai.mock_agent import MockAgent

sc = scene()
declare(sc)
acted = _handle_charge(MockAgent(), AIMemory(), "Player 2", sc["state"].tokens,
                       sc["charge"], sc["movement"], None)
check("the AI's charge defers instead of moving", acted and sc["decision"].is_pending
      and sc["movement"].move_mode is None)
check("the declaration is still standing", sc["charge"].state == DECLARING_TARGETS
      and sc["defender"] in sc["charge"].charge_targets)
sc["decision"].choose(1)  # the human declines
check("answering it opens the charge move", sc["movement"].move_mode == "charge")

# And re-entering the AI branch must not un-select the already-declared target
# (toggle_charge_target() is a toggle).
sc = scene()
declare(sc)
_handle_charge(MockAgent(), AIMemory(), "Player 2", sc["state"].tokens,
               sc["charge"], sc["movement"], None)
sc["decision"].choose(1)
sc["movement"].cancel_move()
_handle_charge(MockAgent(), AIMemory(), "Player 2", sc["state"].tokens,
               sc["charge"], sc["movement"], None)
# Observed as "the charge REACHED A CONCLUSION", not as "the models moved":
# whether this particular geometry lets 11 models fit around 3 is beside the
# point (the baseline charge here fails on geometry too, with or without the
# stratagem). What the guard prevents is the charge never being resolved at
# all - and that is a stuck AI, re-offered the same declaration forever.
check("re-entering resolves the charge instead of stalling",
      sc["charge"].state == IDLE, f"state={sc['charge'].state}")

# A/B: an extra toggle reproduces exactly what the un-guarded code did - it
# de-selects the only declared target. Without the guard the charge cannot
# resolve, which is the stall this protects against.
sc = scene()
declare(sc)
_handle_charge(MockAgent(), AIMemory(), "Player 2", sc["state"].tokens,
               sc["charge"], sc["movement"], None)
sc["decision"].choose(1)
sc["movement"].cancel_move()
sc["charge"].toggle_charge_target(sc["defender"])  # what the old code did on re-entry
check("A/B: an un-done toggle leaves nothing declared", not sc["charge"].charge_targets)
sc["charge"].begin_charge_move()
check("A/B: and no charge move can open, which is the stall",
      sc["movement"].move_mode is None and sc["charge"].state == DECLARING_TARGETS)


# =================================================================== summary
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for name in FAIL:
    print(f"  FAILED: {name}")
sys.exit(1 if FAIL else 0)
