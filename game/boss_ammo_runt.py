"""The Warboss's Boss' Ammo Runt (2026-09 Ork codex).

RULE (verbatim, rules/orks/Warboss.md):
  "Boss' Ammo Runt (Once per battle, per unit): In your Shooting phase, when
   this unit is selected to shoot, you can use this ability. If you do, this
   model's ranged attacks have +1 to hit rolls."

THE SECOND CARRIER OF game/ork_ammo_runts.py's offer. The WHEN, the spend and
the bonus are the Boyz' Ammo Runts word for word, so the controller is a
subclass that sets the knobs. Two words differ, and both are real:

  * "this MODEL's ranged attacks" - the Warboss's own, not his mob's. After a
    19.01 merge he is one model of twenty, so shooting.py's _attack_key()
    carries attack_key() below; without it the one-representative shortcut
    would hand +1 to whichever group he shares, or take it from him.
  * "per UNIT" - the spend lives on the unit, like Ammo Runts, so a Warboss
    leading Boyz holds TWO separate once-per-battle uses: the mob's and his.
    Each is asked about on its own.

The AI uses it at its first opportunity, as it does Ammo Runts - 0 API calls.
"""

from game.modifiers import Modifier
from game.ork_ammo_runts import AMMO_RUNTS_HIT_BONUS, AmmoRuntsController

BOSS_AMMO_RUNT_NAME = "Boss' Ammo Runt"


def bearer_models(squad):
    """The living models of `squad` that print the ability."""
    return [m for m in getattr(squad, "models", ()) or ()
            if not m.is_dead() and getattr(m.profile, "boss_ammo_runt", False)]


def has_ability(squad):
    return squad is not None and bool(bearer_models(squad))


def is_active(squad):
    return bool(getattr(squad, "boss_ammo_runt_active", False))


def attack_key(model):
    """The per-model term for shooting.py's _attack_key(): True for a bearer
    only, so no group that existed before splits."""
    return bool(model is not None and getattr(model.profile, "boss_ammo_runt", False))


def hit_modifiers(model, squad):
    """The Modifier for a group whose representative is a bearer, while the
    grant is up. Exact because attack_key() keeps a bearer's group his own."""
    if not is_active(squad) or not attack_key(model):
        return []
    return [Modifier(-AMMO_RUNTS_HIT_BONUS, BOSS_AMMO_RUNT_NAME)]


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "boss_ammo_runt_active", False):
            squad.boss_ammo_runt_active = False


class BossAmmoRuntController(AmmoRuntsController):
    NAME = BOSS_AMMO_RUNT_NAME
    USED_ATTR = "boss_ammo_runt_used"
    ACTIVE_ATTR = "boss_ammo_runt_active"
    SUBJECT = "the Warboss's own"
    USE_LABEL = "Use Boss' Ammo Runt"

    def has_ability(self, squad):
        return has_ability(squad)
