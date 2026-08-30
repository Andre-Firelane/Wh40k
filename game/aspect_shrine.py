"""Aspect Shrine tokens - the wargear shared by every ASPECT WARRIORS
datasheet in this engine (Striking Scorpions, Howling Banshees, Warp Spiders,
Dire Avengers).

RULE (printed, word for word):
  Wargear: "For every 5 models in this unit, it can have 1 Aspect Shrine
  token."
  Ability: "Once per battle for each Aspect Shrine token this unit has, you can
  change the result of one Hit roll or one Wound roll made for a model in this
  unit (excluding CHARACTER models) to an unmodified 6."

WHY THIS TOOK ITS OWN STEP
--------------------------
It was deferred on four datasheets in a row, and the reason changed halfway.
At first the printed wording was missing and only a paraphrase was available -
a bad reason once the wording could simply be asked for, and that is recorded
in CLAUDE.md. What remained after the text arrived is a real one: this is a
per-battle resource plus an INTERACTIVE intervention at four different
resolution points (the Hit roll and the Wound roll, in both game/shooting.py
and game/fight.py), i.e. the two hottest paths in the engine.

WHERE THE TOKENS COME FROM
--------------------------
Granted automatically at build time, `starting strength // 5`, rather than
offered as a menu item. The wargear line says "can have", but it costs no
points and has no downside whatsoever, so a choice between "take it" and "do
not take it" has exactly one sensible answer - the same reasoning that makes
Commander Farsight's Puretide's Teachings discount automatic rather than a
prompt. Derived from STARTING strength, not the live model count: tokens are
bought when the army list is written, and a unit that loses models keeps them.

WHICH DIE IS CHANGED
--------------------
Not asked. Within one roll every die is identical - same weapon, same target -
so the best die to change is always determined, never a judgement call:

- a FAILURE, if there is one: it becomes a hit/wound AND a critical, which is
  strictly the largest possible gain;
- otherwise a non-critical SUCCESS, which gains only the critical.

So the player is asked one yes/no question, not two questions.

WHEN IT IS OFFERED
------------------
Only when it would actually buy something, which is a CERTAINTY check rather
than an estimate (the same honest-eligibility shape as The Arro'kon Protocol's
"nothing in range is big enough" and game/overwatch.py's own filter):

- the unit must hold an unspent token;
- the roll must be for a non-CHARACTER model;
- and there must be something to gain - a failure to convert, OR a non-critical
  success in a step where a critical actually does something. A critical hit is
  worth nothing over an ordinary one unless the weapon has [SUSTAINED HITS] or
  [LETHAL HITS]; a critical wound likewise unless it has [DEVASTATING WOUNDS].

The offer sits at the END of its step, after every re-roll has resolved - a
once-per-battle resource should be spent against the roll that actually stands,
which is the same ordering argument that puts Monster Hunters after Forward
Observers. It is a pure choice with no dice of its own, so unlike the re-roll
offers it resolves synchronously.

ONE TOKEN PER ROLL, deliberately. The rule would allow a two-token unit to
change two dice of the same roll, but each token is a separate "you can change
the result of one roll" and re-prompting on the same roll for the second is the
sort of repeated interruption this project has pushed back on before. Noted as
a simplification rather than left to be discovered; the second token remains
fully available on any later roll.
"""

from game import attached_units
from game import unmodified_six

ASPECT_SHRINE_MODELS_PER_TOKEN = 5
# "an unmodified 6" - and rule 05.01 makes an unmodified 6 always a success,
# while rule 05.02 makes it a critical under any threshold at or below 6 (so
# also under Mandiblasters' or Unbridled Carnage's lowered 5+).
ASPECT_SHRINE_RESULT = unmodified_six.UNMODIFIED_SIX


def squad_has_aspect_shrine(squad):
    """Rule 19.04's shape: any() rather than all(), so an attached CHARACTER
    does not take the unit's own wargear away from it."""
    models = getattr(squad, "models", None)
    if not models:
        return False
    return any(getattr(m.profile, "aspect_shrine", False) for m in models)


def tokens_for(squad):
    """How many tokens this unit is entitled to - "for every 5 models", read
    off STARTING strength (see the module docstring)."""
    if squad is None or not squad_has_aspect_shrine(squad):
        return 0
    starting = getattr(squad, "starting_model_count", 0) or 0
    return starting // ASPECT_SHRINE_MODELS_PER_TOKEN


def grant_tokens(squad):
    """Called once, when the unit is built."""
    squad.aspect_shrine_tokens = tokens_for(squad)


def unspent_tokens(squad):
    if squad is None:
        return 0
    held = getattr(squad, "aspect_shrine_tokens", 0)
    return max(0, held - getattr(squad, "aspect_shrine_tokens_used", 0))


def spend(squad):
    squad.aspect_shrine_tokens_used = getattr(squad, "aspect_shrine_tokens_used", 0) + 1


def _is_character(squad, model):
    """"excluding CHARACTER models" - a CHARACTER here is a model that joined
    via rule 19.01, i.e. one of the leader/support component's own models.

    Judged from the weapon group's representative model, the same
    exact-in-practice simplification every adjuster in this codebase uses: a
    joined character carries its own datasheet's weapons, so it lands in its
    own attack group rather than sharing one with the Aspect Warriors."""
    if model is None or squad is None:
        return False
    return model in attached_units.leader_models(squad, alive_only=False)


def _usable(squad, model):
    return (
        squad is not None
        and unspent_tokens(squad) > 0
        and not _is_character(squad, model)
    )


def usable(squad, model):
    """Public: has this unit a token to spend on a roll made by `model`?

    The RESOURCE half only - whether changing a die would buy anything is a
    separate question, and since game/unmodified_six_controller.py turned the
    offer into a button rather than a prompt, it is the player's to answer
    (see that module for why the old certainty gate could relax)."""
    return _usable(squad, model)


ACCEPT_LABEL = "Spend an Aspect Shrine token"


def button_label(squad):
    """The left-panel button. Says how many tokens are left, because with a
    once-per-battle resource that is the whole decision."""
    return f"Aspect Shrine ({unspent_tokens(squad)} token(s) left)"

