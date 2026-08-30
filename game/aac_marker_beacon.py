"""Advanced Acquisition Cadre Stratagem: Marker Beacon (1CP).

RULE (verbatim, rules/tau_empire/detachments/Advanced Acquisition Cadre.md):
  WHEN:   End of your Movement phase.
  TARGET: One friendly PATHFINDER TEAM/STEALTH BATTLESUITS unit.
  EFFECT: Select one objective your unit is controlling. That objective is
          secured.

IT IS THE FIRST CALLER OF A HOOK THAT HAS BEEN WAITING
-------------------------------------------------------
game/objectives.py's Objective.secure_for() implements rule 14.03 and its own
docstring says it is "not called by anything yet, since we have no unit-ability
system; here for when one exists". This is that caller - so the mechanics of
Secured (a held objective stays controlled until the opponent's raw level of
control is strictly greater) are already written and are not restated here.

"AN OBJECTIVE YOUR UNIT IS CONTROLLING" is two conditions, not one: the
objective's controlled_by must be this player AND the unit must be in range of
it. A unit standing nowhere near an objective its army happens to hold cannot
plant a beacon on it.
"""

from game import advanced_acquisition_cadre as aac, objectives as objectives_module
from game import tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

MARKER_BEACON_CP = 1
MARKER_BEACON_NAME = "Marker Beacon"


class MarkerBeaconController:
    def __init__(self, stratagem_controller, turn_tracker=None, objectives=(),
                 all_tokens=None, decision_manager=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.objectives = list(objectives)
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._pending = None
        self._stratagem = Stratagem(
            name=MARKER_BEACON_NAME, cp_cost=MARKER_BEACON_CP, effect=self._secure,
        )

    def controllable_objectives(self, squad):
        """"one objective your unit is controlling" - held by this player AND
        with this unit in range of it."""
        if squad is None:
            return []
        return [o for o in self.objectives
                if o.controlled_by == squad.owner
                and o.secured_by != squad.owner
                and objectives_module.is_within_range_of_objective(squad, [o])]

    def panel_label(self, squad):
        return f"{MARKER_BEACON_NAME} ({MARKER_BEACON_CP} CP) - secure an objective"

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if not tau_detachments.has_detachment(squad.owner, aac.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        if not aac.is_fieldcraft_unit(squad):
            return False
        # Never offer what buys nothing: with no controlled objective in range
        # there is nothing to secure.
        if not self.controllable_objectives(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        candidates = self.controllable_objectives(squad)
        if len(candidates) == 1 or self.decision_manager is None:
            self._pending = candidates[0]
            return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])
        self.decision_manager.request(
            squad.owner,
            f"{MARKER_BEACON_NAME}: which objective does {squad.name} secure?",
            [(o.name, (lambda o=o: self._commit(squad, o))) for o in candidates]
            + [("Cancel", lambda: None)],
        )
        return True

    def _commit(self, squad, objective):
        self._pending = objective
        used = self.stratagem_controller.use(squad.owner, self._stratagem, [squad])
        if not used:
            self._pending = None
        return used

    def _secure(self, controller, player, targets):
        objective, self._pending = self._pending, None
        if objective is None:
            return
        objective.secure_for(player)
        if self.game_log is not None:
            self.game_log.add(
                f"{MARKER_BEACON_NAME}: {objective.name} is secured for {player} "
                "(rule 14.03)."
            )
