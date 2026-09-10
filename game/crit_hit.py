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
LEADING_RANGED_CRIT_HIT_THRESHOLD = 5


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


def _flesh_hunger_applies(model, target_squad):
    """Flayed Ones' Flesh Hunger, both of its conditions.

    Read off the MODEL rather than the unit ("each time a model in this unit
    makes a melee attack") - exact by construction here, since every model in
    one attack group belongs to one unit, and it keeps working if the squad is
    ever an attached one whose other component does not print it.

    "Below Half-strength" is game/squad.py's is_below_half_strength(), the
    same answer the four DESTROYER CULT re-rolls read - one definition of the
    phrase rather than a second count of models."""
    if model is None or target_squad is None:
        return False
    if not getattr(model.profile, "flesh_hunger", False):
        return False
    from game.squad import is_below_half_strength
    return is_below_half_strength(target_squad)


def crit_hit_threshold(model, target_squad=None, whispering_web=None, melee_only=False,
                       hit_threshold=None, weapon=None):
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

    `weapon` is the gun this attack is being made with, and is read by exactly
    one source: Warhost's Blitzing Firepower, whose second clause is a
    property of the WEAPON rather than of the model or its unit ("if such a
    weapon already has that ability"). Two guns on one model can differ, which
    is why the model alone cannot answer it. Optional, like the two below, so
    every existing caller keeps its behaviour - the Fight-phase call sites do
    not pass one, and Blitzing Firepower is ranged-only anyway.

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
    # Warhost's Blitzing Firepower - the only WEAPON-specific source here.
    # Folded with min() like every other one: the best threshold wins.
    if weapon is not None:
        from game import warhost_blitzing_firepower
        _bf = warhost_blitzing_firepower.crit_hit_threshold_for(model, weapon)
        if _bf is not None:
            threshold = min(threshold, _bf)
    if melee_only:
        if _unbridled_carnage_applies(squad):
            threshold = min(threshold, UNBRIDLED_CARNAGE_CRIT_HIT_THRESHOLD)
        if _mandiblasters_applies(model, squad):
            threshold = min(threshold, MANDIBLASTERS_CRIT_HIT_THRESHOLD)
        # Flayed Ones' Flesh Hunger: "each time a model in this unit makes a
        # melee attack, if the target of that attack is Below Half-strength, a
        # successful Hit roll scores a Critical Hit."
        #
        # THE SECOND SOURCE THAT IS NOT A NUMBER. Like Cry of the Wind below,
        # the threshold is not fixed - it is whatever this attack needs to hit,
        # so the grant is min()ed against `hit_threshold` rather than against a
        # constant. The fallback when a caller has none is the model's own
        # printed Weapon Skill, which is the same answer whenever nothing is
        # modifying the roll (the dice-panel label's case).
        #
        # MELEE-only by the printed wording, hence its place inside this guard,
        # and TARGET-specific, which is why it needs target_squad - a Flayed One
        # swinging at a full-strength unit gets rule 05.01's unmodified 6.
        if (_flesh_hunger_applies(model, target_squad)):
            needed = hit_threshold
            if needed is None:
                needed = _threshold_number(getattr(model.profile, "weapon_skill", None))
            if needed is not None:
                threshold = min(threshold, needed)
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
    # TWO Necron characters print this ability under two different names, word
    # for word the same text: the Plasmancer's "Harbinger of Destruction" and
    # the Lokhust Lord's "Destroyer Cult" - "while this model is leading a
    # unit, each time a model in that unit makes a RANGED attack, a successful
    # unmodified Hit roll of 5+ scores a Critical Hit."
    #
    # So the FLAG is named for the mechanic and not for whichever datasheet
    # arrived first: a `harbinger_of_destruction` attribute on a Lokhust Lord
    # would be the lying name this repo renames rather than copies. Each
    # datasheet still states its own printed name in abilities_text.
    #
    # Ranged only, hence the same melee_only guard Cry of the Wind uses; and a
    # LEADER ability, so it is read with leader_ability() rather than off the
    # model - none of the bodyguards print it, which is the whole point of one.
    if not melee_only and leader_ability(squad, "leading_ranged_crit_on_5"):
        threshold = min(threshold, LEADING_RANGED_CRIT_HIT_THRESHOLD)
    return threshold
