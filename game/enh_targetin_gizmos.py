"""Blitz Brigade Enhancement: Targetin' Gizmos (10 pts, Mecha Orks stage G4).

RULE (verbatim, rules/orks/detachments/Blitz Brigade.md):
  "WAGON unit only. While a BIG MEK model is embarked within this unit:
   - This unit's ranged attacks have [Ignores Cover].
   - If this unit is riled up, this unit's ranged attacks have [Sustained Hits 1]."

THE SAME TWO POINTS AS THE BIG MEK'S MORE DAKKA, so it is the second source of
game/more_dakka.py's grant (the module was written against a predicate for
exactly this): more_dakka.grants_more_dakka() asks applies() below beside the
Big Mek's own ability, and both of [IGNORES COVER]'s readers - the chain and the
cover gate (test_event_chain_wiring.py section 29) - see it through the one
adjusted weapon.

A UNIT-LEVEL Enhancement on a model-less restriction ("WAGON unit only"), like
the T'au "... unit only" ones: every model of the WAGON is marked.

"WHILE A BIG MEK MODEL IS EMBARKED WITHIN THIS UNIT": a living model of a unit
whose embarked_in token belongs to this WAGON, carrying the BIG MEK datasheet
keyword on ITS component (a Big Mek leading Meganobz embarks as one attached
unit, and only the Big Mek is a BIG MEK). The passengers are not a fact the
WAGON knows - the caller hands them in (ShootingController asks main()'s
embarked_squads through its `embarked_squads_provider`); with none handed in the
Enhancement answers "no", which can only under-report.

"THIS UNIT IS RILED UP" is the WAGON's own riled up - game/riled_up.py, asked by
more_dakka at attack time.
"""

from game import attached_units, enhancements

TARGETIN_GIZMOS = "Targetin' Gizmos"


def passengers(squad, embarked_squads):
    """The units embarked within `squad` (a TRANSPORT unit), from the game's
    embarked list."""
    if squad is None:
        return []
    own = set(id(m) for m in getattr(squad, "models", ()) or ())
    return [s for s in embarked_squads or ()
            if id(getattr(s, "embarked_in", None)) in own]


def has_big_mek_aboard(squad, embarked_squads):
    for passenger in passengers(squad, embarked_squads):
        for model in passenger.models:
            if not model.is_dead() and attached_units.model_has_datasheet_keyword(passenger, model, "BIG MEK"):
                return True
    return False


def applies(squad, embarked_squads=()):
    """The WAGON has the Enhancement (and its owner Blitz Brigade), and a BIG MEK
    rides inside it."""
    return (squad is not None and enhancements.is_active(squad, TARGETIN_GIZMOS)
            and has_big_mek_aboard(squad, embarked_squads))
