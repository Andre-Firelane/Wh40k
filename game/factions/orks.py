"""Orks faction data.

Army rule "Waaagh!" is the 2026-09 codex text (rules/orks/army_rules.md) and
is engine-wired: the Advance re-roll in game/waaagh.py, riled up in
game/riled_up.py and War Cry in game/war_cry.py - a prompt for a human at the
start of every Command phase until used, a deterministic verdict for the AI
(ai/agent_driver.py's war_cry_verdict()). The old user-supplied Waaagh! and its
WaaaghController are retired; see game/waaagh.py's docstring for what went
with them. This module holds twenty datasheets: Boyz, Warbikers,
Stormboyz, Trukk, Gretchin, Warboss, Meganobz, Warboss in Mega Armour,
Tankbustas, Deffkoptas, Deff Dread, Beast Snagga Boyz, Beastboss, Painboy,
Kill Rig, Flash Gitz, Battlewagon, and the three the Mecha Orks list added
(Bigboss, Weirdboy, Gunwagon) - every one of their UnitProfile classes sets
`waaagh = True` (user: "ALLE bisher angelegten Ork einheiten haben die
Waaagh! ability").

Beast Snagga Boyz (2026-09 codex) carry this module's first HUNTER weapon:
the Choppa prints a Standard and a Hunter profile (rule 04.01.03), the Hunter
one usable only against MONSTER/VEHICLE targets (game/weapon_profiles.py). The
codex dropped Monster Hunters and the unit's Feel No Pain; its Thump Gun is an
ADDITION per 10 models, not a swap.

Beastboss is its Leader. The 2026-09 codex gave it Keep Huntin'! (game/
boss_motivation.py - one friendly BEAST SNAGGA unit within 6" at the start or
end of its move is no longer battle-shocked and is riled up, once per battle
round per army) and Dodge Dis! (game/dodge_dis.py, read literally: the unit's
own attacks have +1 to hit); its Beast Snagga Klaw and Beastchoppa are ONE
printed weapon with [SUSTAINED HITS 2: MONSTER/VEHICLE]. The pre-codex
Beastboss rule (Might is Right's twin) and Ferocious Rage are gone, and with
them game/ferocious_rage.py.

Kill Rig (2026-09 codex) is the first MONSTER that is also a TRANSPORT. Its two
psychic abilities share one psychic roll (game/psychic_roll.py: not
battle-shocked, the Unstable Energies budget of its Wurrboy's psyker level 1, a
1 battle-shocks): Beastscent (game/beastscent.py) and Warpath (game/warpath.py).
Damaged 6, Deadly Demise D6 and Feel No Pain 5+ are generic UnitProfile fields;
its Transport line uses `transport_requires` - the INCLUSIVE counterpart of
transport_excludes - for "12 BEAST SNAGGAS INFANTRY models". The pre-codex
Spirit of Gork is gone, with game/spirit_of_gork.py.

Flash Gitz (2026-09 codex) carry a THREE-profile Snazzgun (Cutta, Dakka, Kill
Shot - rule 04.01.03) and Finderz Keeperz (game/finderz_keeperz.py: +1 AP on
their ranged attacks in your Shooting phase while they or the target are within
range of an objective). The pre-codex Gun-crazy Show-offs and the Kaptin's Ammo
Runt wargear are gone, with game/gun_crazy_showoffs.py and game/ammo_runt.py.

The five vehicles and bikes (2026-09 codex, stage E3d). Warbikers carry
High-speed Carnage (game/high_speed_carnage.py: +1 S and D on their melee
attacks in a turn they charged). Deffkoptas are MOUNTED now, not VEHICLE, with
Deff from Above (game/deff_from_above.py: +1 to hit in your Shooting phase after
an ingress move) and Aerial Manoover (game/aerial_manoover.py: into Strategic
Reserves at the end of the opponent's Fight phase). The Trukk's Pilin' Out
(game/pilin_out.py) lets its passengers make a rapid disembark move when an enemy
unit ends a move within 8" of it in the opponent's Movement phase. The
Battlewagon's Mobile Fortress and the Deff Dread's Dread 'Ard are Damage
reductions (game/damage_reduction.py - ranged attacks only for the first).
Retired with the pre-codex sheets: Drive-by Dakka, Grot Riggers, Ramshackle but
Rugged, the 'Ard Case, Piston-driven Brutality and Dead Choppy, and the Zzap Gun
that was this engine's only dice-rolled Strength.

Warboss is a single-model Character/Leader datasheet (2026-09 codex). All
three of its abilities are engine-wired: Boss' Ammo Runt (game/
boss_ammo_runt.py, the second carrier of the Boyz' Ammo Runts offer, for the
Warboss's own ranged attacks), Might Is Right (game/might_is_right.py, +3 A
and +2 S on his melee attacks in a turn his unit charged - per MODEL) and
Intimidating Motivation (game/boss_motivation.py). Its Invulnerable Save 5+
is WarbossProfile's own `invulnerable_save` field.

Meganobz is the first MEGA ARMOUR datasheet - the new `mega_armour`
UnitProfile flag makes Trukk's own "each MEGA ARMOUR model takes up the
space of 2 models" transport-capacity rule reachable for the first time
(previously documented as unreachable in TrukkProfile's own note, since no
such datasheet existed yet), see game/transport.py's
_model_capacity_cost(). Its old Krumpin' Time (Feel No Pain 5+ while the old
Waaagh! was active) was retired with that rule (2026-09 codex).

Warboss in Mega Armour is a second single-model Character/Leader datasheet,
a MEGA ARMOUR one that leads Meganobz. Krushin' Impetus (game/
krushin_impetus.py - one D6 per engaged model after a charge, each 3+ a mortal
wound) and Intimidating Motivation, which it shares with the Warboss as ONE
once-per-battle-round budget, are engine-wired.

Painboy is the SUPPORT of Boyz, Breaka Boyz, Flash Gitz, Nobz and Tankbustas.
Crude Surgery heals its unit 3 wounds at the start of its Command phase
through core rule 02.02.04 (game/heal.py), and Catch Dat Red Bit adds D3 once
per battle (game/crude_surgery.py). The user-supplied Grot Orderly, Dok's
Toolz' Feel No Pain and Hold Still and Say 'Aargh!' are gone with the
pre-codex sheet.

Three datasheets built for the user's Mecha Orks list (stage G1). The Bigboss
is a SUPPORT of Boyz, Breaka Boyz and Nobz - a mob takes a Warboss AND a Bigboss
- with Sumfin' to Prove (game/sumfin_to_prove.py: +1 to hit on the unit's melee
attacks). The Weirdboy is a SUPPORT of Beast Snagga Boyz and Boyz and a psyker
level 1: Da Jump (game/da_jump.py - a psychic roll places his unit in Strategic
Reserves with Deep Strike) and HIS Warpath (game/weirdboy_warpath.py - the Kill
Rig's frame, but a re-roll of wound 1s and [PSYCHIC]; one name, two effects).
The Gunwagon is the Battlewagon's gun variant: a two-profile Kannon swappable for
a Killkannon or a (priced) Zzap Gun, four free additions, Mobile Arsenal
(game/mobile_arsenal.py: re-roll hit rolls of 1 in your Shooting phase) and a
12-model transport.

Tankbustas (2026-09 codex) are a Nob and five Tankbustas; the Busta Rokkit
Launcha and the Smash Hammer each print a Standard and a Hunter profile. All
three abilities are engine-wired: Rokkit Barrage (game/rokkit_barrage.py, a
Battle-shock test at -1 on a unit they hit), Bomb Squigs (game/bomb_squigs.py,
twice per battle after a Normal move, D6 3+ then D3 mortal wounds) and the
Pulsa Rokkit wargear (game/pulsa_rokkit.py, +1 AP and [LETHAL HITS] against one
MONSTER/VEHICLE unit). The pre-codex Tank Hunters is gone, and with it the Ork
half of game/squad.py's tank_hunters_modifiers() (the Myphitic Blight-hauler's
ranged-only twin stays).

Detachment "War Horde" is engine-wired (game/war_horde.py -
get_stuck_in_adjusted_weapon(), chained into FightController the same way
Bonded Heroes is, see that module's own docstring), gated on
config.WAR_HORDE_PLAYERS like every other detachment since the 2026-09 codex.
Its three pre-codex stratagems (Unbridled Carnage, 'Ard as Nails, 'Ere We Go)
are retired. Every Ork UnitProfile here sets an `orks` flag (see
UnitProfile.orks' own note) so the rule has something to check, since there is
no generic per-model Faction tracking to read instead.

Gretchin's Thievin' Scavengers (2026-09 codex) secures an objective the unit
is controlling at the end of its Movement phase (game/thievin_scavengers.py,
called from main.py's end-of-Movement block after update_control()). The
codex's other new mob abilities each have a module of their own: Ammo Runts
(game/ork_ammo_runts.py), Tide of Muscle, Never Too Busy to Fight, Mobbed,
Rokkit Charge, Krumpin' Time, Arrogant Invulnerability, and Downtrodden
(game/transport.py's squad_capacity_cost()).

Points costs live in game/factions/orks_points.py (the whole published list -
all 58 entries, including the 53 units without a datasheet here yet), same
arrangement as game/factions/tau_empire.py and its own points module: each
datasheet below only points its `points=` field at its entry there, so no
cost is written down twice. See game/factions/points.py for the structure."""

