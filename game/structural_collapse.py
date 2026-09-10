"""The D-cannon Platform's "Structural Collapse" - a datasheet ability.

RULE (printed, word for word):
  "Each time this model makes an attack with its D-cannon, re-roll a Damage
  roll of 1. If that attack targets a TITANIC unit, you can re-roll the Damage
  roll instead."

TWO CLAUSES, AND ONLY ONE OF THEM CAN FIRE HERE
-----------------------------------------------
  * "re-roll a Damage roll of 1" has NO "you can" - it is mandatory, so it is
    not an offer and nothing is asked. game/damage_reroll.py grew
    `automatic_faces` for it, and the session resolves it on the same
    synchronous path a declined offer takes.
  * "if that attack targets a TITANIC unit ... instead" is a BELIEVED NO-OP:
    no datasheet in this engine carries TITANIC (the two Wraithknights that do
    are deliberately not built, and every other carrier is Legends or Forge
    World). It is written out rather than dropped so that the day a TITANIC
    datasheet arrives, this is one predicate rather than a re-reading of the
    printed text - the same treatment rapid_ingress.py's AIRCRAFT carve-out
    gets.

"A DAMAGE ROLL OF 1" NAMES THE DIE, NOT THE TOTAL. The D-cannon's Damage is
D6+2, so the die showing a 1 arrives at the session as a 3, and the face is
derived from the notation rather than compared against the total.

This reading is now the repo's ONLY one, and getting there took a user report.
Branching Fates' damage half read the structurally identical phrase ("change
the result of one ... Damage roll to an unmodified 6") as the RESULT instead,
so it set a D6+2 die to 4 - capping a weapon at less than its own maximum. Two
readings of one phrase, in one engine, shipped side by side. If a third
Damage-die ability arrives, it belongs on THIS side.

"WITH ITS D-CANNON" is a per-WEAPON condition, not a per-unit one: the
platform's shuriken catapult re-rolls nothing.
"""
from game.weapons import DCannonProfile

STRUCTURAL_COLLAPSE_LABEL = "Structural Collapse"

#: "re-roll a Damage roll of 1" - the die faces re-rolled without asking.
STRUCTURAL_COLLAPSE_AUTOMATIC_FACES = (1,)


def applies(squad, weapon):
    """Whether this attack's Damage roll gets the automatic re-roll.

    Takes the WEAPON as well as the unit because the printed text names one:
    a D-cannon Platform firing its shuriken catapult gets nothing. Read off
    the profile CLASS rather than the weapon name, which is free text."""
    if squad is None or weapon is None:
        return False
    if not isinstance(weapon, DCannonProfile):
        return False
    return any(getattr(m.profile, "structural_collapse", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


def targets_titanic(target_squad):
    """The second clause's condition, kept live but currently unreachable.

    No built datasheet carries TITANIC - see the module docstring. Written as a
    predicate so that adding one is a data change rather than a code change."""
    models = getattr(target_squad, "models", None) or ()
    return any(getattr(m.profile, "titanic", False) for m in models)
