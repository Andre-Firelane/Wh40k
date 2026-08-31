"""Path of the Outcast Enhancement: Camouflaged Snipers (10 pts).

RULE (verbatim, rules/aeldari/detachments/Path of the Outcast.md):
  "RANGERS unit only. This unit's ranged attacks do not prevent this unit from
  being hidden."

THE THIRD CONSUMER OF game/hidden_after_shooting.py, and the reason that module
carries the name it does. It was extracted when Advanced Acquisition Cadre's
Expert Fieldcraft and Auxiliary Cadre's Localised Stealth Projectors turned out
to be the same QUESTION reached two ways - a keyword and an aura - so it was
named after the question rather than after whichever ability arrived first.
A third source therefore costs one entry and changes nothing in
game/shooting.py, which still asks exactly once.

UNIT-LEVEL. "RANGERS unit only", not "model only" - one of only two among the
28. So grant() marks every model, and 19.04's "a living model still carries it"
becomes "the unit still exists", which is the right lifetime for something the
whole unit is doing.

AND THAT MAKES IT THE SIMPLEST OF THE FOUR: no leader clause, no keyword to
pool, no distance. It is worth having as a separate module anyway rather than a
bare flag read inline, because the shared question is what keeps the three
sources from drifting apart.
"""
from game import enhancements

CAMOUFLAGED_SNIPERS = "Camouflaged Snipers"

CAMOUFLAGED_SNIPERS_LABEL = "Camouflaged Snipers"


def applies(squad):
    """Whether this unit's own shooting leaves its Hidden status alone."""
    return enhancements.is_active(squad, CAMOUFLAGED_SNIPERS)
