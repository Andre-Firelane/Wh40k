"""What the Aeldari detachment rules share.

WHY THIS EXISTS
---------------
The mirror of game/tau_detachments.py, and built for the same two reasons.

FIRST, the faction test. `_is_aeldari()` lives in game/psychic_guidance.py -
a DATASHEET-ability module - and is reached by thirteen other modules through
its leading underscore. One ability owning it was fine when one ability asked;
thirteen callers into a private name is the lying name this repo renames rather
than copies, and the seven detachment rules would have made fourteen.
game/psychic_guidance.py re-exports it, so there is still ONE definition and
the thirteen callers did not have to move.

SECOND, ASURYANI. Three of the seven printed rules name it, and it is NOT a
synonym for AELDARI: the Ynnari triumvirate is AELDARI and not ASURYANI.
Measured on the built roster - 54 Aeldari datasheets, 51 ASURYANI, and the
three that are not are Yvraine, The Visarch and The Yncarne. Two of those three
are PSYKERs, which is exactly the set Spirit Conclave's "ASURYANI PSYKER"
clause has to exclude, so reading ASURYANI as AELDARI would be wrong in the one
place it bites rather than harmlessly wide.

WHAT IS DELIBERATELY NOT HERE: a doctrine_active()-style helper. Kauyon and
Mont'ka are one mechanism twice, so their round window was worth sharing; these
seven detachments have nothing in common beyond the two predicates below - they
hang on seven different seams - so a shared "is this rule live" helper would be
a wrapper around has_detachment() with a different name.
"""

from game.attached_units import unit_has_faction_keyword
from game.detachment_gate import has_detachment  # noqa: F401  (re-exported)

AELDARI_KEYWORD = "AELDARI"
ASURYANI_KEYWORD = "ASURYANI"


def is_aeldari_unit(squad):
    """"a unit from your army" for an AELDARI detachment rule.

    Read off the DATASHEET's faction rather than a per-model flag, like
    tau_detachments.is_tau_unit() and awakened_dynasty.is_necrons_unit(): that
    is what the keyword actually is, and game/factions/aeldari.py deliberately
    does not repeat it on every datasheet's keyword line."""
    if squad is None:
        return False
    from game.factions.faction import faction_keyword_of
    return faction_keyword_of(squad) == AELDARI_KEYWORD


def is_asuryani_unit(squad):
    """"an ASURYANI unit" - the craftworld half of the faction.

    A narrower question than is_aeldari_unit(), and the difference is the whole
    reason game/factions/datasheet.py grew a `faction_keywords` field: ASURYANI
    is printed on the datasheet's SECOND keyword line, which nothing read until
    these detachments arrived.

    Answered per COMPONENT through rule 19.03's pooling, so an attached unit
    whose leader is ASURYANI counts - which is what "unit" means everywhere
    else in this engine."""
    return unit_has_faction_keyword(squad, ASURYANI_KEYWORD)
