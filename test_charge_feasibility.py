"""Charge feasibility BEFORE the AI declares (ai/agent_driver._handle_charge's
declaration loop, _charge_nearest_legal_slot): a target with no legal
standing room round it is not offered, and the odds are quoted to the
nearest legal spot rather than to the unit's edge.

Part of the AI-movement review of 2026-09-09. Both reported charges were
declared against targets the charge could not be completed on: one parked
in Dense terrain with its ring 27 legal slots of 196 and the nearest 11.17"
off against a 9.3" straight-line gap, one behind the charger's own Warriors.
Rule 11.02's eligibility (12" in a straight line) stays exactly as printed -
a player may declare a hopeless charge - but the engine must not OFFER what
it does not want chosen (error class 5), and it must not quote a roll that
cannot reach anywhere legal.

The AI's own observation (ai/observation.py's charge_now) is deliberately
untouched: that number is pinned elsewhere and is a separate decision.

Real ChargeController / MovementController / AIMemory objects, real
datasheets, map2 dimensions, driven through the real _handle_charge().

Run: python test_charge_feasibility.py
"""
import io
import math
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from ai import agent_driver as ad  # noqa: E402
from ai.agent_driver import AIMemory  # noqa: E402
from game import config, maps  # noqa: E402
from game.charge import CHARGE_RANGE_IN, IDLE, ChargeController  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.factions.orks import BOYZ  # noqa: E402
from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.terrain import DENSE, Obstacle  # noqa: E402
from game.turn import PHASES, PHASE_CHARGE, TurnTracker  # noqa: E402
import testkit as tk  # noqa: E402
from testkit import Checks  # noqa: E402

maps.apply_to_config(maps.get("map2"))
c = Checks("charge feasibility")


class Spy:
    """Records what it is offered and always DECLARES."""

    def __init__(self):
        self.offers = []

    def decide(self, observation):
        actions = observation["available_actions"]
        self.offers.append([a.get("description", "") for a in actions])
        for i, a in enumerate(actions):
            if "declare a charge" in a.get("description", ""):
                return i
        return 0


def scene(target_at=(20.0, 28.0), charger_at=(20.0, 20.0), obstacles=()):
    st = GameState()
    charger = tk.build(BOYZ, owner="Player 2", name="2 Boyz 1")
    charger.models = charger.models[:5]
    for i, m in enumerate(charger.models):
        m.x_in, m.y_in = charger_at[0] + i * 1.4, charger_at[1]
        st.add_token(m)
    target = tk.build(STRIKE_TEAM, owner="Player 1", name="1 Strike Team 1")
    target.models = target.models[:3]
    for i, m in enumerate(target.models):
        m.x_in, m.y_in = target_at[0] + i * 1.3, target_at[1]
        st.add_token(m)
    for o in obstacles:
        st.obstacles.append(o)
    tt = TurnTracker()
    tt.started = True
    tt.battle_round = 2
    tt.phase_index = PHASES.index(PHASE_CHARGE)
    tt.turn_owner = tt.active_player = "Player 2"
    dm = DiceManager()
    mc = MovementController(all_tokens=st.tokens, obstacles=st.obstacles, turn_tracker=tt,
                            board_width_in=config.BOARD_WIDTH_IN, board_height_in=config.BOARD_HEIGHT_IN)
    cc = ChargeController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, movement_controller=mc)
    return dict(state=st, charger=charger, target=target, turn=tt, dice=dm, movement=mc, charge=cc)


def handle(sc, agent, memory, log):
    return ad._handle_charge(agent, memory, "Player 2", sc["state"].tokens, sc["charge"], sc["movement"],
                             None, game_log=log)


# ================================================== 1. nowhere legal to stand
print("1) a target with no legal standing room is not offered")
box = Obstacle(21.3, 28.4, 20.0, 6.2, DENSE)   # the Strike Team parked inside a Dense box
sc = scene(obstacles=[box])
c.true("scene check: rule 11.02 still lets the unit declare", sc["charge"].can_declare_charge(sc["charger"]))
c.eq("scene check: the ring has no legal slot", ad._charge_nearest_legal_slot(sc["charger"], sc["target"], sc["movement"]), None)
spy, memory, log = Spy(), AIMemory(), tk.Log()
acted = handle(sc, spy, memory, log)
c.eq("no action is taken", acted, False)
c.eq("the agent is never asked", spy.offers, [])
c.eq("the charge is not declared", sc["charge"].state, IDLE)
c.true("the unit is recorded as declined for the phase", sc["charger"].name in memory.declined_charge)
line = [ln for ln in log.lines if "not offered" in ln]
c.true(f"the log says why, once ({str(line)[:110]})", len(line) == 1 and "no legal standing room" in line[0])
acted = handle(sc, spy, memory, log)
c.true("a second call in the same phase neither acts nor logs again",
       acted is False and sum(1 for ln in log.lines if "not offered" in ln) == 1)

