"""T'au Empire detachment rule: Experimental Prototype Cadre's Superior
Craftsmanship.

RULE (verbatim, rules/tau_empire/detachments/Experimental Prototype Cadre.md):
  Friendly BATTLESUIT CHARACTER units' ranged attacks have +6" Range.
  This detachment has the BATTLESUIT tag and cannot be taken with another
  BATTLESUIT detachment.

IT IS A RANGE CHANGE, SO IT GOES WHERE RANGE IS DECIDED
-------------------------------------------------------
game/weapon_range.py is the one definition of "how far does this weapon reach
right now", and it exists precisely because more than one ability adds to the
Range characteristic. This is the THIRD such source, after the Pulse
Accelerator Drone and Fuegan's Burning Lance, and it joins them there rather
than being measured at any of the three call sites.

That also means it reaches all three range questions for free - the "can this
weapon reach that target" test AND the two HALF-range ones ([MELTA X]'s damage
bonus and [RAPID FIRE X]'s extra attacks). Half of a Range characteristic that
has grown by 6" is half of the NEW number, which is the whole substance of that
module's extraction. A Commander's fusion blaster is [MELTA], so this is a live
consequence here, not a hypothetical one.

TAKES THE MODEL, NOT THE SQUAD, for the same reason both of its siblings give:
game/shooting.py measures per shooter on the hot path, and a model with no
squad (probe tokens, tests) degrades to no bonus instead of raising.

"BATTLESUIT CHARACTER UNITS" IS READ THROUGH RULE 19.03
-------------------------------------------------------
A unit has all of its components' keywords, so a Commander attached to a Crisis
team makes the WHOLE unit both BATTLESUIT and CHARACTER - and the printed text
says "units", not "models", so the bodyguards get the +6" too. That is the same
reading game/retaliation_cadre.py's is_battlesuit_unit() already applies for
Bonded Heroes, and it is written out as its own test line because it looks like
an oversight until you check which noun the rule uses.

THE SECOND SENTENCE IS A DEMONSTRATED NO-OP
-------------------------------------------
"cannot be taken with another BATTLESUIT detachment" is a list-building
restriction, and this engine has no army-building step (CLAUDE.md's
Später-Liste); a player fields exactly one detachment here by construction, so
there is nothing it could forbid. Written out rather than dropped, the same way
game/actions.py spells out AIRCRAFT/FORTIFICATION/TITANIC, so that a later
army-building step has a place to hang it.
"""

from game import tau_detachments
from game.attached_units import unit_has_keyword
from game.weapons import RANGED

SETTING = "EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS"
SUPERIOR_CRAFTSMANSHIP_BONUS_IN = 6.0
LABEL = "Superior Craftsmanship"


def is_battlesuit_character_unit(squad):
    """"BATTLESUIT CHARACTER units" under rule 19.03's keyword pooling.

    Two separate any-model questions rather than one "is there a model that is
    both": that is what pooling means, and it is the same helper Bonded Heroes
    uses for its own BATTLESUIT half. In practice the two keywords come from
    the same model (a Commander), but a rule that reads a UNIT's keywords must
    not care which model supplied each one.
    """
    if squad is None:
        return False
    return (unit_has_keyword(squad, lambda model: model.profile.battlesuit)
            and unit_has_keyword(squad, lambda model: model.profile.character))


def applies(squad):
    """Whether this unit's ranged attacks get the extra 6"."""
    if squad is None:
        return False
    if not tau_detachments.has_detachment(getattr(squad, "owner", None), SETTING):
        return False
    if not tau_detachments.is_tau_unit(squad):
        return False
    return is_battlesuit_character_unit(squad)


def bonus_for(model, weapon):
    """This weapon's Range bonus from Superior Craftsmanship, or 0.

    No battle-round window and no Guided clause - unlike Kauyon and Mont'ka
    this one is simply on for the whole battle, which is why it does not use
    game/tau_detachments.py's doctrine_active().
    """
    if weapon is None or getattr(weapon, "weapon_type", None) != RANGED:
        return 0.0
    if not applies(getattr(model, "squad", None)):
        return 0.0
    return SUPERIOR_CRAFTSMANSHIP_BONUS_IN