from game import force_dispositions
from game.factions import Datasheet, Detachment, Faction, Gear, ModelLine, WargearOption, register_faction
from game.factions.detachment import Enhancement
from game.factions.orks_points import ORKS_POINTS
from game.units import (
    BattlewagonProfile, BeastbossProfile, FlashGitzKaptinProfile, FlashGitzProfile, KillRigProfile,
    BeastSnaggaBoyProfile, BeastSnaggaNobProfile, BikerNobProfile, BoyzNobProfile, BoyzProfile,
    BigbossProfile, DeffDreadProfile, DeffkoptaProfile, GretchinProfile, GunwagonProfile, WeirdboyProfile,
    MeganobzProfile, PainboyProfile, StormboyProfile, StormboyzNobProfile, TankbustaNobProfile,
    TankbustaProfile, TrukkProfile, WarbikerProfile, WarbossMegaArmourProfile, WarbossProfile,
)
from game.weapons import (
    BeastSnaggaChoppaProfile, BeastSnaggaKlawAndBeastchoppaProfile, BigShootaS5Profile,
    BustaRokkitLaunchaProfile, ButchaBoyzProfile, ChoppaA4Profile, DoksToolzProfile,
    EavyLobbaProfile, GitstikkaProfile,
    SavageHornsAndHoovesProfile,
    SawBladesProfile, SnazzgunCuttaProfile,
    ShootaProfile, StikkaKannonProfile, WurrtowerProfile,
    BigChoppaProfile, BigShootaProfile, BurnaProfile, ChoppaProfile,
    GrotBlastaProfile, KillsawProfile, KombiRokkitBustaRokkitProfile, KombiSkorchaShootaProfile,
    KombiWeaponShootaProfile, KustomChoppaProfile,
    KustomShootaAimedProfile, KustomShootaProfile,
    PowerKlawProfile, PowerSnappaProfile, RokkitLaunchaBlastaProfile,
    RokkitPistolProfile, ScavengedShivsProfile, SluggaProfile,
    SmashHammerProfile,
    ThumpGunProfile, TwinKillsawProfile,
    UgeChoppaProfile, UrtySyringeProfile,
    WarbossKustomChoppaProfile, WarbossPowerKlawProfile,
    # stage E3d - Warbikers, Deffkoptas, Trukk, Battlewagon, Deff Dread
    BuzzsawProfile, CrushinBulkProfile, DeffkoptaChoppaProfile, DeffkoptaKustomMegaBlastaProfile,
    DeffkoptaRokkitLaunchaBlastaProfile, DreadKlawsProfile, DualBigShootaProfile, DualDakkagunProfile,
    DualKombiRokkitDakkagunProfile, ExtraKlawProfile, GrabbinKlawProfile, KustomMegaBlastaProfile,
    SkorchaProfile, SpikedRamProfile, SpinninBladesProfile, WreckinBallProfile,
    # Mecha Orks stage G1 - Bigboss, Weirdboy, Gunwagon
    BigbossBigChoppaProfile, CopperStaffProfile, GunwagonCrushinBulkProfile, KannonFragProfile,
    KillkannonProfile, LobbaProfile, PowerVomitProfile, ZzapGunProfile,
)

ORKS = Faction("Orks", "ORKS")

WAR_HORDE = ORKS.add_detachment(Detachment(
    "War Horde",
    rule_name="Get Stuck In",
    points=3,
    # The 2026-09 Ork codex prints TWO on War Horde's heading ("Take and Hold;
    # Purge the Foe"); armies/orks.json declares the first.
    force_dispositions=(force_dispositions.TAKE_AND_HOLD, force_dispositions.PURGE_THE_FOE),
    # A config setting like every other detachment since the 2026-09 codex:
    # War Horde is no longer the only Ork detachment Wahapedia prints (15 are),
    # so "this unit is an Ork" stopped meaning "this army runs War Horde".
    setting="WAR_HORDE_PLAYERS",
    rule_text=(
        "Get Stuck In: Friendly ORKS units' melee attacks have [Sustained Hits 1]."
    ),
    enhancements=[
        # ENGINE-WIRED, all four - registered in game/enhancements.py, each rule
        # in its own game/enh_*.py module. Dormant by roster: armies/orks.json
        # buys none of them, which test_ork_war_horde.py pins.
        Enhancement("Headwoppa's Killchoppa", 15, description=(
            "ORKS model only. If this unit made a charge move this turn, this model's melee "
            "attacks have +1 AP.")),
        Enhancement("Da Boss is Watchin'", 25, description=(
            "ORKS model only. (Once per battle, per army) In your Movement phase, you can use "
            "this ability. If you do, this unit is riled up until the start of your next turn.")),
        Enhancement("Kunnin' But Brutal", 20, description=(
            "ORKS model only. When this unit is selected to make a fall-back move, that "
            "fall-back move does not prevent this unit from being eligible to shoot/declare a "
            "charge.")),
        Enhancement("Follow Me Ladz", 20, description=(
            "ORKS model only. This unit has +2\" M.")),
    ],
    # The six Stratagems (game/horde_*.py) are built in main.py, like every other
    # detachment's.
))

_NOB_LOADOUT = [KustomChoppaProfile, KombiSkorchaShootaProfile]
_BOY_LOADOUT = [ChoppaProfile, ShootaProfile, SluggaProfile]

