"""T'au Empire datasheet ability: Cadre Fireblade's Crack Shot, as supplied
by the user (not a rule from the generic 40k core rulebook, so it lives in
its own module - same reasoning as game/starscythe.py for Starscythe and
game/drive_by_dakka.py for Drive-by Dakka).

RULE: each time this model makes a ranged attack, on a Critical Wound, that
attack has an Armour Penetration characteristic of -3.

Unlike Starscythe's own "improve the Armour Penetration characteristic by
1" (a modifier, applied to a whole group's wounds alike), this is a flat
OVERRIDE of the AP characteristic, and only for the subset of a group's
wounds that actually rolled a Critical Wound - a normal (non-critical)
wound from the exact same attack still uses the weapon's own printed AP.
That per-wound split can't be expressed as a single adjusted WeaponProfile
covering the whole group (like starscythe_adjusted_weapon() does) - it
needs its own Save-roll sub-step, separate from the group's main one, that
only the critical-wound subset goes through. See
game/shooting.py's ShootingController._begin_crack_shot_save() and its
caller (_resolve_wounds()) for where that split happens and why."""

import copy

CRACK_SHOT_AP = -3


def crack_shot_adjusted_weapon(weapon):
    """A shallow copy with `ap` forced to CRACK_SHOT_AP - the shared
    WeaponProfile instance is never mutated, same convention as every other
    *_adjusted_weapon() helper (bonded_heroes_adjusted_weapon(),
    starscythe_adjusted_weapon(), melta_adjusted_weapon(), ...)."""
    adjusted = copy.copy(weapon)
    adjusted.ap = CRACK_SHOT_AP
    return adjusted
