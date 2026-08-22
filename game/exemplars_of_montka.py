"""The Twin Lance's own "Exemplars of Mont'ka" ability, as supplied by the
user (not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/sunforge.py, game/target_uploaded.py and
game/nova_charge.py for the other recent datasheet abilities).

RULE: Each time a model in this unit makes a ranged attack that targets the
closest eligible target, that attack has the [SUSTAINED HITS 1] and
[IGNORES COVER] abilities.

WHEN "CLOSEST ELIGIBLE TARGET" IS DECIDED
-----------------------------------------
At target selection, not per attack - and that is the accurate reading, not
a shortcut. "Eligible target" is rule 10.02's own notion (a unit this squad
may legally select), and 10.02 settles every eligibility question about a
target at the instant it is chosen. Casualties from this unit's own earlier
weapon groups must therefore not change the answer partway through, exactly
as they must not change range, line of sight or Benefit of Cover - the bug
that ShootingController._snapshot_target_state() exists to prevent.

So the flag is computed once, in that same snapshot, and read from there for
the rest of the activation. That also keeps it off the hot path: deciding
which target is closest means an eligibility sweep over every enemy unit,
which is far too expensive to redo per weapon group.

WHY THE [IGNORES COVER] HALF IS CURRENTLY REDUNDANT - AND STILL WIRED
--------------------------------------------------------------------
The only datasheet with this ability also has a unit-level "Ignores Cover"
rule (see UnitProfile.ignores_cover), which already bypasses cover against
EVERY target, closest or not. The half is implemented anyway rather than
silently dropped: it is genuinely part of this ability, the two are
independent on paper, and a future unit could have one without the other.
Both are ORed together in shooting.py's _cover_ignored_for_group().
"""

import copy

SUSTAINED_HITS_GRANTED = 1


def unit_has_exemplars_of_montka(squad):
    """True while at least one live model with the ability is in the unit -
    the same rule 19.04 reading every other datasheet ability here uses."""
    if squad is None:
        return False
    return any(m.profile.exemplars_of_montka for m in squad.models if not m.is_dead())


def closest_eligible_target(attacking_squad, eligible_targets):
    """Which of `eligible_targets` is nearest to `attacking_squad`, or None
    when there are none.

    Measured edge to edge via Squad.min_distance_to(), the same measurement
    rules 11.02/11.04 and every range check in this engine use - not
    centroid distance, which would disagree with what the player sees for
    units of different footprints."""
    candidates = [t for t in eligible_targets if t is not None]
    if not candidates:
        return None
    return min(candidates, key=attacking_squad.min_distance_to)


def montka_adjusted_weapon(weapon, pairs, is_closest):
    """"That attack has the [SUSTAINED HITS 1] ability" modeled as an actual
    characteristic change (shallow copy - the shared WeaponProfile instance
    is never mutated), same shape as arrokon_adjusted_weapon() and
    game/war_horde.py's Get Stuck In.

    GRANTS rather than overwrites: a weapon that already has a higher
    [SUSTAINED HITS] keeps its better value, and the two never add up (two
    sources of the same ability don't stack).

    `is_closest` is passed in rather than recomputed - the caller holds the
    snapshot that decided it (see the module docstring)."""
    if not is_closest or not pairs:
        return weapon
    shooter = pairs[0][0]
    if not unit_has_exemplars_of_montka(getattr(shooter, "squad", None)):
        return weapon
    if SUSTAINED_HITS_GRANTED <= weapon.sustained_hits:
        return weapon
    boosted = copy.copy(weapon)
    boosted.sustained_hits = SUSTAINED_HITS_GRANTED
    return boosted
