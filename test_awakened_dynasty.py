"""The Awakened Dynasty detachment: Command Protocols and its six Stratagems.

WHAT IS WORTH GUARDING HERE is not "does the flag get set" - it is the WHEN and
the TARGET lines, because those are where a Stratagem goes wrong in a way
nobody notices: a button that appears one phase too early, a unit that can buy
the same grant twice, an upgrade clause that fires without its leader. So most
checks below drive can_use() across the boundary rather than asserting an
effect, and the effects themselves are measured at the site that consumes them.

FIVE OF THE SIX have a "if a NECRONS CHARACTER is leading your unit" clause, and
all five read it from game/awakened_dynasty.py. That shared predicate gets its
own section, because getting it wrong once would get it wrong five times.
"""

import pathlib

import testkit as tk
from testkit import Checks, GameState, build_squad, script
from game import (
    attached_units, awakened_dynasty, protocol_conquering_tyrant, protocol_eternal_revenant,
    protocol_hungry_void, protocol_sudden_storm, protocol_undying_legions,
    protocol_vengeful_stars, reanimation_protocols as rp, reroll_scope,
)
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import necrons as nec
from game.factions import orks
from game.stratagems import StratagemController
from game.turn import PHASE_COMMAND, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game import weapons as w

c = Checks("Awakened Dynasty")

AI = "Player 2"


def build(sheet, owner=AI, name=None, **kw):
    kw.setdefault("name", name or f"{owner[-1]} {sheet.name} 1")
    return build_squad(sheet, owner, **kw)


def warriors(name="2 Necron Warriors 1", owner=AI):
    return build(nec.NECRON_WARRIORS, owner, name=name, composition_index=0)


def led_warriors(name="2 Necron Warriors 2"):
    return attached_units.attach(build(nec.OVERLORD, name="2 Overlord 1"),
                                 warriors(name=name))


def turn_at(phase, owner=AI):
    t = TurnTracker(first_player=owner)
    from game.turn import PHASES
    t.phase_index = PHASES.index(phase)
    t.turn_owner = owner
    return t


def strat_controller(cp=10, turn=None):
    """A real StratagemController with a real CP ledger - the 15.01
    bookkeeping is half of what these checks are about, so a stub would test
    the stub."""
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


# --- 1. the shared predicates ------------------------------------------------
print("--- 1. shared predicates ---")

c.eq("Player 2 has the detachment", awakened_dynasty.has_detachment(AI), True)
c.eq("Player 1 does not", awakened_dynasty.has_detachment("Player 1"), False)
c.eq("a Necron unit is a NECRONS unit",
     awakened_dynasty.is_necrons_unit(warriors()), True)
c.eq("an Ork unit is not",
     awakened_dynasty.is_necrons_unit(build(orks.BOYZ, name="2 Boyz 1")), False)
c.eq("an Ork unit is never a legal TARGET, even for Player 2",
     awakened_dynasty.stratagem_target_ok(build(orks.BOYZ, name="2 Boyz 2")), False)
c.eq("a Necron unit belonging to a player WITHOUT the detachment is not either",
     awakened_dynasty.stratagem_target_ok(warriors(name="1 Necron Warriors 1", owner="Player 1")), False)

c.eq("an unled unit is not led by a CHARACTER",
     awakened_dynasty.is_led_by_character(warriors()), False)
c.eq("...and one with an Overlord attached is",
     awakened_dynasty.is_led_by_character(led_warriors()), True)


# --- 2. Command Protocols (the detachment rule) -----------------------------
print("--- 2. Command Protocols ---")

c.eq("an unled unit gets no bonus", awakened_dynasty.hit_modifiers(warriors()), [])
led = led_warriors(name="2 Necron Warriors 3")
mods = awakened_dynasty.hit_modifiers(led)
c.eq("a led unit gets exactly one modifier", len(mods), 1)
c.eq("...and it is NEGATIVE, because a Modifier adjusts the THRESHOLD and "
     "'add 1 to the Hit roll' makes that easier", mods[0].amount, -1)
c.eq("...labelled so the roll's log line says what changed it",
     mods[0].source, "Command Protocols")

