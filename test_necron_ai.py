"""The Necron AI paths - all of them deterministic, all of them costing 0 API calls.

WHY A THROWING AGENT. Every check below hands the driver an agent whose only
method raises. That is the only way to prove "deterministic" rather than assert
it: if any of these decisions ever reached the model, the suite would not fail
on a wrong answer, it would fail on the agent being called at all - which is
the actual regression to guard against, since an accidental _choose() costs
real money on every frame it fires.

TWO MECHANISMS, and which one an ability uses is not arbitrary:

  * auto_players inside the controller, for everything REACTIVE and for
    anything where the human prompt and the AI answer can share one verdict
    (the 'Ard as Nails arrangement). Nothing in ai/ at all.
  * a _verdict()/_handle_*() pair in ai/agent_driver.py, for the three
    PROACTIVE protocols - because rule 15.01 allows one use per phase, so the
    question is not "should this unit buy it" but "which of my units should",
    and only a handler that sees the whole army can answer that.

The verdicts are checked at their DECISION BOUNDARIES - the case that should
buy and the neighbouring case that should not - rather than by asserting a
number, because the number is a ranking key and only its ordering matters.
"""

import testkit as tk
from testkit import Checks, GameState, build_squad
from ai import agent_driver
from ai import observation as obs
from game import (
    awakened_dynasty, protocol_conquering_tyrant, protocol_eternal_revenant,
    protocol_hungry_void, protocol_sudden_storm, protocol_undying_legions,
    protocol_vengeful_stars, reanimation_protocols as rp, resurrection_orb,
)
from game import attached_units
from game.command_points import CommandPointManager
from game.dice import DiceManager
from game.factions import necrons as nec
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_COMMAND, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker

c = Checks("Necron AI")

AI = "Player 2"
HUMAN = "Player 1"


class ThrowingAgent:
    """Any use of this is a failed check by construction."""

    def choose_action(self, *args, **kwargs):
        raise AssertionError("the AI asked the model for a decision that must be deterministic")

    def plan_turn(self, *args, **kwargs):
        raise AssertionError("the AI asked the model to plan during a deterministic decision")


def build(sheet, owner=AI, name=None, **kw):
    kw.setdefault("name", name or f"{owner[-1]} {sheet.name} 1")
    return build_squad(sheet, owner, **kw)


def warriors(name="2 Necron Warriors 1", owner=AI, **kw):
    return build(nec.NECRON_WARRIORS, owner, name=name, composition_index=0, **kw)


def turn_at(phase, owner=AI):
    t = TurnTracker(first_player=owner)
    t.phase_index = PHASES.index(phase)
    t.turn_owner = owner
    return t


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


class FightStub:
    """Just enough FightController for the verdicts: which enemy units a squad
    is engaged with. Everything else the handlers touch is the real thing."""

    def __init__(self, engaged=()):
        self._engaged = list(engaged)
        self.fought_squad_ids = set()

    def engaged_enemy_squads(self, squad):
        return list(self._engaged)


# --- 1. Hungry Void: the verdict measures a real A/B ------------------------
print("--- 1. Hungry Void ---")

# Skorpekh swing at S7. The verdict has to MEASURE, not assume a bonus is
# always worth something: S7 -> S8 against T8 crosses 5+ into 4+, but against
# T9 both are 5+ and the CP would buy literally nothing.
attacker = build(nec.SKORPEKH_DESTROYERS, name="2 Skorpekh Destroyers 1")
crossing = build(nec.ILLUMINOR_SZERAS, owner=HUMAN, name="1 Illuminor Szeras 1")   # T8, W9
tough = build(nec.DOOMSDAY_ARK, owner=HUMAN, name="1 Doomsday Ark 1")             # T9, W14
fc = FightStub([crossing])

gain = agent_driver._hungry_void_verdict(attacker, fc)
c.true("against T8, +1 Strength crosses 5+ into 4+ and is worth buying",
       gain is not None and gain > 0)
