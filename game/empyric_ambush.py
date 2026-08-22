"""Lhykhis' "Empyric Ambush" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "While this model is leading a unit, that unit is eligible to declare a charge
  in a turn in which it used its Flickerjump ability."

THE ONLY ABILITY HERE THAT UNDOES ANOTHER ONE
---------------------------------------------
Flickerjump is Warp Spiders' own ability (game/flickerjump.py) and she leads
exactly one datasheet: Warp Spiders. So this is written to cancel the downside
of the unit she attaches to - 24" of movement without giving up the charge.

IMPLEMENTED BY NOT SETTING THE LOCK, not by ignoring it. Flickerjump's charge
restriction reuses Squad.charge_locked_until_end_of_turn, which is a SHARED
boolean: rules 18.04/18.05 (disembarking), The Shortened Blade and The Torchstar
Gambit all set the same field. Reading it and ignoring it would hand a charge
back to a unit that disembarked, which this ability says nothing about.

So the condition lives at the one place Flickerjump sets it: if the unit
qualifies, Flickerjump simply does not add its own lock. That is exact for a
boolean - if something else already locked the unit, the flag is already True
and not setting it changes nothing, so a Lhykhis-led unit that also disembarked
still cannot charge. One condition, one place, no second reader.

WHY NOT A NEW FLAG for "used Flickerjump this turn": Squad.flickerjump_active
already records exactly that, with exactly the right lifetime (set in use(),
cleared at end of turn), because Flickerjump's other half - the 24" Move
characteristic - needs the same fact.
"""

from game import attached_units


def applies(squad):
    """Whether this unit is being LED by a model with the ability.

    attached_units.leader_ability() is the 19.04-correct lookup: it requires a
    real attached unit (a lone Lhykhis leads nobody), reads the ability off the
    leader COMPONENT so it ends when she dies, and brings 19.04's grace window
    with it."""
    return attached_units.leader_ability(squad, "empyric_ambush")
