"""Rule 24.24's LONE OPERATIVE, where it is CONDITIONAL rather than printed -
the 25th extraction, one carrier late.

WHY IT EXISTS
-------------
Three abilities already grant Lone Operative on a condition instead of printing
a range on the profile, and all three print the SAME sentence with a different
keyword and a different distance:

    Illuminor Szeras      within 3" of one or more OTHER friendly NECRONS units
    the Spiritseer        within 3" of one or more friendly WRAITH CONSTRUCT units
    Death Guard Defenders within 3" of one or more friendly DEATH GUARD units

Each is a module-level `grants_lone_operative(squad, all_tokens)` plus a named
range constant, and each was folded into status_effects.lone_operative_range()
as its own hand-written `if`. The comments there tell the story on their own:
the Spiritseer's says "Second such grant", and Death Guard Defenders' also says
"the SECOND conditional granter" - two blocks both claiming to be the second,
which is what three copies of one shape look like from the inside.

Armoured Warhost's Spirit Stone of Raelyth is the fourth ("while this model is
within 3" of a friendly AELDARI VEHICLE unit, this model has Lone Operative"),
and a fourth hand-written block is one past defensible.

WHAT IS SHARED AND WHAT IS NOT. Only the FOLD is shared - "ask every
conditional source, and take the longest range it grants". Each source keeps
its own module, its own predicate and its own printed distance, because those
are the parts that differ. A source registers here instead of being appended to
a chain in whichever file happened to need it first, which is the same move
game/move_exceptions.py and game/hidden_after_shooting.py both make.

THE COMPOSITION IS max(), NOT first-wins, and that is inherited rather than
invented: lone_operative_range() already returned max() over the printed values,
because a model with two sources of the ability keeps the better one - the same
reading rule 05.04 gives armour and invulnerable saves. Nothing here changes it.

`all_tokens` STAYS OPTIONAL. Every one of these predicates needs the board, and
lone_operative_range()'s own note explains why the default is empty rather than
required: a caller that does not pass the board simply never sees a conditional
grant, which is the safe direction and is what keeps every existing call site
meaning what it did.
"""

from game import death_guard_defenders, illuminor, spiritseer
from game import enh_spirit_stone_of_raelyth

#: (predicate, range) for every CONDITIONAL grant. A source is a pair, not a
#: subclass: what it shares is the question, not any behaviour.
#:
#: Order is irrelevant - the fold takes max() - so this is in the order the
#: three arrived, which is also the order their own comments reference.
SOURCES = (
    (illuminor.grants_lone_operative,
     illuminor.ILLUMINOR_LONE_OPERATIVE_RANGE_IN),
    (spiritseer.grants_lone_operative,
     spiritseer.SPIRITSEER_LONE_OPERATIVE_RANGE_IN),
    (death_guard_defenders.grants_lone_operative,
     death_guard_defenders.DEATH_GUARD_DEFENDERS_LONE_OPERATIVE_RANGE_IN),
    # Armoured Warhost's Spirit Stone of Raelyth - the FOURTH, and the first
    # that is an Enhancement rather than a printed datasheet ability. Same
    # sentence, same signature, one more entry.
    (enh_spirit_stone_of_raelyth.grants_lone_operative,
     enh_spirit_stone_of_raelyth.SPIRIT_STONE_RANGE_IN),
)


def granted_ranges(squad, all_tokens=()):
    """Every conditional LONE OPERATIVE range that currently applies to this
    unit, as a list. Empty when none does."""
    return [range_in for applies, range_in in SOURCES
            if applies(squad, all_tokens)]
