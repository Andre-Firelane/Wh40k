"""Auxiliary Cadre Stratagem: Experimental Modifications (1CP).

RULE (verbatim, rules/tau_empire/detachments/Auxiliary Cadre.md):
  WHEN:   Your Shooting phase or the Fight phase, when a friendly KROOT/VESPID
          STINGWINGS unit is selected to attack.
  TARGET: That KROOT/VESPID STINGWINGS unit.
  EFFECT: Your unit's attacks have +1 AP.

BOTH PHASES, AND THAT IS THE POINT
-----------------------------------
"Your Shooting phase OR the Fight phase" and "attacks", not "ranged attacks" -
so this is wired into BOTH _adjusted_weapon() chains, and the melee half is not
an afterthought. Note also "the Fight phase" without "your": the Fight phase
belongs to both players, so a Kroot unit fighting in the opponent's turn is
still covered. That asymmetry is printed, and can_use() reads it that way
rather than requiring the active player in both phases.
"""

import copy

from game import auxiliary_cadre, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

EXPERIMENTAL_MODIFICATIONS_CP = 1
EXPERIMENTAL_MODIFICATIONS_NAME = "Experimental Modifications"


def is_active(squad):
    return bool(getattr(squad, "experimental_modifications_active", False))


def adjusted_weapon(weapon, squad):
    """+1 AP on this unit's attacks, ranged or melee, while the grant is up."""
    if weapon is None or not is_active(squad):
        return weapon
    granted = copy.copy(weapon)
    # AP is stored negative, so "+1 AP" is one MORE negative.
    granted.ap = weapon.ap - 1
    return granted


class ExperimentalModificationsController:
    def __init__(self, stratagem_controller, shooting_controller=None,
                 fight_controller=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=EXPERIMENTAL_MODIFICATIONS_NAME, cp_cost=EXPERIMENTAL_MODIFICATIONS_CP,
            effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.experimental_modifications_active = False

    def panel_label(self, squad):
        return (f"{EXPERIMENTAL_MODIFICATIONS_NAME} "
                f"({EXPERIMENTAL_MODIFICATIONS_CP} CP) - +1 AP on this unit's attacks")

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        phase = self.turn_tracker.phase
        if phase not in (PHASE_SHOOTING, PHASE_FIGHT):
            return False
        # "YOUR Shooting phase" but "THE Fight phase" - the Fight phase is not
        # anyone's, so the owner check applies to shooting alone.
        if phase == PHASE_SHOOTING and squad.owner != self.turn_tracker.active_player:
            return False
        if is_active(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, auxiliary_cadre.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        if not auxiliary_cadre.is_harnessed_unit(squad):
            return False
        if phase == PHASE_SHOOTING:
            if self.shooting_controller is None:
                return False
            if self.shooting_controller.active_squad is squad:
                return False
            if not self.shooting_controller.can_shoot(squad):
                return False
        else:
            # "selected to attack" in the Fight phase: the unit must still have
            # a fight coming. fought_squad_ids is the Fight-phase twin of
            # shot_squad_ids.
            if self.fight_controller is None:
                return False
            if squad in getattr(self.fight_controller, "fought_squad_ids", ()):
                return False
            if not self.fight_controller.is_eligible_to_fight(squad):
                return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.experimental_modifications_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{EXPERIMENTAL_MODIFICATIONS_NAME}: {squad.name}'s attacks have "
                    "+1 Armour Penetration this phase."
                )
