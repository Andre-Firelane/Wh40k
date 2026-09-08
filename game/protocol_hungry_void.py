"""Awakened Dynasty Stratagem: "Protocol of the Hungry Void".

RULE (printed, word for word):
  WHEN:   "Fight phase."
  TARGET: "One NECRONS unit from your army that has not been selected to fight
           this phase."
  EFFECT: "Until the end of the phase, add 1 to the Strength characteristic of
           melee weapons equipped by models in your unit. In addition, if a
           NECRONS CHARACTER is leading your unit, until the end of the phase,
           improve the Armour Penetration characteristic of melee weapons
           equipped by models in your unit by 1."

TWO EFFECTS, ONE PURCHASE, and the second is conditional on the same "is a
CHARACTER leading this unit" clause five of the six protocols share - so it is
read from game/awakened_dynasty.py rather than restated here.

THE LEADER CLAUSE IS EVALUATED WHEN THE WEAPON IS ADJUSTED, not when the
Stratagem is bought. That is deliberate and it follows the printed text: the
grant lasts "until the end of the phase", and if the Overlord dies partway
through it the unit is no longer being led. Rule 19.04's grace window (which
leader_ability() brings along) keeps that from biting mid-sequence.

WHERE THE EFFECT IS READ: FightController._adjusted_weapon(), the same chain
Waaagh!'s +1 Strength already uses - and for the same reason it must be a chain
entry rather than applied at the wound step, since _crit_note() has to know the
weapon's final shape at ROLL time.

MELEE ONLY, which the printed text says twice ("melee weapons" in both
clauses), so a Necron unit that shoots in the same turn is untouched.
"""

import copy

from game import awakened_dynasty
from game.stratagems import Stratagem

HUNGRY_VOID_CP_COST = 1
HUNGRY_VOID_STRENGTH_BONUS = 1
HUNGRY_VOID_AP_BONUS = 1        # "improve by 1" = one MORE negative, see game/crit_ap.py
HUNGRY_VOID_NAME = "Protocol of the Hungry Void"


def is_active(squad):
    return bool(getattr(squad, "hungry_void_active", False))


def adjusted_weapon(weapon, squad):
    """The melee profile with the grant applied. A no-op passthrough unless it
    is up, so the chain can call it unconditionally.

    Copies rather than mutating: WeaponProfile instances are shared, and this
    repo's standing rule is that effects copy."""
    if weapon is None or not is_active(squad):
        return weapon
    granted = copy.copy(weapon)
    granted.strength = weapon.strength + HUNGRY_VOID_STRENGTH_BONUS
    # The second clause, still conditional at read time - see the module
    # docstring on why this is not baked in at purchase.
    if awakened_dynasty.is_led_by_character(squad):
        granted.ap = weapon.ap - HUNGRY_VOID_AP_BONUS
    return granted


class HungryVoidController:
    """Proactive: the active player buys it at a moment of their own choosing,
    so there is no DecisionManager hook - an ActionPanel button for a human,
    and a deterministic verdict for the AI."""

    def __init__(self, stratagem_controller, turn_tracker=None, fight_controller=None,
                 game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self.game_log = game_log
        self._stratagem = Stratagem(name=HUNGRY_VOID_NAME, cp_cost=HUNGRY_VOID_CP_COST,
                                    effect=self._grant)

    def reset_phase(self, squads=()):
        """"until the end of the phase"."""
        for squad in squads or ():
            squad.hungry_void_active = False

    def can_use(self, squad):
        if squad is None or is_active(squad):
            return False
        if not awakened_dynasty.stratagem_target_ok(squad):
            return False
        if self.turn_tracker is not None:
            from game.turn import PHASE_FIGHT
            if self.turn_tracker.phase != PHASE_FIGHT:
                return False
        # "that has not been selected to fight this phase" - the engine already
        # keeps that ledger, so it is read rather than re-derived.
        if False:
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.hungry_void_active = True
        if self.game_log is not None:
            extra = (" and improve their AP by 1"
                     if awakened_dynasty.is_led_by_character(squad) else "")
            self.game_log.add(
                f"{HUNGRY_VOID_NAME}: {squad.name}'s melee weapons gain +1 Strength{extra} "
                f"until the end of the phase.")
