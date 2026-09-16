"""The Flash Gitz' Finderz Keeperz (2026-09 Ork codex).

RULE (verbatim, rules/orks/Flash Gitz.md):
  "Finderz Keeperz: In your Shooting phase, if any of the following apply, this
   unit's ranged attacks have +1 AP:
   - This unit is within range of an objective.
   - The target of that attack is within range of an objective."

"ANY OF THE FOLLOWING" IS AN OR, and it is Guardian Battlehost's Defend at All
Costs' "that model's unit and/or the target unit" in other words. Both now ask
objectives.attacker_or_target_within_range_of_objective() - one definition of
the OR, extracted at this second consumer - so the two cannot drift about what
"within range of an objective" is (the 3" reading every "within range" rule in
this engine uses; see game/objectives.py and the Cleanse note in CLAUDE.md).

WHERE IT HANGS: ShootingController._adjusted_weapon(), as an AP change on a copy.
In the chain rather than at the wound step because the Save roll reads the AP
off the weapon that chain returns - anywhere else and the +1 never reaches the
roll. "+1 AP" IMPROVES the characteristic, so the value goes one more negative.

"IN YOUR SHOOTING PHASE": a reactive activation (Fire Overwatch in the
opponent's turn) is not the unit's own Shooting phase, so it gains nothing -
the same `reactive` flag game/hidden_after_shooting.py reads for Expert
Fieldcraft's identical clause.

"THIS UNIT" is the unit, read component-wise (rule 19.04) through
unit_wide_ability(): a leader joining the Flash Gitz does not strip the ability.
"""

import copy

from game import objectives as objectives_module
from game.squad import unit_wide_ability
from game.weapons import RANGED

FINDERZ_KEEPERZ_NAME = "Finderz Keeperz"
#: "+1 AP" - an improvement, so the AP characteristic goes down by 1.
FINDERZ_KEEPERZ_AP_BONUS = 1


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "finderz_keeperz"))


def applies(squad, target_squad, objectives=(), reactive=False):
    """The whole printed condition for one attack against `target_squad`."""
    if reactive or not objectives or not has_ability(squad):
        return False
    return objectives_module.attacker_or_target_within_range_of_objective(
        squad, target_squad, objectives)


def adjusted_weapon(weapon, squad, target_squad, objectives=(), reactive=False):
    """The chain link: a copy with +1 AP for a ranged weapon when applies(),
    otherwise the weapon it was handed, untouched."""
    if weapon is None or getattr(weapon, "weapon_type", None) != RANGED:
        return weapon
    if not applies(squad, target_squad, objectives, reactive=reactive):
        return weapon
    granted = copy.copy(weapon)
    granted.ap = weapon.ap - FINDERZ_KEEPERZ_AP_BONUS
    return granted
