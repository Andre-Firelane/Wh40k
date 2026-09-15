"""Rule 24.01's conditional weapon abilities, granted against the real target.

A weapon prints "[LETHAL HITS: non-MONSTER/VEHICLE]": the ability, restricted
to a class of target. WeaponProfile.conditional_keywords holds each one as
(attribute, value, KeywordCondition) - ("lethal_hits", True,
NON_MONSTER_VEHICLE_TARGETS), ("sustained_hits", 2, MONSTER_OR_VEHICLE_TARGETS).

WHY IT IS NOT A FLAG. The hit and wound steps, _crit_note() and
extra_attack_dice() read `weapon.lethal_hits` & co. off the weapon the ADJUSTER
CHAIN returns, and none of them knows a condition. A flat flag would grant the
ability against exactly the targets the printed line excludes. So the grant is
one link of that chain - in BOTH game/shooting.py's and game/fight.py's
_adjusted_weapon() - and every reader downstream sees the right weapon without
knowing a condition exists.

THE LEYSTALKER'S LONG RIFLE WAS THE FIRST CARRIER and had its own module
(game/conditional_devastating_wounds.py, one flag for one keyword and one
condition). The Ork codex prints the same shape on almost every gun, with
other keywords and the positive condition too, so that module became this one;
its behaviour is pinned identical in test_conditional_keywords.py.

NEVER A DOWNGRADE. "Has the ability" GRANTS it: a weapon already carrying
[SUSTAINED HITS 2] keeps its 2 against a condition that would grant 1, and a
dice-notation value is left alone - the same two guards
game/ritual_butchery.py gives the keyword it grants.

Rule 24.02 (duplicated abilities are not cumulative) needs nothing here: a
keyword this engine stores as a flag cannot be granted twice, and a valued one
keeps the larger value, which is the instance a player would select.
"""

import copy


def entries(weapon):
    """The weapon's conditional abilities as a tuple (empty for almost all)."""
    return tuple(getattr(weapon, "conditional_keywords", ()) or ())


def _already_has(weapon, attribute, value):
    if attribute == "sustained_hits" and getattr(weapon, "sustained_hits_notation", None) is not None:
        return True
    current = getattr(weapon, attribute, 0)
    if isinstance(value, bool):
        return bool(current)
    return (current or 0) >= value


def adjusted_weapon(weapon, target_squad):
    """A copy carrying every conditional ability whose condition the target
    meets, or the SAME OBJECT when nothing applies - so a caller can tell
    "unchanged" from "copied" by identity."""
    if weapon is None or target_squad is None:
        return weapon
    adjusted = weapon
    for attribute, value, condition in entries(weapon):
        if not condition.matches(target_squad):
            continue
        if _already_has(adjusted, attribute, value):
            continue
        if adjusted is weapon:
            adjusted = copy.copy(weapon)
        setattr(adjusted, attribute, value)
    return adjusted
