"""Blitz Brigade Stratagem: Keep It Runnin' (1CP, Mecha Orks stage G4).

RULE (verbatim, rules/orks/detachments/Blitz Brigade.md):
  WHEN:   End of the Fight phase.
  TARGET: One friendly unengaged ORKS INFANTRY unit that was eligible to fight
          this phase and is wholly within 6" of a friendly TRANSPORT unit that
          INFANTRY unit is able to embark within.
  EFFECT: Your INFANTRY unit embarks within that TRANSPORT unit.

THE THIRD PRINTING OF ONE MECHANISM. The Aeldari print this sentence twice as
Skyborne Sanctuary; the mechanism - the end-of-Fight PhaseWindow, both players
offered ("End of THE Fight phase"), the board pick then the transport list,
can_embark(require_move=False, range_in=6.0) for "able to embark within" and
"wholly within 6"", "unengaged" and "eligible to fight" as two clauses - moved to
game/end_of_fight_embark.py with this card's arrival, and this module is the Ork
knobs: the name, the cost, and the TARGET's own words, "friendly ... ORKS
INFANTRY unit" of a player fielding Blitz Brigade.

"THAT INFANTRY UNIT IS ABLE TO EMBARK WITHIN" also brings the transports' own
bans: a Trukk refuses GHAZGHKULL THRAKA, a Kill Rig takes only BEAST SNAGGA -
TransportController.can_embark() answers both, unchanged.

THE AI DECLINES - game/unit_choice_offer.py raises no prompt for an auto player,
by design (taking a unit off the board unasked is a real cost). Named here, and
in the stage's documentation, rather than left to be discovered.
"""

from game import blitz_brigade, ork_units
from game.end_of_fight_embark import EndOfFightEmbarkController

KEEP_IT_RUNNIN_NAME = "Keep It Runnin'"
KEEP_IT_RUNNIN_CP = 1
#: "wholly within 6" of a friendly TRANSPORT unit".
KEEP_IT_RUNNIN_RANGE_IN = 6.0


def eligible_unit(squad):
    """"One friendly ... ORKS INFANTRY unit" of a player fielding Blitz Brigade."""
    return (squad is not None and blitz_brigade.fields_blitz_brigade(getattr(squad, "owner", None))
            and ork_units.is_orks_infantry_unit(squad))


class KeepItRunninController(EndOfFightEmbarkController):
    NAME = KEEP_IT_RUNNIN_NAME
    CP = KEEP_IT_RUNNIN_CP
    RANGE_IN = KEEP_IT_RUNNIN_RANGE_IN

    def eligible_unit(self, squad):
        return eligible_unit(squad)
