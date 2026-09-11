"""'You can re-roll Charge rolls made for this unit' - the shared machinery.

TWO CARRIERS, which is why this exists:

  * Triarch Praetorians' "Relentless Combatants" (stage 4), whose predicate is
    rule 19.04's component-wise unit_wide_ability();
  * The Silent King's "Phaeron of the Blades" (stage 9), whose predicate is an
    AURA - a friendly NECRONS unit (excluding MONSTER units) within 6" of
    Szarekh, and only while that Triarch ability is the one selected this
    battle round.

The predicates could hardly be less alike, and everything else is identical.
game/relentless_combatants.py keeps its own predicate and re-exports its label
and its MAX_CHARGE_ROLL_TOTAL, so none of its call sites move.

WHAT IS SHARED IS EXACTLY WHAT IS EASY TO GET SUBTLY WRONG, and every line of
it was paid for once already by the first carrier:

  * IT IS OFFERED BEFORE acknowledge(), and only there. acknowledge() clears
    DiceManager.pending_values and reroll_all() then refuses to throw anything,
    so a re-roll offered one line later is an offer that cannot be taken.
  * IT IS CLAIMED ONCE PER ROLL, through DiceManager.claim_reroll_offer().
    Declining leaves EXACTLY the board that produced the question, so without
    the claim the next click asks again - the reported infinite loop that
    helper exists for, and re-rolling was the only answer that ended it. The
    claim is keyed by LABEL, so two carriers may each ask once about the same
    roll; no unit can hold both today, and the suite pins that rather than
    leaving it to luck.
  * IT IS ALL OR NOTHING. A Charge roll is 2D6 and rule 15.02's own wording
    for re-rolling one is "must be re-rolled in full", so reroll_all() rather
    than picking a die - and can_reroll_all() refuses once any single die has
    been thrown twice, which keeps a Command Re-roll and this from stacking.
  * THE AI ANSWERS IT DETERMINISTICALLY IN BOTH DIRECTIONS, and its rule is
    NARROWER than the CP-paying one in ai/agent_driver.py because this re-roll
    is FREE: re-roll only when the roll reached NOTHING and a maximum roll
    could reach something; KEEP a roll that reached something (all-or-nothing
    means a free re-roll can still lose a live charge); and do not ask at all
    when nothing is reachable even on a 12. A HUMAN is still asked in the
    middle case - trading a hit for a longer one is a real judgement.

A SUBCLASS OWNS TWO THINGS, as class attributes rather than constructor
arguments so that forgetting one fails loudly at definition time instead of
quietly offering a nameless re-roll: LABEL, and applies().
"""

from game import ai_mode

#: A Charge roll is 2D6, so this is the best it can possibly come out - used
#: only to ask "could a re-roll reach anything AT ALL", never as a result.
MAX_CHARGE_ROLL_TOTAL = 12


class ChargeRerollController:
    LABEL = None

    def __init__(self, dice_manager=None, decision_manager=None,
                 charge_controller=None, game_log=None, auto_players=(),
                 game_state=None):
        if not self.LABEL:
            raise TypeError("%s must set LABEL" % type(self).__name__)
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.charge_controller = charge_controller
        self.game_log = game_log
        self.game_state = game_state
        self.auto_players = ai_mode.players(auto_players)

    # ------------------------------------------------------------- subclass
    def applies(self, squad):
        """Whether this unit may re-roll its Charge roll right now."""
        raise NotImplementedError

    # ------------------------------------------------------------- plumbing
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
        if not self.applies(squad):
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
                      % (self.LABEL, squad.name, MAX_CHARGE_ROLL_TOTAL),
                      file_only=True)
            return False
        if not self.dice_manager.claim_reroll_offer(self.LABEL):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return bool(self._reroll(squad, rolled))
        self.decision_manager.request(
            squad.owner,
            '%s rolled %d" for its charge - re-roll it in full? (%s)'
            % (squad.name, rolled, self.LABEL),
            [("Re-roll the Charge roll", lambda: self._reroll(squad, rolled)),
             ("Keep it", None)],
        )
        return True

    def _reroll(self, squad, rolled):
        if not self.dice_manager.reroll_all():
            return False
        self._log('%s (%s): charge roll of %d" re-rolled in full -> %d".'
                  % (self.LABEL, squad.name, rolled,
                     sum(self.dice_manager.pending_values)))
        return True
