"""Immortals' "Implacable Eradication".

RULE (printed, word for word):
  "Each time a model in this unit makes an attack, re-roll a Wound roll of 1.
   If the target of that attack is an enemy unit within range of an objective
   marker, you can re-roll the Wound roll instead."

THE SAME TWO-CLAUSE SHAPE as the three DESTROYER CULT abilities
(game/destroyer_cult.py) and the Windriders' Swift Demise: an automatic re-roll
of the natural 1s, upgraded - "INSTEAD", so in place of, never on top of - to
an optional re-roll of the whole roll when the condition holds.

TWO THINGS SEPARATE IT FROM ITS COUSINS, both printed:

  * "makes an ATTACK", not "a ranged attack" and not "a melee attack". So this
    is the first Necron re-roll wired into game/fight.py as well as
    game/shooting.py - Hard-wired for Destruction says ranged, Whirling
    Onslaught says melee, and each is wired to its own phase only.
  * "within range of an objective marker" with NO ownership clause. Hard-wired
    for Destruction says "an objective marker YOUR OPPONENT controls"; this one
    does not care who holds it, or whether anyone does. The difference is one
    argument at the call site and it is easy to mirror by accident, so both
    modules state their own version explicitly.

It is a WOUND re-roll, where the Destroyer Cult's two upgradeable ones are HIT
re-rolls. That mattered more than expected: the hit step already had the
"1s or the whole roll" shape from Swift Demise, and the wound step did not -
its sources were each pinned to one fixed scope. game/reroll_scope.py is where
that shape is now named, so both steps ask the same question.
"""

from game.objectives import is_within_range_of_objective

IMPLACABLE_ERADICATION_LABEL = "Implacable Eradication"


def applies(squad):
    """The base clause. Rule 19.03: a merged unit has the ability if any
    component brought it, which reading it live off the models gives free."""
    if squad is None:
        return False
    return any(getattr(m.profile, "implacable_eradication", False)
               for m in squad.models if not m.is_dead())


def offers_full_reroll(squad, target_squad, objectives=()):
    """The upgrade: the target is within range of an objective marker - any
    objective marker, held by anyone or by nobody."""
    if not applies(squad) or target_squad is None:
        return False
    return is_within_range_of_objective(target_squad, objectives or ())
