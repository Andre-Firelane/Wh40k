"""T'au Empire datasheet ability: the Commander in Coldstar Battlesuit's own
"Coldstar Commander" ability, as supplied by the user (not a core rulebook
rule):

    "While this model is leading a unit, models in that unit have a Move
     characteristic of 12" and ranged weapons equipped by models in that unit
     have the [ASSAULT] ability."

Two effects, both conferred on the whole attached unit (19.01) by one model,
so both read the squad rather than the model's own profile - see
game/attached_units.py's leader_ability() for why unit_wide_ability() is the
wrong tool for this shape of ability.

Deferred, like Cadre Fireblade's Volley Fire and Warboss's Might is Right,
while there was no way to form an attached unit at all - and, like them, not
picked up again once that arrived. This engine's demo scene attaches a Coldstar
Commander to a Crisis Starscythe squad, so both halves were silently missing
from a unit on the board: it moved 8" instead of 12", and could not shoot at
all after Advancing.

Imports only game/attached_units.py (which has no imports of its own),
game/battle_focus.py (which imports only game/config.py) and the RANGED
constant, so game/squad.py can depend on this module for
effective_movement_in() without a cycle.

Naming debt, stated rather than paid: effective_movement_in() and
weapon_has_assault() are no longer only about the Coldstar Commander - the
Aeldari army rule's Swift as the Wind and Star Engines (game/battle_focus.py)
fold in here too, because these two functions are where the engine ASKS those
questions, and a second answer somewhere else is how two sources of truth
start. Both should move to a neutrally named module the moment a third source
turns up; that was not done for a two-line addition because they have eight
call sites across five files, including the AI movement code, which is the
single most regression-prone area in this repo. The Aeldari logic itself lives
in battle_focus.py, so only the composition is here.
"""
from game import attached_units
from game import battle_focus, flickerjump, whirling_death
from game.weapons import RANGED

COLDSTAR_MOVEMENT_IN = 12.0


def squad_has_coldstar_commander(squad):
    """Is a Coldstar Commander currently LEADING this unit?"""
    return attached_units.leader_ability(squad, "coldstar_commander")


def effective_movement_in(model):
    """This model's Move characteristic, after the ability.

    A flat override, not a bonus and not a floor: the wording is "models in
    that unit HAVE a Move characteristic of 12\"". For every unit the ability
    can currently reach that is an increase anyway (Crisis Battlesuits move
    8"), and the Commander himself already moves 12" - so the override and a
    max() cannot be told apart today. Written the way the rule reads, and
    noted here because a future 14" bodyguard would be the case that
    distinguishes them.

    The Aeldari Battle Focus manoeuvre Swift as the Wind then ADDS to whatever
    the characteristic is, override included ("add 2 inches to the Move
    characteristic"), so it lands after this and not instead of it."""
    squad = getattr(model, "squad", None)
    base = model.profile.movement_in
    if squad is not None and squad_has_coldstar_commander(squad):
        base = COLDSTAR_MOVEMENT_IN
    # Warp Spiders' Flickerjump is a second override of the same shape. The two
    # can never both apply (one is T'au, one is Aeldari), so max() rather than a
    # precedence rule: whichever one is active simply wins, and if a future
    # datasheet did carry both, the better characteristic is the safe reading.
    flicker = flickerjump.movement_override_in(squad)
    if flicker is not None:
        base = max(base, flicker)
    # Jain Zar's Whirling Death adds its 6" the same way Swift as the Wind
    # adds its 2": on top of whichever override won, per unit rather than
    # per model.
    return base + battle_focus.movement_bonus_in(model) + whirling_death.movement_bonus_in(squad)


def weapon_has_assault(weapon, squad):
    """Does this weapon have [ASSAULT] (24.03) - printed, or granted by the
    ability?

    Gated on RANGED even though both call sites in game/shooting.py only ever
    hold ranged weapons: the ability says "RANGED weapons equipped by models
    in that unit", and [ASSAULT] on a melee weapon would be meaningless in a
    way that is easier to prevent here than to notice later."""
    if weapon.assault:
        return True
    if getattr(weapon, "weapon_type", None) != RANGED:
        return False
    if squad is None:
        return False
    # Two independent grants, and the RANGED gate above is right for both:
    # Star Engines also says "Ranged weapons equipped by this unit".
    return squad_has_coldstar_commander(squad) or battle_focus.grants_assault(squad)
