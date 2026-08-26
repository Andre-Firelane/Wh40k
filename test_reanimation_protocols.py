"""The NECRONS army rule, Reanimation Protocols - and the shared model-return
extraction underneath it.

WHAT THIS SUITE IS ACTUALLY GUARDING. The rule is easy to state and easy to get
subtly wrong, because the interesting half is in the CORE rules rather than on
the datasheet: heal before revive, one wound at a time, CHARACTER models
excluded from revival, never past starting strength, and a returned model must
be placed in coherency and clear of enemies it was not already fighting. Each
of those is a separate way to be wrong, so each gets its own check rather than
one end-to-end "it healed something".

The placement half is checked by MEASURING the result (is the returned model
inside coherency? is it clear of the enemy it was not engaged with?) rather
than by asserting that returning_positions() was called - a mark that is set
and never read is exactly the failure a "did we call it" test cannot see.
"""

import testkit as tk
from testkit import Checks, GameState, script
from game import model_return, reanimation_protocols as rp
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import necrons as nec
from game.squad import ENGAGEMENT_RANGE_IN, Squad
from game.token import Token
from game.units import LychguardProfile, OverlordProfile

c = Checks("Reanimation Protocols")


def necron_squad(sheet=nec.LYCHGUARD, name="2 Lychguard 1", owner="Player 2", **kw):
    return tk.build(sheet, owner, name=name, **kw)


def scene(sheet=nec.LYCHGUARD, name="2 Lychguard 1"):
    state = GameState()
    squad = necron_squad(sheet, name)
    tk.line_up(squad, x=20.0, y=20.0)
    state.tokens = list(squad.models)
    return state, squad


def kill(state, squad, count):
    for model in squad.models[:count]:
        model.current_wounds = 0
    return state.remove_dead_models()


# --- 1. the healing half (core rule 02.02.04, first clause) ------------------
print("--- 1. healing comes first ---")

state, squad = scene()
squad.models[0].current_wounds = 1          # Lychguard are W2
squad.models[1].current_wounds = 1
c.eq("recoverable_wounds counts missing wounds", rp.recoverable_wounds(squad), 2)

spent, revived = rp.reanimate(squad, 1, all_tokens=list(state.tokens), game_state=state)
c.eq("one wound heals one model", spent, 1)
c.eq("...and revives nobody", len(revived), 0)
c.eq("the MOST damaged model is topped up first",
     sorted(m.current_wounds for m in squad.models), [1, 2, 2, 2, 2])

spent, _ = rp.reanimate(squad, 5, all_tokens=list(state.tokens), game_state=state)
c.eq("surplus beyond what the unit can use is LOST, not banked", spent, 1)
c.true("every model is at full wounds afterwards",
       all(m.current_wounds == m.profile.wounds for m in squad.models))
c.eq("a whole unit at full health can recover nothing", rp.recoverable_wounds(squad), 0)


# --- 2. the revival half (02.02.04 second clause + 01.02.03) -----------------
print("--- 2. revival ---")

state, squad = scene()
kill(state, squad, 2)
c.eq("two models are destroyed", len(squad.destroyed_models), 2)
c.eq("recoverable = 2 destroyed x W2", rp.recoverable_wounds(squad), 4)

spent, revived = rp.reanimate(squad, 1, all_tokens=list(state.tokens), game_state=state)
c.eq("one wound revives exactly one model", len(revived), 1)
c.eq("...with ONE wound remaining, not full", revived[0].current_wounds, 1)

returned = revived[0]
c.true("back in the token list", returned in state.tokens)
c.true("back in its squad", returned in squad.models)
c.true("off the destroyed list", returned not in squad.destroyed_models)

spent, revived2 = rp.reanimate(squad, 3, all_tokens=list(state.tokens), game_state=state)
c.eq("the next wound finishes healing the model already raised",
     returned.current_wounds, 2)
c.eq("...and the rest raise the second one", len(revived2), 1)
c.eq("the unit is back to full strength", len(squad.models), 5)

# oldest destruction first, which is the documented ordering
state, squad = scene()
first_dead = squad.models[0]
kill(state, squad, 1)
squad.models[0].current_wounds = 0
state.remove_dead_models()
c.eq("revivable_models is oldest-destruction-first",
     rp.revivable_models(squad)[0] is first_dead, True)


# --- 3. the two hard caps ---------------------------------------------------
print("--- 3. starting strength and the CHARACTER exclusion ---")

state, squad = scene()
kill(state, squad, 5)
c.eq("a WIPED unit has no survivors to reanimate around",
     rp.reanimate(squad, 6, all_tokens=list(state.tokens), game_state=state)[0], 0)

# starting strength: kill two, revive with a huge roll, expect no more than two
state, squad = scene()
kill(state, squad, 2)
spent, revived = rp.reanimate(squad, 99, all_tokens=list(state.tokens), game_state=state)
c.eq("cannot expand a unit beyond its starting strength (01.02.03)",
     len(squad.models), squad.starting_model_count)
