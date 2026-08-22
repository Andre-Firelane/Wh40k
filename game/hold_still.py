"""Painboy's "Hold Still and Say 'Aargh!'" ability (user-supplied datasheet
text, not a core rule - hence its own module, same reasoning as
game/ferocious_rage.py and game/doks_toolz.py).

RULE (Painboy, Orks):
  Hold Still and Say 'Aargh!': Each time an attack made by this model with
  its 'Urty syringe scores a Critical Wound against a unit (excluding
  VEHICLE units), that unit suffers D6 mortal wounds.

WHERE THE FLAG LIVES, AND WHY IT IS ON THE WEAPON
-------------------------------------------------
The condition is entirely "this attack was made with the 'Urty syringe", and
that weapon profile exists only on this datasheet - so WeaponProfile.hold_still
is where the check is cheapest and least likely to drift. It is also the exact
shape of the closest core-rule analogue, [DEVASTATING WOUNDS] (24.10), which is
a weapon field for the same reason.

HOW IT DIFFERS FROM [DEVASTATING WOUNDS], WHICH IT OTHERWISE RESEMBLES
----------------------------------------------------------------------
Two differences, and both matter for the wiring in game/fight.py:

  * 24.10 REPLACES the rest of the attack sequence for that wound (the crit
    becomes mortal wounds instead of going on to a save). This text does not
    say that - the critical wound still goes to a save and still does its
    normal damage, and the mortal wounds are ADDITIONAL. So the crits are not
    subtracted from the normal wound pool the way _devastating_crits are.
  * The amount is D6 per critical wound rather than the weapon's Damage, so
    there is a real, visible dice step before any mortal wound is allocated
    (the same "roll it where the player can see it" principle FeelNoPainRoll
    is built on). One roll of N D6 for N crits, summed - N separate one-die
    rolls would be the same distribution and N times the clicking.

MELEE ONLY, DELIBERATELY
------------------------
Wired into game/fight.py and not game/shooting.py: the only weapon that has
the flag is a Melee profile, so the shooting path could never reach it. Same
call made for Crisis Sunforge's damage re-roll (ranged-only) in the opposite
direction - wire the phase the rule can actually occur in, and say so.

The VEHICLE exclusion is read through rule 19.03's keyword pooling, so an
attached unit (19.01) containing a VEHICLE component is excluded as one unit.
"""

from game import attached_units

# "that unit suffers D6 mortal wounds" - per critical wound, rolled visibly.
HOLD_STILL_DICE_PER_CRIT = 1
HOLD_STILL_DICE_SIDES = 6
HOLD_STILL_LABEL = "Hold Still and Say 'Aargh!'"


def _is_vehicle(squad):
    return attached_units.unit_has_keyword(squad, lambda m: m.profile.vehicle)


def applies(weapon, target_squad):
    """Whether a critical wound scored by `weapon` against `target_squad`
    triggers this ability at all - i.e. whether the caller should count the
    critical wounds of this weapon group for it."""
    if weapon is None or not getattr(weapon, "hold_still", False):
        return False
    if target_squad is None or not target_squad.models:
        return False
    return not _is_vehicle(target_squad)


def dice_count(crits):
    """How many D6 to throw for `crits` critical wounds."""
    return max(0, crits) * HOLD_STILL_DICE_PER_CRIT


def mortal_wounds(rolls):
    """The mortal wound total for a set of already-thrown D6."""
    return sum(rolls or ())


def roll_label(crits, target_squad):
    return (
        f"{HOLD_STILL_LABEL}: {crits} critical wound(s) vs "
        f"{target_squad.name} (D6 mortal wounds each)"
    )
