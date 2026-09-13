"""Canoptek Court Enhancement: Dimensional Sanctum (20 pts).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  "CRYPTEK model only. Models in the bearer's unit have the Infiltrators
   ability."

A UNIT-LEVEL GRANT, and that is what makes it reach rule 24.20 at all. Infiltrators
applies "if every model in a unit has this ability", so giving the flag to the
bearer alone would grant nothing - the bodyguards do not print it. The printed
subject is "models in the bearer's unit", i.e. every model, which is exactly the
state 24.20's every-model gate tests for. So it is one more clause in
game/squad.py's squad_has_infiltrators(), beside the Recon Drone - the same
arrangement, and the same reason, that module already writes out.

A living bearer is the 19.04 reading enhancements.is_active() already carries,
and so is the detachment gate. The one reader is the pre-battle deployment
(game/pregame.py), which runs after army building has handed the Enhancement out.
"""

from game import enhancements

DIMENSIONAL_SANCTUM = "Dimensional Sanctum"


def grants_infiltrators(squad):
    return enhancements.is_active(squad, DIMENSIONAL_SANCTUM)
