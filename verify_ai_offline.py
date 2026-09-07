"""Runtime proof through the REAL main() loop that an API failure stops the AI
and not the game.

User: "momentan stürzt das Spiel ab, wenn KI Modus an ist und die Verbindung
verloren geht oder api Fehler oder Guthaben leer. besser wäre eine Meldung
'Connection lost' und das Spiel geht aber ohne KI weiter."

The agent is made to raise what the SDK really raises, on its first call, in
selfplay.py's real loop. Reported: whether main() survived, whether the failure
was latched with a readable reason, whether the notice was raised exactly once,
and how many frames the game went on running afterwards - because "it did not
crash" and "it kept playing" are different claims and only the second is what
was asked for.

Harness trap this walks into deliberately: importing selfplay runs nothing (its
__main__ guard), so it goes via runpy.

Usage:  python verify_ai_offline.py [map] [frames]
        python verify_ai_offline.py map2 1200 --neutralize
"""

import runpy
import sys

import anthropic

from ai import connection, mock_agent
from game.ui import ai_offline_overlay

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

state = {"calls": 0, "shown": 0, "reason": None, "frames_after": 0, "crash": None}

connection.reset()

_real_decide = mock_agent.MockAgent.decide
_real_show = ai_offline_overlay.AIOfflineOverlay.show


def decide(self, observation):
    state["calls"] += 1
    # What the SDK raises when the socket dies. Raised from the AGENT, so
    # everything between it and the loop is the real path.
    raise anthropic.APIConnectionError(request=None)


def show(self, reason=None):
    out = _real_show(self, reason)
    if out:
        state["shown"] += 1
        state["reason"] = reason
    return out


mock_agent.MockAgent.decide = decide
ai_offline_overlay.AIOfflineOverlay.show = show

if NEUTRALIZE:
    # THE PRE-FIX WORLD: the engine calls the agent directly again, so an SDK
    # error propagates exactly as it used to. Only the guard is removed -
    # everything else, including the notice, stays wired, so what this measures
    # is the guard and not the whole feature.
    connection.ask = lambda call, *a, **k: call(*a, **k)

# Count frames AFTER the failure, which is the half that says "the game went
# on" rather than merely "it did not crash".
import pygame  # noqa: E402

_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    if state["calls"]:
        state["frames_after"] += 1
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "1200"])
try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit as exc:
    if exc.code:
        state["crash"] = f"SystemExit({exc.code})"
except BaseException as exc:  # noqa: BLE001 - reporting the crash IS the point
    state["crash"] = f"{type(exc).__name__}: {exc}"

print()
print("--- AI offline spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print(f"  agent calls attempted : {state['calls']}")
if not state["calls"]:
    print("  INCONCLUSIVE - the harness never reached a decision point")
    raise SystemExit(2)
print(f"  CRASHED OUT OF main() : {state['crash'] or 'no'}")
print(f"  latched offline       : {not connection.is_online()}"
      f"  ({connection.reason()})")
print(f"  notice raised         : {state['shown']} time(s)"
      f"  reason={state['reason']!r}")
print(f"  frames after failure  : {state['frames_after']}")
