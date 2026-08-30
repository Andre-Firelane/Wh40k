"""Aspect Host Enhancement: Aspect of Murder (15 pts).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  "AUTARCH or AUTARCH WAYLEAPER model only. Add 1 to the Damage characteristic
  of melee weapons equipped by the bearer, and those weapons have the
  [precision] ability."

THE FIRST ENHANCEMENT IN THIS ENGINE TO TOUCH THE MELEE CHAIN. All nineteen
T'au ones and the five Aeldari ones before it live in game/shooting.py's
_adjusted_weapon() or in a non-attack seam; this one is MELEE-only, so it goes
into game/fight.py's twin and nowhere else. Checked as negative space in the
test - game/shooting.py never importing this module is a stronger statement
than a ranged scene that happens to come out unchanged.

AND IT NEEDS A TERM IN _melee_attack_key(), which is the fourth time this exact
fix has been needed (psychic_communion_bonus, Precision of the Patient Hunter,
Prototype Weapon System, and now this). The key groups melee attacks by
WS/S/AP/D and reads the group's FIRST model as representative; an Autarch
leading Howling Banshees whose blade happens to share those stats would
otherwise hand its +1 Damage and [PRECISION] to the whole squad. Reads False
for every other model, so no existing group splits.

TWO EFFECTS, ONE COPY. The +1 Damage and the [PRECISION] grant are one printed
sentence and one bearer, so they are applied together on a single copy.copy() -
a WeaponProfile CLASS is shared by every model in the game carrying that
weapon, and writing through would hand every Autarch's blade in existence a
permanent upgrade.

A ROLLED DAMAGE GETS THE BONUS ON ITS NOTATION, not skipped. "Add 1 to the
Damage characteristic" of a D3 weapon makes it D3+1, and DiceNotation carries a
`bonus` field for exactly that - rule 24.25's [MELTA] already does it this way.
Both halves are written: the notation so the roll is right, and `damage` so the
preview beside it agrees.

[PRECISION] IS NEVER A DOWNGRADE: a weapon that already prints it is returned
with only the Damage changed.
"""
import copy

from game import enhancements
from game.dice_notation import DiceNotation
from game.weapons import RANGED

ASPECT_OF_MURDER = "Aspect of Murder"

#: "Add 1 to the Damage characteristic".
ASPECT_OF_MURDER_DAMAGE = 1


def is_active(model):
    """Per BEARER - "melee weapons equipped by the bearer"."""
    if model is None:
        return False
    return enhancements.model_is_active(model, ASPECT_OF_MURDER)


def adjusted_weapon(weapon, model):
    """+1 Damage and [PRECISION] on the bearer's melee weapons."""
    if weapon is None or not is_active(model):
        return weapon
    if getattr(weapon, "weapon_type", None) == RANGED:
        return weapon              # "MELEE weapons", as printed
    out = copy.copy(weapon)
    out.damage = weapon.damage + ASPECT_OF_MURDER_DAMAGE
    # A ROLLED Damage gets the bonus on its NOTATION, not skipped - see the
    # docstring, and rule 24.25's [MELTA] for the same treatment.
    if weapon.damage_notation is not None:
        out.damage_notation = DiceNotation(
            weapon.damage_notation.sides,
            weapon.damage_notation.bonus + ASPECT_OF_MURDER_DAMAGE)
    out.precision = True
    return out


def attack_key(model):
    """The per-MODEL term game/fight.py's _melee_attack_key() needs - fourth
    instance of this fix. False for every other model."""
    return is_active(model)
