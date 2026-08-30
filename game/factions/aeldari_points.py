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
    # --- Wraith constructs ----------------------------------------------
    # Both are LED BY the Bonesinger, which is a Legends datasheet and so is
    # deliberately not built. That direction of the pairing lives on the
    # LEADER's own entry, so there is nothing to leave out here - it is
    # recorded in each datasheet's abilities_text instead, and pinned.
    # Flat, no copy tiers; the one wargear option is free on the list.
    "Wraithblades": flat_points({5: 140}),
    "Wraithlord": flat_points({1: 125}),
    # --- Support Weapon Platforms ---------------------------------------
    # All three are SUPPORT models (24.34): "Support Artillery" lets one join a
    # GUARDIAN DEFENDERS unit at Declare Battle Formations, which is exactly
    # what UnitPoints.supports declares. No wargear options at all on any of
    # the three, so nothing is priced.
    #
    # The D-cannon is the only one of the three tiered by copies fielded -
    # transcribed as printed, and the reason its entry is spelled out rather
    # than using flat_points() like its two siblings.
    "D-cannon Platform": UnitPoints([
        PointsTier({1: 110}, to_unit=1),
        PointsTier({1: 125}),
    ], supports=("Guardian Defenders",)),
    "Shadow Weaver Platform": flat_points({1: 60}, supports=("Guardian Defenders",)),
    "Vibro Cannon Platform": flat_points({1: 60}, supports=("Guardian Defenders",)),
    # --- Grav-tanks and Vypers ------------------------------------------
    # The one wargear option on each grav-tank (twin shuriken catapult ->
    # shuriken cannon) is free, as are both of the Vypers'.
    "Fire Prism": flat_points({1: 150}),
    # The Night Spinner is the tiered one of the pair - transcribed as printed,
    # which is why it is spelled out rather than using flat_points().
    "Night Spinner": UnitPoints([
        PointsTier({1: 170}, to_unit=1),
        PointsTier({1: 190}),
    ]),
    "Vypers": flat_points({1: 75, 2: 140}),
    # --- the standalone Asuryani psykers ---------------------------------
    # The Warlock's CORE line is SUPPORT, not LEADER, so its pairing goes in
    # `supports` - the same field the Support Weapon Platforms use. Its one
    # wargear option (witchblade -> singing spear) is free.
    "Warlock": flat_points({1: 40}, supports=("Guardian Defenders", "Storm Guardians")),
    # The Spiritseer has NO printed LEADER or SUPPORT line at all - it stands
    # alone, and its three abilities reach WRAITH CONSTRUCT units by RANGE
    # rather than by attachment. An empty pairing here is the statement.
    "Spiritseer": flat_points({1: 50}),
    "Farseer Skyrunner": flat_points({1: 60}, leads=("Windriders",)),
    # --- Autarchs and Maugan Ra -----------------------------------------
    # The widest LEADER line in the faction. "DARK REAPER" is printed in the
    # SINGULAR on the datasheet and the built datasheet is "Dark Reapers" -
    # `leads` takes DATASHEET names, so the plural is what goes here.
    "Autarch": flat_points({1: 75}, leads=(
        "Dark Reapers", "Dire Avengers", "Fire Dragons", "Guardian Defenders",
        "Howling Banshees", "Storm Guardians", "Striking Scorpions",
    )),
    "Autarch Wayleaper": flat_points({1: 70}, leads=("Swooping Hawks", "Warp Spiders")),
    # EPIC HERO, PHOENIX LORD. Leads one datasheet only, like the other five.
    "Maugan Ra": flat_points({1: 100}, leads=("Dark Reapers",)),
    # --- Exodites --------------------------------------------------------
    # 1 Dragon Knight Leader + 2-5 Dragon Knights, priced at 3 and 6 models.
    # Their Drakolithe option is free ("for every 3 models, 2 Drakolithe").
    "Dragon Knights": flat_points({3: 90, 6: 180}),
    # The Clanblade LEADS the Dragon Knights; the Stonesinger SUPPORTS them -
    # two different core abilities pointing at the same unit, which is why one
    # uses `leads` and the other `supports`.
    "Clanblade": flat_points({1: 70}, leads=("Dragon Knights",)),
    "Stonesinger": flat_points({1: 60}, supports=("Dragon Knights",)),
    # The Leystalker has NO leader or support line - a LONE OPERATIVE sniper
    # that stands alone, and the empty pairing is the statement.
    "Leystalker": flat_points({1: 80}),
    # --- Anhrathe (Corsairs) --------------------------------------------
    # Every Corsair wargear option is free on the list.
    "Corsair Voidreavers": flat_points({5: 65, 10: 110}),
    "Corsair Voidscarred": flat_points({5: 70, 10: 140}),
    "Corsair Skyreavers": flat_points({5: 75, 10: 140}),
    "Starfangs": flat_points({1: 70, 2: 140}),
    # Both EPIC HEROES lead the two Corsair foot squads. Their printed LEADER
    # lines also name CORSAIR REAVER BAND, which is a LEGENDS datasheet and
    # deliberately not built - so it is left out of `leads` and recorded in
    # abilities_text instead, the same treatment the Bonesinger's pairing gets.
    "Kharseth": flat_points({1: 85}, leads=(
        "Corsair Voidreavers", "Corsair Voidscarred")),
    "Prince Yriel": flat_points({1: 95}, leads=(
        "Corsair Voidreavers", "Corsair Voidscarred")),
    # --- The Ynnari triumvirate -----------------------------------------
    # Yvraine's printed LEADER line names eight datasheets. Only four of them
    # are built: CORSAIR REAVER BAND is Legends, and the three Ynnari-Drukhari
    # entries (Incubi, Kabalite Warriors, Wyches) are deliberately out of
    # scope. Those four are left out of `leads` and recorded in abilities_text
    # instead - the same treatment Kharseth's line gets, and the same one that
    # kept "Kroot Farstalkers is named by three LEADER lines and has no
    # datasheet" honest until the datasheet arrived.
    "Yvraine": flat_points({1: 100}, leads=(
        "Corsair Voidreavers", "Corsair Voidscarred",
        "Guardian Defenders", "Storm Guardians")),
    # The Visarch SUPPORTS the same eight, so the same four survive the filter.
    # Support rather than Leader is the whole reason he can join a unit Yvraine
    # is already attached to - his printed line says so in as many words.
    "The Visarch": flat_points({1: 80}, supports=(
        "Corsair Voidreavers", "Corsair Voidscarred",
        "Guardian Defenders", "Storm Guardians")),
    # No leader or support line at all: a MONSTER that teleports to its own
    # army's dead. The empty pairing is the statement.
    "The Yncarne": flat_points({1: 245}),
}
