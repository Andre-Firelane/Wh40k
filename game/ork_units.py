"""The two Ork unit predicates every Ork detachment asks: "a friendly ORKS unit"
and "a friendly ORKS INFANTRY unit".

WHY THIS EXISTS. game/war_horde.py wrote is_orks_unit() when War Horde was the
only Ork detachment; Green Tide (Mecha Orks G3) wrote the same function again
beside is_orks_infantry_unit(), and Blitz Brigade (G4) asks both. An Ork rule
importing them from another DETACHMENT's module would carry a lying name (error
class 11), so they live here and both detachment modules re-export them - none
of their call sites move.

"ORKS" is read off the models' `orks` flag, which every Ork UnitProfile sets:
there is no per-model faction keyword to read instead (the gap UnitProfile.orks'
own note records). Both predicates are rule 19.03's any-model reading - an
attached unit has all of its components' keywords.
"""

from game import attached_units


def is_orks_unit(squad):
    """"Friendly ORKS unit"."""
    return bool(squad is not None and any(
        getattr(m.profile, "orks", False) for m in getattr(squad, "models", ()) or ()))


def is_orks_infantry_unit(squad):
    """"ORKS INFANTRY unit", both keywords pooled over the components (19.03)."""
    return is_orks_unit(squad) and attached_units.unit_has_keyword(
        squad, lambda m: getattr(m.profile, "infantry", False))
