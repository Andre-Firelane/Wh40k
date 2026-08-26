"""The army lists this build can field, as data plus a builder each.

WHY THIS IS A MODULE AND NOT STILL INSIDE main(). Until now Player 1 WAS the
Aeldari list and Player 2 was whichever of Orks/Necrons config.PLAYER2_ARMY
named - three blocks of straight-line code in main(), each with its owner
hard-coded into every build_squad() call and into every squad NAME. User: "ich
haette gerne noch, bevor das Pre game losgeht, eine Auswahlmoeglichkeit fuer
die Voelker/listen ... man kann in grossen Kacheln auswaehlen, welche Liste wer
spielen soll." A screen that offers a list to EITHER player cannot be built on
top of code that knows which player it is for, so each list became a function
of its owner.

WHAT IS AND IS NOT PARAMETERISED. The owner is - it decides the `owner=`
argument and the squad-name prefix ("1 Boyz 1" vs "2 Boyz 1"). Nothing else is:
the compositions, the wargear choices, the attachments and the transport
declarations are the user-supplied lists, copied here verbatim from main() with
their reasoning comments intact. Every one of those comments earned its place
by being the answer to a question that came up once already, so they moved with
the code rather than being summarised away.

THE SQUAD NAME IS AN IDENTIFIER, not decoration. ai/agent_driver.py's plan
orders address units by exact name, game/maps.py's partial rosters name them,
and game/scene_io.py keys a saved position on them - so the "<player digit>
<datasheet> <copy>" shape is load-bearing and unit_name() below is the one
place it is formed.

WHAT A LIST CARRIES BESIDES ITS BUILDER: the faction keyword (which is how
game/sprites.py finds the badge - the same keyword the rules use, not a second
name to keep in sync), the army rule's name and the detachment's name. The last
two are list-building declarations and cannot be derived from the units - the
same reason config.SEER_COUNCIL_PLAYERS and config.AWAKENED_DYNASTY_PLAYERS
exist - which is also why apply_to_config() at the bottom is what turns a
choice into those settings.
"""

from game import attached_units, config, pregame, starflare_ignition
from game.factions import build_squad
from game.factions.aeldari import (
    ASURMEN, BANSHEE_BLADE_TO_EXECUTIONER, DARK_REAPERS, DIRE_AVENGERS,
    DIRE_AVENGER_SECOND_CATAPULT, ELDRAD_ULTHRAN, FALCON,
    FALCON_CATAPULT_TO_SHURIKEN_CANNON, FALCON_SCATTER_TO_BRIGHT_LANCE, FARSEER,
    FARSEER_WITCHBLADE_TO_SPEAR, GUARDIAN_DEFENDERS, HOWLING_BANSHEES,
    JAIN_ZAR, LHYKHIS, RANGERS, SHINING_SPEARS, SHINING_SPEAR_SHIMMERSHIELD,
    SHINING_SPEAR_TO_SHURIKEN_CANNON, SHINING_SPEAR_TO_STAR_LANCE, SHROUD_RUNNERS,
    STORM_GUARDIANS, STORM_GUARDIAN_CCW_TO_POWER_SWORD,
    STORM_GUARDIAN_PISTOL_TO_FLAMER, STORM_GUARDIAN_PISTOL_TO_FUSION,
    STRIKING_SCORPIONS, WARLOCK_CONCLAVE, WARLOCK_SKYRUNNERS,
    WARLOCK_WITCHBLADE_TO_SPEAR, WARP_SPIDERS,
    WARP_SPIDER_TO_POWERBLADE_ARRAY, WRAITHGUARD, WRAITHGUARD_TO_D_SCYTHE,
)
from game.factions.necrons import (
    CANOPTEK_WRAITHS, CTAN_SHARD_OF_THE_VOID_DRAGON, DOOMSDAY_ARK, ILLUMINOR_SZERAS,
    IMMORTALS, LOKHUST_DESTROYERS, LOKHUST_HEAVY_DESTROYERS,
    LOKHUST_HEAVY_TO_ENMITIC_EXTERMINATOR, LYCHGUARD, LYCHGUARD_DISPERSION_SHIELD,
    LYCHGUARD_TO_HYPERPHASE_SWORD, NECRON_WARRIORS, OVERLORD, OVERLORD_RESURRECTION_ORB,
    OVERLORD_TO_VOIDSCYTHE, PLASMANCER, SKORPEKH_DESTROYERS, TECHNOMANCER,
)
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, BATTLEWAGON_ADD_ZZAP_GUN, BATTLEWAGON_ARD_CASE,
    BEAST_SNAGGA_BOYZ, BEASTBOSS, BOYZ, BOYZ_BIG_CHOPPA_TO_POWER_KLAW, DEFF_DREAD, DEFFKOPTAS,
    FLASH_GITZ, FLASH_GITZ_AMMO_RUNT, GRETCHIN, KILL_RIG, MEGANOBZ, PAINBOY,
    PAINBOY_GROT_ORDERLY, STORMBOYZ,
    STORMBOYZ_CHOPPA_TO_POWER_KLAW, TANKBUSTAS, TANKBUSTAS_ADD_ROKKIT_LAUNCHA,
    TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER,
    WARBIKERS, WARBIKERS_ADD_POWER_KLAW, WARBOSS, WARBOSS_ADD_ATTACK_SQUIG, WARBOSS_MEGA_ARMOUR,
)

from game.factions.tau_empire import (
    BREACHER_TEAM, CADRE_FIREBLADE, COLDSTAR_ADD_2X_BURST_CANNON, COLDSTAR_ADD_CYCLIC_ION_BLASTER,
    COMMANDER_FARSIGHT, COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_STARSCYTHE, CRISIS_SUNFORGE,
    DEVILFISH, DEVILFISH_SEEKER_MISSILE_OPTION, GHOSTKEEL_BATTLESUIT,
    GHOSTKEEL_FLAMER_TO_FUSION_BLASTER, GHOSTKEEL_FUSION_TO_ION_RAKER, KROOT_CARNIVORES,
    PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER, PATHFINDER_CARBINE_TO_RAIL_RIFLE, PATHFINDER_TEAM,
    RIPTIDE_BATTLESUIT, RIPTIDE_BURST_TO_ION_ACCELERATOR, RIPTIDE_PLASMA_TO_TWIN_FUSION,
    STARSCYTHE_FLAMER_TO_BURST, STEALTH_BATTLESUITS, STRIKE_TEAM, THE_TWIN_LANCE,
)

AELDARI = "aeldari"
ORKS_ARMY = "orks"
TAU_ARMY = "tau"
NECRONS_ARMY = "necrons"


