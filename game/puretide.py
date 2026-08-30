"""Commander Farsight's own "Puretide's Teachings" ability, as supplied by
the user (not a rule from the generic 40k core rulebook, so it lives in its
own module - same reasoning as game/way_of_the_short_blade.py for his other
one).

RULE: Once per battle round, one unit from your army with this ability can
use it when its unit is targeted with a Stratagem. If it does, reduce the CP
cost of that use of that Stratagem by 1CP.

WHERE IT LANDS
--------------
On the COST, which game/stratagems.py computes in exactly two places -
can_use() (may I afford this?) and use() (spend it). Those two must always
agree, or a Stratagem would look affordable and then fail to pay, so the
discount is applied through a single hook the controller consults from both
rather than being added at either call site.

Applied to the cost, NOT refunded afterwards, because the rule says "reduce
the CP cost of that use": a player with exactly enough CP only because of
the discount can still use the Stratagem. A refund would fail the
affordability check first and never happen.

AUTOMATIC, NOT A PROMPT
-----------------------
The text is "can use it", but the choice has no downside worth interrupting
the game for: the resource it spends is its own once-per-round availability,
and holding that back cannot help - there is no second, better Stratagem
this round that it would rather discount, since it is available again next
round regardless. Same reasoning rule 24.29's [PSYCHIC] modifier-ignoring is
applied automatically rather than asked about. It is logged, so a player can
see it happened.

"ONCE PER BATTLE ROUND"
-----------------------
Per battle round and per PLAYER, keyed off TurnTracker.battle_round - not
per phase and not per turn. A battle round contains both players' turns
(07.03), so the natural reading of "once per battle round" for an ability
that reacts to YOUR OWN Stratagem use is one use per round per army; two
Farsights in one army would still get one between them ("ONE unit from your
army with this ability can use it").
"""

from game.cp_discount import OncePerRoundCpDiscount


def unit_has_puretide(squad):
    """True while at least one live model with the ability is in the unit -
    the same rule 19.04 reading every other datasheet ability here uses."""
    if squad is None:
        return False
    return any(m.profile.puretide_teachings for m in squad.models if not m.is_dead())


PURETIDE_DISCOUNT_CP = 1


class PuretideController(OncePerRoundCpDiscount):
    """Plugged into StratagemController.cost_discounts (see its own note).
    Takes `stratagem` and ignores it - this ability keys off the TARGET, not
    off which stratagem is being used, unlike the Aeldari Seer Council's
    Strands of Fate, which is why that argument exists at all.
    Two methods, deliberately split: available_discount() is a pure query
    that can_use() may call as often as it likes, and consume() is the only
    thing that spends the once-per-round use - so merely ASKING whether a
    Stratagem is affordable never burns the ability."""

    # Everything this ability does is the shared sentence in
    # game/cp_discount.py; what is left here is only what differs.
    flag = 'puretide_teachings'
    discount_cp = PURETIDE_DISCOUNT_CP
    label = "Puretide's Teachings"