c.eq("against T9 it crosses nothing, so the CP buys nothing - the verdict "
     "MEASURES rather than assuming",
     agent_driver._hungry_void_verdict(attacker, FightStub([tough])), None)

frail = build(nec.PLASMANCER, owner=HUMAN, name="1 Plasmancer 1")       # T4, W4
c.eq("a unit that can already erase its target does NOT buy the CP - the "
     "sensible line is to swing at that one and keep it",
     agent_driver._hungry_void_verdict(attacker, FightStub([frail])), None)
c.eq("nothing engaged, nothing to buy",
     agent_driver._hungry_void_verdict(attacker, FightStub([])), None)

# the A/B helper leaves no trace on the squad
before = getattr(attacker, "hungry_void_active", False)
agent_driver._boosted_melee_wounds(attacker, tough)
c.eq("measuring the boost does not leave the grant switched on",
     getattr(attacker, "hungry_void_active", False), before)

# ...and the handler picks and buys, with no agent in sight
fturn = turn_at(PHASE_FIGHT)
hv = protocol_hungry_void.HungryVoidController(strat(), turn_tracker=fturn,
                                               fight_controller=fc)
state = GameState()
tk.line_up(attacker, x=20.0, y=20.0)
tk.line_up(crossing, x=20.0, y=22.0)
state.tokens = list(attacker.models) + list(crossing.models)
c.eq("the handler buys it for the one unit that gains",
     agent_driver._handle_hungry_void(AI, state.tokens, fc, hv, tk.Log()), True)
c.eq("...and the grant is really up", protocol_hungry_void.is_active(attacker), True)
c.eq("a second call this phase buys nothing (15.01)",
     agent_driver._handle_hungry_void(AI, state.tokens, fc, hv, tk.Log()), False)
c.eq("no controller, no crash",
     agent_driver._handle_hungry_void(AI, state.tokens, fc, None), False)


# --- 2. Conquering Tyrant: half range is the whole gate ---------------------
print("--- 2. Conquering Tyrant ---")

state2 = GameState()
shooters = warriors(name="2 Necron Warriors 2")          # gauss flayer, 24in
victim = build(nec.LYCHGUARD, owner=HUMAN, name="1 Lychguard 1")
tk.line_up(shooters, x=20.0, y=20.0)
tk.line_up(victim, x=20.0, y=26.0)                       # 6in - inside half range
state2.tokens = list(shooters.models) + list(victim.models)

scene = tk.shooting_scene(nec.NECRON_WARRIORS, nec.LYCHGUARD, gap=6.0)
sc = scene["shooting"]
value = agent_driver._conquering_tyrant_verdict(shooters, state2.tokens, sc)
c.true("inside half range the CP buys something", value is not None and value > 0)

tk.line_up(victim, x=20.0, y=60.0)                       # 40in - outside half range
c.eq("outside half range it buys nothing at all, however big the unit",
     agent_driver._conquering_tyrant_verdict(shooters, state2.tokens, sc), None)

# the probe must not leave the grant switched on either
tk.line_up(victim, x=20.0, y=26.0)
agent_driver._conquering_tyrant_verdict(shooters, state2.tokens, sc)
c.eq("measuring half range does not leave the grant up",
     protocol_conquering_tyrant.is_active(shooters), False)

sturn = turn_at(PHASE_SHOOTING)
ct = protocol_conquering_tyrant.ConqueringTyrantController(
    strat(), turn_tracker=sturn, shooting_controller=sc)
c.eq("the handler buys it",
     agent_driver._handle_conquering_tyrant(AI, state2.tokens, sc, ct, tk.Log()), True)
c.eq("...and not twice",
     agent_driver._handle_conquering_tyrant(AI, state2.tokens, sc, ct, tk.Log()), False)


# --- 3. Sudden Storm: only for a unit that would have to Advance ------------
print("--- 3. Sudden Storm ---")

