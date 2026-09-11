"""The Silent King's "Damaged:" tier - the half the generic field cannot hold.

RULE (verbatim, rules/necrons/The Silent King.md):

  "Damaged: 1-6 Wounds Remaining. While this unit's Szarekh model has 1-6
   wounds remaining, halve the Attacks characteristic of that model's weapons,
   and each time this unit makes an attack, subtract 1 from the Hit roll."

TWO HALVES WITH TWO DIFFERENT SUBJECTS, and the printed words are the only
thing that says so:

  * halving is "that MODEL's weapons" - Szarekh's, and no one else's;
  * the Hit penalty is "each time THIS UNIT makes an attack" - Szarekh AND both
    Triarchal Menhirs, all three, and all of them keyed off SZAREKH's wounds
    rather than their own.

UnitProfile.damaged_threshold answers a narrower question than either. It is
read by shooting.py's and fight.py's shared _damaged_modifier(), which takes
the ATTACKING MODEL and compares that model's own current_wounds - correct for
every earlier carrier, because each of those is a one-model unit where "this
model" and "this unit" are the same thing. Here they are not: a Menhir on full
wounds takes the Hit penalty from SZAREKH's damage, and _damaged_modifier()
asked about the Menhir would answer no.

So this module owns the UNIT-WIDE reading, and both attack steps ask it beside
the per-model one. The two cannot double up: Szarekh's own damaged_threshold
and this module's answer are the same condition, so _damaged_modifier() is
skipped for a model this module already covers.

HALVING ROUNDS UP - the core-rules convention this repo uses everywhere a
characteristic is halved (see the Avatar of Khaine's Molten Form, which halves
Damage the same way). A 12-attack weapon becomes 6, and a 1-attack weapon stays
1 rather than becoming 0: rounding down would silently delete a weapon.

IT APPLIES TO THE CHARACTERISTIC, NOT TO A ROLLED RESULT. None of Szarekh's
weapons prints a dice Attacks characteristic today, so the two readings cannot
be told apart on this datasheet - written against the printed characteristic
because that is what the rule names, and noted here because a future D6-attack
weapon on a damaged model is the case that would distinguish them.
"""

DAMAGED_LABEL = "Damaged"


def _alive(squad):
    return [m for m in squad.models if not m.is_dead()] if squad else []


def _damaged_bearers(squad):
    """Living models of this unit whose own wounds drive a UNIT-WIDE tier."""
    out = []
    for model in _alive(squad):
        threshold = getattr(model.profile, "damaged_threshold", None)
        if threshold is None:
            continue
        if not getattr(model.profile, "damaged_halves_attacks", False):
            continue    # a per-MODEL tier only - _damaged_modifier() owns it
        if model.current_wounds <= threshold:
            out.append(model)
    return out


def unit_is_damaged(squad):
    """Whether this UNIT is under a unit-wide "Damaged:" tier right now."""
    return bool(_damaged_bearers(squad))


def covers_model(model):
    """Whether this module already answers the Hit penalty for `model`, so
    shooting.py/fight.py's per-model _damaged_modifier() must not add a second
    one for the same printed sentence."""
    squad = getattr(model, "squad", None)
    return unit_is_damaged(squad)


def halves_attacks_for(model):
    """Whether THIS model's weapons have their Attacks characteristic halved.

    Only the model that carries the tier - "that MODEL's weapons". A Menhir
    beside a damaged Szarekh takes the Hit penalty and keeps its Attacks."""
    if model is None or model.is_dead():
        return False
    threshold = getattr(model.profile, "damaged_threshold", None)
    if threshold is None or not getattr(model.profile, "damaged_halves_attacks", False):
        return False
    return model.current_wounds <= threshold


def attacks_for(model, weapon):
    """This model's Attacks characteristic for `weapon`, after the tier.

    The ONE reader both attack steps call, so the shooting and fight sides
    cannot end up with different arithmetic for one printed sentence.

    A weapon whose Attacks is a DICE NOTATION is returned untouched, and that
    is the named boundary: the notation is rolled in its own pending step, and
    none of Szarekh's weapons prints one - so on this datasheet the two
    readings ("halve the characteristic" vs "halve the rolled result") cannot
    be told apart. Written against the characteristic, which is what the rule
    names."""
    if weapon is None:
        return 0
    attacks = getattr(weapon, "attacks", 0)
    if getattr(weapon, "attacks_notation", None) is not None:
        return attacks
    if not halves_attacks_for(model):
        return attacks
    return halved(attacks)


def halved(attacks):
    """Round UP, the core-rules convention - see the module docstring."""
    if not attacks:
        return attacks
    return (attacks + 1) // 2