def unit_name(owner, text):
    """This army's name for a unit: the owner's digit, then the datasheet name
    and the copy number ("2 Boyz 1").

    One definition because the name is an identifier - see this module's
    docstring. owner[-1] rather than a lookup table for the same reason main()
    already used it: the two players are "Player 1" and "Player 2" everywhere
    in this engine, and a third would need a great deal more than a prefix."""
    return f"{owner[-1]} {text}"


def _check_positions(list_name, model_positions, wanted):
    """Refuse --no-deployment loudly when the map's hand-placed table does not
    cover this list.

    Kept from main(), where it guarded exactly one roster. It matters more now
    that either player may field either list: the tables in game/maps.py are a
    property of the MAP and were written for a Player 1 Aeldari roster that has
    since been revised twice, so any other pairing has no table at all - and
    the failure without this is silent, every uncovered unit simply starting on
    top of each other at (0, 0)."""
    if model_positions is None:
        return
    if len(model_positions) != wanted:
        raise SystemExit(
            f"--no-deployment needs one hand-placed position list per unit, and the {list_name} "
            f"list does not have them: this map carries {len(model_positions)} position list(s) "
            f"for {wanted} unit(s). Every army list in this build was written on the "
            "understanding that the Pre-game Sequence (rule 03.01) places it - user: \"nicht "
            "aufstellen, wir haben ja jetzt die spieler aufstellung drin\". Run without "
            "--no-deployment, or add the missing entries to game/maps.py."
        )


def _apply_positions(squad, model_positions, index):
    """Hand-place one unit's models, legacy --no-deployment mode only."""
    positions = model_positions[index] if model_positions and index < len(model_positions) else []
    for model, (x_in, y_in) in zip(squad.models, positions):
        model.x_in, model.y_in = x_in, y_in
    return positions


# ===========================================================================
# Aeldari (Asuryani) - Seer Council
# ===========================================================================

