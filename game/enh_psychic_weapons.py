"""Three Enhancements that change the bearer's PSYCHIC weapons, in one module
because they answer one question three ways.

RULES (verbatim, from rules/aeldari/detachments/):
  Seersight Strike (Windrider Host, 15):
    "ASURYANI MOUNTED PSYKER model only. Psychic weapons equipped by the bearer
    have the [anti-monster 2+] and [anti-vehicle 2+] abilities."
  Psychic Destroyer (Warhost, 30):
    "ASURYANI PSYKER model only. Add 1 to the Damage characteristic of ranged
    Psychic weapons equipped by the bearer."
  Stone of Eldritch Fury (Seer Council, 15):
    "ASURYANI PSYKER model only. Add 12" to the Range characteristic of ranged
    Psychic weapons equipped by the bearer."

ONE MODULE BECAUSE ONE QUESTION. All three begin "Psychic weapons equipped by
the bearer", and that clause is the part worth having in one place: it is the
[PSYCHIC] KEYWORD (rule 24.29, WeaponProfile.psychic), not a weapon name, and
each of the three would otherwise re-derive it. What differs is only which
characteristic moves, so they are three functions rather than three files - the
same call game/enh_exemplars.py and game/enh_prototype_weapons.py make.

"RANGED PSYCHIC WEAPONS" IS TWO OF THE THREE. Seersight Strike says only
"Psychic weapons", so it reaches a melee one; the other two say "ranged Psychic
weapons". One printed word, and it is checked separately for each - a shared
"psychic and ranged" helper would have silently narrowed Seersight Strike.

PER BEARER, NOT PER UNIT. All three say "equipped by the bearer", so they are
read per MODEL - which is why Psychic Destroyer and Seersight Strike need a term
in the attack key: shooting.py groups attacks by their stats and reads the
group's FIRST model as representative, so a bearer whose stats happen to match a
squadmate's would otherwise hand the whole group its answer. That is the same
fix psychic_communion_bonus, Precision of the Patient Hunter and Prototype
Weapon System all needed, and it reads 0/False for every other model so no
existing group splits.

STONE OF ELDRITCH FURY IS NOT IN THE ATTACK KEY, and that is not an oversight:
range is not a characteristic the key groups on, and game/weapon_range.py is
asked per MODEL already (its own docstring says it takes the model "so callers
can pass what they already have on the hot path"). It is the FOURTH bonus term
there, and the first that is not +6".

A ROLLED DAMAGE GETS THE BONUS TOO, on its NOTATION. My first version skipped a
weapon whose Damage is a notation, reasoning that adding to the preview value
would be overwritten by the roll - true of the preview, and the wrong
conclusion. "Add 1 to the Damage characteristic" of a D3 weapon makes it D3+1,
and DiceNotation carries a `bonus` field for exactly that; rule 24.25's [MELTA]
already does it this way (game/shooting.py's melta_adjusted_weapon), as does
Psychic Communion for an Attacks notation. BOTH are updated - the notation so
the roll is right, and `damage` so the preview beside it agrees.

IT MATTERS HERE MORE THAN ANYWHERE: measured, EVERY ranged psychic weapon a
Farseer, Eldrad, a Farseer Skyrunner or the Yncarne carries prints a rolled
Damage. Skipping notations would have made a 30-point Enhancement inert on
four of its most likely bearers, and a probe on a flat-damage weapon would
never have shown it.

NEVER A DOWNGRADE, AND NEVER A MUTATION. A WeaponProfile CLASS is shared by
every model in the game carrying that gun, so each adjuster copies before
writing; and Seersight Strike's [ANTI-X] is folded into whatever the weapon
already prints, because game/shooting.py's _wound_crit_threshold() takes the
BEST (lowest) threshold where several match - so a weapon printing
[ANTI-VEHICLE 4+] keeps a better 2+ rather than being overwritten either way.
"""
import copy

from game import enhancements
from game.dice_notation import DiceNotation
from game.weapons import RANGED