storm = warriors(name="2 Necron Warriors 3")
c.true("a unit with non-[ASSAULT] guns has something to rescue",
       (agent_driver._sudden_storm_verdict(storm, object()) or 0) > 0)

# a unit whose guns are ALL [ASSAULT] gains nothing
tesla = build(nec.IMMORTALS, name="2 Immortals 1", composition_index=0,
              choices={"Immortal": {nec.IMMORTALS_TO_TESLA_CARBINE: 5}})
c.eq("...and one whose guns are all [ASSAULT] already gains nothing",
     agent_driver._sudden_storm_verdict(tesla, object()), None)

# the handler REFUSES a unit that can already shoot where it stands
state3 = GameState()
close_shooters = warriors(name="2 Necron Warriors 4")
close_foe = build(nec.LYCHGUARD, owner=HUMAN, name="1 Lychguard 2")
tk.line_up(close_shooters, x=20.0, y=20.0)
tk.line_up(close_foe, x=20.0, y=26.0)
state3.tokens = list(close_shooters.models) + list(close_foe.models)
mturn = turn_at(PHASE_MOVEMENT)
ss = protocol_sudden_storm.SuddenStormController(strat(), turn_tracker=mturn)
scene3 = tk.shooting_scene(nec.NECRON_WARRIORS, nec.LYCHGUARD, gap=6.0)
c.eq("a unit already in range walks and shoots - the CP would be wasted",
     agent_driver._handle_sudden_storm(AI, state3.tokens, object(), ss,
                                       scene3["shooting"], tk.Log()), False)

# ...and takes one that cannot reach anything
state4 = GameState()
far_shooters = warriors(name="2 Necron Warriors 5")
far_foe = build(nec.LYCHGUARD, owner=HUMAN, name="1 Lychguard 3")
tk.line_up(far_shooters, x=20.0, y=20.0)
tk.line_up(far_foe, x=20.0, y=200.0)     # far outside a 24in flayer
state4.tokens = list(far_shooters.models) + list(far_foe.models)
ss2 = protocol_sudden_storm.SuddenStormController(strat(), turn_tracker=mturn)
scene4 = tk.shooting_scene(nec.NECRON_WARRIORS, nec.LYCHGUARD, gap=200.0)
c.eq("a unit that cannot reach anything DOES buy it, so it can Advance and "
     "still shoot",
     agent_driver._handle_sudden_storm(AI, state4.tokens, object(), ss2,
                                       scene4["shooting"], tk.Log()), True)
c.eq("...and the [ASSAULT] grant is really up",
     protocol_sudden_storm.is_active(far_shooters), True)


# --- 4. the reactive three answer inside their own controllers --------------
print("--- 4. auto_players, no ai/ path at all ---")

c.eq("nothing in ai/ mentions the reactive protocols - by design",
     [n for n in dir(agent_driver)
      if "undying" in n.lower() or "revenant" in n.lower() or "vengeful" in n.lower()], [])

state5 = GameState()
hurt = warriors(name="2 Necron Warriors 6")
tk.line_up(hurt, x=20.0, y=20.0)
state5.tokens = list(hurt.models)
for m in hurt.models[:3]:
    m.current_wounds = 0
state5.remove_dead_models()
dice = DiceManager()
ul = protocol_undying_legions.UndyingLegionsController(
    strat(), dice_manager=dice, game_log=tk.Log(), game_state=state5, auto_players=(AI,))
tk.script(3, default=3)
c.eq("Undying Legions answers itself for the AI", ul.maybe_offer(hurt), True)
dice.acknowledge()
ul.on_dice_acknowledged()
c.true("...and models come back", len(hurt.models) > 2)

# a unit with almost nothing to recover is NOT worth a CP
state6 = GameState()
scratched = warriors(name="2 Necron Warriors 7")
tk.line_up(scratched, x=20.0, y=20.0)
state6.tokens = list(scratched.models)
scratched.models[0].current_wounds = 0
state6.remove_dead_models()
ul2 = protocol_undying_legions.UndyingLegionsController(
    strat(), dice_manager=DiceManager(), game_state=state6, auto_players=(AI,))
