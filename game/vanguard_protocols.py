"""The Geomancer's "Vanguard Protocols" (Necrons).

RULE (printed, word for word):
  "If this model is attached to a CANOPTEK MACROCYTES unit during the Declare
   Battle Formations step, this model has the Scouts 8" ability."

A LATCHED CONDITIONAL, unlike game/illuminor.py's Lone Operative: that one
switches on and off as the board moves, this one is decided ONCE at Declare
Battle Formations and then holds for the battle. So it is answered by asking
the ATTACHMENT rather than by measuring anything.

IT IS A MEASURED NO-OP IN THIS ENGINE TODAY, and that is worth saying plainly
rather than discovering later:

  Rule 19.04's reading here is COMPONENT-WISE - attached_units.unit_has_ability()
  reports a unit-wide ability if EVERY model of ANY still-conferring component
  has it. The Canoptek Macrocytes print Scouts 8" themselves, so the merged
  unit has Scouts 8" whether or not the Geomancer does; scouts.scout_distance()
  then takes min() over the models that carry a value, and 8 is the only value
  present either way.

  In tabletop 40k the clause is load-bearing because a unit only has an
  ability if every model has it, so an attached character WITHOUT Scouts would
  strip it from the unit. This engine does not read it that way, and changing
  that reading is a decision about rule 19.04 for every faction - not a side
  effect of one datasheet.

SO WHY BUILD IT AT ALL. Because the predicate is the printed rule and it is
cheap, because the flag makes the clause visible where a reader will look for
it, and because the day 19.04's reading tightens this ability starts working
by itself. The no-op is PINNED in the suite from both sides - the merged unit
has Scouts 8" either way, and a Geomancer attached to Immortals or Necron
Warriors (his other two printed hosts) gets nothing - so it cannot quietly stop
being a no-op without a red line.

THE OTHER TWO HOSTS ARE THE CONTROL. His Support line names CANOPTEK
MACROCYTES, IMMORTALS and NECRON WARRIORS; only the first grants this. A
version that just said "attached to anything" would look identical on a
Macrocytes board and be wrong on the other two.
"""

from game.attached_units import components

VANGUARD_PROTOCOLS_LABEL = "Vanguard Protocols"

#: "this model has the Scouts 8" ability".
VANGUARD_PROTOCOLS_SCOUTS_IN = 8
MACROCYTES_KEYWORD = "MACROCYTES"


def _has_bearer(squad):
    return squad is not None and any(
        getattr(m.profile, "vanguard_protocols", False)
        for m in getattr(squad, "models", ()) or ())


def applies(squad):
    """Whether a Geomancer in THIS unit has Scouts 8" from this rule.

    "ATTACHED TO A CANOPTEK MACROCYTES UNIT" is asked of the unit's own
    COMPONENTS after rule 19.01 has merged them - the provenance attach()
    keeps. A Geomancer standing alone has no components and gets nothing,
    which is what "if this model is ATTACHED" says."""
    if not _has_bearer(squad):
        return False
    parts = components(squad) or ()
    if not parts:
        return False
    for component in parts:
        sheet = getattr(component, "datasheet", None)
        keywords = getattr(sheet, "keywords", None) or ()
        if MACROCYTES_KEYWORD in keywords:
            return True
    return False


def scouts_for(squad):
    """The Scouts distance this rule grants, or None."""
    return VANGUARD_PROTOCOLS_SCOUTS_IN if applies(squad) else None


def apply_at_formations(squad):
    """Stamp the granted ability on the bearer's own model, once, after the
    join has happened.

    Set on the MODEL's profile instance (build_squad() gives every model its
    own), never on the class - a flag written to a shared UnitProfile switches
    it on for every other unit built from that datasheet, which is the trap
    CLAUDE.md records for exactly this shape."""
    if not applies(squad):
        return False
    granted = False
    for model in getattr(squad, "models", ()) or ():
        if getattr(model.profile, "vanguard_protocols", False):
            model.profile.scouts = VANGUARD_PROTOCOLS_SCOUTS_IN
            granted = True
    return granted
