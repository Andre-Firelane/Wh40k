"""Warlock Conclave's "Protect" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "While a FARSEER model is leading this unit, each time an attack targets this
  unit, subtract 1 from the Wound roll."

A -1 TO THE WOUND ROLL AGAINST THIS UNIT is exactly the shape War Horde's 'Ard
as Nails and the T'au Guardian Drone already have, so it lands in the same two
_wound_modifiers() hooks - in BOTH phases, because "each time an attack targets
this unit" says attack, not ranged attack.

Sign convention: game/modifiers.py counts a POSITIVE amount as worsening a
threshold, and "subtract 1 from the Wound roll" makes the roll harder, so it is
a +1 on the wound threshold. Same as the two abilities above.

LIVE SINCE ELDRAD ULTHRAN, and the route there is worth recording because it
was guessed wrong twice.

It was built while no FARSEER datasheet existed at all. When the Farseer
arrived, this ability did NOT come to life: Protect needs a Farseer LEADING a
unit that contains Warlocks, and a Warlock Conclave is itself a leader unit, so
no Farseer could attach to it, and no bodyguard datasheet here printed rule
19.01's two-leader exception. The reachable shape was missing, not the code.

Eldrad Ulthran supplies it, from the direction nobody was watching: the second
sentence of his own LEADER line reads "you can attach this model to a unit,
even if one WARLOCKS unit has already been attached to it". He is a FARSEER, so
Guardian Defenders + Warlock Conclave + Eldrad is a unit with a Farseer leading
Warlocks - exactly this condition. See game/attached_units.py's
_leader_allows_joining_led_unit(), which is the mirror of the bodyguard-side
permission that was being looked for.

test_eldrad_ulthran.py pins the whole chain: that the attachment is legal, that
this predicate then fires, and that the -1 reaches the wound roll in both
phases. test_farseer.py keeps pinning that a PLAIN Farseer still cannot get
there, since that is a different datasheet with no such clause.

"WHILE A FARSEER MODEL IS LEADING THIS UNIT" is rule 19.01's leader
relationship, so it is read off the attached unit's own components rather than
from any model of the squad - a Conclave nobody has joined is not being led.
"""

from game import attached_units


def applies(squad):
    """Whether a FARSEER is currently leading this unit.

    Two halves, both necessary: the unit must be one that HAS this ability
    (a Warlock Conclave), and the model leading it must be a Farseer.
    attached_units.leader_models() answers the second against the leader
    COMPONENT, so it ends when that model dies."""
    if squad is None:
        return False
    models = getattr(squad, "models", None)
    if not models:
        return False
    if not any(getattr(m.profile, "protect", False) and not m.is_dead() for m in models):
        return False
    return any(getattr(m.profile, "farseer", False)
               for m in attached_units.leader_models(squad, alive_only=True))
