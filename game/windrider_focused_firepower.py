"""Windrider Host Stratagem: Focused Firepower (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  WHEN:   Your Shooting phase.
  TARGET: One ASURYANI MOUNTED or VYPER unit from your army that has not been
          selected to shoot this phase.
  EFFECT: Until the end of the phase, each time a model in your unit makes an
          attack, improve the Armour Penetration characteristic of that attack
          by 1.
  RESTRICTIONS: none printed.

"IMPROVE THE AP BY 1" IS ap - 1, NOT ap + 1. AP is printed as a negative
number, so improving it makes it MORE negative - the same arithmetic
game/crit_ap.py, Crystalline Targeting and Experimental Modifications all
write out, and the one line in this module that would still pass a "the AP
changed" test while doing the exact opposite of the printed text.

IT RIDES THE ADJUSTER CHAIN, ON A COPY. ShootingController._adjusted_weapon()
is where a per-attack characteristic change belongs, because the Save roll
reads the AP off the weapon this chain returns - anywhere else and the
modified value would never reach the roll it is meant to change. And a
WeaponProfile CLASS is shared by every model in the game carrying that gun, so
the copy is not tidiness: writing through would improve the AP of every
shuriken cannon on the table, permanently.

SHOOTING ONLY, and that is the WHEN clause rather than a simplification. The
grant lasts "until the end of the phase" and can only be bought in your
Shooting phase, so no melee attack can ever fall inside its lifetime. Checked
as negative space in the test - game/fight.py never importing this module is a
stronger statement than a melee scene that happens to come out unchanged.

WIDER THAN ITS SIBLING. Death from on High also improves this unit's attacks,
but needs a unit that arrived from Reserves this turn where this one needs
only that it has not shot yet - so this is the one that pays on an ordinary
turn, and the two keep separate eligibility for that reason.

THE AI DECLINES (standing Aeldari instruction).
"""
import copy

from game import ride_the_wind
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

FOCUSED_FIREPOWER_NAME = "Focused Firepower"
FOCUSED_FIREPOWER_CP = 1

#: "improve the Armour Penetration characteristic of that attack by 1".
FOCUSED_FIREPOWER_AP_BONUS = 1


def is_active(squad):
    return bool(getattr(squad, "focused_firepower_active", False))


def eligible_unit(squad):
    """"One ASURYANI MOUNTED or VYPER unit from your army" - the detachment
    rule's own set, asked of the module that owns it."""
    if squad is None or not ride_the_wind.has_detachment(getattr(squad, "owner", None)):
        return False
    return ride_the_wind.applies(squad)


def adjusted_weapon(weapon, squad):
    """AP improved by 1 while the grant is up. A COPY, never the shared
    instance."""
    if weapon is None or not is_active(squad):
        return weapon
    improved = copy.copy(weapon)
    improved.ap = weapon.ap - FOCUSED_FIREPOWER_AP_BONUS
    return improved


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.focused_firepower_active = False


class FocusedFirepowerController:
    """A Shooting-phase panel button."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=FOCUSED_FIREPOWER_NAME, cp_cost=FOCUSED_FIREPOWER_CP,
            effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - improve this unit's AP by %d this phase"
                % (FOCUSED_FIREPOWER_NAME, FOCUSED_FIREPOWER_CP,
                   FOCUSED_FIREPOWER_AP_BONUS))

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False               # "YOUR Shooting phase"
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        if self.shooting_controller is not None \
                and self.shooting_controller.active_squad is squad:
            return False               # "has not been selected to shoot"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.focused_firepower_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s improves the Armour Penetration of its attacks by %d "
                    "this phase."
                    % (FOCUSED_FIREPOWER_NAME, squad.name,
                       FOCUSED_FIREPOWER_AP_BONUS))
