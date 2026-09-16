"""Orks faction data.

Army rule "Waaagh!" is the 2026-09 codex text (rules/orks/army_rules.md) and
is engine-wired: the Advance re-roll in game/waaagh.py, riled up in
game/riled_up.py and War Cry in game/war_cry.py - a prompt for a human at the
start of every Command phase until used, a deterministic verdict for the AI
(ai/agent_driver.py's war_cry_verdict()). The old user-supplied Waaagh! and its
WaaaghController are retired; see game/waaagh.py's docstring for what went
with them. Detachment rule
is still to come (user announcement, not yet supplied). This module
currently holds sixteen datasheets: Boyz, Warbikers, Stormboyz, Trukk,
Gretchin, Warboss, Meganobz, Warboss in Mega Armour, Tankbustas,
Deffkoptas, Deff Dread, Beast Snagga Boyz, Beastboss, Kill Rig, Flash Gitz,
Battlewagon - every
one of their UnitProfile classes sets `waaagh = True` (user: "ALLE bisher
angelegten Ork einheiten haben die Waaagh! ability").

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

Kill Rig is the first MONSTER that is also a TRANSPORT, and the first PSYKER
of either faction. Only Spirit of Gork needed new code
(game/spirit_of_gork.py); Damaged 1-5, Deadly Demise D6 and Feel No Pain 6+
are all existing generic UnitProfile fields. Its Transport line needed the
new `transport_requires` - the INCLUSIVE counterpart of the long-standing
transport_excludes, which could only ever express a refusal and so could not
say "11 BEAST SNAGGA INFANTRY models".

Flash Gitz is the cheapest addition of the three: one ability, no new
mechanism. Gun-crazy Show-offs reuses the closest-eligible-target snapshot
ShootingController already computes for The Twin Lance's Exemplars of
Mont'ka - but it is applied at a DIFFERENT point in the sequence than every
other weapon adjuster in that file, because it changes the Attacks
characteristic and therefore has to land before the attack count is summed
rather than at the hit/wound step. Adding it also widened
_is_closest_eligible_target()'s own performance guard, which until now
short-circuited to False for anyone without Exemplars of Mont'ka - a second
consumer of that snapshot had to be named there or it would have silently
got False forever.

Battlewagon brought this engine's FIRST defensive weapon adjuster. Every
other one belongs to the attacker and is chained onto the weapon while its
group resolves; Ramshackle but Rugged belongs to the TARGET ("each time an
attack is allocated to this model") and is therefore applied at rule 05.03's
allocation step in game/damage_resolution.py, against the model actually
taking the wound - see game/ramshackle.py. Its 'Ard Case is also the first
PRICED Gear item (every drone menu before it was free), which is what gave
Gear a `points` field and taught Datasheet.points_for() to charge for gear at
all - priced from what build_squad() actually APPLIED rather than from the
caller's request, so a trimmed-away second copy cannot be billed.

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

Tankbustas is the first non-standalone datasheet since Gretchin - a real
6-model squad (1 Boss Nob + 5 Tankbusta), whose Boss Nob shares the rank-
and-file's exact stat line (see TankbustaProfile's own note). Tank Hunters
IS engine-wired (self-contained: a per-model ability plus a per-target
keyword check, no attached-unit dependency) - new `tank_hunters` UnitProfile
flag, plus a new shared game/squad.py's tank_hunters_modifiers() (used by
BOTH game/shooting.py's and game/fight.py's own _hit_modifiers()/
_wound_modifiers(), since the rule text isn't restricted to ranged attacks
- fight.py's own _hit_modifiers()/_wound_modifiers() needed a new
`target_squad` parameter for this, which they didn't previously take).
Attached Unit is NOT engine-wired, same Attached-Unit-flow gap as every
other Leader/Bodyguard text in this module (Lootas doesn't even exist as a
datasheet here yet either). Bomb Squigs is also NOT engine-wired, and
unlike every other ability decision in this module, that's a genuine scope
call rather than a missing-infrastructure gap: it's a real once-per-battle
reactive ability (fires after this unit ends a Normal move, needs its own
target-selection/decision-manager prompt, a D6 roll at 3+, then a D3
mortal-wound roll, and a 2-charge "Bomb Squig" counter per unit) - i.e. a
whole new controller comparable in scope to game/explosives.py, not a
one-line extension of an existing hook the way Da Biggest and da Best/
Krumpin' Time/Dead Brutal/Tank Hunters all were. Left as abilities_text
only; flagged here for whoever picks it up next rather than built silently
without being asked.

Deffkoptas is a multi-model (3x) VEHICLE squadron - unusual for VEHICLE
(every other VEHICLE datasheet here so far, Trukk, is single-model), but a
real printed composition, and no separate leader model this time. Deep
Strike (24.09) needs no new code - `deep_strike` is an existing generic
UnitProfile flag, already read by game/ingress.py/game/transport.py.
Invulnerable Save (6+) is likewise just DeffkoptaProfile's own
`invulnerable_save` field. Deff from Above is NOT engine-wired, for the
same reason as Bomb Squigs above (see that note) - it's a once-per-Normal-
move reactive ability needing its own "which enemy unit did we move over"
detection, a D6-per-model roll, and per-model mortal wounds, i.e. real new
controller work, not a one-line hook extension.

Deff Dread is a single-model VEHICLE/WALKER, the first datasheet to set the
existing (previously unused) `walker` flag. Deadly Demise 1 needs no new
code at all - it's an existing generic mechanic (game/deadly_demise.py's
DeadlyDemiseController), already fully wired for T'au's own Devilfish/
Ghostkeel. Dead Choppy is NOT engine-wired as a live per-count calculation
- with only one modeled composition (always 2x Dread klaw), the +1-per-
additional-klaw bonus is simply baked into DreadKlawProfile's own fixed
Attacks value (see that class's own note in game/weapons.py) rather than
computed at runtime; nothing to recompute since there's no other loadout
to differ against yet. Piston-driven Brutality is NOT engine-wired, same
deliberate scope call as Tankbustas' Bomb Squigs/Deffkoptas' Deff from
Above - a reactive post-Charge ability needing its own target selection
and a two-tier D6 roll (2-5 vs 6) into mortal wounds, not a hook
extension.

Bodyguard is purely descriptive (`abilities_text`) for now, same status as
Kroot Carnivores' own Bodyguard text in game/factions/tau_empire.py: it
depends on the live Attached-Unit formation flow this engine doesn't have
yet (see that module's note). Get Da Good Bitz IS engine-wired: it's
word-for-word the same rule as Kroot Carnivores' own Fieldcraft, so both
BoyzProfile and BossNobProfile just set the shared `fieldcraft` flag and
reuse game/fieldcraft.py's apply_fieldcraft()/squad_has_fieldcraft() as-is
(see UnitProfile.fieldcraft's own note on why that field isn't
Kroot-exclusive) - no new code needed for this datasheet. Warbikers' own
Drive-by Dakka IS engine-wired too, but needed real new code (see
game/drive_by_dakka.py) rather than reusing an existing mechanism - it isn't
identical to any ability already built (Bonded Heroes' own 9" AP tier is the
closest match, but that's one tier of a two-tier S/AP ability gated on
BATTLESUIT, not a standalone rule). Stormboyz' Full Throttle is engine-wired
too - a named exception in game/charge.py's can_declare_charge(), the
charging equivalent of Battlesuit Support System's own shooting-after-
Fall-Back exception (see squad_has_full_throttle() in game/squad.py).
Trukk's Grot Riggers is engine-wired too (game/grot_riggers.py, called from
main.py's own start-of-Command-phase block, same hook as Support Turret's
own expiry) - genuinely new code again, no existing per-model wound-
regeneration mechanism to reuse.

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
    BeastSnaggaBoyProfile, BeastSnaggaNobProfile, BossNobOnWarbikeProfile, BoyzNobProfile, BoyzProfile,
    DeffDreadProfile, DeffkoptaProfile, GretchinProfile,
    MeganobzProfile, PainboyProfile, StormboyProfile, StormboyzNobProfile, TankbustaBossNobProfile,
    TankbustaProfile, TrukkProfile, WarbikerProfile, WarbossMegaArmourProfile, WarbossProfile,
)
from game.weapons import (
    BeastSnaggaChoppaProfile, BeastSnaggaKlawAndBeastchoppaProfile, BigShootaS5Profile,
    ButchaBoyzProfile, DeffRollaProfile, DoksToolzProfile, EavyLobbaProfile, FlashGitzChoppaProfile,
    GrabbinKlawProfile,
    LobbaProfile, SavageHornsAndHoovesProfile, TracksAndWheelsProfile, WreckinBallProfile,
    ZzapGunProfile,
    SawBladesProfile, SnazzgunProfile,
    ShootaProfile, StikkaKannonProfile, WurrtowerProfile,
    BigChoppaProfile, BigShootaProfile, BurnaProfile, ChoppaProfile, DreadKlawProfile,
    GrotBlastaProfile, KillsawProfile, KombiRokkitBustaRokkitProfile, KombiSkorchaShootaProfile,
    KombiWeaponShootaProfile, KoptaRokkitsProfile, KustomChoppaProfile,
    KustomShootaAimedProfile, KustomShootaProfile,
    OrkCloseCombatWeaponProfile, PowerKlawProfile, PowerSnappaProfile, RokkitLaunchaBlastaProfile,
    RokkitLunchaProfile, RokkitPistolProfile, ScavengedShivsProfile, SluggaProfile,
    SmashHammerProfile, SpikedWheelProfile, SpinninBladesProfile, StompyFeetProfile, TankbustaChoppaProfile,
    TankbustaCloseCombatWeaponProfile, ThumpGunProfile, TwinDakkagunProfile, TwinKillsawProfile,
    UgeChoppaProfile, UrtySyringeProfile,
    WarbossKustomChoppaProfile, WarbossPowerKlawProfile,
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

_WARBIKER_LOADOUT = [OrkCloseCombatWeaponProfile, TwinDakkagunProfile]

WARBIKERS_ADD_POWER_KLAW = "+ Power Klaw"

# Two composition sizes, same pattern datasheet.py's own docstring
# describes for Boyz' 10/20-model builds - the original 3-model composition
# (1 Boss Nob on Warbike + 2 Warbiker) plus a larger 6-model one, user-
# supplied separately via an actual army list ("6x Warbikers... 1x Boss Nob
# on Warbike + 5x Warbiker"). composition_index=0 is the original 3-model
# build, 1 is this new 6-model one.
WARBIKERS = ORKS.add_datasheet(Datasheet(
    "Warbikers",
    keywords=("MOUNTED", "GRENADES", "WARBIKERS", "SPEED FREEKS"),
    composition_options=[
        [
            ModelLine(BossNobOnWarbikeProfile, 1, _WARBIKER_LOADOUT, name="Boss Nob on Warbike"),
            ModelLine(WarbikerProfile, 2, _WARBIKER_LOADOUT, name="Warbiker"),
        ],
        [
            ModelLine(BossNobOnWarbikeProfile, 1, _WARBIKER_LOADOUT, name="Boss Nob on Warbike"),
            ModelLine(WarbikerProfile, 5, _WARBIKER_LOADOUT, name="Warbiker"),
        ],
    ],
    # Real wargear choice, user-supplied separately from the datasheet
    # itself (an army list build: "1x Boss Nob on Warbike: Close combat
    # weapon, Twin dakkagun, Power klaw" - all 3 weapons at once,
    # user-confirmed when asked: the Boss Nob keeps its Close Combat Weapon
    # AND gains a Power Klaw, a genuine second melee profile to choose
    # between each fight activation, not a replacement). replaces=None
    # since it's a pure addition, same pattern as e.g. Devilfish's Seeker
    # Missile option.
    wargear_options=[
        WargearOption("Boss Nob on Warbike", replaces=None, with_weapons=[PowerKlawProfile], max_models=1, name=WARBIKERS_ADD_POWER_KLAW),
    ],
    # Unselected Profiles (user-supplied reference block): a bare "3x
    # Warbiker, no Boss Nob" build reference - same weapons already used
    # above (Twin Dakkagun/Close combat weapon, just fewer copies) plus two
    # alternates, Slugga and Choppa, that already exist from Boyz (see
    # SluggaProfile/ChoppaProfile above) - no new classes needed. No
    # wargear-swap rule text given for either alternate, so still a
    # documented gap for those specifically.
    # Official list: 3 models 60 pts / 6 models 120 pts, no per-copy tiering -
    # and both of those sizes ARE modeled above, so either composition_index
    # prices correctly. The added Power Klaw is free on the list.
    points=ORKS_POINTS["Warbikers"],
    abilities_text=[
        'Drive-by Dakka: Each time a model in this unit makes a ranged attack that targets a unit '
        'within 9", improve the Armour Penetration characteristic of that attack by 1.',
        'Invulnerable Save (6+) [Warbikers]: Models in this unit have a 6+ invulnerable save.',
    ],
))

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

_TRUKK_LOADOUT = [BigShootaProfile, SpikedWheelProfile]

TRUKK = ORKS.add_datasheet(Datasheet(
    "Trukk",
    keywords=("DEDICATED TRANSPORT", "VEHICLE", "TRANSPORT", "TRUKK"),
    model_lines=[
        ModelLine(TrukkProfile, 1, _TRUKK_LOADOUT, name="Trukk"),
    ],
    # Unselected Profiles (user-supplied reference block): Wreckin' Ball -
    # now a real class (WreckinBallProfile), unlike Boyz's Power klaw, since
    # its WS4+ actually matches the Trukk's own weapon_skill (no per-weapon
    # WS override needed). No wargear-swap rule text given, so no
    # wargear_options yet, same documented gap as every other datasheet's
    # own Unselected Profiles.
    # Official list: 1 model 55 pts for your 1st to 3rd Trukk, 65 pts from the
    # 4th on - the demo scene's two Trukks are 55 each.
    points=ORKS_POINTS["Trukk"],
    abilities_text=[
        'Grot Riggers: At the start of your Command phase, this model regains 1 lost wound.',
        'Invulnerable Save (6+): This model has a 6+ invulnerable save.',
        'Transport: This model has a transport capacity of 12 ORKS INFANTRY models. Each MEGA '
        'ARMOUR model takes up the space of 2 models. It cannot transport JUMP PACK or GHAZGHKULL '
        'THRAKA models.',
    ],
))

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

_TANKBUSTA_BOSS_NOB_LOADOUT = [TankbustaChoppaProfile, RokkitPistolProfile, RokkitPistolProfile]
_TANKBUSTA_LOADOUT = [TankbustaCloseCombatWeaponProfile, RokkitLunchaProfile]

TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER = "Rokkit Pistol -> Rokkit Pistol + Smash Hammer"
TANKBUSTAS_ADD_ROKKIT_LAUNCHA = "+ Rokkit Launcha"

TANKBUSTAS = ORKS.add_datasheet(Datasheet(
    "Tankbustas",
    keywords=("INFANTRY", "TANKBUSTAS", "GRENADES"),
    model_lines=[
        ModelLine(TankbustaBossNobProfile, 1, _TANKBUSTA_BOSS_NOB_LOADOUT, name="Boss Nob"),
        ModelLine(TankbustaProfile, 5, _TANKBUSTA_LOADOUT, name="Tankbusta"),
    ],
    # Real wargear choices, user-supplied separately from the datasheet
    # itself (an army list build: Boss Nob "Choppa, Rokkit pistol, Smash
    # hammer" - one of the default 2x Rokkit pistol swapped for a Smash
    # Hammer, modeled as replacing BOTH default Rokkit pistols and adding
    # back one Rokkit pistol plus one Smash Hammer, since WargearOption's
    # own `replaces` filter removes every matching instance at once, not
    # just one of several duplicates - nets to the same final loadout
    # either way; and one Tankbusta "Close combat weapon, 2x Rokkit
    # launcha" - a second Rokkit launcha added, same "replace-then-re-add"
    # shape for the same reason.
    wargear_options=[
        WargearOption("Boss Nob", replaces=RokkitPistolProfile, with_weapons=[RokkitPistolProfile, SmashHammerProfile], max_models=1, name=TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER),
        WargearOption("Tankbusta", replaces=RokkitLunchaProfile, with_weapons=[RokkitLunchaProfile, RokkitLunchaProfile], max_models=1, name=TANKBUSTAS_ADD_ROKKIT_LAUNCHA),
    ],
    # Unselected Profiles (user-supplied reference block): a bare "2x
    # Tankbusta" reference build (same weapons already used above, just
    # fewer copies) plus one new alternate, Smash Hammer (now a real class,
    # SmashHammerProfile - see game/weapons.py's own note on its dual-
    # [ANTI-X] limitation) - now also a real wargear_option above, since an
    # actual list selected it. Pulsa Rokkit (a once-per-battle Strength/AP
    # buff, printed under the Unselected Profiles block) isn't wired either
    # - same "not part of the actual modeled loadout" reasoning.
    # Official list: 6 models 125 pts for your 1st-2nd Tankbustas unit, 135
    # from the 3rd on - this is the only size this datasheet's own list
    # prices, and it's exactly the 6-model build modeled here. Both wargear
    # options above are free on the list (no `points=` given for either).
    points=ORKS_POINTS["Tankbustas"],
    abilities_text=[
        'Tank Hunters: Each time a model in this unit makes an attack that targets a MONSTER or '
        'VEHICLE unit, add 1 to the Hit roll and add 1 to the Wound roll.',
        'Attached Unit: If a CHARACTER unit from your army with the Leader ability can be attached '
        'to a LOOTAS unit, it can be attached to this unit instead.',
        'Bomb Squigs: Once per battle, for each bomb squig this unit has, after this unit ends a '
        'Normal move, you can use one Bomb Squig. If you do, select one enemy unit within 12" and '
        'visible to this unit and roll one D6: on a 3+, that enemy unit suffers D3 mortal wounds.',
    ],
))
# Tank Hunters IS engine-wired - see this module's own docstring
# (TankbustaProfile's own `tank_hunters` flag in game/units.py and
# game/squad.py's tank_hunters_modifiers()). Attached Unit and Bomb Squigs
# are NOT engine-wired - see this module's own docstring for why (an
# Attached-Unit-flow gap and a deliberate scope call, respectively).

_DEFFKOPTA_LOADOUT = [KoptaRokkitsProfile, SluggaProfile, SpinninBladesProfile]

DEFFKOPTAS = ORKS.add_datasheet(Datasheet(
    "Deffkoptas",
    keywords=("VEHICLE", "FLY", "GRENADES", "DEFFKOPTAS", "SPEED FREEKS"),
    # Two composition sizes, same pattern as Warbikers/Stormboyz/Meganobz/
    # Flash Gitz - the printed 3-model build plus the 6-model one an actual
    # army list fields ("6x Deffkoptas: 6 with Kopta rokkits, Slugga,
    # Spinnin' blades"). composition_index=0 is the 3-model build, 1 the
    # 6-model one; the points list already prices both. No separate leader
    # ModelLine on this datasheet (like Meganobz, unlike Boyz/Stormboyz) -
    # every model shares DeffkoptaProfile's stat line and loadout, which is
    # exactly what "6 with Kopta rokkits, Slugga, Spinnin' blades" says.
    composition_options=[
        [ModelLine(DeffkoptaProfile, 3, _DEFFKOPTA_LOADOUT, name="Deffkopta")],
        [ModelLine(DeffkoptaProfile, 6, _DEFFKOPTA_LOADOUT, name="Deffkopta")],
    ],
    # Unselected Profiles (user-supplied reference block): a bare "2x
    # Deffkopta" reference build (same weapons already used above, just
    # fewer copies) plus one new alternate, Kustom Mega-Blasta (now a real
    # class, KustomMegaBlastaProfile - see game/weapons.py). No wargear-swap
    # rule text given, so no wargear_options yet - same documented gap as
    # every other datasheet's own Unselected Profiles.
    # Official list: 3 models 75 pts / 6 models 140 pts, no per-copy
    # tiering - both sizes are modeled and therefore both reachable.
    points=ORKS_POINTS["Deffkoptas"],
    abilities_text=[
        'Deff from Above: Each time this unit ends a Normal move, you can select one enemy unit it '
        'moved over during that move and roll one D6 for each model in this unit: for each 4+, that '
        'enemy unit suffers 1 mortal wound.',
        'Invulnerable Save (6+) [Deffkoptas]: Models in this unit have a 6+ invulnerable save.',
    ],
))
# Deff from Above is NOT engine-wired - see this module's own docstring for
# why (a deliberate scope call, same reasoning as Tankbustas' own Bomb
# Squigs). Invulnerable Save (6+) is just DeffkoptaProfile.invulnerable_save,
# no new code needed.

_DEFF_DREAD_LOADOUT = [StompyFeetProfile, BigShootaProfile, BigShootaProfile, DreadKlawProfile, DreadKlawProfile]

DEFF_DREAD = ORKS.add_datasheet(Datasheet(
    "Deff Dread",
    keywords=("VEHICLE", "WALKER", "DEFF DREAD"),
    model_lines=[
        ModelLine(DeffDreadProfile, 1, _DEFF_DREAD_LOADOUT, name="Deff Dread"),
    ],
    # Unselected Profiles (user-supplied reference block): Big shoota/Rokkit
    # launcha/Kustom mega-blasta all reuse existing classes (identical stat
    # lines to Trukk's/Tankbustas'/Deffkoptas' own weapons, see
    # game/weapons.py's own notes); Skorcha and the reference "Dread klaw"
    # row are also now real/reused classes. No wargear-swap rule text given
    # for any of these, so no wargear_options yet - same documented gap as
    # every other datasheet's own Unselected Profiles.
    # Official list: 1 model 110 pts for your 1st-2nd Deff Dread, 120 from
    # the 3rd on.
    points=ORKS_POINTS["Deff Dread"],
    abilities_text=[
        'Piston-driven Brutality: Each time this model ends a Charge move, select one enemy unit '
        'within Engagement Range of it and roll one D6: on a 2-5, that enemy unit suffers D3 mortal '
        'wounds; on a 6, that enemy unit suffers D3+3 mortal wounds.',
        'Invulnerable Save (6+): This model has a 6+ invulnerable save.',
        'Dead Choppy: The Attacks characteristic of this weapon is increased by 1 for each '
        'additional Dread klaw this model is equipped with.',
    ],
))
# Piston-driven Brutality is NOT engine-wired - see this module's own
# docstring for why (a deliberate scope call, same reasoning as Tankbustas'
# Bomb Squigs/Deffkoptas' Deff from Above). Dead Choppy is NOT engine-wired
# as a live calculation either - see DreadKlawProfile's own note in
# game/weapons.py (its fixed Attacks value already bakes in this loadout's
# only possible count). Invulnerable Save (6+) is just
# DeffDreadProfile.invulnerable_save, no new code needed.

_BEAST_SNAGGA_NOB_LOADOUT = [PowerSnappaProfile, SluggaProfile]
_BEAST_SNAGGA_BOY_LOADOUT = [BeastSnaggaChoppaProfile, SluggaProfile]

BEAST_SNAGGA_BOYZ_THUMP_GUN = "+ Thump Gun"
FLASH_GITZ_AMMO_RUNT = "Ammo Runt"


def _apply_ammo_runt(token):
    """Flags the bearer as carrying an Ammo Runt. Unlike a drone's effect
    this changes no characteristic at all - the ability it grants is
    resolved at shooting time, see game/ammo_runt.py."""
    token.ammo_runt = True


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
    keywords=("MONSTER", "TRANSPORT", "PSYKER", "BEAST SNAGGA", "KILL RIG"),
    model_lines=[
        ModelLine(KillRigProfile, 1, _KILL_RIG_LOADOUT, name="Kill Rig"),
    ],
    # No Unselected Profiles block and no Wargear Options text were given -
    # every one of the six printed weapons is carried at once, which is the
    # whole loadout. Same documented gap as Warboss in Mega Armour's entry.
    #
    # Three melee weapons, but that is not three swings: Butcha boyz and
    # Savage horns and hooves both have [EXTRA ATTACKS] (24.11), so they
    # resolve ALONGSIDE the model's chosen weapon rather than competing with
    # it under rule 04.01 - in practice Saw blades plus both extras.
    #
    # Official list: 1 model 145 pts, no per-copy tiering.
    points=ORKS_POINTS["Kill Rig"],
    abilities_text=[
        'Spirit of Gork (Psychic): At the start of the Fight phase, you can select one friendly '
        'ORKS unit within 12" of this model and roll one D6: on a 1, this model suffers D3 mortal '
        'wounds; on a 2-5, until the end of the phase, add 1 to the Strength characteristic of '
        'melee weapons equipped by models in that unit; on a 6, until the end of the phase, add 1 '
        'to the Strength characteristic of melee weapons equipped by models in that unit and those '
        'weapons have the [LETHAL HITS] ability.',
        'Damaged: 1-5 Wounds Remaining: While this model has 1-5 wounds remaining, each time this '
        'model makes an attack, subtract 1 from the Hit roll.',
        'Deadly Demise D6: When this model is destroyed, roll one D6. On a 6, each unit within 6" '
        'suffers D6 mortal wounds.',
        'Feel No Pain 6+: Each time an attack is allocated to this model, roll one D6: on a 6, that '
        'attack is ignored.',
        'Transport: This model has a transport capacity of 11 BEAST SNAGGA INFANTRY models.',
    ],
))
# Only Spirit of Gork needed new code (game/spirit_of_gork.py, chained into
# game/fight.py and driven from main.py's own start-of-Fight-phase block) -
# and the AI resolves it deterministically on the highest-points eligible
# unit via the controller's own auto_players, per explicit user instruction,
# so no ai/agent_driver.py change was needed either. Everything else is an
# existing generic field: Damaged 1-5 is `damaged_threshold`, Deadly Demise
# D6 is `deadly_demise_notation`, Feel No Pain 6+ is `feel_no_pain`, and the
# Transport line is transport_capacity/transport_requires_infantry plus the
# new `transport_requires` for its BEAST SNAGGA half (see
# UnitProfile.transport_requires - the inclusive counterpart of the existing
# transport_excludes, which could only ever express a refusal).
#
# NOTE: like Beast Snagga Boyz and Beastboss, this datasheet is NOT in any
# demo army yet (main.py) and has no sprite in Sprites/.

_FLASH_GITZ_LOADOUT = [FlashGitzChoppaProfile, SnazzgunProfile]

FLASH_GITZ = ORKS.add_datasheet(Datasheet(
    "Flash Gitz",
    keywords=("INFANTRY", "GRENADES", "FLASH GITZ"),
    # Two composition sizes, same pattern as Warbikers/Stormboyz/Meganobz -
    # the printed 5-model build plus the 10-model one an actual army list
    # fields ("10x Flash Gitz ... 1x Kaptin + 9x Flash Gitz").
    # composition_index=0 is the 5-model build, 1 the 10-model one; the
    # points list already prices both.
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
    # Unselected Profiles (user-supplied reference block): just restates the
    # same Snazzgun and Choppa the loadout above already uses, one copy
    # instead of five - no new classes needed, nothing left unused. This is
    # the first datasheet here whose Unselected Profiles block adds nothing
    # at all.
    #
    # Official list: 5 models 75 pts / 10 models 150 pts for your 1st-2nd
    # Flash Gitz unit, 85/160 from the 3rd on - both sizes are modeled
    # above, so either composition_index prices correctly.
    #
    # NOT modeled: "Ammo Runt", which the supplied army list gives this unit.
    # No rule text and no price were supplied for it, and it is not on the
    # published points list this module reads, so there is nothing to build
    # against - flagged rather than invented. (The list's own 160 pts for a
    # 10-model unit against the published 150 is consistent with it costing
    # 10, but that is an inference, not a source.)
    points=ORKS_POINTS["Flash Gitz"],
    # Ammo Runt is a Gear item rather than a WargearOption because it swaps
    # no weapons - it grants an ability, which is what Gear's effect(token)
    # callback is for (same shape as the Battlewagon's 'Ard Case). FREE here:
    # the published points list carries no wargear entry for this datasheet,
    # and the supplied army list's own 160 vs the published 150 is an
    # inference about its cost, not a source - so no price is invented.
    gear_options=[
        Gear("Kaptin", FLASH_GITZ_AMMO_RUNT, _apply_ammo_runt),
    ],
    gear_slots={"Kaptin": 1},
    abilities_text=[
        'Gun-crazy Show-offs: Each time a model in this unit targets the closest eligible target '
        'with its Snazzgun, until the end of the phase, that weapon has an Attacks characteristic '
        'of 4.',
        'Ammo Runt: Once per battle, when this unit is selected to shoot, it can use this ability. '
        'If it does, until the end of the phase, ranged weapons equipped by models in this unit '
        'have the [LETHAL HITS] ability.',
    ],
))
# Gun-crazy Show-offs IS engine-wired (game/gun_crazy_showoffs.py). It reuses
# the closest-eligible-target snapshot ShootingController already computes
# for The Twin Lance's Exemplars of Mont'ka, so the expensive half needed no
# new code - but unlike every other weapon adjuster in game/shooting.py it
# has to be applied BEFORE the attack count is summed rather than at the
# hit/wound step, because it changes the Attacks characteristic itself.
#
# NOTE: like Beast Snagga Boyz, Beastboss and Kill Rig, this datasheet is NOT
# in any demo army yet (main.py) and has no sprite in Sprites/.

_BATTLEWAGON_LOADOUT = [TracksAndWheelsProfile]

BATTLEWAGON_ARD_CASE = "'Ard Case"
BATTLEWAGON_ADD_BIG_SHOOTAS = "+ 4x Big Shoota"
BATTLEWAGON_ADD_ZZAP_GUN = "+ Zzap Gun"


def _apply_ard_case(token):
    """"Add 2 to the bearer's Toughness characteristic, but it no longer has
    the Firing Deck ability."

    Mutates this token's OWN profile instance - build_squad() gives every
    token a fresh one (see game/factions/datasheet.py), so nothing else on
    the board is touched. Both halves are applied together because the
    printed wargear is one item: the +2 T is the whole reason to take it and
    losing Firing Deck 11 is what it costs."""
    token.profile.toughness += 2
    token.profile.firing_deck = 0


BATTLEWAGON = ORKS.add_datasheet(Datasheet(
    "Battlewagon",
    keywords=("VEHICLE", "TRANSPORT", "BATTLEWAGON"),
    model_lines=[
        ModelLine(BattlewagonProfile, 1, _BATTLEWAGON_LOADOUT, name="Battlewagon"),
    ],
    # 'Ard Case is a real, PRICED option - the one Ork wargear cost on the
    # published list is "Battlewagon: per 'ard case 15 pts", stored in
    # game/factions/orks_points.py long before this datasheet existed and
    # now finally read. It is a Gear item rather than a WargearOption
    # because it swaps no weapons at all: it changes a characteristic and
    # removes an ability, which is exactly what Gear's effect(token)
    # callback is for.
    # Real wargear choice, user-supplied separately from the datasheet
    # itself (an army list build: "1x Battlewagon: 'Ard Case, 4x Big shoota,
    # Zzap gun, Tracks and wheels") - the same "an actual list selected it"
    # evidence that turned Boyz' Power Klaw and Tankbustas' Smash Hammer
    # into real options. replaces=None since the Big shootas are a pure
    # addition alongside Tracks and wheels, and free on the published list.
    #
    # The Zzap gun is the same kind of addition, and the first weapon in this
    # engine with a DICE-ROLLED Strength ("S D6+6") - see ZzapGunProfile and
    # WeaponProfile.strength_notation.
    wargear_options=[
        WargearOption(
            "Battlewagon", replaces=None,
            with_weapons=[BigShootaProfile] * 4, max_models=1,
            name=BATTLEWAGON_ADD_BIG_SHOOTAS,
        ),
        WargearOption(
            "Battlewagon", replaces=None, with_weapons=[ZzapGunProfile], max_models=1,
            name=BATTLEWAGON_ADD_ZZAP_GUN,
        ),
    ],
    gear_options=[
        Gear("Battlewagon", BATTLEWAGON_ARD_CASE, _apply_ard_case,
             points=ORKS_POINTS["Battlewagon"].wargear["'ard case"]),
    ],
    gear_slots={"Battlewagon": 1},
    # Unselected Profiles (user-supplied reference block): Big shoota and
    # Wreckin' ball reuse existing classes unchanged (identical stat lines to
    # Trukk's own, see game/weapons.py); Lobba, Grabbin' klaw and Deff rolla
    # are new classes there. None is wired as a wargear option - no swap-rule
    # text was given for them, the same documented gap as every other
    # datasheet's Unselected Profiles.
    #
    # Official list: 1 model 145 pts, no per-copy tiering, plus 15 pts per
    # 'ard case.
    points=ORKS_POINTS["Battlewagon"],
    abilities_text=[
        'Ramshackle but Rugged: Each time an attack is allocated to this model, worsen the Armour '
        'Penetration characteristic of that attack by 1.',
        'Damaged: 1-5 Wounds Remaining: While this model has 1-5 wounds remaining, each time this '
        'model makes an attack, subtract 1 from the Hit roll.',
        'Invulnerable Save (6+): This model has a 6+ invulnerable save.',
        'Deadly Demise D6: When this model is destroyed, roll one D6. On a 6, each unit within 6" '
        'suffers D6 mortal wounds.',
        'Firing Deck 11: Each time this model shoots, up to 11 models embarked within it can each '
        'have one of their ranged weapons fired as if by this model.',
        'Transport: This model has a transport capacity of 22 ORKS INFANTRY models. If this model '
        'is equipped with a Killkannon, it has a transport capacity of 12 ORKS INFANTRY models. '
        'Each MEGA ARMOUR or JUMP PACK model takes up the space of 2 models. The GHAZGHKULL THRAKA '
        'model takes up the space of 4 models.',
        "'Ard Case: Add 2 to the bearer's Toughness characteristic, but it no longer has the Firing "
        'Deck ability.',
    ],
))
# Only Ramshackle but Rugged needed new code (game/ramshackle.py) - and it is
# the FIRST defensive adjuster in this engine: every other one belongs to the
# attacker and is chained onto the weapon while its group resolves, this one
# belongs to the target and is applied at rule 05.03's allocation step, in
# game/damage_resolution.py. Everything else is an existing generic field:
# Damaged 1-5 is `damaged_threshold`, Deadly Demise D6 is
# `deadly_demise_notation`, Invulnerable Save 6+ is `invulnerable_save`, and
# Firing Deck 11 is `firing_deck` (game/firing_deck.py, built for the
# Devilfish). Its Transport line needed one small generalisation: JUMP PACK
# models now cost 2 capacity alongside MEGA ARMOUR ones, see
# game/transport.py's _model_capacity_cost().
#
# TWO printed clauses are NOT modeled, both because the thing they refer to
# does not exist here: the Killkannon (a weapon this datasheet has no wargear
# text for, which would drop capacity 22 -> 12) and GHAZGHKULL THRAKA taking
# 4 slots (no such datasheet).

register_faction(ORKS)
