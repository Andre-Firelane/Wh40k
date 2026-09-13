"""Hypercrypt Legion's "Hyperphasing" - the detachment rule.

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md, with its errata
table as printed):
  "At the end of your opponent's turn, you can select a number of NECRONS units
   from your army (excluding units that are within Engagement Range of one or
   more enemy units). The maximum number of units you can select depends on the
   battle size, as follows:
     Incursion: Up to 1 unit
     Strike Force: Up to 2 units
     Onslaught: Up to 3 units
   Once you have made your selections, remove those units from the battlefield
   and place them into Strategic Reserves."

WINDRIDER HOST'S RIDE THE WIND PRINTS THE SAME PARAGRAPH for ASURYANI MOUNTED
and VYPER units, so the machinery is game/end_of_turn_withdrawal.py - extracted
at this, its second consumer: the chained one-prompt-per-unit offer, the cap
re-read before each prompt, the counter that resets only at the start of the
offer, the Engagement Range exclusion and the withdrawal itself. What this
module owns is the unit filter, the cap and the words.

"NECRONS UNITS FROM YOUR ARMY" that are ON THE BATTLEFIELD: "remove those units
from the battlefield" presupposes it. A unit already in reserves is refused by
the base class, and an EMBARKED unit here - whose models are not on the board -
is refused by applies(): taking a passenger out of its transport into reserves
is not something the printed text offers.

THE CAP is game/battle_size.py's reading of the setting against this rule's
own table, plus the Dimensional Overseer's +1 (game/enh_dimensional_overseer.py)
for the army that carries it - which is why limit() takes the player.

THE AI USES IT (user decision: "Retten + Umpositionieren"), and the policy is
ai/agent_driver.py's hyperphasing_choice(), injected by main.py as `choose`
because game/ must not import ai/. Two facts the policy needs are RULE facts
and live here instead, so a test can pin them without the AI:

  * withdrawal_is_doomed() - rule 20.03 destroys every unit still in Strategic
    Reserves at the end of battle round 3, and main.py runs that destruction in
    the same advance_turn_phase() call as the end-of-turn offers. A unit
    withdrawn at the end of round 3 never gets a Movement phase to arrive in.
  * misses_next_arrival() - rule 20.03 also forbids arriving before battle
    round 2, so a unit withdrawn at the end of the opponent's first-round turn
    skips its owner's next Movement phase entirely.
"""

from game import battle_size as battle_size_module
from game import enh_dimensional_overseer, necron_detachments
from game.end_of_turn_withdrawal import EndOfTurnWithdrawalController

HYPERPHASING_LABEL = "Hyperphasing"
SETTING = "HYPERCRYPT_LEGION_PLAYERS"

#: The errata table: "Incursion: Up to 1 unit / Strike Force: Up to 2 units /
#: Onslaught: Up to 3 units".
UNITS_BY_BATTLE_SIZE = {
    battle_size_module.INCURSION: 1,
    battle_size_module.STRIKE_FORCE: 2,
    battle_size_module.ONSLAUGHT: 3,
}

#: Rule 20.03: "At the end of the third battle round ... all strategic reserves
#: units that have not made one or more ingress moves are destroyed."
RESERVES_DESTROYED_AFTER_ROUND = 3


def has_detachment(player):
    return necron_detachments.has_detachment(player, SETTING)


def base_limit(battle_size=None):
    """The printed table, without the Enhancement."""
    return battle_size_module.lookup(UNITS_BY_BATTLE_SIZE, battle_size)


def applies(squad):
    """"NECRONS units from your army" - the detachment and the faction."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    return necron_detachments.is_necrons_unit(squad)


def withdrawal_is_doomed(turn_tracker):
    """Whether a unit placed into Strategic Reserves at THIS end of turn is lost
    before it can arrive. Read after advance_phase(), which is when main.py makes
    the end-of-turn offers.

    True when the battle is over, and when the turn that just ended was the last
    of battle round 3: advance_phase() has then rolled the counter to 4 with the
    round's first turn still to come (turn_index_in_round 0), and rule 20.03's
    destruction runs right after the offers in the same call."""
    if turn_tracker is None:
        return False
    if getattr(turn_tracker, "battle_over", False):
        return True
    return (getattr(turn_tracker, "battle_round", 0) == RESERVES_DESTROYED_AFTER_ROUND + 1
            and getattr(turn_tracker, "turn_index_in_round", None) == 0)


def misses_next_arrival(turn_tracker):
    """Whether a unit withdrawn now cannot arrive in its owner's NEXT Movement
    phase because rule 20.03 forbids arrivals before battle round 2. The owner's
    next turn is the one advance_phase() has just started."""
    if turn_tracker is None:
        return False
    from game.ingress import INGRESS_MIN_BATTLE_ROUND
    return getattr(turn_tracker, "battle_round", 0) < INGRESS_MIN_BATTLE_ROUND


class HyperphasingController(EndOfTurnWithdrawalController):
    """The end-of-opponent-turn selection. main.py builds it beside Ride the
    Wind and offers it at the same instant.

    NOT OFFERED WHEN THE WITHDRAWAL IS DOOMED (withdrawal_is_doomed()). main.py
    destroys the round-3 reserves in the same advance_turn_phase() call as these
    offers, but a HUMAN answers frames later - so a unit withdrawn at the end of
    round 3 would slip into Strategic Reserves after the destruction had run and
    arrive in round 4, which rule 20.03 forbids. Refusing the offer is the only
    reading that neither breaks 20.03 nor asks a question whose only answer
    destroys the unit."""

    LABEL = HYPERPHASING_LABEL

    def __init__(self, *args, turn_tracker=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.turn_tracker = turn_tracker

    def applies(self, squad):
        if not applies(squad):
            return False
        if withdrawal_is_doomed(self.turn_tracker):
            return False
        if getattr(squad, "embarked_in", None) is not None:
            return False
        tokens = getattr(self.game_state, "tokens", None) or ()
        return any(m in tokens for m in squad.models if not m.is_dead())

    def limit(self, player=None):
        return (base_limit(self.battle_size)
                + enh_dimensional_overseer.extra_units(player, self.game_state))

    def prompt_for(self, squad):
        return ("%s: %s - phase it into Strategic Reserves? (%d of %d left this turn)"
                % (HYPERPHASING_LABEL, squad.name, self.remaining(squad.owner),
                   self.limit(squad.owner)))

    def withdraw_message(self, squad):
        return ("%s: %s is removed from the battlefield and placed into Strategic Reserves."
                % (HYPERPHASING_LABEL, squad.name))
