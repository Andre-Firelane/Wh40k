"""Worsening an attack's Armour Penetration - the one arithmetic.

Defender-side rules that worsen AP by 1: the Enforcer Commander's aura (ranged
attacks on its unit, game/enforcer_commander.py) and the Meganobz' Arrogant
Invulnerability (game/arrogant_invulnerability.py). Extracted at the third -
the Battlewagon's Ramshackle but Rugged, which the 2026-09 Ork codex dropped
(stage E3d); the arithmetic stays one definition for the two that remain.

AP is written as a penalty (0, -1, -2 ...), so "worsen by N" moves N steps
TOWARD zero and stops there: an AP0 attack cannot become a bonus to the save.
With only AP0 weapons on the board min(0, ap + N) and ap + N are
indistinguishable, and the wrong one would hand out a better-than-printed
save - the reason it is written once.

Each rule still applies its own step in turn (game/damage_resolution.py's
save_thresholds()), so two sources on one attack compose to -2 rather than
being capped at one.
"""


def worsen(ap, steps=1):
    """`ap` worsened by `steps`, never past 0."""
    return min(0, ap + steps)
