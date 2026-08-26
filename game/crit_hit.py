"""When a hit roll counts as a Critical Hit - the single place both hit steps
ask.

Was game/melee_crit.py, whose docstring said "melee only, and that holds twice
over: this module is read from game/fight.py's hit step alone, so a ranged
attack can never see it, and each source has its own 'melee attack' wording".
Lhykhis' Whispering Web breaks both halves of that: it says "each time a
friendly AELDARI model makes an attack", not melee attack, so it has to be read
from game/shooting.py's hit step as well - which until now passed no crit
threshold at all and simply took rule 05.02's default.

So the module is renamed rather than given a ranged twin. A second place
deciding "what is the crit threshold" is precisely the drift this codebase
keeps consolidating away (see game/invulnerable_save.py, game/melee_crit.py
itself, game/damage_reroll.py, game/damage_estimate.py, game/unmodified_six.py
and game/psychic_mark.py), and Whispering Web applies to BOTH phases, so it
could not live in either one.

Rule 05.02's default is 6. Every source here LOWERS that threshold, and the
comparison is against the RAW die, which is what "unmodified hit roll of N+"
asks for - a -1 to hit still misses on a 4, but a natural 5 is still a Critical
Hit. The BEST (lowest) threshold wins if two sources apply at once.

WHICH SOURCES REACH WHICH PHASE is a property of each source's own wording, not
of this module any more:

  * Unbridled Carnage (Ork stratagem) and Mandiblasters (Striking Scorpions)
    both say "melee attack", so they are gated on the caller being the Fight
    phase. That gate is `melee_only`, passed by the two call sites, rather than
    a re-check of the phase here - the caller knows which step it is, and
    reading turn_tracker.phase would be wrong anyway for a reactive Snap Shot
    (15.08/15.09), which is a ranged attack made during the Movement phase.
  * Whispering Web says "makes an attack", so it reaches both.
"""

from game import whispering_web as ww
from game.attached_units import leader_ability

DEFAULT_CRIT_HIT_THRESHOLD = 6

UNBRIDLED_CARNAGE_CRIT_HIT_THRESHOLD = 5
MANDIBLASTERS_CRIT_HIT_THRESHOLD = 5
WHISPERING_WEB_CRIT_HIT_THRESHOLD = 5
HARBINGER_OF_DESTRUCTION_CRIT_HIT_THRESHOLD = 5


def _unbridled_carnage_applies(squad):
    """War Horde's Unbridled Carnage: a phase-long grant on the unit."""
    return squad is not None and getattr(squad, "unbridled_carnage_active", False)


def _mandiblasters_applies(model, squad):
    """Striking Scorpions' Mandiblasters: the model has the ability AND its
    unit made a Charge move this turn.

    Reads Squad.charged_this_turn rather than Squad.fights_first, which looks
    like it would do the job and does not: game/counteroffensive.py (15.12)
    also sets that one, so it means "fights first", not "charged". Using it
    would hand this ability to a unit that never charged."""
    profile = getattr(model, "profile", None)
    if profile is None or not getattr(profile, "mandiblasters", False):
        return False
    return squad is not None and getattr(squad, "charged_this_turn", False)


def _threshold_number(value):
    """"2+" -> 2. None/"-" -> None."""
    try:
        return int(str(value).rstrip("+"))
    except (TypeError, ValueError):
        return None


def crit_hit_threshold(model, target_squad=None, whispering_web=None, melee_only=False,
                       hit_threshold=None):
    """The unmodified hit roll this model needs for a Critical Hit.

    `hit_threshold` is the roll this attack actually needs to HIT, and is only
    read by Baharroth's Cry of the Wind, whose printed wording is not a fixed
    number at all: "a successful unmodified Hit roll scores a Critical Hit", so
    the two thresholds are the same roll. The callers that have it pass it (the
    hit step and its re-roll branch); the one that does not is the dice-panel
    label, which falls back to the model's own printed Ballistic Skill - the
    same answer whenever nothing is modifying the roll, which is the case the
    label is describing anyway.

    Takes the attacking MODEL so the call sites read their group's
    representative exactly like every other per-group adjuster does. Exact
    rather than approximate for the unit-level sources, since every model in one
    attack group belongs to one unit; Mandiblasters is read off the model's own
    profile, which is exact by construction.

    `target_squad` and `whispering_web` are only needed by that ability, which
    is target-specific; both default to None so every existing caller keeps its
    behaviour. `melee_only` says the caller is the Fight phase's hit step, which
    is what admits the two melee-worded sources.

    Tolerates `model` being None and degrades to the default. The function this
    replaced did so by accident (it only ever used getattr); doing it on purpose
    matters, because a threshold lookup that raises would abort a whole attack
    sequence over a missing representative."""
    if model is None:
        return DEFAULT_CRIT_HIT_THRESHOLD
    squad = getattr(model, "squad", None)
    threshold = DEFAULT_CRIT_HIT_THRESHOLD
    if melee_only:
        if _unbridled_carnage_applies(squad):
            threshold = min(threshold, UNBRIDLED_CARNAGE_CRIT_HIT_THRESHOLD)
        if _mandiblasters_applies(model, squad):
            threshold = min(threshold, MANDIBLASTERS_CRIT_HIT_THRESHOLD)
    if whispering_web is not None and whispering_web.applies(squad, target_squad):
        threshold = min(threshold, WHISPERING_WEB_CRIT_HIT_THRESHOLD)
    # Baharroth's Cry of the Wind: "each time this model is set up on the
    # battlefield, until the end of the turn, each time this model makes a
    # ranged attack, a successful unmodified Hit roll scores a Critical Hit."
    # RANGED only, hence the melee_only guard - and it is not a fixed number,
    # it is whatever the attack needs to hit.
    # Gated on the PRINTED ability as well as the runtime flag: main.py only
    # ever sets the flag on a model whose profile has it, and this makes that
    # true by construction rather than by convention.
    if (not melee_only
            and getattr(model, "cry_of_the_wind_active", False)
            and getattr(model.profile, "cry_of_the_wind", False)):
        needed = hit_threshold
        if needed is None:
            needed = _threshold_number(getattr(model.profile, "ballistic_skill", None))
        if needed is not None:
            threshold = min(threshold, needed)
    # The Necron Plasmancer's Harbinger of Destruction: "while this model is
    # leading a unit, each time a model in that unit makes a RANGED attack, a
    # successful unmodified Hit roll of 5+ scores a Critical Hit." Ranged only,
    # hence the same melee_only guard Cry of the Wind uses; and a LEADER
    # ability, so it is read with leader_ability() rather than off the model -
    # none of the bodyguards print it, which is the whole point of one.
    if not melee_only and leader_ability(squad, "harbinger_of_destruction"):
        threshold = min(threshold, HARBINGER_OF_DESTRUCTION_CRIT_HIT_THRESHOLD)
    return threshold
