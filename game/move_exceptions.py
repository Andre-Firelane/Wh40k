"""The exceptions to rule 09.06 and 09.07 - who may still shoot or charge
after Advancing or Falling Back.

WHY THIS MODULE EXISTS
----------------------
Two rules ban something, and both bans have grown a hard-coded list of
exceptions written inline at the point of use:

  * rule 09.07's "a unit that Fell Back cannot SHOOT" - game/shooting.py's
    available_shooting_types(), a FIVE-source `and not` chain.
  * rule 09.07's "...and cannot CHARGE" - game/charge.py's
    can_declare_charge(), a two-source chain naming a DIFFERENT pair.
  * rule 09.06's "a unit that Advanced cannot charge" - the same method's
    `advance_ok` fold, four sources.

Three lists, in two files, for two rules, and no two of them agree about who is
on them. That is precisely the shape CLAUDE.md records burning this repo twice:
MovementController.REACTIVE_MOVE_MODES (a set written as one string, so the
second ability that needed it was walked over) and the `battle_focus` string
compare behind it. The Aeldari detachment Stratagems bring three more
consumers - Vectored Engines, Feigned Retreat and Wind of Blades - which is the
second-consumer trigger three times over.

WHAT IS SHARED AND WHAT IS NOT. The exceptions are not interchangeable, and
this module does NOT flatten them:

  * some abilities lift the SHOOTING ban only (Battlesuit Support System, War
    Construct, Agile Combatant),
  * some lift BOTH halves of 09.07 (Hovering Death, Full Throttle),
  * some lift only 09.06's CHARGE ban (Waaagh!, Loping Pounce, Alien
    Expertise).

So there are three questions here, not one, and each keeps its own source list.
What they share is that each is a SET rather than a hard-coded name, and that a
new source registers in one place instead of being appended to a chain in
whichever file happened to need it first.

LATCHED VERSUS LIVE is deliberately not this module's business. Some sources
read a flag set earlier in the turn (Loping Pounce, Alien Expertise), some
measure the board right now (Waaagh!). Each predicate answers for itself; the
folds below only ask.
"""

from game import aux_alien_expertise, hovering_death, loping_pounce
from game.relentless_combatants import squad_has_relentless_combatants
from game.squad import (squad_has_agile_combatant, squad_has_battlesuit_support_system,
                        squad_has_full_throttle, squad_has_war_construct)
from game.waaagh import squad_waaagh_active


def _flag(squad, name):
    """A per-squad latch set by a Stratagem. Stratagem-granted exceptions are
    plain attributes on the Squad, the way every other one-turn grant in this
    engine is."""
    return bool(getattr(squad, name, False))


#: Stratagem latches that lift rule 09.07's SHOOTING ban. Registered here
#: rather than appended to game/shooting.py's chain, which is the whole point.
SHOOT_AFTER_FALL_BACK_FLAGS = (
    "vectored_engines_active",      # Armoured Warhost
    "feigned_retreat_active",       # Warhost - lifts both halves, see below
    "wind_of_blades_active",        # Windrider Host - lifts both halves
)

#: Latches that lift rule 09.07's CHARGE ban.
CHARGE_AFTER_FALL_BACK_FLAGS = (
    "feigned_retreat_active",
    "wind_of_blades_active",
)

#: Latches that lift rule 09.06's "Advanced, so cannot charge".
CHARGE_AFTER_ADVANCE_FLAGS = (
    "time_to_strike_active",        # Guardian Battlehost
    "wind_of_blades_active",
)

#: Latches that let a unit SHOOT in a turn in which it Advanced.
#:
#: The fourth question here, and the only one with no datasheet source at all -
#: [ASSAULT] is how a WEAPON gets to fire after an Advance (24.04), and that is
#: a property of the weapon rather than of the unit. These two Stratagems say
#: "your unit is eligible to shoot ... in a turn in which it Advanced", which
#: is about the UNIT and applies to every gun it carries, so it cannot be
#: expressed as a keyword grant without silently widening what [ASSAULT] means.
SHOOT_AFTER_ADVANCE_FLAGS = (
    "time_to_strike_active",        # Guardian Battlehost
    "wind_of_blades_active",        # Windrider Host
)


def may_shoot_after_falling_back(squad):
    """Rule 09.07's shooting ban - is this unit exempt?

    The four datasheet sources are three different printed wordings of one
    sentence ("this unit is eligible to shoot in a turn in which it Fell
    Back"), which is why they were already asked at one gate."""
    if squad is None:
        return False
    return (squad_has_battlesuit_support_system(squad)
            or hovering_death.squad_ignores_fall_back(squad)
            or squad_has_war_construct(squad)
            or squad_has_agile_combatant(squad)
            or any(_flag(squad, name) for name in SHOOT_AFTER_FALL_BACK_FLAGS))


def may_charge_after_falling_back(squad):
    """Rule 09.07's charge ban - a SHORTER list than the shooting one, and
    that difference is printed: Battlesuit Support System and Agile Combatant
    say "shoot", Hovering Death and Full Throttle say both, and the Triarch
    Praetorians' Relentless Combatants says only "declare a charge" (its other
    clause is a Charge-roll re-roll, which is a different question entirely -
    see game/relentless_combatants.py)."""
    if squad is None:
        return False
    return (squad_has_full_throttle(squad)
            or hovering_death.squad_ignores_fall_back(squad)
            or squad_has_relentless_combatants(squad)
            or any(_flag(squad, name) for name in CHARGE_AFTER_FALL_BACK_FLAGS))


def may_shoot_after_advancing(squad):
    """Rule 09.06's shooting ban - is this unit exempt?

    No datasheet source: a unit that Advanced normally shoots only with an
    [ASSAULT] weapon, which is answered per WEAPON by
    game/coldstar.py's weapon_has_assault(). These two Stratagems exempt the
    whole UNIT, so they are asked here instead of pretending every gun gained
    a keyword."""
    if squad is None:
        return False
    return any(_flag(squad, name) for name in SHOOT_AFTER_ADVANCE_FLAGS)


def may_charge_after_advancing(squad, waaagh=None):
    """Rule 09.06's ban on charging after an Advance.

    `waaagh` is passed in because the Orks army rule is a live per-player
    state rather than anything on the squad - the same argument every other
    reader of it takes."""
    if squad is None:
        return False
    return (squad_has_full_throttle(squad)
            or squad_waaagh_active(squad, waaagh)
            or loping_pounce.is_active(squad)
            or aux_alien_expertise.is_active(squad)
            or any(_flag(squad, name) for name in CHARGE_AFTER_ADVANCE_FLAGS))


def clear_turn_flags(squads=()):
    """Every latch here is "until the end of the turn"."""
    for squad in squads or ():
        if squad is None:
            continue
        for name in set(SHOOT_AFTER_FALL_BACK_FLAGS + CHARGE_AFTER_FALL_BACK_FLAGS
                        + CHARGE_AFTER_ADVANCE_FLAGS + SHOOT_AFTER_ADVANCE_FLAGS):
            setattr(squad, name, False)
