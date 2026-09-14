"""'You can re-roll Advance rolls made for this unit' - the shared machinery.

CARRIERS:

  * The Autarch's "Superlative Strategist" (game/superlative_strategist.py) -
    while he is LEADING the unit;
  * The Orks army rule "Waaagh!" (game/waaagh.py) - every unit with the ability,
    always ("Friendly ORKS units with this ability can: re-roll advance rolls").

Protocol of the Sudden Storm (game/protocol_sudden_storm.py) prints the same
clause and is NOT folded in here: it lives on a Stratagem controller, its grant
is a phase-scoped flag the Stratagem sets, and its re-roll is a second effect of
a purchase rather than an ability of its own. It keeps its own copy of the
offer and asks the same DiceManager seams, so the three cannot disagree about
WHEN an Advance may be re-rolled.

This is game/charge_reroll.py's shape one roll type over, and what is shared is
exactly what was paid for once already:

  * IT IS OFFERED BEFORE acknowledge(), and only there. acknowledge() clears
    DiceManager.pending_values and reroll_die() then refuses to throw anything,
    so an offer made one line later cannot be taken. main.py's
    _acknowledge_pending_roll() makes it.
  * IT IS CLAIMED ONCE PER ROLL, through DiceManager.claim_reroll_offer().
    Declining leaves exactly the board that produced the question, so without
    the claim the next click asks again - the reported loop that helper exists
    for. The claim is keyed by LABEL, so two carriers may each ask once.
  * A DIE THAT WAS ALREADY RE-ROLLED IS LEFT ALONE (rerollable_indices()), so a
    Command Re-roll and this can never both throw the same die.
  * THE AI ANSWERS DETERMINISTICALLY: a D6 averages 3.5, so a die below
    ADVANCE_REROLL_FLOOR is thrown again and the rest kept.

A SUBCLASS OWNS TWO THINGS, as class attributes rather than constructor
arguments so that forgetting one fails loudly: LABEL, and applies().
"""

from game import ai_mode

#: A D6 averages 3.5, so 4+ is not worth throwing again.
ADVANCE_REROLL_FLOOR = 4


class AdvanceRerollOfferController:
    LABEL = None

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 auto_players=()):
        if not self.LABEL:
            raise TypeError("%s must set LABEL" % type(self).__name__)
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)

    # ------------------------------------------------------------- subclass
    def applies(self, squad):
        """Whether this unit may re-roll its Advance roll right now."""
        raise NotImplementedError

    # ------------------------------------------------------------- the offer
    def maybe_offer_advance_reroll(self, squad):
        """Called from main.py while the Advance roll is still PENDING.

        Returns True when it either threw the die or opened a prompt, so the
        caller knows not to acknowledge a roll that is being replaced."""
        if not self._offerable(squad):
            return False
        values = self.dice_manager.pending_values
        if not self.dice_manager.claim_reroll_offer(self.LABEL):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            if values[0] >= ADVANCE_REROLL_FLOOR:
                return False
            return bool(self._reroll(squad))
        self.decision_manager.request(
            squad.owner,
            '%s advanced %d" - re-roll it? (%s)' % (squad.name, values[0], self.LABEL),
            [("Re-roll the Advance", lambda: self._reroll(squad)),
             ("Keep it", None)],
        )
        return True

    def _offerable(self, squad):
        """Every gate of the offer except "has it already been made" - read by
        the prompt path and by the dice panel's button, so the two cannot
        disagree about when the Advance may be re-rolled."""
        dm = self.dice_manager
        return (dm is not None and squad is not None and self.applies(squad)
                and bool(dm.rerollable_indices()) and bool(dm.pending_values))

    def pending_roll_choice(self, squad):
        """The dice panel's version of maybe_offer_advance_reroll() for a HUMAN
        - a "Re-roll Advance" button beside Accept while the roll is on the
        table (game/roll_choice.py). Pressing it claims the offer and throws
        the die in place; Accept claims it on the player's behalf, so the
        prompt does not open afterwards either."""
        from game import roll_choice
        from game.dice import ADVANCE_ROLL
        dm = self.dice_manager
        if (not self._offerable(squad) or dm.roll_kind != ADVANCE_ROLL
                or squad.owner in self.auto_players or self.decision_manager is None
                or dm.reroll_offer_claimed(self.LABEL)):
            return None
        return roll_choice.RollChoice(squad.owner, [
            roll_choice.RollOption(roll_choice.ACCEPT),
            roll_choice.RollOption(roll_choice.WHOLE, 1, label="Re-roll Advance", acknowledges=False,
                                   apply=lambda: self._reroll_from_panel(squad)),
        ], claims=(self.LABEL,))

    def _reroll_from_panel(self, squad):
        if self.dice_manager.claim_reroll_offer(self.LABEL):
            self._reroll(squad)

    def _reroll(self, squad):
        thrown = self.dice_manager.reroll_die(0)
        if thrown and self.game_log is not None:
            self.game_log.add("%s: %s re-rolls its Advance." % (self.LABEL, squad.name))
        return thrown
