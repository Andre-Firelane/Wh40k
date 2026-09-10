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

from game import ai_mode
from game.squad import unit_wide_ability

RELENTLESS_COMBATANTS_LABEL = "Relentless Combatants"

#: A Charge roll is 2D6, so this is the best it can possibly come out - used
#: only to ask "could a re-roll reach anything AT ALL", never as a result.
MAX_CHARGE_ROLL_TOTAL = 12


def squad_has_relentless_combatants(squad):
    """Whether this unit has the ability, under rule 19.04's component-wise
    reading - the same helper every other whole-unit datasheet ability uses.

    Read by game/move_exceptions.py's may_charge_after_falling_back() for the
    second clause, and by the controller below for the first."""
    if squad is None:
        return False
    return unit_wide_ability(squad, "relentless_combatants")


class RelentlessCombatantsController:
    """Clause 1 only. Clause 2 needs no controller at all - it is a predicate
    that game/move_exceptions.py asks."""

    def __init__(self, dice_manager=None, decision_manager=None,
                 charge_controller=None, game_log=None, auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.charge_controller = charge_controller
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def charging_squad(self):
        return getattr(self.charge_controller, "active_squad", None)

    def can_offer(self, squad):
        """Every gate except "has this offer already been made", which is
        DiceManager's to answer and must not be asked twice."""
        if self.dice_manager is None or self.charge_controller is None:
            return False
        if not squad_has_relentless_combatants(squad):
            return False
        if not self.dice_manager.can_reroll_all():
            return False
        return bool(self.dice_manager.pending_values)

    def maybe_offer_charge_reroll(self, squad=None):
        """Called from main.py the instant a Charge roll is about to be
        acknowledged - and only there, see this module's docstring.

        `squad` defaults to whoever is charging, which is the only unit whose
        Charge roll this can be."""
        squad = self.charging_squad() if squad is None else squad
        if not self.can_offer(squad):
            return False
        rolled = sum(self.dice_manager.pending_values)
        if self.charge_controller.targets_reachable_with(rolled):
            if squad.owner in self.auto_players or self.decision_manager is None:
                return False
        elif not self.charge_controller.targets_reachable_with(MAX_CHARGE_ROLL_TOTAL):
            self._log('%s (%s): no unit is within reach even on a %d" charge roll, '
                      'so the re-roll is not offered.'
                      % (RELENTLESS_COMBATANTS_LABEL, squad.name, MAX_CHARGE_ROLL_TOTAL),
                      file_only=True)
            return False
        # ONCE per roll. Declining used to leave the dice on the table with
        # nothing changed, so the next click asked again - see
        # DiceManager.claim_reroll_offer().
        if not self.dice_manager.claim_reroll_offer(RELENTLESS_COMBATANTS_LABEL):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return bool(self._reroll(squad, rolled))
        self.decision_manager.request(
            squad.owner,
            '%s rolled %d" for its charge - re-roll it in full? (%s)'
            % (squad.name, rolled, RELENTLESS_COMBATANTS_LABEL),
            [("Re-roll the Charge roll", lambda: self._reroll(squad, rolled)),
             ("Keep it", None)],
        )
        return True

    def _reroll(self, squad, rolled):
        if not self.dice_manager.reroll_all():
            return False
        self._log('%s (%s): charge roll of %d" re-rolled in full -> %d".'
                  % (RELENTLESS_COMBATANTS_LABEL, squad.name, rolled,
                     sum(self.dice_manager.pending_values)))
        return True
