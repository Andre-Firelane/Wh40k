"""Forewarned has to be DECIDED BEFORE the Hit roll, not alongside it.

User report: "forewarned wurde angeboten, da wurde der trefferwurf schon
gewuerfelt. das ist zu frueh. das muss ich davor entscheiden."

The engine's own sequence was already right - FightController fires its target
reactions at the select-targets step (rule 12.02), before anything is rolled.
What was wrong sat in ai/agent_driver.py: _handle_fight() called
select_to_fight() and then _resolve_fight_choices() in ONE synchronous call, and
the second of those throws the Hit roll. So the defender's prompt and the dice
appeared in the same frame, and answering it could no longer affect the roll it
was raised for.

The Shooting phase learned this one report earlier (Psychic Shield, see
_choose_shooting_target_and_weapon()'s guard). The Fight phase - Forewarned's
phase - never got the same treatment. Both halves of the select-targets step are
covered here: the auto-pick for a unit engaged with exactly ONE enemy (the
ordinary case, and the one the report came from) and the explicit multi-target
choice.

The assertion that matters is not "a prompt appeared" but WHICH SIDE OF THE
DICE it appeared on - so every check below is about the dice log.
"""
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk
from ai import agent_driver
from game import fight as fight_mod
from game import forewarned
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.factions import aeldari as ae
from game.factions import necrons as nec
from game.factions.datasheet import build_squad
from game.stratagems import StratagemController
from game.turn import PHASE_FIGHT, TurnTracker

c = tk.Checks("Forewarned - decided before the Hit roll")


def section(title):
    print(f"\n--- {title} ---")


HUMAN, AI = "Player 1", "Player 2"


def scene(psyker_y=14.0, second_target=False):
    """The AI's Skorpekh Destroyers engaged with a human ASURYANI INFANTRY unit
    that stands within 9" of a friendly PSYKER - Forewarned's printed TARGET
    clause, built to fire rather than asserted to."""
    state = tk.GameState()
    defender = build_squad(ae.STORM_GUARDIANS, HUMAN, name="1 Storm Guardians 1")
    psyker = build_squad(ae.FARSEER, HUMAN, name="1 Farseer 1")
    attacker = build_squad(nec.SKORPEKH_DESTROYERS, AI, name="2 Skorpekh Destroyers 1")
    tk.line_up(defender, x=20.0, y=20.0)
    # Inside 9" so the TARGET clause holds, but out of Engagement Range unless
    # the caller wants a second legal target (which is what turns the auto-pick
    # into an explicit choice).
    tk.line_up(psyker, x=20.0, y=psyker_y)
    tk.line_up(attacker, x=20.0, y=20.9)
    tokens = list(defender.models) + list(psyker.models) + list(attacker.models)
    state.tokens = tokens

    turn = TurnTracker(first_player=AI)
    while turn.phase != PHASE_FIGHT:
        turn.advance_phase()
    dice = tk.RecordingDice()
    dm = DecisionManager()
    points = CommandPointManager(game_log=tk.Log())
    for player in points.cp:
        points.cp[player] = 6
    strat = StratagemController(game_log=tk.Log(), command_points=points)
    ctrl = forewarned.ForewarnedController(
        strat, decision_manager=dm, game_log=tk.Log(),
        all_tokens=tokens, turn_tracker=turn,
    )
    fc = fight_mod.FightController(
        all_tokens=tokens, game_log=tk.Log(), dice_manager=dice, turn_tracker=turn,
        decision_manager=dm, target_reactions=(ctrl,),
    )
    fc.begin_fight_step()
    return dict(fight=fc, dice=dice, dm=dm, defender=defender, attacker=attacker,
                tokens=tokens, points=points)


def rolled(s):
    return [label for label, _values in s["dice"].rolled]


# --------------------------------- 1. the reported case: one engaged enemy
section("1. auto-picked target (the reported case)")

s = scene()
c.true("the scene really makes Forewarned legal",
       forewarned.eligible_unit(s["defender"])
       and forewarned.near_friendly_psyker(s["defender"], s["tokens"]))

