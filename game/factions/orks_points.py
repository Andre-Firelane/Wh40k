"""The Orks points list, transcribed verbatim from the official army app's
"Unit Costs" screen (user-supplied paste, 2026-07-29). The entries of the
datasheets rebuilt for the 2026-09 codex (Boyz, Beast Snagga Boyz, Stormboyz,
Gretchin, Meganobz, Warboss, Warboss in Mega Armour, Beastboss, Painboy, Flash Gitz,
Tankbustas, Warbikers, Deffkoptas, Trukk, Battlewagon, Deff Dread, Kill Rig) follow the
POINTS table of their rules/orks/*.md page instead, and say so where they stand.

All 58 entries, not just the five units game/factions/orks.py has datasheets
for - same reasoning as game/factions/tau_empire_points.py, which this
module mirrors exactly. Structure, the omitted ▲/▼ change markers, and the
"a priced wargear option is only charged when actually selected" rule are all
explained in game/factions/points.py.

Two things this list does that the T'au one doesn't:

- Gretchin USED to be priced by composition (with and without Runtherds);
  the 2026-09 codex prints 10 and 20 Gretchin only, the Runtherd being a
  separate SUPPORT unit now.
- Two entries attach as SUPPORT rather than LEADER (Bannernob, Painboy) -
  see UnitPoints' own `supports` field.

The one pre-codex Ork wargear price ("Battlewagon: per 'ard case 15 pts") went
with the 'Ard Case: the 2026-09 Battlewagon page prints "WARGEAR COSTS
REMOVED". Big Mek Dakkarig's "UPDATED / REQUISITION THRESHOLDS REMOVED" note is
not a cost and isn't stored.
"""

from game.factions.points import PointsTier, UnitPoints, flat_points

_LEADS_BOYZ_MOBS = ("Boyz", "Breaka Boyz", "Nobz")
_LEADS_MEK_UNITS = ("Boyz", "Breaka Boyz", "Lootas", "Mek Gunz", "Nobz", "Tankbustas")

