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

NO LONGER INERT - this note used to say "no AELDARI PSYKER datasheet exists in
this engine yet", which was true when Wraithguard were built and has since
stopped being true: the Warlock Conclave, Farseer, Eldrad Ulthran and Warlock
Skyrunners all set `psyker`. The ability fires for real now. (UnitProfile.psyker
also exists on non-Aeldari models - the Ork Kill Rig carries it - which is
exactly why the AELDARI half of the check is not optional: without it, an Ork
psyker in the same army would buff Wraithguard.)

THREE CARRIERS, TWO PRINTED VARIANTS
------------------------------------
Wraithguard and Wraithblades print the text quoted above. The WRAITHLORD prints
the same ability NAME with a different second half:

  "...improve the Ballistic Skill and Weapon Skill characteristics of weapons
   equipped by this model by 1 and it has a Leadership characteristic of 6+."

So the Leadership half is shared and the offensive half is not: one modifies
the Hit ROLL, the other improves the CHARACTERISTIC. They are kept as two
flags (`psychic_guidance` and `psychic_guidance_characteristics`) and two
predicates, because they are two printed effects.

WHY THE WRAITHLORD'S HALF IS STILL IMPLEMENTED AS A -1 MODIFIER: in this engine
every skill is a threshold and game/modifiers.py adjusts thresholds, so
"improve the characteristic by 1" and "add 1 to the roll" land on the same
number. The one place they could diverge is an "ignore Hit roll modifiers"
effect (24.29, and the Weapon Support System) - and both of those filters drop
only WORSENING modifiers and keep improving ones, so an improvement survives
them either way. The two readings therefore cannot produce a different result
here; the distinction is preserved in the flags rather than in the arithmetic.

"FRIENDLY" is same-owner, and AELDARI is read off the datasheet's FACTION
rather than its keyword line: game/factions/aeldari.py deliberately does not
repeat the faction keywords on each datasheet, because the Faction object
carries them (see that module's own note).
"""

AELDARI_KEYWORD = "AELDARI"
PSYCHIC_GUIDANCE_RANGE_IN = 12.0
PSYCHIC_GUIDANCE_LEADERSHIP = "6+"


def _squad_has_flag(squad, flag):
    """Rule 19.04's shape: any() rather than all(), so an attached model
    without the ability does not take it away from the unit."""
    models = getattr(squad, "models", None)
    if not models:
        return False
    return any(getattr(m.profile, flag, False) and not m.is_dead() for m in models)


def squad_has_psychic_guidance(squad):
    """Either printed variant - both grant the Leadership half, so this is the
    right question for game/leadership.py to ask."""
    return (_squad_has_flag(squad, "psychic_guidance")
            or _squad_has_flag(squad, "psychic_guidance_characteristics"))


def _is_aeldari(squad):
    """Re-exported, not redefined - see game/aeldari_detachments.py.

    Thirteen other modules reach in here for this, which is thirteen callers
    into a private name in a DATASHEET-ability module for a question about the
    FACTION. It moved under the same rule that moved is_tau_unit() out of
    game/retaliation_cadre.py; kept reachable under this name so those callers
    did not have to move with it, and the test pins that the two are the SAME
    object rather than two copies that agree today.

    Imported inside the function: game/aeldari_detachments.py reaches
    game.factions, and this module is imported early enough that a
    module-level import closes a cycle."""
    from game.aeldari_detachments import is_aeldari_unit
    return is_aeldari_unit(squad)


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
    """The HIT-ROLL variant (Wraithguard, Wraithblades): is the unit currently
    within 12" of a friendly AELDARI PSYKER?

    Measured centre to centre rather than edge to edge, matching how every
    other "within X inches of a model" aura in this engine measures - the
    distinction is below the granularity these ranges are chosen at."""
    return _in_range(squad, all_tokens, "psychic_guidance")


def applies_characteristics(squad, all_tokens):
    """The CHARACTERISTIC variant (Wraithlord). Same condition, different
    printed effect - see the module docstring."""
    return _in_range(squad, all_tokens, "psychic_guidance_characteristics")


def applies_any(squad, all_tokens):
    """Either variant - what the Leadership half needs, since both grant it."""
    return applies(squad, all_tokens) or applies_characteristics(squad, all_tokens)


# Imported here rather than at module level: the Stratagem imports
# game/shepherds_of_the_dead.py, which reaches back to this module's
# own import chain.
from game import conclave_soul_bridge  # noqa: E402


def _in_range(squad, all_tokens, flag):
    if not _squad_has_flag(squad, flag):
        return False
    mine = [m for m in squad.models if not m.is_dead()]
    if not mine:
        return False
    for psyker in _friendly_aeldari_psyker_models(squad, all_tokens):
        # Spirit Conclave's Soul Bridge: "your unit is CONSIDERED TO BE within
        # 12\" of your PSYKER model for the purposes of the Psychic Guidance
        # and Spirit Guides abilities". One of exactly two predicates the
        # printed text names - see game/conclave_soul_bridge.py for why it is a
        # mark read here rather than a spoofed distance.
        if conclave_soul_bridge.is_bridged_to(squad, psyker):
            return True
        for model in mine:
            dx = model.x_in - psyker.x_in
            dy = model.y_in - psyker.y_in
            if (dx * dx + dy * dy) ** 0.5 <= PSYCHIC_GUIDANCE_RANGE_IN:
                return True
    return False