# it reaches BOTH attack steps
scene = tk.shooting_scene(nec.IMMORTALS, nec.LYCHGUARD, gap=12.0)
sc = scene["shooting"]
sc.active_squad = led
group = {"pairs": [(led.models[0], w.GaussFlayerProfile())], "target_squad": scene["target"]}
c.true("Command Protocols reaches the SHOOTING hit step",
       any(m.source == "Command Protocols" for m in sc._hit_modifiers(group)))
fight = tk.fight_scene(nec.SKORPEKH_DESTROYERS, nec.LYCHGUARD)
fc = fight["fight"]
fc.fighting_squad = led
c.true("...and the FIGHT hit step - its text says 'an attack', not 'a ranged attack'",
       any(m.source == "Command Protocols" for m in fc._hit_modifiers(led.models[0], fight["target"])))

# A/B at the source
_orig = awakened_dynasty.has_detachment
try:
    awakened_dynasty.has_detachment = lambda player: False
    c.eq("A/B: an army WITHOUT the detachment gets nothing",
         awakened_dynasty.hit_modifiers(led), [])
finally:
    awakened_dynasty.has_detachment = _orig
c.eq("...and restored, the bonus is back", len(awakened_dynasty.hit_modifiers(led)), 1)


# --- 3. Protocol of the Hungry Void -----------------------------------------
print("--- 3. Hungry Void ---")

turn = turn_at(PHASE_FIGHT)
sc_ = strat_controller(turn=turn)
hv = protocol_hungry_void.HungryVoidController(sc_, turn_tracker=turn)
plain = warriors(name="2 Necron Warriors 4")
c.eq("buyable in the Fight phase", hv.can_use(plain), True)
c.eq("...and used", hv.use(plain), True)
c.eq("...but not twice on the same unit", hv.can_use(plain), False)

scythe = w.WarscytheProfile()
boosted = protocol_hungry_void.adjusted_weapon(scythe, plain)
c.eq("melee Strength goes up by 1", boosted.strength, scythe.strength + 1)
c.eq("AP is UNTOUCHED without a leader - that clause is conditional",
     boosted.ap, scythe.ap)
c.eq("the shared instance is never mutated", scythe.strength, w.WarscytheProfile().strength)

led2 = led_warriors(name="2 Necron Warriors 5")
hv2 = protocol_hungry_void.HungryVoidController(strat_controller(turn=turn), turn_tracker=turn)
hv2.use(led2)
led_boost = protocol_hungry_void.adjusted_weapon(scythe, led2)
c.eq("with a CHARACTER leading, AP improves by 1 as well",
     (led_boost.strength, led_boost.ap), (scythe.strength + 1, scythe.ap - 1))

hv.reset_phase([plain])
c.eq("the grant expires at the end of the phase",
     protocol_hungry_void.adjusted_weapon(scythe, plain).strength, scythe.strength)

wrong_phase = turn_at(PHASE_SHOOTING)
hv3 = protocol_hungry_void.HungryVoidController(strat_controller(turn=wrong_phase),
                                                turn_tracker=wrong_phase)
c.eq("not buyable outside the Fight phase",
     hv3.can_use(warriors(name="2 Necron Warriors 6")), False)


# --- 4. Protocol of the Sudden Storm ----------------------------------------
print("--- 4. Sudden Storm ---")

mturn = turn_at(PHASE_MOVEMENT)
ss = protocol_sudden_storm.SuddenStormController(strat_controller(turn=mturn), turn_tracker=mturn)
storm_unit = warriors(name="2 Necron Warriors 7")
c.eq("buyable in your Movement phase", ss.can_use(storm_unit), True)
ss.use(storm_unit)
flayer = w.GaussFlayerProfile()
c.eq("ranged weapons gain [ASSAULT]",
     protocol_sudden_storm.adjusted_weapon(flayer, storm_unit).assault, True)
c.eq("...and MELEE weapons do not - the text says ranged",
     protocol_sudden_storm.adjusted_weapon(w.WarscytheProfile(), storm_unit).assault, False)
c.eq("the Advance re-roll is NOT available without a leader",
     protocol_sudden_storm.advance_reroll_available(storm_unit), False)

