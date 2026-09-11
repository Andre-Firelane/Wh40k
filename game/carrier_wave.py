"""Catacomb Command Barge: "Carrier Wave (Aura)".

RULE (verbatim, rules/necrons/Catacomb Command Barge.md):
  "While a friendly NECRONS unit is within 6" of this model, add 1 to the
   Objective Control characteristic of models in that unit."

AN ADDER IN game/objective_control.py's effective_oc(), and the FIRST one that
is a DATASHEET AURA rather than an Enhancement. It lands in the last of that
function's three documented steps (setters replace, Scabrous Soulrot worsens,
adders add), for the reason written there: the additions come last so a +1
always buys one rather than being clamped away by a floor or overwritten by a
setter.

NO SQUAD FLAG, AND THAT IS MEASURED RATHER THAN ASSUMED. The house pattern for
an aura whose consumer takes no token list is to stamp a per-frame flag onto
the Squad - game/plagues.py's Afflicted, game/fnp_aura.py, Admired Leader.
That pattern exists because current_feel_no_pain() and leadership_threshold()
have well over a dozen callers between them and none of them carries the
board. effective_oc() is NOT in that position: it has exactly THREE call sites
- objectives.py's Objective.level_of_control(), which is the only engine one,
and two in ai/agent_driver.py - and all three already pass `all_tokens`. A
stamped flag here would be a second answer to a question the live board can
already answer, and the AI asks OC against live positions.

"A FRIENDLY NECRONS UNIT" IS THE DATASHEET READING. It goes through
awakened_dynasty.is_necrons_unit(), which reads the datasheet keyword line, and
NOT through the per-model `reanimation_protocols` flag. Those two agree on every
built datasheet, but they are different questions, and CLAUDE.md already records
four definitions of "is this a NECRONS unit" across this faction as an open
consolidation - this does not make it five. Grand Illusion (stage 6) made the
same call for the same reason.

THE BEARER'S OWN UNIT IS NOT EXCLUDED: the printed word is "a friendly NECRONS
unit", not "ANOTHER friendly NECRONS unit". Nekrosor Ammentar's Protective
Disciples, three lines away on another Necron sheet, DOES say "other" - so the
absence here is a real distinction and not an oversight. A lone Barge is OC3
and becomes OC4.

TWO DIFFERENT DISTANCES IN ONE SENTENCE, and conflating them is the easy
mistake: the UNIT qualifies if it is "within 6"", which needs only ONE of its
models in range; then "the Objective Control characteristic of MODELS IN THAT
UNIT" is raised for EVERY model of it, including one standing twenty inches
away. A test that puts the whole unit inside the aura cannot tell the two
readings apart, so the suite deliberately leaves a straggler behind.

THE AURA IS MEASURED FROM THE MODEL ("within 6" of this model"), edge to edge
like every other range in this engine.
"""

from game import awakened_dynasty
from game.squad import edge_distance

CARRIER_WAVE_RANGE_IN = 6.0
CARRIER_WAVE_OC_BONUS = 1
CARRIER_WAVE_LABEL = "Carrier Wave"


def bearers(all_tokens):
    """Every living Carrier Wave model on the board."""
    return [t for t in (all_tokens or ())
            if getattr(t.profile, "carrier_wave", False) and not t.is_dead()]


def oc_bonus(model, all_tokens=None):
    """+1 if this model's unit is a friendly NECRONS unit within 6" of a
    Carrier Wave bearer, else 0.

    "Friendly" is same-owner. The bearer's own unit qualifies (see the module
    docstring), so no identity test excludes it."""
    squad = getattr(model, "squad", None)
    if squad is None or not all_tokens:
        return 0
    if not awakened_dynasty.is_necrons_unit(squad):
        return 0
    for bearer in bearers(all_tokens):
        if bearer.squad is None or bearer.squad.owner != squad.owner:
            continue
        # "within 6" of this model" qualifies the UNIT: one model in range is
        # enough, and then every model of that unit gets the bonus - which is
        # why this asks about the squad's models rather than about `model`.
        if any(edge_distance(m, bearer) <= CARRIER_WAVE_RANGE_IN
               for m in squad.models if not m.is_dead()):
            return CARRIER_WAVE_OC_BONUS
    return 0
