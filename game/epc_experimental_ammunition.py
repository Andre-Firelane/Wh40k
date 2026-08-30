"""Experimental Prototype Cadre Stratagem: Experimental Ammunition (1CP).

RULE (verbatim, rules/tau_empire/detachments/Experimental Prototype Cadre.md):
  WHEN:   Your Shooting phase, when a friendly BATTLESUIT CHARACTER unit is
          selected to shoot.
  TARGET: That BATTLESUIT CHARACTER unit.
  EFFECT: Your unit's ranged attacks have:
            - +1 S.
            - OR: +1 S, AP and [HAZARDOUS].

TWO MODES, TWO BUTTONS - NOT A PROMPT
--------------------------------------
"OR" makes this a genuine choice with a real trade-off, unlike the
"ignore any or all modifiers" clauses that this codebase resolves
automatically: [HAZARDOUS] (24.15) can kill the bearer, so the richer option is
not strictly better and the player must decide. It is offered as TWO panel
buttons rather than a button plus a follow-up prompt, for the reason
game/unmodified_six_controller.py records about Command Re-roll: a decision the
player can read off the label costs one click, and an extra modal costs two.

Both buttons are the same Stratagem for rule 15.01 - one Stratagem object, so
buying either uses up the once-per-phase allowance.
"""

import copy

from game import experimental_prototype_cadre as epc, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

EXPERIMENTAL_AMMUNITION_CP = 1
EXPERIMENTAL_AMMUNITION_NAME = "Experimental Ammunition"

# The two printed modes, as the value stored on the squad.
MODE_STRENGTH = "strength"
MODE_STRENGTH_AP_HAZARDOUS = "strength_ap_hazardous"


def active_mode(squad):
    return getattr(squad, "experimental_ammunition_mode", None)


def adjusted_weapon(weapon, squad):
    """The grant, as a copy - the shared WeaponProfile is never mutated."""
    mode = active_mode(squad)
    if weapon is None or mode is None or weapon.weapon_type != RANGED:
        return weapon
    granted = copy.copy(weapon)
    granted.strength = weapon.strength + 1
    if mode == MODE_STRENGTH_AP_HAZARDOUS:
        # AP is stored negative (save_threshold += -weapon.ap), so "+1 AP"
        # means MORE negative - the same arithmetic Bonded Heroes documents.
        granted.ap = weapon.ap - 1
        granted.hazardous = True
    return granted


class ExperimentalAmmunitionController:
    """One controller, two panel buttons - one per printed mode."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None, mode=MODE_STRENGTH):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.mode = mode
        self._stratagem = Stratagem(
            name=EXPERIMENTAL_AMMUNITION_NAME, cp_cost=EXPERIMENTAL_AMMUNITION_CP,
            effect=self._grant,
        )

    def reset_phase(self, squads=()):
        """"Your unit's ranged attacks have..." with no stated duration, in a
        Stratagem whose WHEN is one activation - so it lasts the phase, like
        every other grant of this shape here."""
        for squad in squads or ():
            squad.experimental_ammunition_mode = None

    def panel_label(self, squad):
        if self.mode == MODE_STRENGTH_AP_HAZARDOUS:
            return (f"{EXPERIMENTAL_AMMUNITION_NAME} ({EXPERIMENTAL_AMMUNITION_CP} CP) - "
                    "+1 S, +1 AP, [HAZARDOUS]")
        return f"{EXPERIMENTAL_AMMUNITION_NAME} ({EXPERIMENTAL_AMMUNITION_CP} CP) - +1 S"

    def can_use(self, squad):
        if squad is None or self.shooting_controller is None:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        if active_mode(squad) is not None:
            return False   # already up on this unit - nothing left to buy
        if not tau_detachments.has_detachment(squad.owner, epc.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        if not epc.is_battlesuit_character_unit(squad):
            return False
        # "when a unit is SELECTED TO SHOOT" - the same reading, and the same
        # two checks, game/arrokon_protocol.py uses: a unit mid-activation has
        # already been selected, and only lands in shot_squad_ids at its end.
        if self.shooting_controller.active_squad is squad:
            return False
        if not self.shooting_controller.can_shoot(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.experimental_ammunition_mode = self.mode
            if self.game_log is not None:
                self.game_log.add(
                    f"{EXPERIMENTAL_AMMUNITION_NAME}: {squad.name}'s ranged attacks have "
                    + ("+1 Strength, +1 AP and [HAZARDOUS] this phase."
                       if self.mode == MODE_STRENGTH_AP_HAZARDOUS
                       else "+1 Strength this phase.")
                )