led3 = led_warriors(name="2 Necron Warriors 8")
ss2 = protocol_sudden_storm.SuddenStormController(strat_controller(turn=mturn), turn_tracker=mturn)
ss2.use(led3)
c.eq("...and IS with one", protocol_sudden_storm.advance_reroll_available(led3), True)

# the two clocks are genuinely different - this is the whole point of the two flags
ss2.reset_phase([led3])
c.eq("end of PHASE kills the Advance re-roll",
     protocol_sudden_storm.advance_reroll_available(led3), False)
c.eq("...but the [ASSAULT] grant SURVIVES it - 'until the end of the turn'",
     protocol_sudden_storm.adjusted_weapon(flayer, led3).assault, True)
ss2.expire_for_turn([led3])
c.eq("...and only the end of the turn removes it",
     protocol_sudden_storm.adjusted_weapon(flayer, led3).assault, False)

# the AI's deterministic re-roll rule
dice = DiceManager()
ss3 = protocol_sudden_storm.SuddenStormController(
    strat_controller(turn=mturn), turn_tracker=mturn, dice_manager=dice,
    auto_players=(AI,))
led4 = led_warriors(name="2 Necron Warriors 9")
ss3.use(led4)
script(2, 6, default=6)
dice.roll(1, 6, label="Advance")
c.eq("the AI re-rolls a low Advance", ss3.maybe_offer_advance_reroll(led4), True)
c.eq("...and the die really changed", dice.pending_values[0], 6)
c.eq("...and cannot be thrown a second time",
     ss3.maybe_offer_advance_reroll(led4), False)

dice2 = DiceManager()
ss4 = protocol_sudden_storm.SuddenStormController(
    strat_controller(turn=mturn), turn_tracker=mturn, dice_manager=dice2, auto_players=(AI,))
led5 = led_warriors(name="2 Necron Warriors 10")
ss4.use(led5)
script(5, default=5)
dice2.roll(1, 6, label="Advance")
c.eq("a 5 is kept - a D6 averages 3.5, so re-rolling it loses on average",
     ss4.maybe_offer_advance_reroll(led5), False)


# --- 4b. the REPORTED bug: Advance, then shoot -------------------------------
# User: "Stratagem 'Protocoll of the sudden storm' scheint nicht funktioniert
# zu haben. ich konnte nach dem vorruecken nicht mehr schiessen mit den necron
# kriegern." Reproduced from logs/game_20260903_212846.log line 652: the AI
# bought it, Advanced 6", and then its Warriors never fired.
#
# Section 4 above measured adjusted_weapon() - the DAMAGE-maths half - and was
# green throughout, which is exactly why this survived. Rule 10.05's gate is a
# DIFFERENT reader: shooting.available_shooting_types() asks
# coldstar.weapon_has_assault(), and that function knew three grants and not
# this one. So the one thing 1 CP buys - "I closed the distance and shot
# anyway" - was the one thing it did not do.
print("--- 4b. Sudden Storm: the Advance-then-shoot gate ---")

from game import coldstar, shooting


class _Advanced:
    """The one thing available_shooting_types() reads off a MovementController."""

    def __init__(self, squads):
        self.advanced_squad_ids = set(squads)


_gate_turn = turn_at(PHASE_MOVEMENT)
_gate_unit = led_warriors(name="2 Necron Warriors 11")
_gate_state = GameState()
tk.line_up(_gate_unit, y=20.0)
for _m in _gate_unit.models:
    _gate_state.add_token(_m)
_gate_gun = next(x for x in _gate_unit.models[0].weapons if x.weapon_type == "ranged")

c.eq("BEFORE the Stratagem: an Advanced unit cannot shoot at all",
     shooting.available_shooting_types(_gate_unit, _gate_state.tokens,
                                       _Advanced([_gate_unit])), [])

protocol_sudden_storm.SuddenStormController(
    strat_controller(turn=_gate_turn), turn_tracker=_gate_turn).use(_gate_unit)

