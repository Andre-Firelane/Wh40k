"""The Autarch's "Superlative Strategist" - a datasheet ability.

RULE (printed, word for word):
  "While this model is leading a unit, you can re-roll Advance rolls made for
  that unit, and you can re-roll any rolls made for that unit while it is
  performing an Agile Manoeuvre."

TWO CLAUSES, AND ONLY THE FIRST IS WIRED
-----------------------------------------
  * THE ADVANCE RE-ROLL is built, and it shares its seam with Protocol of the
    Sudden Storm - see the note below, because that seam did not previously
    exist.
  * "ANY ROLLS MADE FOR THAT UNIT WHILE IT IS PERFORMING AN AGILE MANOEUVRE" is
    NOT modelled. game/battle_focus.py's manoeuvres are resolved without a dice
    step of their own - the six are movement and eligibility effects, and the
    only dice they touch belong to the move or the shot that follows, which are
    not "rolls made while performing the manoeuvre". There is no roll here to
    re-roll, so the clause has nothing to attach to. Named rather than dropped,
    the same treatment Trail Finding and Jammer Array get.

THE SEAM THIS NEEDED DID NOT EXIST, AND ITS ABSENCE WAS A LIVE BUG
-------------------------------------------------------------------
game/protocol_sudden_storm.py has had maybe_offer_advance_reroll() since the
Necron work. It is unit-tested and was never called from main.py - the "built
but never FED" failure this repo has now hit five times, and which only a
source-level guard can see.

Worse, its own docstring says it is "called from main.py right after an Advance
roll is acknowledged", and that could not have worked either:
DiceManager.acknowledge() clears pending_values, and reroll_die() refuses a
roll with none. So the offer has to come BEFORE the acknowledgement, which is
where main.py now makes it - for both abilities, from one place.

THE AI ANSWERS IT DETERMINISTICALLY, so nothing stalls and there is no path in
ai/: a D6 Advance averages 3.5, so anything below ADVANCE_REROLL_FLOOR is
re-rolled and the rest kept - the same "re-rolling an average result wins
nothing" reasoning Sudden Storm and Reanimation Protocols already use.
"""
from game.attached_units import leader_ability
from game import ai_mode

SUPERLATIVE_STRATEGIST_LABEL = "Superlative Strategist"

#: A D6 averages 3.5, so 4+ is not worth throwing again.
ADVANCE_REROLL_FLOOR = 4


def applies(squad):
    """"While this model is LEADING a unit" - so 24.22's leader question, not
    a plain flag check: an Autarch standing alone grants nothing, and a
    bodyguard model never carries it."""
    return bool(squad is not None and leader_ability(squad, "superlative_strategist"))


class SuperlativeStrategistController:
    """The Advance re-roll offer. One per battle."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)

    def maybe_offer_advance_reroll(self, squad):
        """Called from main.py while the Advance roll is still PENDING.

        Returns True when it either threw the die or opened a prompt, so the
        caller knows not to acknowledge a roll that is being replaced."""
        if self.dice_manager is None or not applies(squad):
            return False
        if not self.dice_manager.rerollable_indices():
            return False
        values = self.dice_manager.pending_values or []
        if not values:
            return False
        # ONCE per roll - see DiceManager.claim_reroll_offer(). Both Advance
        # re-roll offers share that seam, so neither can loop.
        if not self.dice_manager.claim_reroll_offer(SUPERLATIVE_STRATEGIST_LABEL):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            if values[0] >= ADVANCE_REROLL_FLOOR:
                return False
            return bool(self._reroll(squad))
        self.decision_manager.request(
            squad.owner,
            '%s advanced %d" - re-roll it? (%s)'
            % (squad.name, values[0], SUPERLATIVE_STRATEGIST_LABEL),
            [("Re-roll the Advance", lambda: self._reroll(squad)),
             ("Keep it", None)],
        )
        return True

    def _reroll(self, squad):
        thrown = self.dice_manager.reroll_die(0)
        if thrown and self.game_log is not None:
            self.game_log.add("%s: %s re-rolls its Advance."
                              % (SUPERLATIVE_STRATEGIST_LABEL, squad.name))
        return thrown
