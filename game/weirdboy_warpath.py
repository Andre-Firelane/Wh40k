"""The Weirdboy's Warpath (2026-09 Ork codex, Mecha Orks stage G1).

RULE (verbatim, rules/orks/Weirdboy.md):
  "Warpath (psychic level 1): In the Fight phase, when this unit is selected to
   fight, if this unit is not battle-shocked, you can make a psychic roll for
   this unit by rolling one D6. If you do:
   - On a 1, this unit is battle-shocked.
   - This unit's melee attacks can re-roll wound rolls of 1.
   - This unit's melee attacks have [Psychic]."

ONE NAME, TWO EFFECTS (error class 11). The Kill Rig prints a Warpath with the
same frame and a different second bullet ([LETHAL HITS] instead of the wound
re-roll). The FRAME is shared - game/warpath.py's WarpathController asks at the
same instant through the same game/psychic_roll.py - and this module owns only
what differs: its own printed flag (UnitProfile.weirdboy_warpath), its own grant
(Squad.weirdboy_warpath_active) and its two effects. A shared flag would have
handed a Kill Rig the re-roll or a Weirdboy's mob [LETHAL HITS].

"THIS UNIT" while the Weirdboy supports Boyz or Beast Snagga Boyz is the whole
attached unit (rule 19.04, read through unit_wide_ability() in the controller),
and so is the psychic roll: the unit's psyker level is the Weirdboy's 1, shared
with Da Jump (game/da_jump.py) for the battle round.

THE TWO EFFECTS, and where each is read:
  * [PSYCHIC] on every melee weapon - adjusted_weapon(), in FightController's
    adjuster chain; rule 24.29's drop of worsening Hit modifiers reads the
    adjusted weapon (the Kill Rig's stage made that so).
  * "can re-roll wound rolls of 1" - a PLAIN automatic re-roll of 1s (no "you
    can re-roll the Wound roll instead"), so it joins FightController's
    _wound_without_optional_reroll() beside Prophet of Destruction and not
    game/reroll_scope.py, which drives a failures-or-whole offer this text never
    gives. A 1 always fails, so re-rolling it cannot cost the attacker anything.

The grant lasts the phase (reset in main.py's per-phase block beside the Kill
Rig's). The AI answers through the Kill Rig's injected warpath_verdict() - roll
unless a 1 would cost an objective.
"""

import copy

from game.squad import unit_wide_ability
from game.warpath import WarpathController
from game.weapons import MELEE

WEIRDBOY_WARPATH_LABEL = "Warpath (Weirdboy)"


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "weirdboy_warpath"))


def is_active(squad):
    return bool(getattr(squad, "weirdboy_warpath_active", False))


def adjusted_weapon(weapon, squad):
    """[PSYCHIC] on a melee weapon while the grant is up. A copy - the shared
    WeaponProfile instance is never mutated."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not is_active(squad):
        return weapon
    if getattr(weapon, "psychic", False):
        return weapon
    granted = copy.copy(weapon)
    granted.psychic = True
    return granted


def rerolls_wound_ones(squad):
    """The melee wound step's automatic 1s. Only the fight side asks, so the
    "melee" of the printed line needs no weapon test here."""
    return is_active(squad)


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "weirdboy_warpath_active", False):
            squad.weirdboy_warpath_active = False


class WeirdboyWarpathController(WarpathController):
    ABILITY_FLAG = "weirdboy_warpath"
    ACTIVE_FLAG = "weirdboy_warpath_active"
    EFFECT_TEXT = "its melee attacks can re-roll wound rolls of 1 and have [PSYCHIC]"

    def reset_phase(self, squads=()):
        reset_phase(squads)
