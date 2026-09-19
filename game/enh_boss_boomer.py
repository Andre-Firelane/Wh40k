"""Blitz Brigade Enhancement: Boss Boomer (10 pts, Mecha Orks stage G4).

RULE (verbatim, rules/orks/detachments/Blitz Brigade.md):
  "WAGON unit only. While a WARBOSS model is embarked within this unit, this
   unit has that WARBOSS model's Intimidating Motivation/Keep Huntin' ability."

THE WAGON BECOMES A BEARER. game/boss_motivation.py's controllers find their
bearer through bearer_models(squad); that method asks lent_models() below beside
the unit's own models, so a WAGON carrying a Warboss (or a Warboss in Mega
Armour) has Intimidating Motivation, and one carrying a Beastboss has Keep
Huntin'! - "that WARBOSS model's" ability, so a WARBOSS without either (Ghazghkull
prints neither) lends nothing. Everything else is the ability's own: "at the start
or end of THIS unit's move" is the WAGON's move, "within 6" of THIS unit" is
measured from the WAGON, and the once-per-battle-round-per-army limit is the one
per ability the Warboss himself would spend.

The passengers come from the controller's squads_provider, which is every unit
in the game wherever it is - embarked ones included.

A UNIT-LEVEL Enhancement ("WAGON unit only"), like Targetin' Gizmos.
"""

from game import attached_units, enhancements

BOSS_BOOMER = "Boss Boomer"


def lent_models(squad, all_squads, flag):
    """The living WARBOSS models embarked within `squad` that print the ability
    `flag` (a UnitProfile field), while `squad` has Boss Boomer. [] otherwise."""
    if squad is None or not enhancements.is_active(squad, BOSS_BOOMER):
        return []
    own = set(id(m) for m in getattr(squad, "models", ()) or ())
    out = []
    for passenger in all_squads or ():
        if id(getattr(passenger, "embarked_in", None)) not in own:
            continue
        for model in passenger.models:
            if model.is_dead() or not getattr(model.profile, flag, False):
                continue
            if attached_units.model_has_datasheet_keyword(passenger, model, "WARBOSS"):
                out.append(model)
    return out
