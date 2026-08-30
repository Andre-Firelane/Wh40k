"""T'au Empire detachment rule: Advanced Acquisition Cadre's Expert Fieldcraft.

RULE (verbatim, rules/tau_empire/detachments/Advanced Acquisition Cadre.md):
  In your Shooting phase, when a friendly PATHFINDER TEAM/STEALTH BATTLESUITS
  unit is selected to shoot, those ranged attacks do not prevent your unit from
  being hidden.

IT IS A HOLE IN ONE PIECE OF BOOKKEEPING, NOT A NEW STATE
----------------------------------------------------------
Hidden (rule 13.09) is decided by status_effects.is_hidden(), which asks
`last_ranged_attack_turn` when this unit last shot. There is exactly one place
that writes that dict - ShootingController._note_ranged_attack() - and this
rule is simply "do not write it for these units". No new flag, no second
record of the same fact.

That one funnel matters: it has TWO callers, the normal end of an activation
and cancel()'s abandon-and-move-on path. Its own docstring records the bug that
taught the codebase this - cancel() used to skip the bookkeeping, so "fire the
main gun, skip the pistol, click Next Phase" left a unit Hidden forever. A rule
that suppressed the write at only one of the two would have reproduced exactly
half of that bug.

"IN YOUR SHOOTING PHASE" EXCLUDES REACTIVE FIRE
-----------------------------------------------
A Fire Overwatch / Snap Shooting activation (15.08/15.09) happens in the
OPPONENT'S turn, so it is not "your Shooting phase" and this rule does not
cover it - such a shot still strips Hidden. game/shooting.py already tracks
exactly this distinction as `_reactive`, and notes at the call site that a
reactive activation still updates last_ranged_attack_turn "since it genuinely
was a ranged attack". The flag is passed in rather than read here, so the
reading lives with the rule and the mechanism stays in the controller.

WHICH UNITS: "STEALTH BATTLESUITS" IS READ AS THE STEALTH KEYWORD
------------------------------------------------------------------
The printed text names a datasheet; this engine matches on datasheet KEYWORDS
(game/attached_units.py's unit_has_datasheet_keyword, rule 19.03). Measured
across the faction, STEALTH is carried by exactly one datasheet - Stealth
Battlesuits - so the keyword and the named datasheet are the same set, and
matching the keyword additionally gets 19.03 pooling right for free. PATHFINDER
TEAM is printed as a keyword outright.
"""

from game import tau_detachments
from game.attached_units import unit_has_datasheet_keyword

SETTING = "ADVANCED_ACQUISITION_CADRE_PLAYERS"
LABEL = "Expert Fieldcraft"
# The datasheet keywords the printed text names. See the docstring on why
# STEALTH stands in for "STEALTH BATTLESUITS".
FIELDCRAFT_KEYWORDS = ("PATHFINDER TEAM", "STEALTH")


def is_fieldcraft_unit(squad):
    """"a friendly PATHFINDER TEAM/STEALTH BATTLESUITS unit"."""
    if squad is None:
        return False
    return any(unit_has_datasheet_keyword(squad, keyword)
               for keyword in FIELDCRAFT_KEYWORDS)


def shooting_keeps_hidden(squad, reactive=False):
    """Whether this unit's shooting should leave its Hidden status alone.

    `reactive` is game/shooting.py's own flag for a Fire Overwatch / Snap
    Shooting activation - see the module docstring on why those are excluded.
    """
    if reactive or squad is None:
        return False
    if not tau_detachments.has_detachment(getattr(squad, "owner", None), SETTING):
        return False
    if not tau_detachments.is_tau_unit(squad):
        return False
    return is_fieldcraft_unit(squad)