BOYZ_NOB_TO_BIG_CHOPPA = "Kustom Choppa + Kombi-skorcha -> Big Choppa"
BOYZ_NOB_TO_POWER_KLAW = "Kustom Choppa -> Power Klaw"
BOYZ_NOB_TO_KOMBI_ROKKIT = "Kombi-skorcha -> Kombi-rokkit"
BOYZ_NOB_TO_KUSTOM_SHOOTA = "Kombi-skorcha -> Kustom Shoota"
BOYZ_BIG_SHOOTA = "Shoota -> Big Shoota"
BOYZ_ROKKIT_LAUNCHA = "Shoota -> Rokkit Launcha"
BOYZ_BURNA = "Shoota -> Burna"

BOYZ = ORKS.add_datasheet(Datasheet(
    "Boyz",
    keywords=("INFANTRY", "BATTLELINE", "EXPLOSIVES", "MOB"),
    # 2026-09 codex (rules/orks/Boyz.md): "1-2 Nob models, 9-18 Boy models",
    # priced at 10 and 20 models - so the two builds are 1 Nob + 9 Boys and
    # 2 Nobs + 18 Boys. composition_index 0 is the 10-model build.
    composition_options=[
        [
            ModelLine(BoyzNobProfile, 1, _NOB_LOADOUT, name="Nob"),
            ModelLine(BoyzProfile, 9, _BOY_LOADOUT, name="Boy"),
        ],
        [
            ModelLine(BoyzNobProfile, 2, _NOB_LOADOUT, name="Nob"),
            ModelLine(BoyzProfile, 18, _BOY_LOADOUT, name="Boy"),
        ],
    ],
    # The printed Wargear Options, in order. The three "for every 10 models"
    # Boy options each give up the Shoota, so they share build_squad()'s
    # cursor - which keeps them on different models but does not make them
    # EXCLUSIVE: a 10-model build can take all three where the sheet allows
    # one of them per 10 models. The same named limitation as Kroot
    # Farstalkers' two special rifles (WargearOption has no "one of").
    wargear_options=[
        WargearOption("Nob", replaces=(KustomChoppaProfile, KombiSkorchaShootaProfile),
                      with_weapons=[BigChoppaProfile], name=BOYZ_NOB_TO_BIG_CHOPPA),
        WargearOption("Nob", replaces=KustomChoppaProfile, with_weapons=[PowerKlawProfile],
                      name=BOYZ_NOB_TO_POWER_KLAW),
        WargearOption("Nob", replaces=KombiSkorchaShootaProfile, with_weapons=[KombiRokkitBustaRokkitProfile],
                      name=BOYZ_NOB_TO_KOMBI_ROKKIT),
        WargearOption("Nob", replaces=KombiSkorchaShootaProfile, with_weapons=[KustomShootaProfile],
                      name=BOYZ_NOB_TO_KUSTOM_SHOOTA),
        WargearOption("Boy", replaces=ShootaProfile, with_weapons=[BigShootaProfile], per_models=10,
                      name=BOYZ_BIG_SHOOTA),
        WargearOption("Boy", replaces=ShootaProfile, with_weapons=[RokkitLaunchaBlastaProfile], per_models=10,
                      name=BOYZ_ROKKIT_LAUNCHA),
        WargearOption("Boy", replaces=ShootaProfile, with_weapons=[BurnaProfile], per_models=10,
                      name=BOYZ_BURNA),
    ],
    points=ORKS_POINTS["Boyz"],
    abilities_text=[
        "Ammo Runts (Once per battle, per unit): In your Shooting phase, when this unit is selected to "
        "shoot, you can use this ability. If you do, this unit's ranged attacks have +1 to hit rolls.",
        "Tide of Muscle: In the Fight phase, if this unit made a charge move this turn, this unit's melee "
        "attacks have [Lethal Hits].",
        "Never Too Busy to Fight: Being engaged does not prevent this unit from being eligible to start "
        "an action.",
    ],
))

_BIKER_NOB_LOADOUT = [KustomChoppaProfile, DualKombiRokkitDakkagunProfile]
_WARBIKER_LOADOUT = [ChoppaProfile, DualDakkagunProfile]

WARBIKERS = ORKS.add_datasheet(Datasheet(
    "Warbikers",
    keywords=("MOUNTED", "EXPLOSIVES", "SPEED FREEKS"),
    # 2026-09 codex (rules/orks/Warbikers.md): "1 Biker Nob model, 2-5 Warbiker
    # models", priced at 3 and 6 - composition_index 0 and 1. No wargear
    # options: the pre-codex Power Klaw addition is gone.
    composition_options=[
        [
            ModelLine(BikerNobProfile, 1, _BIKER_NOB_LOADOUT, name="Biker Nob"),
            ModelLine(WarbikerProfile, 2, _WARBIKER_LOADOUT, name="Warbiker"),
        ],
        [
            ModelLine(BikerNobProfile, 1, _BIKER_NOB_LOADOUT, name="Biker Nob"),
            ModelLine(WarbikerProfile, 5, _WARBIKER_LOADOUT, name="Warbiker"),
        ],
    ],
    points=ORKS_POINTS["Warbikers"],
    abilities_text=[
        "High-speed Carnage: If this unit made a charge move this turn, this unit's melee attacks have: "
        "+1 S and D.",
    ],
))
# High-speed Carnage is engine-wired (game/high_speed_carnage.py, in
# FightController's adjuster chain). The pre-codex Drive-by Dakka is gone.

_STORMBOYZ_NOB_LOADOUT = [KustomChoppaProfile, SluggaProfile]
_STORMBOY_LOADOUT = [ChoppaProfile, SluggaProfile]

STORMBOYZ_NOB_TO_POWER_KLAW = "Kustom Choppa -> Power Klaw"

STORMBOYZ = ORKS.add_datasheet(Datasheet(
    "Stormboyz",
    keywords=("INFANTRY", "EXPLOSIVES", "FLY", "JUMP PACK"),
    # 2026-09 codex (rules/orks/Stormboyz.md): "1 Nob model, 4-9 Stormboy
    # models", priced at 5 and 10 models. CORE: Deep Strike is the profile's
    # `deep_strike`.
    composition_options=[
        [
            ModelLine(StormboyzNobProfile, 1, _STORMBOYZ_NOB_LOADOUT, name="Nob"),
            ModelLine(StormboyProfile, 4, _STORMBOY_LOADOUT, name="Stormboy"),
        ],
        [
            ModelLine(StormboyzNobProfile, 1, _STORMBOYZ_NOB_LOADOUT, name="Nob"),
            ModelLine(StormboyProfile, 9, _STORMBOY_LOADOUT, name="Stormboy"),
        ],
    ],
    wargear_options=[
        WargearOption("Nob", replaces=KustomChoppaProfile, with_weapons=[PowerKlawProfile], max_models=1,
                      name=STORMBOYZ_NOB_TO_POWER_KLAW),
    ],
    points=ORKS_POINTS["Stormboyz"],
    abilities_text=[
        "Rokkit Charge: When this unit is selected to fight, if this unit made a charge move this turn, you "
        "can use this ability. If you do, this unit's melee attacks have: +1 A and S; [Hazardous].",
    ],
))

_TRUKK_LOADOUT = [DualBigShootaProfile, SpikedRamProfile]

TRUKK_DUAL_BIG_SHOOTA_TO_ROKKIT_LAUNCHA = "Dual Big Shoota -> Rokkit Launcha"
TRUKK_ADD_BUZZSAW = "+ Buzzsaw"
TRUKK_ADD_GRABBIN_KLAW = "+ Grabbin' Klaw"

