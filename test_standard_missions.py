"""game/missions.py: the two STANDARD missions and their rates.

User: "ändere die Missionen der ki leicht. primary gibt 6 Punkte pro objektive,
statt 3. und secondary gibt 3 statt 1."

There was no suite for this module - the two rates were only ever asserted
incidentally, as literals, inside three other files. That is exactly how a
retune goes wrong: the ledger changes, the mission card keeps printing the old
number, and the AI keeps planning against it. Both of those are checked here.

The load-bearing section is 3: every place a rate is SHOWN or TOLD to someone
must be derived from the constant, not written out beside it.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from game import config, missions, primary_missions  # noqa: E402
from game.missions import MissionController  # noqa: E402

c = tk.Checks("Standard missions")


class _Objective:
    def __init__(self, controlled_by=None):
        self.controlled_by = controlled_by


class _Squad:
    def __init__(self, owner):
        self.owner = owner


def ledger(players=("Player 1", "Player 2")):
    return MissionController(players=players, game_log=tk.Log())


# Both standard missions are what a player gets when they are NOT on one of the
# two card systems, so every check here empties those tuples.
_was_primary = config.PRIMARY_MISSION_CARD_PLAYERS
_was_secondary = config.SECONDARY_MISSION_CARD_PLAYERS
config.PRIMARY_MISSION_CARD_PLAYERS = ()
config.SECONDARY_MISSION_CARD_PLAYERS = ()


# --- 1. the rates ----------------------------------------------------------
print("--- 1. the rates ---")

# Every rate check below runs in a round that PAYS. The round band itself is
# section 1b's subject, and mixing the two would let a broken band hide behind
# a rate that happens to be zero.
SCORING_ROUND = missions.PRIMARY_FIRST_SCORING_ROUND

c.eq("Hold the Line pays 6 per objective", missions.PRIMARY_POINTS_PER_OBJECTIVE, 6)
c.eq("No Mercy pays 3 per kill", missions.SECONDARY_POINTS_PER_KILL, 3)

# Multiples, not just one: a rate mistaken for a flat "score N if you hold
# anything" passes every single-objective test.
board = [_Objective("Player 2"), _Objective("Player 2"), _Objective("Player 1"),
         _Objective(None)]
led = ledger()
c.eq("two objectives pay twice the rate",
     led.score_primary(board, "Player 2", SCORING_ROUND), 2 * missions.PRIMARY_POINTS_PER_OBJECTIVE)
c.eq("...and the other player's one pays once",
     led.score_primary(board, "Player 1", SCORING_ROUND), missions.PRIMARY_POINTS_PER_OBJECTIVE)
c.eq("...both landing in the same ledger",
     led.primary_points["Player 2"], 2 * missions.PRIMARY_POINTS_PER_OBJECTIVE)
c.eq("holding nothing pays nothing",
     ledger().score_primary([_Objective(None)], "Player 1", SCORING_ROUND), 0)

# The victims are held in a list on purpose. record_destroyed_squad()
# deduplicates by id(squad), and a squad created inline is freed the moment the
# call returns - CPython then hands the SAME id to the next one, so three
# temporaries counted as one kill. Harmless in the real game, where the squads
# are alive on the board, but a trap for anything driving this module directly.
led = ledger()
victims = [_Squad("Player 1") for _ in range(3)]   # each credits Player 2
for victim in victims:
    led.record_destroyed_squad(victim)
c.eq("three kills pay three times the rate",
     led.score_secondary_end_of_turn("Player 2"), 3 * missions.SECONDARY_POINTS_PER_KILL)
c.eq("...and the tally is cleared", led.score_secondary_end_of_turn("Player 2"), 0)
c.eq("no kills, no points", ledger().score_secondary_end_of_turn("Player 1"), 0)


# --- 1b. the first battle round pays nothing --------------------------------
print("--- 1b. round 1 pays nothing ---")

# User: "man sollte im ersten zug noch keine vp fuer objectives bekommen. erst
# ab zug 2." Hold the Line was the ONLY Primary in the game still paying for the
# board as it stood at deployment - all five Force Disposition cards already
# band their objective boxes "2ND ROUND ONWARD".
c.eq("the band starts at round 2", missions.PRIMARY_FIRST_SCORING_ROUND, 2)
c.eq("...which is the same round the Force Disposition cards print",
     missions.PRIMARY_FIRST_SCORING_ROUND, primary_missions.SECOND_ROUND_ONWARD)

_held = [_Objective("Player 2"), _Objective("Player 2"), _Objective("Player 2")]
led = ledger()
c.eq("round 1 pays nothing at all, however much is held",
     led.score_primary(_held, "Player 2", 1), 0)
c.eq("...and nothing reaches the ledger either", led.primary_points["Player 2"], 0)
# BOTH sides of the boundary, or "< 2" written as "< 3" would pass too.
c.eq("round 2 pays in full",
     led.score_primary(_held, "Player 2", 2), 3 * missions.PRIMARY_POINTS_PER_OBJECTIVE)
c.eq("...and so does every round after",
     led.score_primary(_held, "Player 2", missions.BATTLE_ROUNDS),
     3 * missions.PRIMARY_POINTS_PER_OBJECTIVE)

# The parameter has no default, so a call site that forgets it is a TypeError
# rather than a silent return to paying for the deployment.
try:
    ledger().score_primary(_held, "Player 2")
    _no_default = False
except TypeError:
    _no_default = True
c.true("battle_round is required, not defaulted", _no_default)

# Source guard: every call site in main.py passes the LIVE round. A behaviour
# test cannot see a fourth one added later, and the argument is what carries
# the rule - a call that hardcoded a 2 would score round 1 again.
_main_src = open("main.py", encoding="utf-8").read()
_calls = [_chunk.split(")")[0] for _chunk in
          _main_src.split("mission_controller.score_primary(")[1:]]
c.eq("main.py still calls score_primary from all three places", len(_calls), 3)
c.eq("...and every one of them passes turn_tracker.battle_round",
     sum(1 for _call in _calls if "turn_tracker.battle_round" in _call), 3)

# Named exception, so it does not read as one the fix missed: Battlefield
# Dominance's "MORE OBJ" box is printed "Rounds 1-2" on the card, and a
# transcribed rule wins over this one.
_more_obj = [b for b in primary_missions.BATTLEFIELD_DOMINANCE.boxes
             if b.key == "more_objectives"]
c.eq("Battlefield Dominance still has its Rounds 1-2 box", len(_more_obj), 1)
c.true("...and it still pays in round 1, because that is what it prints",
       _more_obj[0].in_round_band(1))


# --- 2. who actually gets them --------------------------------------------
print("--- 2. who gets them ---")

# "The AI's missions" is what these are in the SHIPPED config, and the reason
# is worth pinning: neither is owned by a player. Each is what everyone NOT on
# the matching card system plays.
config.PRIMARY_MISSION_CARD_PLAYERS = ("Player 1",)
config.SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)
led = ledger()
c.eq("the card player gets no Hold the Line",
     led.score_primary([_Objective("Player 1")], "Player 1", SCORING_ROUND), 0)
c.eq("...but the AI does",
     led.score_primary([_Objective("Player 2")], "Player 2", SCORING_ROUND),
     missions.PRIMARY_POINTS_PER_OBJECTIVE)
pair = [_Squad("Player 2"), _Squad("Player 1")]   # held: see the note above
for victim in pair:
    led.record_destroyed_squad(victim)
c.eq("the deck player gets no No Mercy", led.score_secondary_end_of_turn("Player 1"), 0)
c.eq("...but the AI does",
     led.score_secondary_end_of_turn("Player 2"), missions.SECONDARY_POINTS_PER_KILL)

# And the flags are read at CALL time, so a harness that empties them really
# turns the card systems off rather than leaving a stale import behind.
config.PRIMARY_MISSION_CARD_PLAYERS = ()
config.SECONDARY_MISSION_CARD_PLAYERS = ()
c.eq("emptied, everyone is back on Hold the Line",
     ledger().score_primary([_Objective("Player 1")], "Player 1", SCORING_ROUND),
     missions.PRIMARY_POINTS_PER_OBJECTIVE)


# --- 3. nothing quotes a stale rate ---------------------------------------
print("--- 3. no stale rate anywhere ---")

# The mission strip prints this text. A card promising a different number than
# the ledger pays is the drift this repo consolidates on sight.
c.true("the Primary's printed text carries its own rate",
       f"{missions.PRIMARY_POINTS_PER_OBJECTIVE} victory points"
       in missions.PRIMARY_MISSION_TEXT)
c.true("the Secondary's printed text carries its own rate",
       f"{missions.SECONDARY_POINTS_PER_KILL} victory points"
       in missions.SECONDARY_MISSION_TEXT)

# The AI plans by weighing ground against kills with exactly this arithmetic,
# so a stale rate in the prompt is a wrong plan every turn - and nothing in the
# game would contradict it.
from ai.planner_prompt import PLANNER_SYSTEM_PROMPT  # noqa: E402
from ai.tactical_prompt import TACTICAL_SYSTEM_PROMPT  # noqa: E402

for name, prompt in (("planner", PLANNER_SYSTEM_PROMPT),
                     ("tactical", TACTICAL_SYSTEM_PROMPT)):
    c.true(f"the {name} prompt quotes the live Primary rate",
           f"{missions.PRIMARY_POINTS_PER_OBJECTIVE} VP" in prompt)
    c.true(f"the {name} prompt quotes the live Secondary rate",
           f"{missions.SECONDARY_POINTS_PER_KILL} VP per enemy unit" in prompt)
    # The counter-check, and the one that would actually have caught the bug:
    # the OLD rates must be gone. "quotes the new number" passes on a prompt
    # that contains both.
    c.true(f"the {name} prompt no longer says 3 VP per objective",
           "3 VP per objective" not in prompt and "3 VP for each objective" not in prompt)
    c.true(f"the {name} prompt no longer says 1 VP per enemy unit",
           "1 VP per enemy unit" not in prompt)

# Source guard: the rates are interpolated, not retyped. Four places quoted
# them before this change and only one of them is the constant.
for path in ("game/missions.py", "ai/planner_prompt.py", "ai/tactical_prompt.py"):
    src = open(path, encoding="utf-8").read()
    c.true(f"{path} names the Primary constant", "PRIMARY_POINTS_PER_OBJECTIVE" in src)
    c.true(f"{path} names the Secondary constant", "SECONDARY_POINTS_PER_KILL" in src)

# Ground still has to pay repeatedly and a kill once - that is the shape of the
# advice both prompts give, and it survives the retune (6 per objective PER
# ROUND against 3 once). If a future retune inverted it, this line is where the
# advice stops matching the arithmetic.
c.true("ground still out-pays kills over a battle",
       missions.PRIMARY_POINTS_PER_OBJECTIVE * missions.BATTLE_ROUNDS
       > missions.SECONDARY_POINTS_PER_KILL)
for name, prompt in (("planner", PLANNER_SYSTEM_PROMPT),
                     ("tactical", TACTICAL_SYSTEM_PROMPT)):
    c.true(f"...and the {name} prompt still says so",
           "pays repeatedly" in prompt or "pays round after round" in prompt)


config.PRIMARY_MISSION_CARD_PLAYERS = _was_primary
config.SECONDARY_MISSION_CARD_PLAYERS = _was_secondary

c.finish()
