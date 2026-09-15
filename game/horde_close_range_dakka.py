"""War Horde Stratagem: Close-Range Dakka (1CP).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  WHEN:   Your Shooting phase, when a friendly ORKS unit is selected to shoot.
  TARGET: That ORKS unit.
  EFFECT: Your unit's ranged attacks have:
          - [Rapid Fire 1].
          - Or: If that attack already has [RAPID FIRE], +1 to the value of
            that [RAPID FIRE] (e.g. [RAPID FIRE 1] becomes [RAPID FIRE 2]).

ONE FORMULA FOR BOTH BULLETS: rapid_fire + 1 - a weapon without the keyword has
0, so it becomes [RAPID FIRE 1].

A KEYWORD GRANT WHOSE READER IS THE EXTRA-DICE STEP. [RAPID FIRE X] adds X dice
per attacking model inside half range (rule 24.30), counted by
extra_attack_dice(), which reads the ADJUSTED weapon (wiring guard section 27).

"Selected to shoot" is read as Experimental Modifications reads it: the unit
may still shoot and is not mid-activation.

THE AI (ai/agent_driver.py's _handle_close_range_dakka()) buys it when
expected_extra_dice() below reaches CLOSE_RANGE_DAKKA_MIN_EXTRA_DICE: one die per
ranged weapon of a living model with an enemy model inside that weapon's half
range.
"""

import copy

from game import war_horde
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

CLOSE_RANGE_DAKKA_NAME = "Close-Range Dakka"
CLOSE_RANGE_DAKKA_CP = 1
#: "[Rapid Fire 1]" / "+1 to the value of that [RAPID FIRE]".
CLOSE_RANGE_DAKKA_RAPID_FIRE = 1
#: The AI's rule.
CLOSE_RANGE_DAKKA_MIN_EXTRA_DICE = 4


def is_active(squad):
    return bool(getattr(squad, "close_range_dakka_active", False))


def adjusted_weapon(weapon, squad):
    if weapon is None or not is_active(squad):
        return weapon
    if getattr(weapon, "weapon_type", None) != RANGED:
        return weapon
    granted = copy.copy(weapon)
    granted.rapid_fire = (weapon.rapid_fire or 0) + CLOSE_RANGE_DAKKA_RAPID_FIRE
    return granted


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "close_range_dakka_active", False):
            squad.close_range_dakka_active = False


def has_ranged_weapons(squad):
    return any(getattr(w, "weapon_type", None) == RANGED
               for m in getattr(squad, "models", ()) or () if not m.is_dead()
               for w in m.weapons)


def expected_extra_dice(squad, enemy_models):
    """Dice the grant adds if the unit shot now: one per ranged weapon of a
    living model with a living enemy model inside that weapon's half range -
    counting, per model, only the weapons it could fire TOGETHER.

    Rule 24.07: a model that is not a MONSTER or VEHICLE fires either its
    [CLOSE-QUARTERS] weapons or its others, never both. The 2026-09 codex
    Boy carries a Shoota AND a close-quarters Slugga, and summing both counted
    nearly two dice per Boy where he can add one."""
    from game import weapon_range
    from game.shooting import is_close_quarters
    from game.squad import edge_distance
    enemies = [m for m in enemy_models or () if not m.is_dead()]
    if squad is None or not enemies:
        return 0
    extra = 0
    for model in squad.models:
        if model.is_dead():
            continue
        sides = {True: 0, False: 0}
        for weapon in model.weapons:
            if getattr(weapon, "weapon_type", None) != RANGED:
                continue
            half = weapon_range.half_range_in(model, weapon)
            if any(edge_distance(model, enemy) <= half for enemy in enemies):
                sides[bool(is_close_quarters(weapon, squad))] += CLOSE_RANGE_DAKKA_RAPID_FIRE
        if model.profile.monster or model.profile.vehicle:
            extra += sides[True] + sides[False]
        else:
            extra += max(sides.values())
    return extra


class CloseRangeDakkaController:
    """A panel button (game/proactive_stratagems.py): can_use / use / panel_label."""

    def __init__(self, stratagem_controller, turn_tracker=None, shooting_controller=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.shooting_controller = shooting_controller
        self.game_log = game_log
        self._stratagem = Stratagem(CLOSE_RANGE_DAKKA_NAME, CLOSE_RANGE_DAKKA_CP, self._grant)

    def panel_label(self, squad):
        return f"{CLOSE_RANGE_DAKKA_NAME} ({CLOSE_RANGE_DAKKA_CP} CP) - [RAPID FIRE] +1 on ranged attacks"

    def reset_phase(self, squads=()):
        reset_phase(squads)

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None or self.shooting_controller is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.turn_owner:
            return False
        if is_active(squad):
            return False
        if not war_horde.fields_war_horde(squad.owner) or not war_horde.is_orks_unit(squad):
            return False
        if not has_ranged_weapons(squad):
            return False
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
            squad.close_range_dakka_active = True
            if self.game_log is not None:
                self.game_log.add(f"{CLOSE_RANGE_DAKKA_NAME}: {squad.name}'s ranged attacks have "
                                  "[RAPID FIRE] +1 this phase.")
        return True
