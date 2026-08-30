"""Auxiliary Cadre Stratagem: Guided Fire (1CP).

RULE (verbatim, rules/tau_empire/detachments/Auxiliary Cadre.md):
  WHEN:   Your Shooting phase, when a friendly T'AU EMPIRE unit (excluding
          KROOT/VESPID STINGWINGS units) is selected to shoot.
  TARGET: That T'AU EMPIRE unit.
  EFFECT: Your unit's ranged attacks that target a unit within 9" of a friendly
          KROOT/VESPID STINGWINGS unit have [LETHAL HITS].

THE EXCLUSION IS THE POINT OF THE STRATAGEM
--------------------------------------------
"excluding KROOT/VESPID STINGWINGS units" means the Kroot cannot buy this for
themselves - they are the spotters, not the shooters. Written as its own check
rather than folded into the T'AU EMPIRE test, because the two are different
questions and one of them is this Stratagem's whole flavour.

THE 9" IS MEASURED AT RESOLUTION, NOT AT PURCHASE
--------------------------------------------------
It is a property of the TARGET ("attacks that target a unit within 9" of a
friendly KROOT unit"), so it is checked per target in the weapon chain, not
once when the CP is spent. A unit that buys this and then shoots something with
no Kroot near it simply gets nothing, which is what the text says.

[LETHAL HITS] MUST BE GRANTED IN THE WEAPON CHAIN, not at the wound step:
_crit_note() reads the keyword at ROLL time to label a critical die.
"""

import copy

from game import auxiliary_cadre, tau_detachments
from game.squad import edge_distance
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

GUIDED_FIRE_CP = 1
GUIDED_FIRE_NAME = "Guided Fire"
GUIDED_FIRE_RANGE_IN = 9.0


def is_active(squad):
    return bool(getattr(squad, "guided_fire_active", False))


def _alive(squad):
    return [m for m in getattr(squad, "models", None) or () if not m.is_dead()]


def target_is_marked(target_squad, all_squads, owner):
    """"a unit within 9" of a friendly KROOT/VESPID STINGWINGS unit" -
    friendly to the SHOOTER, so the owner is passed in rather than read off the
    target (whose owner is the other player)."""
    if target_squad is None:
        return False
    defenders = _alive(target_squad)
    if not defenders:
        return False
    for other in all_squads or ():
        if getattr(other, "owner", None) != owner:
            continue
        if not auxiliary_cadre.is_harnessed_unit(other):
            continue
        if any(edge_distance(a, b) <= GUIDED_FIRE_RANGE_IN
               for a in _alive(other) for b in defenders):
            return True
    return False


def adjusted_weapon(weapon, squad, target_squad, all_squads=()):
    """[LETHAL HITS] on this unit's ranged attacks against a marked target."""
    if weapon is None or not is_active(squad):
        return weapon
    if weapon.weapon_type != RANGED or weapon.lethal_hits:
        return weapon
    if not target_is_marked(target_squad, all_squads, getattr(squad, "owner", None)):
        return weapon
    granted = copy.copy(weapon)
    granted.lethal_hits = True
    return granted


class GuidedFireController:
    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=GUIDED_FIRE_NAME, cp_cost=GUIDED_FIRE_CP, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.guided_fire_active = False

    def panel_label(self, squad):
        return (f"{GUIDED_FIRE_NAME} ({GUIDED_FIRE_CP} CP) - "
                f'[LETHAL HITS] vs targets within {GUIDED_FIRE_RANGE_IN:g}" of your Kroot')

    def can_use(self, squad):
        if squad is None or self.shooting_controller is None:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        if is_active(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, auxiliary_cadre.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        # "EXCLUDING KROOT/VESPID STINGWINGS units" - they are the spotters.
        if auxiliary_cadre.is_harnessed_unit(squad):
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
            squad.guided_fire_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{GUIDED_FIRE_NAME}: {squad.name}'s ranged attacks have [LETHAL HITS] "
                    f'against targets within {GUIDED_FIRE_RANGE_IN:g}" of a friendly '
                    "KROOT/VESPID STINGWINGS unit this phase."
                )
