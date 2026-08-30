"""The Clanblade's "Cornered Prey" - a datasheet ability.

RULE (printed, word for word):
  "When an enemy unit engaged with this unit is selected to make a fall-back
  move, that enemy unit must use the desperate escape mode. If that enemy unit
  is battle-shocked, -1 from those hazard rolls."

TWO CLAUSES, BOTH ON MACHINERY THAT ALREADY EXISTS
---------------------------------------------------
Desperate Escape (09.07) and its hazard rolls are built - a battle-shocked unit
already has to use them, which is exactly what makes the second clause read
oddly at first glance. It is not redundant: the FIRST clause forces the mode on
a unit that is NOT battle-shocked and would otherwise fall back freely, and the
second then adds a penalty for one that is.

So the two clauses stack rather than overlap:
  * not battle-shocked -> forced into Desperate Escape at the normal threshold;
  * battle-shocked     -> already in Desperate Escape, now at -1.

"ENGAGED WITH THIS UNIT" is measured when the fall back is SELECTED, which is
the moment game/fall_back.py asks - so the question is asked live rather than
from a mark, and a Clanblade that dies before then stops imposing it.
"""
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance

CORNERED_PREY_LABEL = "Cornered Prey"

#: "-1 from those hazard rolls" for a battle-shocked unit.
CORNERED_PREY_HAZARD_PENALTY = 1


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def _bearers_engaged_with(squad, all_tokens):
    """Enemy units within Engagement Range of `squad` that carry the ability."""
    seen, out = set(), []
    mine = _living(squad)
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other is squad or id(other) in seen:
            continue
        if other.owner == squad.owner:
            continue
        if not any(getattr(m.profile, "cornered_prey", False) for m in _living(other)):
            continue
        if any(edge_distance(a, b) <= ENGAGEMENT_RANGE_IN
               for a in mine for b in _living(other)):
            seen.add(id(other))
            out.append(other)
    return out


def forces_desperate_escape(squad, all_tokens=()):
    """The first clause: must this unit use Desperate Escape when it falls
    back, whether or not it is battle-shocked?"""
    return bool(_bearers_engaged_with(squad, all_tokens))


def hazard_penalty_for(squad, all_tokens=()):
    """The second clause, and ONLY for a battle-shocked unit - the printed text
    makes that its condition, so it is not folded into the first."""
    if not getattr(squad, "battle_shocked", False):
        return 0
    return (CORNERED_PREY_HAZARD_PENALTY
            if _bearers_engaged_with(squad, all_tokens) else 0)