def build_aeldari(owner, register, state=None, model_positions=None):
    """The Aeldari (Asuryani) list the user supplied (revised 2026-08-23):
    five characters - Asurmen, Eldrad Ulthran, a Farseer, Jain Zar and
    Lhykhis - plus Guardian Defenders, Storm Guardians, Dark Reapers, Dire
    Avengers, a Falcon, Howling Banshees, Rangers, Shining Spears, Shroud
    Runners, Striking Scorpions, two Warlock Conclaves, Warlock Skyrunners,
    Warp Spiders and Wraithguard. 20 list entries, 13 units once the five
    attachments are merged (19.01), 74 models, 1900 pts here against the
    list's own 1930.

    WHAT CHANGED IN THE REVISION: the Avatar of Khaine and the Fire Dragons
    are gone; Dark Reapers, Rangers, Shining Spears, Shroud Runners and a
    Warlock Skyrunner join. Every other entry, and every attachment, is
    unchanged. The Warlock Skyrunner stands ALONE: its LEADER line is a JOIN
    that names Windriders only, and this list fields none - a legal
    standalone unit, not an attachment that failed.

    THIS IS WHAT MAKES THE AELDARI WORK REACHABLE IN PLAY. Every one of the
    Aeldari datasheet entries in CLAUDE.md ends with the same open point -
    "built and tested, but in no demo army, so none of it is exercised in a
    game" - and so do Battle Focus, all six Seer Council stratagems and
    Strands of Fate. The army rule in particular derives ASURYANI from units
    that carry the flag (see game/battle_focus.py's qualifying_players()), so
    it starts working for whoever fields this list, without a setting.

    POINTS: 12 of the 19 distinct entries disagree with the transcribed
    official points list - Eldrad 120 vs 130, Farseer 70 vs 65, Jain Zar 120
    vs 105, Guardian Defenders 100 vs 90, Dark Reapers 90 vs 100, Howling
    Banshees 95 vs 85, Rangers 55 vs 60, Shining Spears 110 vs 100, Shroud
    Runners 80 vs 90, Striking Scorpions 85 vs 75, Warlock Skyrunners 45 vs
    55, Wraithguard 160 vs 145. Note the revision's mismatches run BOTH ways,
    which is worth stating: the earlier list was uniformly dearer than the
    transcription, so "the app rounds up" was a tempting story, and the five
    new entries falsify it. Same kind of app-vs-list mismatch both other
    armies already carry, and handled the same way: named here, not used to
    overwrite game/factions/aeldari_points.py. The COMPOSITION is followed
    model for model, which is what the tests check.

    ATTACHMENTS (user: "farseer in die guardian defenders / warlock
    conclaive 1 in die guardian defenders / eldrad in die storm guardians /
    warlock conclaive 2 in die storm guardians / die phoenix lords in ihre
    passenden squads"). The order below is not cosmetic - see the note on
    the Guardian Defenders block.
    """
    # The Falcon's own build: "Pulse Laser, Wraithbone hull, Bright Lance,
    # Shuriken Cannon" - the printed baseline is Pulse Laser + Wraithbone Hull
    # + Scatter Laser + Twin Shuriken Catapult, so the list takes both of the
    # datasheet's independent swaps (they give up different weapons, which is
    # exactly why they can be taken together). It carries nothing: the list
    # embarks no unit in it.
    falcon_choices = {"Falcon": {FALCON_SCATTER_TO_BRIGHT_LANCE: 1,
                                FALCON_CATAPULT_TO_SHURIKEN_CANNON: 1}}
    # "5x Wraithguard: 5 with Close Combat Weapon, D-Scythe" - all five, which
    # is the only legal way to take this swap ("ALL of the models in this unit
    # can EACH have their wraithcannon replaced").
    wraithguard_choices = {"Wraithguard": {WRAITHGUARD_TO_D_SCYTHE: 5}}
    # The Shining Spear Exarch's listed "Shimmershield, Shuriken Cannon, Star
    # Lance" is THREE printed sentences and they are not all the same kind of
    # thing, which is the one trap on this datasheet: the star lance and the
    # shuriken cannon are weapon swaps (they give up different weapons, so they
    # can be taken together), but the shimmershield is a pure ADDITION and is
    # modelled as Gear, not as a WargearOption - it takes nothing away and only
    # sets the 4+ invulnerable save. So it goes in the gear columns below, and
    # this is the first Aeldari entry that uses them at all.
    #
    # "Star Lance" appears twice in the built loadout and that is correct: the
    # lance is one printed weapon with a ranged row AND a melee row, exactly
    # like the laser lance it replaces.
    shining_spears_choices = {"Shining Spear Exarch": {
        SHINING_SPEAR_TO_STAR_LANCE: 1,
        SHINING_SPEAR_TO_SHURIKEN_CANNON: 1,
    }}
    army = [
        # (datasheet, gear-slot model line name (or None), gear list, color, wargear choices (or None))
        # The Shining Spears' shimmershield is the only non-weapon gear in this
        # roster; every other entry leaves the two gear columns None.
        #
        # Dark Reapers, Rangers and Shroud Runners are listed with exactly their
        # printed defaults - Reaper Launchers on all five including the Exarch,
        # and no wargear options at all on the other two - so there is nothing
        # to choose for any of them. Checked rather than assumed.
        (DARK_REAPERS, None, None, (60, 60, 95), None),
        (FALCON, None, None, (100, 140, 190), falcon_choices),
        (RANGERS, None, None, (140, 130, 105), None),
        (SHINING_SPEARS, "Shining Spear Exarch", [SHINING_SPEAR_SHIMMERSHIELD],
         (240, 200, 90), shining_spears_choices),
        (SHROUD_RUNNERS, None, None, (120, 155, 130), None),
        # The Striking Scorpion Exarch's listed "Scorpion chainsword,
        # Scorpion's claw, Shuriken pistol" is the datasheet's printed
        # default, so there is nothing to choose - checked rather than assumed,
        # since both of this datasheet's options replace exactly those three.
        (STRIKING_SCORPIONS, None, None, (110, 180, 100), None),
        # Listed with its printed witchblade rather than the singing spear the
        # two foot Conclaves take - the one swap this datasheet has, not taken.
        (WARLOCK_SKYRUNNERS, None, None, (170, 140, 220), None),
        (WRAITHGUARD, None, None, (225, 225, 195), wraithguard_choices),
    ]
    _check_positions("Aeldari", model_positions, len(army))

    unit_counts = {}
    for index, (datasheet, leader_line_name, gear_list, color, choices) in enumerate(army):
        unit_counts[datasheet.name] = unit_counts.get(datasheet.name, 0) + 1
        gear = {leader_line_name: gear_list} if leader_line_name is not None else None
        positions = model_positions[index] if model_positions and index < len(model_positions) else []
        first_x, first_y = positions[0] if positions else (0.0, 0.0)
        squad = build_squad(
            datasheet, owner=owner, gear=gear, choices=choices,
            name=unit_name(owner, f"{datasheet.name} {unit_counts[datasheet.name]}"),
            x_in=first_x, y_in=first_y, color=color,
            # Which copy of this datasheet the list is buying - the same
            # running count that already names the squad. The official points
            # list charges more for later copies of some units (see
            # game/factions/points.py), so this is what makes Squad.points
            # come out right rather than always quoting the 1st-unit price.
            unit_index=unit_counts[datasheet.name],
        )
        _apply_positions(squad, model_positions, index)
        register(squad)

    def aeldari_squad(datasheet, color, name=None, choices=None, composition_index=0, unit_index=1):
        """One unit of this list, built the way the loop above builds them.

        The five attached units below are built here rather than in `army` for
        the reason the T'au roster's own Coldstar/Farsight pairs were: an entry
        in that table registers its squad immediately, and an attachment has to
        happen BEFORE registration so the scene records one merged unit rather
        than two."""
        return build_squad(
            datasheet, owner=owner, choices=choices, composition_index=composition_index,
            name=name or unit_name(owner, f"{datasheet.name} 1"), color=color, unit_index=unit_index,
        )

    # Guardian Defenders + Farseer + Warlock Conclave 1.
    #
    # THE ORDER IS LOAD-BEARING, and it is the two printed texts rather than a
    # preference. A Warlock Conclave's LEADER ability is worded as a JOIN that
    # states its own limit ("a unit cannot have more than one WARLOCK CONCLAVE
    # unit joined to it"), so it may join a unit a Farseer already leads. A
    # Farseer attaching is an ordinary 19.01 attachment, and a plain Farseer's
    # LEADER line carries no permission to join a unit something is already
    # attached to - only Eldrad's does. So Farseer first, Conclave second is
    # legal and the reverse is not; can_attach() enforces exactly that (see
    # game/attached_units.py's _join_not_bound_by_leader_slot(), which quotes
    # both texts).
    #
    # The Guardian Defenders' listed build - 10 Guardians on Shuriken Catapults
    # and a Heavy Weapon Platform on a Bright Lance - is the printed default,
    # and the Farseer's "Singing Spear" is his one swap.
    guardians_squad = aeldari_squad(GUARDIAN_DEFENDERS, (90, 170, 210))
    guardians_squad = attached_units.attach(
        aeldari_squad(FARSEER, (150, 130, 200),
                      choices={"Farseer": {FARSEER_WITCHBLADE_TO_SPEAR: 1}}),
        guardians_squad, game_state=state)
    guardians_squad = attached_units.attach(
        aeldari_squad(WARLOCK_CONCLAVE, (150, 120, 200), name=unit_name(owner, "Warlock Conclave 1"),
                      choices={"Warlock": {WARLOCK_WITCHBLADE_TO_SPEAR: 2}}, unit_index=1),
        guardians_squad, game_state=state)
    register(guardians_squad)

    # Storm Guardians + Eldrad Ulthran + Warlock Conclave 2. Either order is
    # legal here - Eldrad's LEADER line explicitly allows him to join a unit a
    # WARLOCKS unit has already joined - but they are attached in the same
    # order as above so the two blocks read the same way.
    #
    # The listed build is 2 models with Flamer, 2 with Fusion Gun, 2 OTHER
    # models with Power Sword (keeping their Shuriken Pistol), 4 with the
    # printed loadout, plus the Serpent's Scale Platform. Every special
    # weapon sits on its own model.
    #
    # The two pistol swaps give up the SAME weapon, so they share a cursor
    # and take models 0-1 and 2-3 by themselves. The sword swap gives up a
    # different weapon (the close combat weapon) and would therefore start
    # its own cursor back at model 0, landing swords on the flamer models -
    # so the sword models are named explicitly, which is how an army list
    # says "different models" (see build_squad()). Checked, not assumed.
    storm_squad = aeldari_squad(STORM_GUARDIANS, (110, 190, 200), choices={
        "Storm Guardian": {
            STORM_GUARDIAN_PISTOL_TO_FLAMER: 2,
            STORM_GUARDIAN_PISTOL_TO_FUSION: 2,
            STORM_GUARDIAN_CCW_TO_POWER_SWORD: [4, 5],
        },
    })
    storm_squad = attached_units.attach(
        aeldari_squad(ELDRAD_ULTHRAN, (170, 140, 210)), storm_squad, game_state=state)
    storm_squad = attached_units.attach(
        aeldari_squad(WARLOCK_CONCLAVE, (150, 120, 200), name=unit_name(owner, "Warlock Conclave 2"),
                      choices={"Warlock": {WARLOCK_WITCHBLADE_TO_SPEAR: 2}}, unit_index=2),
        storm_squad, game_state=state)
    register(storm_squad)

    # The three Phoenix Lords, each with the one unit its own LEADER line names
    # (user: "die phoenix lords in ihre passenden squads") - which is also the
    # pairing table attach() checks, so a wrong guess here would be refused
    # rather than silently built.
    #
    # Dire Avengers: the Exarch's listed "2x Avenger Shuriken Catapult" is the
    # datasheet's pure-addition option, taken on top of his printed one.
    avengers_squad = aeldari_squad(DIRE_AVENGERS, (70, 150, 220), choices={
        "Dire Avenger Exarch": {DIRE_AVENGER_SECOND_CATAPULT: 1}})
    avengers_squad = attached_units.attach(
        aeldari_squad(ASURMEN, (240, 240, 250)), avengers_squad, game_state=state)
    register(avengers_squad)

    # Howling Banshees: the Exarch trades her Banshee Blade for an Executioner
    # and keeps her Shuriken Pistol.
    banshees_squad = aeldari_squad(HOWLING_BANSHEES, (230, 220, 210), choices={
        "Howling Banshee Exarch": {BANSHEE_BLADE_TO_EXECUTIONER: 1}})
    banshees_squad = attached_units.attach(
        aeldari_squad(JAIN_ZAR, (235, 225, 215)), banshees_squad, game_state=state)
    register(banshees_squad)

    # Warp Spiders: the Exarch trades his Death Spinner for a Powerblade Array.
    spiders_squad = aeldari_squad(WARP_SPIDERS, (200, 200, 230), choices={
        "Warp Spider Exarch": {WARP_SPIDER_TO_POWERBLADE_ARRAY: 1}})
    spiders_squad = attached_units.attach(
        aeldari_squad(LHYKHIS, (180, 190, 220)), spiders_squad, game_state=state)
    register(spiders_squad)


