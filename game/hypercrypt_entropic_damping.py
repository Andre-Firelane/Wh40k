"""Hypercrypt Legion Stratagem: Entropic Damping (1CP).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  WHEN:   Your opponent's Shooting phase, just after an enemy unit has selected its
          targets.
  TARGET: One TITANIC model from your army that was selected as the target of one
          or more of the attacking unit's attacks and is within 18" of the
          attacking unit.
  EFFECT: Until the end of the phase, weapons equipped by models in the attacking
          unit have the [HAZARDOUS] ability.

THE GRANT LANDS ON THE ATTACKER, and that is the whole trap of this card. The
TARGET is your own TITANIC model - it is what the Stratagem is used on, and what
rule 15.01's once-per-phase ledger records - but the EFFECT names "weapons
equipped by models in the ATTACKING unit". A version that flagged the target
would read naturally from inside and give the Monolith [HAZARDOUS] weapons.

WHERE [HAZARDOUS] IS READ. Rule 24.15's Hazard roll is counted in
ShootingController._dispatch_group(), off the ADJUSTED weapon
(`self._adjusted_weapon(pairs, target_squad).hazardous`) - it was moved there
precisely so a granted [HAZARDOUS] counts (Experimental Ammunition). So the
grant is one link in _adjusted_weapon()'s chain: a copy with hazardous=True for
every weapon of a flagged unit, never a mutation of the shared profile. The flag
is set at target selection, before any group is dispatched, so every group the
activation fires afterwards is counted - one D6 per weapon, the ledger's own rule.

UNTIL THE END OF THE PHASE: a flag on the attacking Squad, cleared by
reset_phase() at the phase boundary with the other phase-scoped grants. It is
read only by the Shooting phase's chain, so "until the end of the phase" cannot
leak into a Fight phase either way.

SHOOTING ONLY, and printed so ("your opponent's SHOOTING phase"), so it sits in
shooting_target_reactions and not in fight_target_reactions.

"WITHIN 18" OF THE ATTACKING UNIT" is the closest pair of models, the engine's
min_distance_to(), the same measure Countertemporal Shift uses.

NEVER OFFERED WHEN IT BUYS NOTHING: an attacker already flagged this phase, or
one whose every ranged weapon already prints [HAZARDOUS].

THE AI USES IT WHENEVER IT IS OFFERED: every Hazard roll is a chance of mortal
wounds on the unit shooting a TITANIC model, and nothing is lost by it.
"""

import copy

from game import ai_mode, necron_detachments, titanic
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

ENTROPIC_DAMPING_NAME = "Entropic Damping"
ENTROPIC_DAMPING_CP = 1
ENTROPIC_DAMPING_RANGE_IN = 18.0
SETTING = "HYPERCRYPT_LEGION_PLAYERS"


def is_active(squad):
    return bool(getattr(squad, "entropic_damping_hazardous", False))


def adjusted_weapon(weapon, attacking_squad):
    """One link in ShootingController._adjusted_weapon()'s chain."""
    if weapon is None or not is_active(attacking_squad) or getattr(weapon, "hazardous", False):
        return weapon
    granted = copy.copy(weapon)
    granted.hazardous = True
    return granted


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads or ():
        if is_active(squad):
            squad.entropic_damping_hazardous = False


def _all_ranged_already_hazardous(squad):
    weapons = [w for m in getattr(squad, "models", ()) or () if not m.is_dead()
               for w in m.weapons if getattr(w, "weapon_type", None) == RANGED]
    return bool(weapons) and all(getattr(w, "hazardous", False) for w in weapons)


class EntropicDampingController:
    """An entry in main.py's shooting_target_reactions - maybe_offer(attacker,
    target, melee=False)."""

    def __init__(self, stratagem_controller, turn_tracker=None, decision_manager=None,
                 game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered_this_phase = set()
        self._pending = None      # the attacking unit, for the purchase in flight
        self._stratagem = Stratagem(name=ENTROPIC_DAMPING_NAME, cp_cost=ENTROPIC_DAMPING_CP,
                                    effect=self._grant)

    def reset_phase(self):
        self._offered_this_phase.clear()

    def can_use(self, attacker, target):
        if self.stratagem_controller is None or attacker is None or target is None:
            return False
        if attacker.owner == target.owner:
            return False
        tt = self.turn_tracker
        if tt is None or tt.phase != PHASE_SHOOTING or tt.turn_owner != attacker.owner:
            return False
        if not necron_detachments.has_detachment(target.owner, SETTING):
            return False
        if not titanic.is_titanic_unit(target):
            return False
        if not any(not m.is_dead() for m in target.models):
            return False
        if is_active(attacker) or _all_ranged_already_hazardous(attacker):
            return False
        if attacker.min_distance_to(target) > ENTROPIC_DAMPING_RANGE_IN:
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        if melee:
            return False               # "your opponent's SHOOTING phase"
        key = (id(attacker), id(target))
        if key in self._offered_this_phase:
            return False
        if not self.can_use(attacker, target):
            return False
        self._offered_this_phase.add(key)
        if target.owner in self.auto_players:
            self.use(attacker, target)
            return False
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            target.owner,
            f"{ENTROPIC_DAMPING_NAME} ({ENTROPIC_DAMPING_CP} CP): {attacker.name} has targeted "
            f"{target.name} - give {attacker.name}'s weapons [HAZARDOUS] until the end of the phase?",
            [(f"Use ({ENTROPIC_DAMPING_CP} CP)", lambda: self.use(attacker, target)),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, attacker, target):
        if not self.can_use(attacker, target):
            return False
        self._pending = attacker
        used = self.stratagem_controller.use(target.owner, self._stratagem, [target])
        if not used:
            self._pending = None
        return used

    def _grant(self, controller, player, targets):
        attacker, self._pending = self._pending, None
        if attacker is None:
            return
        attacker.entropic_damping_hazardous = True
        if self.game_log is not None:
            self.game_log.add(
                f"{ENTROPIC_DAMPING_NAME}: until the end of the phase, weapons equipped by models in "
                f"{attacker.name} have [HAZARDOUS].")
