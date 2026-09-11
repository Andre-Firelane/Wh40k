"""The Wave Serpent's "Wave Serpent Shield".

RULE (printed, word for word):
  "Each time a ranged attack targets this model, if the Strength characteristic
   of that attack is greater than the Toughness characteristic of this model,
   subtract 1 from the Wound roll."

A DEFENDER-SIDE WOUND MODIFIER, so it sits with 'Ard as Nails, Protect,
Forewarned and the Guardian Drone in _wound_modifiers() - and, like them, its
sign is POSITIVE: game/modifiers.py's convention is that a modifier adjusts the
THRESHOLD, and "subtract 1 from the Wound roll" makes the roll harder, i.e.
raises what it has to beat.

WHAT MAKES IT DIFFERENT from the four above is that its condition is about the
ATTACK rather than about who is shooting: S > T, evaluated per weapon group.
That comparison is the whole ability, and it means the shield does nothing
against the small-arms fire it is already shrugging off and everything against
the anti-tank weapon that would otherwise wound on a 3+.

RANGED ONLY - "each time a RANGED attack targets this model". That one printed
word is now expressed as `ranged_only = True` on the carrier rather than by
which file wires it up, and it is what keeps the shield out of game/fight.py
where its two siblings do appear.

THE ARITHMETIC MOVED TO game/strength_over_toughness.py (the 50th extraction),
at the third carrier. This module keeps its name and RE-EXPORTS everything it
ever exported, so no caller moves - the treatment game/root_of_honour.py and
game/monofilament_web.py got. The Toughness is still read through
attached_unit_toughness() (rule 19.02): it cannot matter today, since a VEHICLE
is not joinable, but reading the same source as the roll it modifies means the
two can never disagree.
"""

from game.strength_over_toughness import WAVE_SERPENT_SHIELD

WAVE_SERPENT_SHIELD_PENALTY = WAVE_SERPENT_SHIELD.penalty
WAVE_SERPENT_SHIELD_LABEL = WAVE_SERPENT_SHIELD.label


def unit_has_shield(squad):
    """Per 19.03 a merged unit counts as having it if any component brought it -
    which reading it off the models gives for free."""
    return WAVE_SERPENT_SHIELD.unit_has(squad)


def applies(target_squad, strength):
    """Whether the shield modifies THIS attack's Wound roll.

    `strength` is the attack's Strength characteristic as the wound step
    computes it - the already-adjusted one, not the printed value, so a weapon
    boosted past the hull's Toughness by something else is caught too."""
    return WAVE_SERPENT_SHIELD.applies(target_squad, strength)
