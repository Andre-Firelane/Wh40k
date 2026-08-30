"""The Defiler's own ability "Scuttling Walker".

RULE (printed): this model can move through models (excluding TITANIC models)
and terrain features when it makes a Normal, Advance or Fall Back move; it can
move within Engagement Range of enemy models but cannot END that move within
Engagement Range of them; and any Desperate Escape test it takes is
automatically passed.

THREE CLAUSES, AND ALL THREE ALREADY HAVE A HOME - this module is a predicate,
not a new movement mechanic:

  * "through terrain features" is rule 13.06's permission, which this engine
    asks through UnitProfile.can_move_through_dense_terrain. That property is
    a keyword test (INFANTRY/BEASTS/SWARM/MOBILE) and a VEHICLE WALKER is none
    of them, so the ability has to be folded in beside it rather than by adding
    a keyword the datasheet does not print.
  * "through models" is the same relaxation MovementController.clamp_move()
    already applies to FLY, asked per model.
  * "cannot END that move within Engagement Range" is rule 09.02's ordinary
    end-of-move check, which this engine enforces for everyone anyway - so the
    clause needs NO code, only a test that pins it. Written out here because
    "can move within Engagement Range" reads like a licence to end there.

TITANIC IS A DOCUMENTED NO-OP: no datasheet in this engine carries that
keyword, the same status game/actions.py and game/rapid_ingress.py record for
AIRCRAFT and FORTIFICATION. Transcribed anyway so the exclusion is visible.

DESPERATE ESCAPE does not exist in this engine either (there is no Fall Back
test), so that clause is a second documented no-op rather than a silent
omission.
"""

TITANIC_EXCLUDED = True  # documented no-op - no datasheet here has the keyword


def has_ability(model):
    return bool(getattr(getattr(model, "profile", None), "scuttling_walker", False))


def can_cross_terrain(model):
    """Whether this model ignores Dense terrain while moving.

    Asked ALONGSIDE UnitProfile.can_move_through_dense_terrain rather than
    instead of it, so the keyword rule keeps meaning what it means for every
    other model."""
    return has_ability(model)


def can_cross_models(model):
    """Whether this model may pass through other models mid-move - the same
    relaxation FLY already gets in MovementController.clamp_move()."""
    return has_ability(model)
