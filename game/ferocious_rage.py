"""Beastboss's own "Ferocious Rage" ability, as supplied by the user (not a
rule from the generic 40k core rulebook, so it lives in its own module -
same reasoning as game/monster_hunters.py for Beast Snagga Boyz' and
game/sunforge.py for the Crisis Sunforge Battlesuits').

RULE: Each time this model makes a Charge move, until the end of the turn,
melee weapons it is equipped with have the [DEVASTATING WOUNDS] ability.

PER MODEL, NOT PER UNIT - AND THAT MATTERS HERE
------------------------------------------------
"melee weapons IT is equipped with", so this is the Beastboss's own weapons
and nobody else's. The distinction is live rather than theoretical: this
model's whole purpose is to LEAD a Beast Snagga Boyz mob (rule 19.01), which
makes it one unit whose models do NOT all have the ability. Contrast
game/war_horde.py's Get Stuck In, which reads its representative model
because it genuinely applies to every Orks model alike.

So the check runs over the attacking models of the group actually being
resolved, and grants only when they are the ones with the ability. Weapon
groups are keyed by weapon characteristics, and the Beastboss's Beastchoppa
and Beast Snagga klaw are unique to it, so in practice a mixed group cannot
arise today - the per-model check is what keeps that a property of the
current datasheets rather than an assumption baked into the code.

"UNTIL THE END OF THE TURN" NEEDS NO NEW BOOKKEEPING
----------------------------------------------------
ChargeController.charged_squad_ids already records who charged, and it is
cleared once per battle round when the Charge phase comes around
(reset_charge_phase(), called from main.py) - NOT at the end of the Charge
phase. That is exactly the lifetime this ability wants, and it is the same
record rule 24.21 ([LANCE]) already reads from game/fight.py for its own
"made a charge move this turn" condition.

It follows that the grant is only ever observable in the Fight phase: a
Charge move happens in the Charge phase, and the Shooting phase is over by
then. So this is wired into game/fight.py only - not a simplification, just
where the rule can actually be reached.
"""

import copy

from game.weapons import MELEE


def model_has_ferocious_rage(model):
    """A live model with the ability (rule 19.04's "while a model that has it
    is still alive" reading, used by every other datasheet ability here)."""
    return (
        model is not None
        and not model.is_dead()
        and getattr(model.profile, "ferocious_rage", False)
    )


def applies(pairs, charge_controller, squad):
    """Whether this group's attacks get [DEVASTATING WOUNDS] right now:
    the attacking models have the ability, and their unit made a Charge
    move this turn."""
    if charge_controller is None or squad is None:
        return False
    if squad not in charge_controller.charged_squad_ids:
        return False
    return any(model_has_ferocious_rage(model) for model, _ in pairs)


def ferocious_rage_adjusted_weapon(weapon, pairs, charge_controller, squad):
    """Grants [DEVASTATING WOUNDS] as a real characteristic change on a
    shallow copy - the shared WeaponProfile instance is never mutated, same
    reasoning as get_stuck_in_adjusted_weapon()/waaagh_melee_adjusted_weapon().

    MELEE only, per the rule text. A weapon that already has the ability
    from another source keeps it and is returned untouched - granting is
    idempotent, so nothing stacks or double-copies."""
    if weapon.weapon_type != MELEE or weapon.devastating_wounds:
        return weapon
    if not applies(pairs, charge_controller, squad):
        return weapon
    raging = copy.copy(weapon)
    raging.devastating_wounds = True
    return raging
