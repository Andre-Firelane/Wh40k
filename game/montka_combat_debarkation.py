"""Mont'ka Stratagem: Combat Debarkation (1CP).

RULE (verbatim, rules/tau_empire/detachments/Mont'ka.md):
  WHEN:   Your Shooting phase.
  TARGET: One T'AU EMPIRE INFANTRY unit from your army that disembarked from a
          TRANSPORT this turn.
  EFFECT: Until the end of the phase, each time a model in your unit makes an
          attack that targets the closest enemy unit, you can re-roll the Wound
          roll.

"THE CLOSEST ENEMY UNIT" IS ALREADY ANSWERED
---------------------------------------------
game/exemplars_of_montka.py works out the closest eligible target for The Twin
Lance's datasheet ability, and it settled two things worth not re-deciding: the
measurement is edge to edge via Squad.min_distance_to() (what the player sees),
and the answer is fixed at TARGET SELECTION rather than per attack - rule
10.02 freezes every eligibility question at that instant, and casualties from
this unit's own earlier weapons must not change the answer partway through.

That module is named after the Twin Lance's ability, not after this Stratagem,
but the QUESTION it answers is neither's property - so this asks it rather than
measuring again. (If a third caller ever arrives the module should be renamed
after the question, which is this repo's standing rule; two is not yet that.)

"DISEMBARKED FROM A TRANSPORT THIS TURN" is Squad.disembarked_from_this_turn,
which TransportController already sets and clears - no second bookkeeping.
"""

from game import montka, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

COMBAT_DEBARKATION_CP = 1
COMBAT_DEBARKATION_NAME = "Combat Debarkation"


def is_active(squad):
    return bool(getattr(squad, "combat_debarkation_active", False))


def disembarked_this_turn(squad):
    return getattr(squad, "disembarked_from_this_turn", None) is not None


def applies(attacking_squad, target_squad, closest_squad):
    """Whether this attack may re-roll its Wound roll: the grant is up and the
    target is the closest enemy unit."""
    if not is_active(attacking_squad) or target_squad is None:
        return False
    return closest_squad is target_squad


class CombatDebarkationController:
    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=COMBAT_DEBARKATION_NAME, cp_cost=COMBAT_DEBARKATION_CP, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.combat_debarkation_active = False

    def panel_label(self, squad):
        return (f"{COMBAT_DEBARKATION_NAME} ({COMBAT_DEBARKATION_CP} CP) - "
                "re-roll Wound vs the closest enemy unit")

    def can_use(self, squad):
        if squad is None or self.shooting_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if is_active(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, montka.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        alive = [m for m in squad.models if not m.is_dead()]
        if not alive or not all(m.profile.infantry for m in alive):
            return False
        if not disembarked_this_turn(squad):
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
            squad.combat_debarkation_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{COMBAT_DEBARKATION_NAME}: {squad.name} can re-roll Wound rolls "
                    "against the closest enemy unit this phase."
                )
