"""Eldrad Ulthran's "Doom" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "At the end of your Movement phase, select one enemy unit within 18" of and
  visible to this model. Until the start of your next Command phase, each time
  a friendly AELDARI model makes an attack that targets that enemy unit, add 1
  to the Wound roll."

Guide's twin, one word apart - the mark machinery is shared and lives in
game/psychic_mark.py, whose docstring carries the reasoning about the duration
that outlives a turn, the army-wide scope, and why range and visibility are
selection criteria checked once.

WHAT IS THIS ABILITY'S OWN is two things:

  * it modifies the WOUND roll, so it hangs in _wound_modifiers() in both
    game/shooting.py and game/fight.py. "Each time a friendly AELDARI model
    makes an attack" says attack, not ranged attack, so both phases - the same
    reading Protect and 'Ard as Nails get in those same two hooks.
  * it does NOT print Guide's "each unit can only be selected for this ability
    once per turn" sentence. Confirmed by asking for that sentence specifically
    rather than assuming the twins matched: copying a near-identical profile is
    exactly how a restriction gets granted or given away by accident. So a
    player fielding both Eldrad and a Farseer may Doom a unit that has already
    been Guided this turn, and a second Eldrad could Doom an already-Doomed one
    (which buys nothing, since the mark is a set).

SIGN CONVENTION: game/modifiers.py counts a POSITIVE amount as worsening a
threshold, and "add 1 to the Wound roll" makes the roll easier, so this is a -1
on the wound threshold. The opposite direction from Protect and 'Ard as Nails,
which sit in the same two hooks as defender-side maluses.
"""

from game.psychic_mark import PsychicMark

DOOM_RANGE_IN = 18.0
# "Add 1 to the Wound roll" improves the roll, so a NEGATIVE amount on the
# threshold - see the sign convention note in the module docstring.
DOOM_WOUND_BONUS = -1


class DoomController(PsychicMark):
    ability_name = "Doom"
    flag = "doom"
    effect_text = "add 1 to Wound rolls"
    range_in = DOOM_RANGE_IN
    once_per_turn = False   # deliberately unlike Guide - see the module docstring


def squad_has_doom(squad):
    return any(getattr(m.profile, "doom", False) and not m.is_dead()
               for m in getattr(squad, "models", None) or ())
