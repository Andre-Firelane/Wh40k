"""The Tomb Blades' three wargear abilities (Necrons).

RULES (printed, word for word):
  NEBULOSCOPE: "Ranged weapons equipped by the bearer have the [IGNORES COVER]
    ability."
  SHADOWLOOM:  "The bearer has the Stealth ability."
  SHIELDVANES: "The bearer has a 3+ Save characteristic and a Move
    characteristic of 8"."

ALL THREE ARE PER-BEARER, set by a Gear item on the TOKEN rather than by a
profile flag - "any number of models can each be equipped with" - so a squad
can carry a different mix on every model. That is what makes each of them a
per-MODEL question below, and it is also what makes Shadowloom interesting.

SHIELDVANES IS A TRADE, NOT AN UPGRADE, and both halves are OVERRIDES for that
reason: the Save improves (4+ -> 3+) and the Move WORSENS (12" -> 8"). A
_better()-style fold, which is how nearly every other grant in this engine is
written, would silently keep the 12" and hand out the 3+ for free. Measured
against the printed profile rather than assumed: TombBladeProfile is Sv4+ M12".

SHADOWLOOM CANNOT BE ASKED PER MODEL AT THE POINT IT MATTERS. Rule 24.33 is a
UNIT ability - "if every model in a unit has this ability" - so buying one
shadowloom grants the bearer nothing anybody can observe, and buying six
grants the unit Stealth. That is the printed rules working as written, not a
simplification, and it is why this module hands squad_has_stealth() a
PREDICATE rather than a threshold: the every-model question stays where it is,
and the answer for one model becomes "its profile prints it OR it carries a
shadowloom".

NEBULOSCOPE IS A KEYWORD GRANT, AND KEYWORD GRANTS ARE READ TWICE in this
engine - once by the damage chain and once by an eligibility gate that does
not resemble it (see CLAUDE.md's error class 10, and what it cost [ASSAULT]
and [PISTOL]). [IGNORES COVER] is the gentle case: its ONE reader is
ShootingController._ignores_cover(), which already ORs a weapon-level term
with several unit-level ones. So the grant is applied to the WEAPON in the
adjuster chain, where that term picks it up, and there is no second gate to
miss. Written down because the next keyword may not be so kind.
"""

import copy

#: "a 3+ Save characteristic and a Move characteristic of 8 inches".
SHIELDVANES_SAVE = "3+"
SHIELDVANES_MOVE_IN = 8


def has_nebuloscope(model):
    return bool(getattr(model, "nebuloscope", False))


def has_shadowloom(model):
    return bool(getattr(model, "shadowloom", False))


def has_shieldvanes(model):
    return bool(getattr(model, "shieldvanes", False))


# ------------------------------------------------------------------ Shieldvanes

def save_override(model):
    """The bearer's Save characteristic, or None for "no opinion"."""
    return SHIELDVANES_SAVE if has_shieldvanes(model) else None


def movement_override_in(model):
    """The bearer's Move characteristic, or None.

    An OVERRIDE and deliberately not a max(): 8" is WORSE than the Tomb
    Blade's printed 12", which is the whole point of the wargear."""
    return SHIELDVANES_MOVE_IN if has_shieldvanes(model) else None


# ------------------------------------------------------------------- Shadowloom

def model_has_stealth(model):
    """Rule 24.33 for ONE model: its profile prints Stealth, or it carries a
    shadowloom. Handed to squad_has_stealth()'s every-model question rather
    than answering that question here."""
    return bool(getattr(getattr(model, "profile", None), "stealth", False)
                or has_shadowloom(model))


# ------------------------------------------------------------------ Nebuloscope

def adjusted_weapon(weapon, model):
    """[IGNORES COVER] on the bearer's RANGED weapons.

    Returns a COPY when it grants, never the shared class instance - a
    WeaponProfile subclass is a class object shared by every model that
    carries it, and mutating one is this repo's standing way to break a
    datasheet everywhere at once."""
    from game.weapons import RANGED
    if weapon is None or not has_nebuloscope(model):
        return weapon
    if getattr(weapon, "weapon_type", None) != RANGED:
        return weapon
    if getattr(weapon, "ignores_cover", False):
        return weapon           # already has it; nothing to copy
    out = copy.copy(weapon)
    out.ignores_cover = True
    return out


# ------------------------------------------------------------------ Gear hooks

def equip_nebuloscope(token):
    token.nebuloscope = True


def equip_shadowloom(token):
    token.shadowloom = True


def equip_shieldvanes(token):
    token.shieldvanes = True
