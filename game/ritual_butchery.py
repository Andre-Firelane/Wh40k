"""Kroot Flesh Shaper's "Ritual Butchery".

RULE (printed, word for word):
  "While this model is leading a unit, melee weapons equipped by models in
   that unit have the [SUSTAINED HITS 1] ability."

THE SKORPEKH LORD'S UNITED IN DESTRUCTION WITH ONE KEYWORD CHANGED - same
sentence, same condition, same shape, [SUSTAINED HITS 1] instead of [LETHAL
HITS]. So this is deliberately its twin (game/united_in_destruction.py) rather
than anything cleverer, and the reader is a chain entry in
FightController._adjusted_weapon() for the same reason that one gives:
_crit_note() has to know at ROLL time whether a critical die is a sustained-
hits die, and it reads that off the returned weapon.

leader_ability() rather than unit_wide_ability(): the printed text is the
"while this model is leading" form, so none of the bodyguards print it and a
unit_wide_ability() predicate would be False for every unit that actually has
the ability. It also brings 19.04's grace window along, so a Shaper killed
partway through the enemy's attacks does not silently shrink the rest of his
squad's.

NEVER DOWNGRADES. A weapon that already prints a higher [SUSTAINED HITS X]
keeps its own X - "have the [SUSTAINED HITS 1] ability" grants the ability, it
does not set the value, and a grant that could make a unit worse would be the
obvious bug. Nothing in the current Kroot loadouts prints one, which is exactly
why it is asserted rather than left to chance.

NO PHASE LEDGER, deliberately - the same reasoning as its twin. There is
nothing to spend and nothing to time out: the condition is whether he is alive
and leading, read live on every attack.
"""

import copy

from game.attached_units import leader_ability

RITUAL_BUTCHERY_SUSTAINED_HITS = 1


def unit_has_ritual_butchery(squad):
    """"While this model is leading a unit" - 24.22, via 19.04's source
    models, so a dead Shaper stops conferring at the documented moment."""
    return leader_ability(squad, "ritual_butchery")


def adjusted_weapon(weapon, squad):
    """[SUSTAINED HITS 1] on this unit's melee weapons while the Shaper leads.

    Returns the weapon unchanged when it does not apply, and a COPY when it
    does - the shared WeaponProfile instance is never mutated (this repo's
    standing rule; a mutated base instance would follow the model out of the
    unit and into the next battle).

    Melee-only is not checked here, for the same reason its twin gives: the
    chain this sits in is FightController's, and game/shooting.py never calls
    it. The test pins that at the source rather than by building a shooting
    scene."""
    if weapon is None:
        return weapon
    if not unit_has_ritual_butchery(squad):
        return weapon
    if getattr(weapon, "sustained_hits", 0) >= RITUAL_BUTCHERY_SUSTAINED_HITS:
        return weapon
    if getattr(weapon, "sustained_hits_notation", None) is not None:
        # A printed dice X (e.g. [SUSTAINED HITS D3]) is already at least as
        # good as a flat 1 in every outcome, so granting a flat 1 could only
        # take something away.
        return weapon
    granted = copy.copy(weapon)
    granted.sustained_hits = RITUAL_BUTCHERY_SUSTAINED_HITS
    return granted