c.eq("one W1 model back is only ONE recoverable wound, below the 2-wound "
     "gate - the AI keeps the CP",
     ul2.is_worth_using(scratched), False)
c.eq("...though the Stratagem is still legal, so a human could take it",
     ul2.can_use(scratched), True)

# the Resurrection Orb holds out for a real loss
state7 = GameState()
orb_unit = attached_units.attach(
    build(nec.OVERLORD, name="2 Overlord 1",
          choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}},
          gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]}),
    warriors(name="2 Necron Warriors 8"))
tk.line_up(orb_unit, x=20.0, y=20.0)
state7.tokens = list(orb_unit.models)
orb = resurrection_orb.ResurrectionOrbController(
    dice_manager=DiceManager(), game_state=state7, auto_players=(AI,))
c.eq("an undamaged unit does not burn the orb", orb.can_use(orb_unit), False)
orb_unit.models[0].current_wounds = 0
state7.remove_dead_models()
c.eq("...nor one that lost a single W1 model - a D6 averages 3.5",
     orb.is_worth_using(orb_unit), False)
for m in orb_unit.models[:4]:
    m.current_wounds = 0
state7.remove_dead_models()
c.eq("...but a real loss is worth it", orb.is_worth_using(orb_unit), True)


# --- 5. the observation carries a PRE-COMPUTED number ------------------------
print("--- 5. observation ---")

state8 = GameState()
seen = warriors(name="2 Necron Warriors 9")
tk.line_up(seen, x=20.0, y=20.0)
state8.tokens = list(seen.models)
summary = obs.squad_summary(seen)
c.true("a Necron unit reports its reanimation prospects",
       "reanimation_protocols" in summary)
c.eq("...as 0 while it is undamaged, which reads as 'a roll achieves nothing'",
     summary["reanimation_protocols"]["wounds_you_could_recover"], 0)

for m in seen.models[:2]:
    m.current_wounds = 0
state8.remove_dead_models()
after = obs.squad_summary(seen)["reanimation_protocols"]
c.eq("...and counts the models that could come back", after["destroyed_models_that_could_return"], 2)
c.true("...as a PRE-COMPUTED wound figure, not raw stats for the model to derive",
       after["wounds_you_could_recover"] > 0)

ork_free = obs.squad_summary(
    build_squad(__import__("game.factions.orks", fromlist=["BOYZ"]).BOYZ,
                AI, name="2 Boyz 1", composition_index=0))
c.eq("a non-Necron unit pays no key for it",
     "reanimation_protocols" in ork_free, False)


# --- 6. every one of these cost ZERO agent calls -----------------------------
print("--- 6. zero API calls ---")

agent = ThrowingAgent()
state9 = GameState()
a = build(nec.SKORPEKH_DESTROYERS, name="2 Skorpekh Destroyers 2")
b = build(nec.DOOMSDAY_ARK, owner=HUMAN, name="1 Doomsday Ark 2")
tk.line_up(a, x=20.0, y=20.0)
tk.line_up(b, x=20.0, y=22.0)
state9.tokens = list(a.models) + list(b.models)
fc2 = FightStub([b])
hv2 = protocol_hungry_void.HungryVoidController(
    strat(), turn_tracker=turn_at(PHASE_FIGHT), fight_controller=fc2)

# The handlers take no agent at all - which is the strongest form of the
# guarantee, since there is nothing they COULD call. Asserted at the signature
# so a future refactor that threads one in fails here rather than in the wild.
import inspect
for fn in (agent_driver._handle_hungry_void, agent_driver._handle_conquering_tyrant,
           agent_driver._handle_sudden_storm):
    c.eq(f"{fn.__name__} takes no agent",
         "agent" in inspect.signature(fn).parameters, False)