TRUKK = ORKS.add_datasheet(Datasheet(
    "Trukk",
    keywords=("VEHICLE", "DEDICATED TRANSPORT", "FRAME", "SPEED FREEKS", "TRANSPORT"),
    model_lines=[
        ModelLine(TrukkProfile, 1, _TRUKK_LOADOUT, name="Trukk"),
    ],
    # 2026-09 codex (rules/orks/Trukk.md): "This model's Dual Big Shoota can be
    # replaced with 1 Rokkit Launcha" and "This model can be equipped with one
    # of the following: 1 Buzzsaw / 1 Grabbin' Klaw" - both of the latter are
    # ADDITIONS beside the Spiked Ram.
    # KNOWN LIMITATION: "one of the following" makes the two additions
    # exclusive, and two WargearOptions that replace nothing cannot exclude each
    # other - the same documented gap as the Tankbustas' Busta Rokkit Launcha
    # and Pulsa Rokkit. A build can take both.
    wargear_options=[
        WargearOption("Trukk", replaces=DualBigShootaProfile, with_weapons=[RokkitLaunchaBlastaProfile],
                      max_models=1, name=TRUKK_DUAL_BIG_SHOOTA_TO_ROKKIT_LAUNCHA),
        WargearOption("Trukk", replaces=None, with_weapons=[BuzzsawProfile], max_models=1,
                      name=TRUKK_ADD_BUZZSAW),
        WargearOption("Trukk", replaces=None, with_weapons=[GrabbinKlawProfile], max_models=1,
                      name=TRUKK_ADD_GRABBIN_KLAW),
    ],
    points=ORKS_POINTS["Trukk"],
    abilities_text=[
        "Pilin' Out: In your opponent's Movement phase, when an enemy unit ends a move within 8\" of this "
        "model, units embarked within this model can make a disembark move using the rapid disembark mode.",
        "Transport: This model has a transport capacity of 12 ORKS INFANTRY models. It cannot transport "
        "GHAZGHKULL THRAKA/JUMP PACK models. Each MEGA ARMOUR model takes up the space of 2 models.",
    ],
))
# Pilin' Out is engine-wired (game/pilin_out.py). Deadly Demise D3 and Firing
# Deck 12 are generic UnitProfile fields. The pre-codex Grot Riggers is gone.

_GRETCHIN_LOADOUT = [ScavengedShivsProfile, GrotBlastaProfile]

GRETCHIN = ORKS.add_datasheet(Datasheet(
    "Gretchin",
    keywords=("INFANTRY", "GROTS"),
    # 2026-09 codex (rules/orks/Gretchin.md): "10-20 Gretchin models", priced
    # at 10 and 20. The Runtherd is a SUPPORT unit of its own now.
    composition_options=[
        [ModelLine(GretchinProfile, 10, _GRETCHIN_LOADOUT, name="Gretchin")],
        [ModelLine(GretchinProfile, 20, _GRETCHIN_LOADOUT, name="Gretchin")],
    ],
    points=ORKS_POINTS["Gretchin"],
    abilities_text=[
        "Downtrodden: For the purposes of transport capacity, each 2 Gretchin models (rounding up) take up "
        "the space of 1 model.",
        "Thievin' Scavengers: At the end of your Movement phase, if this unit is controlling an objective, "
        "that objective is secured.",
    ],
))

_WARBOSS_LOADOUT = [WarbossKustomChoppaProfile, KustomShootaProfile]

WARBOSS_KUSTOM_CHOPPA_TO_POWER_KLAW = "Kustom Choppa -> Power Klaw"
WARBOSS_KUSTOM_SHOOTA_TO_KOMBI_ROKKIT = "Kustom Shoota -> Kombi-rokkit"
WARBOSS_KUSTOM_SHOOTA_TO_KOMBI_SKORCHA = "Kustom Shoota -> Kombi-skorcha"

WARBOSS = ORKS.add_datasheet(Datasheet(
    "Warboss",
    keywords=("INFANTRY", "CHARACTER", "EXPLOSIVES", "WARBOSS"),
    # 2026-09 codex (rules/orks/Warboss.md): 1 Warboss with a Kustom Choppa and a
    # Kustom Shoota.
    model_lines=[
        ModelLine(WarbossProfile, 1, _WARBOSS_LOADOUT, name="Warboss"),
    ],
    # "This model's Kustom Choppa can be replaced with 1 Power Klaw" and "This
    # model's Kustom Shoota can be replaced with one of the following: 1
    # Kombi-rokkit, 1 Kombi-skorcha". The two Kombi options give up the same
    # weapon, so they share build_squad()'s cursor - on a one-model line that is
    # "one of the following" exactly. The Kombi weapons are the Boyz Nob's
    # profile chains (rule 04.01.03).
    wargear_options=[
        WargearOption("Warboss", replaces=WarbossKustomChoppaProfile, with_weapons=[WarbossPowerKlawProfile],
                      max_models=1, name=WARBOSS_KUSTOM_CHOPPA_TO_POWER_KLAW),
        WargearOption("Warboss", replaces=KustomShootaProfile, with_weapons=[KombiRokkitBustaRokkitProfile],
                      max_models=1, name=WARBOSS_KUSTOM_SHOOTA_TO_KOMBI_ROKKIT),
        WargearOption("Warboss", replaces=KustomShootaProfile, with_weapons=[KombiSkorchaShootaProfile],
                      max_models=1, name=WARBOSS_KUSTOM_SHOOTA_TO_KOMBI_SKORCHA),
    ],
    points=ORKS_POINTS["Warboss"],
    abilities_text=[
        "Boss' Ammo Runt (Once per battle, per unit): In your Shooting phase, when this unit is selected "
        "to shoot, you can use this ability. If you do, this model's ranged attacks have +1 to hit rolls.",
        "Might Is Right: If this unit made a charge move this turn, this model's melee attacks have +3 A "
        "and +2 S.",
        "Intimidating Motivation (Once per battle round, per army): In your Movement phase, at the start "
        "or end of this unit's move, you can select one friendly ORKS unit within 6\" of this unit. That "
        "unit is no longer battle-shocked and is riled up until the start of your next turn.",
    ],
))

_MEGANOB_LOADOUT = [KustomShootaAimedProfile, PowerKlawProfile]

MEGANOBZ_POWER_KLAW_TO_KILLSAW = "Power Klaw -> Killsaw"
MEGANOBZ_KUSTOM_SHOOTA_TO_KOMBI_WEAPON = "Kustom Shoota -> Kombi-weapon"
MEGANOBZ_TO_TWIN_KILLSAWS = "Power Klaw + Kustom Shoota -> Twin Killsaws"