attacker = s["attacker"]
s["fight"].select_to_fight(attacker)
c.eq("select_to_fight() auto-picks the only engaged enemy",
     getattr(s["fight"].target_squad, "name", None), s["defender"].name)
c.true("...and that raises the defender's prompt", s["dm"].is_pending)
c.eq("...owned by the DEFENDER, not the attacker", s["dm"].player, HUMAN)
c.eq("NOTHING has been rolled yet", rolled(s), [])

# The guard itself: this is what makes the AI stop instead of rolling on.
c.true("the AI is told to yield", agent_driver._defender_is_deciding(s["fight"]))

# Answer it, exactly as the human would.
s["dm"].choose(0)
c.true("accepting sets the grant", forewarned.applies(s["defender"]))
c.eq("...and still nothing has been rolled", rolled(s), [])

# Only now may the attacker resume.
agent_driver._resolve_fight_choices(None, AI, s["tokens"], s["fight"], attacker, None)
labels = rolled(s)
c.eq("the Hit roll happens after the answer", len(labels), 1)
# The point of the whole fix: the decision reached the roll it was raised for.
c.true(f"...and it CARRIES Forewarned ({labels[0]!r})", "Forewarned" in labels[0])


# ------------------------------- 2. A/B: without the guard, dice come first
section("2. A/B - the pre-fix ordering")

s = scene()
attacker = s["attacker"]
s["fight"].select_to_fight(attacker)
c.true("prompt open", s["dm"].is_pending)
# Exactly what _handle_fight() used to do: resolve in the same call, without
# ever asking whether the defender was still deciding.
agent_driver._resolve_fight_choices(None, AI, s["tokens"], s["fight"], attacker, None)
labels = rolled(s)
c.eq("A/B: the Hit roll lands while the prompt is still open", len(labels), 1)
c.true("A/B: the prompt is STILL unanswered at that point", s["dm"].is_pending)
c.true(f"A/B: and the roll could not carry Forewarned ({labels[0]!r})",
       "Forewarned" not in labels[0])


# --------------------------------- 3. the multi-target half of the same step
section("3. explicitly chosen target")

# A second engaged enemy turns the auto-pick into choose_target_squad(), which
# is the other place the select-targets step happens - and it raises the same
# reactions.
s = scene(psyker_y=20.9)
attacker = s["attacker"]
s["fight"].select_to_fight(attacker)
c.eq("two engaged enemies -> the AI must choose", s["fight"].state, fight_mod.CHOOSING_TARGET)
c.eq("no prompt yet, no target selected", s["dm"].is_pending, False)
c.eq("...and nothing rolled", rolled(s), [])

s["fight"].choose_target_squad(s["defender"])
c.true("choosing raises the prompt", s["dm"].is_pending)
c.eq("...before any dice", rolled(s), [])
c.true("the AI is told to yield here too", agent_driver._defender_is_deciding(s["fight"]))


# ------------------------------------------- 4. the guard is wired in main
section("4. wiring in ai/agent_driver.py")

src = io.open("ai/agent_driver.py", encoding="utf-8").read()

# Both halves of the select-targets step must stop. Checked at the SOURCE
# because a behavioural test drives _resolve_fight_choices() itself and so
# cannot see whether _handle_fight() would have called it too early.
select_i = src.index("fight_controller.select_to_fight(squad)")
c.true("_handle_fight() checks before resolving",
       "_defender_is_deciding(fight_controller)" in src[select_i:select_i + 1400])
choose_i = src.index("fight_controller.choose_target_squad(target)")
c.true("_resolve_fight_choices() checks after choosing a target",
       "_defender_is_deciding(fight_controller)" in src[choose_i:choose_i + 500])
c.eq("one definition of the question, used twice",
     src.count("def _defender_is_deciding("), 1)
c.eq("...and called from exactly those two places",
     src.count("if _defender_is_deciding(fight_controller):"), 2)

# The Shooting phase's equivalent guard must stay - it is the same bug, and
# this suite is where the pair is documented.
c.true("the Shooting phase keeps its own guard",
       "shooting_controller.decision_manager is not None and shooting_controller.decision_manager.is_pending" in src)


c.finish()
