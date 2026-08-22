"""Warlock Conclave's "Psychic Communion" - a datasheet ability, so its own
module.

RULE (printed, word for word):
  "Each time this unit is selected to shoot, for each WARLOCK model in this
  unit, until the end of the phase, add 1 to the Attacks and Strength
  characteristics of that model's Destructor weapon for each other friendly
  AELDARI PSYKER model within 6" of that model (to a maximum of +2)."

PER MODEL, NOT PER UNIT - which is the whole shape of it
--------------------------------------------------------
Almost every aura in this codebase asks a question about a UNIT. This one asks
it once per WARLOCK, about that Warlock's own surroundings, and two models of
the same unit can legitimately end up with different bonuses. So the count is
stored on the MODEL, and the adjuster reads it from there.

That also means the weapon groups sort themselves out for free: a group is
keyed on (BS, S, AP, D, ...) via _attack_key(), and this ability changes S, so
Warlocks with different bonuses land in different groups without anything here
having to arrange it.

SNAPSHOT AT SELECTION, not per attack. "Each time this unit is selected to
shoot ... until the end of the phase" - so it is computed once, when the unit
is picked, and held. Models can die during a phase, and re-deriving it per
attack would silently shrink the bonus mid-activation, which the printed
wording does not say.

"EACH OTHER FRIENDLY AELDARI PSYKER MODEL" - so:
  * OTHER: a Warlock never counts itself, but its squadmates do count for it
    (they are other models, and they are psykers);
  * FRIENDLY: same owner;
  * AELDARI: read off the datasheet's FACTION, since game/factions/aeldari.py
    deliberately does not repeat faction keywords on each datasheet - the same
    lookup game/psychic_guidance.py uses, and for the same reason (the Ork Kill
    Rig is a PSYKER too).
"""

from game import psychic_guidance

PSYCHIC_COMMUNION_RANGE_IN = 6.0
PSYCHIC_COMMUNION_MAX_BONUS = 2
PSYCHIC_COMMUNION_WEAPON = "Destructor"


def _warlocks(squad):
    return [m for m in getattr(squad, "models", None) or ()
            if getattr(m.profile, "psychic_communion", False) and not m.is_dead()]


def bonus_for(model, squad, all_tokens):
    """How many other friendly AELDARI PSYKER models are within 6" of this one,
    capped at +2."""
    count = 0
    for token in all_tokens or ():
        if token is model or token.is_dead() or not getattr(token.profile, "psyker", False):
            continue
        other = getattr(token, "squad", None)
        if other is None or other.owner != squad.owner:
            continue
        # psychic_guidance's own AELDARI test, reused rather than re-derived -
        # it reads the datasheet's faction, which is where the keyword lives.
        if not psychic_guidance._is_aeldari(other):
            continue
        dx, dy = model.x_in - token.x_in, model.y_in - token.y_in
        if (dx * dx + dy * dy) ** 0.5 <= PSYCHIC_COMMUNION_RANGE_IN:
            count += 1
            if count >= PSYCHIC_COMMUNION_MAX_BONUS:
                return PSYCHIC_COMMUNION_MAX_BONUS
    return count


def on_selected_to_shoot(squad, all_tokens):
    """Called from ShootingController.start_shooting(). Stores each Warlock's
    own bonus for the rest of the phase."""
    for model in _warlocks(squad):
        model.psychic_communion_bonus = bonus_for(model, squad, all_tokens)


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads:
        for model in getattr(squad, "models", None) or ():
            if getattr(model, "psychic_communion_bonus", 0):
                model.psychic_communion_bonus = 0


def psychic_communion_adjusted_weapon(weapon, pairs):
    """+N to Attacks and Strength of that model's Destructor, on a shallow copy
    so the shared WeaponProfile instance is never mutated.

    Read off the group's representative model, which is exact here for the
    reason given in the module docstring: the bonus changes Strength, and
    Strength is part of _attack_key(), so a group's models all share it."""
    if not pairs:
        return weapon
    if weapon.name != PSYCHIC_COMMUNION_WEAPON:
        return weapon
    model = pairs[0][0]
    bonus = getattr(model, "psychic_communion_bonus", 0)
    if not bonus:
        return weapon
    import copy

    boosted = copy.copy(weapon)
    boosted.strength = weapon.strength + bonus
    # The Destructor's Attacks is a printed D6, so the bonus has to land on the
    # notation's own flat bonus - bumping only the preview/grouping placeholder
    # would do nothing once the count is actually rolled. `attacks` is bumped
    # too, purely so the preview and _attack_key stay consistent with it. Same
    # treatment melta_adjusted_weapon() gives a dice-notation Damage.
    boosted.attacks = weapon.attacks + bonus
    if weapon.attacks_notation is not None:
        from game.dice_notation import DiceNotation

        boosted.attacks_notation = DiceNotation(
            weapon.attacks_notation.sides, weapon.attacks_notation.bonus + bonus,
        )
    return boosted
