"""Aeldari points costs.

DELIBERATELY INCOMPLETE, unlike its T'au and Ork counterparts, and that is
worth stating rather than leaving to be discovered: those two hold the ENTIRE
published list (43 and 58 entries) specifically so that "this unit is free" can
never be confused with "nobody has typed it in yet". Here only the units this
project has actually built are priced, because only their costs have been
supplied.

So: a KeyError from this table means "not transcribed yet", not "no cost". When
the full Aeldari list arrives it belongs here in one go, same as the other two.
"""

from game.factions.points import PointsTier, UnitPoints, flat_points

AELDARI_POINTS = {
    # 10 Guardian Defenders + 1 Heavy Weapon Platform = 11 models.
    "Guardian Defenders": flat_points({11: 90}),
    # 10 Storm Guardians + 1 Serpent's Scale Platform = 11 models. Every
    # wargear option on the datasheet is free on the list.
    "Storm Guardians": flat_points({11: 110}),
    # 1 Exarch + 4 or 9 Striking Scorpions. Every wargear option is free.
    "Striking Scorpions": flat_points({5: 75, 10: 145}),
    # 1 Exarch + 4 or 9 Howling Banshees. Every wargear option is free.
    "Howling Banshees": flat_points({5: 85, 10: 165}),
    # 1 Exarch + 4 or 9 Warp Spiders. The first Aeldari entry here that is
    # tiered by how many copies the army already fields, the same shape the
    # Ghostkeel Battlesuit uses in the T'au list.
    "Warp Spiders": UnitPoints([
        PointsTier({5: 105, 10: 200}, to_unit=2),
        PointsTier({5: 125, 10: 220}, from_unit=3),
    ]),
    # 1 Exarch + 4 or 9 Dire Avengers. Every wargear option is free.
    "Dire Avengers": flat_points({5: 75, 10: 150}),
    # 1 Exarch + 4 or 9 Fire Dragons. Tiered by army copies, like Warp Spiders.
    "Fire Dragons": UnitPoints([
        PointsTier({5: 120, 10: 240}, to_unit=2),
        PointsTier({5: 130, 10: 250}, from_unit=3),
    ]),
    # 1 model, and no army-copy tiering printed on this entry.
    "Falcon": flat_points({1: 130}),
    # 5 models, and only that size is printed - no 10-model variant.
    "Wraithguard": flat_points({5: 145}),
    # 1 model. Its LEADER line is the whole of rule 19.01's legality check
    # for him, the same way every other faction's list carries it.
    "Asurmen": UnitPoints([PointsTier({1: 135})], leads=("Dire Avengers",)),
    "Jain Zar": UnitPoints([PointsTier({1: 105})], leads=("Howling Banshees",)),
    # "2-4 Warlocks", but only 2 and 4 are PRICED - a 3-model unit is legal
    # on the composition line and has no cost printed, so it is deliberately
    # not built (an unlisted size resolves to None, which is the honest answer).
    "Warlock Conclave": UnitPoints(
        [PointsTier({2: 55, 4: 120})], leads=("Guardian Defenders", "Storm Guardians"),
    ),
    "Farseer": UnitPoints(
        [PointsTier({1: 65})], leads=("Guardian Defenders", "Storm Guardians"),
    ),
    # EPIC HERO. The PRINTED leader list is these two; the separate errata
    # document is reported to add WARLOCK CONCLAVE to it. Only the printed list
    # is transcribed, because the errata was available only as a paraphrase of
    # what it replaces, and because it changes nothing that matters here: his
    # own LEADER line already reaches a Conclave-led unit as the second leader
    # (see UnitProfile.joins_warlock_led_unit), which is the shape Protect
    # needs. Adding "Warlock Conclave" below is the one-line switch if the
    # errata wording is confirmed.
    # EPIC HERO, MONSTER. No LEADER line at all, hence no `leads`.
    "Avatar of Khaine": UnitPoints([PointsTier({1: 250})]),
    # EPIC HERO, PHOENIX LORD. Leads one datasheet only.
    "Lhykhis": UnitPoints(
        [PointsTier({1: 135})], leads=("Warp Spiders",),
    ),
    # 1 Exarch + 4 or 9 Dark Reapers. Every wargear option is free.
    "Dark Reapers": flat_points({5: 100, 10: 210}),
    # 1 Exarch + 4 or 9 Swooping Hawks, tiered by how many copies the army
    # already fields - the same shape Warp Spiders and the Ghostkeel use.
    "Swooping Hawks": UnitPoints([
        PointsTier({5: 95, 10: 190}, to_unit=2),
        PointsTier({5: 110, 10: 205}),
    ]),
    # EPIC HERO, PHOENIX LORD. Leads one datasheet only.
    "Baharroth": UnitPoints([PointsTier({1: 125})], leads=("Swooping Hawks",)),
    # 5-10 Rangers. No wargear options at all.
    "Rangers": flat_points({5: 60, 10: 110}),
    # 3-6 Shroud Runners. No wargear options at all.
    "Shroud Runners": flat_points({3: 90, 6: 175}),
    # 3 or 6 jetbikes. Every wargear option is free.
    "Windriders": flat_points({3: 80, 6: 170}),
    # 1-2 models. Its LEADER ability is a JOIN rather than an ordinary
    # attachment (see game/attached_units.py), but `leads` is what
    # can_attach() reads for the pairing table either way.
    "Warlock Skyrunners": UnitPoints(
        [PointsTier({1: 55, 2: 90})], leads=("Windriders",),
    ),
    # 1 Exarch + 2 or 5 Shining Spears. Every wargear option is free.
    "Shining Spears": flat_points({3: 100, 6: 200}),
    # 1-2 War Walkers. Every wargear option is free on the list.
    "War Walkers": flat_points({1: 85, 2: 160}),
    # A DEDICATED TRANSPORT, tiered by copies fielded - the shape Warp
    # Spiders and Swooping Hawks use. Every wargear option is free.
    "Wave Serpent": UnitPoints([
        PointsTier({1: 115}, to_unit=3),
        PointsTier({1: 125}),
    ]),
    # EPIC HERO, PHOENIX LORD. Leads one datasheet only, like the other four.
    "Fuegan": UnitPoints([PointsTier({1: 130})], leads=("Fire Dragons",)),
    "Eldrad Ulthran": UnitPoints(
        [PointsTier({1: 130})], leads=("Guardian Defenders", "Storm Guardians"),
    ),
}
