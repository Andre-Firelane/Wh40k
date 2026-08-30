"""Sky Ray Gunship's "Velocity Tracker".

RULE (printed, word for word):
  "Each time this model makes a ranged attack that targets a unit that can FLY,
   you can re-roll the Hit roll."

AN ORDINARY FAILURES-OR-WHOLE OFFER - "you can re-roll the Hit roll", with no
automatic-1s clause to be an alternative to. So it is a plain
ShootingController._hit_reroll_reason() entry and must NOT be registered in
game/reroll_scope.py: doing so would offer a ones-only re-roll this text never
grants. That absence is asserted in the test, which is the only place it shows.

"A UNIT THAT CAN FLY" is the FLY keyword on the TARGET, which this engine
already tracks per model (UnitProfile.fly, rule 21.03's Take to the Skies).
Read as "any model of that unit can fly", the same any() reading every other
keyword test here uses - a unit with one flying model is a unit that can fly.

RANGED ONLY, so game/fight.py never asks. The Sky Ray has an armoured hull and
could in principle be in melee; the printed text still says "a ranged attack",
and the test pins the absence at the source rather than by building a melee
scene that proves nothing.
"""

VELOCITY_TRACKER_LABEL = "Velocity Tracker"


def unit_has_velocity_tracker(squad):
    """Read live off the living models, so it ends with the gunship."""
    if squad is None:
        return False
    return any(getattr(m.profile, "velocity_tracker", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def target_can_fly(squad):
    """"a unit that can FLY" - any living model of it having the keyword."""
    if squad is None:
        return False
    return any(getattr(m.profile, "fly", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def applies(attacking_squad, target_squad):
    return unit_has_velocity_tracker(attacking_squad) and target_can_fly(target_squad)
