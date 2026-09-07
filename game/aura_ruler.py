"""The range ruler: a circle of a chosen radius around the selected unit.

User: "es gibt einen Aura toggle. wenn man den aktiviert erscheinen weitere
knoepfe die wie Radio Buttons funktionieren. 3" 6" 9" 12" 15" 18" 24" 36". wenn
man einen dieser knoepfe aktiviert, dann wird bei angewaehlten modellen die
entsprechende Aura subtil angezeigt. optisch wie die deathguard Aura, aber in
weiss. das hilft bei Reichweiten."

WHAT IT IS FOR. Almost every question in this game is "is that within X of
this?" - weapon range, an aura's reach, 3" to an objective, 9" for a deep
strike. The ALT ruler answers it for ONE pair of points; this answers it for a
whole unit at once, and stays up while you look around.

TWO CONTROLS, and that is the whole model:

  * a TOGGLE - is the ruler on at all;
  * a RADIO of eight radii - which one.

A radio, so exactly one radius is live at a time: two overlapping white rings
would say less than one, since the whole point is reading a single distance off
the board. The toggle is what turns it off, not "click the active radius
again" - the user asked for those as two separate controls, and a radio button
that also un-selects itself is the kind of thing you discover by accident.

`active_radius()` is the ONE question anything drawing should ask. Keeping the
toggle and the radius as two values but only ever ANSWERING with their
combination is what stops the renderer and the panel from disagreeing about
whether something should be on screen.

MODULE-LEVEL, like game/whole_unit_drag.py next door and for the same reason:
this is one session preference for the whole application, not per-controller,
per-battle or per-squad state. It is deliberately NOT reset between battles -
a player who wants a 9" ring wants it in the next game too.
"""

# The eight the user named, in the order they asked for them - which is also
# ascending, so the row reads as a scale.
RADII_IN = (3, 6, 9, 12, 15, 18, 24, 36)

# What the radio opens on. Not "nothing selected": a radio with no selection
# would make the toggle do nothing on its first press, and the toggle is the
# control that is supposed to answer "on or off". 6" is the middle of the
# common half - Engagement Range plus a move, most pistols, most auras.
DEFAULT_RADIUS_IN = 6

_enabled = False
_radius_in = DEFAULT_RADIUS_IN


def is_enabled():
    return _enabled


def set_enabled(value):
    global _enabled
    _enabled = bool(value)
    return _enabled


def toggle():
    """Flip the ruler on or off. Leaves the chosen radius alone, so turning it
    back on returns to the distance you were last reading."""
    global _enabled
    _enabled = not _enabled
    return _enabled


def radius_in():
    """The chosen radius, whether or not the ruler is on."""
    return _radius_in


def set_radius(value):
    """Pick one of RADII_IN. An unknown value is refused rather than stored:
    the radio's buttons ARE the list, so anything else is a caller bug, and a
    silently accepted 7" would draw a circle no button could explain."""
    global _radius_in
    if value not in RADII_IN:
        return False
    _radius_in = value
    return True


def active_radius():
    """The radius to draw right now, or None.

    The one question the renderer and the panel both ask, so they cannot come
    to different conclusions about whether the ruler is showing."""
    return _radius_in if _enabled else None
