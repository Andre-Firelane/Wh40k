"""Firesight Team's "Precise Targeting".

RULE (printed, word for word):
  "Each time a model in this unit makes an attack that targets a Spotted unit,
   you can re-roll the Hit roll."

SPOTTED IS ALREADY A THING HERE. game/greater_good.py implements the T'au army
rule For The Greater Good, whose Observer/Guided step marks an enemy unit as
Spotted until the end of the phase - so this ability needs no new state at all,
only a read of GreaterGoodController.is_spotted().

"AN ATTACK", NOT "A RANGED ATTACK" - so on a strict reading it covers melee
too. It is nevertheless wired into the shooting step only, and that is NOT a
simplification: Spotted is set during the Shooting phase and cleared at the end
of it (GreaterGoodController.reset_shooting_phase()), so no melee attack can
ever be made against a Spotted unit. Wiring FightController to a mark that is
always absent there would be dead code. Written out here so the next reader
does not have to re-derive it, and asserted in the test.

THE OFFER SHAPE IS FAILURES-OR-WHOLE, the ordinary one: the text is the plain
"you can re-roll the Hit roll" with no automatic-1s clause, so it must NOT be
registered in game/reroll_scope.py - doing so would offer a ones-only re-roll
the printed text never grants. That absence is asserted in the test, which is
the only place it shows.
"""

PRECISE_TARGETING_LABEL = "Precise Targeting"


def unit_has_precise_targeting(squad):
    """Read live off the living models, so it ends with the Marksman."""
    if squad is None:
        return False
    return any(getattr(m.profile, "precise_targeting", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def applies(attacking_squad, target_squad, greater_good):
    """Whether this group's Hit roll may be re-rolled.

    `greater_good` is the GreaterGoodController, which is optional everywhere
    in ShootingController - None simply means no Spotted state exists."""
    if greater_good is None or target_squad is None:
        return False
    if not unit_has_precise_targeting(attacking_squad):
        return False
    return greater_good.is_spotted(target_squad)
