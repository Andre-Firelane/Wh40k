"""Tests for the AI's deterministic Command Re-roll on a failed charge
(ai/agent_driver.py's _charge_reroll_verdict()).

USER RULE, given in two parts:
  "kannst du der ki mitgeben, dass sie immer bei charges, die verfehlt sind
   einen command reroll macht? aber nur, wenn es auch gute nahkampf
   erfolgsaussichten gibt. zb nicht mit einem transporter."
  "und zwar bei der ersten gelegenheit für nahkampfeinheiten, die nach ihren
   charge roll nichts erreichen können. und gegner nicht mehr als 7 zoll
   entfernt sind."

So three conditions, all required: the roll reached NOTHING, the unit is a
real melee unit, and the nearest reachable enemy is within 7".

What carries risk here, and so gets the most attention:

  * each of the three conditions ISOLATED, with the other two held true, so a
    "did not re-roll" is attributable to one named condition rather than to
    whichever happened to fail first;
  * the 7" boundary itself, checked from both sides at the exact edge-to-edge
    distance rule 11.02 measures;
  * that it is deterministic in BOTH directions - the test agent raises on
    decide(), so "no API call" is proven for the yes case AND the no case;
  * that a roll which DID reach something is still handed to the agent, since
    trading a hit for a better one is a judgement call and not a rule.

Uses real ChargeController/CommandRerollController/StratagemController/
CommandPointManager/DiceManager/TurnTracker/GameState objects and real
datasheets throughout.

Run: python test_charge_reroll.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver
from ai.agent_driver import (
    MAX_CHARGE_REROLL_GAP_IN, MIN_CHARGE_REROLL_MELEE_FRACTION, _charge_reroll_verdict,
)
from game import dice as dice_mod
from game import maps
from game.charge import ChargeController
from game.command_points import CommandPointManager
from game.command_reroll import CommandRerollController
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BOYZ, TRUKK
from game.factions.tau_empire import STRIKE_TEAM
from game.game_state import GameState
from game.movement import MovementController
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_CHARGE, TurnTracker

m = maps.get("map2")
maps.apply_to_config(m)

checks, failed = 0, []


def ok(label, cond, detail=""):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label + ((" - " + detail) if detail else ""))


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


class RaisingAgent:
    def decide(self, *args, **kwargs):
        raise AssertionError("the deterministic charge-re-roll path must never call the agent")


def scene(gap_in=5.0, charger_sheet=BOYZ, cp=5, roll=(1, 2)):
    """An Ork unit `gap_in` EDGE TO EDGE from a T'au unit (the measurement
    rule 11.02 uses), with a charge declared and its roll still pending.

    The y offset is derived from the two base radii rather than hard-coded, so
    `gap_in` really is the number Squad.min_distance_to() will report - the
    7" boundary checks below are worthless otherwise."""
    st = GameState()
    charger = build_squad(charger_sheet, "Player 2", name="2 Charger 1")
    foe = build_squad(STRIKE_TEAM, "Player 1", name="1 Foe 1")
    separation = gap_in + charger.models[0].radius_in + foe.models[0].radius_in
    for i, mdl in enumerate(charger.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 20.0
    for i, mdl in enumerate(foe.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 20.0 + separation
    for sq in (charger, foe):
        for mdl in sq.models:
            st.add_token(mdl)

    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_CHARGE)
    tt.turn_owner = "Player 2"
    tt.set_active("Player 2")
    cps = CommandPointManager()
    cps.cp["Player 1"] = cps.cp["Player 2"] = cp
    dm = DiceManager()
    mc = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens, dice_manager=dm)
    cc = ChargeController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, movement_controller=mc)
    cr = CommandRerollController(StratagemController(command_points=cps), dm, turn_tracker=tt)
    script(*roll)
    cc.declare_charge(charger)
    return dict(state=st, charger=charger, foe=foe, dice=dm, charge=cc, reroll=cr,
                turn=tt, cp=cps, move=mc)


def verdict(sc, player="Player 2"):
    return _charge_reroll_verdict(sc["charge"], sc["dice"], player)


# ================================================== 1. the scene measures right
print("\n1) the fixture itself")

sc = scene(gap_in=5.0)
measured = sc["charger"].min_distance_to(sc["foe"])
ok("the scene really is 5.0 inches edge to edge", abs(measured - 5.0) < 0.01, f"{measured:.3f}")
ok("the charge roll is pending and reached nothing",
   sum(sc["dice"].pending_values) == 3 and not sc["charge"].targets_reachable_with(3))
ok("...but a 12 would reach", bool(sc["charge"].targets_reachable_with(12)))


# =================================== 2. the three conditions, one at a time
print("\n2) the three conditions, isolated")