# ===========================================================================
# Orks - War Horde
# ===========================================================================

def build_orks(owner, register, state=None, model_positions=None):
    """The Ork army list the user supplied:

      Char1 Beastboss              -> attached to Beast Snagga Boyz
      Char2 Warboss                -> attached to Boyz 1
      Char3 Warboss in Mega Armour -> attached to Meganobz
      1x Beast Snagga Boyz (10), 2x Boyz (10, Boss Nob w/ Power Klaw),
      1x Battlewagon ('Ard Case + 4x Big Shoota), 1x Deff Dread,
      6x Deffkoptas, 1x Flash Gitz (10), 2x Gretchin (11), 1x Kill Rig,
      6x Meganobz, 1x Stormboyz (10, Boss Nob w/ Power Klaw),
      6x Tankbustas, 2x Trukk, 2x Warbikers (3 each, + Power Klaw)

    Every item on that list is modeled. The three that were missing once - the
    Warboss's Attack squig, the Battlewagon's Zzap gun and the Flash Gitz'
    Ammo Runt - had their stat lines/rules text supplied afterwards and are
    built here. The Zzap gun in particular is the first weapon in this engine
    with a dice-rolled Strength ("S D6+6"), see
    WeaponProfile.strength_notation.

    Points: the list's own per-unit numbers run consistently above this
    project's transcribed published list (e.g. Trukk 70 vs 55, Tankbustas
    140 vs 125, Kill Rig 155 vs 145, Deffkoptas 160 vs 140) - a newer
    revision. Same treatment as the other two lists: named as an informative
    mismatch, with the transcribed data left as the single source of truth
    (see game/factions/orks_points.py).

    Transports (user instruction): "die ki soll die beast boyz + beast boss
    bevorzugt in den kill rig packen und die meganobs + megaboss in
    megaarmor in den battle wagon" - declared below as EMBARK hints, which
    ai/deployment_ai.py's own _transport_affinity() honours as the scene's
    answer AND, since this instruction, treats as exclusive (a hinted unit
    is never loaded into some other transport that happens to be processed
    first). Both fit: Beast Snagga Boyz + Beastboss = 11 models against the
    Kill Rig's capacity 11, all BEAST SNAGGA INFANTRY as that datasheet
    requires; Meganobz + Warboss in Mega Armour = 7 MEGA ARMOUR models = 14
    capacity against the Battlewagon's 22.

    The two Trukks carry nobody by declaration - the AI fills them from
    whatever short-ranged infantry is left, which is what its own
    _transport_affinity() is for.
    """
    # 14 units once the three attachments are merged; the count is what
    # --no-deployment would need a position list for, and there is none.
    _check_positions("Orks", model_positions, 0)

    GRETCHIN_COLOR = (140, 110, 70)
    STORMBOYZ_COLOR = (110, 150, 70)
    WARBIKERS_COLOR = (150, 130, 60)
    BOYZ_COLOR = (70, 140, 60)
    PAINBOY_COLOR = (150, 65, 105)
    WARBOSS_COLOR = (170, 60, 60)
    MEGANOBZ_COLOR = (120, 100, 130)
    DEFF_DREAD_COLOR = (80, 80, 90)
    DEFFKOPTAS_COLOR = (130, 145, 165)
    TANKBUSTAS_COLOR = (160, 110, 40)
    BEAST_SNAGGA_COLOR = (120, 145, 55)
    BEASTBOSS_COLOR = (185, 80, 45)
    KILL_RIG_COLOR = (100, 85, 65)
    BATTLEWAGON_COLOR = (75, 95, 55)
    FLASH_GITZ_COLOR = (170, 150, 55)

    # --- Kill Rig, and the Beast Snagga Boyz + Beastboss that ride in it ---
    kill_rig_squad = build_squad(
        KILL_RIG, owner=owner, name=unit_name(owner, "Kill Rig 1"), color=KILL_RIG_COLOR,
    )
    kill_rig_token = kill_rig_squad.models[0]
    register(kill_rig_squad)

    beast_snagga_squad = build_squad(
        BEAST_SNAGGA_BOYZ, owner=owner, name=unit_name(owner, "Beast Snagga Boyz 1"),
        color=BEAST_SNAGGA_COLOR,
    )
    beastboss_squad = build_squad(
        BEASTBOSS, owner=owner, name=unit_name(owner, "Beastboss 1"), color=BEASTBOSS_COLOR,
    )
    # The Beastboss's own Leader ability (24.22) lists Beast Snagga Boyz, so
    # attach() accepts the pairing. Attached BEFORE the transport hint so the
    # capacity check sees the finished 11-model unit.
    beast_snagga_squad = attached_units.attach(beastboss_squad, beast_snagga_squad, game_state=state)
    register(beast_snagga_squad, pregame.EMBARK, transport=kill_rig_token)

    # --- Battlewagon, and the Meganobz + Warboss in Mega Armour inside ---
    battlewagon_squad = build_squad(
        BATTLEWAGON, owner=owner, name=unit_name(owner, "Battlewagon 1"), color=BATTLEWAGON_COLOR,
        gear={"Battlewagon": [BATTLEWAGON_ARD_CASE]},
        choices={"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1, BATTLEWAGON_ADD_ZZAP_GUN: 1}},
    )
    battlewagon_token = battlewagon_squad.models[0]
    register(battlewagon_squad)

    meganobz_squad = build_squad(
        MEGANOBZ, owner=owner, composition_index=1, name=unit_name(owner, "Meganobz 1"),
        color=MEGANOBZ_COLOR,
    )
    warboss_mega_squad = build_squad(
        WARBOSS_MEGA_ARMOUR, owner=owner, name=unit_name(owner, "Warboss in Mega Armour 1"),
        color=WARBOSS_COLOR,
    )
    # Its Leader ability lists Meganobz. Unlike the old Trukk arrangement -
    # where 6 MEGA ARMOUR Meganobz alone already filled a Trukk's capacity 12
    # and the leader had to be left out entirely - the Battlewagon's 22 has
    # room for all 14 capacity this attached unit costs.
    meganobz_squad = attached_units.attach(warboss_mega_squad, meganobz_squad, game_state=state)
    register(meganobz_squad, pregame.EMBARK, transport=battlewagon_token)

    # --- One 20-strong Boyz mob, led by BOTH the Warboss and the Painboy ---
    # composition_index=1 is the 20-model build, and it is load-bearing here
    # rather than just bigger: Boyz' own "Bodyguard" ability only allows a
    # SECOND Leader on a unit with a Starting Strength of 20, and only if one
    # of the two is a WARBOSS. Both conditions are checked for real - see
    # game/attached_units.py's _bodyguard_allows_second_leader().
    boyz_squad = build_squad(
        BOYZ, owner=owner, composition_index=1,
        choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}},
        name=unit_name(owner, "Boyz 1"), color=BOYZ_COLOR, unit_index=1,
    )
    warboss_squad = build_squad(
        WARBOSS, owner=owner, name=unit_name(owner, "Warboss 1"), color=WARBOSS_COLOR,
        choices={"Warboss": {WARBOSS_ADD_ATTACK_SQUIG: 1}},
    )
    painboy_squad = build_squad(
        PAINBOY, owner=owner, name=unit_name(owner, "Painboy 1"), color=PAINBOY_COLOR,
        gear={"Painboy": [PAINBOY_GROT_ORDERLY]},
    )
    # Warboss FIRST: the exception needs a WARBOSS among the two, and
    # attaching him first means the Painboy's own check finds one already
    # there rather than depending on the order the pair happens to arrive in
    # (it accepts either, but this is the order the rule text reads in).
    boyz_squad = attached_units.attach(warboss_squad, boyz_squad, game_state=state)
    boyz_squad = attached_units.attach(painboy_squad, boyz_squad, game_state=state)
    register(boyz_squad)

    # --- The rest of the roster ---
    for index in (1, 2):
        register(build_squad(
            GRETCHIN, owner=owner, name=unit_name(owner, f"Gretchin {index}"),
            color=GRETCHIN_COLOR, unit_index=index,
        ))

    # composition_index=0 is the 3-model composition (1 Boss Nob on Warbike +
    # 2 Warbikers), which is what this list fields twice.
    for index in (1, 2):
        register(build_squad(
            WARBIKERS, owner=owner, composition_index=0,
            choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}},
            name=unit_name(owner, f"Warbikers {index}"), color=WARBIKERS_COLOR, unit_index=index,
        ))

    register(build_squad(
        STORMBOYZ, owner=owner, composition_index=1,
        choices={"Boss Nob": {STORMBOYZ_CHOPPA_TO_POWER_KLAW: 1}},
        name=unit_name(owner, "Stormboyz 1"), color=STORMBOYZ_COLOR,
    ))

    register(build_squad(
        DEFF_DREAD, owner=owner, name=unit_name(owner, "Deff Dread 1"), color=DEFF_DREAD_COLOR,
    ))

    # composition_index=1 is the 6-model build this list fields; every model
    # keeps the printed Kopta rokkits + Slugga + Spinnin' blades, so there
    # are no wargear choices to make. DEEP STRIKE (24.09), so the deployment
    # AI is free to hold it in Strategic Reserves.
    register(build_squad(
        DEFFKOPTAS, owner=owner, composition_index=1,
        name=unit_name(owner, "Deffkoptas 1"), color=DEFFKOPTAS_COLOR,
    ))

    # composition_index=1 is the 10-model build this list fields.
    register(build_squad(
        FLASH_GITZ, owner=owner, composition_index=1, name=unit_name(owner, "Flash Gitz 1"),
        color=FLASH_GITZ_COLOR, gear={"Kaptin": [FLASH_GITZ_AMMO_RUNT]},
    ))

    # This list's own custom Tankbusta loadout - Boss Nob w/ Smash Hammer
    # instead of a 2nd Rokkit Pistol, one Tankbusta w/ an extra Rokkit
    # Launcha (see TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER/
    # TANKBUSTAS_ADD_ROKKIT_LAUNCHA's own notes).
    register(build_squad(
        TANKBUSTAS, owner=owner, name=unit_name(owner, "Tankbustas 1"), color=TANKBUSTAS_COLOR,
        choices={
            "Boss Nob": {TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER: 1},
            "Tankbusta": {TANKBUSTAS_ADD_ROKKIT_LAUNCHA: 1},
        },
    ))


