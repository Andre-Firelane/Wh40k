"""Kroot War Shaper's "War Leader".

RULE (printed, word for word):
  "Once per battle round, one unit from your army with this ability can use it
   when its unit is targeted with a Stratagem. If it does, reduce the CP cost
   of that use of that Stratagem by 1CP."

THE FIFTH cost_discounts COLLABORATOR, after the T'au Puretide engram neurochip
(game/puretide.py), the Aeldari Seer Council's Strands of Fate
(game/strands_of_fate.py), the Necron Overlord's My Will Be Done
(game/my_will_be_done.py) and the Death Guard's Fevered Strategist
(game/fevered_strategist.py).

It is My Will Be Done word for word in a different faction's typeface - same
"once per battle round", same "a Stratagem targeting this model's unit", same
1CP - so this is deliberately its twin rather than a new mechanism, and
StratagemController needs no change at all: it already folds a LIST of
discounts, and already keeps _cost_for() as the one definition of the price so
can_use() and use() cannot disagree.

"ONE UNIT FROM YOUR ARMY WITH THIS ABILITY" is why the ledger is keyed by
PLAYER and not by squad: two War Shapers in one army share the single
entitlement, they do not get one each. That is the same reading My Will Be Done
takes of the same sentence.

WHY A LIVE MODEL CHECK RATHER THAN A FLAG ON THE SQUAD: `unit_has_war_leader()`
walks the unit's living models, so the discount stops the moment the Shaper
dies, and it works whether he is leading a Kroot unit (19.01 merged him in) or
standing alone.

AVAILABILITY IS A PURE QUERY. `available_discount()` never spends anything;
`consume()` is separate and is called only once a discounted use has actually
gone through. Asking a Stratagem's price - which the UI does every frame to
decide whether to grey a button out - must not burn the entitlement.
"""

from game.cp_discount import OncePerRoundCpDiscount

WAR_LEADER_DISCOUNT_CP = 1


def unit_has_war_leader(squad):
    """Whether a living model in this unit prints War Leader.

    Read live off the models rather than cached on the squad, which is what
    makes it stop working the moment the War Shaper dies."""
    if squad is None:
        return False
    return any(getattr(m.profile, "war_leader", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class WarLeaderDiscount(OncePerRoundCpDiscount):
    """Appended to StratagemController.cost_discounts in main.py."""

    # Everything this ability does is the shared sentence in
    # game/cp_discount.py; what is left here is only what differs.
    flag = 'war_leader'
    discount_cp = WAR_LEADER_DISCOUNT_CP
    label = 'War Leader'
