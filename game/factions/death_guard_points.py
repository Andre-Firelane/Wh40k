"""Munitorum points for the DEATH GUARD datasheets this engine builds.

DELIBERATELY PARTIAL, the same convention game/factions/aeldari_points.py and
game/factions/necrons_points.py follow: only units that actually exist here are
listed, so a KeyError means "not transcribed yet", never "free". Written before
the datasheets for the same reason - they look their cost up by exact name, so
a typo fails loudly at import instead of silently pricing a unit at nothing.

THE USER'S ARMY LIST AND THIS TABLE DISAGREE ON FOUR ENTRIES, and the
transcription wins. Recorded per line as `# the list says N`, never reconciled -
the same treatment the Aeldari and Necron tables document. The list totals
2015 pts; these values total 2020 for the same sixteen units.

The deviations run in BOTH directions (Plague Marines and Myphitic Blight-hauler
are cheaper here, Defiler and Plagueburst Crawler dearer), which is the third
independent refutation of the "the app just rounds up" theory the Aeldari and
Necron tables each recorded.
"""

from game.factions.points import PointsTier, UnitPoints, flat_points

DEATH_GUARD_POINTS = {
    # --- Characters -------------------------------------------------------
    "Daemon Prince of Nurgle": flat_points({1: 195}),
    # No LEADER line at all - a MONSTER CHARACTER that always fights alone.
    # Its Death Guard Defenders ability is what keeps it protected instead.

    "Malignant Plaguecaster": UnitPoints(
        [PointsTier({1: 60})],
        leads=("Plague Marines", "Poxwalkers"),
    ),

    "Typhus": UnitPoints(
        [PointsTier({1: 100})],
        # BLIGHTLORD TERMINATORS is printed on his LEADER line too, but no such
        # datasheet is built here - naming it would make attached_units.py offer
        # a pairing that can never resolve. Left out and recorded instead, so
        # adding that datasheet later is one name and no rules work.
        leads=("Deathshroud Terminators", "Poxwalkers"),
    ),

    # --- Infantry ---------------------------------------------------------
    "Plague Marines": flat_points({5: 90, 7: 125, 10: 180}),   # the list says 190 for 10

    "Poxwalkers": flat_points({10: 65, 20: 130}),

    "Deathshroud Terminators": UnitPoints([
        PointsTier({3: 160, 6: 305}, to_unit=2),
        PointsTier({3: 170, 6: 315}, from_unit=3),
    ]),

    # --- Beasts -----------------------------------------------------------
    # A fixed two-model unit; there is no other legal size.
    "Chaos Spawn": flat_points({2: 80}),

    # --- Vehicles ---------------------------------------------------------
    "Foetid Bloat-drone": UnitPoints([
        PointsTier({1: 100}, to_unit=2),
        PointsTier({1: 110}, from_unit=3),
    ]),

    "Myphitic Blight-hauler": flat_points({1: 95, 2: 190}),    # the list says 100 for 1

    "Plagueburst Crawler": UnitPoints([                        # the list says 210
        PointsTier({1: 170}, to_unit=1),
        PointsTier({1: 200}, from_unit=2),
    ]),

    "Defiler": UnitPoints(                                     # the list says 250
        [
            PointsTier({1: 300}, to_unit=1),
            PointsTier({1: 350}, from_unit=2),
        ],
        # Charged only when actually selected, never for the printed default -
        # so a Defiler keeping its heavy baleflamer pays nothing extra.
        wargear={
            "heavy reaper autocannon": 15,
            "Hades lascannon": 15,
        },
    ),
}