# ================================================== 2. open ground: offered
print("2) open ground: offered, with the odds to the unit's edge as before")
sc = scene()
spy, memory, log = Spy(), AIMemory(), tk.Log()
walk = ad._charge_nearest_legal_slot(sc["charger"], sc["target"], sc["movement"])
gap = sc["charger"].min_distance_to(sc["target"])
c.true(f"scene check: the nearest legal slot is not further than the unit (walk {walk:.2f}\", gap {gap:.2f}\")",
       walk is not None and walk <= gap + 0.5)
acted = handle(sc, spy, memory, log)
c.true("the charge is offered and declared", acted and len(spy.offers) == 1 and sc["charge"].active_squad is sc["charger"])
desc = next((d for d in spy.offers[0] if "declare a charge" in d), "")
quoted = re.search(r"come up (\d+)\+", desc)
c.true(f"...quoting the roll needed ({desc[:110]})", quoted is not None)
c.eq("...which is the routed gap, as before (the near side is open)",
     int(quoted.group(1)) if quoted else None, math.ceil(ad._charge_gap(sc["charger"], sc["target"], sc["movement"])))
c.true("...without a blocked-side note", "near side is blocked" not in desc)

# ==================================== 3. near side blocked, a flank open
print("3) the near side blocked: the roll is quoted to the nearest legal spot")
# A Dense strip between the two units, wide enough that every slot on the
# near face AND both flanks of the target is on it - the legal ring is behind
# the target, reached round the strip's ends (the AI crosses walls, but may
# not END on one - 13.05).
strip = Obstacle(21.3, 26.3, 16.0, 2.2, DENSE)   # centred: x 13.3-29.3, y 25.2-27.4 (the target's bases start at 27.51)
sc = scene(obstacles=[strip])
walk = ad._charge_nearest_legal_slot(sc["charger"], sc["target"], sc["movement"])
gap = ad._charge_gap(sc["charger"], sc["target"], sc["movement"])
c.true(f"scene check: the nearest legal slot is round the flank (walk {walk:.2f}\" vs gap {gap:.2f}\")",
       walk is not None and walk - gap >= ad.CHARGE_DETOUR_REPORT_IN)
c.true("scene check: still within 12\"", walk <= CHARGE_RANGE_IN)
spy, memory, log = Spy(), AIMemory(), tk.Log()
acted = handle(sc, spy, memory, log)
c.true("the charge is still offered (a flank is open)", acted and len(spy.offers) == 1)
desc = next((d for d in spy.offers[0] if "declare a charge" in d), "")
quoted = re.search(r"come up (\d+)\+", desc)
c.eq("...quoting the walk to the nearest legal spot, not the gap",
     int(quoted.group(1)) if quoted else None, math.ceil(walk))
c.true(f"...and saying why ({desc[-120:]})", "near side is blocked" in desc)

# ====================================== 4. the observation is untouched
print("4) the AI's own charge odds (ai/observation.py) are a separate decision")
obs_src = io.open(os.path.join("ai", "observation.py"), encoding="utf-8").read()
c.true("observation.charge_now still exists", "def charge_now(" in obs_src)
c.true("...and does not read the ring", "_charge_nearest_legal_slot" not in obs_src and "_engagement_slots" not in obs_src)

# ================================================================ 5. source
print("5) guards at the source")
driver = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()
loop = driver[driver.index("# Otherwise: look for a new squad to declare"):driver.index("def _consolidate_toward_squads(")]
c.true("the gate stands before the offer", "if reachable and not feasible:\n            memory.declined_charge.add(candidate.name)" in loop)
c.true("...and the odds use the longer of gap and walk", "needed = math.ceil(max(gap, walk))" in loop)
c.true("...and quote the blocked side", "the near side is blocked" in loop)
c.true("the ring asked is the charge ring", "_CHARGE_RING_INNER_EDGE_IN,\n        legal=_engagement_slot_filter(candidate, movement_controller, keep_out))" in driver)

c.finish()