MEGANOBZ = ORKS.add_datasheet(Datasheet(
    "Meganobz",
    keywords=("INFANTRY", "EXPLOSIVES", "MEGA ARMOUR"),
    # 2026-09 codex (rules/orks/Meganobz.md): "2-6 Meganob models", priced at
    # 2, 3, 5 and 6 - the four composition_options in that order, so index 3
    # is the 6-model build.
    composition_options=[
        [ModelLine(MeganobzProfile, count, _MEGANOB_LOADOUT, name="Meganob")] for count in (2, 3, 5, 6)
    ],
    # "Any number of models can each..." - no cap. The Twin Killsaws option
    # gives up both weapons the other two options each give up one of, so all
    # three share build_squad()'s cursor and never land on the same model.
    wargear_options=[
        WargearOption("Meganob", replaces=PowerKlawProfile, with_weapons=[KillsawProfile],
                      name=MEGANOBZ_POWER_KLAW_TO_KILLSAW,
                      points=ORKS_POINTS["Meganobz"].wargear["Killsaw"]),
        WargearOption("Meganob", replaces=KustomShootaAimedProfile, with_weapons=[KombiWeaponShootaProfile],
                      name=MEGANOBZ_KUSTOM_SHOOTA_TO_KOMBI_WEAPON),
        WargearOption("Meganob", replaces=(PowerKlawProfile, KustomShootaAimedProfile),
                      with_weapons=[TwinKillsawProfile], name=MEGANOBZ_TO_TWIN_KILLSAWS,
                      points=ORKS_POINTS["Meganobz"].wargear["Twin Killsaws"]),
    ],
    points=ORKS_POINTS["Meganobz"],
    abilities_text=[
        "Arrogant Invulnerability: Attacks that target this unit have -1 AP.",
        "Krumpin' Time: In the Fight phase, if this unit is riled up, this unit has +1 to hit rolls.",
    ],
))

_WARBOSS_MEGA_ARMOUR_LOADOUT = [BigShootaS5Profile, UgeChoppaProfile]

WARBOSS_MEGA_ARMOUR = ORKS.add_datasheet(Datasheet(
    "Warboss in Mega Armour",
    keywords=("INFANTRY", "CHARACTER", "MEGA ARMOUR", "WARBOSS"),
    # 2026-09 codex (rules/orks/Warboss in Mega Armour.md): 1 model with a Big
    # Shoota and an 'Uge Choppa, no wargear options.
    model_lines=[
        ModelLine(WarbossMegaArmourProfile, 1, _WARBOSS_MEGA_ARMOUR_LOADOUT, name="Warboss in Mega Armour"),
    ],
    points=ORKS_POINTS["Warboss in Mega Armour"],
    abilities_text=[
        "Krushin' Impetus: When this unit ends a charge move, you can select one enemy unit engaged with "
        "this unit. If you do, roll one D6 for each model in this unit engaged with that enemy unit: for "
        "each 3+, that enemy unit suffers 1 mortal wound.",
        "Intimidating Motivation (Once per battle round, per army): In your Movement phase, at the start "
        "or end of this unit's move, you can select one friendly ORKS unit within 6\" of this unit. That "
        "unit is no longer battle-shocked and is riled up until the start of your next turn.",
    ],
))

_TANKBUSTA_NOB_LOADOUT = [ChoppaA4Profile, RokkitPistolProfile, RokkitPistolProfile]
_TANKBUSTA_LOADOUT = [BustaRokkitLaunchaProfile, GitstikkaProfile]

TANKBUSTAS_NOB_SMASH_HAMMER = "Rokkit Pistol -> Smash Hammer"
TANKBUSTAS_ADD_BUSTA_ROKKIT_LAUNCHA = "+ Busta Rokkit Launcha"
TANKBUSTAS_PULSA_ROKKIT = "Pulsa Rokkit"


def _apply_pulsa_rokkit(token):
    """The bearer carries a Pulsa Rokkit. It is wargear, not a weapon (the
    datasheet prints no profile for it); what it grants is the unit's Pulsa
    Rokkit ability, resolved when the unit is selected to shoot - see
    game/pulsa_rokkit.py."""
    token.pulsa_rokkit = True


TANKBUSTAS = ORKS.add_datasheet(Datasheet(
    "Tankbustas",
    keywords=("INFANTRY", "EXPLOSIVES"),
    # 2026-09 codex (rules/orks/Tankbustas.md): "1 Nob model, 5 Tankbusta
    # models", priced for exactly that size.
    model_lines=[
        ModelLine(TankbustaNobProfile, 1, _TANKBUSTA_NOB_LOADOUT, name="Nob"),
        ModelLine(TankbustaProfile, 5, _TANKBUSTA_LOADOUT, name="Tankbusta"),
    ],
    # "The Nob can have their Rokkit Pistol replaced with 1 Smash Hammer" - ONE
    # of the two pistols, so both are taken off and one is put back
    # (WargearOption's `replaces` removes every matching instance at once).
    # "1 Tankbusta model can be equipped with one of the following: 1 Busta
    # Rokkit Launcha / 1 Pulsa Rokkit" - an ADDITION, and the Pulsa Rokkit is
    # wargear rather than a weapon, so it is a Gear item.
    # KNOWN LIMITATION: "one of the following" makes the two exclusive, and a
    # WargearOption cannot exclude a Gear item - the same documented gap as the
    # Kroot Farstalkers' and the Broadside's menus. A build can take both.
    wargear_options=[
        WargearOption("Nob", replaces=RokkitPistolProfile,
                      with_weapons=[RokkitPistolProfile, SmashHammerProfile], max_models=1,
                      name=TANKBUSTAS_NOB_SMASH_HAMMER),
        WargearOption("Tankbusta", replaces=None, with_weapons=[BustaRokkitLaunchaProfile],
                      max_models=1, name=TANKBUSTAS_ADD_BUSTA_ROKKIT_LAUNCHA),
    ],
    gear_options=[
        Gear("Tankbusta", TANKBUSTAS_PULSA_ROKKIT, _apply_pulsa_rokkit),
    ],
    gear_slots={"Tankbusta": 1},
    points=ORKS_POINTS["Tankbustas"],
    abilities_text=[
        "Rokkit Barrage: In your Shooting phase, when this unit has shot, select one enemy unit hit "
        "by those attacks. That unit makes a battle-shock roll, with -1 to that battle-shock roll.",
        "Bomb Squigs (Once per turn, twice per battle, per unit): In your Movement phase, when this "
        "unit ends a normal move, you can select one visible enemy unit within 12\" of this unit and "
        "roll one D6: on a 3+, that enemy unit suffers D3 mortal wounds.",
        "Pulsa Rokkit: In your Shooting phase, when this unit is selected to shoot, you can select "
        "one enemy MONSTER/VEHICLE unit within 24\" of this unit. If you do, this unit's attacks that "
        "target that unit have +1 AP and [LETHAL HITS].",
    ],
))
# All three are engine-wired: Rokkit Barrage (game/rokkit_barrage.py, the
# fourth carrier of game/battle_shock_after_shooting.py), Bomb Squigs
# (game/bomb_squigs.py) and the Pulsa Rokkit (game/pulsa_rokkit.py). The
# pre-codex Tank Hunters and Attached Unit text are gone.

_DEFFKOPTA_LOADOUT = [DeffkoptaChoppaProfile, DeffkoptaRokkitLaunchaBlastaProfile, SluggaProfile,
                      SpinninBladesProfile]

DEFFKOPTAS_KUSTOM_MEGA_BLASTA = "Rokkit Launcha -> Kustom Mega-blasta"

