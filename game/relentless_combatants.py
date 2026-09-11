"""Triarch Praetorians' own ability "Relentless Combatants" (Necrons).

RULE (printed, word for word):

  "You can re-roll Charge rolls made for this unit, and this unit is eligible
   to declare a charge in a turn in which it Fell Back."

ONE SENTENCE, TWO CLAUSES, TWO SEAMS - and they are not near each other.

CLAUSE 2 IS THE CHEAP ONE, AND IT ALREADY HAD A HOME.
game/move_exceptions.py owns "who is exempt from rule 09.07's charge ban", and
this joins its predicate chain beside Full Throttle and Hovering Death. What is
new is only WHO: every datasheet source in that fold today is T'au or Ork, and
this is the first NECRON one. The fold is a set rather than an inline `or`
chain precisely so a new source registers in one place - see that module's own
docstring for the three burns behind it.

CLAUSE 1 IS THE ONE WITH REAL WORK IN IT, and its shape is Protocol of the
Sudden Storm's Advance re-roll (game/protocol_sudden_storm.py), one roll kind
over:

  * IT IS OFFERED BEFORE acknowledge(), and only there. acknowledge() clears
    DiceManager.pending_values, and reroll_all() then refuses to throw
    anything - so a re-roll offered one line later is an offer that cannot be
    taken. main.py holds the roll un-acknowledged while a human prompt is open.
  * IT IS CLAIMED ONCE PER ROLL, through DiceManager.claim_reroll_offer().
    Declining leaves EXACTLY the board that produced the question, so without
    the claim the next click asks again - the reported infinite loop that
    helper exists for, and re-rolling was the only answer that ended it.
  * IT IS ALL OR NOTHING. A Charge roll is 2D6 and rule 15.02's own wording
    for re-rolling one is "must be re-rolled in full", so this uses
    reroll_all() rather than picking a die - and can_reroll_all() refuses once
    any single die of the roll has already been thrown twice, which is what
    keeps a Command Re-roll and this one from stacking on the same dice.

THE AI ANSWERS IT DETERMINISTICALLY, IN BOTH DIRECTIONS, so it costs no API
call either way - and the rule it uses is narrower than the CP-paying one in
ai/agent_driver.py because this re-roll is FREE:

  * the roll reached NOTHING and a maximum roll could reach something
    -> re-roll, because a free re-roll of a failed charge risks nothing.
  * the roll reached something -> KEEP it. Re-rolling is all-or-nothing, so
    this would gamble a live charge away; free does not make that good. A
    HUMAN is still asked, because trading a hit for a longer one is a real
    judgement - the same split ai/agent_driver.py's CP verdict makes at
    exactly this point.
  * nothing is reachable even on a 12 -> keep, and do not ask AT ALL. Never
    offer what cannot buy anything (the standing rule); here it is also the
    honest answer, since the charge is already lost.

Both answers come from ChargeController.targets_reachable_with(), the REAL
rule 11.04 gate asked about a roll that has not been acknowledged yet, rather
than from a second copy of the reachability arithmetic.

"MADE FOR THIS UNIT" is read through rule 19.04 (unit_wide_ability), like
every other whole-unit datasheet ability here: a Praetorian unit keeps the
ability while the component that prints it is still conferring, and a leader
attached to it does not dilute it.
"""

from game.charge_reroll import MAX_CHARGE_ROLL_TOTAL, ChargeRerollController
from game.squad import unit_wide_ability

RELENTLESS_COMBATANTS_LABEL = "Relentless Combatants"

#: Re-exported from game/charge_reroll.py (the 51st extraction), where the
#: whole "re-roll Charge rolls made for this unit" machinery now lives - The
#: Silent King's Phaeron of the Blades is the second carrier. Kept under the
#: old name so no reader of this module moves.
MAX_CHARGE_ROLL_TOTAL = MAX_CHARGE_ROLL_TOTAL


def squad_has_relentless_combatants(squad):
    """Whether this unit has the ability, under rule 19.04's component-wise
    reading - the same helper every other whole-unit datasheet ability uses.

    Read by game/move_exceptions.py's may_charge_after_falling_back() for the
    second clause, and by the controller below for the first."""
    if squad is None:
        return False
    return unit_wide_ability(squad, "relentless_combatants")


class RelentlessCombatantsController(ChargeRerollController):
    """Clause 1 only. Clause 2 needs no controller at all - it is a predicate
    that game/move_exceptions.py asks.

    Everything this used to spell out by hand is in ChargeRerollController
    now; what is left is the two knobs a carrier owns. Behaviour is unchanged
    by construction - the base class is this class's own body, moved."""

    LABEL = RELENTLESS_COMBATANTS_LABEL

    def applies(self, squad):
        return squad_has_relentless_combatants(squad)
