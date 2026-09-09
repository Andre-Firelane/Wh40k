import json

import anthropic

from ai.base import Agent
from game import config

# Ceiling for the once-per-turn planning call (seconds). The SDK's own default
# is 600 - long enough that a stalled call reads as a hung game rather than a
# slow one. A planner that hasn't answered well inside this has already cost
# more than the turn it was planning; _maybe_generate_turn_plan() logs the
# failure and plays the turn unplanned rather than waiting any longer.
PLANNING_TIMEOUT_SECONDS = 120.0

# The tactical prompt lives in ai/tactical_prompt.py (see that module's docstring
# for why, and for where new rules belong). Re-exported under the old name so
# every existing reference keeps working.
from ai.tactical_prompt import TACTICAL_SYSTEM_PROMPT

SYSTEM_PROMPT = TACTICAL_SYSTEM_PROMPT

CHOOSE_ACTION_TOOL = {
    "name": "choose_action",
    "description": "Pick one of the numbered available actions.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "index": {"type": "integer", "description": "index into available_actions"},
        },
        "required": ["index"],
        "additionalProperties": False,
    },
}

# The strategic planning phase (see CLAUDE.md's Später-Liste "Planungsphase"
# design note for the original discussion): once per the AI's own turn,
# before any individual squad's Movement-phase decision, a separate call asks
# for a short, advisory turn plan - a role/target/priority per squad plus an
# overall turn_intent - that ai/agent_driver.py's per-squad decisions (see
# _handle_movement()) use as extra context and to reorder its squad loop.
# This never supplies coordinates and never creates new movement options -
# the existing deterministic geometry/legality code is untouched; it's purely
# whole-army coordination the isolated per-squad calls otherwise can't see
# (e.g. "let the vehicle go first" or "this squad screens while that one
# stays back to shoot").
PLAN_ROLES = (
    "advance", "hold", "screen", "stage", "claim_objective", "fall_back", "reserve_commit",
    "disembark",
    # The counterpart to "disembark", and its absence was a real bug: the role
    # vocabulary offered a way to say "get out" and none to say "stay in", so a
    # planner that wanted the latter picked "disembark" as the only
    # transport-related role and wrote its actual intent in the reason instead
    # ("2 Boyz 1: disembark (Stay embarked in 2 Trukk 1 this turn; no enemy in
    # charge or shooting range ... to justify unloading into the open yet.)").
    # agent_driver read the role, forced the question, and unloaded the squad -
    # the exact opposite of the order.
    "stay_embarked",
    # "stay off the board this round" - the counterpart to reserve_commit, and
    # what _validate_turn_plan() rewrites a too-early reserve_commit into. An
    # unrecognised role silently becomes "advance" (see _sanitize_turn_plan()
    # below), which for an off-board unit is meaningless noise, so this needs
    # to be a real role rather than a convention.
    "reserve",
)

# The planner's system prompt lives in its own module: it is long enough that
# keeping it here buried the logic, and long enough that it needs reviewing as
# a document rather than as a growing pile of appended paragraphs.
from ai.planner_prompt import PLANNER_SYSTEM_PROMPT  # noqa: E402  (kept next to its users)

TURN_PLAN_TOOL = {
    "name": "submit_turn_plan",
    "description": (
        "Submit a short turn plan: an overall intent, plus a role/target/priority for each of "
        "your own squads."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "turn_intent": {"type": "string"},
            "unit_plans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "squad": {"type": "string"},
                        "role": {"type": "string", "enum": list(PLAN_ROLES)},
                        "target": {"type": "string", "description": "empty string if not applicable"},
                        "priority": {"type": "integer", "description": "lower moves first"},
                        "reason": {"type": "string", "description": "empty string if not applicable"},
                        # A place, for everything that isn't a named unit or
                        # objective. Before this the plan could only ever point
                        # at things that HAVE names, so "get behind that ruin"
                        # or "hold this corner of the midfield" was simply
                        # inexpressible (user: "Der Planner muss da zum
                        # Beispiel einem Squad mal die Anweisung geben, hinter
                        # Mauer XY sich zu stellen... Kann der Planner der
                        # ausfuehrenden KI auch grobe Koordinaten mitgeben, wo
                        # sie sich hinbewegen soll?"). Two plain numbers rather
                        # than a nested object because the schema is strict:
                        # every property must be present on every entry, and
                        # -1 is off-board in both axes, so it reads as "no
                        # position given" without needing a nullable type.
                        "position_x": {
                            "type": "number",
                            "description": "board x in inches to move toward, or -1 for none",
                        },
                        "position_y": {
                            "type": "number",
                            "description": "board y in inches to move toward, or -1 for none",
                        },
                    },
                    "required": ["squad", "role", "target", "priority", "reason",
                                 "position_x", "position_y"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["turn_intent", "unit_plans"],
        "additionalProperties": False,
    },
}

