"""Canoptek Tomb Crawlers' "Weapon Sentinels" (Necrons).

RULE (printed, word for word):
  "Each time a model in this unit makes a ranged attack that targets a unit
   within 12", you can ignore any or all modifiers to the following: that
   attack's Ballistic Skill characteristic; the Hit roll; the Wound roll."

THREE THINGS TO IGNORE, AND THE THIRD IS NEW HERE. The first two are what
UnitProfile.ignores_hit_modifiers and Kauyon's Patient Hunter already do, and
they meet at ShootingController._hit_modifiers()'s filter. The WOUND roll has
never had such a filter, so this adds one to _wound_modifiers() - the first
reader of that idea on that fold.

"ANY OR ALL" IS RESOLVED AUTOMATICALLY, not asked. That is the reading rule
24.29 [PSYCHIC], UnitProfile.ignores_hit_modifiers, Kauyon and Aspect Host's
Warrior Focus all take, and it is not a shortcut: every filter of this shape
drops the WORSENING modifiers and keeps the improving ones, and there is no
board state in which a player wants to keep a worsening one. Asking per attack
would be error class 5 - offering something nobody would ever choose.

"THAT TARGETS A UNIT WITHIN 12"" is a property of the ATTACK, not of the unit,
so the same Tomb Crawler shooting a second, farther target that phase gets
nothing. Measured from the shooting unit to the target unit, base edge to base
edge, at the moment the modifiers are folded - which is where the target is
known.

"A MODEL IN THIS UNIT MAKES A RANGED ATTACK" - ranged only, so
game/fight.py is deliberately untouched. Stated because the two neighbours of
this rule in the Canoptek batch (Harassment Swarm) DO reach both steps, and the
difference is the printed word.
"""

from game.squad import edge_distance

WEAPON_SENTINELS_LABEL = "Weapon Sentinels"

#: "targets a unit within 12"".
WEAPON_SENTINELS_RANGE_IN = 12.0


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def unit_has_ability(squad):
    return squad is not None and any(
        getattr(m.profile, "weapon_sentinels", False) for m in _living(squad))


def applies(shooter_squad, target_squad):
    """Whether THIS attack qualifies: the shooting unit has the ability and
    the target is within 12"."""
    if not unit_has_ability(shooter_squad) or target_squad is None:
        return False
    mine, theirs = _living(shooter_squad), _living(target_squad)
    if not mine or not theirs:
        return False
    return any(edge_distance(a, b) <= WEAPON_SENTINELS_RANGE_IN
               for a in mine for b in theirs)


def filtered(modifiers, shooter_squad, target_squad):
    """The modifier list with the worsening ones dropped when this applies.

    ONE function for both folds (Hit and Wound), because the printed sentence
    names them in one breath and the filter is the same - two copies would be
    two chances for one of them to stop matching the other."""
    if not applies(shooter_squad, target_squad):
        return modifiers
    return [m for m in modifiers if m.amount <= 0]
