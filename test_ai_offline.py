"""A lost connection stops the AI, not the game.

User: "momentan stürzt das Spiel ab, wenn KI Modus an ist und die Verbindung
verloren geht oder api Fehler oder Guthaben leer. besser wäre eine Meldung
'Connection lost' und das Spiel geht aber ohne KI weiter."

WHAT IS WORTH GUARDING here is not "an exception was caught". It is:
  * that the catch is NARROW - a bug in a handler must still crash loudly,
    because a silently skipped AI turn is far harder to notice than a
    traceback, and swallowing everything is the easy wrong fix;
  * that it LATCHES - the loop asks the agent many times a second, and
    retrying a dead socket every frame would stall every frame;
  * that the game really goes ON, which is a different claim from "it did not
    crash" and the one the report actually makes.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()
pygame.display.set_mode((1, 1))

import io  # noqa: E402

import testkit as tk  # noqa: E402
from ai import connection  # noqa: E402
from ai.connection import AIUnavailable  # noqa: E402
from game.ui import ai_offline_overlay as aoo  # noqa: E402
from game.ui.ai_offline_overlay import AIOfflineOverlay  # noqa: E402

c = tk.Checks("AI offline")


def read(path):
    return io.open(path, encoding="utf-8").read()


class FakeSDKError(Exception):
    pass


def named(name, text=""):
    """An exception whose TYPE NAME is what describe() matches on - which is
    how ai/connection.py avoids importing anthropic just to classify."""
    return type(name, (Exception,), {})(text)


# --- 1. the latch ----------------------------------------------------------
print("\n=== 1. the latch ===")

connection.reset()
c.true("it starts online", connection.is_online())
c.eq("...with nothing to report", connection.reason(), None)

raised = connection.report_failure(named("APIConnectionError"))
c.true("a failure takes it offline", not connection.is_online())
c.true("...and hands back the exception to raise", isinstance(raised, AIUnavailable))
c.eq("...with a readable reason", connection.reason(), "no connection to the API")

# The FIRST failure is the informative one; everything after is a consequence.
connection.report_failure(named("RateLimitError"))
c.eq("a later failure does not overwrite the first",
     connection.reason(), "no connection to the API")
connection.reset()
c.true("reset puts it back online", connection.is_online())


# --- 2. the four failures a player can actually have -----------------------
print("\n=== 2. what it says ===")

for name, text, want in (
    ("APIConnectionError", "", "no connection to the API"),
    ("APITimeoutError", "", "no connection to the API"),
    ("AuthenticationError", "", "the API key was rejected"),
    ("PermissionDeniedError", "", "the API key was rejected"),
    ("RateLimitError", "", "the API rate limit was reached"),
    ("BadRequestError", "Your credit balance is too low", "the API account is out of credit"),
    ("InternalServerError", "", "the API returned an error"),
):
    c.eq(f"{name} reads as something a player can act on",
         connection.describe(named(name, text)), want)

# Anything else is NAMED rather than dressed up as a network problem: an
# unexpected type reading as "no connection" would send someone to check their
# router over a bug in the agent.
c.true("an unexpected failure names itself",
       connection.describe(named("ValueError", "boom")).startswith("ValueError"))
c.true("...including its message", "boom" in connection.describe(named("ValueError", "boom")))
# A BadRequestError that is NOT about credit must not claim it is.
c.eq("a non-credit BadRequestError is not called an empty account",
     connection.describe(named("BadRequestError", "tool schema invalid")),
     "BadRequestError: tool schema invalid")


# --- 3. ask(): narrow on purpose -------------------------------------------
print("\n=== 3. the boundary ===")

connection.reset()
c.eq("a working call passes its result through",
     connection.ask(lambda obs: obs * 2, 21), 42)
c.eq("...and its keyword arguments", connection.ask(lambda a, b=0: a + b, 1, b=2), 3)
c.true("...without going offline", connection.is_online())


def boom(_obs):
    raise named("APIConnectionError")


try:
    connection.ask(boom, {})
    c.true("a failed call raises AIUnavailable", False)
except AIUnavailable:
    c.true("a failed call raises AIUnavailable", True)
c.true("...and latches", not connection.is_online())

# ALREADY-AIUnavailable passes straight through rather than being re-wrapped,
# so a nested call cannot rewrite the reason that was recorded first.
connection.reset()
connection.report_failure(named("AuthenticationError"))
try:
    connection.ask(lambda: (_ for _ in ()).throw(AIUnavailable("inner")))
except AIUnavailable:
    pass
c.eq("an AIUnavailable is not re-described", connection.reason(),
     "the API key was rejected")
connection.reset()


# --- 4. the notice ---------------------------------------------------------
print("\n=== 4. the notice ===")

ov = AIOfflineOverlay()
c.true("it starts silent", not ov.is_pending)
c.true("showing it raises the notice", ov.show("no connection to the API"))
c.true("...and it is pending", ov.is_pending)
c.eq("showing it AGAIN does nothing - one event, one notice", ov.show("whatever"), False)
ov.dismiss()
c.true("a click puts it away", not ov.is_pending)
c.eq("...and it does not come back", ov.show("again"), False)
c.true("...still away", not ov.is_pending)

# A new battle in the same process may announce it again - main() is one
# battle, run() is the application.
ov.reset()
c.true("a fresh battle can announce it again", ov.show("no connection to the API"))

surface = pygame.Surface((900, 560))
surface.fill((40, 55, 70))
ov.draw(surface)
ink = sum(1 for x in range(0, 900, 3) for y in range(0, 560, 3)
          if surface.get_at((x, y))[:3] != (40, 55, 70))
c.true("it draws something", ink > 500)
# It must say the two things the report asked for: what happened, and that the
# game goes on. Pinned as the TEXT, because a notice that only said
# "Connection lost" would leave a player waiting for it to come back.
c.true("the heading is the one the user asked for", "CONNECTION LOST" in aoo.HEADING)
c.true("...and the body says the battle continues", "continues" in aoo.BODY.lower())
c.true("...and that they take over", "you" in aoo.BODY.lower())

blank = AIOfflineOverlay()
before = surface.copy()
blank.draw(surface)
c.eq("a silent notice draws nothing",
     pygame.image.tostring(surface, "RGB"), pygame.image.tostring(before, "RGB"))


# --- 5. the driver stops asking --------------------------------------------
print("\n=== 5. the driver ===")

from ai import agent_driver  # noqa: E402

connection.reset()
calls = {"n": 0}


def counting_take_one_action(*_a, **_k):
    calls["n"] += 1
    return "acted"


_real = agent_driver._take_one_action
try:
    agent_driver._take_one_action = counting_take_one_action
    c.eq("online: the action runs", agent_driver.take_one_action(None, None, None), "acted")
    c.eq("...once", calls["n"], 1)

    connection.report_failure(named("APIConnectionError"))
    c.eq("offline: it does nothing at all", agent_driver.take_one_action(None, None, None), None)
    c.eq("...and does not even try - no round-trip per frame", calls["n"], 1)

    # THE NARROWNESS, and it is the check most worth having: a real bug must
    # still crash. Swallowing everything here would turn a broken handler into
    # an AI that silently stops playing, which nobody would report as a bug.
    connection.reset()

    def broken(*_a, **_k):
        raise ValueError("a bug in a handler")

    agent_driver._take_one_action = broken
    try:
        agent_driver.take_one_action(None, None, None)
        c.true("a genuine bug still crashes", False)
    except ValueError:
        c.true("a genuine bug still crashes", True)

    def unavailable(*_a, **_k):
        raise AIUnavailable("mid-action")

    agent_driver._take_one_action = unavailable
    try:
        absorbed = agent_driver.take_one_action(None, None, None)
    except AIUnavailable:
        # Red, not a crash: a probe that removes the catch must say WHICH
        # check broke. Sixth time this lesson has been paid for here.
        absorbed = "escaped"
    c.eq("...but an unreachable agent mid-action is absorbed", absorbed, None)
finally:
    agent_driver._take_one_action = _real
    connection.reset()


# --- 6. wiring -------------------------------------------------------------
print("\n=== 6. wiring ===")

DRIVER = read(os.path.join("ai", "agent_driver.py"))
MAIN = read("main.py")

# EVERY agent call goes through the boundary. Counted, so a fourth one added
# later without the guard moves this line rather than crashing a game.
c.eq("every agent call goes through connection.ask()",
     DRIVER.count("connection.ask("), 3)
c.eq("...and none calls the agent directly any more",
     DRIVER.count("agent.decide(observation)") + DRIVER.count("agent.plan_turn(observation"), 0)

c.true("main() builds the notice", "ai_offline_overlay = AIOfflineOverlay()" in MAIN)
# The WHOLE statement, not just the call: "if False and <call>" still contains
# the call, so a pin on the substring alone stayed green while the notice was
# disabled - found by its own A/B probe, which is what they are for.
c.true("...raises it where the AI would have acted",
       "if not ai_connection.is_online():" in MAIN
       and "if ai_offline_overlay.show(ai_connection.reason()):" in MAIN)
c.true("...logs it too, so a finished game still says why",
       "The AI stopped playing" in MAIN)
c.true("...and can be clicked away", "ai_offline_overlay.dismiss()" in MAIN)
# It leads the notice order: everything behind it is about a game whose rules
# of engagement just changed.
c.true("it is in the one-modal-at-a-time order",
       "battle_end_overlay, ai_offline_overlay," in MAIN)
# find(), not index(): a missing needle must make this red rather than raise
# ValueError out of the suite - the same trap `before()` was added for
# elsewhere in this repo.
_offline_at = MAIN.find("ai_offline_overlay,")
_notice_at = MAIN.find("stratagem_notice_overlay,")
c.true("...ahead of the announcements",
       _offline_at != -1 and _notice_at != -1 and _offline_at < _notice_at)

c.finish()
