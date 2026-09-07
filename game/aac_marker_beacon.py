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

WHY IT IS AN OFFER AND NOT A PANEL BUTTON
-----------------------------------------
It was a button on the Movement-phase panel, and in a real game it was NEVER
offered. Objective.controlled_by is only recomputed in advance_turn_phase()
(rule 14.02, "at the end of each phase"), so DURING the Movement phase it is
still the snapshot taken before anything moved - and the case this Stratagem
exists for is precisely "walk onto an objective and nail it down". The button
could only ever appear for ground you already held before you moved.

Its printed WHEN says "End of your Movement phase", which is exactly the
instant control has just been recomputed, so the offer lives there instead:
main.py calls offer_at_end_of_movement_phase() in its `phase_before ==
PHASE_MOVEMENT` block, after update_control(). The window that makes a
deferred answer legal is game/phase_window.py, for the same reason the three
end-of-Fight-phase Stratagems need one.

Its options name UNITS, so they are TAGGED for a board pick (game/unit_pick.py)
per the standing rule; the follow-up objective choice stays a list, because
objectives are not units.
"""

from game import advanced_acquisition_cadre as aac, ai_mode, objectives as objectives_module
from game import tau_detachments
from game.phase_window import PhaseWindow
from game.stratagems import Stratagem

MARKER_BEACON_CP = 1
MARKER_BEACON_NAME = "Marker Beacon"


class MarkerBeaconController:
    def __init__(self, stratagem_controller, turn_tracker=None, objectives=(),
                 all_tokens=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.objectives = list(objectives)
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # The end-of-Movement-phase window this controller's own offer opens.
        # NOT a live turn_tracker.phase test - see game/phase_window.py.
        self._window = PhaseWindow()
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

    def can_use(self, squad):
        if squad is None:
            return False
        if not self._window.is_open(squad.owner):
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

    def eligible_units(self, player):
        """Every unit of `player` this could be bought for right now."""
        squads = []
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            if squad is None or squad in squads or squad.owner != player:
                continue
            if not any(not m.is_dead() for m in squad.models):
                continue
            if not self.can_use(squad):
                continue
            squads.append(squad)
        return sorted(squads, key=lambda s: s.name)

    def reset_phase(self):
        """The window lasts exactly one phase boundary. main.py clears it in
        the per-phase reset block, which runs BEFORE that boundary's offers."""
        self._window.close()

    def offer_at_end_of_movement_phase(self, player):
        """WHEN: "End of your Movement phase" - offered to the player whose
        Movement phase just ended, i.e. main.py's `mover_before`.

        Called AFTER update_control(), which is the whole point: an objective
        this unit took during the move it just made is only controlled_by it
        from that recompute onwards.
        """
        if player is None or self.decision_manager is None:
            return False
        # Armed first, because can_use() asks the window - the offer IS the
        # moment, and it is only ever made at the boundary that owns it.
        self._window.arm(player)
        candidates = self.eligible_units(player)
        if not candidates:
            self._window.close()
            return False
        if player in self.auto_players:
            self._window.close()
            return False     # no AI path, by standing instruction
        self.decision_manager.request(
            player,
            f"{MARKER_BEACON_NAME} ({MARKER_BEACON_CP} CP): secure an objective "
            "with which unit?",
            [(squad.name, (lambda s=squad: self.use(s)), squad) for squad in candidates]
            + [("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

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
