"""Skyborne Sanctuary (1CP, Strategic Ploy) - printed by TWO detachments.

RULE (verbatim, and byte-identical in rules/aeldari/detachments/Warhost.md and
rules/aeldari/detachments/Aspect Host.md apart from one comma in the flavour
line):
  WHEN:   End of the Fight phase.
  TARGET: One unengaged ASURYANI unit from your army that was eligible to fight
          this phase and one friendly TRANSPORT it is able to embark within.
  EFFECT: If your ASURYANI unit is wholly within 6" of that TRANSPORT, it can
          embark within it.
  RESTRICTIONS: none printed.

THE TARGET LINE NAMES TWO THINGS, SO THE OFFER ASKS TWICE. It used to ask
neither: it raised a prompt about whichever eligible unit sorted FIRST and took
`transports_for(squad)[0]` for the transport, silently. Step one is now a board
pick over every eligible unit (game/unit_choice_offer.py, shared with the three
sibling Stratagems that print the same "One <X> unit from your army"); step two
is an ordinary list, and only when there is more than one legal transport -
never offer what cannot be chosen. That the old one-step prompt read correctly
wherever exactly one Wave Serpent was in range is why it survived.

ONE MODULE, TWO CONTROLLER INSTANCES - the arrangement game/enh_exemplars.py
already uses for the two Exemplars. Two copies of a Stratagem that is the same
sentence twice is the drift this repo consolidates at the second consumer, and
the only thing that differs between the two printings is which config constant
gates it, which is a constructor argument rather than a second file.

"IT IS ABLE TO EMBARK WITHIN" IS THE TRANSPORT'S OWN QUESTION, not a new one.
TransportController.can_embark() already owns capacity, the keyword bans and
rule 18.02's "not set up this turn" - so this asks it rather than re-deriving
any of that, and passes the two things the printed text overrides:

  * require_move=False, because 18.02's "after it has made a Normal move this
    phase" cannot be satisfied at the end of the Fight phase - the unit's move
    was two phases ago. That the Stratagem is about a moment where the normal
    permission cannot apply is the whole reason it exists.
  * range_in=6.0, because the printed distance is 6" and not the ordinary 3".

Both were added to can_embark() as named parameters beside its existing ones,
so every other caller keeps meaning exactly what it did.

"WHOLLY WITHIN 6"" IS THE STRICTER READING, and it is the one printed. WITHIN
would let one model's toe do it; wholly within means every model. This repo has
a whole test section on that distinction because the two look alike and the
wrong one passes any test that puts a unit clearly inside or clearly outside.
can_embark()'s range test is already per model, so passing range_in gets the
strict reading for free - measured rather than assumed, with a straggler.

"UNENGAGED" AND "ELIGIBLE TO FIGHT THIS PHASE" ARE DIFFERENT CLAUSES AND BOTH
ARE CHECKED. A unit can be eligible to fight and still be unengaged by the end
of the phase - it consolidated away, or everything near it died - and that is
precisely the unit this Stratagem is for. Engagement is asked of
game/engagement.py; eligibility is asked of the FightController, which owns
rule 12.04's sticky engaged_at_start set and is the only thing that can still
answer once the phase is over.

"END OF THE FIGHT PHASE", not "your Fight phase" - it belongs to nobody, so
both players are offered it at the same boundary and there is no owner check.

THE WINDOW IS A FACT THIS MODULE OWNS, NOT A LIVE PHASE TEST. This used to read

    if self.turn_tracker.phase != PHASE_FIGHT:
        return False

and that check could never hold. Its only offer is main.py's advance_turn_phase(),
which calls turn_tracker.advance_phase() FIRST and only then runs the
end-of-phase offers - and Fight is the LAST phase, so by the time the offer is
made the clock has rolled all the way round to Command. Both printings of this
Stratagem were therefore a guaranteed, silent no-op: never offered, for either
detachment. Same shape, same cause and same fix as Cost of Victory and Webway
Tunnel before it - see game/phase_window.py.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, detachment_gate
from game.end_of_fight_embark import EndOfFightEmbarkController

SKYBORNE_SANCTUARY_NAME = "Skyborne Sanctuary"
SKYBORNE_SANCTUARY_CP = 1

#: 'wholly within 6"' - the printed distance, overriding the ordinary 3".
SKYBORNE_SANCTUARY_RANGE_IN = 6.0


def eligible_unit(squad, setting):
    """"One unengaged ASURYANI unit from your army"."""
    if squad is None or not detachment_gate.has_detachment(
            getattr(squad, "owner", None), setting):
        return False
    return aeldari_detachments.is_asuryani_unit(squad)


class SkyborneSanctuaryController(EndOfFightEmbarkController):
    """The end-of-Fight-phase offer. Built once per detachment that prints it,
    each with its own `setting`. The mechanism is
    game/end_of_fight_embark.py's (moved there when the Orks' Keep It Runnin'
    became its third printing); this class owns the name, the cost, the
    distance and the ASURYANI TARGET."""

    NAME = SKYBORNE_SANCTUARY_NAME
    CP = SKYBORNE_SANCTUARY_CP
    RANGE_IN = SKYBORNE_SANCTUARY_RANGE_IN

    def __init__(self, stratagem_controller, setting, **kwargs):
        super().__init__(stratagem_controller, **kwargs)
        #: Which detachment's copy this instance is - the ONLY difference
        #: between the two printings.
        self.setting = setting

    def eligible_unit(self, squad):
        return eligible_unit(squad, self.setting)
