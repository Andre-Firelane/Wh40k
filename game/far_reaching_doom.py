"""Path of the Outcast's "Far-Reaching Doom" - the detachment rule.

RULE (printed, word for word):
  "When a friendly RANGERS/SHROUD RUNNERS unit is selected to shoot, enemy
  units have +6" detection range until that friendly unit has shot."

NAMED AFTER THE RULE, NOT THE DETACHMENT, and that is deliberate: this engine
already has a game/path_of_the_outcast.py, and it is the RANGERS DATASHEET
ability of the same name - a reactive D6" Normal move when an enemy ends a move
nearby. The two share a name and not one word of text. Naming this module after
the detachment would have put two unrelated rules one underscore apart; the
test pins the pair from both sides.

THE FOURTH SOURCE IN game/detection_range.py, after prey_marks, unmasking and
the Negation Emitters Enhancement. Attached the way Negation Emitters is - a
module-level call INSIDE bonus_in() - rather than as a fifth named argument,
so neither of that function's two call sites has to change. Five ability-named
arguments summed at a call site is exactly the shape in which the sixth reaches
only one of them, which is why the extraction happened in the first place.

WHICH DIRECTION, written out because it inverts cleanly and reads fine wrong.
Detection Range belongs to the HIDDEN model: is_detectable() asks whether an
observer stands within the hidden model's range. A POSITIVE contribution on an
enemy therefore makes that enemy visible from FURTHER AWAY - a penalty on them,
which is what a sniper detachment should be. Granting it to one's own units
instead would hide them better, which is a different (and better) rule than the
one printed.

WHOSE RANGE CHANGES: "ENEMY units", i.e. the enemies of whoever owns the
shooting Rangers. So the window records the shooting unit's OWNER, and the
bonus is handed to squads belonging to anyone else. Holding a set of marked
squads instead would have been wrong in a way no two-player test can see - the
printed text names no targets, it changes a characteristic of everything on the
other side.

THE WINDOW is "selected to shoot" ... "until that friendly unit has shot", which
is exactly the pair of seams game/targeting_array.py already uses:
ShootingController.start_shooting() opens it, _actually_finish_squad() closes
it. Module-level state rather than a controller, because detection_range.py's
fold reaches it from inside a pure function with nothing else in scope - the
same arrangement Negation Emitters has.
"""

from game import aeldari_detachments

FAR_REACHING_DOOM_LABEL = "Far-Reaching Doom"

#: "enemy units have +6 inches detection range".
FAR_REACHING_DOOM_BONUS_IN = 6.0

#: The datasheets the rule names. Read as DATASHEET names rather than as a
#: keyword: RANGERS is a keyword on exactly one datasheet here, but SHROUD
#: RUNNERS is too, and naming both is what the printed text does. A keyword
#: reading would silently widen if a future datasheet took one of them.
FAR_REACHING_DOOM_DATASHEETS = ("Rangers", "Shroud Runners")

#: The config constant game/detachments.py writes for Path of the Outcast.
SETTING = "PATH_OF_THE_OUTCAST_PLAYERS"

#: The owner of the unit currently inside its "selected to shoot" window, or
#: None. One value, not a set: a Shooting phase resolves one activation at a
#: time, and the window closes before the next one opens.
_shooting_owner = None


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def _datasheet_names(squad):
    """The datasheet names behind this unit, including an attached unit's
    components - 19.01 merges a leader in, and the printed text names the
    UNIT."""
    names = []
    sheet = getattr(squad, "datasheet", None)
    if sheet is not None:
        names.append(sheet.name)
    for component in getattr(squad, "attached_components", None) or ():
        sheet = getattr(component, "datasheet", None)
        if sheet is not None:
            names.append(sheet.name)
    return names


def applies(squad):
    """"a friendly RANGERS/SHROUD RUNNERS unit" of a player fielding it."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    return any(name in FAR_REACHING_DOOM_DATASHEETS for name in _datasheet_names(squad))


def begin_shooting(squad):
    """"When a friendly ... unit is SELECTED TO SHOOT" - opens the window."""
    global _shooting_owner
    if applies(squad):
        _shooting_owner = squad.owner
        return True
    return False


def end_shooting(squad=None):
    """"...UNTIL THAT FRIENDLY UNIT HAS SHOT" - closes it.

    Takes the squad only so a caller can be explicit; the window is closed
    unconditionally, because the one it belongs to is the one that is
    finishing. Closing on any activation end is also the safe direction: a
    window that outlived its unit would hand the bonus to the rest of the
    phase."""
    global _shooting_owner
    _shooting_owner = None


def is_open(player=None):
    if player is None:
        return _shooting_owner is not None
    return _shooting_owner == player


def detection_bonus_in(squad):
    """This rule's contribution to game/detection_range.py's fold.

    Named `..._bonus_in` like every other source there. Given to units that are
    ENEMIES of the shooting unit's owner - see the module docstring on why the
    direction and the ownership both matter."""
    if _shooting_owner is None or squad is None:
        return 0.0
    if getattr(squad, "owner", None) == _shooting_owner:
        return 0.0
    return FAR_REACHING_DOOM_BONUS_IN


def reset():
    """For tests and for a fresh battle - module-level state, so it has to be
    clearable by something other than the end of an activation."""
    global _shooting_owner
    _shooting_owner = None
