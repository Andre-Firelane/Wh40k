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
    "C'tan Shard of the Nightbringer": flat_points({1: 360}),
    "C'tan Shard of the Deceiver": flat_points({1: 330}),
    # The only C'tan a list may take twice, and the only one that is not an
    # EPIC HERO - so it is also the only one with per-unit tiers.
    "Transcendent C'tan": UnitPoints([
        PointsTier({1: 340}, to_unit=1),
        PointsTier({1: 360}, from_unit=2),
    ]),
    "Illuminor Szeras": flat_points({1: 175}),                      # the list says 165
    # The four characters that LEAD. Their `leads` tuples are cross-checked
    # against the LED BY blocks of Immortals, Lychguard and Necron Warriors,
    # which is how this table is kept honest - and the Royal Warden is the one
    # that differs: his printed Leader section names IMMORTALS and NECRON
    # WARRIORS and NOT Lychguard.
    #
    # Those LED BY blocks also name LORD, ANRAKYR THE TRAVELLER, NEMESOR
    # ZAHNDREKH and VARGARD OBYRON, none of which is in this backfill's scope.
    # That is a `leads`-side absence - nothing here has to change for it - but
    # it is written down rather than left to look like an oversight.
    "Royal Warden": flat_points(
        {1: 50}, leads=("Immortals", "Necron Warriors")),
    "Overlord with translocation shroud": flat_points(
        {1: 90}, leads=("Immortals", "Lychguard", "Necron Warriors")),
    "Imotekh The Stormlord": flat_points(
        {1: 100}, leads=("Immortals", "Lychguard", "Necron Warriors")),
    "Trazyn The Infinite": flat_points(
        {1: 65}, leads=("Immortals", "Lychguard", "Necron Warriors")),
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
        # SUPPORTS, not leads. Both spellings resolve identically today -
        # leadable_unit_names() falls back from one to the other - but the
        # printed line reads "SUPPORT" and the profile now carries the matching
        # role, so the pairing is written where the role expects to find it.
        supports=("Immortals", "Necron Warriors"),
    ),
    # --- Crypteks (the Chronomancer batch) ---
    "Chronomancer": UnitPoints(
        [PointsTier({1: 70}, to_unit=1),
         PointsTier({1: 80}, from_unit=2)],
        supports=("Immortals", "Necron Warriors"),
    ),
    "Psychomancer": flat_points(
        {1: 55}, supports=("Immortals", "Necron Warriors")),
    "Orikan The Diviner": flat_points(
        {1: 90}, supports=("Immortals", "Necron Warriors")),
    # --- Destroyer Cult (the Hexmark batch) ---
    # Not in the user's 13-entry army list, so there is no list column to
    # disagree with for any of these three.
    "Hexmark Destroyer": flat_points({1: 75}),
    "Nekrosor Ammentar": flat_points({1: 185}),
    # --- rank and file (the Deathmarks batch) ---
    "Deathmarks": UnitPoints([
        PointsTier({5: 60, 10: 120}, to_unit=2),
        PointsTier({5: 70, 10: 130}, from_unit=3),
    ]),
    "Flayed Ones": flat_points({5: 55, 10: 100}),
    # Its pairings are NOT here: the Cryptek Retinue is not a printed
    # "SUPPORT: ..." line but a rule with a runtime condition ("a unit being
    # led by a CRYPTEK INFANTRY model"), so it is answered by
    # cryptothralls.retinue_join_errors() and leadable_unit_names() correctly
    # returns nothing - which is what makes can_attach() skip its pairing check.
    "Cryptothralls": flat_points({2: 60}),
    "Tomb Blades": UnitPoints([
        PointsTier({3: 70, 6: 140}, to_unit=2),
        PointsTier({3: 80, 6: 150}, from_unit=3),
    ]),
    "Technomancer": UnitPoints(
        [PointsTier({1: 80}, to_unit=1),                            # the list says 80 - agrees for the 1st
         PointsTier({1: 90}, from_unit=2)],
        supports=("Canoptek Wraiths", "Immortals", "Necron Warriors"),
    ),
    # Neither this nor the Skorpekh Lord is in the user's 13-entry army list -
    # both were added on their own, so there is no list column to disagree with.
    "Lokhust Lord": UnitPoints(
        [PointsTier({1: 70})],
        # Both wargear choices (nanoscarab amulet / resurrection orb, and the
        # Lord's blade) are printed without a price, so they are free upgrades
        # rather than untranscribed ones - stated because a missing wargear
        # number and a genuinely free option look identical from here.
        leads=("Lokhust Destroyers", "Lokhust Heavy Destroyers"),
    ),
    # Not in the user's 13-entry army list - added on its own ("Lege die
    # einheit an / Skorpekh Lord"), so there is no list column to disagree
    # with here.
    "Skorpekh Lord": UnitPoints(
        [PointsTier({1: 90}, to_unit=2),
         PointsTier({1: 100}, from_unit=3)],
        # The narrowest LEADER line of any Necron character here: the other
        # four each lead two or three datasheets, this one leads exactly the
        # unit it is a bigger version of.
        leads=("Skorpekh Destroyers",),
    ),

    # --- Battleline -------------------------------------------------------
    "Necron Warriors": flat_points({10: 80, 20: 190}),              # the list says 200 for 20
    "Immortals": flat_points({5: 70, 10: 140}),                     # the list says 150 for 10

    # --- Infantry ---------------------------------------------------------
    "Ophydian Destroyers": UnitPoints([
        PointsTier({3: 80, 6: 150}, to_unit=2),
        PointsTier({3: 90, 6: 160}, from_unit=3),
    ]),
    "Lychguard": flat_points({5: 80, 10: 160}),                     # the list says 85 for 5
    # --- Triarch (the Praetorians batch) ---
    #
    # Neither of these two is LED BY anything and neither prints a LEADER
    # line - checked against the page's own LED BY blocks (six of them on this
    # faction, none naming a Triarch datasheet), not assumed from the absence
    # of a pairing here.
    "Triarch Praetorians": flat_points({5: 80, 10: 160}),
    "Skorpekh Destroyers": UnitPoints([
        PointsTier({3: 85, 6: 170}, to_unit=2),                     # the list says 90 for 3
        PointsTier({3: 95, 6: 180}, from_unit=3),
    ]),

    # --- Canoptek (the Spyders batch) ---
    "Canoptek Scarab Swarms": flat_points({3: 40, 6: 80}),
    "Canoptek Spyders": flat_points({1: 65, 2: 110}),
    "Canoptek Doomstalker": flat_points({1: 140}),
    "Canoptek Reanimator": flat_points({1: 75}),
    "Canoptek Macrocytes": flat_points({5: 70}),
    "Canoptek Tomb Crawlers": flat_points({2: 50}),
    "Geomancer": UnitPoints(
        [PointsTier({1: 75})],
        # The sixth Cryptek, and the only one whose SUPPORTED BY list names a
        # unit outside the two every other one attaches to.
        supports=("Canoptek Macrocytes", "Immortals", "Necron Warriors"),
    ),

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
    "Triarch Stalker": UnitPoints([
        PointsTier({1: 110}, to_unit=2),
        PointsTier({1: 120}, from_unit=3),
    ]),
    "Doomsday Ark": UnitPoints([
        PointsTier({1: 210}, to_unit=2),                            # the list says 200
        PointsTier({1: 230}, from_unit=3),
    ]),
    # The three grav skimmers of stage 8. Each prints a SINGLE tier - no
    # "YOUR 2ND + UNIT COSTS" line at all, unlike the two above - so they are
    # flat_points and not a two-tier UnitPoints.
    #
    # NO `leads` AND NO `supports` ON ANY OF THEM, and that is measured rather
    # than inferred from an absent entry: the Catacomb Command Barge prints the
    # CHARACTER keyword but no Leader section whatsoever, and no LED BY block
    # anywhere on the Necron page names any of the three. So can_attach()
    # refuses every pairing, which the suite pins in both directions.
    "Catacomb Command Barge": flat_points({1: 120}),
    "Annihilation Barge": flat_points({1: 95}),
    "Ghost Ark": flat_points({1: 100}),
}
