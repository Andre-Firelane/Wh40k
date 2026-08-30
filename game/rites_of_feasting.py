"""Kroot Flesh Shaper's "Rites of Feasting".

RULE (printed, word for word):
  "While this model is leading a unit, models in that unit have the Feel No
   Pain 6+ ability. If that unit destroys one or more enemy units in the Fight
   phase, until the end of the battle, models in that unit have the Feel No
   Pain 5+ ability instead."

RITES OF REANIMATION WITH A SECOND GEAR. The first sentence is word for word
the Technomancer's ability (game/rites_of_reanimation.py) at a worse threshold,
and folds into game/feel_no_pain.py's current_feel_no_pain() the same way -
which also means the "never worse than printed" guarantee is free, so a model
that already prints a 5+ is not dragged down to 6+.

WHAT IS NEW IS THE UPGRADE, and two things about it are easy to get wrong:

  * "UNTIL THE END OF THE BATTLE" - not the turn, not the phase. So the flag
    lives on the SQUAD and is never cleared by any phase or turn boundary. It
    is deliberately NOT on the Shaper's own token: the printed text says the
    UNIT gets it, and a unit whose Shaper later dies has still done the thing
    the rule rewards.
  * "IF THAT UNIT DESTROYS ... IN THE FIGHT PHASE" - the kill has to happen in
    the Fight phase, so a unit that shoots an enemy off the board does not
    qualify. The recorder is therefore called from the fight-phase death sweep
    and asks the turn tracker which phase it is, rather than trusting the
    caller.

WHY THE UPGRADE STICKS TO A UNIT THAT LOSES ITS SHAPER: it does not confer
anything on its own. `rites_of_feasting_feel_no_pain()` still requires the
leader_ability() check first, so a unit with the flag and no living Shaper gets
"-" like any other. The flag only chooses WHICH threshold the ability grants.
"""

from game.attached_units import leader_ability

RITES_OF_FEASTING_FEEL_NO_PAIN = "6+"
RITES_OF_FEASTING_FEAST_FEEL_NO_PAIN = "5+"

FIGHT_PHASE = "Fight"


def unit_has_rites_of_feasting(squad):
    """"While this model is leading a unit" - 24.22, via 19.04's source
    models, so a dead Shaper stops conferring at the documented moment."""
    return leader_ability(squad, "rites_of_feasting")


def has_feasted(squad):
    """Whether this unit has already destroyed an enemy unit in a Fight phase.

    Survives every phase and turn boundary on purpose - the printed duration is
    "until the end of the battle"."""
    return bool(getattr(squad, "rites_of_feasting_feasted", False))


def record_fight_phase_kill(squad, turn_tracker=None):
    """Called when `squad` destroyed an enemy unit. Only counts in the Fight
    phase, which is checked HERE rather than trusted from the caller - the
    death sweep that feeds this runs in every phase.

    Recorded on any unit that has the ability right now, not only while the
    kill is being resolved, and never un-recorded."""
    if squad is None or not unit_has_rites_of_feasting(squad):
        return False
    if turn_tracker is not None and getattr(turn_tracker, "phase", None) != FIGHT_PHASE:
        return False
    squad.rites_of_feasting_feasted = True
    return True


def rites_of_feasting_feel_no_pain(model):
    """This model's Feel No Pain threshold from a Flesh Shaper leading its
    unit, or "-" if there is none.

    Returns a threshold STRING, matching UnitProfile.feel_no_pain's own
    convention, so the caller keeps parsing it with parse_threshold()."""
    squad = getattr(model, "squad", None)
    if squad is None or not unit_has_rites_of_feasting(squad):
        return "-"
    return (RITES_OF_FEASTING_FEAST_FEEL_NO_PAIN if has_feasted(squad)
            else RITES_OF_FEASTING_FEEL_NO_PAIN)
