"""The Defiler's own ability "Barrage of Filth".

RULE (printed, word for word):

  "In your Shooting phase, after this model has shot, select one enemy unit hit
  by one or more of those attacks. Until the end of the phase, that unit cannot
  have the benefit of Cover."

THE SEVENTH CONSUMER of ShootingController.on_squad_finished_shooting, and the
third whose effect is a MARK ON THE TARGET rather than a grant on the shooter -
Target Acquisition and Crystalline Targeting are the other two, and this is
modelled on them.

EVERYTHING THIS ABILITY DOES NOW LIVES IN game/cover_denial.py, and this module
is the two lines that make it this ability. The Triarch Stalker's Targeting
Relay prints the same sentence under another name, so the shared head was
extracted at that second consumer - the repo's standing rule. What was here
before is unchanged in behaviour: the base class IS this class's old body, and
its docstring carries the reasoning that used to sit here (why the candidates
are what was HIT, why "select" is not a choice about WHETHER, why the mark is
phase-scoped, and why removing cover has to be checked before every grant).
"""

from game.cover_denial import CoverDenialAfterShooting


class BarrageOfFilthController(CoverDenialAfterShooting):
    flag = "barrage_of_filth"
    label = "Barrage of Filth"
