import random

from ai.base import Agent


class MockAgent(Agent):
    """Chooses a random legal action index. No API call - proves the
    decision-point/dispatch pipeline (ai/agent_driver.py) end-to-end for
    free, without any network dependency. Useful for smoke tests that must
    never spend real API credits."""

    def decide(self, observation):
        return random.randrange(len(observation["available_actions"]))

    def plan_turn(self, observation):
        """Trivial deterministic plan (role "advance" for every one of the
        caller's own squads, in observation order) - already in the exact
        sanitized shape ClaudeAgent.plan_turn() produces via
        ai/claude_agent.py's _sanitize_turn_plan(), so it exercises the
        whole planning pipeline for free, same purpose as decide() above."""
        unit_plans = {
            squad["name"]: {"role": "advance", "target": "", "priority": index, "reason": ""}
            for index, squad in enumerate(observation["squads"])
            if squad["owner"] == observation["meta"]["player"]
        }
        return {"turn_intent": "(mock plan) advance with everything.", "unit_plans": unit_plans}