DEFFKOPTAS = ORKS.add_datasheet(Datasheet(
    "Deffkoptas",
    keywords=("MOUNTED", "EXPLOSIVES", "FLY", "SPEED FREEKS"),
    # 2026-09 codex (rules/orks/Deffkoptas.md): "3-6 Deffkopta models", priced
    # at 3 and 6 - composition_index 0 and 1.
    composition_options=[
        [ModelLine(DeffkoptaProfile, 3, _DEFFKOPTA_LOADOUT, name="Deffkopta")],
        [ModelLine(DeffkoptaProfile, 6, _DEFFKOPTA_LOADOUT, name="Deffkopta")],
    ],
    # "For every 3 models in this unit, 1 model can have their Rokkit Launcha
    # replaced with 1 Kustom Mega-blasta."
    wargear_options=[
        WargearOption("Deffkopta", replaces=DeffkoptaRokkitLaunchaBlastaProfile,
                      with_weapons=[DeffkoptaKustomMegaBlastaProfile], per_models=3,
                      name=DEFFKOPTAS_KUSTOM_MEGA_BLASTA),
    ],
    points=ORKS_POINTS["Deffkoptas"],
    abilities_text=[
        "Deff from Above: In your Shooting phase, if this unit made an ingress move this turn, this unit's "
        "ranged attacks have +1 to hit rolls.",
        "Aerial Manoover: At the end of your opponent's Fight phase, if this unit is unengaged, you can place "
        "this unit in strategic reserves.",
    ],
))
# Both abilities are engine-wired: Deff from Above (game/deff_from_above.py, in
# ShootingController's hit modifiers) and Aerial Manoover
# (game/aerial_manoover.py, offered at main.py's end-of-Fight-phase seam).

_DEFF_DREAD_LOADOUT = [BigShootaS5Profile, DreadKlawsProfile, SkorchaProfile]

DEFF_DREAD_BIG_SHOOTA_TO_EXTRA_KLAW = "Big Shoota -> Extra Klaw"
DEFF_DREAD_BIG_SHOOTA_TO_KUSTOM_MEGA_BLASTA = "Big Shoota -> Kustom Mega-blasta"
DEFF_DREAD_BIG_SHOOTA_TO_ROKKIT_LAUNCHA = "Big Shoota -> Rokkit Launcha"
DEFF_DREAD_SKORCHA_TO_EXTRA_KLAW = "Skorcha -> Extra Klaw"
DEFF_DREAD_SKORCHA_TO_BIG_SHOOTA = "Skorcha -> Big Shoota"
DEFF_DREAD_SKORCHA_TO_KUSTOM_MEGA_BLASTA = "Skorcha -> Kustom Mega-blasta"
DEFF_DREAD_SKORCHA_TO_ROKKIT_LAUNCHA = "Skorcha -> Rokkit Launcha"

DEFF_DREAD = ORKS.add_datasheet(Datasheet(
    "Deff Dread",
    keywords=("VEHICLE", "WALKER"),
    model_lines=[
        ModelLine(DeffDreadProfile, 1, _DEFF_DREAD_LOADOUT, name="Deff Dread"),
    ],
    # 2026-09 codex (rules/orks/Deff Dread.md): the Big Shoota and the Skorcha
    # can each be replaced with "one of the following". Options that give up the
    # same weapon share build_squad()'s cursor, which on a one-model line is "one
    # of" exactly. ORDER MATTERS: the Big Shoota swaps come first, because
    # build_squad() applies options in this order and a swap removes EVERY copy
    # of what it replaces - "Skorcha -> Big Shoota" listed first would hand the
    # Big Shoota swap a second Big Shoota to take away.
    wargear_options=[
        WargearOption("Deff Dread", replaces=BigShootaS5Profile, with_weapons=[ExtraKlawProfile],
                      max_models=1, name=DEFF_DREAD_BIG_SHOOTA_TO_EXTRA_KLAW),
        WargearOption("Deff Dread", replaces=BigShootaS5Profile, with_weapons=[KustomMegaBlastaProfile],
                      max_models=1, name=DEFF_DREAD_BIG_SHOOTA_TO_KUSTOM_MEGA_BLASTA),
        WargearOption("Deff Dread", replaces=BigShootaS5Profile, with_weapons=[RokkitLaunchaBlastaProfile],
                      max_models=1, name=DEFF_DREAD_BIG_SHOOTA_TO_ROKKIT_LAUNCHA),
        WargearOption("Deff Dread", replaces=SkorchaProfile, with_weapons=[ExtraKlawProfile],
                      max_models=1, name=DEFF_DREAD_SKORCHA_TO_EXTRA_KLAW),
        WargearOption("Deff Dread", replaces=SkorchaProfile, with_weapons=[BigShootaS5Profile],
                      max_models=1, name=DEFF_DREAD_SKORCHA_TO_BIG_SHOOTA),
        WargearOption("Deff Dread", replaces=SkorchaProfile, with_weapons=[KustomMegaBlastaProfile],
                      max_models=1, name=DEFF_DREAD_SKORCHA_TO_KUSTOM_MEGA_BLASTA),
        WargearOption("Deff Dread", replaces=SkorchaProfile, with_weapons=[RokkitLaunchaBlastaProfile],
                      max_models=1, name=DEFF_DREAD_SKORCHA_TO_ROKKIT_LAUNCHA),
    ],
    points=ORKS_POINTS["Deff Dread"],
    abilities_text=[
        "Dread 'Ard: Attacks that target this unit have -1 D.",
    ],
))
# Dread 'Ard is UnitProfile.damage_reduction (game/damage_reduction.py). Deadly
# Demise 1 is a generic field. The pre-codex Piston-driven Brutality and Dead
# Choppy are gone.

_BEAST_SNAGGA_NOB_LOADOUT = [PowerSnappaProfile, SluggaProfile]
_BEAST_SNAGGA_BOY_LOADOUT = [BeastSnaggaChoppaProfile, SluggaProfile]

BEAST_SNAGGA_BOYZ_THUMP_GUN = "+ Thump Gun"


BEAST_SNAGGA_BOYZ = ORKS.add_datasheet(Datasheet(
    "Beast Snagga Boyz",
    keywords=("INFANTRY", "BATTLELINE", "BEAST SNAGGA", "MOB"),
    # 2026-09 codex (rules/orks/Beast Snagga Boyz.md): "1-2 Nob models, 9-18
    # Beast Snagga Boy models", priced at 10 and 20 - Boyz' shape exactly.
    composition_options=[
        [
            ModelLine(BeastSnaggaNobProfile, 1, _BEAST_SNAGGA_NOB_LOADOUT, name="Nob"),
            ModelLine(BeastSnaggaBoyProfile, 9, _BEAST_SNAGGA_BOY_LOADOUT, name="Beast Snagga Boy"),
        ],
        [
            ModelLine(BeastSnaggaNobProfile, 2, _BEAST_SNAGGA_NOB_LOADOUT, name="Nob"),
            ModelLine(BeastSnaggaBoyProfile, 18, _BEAST_SNAGGA_BOY_LOADOUT, name="Beast Snagga Boy"),
        ],
    ],
    # "For every 10 models in this unit, 1 Beast Snagga Boy model can be
    # equipped with 1 Thump Gun" - an addition, the Choppa and Slugga stay.
    wargear_options=[
        WargearOption("Beast Snagga Boy", replaces=None, with_weapons=[ThumpGunProfile], per_models=10,
                      name=BEAST_SNAGGA_BOYZ_THUMP_GUN),
    ],
    points=ORKS_POINTS["Beast Snagga Boyz"],
    abilities_text=[
        "Mobbed: When this unit ends a charge move, each enemy MONSTER/VEHICLE unit engaged with this unit "
        "makes a battle-shock roll: with -1 to that battle-shock roll, or with -2 to that battle-shock roll "
        "if this unit has 13+ models.",
    ],
))

_BEASTBOSS_LOADOUT = [ShootaProfile, BeastSnaggaKlawAndBeastchoppaProfile]