# Both readers, separately - the bug was that they DISAGREED.
c.eq("the adjuster chain grants [ASSAULT]",
     protocol_sudden_storm.adjusted_weapon(_gate_gun, _gate_unit).assault, True)
c.eq("...and so does weapon_has_assault(), the rule-10.05 gate",
     coldstar.weapon_has_assault(_gate_gun, _gate_unit), True)

c.eq("AFTER it: the Advanced unit gets Assault shooting - the reported case",
     shooting.available_shooting_types(_gate_unit, _gate_state.tokens,
                                       _Advanced([_gate_unit])),
     [shooting.ASSAULT_SHOOTING])
c.eq("...and a unit that did NOT Advance still shoots normally",
     shooting.available_shooting_types(_gate_unit, _gate_state.tokens, _Advanced([])),
     [shooting.NORMAL_SHOOTING])

# The counter-check, without which the section would pass on an engine that
# handed [ASSAULT] to everything: MELEE weapons are untouched, and the grant
# dies with the turn.
c.eq("melee weapons never reach the gate",
     coldstar.weapon_has_assault(
         next(x for x in _gate_unit.models[0].weapons if x.weapon_type == "melee"),
         _gate_unit), False)
protocol_sudden_storm.SuddenStormController(
    strat_controller(turn=_gate_turn), turn_tracker=_gate_turn).expire_for_turn([_gate_unit])
c.eq("...and the gate closes again at the end of the turn",
     coldstar.weapon_has_assault(_gate_gun, _gate_unit), False)


# --- 5. Protocol of the Conquering Tyrant -----------------------------------
print("--- 5. Conquering Tyrant ---")

sturn = turn_at(PHASE_SHOOTING)
ct = protocol_conquering_tyrant.ConqueringTyrantController(
    strat_controller(turn=sturn), turn_tracker=sturn)
shooters = warriors(name="2 Necron Warriors 11")
target = build(nec.LYCHGUARD, owner="Player 1", name="1 Lychguard 1")
tk.line_up(shooters, x=20.0, y=20.0)
tk.line_up(target, x=20.0, y=26.0)     # 6in apart, inside a 24in flayer's half range
c.eq("buyable in your Shooting phase", ct.can_use(shooters), True)
ct.use(shooters)

pairs = [(shooters.models[0], w.GaussFlayerProfile())]
c.eq("the base clause fires inside half range",
     protocol_conquering_tyrant.applies(shooters, w.GaussFlayerProfile(), pairs, target), True)
c.eq("...but not the whole-roll upgrade without a leader",
     protocol_conquering_tyrant.offers_full_reroll(shooters, w.GaussFlayerProfile(), pairs, target), False)

tk.line_up(target, x=20.0, y=60.0)     # now 40in away, well outside half range
c.eq("outside half range it does nothing at all",
     protocol_conquering_tyrant.applies(shooters, w.GaussFlayerProfile(), pairs, target), False)

# Its base clause is a MANDATORY re-roll of the 1s, so the offer ends in "the
# 1s only" rather than "Keep result". It does NOT suppress the failures-only
# option: "you can re-roll the Hit roll FOR THAT ATTACK instead" is a permission
# per die, and this datasheet is the one that spells that scope out.
c.true("it registers as a mandatory-1s source",
       reroll_scope.is_ones_or_whole(protocol_conquering_tyrant.CONQUERING_TYRANT_LABEL))
ct.reset_phase([shooters])
c.eq("the grant expires at the end of the phase",
     protocol_conquering_tyrant.is_active(shooters), False)


# The Advance re-roll, and the loop it used to be. Same seam as the Autarch's
# Superlative Strategist, so the check is deliberately the same shape: main.py
# keeps the roll un-acknowledged while the prompt is open, so declining left
# the board unchanged and the next click asked again (user: "es war eine
# schleife bis ich ihn gererollt habe").
from game.decision import DecisionManager as _DM  # noqa: E402
from game.dice import ADVANCE_ROLL  # noqa: E402

state_sr = GameState()
storm_unit = led_warriors(name="2 Necron Warriors 14")
tk.line_up(storm_unit, x=20.0, y=20.0)
state_sr.tokens = list(storm_unit.models)
storm_unit.sudden_storm_advance_reroll = True
c.true("the grant is up and a CHARACTER is leading",
       protocol_sudden_storm.advance_reroll_available(storm_unit))

