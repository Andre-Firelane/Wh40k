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

THE 2026-09 ORK CODEX BROUGHT TWO MORE (stage E3d):

  * Deff Dread, "Dread 'Ard": "Attacks that target this unit have -1 D." The
    same field. The printed subject is the UNIT and this reads the MODEL - on a
    one-model unit those are the same attacks, and no rule lets anything join a
    Deff Dread.
  * Battlewagon, "Mobile Fortress": "RANGED attacks that target this unit have
    -1 D." The one qualifier the others lack, so it is its own field
    (UnitProfile.ranged_damage_reduction) and this module is handed the
    attack's WEAPON to answer it. A melee attack is untouched - the half a
    shared field would lose.

UnitProfile.damage_reduction_label names the rule for the log line, since five
carriers print it under four names.
"""

from game.weapons import RANGED

DAMAGE_FLOOR = 1


def reduction_for(model, weapon=None):
    """How much this model subtracts from an attack made with `weapon`. Per
    MODEL, because the printed sentence says "this model" - after rule 19.01 a
    merged unit can hold models that do and do not have it, and an Overlord
    leading Lychguard is exactly that.

    `weapon` is only needed for the ranged-only half (Mobile Fortress); without
    it that half is not counted, so a caller that cannot say what attacked never
    claims a reduction the printed text limits to ranged attacks."""
    if model is None:
        return 0
    profile = getattr(model, "profile", None)
    reduction = int(getattr(profile, "damage_reduction", 0) or 0)
    if getattr(weapon, "weapon_type", None) == RANGED:
        reduction += int(getattr(profile, "ranged_damage_reduction", 0) or 0)
    return reduction


def adjusted_damage(model, amount, weapon=None):
    """`amount` after this model's reduction against `weapon`, floored at 1."""
    reduction = reduction_for(model, weapon)
    if reduction <= 0:
        return amount
    return max(DAMAGE_FLOOR, amount - reduction)


def label_for(model):
    """The ability's printed NAME, for the log line - the carriers call the
    same rule different things, and a log that says "damage reduction" would
    make the reader look for a rule with that name."""
    profile = getattr(model, "profile", None)
    printed = getattr(profile, "damage_reduction_label", None)
    if printed:
        return printed
    if getattr(profile, "matter_absorption", False):
        return "Necrodermis"
    return "Implacable Resilience"
