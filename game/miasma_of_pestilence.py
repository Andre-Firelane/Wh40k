"""The Daemon Prince of Nurgle's Aura "Miasma of Pestilence".

RULE (printed, word for word):

  "While a friendly DEATH GUARD unit is within 6" of this model, each time a
  ranged attack targets that unit, models in that unit have the Benefit of
  Cover against that attack."

THE THIRD UNCONDITIONAL GRANT OF COVER in this engine, after rule 24.33
(STEALTH) and the Death Guard Plague Skullsquirm Blight - and like both of
those it short-circuits ahead of _compute_benefit_of_cover()'s per-model
terrain and visibility loop, because the printed text asks for neither.

Asked of the TARGET, unlike Skullsquirm Blight, which is asked of the shooter.
The two therefore sit on opposite sides of the same function, which is worth
saying because they read almost identically in prose.

"A FRIENDLY DEATH GUARD unit" includes the Daemon Prince's own unit - it is a
DEATH GUARD unit within 6" of itself. The printed text has no "other", unlike
game/mechanical_augmentation.py's aura, which does and therefore excludes the
bearer. Written out because the two look the same at a glance and differ.

The distance is measured unit-to-unit through Squad.min_distance_to(), the same
measurement game/mechanical_augmentation.py's aura uses, so "within 6"" means
what it means everywhere else in this engine.
"""

MIASMA_RANGE_IN = 6.0
DEATH_GUARD_KEYWORD = "DEATH GUARD"


def _bearers(all_tokens, owner):
    """Every living model projecting the aura on `owner`'s side."""
    return [t for t in all_tokens or ()
            if getattr(t, "squad", None) is not None
            and t.squad.owner == owner
            and not t.is_dead()
            and getattr(t.profile, "miasma_of_pestilence", False)]


def _is_death_guard(squad):
    """Read via the army rule, which every Death Guard datasheet prints - the
    same source game/death_lords_chosen.py falls back to, and the only one
    available to a squad built without a datasheet."""
    return any(getattr(m.profile, "nurgles_gift", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


def applies(target_squad, all_tokens=()):
    """Whether ranged attacks against `target_squad` are met by cover."""
    if target_squad is None or not _is_death_guard(target_squad):
        return False
    if not any(not m.is_dead() for m in getattr(target_squad, "models", ()) or ()):
        return False
    for bearer in _bearers(all_tokens, target_squad.owner):
        if bearer.squad is target_squad:
            return True  # "a friendly DEATH GUARD unit" - its own unit qualifies
        if target_squad.min_distance_to(bearer.squad) <= MIASMA_RANGE_IN:
            return True
    return False
