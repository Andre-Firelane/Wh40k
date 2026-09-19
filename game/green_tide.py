"""Orks detachment rule: Green Tide's Mob-handed Brutality (2026-09 codex,
Mecha Orks stage G3).

PRINTED (rules/orks/detachments/Green Tide.md):

    Mob-handed Brutality
    - Friendly BOYZ units' melee attacks have [Sustained Hits 1].
    - If a friendly ORKS INFANTRY unit made a charge move this turn, that
      unit's melee attacks have [Lethal Hits: non-Monster/Vehicle].

TWO GRANTS, TWO DIFFERENT UNITS. The first names BOYZ - a DATASHEET, not a
keyword on the Boyz' line (INFANTRY, BATTLELINE, EXPLOSIVES, MOB) - so it is
asked of attached_units.unit_is_datasheet(): a Warboss leading the mob swings
with it (rule 19.03, an attached unit has its components' keywords). Beast
Snagga Boyz are NOT Boyz; Green Tide's own 'Ere We Go prints the two apart
("BEAST SNAGGA BOYZ/BOYZ"). The second names any ORKS INFANTRY unit, and only in
a turn it made a charge move (Squad.charged_this_turn, rule 11.04's flag).

THE CONDITION IS THE TARGET'S. "[Lethal Hits: non-Monster/Vehicle]" is rule
24.01's conditional ability, the one this engine keeps as
game/keyword_condition.py's NON_MONSTER_VEHICLE_TARGETS; it is matched against
the unit being attacked here, the same object game/conditional_keywords.py
matches a printed weapon's condition against. With no target in hand the grant
is withheld - it can under-report, never hand [LETHAL HITS] to a swing at a
VEHICLE.

A KEYWORD GRANT WITH ONE READER: game/fight.py's adjuster chain, which the hit
step, _crit_note() and extra_attack_dice() all read. Neither keyword has an
eligibility gate of its own (unlike [ASSAULT] or [PISTOL]).

The two Enhancements are game/enh_ferocious_show_off.py and
game/enh_ardboyz.py; the three Stratagems are game/green_tide_*.py.
"""

import copy

from game import attached_units
from game.detachment_gate import has_detachment
from game.keyword_condition import NON_MONSTER_VEHICLE_TARGETS
from game.weapons import MELEE

#: The config constant game/detachments.py writes for this detachment.
SETTING = "GREEN_TIDE_PLAYERS"
MOB_HANDED_BRUTALITY = "Mob-handed Brutality"
MOB_HANDED_SUSTAINED_HITS = 1

#: "BOYZ" - the datasheet the capitals name.
BOYZ_DATASHEETS = ("Boyz",)
#: "BEAST SNAGGA BOYZ/BOYZ" - 'Ere We Go's TARGET.
BEAST_SNAGGA_BOYZ_OR_BOYZ_DATASHEETS = ("Beast Snagga Boyz", "Boyz")


def fields_green_tide(player):
    return has_detachment(player, SETTING)


# "Friendly ORKS unit" / "ORKS INFANTRY unit" - game/ork_units.py (extracted when
# Blitz Brigade became their third asker), re-exported for Green Tide's modules.
from game.ork_units import is_orks_infantry_unit, is_orks_unit  # noqa: E402,F401


def is_boyz_unit(squad):
    return attached_units.unit_is_datasheet(squad, BOYZ_DATASHEETS)


def is_beast_snagga_boyz_or_boyz_unit(squad):
    return attached_units.unit_is_datasheet(squad, BEAST_SNAGGA_BOYZ_OR_BOYZ_DATASHEETS)


def living_model_count(squad):
    """"This unit has 11+ models", "a unit of 13+ models": the models it has
    NOW, counted over the whole attached unit (19.01 makes it one unit)."""
    return sum(1 for m in getattr(squad, "models", ()) or () if not m.is_dead())


def sustained_hits_applies(squad):
    """The first bullet: a friendly BOYZ unit of a player fielding Green Tide."""
    return (squad is not None and fields_green_tide(getattr(squad, "owner", None))
            and is_boyz_unit(squad))


def lethal_hits_applies(squad, target_squad):
    """The second bullet, against THIS target."""
    if squad is None or target_squad is None:
        return False
    if not fields_green_tide(getattr(squad, "owner", None)):
        return False
    if not getattr(squad, "charged_this_turn", False) or not is_orks_infantry_unit(squad):
        return False
    return NON_MONSTER_VEHICLE_TARGETS.matches(target_squad)


def adjusted_weapon(weapon, squad, target_squad=None):
    """Both grants on a melee weapon, as a copy - never a downgrade: a weapon
    already carrying [SUSTAINED HITS 2] (or a dice-notation value) keeps it, one
    already carrying [LETHAL HITS] is left alone."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE:
        return weapon
    adjusted = weapon
    if (sustained_hits_applies(squad)
            and getattr(weapon, "sustained_hits_notation", None) is None
            and (weapon.sustained_hits or 0) < MOB_HANDED_SUSTAINED_HITS):
        adjusted = copy.copy(adjusted)
        adjusted.sustained_hits = MOB_HANDED_SUSTAINED_HITS
    if not weapon.lethal_hits and lethal_hits_applies(squad, target_squad):
        if adjusted is weapon:
            adjusted = copy.copy(adjusted)
        adjusted.lethal_hits = True
    return adjusted