BEASTBOSS = ORKS.add_datasheet(Datasheet(
    "Beastboss",
    keywords=("INFANTRY", "BEAST SNAGGA", "CHARACTER", "WARBOSS"),
    # 2026-09 codex (rules/orks/Beastboss.md): 1 model with a Shoota and a Beast
    # Snagga Klaw and Beastchoppa - ONE melee weapon now, no wargear options.
    model_lines=[
        ModelLine(BeastbossProfile, 1, _BEASTBOSS_LOADOUT, name="Beastboss"),
    ],
    points=ORKS_POINTS["Beastboss"],
    abilities_text=[
        "Keep Huntin'! (Once per battle round, per army): In your Movement phase, at the start or end of "
        "this unit's move, you can select one friendly BEAST SNAGGA unit within 6\" of this unit. That "
        "unit is no longer battle-shocked and is riled up until the start of your next turn.",
        "Dodge Dis!: This unit's attacks have +1 to hit rolls.",
    ],
))

_PAINBOY_LOADOUT = [DoksToolzProfile, UrtySyringeProfile]

PAINBOY = ORKS.add_datasheet(Datasheet(
    "Painboy",
    keywords=("INFANTRY", "CHARACTER"),
    # 2026-09 codex (rules/orks/Painboy.md): 1 model with Dok's Toolz and an
    # 'Urty Syringe, no wargear options. The syringe's [EXTRA ATTACKS] lets both
    # swing in one activation (rule 04.01). The pre-codex Grot Orderly gear is
    # gone - Catch Dat Red Bit prints the same token, as an ability.
    model_lines=[
        ModelLine(PainboyProfile, 1, _PAINBOY_LOADOUT, name="Painboy"),
    ],
    points=ORKS_POINTS["Painboy"],
    abilities_text=[
        "Crude Surgery: In your Command phase, this unit heals 3 wounds.",
        "Catch Dat Red Bit (Once per battle, per unit): When this model uses its Crude Surgery ability, "
        "you can add D3 to the number of wounds healed.",
    ],
))

_KILL_RIG_LOADOUT = [
    EavyLobbaProfile, ButchaBoyzProfile, SavageHornsAndHoovesProfile,
    SawBladesProfile, StikkaKannonProfile, WurrtowerProfile,
]

KILL_RIG = ORKS.add_datasheet(Datasheet(
    "Kill Rig",
    keywords=("MONSTER", "BEAST SNAGGA", "PSYKER", "TRANSPORT", "WAGON"),
    model_lines=[
        ModelLine(KillRigProfile, 1, _KILL_RIG_LOADOUT, name="Kill Rig"),
    ],
    # 2026-09 codex (rules/orks/Kill Rig.md): one model carrying all six printed
    # weapons, no wargear options. Every melee weapon is [EXTRA ATTACKS] now, so
    # rule 04.01's one-weapon choice contests none of them.
    points=ORKS_POINTS["Kill Rig"],
    abilities_text=[
        "Beastscent (psychic level 1): In your Movement phase, when a unit embarked within this unit is "
        "selected to make a disembark move, if this unit is not battle-shocked, you can make a psychic roll "
        "for this unit by rolling one D6. If you do: On a 1, this unit is battle-shocked. That disembarking "
        "unit's attacks that target a MONSTER/VEHICLE unit have +1 to wound rolls until the end of the turn.",
        "Warpath (psychic level 1): In the Fight phase, when this unit is selected to fight, if this unit is "
        "not battle-shocked, you can make a psychic roll for this unit by rolling one D6. If you do: On a 1, "
        "this unit is battle-shocked. This unit's melee attacks have [Lethal Hits] and [Psychic].",
        "Wurrboy (psyker level 1): This model has the psychic abilities listed in the Psychic Abilities "
        "section (see above).",
        "Transport: This model has a transport capacity of 12 BEAST SNAGGAS INFANTRY models.",
    ],
))
# Both psychic abilities are engine-wired through one psychic roll
# (game/psychic_roll.py: not battle-shocked, the Unstable Energies budget, a 1
# battle-shocks): Beastscent (game/beastscent.py, TransportController's
# on_disembark_started) and Warpath (game/warpath.py, offered in
# FightController._start_fighting()). Damaged 6, Deadly Demise D6 and Feel No
# Pain 5+ are generic UnitProfile fields; the Transport line is
# transport_capacity/transport_requires_infantry plus transport_requires for its
# BEAST SNAGGA half. The pre-codex Spirit of Gork is gone.

_FLASH_GITZ_LOADOUT = [ChoppaA4Profile, SnazzgunCuttaProfile]

FLASH_GITZ = ORKS.add_datasheet(Datasheet(
    "Flash Gitz",
    keywords=("INFANTRY", "EXPLOSIVES"),
    # 2026-09 codex (rules/orks/Flash Gitz.md): "1 Kaptin model, 4-9 Flash Git
    # models", priced at 5 and 10 - composition_index 0 and 1.
    composition_options=[
        [
            ModelLine(FlashGitzKaptinProfile, 1, _FLASH_GITZ_LOADOUT, name="Kaptin"),
            ModelLine(FlashGitzProfile, 4, _FLASH_GITZ_LOADOUT, name="Flash Git"),
        ],
        [
            ModelLine(FlashGitzKaptinProfile, 1, _FLASH_GITZ_LOADOUT, name="Kaptin"),
            ModelLine(FlashGitzProfile, 9, _FLASH_GITZ_LOADOUT, name="Flash Git"),
        ],
    ],
    points=ORKS_POINTS["Flash Gitz"],
    abilities_text=[
        "Finderz Keeperz: In your Shooting phase, if any of the following apply, this unit's ranged "
        "attacks have +1 AP: this unit is within range of an objective; the target of that attack "
        "is within range of an objective.",
    ],
))
# Finderz Keeperz is engine-wired (game/finderz_keeperz.py, in ShootingController's
# adjuster chain). The pre-codex Gun-crazy Show-offs and the Kaptin's Ammo Runt
# wargear are gone.

_BATTLEWAGON_LOADOUT = [CrushinBulkProfile]

BATTLEWAGON_ADD_WRECKIN_BALL = "+ Wreckin' Ball"
BATTLEWAGON_ADD_BIG_SHOOTAS = "+ 4x Big Shoota"
BATTLEWAGON_ADD_GRABBIN_KLAW = "+ Grabbin' Klaw"

BATTLEWAGON = ORKS.add_datasheet(Datasheet(
    "Battlewagon",
    keywords=("VEHICLE", "FRAME", "TRANSPORT", "WAGON"),
    model_lines=[
        ModelLine(BattlewagonProfile, 1, _BATTLEWAGON_LOADOUT, name="Battlewagon"),
    ],
    # 2026-09 codex (rules/orks/Battlewagon.md): "This model can be equipped
    # with 1 Wreckin' Ball", "...with up to 4 Big Shoota" and "...with 1 Grabbin'
    # Klaw" - three additions beside the Crushin' Bulk, every one free
    # ("WARGEAR COSTS REMOVED").
    # KNOWN LIMITATION: "up to 4" is offered as the four at once. A WargearOption
    # counts MODELS, and this line has one, so 1-3 Big Shootas cannot be
    # expressed; the full four is what a list takes.
    wargear_options=[
        WargearOption("Battlewagon", replaces=None, with_weapons=[WreckinBallProfile], max_models=1,
                      name=BATTLEWAGON_ADD_WRECKIN_BALL),
        WargearOption("Battlewagon", replaces=None, with_weapons=[BigShootaS5Profile] * 4, max_models=1,
                      name=BATTLEWAGON_ADD_BIG_SHOOTAS),
        WargearOption("Battlewagon", replaces=None, with_weapons=[GrabbinKlawProfile], max_models=1,
                      name=BATTLEWAGON_ADD_GRABBIN_KLAW),
    ],
    points=ORKS_POINTS["Battlewagon"],
    abilities_text=[
        "Mobile Fortress: Ranged attacks that target this unit have -1 D.",
        "Transport: This model has a transport capacity of 22 ORKS INFANTRY models. Each MEGA ARMOUR/JUMP "
        "PACK model takes up the space of 2 models. Each GHAZGHKULL THRAKA model takes up the space of 4 "
        "models.",
    ],
))
# Mobile Fortress is UnitProfile.ranged_damage_reduction (game/damage_reduction.py).
# Damaged 6, Deadly Demise D6 and Firing Deck 11 are generic fields. The
# pre-codex Ramshackle but Rugged, 'Ard Case, Zzap Gun and Killkannon clause
# are gone. GHAZGHKULL THRAKA taking 4 slots is not modeled (no such datasheet).