c.eq("...so only the two that died come back", len(revived), 2)

# the CHARACTER exclusion, through a real attached-shaped unit
state = GameState()
squad = necron_squad(name="2 Lychguard 2")
tk.line_up(squad, x=20.0, y=20.0)
lead_profile = OverlordProfile()
lead = Token(18.0, 20.0, lead_profile.base_radius_in, (200, 200, 200),
             profile=lead_profile, current_wounds=lead_profile.wounds)
squad.models.append(lead)
lead.squad = squad
squad.starting_model_count = len(squad.models)
state.tokens = list(squad.models)
lead.current_wounds = 0
squad.models[0].current_wounds = 0
state.remove_dead_models()
names = [m.profile.name for m in squad.destroyed_models]
c.true("both a Lychguard and the Overlord are destroyed",
       "Overlord" in names and "Lychguard" in names)
c.eq("02.02.04 refuses to revive a CHARACTER model",
     [m.profile.name for m in rp.revivable_models(squad)], ["Lychguard"])


# --- 4. placement: coherency, and 01.02.03's engagement clause ---------------
print("--- 4. placement ---")

state, squad = scene()
kill(state, squad, 1)
spent, revived = rp.reanimate(squad, 2, all_tokens=list(state.tokens), game_state=state)
back = revived[0]
gaps = [((back.x_in - m.x_in) ** 2 + (back.y_in - m.y_in) ** 2) ** 0.5
        - back.radius_in - m.radius_in
        for m in squad.models if m is not back]
c.true("the returned model lands in coherency with a survivor (09.02)",
       min(gaps) <= 2.0)

# ...and clear of an enemy the unit was NOT already engaged with
state, squad = scene()
enemy = tk.build(nec.IMMORTALS, "Player 1", name="1 Immortals 1")
tk.line_up(enemy, x=20.0, y=26.0)
state.tokens = list(squad.models) + list(enemy.models)
kill(state, squad, 1)
spent, revived = rp.reanimate(squad, 2, all_tokens=list(state.tokens), game_state=state)
c.eq("a model still comes back with an enemy unit nearby", len(revived), 1)
if revived:
    back = revived[0]
    enemy_gaps = [((back.x_in - t.x_in) ** 2 + (back.y_in - t.y_in) ** 2) ** 0.5
                  - back.radius_in - t.radius_in for t in enemy.models]
    c.true("...and NOT within Engagement Range of a unit it was not fighting",
           min(enemy_gaps) > ENGAGEMENT_RANGE_IN)


# --- 5. the Necron Warriors re-roll ------------------------------------------
print("--- 5. Their Number Is Legion (the re-roll) ---")

state, warriors = scene(nec.NECRON_WARRIORS, "2 Necron Warriors 1")
kill(state, warriors, 3)
c.true("Warriors print the re-roll flag",
       any(m.profile.reanimation_reroll for m in warriors.models))
c.eq("a 1 is re-rolled", rp.should_reroll(warriors, 1), True)
c.eq("a 2 is NOT - a D3 averages 2, so re-rolling it wins nothing",
     rp.should_reroll(warriors, 2), False)
c.eq("a 3 is not either", rp.should_reroll(warriors, 3), False)

state, healthy = scene(nec.NECRON_WARRIORS, "2 Necron Warriors 2")
c.eq("a unit with nothing to recover does not re-roll even a 1",
     rp.should_reroll(healthy, 1), False)

state, lych = scene()
kill(state, lych, 2)
c.eq("a datasheet WITHOUT the ability never re-rolls", rp.should_reroll(lych, 1), False)


# --- 6. the controller, through real dice ------------------------------------
print("--- 6. the queue, through the real controller ---")

state = GameState()
a = necron_squad(name="2 Lychguard 1")
b = necron_squad(nec.IMMORTALS, name="2 Immortals 1")
tk.line_up(a, x=20.0, y=20.0)
tk.line_up(b, x=40.0, y=20.0)
state.tokens = list(a.models) + list(b.models)
kill(state, a, 1)
b.models[0].current_wounds = 0
state.remove_dead_models()

dice = DiceManager()
ctrl = rp.ReanimationProtocolsController(
    dice_manager=dice, decision_manager=DecisionManager(), game_log=tk.Log(),
    game_state=state, auto_players=("Player 2",))

script(2, 2, default=2)
started = ctrl.begin_command_phase({a, b}, "Player 2")
c.eq("the queue starts with a roll on the table", started, True)
c.eq("...and the dice manager really is pending", dice.is_pending, True)
c.eq("the roll is labelled", dice.label.startswith("Reanimation Protocols"), True)
c.eq("it names the unit reanimating, not a 'Target'", dice.subject_label, "Reanimating")

seen = 0
while ctrl.is_busy and seen < 12:
    dice.acknowledge()
    ctrl.on_dice_acknowledged()
    seen += 1
c.true("the queue drains over successive acknowledgements", seen >= 2)
c.eq("both units are back to full strength", (len(a.models), len(b.models)), (5, 5))