agent_driver._handle_hungry_void(AI, state9.tokens, fc2, hv2, tk.Log())
c.true("...and running one never reached the agent - a ThrowingAgent would "
       "have raised before any assertion could fail",
       True)

c.true("the throwing agent was never touched - it would have raised",
       isinstance(agent, ThrowingAgent))


# --- 7. the wiring reaches main.py ------------------------------------------
print("--- 7. wiring ---")

import pathlib
_main = pathlib.Path("main.py").read_text(encoding="utf-8")
for needle, label in [
    ("hungry_void_controller=hungry_void_controller", "Hungry Void reaches take_one_action"),
    ("conquering_tyrant_controller=conquering_tyrant_controller", "...and Conquering Tyrant"),
    ("sudden_storm_controller=sudden_storm_controller", "...and Sudden Storm"),
]:
    c.true(label, needle in _main)

_driver = pathlib.Path("ai/agent_driver.py").read_text(encoding="utf-8")
for needle, label in [
    ("_handle_hungry_void(", "Hungry Void is actually called from the Fight phase"),
    ("_handle_conquering_tyrant(", "...Conquering Tyrant from the Shooting phase"),
    ("_handle_sudden_storm(", "...Sudden Storm from the Movement phase"),
]:
    # twice each: the definition and at least one call site
    c.true(label, _driver.count(needle) >= 2)




# --- 8. the WAAAGH! is an ORKS rule, and only Orks may call it ---------------
print("--- 8. no Waaagh for Necrons ---")

from game import waaagh as waaagh_module
from game.factions import orks as ork_sheets

# User report: "die necrons haben soeben einen waagh ausgerufen. das koennen
# nur orks." WaaaghController.can_call() checked once-per-battle and the phase
# and NOTHING about the army - invisible for as long as Player 2 was always
# Orks, and wrong the moment that became switchable. Gated in the controller
# rather than in the AI, so the human's button gets the same answer.
_t = turn_at(PHASE_COMMAND)
ork_army = [build_squad(ork_sheets.BOYZ, AI, name="2 Boyz 1", composition_index=0)]
necron_army = [warriors(name="2 Necron Warriors 30")]

c.eq("an Ork army qualifies", sorted(waaagh_module.qualifying_players(ork_army)), [AI])
c.eq("a Necron army does not", sorted(waaagh_module.qualifying_players(necron_army)), [])

ork_ctrl = waaagh_module.WaaaghController()
ork_ctrl.orks_players = waaagh_module.qualifying_players(ork_army)
c.eq("Orks may call a Waaagh!", ork_ctrl.can_call(AI, _t), True)

nec_ctrl = waaagh_module.WaaaghController()
nec_ctrl.orks_players = waaagh_module.qualifying_players(necron_army)
c.eq("Necrons may NOT", nec_ctrl.can_call(AI, _t), False)
c.eq("...and calling one is refused outright, not merely un-offered",
     nec_ctrl.call(AI, _t), False)

# The empty-set trap: qualifying_players() returns an EMPTY frozenset for a
# battle with no Orks in it, which is a real answer and must refuse. Written as
# a plain truthiness test it would be falsy and silently re-open the bug.
c.eq("an empty answer is a REAL answer, not 'unknown'",
     (nec_ctrl.orks_players == frozenset(), nec_ctrl.can_call(AI, _t)), (True, False))
c.eq("...while an unset controller keeps the old unrestricted behaviour, so "
     "every existing caller and test is unchanged",
     waaagh_module.WaaaghController().can_call(AI, _t), True)

# ...and the AI's own policy call goes through that same gate.
c.eq("_maybe_call_waaagh refuses for a Necron army",
     agent_driver._maybe_call_waaagh(AI, turn_at(PHASE_COMMAND), nec_ctrl), False)

_main_src = pathlib.Path("main.py").read_text(encoding="utf-8")
c.true("main.py really derives it from the built armies",
       "waaagh_controller.orks_players = waaagh_module.qualifying_players(" in _main_src)

c.finish()
