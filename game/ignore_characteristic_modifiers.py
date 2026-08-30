"""'Ignore any or all modifiers to that attack's <characteristics>' - the 24th
extraction, at its second consumer.

WHY IT EXISTS
-------------
The HIT ROLL has a real modifier list (game/modifiers.py), and three abilities
already filter it. Strength, Armour Penetration and Damage do NOT: they come out
of _adjusted_weapon() as flat values on a shallow copy, with every source having
already overwritten them. By the time the Save roll reads the AP there is
nothing left that remembers what changed it, so there is no list to drop from.

Spirit Conclave's Seer's Eye needed AP and Damage; Aspect Host's Warrior Focus
needs Strength as well. Two consumers of one mechanism, so it moves here rather
than being written twice with a third characteristic bolted onto one copy.

HOW IT WORKS: BY COMPARISON, NOT BY A LEDGER. The adjusted weapon is compared
against its own PRINTED class - which is the untouched original, since every
adjuster in both chains copies before writing - and the BETTER of the two is
taken per characteristic. No new bookkeeping, and it cannot fall out of step
with the chain, because it reads the chain's own output.

"ANY OR ALL" IS RESOLVED AUTOMATICALLY. There is no board state in which a
player wants to KEEP a modifier that made their own attack worse, so a prompt
per attack would be rule 15.01's cost with none of its choice. Taking the better
of printed and adjusted is exactly "ignore the ones that hurt, keep the ones
that help". The same reading Kauyon's Patient Hunter and rule 24.29 [PSYCHIC]
already write out for the identical wording.

BETTER RUNS IN TWO DIRECTIONS, and that is the one thing a single min() or
max() would get half right:

    Strength            HIGHER is better
    Armour Penetration  MORE NEGATIVE is better
    Damage              HIGHER is better

A ROLLED CHARACTERISTIC IS LEFT ALONE. Nine weapons here print a Damage
notation (D6+1 and friends); comparing a resolved number against a notation is
meaningless, so a weapon whose printed value is a notation keeps whatever the
chain produced. Named rather than left as a silent branch - the same call
game/branching_fates.py makes when it refuses a multi-die roll.

THE HIT-ROLL HALF IS NOT HERE. Both consumers also ignore Hit-roll modifiers
(Warrior Focus explicitly, Seer's Eye not at all), and that half already has a
home: _hit_modifiers() drops every worsening entry, which is what
UnitProfile.ignores_hit_modifiers and the Riptide's Weapon Support System do.
Ballistic Skill and Weapon Skill modifiers land on the same threshold in this
engine, so one filter covers all three printed nouns - that equivalence is
recorded at game/shooting.py's own branch and is not restated here.
"""
import copy

#: The three characteristics this module can restore, by name.
STRENGTH = "strength"
ARMOUR_PENETRATION = "ap"
DAMAGE = "damage"

#: What every consumer so far asks for, in the order the cards print them.
ALL_CHARACTERISTICS = (STRENGTH, ARMOUR_PENETRATION, DAMAGE)


def _better_strength(printed, adjusted):
    """HIGHER is better."""
    if printed is None or adjusted is None:
        return adjusted
    return max(printed, adjusted)


def _better_ap(printed, adjusted):
    """AP is printed as a negative number, so MORE NEGATIVE is better - the
    opposite direction from the other two, which is why these are three
    functions and not one."""
    if printed is None or adjusted is None:
        return adjusted
    return min(printed, adjusted)


def _better_damage(printed, adjusted):
    """HIGHER is better."""
    if printed is None or adjusted is None:
        return adjusted
    return max(printed, adjusted)


_BETTER = {
    STRENGTH: _better_strength,
    ARMOUR_PENETRATION: _better_ap,
    DAMAGE: _better_damage,
}

#: The rolled-notation field that makes a characteristic incomparable.
_NOTATION_FIELD = {
    STRENGTH: None,
    ARMOUR_PENETRATION: None,
    DAMAGE: "damage_notation",
}


def restore(weapon, characteristics=ALL_CHARACTERISTICS):
    """Undo every WORSENING modifier to `characteristics`, keep every improving
    one. Returns a COPY; the caller's weapon is never touched.

    `characteristics` is the printed list of the rule invoking this - Seer's
    Eye names two, Warrior Focus three - so a rule can never quietly ignore a
    characteristic its card does not mention."""
    if weapon is None:
        return weapon
    printed = type(weapon)
    out = copy.copy(weapon)
    for name in characteristics or ():
        notation = _NOTATION_FIELD.get(name)
        if notation is not None and (getattr(weapon, notation, None) is not None
                                     or getattr(printed, notation, None) is not None):
            continue           # a rolled value cannot be compared to a number
        better = _BETTER.get(name)
        if better is None:
            continue
        setattr(out, name, better(getattr(printed, name, None),
                                  getattr(weapon, name, None)))
    return out