dice_sr, dec_sr = DiceManager(), _DM()
ss_ctrl = protocol_sudden_storm.SuddenStormController(
    strat_controller(), dice_manager=dice_sr, decision_manager=dec_sr,
    game_log=tk.Log(), auto_players=("Player 1",))   # this unit's owner is P2
script(2, 2, 2, 2, default=2)
dice_sr.roll(1, 6, label="Advance", roll_kind=ADVANCE_ROLL, target_squad=storm_unit)
c.true("the re-roll is offered once", ss_ctrl.maybe_offer_advance_reroll(storm_unit))
c.true("...and the prompt is open", dec_sr.is_pending)
dec_sr.choose(1)                                    # "Keep it"
c.true("...declining does NOT bring it back for the same roll",
       not ss_ctrl.maybe_offer_advance_reroll(storm_unit))
c.eq("...and the die is still there to acknowledge", dice_sr.pending_values, [2])
dice_sr.roll(1, 6, label="Advance", roll_kind=ADVANCE_ROLL, target_squad=storm_unit)
c.true("the NEXT Advance is offered again",
       ss_ctrl.maybe_offer_advance_reroll(storm_unit))
dec_sr.choose(1)

# --- 6. Protocol of the Undying Legions --------------------------------------
print("--- 6. Undying Legions ---")

state = GameState()
hurt = warriors(name="2 Necron Warriors 12")
tk.line_up(hurt, x=20.0, y=20.0)
state.tokens = list(hurt.models)
dice3 = DiceManager()
ul = protocol_undying_legions.UndyingLegionsController(
    strat_controller(), dice_manager=dice3, game_log=tk.Log(), game_state=state,
    auto_players=(AI,))
c.eq("a unit that lost nothing cannot use it", ul.can_use(hurt), False)

for m in hurt.models[:3]:
    m.current_wounds = 0
state.remove_dead_models()
c.eq("a unit that lost models can", ul.can_use(hurt), True)
c.eq("...and the AI thinks it worth a CP", ul.is_worth_using(hurt), True)

before = len(hurt.models)
script(3, default=3)
c.eq("it fires", ul.maybe_offer(hurt), True)
dice3.acknowledge()
ul.on_dice_acknowledged()
c.true("...and models come back", len(hurt.models) > before)

# the leader bonus is +1 on the RESULT, not a different die
state2 = GameState()
led6 = led_warriors(name="2 Necron Warriors 13")
tk.line_up(led6, x=20.0, y=20.0)
state2.tokens = list(led6.models)
for m in led6.models[:4]:
    m.current_wounds = 0
state2.remove_dead_models()
dice4 = DiceManager()
ul2 = protocol_undying_legions.UndyingLegionsController(
    strat_controller(), dice_manager=dice4, game_log=tk.Log(), game_state=state2,
    auto_players=(AI,))
count_before = len(led6.models)
script(1, default=1)
ul2.maybe_offer(led6)
dice4.acknowledge()
ul2.on_dice_acknowledged()
c.eq("a rolled 1 reanimates TWO wounds when a CHARACTER is leading (D3+1)",
     len(led6.models) - count_before, 2)


# --- 7. Protocol of the Eternal Revenant -------------------------------------
print("--- 7. Eternal Revenant ---")

state3 = GameState()
lord = build(nec.OVERLORD, name="2 Overlord 5")
tk.line_up(lord, x=20.0, y=20.0)
state3.tokens = list(lord.models)
er = protocol_eternal_revenant.EternalRevenantController(
    strat_controller(), game_log=tk.Log(), game_state=state3, auto_players=(AI,))

model = lord.models[0]
c.eq("an Overlord is an eligible NECRONS INFANTRY CHARACTER",
     protocol_eternal_revenant.is_eligible_model(model), True)
c.eq("a Necron Warrior is NOT - it is no CHARACTER",
     protocol_eternal_revenant.is_eligible_model(warriors(name="2 Necron Warriors 14").models[0]), False)

