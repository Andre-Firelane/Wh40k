"""Maugan Ra's "Face of Death" - a datasheet ability.

RULE (printed, word for word):
  "In your Shooting phase, after this model has shot, select one enemy unit hit
  by one or more of those attacks. That enemy unit must take a Battle-shock
  test, subtracting 1 from the result."

THE MACHINERY MOVED to game/battle_shock_after_shooting.py when the
Leystalker's Panicked Quarry turned out to print the same sentence with one
extra clause. What stays here is this datasheet's own reading, plus the names
its call sites already use.

NO TARGET RESTRICTION, and that is the difference: Panicked Quarry excludes
MONSTER and VEHICLE units, this one names nobody. So Maugan Ra can rattle a
Land Raider and the Leystalker cannot, which is its own test line.

NO PER-WEAPON CLAUSE either, unlike the Shadow Weaver's and the Night Spinner's
marks: Maugan Ra carries exactly one weapon, and the printed text says "one or
more of those attacks" without naming it. So the plain hit list is the right
input, and asking for a per-weapon subset would invent a restriction.
"""
from game.battle_shock_after_shooting import (
    BATTLE_SHOCK_PENALTY, BattleShockAfterShooting, any_target,
)

FACE_OF_DEATH_LABEL = "Face of Death"

#: "subtracting 1 from the result".
FACE_OF_DEATH_PENALTY = BATTLE_SHOCK_PENALTY


def unit_has_face_of_death(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "face_of_death", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class FaceOfDeathController(BattleShockAfterShooting):
    """Sits in ShootingController.on_squad_finished_shooting."""

    flag = "face_of_death"
    label = FACE_OF_DEATH_LABEL
    eligible = staticmethod(any_target)
