"""A flat "subtract N from the Damage characteristic of that attack".

TWO CARRIERS, ONE RULE, which is why this is a module and not a second copy of
game/molten_form.py:

  * Overlord, "Implacable Resilience": "Each time an attack is allocated to
    this model, subtract 1 from that attack's Damage characteristic."
  * C'tan Shard of the Void Dragon, "Necrodermis": "Each time an attack is
    allocated to this model, subtract 1 from the Damage characteristic of that
    attack."

Word for word the same sentence with two different flavour names, so it is one
field (UnitProfile.damage_reduction) holding the N rather than two booleans -
the same call this repo made when an Aeldari effect turned out to be living in
ere_we_go.py and a ranged rule in melee_crit.py.

WHERE IT HOOKS is settled by the same sentence that settled Molten Form's:
"each time an attack is ALLOCATED TO THIS MODEL" names the per-model allocation
step, and DamageAllocationSession._reduced_damage() is the one funnel every
route to a settled amount passes through.

ORDER RELATIVE TO MOLTEN FORM: halve first, then subtract. That is the core
rules' own sequencing for characteristic modifiers (multiply/divide before
add/subtract), and it is also the order that makes the two independent of how
they happen to be listed. No model in this engine currently has both, so
nothing observable depends on it today - it is fixed here so that the day one
does, the answer is already written down rather than emergent.

NEVER BELOW 1. A Damage characteristic cannot be reduced below 1 by the core
rules; without that floor a pair of these would turn a Damage 1 attack into a
Damage 0 one, which is a different (and much stronger) ability than the one
printed.

MORTAL WOUNDS ARE NOT REDUCED, for exactly the reason Molten Form's docstring
gives: a mortal wound is not an attack with a Damage characteristic being
allocated (rule 06.02 is its own mechanism), so MortalWoundAllocationSession
does not call this. Deadly Demise, [HAZARDOUS] and Living Lightning are
therefore untouched by it.
"""

DAMAGE_FLOOR = 1


def reduction_for(model):
    """How much this model subtracts. Per MODEL, because the printed sentence
    says "this model" - after rule 19.01 a merged unit can hold models that do
    and do not have it, and an Overlord leading Lychguard is exactly that."""
    if model is None:
        return 0
    return int(getattr(getattr(model, "profile", None), "damage_reduction", 0) or 0)


def adjusted_damage(model, amount):
    """`amount` after this model's reduction, floored at 1."""
    reduction = reduction_for(model)
    if reduction <= 0:
        return amount
    return max(DAMAGE_FLOOR, amount - reduction)


def label_for(model):
    """The ability's printed NAME, for the log line - the two carriers call the
    same rule different things, and a log that says "damage reduction" would
    make the reader look for a rule with that name."""
    profile = getattr(model, "profile", None)
    if getattr(profile, "matter_absorption", False):
        return "Necrodermis"
    return "Implacable Resilience"
