"""War Horde Stratagem: Mow 'Em Down (1CP).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  WHEN:   Fight phase, when a friendly ORKS VEHICLE unit (excluding WALKER
          units) that made a charge move this turn is selected to fight.
  TARGET: That ORKS VEHICLE unit.
  EFFECT: Your unit's melee attacks have:
          - [Cleave 1].
          - Or: If that attack already has [CLEAVE], +1 to the value of that
            [CLEAVE] (e.g. [CLEAVE 1] becomes [CLEAVE 2]).

ONE FORMULA FOR BOTH BULLETS: a weapon without [CLEAVE] has cleave 0, so
"cleave + 1" is [CLEAVE 1] for it and +1 for one that already has it.

A KEYWORD GRANT WHOSE READER IS THE EXTRA-DICE STEP. [CLEAVE] adds attack dice
per five models in the target (rule 24.06), counted by extra_attack_dice() -
which reads the ADJUSTED weapon since this detachment's stage (wiring guard
section 27). A grant that only reached the damage chain would roll no extra die.

"MADE A CHARGE MOVE THIS TURN" is Squad.charged_this_turn (rule 11.04's own
flag). "Selected to fight" is read as Hit 'Em Harder reads it.

THE AI (ai/agent_driver.py's _handle_mow_em_down()) buys it when an engaged
enemy has at least MOW_EM_DOWN_MIN_TARGET_MODELS models - below five, [CLEAVE 1]
adds no die at all.
"""

import copy

from game import attached_units, war_horde
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT
from game.weapons import MELEE

MOW_EM_DOWN_NAME = "Mow 'Em Down"
MOW_EM_DOWN_CP = 1
#: "[Cleave 1]" / "+1 to the value of that [CLEAVE]".
MOW_EM_DOWN_CLEAVE = 1
#: Rule 24.06: one die per five models - the AI's floor.
MOW_EM_DOWN_MIN_TARGET_MODELS = 5


def is_active(squad):
    return bool(getattr(squad, "mow_em_down_active", False))


def is_eligible_vehicle(squad):
    """An ORKS VEHICLE unit that is not a WALKER (rule 19.03's pooled keywords)."""
    if squad is None or not war_horde.is_orks_unit(squad):
        return False
    if not attached_units.unit_has_keyword(squad, lambda m: getattr(m.profile, "vehicle", False)):
        return False
    return not attached_units.unit_has_keyword(squad, lambda m: getattr(m.profile, "walker", False))


def adjusted_weapon(weapon, squad):
    if weapon is None or not is_active(squad):
        return weapon
    if getattr(weapon, "weapon_type", None) != MELEE:
        return weapon
    granted = copy.copy(weapon)
    granted.cleave = (weapon.cleave or 0) + MOW_EM_DOWN_CLEAVE
    return granted


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "mow_em_down_active", False):
            squad.mow_em_down_active = False


class MowEmDownController:
    """A panel button (game/proactive_stratagems.py): can_use / use / panel_label."""

    def __init__(self, stratagem_controller, turn_tracker=None, fight_controller=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self.game_log = game_log
        self._stratagem = Stratagem(MOW_EM_DOWN_NAME, MOW_EM_DOWN_CP, self._grant)

    def panel_label(self, squad):
        return f"{MOW_EM_DOWN_NAME} ({MOW_EM_DOWN_CP} CP) - [CLEAVE] +1 on melee attacks"

    def reset_phase(self, squads=()):
        reset_phase(squads)

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None or self.fight_controller is None:
            return False
        if self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if is_active(squad):
            return False
        if not war_horde.fields_war_horde(squad.owner) or not is_eligible_vehicle(squad):
            return False
        if not getattr(squad, "charged_this_turn", False):
            return False
        fc = self.fight_controller
        if squad in getattr(fc, "fought_squad_ids", ()) or getattr(fc, "fighting_squad", None) is squad:
            return False
        if not fc.is_eligible_to_fight(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.mow_em_down_active = True
            if self.game_log is not None:
                self.game_log.add(f"{MOW_EM_DOWN_NAME}: {squad.name}'s melee attacks have "
                                  "[CLEAVE] +1 this phase.")
        return True
