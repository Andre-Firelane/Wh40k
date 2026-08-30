"""Death Lord's Chosen Stratagem: GRIM REAPERS (1 CP, Battle Tactic).

  WHEN: Fight phase.
  TARGET: One TERMINATOR unit from your army that has not been selected to
        fight this phase.
  EFFECT: Until the end of the phase, each time a model in your unit makes an
        attack that targets an enemy unit (excluding MONSTERS and VEHICLES) you
        can re-roll the Hit roll.

A HIT RE-ROLL WITH A TARGET FILTER, which makes it the mirror image of the
engine's existing Monster Hunters (re-roll against MONSTERS and VEHICLES) - so
it plugs into exactly the same seam, FightController._hit_reroll_reason(), and
needs no new mechanism at all. Worth naming the symmetry: the two can never
both apply to the same attack, because their target tests are complements.

"YOU CAN re-roll" - a WHOLE-roll re-roll offered as a choice, not an automatic
one and not a failures-only one. It therefore returns a label from
_hit_reroll_reason() rather than joining game/reroll_scope.py's "ones or the
whole roll" registry, which is for the differently-worded two-clause sources.

MELEE ONLY. The printed text says "makes an attack" without qualifying the
phase - but the WHEN is "Fight phase" and the grant lasts "until the end of the
phase", so a Fight-phase grant can only ever be read in the Fight phase. It is
therefore not wired into game/shooting.py, and the suite asserts that at the
source rather than by building a shooting scene that would prove nothing.

"EXCLUDING MONSTERS AND VEHICLES" uses squad.py's own
is_monster_or_vehicle_unit(), the same test rule 06.03 and 10.06 use - so
"is this a monster or a vehicle" has one answer in this engine, not two.
"""
from game import death_lords_chosen
from game.squad import is_monster_or_vehicle_unit
from game.stratagems import Stratagem

GRIM_REAPERS_CP = 1
GRIM_REAPERS_NAME = "Grim Reapers"
GRIM_REAPERS_LABEL = "Grim Reapers"


def is_active(squad):
    return bool(getattr(squad, "grim_reapers_active", False))


def applies(squad, target_squad):
    """Both halves: the grant is up, and the target is not a MONSTER/VEHICLE."""
    if not is_active(squad) or target_squad is None:
        return False
    return not is_monster_or_vehicle_unit(target_squad)


class GrimReapersController:
    def __init__(self, stratagem_controller, turn_tracker=None,
                 fight_controller=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self.game_log = game_log
        self._stratagem = Stratagem(name=GRIM_REAPERS_NAME, cp_cost=GRIM_REAPERS_CP,
                                    effect=self._grant)

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.grim_reapers_active = False

    def _has_fought(self, squad):
        ledger = getattr(self.fight_controller, "fought_squad_ids", None) or ()
        return squad in ledger or id(squad) in {id(s) for s in ledger}

    def can_use(self, squad):
        if squad is None or is_active(squad):
            return False
        if not death_lords_chosen.stratagem_target_ok(squad):
            return False
        if not death_lords_chosen.is_terminator_unit(squad):
            return False
        if self.turn_tracker is not None:
            from game.turn import PHASE_FIGHT
            # "Fight phase" with NO "your" - the Fight phase belongs to both
            # players, so unlike Mortarion's Teachings there is no turn_owner
            # test here. That is printed, not an omission.
            if self.turn_tracker.phase != PHASE_FIGHT:
                return False
        if self._has_fought(squad):
            return False   # "has not been selected to fight this phase"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.grim_reapers_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"[grim reapers] {squad.name} - Hit rolls may be re-rolled against "
                    f"anything but MONSTERS and VEHICLES until the end of the phase.",
                    file_only=True)
        return True
