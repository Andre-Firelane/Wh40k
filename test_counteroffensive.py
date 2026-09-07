"""Rule 15.12 (Counteroffensive, 2 CP).

There was no suite for this stratagem at all, which is why the reported bug
survived: the grant set its bookkeeping correctly and a unit test driving the
controller directly would have seen every field it writes come out right. The
half that was missing is the one only the ALTERNATION can show - who actually
gets to select the next fighter.

Reported: "ich habe gerade counter offinsive benutzt, aber die ki hat dann
trotzdem zugeschlagen. cp wurden abgezogen"
(logs/game_20260901_142406.log, lines 440-447).
"""

import testkit as tk
from game.game_state import GameState
from game.turn import TurnTracker, PHASES, PHASE_FIGHT
from game.decision import DecisionManager
from game import fight as fight_module
from game.fight import FightController, FIGHTS_FIRST, REMAINING
from game.stratagems import StratagemController
from game.command_points import CommandPointManager
from game.counteroffensive import CounteroffensiveController, COUNTEROFFENSIVE_CP_COST
from game.factions import death_guard, aeldari

checks = tk.Checks("Counteroffensive (rule 15.12)")


# ---------------------------------------------------------------- the board

def scene(ai_second_unit_charged=True, human_charged=False):
    """The reported board: the AI has two engaged units, the human two.

    `ai_second_unit_charged` is what made the bug visible - with a Fights
    First unit still waiting on the AI's side, _settle_turn_state() hands the
    turn straight back to the AI after the first AI unit finishes, so the
    Counteroffensive grant lands on a player who is not the one selecting.
    """
    state = GameState()
    spawn = tk.build(death_guard.CHAOS_SPAWN, "Player 2", name="2 Chaos Spawn 2")
    prince = tk.build(death_guard.DAEMON_PRINCE_OF_NURGLE, "Player 2", name="2 Daemon Prince 1")
    scorps = tk.build(aeldari.STRIKING_SCORPIONS, "Player 1", name="1 Striking Scorpions 1")
    spears = tk.build(aeldari.SHINING_SPEARS, "Player 1", name="1 Shining Spears 1")
    # two separate combats, as in the reported game
    tk.line_up(spawn, x=52.0, y=37.0)
    tk.line_up(scorps, x=52.0, y=38.2)
    tk.line_up(prince, x=29.0, y=23.0)
    tk.line_up(spears, x=29.0, y=24.2)
    for squad in (spawn, prince, scorps, spears):
        for model in squad.models:
            state.add_token(model)

    tracker = TurnTracker()
    tracker.phase_index = PHASES.index(PHASE_FIGHT)
    tracker.turn_owner = "Player 2"
    tracker.set_active("Player 2")

    log, dice, decision = tk.Log(), tk.RecordingDice(), DecisionManager()
    fight = FightController(dice_manager=dice, turn_tracker=tracker, all_tokens=state.tokens,
                            decision_manager=decision, game_log=log)
    prince.fights_first = True          # rule 11.04: it charged
    spawn.fights_first = ai_second_unit_charged
    scorps.fights_first = human_charged
    spears.fights_first = human_charged
    fight.begin_fight_step()

    points = CommandPointManager(game_log=log)
    points.cp["Player 1"] = 5
    stratagems = StratagemController(game_log=log, command_points=points)
    counter = CounteroffensiveController(stratagems, fight, all_tokens=state.tokens,
                                         turn_tracker=tracker, game_log=log)
    fight.on_unit_finished_fighting = lambda squad: counter.offer_after(squad, decision)
    return dict(state=state, fight=fight, decision=decision, points=points, log=log,
                stratagems=stratagems, counter=counter,
                spawn=spawn, prince=prince, scorps=scorps, spears=spears)


def finish_a_fight(fight, squad):
    """Drive `squad` through a whole fight activation's END, the one place
    rule 15.12's window ("just after an enemy unit has resolved its attacks")
    is fired from, without rolling any dice."""
    fight.fighting_squad = squad
    fight._actually_finish_current_fight()


def choose(decision, needle):
    """Answer the pending prompt by LABEL, never by index."""
    for i, option in enumerate(decision.options):
        if needle in option["label"]:
            decision.choose(i)
            return True
    return False


# ------------------------------------- 1. the reported bug, end to end

s = scene()
fight = s["fight"]
checks.eq("1. before any fighting, alternation is on the AI", fight.whose_turn, "Player 2")

finish_a_fight(fight, s["prince"])

# This is the state the bug hides in: the AI's OTHER charged unit means the
# settle handed the turn back to the AI before the reaction was even offered.
checks.eq("1. after the AI unit finishes, the settle handed the turn back to the AI",
          fight.whose_turn, "Player 2")
checks.true("1. the reaction is offered to the human", s["decision"].is_pending)
checks.eq("1. it is offered to the human", s["decision"].player, "Player 1")

cp_before = s["points"].cp["Player 1"]
checks.true("1. the human can buy it for the Striking Scorpions",
            choose(s["decision"], "1 Striking Scorpions 1"))
checks.eq("1. it costs 2 CP", cp_before - s["points"].cp["Player 1"], COUNTEROFFENSIVE_CP_COST)

# The two halves of the printed effect.
checks.true("1. the unit gains Fights First", s["scorps"].fights_first)
checks.eq("1. it is recorded as the forced next fighter",
          fight.forced_next_fighter.get("Player 1"), s["scorps"])

# THE REPORTED FAILURE: everything above was already true before the fix.
checks.eq("1. alternation is handed to the human (the reported failure)",
          fight.whose_turn, "Player 1")
