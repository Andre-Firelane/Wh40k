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
from game import attached_units, montka_aggressive_mobility, montka_pulse_onslaught
from game import battle_focus, elemental_ensnarement, flickerjump, monofilament_web, plagues, whirling_death
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
    # The Tomb Blades' Shieldvanes: "the bearer has a Move characteristic
    # of 8 inches". An OVERRIDE of the printed 12" and a WORSE one, so it
    # replaces the base before anything else folds - a max() here would
    # keep the 12" and hand out the wargear's save for nothing.
    from game import tomb_blade_wargear
    _tb = tomb_blade_wargear.movement_override_in(model)
    if _tb is not None:
        base = _tb
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
    #
    # The Death Guard Plague Scabrous Soulrot ("worsen the Move ... by 1")
    # SUBTRACTS here, and last: it worsens the characteristic this unit
    # actually has, not the printed one, so a Flickerjumping Warp Spider under
    # it moves 23" and not 5". Clamped at 0 - a negative Move would let a
    # clamp_move() budget run backwards.
    total = (base + battle_focus.movement_bonus_in(model)
             + whirling_death.movement_bonus_in(squad)
             - plagues.movement_penalty_in(squad))
    # Mont'ka's Aggressive Mobility (+6") and its Pulse Onslaught's shaken
    # status (-2) ADD TO or SUBTRACT FROM whatever the characteristic has
    # become, so they land on `total` - after every override AND after the
    # other add/subtract terms - which is the same place Swift as the Wind's
    # note above describes. Applied to `base` instead they would be silently
    # discarded, since `total` is already computed from it.
    total += montka_aggressive_mobility.move_bonus_for(squad)
    # Guardian Battlehost's Time to Strike prints Aggressive Mobility's two
    # sentences word for word, so it reads the same two seams - its own flag
    # rather than reusing that one, because the two Stratagems have different
    # names, costs and owners and only happen to share an effect.
    from game import guardian_time_to_strike
    total += guardian_time_to_strike.move_bonus_for(squad)
    total -= montka_pulse_onslaught.move_penalty_for(squad)
    # The Night Spinner's Monofilament Web leaves a unit `pinned`: -2 Move.
    # A SEPARATE status from `shaken` above, and they STACK - two printed
    # effects on one unit - which is why this is its own term rather than a
    # second writer of the same flag. See game/monofilament_web.py.
    total -= monofilament_web.move_penalty_for(squad)
    # The Stonesinger's Elemental Ensnarement leaves a unit `ensnared`: -2
    # Move. The THIRD movement status, and its own term for the same reason -
    # ensnared and shaken can hold at once and both apply. It cannot stack
    # with `pinned` though, because an ensnared unit cannot BECOME pinned.
    total -= elemental_ensnarement.move_penalty_for(squad)
    return max(0.0, total)


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
    # Four independent grants now, and the RANGED gate above is right for all
    # of them: Star Engines, Skilled Crews and Sudden Storm all say "ranged".
    #
    # Skilled Crews HAS to be read here and not only in the adjuster chain.
    # [ASSAULT] is what lets a unit shoot after Advancing (24.04), and that is
    # decided by this function, not by the damage maths - a grant that reached
    # only the chain would look wired while failing to do the one thing the
    # detachment is bought for.
    #
    # Protocol of the Sudden Storm is the fourth grant, and it is here because
    # that warning came true: it reached only the adjuster chain, so a Necron
    # unit that bought the Stratagem, Advanced, and then could not shoot -
    # which is the ONE thing 1 CP was paid for - reported by a player
    # ("ich konnte nach dem vorruecken nicht mehr schiessen mit den necron
    # kriegern"). available_shooting_types() asks THIS function whether an
    # Advanced unit still has an Assault option, and it never saw the flag.
    #
    # Mortarion's Teachings is the fifth, found by the same probe in the same
    # session and broken the same way - its OWN docstring says "[ASSAULT]
    # (10.05) lets a unit that Advanced still shoot", which is exactly what it
    # could not do.
    #
    # Mont'ka's Killing Blow is the SIXTH, and it was named here as a "known
    # gap" for exactly as long as the claim "no shipped army list fields
    # Mont'ka" was true. That stopped being true when the tau_montka roster was
    # added, and the comment outlived the fact - which is the failure mode a
    # NAMED gap has and a set difference does not. Measured on that roster in
    # rounds 1-3 before the fix: Killing Blow is active for all 14 of its units
    # and grants [ASSAULT] to 102 of their 151 ranged weapons, of which this
    # gate could see NONE. Three of those units were offered no shooting type
    # at all after Advancing.
    #
    # It reads a FLAG rather than its own condition, unlike the four above: the
    # rule is gated on the battle round and this function is handed only
    # (weapon, squad), so montka.refresh_killing_blow() stamps
    # Squad.montka_killing_blow once per phase change from the same is_active()
    # the adjuster chain uses. One condition, two read paths - not two
    # conditions. See game/montka.py.
    #
    # Imported inside the function: game/coldstar.py is reached very early
    # from game/squad.py's own import, and game/skilled_crews.py pulls
    # game.factions through aeldari_detachments (protocol_sudden_storm reaches
    # it too, via game/awakened_dynasty.py).
    from game import (dlc_mortarions_teachings, montka, protocol_sudden_storm,
                      skilled_crews)
    return (squad_has_coldstar_commander(squad) or battle_focus.grants_assault(squad)
            or skilled_crews.applies(squad) or protocol_sudden_storm.is_active(squad)
            or dlc_mortarions_teachings.is_active(squad)
            or montka.grants_assault(squad))
