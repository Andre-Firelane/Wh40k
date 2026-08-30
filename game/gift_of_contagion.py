"""The Malignant Plaguecaster's own ability "Gift of Contagion".

RULE (printed, word for word):

  "While this model is leading a unit, each time a model in that unit makes an
  attack that targets a unit that is Afflicted, that attack has the
  [SUSTAINED HITS 1] ability."

A CONDITIONAL WEAPON GRANT, so it belongs in the _adjusted_weapon() chain in
BOTH attack steps - the text says "an attack", not "a ranged attack". That is
also where it has to be rather than in the wound step: game/crit_hit.py's
_crit_note() needs to know AT THE MOMENT OF THE HIT ROLL whether a critical die
is a [SUSTAINED HITS] die, so the label on the dice panel is right.

TWO CONDITIONS, and they are asked of DIFFERENT units:
  * the ATTACKING unit must be led by the Plaguecaster (leader_ability(), for
    the same reason game/destroyer_hive.py gives);
  * the TARGET unit must be Afflicted - the army rule's own flag, so this is
    the first ability in the faction that reads Nurgle's Gift rather than
    producing it.

The grant is applied to a COPY. UnitProfile and WeaponProfile subclasses are
shared class objects and their instances are per model, but an adjuster that
mutated the instance would leave [SUSTAINED HITS 1] on the weapon after the
target stopped being Afflicted. copy.copy() is what every other entry in the
chain does, for exactly this reason.

If the weapon ALREADY has [SUSTAINED HITS X] the printed grant would not stack -
it says the attack "has the [SUSTAINED HITS 1] ability", not "add 1". So the
better of the two is kept, which for X >= 1 means the weapon is returned
untouched. No Death Guard weapon prints [SUSTAINED HITS] today except the
Defiler's electroscourge and heavy reaper autocannon, neither of which the
Plaguecaster can lead - recorded because that is what makes the clause
currently unobservable rather than wrong.
"""
import copy

from game import nurgles_gift
from game.attached_units import leader_ability

GIFT_OF_CONTAGION_SUSTAINED = 1


def applies(attacking_squad, target_squad):
    """Both halves of the condition."""
    if not leader_ability(attacking_squad, "gift_of_contagion"):
        return False
    return nurgles_gift.is_afflicted(target_squad)


def adjusted_weapon(weapon, attacking_squad, target_squad):
    """The weapon after the grant - the same signature every other
    _adjusted_weapon() chain entry uses, so it slots in next to them."""
    if weapon is None or not applies(attacking_squad, target_squad):
        return weapon
    if (getattr(weapon, "sustained_hits", 0) or 0) >= GIFT_OF_CONTAGION_SUSTAINED:
        return weapon  # already at least this good; the text grants, it does not add
    adjusted = copy.copy(weapon)   # never mutate the shared instance
    adjusted.sustained_hits = GIFT_OF_CONTAGION_SUSTAINED
    return adjusted
