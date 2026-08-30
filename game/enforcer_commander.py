"""Commander in Enforcer Battlesuit's "Enforcer Commander".

RULE (printed, word for word):
  "While this model is leading a unit, each time a ranged attack targets that
   unit, worsen the Armour Penetration characteristic of that attack by 1."

THE BATTLEWAGON'S RAMSHACKLE BUT RUGGED, ONE CONDITION RICHER - so it sits in
exactly the same slot: game/damage_resolution.py's save_thresholds(), where the
save roll is actually built. That is a DEFENDER-side adjustment, and the reason
it belongs there rather than on the attacker's weapon chain is Ramshackle's own
note: the trigger is about the attack arriving, not about who fired it, and the
panel and the resolution must not disagree about a save.

TWO DIFFERENCES FROM RAMSHACKLE, both printed:

  * RANGED ONLY. Ramshackle worsens every attack; this one names ranged
    attacks, so a melee attack is untouched. That is why this takes the weapon
    rather than only the model.
  * WHILE LEADING A UNIT, and it protects THAT UNIT - so unlike Ramshackle,
    which is a property of the model being allocated to, this reaches every
    model in the Commander's unit, bodyguards included. Read through
    leader_ability(), which brings 19.04's grace window: a Commander killed
    partway through the enemy's attacks does not silently strip the protection
    from the rest of that attacking unit's attacks.

WORSENING STOPS AT 0, the same arithmetic and the same reason as Ramshackle:
AP is written as a penalty (0, -1, -2...), "worsen by 1" moves one step TOWARD
zero, and an AP0 attack must not become a BONUS to the target's save. With only
AP0 weapons on the table the two spellings are indistinguishable, which is
exactly why it is written as min(0, ap + 1) and tested at AP0.

STACKS WITH RAMSHACKLE by construction, because each is applied in turn - no
T'au model has both, but the arithmetic is composition rather than a max().
"""

from game.attached_units import leader_ability
from game.weapons import MELEE

ENFORCER_COMMANDER_LABEL = "Enforcer Commander"


def applies(model, weapon):
    """Whether this attack's AP is worsened by an Enforcer Commander.

    `model` is the model the attack is being allocated to (its unit is what
    matters), `weapon` the attacking weapon - melee attacks are excluded."""
    if model is None or weapon is None:
        return False
    if getattr(weapon, "weapon_type", None) == MELEE:
        return False
    return leader_ability(getattr(model, "squad", None), "enforcer_commander")


def adjusted_ap(ap, model, weapon):
    """The attack's AP after this ability, clamped so it can never become a
    bonus to the target's save."""
    if not applies(model, weapon):
        return ap
    return min(0, ap + 1)
