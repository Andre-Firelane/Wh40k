"""Battlewagon's own "Ramshackle but Rugged" ability, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own module
- same reasoning as game/gun_crazy_showoffs.py for Flash Gitz' and
game/spirit_of_gork.py for the Kill Rig's).

RULE: Each time an attack is allocated to this model, worsen the Armour
Penetration characteristic of that attack by 1.

A DEFENSIVE ADJUSTMENT, SO IT LIVES AT ALLOCATION
--------------------------------------------------
Every other weapon adjuster in this engine belongs to the ATTACKER and is
chained onto the weapon while its group is being resolved. This one belongs
to the DEFENDER, and its trigger is "each time an attack is allocated to this
model" - rule 05.03's allocation step, which is where DamageAllocationSession
picks the model that will take the wound and rolls its save. So it is applied
there, against the model actually being allocated to, and not to the group's
weapon as a whole: in a mixed unit only the models with the ability benefit.

WORSENING STOPS AT 0
--------------------
AP is written as a penalty (0, -1, -2...), so "worsen by 1" means moving one
step TOWARD zero, and it stops there: an AP0 attack cannot become a bonus to
the target's save. Written as min(0, ap + 1) rather than plain ap + 1 for
that reason - with only AP0 weapons on the board the two would be
indistinguishable, and the wrong one would quietly hand out a better-than-
printed save.

NOT A Modifier
--------------
game/modifiers.py's Modifier adjusts a THRESHOLD a die must beat, and carries
a label for the roll's own log line. AP is a characteristic of the attack,
consumed by _resolve_save() before any threshold exists, so it is adjusted as
a value here - the same distinction game/waaagh.py already draws for its own
Strength bonus.
"""


def unit_has_ramshackle(squad):
    """True while at least one live model with the ability is in the unit -
    the same rule 19.04 reading every other datasheet ability here uses.
    Only useful for reporting; the real check is per model, see below."""
    if squad is None:
        return False
    return any(m.profile.ramshackle_but_rugged for m in squad.models if not m.is_dead())


def adjusted_ap(ap, model):
    """The Armour Penetration an attack allocated to `model` resolves with.

    A no-op passthrough unless that model actually has the ability, so every
    caller can apply it unconditionally."""
    if model is None or not getattr(model.profile, "ramshackle_but_rugged", False):
        return ap
    return min(0, ap + 1)
