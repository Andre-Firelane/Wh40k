"""Mont'ka Stratagem: Counterfire Defence Systems (2CP).

RULE (verbatim, rules/tau_empire/detachments/Mont'ka.md):
  WHEN:   Your opponent's Shooting phase, just after an enemy unit has selected
          its targets.
  TARGET: One T'AU EMPIRE unit from your army that was selected as the target
          of one or more of the attacking unit's attacks.
  EFFECT: Until the end of the phase, each time an attack is allocated to your
          unit, subtract 1 from the Damage characteristic of that attack.

"EACH TIME AN ATTACK IS ALLOCATED" IS A DAMAGE-STEP RULE
---------------------------------------------------------
Not a save, not a Feel No Pain - it changes the Damage characteristic itself,
which is exactly what DamageAllocationSession._reduced_damage() is for. That
method already folds the Avatar's Molten Form, the Overlord's Implacable
Resilience and the Void Dragon's Necrodermis, and its own docstring records
that it was renamed from _molten() the moment a second carrier arrived. This is
the fourth, and it joins there rather than anywhere else.

MINIMUM 1, and that is the fold's rule rather than this one's: a Damage
characteristic cannot be reduced below 1, which _reduced_damage() already
enforces for every source at once.

THE SAME INSTANT AS STIM INJECTORS
-----------------------------------
"just after an enemy unit has selected its targets" is ShootingController's
`target_reactions` hook, which Stim Injectors and Kroot Packmates already use.
The protocol is maybe_offer(attacker, target, melee=False); melee is declined
outright, because the printed WHEN names the Shooting phase.
"""

from game import ai_mode, montka, tau_detachments
from game.stratagems import Stratagem

COUNTERFIRE_CP = 2
COUNTERFIRE_NAME = "Counterfire Defence Systems"
COUNTERFIRE_DAMAGE_REDUCTION = 1


def is_active(squad):
    return bool(getattr(squad, "counterfire_defence_active", False))


def damage_reduction_for(squad):
    """Read by DamageAllocationSession._reduced_damage(), beside the three
    abilities already folded there."""
    return COUNTERFIRE_DAMAGE_REDUCTION if is_active(squad) else 0


class CounterfireDefenceController:
    def __init__(self, stratagem_controller, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered_this_phase = set()
        self._stratagem = Stratagem(
            name=COUNTERFIRE_NAME, cp_cost=COUNTERFIRE_CP, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        """Both the grant and the de-duplication memo - Split Fire's
        per-assignment hook would otherwise ask once per weapon group, the same
        reason game/stim_injectors.py keeps one."""
        for squad in squads or ():
            squad.counterfire_defence_active = False
        self._offered_this_phase = set()

    def maybe_offer(self, attacker, target, melee=False):
        """ShootingController.target_reactions' protocol."""
        if melee or attacker is None or target is None:
            return False
        if target.owner == attacker.owner:
            return False
        if is_active(target):
            return False
        if not tau_detachments.has_detachment(target.owner, montka.SETTING):
            return False
        if not tau_detachments.is_tau_unit(target):
            return False
        if not any(not m.is_dead() for m in target.models):
            return False
        key = (id(attacker), id(target))
        if key in self._offered_this_phase:
            return False
        if not self.stratagem_controller.can_use(target.owner, self._stratagem, [target]):
            return False
        self._offered_this_phase.add(key)
        if target.owner in self.auto_players or self.decision_manager is None:
            return False
        self.decision_manager.request(
            target.owner,
            f"{COUNTERFIRE_NAME} ({COUNTERFIRE_CP} CP): {attacker.name} is shooting "
            f"{target.name} - subtract {COUNTERFIRE_DAMAGE_REDUCTION} from the Damage "
            "characteristic of every attack allocated to it this phase?",
            [(f"Use ({COUNTERFIRE_CP} CP)",
              (lambda: self.stratagem_controller.use(target.owner, self._stratagem, [target]))),
             ("Decline", lambda: None)],
        )
        return True

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.counterfire_defence_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{COUNTERFIRE_NAME}: attacks allocated to {squad.name} have their "
                    f"Damage reduced by {COUNTERFIRE_DAMAGE_REDUCTION} this phase."
                )
