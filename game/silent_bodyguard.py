"""The Deathshroud Terminators' own ability "Silent Bodyguard".

RULE (printed): while a CHARACTER model is leading this unit, that CHARACTER
model has the Feel No Pain 4+ ability.

THE MIRROR OF Rites of Reanimation, and worth stating because they look alike:
the Technomancer's ability is printed on the LEADER and protects the BODYGUARDS;
this one is printed on the BODYGUARDS and protects the LEADER. So it is not
leader_ability() - that asks whether a leader brought the ability - but the
opposite question, asked of the model rather than the unit:

    does THIS model lead a unit whose bodyguards print Silent Bodyguard?

Which is why it reads attached_units' component provenance instead of the
merged model list: after rule 19.01 merges everyone into one Squad, "who was
the leader" survives only in Squad.attached_components.

FNP 4+ is the best in this engine - better than the Technomancer's 5+ and the
Painboy's 5+ - so a character standing here is genuinely hard to kill. It folds
into current_feel_no_pain() like every other source, so a character who already
prints something better keeps it.
"""
from game import attached_units

SILENT_BODYGUARD_FEEL_NO_PAIN = "4+"


def _is_leader_model(model, squad):
    """Whether this model joined `squad` as a Leader/Support component.

    attached_units.leader_models() is the counterpart of bodyguard_models()
    below and already answers exactly this, including the fallback to the
    profile flags for a hand-built squad - so it is asked rather than
    re-derived here."""
    return model in attached_units.leader_models(squad)


def silent_bodyguard_feel_no_pain(model):
    """This model's Feel No Pain threshold from Silent Bodyguard, or "-".

    Returns a threshold STRING, matching UnitProfile.feel_no_pain's own
    convention, so current_feel_no_pain() keeps folding it the same way."""
    squad = getattr(model, "squad", None)
    if squad is None:
        return "-"
    if not getattr(model.profile, "character", False):
        return "-"          # "a CHARACTER model"
    if not _is_leader_model(model, squad):
        return "-"          # "...leading this unit"
    bodyguards = [m for m in attached_units.bodyguard_models(squad) if not m.is_dead()]
    if not bodyguards:
        # Every bodyguard is dead, so nothing is shielding him any more. Read
        # live off survivors for the same reason has_nurgles_gift() is.
        return "-"
    if not all(getattr(m.profile, "silent_bodyguard", False) for m in bodyguards):
        return "-"
    return SILENT_BODYGUARD_FEEL_NO_PAIN
