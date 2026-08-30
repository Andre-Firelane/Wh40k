"""The Autarch's "Aspect Training" - a datasheet ability.

RULE (printed, word for word):
  "While this model is leading a HOWLING BANSHEES unit, it has the Fights First
   ability.
   While this model is leading a STRIKING SCORPIONS unit, it has the
   Infiltrators, Scouts 7" and Stealth abilities."

FOUR CORE ABILITIES, GRANTED CONDITIONALLY, AND ALL FOUR ALREADY EXIST
-----------------------------------------------------------------------
Fights First (24.13), Infiltrators (24.20), Scouts (24.31/24.32) and Stealth
(24.33) are all implemented; what is new is only that this model has them
sometimes. So this module grants nothing itself - it answers "which of them
does the Autarch have right now", and the four existing questions ask it.

WHAT THIS ABILITY IS FOR, AND WHY IT IS ALMOST INERT HERE
---------------------------------------------------------
In the printed game its job is DEFENSIVE. Fights First, Infiltrators, Scouts
and Stealth all apply only "while EVERY model in a unit has this ability", so
an Autarch joining Striking Scorpions would otherwise BREAK the Infiltrators
and Stealth the squad already had. Aspect Training gives him the same abilities
so that he does not.

This engine already prevents that breakage generically. game/attached_units.py's
unit_has_ability() implements 19.04 as "every model of ANY still-conferring
component", so the bodyguard component keeps conferring its own abilities and a
joining character can never strip them - the note in game/squad.py's
unit_wide_ability() calls that "the single most likely way attaching a leader
goes wrong" and fixes it for every leader at once.

So ALL FOUR grants change nothing measurable here, and that is measured rather
than assumed - the first draft of this note claimed the Striking Scorpions do
not print Scouts, and their datasheet says otherwise:

  * Fights First   - the Howling Banshees print it themselves.
  * Infiltrators   - the Striking Scorpions print it themselves.
  * Scouts 7"      - so do they. CORE: "Infiltrators, Scouts 7\", Stealth".
  * Stealth        - likewise.

All four are therefore BELIEVED NO-OPS, kept as predicates so that the day
19.04's reading tightens - or an Autarch gains a LEADER line to a unit that
does NOT print these - this is one wiring change rather than a re-reading of
the printed text. The test measures the emptiness from both sides: the
predicates fire, and the units keep their abilities either way.

WHAT IS DELIBERATELY NOT DONE: granting the Autarch's Scouts to the whole
attached unit. "IT has" names the MODEL, and rule 24.31 needs every model, so
the narrow reading grants him a value his unit reads through its own models
anyway. The wider reading - that 19.04 propagates it the way it propagates
every other leader ability - is defensible and named here rather than left to
be rediscovered; it would mean teaching game/scouts.py's scout_distance() to
ask grants_scouts_in(), and nothing else. The narrow one cannot invent a
pre-battle move, which is the safe direction.

WHICH UNIT IS BEING LED is read off the attached components (19.01 keeps each
one's datasheet), not off the merged squad's name - the same source
game/attached_units.py's own keyword questions use.
"""
from game import attached_units

ASPECT_TRAINING_LABEL = "Aspect Training"

#: The printed Scouts distance for the Striking Scorpions half.
ASPECT_TRAINING_SCOUTS_IN = 7.0

BANSHEES_DATASHEET = "Howling Banshees"
SCORPIONS_DATASHEET = "Striking Scorpions"


def _has_ability(squad):
    return any(getattr(m.profile, "aspect_training", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def _led_datasheet_names(squad):
    """Which datasheets make up this attached unit, from the recorded
    components - the same place 19.01 keeps them."""
    names = set()
    for component in getattr(squad, "attached_components", ()) or ():
        datasheet = getattr(component, "datasheet", None)
        name = getattr(datasheet, "name", None)
        if name:
            names.add(name)
    if not names:
        datasheet = getattr(squad, "datasheet", None)
        if getattr(datasheet, "name", None):
            names.add(datasheet.name)
    return names


def leads_banshees(squad):
    return _has_ability(squad) and BANSHEES_DATASHEET in _led_datasheet_names(squad)


def leads_scorpions(squad):
    return _has_ability(squad) and SCORPIONS_DATASHEET in _led_datasheet_names(squad)


def grants_fights_first(squad):
    """"While this model is leading a HOWLING BANSHEES unit, it has Fights
    First." The Banshees print it themselves, so this changes nothing today -
    a BELIEVED NO-OP, written out rather than dropped so that it is one
    predicate on the day an Autarch can lead something that does not."""
    return leads_banshees(squad)


def grants_infiltrators(squad):
    return leads_scorpions(squad)


def grants_stealth(squad):
    return leads_scorpions(squad)


def grants_scouts_in(squad):
    """The Scouts half. Like its three siblings this is a believed no-op - the
    Striking Scorpions print Scouts 7" themselves - and it is deliberately not
    granted unit-wide; see the module docstring."""
    return ASPECT_TRAINING_SCOUTS_IN if leads_scorpions(squad) else None
