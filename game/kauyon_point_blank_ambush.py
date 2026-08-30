"""Kauyon Stratagem: Point-Blank Ambush (1CP).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  WHEN:   Your Shooting phase.
  TARGET: One T'AU EMPIRE unit from your army that has not been selected to
          shoot this phase.
  EFFECT: Until the end of the phase, each time a model in your unit makes a
          ranged attack that targets an enemy unit within 9", improve the
          Armour Penetration characteristic of that attack by 1.
  RESTRICTIONS: You cannot use this Stratagem during the first or second battle
          rounds.

THE 9" IS PER TARGET, NOT PER PURCHASE
---------------------------------------
"each time a model makes a ranged attack that targets an enemy unit within 9""
is a property of the ATTACK, so it is measured in the weapon chain against the
target in hand - the same unit gets the bonus against a near target and not
against a far one in the same phase. Bonded Heroes' own AP half is measured
exactly this way, and this reuses that reading rather than inventing a second.

THE ROUND RESTRICTION IS THE MIRROR OF THE DETACHMENT RULE
-----------------------------------------------------------
"not during the first or second battle rounds" is rounds 3+, which is where
Kauyon's Patient Hunter switches on too. It is written as its own constant
rather than reusing game/kauyon.py's window, because the two are not the same
set - Patient Hunter stops after round 5 and this does not.
"""

import copy

from game import kauyon, tau_detachments
from game.squad import edge_distance
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

POINT_BLANK_AMBUSH_CP = 1
POINT_BLANK_AMBUSH_NAME = "Point-Blank Ambush"
POINT_BLANK_RANGE_IN = 9.0
# "You cannot use this Stratagem during the first or second battle rounds."
POINT_BLANK_EARLIEST_ROUND = 3


def is_active(squad):
    return bool(getattr(squad, "point_blank_ambush_active", False))


def adjusted_weapon(weapon, squad, pairs, target_squad):
    """+1 AP against a target within 9" of the shooter."""
    if weapon is None or not is_active(squad):
        return weapon
    if weapon.weapon_type != RANGED or target_squad is None:
        return weapon
    if not any(edge_distance(shooter, defender) <= POINT_BLANK_RANGE_IN
               for shooter, _w in (pairs or ())
               for defender in target_squad.models):
        return weapon
    granted = copy.copy(weapon)
    # AP is stored negative, so "improve by 1" is one MORE negative.
    granted.ap = weapon.ap - 1
    return granted


class PointBlankAmbushController:
    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=POINT_BLANK_AMBUSH_NAME, cp_cost=POINT_BLANK_AMBUSH_CP, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.point_blank_ambush_active = False

    def panel_label(self, squad):
        return (f"{POINT_BLANK_AMBUSH_NAME} ({POINT_BLANK_AMBUSH_CP} CP) - "
                f'+1 AP vs targets within {POINT_BLANK_RANGE_IN:g}"')

    def can_use(self, squad):
        if squad is None or self.shooting_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if getattr(self.turn_tracker, "battle_round", 0) < POINT_BLANK_EARLIEST_ROUND:
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
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.point_blank_ambush_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{POINT_BLANK_AMBUSH_NAME}: {squad.name}'s ranged attacks have +1 AP "
                    f'against targets within {POINT_BLANK_RANGE_IN:g}" this phase.'
                )