_DEFAULT_PLAN_PRIORITY = 10**6


PLACEHOLDER_REASON_MARKERS = ("test plan", "placeholder", "tbd", "n/a", "example")


def _is_placeholder_plan(unit_plans):
    """Did the model hand back a stub instead of an actual plan?

    Observed in a real game: every one of seven units came back as
    `advance -> <some enemy>` with the reason literally "(test plan)" and no
    position for any of them. The plan was structurally perfect, so `malformed`
    (which only checked for an empty unit_plans and for leaked tool-call markup)
    passed it, and the whole turn ran on orders that carried no reasoning - which
    is how two units ended up shuffling along the board edge under the tactical
    layer's own fallback.

    Three signals, all cheap: a squad NAME that names itself a placeholder, a
    reason that does, or every unit sharing one identical reason. The last is
    the most general - a genuine plan explains each unit differently, because
    the whole point of per-unit orders is that the units have different jobs.

    The name check was added after a second real game: a revision came back with
    its entire unit_plans as one entry keyed literally "placeholder" at (0,0) and
    no reason at all. Both existing signals missed it - there was no reason text
    to match, and the "all reasons identical" rule needs more than two entries -
    so the plan passed as structurally valid and the turn ran with no orders.
    Whether the name matches a real squad cannot be asked here (this layer has
    no game state); ai/agent_driver.py's _validate_turn_plan() asks that."""
    names = [str(name or "").strip().lower() for name in unit_plans]
    if any(marker in name for name in names for marker in PLACEHOLDER_REASON_MARKERS):
        return True
    reasons = [str(entry.get("reason") or "").strip().lower()
               for entry in unit_plans.values()]
    if not reasons:
        return False
    if any(marker in reason for reason in reasons for marker in PLACEHOLDER_REASON_MARKERS):
        return True
    return len(reasons) > 2 and len(set(reasons)) == 1


def _sanitize_turn_plan(raw):
    """Defensive parsing of the raw submit_turn_plan tool input into the one
    shape ai/agent_driver.py is ever allowed to see:
    {"turn_intent": str, "unit_plans": {squad_name: {"role", "target",
    "priority", "reason"}}} (dict-keyed by squad name for O(1) lookup) -
    the same "never trust the model's raw output" convention as
    ClaudeAgent.decide()'s own index-bounds clamp. Malformed/missing fields
    fall back to safe defaults rather than raising - a bad plan should
    degrade to "no useful coordination this turn", never crash the game."""
    turn_intent = raw.get("turn_intent")
    if not isinstance(turn_intent, str):
        turn_intent = ""

    unit_plans = {}
    for entry in raw.get("unit_plans") or []:
        if not isinstance(entry, dict):
            continue
        squad = entry.get("squad")
        if not isinstance(squad, str) or not squad:
            continue
        role = entry.get("role")
        if role not in PLAN_ROLES:
            role = "advance"
        priority = entry.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool):
            priority = _DEFAULT_PLAN_PRIORITY
        target = entry.get("target")
        if not isinstance(target, str):
            target = ""
        reason = entry.get("reason")
        if not isinstance(reason, str):
            reason = ""
        # Normalised to a (x, y) tuple or None, so nothing downstream has to
        # know about the -1 sentinel or handle two loose numbers. Anything
        # off-board is treated as "not given" rather than clamped: a bogus
        # coordinate should fall back to the plan's other fields, not send a
        # squad marching at the table edge.
        position = None
        px, py = entry.get("position_x"), entry.get("position_y")
        if isinstance(px, (int, float)) and isinstance(py, (int, float)) \
                and not isinstance(px, bool) and not isinstance(py, bool) \
                and 0.0 <= px <= config.BOARD_WIDTH_IN and 0.0 <= py <= config.BOARD_HEIGHT_IN:
            position = (float(px), float(py))
        unit_plans[squad] = {
            "role": role, "target": target, "priority": priority,
            "reason": reason, "position": position,
        }

    # A plan with no unit entries is not a quiet plan, it is a FAILED plan: the
    # whole turn then runs with no coordination at all, and every field the
    # planner was given (threat assessment, score, terrain) goes unused. It was
    # previously indistinguishable from a plan that simply said little.
    # Observed for real: the model wrote the remainder of its own tool call as
    # literal text into turn_intent ("...next turn.</parname ... "unit_plans">
    # [{"squad": ...") and unit_plans parsed as empty, with no max_tokens
    # truncation to blame. Flag both so the caller can warn and retry.
    malformed = any(marker in turn_intent for marker in ("antml:", '"squad":', "unit_plans"))
    if malformed:
        # Keep the readable first sentence, drop the leaked markup - it is
        # otherwise dumped verbatim into the on-screen TURN PLAN overlay.
        for marker in ("antml:", '"squad":', "unit_plans"):
            cut = turn_intent.find(marker)
            if cut > 0:
                turn_intent = turn_intent[:cut].rstrip("<[{ \n")
    return {
        "turn_intent": turn_intent,
        "unit_plans": unit_plans,
        "malformed": malformed or not unit_plans or _is_placeholder_plan(unit_plans),
    }


