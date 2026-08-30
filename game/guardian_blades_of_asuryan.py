"""Guardian Battlehost Stratagem: Blades of Asuryan (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  WHEN:   Your Shooting phase.
  TARGET: One DIRE AVENGERS or GUARDIANS unit from your army that has not been
          selected to shoot this phase.
  EFFECT: Until the end of the phase, ranged weapons equipped by models in your
          unit have the [PISTOL] ability.
  RESTRICTIONS: none printed.

A KEYWORD GRANT, so it goes in ShootingController._adjusted_weapon()'s chain
and nowhere else. That is not tidiness: _crit_note() reads the returned weapon
at ROLL time, and the [TORRENT] shortcut and on_dice_acknowledged() read it
too, so a grant applied at the wound step would be invisible to all three.

NEVER A DOWNGRADE, and NEVER a mutation: the weapon is copy.copy()'d before the
flag is set, because Token.weapons instances are per model but a WeaponProfile
CLASS is shared, and a rule that wrote through would change every model in the
game carrying that gun.

RANGED ONLY - the printed text says "ranged weapons", and [PISTOL] on a melee
weapon would be meaningless in a way that is easier to prevent here than to
notice later. Checked as negative space in the test: game/fight.py never
importing this module is stronger evidence than a melee scene that happens to
come out unchanged.

WHAT [PISTOL] BUYS is rule 24.30's permission to shoot while within Engagement
Range - which is why this is a Guardian Stratagem at all: a unit tied up in
combat on an objective can still shoot. The engine already reads
WeaponProfile.pistol for that, so this grants the flag and nothing else.
"""
import copy

from game import aeldari_detachments, defend_at_all_costs
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

BLADES_OF_ASURYAN_NAME = "Blades of Asuryan"
BLADES_OF_ASURYAN_CP = 1

BLADES_OF_ASURYAN_KEYWORDS = ("DIRE AVENGERS", "GUARDIANS")


def is_active(squad):
    return bool(getattr(squad, "blades_of_asuryan_active", False))


def eligible_unit(squad):
    if squad is None or not defend_at_all_costs.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k) for k in BLADES_OF_ASURYAN_KEYWORDS)


def adjusted_weapon(weapon, squad):
    """[PISTOL] on this unit's ranged weapons while the grant is up."""
    if weapon is None or not is_active(squad):
        return weapon
    if getattr(weapon, "weapon_type", None) != RANGED or weapon.pistol:
        return weapon
    granted = copy.copy(weapon)
    granted.pistol = True
    return granted


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.blades_of_asuryan_active = False


class BladesOfAsuryanController:
    """A Shooting-phase panel button."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=BLADES_OF_ASURYAN_NAME, cp_cost=BLADES_OF_ASURYAN_CP,
            effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - ranged weapons gain [PISTOL]"
                % (BLADES_OF_ASURYAN_NAME, BLADES_OF_ASURYAN_CP))

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
            squad.blades_of_asuryan_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s's ranged weapons have [PISTOL] this phase."
                    % (BLADES_OF_ASURYAN_NAME, squad.name))
