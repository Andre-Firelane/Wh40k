"""Death Lord's Chosen Stratagem: MORTARION'S TEACHINGS (1 CP, Strategic Ploy).

  WHEN: Your Shooting phase.
  TARGET: One TERMINATOR unit from your army that has not been selected to
        shoot this phase.
  EFFECT: Until the end of the phase, ranged weapons equipped by models in your
        unit have the [ASSAULT] and [HEAVY] abilities.

STRUCTURALLY Protocol of the Sudden Storm, with three printed differences:

  * TWO keywords, not one. [ASSAULT] (10.05) lets a unit that Advanced still
    shoot; [HEAVY] (24.16) gives +1 to Hit if the unit Remained Stationary.
    They are mutually exclusive in effect - a unit either moved or it did not -
    which is exactly what makes the Stratagem good: it pays whichever way the
    unit ends up being used.
  * "Until the end of the PHASE", where Sudden Storm's [ASSAULT] half runs to
    the end of the TURN. One clock, not two, so this expires with reset_phase()
    and has no expire_for_turn() at all.
  * "has not been selected to shoot this phase" - read off
    ShootingController.shot_squad_ids, the same ledger the other Stratagems'
    equivalent clauses use.

WORTH SAYING FOR THIS ROSTER: the only TERMINATOR units here are the two
Deathshroud squads and Typhus, and their sole ranged weapon is the plaguespurt
gauntlet, which is [TORRENT]. [TORRENT] skips the Hit roll entirely, so
[HEAVY]'s +1 to Hit buys those units NOTHING - the whole value here is the
[ASSAULT] half. That is measured rather than assumed in the AI verdict, which
is why the verdict asks "would this unit otherwise be unable to shoot" and not
"does it have guns".
"""
import copy

from game import death_lords_chosen
from game.stratagems import Stratagem
from game.weapons import RANGED

MORTARIONS_TEACHINGS_CP = 1
MORTARIONS_TEACHINGS_NAME = "Mortarion's Teachings"


def is_active(squad):
    return bool(getattr(squad, "mortarions_teachings_active", False))


def adjusted_weapon(weapon, squad):
    """[ASSAULT] and [HEAVY] on ranged weapons while the grant is up.

    A COPY, never the shared instance - the same care every other entry in the
    _adjusted_weapon() chain takes."""
    if weapon is None or not is_active(squad):
        return weapon
    if weapon.weapon_type != RANGED:
        return weapon
    if weapon.assault and weapon.heavy:
        return weapon
    granted = copy.copy(weapon)
    granted.assault = True
    granted.heavy = True
    return granted


class MortarionsTeachingsController:
    def __init__(self, stratagem_controller, turn_tracker=None,
                 shooting_controller=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.shooting_controller = shooting_controller
        self.game_log = game_log
        self._stratagem = Stratagem(name=MORTARIONS_TEACHINGS_NAME,
                                    cp_cost=MORTARIONS_TEACHINGS_CP,
                                    effect=self._grant)

    def reset_phase(self, squads=()):
        """"Until the end of the phase" - one clock, unlike Sudden Storm's two."""
        for squad in squads or ():
            squad.mortarions_teachings_active = False

    def _has_shot(self, squad):
        ledger = getattr(self.shooting_controller, "shot_squad_ids", None) or ()
        return squad in ledger or id(squad) in {id(s) for s in ledger}

    def can_use(self, squad):
        if squad is None or is_active(squad):
            return False
        if not death_lords_chosen.stratagem_target_ok(squad):
            return False
        if not death_lords_chosen.is_terminator_unit(squad):
            return False
        if self.turn_tracker is not None:
            from game.turn import PHASE_SHOOTING
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.turn_owner:
                return False   # "YOUR Shooting phase"
        if self._has_shot(squad):
            return False       # "has not been selected to shoot this phase"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.mortarions_teachings_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"[mortarion's teachings] {squad.name} - ranged weapons gain "
                    f"[ASSAULT] and [HEAVY] until the end of the phase.",
                    file_only=True)
        return True