checks.eq("1. only that unit may be selected next",
          [q.name for q in fight.eligible_to_select_now()], ["1 Striking Scorpions 1"])
checks.true("1. the AI's remaining unit can NOT swing (the reported failure)",
            not fight.can_select_to_fight(s["spawn"]))
checks.true("1. the human's OTHER engaged unit is locked out too",
            not fight.can_select_to_fight(s["spears"]))
checks.true("1. the granted unit can actually be selected",
            fight.can_select_to_fight(s["scorps"]))


# ------------------------------------- 2. the constraint clears on use

s = scene()
fight = s["fight"]
finish_a_fight(fight, s["prince"])
choose(s["decision"], "1 Striking Scorpions 1")
fight.select_to_fight(s["scorps"])
checks.eq("2. selecting the forced unit satisfies and clears the constraint",
          fight.forced_next_fighter.get("Player 1"), None)
checks.eq("2. that unit is the one now fighting", fight.fighting_squad, s["scorps"])

# and the AI gets its turn back afterwards
finish_a_fight(fight, s["scorps"])
checks.eq("2. after the reaction resolves, alternation returns to the AI",
          fight.whose_turn, "Player 2")
checks.true("2. the AI's waiting unit can swing now",
            fight.can_select_to_fight(s["spawn"]))


# ------------------------------------- 3. a lapsed constraint frees selection

s = scene()
fight = s["fight"]
finish_a_fight(fight, s["prince"])
choose(s["decision"], "1 Striking Scorpions 1")
for model in s["scorps"].models:          # wiped out before its turn came up
    model.current_wounds = 0                 # Token.is_dead() reads this one
checks.true("3. a destroyed forced fighter is no longer eligible",
            not fight._is_eligible_to_fight(s["scorps"]))
eligible = fight.eligible_to_select_now()
checks.true("3. the constraint lapses instead of deadlocking",
            "Player 1" not in fight.forced_next_fighter)
checks.true("3. selection is not pinned to the dead unit",
            s["scorps"] not in eligible)


# ------------------------------------- 4. sub-step is NOT rewound

s = scene(ai_second_unit_charged=False)
fight = s["fight"]
finish_a_fight(fight, s["prince"])
# No Fights First unit left anywhere, so the settle dropped to Remaining.
checks.eq("4. with no Fights First unit left, the settle dropped to Remaining",
          fight.sub_step, REMAINING)
choose(s["decision"], "1 Striking Scorpions 1")
checks.eq("4. the grant does not rewind the sub-step", fight.sub_step, REMAINING)
checks.eq("4. the constraint binds regardless of sub-step",
          [q.name for q in fight.eligible_to_select_now()], ["1 Striking Scorpions 1"])


# ------------------------------------- 5. the announcement matches selection

s = scene()
fight = s["fight"]
finish_a_fight(fight, s["prince"])
choose(s["decision"], "1 Striking Scorpions 1")
# the LAST such line, not the first - the first is the AI's own turn
# announcement from the start of the Fight step.
line = [l for l in s["log"].lines if "it is your turn to fight" in l][-1]
checks.true("5. the human is told it is their turn", "Player 1:" in line)
checks.true("5. the announcement names the forced unit", "1 Striking Scorpions 1" in line)
checks.true("5. it does not also name a unit that cannot be picked",
            "1 Shining Spears 1" not in line)


# ------------------------------------- 6. rule 15.01, once per phase

s = scene()
fight = s["fight"]
finish_a_fight(fight, s["prince"])
choose(s["decision"], "1 Striking Scorpions 1")
fight.select_to_fight(s["scorps"])
finish_a_fight(fight, s["scorps"])
finish_a_fight(fight, s["spawn"])
checks.true("6. a second Counteroffensive in the same phase is not offered",
            not s["decision"].is_pending)


# ------------------------------------- 7. the offer itself

s = scene()
fight = s["fight"]
finish_a_fight(fight, s["prince"])
labels = [o["label"] for o in s["decision"].options]
checks.eq("7. both engaged human units are offered, plus Decline", len(labels), 3)
checks.eq("7. options are in a stable (sorted) order",
          labels[:2], sorted(labels[:2]))
checks.true("7. Decline is last", labels[-1] == "Decline")

s = scene()
fight = s["fight"]
finish_a_fight(fight, s["prince"])
cp_before = s["points"].cp["Player 1"]
choose(s["decision"], "Decline")
checks.eq("7. declining costs nothing", s["points"].cp["Player 1"], cp_before)
checks.eq("7. declining leaves alternation where the settle put it",
          fight.whose_turn, "Player 2")
checks.true("7. declining leaves no constraint", not fight.forced_next_fighter)


# ------------------------------------- 8. source guards

src_fight = open("game/fight.py", encoding="utf-8").read()
src_counter = open("game/counteroffensive.py", encoding="utf-8").read()

checks.true("8. the grant goes through force_next_fighter()",
            "self.fight_controller.force_next_fighter(player, squad)" in src_counter)
checks.true("8. it does not write forced_next_fighter directly any more",
            "forced_next_fighter[player]" not in src_counter)
checks.true("8. force_next_fighter hands alternation to the granting player",
            "self.whose_turn = player" in src_fight)
checks.true("8. the narrowing has ONE definition, read by selection",
            "self._forced_fighter_for(self.whose_turn)" in src_fight)
checks.eq("8. and by the announcement and the settle as well",
          src_fight.count("_forced_fighter_for("), 4)  # def + 3 readers

checks.finish()