_BIGBOSS_LOADOUT = [BigbossBigChoppaProfile, SluggaProfile]

BIGBOSS = ORKS.add_datasheet(Datasheet(
    "Bigboss",
    keywords=("INFANTRY", "CHARACTER"),
    # 2026-09 codex (rules/orks/Bigboss.md): 1 model with a Big Choppa and a
    # Slugga, no wargear options. SUPPORT (Boyz, Breaka Boyz, Nobz).
    model_lines=[
        ModelLine(BigbossProfile, 1, _BIGBOSS_LOADOUT, name="Bigboss"),
    ],
    points=ORKS_POINTS["Bigboss"],
    abilities_text=[
        "Sumfin' to Prove: This unit's melee attacks have +1 to hit rolls.",
    ],
))
# Sumfin' to Prove is engine-wired (game/sumfin_to_prove.py, in
# FightController's hit modifiers only - "melee").

_WEIRDBOY_LOADOUT = [PowerVomitProfile, CopperStaffProfile]

WEIRDBOY = ORKS.add_datasheet(Datasheet(
    "Weirdboy",
    keywords=("INFANTRY", "CHARACTER", "PSYKER"),
    # 2026-09 codex (rules/orks/Weirdboy.md): 1 model with a Power Vomit and a
    # Copper Staff, no wargear options. SUPPORT (Beast Snagga Boyz, Boyz). NOT
    # BEAST SNAGGA - a mob he supports does not fit a Kill Rig.
    model_lines=[
        ModelLine(WeirdboyProfile, 1, _WEIRDBOY_LOADOUT, name="Weirdboy"),
    ],
    points=ORKS_POINTS["Weirdboy"],
    abilities_text=[
        "Da Jump (psychic level 1, once per army, per battle round): In your Movement phase, if this unit is "
        "not battle-shocked, you can make a psychic roll for this unit by rolling one D6. If you do: On a 1, "
        "this unit is battle-shocked. Place this unit in strategic reserves. This unit has Deep Strike.",
        "Warpath (psychic level 1): In the Fight phase, when this unit is selected to fight, if this unit is "
        "not battle-shocked, you can make a psychic roll for this unit by rolling one D6. If you do: On a 1, "
        "this unit is battle-shocked. This unit's melee attacks can re-roll wound rolls of 1. This unit's "
        "melee attacks have [Psychic].",
        "Waaagh! Energy (psyker level 1): This model has the psychic abilities listed in the Psychic "
        "Abilities section (see above).",
    ],
))
# Both psychic abilities are engine-wired through the Kill Rig's psychic roll
# (game/psychic_roll.py) and one shared psyker level: Da Jump (game/da_jump.py,
# a panel button in your Movement phase) and Warpath (game/weirdboy_warpath.py,
# offered in FightController._start_fighting()). Deadly Demise D3 is a generic
# field.

_GUNWAGON_LOADOUT = [GunwagonCrushinBulkProfile, KannonFragProfile]

GUNWAGON_ADD_WRECKIN_BALL = "+ Wreckin' Ball"
GUNWAGON_ADD_GRABBIN_KLAW = "+ Grabbin' Klaw"
GUNWAGON_ADD_LOBBA = "+ Lobba"
GUNWAGON_ADD_BIG_SHOOTAS = "+ 4x Big Shoota"
GUNWAGON_KANNON_TO_KILLKANNON = "Kannon -> Killkannon"
GUNWAGON_KANNON_TO_ZZAP_GUN = "Kannon -> Zzap Gun"

GUNWAGON = ORKS.add_datasheet(Datasheet(
    "Gunwagon",
    keywords=("VEHICLE", "FRAME", "TRANSPORT", "WAGON"),
    model_lines=[
        ModelLine(GunwagonProfile, 1, _GUNWAGON_LOADOUT, name="Gunwagon"),
    ],
    # 2026-09 codex (rules/orks/Gunwagon.md), the printed Wargear Options in
    # order: four ADDITIONS beside the Crushin' Bulk and the Kannon, then "This
    # model's Kannon can be replaced with one of the following: 1 Killkannon / 1
    # Zzap Gun" - two options giving up the same weapon, so they share
    # build_squad()'s cursor, which on a one-model line is "one of" exactly. Only
    # the Zzap Gun is priced ("per Zzap Gun 10").
    # KNOWN LIMITATION, the Battlewagon's: "up to 4 Big Shoota" is offered as the
    # four at once - a WargearOption counts models, and this line has one.
    wargear_options=[
        WargearOption("Gunwagon", replaces=None, with_weapons=[WreckinBallProfile], max_models=1,
                      name=GUNWAGON_ADD_WRECKIN_BALL),
        WargearOption("Gunwagon", replaces=None, with_weapons=[GrabbinKlawProfile], max_models=1,
                      name=GUNWAGON_ADD_GRABBIN_KLAW),
        WargearOption("Gunwagon", replaces=None, with_weapons=[LobbaProfile], max_models=1,
                      name=GUNWAGON_ADD_LOBBA),
        WargearOption("Gunwagon", replaces=None, with_weapons=[BigShootaS5Profile] * 4, max_models=1,
                      name=GUNWAGON_ADD_BIG_SHOOTAS),
        WargearOption("Gunwagon", replaces=KannonFragProfile, with_weapons=[KillkannonProfile], max_models=1,
                      name=GUNWAGON_KANNON_TO_KILLKANNON),
        WargearOption("Gunwagon", replaces=KannonFragProfile, with_weapons=[ZzapGunProfile], max_models=1,
                      name=GUNWAGON_KANNON_TO_ZZAP_GUN,
                      points=ORKS_POINTS["Gunwagon"].wargear["Zzap Gun"]),
    ],
    points=ORKS_POINTS["Gunwagon"],
    abilities_text=[
        "Mobile Arsenal: In your Shooting phase, this unit's ranged attacks can re-roll hit rolls of 1.",
        "Transport: This model has a transport capacity of 12 ORKS INFANTRY models. Each MEGA ARMOUR/JUMP "
        "PACK model takes up the space of 2 models. Each GHAZGHKULL THRAKA model takes up the space of 4 "
        "models.",
    ],
))
# Mobile Arsenal is engine-wired (game/mobile_arsenal.py, in ShootingController's
# automatic re-roll of 1s). Damaged 6 and Deadly Demise D6 are generic fields; the
# Gunwagon prints no Firing Deck and no Mobile Fortress. GHAZGHKULL THRAKA taking 4
# slots is not modeled (no such datasheet yet).

register_faction(ORKS)
