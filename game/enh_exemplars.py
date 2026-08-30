"""Two Enhancements, one mechanism: Exemplar of the Kauyon and Exemplar of the
Mont'ka.

RULES (verbatim, rules/tau_empire/detachments/{Kauyon,Mont'ka}.md):
  Exemplar of the Kauyon (Kauyon, 20 pts)
    T'AU EMPIRE model only (excluding KROOT SHAPER models). While the bearer is
    leading a unit, the Patient Hunter Detachment rule applies to that unit
    from the second battle round onwards instead of from the third.

  Exemplar of the Mont'ka (Mont'ka, 10 pts)
    T'AU EMPIRE model only (excluding KROOT SHAPER models). While the bearer is
    leading a unit, the Killing Blow Detachment rule applies to that unit
    during the fourth battle round as well.

WHY BOTH LIVE HERE
------------------
They are the same edit to the same thing: each WIDENS its detachment rule's
round window, for one unit, while a character leads it. game/kauyon.py and
game/montka.py already share game/tau_detachments.py for exactly that reason,
and splitting these two would mean two copies of "which rounds does this unit
see" that could drift by one - the kind of off-by-one that only shows up in a
game.

WHERE IT LANDS, AND WHY NOT IN THE ENHANCEMENT'S OWN CHECK
-----------------------------------------------------------
The window is read by game/tau_detachments.py's doctrine_active(), which both
detachment rules open with and which every one of their grant sites goes
through. So the widening belongs THERE - as rounds_for(squad, ...) below,
consulted by doctrine_active() - and not bolted onto each of the four places
that grant a keyword. Kauyon alone has two halves in two different files
(_adjusted_weapon() and _hit_modifiers()); an Enhancement wired into one of
them and not the other would be half a rule, and the printed text says the
DETACHMENT RULE applies, not one clause of it.

"FROM THE SECOND BATTLE ROUND ONWARDS INSTEAD OF FROM THE THIRD" is a
REPLACEMENT of the window, not an addition to it - which happens to be the same
set here (2,3,4,5 vs 3,4,5 plus 2), but the two readings differ the moment a
window is not a suffix, so it is written as the printed one.

"DURING THE FOURTH BATTLE ROUND AS WELL" is an ADDITION - (1,2,3) plus 4. Both
are pinned separately, because a shared "widen by one round" helper would make
these two look interchangeable when only their result is.

"WHILE THE BEARER IS LEADING A UNIT" is rule 24.22, read through
attached_units.leader_ability(): NOT unit_wide_ability(), which asks whether
every model prints the ability and is therefore False for every unit that
actually has a leader ability. It brings 19.04's grace window along for free, so
a bearer killed mid-sequence does not shrink the rest of his unit's attacks.

A bearer standing ALONE is leading nothing, so neither Enhancement does
anything - the printed condition, and its own test line, because "the unit the
bearer is in" is the plausible misreading.
"""

from game import attached_units, enhancements

EXEMPLAR_OF_THE_KAUYON = "Exemplar of the Kauyon"
EXEMPLAR_OF_THE_MONTKA = "Exemplar of the Mont'ka"

# The printed windows, as the two Enhancements state them.
KAUYON_EXEMPLAR_ROUNDS = (2, 3, 4, 5)   # "from the second battle round onwards INSTEAD of from the third"
MONTKA_EXEMPLAR_EXTRA_ROUND = 4         # "during the fourth battle round AS WELL"


def _leads_with(squad, name):
    """"While the bearer is leading a unit" - and the bearer's owner actually
    fields the Enhancement's detachment (game/enhancements.py's is_active())."""
    if not enhancements.is_active(squad, name):
        return False
    return attached_units.leader_ability(squad, enhancements.get(name).flag)


def kauyon_applies(squad):
    return _leads_with(squad, EXEMPLAR_OF_THE_KAUYON)


def montka_applies(squad):
    return _leads_with(squad, EXEMPLAR_OF_THE_MONTKA)


def rounds_for(squad, setting, printed_rounds):
    """The battle rounds `squad` actually sees its detachment rule in.

    Called by game/tau_detachments.py's doctrine_active() with the detachment's
    own config constant and printed window, so ONE function answers "is this
    round in the window" for both detachment rules and both Enhancements.

    `setting` rather than the detachment name because that is the constant both
    rule modules already carry, and it is what makes a Kauyon Enhancement
    unable to widen Mont'ka's window: each branch below is reached only for its
    own detachment.
    """
    from game import kauyon, montka
    if setting == kauyon.SETTING and kauyon_applies(squad):
        return KAUYON_EXEMPLAR_ROUNDS
    if setting == montka.SETTING and montka_applies(squad):
        return tuple(printed_rounds) + (MONTKA_EXEMPLAR_EXTRA_ROUND,)
    return tuple(printed_rounds)
