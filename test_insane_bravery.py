"""Rule 15.04 Insane Bravery, and rule 08.03's Battle-Shock eligibility.

THERE WAS NO TEST FOR EITHER before now - no test_insane_bravery.py and no
test_battle_shock.py - which is why "Insane bravery wird manchmal nicht
angeboten" could stand as a user report with nothing in the repo able to
answer it. BattleShockController appeared only as an incidental stub in eight
other suites.

The report was NOT a broken rule. Four separate clauses can each remove the
button, at four different moments, and none of them said anything:

    * max_per_battle=1 - it was already spent this battle (15.04);
    * rule 15.01's targeted_this_phase - ANY other stratagem used on this
      same squad this phase hides it, and Command Re-roll is a stratagem;
    * not enough CP, surcharges included;
    * the unit no longer owes a roll at all (08.03).

So what is fixed is the SILENCE: why_not() returns a reason, and the panel
prints it where the button would have been. The rule itself is unchanged - the
ten out-of-turn battle-shock triggers it still does not reach are a deliberate
gap, guarded by test_event_chain_wiring.py section 21.

FIXTURE WARNING, and it will bite anyone extending this file: force_pass() and
on_dice_acknowledged() BOTH write rolled_squad_ids, so a section that resolves
a roll poisons every later section that renders the same squad. Every section
below builds its own stage. (And UnitProfile is a CLASS attribute - copy it,
never set a flag on it.)
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()

import testkit as tk  # noqa: E402
from game.battle_shock import BattleShockController  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.insane_bravery import InsaneBraveryController, INSANE_BRAVERY_CP_COST  # noqa: E402
from game.stratagems import Stratagem, StratagemController  # noqa: E402
from game.turn import PHASE_COMMAND, PHASE_MOVEMENT, TurnTracker  # noqa: E402
from game.factions import orks  # noqa: E402

checks = tk.Checks("Insane Bravery")


def stage(cp=3, phase=PHASE_COMMAND, active="Player 1", shocked=True):
    """A fresh stage - see the module docstring on why every section needs one.

    The squad is battle-shocked by default, which is one of 08.03's two ways of
    owing a roll and the one that does not depend on casualties."""
    squad = tk.build(orks.BOYZ, "Player 1", name="1 Boyz 1")
    tk.line_up(squad, x=20.0, y=20.0)
    squad.battle_shocked = shocked
    turn = TurnTracker(first_player="Player 1")
    while turn.phase != phase:
        turn.advance_phase()
    turn.turn_owner = active
    turn.set_active(active)
    log = tk.Log()
    dice = tk.RecordingDice()
    points = CommandPointManager(game_log=log)
    points.cp["Player 1"] = cp
    strat = StratagemController(command_points=points, game_log=log)
    shock = BattleShockController(dice_manager=dice, turn_tracker=turn, game_log=log)
    bravery = InsaneBraveryController(stratagem_controller=strat, battle_shock_controller=shock,
                                     turn_tracker=turn, game_log=log)
    return dict(squad=squad, turn=turn, log=log, dice=dice, points=points,
                strat=strat, shock=shock, bravery=bravery)


# --- 1. the rule works -----------------------------------------------------
print("--- 1. the rule works ---")

sc = stage()
tokens = list(sc["squad"].models)
checks.true("a battle-shocked unit owes a roll (08.03)", sc["shock"].can_roll(sc["squad"]))
checks.eq("...so the button belongs on screen", sc["bravery"].why_not(sc["squad"]), (True, None))
checks.true("...and 08.03 counts it as still pending",
            sc["shock"].has_pending_required_rolls(tokens, "Player 1"))

sc["bravery"].use(sc["squad"])
checks.eq("using it clears battle-shock without a roll", sc["squad"].battle_shocked, False)
checks.eq("...and no dice were thrown", sc["dice"].is_pending, False)
checks.eq("it costs 1 CP", sc["points"].cp["Player 1"], 3 - INSANE_BRAVERY_CP_COST)
checks.eq("...and 08.03 no longer counts the unit as owing one",
          sc["shock"].has_pending_required_rolls(tokens, "Player 1"), False)
checks.true("...and it is logged",
            any("Insane Bravery" in line for line in sc["log"].lines))


# --- 2. every refusal reason, as a STRING and against the boolean ----------
print("--- 2. every refusal says why ---")


def refusal(sc_, label):
    """why_not(), with the boolean asserted at EVERY level from the same call.

    A reason that disagrees with the boolean is the drift the (bool, reason)
    shape exists to prevent - and it has to be checked on each pair, not just
    the top one. InsaneBraveryController.can_use() IS why_not()[0], so
    comparing those two can never fail; the pair that can genuinely diverge is
    BattleShockController's, and an A/B probe that made can_roll() forget a
    clause proved this helper was checking the wrong level."""
    ok, why = sc_["bravery"].why_not(sc_["squad"])
    checks.eq("%s: can_use() agrees with why_not()" % label,
              sc_["bravery"].can_use(sc_["squad"]), ok)
    checks.eq("%s: can_roll() agrees with why_cannot_roll()" % label,
              sc_["shock"].can_roll(sc_["squad"]),
              sc_["shock"].why_cannot_roll(sc_["squad"])[0])
    checks.eq("%s: the stratagem's can_use() agrees with refusal()" % label,
              sc_["strat"].can_use("Player 1", sc_["bravery"]._stratagem, [sc_["squad"]]),
              sc_["strat"].refusal("Player 1", sc_["bravery"]._stratagem, [sc_["squad"]]) is None)
    return ok, why


# ONCE PER BATTLE (15.04) - the reported case: it works, then it is gone.
sc = stage()
sc["bravery"].use(sc["squad"])
sc["squad"].battle_shocked = True          # shocked again a round later
sc["shock"].reset_command_phase()          # a new Command phase...
sc["strat"].reset_phase()                  # ...on BOTH ledgers
# Both resets are needed and the order of the clauses is why: 15.01's
# once-per-PHASE check sits above max_per_battle in refusal(), so without the
# stratagem reset this measures "already used this phase" and never reaches
# the once-per-BATTLE clause it means to.
ok, why = refusal(sc, "spent")
checks.eq("spent: not offered", ok, False)
checks.true("...and it says it is spent, not nothing: %r" % why,
            bool(why) and "this battle" in why)

# RULE 15.01: any OTHER stratagem on this same squad this phase hides it.
sc = stage()
# allow_battle_shocked_target, or rule 01.07 refuses this use outright and
# targeted_this_phase never gets written - the stage would then measure
# nothing. Insane Bravery itself opts out of 01.07 for the same reason.
other = Stratagem(name="Something Else", cp_cost=0, effect=lambda *a: None,
                  allow_battle_shocked_target=True)
sc["strat"].use("Player 1", other, [sc["squad"]])
ok, why = refusal(sc, "another stratagem")
checks.eq("another stratagem hit this squad this phase: not offered", ok, False)
checks.true("...and it names the unit and the rule: %r" % why,
            bool(why) and "15.01" in why and sc["squad"].name in why)

# NOT ENOUGH CP.
sc = stage(cp=0)
ok, why = refusal(sc, "no CP")
checks.eq("no CP: not offered", ok, False)
checks.true("...and it says how much is needed: %r" % why,
            bool(why) and "1 CP" in why and "have 0" in why)

# THE UNIT OWES NO ROLL (08.03) - neither shocked nor below half strength.
sc = stage(shocked=False)
ok, why = refusal(sc, "healthy unit")
checks.eq("a healthy unit: not offered", ok, False)
checks.true("...and it says the unit owes nothing: %r" % why,
            bool(why) and "08.03" in why)

# WRONG PHASE, and whose phase it is - two different reasons.
sc = stage(phase=PHASE_MOVEMENT)
ok, why = refusal(sc, "wrong phase")
checks.eq("outside the Command phase: not offered", ok, False)
checks.true("...and it says which phase: %r" % why,
            bool(why) and "Command phase" in why)

sc = stage(active="Player 2")
ok, why = refusal(sc, "opponent's phase")
checks.eq("in the opponent's Command phase: not offered", ok, False)
checks.true("...and it says whose: %r" % why, bool(why) and "your own" in why)

# ALREADY ROLLED this phase - the clause a forced out-of-turn test can also
# set, and the one that takes the mandatory 08.03 button away at the same time.
sc = stage()
sc["shock"].rolled_squad_ids.add(sc["squad"])
ok, why = refusal(sc, "already rolled")
checks.eq("already rolled this phase: not offered", ok, False)
checks.true("...and it says so: %r" % why, bool(why) and "already made" in why)

# NOTHING SELECTED is not a refusal to explain - the panel prints nothing.
sc = stage()
checks.eq("no squad: no reason to print", sc["bravery"].why_not(None), (False, None))

# A ROLL IN PROGRESS blocks it too, and says so.
sc = stage()
sc["shock"].rolling_squad = sc["squad"]
ok, why = refusal(sc, "roll in progress")
checks.eq("a roll already being made: not offered", ok, False)
checks.true("...and it says so: %r" % why, bool(why) and "already being made" in why)


# --- 3. can_use() is DERIVED, so each rule has one reader ------------------
print("--- 3. one reader per rule ---")

_bs_src = io.open("game/battle_shock.py", encoding="utf-8").read()
_st_src = io.open("game/stratagems.py", encoding="utf-8").read()
_ib_src = io.open("game/insane_bravery.py", encoding="utf-8").read()
checks.true("BattleShockController.can_roll() is derived from why_cannot_roll()",
            "return self.why_cannot_roll(squad)[0]" in _bs_src)
checks.true("StratagemController.can_use() is derived from refusal()",
            "return self.refusal(player, stratagem, targets, extra_cp) is None" in _st_src)
checks.true("InsaneBraveryController.can_use() is derived from why_not()",
            "return self.why_not(squad)[0]" in _ib_src)


# --- 4. the panel prints the reason where the button would be --------------
print("--- 4. the panel prints it ---")

# Checked at the SOURCE. _draw_movement_ui() takes ~80 arguments through a
# three-stage positional chain, and reaching this branch through the real
# dispatch would be testing the call, not the branch. What matters is that the
# panel asks the explainer and prints its answer through the panel's own hint
# channel rather than inventing a disabled-button look.
_ap_src = io.open("game/ui/action_panel.py", encoding="utf-8").read()
checks.true("the panel asks why_not(), not can_use()",
            "insane_bravery_controller.why_not(squad)" in _ap_src)
checks.eq("...exactly once - widening the offer has to be a deliberate act",
          _ap_src.count("insane_bravery_controller.why_not"), 1)
checks.true("the button is still drawn when it is allowed",
            'self._draw_button(surface, bravery_rect, "Insane Bravery (1CP)"' in _ap_src)
_after = _ap_src.split("bravery_why")[-1][:260] if "bravery_why" in _ap_src else ""
checks.true("...and the reason is printed instead when it is not",
            "Insane Bravery (1CP): {bravery_why}" in _ap_src)
checks.true("...through the panel's hint channel, not as a dead button",
            "color=HINT_COLOR" in _after)

# THE CONVENTION THIS FOLLOWS, stated in action_panel.py itself three times
# over: no chrome for a control that cannot do anything. A greyed-out button
# would need a disabled state in button_style, which every screen reads.
checks.eq("no disabled-button state was invented in button_style",
          "disabled" in io.open("game/ui/button_style.py", encoding="utf-8").read().lower(),
          False)


checks.finish()
