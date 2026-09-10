"""Rule 03.04's "within Engagement Range of one or more enemy units", asked of
a whole unit - the 23rd extraction, and four consumers late.

WHY IT EXISTS
-------------
Three modules had already written this out - game/airborne_agility.py,
game/fire_and_fade.py and game/guardian_cost_of_victory.py - because each has a
printed clause that turns on it ("excluding units within Engagement Range").
Warhost's Skyborne Sanctuary and Webway Tunnel are the fourth and fifth, which
makes five copies of one sentence: exactly the drift this repo consolidates at
the SECOND consumer, so this one is overdue rather than early.

THE LIVING FILTER IS THE POINT, AND IT IS A MEASURED DIFFERENCE FROM
Squad.is_engaged(). That method predates this question and does not skip dead
models on either side, because remove_dead_models() runs once per frame and
every trigger before it still sees corpses (CLAUDE.md's error class 12). All
three existing copies filter them; measured, the two readings disagree in
exactly the frame that matters:

    both units alive        Squad.is_engaged True   this module True
    the enemy just wiped out Squad.is_engaged True   this module False
    my own unit wiped out    Squad.is_engaged True   this module False

So a unit is reported "engaged" with a unit the very attack being resolved has
just destroyed. For an end-of-phase clause like these five that is the
difference between offering a Stratagem and refusing it.

Squad.is_engaged() IS DELIBERATELY NOT CHANGED HERE. It is read by shooting
eligibility, charge declaration, Fall Back and a dozen other places whose
behaviour would move with it; that is its own measured step, not a side effect
of adding a Stratagem. The difference is named rather than left for the next
reader to rediscover - and the two are pinned against each other in the test so
a later attempt to "unify" them has to be a deliberate change.
"""

from game.squad import ENGAGEMENT_RANGE_IN, edge_distance


def is_engaged(squad, all_tokens=()):
    """"within Engagement Range of one or more enemy units" (03.04), counting
    only models that are still alive on both sides."""
    if squad is None or not all_tokens:
        return False
    mine = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
    if not mine:
        return False
    for token in all_tokens:
        other = getattr(token, "squad", None)
        if other is None or other.owner == squad.owner or token.is_dead():
            continue
        for model in mine:
            if edge_distance(model, token) <= ENGAGEMENT_RANGE_IN:
                return True
    return False


def units_are_engaged(squad, other):
    """Whether these TWO specific units are within Engagement Range of each
    other, living models only.

    is_engaged() above asks "is anything engaging me"; this asks about a NAMED
    pair, which is what a clause aimed at one unit needs ("while an ENEMY UNIT
    is within Engagement Range of THIS unit"). Same 2" and the same living
    filter, so the two can never disagree about what Engagement Range means.

    First consumer: Canoptek Scarab Swarms' Chittering Swarm."""
    if squad is None or other is None:
        return False
    mine = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
    theirs = [m for m in (getattr(other, "models", ()) or ()) if not m.is_dead()]
    for a in mine:
        for b in theirs:
            if edge_distance(a, b) <= ENGAGEMENT_RANGE_IN:
                return True
    return False
