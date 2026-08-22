"""Commander Farsight's own "Way of the Short Blade" ability, as supplied by
the user (not a rule from the generic 40k core rulebook, so it lives in its
own module - same reasoning as game/exemplars_of_montka.py and
game/sunforge.py for the other recent datasheet abilities).

RULE: While this model is leading a unit, each time a model in that unit
makes an attack that targets an enemy unit within 9", add 1 to the Wound
roll.

A LEADER ABILITY, NOT A UNIT-WIDE ONE
-------------------------------------
"While this model is LEADING a unit" - so it is read through
game/attached_units.py's leader_ability(), the predicate built for exactly
this shape (Cadre Fireblade's Volley Fire, Warboss's Might is Right,
Coldstar Commander's own). game/squad.py's unit_wide_ability() would be
wrong and not subtly: it asks whether EVERY model is printed with the
ability, and none of the bodyguards are - that is what makes it a leader
ability. leader_ability() also brings rule 19.04's grace window along, so
Farsight dying partway through his unit's attacks does not silently shrink
the rest of them.

BOTH PHASES
-----------
"makes an attack", not "makes a ranged attack" - so this hooks into BOTH
game/shooting.py's and game/fight.py's _wound_modifiers(). Compare
game/sunforge.py, whose own text and WHEN confine it to shooting; this one
has no such limit, and a Farsight-led Crisis team swinging Battlesuit fists
at something 2" away is very much "an attack that targets an enemy unit
within 9"".

THE 9" IS MEASURED UNIT TO UNIT
-------------------------------
"targets an enemy unit within 9\"" describes the TARGET, so it is the
attacking unit's distance to it - Squad.min_distance_to(), edge to edge,
the same measurement every other range check in this engine uses. Not
per-attacking-model: the rule qualifies the target, and both callers here
resolve a whole weapon group against one target squad at a time.
"""

from game.attached_units import leader_ability
from game.modifiers import Modifier

SHORT_BLADE_RANGE_IN = 9.0


def applies(attacking_squad, target_squad):
    """Whether this attack qualifies: the unit is being led by a model with
    the ability, and the target is within 9"."""
    if attacking_squad is None or target_squad is None:
        return False
    if not leader_ability(attacking_squad, "way_of_the_short_blade"):
        return False
    return attacking_squad.min_distance_to(target_squad) <= SHORT_BLADE_RANGE_IN


def wound_modifiers(attacking_squad, target_squad):
    """"Add 1 to the Wound roll" - a BONUS, so per this engine's Modifier
    sign convention (positive worsens a threshold, negative improves it)
    that is a -1 on the wound threshold, exactly like Tank Hunters' own."""
    if not applies(attacking_squad, target_squad):
        return []
    return [Modifier(-1, "Way of the Short Blade")]
