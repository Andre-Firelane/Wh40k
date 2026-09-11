"""Drain Life - the C'tan Shard of the Nightbringer's own ability.

RULE (printed, word for word):

  "At the end of the Fight phase, roll one D6 for each enemy unit within 6" of
   this model: on a 4+, that enemy unit suffers D3 mortal wounds."

The whole machine is game/mortal_wound_sweep.py's - this file is the four
printed numbers and nothing else, the same way game/conclave_crushing_strides.py
is the sixth carrier of the one-target base next door.

THREE THINGS THE PRINTED TEXT SAYS THAT A COPY WOULD LOSE:

  * "AT THE END OF THE FIGHT PHASE", not "of YOUR Fight phase". The Fight phase
    belongs to nobody (12.04 alternates within it), so this fires ONCE per
    Fight phase and a Nightbringer drains at the end of its owner's turn and
    its opponent's alike. That is why main.py calls it from the
    `phase_before == PHASE_FIGHT` block WITHOUT `mover_before`, next to
    Illuminor Szeras's Atomic Energy, and not from any of the four offers below
    it that do take a side.

  * NO "YOU CAN". It is not optional and there is nothing to ask - so there is
    no prompt, no auto_players split and no decline. Same reading Crimson
    Harvest records for its own "select": the absence of those two words is the
    whole difference between an offer and an event.

  * "EACH ENEMY UNIT", so there is no target choice either. That is what makes
    this a sweep rather than another MortalWoundOfferController carrier.

ONCE PER PHASE NEEDS NO LEDGER. The trigger IS the limit: there is exactly one
end of the Fight phase per phase, and main.py's block runs once at that
boundary. A ledger on top would be a second answer to a question the boundary
already answers - the reasoning Crimson Harvest gives for deliberately not
having one.
"""

from game.dice_notation import D3
from game.mortal_wound_sweep import MortalWoundSweepController

DRAIN_LIFE_RANGE_IN = 6.0
DRAIN_LIFE_THRESHOLD = 4      # "on a 4+"
DRAIN_LIFE_SIDES = 3          # "D3 mortal wounds"


def has_drain_life(squad):
    """Whether this unit contains a living Nightbringer."""
    from game.mortal_wound_abilities import bearers
    return bool(bearers(squad, "drain_life"))


class DrainLifeController(MortalWoundSweepController):
    label = "Drain Life"
    flag = "drain_life"
    range_in = DRAIN_LIFE_RANGE_IN
    threshold = DRAIN_LIFE_THRESHOLD

    def wounds_for(self, roll):
        """One band. `roll` is only ever a die that already met the 4+, so
        there is nothing left to compare."""
        return D3()

    def resolve_end_of_fight_phase(self, squads):
        """main.py's hook. Takes every squad on the board rather than one
        side's, because the phase belongs to neither player - see the module
        docstring."""
        return self.start_many(squads)
