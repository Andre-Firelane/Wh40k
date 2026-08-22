"""Grav-inhibitor Drone wargear, as supplied by the user (not a rule from
the generic 40k core rulebook, so it lives in its own module - same
reasoning as game/drones.py's other drone effects, which are simple enough
to sit inline there; this one needs real logic in the charge sequence).

RULE (as printed): Each time an enemy unit selects the bearer's unit as the
target of a charge, subtract 2 from the Charge roll (this is not cumulative
with any other negative modifiers to that Charge roll).

NOT the same thing as game/grav_inhibitor_field.py - that is the Retaliation
Cadre STRATAGEM (battle-shock test plus mortal wounds), which shares only a
name fragment.

ADAPTING IT TO THIS ENGINE'S CHARGE ORDER
-----------------------------------------
User: "die Grav Inhibitor Drone wurde vor der 11ten Edition geschrieben, das
müssen wir etwas auf unser System anpassen." Correct, and the mismatch is
specifically about ORDER.

The printed text assumes rule 11.04's own sequence - declare targets first,
THEN roll 2D6 - so "subtract 2 from the Charge roll" is a thing you do to a
roll that hasn't happened yet, at a moment when the targets are already
known.

game/charge.py inverts that: declare_charge() rolls the 2D6 IMMEDIATELY, and
the declared targets are then picked from whatever that roll can reach
(eligible_charge_target_squads() filters by max_distance). At the moment the
roll is turned into a distance (_capped_roll()), charge_targets is still
empty - there is literally nothing to check the bearer's unit against, which
is why this cannot be modeled the way 'Ere We Go's +2 is.

So the -2 is applied where the roll is CONSUMED against a declared target
instead of where it is produced. That is arithmetically the same rule:

    printed:  roll - 2 >= gap        (declare, then roll, then subtract)
    here:     gap <= roll - 2        (roll, then declare against a reduced
                                      effective distance)

Two consumption points, and BOTH are needed - together they are the whole
of what "subtract 2 from the Charge roll" does:

  1. Target eligibility (rule 11.04 BEFORE MOVING, "within the maximum
     distance") - a unit carrying this drone can only be declared if the
     gap fits in roll-2. This half also flows into
     targets_reachable_with(), i.e. the Command Re-roll verdict (15.02),
     for free, because that shares the same gate.
  2. The charge MOVE distance - the models actually get 2" less to travel
     with. Without this half the charge would be harder to declare but
     just as easy to complete, which is not what a reduced roll means.

"NOT CUMULATIVE WITH ANY OTHER NEGATIVE MODIFIERS"
--------------------------------------------------
Expressed as a MAXIMUM over negative sources rather than a sum, so the
clause is encoded rather than merely happening to hold. Today this is the
only negative modifier to a Charge roll in the engine, so the max is always
just this one - but a second source added later gets the clause honoured
without anyone having to remember it. Positive modifiers ('Ere We Go's +2)
are untouched by the clause and keep applying normally, in _capped_roll().
"""

GRAV_INHIBITOR_CHARGE_PENALTY = 2


def unit_has_grav_inhibitor_drone(squad):
    """Rule 19.04-style "the ability applies while a model that has it is
    still alive" - the drone is wargear on one model (the Shas'ui), but its
    effect is worded about "the bearer's UNIT", so any live bearer protects
    the whole unit."""
    if squad is None:
        return False
    return any(m.profile.grav_inhibitor_drone for m in squad.models if not m.is_dead())


def charge_penalty_against(target_squads):
    """How much to subtract from a Charge roll declared against these units.

    A MAX over the negative sources rather than a sum - see the module
    docstring's "not cumulative" note. With a mixed set of targets (one
    carrying the drone, one not) the penalty applies to the ROLL, so it
    applies to the whole declaration, not per target: that is what the
    printed text says, and it is why this takes the whole set."""
    if not target_squads:
        return 0
    negatives = [
        GRAV_INHIBITOR_CHARGE_PENALTY for s in target_squads
        if unit_has_grav_inhibitor_drone(s)
    ]
    return max(negatives, default=0)
