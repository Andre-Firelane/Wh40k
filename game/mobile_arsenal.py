"""The Gunwagon's Mobile Arsenal (2026-09 Ork codex, Mecha Orks stage G1).

RULE (verbatim, rules/orks/Gunwagon.md):
  "Mobile Arsenal: In your Shooting phase, this unit's ranged attacks can re-roll
   hit rolls of 1."

A PLAIN automatic re-roll of 1s - no "re-roll the Hit roll instead" - so it joins
ShootingController._hit_step()'s automatic_ones disjunction beside Hard-wired for
Destruction and Swift Demise, and NOT game/reroll_scope.py, which drives a
failures-or-whole offer this text never gives. A 1 always misses, so throwing it
again can never cost the attacker a hit.

"IN YOUR SHOOTING PHASE": a reactive activation (Fire Overwatch in the
opponent's turn) is not the unit's own Shooting phase, so it gains nothing - the
same `reactive` flag Finderz Keeperz reads for its identical clause.

"THIS UNIT" is read component-wise (rule 19.04) through unit_wide_ability(). A
Gunwagon is a one-model unit and never attached, so that is the ordinary
all-models reading in practice.
"""

from game.squad import unit_wide_ability

MOBILE_ARSENAL_LABEL = "Mobile Arsenal"


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "mobile_arsenal"))


def applies(squad, reactive=False):
    """Whether `squad`'s ranged Hit roll re-rolls its 1s right now."""
    return not reactive and has_ability(squad)