# ===========================================================================
# Necrons - Awakened Dynasty
# ===========================================================================

def build_necrons(owner, register, state=None, model_positions=None):
    """The Necron army list the user supplied. Awakened Dynasty, 13 list
    entries, 59 models, engine total 2000 pts against the list's own 2005 -
    the per-entry differences are recorded in
    game/factions/necrons_points.py and deliberately not reconciled.

      Char1 C'tan Shard of the Void Dragon   (330 in the list, 345 here)
      Char2 Illuminor Szeras                 (165 / 175)
      Char3 Overlord, Resurrection orb + Voidscythe   (85 / 90)
      Char4 Plasmancer                       (55 / 55)
      Char5 Technomancer                     (80 / 80)

    THREE ATTACHED UNITS (rule 19.01), assigned by the user:
      Overlord     -> Lychguard        (and with him NOBLE, so Guardian
                                        Protocols finally has a carrier)
      Technomancer -> Necron Warriors  (Rites of Reanimation: FNP 5+)
      Plasmancer   -> Immortals        (Harbinger of Destruction: 5+ crits)
    All three are on the leaders' own printed LEADER lines - checked
    against attached_units.can_attach() rather than assumed.

    THE OTHER TWO CHARACTERS STAND ALONE, and that is a statement rather
    than an omission: Illuminor Szeras has no printed LEADER line at all
    (his Aura is how he helps, which is a range test, not an attachment)
    and neither does the C'tan Shard.

    This is also what switches Command Protocols on: the detachment rule
    only pays a unit "while a NECRONS CHARACTER model is leading" it, so
    before these three attachments it had nothing to apply to anywhere in
    the army.

    NO RESERVES AND NO TRANSPORTS: the list has neither, so every unit
    deploys normally. That is also why ai/deployment_ai.py needs no
    TRANSPORT_PASSENGER_PRIORITY entry for this army.
    """
    _check_positions("Necrons", model_positions, 0)

    VOID_DRAGON_COLOR = (90, 110, 140)
    SZERAS_COLOR = (150, 140, 90)
    OVERLORD_COLOR = (170, 150, 70)
    PLASMANCER_COLOR = (110, 170, 190)
    TECHNOMANCER_COLOR = (120, 160, 140)
    IMMORTALS_COLOR = (100, 130, 150)
    WARRIORS_COLOR = (90, 120, 130)
    WRAITHS_COLOR = (150, 170, 180)
    DOOMSDAY_ARK_COLOR = (80, 100, 120)
    LOKHUST_COLOR = (110, 120, 100)
    LOKHUST_HEAVY_COLOR = (130, 130, 100)
    LYCHGUARD_COLOR = (160, 140, 60)
    SKORPEKH_COLOR = (120, 90, 90)

    register(build_squad(
        CTAN_SHARD_OF_THE_VOID_DRAGON, owner=owner,
        name=unit_name(owner, "C'tan Shard of the Void Dragon 1"), color=VOID_DRAGON_COLOR,
    ))
    register(build_squad(
        ILLUMINOR_SZERAS, owner=owner, name=unit_name(owner, "Illuminor Szeras 1"),
        color=SZERAS_COLOR,
    ))
    # The Overlord, Plasmancer and Technomancer are built further down,
    # each one attached to the unit it leads - an attachment has to happen
    # BEFORE registration, so the scene records one merged unit rather
    # than two. Same arrangement the Aeldari list's five attachments use.
    #
    # "Resurrection orb, Voidscythe": the voidscythe swap gives up BOTH the
    # tachyon arrow and the Overlord's blade, which is what makes him
    # eligible for the orb at all - the Gear item checks for the arrow and
    # runs after the weapon swaps, so the printed precondition enforces
    # itself. See game/factions/necrons.py's _equip_resurrection_orb.

    # 10 Immortals with gauss blasters - the printed default, so no
    # choices - led by the Plasmancer.
    immortals_squad = build_squad(
        IMMORTALS, owner=owner, composition_index=1, name=unit_name(owner, "Immortals 1"),
        color=IMMORTALS_COLOR,
    )
    register(attached_units.attach(
        build_squad(PLASMANCER, owner=owner, name=unit_name(owner, "Plasmancer 1"),
                    color=PLASMANCER_COLOR),
        immortals_squad, game_state=state,
    ))
    # 20 Necron Warriors with gauss flayers - likewise the default - led by
    # the Technomancer.
    warriors_squad = build_squad(
        NECRON_WARRIORS, owner=owner, composition_index=1,
        name=unit_name(owner, "Necron Warriors 1"), color=WARRIORS_COLOR,
    )
    register(attached_units.attach(
        build_squad(TECHNOMANCER, owner=owner, name=unit_name(owner, "Technomancer 1"),
                    color=TECHNOMANCER_COLOR),
        warriors_squad, game_state=state,
    ))
    # 6 Canoptek Wraiths with vicious claws, no particle casters or
    # beamers - the list adds none, so the default loadout stands.
    register(build_squad(
        CANOPTEK_WRAITHS, owner=owner, composition_index=1,
        name=unit_name(owner, "Canoptek Wraiths 1"), color=WRAITHS_COLOR,
    ))
    register(build_squad(
        DOOMSDAY_ARK, owner=owner, name=unit_name(owner, "Doomsday Ark 1"),
        color=DOOMSDAY_ARK_COLOR,
    ))
    # 6 Lokhust Destroyers with gauss cannons - the datasheet has no
    # wargear options at all.
    register(build_squad(
        LOKHUST_DESTROYERS, owner=owner, composition_index=3,
        name=unit_name(owner, "Lokhust Destroyers 1"), color=LOKHUST_COLOR,
    ))
    # "1 with Enmitic exterminator, 2 with Gauss destructor" - exactly ONE
    # model takes the swap, which is why the count is 1 rather than the
    # unit size.
    register(build_squad(
        LOKHUST_HEAVY_DESTROYERS, owner=owner, composition_index=2,
        name=unit_name(owner, "Lokhust Heavy Destroyers 1"), color=LOKHUST_HEAVY_COLOR,
        choices={"Lokhust Heavy Destroyer": {LOKHUST_HEAVY_TO_ENMITIC_EXTERMINATOR: 1}},
    ))
    # "5 with Dispersion shield, Hyperphase sword" - one printed option
    # that is half a weapon swap and half a Gear item, so it takes both
    # columns. The Gear carries all_models=True; without it four of the
    # five would silently have no invulnerable save.
    lychguard_squad = build_squad(
        LYCHGUARD, owner=owner, name=unit_name(owner, "Lychguard 1"), color=LYCHGUARD_COLOR,
        choices={"Lychguard": {LYCHGUARD_TO_HYPERPHASE_SWORD: 5}},
        gear={"Lychguard": [LYCHGUARD_DISPERSION_SHIELD]},
    )
    # The Overlord joins them, which is what gives Guardian Protocols the
    # NOBLE its own text asks for - without him the Lychguard have the
    # ability printed and it never fires.
    register(attached_units.attach(
        build_squad(
            OVERLORD, owner=owner, name=unit_name(owner, "Overlord 1"), color=OVERLORD_COLOR,
            choices={"Overlord": {OVERLORD_TO_VOIDSCYTHE: 1}},
            gear={"Overlord": [OVERLORD_RESURRECTION_ORB]},
        ),
        lychguard_squad, game_state=state,
    ))
    # 3 Skorpekh Destroyers, no Plasmacyte - the list takes none.
    register(build_squad(
        SKORPEKH_DESTROYERS, owner=owner, name=unit_name(owner, "Skorpekh Destroyers 1"),
        color=SKORPEKH_COLOR,
    ))



