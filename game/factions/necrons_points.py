"""Necrons points costs, as printed on Wahapedia's 11th-edition datasheets.

DELIBERATELY PARTIAL, the same choice game/factions/aeldari_points.py records
and for the same reason: this table covers only the thirteen datasheets this
engine actually builds. A KeyError from it means "that unit has not been
transcribed yet", NOT "that unit is free". The T'au and Ork tables carry their
whole published lists because those factions were transcribed wholesale; this
one grows as datasheets arrive.

THE ARMY LIST DISAGREES WITH THIS TABLE, on purpose. The user's Necron list
prices nine of these thirteen entries differently, and - as with Player 1's
Aeldari list - the differences run in BOTH directions (the list is cheaper for
the Void Dragon, Szeras, the Overlord and the Doomsday Ark; dearer for
Immortals, Warriors, Lychguard, Skorpekh and Lokhust Destroyers). The
transcription wins here and the deviation is recorded next to each entry
rather than reconciled, which is the standing convention. The two-directional
spread is also the second independent refutation of the "the army app just
rounds up" theory that the old, uniformly-dearer Aeldari list made tempting.

LEADER lines are recorded on `leads`, which is what rule 19.01's pairing table
(game/attached_units.py's leadable_unit_names()) actually reads.
"""

from game.factions.points import PointsTier, UnitPoints, flat_points

NECRONS_POINTS = {
    # --- Characters -------------------------------------------------------
    "C'tan Shard of the Void Dragon": flat_points({1: 345}),        # the list says 330
    "Illuminor Szeras": flat_points({1: 175}),                      # the list says 165
    "Overlord": UnitPoints(
        [PointsTier({1: 90})],                                      # the list says 85
        # "This model can be equipped with 1 resurrection orb" carries no
        # price on the printed entry, so it is a free upgrade rather than an
        # untranscribed one - stated here because a missing wargear number and
        # a genuinely free option look identical from the datasheet side.
        leads=("Immortals", "Lychguard", "Necron Warriors"),
    ),
    "Plasmancer": UnitPoints(
        [PointsTier({1: 55})],                                      # the list agrees
        leads=("Immortals", "Necron Warriors"),
    ),
    "Technomancer": UnitPoints(
        [PointsTier({1: 80}, to_unit=1),                            # the list says 80 - agrees for the 1st
         PointsTier({1: 90}, from_unit=2)],
        leads=("Canoptek Wraiths", "Immortals", "Necron Warriors"),
    ),

    # --- Battleline -------------------------------------------------------
    "Necron Warriors": flat_points({10: 80, 20: 190}),              # the list says 200 for 20
    "Immortals": flat_points({5: 70, 10: 140}),                     # the list says 150 for 10

    # --- Infantry ---------------------------------------------------------
    "Lychguard": flat_points({5: 80, 10: 160}),                     # the list says 85 for 5
    "Skorpekh Destroyers": UnitPoints([
        PointsTier({3: 85, 6: 170}, to_unit=2),                     # the list says 90 for 3
        PointsTier({3: 95, 6: 180}, from_unit=3),
    ]),

    # --- Beasts -----------------------------------------------------------
    "Canoptek Wraiths": UnitPoints([
        PointsTier({3: 95, 6: 220}, to_unit=1),                     # the list says 220 for 6 - agrees at the 1st unit
        PointsTier({3: 115, 6: 240}, from_unit=2),
    ]),

    # --- Mounted ----------------------------------------------------------
    "Lokhust Destroyers": UnitPoints([
        PointsTier({1: 40, 2: 55, 3: 80, 6: 170}, to_unit=2),       # the list says 180 for 6
        PointsTier({1: 50, 2: 65, 3: 90, 6: 180}, from_unit=3),
    ]),
    "Lokhust Heavy Destroyers": UnitPoints([
        PointsTier({1: 50, 2: 100, 3: 160}, to_unit=2),             # the list says 165 for 3
        PointsTier({1: 60, 2: 110, 3: 170}, from_unit=3),
    ]),

    # --- Vehicles ---------------------------------------------------------
    "Doomsday Ark": UnitPoints([
        PointsTier({1: 210}, to_unit=2),                            # the list says 200
        PointsTier({1: 230}, from_unit=3),
    ]),
}
