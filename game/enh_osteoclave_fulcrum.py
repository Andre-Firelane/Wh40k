"""Hypercrypt Legion Enhancement: Osteoclave Fulcrum (20 pts).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  "NECRONS model only. Models in the bearer's unit have the Deep Strike ability."

A UNIT-LEVEL GRANT of a keyword that rule 24.09 reads EVERY-MODEL ("if every
model in this unit has this ability"), so giving the flag to the bearer alone
would grant nothing - the bodyguards do not print it. The printed subject is
"models in the bearer's unit".

WHERE AND WHEN IT LANDS is game/enh_student_of_kauyon.py's seam, and for its
reason: Deep Strike is what lets a unit that starts in Strategic Reserves arrive
anywhere more than 9" from the enemy, and the DECLARATION that a unit starts in
reserves is made in Declare Battle Formations. So the flag is written onto the
models' own UnitProfile instances (build_squad() makes them per model) at the
start of that step, from main.py, before either player - or the deployment AI,
which reads deep_strike to decide what goes into reserves - has declared
anything. The legacy instant scene path, which has no such step, applies it
beside the Experimental Prototype Cadre upgrades.

Written onto the profile rather than asked at read time because Deep Strike has
four readers (game/ingress.py, game/transport.py, ai/deployment_ai.py and
Student of Kauyon's own check), and a grant each of them has to learn is four
chances for one to forget. It is permanent: the text gives no end, and the one
moment it matters - an arrival from reserves - comes before the bearer can die.

IDEMPOTENT, so a scene that reaches both paths is granted once.
"""

from game import enhancements

OSTEOCLAVE_FULCRUM = "Osteoclave Fulcrum"


def grants_deep_strike(squad):
    return squad is not None and enhancements.is_active(squad, OSTEOCLAVE_FULCRUM)


def apply_all(squads, game_log=None):
    """Write Deep Strike onto every model of every unit whose bearer is active.
    Returns how many units gained it."""
    granted = 0
    for squad in squads or ():
        if not grants_deep_strike(squad):
            continue
        models = list(getattr(squad, "models", ()) or ())
        if all(getattr(m.profile, "deep_strike", False) for m in models):
            continue
        for model in models:
            model.profile.deep_strike = True
        granted += 1
        if game_log is not None:
            game_log.add(f"{squad.owner}: {squad.name} has Deep Strike (rule 24.09) from the "
                         f"{OSTEOCLAVE_FULCRUM} Enhancement.")
    return granted