model.current_wounds = 0
dead = state3.remove_dead_models()
er.notify_destroyed(dead)
c.eq("the death is noted", er.is_pending(), True)
returned = er.resolve_end_of_phase()
c.eq("he comes back", len(returned), 1)
c.eq("...on HALF his starting wounds, not full",
     model.current_wounds, lord.models[0].profile.wounds // 2)
c.true("...back in the token list", model in state3.tokens)
c.eq("...as a unit with a starting strength of 1", lord.starting_model_count, 1)

model.current_wounds = 0
state3.remove_dead_models()
er.notify_destroyed([model])
c.eq("once per battle, per model - a second death is not offered",
     er.is_pending(), False)

# ...and the army rule still refuses to bring a CHARACTER back, which is the
# whole reason this Stratagem exists.
state4 = GameState()
led7 = led_warriors(name="2 Necron Warriors 15")
tk.line_up(led7, x=20.0, y=20.0)
state4.tokens = list(led7.models)
for m in led7.models:
    if m.profile.character:
        m.current_wounds = 0
state4.remove_dead_models()
c.eq("Reanimation Protocols cannot revive the Overlord (02.02.04)",
     [m.profile.name for m in rp.revivable_models(led7) if m.profile.character], [])


# --- 8. Protocol of the Vengeful Stars ---------------------------------------
print("--- 8. Vengeful Stars ---")

state5 = GameState()
avenger = build(nec.OVERLORD, name="2 Overlord 6")
victim = warriors(name="2 Necron Warriors 16")
killer = build(nec.LYCHGUARD, owner="Player 1", name="1 Lychguard 2")
tk.line_up(avenger, x=20.0, y=20.0)
tk.line_up(victim, x=22.0, y=20.0)     # within 6in of the avenger
tk.line_up(killer, x=60.0, y=60.0)
state5.tokens = list(avenger.models) + list(victim.models) + list(killer.models)

vs = protocol_vengeful_stars.VengefulStarsController(
    strat_controller(), game_log=tk.Log(), game_state=state5, auto_players=(AI,))
c.eq("an Overlord unit is a NECRONS CHARACTER unit",
     protocol_vengeful_stars.is_character_unit(avenger), True)
c.eq("a Warriors unit is not",
     protocol_vengeful_stars.is_character_unit(victim), False)

vs.notify_unit_destroyed(victim, killer)
c.eq("a character within 6in of the dead unit is captured as a candidate",
     vs.has_candidates(), True)

state6 = GameState()
far_avenger = build(nec.OVERLORD, name="2 Overlord 7")
far_victim = warriors(name="2 Necron Warriors 17")
tk.line_up(far_avenger, x=20.0, y=20.0)
tk.line_up(far_victim, x=50.0, y=20.0)   # 30in away
state6.tokens = list(far_avenger.models) + list(far_victim.models)
vs2 = protocol_vengeful_stars.VengefulStarsController(
    strat_controller(), game_log=tk.Log(), game_state=state6, auto_players=(AI,))
vs2.notify_unit_destroyed(far_victim, killer)
c.eq("...and one further than 6in away is NOT", vs2.has_candidates(), False)

c.eq("a killer that is itself wiped out is not an eligible target",
     vs.can_use(avenger, build(nec.LYCHGUARD, owner="Player 1", name="1 Lychguard 3")), True)
for m in killer.models:
    m.current_wounds = 0
c.eq("...so the Stratagem simply does not fire", vs.can_use(avenger, killer), False)


# --- 9. 15.01 bookkeeping ----------------------------------------------------
print("--- 9. rule 15.01 ---")

turn2 = turn_at(PHASE_FIGHT)
shared = strat_controller(cp=1, turn=turn2)
hv4 = protocol_hungry_void.HungryVoidController(shared, turn_tracker=turn2)
a = warriors(name="2 Necron Warriors 18")
b = warriors(name="2 Necron Warriors 19")
c.eq("the first use is affordable", hv4.use(a), True)
c.eq("...and with 0 CP left the second is refused", hv4.can_use(b), False)

poor = strat_controller(cp=0, turn=turn2)
hv5 = protocol_hungry_void.HungryVoidController(poor, turn_tracker=turn2)
c.eq("no CP, no Stratagem", hv5.can_use(warriors(name="2 Necron Warriors 20")), False)

# Undying Legions opts OUT of once-per-target-per-phase, because each enemy
# unit's attacks are their own window
c.eq("Undying Legions allows a repeat target on purpose",
     protocol_undying_legions.UndyingLegionsController(
         strat_controller())._stratagem.allow_repeat_target, True)
c.eq("...and Hungry Void does not",
     protocol_hungry_void.HungryVoidController(strat_controller())._stratagem.allow_repeat_target,
     False)

# --- 10. the wiring is REAL, not just present -------------------------------
print("--- 10. wiring ---")

# Found the hard way: notify_unit_destroyed() existed, was unit-tested, and was
# called from nowhere in main.py - so Vengeful Stars could never have fired in
# a real game. A controller that is constructed but never FED is invisible to
# every test that drives it directly, which is what verify_mark_wiring.py
# exists for. This is the cheap standing version of that check.
_main = pathlib.Path("main.py").read_text(encoding="utf-8")
FEEDS = [
    ("vengeful_stars_controller.notify_unit_destroyed", "Vengeful Stars is fed a destroyed unit"),
    ("vengeful_stars_controller.maybe_offer", "...and offered after the attacks resolve"),
    ("eternal_revenant_controller.notify_destroyed", "Eternal Revenant is fed destroyed models"),
    ("eternal_revenant_controller.resolve_end_of_phase", "...and resolved at the phase boundary"),
    ("undying_legions_controller.maybe_offer", "Undying Legions is offered after enemy attacks"),
    ("undying_legions_controller.on_dice_acknowledged", "...and its roll reaches the dispatch"),
    ("hungry_void_controller.reset_phase", "Hungry Void expires at the end of the phase"),
    ("conquering_tyrant_controller.reset_phase", "Conquering Tyrant expires too"),
    ("sudden_storm_controller.reset_phase", "Sudden Storm's Advance re-roll expires per PHASE"),
    ("sudden_storm_controller.expire_for_turn", "...and its [ASSAULT] grant per TURN"),
    ("hungry_void_controller=hungry_void_controller", "Hungry Void reaches the ActionPanel"),
    ("sudden_storm_controller=sudden_storm_controller", "...and Sudden Storm"),
    ("conquering_tyrant_controller=conquering_tyrant_controller", "...and Conquering Tyrant"),
]
for needle, label in FEEDS:
    c.true(label, needle in _main)

# --- 11. Vengeful Stars: the AI and the human see the SAME candidates --------
print("--- 11. Vengeful Stars offers every avenger ---")

# maybe_offer() drained self._candidates into a local, then the AI branch
# walked EVERY (avenger, killer) pair while the human branch request()ed a bare
# yes/no on the FIRST valid one and returned. The rest were already popped and
# were silently discarded, and the options carried no squad tag either.
#
# Measured before the fix, with two eligible avengers:
#     HUMAN prompt options: ['Use Protocol of the Vengeful Stars', 'Decline']
#     candidates left in queue: []
#     option carries a squad tag: [False, False]
#
# game/resurrection_orb.py had already been fixed for exactly this, and its
# comment quotes the user report the class came from.

from game import config as _vs_config                                # noqa: E402
from game import unit_pick as _vs_pick                               # noqa: E402

_vs_prev = _vs_config.AWAKENED_DYNASTY_PLAYERS
_vs_config.AWAKENED_DYNASTY_PLAYERS = (AI,)
try:
    _a1 = warriors(name="2 Necron Warriors A")
    _a2 = build(nec.IMMORTALS, AI, name="2 Immortals A", composition_index=0)
    _killer = build(orks.BOYZ, "Player 1", name="1 Boyz A")
    for _i, _m in enumerate(_a1.models):
        _m.x_in, _m.y_in = 10.0 + _i * 1.2, 20.0
    for _i, _m in enumerate(_a2.models):
        _m.x_in, _m.y_in = 14.0 + _i * 1.2, 22.0
    for _i, _m in enumerate(_killer.models):
        _m.x_in, _m.y_in = 20.0 + _i * 1.2, 20.0

    _dec = DecisionManager()
    _vs = protocol_vengeful_stars.VengefulStarsController(
        strat_controller(), decision_manager=_dec, game_log=tk.Log(), auto_players=())
    _vs._candidates = [(_a1, _killer), (_a2, _killer)]
    c.true("the offer is made", _vs.maybe_offer())

    _labels = [o["label"] for o in _dec.options]
    c.eq("BOTH avengers are offered, not just the first", len(_labels), 3)
    c.true("...the first names its own unit", _a1.name in _labels[0])
    c.true("...the second names the other", _a2.name in _labels[1])
    c.true("...and each names the unit it would shoot back at",
           all(_killer.name in lab for lab in _labels[:2]))
    c.eq("...with a Decline last", _labels[-1], "Decline")

    # A LABEL THAT NAMES ONLY THE STRATAGEM is indistinguishable when there are
    # two of them - which a single-pair prompt never had to solve.
    c.eq("no two options read the same", len(set(_labels)), len(_labels))

    # TAGGED, so the choice is made by clicking the unit on the board.
    _tokens = [m for s in (_a1, _a2, _killer) for m in s.models]
    _pick = _vs_pick.pending(_dec, _tokens)
    c.true("it is a BOARD pick, not a list", _pick is not None)
    c.eq("...over both avengers",
         sorted(s.name for s in (_pick.squads if _pick else ())),
         sorted([_a1.name, _a2.name]))

    # The printed NAME stays in the prompt: game/prompt_rule.py reads it back
    # out of the prompt text to fill the left column while the pick is open.
    c.true("the prompt still names the Stratagem",
           protocol_vengeful_stars.VENGEFUL_STARS_NAME in _dec.prompt)

    # And the second option really fires the SECOND avenger. Measured through
    # the LOG line _grant() writes, because that is where both units are named
    # together - the controller keeps only the killer as state, so an attribute
    # check would be a tautology (the first version of this check was one).
    _vs_log = tk.Log()
    _vs.game_log = _vs_log
    _vs.shooting_controller = None          # the grant's effect is not the point here
    _dec.choose(1)
    c.true("choosing the second option fires the SECOND avenger",
           _vs_log.has("%s shoots back at %s" % (_a2.name, _killer.name)))
    c.eq("...and not the first", _vs_log.has(_a1.name), False)

    # THE AI IS UNCHANGED: it still walks past a pair its own measure rejects.
    _b1 = warriors(name="2 Necron Warriors B")
    _b2 = build(nec.IMMORTALS, AI, name="2 Immortals B", composition_index=0)
    for _i, _m in enumerate(_b1.models):
        _m.x_in, _m.y_in = 10.0 + _i * 1.2, 30.0
    for _i, _m in enumerate(_b2.models):
        _m.x_in, _m.y_in = 14.0 + _i * 1.2, 32.0
    _dec2 = DecisionManager()
    _vs2 = protocol_vengeful_stars.VengefulStarsController(
        strat_controller(), decision_manager=_dec2, game_log=tk.Log(),
        auto_players=(AI,),
        worth_using=lambda a, k: a.name.startswith("2 Immortals"))
    _vs2._candidates = [(_b1, _killer), (_b2, _killer)]
    c.true("the AI still skips a pair its measure rejects and fires the next",
           _vs2.maybe_offer())
    c.eq("...and asks nobody", _dec2.is_pending, False)

    # Nothing valid: no prompt, and the queue is not left holding anything.
    _dec3 = DecisionManager()
    _vs3 = protocol_vengeful_stars.VengefulStarsController(
        strat_controller(cp=0), decision_manager=_dec3, game_log=tk.Log(), auto_players=())
    _vs3._candidates = [(warriors(name="2 Necron Warriors C"), _killer)]
    c.eq("no CP, no offer", _vs3.maybe_offer(), False)
    c.eq("...and no prompt", _dec3.is_pending, False)
finally:
    _vs_config.AWAKENED_DYNASTY_PLAYERS = _vs_prev

c.finish()
