"""The Avatar of Khaine's "Molten Form" - a datasheet ability, so its own
module.

RULE (printed, word for word):
  "Each time an attack is allocated to this model, halve the Damage
  characteristic of that attack."

THE FIRST HALVING IN THIS ENGINE. Nothing else here halves a characteristic, so
the rounding convention had to be settled: the core rules round UP when halving,
which is also the reading that does not quietly favour the model with the
ability (a Damage 1 attack still does 1, a Damage 3 attack does 2). No
user-supplied text covers rounding, so this is the standard convention applied
deliberately rather than a house rule - flagged here so it is one line to change
if the user rules otherwise.

WHERE IT HOOKS, and why that one place is exact:
"each time an attack is ALLOCATED TO THIS MODEL" names the per-model allocation
step, and game/damage_resolution.py's DamageAllocationSession funnels every
route to a settled amount through _apply_feel_no_pain() - the fixed-damage path,
the rolled-notation path, the Stealth Drones path, the Branching Fates override
and the Sunforge re-roll all end there. Halving there covers all of them with
one call.

BEFORE FEEL NO PAIN, deliberately. The ability halves the Damage
CHARACTERISTIC, i.e. how many wounds the attack would inflict; Feel No Pain
(24.12) is then rolled per wound against that reduced number. Halving after
would let FNP ignore wounds that the attack never had.

MORTAL WOUNDS ARE NOT HALVED, and that is not an omission: a mortal wound is
not an attack with a Damage characteristic being allocated (rule 06.02 is its
own mechanism), so MortalWoundAllocationSession deliberately does not call this.
That also keeps Deadly Demise (24.08), [HAZARDOUS] (24.15) and Hold Still
untouched by it.

ONE READING LEFT OPEN, and flagged rather than silently decided:
[DEVASTATING WOUNDS] (24.10) turns an attack into mortal wounds equal to its
Damage characteristic. Whether Molten Form halves THAT depends on whether such
an attack counts as "allocated to this model" - 24.10 has it bypass the normal
allocation and saves. The narrower reading is implemented (it is not halved),
because "allocated" is the word the ability prints, and because
DevastatingWoundAllocationSession is a separate mechanism here for that reason.
One call to change if the user rules the other way.
"""


def halves_damage(model):
    """Whether this model has the ability. Per MODEL, because the printed
    sentence says "this model" - and after rule 19.01 a merged unit can hold
    models that do and do not have it."""
    if model is None:
        return False
    return bool(getattr(getattr(model, "profile", None), "molten_form", False))


def adjusted_damage(model, amount):
    """The Damage this allocated attack actually inflicts on `model`.

    Rounds UP (see the module docstring), so a Damage 1 attack is unchanged and
    only 2+ is actually reduced. Leaves a 0 alone: something upstream (Stealth
    Drones) already cancelled the attack, and halving nothing is nothing."""
    if amount <= 0 or not halves_damage(model):
        return amount
    return -(-amount // 2)   # ceiling division: halve, rounding up
