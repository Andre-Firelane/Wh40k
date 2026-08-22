"""Wraithguard's "Psychic Guidance" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "While this unit is within 12" of one or more friendly AELDARI PSYKER models,
  models in this unit have a Leadership characteristic of 6+ and each time a
  model in this unit makes an attack, add 1 to the Hit roll."

TWO EFFECTS, TWO PLACES
-----------------------
  * The LEADERSHIP half is an OVERRIDE ("have a Leadership characteristic of
    6+"), folded into game/leadership.py's leadership_threshold() - the one
    place rule 01.06's "it only needs to beat the lowest Ld present" is
    computed. Wraithguard print Ld8+, so it is an improvement here; it is
    written as the rule reads (a flat value) rather than as a maximum, and the
    fold takes the better of the two so a future unit with a printed Ld6+ or
    better cannot be made worse by it.
  * The HIT half is a +1 in _hit_modifiers(), in BOTH game/shooting.py and
    game/fight.py: the text says "makes an attack", not "makes a ranged
    attack", so restricting it to shooting would be a simplification rather
    than the rule.

INERT TODAY, AND DELIBERATELY BUILT ANYWAY
------------------------------------------
No AELDARI PSYKER datasheet exists in this engine yet, so the condition is
currently always false. That is not the same as an ability that does nothing:
it is a condition that correctly evaluates to False and will start firing the
moment such a datasheet is added, with no further work. (UnitProfile.psyker
does already exist - the Ork Kill Rig carries it - which is exactly why the
AELDARI half of the check is not optional: without it, an Ork psyker in the
same army would buff Wraithguard.)

"FRIENDLY" is same-owner, and AELDARI is read off the datasheet's FACTION
rather than its keyword line: game/factions/aeldari.py deliberately does not
repeat the faction keywords on each datasheet, because the Faction object
carries them (see that module's own note).
"""

AELDARI_KEYWORD = "AELDARI"
PSYCHIC_GUIDANCE_RANGE_IN = 12.0
PSYCHIC_GUIDANCE_LEADERSHIP = "6+"


def squad_has_psychic_guidance(squad):
    """Rule 19.04's shape: any() rather than all(), so an attached model
    without the ability does not take it away from the unit."""
    models = getattr(squad, "models", None)
    if not models:
        return False
    return any(getattr(m.profile, "psychic_guidance", False) and not m.is_dead() for m in models)


def _is_aeldari(squad):
    datasheet = getattr(squad, "datasheet", None)
    faction = getattr(datasheet, "faction", None)
    return getattr(faction, "keyword", None) == AELDARI_KEYWORD


def _friendly_aeldari_psyker_models(squad, all_tokens):
    for token in all_tokens or ():
        if token.is_dead() or not getattr(token.profile, "psyker", False):
            continue
        other = getattr(token, "squad", None)
        if other is None or other.owner != squad.owner or other is squad:
            continue
        if _is_aeldari(other):
            yield token


def applies(squad, all_tokens):
    """Whether the unit is currently within 12" of a friendly AELDARI PSYKER.

    Measured centre to centre rather than edge to edge, matching how every
    other "within X inches of a model" aura in this engine measures - the
    distinction is below the granularity these ranges are chosen at."""
    if not squad_has_psychic_guidance(squad):
        return False
    mine = [m for m in squad.models if not m.is_dead()]
    if not mine:
        return False
    for psyker in _friendly_aeldari_psyker_models(squad, all_tokens):
        for model in mine:
            dx = model.x_in - psyker.x_in
            dy = model.y_in - psyker.y_in
            if (dx * dx + dy * dy) ** 0.5 <= PSYCHIC_GUIDANCE_RANGE_IN:
                return True
    return False
