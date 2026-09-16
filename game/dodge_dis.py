"""The Beastboss's Dodge Dis! (2026-09 Ork codex).

RULE (verbatim, rules/orks/Beastboss.md):
  "Dodge Dis!: This unit's attacks have +1 to hit rolls."

Read LITERALLY, a user decision: it is the unit's OWN attacks that gain +1, in
both phases ("attacks", not "ranged" or "melee"), even though the name reads
like a defensive rule.

"THIS UNIT" while the Beastboss leads Beast Snagga Boyz is the whole attached
unit - rule 19.04: the Beastboss component confers the ability on every model
until it is destroyed - so it is asked with unit_wide_ability(), whose
component-wise reading is exactly that. A mob that has lost its Beastboss loses
the bonus.

A Hit-roll Modifier, -1 on the threshold (this engine's sign convention), read
by both _hit_modifiers() before their ignore-modifier filters.
"""

from game.modifiers import Modifier
from game.squad import unit_wide_ability

DODGE_DIS_NAME = "Dodge Dis!"
#: "+1 to hit rolls" - a bonus, so -1 on the threshold.
DODGE_DIS_HIT_BONUS = 1


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "dodge_dis"))


def hit_modifiers(squad):
    if not has_ability(squad):
        return []
    return [Modifier(-DODGE_DIS_HIT_BONUS, DODGE_DIS_NAME)]
