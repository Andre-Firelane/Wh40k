from abc import ABC, abstractmethod


class Agent(ABC):
    @abstractmethod
    def decide(self, observation):
        """observation: the dict from ai/observation.py's build_observation()
        (meta/squads/available_actions). Return the integer index of the
        chosen entry in observation["available_actions"]."""
        raise NotImplementedError

    @abstractmethod
    def plan_turn(self, observation):
        """observation: the dict from ai/observation.py's
        build_planning_observation() (meta/squads/objectives, no
        available_actions - this isn't a choose_action-style enumerated
        choice). Return a sanitized turn plan:
        {"turn_intent": str, "unit_plans": {squad_name: {"role": str,
        "target": str, "priority": int, "reason": str}}} - advisory context
        for ai/agent_driver.py's per-squad movement decisions, never
        coordinates. See ai/claude_agent.py's PLAN_ROLES for the known role
        values."""
        raise NotImplementedError
