"""The Lokhust Lord's "Nanoscarab Amulet" wargear.

RULE (printed, word for word):
  "The bearer has the Feel No Pain 5+ ability."

THE BEARER, AND ONLY THE BEARER. That one word is what makes this a per-TOKEN
grant rather than a unit one, and it is the difference from the Technomancer's
Rites of Reanimation next door, which reads "while this model is leading a
unit" and therefore covers every bodyguard. A Lokhust Lord attached to six
Destroyers under 19.01 gives Feel No Pain to exactly himself.

So the flag is set by the Gear item onto the TOKEN (game/factions/necrons.py),
the same arrangement the Overlord's resurrection orb and the Lychguard's
dispersion shield already use, and this module is simply one more fold into
game/feel_no_pain.py's current_feel_no_pain(). That function's own docstring
invites it: "adding a source is one more fold", and the fold keeps the "never
worse than what's printed" guarantee - a model already printing a 4+ is not
dragged down to a 5+ by taking the amulet.
"""

NANOSCARAB_AMULET_FEEL_NO_PAIN = "5+"


def nanoscarab_amulet_feel_no_pain(model):
    """This model's Feel No Pain threshold from a nanoscarab amulet it is
    carrying, or "-" if it has none.

    Returns a threshold STRING, matching UnitProfile.feel_no_pain's own
    convention, so the caller keeps parsing it with parse_threshold()."""
    if model is None:
        return "-"
    return (NANOSCARAB_AMULET_FEEL_NO_PAIN
            if getattr(model, "nanoscarab_amulet", False) else "-")
