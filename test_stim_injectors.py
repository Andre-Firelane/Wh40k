"""Tests for Retaliation Cadre's Stim Injectors stratagem (game/stim_injectors.py).

RULE (user-supplied): 1CP. WHEN your opponent's Shooting phase or the Fight
phase, just after an enemy unit has selected its targets. TARGET one T'AU
EMPIRE BATTLESUIT unit from your army that was selected as the target of one
or more of the attacking unit's attacks. EFFECT until the end of the phase,
models in your unit have the Feel No Pain 6+ ability.

The interesting part is not the effect - it is the WHEN. This is the first
stratagem whose trigger fires on every enemy target selection, which is the
user's own design objection ("das würde sehr nerven"). The relevance gate is
the answer, so the tests that matter most are the ones that prove the gate
suppresses the pointless offers, keeps the real ones, and - critically, via an
A/B - that the suppression really comes from the GATE and not from some other
clause quietly rejecting the same case.

Uses real StratagemController/CommandPointManager/DecisionManager/TurnTracker/
ShootingController/FightController objects and real datasheets throughout.

Run: python test_stim_injectors.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import stim_injectors as si
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BOYZ, GRETCHIN, TANKBUSTAS
from game.factions.tau_empire import (COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_STARSCYTHE,
                                      GHOSTKEEL_BATTLESUIT, STEALTH_BATTLESUITS, STRIKE_TEAM)
from game.feel_no_pain import FeelNoPainRoll, current_feel_no_pain
from game.fight import FightController
from game.shooting import NORMAL_SHOOTING, ShootingController
from game.stim_injectors import StimInjectorsController
from game.stratagems import StratagemController
from game.turn import PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, PHASES, TurnTracker

# Retaliation Cadre must be DECLARED for this suite: its rule and all six of
# its Stratagems gate on config.RETALIATION_CADRE_PLAYERS, which is empty until
# an army list that fields the detachment is chosen. Set here so the subject of
# these checks actually applies - the same precondition
# test_death_guard_stratagems.py's `detachment_on` exists for.
from game import config as _config  # noqa: E402
_config.RETALIATION_CADRE_PLAYERS = ("Player 1", "Player 2")

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(f"  {'OK  ' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")


def place(squad, positions):
    for model, (x, y) in zip(squad.models, positions):
        model.x_in, model.y_in = x, y
    return squad


def row(x, y, n, dx=1.5):
    return [(x + i * dx, y) for i in range(n)]


def make_rig(cp=3, phase=PHASE_SHOOTING):
    """A real stratagem/decision/turn stack, plus the controller under test."""
    points = CommandPointManager()
    points.cp["Player 1"] = cp
    points.cp["Player 2"] = cp
    strat = StratagemController(command_points=points)
    decisions = DecisionManager()
    tracker = TurnTracker()
    tracker.started = True
    tracker.phase_index = PHASES.index(phase)  # `phase` is a read-only property over this
    controller = StimInjectorsController(strat, decision_manager=decisions, turn_tracker=tracker)
    return controller, strat, decisions, tracker, points


def set_phase(tracker, phase):
    tracker.phase_index = PHASES.index(phase)


# ---------------------------------------------------------------- the effect
print("\n-- the Feel No Pain 6+ grant --")

crisis = build_squad(CRISIS_STARSCYTHE, "Player 1", name="crisis")
check("no grant by default", si.stim_injectors_feel_no_pain(crisis.models[0]) == "-")
crisis.stim_injectors_active = True
check("granted while active", si.stim_injectors_feel_no_pain(crisis.models[0]) == "6+")
check("current_feel_no_pain folds it in", current_feel_no_pain(crisis.models[0]) == "6+")

# "Never worse than what is already printed" - the same principle Krumpin'
# Time follows. Faked onto a real model rather than hunting for a datasheet
# that prints one, since none of the Battlesuits do.
crisis.models[0].profile.feel_no_pain = "5+"
check("a better printed FNP is kept", current_feel_no_pain(crisis.models[0]) == "5+")
crisis.models[0].profile.feel_no_pain = "-"

dice = DiceManager()
roll = FeelNoPainRoll(crisis.models[0], 4, dice)
check("an active grant actually rolls dice", roll.is_pending and dice.is_pending,
      f"pending={roll.is_pending}")
dice.last_values = [6, 6, 1, 2]  # two 6s meet the 6+ threshold
roll.on_dice_acknowledged()
check("and reduces the damage", roll.reduced_amount == 2, f"4 -> {roll.reduced_amount}")

crisis.stim_injectors_active = False
quiet = FeelNoPainRoll(crisis.models[0], 4, DiceManager())
check("no roll without the grant", not quiet.is_pending and quiet.reduced_amount == 4)

# --------------------------------------------------------------- eligibility
print("\n-- WHEN / TARGET clauses --")

boyz = place(build_squad(BOYZ, "Player 2", name="boyz"), row(10, 10, 10))
stealth = place(build_squad(STEALTH_BATTLESUITS, "Player 1", name="stealth"), row(10, 20, 3))
strike = place(build_squad(STRIKE_TEAM, "Player 1", name="strike"), row(20, 14, 10))
gretchin = place(build_squad(GRETCHIN, "Player 2", name="gretchin"), row(30, 10, 11))
# Rokkit Launchas (S9 AP-2 D3): the ranged counterpart to the Boyz' melee
# threat. Boyz SHOOTING is Sluggas, which the gate suppresses on purpose.
tank = place(build_squad(TANKBUSTAS, "Player 2", name="tankbustas"), row(10, 11, 6))

c, strat, decisions, tracker, points = make_rig()
check("enemy attack on a BATTLESUIT unit qualifies", c.can_offer(boyz, stealth, melee=True))
check("a non-BATTLESUIT target does not", not c.can_offer(boyz, strike, melee=True))
check("a friendly 'attacker' does not", not c.can_offer(strike, stealth))

set_phase(tracker, PHASE_FIGHT)
check("the Fight phase qualifies (WHEN names it)", c.can_offer(boyz, stealth, melee=True))
set_phase(tracker, PHASE_MOVEMENT)
check("Fire Overwatch's phase does not (rule 15.08 is the Movement phase)",
      not c.can_offer(boyz, stealth, melee=True))
set_phase(tracker, PHASE_SHOOTING)

stealth.battle_shocked = True
check("a battle-shocked target is blocked (rule 01.07)", not c.can_offer(boyz, stealth, melee=True))
stealth.battle_shocked = False

points.cp["Player 1"] = 0
check("no CP, no offer", not c.can_offer(boyz, stealth, melee=True))
points.cp["Player 1"] = 3

stealth.stim_injectors_active = True
check("already active, nothing to gain", not c.can_offer(boyz, stealth, melee=True))
stealth.stim_injectors_active = False

# Rule 19.03: keywords pool across an attached unit, so a Commander joined to
# a Crisis team is a BATTLESUIT unit even though only some models print it.
from game.attached_units import attach

crisis2 = place(build_squad(CRISIS_STARSCYTHE, "Player 1", name="crisis2"), row(40, 14, 3))
coldstar = place(build_squad(COMMANDER_IN_COLDSTAR_BATTLESUIT, "Player 1", name="coldstar"), [(44, 14)])
attach(coldstar, crisis2)
check("an attached unit qualifies via rule 19.03", si.is_battlesuit_unit(crisis2),
      f"{len(crisis2.attached_components)} components")

# ------------------------------------------------------------ relevance gate
print("\n-- the relevance gate (and proof it is the gate) --")

ghostkeel = place(build_squad(GHOSTKEEL_BATTLESUIT, "Player 1", name="ghostkeel"), [(10, 20)])
c, strat, decisions, tracker, points = make_rig()

weak = si.expected_wounds_saved(gretchin, ghostkeel)
strong = si.expected_wounds_saved(boyz, stealth, melee=True)
check("chip damage falls under the floor", weak < si.MIN_EXPECTED_WOUNDS_SAVED, f"{weak:.3f}")
check("a real threat clears it", strong >= si.MIN_EXPECTED_WOUNDS_SAVED, f"{strong:.3f}")
check("chip damage is suppressed", not c.can_offer(gretchin, ghostkeel))
check("the real threat is offered", c.can_offer(boyz, stealth, melee=True))

# A/B: drop the floor to zero and the SAME pair must now be offered. Without
# this, "suppressed" could just as well have come from the TARGET clause or the
# CP check, and the test would prove nothing about the gate.
original_floor = si.MIN_EXPECTED_WOUNDS_SAVED
si.MIN_EXPECTED_WOUNDS_SAVED = 0.0
check("A/B: with the floor at 0 the same pair IS offered", c.can_offer(gretchin, ghostkeel),
      "so the suppression above came from the gate, not another clause")
si.MIN_EXPECTED_WOUNDS_SAVED = original_floor
check("floor restored", si.MIN_EXPECTED_WOUNDS_SAVED == original_floor)

# ------------------------------------------------------- through the engine
print("\n-- through the real ShootingController --")

tokens = (list(boyz.models) + list(stealth.models) + list(strike.models)
          + list(gretchin.models) + list(tank.models))
c, strat, decisions, tracker, points = make_rig()
tracker.turn_owner = tracker.active_player = "Player 2"
shooting = ShootingController(all_tokens=tokens, turn_tracker=tracker, dice_manager=DiceManager(),
                              decision_manager=decisions, target_reactions=(c,))
shooting.active_squad = tank
shooting.shooting_type = NORMAL_SHOOTING
shooting.state = "choosing_target"
shooting.choose_target_squad(stealth)
check("selecting a BATTLESUIT target opens the prompt", decisions.is_pending)
check("and it belongs to the DEFENDER", decisions.player == "Player 1", str(decisions.player))
check("the prompt quotes the expected saving", "wounds" in (decisions.prompt or "")
      and "1 CP" in (decisions.prompt or ""), (decisions.prompt or "")[:120])
check("it is flagged as a stratagem prompt", decisions.is_stratagem)

decisions.choose(0)  # "Use Stim Injectors"
check("accepting sets the grant", stealth.stim_injectors_active)
check("and spends exactly 1 CP", points.cp["Player 1"] == 2, str(points.cp["Player 1"]))
check("the queue is empty afterwards", not decisions.is_pending)

# Declining must cost nothing.
c2, strat2, decisions2, tracker2, points2 = make_rig()
tracker2.turn_owner = tracker2.active_player = "Player 2"
stealth.stim_injectors_active = False
shooting2 = ShootingController(all_tokens=tokens, turn_tracker=tracker2, dice_manager=DiceManager(),
                               decision_manager=decisions2, target_reactions=(c2,))
shooting2.active_squad = tank
shooting2.shooting_type = NORMAL_SHOOTING
shooting2.state = "choosing_target"
shooting2.choose_target_squad(stealth)
decisions2.choose(1)  # "Decline"
check("declining grants nothing", not stealth.stim_injectors_active)
check("and spends no CP", points2.cp["Player 1"] == 3, str(points2.cp["Player 1"]))

# Split Fire reaches the same hook once per assignment - it must not ask once
# per weapon.
c3, strat3, decisions3, tracker3, points3 = make_rig()
c3.maybe_offer(tank, stealth, melee=False)
first = len(decisions3._queue)
c3.maybe_offer(tank, stealth, melee=False)
c3.maybe_offer(tank, stealth, melee=False)
check("split fire asks once per target, not per weapon",
      first == 1 and len(decisions3._queue) == 1, f"{len(decisions3._queue)} prompts")

print("\n-- through the real FightController --")

c4, strat4, decisions4, tracker4, points4 = make_rig(phase=PHASE_FIGHT)
stealth.stim_injectors_active = False
fight = FightController(all_tokens=tokens, turn_tracker=tracker4, dice_manager=DiceManager(),
                        decision_manager=decisions4, target_reactions=(c4,))
fight.fighting_squad = boyz
fight.state = "choosing_target"
fight.target_squad = None


class _EngagedAll:
    """engaged_enemy_squads() normally needs real engagement geometry; the hook
    under test runs after that check, so it is stubbed rather than staged."""

    def __get__(self, obj, cls):
        return lambda squad: [stealth]


FightController.engaged_enemy_squads = _EngagedAll()
fight.choose_target_squad(stealth)
check("a melee target selection also offers it", decisions4.is_pending,
      (decisions4.prompt or "")[:80])

# ------------------------------------------------------------------- expiry
print("\n-- 'until the end of the phase' --")

c5, strat5, decisions5, tracker5, points5 = make_rig()
stealth.stim_injectors_active = True
ghostkeel.stim_injectors_active = True
c5.maybe_offer(tank, stealth)
c5.reset_phase([stealth, ghostkeel, boyz])
check("the grant expires on the phase change", not stealth.stim_injectors_active)
check("for both armies", not ghostkeel.stim_injectors_active and not boyz.stim_injectors_active)
check("and the per-attack de-duplication resets", not c5._offered_this_phase)

# Rule 15.01's own once-per-phase cap should make a second ACCEPTED use
# impossible without any extra bookkeeping here.
c6, strat6, decisions6, tracker6, points6 = make_rig()
stealth.stim_injectors_active = False
crisis2.stim_injectors_active = False
c6.maybe_offer(tank, stealth)
decisions6.choose(0)
check("first use accepted", stealth.stim_injectors_active)
check("a second unit cannot be given it the same phase (rule 15.01)",
      not c6.can_offer(tank, crisis2), "once per phase")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    for name in FAIL:
        print("  FAILED: " + name)
sys.exit(1 if FAIL else 0)
