"""The Bigboss's Sumfin' to Prove (2026-09 Ork codex).

RULE (verbatim, rules/orks/Bigboss.md):
  "Sumfin' to Prove: This unit's melee attacks have +1 to hit rolls."

The Beastboss's Dodge Dis! with one word more: "melee". So it is read in ONE
place, game/fight.py's _hit_modifiers(), and game/shooting.py never asks - the
same single word that wires Mirage Field and Shimmerstone differently.

"THIS UNIT" while the Bigboss supports a Boyz mob is the whole attached unit -
rule 19.04: the Bigboss component confers the ability on every model until it is
destroyed - so it is asked with unit_wide_ability(), whose component-wise reading
is exactly that. A mob that has lost its Bigboss loses the bonus. Both Fight
phases: the printed line names no phase.

A Hit-roll Modifier, -1 on the threshold (this engine's sign convention), added
before the ignore-modifier filters like every other improving modifier.
"""

from game.modifiers import Modifier
from game.squad import unit_wide_ability

SUMFIN_TO_PROVE_NAME = "Sumfin' to Prove"
#: "+1 to hit rolls" - a bonus, so -1 on the threshold.
SUMFIN_TO_PROVE_HIT_BONUS = 1


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "sumfin_to_prove"))


def hit_modifiers(squad):
    """For a MELEE attack by `squad` - the only caller is the fight side."""
    if not has_ability(squad):
        return []
    return [Modifier(-SUMFIN_TO_PROVE_HIT_BONUS, SUMFIN_TO_PROVE_NAME)]