SEERSIGHT_STRIKE = "Seersight Strike"
PSYCHIC_DESTROYER = "Psychic Destroyer"
STONE_OF_ELDRITCH_FURY = "Stone of Eldritch Fury"

#: "[anti-monster 2+] and [anti-vehicle 2+]", in the (keyword, threshold) shape
#: this engine already uses for a printed pair.
SEERSIGHT_STRIKE_ANTI = (("MONSTER", 2), ("VEHICLE", 2))

#: "Add 1 to the Damage characteristic".
PSYCHIC_DESTROYER_DAMAGE = 1

#: 'Add 12" to the Range characteristic'.
STONE_OF_ELDRITCH_FURY_RANGE_IN = 12.0


def _is_psychic(weapon):
    """Rule 24.29's [PSYCHIC] keyword - what all three clauses name."""
    return weapon is not None and bool(getattr(weapon, "psychic", False))


def _is_ranged_psychic(weapon):
    """The narrower clause the other two print."""
    return _is_psychic(weapon) and getattr(weapon, "weapon_type", None) == RANGED


def _bearer_has(model, name):
    return model is not None and enhancements.model_is_active(model, name)


# --- Seersight Strike ------------------------------------------------------

def seersight_anti(model, weapon):
    """The [ANTI-X] entries this bearer's psychic weapon gains, or ()."""
    if not _is_psychic(weapon) or not _bearer_has(model, SEERSIGHT_STRIKE):
        return ()
    return SEERSIGHT_STRIKE_ANTI


def _merged_anti(printed, extra):
    """Both sets, as the flat tuple-of-tuples this engine's fold expects.

    Not a replacement: _wound_crit_threshold() takes the BEST threshold among
    every matching entry, so keeping the printed ones costs nothing and losing
    them could cost a better one against a keyword this Enhancement does not
    name."""
    if not printed:
        return tuple(extra)
    entries = printed if isinstance(printed[0], tuple) else (printed,)
    return tuple(entries) + tuple(extra)


# --- the three adjusters ---------------------------------------------------

def adjusted_weapon(weapon, model):
    """Every one of the three that applies to this (model, weapon), on ONE
    copy. Returns `weapon` untouched when none does."""
    if weapon is None or model is None:
        return weapon
    out = None

    anti = seersight_anti(model, weapon)
    if anti:
        out = copy.copy(weapon)
        out.anti = _merged_anti(getattr(weapon, "anti", None), anti)

    if _is_ranged_psychic(weapon) and _bearer_has(model, PSYCHIC_DESTROYER):
        out = out if out is not None else copy.copy(weapon)
        out.damage = weapon.damage + PSYCHIC_DESTROYER_DAMAGE
        # A ROLLED Damage gets the bonus on its NOTATION - see the docstring.
        if weapon.damage_notation is not None:
            out.damage_notation = DiceNotation(
                weapon.damage_notation.sides,
                weapon.damage_notation.bonus + PSYCHIC_DESTROYER_DAMAGE)

    return out if out is not None else weapon


def range_bonus_in(model, weapon):
    """Stone of Eldritch Fury's +12". Read by game/weapon_range.py's fold -
    the fourth bonus term there, and the first that is not +6"."""
    if not _is_ranged_psychic(weapon) or not _bearer_has(model, STONE_OF_ELDRITCH_FURY):
        return 0.0
    return STONE_OF_ELDRITCH_FURY_RANGE_IN


def attack_key(model):
    """The per-MODEL term shooting.py's _attack_key() needs.

    Two of the three change a characteristic the key groups on (Damage, and
    the crit threshold [ANTI-X] feeds), and the key's one-representative
    shortcut would otherwise hand a bearer's answer to its whole group. Reads
    (False, False) for every other model, so no existing group splits."""
    if model is None:
        return (False, False)
    return (_bearer_has(model, SEERSIGHT_STRIKE),
            _bearer_has(model, PSYCHIC_DESTROYER))
