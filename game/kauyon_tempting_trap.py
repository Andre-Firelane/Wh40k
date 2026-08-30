"""Kauyon Stratagem: A Tempting Trap (1CP).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  WHEN:   Your Shooting phase.
  TARGET: One T'AU EMPIRE unit from your army that has not been selected to
          shoot this phase. The first time you use this Stratagem, you must
          also select one objective marker that is not in your opponent's
          deployment zone; until the end of the battle, this becomes your Trap
          objective marker.
  EFFECT: Until the end of the phase, each time a model in your unit makes a
          ranged attack that targets an enemy unit within range of your Trap
          objective marker, add 1 to the Wound roll.
  RESTRICTIONS: You cannot use this Stratagem during the first or second battle
          rounds.

TWO LIFETIMES IN ONE STRATAGEM
-------------------------------
The GRANT lasts the phase; the TRAP OBJECTIVE lasts the BATTLE and is chosen
once, on first use. They are stored and cleared separately for the same reason
Auxiliary Cadre's prey mark and its offer memo are: folding them together would
quietly re-ask for the objective every phase, or quietly keep the grant for the
whole game.

The trap is held per PLAYER rather than per unit - "YOUR Trap objective
marker", one per army, read by every unit that later buys this.

"NOT IN YOUR OPPONENT'S DEPLOYMENT ZONE"
-----------------------------------------
Checked geometrically against the zone itself, the same way
game/secondary_missions.py decides what counts as a home objective, rather than
by name. Note it is the OPPONENT'S zone only: your own zone and No Man's Land
are both legal, which is wider than the "No Man's Land only" clause some
mission cards use and is why this does not reuse their helper.

"WITHIN RANGE OF AN OBJECTIVE MARKER" is rule 12.08's own phrase, so it is
game/objectives.py's is_within_range_of_objective() and its 3" - not a new
distance.
"""

from game import kauyon, objectives as objectives_module, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

TEMPTING_TRAP_CP = 1
TEMPTING_TRAP_NAME = "A Tempting Trap"
TEMPTING_TRAP_EARLIEST_ROUND = 3


def is_active(squad):
    return bool(getattr(squad, "tempting_trap_active", False))


class TemptingTrapController:
    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, objectives=(), deployment_zones=None,
                 decision_manager=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.objectives = list(objectives)
        # {player -> DeploymentZone}, so "not in your OPPONENT'S zone" can be
        # asked without this module knowing how zones are built.
        self.deployment_zones = dict(deployment_zones or {})
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._traps = {}          # player -> the chosen objective, for the battle
        self._stratagem = Stratagem(
            name=TEMPTING_TRAP_NAME, cp_cost=TEMPTING_TRAP_CP, effect=self._grant,
        )

    # -- state ------------------------------------------------------------
    def reset_phase(self, squads=()):
        """The GRANT is phase-scoped. The trap objective is NOT touched here -
        it lasts the battle."""
        for squad in squads or ():
            squad.tempting_trap_active = False

    def trap_for(self, player):
        return self._traps.get(player)

    def candidate_objectives(self, player):
        """"one objective marker that is not in your opponent's deployment
        zone" - so your own zone and No Man's Land both qualify."""
        enemy_zones = [zone for owner, zone in self.deployment_zones.items()
                       if owner != player and zone is not None]
        out = []
        for objective in self.objectives:
            area = objective.terrain_area
            centre = (getattr(area, "center_x_in", None), getattr(area, "center_y_in", None))
            if None in centre:
                out.append(objective)
                continue
            if any(zone.contains_point(centre[0], centre[1]) for zone in enemy_zones):
                continue
            out.append(objective)
        return out

    def target_in_trap_range(self, player, target_squad):
        """"an enemy unit within range of your Trap objective marker"."""
        trap = self.trap_for(player)
        if trap is None or target_squad is None:
            return False
        return objectives_module.is_within_range_of_objective(target_squad, [trap])

    def wound_bonus_applies(self, attacking_squad, target_squad):
        """The whole EFFECT condition, asked from the wound step."""
        if attacking_squad is None or not is_active(attacking_squad):
            return False
        return self.target_in_trap_range(attacking_squad.owner, target_squad)

    # -- the Stratagem ----------------------------------------------------
    def panel_label(self, squad):
        trap = self.trap_for(squad.owner)
        where = trap.name if trap is not None else "pick a Trap objective"
        return f"{TEMPTING_TRAP_NAME} ({TEMPTING_TRAP_CP} CP) - +1 Wound near {where}"

    def can_use(self, squad):
        if squad is None or self.shooting_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if getattr(self.turn_tracker, "battle_round", 0) < TEMPTING_TRAP_EARLIEST_ROUND:
            return False
        if is_active(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, kauyon.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        if self.shooting_controller.active_squad is squad:
            return False
        if not self.shooting_controller.can_shoot(squad):
            return False
        # On first use the objective MUST be selectable, or the Stratagem
        # cannot be paid for in full - never offer what cannot be completed.
        if self.trap_for(squad.owner) is None and not self.candidate_objectives(squad.owner):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.tempting_trap_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{TEMPTING_TRAP_NAME}: {squad.name} adds 1 to Wound rolls against "
                    "enemy units near the Trap objective this phase."
                )
        if self.trap_for(player) is not None:
            return
        candidates = self.candidate_objectives(player)
        if not candidates:
            return
        if len(candidates) == 1 or self.decision_manager is None:
            self.set_trap(player, candidates[0])
            return
        self.decision_manager.request(
            player,
            f"{TEMPTING_TRAP_NAME}: which objective marker becomes your Trap objective "
            "for the rest of the battle?",
            [(objective.name, (lambda o=objective: self.set_trap(player, o)))
             for objective in candidates],
        )

    def set_trap(self, player, objective):
        self._traps[player] = objective
        if self.game_log is not None:
            self.game_log.add(
                f"{TEMPTING_TRAP_NAME}: {objective.name} is {player}'s Trap objective "
                "for the rest of the battle."
            )
        return True
