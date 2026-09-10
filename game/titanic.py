""""Is this a TITANIC unit?" - one reader, because there were three.

WHY THIS EXISTS
---------------
TITANIC has been a documented no-op for as long as this engine has existed:
no built datasheet carried the keyword, so roughly a dozen printed clauses
that say "excluding TITANIC units" were written out in prose and left
unfiltered. Several of them promise, word for word, that they "start working
by itself the day a TITANIC datasheet exists".

The Monolith is that day. And measured before building it, the promise did NOT
hold, because the question was being answered THREE different ways:

  1. `getattr(profile, "titanic", False)` - a field `UnitProfile` DOES NOT
     DECLARE (measured: zero occurrences in game/units.py). Unconditionally
     False, so these four sites were silent no-ops that LOOKED wired:
        game/actions.py               (16.01, twice)
        game/elemental_ensnarement.py (an Aeldari stratagem's exclusion)
        game/structural_collapse.py   (the D-cannon's second clause)
  2. `attached_units.unit_has_datasheet_keyword(squad, "TITANIC")` - correct,
     and what game/battle_focus.py, game/conclave_wraithbone_armour.py and
     game/wraith_construct.py already do.
  3. A constant with no filter behind it at all (game/scuttling_walker.py's
     TITANIC_EXCLUDED, game/overwatch.py's comment).

Form 1 is byte-for-byte the bug game/wraith_construct.py's own docstring
already indicts: "game/spiritseer.py's filter for that clause read
`profile.titanic`, a field UnitProfile does not declare - measured: zero
occurrences - so it was unconditionally False, a silent no-op." That one was
found and fixed; these four were not, because nothing carried the keyword and
so nothing could tell the difference.

THE KEYWORD FORM WINS, for the same reason it won there: every printed line
says "excluding TITANIC units", not "units whose models carry a flag". It is
also the form that keeps working when a datasheet is added without someone
remembering a profile flag - which is the likelier direction of drift, and
exactly how these four went dead in the first place.

WHY ITS OWN MODULE rather than another function in wraith_construct.py, which
already has one: that module is named for WRAITH CONSTRUCT and its
is_titanic_unit() is there because ONE Aeldari Enhancement pairs the two
keywords in a single printed clause. Four of the callers below are Necron,
Death Guard and core-rule sites that have nothing to do with wraith
constructs, so leaving the canonical reader there would be error class 11 - a
name that lies about what it answers. wraith_construct.py now delegates here,
so there is still exactly ONE definition and its own callers do not move.

NOT ALL OF THIS IS DORMANT, and the distinction is worth writing down: two of
the four repaired sites are CROSS-FACTION readers on live rosters
(elemental_ensnarement is Aeldari, and the D-cannon's clause fires for any
Aeldari list that fields one). They go live against a Monolith the day one is
fielded, not the day one is built.
"""

from game.attached_units import unit_has_datasheet_keyword

#: The printed keyword, spelled once.
TITANIC_KEYWORD = "TITANIC"


def is_titanic_unit(squad):
    """Rule 19.03's keyword pooling, asked of the datasheet keyword line."""
    if squad is None:
        return False
    return unit_has_datasheet_keyword(squad, TITANIC_KEYWORD)