# ===========================================================================
# T'au Empire - Retaliation Cadre
# ===========================================================================

def build_tau(owner, register, state=None, model_positions=None):
    """The T'au Empire (Retaliation Cadre) list the user supplied on
    2026-07-31 - Player 1's roster until the Aeldari replaced it wholesale.

    RESTORED, NOT REWRITTEN (user: "wo ist die Tau-Liste?"). The FACTION never
    went anywhere - 14 datasheets, Retaliation Cadre with all six stratagems,
    a 43-entry points list and every ability from For The Greater Good to the
    Riptide's Nova charge are built and tested. What the list swap deleted was
    the ROSTER, and this is that roster recovered from the initial commit,
    entry for entry, with only the owner parameterised. Nothing here is a new
    judgement about what the list should contain.

    Char1 Cadre Fireblade      -> attached to the Breacher Team, both aboard
                                  the Devilfish (user: "den fireblade zu den
                                  breachern im devilfish")
    Char2 Commander in Coldstar -> attached to the Crisis Starscythes, both in
                                  Strategic Reserves (user: "den coldstar zu
                                  den starsythe in reserve")
    Char3 Commander Farsight   -> attached to the Crisis Sunforges
    plus Breacher Team, Strike Team, Kroot Carnivores, Pathfinder Team,
    Stealth Battlesuits, a Ghostkeel, a Riptide, The Twin Lance and a
    Devilfish.

    The Coldstar carries the Starflare Ignition System Enhancement - the one
    Enhancement this engine actually grants rather than merely records (see
    game/starflare_ignition.py), and the reason the Enhancement log line in
    main() exists at all.

    Points: the supplied list's own per-unit numbers disagree with the
    transcribed official ones in a few places (the Ghostkeel's build prices at
    165 against the list's 160, the Devilfish likewise) - named as an
    informational mismatch and NOT used to overwrite
    game/factions/tau_empire_points.py, exactly as the other three lists
    handle the same disagreement.
    """
    guardian_shield_gear = ["Guardian Drone", "Shield Drone"]
    # The printed default for a Ghostkeel is Fusion Collider + Twin T'au
    # Flamer; this list's build ("Cyclic ion raker, Twin fusion blaster") is
    # reproduced explicitly through both swaps rather than by trusting the
    # coded default to match it.
    ghostkeel_choices = {"Ghostkeel Battlesuit": {GHOSTKEEL_FUSION_TO_ION_RAKER: 1,
                                                  GHOSTKEEL_FLAMER_TO_FUSION_BLASTER: 1}}
    # Pathfinder Team: the Shas'ui trades his Pulse carbine for a
    # semi-automatic grenade launcher and carries two Shield Drones plus a
    # Grav-inhibitor Drone; three rank-and-file trade their carbines for Rail
    # rifles.
    pathfinder_gear = ["Shield Drone", "Shield Drone", "Grav-inhibitor Drone"]
    pathfinder_choices = {
        "Pathfinder Shas'ui": {PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER: 1},
        "Pathfinder": {PATHFINDER_CARBINE_TO_RAIL_RIFLE: 3},
    }
    # Riptide: "Ion accelerator, 2x Missile pod, Twin fusion blaster" - the
    # accelerator replaces the heavy burst cannon, the twin fusion blaster the
    # twin plasma rifle, and the two missile pods are the datasheet's own
    # baseline Missile Drones.
    riptide_choices = {
        "Riptide Battlesuit": {RIPTIDE_BURST_TO_ION_ACCELERATOR: 1,
                               RIPTIDE_PLASMA_TO_TWIN_FUSION: 1},
    }
    army = [
        # (datasheet, gear-slot model line name (or None), gear list, color, wargear choices)
        (BREACHER_TEAM, "Breacher Fire Warrior Shas'ui", guardian_shield_gear, (220, 150, 70), None),
        (STRIKE_TEAM, "Fire Warrior Shas'ui", guardian_shield_gear, (60, 140, 200), None),
        (KROOT_CARNIVORES, None, None, (120, 90, 40), None),
        (PATHFINDER_TEAM, "Pathfinder Shas'ui", pathfinder_gear, (90, 180, 140), pathfinder_choices),
        (STEALTH_BATTLESUITS, None, None, (100, 100, 150), None),
        (GHOSTKEEL_BATTLESUIT, None, None, (130, 130, 170), ghostkeel_choices),
        (RIPTIDE_BATTLESUIT, None, None, (150, 150, 195), riptide_choices),
        (THE_TWIN_LANCE, None, None, (210, 190, 120), None),
    ]
    _check_positions("T'au Empire", model_positions, len(army))

    devilfish_choices = {"Devilfish": {DEVILFISH_SEEKER_MISSILE_OPTION: 1}}
    fireblade_gear = ["Gun Drone", "Gun Drone"]

    unit_counts = {}
    for index, (datasheet, leader_line_name, gear_list, color, choices) in enumerate(army):
        unit_counts[datasheet.name] = unit_counts.get(datasheet.name, 0) + 1
        gear = {leader_line_name: gear_list} if leader_line_name is not None else None
        positions = model_positions[index] if model_positions and index < len(model_positions) else []
        first_x, first_y = positions[0] if positions else (0.0, 0.0)
        squad = build_squad(
            datasheet, owner=owner, gear=gear, choices=choices,
            name=unit_name(owner, f"{datasheet.name} {unit_counts[datasheet.name]}"),
            x_in=first_x, y_in=first_y, color=color,
            unit_index=unit_counts[datasheet.name],
        )
        _apply_positions(squad, model_positions, index)
        if datasheet is BREACHER_TEAM:
            # The Devilfish and the Fireblade are built alongside the unit that
            # rides in it: 10 Breacher Fire Warriors + the Fireblade is 11 of
            # its 12-model capacity, and the attachment has to happen BEFORE
            # registration so the scene records one merged unit.
            devilfish_squad = build_squad(
                DEVILFISH, owner=owner, choices=devilfish_choices,
                name=unit_name(owner, "Devilfish 1"), color=color,
            )
            devilfish_token = devilfish_squad.models[0]
            register(devilfish_squad)
            squad = attached_units.attach(
                build_squad(CADRE_FIREBLADE, owner=owner,
                            gear={"Cadre Fireblade": fireblade_gear},
                            name=unit_name(owner, "Cadre Fireblade 1"), color=color),
                squad, game_state=state)
            register(squad, pregame.EMBARK, transport=devilfish_token)
        else:
            register(squad)

    # The Coldstar Commander, with the Starflare Ignition System Enhancement,
    # arriving from Strategic Reserves (03.02) together with the Starscythes
    # he leads.
    coldstar_squad = build_squad(
        COMMANDER_IN_COLDSTAR_BATTLESUIT, owner=owner,
        gear={"Commander in Coldstar Battlesuit": ["Shield Drone", "Shield Drone"]},
        choices={"Commander in Coldstar Battlesuit": {COLDSTAR_ADD_2X_BURST_CANNON: 1,
                                                      COLDSTAR_ADD_CYCLIC_ION_BLASTER: 1}},
        name=unit_name(owner, "Commander in Coldstar Battlesuit 1"), color=(200, 170, 90),
    )
    starflare_ignition.grant(coldstar_squad)
    starscythe_lines = ("Crisis Starscythe Shas'vre", "Crisis Starscythe Shas'ui (1)",
                        "Crisis Starscythe Shas'ui (2)")
    starscythe_squad = build_squad(
        CRISIS_STARSCYTHE, owner=owner,
        gear={
            "Crisis Starscythe Shas'vre": ["Marker Drone", "Shield Drone"],
            "Crisis Starscythe Shas'ui (1)": ["Gun Drone", "Shield Drone"],
            "Crisis Starscythe Shas'ui (2)": ["Gun Drone", "Shield Drone"],
        },
        choices={line: {STARSCYTHE_FLAMER_TO_BURST: 1} for line in starscythe_lines},
        name=unit_name(owner, "Crisis Starscythe Battlesuits 1"), color=(170, 130, 200),
    )
    starscythe_squad = attached_units.attach(coldstar_squad, starscythe_squad, game_state=state)
    register(starscythe_squad, pregame.RESERVES)

    # Commander Farsight and the Sunforges he leads, deploying normally.
    sunforge_squad = build_squad(
        CRISIS_SUNFORGE, owner=owner,
        gear={
            "Crisis Sunforge Shas'vre": ["Marker Drone", "Shield Drone"],
            "Crisis Sunforge Shas'ui (1)": ["Gun Drone", "Shield Drone"],
            "Crisis Sunforge Shas'ui (2)": ["Gun Drone", "Shield Drone"],
        },
        name=unit_name(owner, "Crisis Sunforge Battlesuits 1"), color=(200, 120, 90),
    )
    register(attached_units.attach(
        build_squad(COMMANDER_FARSIGHT, owner=owner,
                    name=unit_name(owner, "Commander Farsight 1"), color=(220, 140, 80)),
        sunforge_squad, game_state=state))


