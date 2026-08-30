"""Does this unit's own shooting leave its Hidden status alone?

EXTRACTED AT THE SECOND CONSUMER, this repo's standing rule. Rule 13.09's
Hidden is decided from one dict - ShootingController.last_ranged_attack_turn -
written in exactly one place, and "do not write it for this unit" is how a rule
says the shooting did not give the unit away. Two T'au detachments now say it,
by different routes:

  * Advanced Acquisition Cadre's Expert Fieldcraft - by KEYWORD: a PATHFINDER
    TEAM or STEALTH BATTLESUITS unit (game/advanced_acquisition_cadre.py).
  * Auxiliary Cadre's Localised Stealth Projectors - by AURA: a KROOT/VESPID
    STINGWINGS unit standing within 6" of a friendly GHOSTKEEL/STEALTH one
    (game/auxiliary_cadre.py).

Without this fold, game/shooting.py would grow a second call and an `or`, and
the next source a third - the drift this codebase keeps consolidating. With it,
_note_ranged_attack() asks one question and a third source changes nothing
there.

THE MODULE IS NAMED AFTER THE QUESTION, not after either detachment, for the
reason game/weapon_range.py and game/model_return.py were: a module named for
whichever ability arrived first is the lying name this repo renames later.

WHY THE ARGUMENTS ARE PASSED IN
-------------------------------
`reactive` is game/shooting.py's own flag for a Fire Overwatch / Snap Shooting
activation, and `all_squads` is what the aura needs to find its source. Both
are handed in rather than reached for, so this module stays a pure question and
the controller keeps owning the state.
"""

from game import advanced_acquisition_cadre, auxiliary_cadre


def keeps_hidden(squad, reactive=False, all_squads=()):
    """True when this unit's ranged attacks must NOT be recorded against it.

    A reactive activation is excluded here, once, rather than in each source:
    both printed texts are about the owner's own Shooting phase, and Fire
    Overwatch happens in the opponent's turn.
    """
    if squad is None or reactive:
        return False
    if advanced_acquisition_cadre.shooting_keeps_hidden(squad):
        return True
    return auxiliary_cadre.stealth_projector_covers(squad, all_squads)
