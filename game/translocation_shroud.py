"""Translocation Shroud - the Overlord with translocation shroud's own ability.

RULE (printed, word for word):

  "Each time this model's unit Advances, do not make an Advance roll for it.
   Instead, until the end of the phase, add 6" to the Move characteristic of
   models in that unit. In addition, each time a model in that unit makes a
   Normal, Advance or Fall Back move, until that move is finished, it can move
   horizontally through models and terrain features (it cannot finish a move on
   top of another model or its base)."

TWO HALVES, and both have to be honoured or the ability is a downgrade.

HALF ONE: THE ADVANCE. Word for word the sentence Mont'ka's Aggressive
Mobility prints ("do not make an Advance roll for it. Instead, until the end of
the phase, add 6" to the Move characteristic of models in your unit"), so it
takes the SAME no-roll branch in MovementController.start_run() rather than a
fourth one beside it. Jain Zar's Whirling Death and the Guardian Battlehost's
Time to Strike are the other two carriers.

HALF TWO: THROUGH MODELS AND TERRAIN, and this one is gated on the MOVE.

  * "Normal, Advance or Fall Back" and nothing else. An ordinary Movement-phase
    move - Normal or Advance alike - leaves MovementController.move_mode None
    (an Advance is a choice made inside that move, which is why can_advance()
    requires it), and a Fall Back is "fall_back". Charge, Pile In, Consolidate
    and every out-of-phase move are NOT on the printed list.
  * SO IT CANNOT LIVE IN Obstacle.blocks_movement_for(), where the Defiler's
    Scuttling Walker puts its own terrain half. That method takes a MODEL and
    nothing else - it is deliberately the one seam every consumer of "may this
    model pass through that" shares, including the route search and the AI's
    corner routing - and it therefore has no idea which move is being made.
    Threading a move mode into it would give three unrelated callers a
    parameter they cannot answer. It is asked in clamp_move() instead, where
    the current move IS known.
  * BOTH terrain and models, so it joins the branch Take to the Skies uses
    rather than the models-only one next to Desperate Escape. The Transcendent
    C'tan's Transdimensional Displacement is the mirror case one file over:
    models only, because its printed text says models and nothing about
    terrain.

"IT CANNOT FINISH A MOVE ON TOP OF ANOTHER MODEL OR ITS BASE" NEEDS NO CODE -
this engine enforces that for every model, on every move
(Squad.check_model_overlap at confirm). Written out because "can move through
models" reads like a licence to end there, and pinned in the suite so the
clause is covered by something rather than by nothing.
"""

#: "add 6" to the Move characteristic" - the same flat replacement for the D6
#: that Aggressive Mobility and Whirling Death print.
TRANSLOCATION_SHROUD_BONUS_IN = 6.0
TRANSLOCATION_SHROUD_NAME = "Translocation Shroud"

#: The three printed moves. An ordinary Movement-phase move (Normal OR Advance)
#: is move_mode None; a Fall Back is "fall_back". Nothing else is on the card.
TRANSLOCATION_SHROUD_MOVE_MODES = (None, "fall_back")


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def squad_has_shroud(squad):
    """Rule 19.03 pooling: the printed subject is "this model's UNIT", so one
    shrouded Overlord carries the whole unit he has been merged into."""
    if squad is None:
        return False
    return any(getattr(m.profile, "translocation_shroud", False) for m in _living(squad))


def skips_advance_roll(squad):
    """MovementController.start_run()'s no-roll branch asks this, exactly as it
    asks Whirling Death and Aggressive Mobility."""
    return squad_has_shroud(squad)


def crosses_everything(move_mode, token):
    """Whether THIS model, on THIS move, ignores models and terrain.

    Both arguments matter: the profile flag says who, the move mode says when.
    A shrouded Overlord charging is bound by terrain and by enemy bases like
    anyone else, because a charge is not on the printed list."""
    if move_mode not in TRANSLOCATION_SHROUD_MOVE_MODES:
        return False
    squad = getattr(token, "squad", None)
    if squad is not None:
        return squad_has_shroud(squad)
    return bool(getattr(getattr(token, "profile", None), "translocation_shroud", False))
