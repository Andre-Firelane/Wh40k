"""Transdimensional Displacement - the Transcendent C'tan's own ability.

RULE (printed, word for word):

  "In your Movement phase, when this unit is selected to make an advance move,
   you can use this ability. If you do:
     - That advance move has no maximum distance.
     - This unit can move through all types of model (including enemy models
       and MONSTER/VEHICLE models).
     - After moving, this unit must be more than 8" horizontally from all
       enemy units."

THREE CLAUSES, THREE EXISTING SEAMS, and the interesting part is that not one
of them needed a new mechanism:

  1. NO MAXIMUM DISTANCE -> MovementController.start_run()'s no-roll branch.
     Three abilities already take it (Jain Zar's Whirling Death, Mont'ka's
     Aggressive Mobility, Guardian Time to Strike); all three say "do not make
     an Advance roll. Instead ... add N inches". This is the fourth, with no
     ceiling instead of a number.

  2. THROUGH ALL TYPES OF MODEL -> clamp_move()'s models-only bypass, next to
     Desperate Escape and the Defiler's Scuttling Walker. MODELS ONLY: the
     printed text says "all types of MODEL" and says nothing about terrain, so
     this is deliberately NOT the FLY branch above it, which also ignores
     terrain features. A Transcendent C'tan still cannot walk through a wall.

  3. MORE THAN 8" AFTER MOVING -> Squad.check_min_enemy_distance(), which is
     rule 24.32's Scout clearance with its wording parameterised. Same eight
     inches, same edge-to-edge 2D reading, same moment (at confirm).

WHY NO ADVANCE ROLL IS MADE, WHICH IS A DECISION AND NOT A TRANSCRIPTION
------------------------------------------------------------------------
The printed text does not contain the words "do not make an Advance roll" that
the three existing carriers of that branch do. It removes the MAXIMUM instead.

Read literally that would mean rolling a D6 whose value cannot change anything,
and this engine does not throw those: game/coordinated_leadership.py refuses to
roll when its result could not be spent, for the reason that a die which cannot
matter reads as a bug. Command Re-roll would also be offered on it (15.02),
letting a player spend a CP to alter a number with no effect.

So: no die. The choice is recorded here rather than buried, because the
opposite reading is defensible and someone will check.

IT IS A CHOICE ("you can use this ability"), so it is offered rather than
applied - a panel button beside Advance, which is exactly how rule 21.03's
Take to the Skies offers its own optional alternative to a normal move. The AI
is not given a verdict for it: the standing instruction for this backfill is no
ai/agent_driver.py judgements, and this one is not army-wide.

THE BUDGET IS THE BOARD DIAGONAL, not float("inf"). MovementController's
remaining_range feeds arithmetic (clamp_move scales a segment by
budget / dist), and an infinity there produces NaN the first time a model is
asked to move zero inches. The diagonal is unreachable by construction, so it
is "no maximum" for every board this engine can build, and it stays a number.
"""

TRANSDIMENSIONAL_DISPLACEMENT_NAME = "Transdimensional Displacement"

#: "more than 8" horizontally from all enemy units" - the same eight rule 24.32
#: prints for a Scout move, and measured by the same helper.
TRANSDIMENSIONAL_MIN_ENEMY_DISTANCE_IN = 8.0


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def has_ability(squad):
    """Whether this unit contains a living model with the ability."""
    return any(getattr(m.profile, "transdimensional_displacement", False)
               for m in _living(squad))


def model_has_ability(model):
    """Per MODEL, for clamp_move()'s bypass.

    Asked per model rather than per unit for the same reason
    `flying_this_move and token.profile.fly` is: the bypass belongs to the
    models that actually have the ability. The Transcendent C'tan is a
    one-model unit that nothing can lead - it prints no Leader line and no
    datasheet leads it - so the two readings cannot differ today; written the
    narrow way anyway, because that is the half that stays right.
    """
    if model is None or getattr(model, "is_dead", lambda: False)():
        return False
    return bool(getattr(getattr(model, "profile", None),
                        "transdimensional_displacement", False))
