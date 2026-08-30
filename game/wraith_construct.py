"""'Is this a WRAITH CONSTRUCT unit?' - the 27th extraction, with two answers
already in the tree and about to gain four more askers.

WHY IT EXISTS
-------------
The question was being answered TWO different ways:

  * game/spiritseer.py's is_wraith_construct_unit() reads the
    UnitProfile.wraith_construct FLAG,
  * game/forewarned.py and game/shepherds_of_the_dead.py read the DATASHEET
    keyword line through attached_units.unit_has_datasheet_keyword().

Two places, one question - error class 10, and the three Spirit Conclave
Enhancements plus Seer's Eye and Wraithbone Armour make it six askers.

THE KEYWORD FORM WINS, because that is what every printed line says: "one
friendly WRAITH CONSTRUCT unit", not "a unit whose models carry a flag". It is
also the form that keeps working when a datasheet is added without its profile
flag being remembered, which is the more likely direction of drift.

MEASURED FIRST, NOT ASSUMED. Across every built Aeldari datasheet the two
answers agree exactly - Wraithblades, Wraithguard and the Wraithlord are
WRAITH CONSTRUCT by both readings, and nothing else is by either. So this
consolidation is behaviour-neutral TODAY, and the test pins that agreement
rather than trusting it.

WHERE THEY WOULD COME APART is the Wraithknight, which the corpus prints as
WRAITH CONSTRUCT and TITANIC and which is deliberately not built (out of scope,
with Aircraft and Forge World). Whichever of the two forms a future
Wraithknight remembered to set, the other would silently answer False for it -
which is exactly the drift this removes.

THE TITANIC EXCLUSION IS NOT FOLDED IN, and that is printed rather than
stylistic: only Stave of Kurnous says "(excluding TITANIC units)". Light of
Clarity and Rune of Mists, the two marks beside it, say nothing of the kind, so
a shared filter would apply an exclusion two Enhancements never printed. It is
a separate function here, asked only by the rule that prints it.

(game/spiritseer.py's own filter for that clause read `profile.titanic`, a
field UnitProfile does not declare - measured: zero occurrences - so it was
unconditionally False, a silent no-op. The keyword route below is the one
game/conclave_wraithbone_armour.py already uses for the same clause, is
identical in behaviour today, and starts working by itself the day a
Wraithknight is built.)
"""

from game.attached_units import unit_has_datasheet_keyword

WRAITH_CONSTRUCT_KEYWORD = "WRAITH CONSTRUCT"
TITANIC_KEYWORD = "TITANIC"


def is_wraith_construct_unit(squad):
    """Rule 19.03's pooling, asked of the datasheet keyword line - which is
    what every printed clause names."""
    if squad is None:
        return False
    return unit_has_datasheet_keyword(squad, WRAITH_CONSTRUCT_KEYWORD)


def is_titanic_unit(squad):
    """Its own question, because only one of the four printed clauses
    excludes TITANIC - see the module docstring."""
    if squad is None:
        return False
    return unit_has_datasheet_keyword(squad, TITANIC_KEYWORD)


def is_non_titanic_wraith_construct(squad):
    """"one friendly WRAITH CONSTRUCT unit ... (excluding TITANIC units)" -
    Stave of Kurnous, and nothing else in this batch."""
    return is_wraith_construct_unit(squad) and not is_titanic_unit(squad)
