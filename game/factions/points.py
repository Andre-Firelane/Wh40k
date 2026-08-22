"""Official points costs, as printed in a faction's own points list (the
army app's "Unit Costs" screen / Munitorum Field Manual), stored as data.

Why this needs more shape than one number per unit: a real points list
prices a unit THREE different ways at once, and all three occur in the T'au
list this engine actually carries (game/factions/tau_empire_points.py):

- by unit SIZE - "10 models 65 pts / 20 models 130 pts" (Kroot Carnivores),
  which lines up exactly with Datasheet.compositions()' own "one build per
  legal size" shape;
- by how many copies of the unit the ARMY already has - "your 1st to 2nd
  units cost 150 pts / your 3rd + unit costs 165 pts" (Ghostkeel
  Battlesuit), i.e. a cost that depends on a fact living outside the
  datasheet entirely;
- by WARGEAR taken - "per Cyclic Ion Raker 15 pts", charged per instance on
  top of the unit's own cost.

PointsTier models the second (holding the first inside it as its own
{model_count: points} table); the third is stored on `UnitPoints.wargear`
and read from there by the datasheet's own WargearOption(points=...), so
each number is written down exactly once, next to the thing it prices.

What is deliberately NOT stored: the list's own up/down arrows and
"(+15)"/"(-10)" annotations, which mark what changed relative to the
PREVIOUS published list rather than forming any part of a cost.

A priced wargear option is charged only when it is actually SELECTED (see
Datasheet.points_for()) - never for the datasheet's printed default
loadout, even when that default includes the priced weapon. Crisis
Starscythe Battlesuits are the case that settles this: every model comes
with a T'au flamer as standard AND the list prices "per T'au flamer 5 pts",
which can only mean the SECOND flamer a model takes by replacing its burst
cannon - otherwise the printed default would cost more than the printed
unit cost.

Nothing in the engine spends or enforces points yet - there is no army
building/Muster Armies flow (see CLAUDE.md's Spaeter-Liste). build_squad()
computes each built unit's cost into Squad.points, so a real list-building
step later finds the arithmetic already done instead of reconstructing it.
"""


class PointsTier:
    """One "YOUR Nth UNIT COSTS" block of a points list. `costs` is
    {model_count: points} covering every unit size that block prices;
    from_unit/to_unit are the 1-based range of copies of the unit (within
    one army list) it applies to, with to_unit=None meaning "and every one
    after that" - the trailing "3rd +" block. A unit with one flat price and
    no tiering at all (Strike Team: "10 models 70 pts") is simply a single
    tier covering 1..None."""

    def __init__(self, costs, from_unit=1, to_unit=None):
        self.costs = dict(costs)
        self.from_unit = from_unit
        self.to_unit = to_unit

    def applies_to_unit(self, unit_index):
        return unit_index >= self.from_unit and (self.to_unit is None or unit_index <= self.to_unit)

    def cost_for(self, model_count):
        """None if this tier doesn't price that unit size. Deliberately not
        interpolated or scaled: a published list only ever names the legal
        sizes (Kroot Hounds cost 45 at 5 models and 65 at 10 - never 7), so
        an unlisted size means the caller built something the list doesn't
        recognise, which is worth surfacing as "unknown" rather than
        inventing a number for."""
        return self.costs.get(model_count)


class UnitPoints:
    """One unit's complete entry in the points list: its cost tiers, plus
    its wargear prices keyed by the item name exactly as the list prints it
    ("Cyclic Ion Raker"). A datasheet that exists in this engine reads those
    wargear numbers straight out of `wargear` when declaring its own
    WargearOption(points=...) - so this entry stays the single source for
    both halves of the unit's cost, and a typo'd item name fails loudly with
    a KeyError at import instead of silently pricing an option at 0.

    `leads` and `supports` record the entry's own "LEADER: ..." / "SUPPORT:
    ..." line (which units this one may be attached to), kept as reference
    next to the cost they belong to. They're two separate fields rather than
    one because they are two different attachment types on the printed
    entries - an Ork Painboy is SUPPORT for Boyz, a Warboss LEADS them.
    Neither drives anything: attaching either kind needs the live
    unit-formation flow this engine deliberately doesn't have yet (see
    CLAUDE.md's Spaeter-Liste, Attached Units)."""

    def __init__(self, tiers, wargear=None, leads=(), supports=()):
        self.tiers = list(tiers)
        self.wargear = dict(wargear) if wargear else {}
        self.leads = tuple(leads)
        self.supports = tuple(supports)

    def tier_for(self, unit_index):
        for tier in self.tiers:
            if tier.applies_to_unit(unit_index):
                return tier
        return None

    def cost_for(self, model_count, unit_index=1):
        """The unit's own cost before any wargear - None if either the unit
        index or the model count isn't priced (see PointsTier.cost_for)."""
        tier = self.tier_for(unit_index)
        return tier.cost_for(model_count) if tier is not None else None


def flat_points(costs, wargear=None, leads=(), supports=()):
    """Shorthand for an entry with no "your Nth unit" tiering - one price
    table that applies to every copy of the unit in the army."""
    return UnitPoints([PointsTier(costs)], wargear=wargear, leads=leads, supports=supports)
