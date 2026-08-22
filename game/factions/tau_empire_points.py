"""The T'au Empire points list, transcribed verbatim from the official army
app's "Unit Costs" screen (user-supplied paste, 2026-07-29).

This is the WHOLE published list - all 43 entries - not just the seven units
game/factions/tau_empire.py currently has datasheets for. The rest are kept
because a points list is a single published document: recording only the
already-implemented units would mean re-sourcing the numbers every time a
new datasheet is added, and a partially-transcribed list gives no way to
tell "this unit is free" from "nobody typed it in yet".

Structure and the two deliberate omissions (the up/down arrows, and never
charging for a printed default loadout) are explained in
game/factions/points.py - read that first. Wargear items are keyed by the
name as printed on the list; only the six entries that actually print a
"WARGEAR OPTIONS" line have one, everything else's options are free.

The "LEADER: ..." lines are carried in `leads` purely as reference (see
UnitPoints); this module prices units, it does not model attaching them.
"""

from game.factions.points import PointsTier, UnitPoints, flat_points

TAU_EMPIRE_POINTS = {
    "AX-1-0 Tiger Shark": UnitPoints([
        PointsTier({1: 315}, to_unit=1),
        PointsTier({1: 375}, from_unit=2),
    ]),
    "Breacher Team": flat_points({10: 90}),
    "Broadside Battlesuits": UnitPoints(
        [
            PointsTier({1: 75, 2: 150, 3: 255}, to_unit=2),
            PointsTier({1: 95, 2: 170, 3: 275}, from_unit=3),
        ],
        wargear={"High-yield missile pods": 5},
    ),
    "Cadre Fireblade": flat_points({1: 50}, leads=("Breacher Team", "Strike Team")),
    "Commander Farsight": flat_points({1: 70}, leads=(
        "Crisis Fireknife Battlesuits", "Crisis Starscythe Battlesuits", "Crisis Sunforge Battlesuits",
    )),
    "Commander in Coldstar Battlesuit": flat_points({1: 95}, leads=(
        "Crisis Fireknife Battlesuits", "Crisis Starscythe Battlesuits", "Crisis Sunforge Battlesuits",
    )),
    "Commander in Enforcer Battlesuit": flat_points({1: 80}, leads=(
        "Crisis Fireknife Battlesuits", "Crisis Starscythe Battlesuits", "Crisis Sunforge Battlesuits",
    )),
    "Commander Shadowsun": flat_points({1: 100}),
    "Crisis Fireknife Battlesuits": UnitPoints(
        [
            PointsTier({3: 100}, to_unit=2),
            PointsTier({3: 110}, from_unit=3),
        ],
        wargear={"Missile pod": 5},
    ),
    "Crisis Starscythe Battlesuits": UnitPoints(
        [
            PointsTier({3: 90}, to_unit=2),
            PointsTier({3: 100}, from_unit=3),
        ],
        wargear={"T'au flamer": 5},
    ),
    "Crisis Sunforge Battlesuits": UnitPoints([
        PointsTier({3: 125}, to_unit=2),
        PointsTier({3: 135}, from_unit=3),
    ]),
    "Darkstrider": flat_points({1: 60}, leads=("Pathfinder Team",)),
    "Devilfish": UnitPoints([
        PointsTier({1: 75}, to_unit=3),
        PointsTier({1: 85}, from_unit=4),
    ]),
    "Ethereal": flat_points({1: 50}, leads=("Breacher Team", "Strike Team")),
    "Firesight Team": flat_points({1: 55}),
    "Ghostkeel Battlesuit": UnitPoints(
        [
            PointsTier({1: 150}, to_unit=2),
            PointsTier({1: 165}, from_unit=3),
        ],
        wargear={"Cyclic Ion Raker": 15},
    ),
    "Hammerhead Gunship": UnitPoints([
        PointsTier({1: 150}, to_unit=2),
        PointsTier({1: 160}, from_unit=3),
    ]),
    "Kroot Carnivores": flat_points({10: 65, 20: 130}),
    "Kroot Farstalkers": UnitPoints([
        PointsTier({12: 75}, to_unit=2),
        PointsTier({12: 85}, from_unit=3),
    ]),
    "Kroot Flesh Shaper": flat_points({1: 45}, leads=("Kroot Carnivores", "Kroot Farstalkers")),
    "Kroot Hounds": flat_points({5: 45, 10: 65}),
    "Kroot Lone-spear": flat_points({1: 80}),
    "Krootox Rampagers": UnitPoints([
        PointsTier({3: 85, 6: 170}, to_unit=2),
        PointsTier({3: 95, 6: 180}, from_unit=3),
    ]),
    "Krootox Riders": flat_points({1: 45, 2: 60, 3: 90}),
    "Kroot Trail Shaper": flat_points({1: 50}, leads=("Kroot Carnivores", "Kroot Farstalkers")),
    "Kroot War Shaper": flat_points({1: 60}, leads=("Kroot Carnivores", "Kroot Farstalkers")),
    "Manta": flat_points({1: 2100}),
    "Pathfinder Team": UnitPoints(
        [
            PointsTier({10: 85}, to_unit=2),
            PointsTier({10: 100}, from_unit=3),
        ],
        wargear={"Ion rifle": 5},
    ),
    "Piranhas": UnitPoints([
        PointsTier({1: 65, 2: 110, 3: 165}, to_unit=2),
        PointsTier({1: 75, 2: 120, 3: 175}, from_unit=3),
    ]),
    "Razorshark Strike Fighter": flat_points({1: 160}),
    "Riptide Battlesuit": UnitPoints(
        [
            PointsTier({1: 190}, to_unit=2),
            PointsTier({1: 220}, from_unit=3),
        ],
        wargear={"Ion accelerator": 25},
    ),
    "Sky Ray Gunship": flat_points({1: 140}),
    "Stealth Battlesuits": UnitPoints([
        PointsTier({5: 100}, to_unit=2),
        PointsTier({5: 110}, from_unit=3),
    ]),
    "Stormsurge": UnitPoints([
        PointsTier({1: 375}, to_unit=1),
        PointsTier({1: 400}, from_unit=2),
    ]),
    "Strike Team": flat_points({10: 70}),
    "Sun Shark Bomber": flat_points({1: 150}),
    "Ta'unar Supremacy Armour": UnitPoints([
        PointsTier({1: 790}, to_unit=1),
        PointsTier({1: 890}, from_unit=2),
    ]),
    "The Twin Lance": flat_points({2: 220}),
    "Tidewall Droneport": flat_points({1: 85}),
    "Tidewall Gunrig": flat_points({1: 90}),
    # The list's "+ 1 Tidewall Defence Platform 20 pts" line sits where every
    # other entry's "WARGEAR OPTIONS" block does, so it's stored as one -
    # even though a Defence Platform isn't a weapon swap, nothing in this
    # module cares which shape the priced extra has.
    "Tidewall Shieldline": flat_points({1: 85}, wargear={"1 Tidewall Defence Platform": 20}),
    "Tiger Shark": UnitPoints([
        PointsTier({1: 375}, to_unit=1),
        PointsTier({1: 425}, from_unit=2),
    ]),
    "Vespid Stingwings": flat_points({5: 70, 10: 115}),
}
