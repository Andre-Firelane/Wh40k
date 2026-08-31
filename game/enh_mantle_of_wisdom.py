"""Aspect Host Enhancement: Mantle of Wisdom (20 pts).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  "AUTARCH or AUTARCH WAYLEAPER model only. While the bearer is leading an
  ASPECT WARRIORS unit, each time that unit is selected to shoot or fight,
  until the end of the phase, models in that unit gain both of the abilities
  from the Path of the Warrior Detachment rule."

THIS DOES NOT ADD A RULE - IT WIDENS ONE. Path of the Warrior is a choice
between two exclusive options (re-roll Hit rolls of 1, OR Wound rolls of 1);
this says the led unit gets BOTH.

SO IT IS READ INSIDE game/path_of_the_warrior.py, at that rule's OWN answer,
and not at the four places the answer is consumed (_hit_reroll_reason and
on_dice_acknowledged, in each of the two attack files). Those four are where a
widening would have to be repeated four times and could therefore be applied
three - the exact shape of the "wired into only half the sites" bug this repo
records, and the same reason the two T'au Exemplars intervene in
doctrine_active() rather than at their four grant sites.

AND IT REMOVES THE PROMPT. Path of the Warrior asks the player which option
their unit takes this phase; with both granted there is nothing to choose, so
offering the question would be asking for a decision that changes nothing -
rule-5 territory ("never offer what buys nothing"), and worse than useless
here because the player would reasonably read the prompt as a limit.

The bearer conditions are Shimmerstone's, one card over: carried, LEADING
(24.22), and leading an ASPECT WARRIORS unit specifically.
"""
from game import attached_units, enhancements

MANTLE_OF_WISDOM = "Mantle of Wisdom"

MANTLE_OF_WISDOM_LABEL = "Mantle of Wisdom"

#: "an ASPECT WARRIORS unit" - the same clause Shimmerstone prints.
MANTLE_OF_WISDOM_KEYWORD = "ASPECT WARRIORS"


def applies(squad):
    """Whether this unit gains BOTH Path of the Warrior options."""
    if squad is None:
        return False
    if not enhancements.is_active(squad, MANTLE_OF_WISDOM):
        return False
    if not attached_units.leader_ability(squad, "mantle_of_wisdom"):
        return False
    return attached_units.unit_has_datasheet_keyword(squad, MANTLE_OF_WISDOM_KEYWORD)
