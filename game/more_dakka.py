"""The Big Mek in Mega Armour's More Dakka (2026-09 Ork codex, Mecha Orks stage G2).

RULE (verbatim, rules/orks/Big Mek In Mega Armour.md):
  "More Dakka: This unit's ranged attacks have:
   - [Ignores Cover].
   - If this unit is riled up, [Sustained Hits 1]."

A KEYWORD GRANT WITH TWO READERS, and that is why it is its own module. The
adjuster chain (ShootingController._adjusted_weapon()) is where both keywords
land - the hit step reads [SUSTAINED HITS] off that copy. [IGNORES COVER] has a
second reader, the cover gate: _cover_ignored_for_group(), asked by the cover
split and by _hit_modifiers(). Building this stage found that gate reading the
PRINTED weapon, so every chain-granted [IGNORES COVER] in the engine (Pech'ra,
Faolchu, the Oversight Drone, the Nebuloscope, Preternatural Precision) never
reached it; it now reads the adjusted weapon, and test_event_chain_wiring.py
section 29 pins both of its call sites.

"THIS UNIT" while the Big Mek leads Meganobz is the whole attached unit (rule
19.04, unit_wide_ability()); the Meganobz' own Kustom Shootas get both keywords,
and a mob that has lost its Big Mek loses them.

"[SUSTAINED HITS 1]" on a weapon that already prints a better X keeps the better
X - a grant never makes a weapon worse - and a dice X (a notation) is left alone.
Riled up is game/riled_up.py's one question, asked at attack time.

Blitz Brigade's Targetin' Gizmos (stage G4) prints the same two points for a WAGON
carrying a BIG MEK; this module is where that second source will join, which is
why the grant is written against a predicate rather than the flag alone.
"""

import copy

from game import riled_up
from game.squad import unit_wide_ability
from game.weapons import RANGED

MORE_DAKKA_NAME = "More Dakka"
#: "[Sustained Hits 1]" while riled up.
MORE_DAKKA_SUSTAINED_HITS = 1


def has_more_dakka(squad):
    return squad is not None and bool(unit_wide_ability(squad, "more_dakka"))


def adjusted_weapon(weapon, squad):
    """The chain link: [IGNORES COVER] on a ranged weapon of a More Dakka unit,
    plus [SUSTAINED HITS 1] while it is riled up. A copy - the shared instance is
    never mutated - and the weapon handed in when nothing changes."""
    if weapon is None or getattr(weapon, "weapon_type", None) != RANGED or not has_more_dakka(squad):
        return weapon
    add_cover = not getattr(weapon, "ignores_cover", False)
    add_sustained = (riled_up.is_riled_up(squad)
                     and getattr(weapon, "sustained_hits_notation", None) is None
                     and (getattr(weapon, "sustained_hits", 0) or 0) < MORE_DAKKA_SUSTAINED_HITS)
    if not add_cover and not add_sustained:
        return weapon
    granted = copy.copy(weapon)
    if add_cover:
        granted.ignores_cover = True
    if add_sustained:
        granted.sustained_hits = MORE_DAKKA_SUSTAINED_HITS
    return granted
