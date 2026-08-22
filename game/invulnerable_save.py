"""A model's invulnerable save after every source that can grant or improve
one - the single place the Save roll asks.

Extracted from game/waaagh.py, which owned it while the Ork Waaagh! was the
only granting source. The Aeldari Serpent's Scale Platform's Serpent Shield is
the second, and a module named after one faction's army rule is the wrong home
for another faction's wargear. Cheap to move: there was exactly one caller
(game/damage_resolution.py's Save roll).

The composition rule for every source, and it is always the same one: take
whichever save is BETTER and never make an existing one worse. That mirrors
rule 05.04, which already lets a model use the better of its armour and
invulnerable saves - so a model that prints a 4+ invulnerable keeps it when a
5+ is granted.

Returns a threshold STRING ("5+", or the model's own unchanged), matching
UnitProfile.invulnerable_save's own convention, so callers keep parsing it with
parse_threshold() exactly as before.

Known gap, stated rather than left to be found: game/damage_estimate.py reads
UnitProfile.invulnerable_save DIRECTLY and so sees none of these grants. The
AI therefore overestimates its damage against a unit whose invulnerable save is
granted rather than printed - which now includes any Serpent Shield unit it
shoots at. That was already true for the Waaagh! grant; closing it means
teaching the estimate both sources and re-verifying it, which is its own
measured step.
"""

from game.thresholds import parse_threshold
from game.waaagh import WAAAGH_INVULNERABLE_SAVE

SERPENT_SHIELD_INVULNERABLE_SAVE = "5+"
SHIMMERSHIELD_INVULNERABLE_SAVE = "4+"


def unit_has_serpent_shield(squad):
    """Serpent Shield: "models in the bearer's unit have a 5+ invulnerable
    save".

    Read LIVE off the surviving models rather than baked onto the unit when it
    is built, for the same reason game/pulse_accelerator.py gives: the grant
    comes from one model and has to end when that model dies."""
    models = getattr(squad, "models", None) or ()
    return any(
        getattr(m.profile, "serpent_shield", False) and not m.is_dead()
        for m in models
    )


def _better(current, candidate):
    """`candidate` if it is a strictly better threshold, else `current`."""
    current_threshold = parse_threshold(current)
    candidate_threshold = parse_threshold(candidate)
    if candidate_threshold is None:
        return current
    if current_threshold is not None and current_threshold <= candidate_threshold:
        return current  # already at least as good - a lower threshold is better
    return candidate


def effective_invulnerable_save(model, waaagh=None, melee=False):
    """This model's invulnerable save, printed value plus every grant.

    `melee` is whether the attack being saved against is a melee one. Some
    printed invulnerable saves improve against one attack type only - Howling
    Banshees print "5+, improved to 4+ against melee attacks" - and that is a
    property of the PRINTED save rather than a granted one, so it is folded in
    first and every grant is then measured against the result. The caller knows
    the attack type from the weapon the Save roll is being made against;
    defaulting to False keeps every existing call site meaning what it did."""
    save = model.profile.invulnerable_save
    if melee:
        save = _better(save, getattr(model.profile, "invulnerable_save_vs_melee", None))
    squad = getattr(model, "squad", None)

    if (waaagh is not None and model.profile.waaagh
            and squad is not None and waaagh.is_active(squad.owner)):
        save = _better(save, WAAAGH_INVULNERABLE_SAVE)

    if unit_has_serpent_shield(squad):
        save = _better(save, SERPENT_SHIELD_INVULNERABLE_SAVE)

    # Dire Avengers' Shimmershield: "The BEARER has a 4+ invulnerable save" -
    # one model, not the unit, so unlike the Serpent Shield above it is read
    # off the token rather than swept over the squad. Set by the Gear item in
    # game/factions/aeldari.py, which is also where the pistol it replaces is
    # removed.
    if getattr(model, "shimmershield", False):
        save = _better(save, SHIMMERSHIELD_INVULNERABLE_SAVE)

    return save
