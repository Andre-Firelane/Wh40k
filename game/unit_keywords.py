"""Does this UNIT have keyword X - asked by a weapon about its target.

Lifted out of game/shooting.py, where it answered rule 24.03's [ANTI-X Y+]
alone, when the 2026-09 Ork codex brought the SECOND consumer: rule 24.01's
conditional weapon abilities ("[LETHAL HITS: non-MONSTER/VEHICLE]" - the
ability applies only if the target unit has one of those keywords). Both
questions are "does the target unit carry this keyword", and two copies of
that are two chances to disagree about what an attached unit is (19.03).
game/shooting.py re-exports both names under their old private spelling, so
none of its call sites moved.

Only the keywords this engine models as UnitProfile fields are recognised
(there is no generic keyword system); an unrecognised keyword never matches.
That is the safe direction for a POSITIVE condition and the unsafe one for a
NEGATED one ("non-X" with an unknown X matches every target) - which is why
game/keyword_condition.py spells its conditions out of this table only.
"""

from game.weapons import NON_MONSTER_VEHICLE

#: printed keyword -> the UnitProfile field that carries it.
KEYWORD_FIELDS = {
    "INFANTRY": "infantry", "BEASTS": "beasts", "SWARM": "swarm", "MOBILE": "mobile",
    "CHARACTER": "character", "MONSTER": "monster", "VEHICLE": "vehicle",
    # The Visarch's mythic stance prints [ANTI-EPIC HERO 2+] - the first
    # weapon here to name that keyword, and the profile flag already
    # existed for rule 15.03 (Epic Challenge).
    "EPIC HERO": "epic_hero",
}


def unit_has_keyword(squad, keyword):
    """Whether ANY model in squad has the named keyword.

    Rule 19.03 (Keywords in Attached Units): "An attached unit has all of the
    keywords of all of its component units" - e.g. a Leader model with PSYKER
    gives the whole attached unit the PSYKER keyword even though its bodyguard
    models don't have it. any(), not all(): for an ordinary unit every model
    shares the same keywords anyway, so this only differs once a squad mixes
    profiles (an attached unit, rule 19.01)."""
    if squad is None:
        return False
    if keyword == NON_MONSTER_VEHICLE:
        # The NEGATED sentinel the Stonesinger's [ANTI-non-MONSTER/VEHICLE X+]
        # is written with - the exact complement of is_monster_or_vehicle_unit().
        from game.squad import is_monster_or_vehicle_unit
        return not is_monster_or_vehicle_unit(squad)
    field = KEYWORD_FIELDS.get(keyword)
    if field is None:
        return False
    return any(getattr(m.profile, field, False) for m in squad.models)