class ArmyList:
    """One selectable list: what to call it, what to badge it with, and how
    to build it for whichever player picked it.

    `detachment_setting` is the name of the config constant that says WHO
    fields this detachment - see apply_to_config(). None for the Orks, whose
    War Horde needs no such setting: its rule and stratagems gate on the
    units' own ORKS keyword, so there is nothing to declare (game/war_horde.py
    records that this only works because War Horde is the only Ork detachment
    modelled)."""

    def __init__(self, key, name, faction_keyword, army_rule, detachment, build,
                 detachment_setting=None):
        self.key = key
        self.name = name
        self.faction_keyword = faction_keyword
        self.army_rule = army_rule
        self.detachment = detachment
        self.build = build
        self.detachment_setting = detachment_setting


ARMY_LISTS = [
    ArmyList(AELDARI, "Aeldari", "AELDARI", "Battle Focus", "Seer Council",
             build_aeldari, detachment_setting="SEER_COUNCIL_PLAYERS"),
    ArmyList(ORKS_ARMY, "Orks", "ORKS", "Waaagh!", "War Horde", build_orks),
    ArmyList(NECRONS_ARMY, "Necrons", "NECRONS", "Reanimation Protocols", "Awakened Dynasty",
             build_necrons, detachment_setting="AWAKENED_DYNASTY_PLAYERS"),
    # No detachment setting: Retaliation Cadre's Bonded Heroes gates on the
    # BATTLESUIT keyword and its stratagems on T'AU EMPIRE, so like War Horde
    # there is nothing about it to declare (see game/retaliation_cadre.py,
    # which records that this holds only while it is the faction's one
    # modelled detachment).
    ArmyList(TAU_ARMY, "T'au Empire", "T'AU EMPIRE", "For The Greater Good", "Retaliation Cadre",
             build_tau),
]

