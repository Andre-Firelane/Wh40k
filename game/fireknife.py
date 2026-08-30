"""Crisis Fireknife Battlesuits' "Fireknife".

RULE (printed, word for word):
  "Each time a model in this unit makes a ranged attack, re-roll a Hit roll of
   1. If that attack targets a unit that is at its Starting Strength, you can
   re-roll the Hit roll instead."

A TEXTBOOK ONES-OR-WHOLE SOURCE - the shape game/reroll_scope.py exists to name,
and the sixth entry in its registry. Two clauses: an AUTOMATIC re-roll of 1s
that always applies, and a conditional "you can re-roll the Hit roll INSTEAD".
"Instead" makes them alternatives, so the player picks one and "failures only"
is NOT among the options: offering it would let a 2 that missed be re-rolled,
which this ability never permits.

The mechanics of that choice are already built - the hit step holds the
automatic 1s back while the whole-roll alternative is on offer, exactly as it
does for Swift Demise and its three siblings. So this module supplies only the
two predicates, and the difference between them is the whole ability:

  * `applies()` - the automatic half, true whenever a Fireknife suit shoots.
  * `offers_full_reroll()` - the conditional half, true only when the TARGET is
    at its Starting Strength.

"AT ITS STARTING STRENGTH" means no models lost, and it is read off
Squad.starting_model_count - the Appendix's own term, and the same field
A Grievous Blow and is_at_half_strength() already use. NOT "undamaged": a
Riptide on one wound out of fourteen is still at its Starting Strength, because
strength counts MODELS. That reading is what makes the ability good against
fresh blobs and useless against a squad that has already lost one Gretchin, and
it is its own test line because "unhurt" is the obvious wrong guess.

RANGED ONLY, so it is read in game/shooting.py and not in game/fight.py - the
printed text says "a ranged attack" where the Lokhust Lord's Driven by Hatred
next door says "an attack" and therefore needs both.
"""

FIREKNIFE_LABEL = "Fireknife"


def unit_has_fireknife(squad):
    """Read live off the living models, so it ends with the last suit."""
    if squad is None:
        return False
    return any(getattr(m.profile, "fireknife", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def at_starting_strength(squad):
    """"a unit that is at its Starting Strength" - no models lost.

    Counts MODELS, not wounds: a unit whose every model is alive but bleeding
    is still at its Starting Strength."""
    if squad is None:
        return False
    living = sum(1 for m in getattr(squad, "models", ()) or () if not m.is_dead())
    return living >= getattr(squad, "starting_model_count", living)


def applies(attacking_squad):
    """The automatic half: re-roll Hit rolls of 1, always."""
    return unit_has_fireknife(attacking_squad)


def offers_full_reroll(attacking_squad, target_squad):
    """The conditional half: the whole Hit roll, INSTEAD of the 1s."""
    return applies(attacking_squad) and at_starting_strength(target_squad)
