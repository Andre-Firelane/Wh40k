"""One question, one answer: should dragging a unit move the WHOLE unit?

Twenty-fifth extraction, and this one merges two flags rather than splitting a
shared one out. Until now the same preference existed twice:

  * SetupController.block_placement_enabled - during a Set Up (03.02: reserves
    arriving, disembarking, deployment) the unit is laid out as a block on the
    drop point and a drag translates the whole block;
  * MovementController.group_move_enabled - during a move (09.02) a drag
    rigidly translates the whole squad instead of one model.

They had separate toggles, separate defaults (True and False) and separate
history, and the user retired the distinction: "ich glaube, dass man Block
Deployment und Block Movement zusammenfassen kann. Mir faellt keine Situation
ein, wo man das getrennt braeuchte." Correct - both answer "do I want to handle
this unit model by model, or as one piece", and a player who wants one wants the
other.

WHY A MODULE AND NOT A FLAG ON ONE OF THE CONTROLLERS: neither owns the
question, and pointing either one at the other would make Set Up depend on
Movement or the reverse for a preference that is about neither. Both keep their
own named attribute, as PROPERTIES onto the single value here, so all fourteen
existing read sites and every test that assigns to them are unchanged - and
there is still exactly one place the state lives (this repo's error class 10:
two places answering one question is the commonest source of silent drift).

DEFAULT ON: it is the default the half the user actually asked for has always
had ("ich will oft nicht jedes modell einzeln anfassen beim platzieren"), and
merging has to pick one. Movement's old default was Off, so a merged On does
change movement drags - deliberately, and visibly: the toolbar switch is now
green/grey with a sliding knob, so an unwanted On is one glance and one click
away rather than something to discover.

NOT reset anywhere - not per placement, per move, per squad, per turn or per
battle. That is the whole point of a session preference ("die toggles sollen
global gelten... bleibt er fuer alle squads an, bis ich ihn ausschalte"), and
the flags this replaces each had to have their own per-move reset removed
before they behaved as advertised.
"""

# The single value. Module-level because it is one session preference for the
# whole app, in the same spirit as config.BIOME being written live by the map
# screen - not per-controller, per-game or per-squad state.
_enabled = True


def is_enabled():
    """Whether a drag should carry the whole unit."""
    return _enabled


def set_enabled(value):
    global _enabled
    _enabled = bool(value)


def toggle():
    """Flip it. Deliberately unguarded and callable at any time (a
    quality-of-life preference, not a rule): it takes effect on the next
    placement or drag, and never rearranges one already in progress, since
    that would throw away adjustments the player made by hand."""
    global _enabled
    _enabled = not _enabled
    return _enabled