sc = scene(gap_in=5.0)
v = verdict(sc)
ok("all three hold: a melee unit, 5 inches away, whose roll reached nothing -> RE-ROLL",
   v is not None and v[0] is True, str(v))

# (a) the roll has to have MISSED.
sc = scene(gap_in=5.0, roll=(4, 4))
ok("a roll that DID reach is left to the agent (verdict None, not a rule)",
   sc["charge"].targets_reachable_with(8) and verdict(sc) is None)

# (b) the unit has to be a melee unit - the "zb nicht mit einem transporter" half.
sc = scene(gap_in=5.0, charger_sheet=TRUKK)
v = verdict(sc)
ok("a Trukk at the same distance does NOT re-roll", v is not None and v[0] is False, str(v))
ok("...and the reason names the melee half", v is not None and "melee" in v[1], v[1] if v else "")

# (c) the enemy has to be within 7 inches - the new half.
sc = scene(gap_in=9.0)
v = verdict(sc)
ok("the same Boyz 9 inches away do NOT re-roll", v is not None and v[0] is False, str(v))
ok("...and the reason names the distance",
   v is not None and '9.0"' in v[1] and str(int(MAX_CHARGE_REROLL_GAP_IN)) in v[1], v[1] if v else "")
ok("...while the melee half would have passed on its own",
   agent_driver._best_melee_prospect(sc["charger"], sc["charge"].targets_reachable_with(12))[0]
   >= MIN_CHARGE_REROLL_MELEE_FRACTION)

# Nothing reachable at all, even on a 12.
sc = scene(gap_in=13.0)
ok("nothing within 12 inches: no charge can be declared at all",
   sc["charge"].state == "idle" and verdict(sc) is None)


# ============================================================ 3. the boundary
print(f"\n3) the {MAX_CHARGE_REROLL_GAP_IN:.0f}-inch boundary, from both sides")

sc = scene(gap_in=MAX_CHARGE_REROLL_GAP_IN)
v = verdict(sc)
ok(f"exactly {MAX_CHARGE_REROLL_GAP_IN:.1f} inches still re-rolls (the limit is inclusive)",
   v is not None and v[0] is True, str(v))
sc = scene(gap_in=MAX_CHARGE_REROLL_GAP_IN + 0.5)
v = verdict(sc)
ok(f"{MAX_CHARGE_REROLL_GAP_IN + 0.5:.1f} inches does not", v is not None and v[0] is False, str(v))


# ================================================= 4. scope: whose roll is it
print("\n4) scope")

sc = scene(gap_in=5.0)
ok("another player's charge is not this one's call", verdict(sc, player="Player 1") is None)
ok("no dice manager / no controller -> no call",
   _charge_reroll_verdict(None, sc["dice"], "Player 2") is None
   and _charge_reroll_verdict(sc["charge"], None, "Player 2") is None)


# ============================== 5. end to end, with an agent that would raise
print("\n5) end to end through _maybe_command_reroll(), 0 agent calls")


class _Log:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)


def drive(sc, log=None):
    memory = agent_driver.AIMemory()
    return agent_driver._maybe_command_reroll(
        RaisingAgent(), memory, sc["reroll"], sc["turn"], sc["state"], "Player 2", None,
        charge_controller=sc["charge"], game_log=log,
    )


sc = scene(gap_in=5.0)
log = _Log()
before = list(sc["dice"].pending_values)
handled = drive(sc, log)
ok("it acts, spends exactly 1 CP, and never asks the agent",
   handled and sc["cp"].cp["Player 2"] == 4)
ok("rule 15.02: the charge roll is re-rolled IN FULL (both dice are new)",
   len(sc["dice"].pending_values) == 2 and sc["dice"].already_rerolled == {0, 1},
   f"{before} -> {list(sc['dice'].pending_values)}")
ok("and it says why in the log",
   any("[charge reroll]" in l and "re-rolls" in l for l in log.lines),
   next((l for l in log.lines if "[charge reroll]" in l), ""))

sc = scene(gap_in=9.0)
log = _Log()
handled = drive(sc, log)
ok("too far: it settles the decision without the agent and keeps the CP",
   handled and sc["cp"].cp["Player 2"] == 5 and not sc["dice"].already_rerolled)
ok("and logs the reason it declined",
   any("[charge reroll]" in l and "keeps" in l for l in log.lines),
   next((l for l in log.lines if "[charge reroll]" in l), ""))

sc = scene(gap_in=5.0, charger_sheet=TRUKK)
handled = drive(sc)
ok("a transport keeps its CP too, still without an agent call",
   handled and sc["cp"].cp["Player 2"] == 5)

sc = scene(gap_in=5.0, cp=0)
ok("with no CP there is nothing to decide at all", not drive(sc))


# =============================================================== summary
print(f"\n{checks - len(failed)}/{checks} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  - " + f)
    sys.exit(1)
