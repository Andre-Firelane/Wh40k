"""Pulse Accelerator Drone wargear, as supplied by the user (not a rule from
the generic 40k core rulebook).

RULE: Add 6" to the Range characteristic of pulse carbines equipped by
models in the bearer's unit.

WHY THIS IS A FUNCTION AND NOT A TOKEN MUTATION
-----------------------------------------------
Every other drone in game/drones.py applies its effect by mutating the
BEARER at build time (Shield Drone bumps the bearer's own Wounds, Gun Drone
appends a weapon to the bearer). This one cannot work that way, for two
independent reasons:

  * It affects "models in the bearer's UNIT", not the bearer - and Gear
    effects run per model at build time, with no access to the finished
    squad.
  * It is conditional on the drone still being there. A characteristic
    baked into every pulse carbine at build time would survive the bearer's
    death, and would also survive the model leaving the unit.

So the drone sets a flag on its own model (profile.pulse_accelerator_drone)
and the range is derived, live, wherever range is actually measured -
exactly the same shape as game/coldstar.py's effective_movement_in(), which
had the identical "one model grants the whole unit a changed characteristic"
problem.

WHICH WEAPONS COUNT
-------------------
"Pulse carbines" by weapon identity, not by anything looser. The Pathfinder
Team's own Pulse carbine qualifies; the Twin pulse carbine a Gun Drone
brings does NOT - it is a different weapon entry with its own name, profile
and BS, and the rule names the singular one. Flagged as a reading rather
than a certainty, since the supplied text does not spell the distinction
out; PULSE_CARBINE_NAMES below is the single place to widen it if that turns
out to be wrong.
"""

PULSE_ACCELERATOR_BONUS_IN = 6.0

# Matched on the printed weapon NAME rather than the class, because a weapon
# instance handed around during resolution can be a shallow copy made by any
# of the adjusters in game/shooting.py (Bonded Heroes, Starscythe, ...) -
# an isinstance() check would still work today but couples this to those
# copies staying class-preserving, which nothing guarantees.
PULSE_CARBINE_NAMES = frozenset({"Pulse Carbine"})


def unit_has_pulse_accelerator_drone(squad):
    """True while at least one live model in the unit carries the drone -
    the same "the wargear works while its bearer is alive" reading every
    other unit-wide drone effect here uses."""
    if squad is None:
        return False
    return any(m.profile.pulse_accelerator_drone for m in squad.models if not m.is_dead())


def effective_range_in(model, weapon):
    """This weapon's Range characteristic as it stands right now, for this
    wielder - the drone's +6" included if it applies.

    Takes the MODEL rather than the squad so callers can pass what they
    already have on the hot path (game/shooting.py measures per shooter),
    and so a model with no squad (probe tokens, tests) degrades to the
    printed range instead of raising."""
    base = weapon.range_in
    if weapon.name not in PULSE_CARBINE_NAMES:
        return base
    squad = getattr(model, "squad", None)
    if not unit_has_pulse_accelerator_drone(squad):
        return base
    return base + PULSE_ACCELERATOR_BONUS_IN
