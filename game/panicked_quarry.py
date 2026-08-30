"""The Leystalker's "Panicked Quarry" - a datasheet ability.

RULE (printed, word for word):
  "In your Shooting phase, when this unit has shot, select one enemy unit
  (excluding MONSTER/VEHICLE units) hit by those attacks. That enemy unit makes
  a battle-shock roll, with -1 to that battle-shock roll."

Maugan Ra's Face of Death prints the same sentence with one clause fewer; the
shared half is game/battle_shock_after_shooting.py, extracted when this became
its second consumer. What belongs to this datasheet is the exclusion.

"EXCLUDING MONSTER/VEHICLE UNITS" is the whole difference, and it is not
decorative: those are exactly the targets a sniper on a drakesteed has no
business panicking, and the Leystalker's own Long Rifle carves the same line
for its conditional [DEVASTATING WOUNDS]. Both use the exact complement of
squad.is_monster_or_vehicle_unit(), so the two halves of that datasheet can
never disagree about which targets they mean.
"""
from game.battle_shock_after_shooting import (
    BATTLE_SHOCK_PENALTY, BattleShockAfterShooting,
    excluding_monsters_and_vehicles,
)

PANICKED_QUARRY_LABEL = "Panicked Quarry"
PANICKED_QUARRY_PENALTY = BATTLE_SHOCK_PENALTY


def unit_has_panicked_quarry(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "panicked_quarry", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class PanickedQuarryController(BattleShockAfterShooting):
    """Sits in ShootingController.on_squad_finished_shooting."""

    flag = "panicked_quarry"
    label = PANICKED_QUARRY_LABEL
    eligible = staticmethod(excluding_monsters_and_vehicles)
