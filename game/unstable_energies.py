"""The Orks army rule "Unstable Energies" - a psyker's budget per battle round.

PRINTED (rules/orks/army_rules.md):

    ORKS PSYKER units with this ability have a psyker level of 1 or higher,
    specified in that unit's abilities. Each psychic ability has a psychic level
    of 1 or higher, specified in that ability's name.

    In a battle round, a friendly ORKS PSYKER unit can use a number of psychic
    abilities whose total psychic level does not exceed that PSYKER unit's
    psyker level.

DORMANT BY CONSTRUCTION, and named so: the only carrier is the Kill Rig, whose
two psychic abilities (Beastscent, Warpath - psychic level 1 each) are built
with its datasheet stage. Until then nothing asks can_use(), and the ledger here
is what that stage reads.

THE LEDGER LIVES ON THE UNIT (Squad.unstable_energies_round and
Squad.unstable_energies_spent, both in activation_state.SQUAD_FLAGS): a psychic
ability used this round is a spend, and a mid-round save that forgot it would
hand the psyker its budget back. Two scalars rather than a {round: spent} dict,
so they round-trip through JSON unchanged; a spend in a NEW round starts the
count again, which is what "in a battle round" means.
"""


def psyker_level(squad):
    """The unit's psyker level - the highest any living model prints. 0 for a
    unit with no psyker level at all (every unit but the Kill Rig today)."""
    levels = [getattr(m.profile, "psyker_level", 0) or 0
              for m in getattr(squad, "models", ()) or () if not m.is_dead()]
    return max(levels, default=0)


def spent_this_round(squad, battle_round):
    if getattr(squad, "unstable_energies_round", None) != battle_round:
        return 0
    return getattr(squad, "unstable_energies_spent", 0) or 0


def can_use(squad, psychic_level, battle_round):
    """Whether this unit may use a psychic ability of `psychic_level` this
    battle round without exceeding its psyker level."""
    if squad is None or psychic_level <= 0:
        return False
    level = psyker_level(squad)
    if level <= 0:
        return False
    return spent_this_round(squad, battle_round) + psychic_level <= level


def spend(squad, psychic_level, battle_round):
    """Record a psychic ability used this round. Refuses (and records nothing)
    when it would exceed the budget."""
    if not can_use(squad, psychic_level, battle_round):
        return False
    squad.unstable_energies_spent = spent_this_round(squad, battle_round) + psychic_level
    squad.unstable_energies_round = battle_round
    return True