c.eq("a unit with no Necron models is never queued",
     ctrl.can_activate(tk.build(nec.LYCHGUARD, "Player 1", name="1 Lychguard 1"), "Player 2"),
     False)


# --- 6b. only DAMAGED units roll -------------------------------------------
print("--- 6b. undamaged units are skipped ---")

# User instruction: an undamaged unit must not stop the game for a die that
# cannot do anything. Checked as a QUEUE result, not as a flag - what matters
# is which units are asked to roll.
state6 = GameState()
fresh = necron_squad(name="2 Lychguard 5")
hurt6 = necron_squad(name="2 Lychguard 6")
tk.line_up(fresh, x=20.0, y=20.0)
tk.line_up(hurt6, x=40.0, y=20.0)
state6.tokens = list(fresh.models) + list(hurt6.models)
hurt6.models[0].current_wounds = 1

ctrl6 = rp.ReanimationProtocolsController(
    dice_manager=DiceManager(), game_log=tk.Log(), game_state=state6,
    auto_players=("Player 2",))
c.eq("an untouched, full-strength unit is NOT queued", ctrl6.can_activate(fresh, "Player 2"), False)
c.eq("...and a unit that lost even one wound IS", ctrl6.can_activate(hurt6, "Player 2"), True)
state7, wounded_unit = scene(name="2 Lychguard 7")
kill(state7, wounded_unit, 1)
ctrl7 = rp.ReanimationProtocolsController(
    dice_manager=DiceManager(), game_state=state7, auto_players=("Player 2",))
c.eq("...losing a model alone is enough, even at full wounds otherwise",
     ctrl7.can_activate(wounded_unit, "Player 2"), True)

script(2, default=2)
c.eq("only the damaged unit reaches the queue",
     [s.name for s in ctrl6.eligible_squads({fresh, hurt6}, "Player 2")], ["2 Lychguard 6"])

# THE OUTCOME IS UNCHANGED, which is the point: the skipped roll is exactly
# the roll that would have achieved nothing.
c.eq("reanimating an undamaged unit was always a no-op anyway",
     rp.reanimate(fresh, 3, all_tokens=list(state6.tokens), game_state=state6), (0, []))

# A/B: with the gate off, the untouched unit is queued again - so the check
# above is really measuring the gate and not something else.
_gate = rp.ReanimationProtocolsController.UNITS_MUST_HAVE_SOMETHING_TO_GAIN
try:
    rp.ReanimationProtocolsController.UNITS_MUST_HAVE_SOMETHING_TO_GAIN = False
    c.eq("A/B: with the gate off, the untouched unit rolls again",
         ctrl6.can_activate(fresh, "Player 2"), True)
finally:
    rp.ReanimationProtocolsController.UNITS_MUST_HAVE_SOMETHING_TO_GAIN = _gate
c.eq("...and restored, it is skipped once more", ctrl6.can_activate(fresh, "Player 2"), False)


# --- 7. A/B: unwire the ability and the rule stops --------------------------
print("--- 7. A/B probes ---")

state, squad = scene()
kill(state, squad, 1)
_real = rp.has_reanimation_protocols
try:
    rp.has_reanimation_protocols = lambda s: False
    ctrl2 = rp.ReanimationProtocolsController(
        dice_manager=DiceManager(), game_state=state, auto_players=("Player 2",))
    c.eq("A/B: with the army rule unwired, nothing is queued",
         ctrl2.begin_command_phase({squad}, "Player 2"), False)
finally:
    rp.has_reanimation_protocols = _real
ctrl3 = rp.ReanimationProtocolsController(
    dice_manager=DiceManager(), game_state=state, auto_players=("Player 2",))
c.eq("...and restored, it is queued again",
     ctrl3.begin_command_phase({squad}, "Player 2"), True)


# --- 8. the extraction is shared, not copied --------------------------------
print("--- 8. game/model_return.py ---")

state, squad = scene()
kill(state, squad, 1)
dead = squad.destroyed_models[0]
model_return.set_up_model(dead, (30.0, 30.0), wounds=1, game_state=state)
c.eq("set_up_model honours a partial wound count", dead.current_wounds, 1)
model_return.set_up_model(dead, (30.0, 30.0), wounds=99, game_state=state)
c.eq("...and clamps above the model's maximum", dead.current_wounds, dead.profile.wounds)
model_return.set_up_model(dead, (30.0, 30.0), game_state=state)
c.eq("wounds=None still means 'full wounds', the old callers' behaviour",
     dead.current_wounds, dead.profile.wounds)

enemy_profile = LychguardProfile()
foe = Token(30.0, 30.5, enemy_profile.base_radius_in, (1, 1, 1), profile=enemy_profile,
            current_wounds=enemy_profile.wounds)
c.eq("clear_of_engagement refuses a spot inside Engagement Range",
     model_return.clear_of_engagement(dead, 30.0, 30.0, [foe]), False)
c.eq("...and allows one well clear",
     model_return.clear_of_engagement(dead, 60.0, 60.0, [foe]), True)

c.finish()
