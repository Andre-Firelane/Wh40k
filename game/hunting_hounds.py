"""Kroot Hounds' "Hunting Hounds".

RULE (printed, word for word):
  "While this unit is within 12" of one or more friendly KROOT CHARACTER
   models, the Objective Control characteristic of models in this unit is 1."

THE ONLY REASON KROOT HOUNDS CAN HOLD ANYTHING. Their printed OC is 0, which
makes them the rare unit that contributes nothing to an objective at all - so
this ability is not a bonus, it is the whole of their objective play, and
getting it wrong is invisible until a game is lost on a point.

"IS 1", NOT "+1". It SETS the characteristic, so a model whose OC were somehow
already 2 would be reduced. On this datasheet the printed value is 0 and the
two readings cannot come apart, which is exactly why the rule's own wording is
followed rather than the convenient one - the Death Guard's Scabrous Soulrot
already documents the mirror trap (a floor that must not raise a printed 0).

READ LIVE, unlike Loping Pounce next door. The printed text is "WHILE this
unit is within 12"", a continuous condition, where Loping Pounce is "AT THE
START of your Command phase ... until the end of the turn". Two abilities on
one datasheet with two different durations, and the difference is one word.

"KROOT CHARACTER MODELS" - measured to the MODEL, not the unit, which matters
because 19.01 merges a Shaper into the unit he leads: the range is to him, not
to the Carnivores around him.
"""

from game.squad import edge_distance

HUNTING_HOUNDS_RANGE_IN = 12.0
HUNTING_HOUNDS_OC = 1


def unit_has_hunting_hounds(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "hunting_hounds", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def kroot_character_models(all_tokens, owner):
    """Living models of `owner` that are both KROOT and CHARACTER."""
    return [t for t in all_tokens or ()
            if not t.is_dead()
            and getattr(t.profile, "kroot", False)
            and getattr(t.profile, "character", False)
            and getattr(getattr(t, "squad", None), "owner", None) == owner]


def applies(squad, all_tokens):
    """Whether the unit is currently inside a friendly Kroot character's 12"."""
    if not unit_has_hunting_hounds(squad) or not all_tokens:
        return False
    models = [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]
    for character in kroot_character_models(all_tokens, squad.owner):
        if getattr(character, "squad", None) is squad:
            continue  # its own unit has no character, but be explicit about it
        for model in models:
            if edge_distance(character, model) <= HUNTING_HOUNDS_RANGE_IN:
                return True
    return False


def objective_control(model, all_tokens):
    """This model's OC right now: 1 while the ability is live, otherwise its
    printed value.

    Returns the NUMBER, so the caller keeps treating OC as a number - the same
    contract game/objectives.py already reads off the profile."""
    printed = getattr(model.profile, "oc", 0)
    if not getattr(model.profile, "hunting_hounds", False):
        return printed
    squad = getattr(model, "squad", None)
    return HUNTING_HOUNDS_OC if applies(squad, all_tokens) else printed
