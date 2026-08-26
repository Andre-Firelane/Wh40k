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

RANGED ONLY, which is why it is wired into game/shooting.py alone and not
game/fight.py - "each time a RANGED attack targets this model".

THE TOUGHNESS IS READ THROUGH attached_unit_toughness() rather than off the
profile, for the same reason the wound threshold itself is: rule 19.02. It
cannot matter today (a VEHICLE is not joinable), but reading the same source as
the roll it modifies means the two can never disagree.
"""

from game.squad import attached_unit_toughness

WAVE_SERPENT_SHIELD_PENALTY = 1
WAVE_SERPENT_SHIELD_LABEL = "Wave Serpent Shield"


def unit_has_shield(squad):
    """Per 19.03 a merged unit counts as having it if any component brought it -
    which reading it off the models gives for free."""
    if squad is None:
        return False
    return any(getattr(m.profile, "wave_serpent_shield", False)
               for m in squad.models if not m.is_dead())


def applies(target_squad, strength):
    """Whether the shield modifies THIS attack's Wound roll.

    `strength` is the attack's Strength characteristic as the wound step
    computes it - the already-adjusted one, not the printed value, so a weapon
    boosted past the hull's Toughness by something else is caught too."""
    if not unit_has_shield(target_squad) or strength is None:
        return False
    toughness = attached_unit_toughness(target_squad)
    return toughness is not None and strength > toughness