BY_KEY = {entry.key: entry for entry in ARMY_LISTS}


def get(key):
    """The ArmyList for `key`, refusing an unknown one LOUDLY.

    The alternative - falling through to a default - is how a typo turns into
    "the game silently fielded a different army", which is exactly the failure
    main()'s own player2_army() guard was written against."""
    normalised = str(key or "").strip().lower()
    if normalised not in BY_KEY:
        raise SystemExit(
            f"{key!r} is not an army list this build knows. Known lists: "
            f"{', '.join(sorted(BY_KEY))}."
        )
    return BY_KEY[normalised]


def configured_choices(config_module=None):
    """{player -> army key} as the settings and the command line leave them,
    before any selection screen runs."""
    cfg = config_module if config_module is not None else config
    return {
        "Player 1": get(getattr(cfg, "PLAYER1_ARMY", AELDARI)).key,
        "Player 2": get(getattr(cfg, "PLAYER2_ARMY", NECRONS_ARMY)).key,
    }


def apply_to_config(choices, config_module=None):
    """Write who fields which detachment into config, where the rules read it.

    The same shape - and the same reason - as maps.apply_to_config(): call it
    once at startup, before anything reads one of these constants. A detachment
    is a list-building declaration and cannot be derived from the units (a
    Necron unit looks identical in every detachment), so picking the list is
    the moment its detachment becomes known, and this is the write that makes
    the choice real. Set from scratch rather than added to, so choosing a
    different list actually takes the old detachment away."""
    cfg = config_module if config_module is not None else config
    per_setting = {}
    for entry in ARMY_LISTS:
        if entry.detachment_setting:
            per_setting.setdefault(entry.detachment_setting, [])
    for player, key in sorted(choices.items()):
        entry = get(key)
        if entry.detachment_setting:
            per_setting[entry.detachment_setting].append(player)
    for setting, players in per_setting.items():
        setattr(cfg, setting, tuple(players))
    cfg.PLAYER1_ARMY = choices.get("Player 1", getattr(cfg, "PLAYER1_ARMY", AELDARI))
    cfg.PLAYER2_ARMY = choices.get("Player 2", getattr(cfg, "PLAYER2_ARMY", NECRONS_ARMY))
    return choices


def preview_squads(key, owner, state=None):
    """Every unit this list fields for this owner, as a plain list - what the
    selection screen shows portraits and loadouts for.

    Built rather than described: a tile that listed hand-written unit names
    would be a second copy of the army list, and the first thing it would do
    is drift from the one that actually gets built. This calls the SAME
    builder main() calls, so what the tile shows is what turns up on the
    board - including the merged attached units (19.01), which is why the
    Aeldari list shows 13 tiles for 20 entries.

    `state=None` is deliberate: attach() takes an optional game_state only to
    unregister the leader's squad from a board it was never put on."""
    squads = []

    def register(squad, destination=pregame.DEPLOY, transport=None):
        squads.append(squad)
        return squad

    get(key).build(owner, register, state=state)
    return squads
