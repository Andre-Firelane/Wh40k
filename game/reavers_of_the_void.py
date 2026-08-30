"""Corsair Voidreavers' "Reavers of the Void" - a datasheet ability.

RULE (printed, word for word):
  "Each time a model in this unit makes an attack, re-roll a Hit roll of 1. If
  the target of that attack is within range of an objective marker, you can
  re-roll the Hit roll instead."

THE "ONES OR WHOLE, NEVER JUST FAILURES" SHAPE, and the SEVENTH source of it -
so it belongs in game/reroll_scope.py rather than growing its own reading.

That module exists because "re-roll 1s ... you can re-roll the Hit roll
INSTEAD" makes the two ALTERNATIVES: with 1s on the table, "keep the result" is
not a legal answer, and offering the ordinary "re-roll failures only" subset
would invent a third option the printed text never gives. Swift Demise, Whirling
Onslaught, Implacable Eradication, Conquering Tyrant, Fireknife and Driven by
Hatred all print the same construction.

WHAT IS NEW HERE is the CONDITION on the whole-roll half: not a unit state, not
a target keyword, but the target's POSITION - "within range of an objective
marker". That is objectives.is_within_range_of_objective(), the same 3" test
rule 12.08 and Burden of Trust already ask, so it is asked rather than
re-derived.

Measured at the moment the re-roll is offered, which is when the Hit roll is on
the table - a target that walks off an objective later does not retroactively
downgrade a re-roll already taken.
"""
from game.objectives import is_within_range_of_objective

REAVERS_OF_THE_VOID_LABEL = "Reavers of the Void"


def applies(squad):
    """Any living model in the unit printing it, per 19.04."""
    if squad is None:
        return False
    return any(getattr(m.profile, "reavers_of_the_void", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def offers_full_reroll(squad, target_squad, objectives=()):
    """Whether the WHOLE-roll half is live - i.e. whether the target is within
    range of an objective marker. The 1s half applies regardless."""
    if not applies(squad) or target_squad is None:
        return False
    return bool(objectives) and is_within_range_of_objective(target_squad, objectives)
