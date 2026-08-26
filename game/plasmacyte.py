"""Skorpekh Destroyers' "Plasmacyte" wargear.

RULE (printed, word for word):
  "Once per battle for each Plasmacyte this unit has, when this unit is
   selected to fight, you can use this ability. If you do, until the end of the
   phase, melee weapons equipped by models in this unit have the
   [DEVASTATING WOUNDS] ability."

THE COUNT IS THE INTERESTING PART. "Once per battle FOR EACH Plasmacyte this
unit has" is not once per battle - a six-model unit may take two Plasmacytes
and therefore gets two uses over the whole game. So the ledger is a REMAINING
USES counter seeded from how many the unit was built with, not a boolean and
not a set of unit ids.

WHERE THE COUNT COMES FROM: game/factions/necrons.py's Gear item increments
Token.plasmacyte_count as it is applied. That is per-token, and the printed
allowance is per-UNIT, so remaining_uses() sums across the unit's models - and
because it sums live models only, losing the model carrying the Plasmacyte
takes its use with it, which is the same reading every other wargear ability
here uses (rule 19.04).

THE GRANT ITSELF is a [DEVASTATING WOUNDS] keyword on melee weapons until the
end of the phase, which is exactly the shape of Ferocious Rage
(game/ferocious_rage.py) - so it is a chain entry in FightController's
_adjusted_weapon(), reading a phase-scoped flag on the Squad. It must be in the
chain rather than applied at the wound step because _crit_note() has to know at
ROLL time whether a critical die is a [DEVASTATING WOUNDS] one.

KNOWN GAP, stated in game/factions/necrons.py too: the printed "for every 3
models in this unit, this unit can have 1 Plasmacyte" ratio is a LIST-BUILDING
limit, and this engine has no army-building step to enforce it in. What is
enforced here is the part that matters in play - a unit cannot use the ability
more times than it has Plasmacytes.
"""

import copy


def plasmacyte_count(squad):
    """How many Plasmacytes this unit still has, summed over its living
    models."""
    if squad is None:
        return 0
    return sum(int(getattr(m, "plasmacyte_count", 0) or 0)
               for m in squad.models if not m.is_dead())


def uses_spent(squad):
    return int(getattr(squad, "plasmacyte_uses_spent", 0) or 0)


def remaining_uses(squad):
    """"Once per battle for each Plasmacyte this unit has"."""
    return max(0, plasmacyte_count(squad) - uses_spent(squad))


def can_use(squad):
    """The whole condition line: the unit has an unspent Plasmacyte, and the
    grant is not already running this phase (using a second one on top of the
    first would spend it for nothing)."""
    if squad is None or getattr(squad, "plasmacyte_active", False):
        return False
    return remaining_uses(squad) > 0


def use(squad):
    """Spend one Plasmacyte and turn the grant on for the phase."""
    if not can_use(squad):
        return False
    squad.plasmacyte_uses_spent = uses_spent(squad) + 1
    squad.plasmacyte_active = True
    return True


def reset_phase(squads=()):
    """"until the end of the phase". The SPENT count deliberately survives -
    it is a per-battle ledger, not a per-phase one."""
    for squad in squads or ():
        squad.plasmacyte_active = False


def adjusted_weapon(weapon, squad):
    """[DEVASTATING WOUNDS] on melee weapons while the grant is up.

    Copies rather than mutating: the WeaponProfile instance is shared, and
    this repo's standing rule is that effects copy."""
    if weapon is None or not getattr(squad, "plasmacyte_active", False):
        return weapon
    if weapon.devastating_wounds:
        return weapon
    granted = copy.copy(weapon)
    granted.devastating_wounds = True
    return granted