ORKS_POINTS = {
    "Bannernob": flat_points({1: 50}, supports=(
        "Boyz", "Breaka Boyz", "Burna Boyz", "Flash Gitz", "Lootas", "Nobz", "Tankbustas",
    )),
    # 2026-09 codex (rules/orks/Battlewagon.md) - the 'ard case price is gone.
    "Battlewagon": UnitPoints([
        PointsTier({1: 150}, to_unit=2),
        PointsTier({1: 160}, from_unit=3),
    ]),
    # 2026-09 codex (rules/orks/Beastboss.md).
    "Beastboss": flat_points({1: 85}, leads=("Beast Snagga Boyz",)),
    "Beastboss on Squigosaur": flat_points({1: 95}, leads=("Squighog Boyz",)),
    # 2026-09 codex (rules/orks/Beast Snagga Boyz.md).
    "Beast Snagga Boyz": UnitPoints([
        PointsTier({10: 85, 20: 170}, to_unit=3),
        PointsTier({10: 95, 20: 180}, from_unit=4),
    ]),
    "Bigboss": flat_points({1: 55}, leads=_LEADS_BOYZ_MOBS),
    "Big'ed Bossbunka": flat_points({1: 135}),
    "Big Mek": flat_points({1: 70}, leads=_LEADS_MEK_UNITS),
    "Big Mek Dakkarig": flat_points({1: 115}),
    "Big Mek in Mega Armour": flat_points({1: 80}, leads=("Meganobz",)),
    "Big Mek with Shokk Attack Gun": UnitPoints(
        [
            PointsTier({1: 70}, to_unit=1),
            PointsTier({1: 80}, from_unit=2),
        ],
        leads=_LEADS_MEK_UNITS,
    ),
    "Blitza-Bommer": flat_points({1: 105}),
    "Boomdakka Snazzwagon": flat_points({1: 70}),
    "Boss Snikrot": flat_points({1: 75}, leads=("Kommandos",)),
    # 2026-09 codex (rules/orks/Boyz.md).
    "Boyz": UnitPoints([
        PointsTier({10: 90, 20: 180}, to_unit=3),
        PointsTier({10: 100, 20: 190}, from_unit=4),
    ]),
    "Breaka Boyz": UnitPoints([
        PointsTier({6: 125}, to_unit=2),
        PointsTier({6: 135}, from_unit=3),
    ]),
    "Burna-Bommer": flat_points({1: 115}),
    "Burna Boyz": flat_points({5: 60, 10: 120}),
    "Dakkajet": flat_points({1: 125}),
    # 2026-09 codex (rules/orks/Deff Dread.md).
    "Deff Dread": UnitPoints([
        PointsTier({1: 130}, to_unit=2),
        PointsTier({1: 140}, from_unit=3),
    ]),
    "Deffkilla Wartrike": flat_points({1: 70}, leads=("Warbikers",)),
    # 2026-09 codex (rules/orks/Deffkoptas.md).
    "Deffkoptas": UnitPoints([
        PointsTier({3: 80, 6: 160}, to_unit=2),
        PointsTier({3: 90, 6: 170}, from_unit=3),
    ]),
    # 2026-09 codex (rules/orks/Flash Gitz.md).
    "Flash Gitz": UnitPoints([
        PointsTier({5: 105, 10: 210}, to_unit=2),
        PointsTier({5: 135, 10: 240}, from_unit=3),
    ]),
    "Gargantuan Squiggoth": UnitPoints([
        PointsTier({1: 440}, to_unit=1),
        PointsTier({1: 490}, from_unit=2),
    ]),
    # 2 models: Ghazghkull comes with Makari on the same datasheet.
    "Ghazghkull Thraka": flat_points({2: 235}, leads=("Boyz", "Breaka Boyz", "Meganobz", "Nobz")),
    "Gorkanaut": UnitPoints([
        PointsTier({1: 255}, to_unit=2),
        PointsTier({1: 275}, from_unit=3),
    ]),
    # 2026-09 codex (rules/orks/Gretchin.md).
    "Gretchin": flat_points({10: 45, 20: 80}),
    "Hunta Rig": flat_points({1: 125}),
    "Killa Kans": UnitPoints([
        PointsTier({3: 120, 6: 240}, to_unit=2),
        PointsTier({3: 130, 6: 250}, from_unit=3),
    ]),
    # 2026-09 codex (rules/orks/Kill Rig.md).
    "Kill Rig": UnitPoints([
        PointsTier({1: 175}, to_unit=2),
        PointsTier({1: 185}, from_unit=3),
    ]),
    "Kommandos": flat_points({10: 120}),
    "Kustom Boosta-blasta": flat_points({1: 70}),
    "Lootas": UnitPoints([
        PointsTier({5: 50, 10: 100}, to_unit=2),
        PointsTier({5: 60, 10: 110}, from_unit=3),
    ]),
    # 2026-09 codex (rules/orks/Meganobz.md): "WARGEAR OPTIONS per Twin Killsaws
    # 5 / per Killsaw 5" - the default loadout carries neither, so charging per
    # swap taken and per weapon in the unit agree.
    "Meganobz": UnitPoints([
        PointsTier({2: 75, 3: 110, 5: 185, 6: 225}, to_unit=2),
        PointsTier({2: 115, 3: 150, 5: 225, 6: 265}, from_unit=3),
    ], wargear={"Killsaw": 5, "Twin Killsaws": 5}),
    "Megatrakk Scrapjet": flat_points({1: 75}),
    "Mek": flat_points({1: 55}, leads=("Boyz", "Lootas", "Mek Gunz", "Nobz", "Tankbustas")),
    "Mek Gunz": UnitPoints([
        PointsTier({1: 45, 2: 90, 3: 135}, to_unit=2),
        PointsTier({1: 55, 2: 100, 3: 145}, from_unit=3),
    ]),
    "Morkanaut": UnitPoints([
        PointsTier({1: 270}, to_unit=2),
        PointsTier({1: 290}, from_unit=3),
    ]),
    "Mozrog Skragbad": flat_points({1: 125}, leads=("Squighog Boyz",)),
    "Nobz": UnitPoints([
        PointsTier({5: 105, 10: 210}, to_unit=2),
        PointsTier({5: 115, 10: 220}, from_unit=3),
    ]),
    "Painboss": flat_points({1: 70}, leads=("Beast Snagga Boyz",)),
    # 2026-09 codex (rules/orks/Painboy.md) - its SUPPORT section.
    "Painboy": flat_points({1: 45}, supports=(
        "Boyz", "Breaka Boyz", "Flash Gitz", "Nobz", "Tankbustas",
    )),
    "Rukkatrukk Squigbuggy": flat_points({1: 85}),
    "Shokkjump Dragsta": flat_points({1: 70}),
    "Squighog Boyz": flat_points({4: 140, 8: 270}),
    "Stompa": UnitPoints([
        PointsTier({1: 600}, to_unit=1),
        PointsTier({1: 700}, from_unit=2),
    ]),
    # 2026-09 codex (rules/orks/Stormboyz.md).
    "Stormboyz": flat_points({5: 70, 10: 140}),
    # 2026-09 codex (rules/orks/Tankbustas.md).
    "Tankbustas": UnitPoints([
        PointsTier({6: 145}, to_unit=2),
        PointsTier({6: 155}, from_unit=3),
    ]),
    # 2026-09 codex (rules/orks/Trukk.md).
    "Trukk": UnitPoints([
        PointsTier({1: 60}, to_unit=3),
        PointsTier({1: 70}, from_unit=4),
    ]),
    # 2026-09 codex (rules/orks/Warbikers.md).
    "Warbikers": flat_points({3: 75, 6: 140}),
    # 2026-09 codex (rules/orks/Warboss.md, rules/orks/Warboss in Mega Armour.md).
    "Warboss": flat_points({1: 100}, leads=_LEADS_BOYZ_MOBS),
    "Warboss in Mega Armour": UnitPoints(
        [
            PointsTier({1: 125}, to_unit=2),
            PointsTier({1: 140}, from_unit=3),
        ],
        leads=("Meganobz",),
    ),
    "Wartrakk": flat_points({1: 60}),
    "Wazbom Blastajet": flat_points({1: 165}),
    "Wazdakka Gutsmek": flat_points({1: 175}),
    "Weirdboy": flat_points({1: 65}, leads=("Boyz", "Breaka Boyz")),
    "Wurrboy": flat_points({1: 60}, leads=("Beast Snagga Boyz",)),
    "Zodgrod Wortsnagga": flat_points({1: 80}, leads=("Gretchin",)),
}
