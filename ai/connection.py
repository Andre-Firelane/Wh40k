"""Whether the AI can still be reached, and why not.

User: "momentan stürzt das Spiel ab, wenn KI Modus an ist und die Verbindung
verloren geht oder api Fehler oder Guthaben leer. besser wäre eine Meldung
'Connection lost' und das Spiel geht aber ohne KI weiter."

THREE FAILURES, ONE ANSWER. A dropped socket, a rejected key, an exhausted
balance and a rate limit are four different exceptions from the SDK, and the
game's response to all of them is the same: stop asking, say so once, and let
the human keep playing. So this module answers one question - is the agent
usable - rather than exposing a taxonomy nothing would branch on.

WHY IT IS A LATCH AND NOT A RETRY. Every one of those failures persists for
longer than a frame, and the loop asks the agent many times a second while
ai_auto_play is on: retrying would turn one lost connection into a stream of
timeouts, each of them stalling the frame it happens in. The first failure is
also the only INFORMATIVE one - everything after it is a consequence - so
`reason` keeps the first and ignores the rest.

MODULE-LEVEL, like game/aura_ruler.py and game/whole_unit_drag.py next door:
this is one fact about the running process, and every reader wants the same
answer. It is deliberately NOT reset between battles - a key that is out of
credit is still out of credit in the next game - but reset() exists for the
tests and for a deliberate "try again" should one ever be offered.
"""


class AIUnavailable(Exception):
    """Raised by the agent when a call could not be completed.

    Its own type rather than letting the SDK's exception through, because the
    engine must be able to tell "the agent could not answer" (recoverable: play
    on without it) from a genuine bug in a handler (not recoverable: it should
    still crash loudly rather than be swallowed into a silent wrong move).
    ai/agent_driver.py catches THIS and nothing wider."""


_offline_reason = None


def is_online():
    return _offline_reason is None


def reason():
    """Why the AI stopped, or None. Kept short enough for a modal line."""
    return _offline_reason


def report_failure(exc):
    """Record that a call failed. The FIRST one wins - see the module note.

    Returns the AIUnavailable to raise, so a caller can `raise
    connection.report_failure(exc)` and cannot forget to do both."""
    global _offline_reason
    if _offline_reason is None:
        _offline_reason = describe(exc)
    return AIUnavailable(_offline_reason)


def ask(call, *args, **kwargs):
    """Make one call to the agent, turning any failure into AIUnavailable.

    THE ONE BOUNDARY between the engine and the agent, and the reason it is
    here rather than inside ai/claude_agent.py: `agent` is an INTERFACE
    (ai/base.py), and the engine must survive any implementation of it failing
    - a MockAgent, a future local model, a stub in a harness. Guarding only the
    Anthropic client would leave every other one crashing the game.

    There are exactly three call sites (one decide, two plan_turn), which is
    the whole surface the engine has to the outside world.

    Deliberately `except Exception` rather than a list of anthropic's classes.
    Four failures matter to a player - dead socket, rejected key, exhausted
    balance, rate limit - and the SDK spells them as four types plus a family
    of status errors; enumerating them would leave the fifth one crashing the
    game, which is the bug being fixed. describe() still NAMES what happened,
    so an unexpected type reads as itself and not as "no connection".

    What this does NOT swallow: it wraps the agent call and nothing else, so a
    bug in a handler around it still crashes loudly instead of turning into a
    silently skipped turn."""
    try:
        return call(*args, **kwargs)
    except AIUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - the whole point is to not crash the game
        raise report_failure(exc) from exc


def describe(exc):
    """A short, human sentence for one SDK failure.

    Named causes rather than a stack trace, because this ends up on a modal a
    player reads mid-game: "out of credit" and "no connection" call for
    different actions from them, even though the game does the same thing. The
    match is on the exception's TYPE NAME rather than on `isinstance`, so this
    module does not import `anthropic` - it is also reached from tests and from
    a MockAgent run, where that import would be dead weight."""
    name = type(exc).__name__
    text = str(exc).strip()
    if name in ("APIConnectionError", "APITimeoutError", "APIConnectionTimeoutError"):
        return "no connection to the API"
    if name in ("AuthenticationError", "PermissionDeniedError"):
        return "the API key was rejected"
    if name == "RateLimitError":
        return "the API rate limit was reached"
    if name == "BadRequestError" and "credit" in text.lower():
        return "the API account is out of credit"
    if name in ("InternalServerError", "APIStatusError"):
        return "the API returned an error"
    # Anything else - including a bug inside the agent itself - is still a
    # reason the AI cannot answer, and is named rather than hidden so it does
    # not look like a network problem when it is not.
    return f"{name}: {text}" if text else name


def reset():
    global _offline_reason
    _offline_reason = None
