"""Crisis Sunforge Battlesuits' own "Sunforge" ability, as supplied by the
user (not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/target_uploaded.py for the Pathfinders' and
game/nova_charge.py for the Riptide's).

RULE: Each time a model in this unit makes a ranged attack that targets a
Monster or Vehicle unit, you can re-roll the Wound roll and you can re-roll
the Damage roll.

TWO HALVES, TWO PLACES
----------------------
The two re-rolls sit at different points of the attack sequence and reuse
different existing machinery:

  * The WOUND half joins game/shooting.py's _wound_reroll_reason()/
    _wound_reroll_is_full(), which already offer exactly this choice for
    rule 24.38 ([TWIN-LINKED]) and Breacher Team's Breach and Clear. Like
    Breach and Clear - and unlike [TWIN-LINKED], which the user explicitly
    scoped to failures only - this one re-rolls the WHOLE roll: "you can
    re-roll the Wound roll", the same wording that decided Breach and Clear.

  * The DAMAGE half lives in game/damage_reroll.py (it was written here
    first, and moved out when Fire Dragons became its second user). A
    dice-notation Damage characteristic (the
    Fusion blaster's printed "D6") is rolled per allocated attack by
    game/damage_resolution.py's DamageAllocationSession, so the offer has to
    live there. It is passed in as an optional collaborator, exactly like
    StealthDronesController already is - the session stays unaware of which
    ability opened the choice.

RANGED ONLY - AND THAT IS COMPLETE, NOT A SIMPLIFICATION
--------------------------------------------------------
"makes a ranged attack", so only game/shooting.py wires this. game/fight.py
builds an identical DamageAllocationSession and deliberately does NOT pass a
damage_reroll: a melee attack is never a ranged attack, and this datasheet's
only melee weapon (Battlesuit fists) has a flat Damage 1 with no roll to
re-roll in the first place.

RE-ROLLING ONCE
---------------
A die can never be re-rolled more than once, no matter how many effects
would each allow it (see game/dice.py's already_rerolled ledger and
CLAUDE.md's own entry on the bug that came from not tracking that). So the
damage offer is only made when the die is actually still re-rollable -
if a Command Re-roll (15.02) already re-rolled it, Sunforge cannot.
"""

from game.squad import is_monster_or_vehicle_unit

SUNFORGE_REROLL_LABEL = "Sunforge"


def unit_has_sunforge(squad):
    """True while at least one live model with the ability is in the unit -
    the same reading every other datasheet ability here uses (rule 19.04's
    "applies while a model that has it is still alive")."""
    if squad is None:
        return False
    return any(m.profile.sunforge for m in squad.models if not m.is_dead())


def applies(attacking_squad, target_squad):
    """Whether this attack is "a ranged attack by a model in this unit that
    targets a MONSTER or VEHICLE unit".

    is_monster_or_vehicle_unit() is the engine's one definition of that
    keyword test (rule 19.03 pooling included), already used by rule 10.06's
    Close-Quarters malus - reused rather than re-derived."""
    if attacking_squad is None or target_squad is None:
        return False
    return unit_has_sunforge(attacking_squad) and is_monster_or_vehicle_unit(target_squad)


# The Damage-roll half used to be a class here. It moved to
# game/damage_reroll.py when Fire Dragons' Assured Destruction became its
# second consumer - nothing about the offer was ever Sunforge-specific except
# the label in its prompt. The old SunforgeDamageReroll name is deliberately
# NOT kept as an alias: the class gained a `label` first argument, so an alias
# would be a working import onto a changed signature.
from game.damage_reroll import DamageRerollOffer  # noqa: E402


def damage_reroll_offer(**kwargs):
    """This ability's DamageRerollOffer, pre-labelled."""
    return DamageRerollOffer(
        SUNFORGE_REROLL_LABEL, prompt_suffix="against this MONSTER/VEHICLE target", **kwargs
    )
