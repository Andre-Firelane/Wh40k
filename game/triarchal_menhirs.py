"""The Silent King: "Triarchal Menhirs" - linked destruction.

RULE (verbatim, rules/necrons/The Silent King.md):

  "Triarchal Menhirs: If this unit's Szarekh model is destroyed, all of this
   unit's remaining Triarchal Menhir models are also destroyed."

THE FIRST LINKED DESTRUCTION IN THIS ENGINE. Nothing else printed by the five
built armies kills one model BECAUSE another one died, so there is no fold to
join and no precedent to copy - this module is the whole of it.

IT RUNS IN THE DEATH SWEEP, and the reason is rule-shaped rather than
convenient: remove_dead_models() runs ONCE per frame, so between a model
reaching 0 wounds and the sweep clearing it there is a window in which
squad.models still holds the corpse. Error class 12 in this repo's list is
made of abilities that read that window wrongly. This one WANTS it: it has to
see that Szarekh is dead while the Menhirs are still standing, which is exactly
what the pre-sweep state offers.

THE LIVENESS TEST IS is_dead(), NOT `not squad.models`. The unit is not wiped -
Szarekh is down and two Menhirs are up - so a whole-unit test answers False and
this would never fire. Same trap the Fade Back report was made of.

IT DOES NOT FIRE IN REVERSE. Both Menhirs dying leaves Szarekh alive and
fighting: the printed sentence has one direction, and a symmetric reading would
kill a 16-wound EPIC HERO because his two escorts fell. Pinned from both sides.

DEADLY DEMISE DOES NOT RIDE ALONG, and that is the printed text rather than a
simplification: the CORE line reads "Deadly Demise D6+3 (SZAREKH MODEL ONLY)",
so the Menhirs carry no deadly_demise at all and destroying them here detonates
nothing. A reader who gave the unit one demise would set off three.
"""

TRIARCHAL_MENHIRS_LABEL = "Triarchal Menhirs"


def _is_szarekh(model):
    return getattr(model.profile, "voice_of_the_triarch", False)


def szarekh_is_down(squad):
    """Whether this unit printed a Szarekh model and it is dead or gone.

    THE "DID IT EVER HAVE ONE" HALF READS models PLUS destroyed_models, not
    the live list alone. Squad has no `starting_models` - it carries a
    starting_model_COUNT, an int - so once remove_dead_models() has swept
    Szarekh into destroyed_models, a live-list-only test finds no Szarekh at
    all, decides this datasheet never printed one, and spares the Menhirs. That
    is the very failure the sweep ordering is supposed to make impossible, and
    it would only show up a frame late.

    The "is it down" half then reads only the LIVE list, where a corpse still
    sitting in the pre-sweep window correctly counts as down."""
    if squad is None:
        return False
    ever = [m for m in list(squad.models) + list(getattr(squad, "destroyed_models", ()) or ())
            if _is_szarekh(m)]
    if not ever:
        return False
    living = [m for m in squad.models if _is_szarekh(m) and not m.is_dead()]
    return not living


def menhirs_to_destroy(squad):
    """The living Menhir models this rule takes, or an empty list."""
    if not szarekh_is_down(squad):
        return []
    return [m for m in squad.models
            if getattr(m.profile, "triarchal_menhir", False) and not m.is_dead()]


def apply(squad, game_log=None):
    """Called from main.py's death sweep, before remove_dead_models(). Returns
    the models it took, so the caller can report a real number."""
    doomed = menhirs_to_destroy(squad)
    if not doomed:
        return []
    for model in doomed:
        model.current_wounds = 0
    if game_log is not None:
        game_log.add("%s (%s): Szarekh is destroyed, so %d remaining Triarchal "
                     "Menhir model(s) are destroyed too."
                     % (TRIARCHAL_MENHIRS_LABEL, squad.name, len(doomed)))
    return doomed
