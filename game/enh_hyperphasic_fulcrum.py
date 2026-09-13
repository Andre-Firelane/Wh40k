"""Canoptek Court Enhancement: Hyperphasic Fulcrum (15 pts).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  "CRYPTEK model only. While the bearer is leading a unit, if that unit is wholly
   within your army's Power Matrix, each time a model in that unit makes an
   attack, re-roll a Wound roll of 1."

A PLAIN AUTOMATIC 1s RE-ROLL - no "you can", no "instead" - so it joins the
automatic wound-1s chains in game/shooting.py and game/fight.py and deliberately
NOT game/reroll_scope.py, which drives an optional offer this text never gives.
"An attack", so both phases.

"WHILE THE BEARER IS LEADING A UNIT" is read as "the bearer is part of a real
attached unit (19.01)" - attached_units.leader_ability()'s own reading. Every
Cryptek that can carry it attaches in the SUPPORT role in this engine (Plasmancer,
Technomancer, ...), and a Support character standing in a unit it was attached to
is the only sense in which one "leads" anything. A Cryptek standing on its own is
leading nothing, and gets nothing.

"WHOLLY WITHIN YOUR ARMY'S POWER MATRIX" is game/court_power_matrix.py's one
answer, so the Enhancement and the detachment rule cannot disagree about it.
"""

from game import attached_units, court_power_matrix, enhancements

HYPERPHASIC_FULCRUM = "Hyperphasic Fulcrum"
HYPERPHASIC_FULCRUM_LABEL = "Hyperphasic Fulcrum"


def applies(squad, matrix):
    if squad is None or not enhancements.is_active(squad, HYPERPHASIC_FULCRUM):
        return False
    if not attached_units.is_attached_unit(squad):
        return False
    return court_power_matrix.unit_wholly_within(squad, matrix)
