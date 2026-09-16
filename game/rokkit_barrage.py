"""The Tankbustas' Rokkit Barrage (2026-09 Ork codex).

RULE (verbatim, rules/orks/Tankbustas.md):
  "Rokkit Barrage: In your Shooting phase, when this unit has shot, select one
   enemy unit hit by those attacks. That unit makes a battle-shock roll, with -1
   to that battle-shock roll."

THE FOURTH CARRIER of game/battle_shock_after_shooting.py, after Maugan Ra's
Face of Death, the Leystalker's Panicked Quarry and Path of the Outcast's
Eldritch Suppression. Word for word the Leystalker's sentence without its
"(excluding MONSTER/VEHICLE units)" - so it names no target restriction, like
Face of Death, and a Tankbusta volley can rattle the tank it just hit.

IT IS NOT OPTIONAL ("select", "makes"): the only decision is WHICH unit that was
hit, and a sole candidate is not asked about. What this carrier adds to the
shared machine is the AI's answer: the Orks are the faction the AI plays, and
the three Aeldari carriers never needed one. The base now takes `auto_players`
and `target_pick` (both optional, so those three are unchanged), and main.py
passes ai/agent_driver.py's battle_shock_target_choice() - 0 API calls.

"IN YOUR SHOOTING PHASE" needs nothing here: ShootingController only walks
on_squad_finished_shooting for a non-reactive activation.
"""

from game.battle_shock_after_shooting import (
    BATTLE_SHOCK_PENALTY, BattleShockAfterShooting, any_target,
)

ROKKIT_BARRAGE_LABEL = "Rokkit Barrage"

#: "with -1 to that battle-shock roll".
ROKKIT_BARRAGE_PENALTY = BATTLE_SHOCK_PENALTY


def has_rokkit_barrage(squad):
    return RokkitBarrageController.has_ability_on(squad)


class RokkitBarrageController(BattleShockAfterShooting):
    """Sits in ShootingController.on_squad_finished_shooting."""

    flag = "rokkit_barrage"
    label = ROKKIT_BARRAGE_LABEL
    eligible = staticmethod(any_target)

    @classmethod
    def has_ability_on(cls, squad):
        if squad is None:
            return False
        return any(getattr(m.profile, cls.flag, False)
                   for m in getattr(squad, "models", ()) or () if not m.is_dead())
