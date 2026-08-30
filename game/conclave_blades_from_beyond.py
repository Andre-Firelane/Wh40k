"""Spirit Conclave Stratagem: Blades from Beyond (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  WHEN:   Fight phase.
  TARGET: One WRAITHBLADES, WRAITHLORD or WRAITHKNIGHT unit from your army that
          has not been selected to fight this phase.
  EFFECT: Until the end of the phase, melee weapons equipped by models in your
          unit have the [DEVASTATING WOUNDS] ability.
  RESTRICTIONS: none printed.

"FIGHT PHASE", WITH NO "YOUR" - the shortest WHEN in the whole detachment, and
the one that decides the most. The Fight phase belongs to nobody, so this can
be bought in the opponent's turn by a unit about to swing back. Its own test
line, because every OTHER phase-named Stratagem in this batch has an owner
check and the missing word is easy to read past.

A KEYWORD GRANT, so it goes in FightController._adjusted_weapon()'s chain and
nowhere else: _crit_note() reads the returned weapon at ROLL time to label a
critical die, so a grant applied at the wound step would be invisible to the
one thing that has to see it.

NEVER A DOWNGRADE, and never a mutation. A weapon that already prints
[DEVASTATING WOUNDS] is returned untouched, and the flag is set on a
copy.copy() - a WeaponProfile CLASS is shared by every model in the game
carrying that weapon, so writing through would hand the ability to every
wraithblade sword on the table, permanently.

MELEE ONLY, and that is the printed wording rather than a consequence of the
phase: "melee weapons equipped by models in your unit". A [PISTOL] fired in the
Fight phase would not gain it. game/shooting.py never imports this module,
checked as negative space.

THREE NAMED DATASHEETS, NOT THE WRAITH CONSTRUCT KEYWORD - and the difference
bites: WRAITHGUARD carry that keyword and are NOT on this list, which is
consistent with the card (they are the gun unit; their guns are ranged). Read
at the three names, with the Wraithguard as an explicit negative case.

WRAITHKNIGHT IS A MEASURED NO-OP for now: the datasheet exists in the corpus
but is not built here (it is TITANIC, deliberately out of scope). Named in the
keyword list anyway so building it later costs nothing.

THE AI DECLINES (standing Aeldari instruction).
"""
import copy

from game import aeldari_detachments, shepherds_of_the_dead
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT
from game.weapons import RANGED

BLADES_FROM_BEYOND_NAME = "Blades from Beyond"
BLADES_FROM_BEYOND_CP = 1

#: The three named datasheets - NOT the WRAITH CONSTRUCT keyword, which would
#: also catch the Wraithguard.
BLADES_FROM_BEYOND_KEYWORDS = ("WRAITHBLADES", "WRAITHLORD", "WRAITHKNIGHT")

SETTING = shepherds_of_the_dead.SETTING


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def is_active(squad):
    return bool(getattr(squad, "blades_from_beyond_active", False))


def eligible_unit(squad):
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k)
               for k in BLADES_FROM_BEYOND_KEYWORDS)


def adjusted_weapon(weapon, squad):
    """[DEVASTATING WOUNDS] on this unit's melee weapons while the grant is
    up. A COPY, never the shared instance, and never a downgrade."""
    if weapon is None or not is_active(squad):
        return weapon
    if getattr(weapon, "weapon_type", None) == RANGED:
        return weapon              # "MELEE weapons", as printed
    if weapon.devastating_wounds:
        return weapon              # already has it - granting is not stacking
    granted = copy.copy(weapon)
    granted.devastating_wounds = True
    return granted


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.blades_from_beyond_active = False


class BladesFromBeyondController:
    """A Fight-phase panel button."""

    def __init__(self, stratagem_controller, fight_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=BLADES_FROM_BEYOND_NAME, cp_cost=BLADES_FROM_BEYOND_CP,
            effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - melee weapons gain [DEVASTATING WOUNDS]"
                % (BLADES_FROM_BEYOND_NAME, BLADES_FROM_BEYOND_CP))

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        # "FIGHT PHASE" - no "your", so no owner check at all. The one
        # Stratagem here that can be bought in the opponent's turn.
        if self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        if self.fight_controller is not None \
                and getattr(self.fight_controller, "fighting_squad", None) is squad:
            return False               # "has not been selected to fight"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.blades_from_beyond_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s's melee weapons have [DEVASTATING WOUNDS] this phase."
                    % (BLADES_FROM_BEYOND_NAME, squad.name))
