"""A mortal wound that is ROLLED must be a mortal wound that LANDS.

Four abilities opened a MortalWoundAllocationSession and none of them could
answer it. Measured before the fix, with Canoptek Wraiths moving over ten Boyz:

    session.remaining = 3   inflicted = 0   pending_choice = 10 candidates
    the log said "3 mortal wound(s)"
    wounds actually landed on the target: 0

Rule 06.02 says the DEFENDER allocates, so the session parks on
`pending_choice` whenever more than one model qualifies - and nothing in the
repo could ever answer it. Against a ONE-model target it resolved, which is why
four abilities shipped this way and every suite stayed green.

AND THE SAME THREE MODULES CRASHED ON THE OTHER SIDE OF THAT COIN. The session
calls `self.log(message)`; GameLog has no `__call__`. Eighteen of the twenty-one
construction sites handed over a callable, exactly three handed over the OBJECT
- so the moment one of those landed a wound on a single-model target it raised
`TypeError: 'GameLog' object is not callable` out of confirm_move() or
on_squad_finished_shooting(). Multi-model targets leaked, single-model targets
crashed; the two failure modes hid each other.

WHY ONE FILE FOR FOUR ABILITIES ACROSS TWO FACTIONS. It is one defect and one
fix: the four are Necron (Wraith Form) and Aeldari (Drakolithe, Harvester of
Souls, Monofilament Snare), and a per-faction suite could only ever have caught
its own - which is exactly what happened for four years. Same reasoning, and
the same shape, as test_return_placement.py owning one concern across eight
abilities.

The SOURCE half - "every module that opens one can drain it" as a set
difference, so the twenty-second cannot appear unnoticed - is
test_event_chain_wiring.py section 17. This file is the BEHAVIOUR half: the
wounds really land, and the log really works.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk                                                 # noqa: E402
from testkit import Checks                                           # noqa: E402

from game import drakolithe as dk                                    # noqa: E402
from game import harvester_of_souls as hs                            # noqa: E402
from game import monofilament_snare as ms                            # noqa: E402
from game import mortal_wound_sessions as mws                        # noqa: E402
from game import wraith_form as wf                                   # noqa: E402
from game.damage_resolution import MortalWoundAllocationSession       # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.factions.necrons import CANOPTEK_WRAITHS                    # noqa: E402
from game.factions.orks import BOYZ, GRETCHIN                         # noqa: E402

c = Checks("mortal wounds land")

HUMAN, AI = "Player 1", "Player 2"


def foe(name="2 Boyz 1", sheet=BOYZ, x=20.0, models=None):
    squad = tk.line_up(tk.build(sheet, AI, name=name), x, 20.0, spacing=1.4)
    if models is not None:
        squad.models[:] = squad.models[:models]
    return squad


def wounds_landed(squad, before):
    """The DIFFERENCE at the squad, which is the only measure that separates
    "landed" from "was ordered".

    `session.inflicted + session.remaining` is identical whether the session
    resolves or is orphaned, and two suites in this repo were once written
    around exactly that sum.
    """
    return before - sum(m.current_wounds for m in squad.models)


def total_wounds(squad):
    return sum(m.current_wounds for m in squad.models)


def pending(controller):
    """`controller.pending_damage_choice`, degrading to None.

    getattr, not a plain attribute: an A/B probe that REMOVES the member must
    make this suite go RED, not raise - the rule this repo has paid for
    seventeen times. A missing member then reads as "nothing on offer", which
    is exactly the defect being measured.
    """
    return getattr(controller, "pending_damage_choice", None)


def answer(controller):
    """Play the defender: keep choosing until the session is done.

    Returns how many allocations the controller actually asked for, so a
    controller that never asks is distinguishable from one that asks once.
    """
    asked = 0
    choose = getattr(controller, "choose_damage_model", None)
    if choose is None:
        return 0
    while pending(controller):
        choose(pending(controller)[0])
        asked += 1
        if asked > 50:                      # pragma: no cover - runaway guard
            break
    return asked


# ==========================================================================
print("=== 1. Wraith Form: the reported case, end to end ===")
# ==========================================================================

wraiths = tk.line_up(tk.build(CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 1"),
                     10.0, 20.0, spacing=1.4)
target = foe()
before = total_wounds(target)

dice = DiceManager()
ctrl = wf.WraithFormController(dice_manager=dice, decision_manager=DecisionManager(),
                               game_log=tk.Log(), auto_players=())
ctrl._use(wraiths, target)
dice.last_values = [6, 6, 6]
ctrl.on_dice_acknowledged()

c.true("three 4+ rolled a session", ctrl.mortal_wound_session is not None)
c.eq("...which parks, because rule 06.02 is the DEFENDER's choice",
     len(pending(ctrl) or []), len([m for m in target.models if not m.is_dead()]))

asked = answer(ctrl)
c.true("the defender was really asked", asked >= 1)
c.eq("THREE mortal wounds rolled, THREE landed", wounds_landed(target, before), 3)
c.eq("...and the session is cleared afterwards", ctrl.mortal_wound_session, None)
c.eq("...so nothing is left pending", pending(ctrl), None)

# THE COUNTER-PROOF. Without it this section would also pass if the fix had
# made every session resolve itself and taken the defender's choice away -
# which is a different bug wearing the same green.
target2 = foe(name="2 Boyz 2", x=30.0)
before2 = total_wounds(target2)
dice2 = DiceManager()
ctrl2 = wf.WraithFormController(dice_manager=dice2, decision_manager=DecisionManager(),
                                game_log=tk.Log(), auto_players=())
ctrl2._use(wraiths, target2)
dice2.last_values = [6, 6, 6]
ctrl2.on_dice_acknowledged()
c.eq("nothing lands until the defender answers", wounds_landed(target2, before2), 0)
c.true("...and it is still waiting", pending(ctrl2) is not None)

# A ONE-MODEL target never parked, which is precisely why this shipped.
solo = foe(name="2 Boyz solo", x=40.0, models=1)
before3 = total_wounds(solo)
dice3 = DiceManager()
ctrl3 = wf.WraithFormController(dice_manager=dice3, decision_manager=DecisionManager(),
                                game_log=tk.Log(), auto_players=())
ctrl3._use(wraiths, solo)
dice3.last_values = [6]
ctrl3.on_dice_acknowledged()
c.eq("a one-model target resolves with no choice at all - the case that hid this",
     wounds_landed(solo, before3), 1)

# is_busy is the DICE, not the allocation - stated, because reading it as the
# allocation is what made the phase gate look covered when it was not.
c.eq("is_busy is False while an allocation is still open", ctrl2.is_busy, False)
c.true("...so the phase gate has to read pending_damage_choice as well",
       pending(ctrl2) is not None)


# --- the Feel No Pain leg, and its ORDERING ---------------------------------
# on_dice_acknowledged() must answer a pending FNP roll BEFORE its `_pending is
# None` early return: _pending is the DICE context and is already cleared by
# the time the session exists, so a branch placed after it swallows every Feel
# No Pain acknowledgement. Six Aeldari controllers paid for this ordering.
#
# A RECORDING STUB, deliberately: what is under test is the CONTROLLER's branch
# order, not the session's Feel No Pain arithmetic - game/damage_resolution.py
# owns that and its own suite measures it. Driving a real roll here would need
# a Feel No Pain bearer and would then fail for reasons that have nothing to do
# with the branch.


class _FnpSession:
    def __init__(self):
        self.pending_fnp = object()
        self.pending_choice = None
        self.done = False
        self.acknowledged = 0

    def on_fnp_acknowledged(self):
        self.acknowledged += 1
        self.pending_fnp = None
        self.done = True


fnp_ctrl = wf.WraithFormController(dice_manager=DiceManager(),
                                   decision_manager=DecisionManager(),
                                   game_log=tk.Log(), auto_players=())
fnp_ctrl.mortal_wound_session = _FnpSession()
c.eq("the dice context is already empty by then", fnp_ctrl._pending, None)
claimed = fnp_ctrl.on_dice_acknowledged()
c.true("a Feel No Pain acknowledgement is still claimed", claimed)
c.eq("...and reached the session", fnp_ctrl.mortal_wound_session, None)


# ==========================================================================
print("=== 2. the log a session is handed must be CALLABLE ===")
# ==========================================================================

# The premise, asserted rather than assumed.
c.eq("testkit's Log is not callable", callable(tk.Log()), False)

# DRIVEN THROUGH THE REAL CONSTRUCTION SITES, not through a session this file
# builds itself. The first version of this section handed `controller._log` to
# a session it made here - which proved the helper exists and measured nothing
# about the argument the module actually passes. Both A/B probes reported NO
# BITE, which is how the gap in the test was found.
import game.dice as _gd                                              # noqa: E402
_real_randint = _gd.random.randint
_gd.random.randint = lambda a, b: b          # every roll succeeds


def crash_from(call):
    """Run a real inflict path against a ONE-model target and report the
    TypeError, if any.

    A one-model target deliberately: with two or more the session parks on
    pending_choice BEFORE the first log call and the crash never fires. That
    is why test_exodites.py and its neighbours were green through all of this.

    Caught rather than propagated, so an A/B probe makes this suite go RED
    instead of exploding - the rule this repo has paid seventeen times.
    """
    try:
        call()
    except TypeError as exc:                # pragma: no cover - the pre-fix world
        return str(exc)
    return None


bearer = tk.line_up(tk.build(CANOPTEK_WRAITHS, HUMAN, name="1 Drakolithe bearer"),
                    8.0, 40.0, spacing=1.4)
bearer.drakolithe_tokens = 3
drako_victim = foe(name="2 Boyz drako", x=20.0, models=1)
drako = dk.DrakolitheController(dice_manager=DiceManager(), game_log=tk.Log())
c.eq("drakolithe hands its session a log it can call",
     crash_from(lambda: drako.use(bearer, drako_victim)), None)
c.true("...and really opened one", len(drako.mortal_wound_sessions) >= 1)

harv_victim = foe(name="2 Boyz harv", x=26.0, models=1)
harvester = hs.HarvesterOfSoulsController(dice_manager=DiceManager(), game_log=tk.Log())
c.eq("harvester_of_souls hands its session a log it can call",
     crash_from(lambda: harvester._inflict(harv_victim)), None)
c.true("...and really opened one", len(harvester.mortal_wound_sessions) >= 1)

snare_victim = foe(name="2 Boyz snare", x=32.0, models=1)
snare_log = ms.MonofilamentSnareController(dice_manager=DiceManager(), game_log=tk.Log())
c.eq("monofilament_snare hands its session a log it can call",
     crash_from(lambda: snare_log._inflict(snare_victim, 1)), None)
c.true("...and really opened one", snare_log.mortal_wound_session is not None)

_gd.random.randint = _real_randint


# ==========================================================================
print("=== 3. the three list-holders drain in insertion order ===")
# ==========================================================================

# ORDER IS PART OF THE ANSWER: pending_choice() must offer the FIRST parked
# session and choose() must route into that SAME one, or two replays of one
# battle allocate the same wounds to different models.

first = foe(name="2 Boyz first", x=20.0)
second = foe(name="2 Boyz second", x=34.0)
b_first, b_second = total_wounds(first), total_wounds(second)

harv = hs.HarvesterOfSoulsController(dice_manager=DiceManager(), game_log=tk.Log())
harv.mortal_wound_sessions.append(
    MortalWoundAllocationSession(first, 2, dice_manager=DiceManager(), log=harv._log))
harv.mortal_wound_sessions.append(
    MortalWoundAllocationSession(second, 2, dice_manager=DiceManager(), log=harv._log))

c.eq("two sessions are open", len(harv.mortal_wound_sessions), 2)
offered = pending(harv)
c.true("the FIRST one is offered first",
       offered is not None and offered[0] in first.models)

answer(harv)
c.eq("both units took their wounds", (wounds_landed(first, b_first),
                                      wounds_landed(second, b_second)), (2, 2))
c.eq("...and the finished sessions were pruned", len(harv.mortal_wound_sessions), 0)
c.eq("...so nothing is left pending", pending(harv), None)

# reset_phase() PRUNES rather than clears: the phase gate holds the phase open
# on an unresolved allocation, so nothing should be dropped here - but if one
# ever is, it must survive rather than vanish.
harv2 = hs.HarvesterOfSoulsController(dice_manager=DiceManager(), game_log=tk.Log())
survivor = foe(name="2 Boyz survivor", x=44.0)
harv2.mortal_wound_sessions.append(
    MortalWoundAllocationSession(survivor, 1, dice_manager=DiceManager(), log=harv2._log))
harv2.reset_phase()
c.eq("reset_phase() keeps an UNRESOLVED session instead of dropping the wounds",
     len(harv2.mortal_wound_sessions), 1)

# The shared helpers themselves, at their edges.
c.eq("pending_choice of nothing is None", mws.pending_choice([]), None)
c.eq("...and of a list of Nones too", mws.pending_choice([None, None]), None)
c.eq("choose() into nothing is False", mws.choose([], object()), False)
c.eq("acknowledge_fnp() of nothing is False", mws.acknowledge_fnp([]), False)
c.eq("any_open() of nothing is False", mws.any_open([]), False)
_live = [None]
c.eq("prune() edits IN PLACE, so a controller's own list is the one that shrinks",
     mws.prune(_live) is _live, True)
c.eq("...and it really dropped the dead slot", _live, [])


# ==========================================================================
print("=== 4. every one of the four answers the three questions ===")
# ==========================================================================

# The shape main.py's damage-choice lists require. Section 17 of
# test_event_chain_wiring.py proves the SET is complete; this proves the four
# really answer, on a real controller, rather than merely defining the names.
FOUR = (("wraith_form", wf.WraithFormController(dice_manager=DiceManager(),
                                                game_log=tk.Log())),
        ("drakolithe", dk.DrakolitheController(dice_manager=DiceManager(),
                                               game_log=tk.Log())),
        ("harvester", hs.HarvesterOfSoulsController(dice_manager=DiceManager(),
                                                    game_log=tk.Log())),
        ("snare", ms.MonofilamentSnareController(dice_manager=DiceManager(),
                                                 game_log=tk.Log())))
for label, controller in FOUR:
    c.eq("%s: pending_damage_choice is None when idle" % label,
         pending(controller), None)
    c.eq("%s: choosing with nothing open is harmless" % label,
         controller.choose_damage_model(object()), None)
    c.eq("%s: an idle dice acknowledgement is not claimed" % label,
         controller.on_dice_acknowledged(), False)


# ==========================================================================
print("=== 5. Monofilament Snare lands its wounds too ===")
# ==========================================================================

# The one of the four whose wounds are rolled INLINE rather than through the
# dice panel, so its drain has an FNP-only acknowledgement - a different shape
# from the other three and worth measuring rather than assuming.
snared = tk.line_up(tk.build(GRETCHIN, AI, name="2 Gretchin 1"), 20.0, 30.0, spacing=1.2)
before_snare = total_wounds(snared)
snare = ms.MonofilamentSnareController(dice_manager=DiceManager(), game_log=tk.Log())
snare._inflict(snared, 2)
c.true("the snare's session parks on a multi-model unit",
       pending(snare) is not None)
answer(snare)
c.eq("...and both wounds land", wounds_landed(snared, before_snare), 2)
c.eq("...and it is cleared", snare.mortal_wound_session, None)

c.finish()