class ClaudeAgent(Agent):
    """Real Claude-backed agent (Anthropic Python SDK). Requires
    ANTHROPIC_API_KEY - see game/env.py's load_dotenv(), called once at
    main.py startup, which reads the project's local (gitignored) .env file."""

    def __init__(self, model=None, planning_model=None):
        self.model = model or config.AI_MODEL
        # A once-per-own-turn call (see _sanitize_turn_plan()/plan_turn()
        # below) is far less frequent than the per-decision decide() calls,
        # so it's a reasonable place to spend a stronger/slower model -
        # defaults to the same tactical model until explicitly overridden.
        self.planning_model = planning_model or self.model
        self.client = anthropic.Anthropic()

    def decide(self, observation):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[CHOOSE_ACTION_TOOL],
            tool_choice={"type": "tool", "name": "choose_action"},
            messages=[{"role": "user", "content": json.dumps(observation)}],
        )
        tool_use = next(b for b in response.content if b.type == "tool_use")
        index = tool_use.input["index"]
        options = observation["available_actions"]
        if not (0 <= index < len(options)):
            return 0
        return index

    def plan_turn(self, observation, problems=()):
        """Produce this turn's plan. `problems` re-issues the request after the
        engine found orders it cannot carry out (see ai/agent_driver.py's
        _problems_for_the_planner()): the planner is the side that knows
        WHY a spot was chosen, so a bad coordinate goes back to it rather than
        being guessed at downstream."""
        # Streamed, with an explicit timeout, for two independent reasons.
        #
        # The timeout: the SDK's default is TEN MINUTES. A planner call that
        # hasn't answered in a couple of minutes has already cost more than
        # the turn it was planning is worth, and before this the whole game
        # would sit there waiting for it (user report: "jetzt hat sich das
        # spiel aufgehängt als der planner aktiv war" - the log ended exactly
        # at "Movement phase begins", the line right before this call).
        #
        # The streaming: a non-streaming request holds one long idle HTTP
        # connection, which is what actually trips request timeouts on a
        # slower model with a big observation and a 4096-token ceiling.
        # get_final_message() gives back the same Message object either way,
        # so nothing downstream changes.
        with self.client.with_options(timeout=PLANNING_TIMEOUT_SECONDS).messages.stream(
            model=self.planning_model,
            # Raised from 1024 once the planner started being shown BOTH
            # armies (see ai/agent_driver.py's _maybe_generate_turn_plan()):
            # a full 7-unit plan with real target names and reasons runs
            # comfortably past the old ceiling, and a plan truncated
            # mid-tool-call is a plan the whole turn then runs without.
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": PLANNER_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[TURN_PLAN_TOOL],
            tool_choice={"type": "tool", "name": "submit_turn_plan"},
            messages=[{"role": "user", "content": json.dumps(observation)}] + ([] if not problems else [
                {
                    "role": "user",
                    "content": (
                        "Your previous plan contained orders this army cannot carry out this turn:\n"
                        + "\n".join("  - " + p for p in problems)
                        + "\n\nIssue the plan again. Keep every order that was fine. For each "
                        "problem above, pick a DIFFERENT spot that keeps what you were after - "
                        "the cover, the objective, the angle - and that lies inside that unit's "
                        "\"reachable_this_turn\" circle. Do not simply shorten the line toward the "
                        "same far-off point: a spot partway there is a place you never evaluated, "
                        "and it is usually in the open."
                    ),
                }
            ]),
        ) as stream:
            response = stream.get_final_message()
        tool_use = next(b for b in response.content if b.type == "tool_use")
        plan = _sanitize_turn_plan(tool_use.input)
        # A plan cut off mid-tool-call silently loses whatever squads came
        # last (user report: "in zug 2 hat der thinking layer irgendwie die
        # strike teams vergessen" - the log showed that turn's plan ending
        # mid-sentence, with both Strike Teams, alphabetically last, absent).
        # Flagged rather than swallowed so the caller can log it.
        plan["truncated"] = response.stop_reason == "max_tokens"
        return plan
