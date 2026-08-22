"""The Orks points list, transcribed verbatim from the official army app's
"Unit Costs" screen (user-supplied paste, 2026-07-29).

All 58 entries, not just the five units game/factions/orks.py has datasheets
for - same reasoning as game/factions/tau_empire_points.py, which this
module mirrors exactly. Structure, the omitted ▲/▼ change markers, and the
"a priced wargear option is only charged when actually selected" rule are all
explained in game/factions/points.py.

Two things this list does that the T'au one doesn't:

- Gretchin is priced by COMPOSITION rather than by a bare model count ("10
  Gretchin 45 pts / 1 Runtherd, 10 Gretchin 45 pts / 20 Gretchin 80 pts / 1
  Runtherd, 20 Gretchin 85 pts / 2 Runtherd, 20 Gretchin 90 pts"). A flat
  {model_count: points} table still captures it losslessly because every one
  of those five builds has a distinct TOTAL model count (10, 11, 20, 21,
  22) - so the two 45-pt builds stay distinguishable even though they cost
  the same. Worth stating explicitly: this holds for this entry, it is not a
  general guarantee, and a future entry pricing two same-sized builds
  differently would need composition-aware tiers instead.
- Two entries attach as SUPPORT rather than LEADER (Bannernob, Painboy) -
  see UnitPoints' own `supports` field.

The one Ork wargear price on the list ("Battlewagon: per 'ard case 15 pts")
belongs to a datasheet that doesn't exist here yet, so nothing reads it -
it's stored so that it's already there when Battlewagon is added. Big Mek
Dakkarig's "UPDATED / REQUISITION THRESHOLDS REMOVED" note is not a cost and
isn't stored.
"""

from game.factions.points import PointsTier, UnitPoints, flat_points

_LEADS_BOYZ_MOBS = ("Boyz", "Breaka Boyz", "Nobz")
_LEADS_MEK_UNITS = ("Boyz", "Breaka Boyz", "Lootas", "Mek Gunz", "Nobz", "Tankbustas")

ORKS_POINTS = {
    "Bannernob": flat_points({1: 50}, supports=(
        "Boyz", "Breaka Boyz", "Burna Boyz", "Flash Gitz", "Lootas", "Nobz", "Tankbustas",
    )),
    "Battlewagon": flat_points({1: 145}, wargear={"'ard case": 15}),
    "Beastboss": flat_points({1: 80}, leads=("Beast Snagga Boyz",)),
    "Beastboss on Squigosaur": flat_points({1: 95}, leads=("Squighog Boyz",)),
    "Beast Snagga Boyz": flat_points({10: 90, 20: 170}),
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
    "Boyz": UnitPoints([
        PointsTier({10: 75, 20: 160}, to_unit=3),
        PointsTier({10: 85, 20: 170}, from_unit=4),
    ]),
    "Breaka Boyz": UnitPoints([
        PointsTier({6: 125}, to_unit=2),
        PointsTier({6: 135}, from_unit=3),
    ]),
    "Burna-Bommer": flat_points({1: 115}),
    "Burna Boyz": flat_points({5: 60, 10: 120}),
    "Dakkajet": flat_points({1: 125}),
    "Deff Dread": UnitPoints([
        PointsTier({1: 110}, to_unit=2),
        PointsTier({1: 120}, from_unit=3),
    ]),
    "Deffkilla Wartrike": flat_points({1: 70}, leads=("Warbikers",)),
    "Deffkoptas": flat_points({3: 75, 6: 140}),
    "Flash Gitz": UnitPoints([
        PointsTier({5: 75, 10: 150}, to_unit=2),
        PointsTier({5: 85, 10: 160}, from_unit=3),
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
    # Keyed by total model count - see this module's docstring on why that is
    # lossless here: 10 Gretchin and 1 Runtherd + 10 Gretchin both cost 45,
    # but come to 10 and 11 models respectively.
    "Gretchin": flat_points({10: 45, 11: 45, 20: 80, 21: 85, 22: 90}),
    "Hunta Rig": flat_points({1: 125}),
    "Killa Kans": UnitPoints([
        PointsTier({3: 120, 6: 240}, to_unit=2),
        PointsTier({3: 130, 6: 250}, from_unit=3),
    ]),
    "Kill Rig": flat_points({1: 145}),
    "Kommandos": flat_points({10: 120}),
    "Kustom Boosta-blasta": flat_points({1: 70}),
    "Lootas": UnitPoints([
        PointsTier({5: 50, 10: 100}, to_unit=2),
        PointsTier({5: 60, 10: 110}, from_unit=3),
    ]),
    "Meganobz": UnitPoints([
        PointsTier({2: 60, 3: 90, 5: 150, 6: 180}, to_unit=2),
        PointsTier({2: 80, 3: 110, 5: 170, 6: 200}, from_unit=3),
    ]),
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
    "Painboy": flat_points({1: 90}, supports=(
        "Boyz", "Breaka Boyz", "Burna Boyz", "Lootas", "Nobz", "Tankbustas",
    )),
    "Rukkatrukk Squigbuggy": flat_points({1: 85}),
    "Shokkjump Dragsta": flat_points({1: 70}),
    "Squighog Boyz": flat_points({4: 140, 8: 270}),
    "Stompa": UnitPoints([
        PointsTier({1: 600}, to_unit=1),
        PointsTier({1: 700}, from_unit=2),
    ]),
    "Stormboyz": flat_points({5: 65, 10: 130}),
    "Tankbustas": UnitPoints([
        PointsTier({6: 125}, to_unit=2),
        PointsTier({6: 135}, from_unit=3),
    ]),
    "Trukk": UnitPoints([
        PointsTier({1: 55}, to_unit=3),
        PointsTier({1: 65}, from_unit=4),
    ]),
    "Warbikers": flat_points({3: 60, 6: 120}),
    "Warboss": flat_points({1: 85}, leads=_LEADS_BOYZ_MOBS),
    "Warboss in Mega Armour": flat_points({1: 80}, leads=("Meganobz",)),
    "Wartrakk": flat_points({1: 60}),
    "Wazbom Blastajet": flat_points({1: 165}),
    "Wazdakka Gutsmek": flat_points({1: 175}),
    "Weirdboy": flat_points({1: 65}, leads=("Boyz", "Breaka Boyz")),
    "Wurrboy": flat_points({1: 60}, leads=("Beast Snagga Boyz",)),
    "Zodgrod Wortsnagga": flat_points({1: 80}, leads=("Gretchin",)),
}
