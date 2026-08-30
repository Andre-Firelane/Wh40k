"""The Death Guard wargear item "icon of despair".

RULE (printed, word for word):

  Icon of Despair (Aura): "While an enemy unit is within 6" of the bearer,
  worsen the Leadership characteristic of models in that unit by 1."

PRINTED ON TWO DATASHEETS (Plague Marines and Deathshroud Terminators) as the
same item with the same text, so it is one module and one token flag rather
than two - the call game/nanoscarab_amulet.py's own note describes for a
per-TOKEN wargear grant.

A PER-TOKEN FLAG, not a profile one. Gear is applied by build_squad() as a
callback that mutates the built Token, so the bearer is one specific model and
the aura dies with it - which is what "the bearer" means and what a
UnitProfile flag could not express, since profiles are shared class objects.

IT LANDS IN game/leadership.py's leadership_threshold(), the one place this
engine asks what a unit's Leadership actually is - so it composes with the
Death Guard Plague Scabrous Soulrot (also -1 Ld) without either knowing about
the other, and both reach Battle-shock through the same call.

Ld is a THRESHOLD, so worsening it means a HIGHER number - the same arithmetic
and the same trap as Scabrous Soulrot next door.
"""

ICON_OF_DESPAIR_RANGE_IN = 6.0
ICON_OF_DESPAIR_PENALTY = 1


def equip(token):
    """The Gear callback. Named `equip` like every other gear effect."""
    token.icon_of_despair = True


def _bearers(all_tokens, enemy_of):
    return [t for t in all_tokens or ()
            if getattr(t, "icon_of_despair", False)
            and getattr(t, "squad", None) is not None
            and t.squad.owner != enemy_of
            and not t.is_dead()]


def leadership_penalty(squad, all_tokens=()):
    """How much to add to this unit's Leadership threshold, or 0.

    `all_tokens` is optional and defaults to empty, exactly as it is for
    Psychic Guidance in the same function: a caller that cannot see the board
    cannot answer a proximity question either, and gets the printed value."""
    if squad is None:
        return 0
    for bearer in _bearers(all_tokens, squad.owner):
        if squad.min_distance_to(bearer.squad) <= ICON_OF_DESPAIR_RANGE_IN:
            return ICON_OF_DESPAIR_PENALTY
    return 0
