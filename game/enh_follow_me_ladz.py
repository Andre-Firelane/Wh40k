"""War Horde Enhancement: Follow Me Ladz (20 pts).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  "ORKS model only. This unit has +2" M."

It ADDS to whatever the Move characteristic has become, so it is a term on
game/coldstar.py's `total` - beside Swift as the Wind and Relentless March -
never on the base an override would discard. "This UNIT", while the bearer
lives (rule 19.04).

effective_movement_in() is on the movement search's hot path, so the War Horde
gate - one config lookup - is asked before the bearer sweep: every army that
does not field War Horde pays nothing more than that.
"""

from game import enhancements, war_horde

FOLLOW_ME_LADZ = "Follow Me Ladz"
#: "+2\" M".
FOLLOW_ME_LADZ_BONUS_IN = 2.0


def move_bonus_for(squad):
    if squad is None or not war_horde.fields_war_horde(getattr(squad, "owner", None)):
        return 0.0
    if not enhancements.is_active(squad, FOLLOW_ME_LADZ):
        return 0.0
    return FOLLOW_ME_LADZ_BONUS_IN
