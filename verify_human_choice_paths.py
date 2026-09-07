"""Does the AI still answer everything ITSELF, in a real battle?

The risk stage 1 carries is not that a rule stops working - it is that a rule
which now OFFERS starts offering to the AI too. Any prompt the AI cannot answer
inside its own controller falls through to ai/agent_driver.py's
_maybe_resolve_decision(), which goes to the LLM: a real API call, potentially
once per frame. So "the human is asked" has to arrive without "the AI is asked".

No suite can answer that. A unit test builds the controller and passes what it
likes; this drives the REAL main() loop with Necrons on BOTH sides - the army
the user named, and the one carrying most of the changed rules - and reports
every DecisionManager prompt by player.

Usage:  python verify_human_choice_paths.py [map2] [--frames N]
Exit 0 if the AI was never prompted.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import collections
import runpy

MAP = "map2"
FRAMES = "1500"
for arg in sys.argv[1:]:
    if arg.startswith("--frames"):
        FRAMES = arg.split("=", 1)[1]
    elif arg.startswith("map"):
        MAP = arg

from game import config                    # noqa: E402
from game.decision import DecisionManager  # noqa: E402

# Necrons on BOTH sides: the changed rules are Necron-heavy (Reanimation
# Protocols, the Warriors re-roll, the Resurrection Orb), and putting them on
# the human's side too is the only way this run exercises the half the user
# reported.
config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False

prompts = collections.Counter()
_real_request = DecisionManager.request


def spy_request(self, player, prompt, options, **kwargs):
    prompts[(player, prompt.split(":")[0][:44])] += 1
    return _real_request(self, player, prompt, options, **kwargs)


DecisionManager.request = spy_request

# The generic fallback. If the AI ever reaches this, a prompt it was supposed
# to answer for free went to the model instead.
from ai import agent_driver                # noqa: E402

fallbacks = [0]
_real_fallback = agent_driver._maybe_resolve_decision


def spy_fallback(*args, **kwargs):
    result = _real_fallback(*args, **kwargs)
    if result:
        fallbacks[0] += 1
    return result


agent_driver._maybe_resolve_decision = spy_fallback

# STAGE THE FACT, rather than hope the run walks into it. A MockAgent run
# rarely reaches a Shooting phase (this repo's documented harness limit), so
# nothing gets damaged, so Reanimation Protocols skips every unit
# (UNITS_MUST_HAVE_SOMETHING_TO_GAIN) and the whole check passes having
# measured nothing - which is the failure mode it exists to avoid.
#
# So: the first time the human's Command phase comes round, wound a couple of
# their Necrons. That is exactly the board state the user described - a human
# playing Necrons with casualties to recover - and everything after it is the
# real controller on a real board.
from game import reanimation_protocols as rp   # noqa: E402

staged = {"done": False, "activations": 0}
_real_begin = rp.ReanimationProtocolsController.begin_command_phase


def spy_begin(self, squads, player):
    if not staged["done"] and player not in config.AI_PLAYERS:
        for squad in sorted(squads, key=lambda s: s.name):
            if squad.owner == player and len(squad.models) > 3:
                for model in squad.models[:2]:
                    model.current_wounds = 0
                for model in squad.models[:2]:
                    if model in squad.models:
                        squad.models.remove(model)
                        squad.destroyed_models.append(model)
                staged["done"] = True
                print(f"[staged] wounded 2 models of {squad.name} "
                      f"so Reanimation Protocols has something to recover")
                break
    result = _real_begin(self, squads, player)
    if result:
        staged["activations"] += 1
    return result


rp.ReanimationProtocolsController.begin_command_phase = spy_begin

sys.argv = ["selfplay.py", MAP, FRAMES]
try:
    runpy.run_path("selfplay.py", run_name="__main__")
except SystemExit:
    pass

ai_players = tuple(config.AI_PLAYERS)
print("\n" + "=" * 72)
print(f"AI side: {ai_players}      prompts raised: {sum(prompts.values())}")
print(f"Reanimation Protocols activated: {staged['activations']} time(s)")

by_player = collections.Counter()
for (player, _label), n in prompts.items():
    by_player[player] += n
for player in sorted(by_player):
    tag = "AI" if player in ai_players else "human"
    print(f"  {player} ({tag}): {by_player[player]}")

if prompts:
    print("\n  what was asked, by player:")
    for (player, label), n in sorted(prompts.items(), key=lambda kv: -kv[1])[:12]:
        tag = "AI" if player in ai_players else "human"
        print(f"    {n:4d}  [{tag:5}] {player}: {label}")

asked_ai = {k: v for k, v in prompts.items() if k[0] in ai_players}
print(f"\n  generic LLM fallback used: {fallbacks[0]} time(s)")

# LIVE GUARD. "The AI was never prompted" is trivially true on a run that
# never reached a rule - so the run has to be shown to have exercised one.
exercised = staged["activations"] > 0
ok = not asked_ai and fallbacks[0] == 0 and exercised
if not exercised:
    print("\n  *** THE RUN NEVER REACHED REANIMATION PROTOCOLS - this check "
          "measured nothing.")
if asked_ai:
    print("\n  *** THE AI WAS PROMPTED - these cost an API call each:")
    for (player, label), n in sorted(asked_ai.items()):
        print(f"      {n:4d}  {player}: {label}")
if fallbacks[0]:
    print("\n  *** THE GENERIC FALLBACK FIRED - that is a real agent.decide() call.")

print("\n" + ("PASS - the AI answered everything inside its own controllers"
              if ok else "FAIL"))
sys.exit(0 if ok else 1)
