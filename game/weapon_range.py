"""How far a weapon reaches RIGHT NOW - the one definition.

Two abilities in this engine add to a weapon's Range characteristic, and both do
it the same way: one model grants the change to every model in its unit, so the
number cannot be baked into the weapon at build time and has to be derived live.

  * the Pulse Accelerator Drone - +6" to pulse carbines in the bearer's unit
    (game/pulse_accelerator.py)
  * Fuegan's Burning Lance - +6" to Melta weapons in the unit he is leading
    (game/burning_lance.py)

EXTRACTED AT THE SECOND CONSUMER, which is this repo's standing rule: the drone
owned the answer while it was the only one asking, and its function was reached
from exactly one place in game/shooting.py. A second source would otherwise have
had to either bolt itself onto a module named after the first ability, or add a
second place that answers the same question - the drift this codebase keeps
consolidating away.

THE TERMS ADD. Nothing in either printed text makes them exclusive, and a weapon
that is both a pulse carbine and [MELTA] does not exist today anyway; adding is
the reading that needs no special case if one ever appears.

ALL THREE RANGE SITES READ THIS, and that is the point of the extraction rather
than a bonus. game/shooting.py used to call the drone's function at the "can
this weapon reach that target" test only, with a comment noting that the two
HALF-range sites ([MELTA X]'s damage bonus and [RAPID FIRE X]'s extra attacks)
still read the printed range because no pulse carbine had either keyword - "if
one ever does, they need the same treatment". Burning Lance is that case: it
modifies the Range characteristic of [MELTA] weapons, so half of it is half of
the new number. Routing all three through here discharges that note instead of
leaving the next reader to rediscover it.
"""

from game import burning_lance, pulse_accelerator


def effective_range_in(model, weapon):
    """This weapon's Range characteristic as it stands for this wielder now.

    Takes the MODEL rather than the squad so callers can pass what they already
    have on the hot path, and so a model with no squad degrades to the printed
    range instead of raising."""
    return (pulse_accelerator.effective_range_in(model, weapon)
            + burning_lance.bonus_for(model, weapon))


def half_range_in(model, weapon):
    """Half the above - the distance [MELTA X] and [RAPID FIRE X] measure.

    Its own function rather than a division at each call site, because "half
    range" is a printed phrase that both keywords name, and having it read the
    modified characteristic is the whole substance of this module."""
    return effective_range_in(model, weapon) / 2
