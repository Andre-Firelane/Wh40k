"""The Silent King's Phaeron of the Blades, first clause: the Charge re-roll.

The SECOND carrier of game/charge_reroll.py (the 51st extraction), after the
Triarch Praetorians' Relentless Combatants. All of the machinery - the
one-instant offer window before acknowledge(), the once-per-roll claim, the
all-or-nothing re-roll and the AI's two-sided deterministic answer - lives in
the base class. What a carrier owns is two knobs, and this module is both of
them.

ITS PREDICATE IS AN AURA, and that is the whole reason the extraction happened:
Relentless Combatants asks rule 19.04's unit_wide_ability(), a fact about the
unit's own datasheet, while this asks whether the unit is standing within 6" of
a Szarekh model whose unit selected THIS Triarch ability this battle round.
Two predicates that could hardly be less alike, in front of identical
machinery.

THE SECOND CLAUSE OF THE SAME PRINTED SENTENCE IS NOT HERE. "each time a model
in that unit makes a melee attack, add 1 to the Strength characteristic of that
attack" is a weapon grant and lives in game/triarch_auras.py's
blades_adjusted_weapon(), folded into fight.py's adjuster chain. One sentence,
two seams - the same split the Triarch Praetorians' own two clauses take.
"""

from game import triarch_auras
from game.charge_reroll import ChargeRerollController


class PhaeronOfTheBladesController(ChargeRerollController):
    LABEL = triarch_auras.TRIARCH_ABILITY_NAMES[triarch_auras.PHAERON_OF_THE_BLADES]

    def applies(self, squad):
        return triarch_auras.is_active(squad, triarch_auras.PHAERON_OF_THE_BLADES)
