"""Canoptek Court Stratagem: Solar Pulse (1CP).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  WHEN:   Start of your Shooting phase.
  TARGET: One CRYPTEK model from your army.
  EFFECT: Select one objective marker within 18" of your CRYPTEK model. Until the
          end of the phase, weapons equipped by friendly NECRONS models have the
          [IGNORES COVER] ability while targeting units within range of that
          objective marker.

[IGNORES COVER] HAS ONE READER, and it is ShootingController._cover_ignored_for_
group() - both the hit-modifier fold and the cover split go through it. So the
grant is a term there, asked with the target in hand, rather than a keyword copied
onto every NECRONS weapon of the army: "while targeting units within range of that
objective marker" is a property of the ATTACK, which a copied weapon cannot carry.

TWO STEPS, AND THE CP IS SPENT AT THE SECOND. The panel button names the unit that
holds the CRYPTEK model; the objective is picked from a list (objectives are not
units, so it is not a board pick) - game/aac_marker_beacon.py's arrangement. A
unit whose Crypteks have no objective within 18" gets no button: there is nothing
to select.

"WITHIN 18" OF YOUR CRYPTEK MODEL" is measured with objectives.
model_is_within_range_of_objective(), the per-MODEL granularity of the same
distance the objective rules use. With two Crypteks in one unit, any of them will do.

ONCE PER PHASE PER PLAYER, by rule 15.01, and the chosen objective is held per
player until the phase ends.

THE AI (ai/agent_driver.py) picks the objective with the most enemy units in range
standing in terrain - the units the grant takes cover away from - and buys it only
when that count is at least one.
"""

from game import ai_mode, necron_detachments, objectives as objectives_module
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

SOLAR_PULSE_NAME = "Solar Pulse"
SOLAR_PULSE_CP = 1
SOLAR_PULSE_RANGE_IN = 18.0
SETTING = "CANOPTEK_COURT_PLAYERS"


def objective_value(objective, player, game_state):
    """How many enemy units within range of `objective` stand in terrain - the
    units [IGNORES COVER] would actually help against. The AI's ranking key."""
    if objective is None or game_state is None:
        return 0
    areas = list(getattr(game_state, "terrain_areas", ()) or ())
    seen, count = set(), 0
    for token in getattr(game_state, "tokens", ()) or ():
        squad = getattr(token, "squad", None)
        if squad is None or squad.owner == player or id(squad) in seen:
            continue
        seen.add(id(squad))
        living = [m for m in squad.models if not m.is_dead()]
        if not living or not objectives_module.is_within_range_of_objective(squad, [objective]):
            continue
        if any(area.overlaps_model(m) for area in areas for m in living):
            count += 1
    return count


class SolarPulseController:
    def __init__(self, stratagem_controller, turn_tracker=None, shooting_controller=None,
                 game_state=None, decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.shooting_controller = shooting_controller
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._pulsed = {}      # player -> the objective selected this phase
        self._pending = None   # (squad, objective) for the purchase in flight
        self._stratagem = Stratagem(name=SOLAR_PULSE_NAME, cp_cost=SOLAR_PULSE_CP,
                                    effect=self._effect)

    # ------------------------------------------------------------- reading
    def pulsed_objective(self, player):
        return self._pulsed.get(player)

    def ignores_cover(self, shooting_squad, target_squad):
        """Read by ShootingController._cover_ignored_for_group()."""
        if shooting_squad is None or target_squad is None:
            return False
        objective = self._pulsed.get(shooting_squad.owner)
        if objective is None:
            return False
        if not necron_detachments.is_necrons_unit(shooting_squad):
            return False
        return objectives_module.is_within_range_of_objective(target_squad, [objective])

    def reset_phase(self):
        """"Until the end of the phase"."""
        self._pulsed.clear()

    # ------------------------------------------------------------ candidates
    def cryptek_models(self, squad):
        return [m for m in getattr(squad, "models", ()) or ()
                if not m.is_dead() and necron_detachments.model_is_cryptek(squad, m)]

    def objectives_for(self, squad):
        crypteks = self.cryptek_models(squad)
        out = []
        for objective in getattr(self.game_state, "objectives", ()) or ():
            if any(objectives_module.model_is_within_range_of_objective(
                    m, objective, SOLAR_PULSE_RANGE_IN) for m in crypteks):
                out.append(objective)
        return out

    # -------------------------------------------------------------- the button
    def panel_label(self, squad):
        return (f"{SOLAR_PULSE_NAME} ({SOLAR_PULSE_CP} CP) - [IGNORES COVER] against units "
                "on one objective this phase")

    def can_use(self, squad):
        tt = self.turn_tracker
        if squad is None or tt is None or self.stratagem_controller is None:
            return False
        if tt.phase != PHASE_SHOOTING or tt.turn_owner != squad.owner:
            return False
        sc = self.shooting_controller
        if sc is None or sc.active_squad is not None or sc.shot_squad_ids:
            return False       # "START of your Shooting phase"
        if not necron_detachments.has_detachment(squad.owner, SETTING):
            return False
        if squad.owner in self._pulsed:
            return False
        if not self.cryptek_models(squad):
            return False
        if not self.objectives_for(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad, objective=None):
        """Opens the objective choice; the CP is spent once one is picked. An
        `objective` given up front (the AI) skips the prompt."""
        if not self.can_use(squad):
            return False
        candidates = self.objectives_for(squad)
        if objective is not None:
            return objective in candidates and self._commit(squad, objective)
        if self.decision_manager is None or squad.owner in self.auto_players:
            best = max(candidates, key=lambda o: (objective_value(o, squad.owner, self.game_state), o.name))
            return self._commit(squad, best)
        self.decision_manager.request(
            squad.owner,
            f"{SOLAR_PULSE_NAME}: which objective within {SOLAR_PULSE_RANGE_IN:g}\" of "
            f"{squad.name}'s CRYPTEK?",
            [(o.name, (lambda o=o: self._commit(squad, o))) for o in candidates]
            + [("Cancel", lambda: None)],
            is_stratagem=True,
        )
        return True

    def _commit(self, squad, objective):
        self._pending = (squad, objective)
        used = self.stratagem_controller.use(squad.owner, self._stratagem, [squad])
        if not used:
            self._pending = None
        return used

    def _effect(self, controller, player, targets):
        pending, self._pending = self._pending, None
        if pending is None:
            return
        _squad, objective = pending
        self._pulsed[player] = objective
        if self.game_log is not None:
            self.game_log.add(
                f"{SOLAR_PULSE_NAME}: until the end of the phase, {player}'s NECRONS weapons "
                f"have [IGNORES COVER] against units within range of {objective.name}.")
