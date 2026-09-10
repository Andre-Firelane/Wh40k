"""Canoptek Doomstalker's "Sentinel Construct" (Necrons).

RULE (printed, word for word):
  "Each time you target this unit with the Fire Overwatch Stratagem, while
   resolving that Stratagem, hits are scored on unmodified Hit rolls of 5+."

THE SECOND NECRON CARRIER of a clause the Hexmark Destroyer already prints, and
the same seam answers both - ShootingController._base_hit_threshold()'s
SNAP_SHOOTING branch, where rule 15.09's flat 6 is overridden.

WHAT IS THE SAME, and why it matters that it is:
  * "EACH TIME YOU TARGET THIS UNIT" - no latch, no entitlement, no once per
    anything. Every Fire Overwatch aimed at this unit hits on 5+, including a
    second, fully paid one in the same phase. That is the wording Inescapable
    Death's third clause has, and it is exactly what distinguishes both from
    Guardian Battlehost's Protector of the Paths, which says "while resolving
    THAT Stratagem" and therefore needs one.
  * It is an OVERRIDE rather than a Modifier, because 15.09 also ignores every
    modifier - a Modifier would be correctly thrown away by the very rule this
    is meant to beat.

WHAT DIFFERS IS ONE NUMBER: 5+ where the Hexmark's is 2+. The fold takes the
BETTER of whatever applies (min), which says what rule 05.04 says about two
sources of one characteristic without inventing a precedence rule - and no unit
can carry both today, so the min never arbitrates between two live sources.

IT IS THE DEFENDER'S ABILITY, not the shooter's. The unit whose profile is read
is the one being SHOT AT (self.active_squad is the Overwatching unit... no - see
the fold: the Hexmark's clause is asked of the unit that was TARGETED with the
Stratagem, which in a Fire Overwatch is the unit doing the shooting). Written
out because "target this unit with the Fire Overwatch Stratagem" names the
OVERWATCHING unit: 15.08's TARGET line is the friendly unit that gets to shoot,
not the enemy that triggered it.
"""

SENTINEL_CONSTRUCT_LABEL = "Sentinel Construct"

#: "hits are scored on unmodified Hit rolls of 5+".
SENTINEL_CONSTRUCT_HIT_THRESHOLD = 5


def unit_has_bearer(squad):
    return squad is not None and any(
        getattr(m.profile, "sentinel_construct", False)
        for m in getattr(squad, "models", ()) or () if not m.is_dead())


def snap_hit_threshold(squad):
    """The unmodified Hit roll this unit's Fire Overwatch needs, or None.

    Same signature and same contract as inescapable_death.snap_hit_threshold()
    - None means "nothing applies, 15.09's printed 6 stands"."""
    if not unit_has_bearer(squad):
        return None
    return SENTINEL_CONSTRUCT_HIT_THRESHOLD
