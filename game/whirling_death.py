"""Jain Zar's "Whirling Death" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "While this model is leading a unit, each time that unit Advances, do not
  make an Advance roll. Instead, until the end of the phase, add 6" to the Move
  characteristic of models in that unit and each time a model in that unit
  makes an Advance move, ignore any vertical distance when determining the
  total distance that model can be moved during that move."

THE ADVANCE STOPS BEING A DICE ROLL
-----------------------------------
Every Advance in this engine goes through MovementController.start_run(), which
rolls a D6 and adds the result. This ability replaces that with a flat +6",
which is a bigger change than it looks: the roll is not just replaced by a
fixed number, it does not HAPPEN. That matters downstream - rule 15.02's
Command Re-roll has nothing to re-roll, and MovementController's own
_pending_advance correction (which exists to fix up a Command Re-roll of the
Advance die) is skipped rather than left pointing at a die that was never
thrown.

The +6" is written as a Move characteristic change rather than as a one-off
addition to the remaining range, because that is what the rule says and it is
what game/coldstar.py's effective_movement_in() already composes: the Coldstar
override, Flickerjump's override, Battle Focus's Swift as the Wind bonus and
now this one all meet in that single function.

THE VERTICAL CLAUSE IS A NO-OP HERE, and deliberately so rather than by
oversight: this engine models no height at all (see CLAUDE.md's Spaeter-Liste,
which is also why rule 22.05's Plunging Fire does not exist). "Ignore any
vertical distance" therefore describes something that is already true of every
move in this game.

WHILE THIS MODEL IS LEADING A UNIT (19.01): read off the attached unit's own
components, so a lone Jain Zar - who leads nobody - grants nothing, and the
ability ends with her.
"""

from game import attached_units

WHIRLING_DEATH_MOVE_BONUS_IN = 6


def unit_has_jain_zar(squad):
    """Whether this unit is being LED by a model with the ability.

    attached_units.leader_ability() is the 19.04-correct lookup: it needs a
    real attached unit (a lone character leads nobody), reads the ability off
    the leader COMPONENT so it ends when she dies, and brings 19.04's grace
    window with it. unit_wide_ability() would be permanently false here - no
    Howling Banshee prints this."""
    return attached_units.leader_ability(squad, "whirling_death")


def movement_bonus_in(squad):
    """The Move characteristic increase, once the unit has Advanced this
    phase. Read by game/coldstar.py's effective_movement_in().

    Gated on having actually Advanced, not merely on being led: the rule reads
    "each time that unit Advances ... Instead, until the end of the phase, add
    6 inches", so the bonus is what the Advance BUYS, not something the unit
    carries around."""
    if squad is not None and getattr(squad, "whirling_death_active", False):
        return WHIRLING_DEATH_MOVE_BONUS_IN
    return 0


def begin_advance(squad):
    """Called by MovementController.start_run() in place of the D6.

    Returns the flat distance to add to the unit's remaining range, and arms
    the Move characteristic increase for the rest of the phase."""
    squad.whirling_death_active = True
    return WHIRLING_DEATH_MOVE_BONUS_IN


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads:
        squad.whirling_death_active = False
