"""Orks faction data.

Army rule "Waaagh!" is supplied and engine-wired (game/waaagh.py -
WaaaghController, wired into ChargeController/FightController/
ShootingController/DamageAllocationSession, plus main.py's own start-of-
Command-phase block for the expiry) - see that module's own docstring for
the full rule text and reasoning. The AI (Player 2) calls it via a
deterministic "always in battle round 2" policy, ai/agent_driver.py's
_maybe_call_waaagh() (user instruction, not a judgment call - never asks
the agent). No UI button exists yet for the human player (Player 1) to call
one themselves - out of scope for what was asked so far, WaaaghController.
call()/can_call() are ready for it whenever that's wanted. Detachment rule
is still to come (user announcement, not yet supplied). This module
currently holds sixteen datasheets: Boyz, Warbikers, Stormboyz, Trukk,
Gretchin, Warboss, Meganobz, Warboss in Mega Armour, Tankbustas,
Deffkoptas, Deff Dread, Beast Snagga Boyz, Beastboss, Kill Rig, Flash Gitz,
Battlewagon - every
one of their UnitProfile classes sets `waaagh = True` (user: "ALLE bisher
angelegten Ork einheiten haben die Waaagh! ability").

Beast Snagga Boyz is the newest, and the first datasheet in this module
whose ability needed a RE-ROLL hook rather than a modifier hook: Monster
Hunters ("you can re-roll the Hit roll" against a MONSTER/VEHICLE target)
reads the same target condition as Tankbustas' Tank Hunters, but a re-roll
cannot be expressed as a Modifier - it needs the dice already read - so it
hooks the hit-roll STEP in BOTH game/shooting.py and game/fight.py (its
text says "makes an attack", not "makes a ranged attack"). See
game/monster_hunters.py's own docstring, including why it re-rolls the
whole roll rather than just the misses. Its Feel No Pain 6+ needed no code
at all (`feel_no_pain` is an existing generic UnitProfile field, rule
24.12). Its one wargear option is also what generalised
WargearOption.replaces to accept several weapons at once - the thump gun
carrier gives up its Slugga AND its Choppa - see that class's own note.

Beastboss is its Leader, and the first Ork Leader datasheet here with NO
deferred ability: its "Beastboss" rule is word-for-word the Warbosses' own
Might is Right (so it reuses that flag outright), Invulnerable Save 5+ and
Feel No Pain 6+ are existing generic UnitProfile fields, the Leader pairing
is already in the points list that game/attached_units.py reads, and only
Ferocious Rage needed new code (game/ferocious_rage.py - [DEVASTATING
WOUNDS] on its own melee weapons for the rest of a turn in which it
charged, keyed off ChargeController.charged_squad_ids, which already has
exactly that lifetime). It is also the datasheet that finally generalised
WeaponProfile.anti from one (keyword, threshold) tuple to a sequence: both
its melee weapons print Anti-Monster 4+ AND Anti-Vehicle 4+, the first real
fielded loadout to do so - Tankbustas' Smash Hammer had the same pair as an
Unselected Profile and had been silently losing half of it, and gets it
back for free.

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

Warboss is a standalone single-model Character/Leader datasheet, unlike the
other five (each a squad built from several ModelLines). Its Leader ability
("can be attached to Boyz/Nobz") and Might is Right (a per-attached-unit
Hit-roll buff) are NOT engine-wired - both depend on the live Attached-Unit
formation flow this engine deliberately doesn't have yet (same documented
gap as Boyz'/Kroot Carnivores' own Bodyguard text below), so they're
abilities_text only. Da Biggest and da Best IS engine-wired though - it's
self-contained (only affects the Warboss's own melee weapons, no attached-
unit dependency) - see the new `waaagh_biggest_and_best` UnitProfile flag
and game/waaagh.py's waaagh_extra_attacks(), which folds it into the
existing army-wide Waaagh! Attacks bonus rather than needing a second
mechanism. Its Invulnerable Save (5+) is just WarbossProfile's own
`invulnerable_save` field, same as Warbikers'/Trukk's own printed 6+ - no
new code, and it happens to coincide numerically with (but is distinct
from) the conditional 5+ that Waaagh! itself grants every `waaagh` model.

Meganobz is the first MEGA ARMOUR datasheet - the new `mega_armour`
UnitProfile flag makes Trukk's own "each MEGA ARMOUR model takes up the
space of 2 models" transport-capacity rule reachable for the first time
(previously documented as unreachable in TrukkProfile's own note, since no
such datasheet existed yet), see game/transport.py's
_model_capacity_cost(). Krumpin' Time IS engine-wired, same "self-contained,
no Attached-Unit dependency" reasoning as Da Biggest and da Best - the new
`krumpin_time` flag and game/waaagh.py's effective_feel_no_pain() grant
Feel No Pain 5+ while the Waaagh! is active, threaded through
DamageAllocationSession/MortalWoundAllocationSession/
DevastatingWoundAllocationSession wherever their owning FightController/
ShootingController already carry a `self.waaagh` (normal shooting/fight
damage, devastating wounds, hazard mortal wounds) - NOT threaded into
game/crushing_impact.py, game/deadly_demise.py, game/explosives.py or
game/hazard.py's own mortal-wound sessions, none of which are given a
WaaaghController at all (a documented, narrower gap - see
effective_feel_no_pain()'s own note).

Warboss in Mega Armour is a second standalone single-model Character/Leader
datasheet (like the plain Warboss), this time a MEGA ARMOUR one - "can be
attached to Meganobz" and Might is Right are NOT engine-wired, same
Attached-Unit-flow gap as every other Leader/Bodyguard text in this module.
Dead Brutal IS engine-wired though (same "self-contained, no attached-unit
dependency" reasoning as Da Biggest and da Best/Krumpin' Time) - see the
new `waaagh_dead_brutal_damage` UnitProfile flag and game/waaagh.py's
waaagh_melee_adjusted_weapon(), which now folds in an ABSOLUTE Damage
override (not a bonus, unlike every other Waaagh!-related adjustment) on
top of its existing Strength bonus.

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

Detachment "War Horde" is supplied and engine-wired too (game/war_horde.py -
get_stuck_in_adjusted_weapon(), chained into FightController the same way
Bonded Heroes/Waaagh! are, see that module's own docstring), as is its
Unbridled Carnage stratagem (game/unbridled_carnage.py - melee Critical Hits
on an unmodified 5+, which is what makes Get Stuck In's army-wide [SUSTAINED
HITS 1] worth 1 CP to double up on). Same
"currently the only detachment, so it's applied unconditionally, no army-
building/detachment-selection flow" simplification as Retaliation Cadre's
own note in game/factions/tau_empire.py - every Ork UnitProfile here also
sets a new `orks` flag (see UnitProfile.orks' own note) so this rule has
something to check, since there's no generic per-model Faction tracking to
read instead.

Gretchin's own "Runtherd" ability is engine-wired directly inside
game/squad.py's attached_unit_toughness() (see that function's own note) -
the exact same "what T does an attack against this mixed unit resolve
against" question it already answered for real Attached Units, just with
one more case. Thievin' Scavengers is engine-wired too (game/
thievin_scavengers.py - ThievinScavengersController, called from main.py's
own start-of-Movement-phase block, with a real visible DiceManager roll per
user instruction) - the first datasheet ability in this engine that grants
CP outright rather than just a combat/movement effect.

Points costs live in game/factions/orks_points.py (the whole published list -
all 58 entries, including the 53 units without a datasheet here yet), same
arrangement as game/factions/tau_empire.py and its own points module: each
datasheet below only points its `points=` field at its entry there, so no
cost is written down twice. See game/factions/points.py for the structure."""

from game.factions import Datasheet, Detachment, Faction, Gear, ModelLine, WargearOption, register_faction
from game.factions.orks_points import ORKS_POINTS
from game.units import (
    BattlewagonProfile, BeastbossProfile, FlashGitzKaptinProfile, FlashGitzProfile, KillRigProfile,
    BeastSnaggaBoyProfile, BeastSnaggaNobProfile, BossNobOnWarbikeProfile, BossNobProfile, BoyzProfile,
    DeffDreadProfile, DeffkoptaProfile, GretchinProfile,
    MeganobzProfile, PainboyProfile, RuntherdProfile, StormboyProfile, StormboyzBossNobProfile, TankbustaBossNobProfile,
    TankbustaProfile, TrukkProfile, WarbikerProfile, WarbossMegaArmourProfile, WarbossProfile,
)
from game.weapons import (
    BeastchoppaProfile, BeastSnaggaChoppaProfile, BeastSnaggaCloseCombatWeaponProfile, BeastSnaggaKlawProfile,
    ButchaBoyzProfile, DeffRollaProfile, EavyLobbaProfile, FlashGitzChoppaProfile, GrabbinKlawProfile,
    LobbaProfile, SavageHornsAndHoovesProfile, TracksAndWheelsProfile, WreckinBallProfile,
    AttackSquigProfile, ZzapGunProfile,
    SawBladesProfile, SnazzgunProfile,
    ShootaProfile, StikkaKannonProfile, WurrtowerProfile,
    BigChoppaProfile, BigShootaProfile, ChoppaProfile, DreadKlawProfile, GretchinCloseCombatWeaponProfile,
    GrotBlastaProfile, GrotSmackaProfile, KombiWeaponProfile, KoptaRokkitsProfile, KustomShootaProfile,
    OrkCloseCombatWeaponProfile, PowerKlawProfile, PowerSnappaProfile, RokkitLunchaProfile, RokkitPistolProfile,
    SluggaProfile,
    SmashHammerProfile, SpikedWheelProfile, SpinninBladesProfile, StompyFeetProfile, TankbustaChoppaProfile,
    TankbustaCloseCombatWeaponProfile, ThumpGunProfile, TwinDakkagunProfile, TwinSluggaProfile, UgeChoppaProfile,
    UrtySyringeProfile,
    WarbossBigChoppaProfile,
)

ORKS = Faction("Orks", "ORKS")

WAR_HORDE = ORKS.add_detachment(Detachment(
    "War Horde",
    rule_text=(
        'Get Stuck In: Melee weapons equipped by Orks models from your army have the '
        '[SUSTAINED HITS 1] ability.'
    ),
))

_BOSS_NOB_LOADOUT = [SluggaProfile, BigChoppaProfile]
_BOY_LOADOUT = [SluggaProfile, ChoppaProfile]

BOYZ_BIG_CHOPPA_TO_POWER_KLAW = "Big Choppa -> Power Klaw"

BOYZ = ORKS.add_datasheet(Datasheet(
    "Boyz",
    keywords=("BATTLELINE", "INFANTRY", "MOB", "GRENADES", "BOYZ"),
    # Both printed sizes, same pattern as WARBIKERS below.
    # composition_index=0 is the 10-model build, 1 the 20-model one - the
    # latter added when an actual army list fielded it, and it is not merely
    # a bigger mob: the "Bodyguard" ability's two-Leader exception is written
    # against "a Starting Strength of 20", so the 20-model build is the only
    # one that can ever take a Warboss AND a second Leader (see
    # game/attached_units.py's can_attach()).
    composition_options=[
        [
            ModelLine(BossNobProfile, 1, _BOSS_NOB_LOADOUT, name="Boss Nob"),
            ModelLine(BoyzProfile, 9, _BOY_LOADOUT, name="Boy"),
        ],
        [
            ModelLine(BossNobProfile, 1, _BOSS_NOB_LOADOUT, name="Boss Nob"),
            ModelLine(BoyzProfile, 19, _BOY_LOADOUT, name="Boy"),
        ],
    ],
    # Real wargear choice, user-supplied separately from the datasheet
    # itself (an army list build: "1x Boss Nob: Power klaw, Slugga") - now
    # a real WargearOption, since PowerKlawProfile exists (see
    # game/weapons.py's own note on why it was deferred until an actual
    # list selected it).
    wargear_options=[
        WargearOption("Boss Nob", replaces=BigChoppaProfile, with_weapons=[PowerKlawProfile], max_models=1, name=BOYZ_BIG_CHOPPA_TO_POWER_KLAW),
    ],
    # Unselected Profiles (user-supplied reference block): Boy w/ Shoota,
    # Boy w/ Kombi-weapon, Boy w/ Slugga (base stat line only, no wargear-
    # swap rule text given - see game/weapons.py's ShootaProfile/
    # KombiWeaponProfile), plus Close combat weapon (x2) (now a real class,
    # OrkCloseCombatWeaponProfile - see WARBIKERS below, which needs the
    # identical stat line for its own actual default loadout). No
    # wargear-swap rule text given for the Boy's own alternates, so still a
    # documented gap for those specifically.
    # Official list: 10 models 75 pts / 20 models 160 pts for your 1st to 3rd
    # Boyz unit, 85/170 from the 4th on - both now reachable, see
    # composition_options above. The Power Klaw swap is free on the list.
    points=ORKS_POINTS["Boyz"],
    abilities_text=[
        'Get Da Good Bitz: At the end of your Command phase, if this unit is within range of an '
        'objective marker you control, that objective marker remains under your control, even if '
        'you have no models within range of it, until your opponent controls it at the start or '
        'end of any turn.',
        'Bodyguard: If this unit has a Starting Strength of 20, you can attach up to two Leader '
        'units to it instead of one (but only if one of those is a WARBOSS model). If you do, and '
        'this unit is destroyed, the Leader units attached to it become separate units with their '
        'original Starting Strengths.',
    ],
))
# Get Da Good Bitz is engine-wired (see game/squad.py's
# squad_has_get_da_good_bitz()). Bodyguard's FIRST sentence is now wired too -
# BoyzProfile/BossNobProfile carry `bodyguard_two_leaders`, which
# game/attached_units.py's can_attach() reads (it used to be purely
# descriptive, which was fine only while no army list wanted two Leaders on
# one mob). Its SECOND sentence - the attached Leaders splitting back into
# separate units when the mob is destroyed - is still NOT wired: that needs a
# runtime split of an attached unit, which rule 19.04 itself never asks for
# anywhere else, so it stays the documented gap it always was.

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

_STORMBOY_LOADOUT = [SluggaProfile, ChoppaProfile]

STORMBOYZ_CHOPPA_TO_POWER_KLAW = "Choppa -> Power Klaw"

# Two composition sizes, same pattern as Warbikers above - the original
# 5-model build (1 Boss Nob + 4 Stormboy) plus a larger 10-model one,
# user-supplied separately via an actual army list ("10x Stormboyz... 1x
# Boss Nob + 9x Stormboy"). composition_index=0 is the original 5-model
# build, 1 is this new 10-model one.
STORMBOYZ = ORKS.add_datasheet(Datasheet(
    "Stormboyz",
    keywords=("INFANTRY", "JUMP PACK", "FLY", "GRENADES", "STORMBOYZ"),
    composition_options=[
        [
            ModelLine(StormboyzBossNobProfile, 1, _STORMBOY_LOADOUT, name="Boss Nob"),
            ModelLine(StormboyProfile, 4, _STORMBOY_LOADOUT, name="Stormboy"),
        ],
        [
            ModelLine(StormboyzBossNobProfile, 1, _STORMBOY_LOADOUT, name="Boss Nob"),
            ModelLine(StormboyProfile, 9, _STORMBOY_LOADOUT, name="Stormboy"),
        ],
    ],
    # Real wargear choice, user-supplied separately from the datasheet
    # itself (an army list build: "1x Boss Nob: Slugga, Power klaw") - same
    # pattern as Boyz's own Big-Choppa-to-Power-Klaw option above.
    wargear_options=[
        WargearOption("Boss Nob", replaces=ChoppaProfile, with_weapons=[PowerKlawProfile], max_models=1, name=STORMBOYZ_CHOPPA_TO_POWER_KLAW),
    ],
    # Official list: 5 models 65 pts / 10 models 130 pts, no per-copy tiering -
    # both sizes modeled above, so either composition_index prices correctly.
    points=ORKS_POINTS["Stormboyz"],
    abilities_text=[
        'Full Throttle: This unit is eligible to declare a charge in a turn in which it Advanced or '
        'Fell Back.',
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

_GRETCHIN_LOADOUT = [GretchinCloseCombatWeaponProfile, GrotBlastaProfile]
_RUNTHERD_LOADOUT = [GrotSmackaProfile, SluggaProfile]

GRETCHIN = ORKS.add_datasheet(Datasheet(
    "Gretchin",
    keywords=("INFANTRY", "GRETCHIN", "GROTS"),
    model_lines=[
        ModelLine(GretchinProfile, 10, _GRETCHIN_LOADOUT, name="Gretchin"),
        ModelLine(RuntherdProfile, 1, _RUNTHERD_LOADOUT, name="Runtherd"),
    ],
    # Unselected Profiles (user-supplied reference block): just restates
    # both model lines' own base stats/weapons - no new classes needed,
    # nothing left unused.
    # Official list: this is the one entry priced per COMPOSITION rather than
    # per bare model count ("10 Gretchin 45 / 1 Runtherd, 10 Gretchin 45 / 20
    # Gretchin 80 / 1 Runtherd, 20 Gretchin 85 / 2 Runtherd, 20 Gretchin 90")
    # - see game/factions/orks_points.py on why a model-count table still
    # captures that exactly. The composition modeled here is 10 Gretchin + 1
    # Runtherd = 11 models = 45 pts.
    points=ORKS_POINTS["Gretchin"],
    abilities_text=[
        'Runtherd: Each time an attack targets this unit, if it contains one or more Gretchin '
        'models, until that attack is resolved, Runtherd models in this unit have a Toughness '
        'characteristic of 2.',
        "Thievin' Scavengers: At the start of your Movement phase, roll one D6 for each objective "
        'marker you control that has one or more units from your army with this ability within '
        'range of it (excluding Battle-shocked units). If one or more of those rolls is a 4+, you '
        'gain 1CP.',
    ],
))

_WARBOSS_LOADOUT = [KombiWeaponProfile, TwinSluggaProfile, WarbossBigChoppaProfile]

WARBOSS_ADD_ATTACK_SQUIG = "+ Attack Squig"

WARBOSS = ORKS.add_datasheet(Datasheet(
    "Warboss",
    keywords=("CHARACTER", "WARBOSS", "INFANTRY", "GRENADES"),
    model_lines=[
        ModelLine(WarbossProfile, 1, _WARBOSS_LOADOUT, name="Warboss"),
    ],
    # Unselected Profiles (user-supplied reference block): Power klaw (A4
    # WS3+ S10 AP-2 D2) - now a real class (WarbossPowerKlawProfile, see
    # game/weapons.py), distinct from Boyz/Stormboyz/Warbikers' shared
    # PowerKlawProfile since the numbers differ. No wargear-swap rule text
    # given, so no wargear_options yet - same documented gap as every other
    # datasheet's own Unselected Profiles.
    # Real wargear choice, user-supplied separately from the datasheet itself
    # (an army list build: "1x Warboss: Kombi-weapon, Twin slugga, Attack
    # squig, Big choppa") - a pure addition, and free on the published list.
    # [EXTRA ATTACKS] is what lets the squig bite alongside whatever the
    # Warboss himself swings under rule 04.01.
    wargear_options=[
        WargearOption(
            "Warboss", replaces=None, with_weapons=[AttackSquigProfile], max_models=1,
            name=WARBOSS_ADD_ATTACK_SQUIG,
        ),
    ],
    # Official list: 1 model 85 pts, leads Boyz/Nobz (see
    # game/factions/orks_points.py's _LEADS_BOYZ_MOBS).
    points=ORKS_POINTS["Warboss"],
    abilities_text=[
        'Might is Right: While this model is leading a unit, each time a model in that unit makes '
        'a melee attack, add 1 to the Hit roll.',
        'Da Biggest and da Best: While the Waaagh! is active for your army, add 4 to the Attacks '
        "characteristic of this model's melee weapons.",
        'Invulnerable Save (5+): This model has a 5+ invulnerable save.',
        'Leader: This model can be attached to the following units: Boyz, Nobz.',
    ],
))
# Might is Right and Leader are NOT engine-wired - see this module's own
# docstring (same Attached-Unit-flow gap as Boyz'/Kroot Carnivores' own
# Bodyguard text). Da Biggest and da Best IS engine-wired (see
# WarbossProfile's own `waaagh_biggest_and_best` flag in game/units.py and
# game/waaagh.py's waaagh_extra_attacks()). Invulnerable Save (5+) is just
# WarbossProfile.invulnerable_save, no new code needed.

_MEGANOB_LOADOUT = [KustomShootaProfile, PowerKlawProfile]

MEGANOBZ = ORKS.add_datasheet(Datasheet(
    "Meganobz",
    keywords=("INFANTRY", "GRENADES", "MEGANOBZ", "MEGA ARMOUR"),
    # Two composition sizes, same pattern as Warbikers/Stormboyz's own
    # 2-size handling - the original 2-model build plus a larger 6-model
    # one, user-supplied separately via an actual army list ("6x Meganobz:
    # 6 with Kustom shoota, Power klaw"). composition_index=0 is the
    # original 2-model build, 1 is this new 6-model one. No separate Boss
    # Nob/leader ModelLine on this datasheet (unlike Boyz/Stormboyz/
    # Warbikers) - every model shares MeganobzProfile's exact stat line and
    # loadout regardless of unit size.
    composition_options=[
        [ModelLine(MeganobzProfile, 2, _MEGANOB_LOADOUT, name="Meganob")],
        [ModelLine(MeganobzProfile, 6, _MEGANOB_LOADOUT, name="Meganob")],
    ],
    # Unselected Profiles (user-supplied reference block): Kombi-weapon (x2)
    # - not a new class, identical stat line to KombiWeaponProfile (Boyz'
    # own Unselected Profiles entry, already reused as-is by Warboss);
    # Killsaw (x3)/Twin killsaw - now real classes (KillsawProfile/
    # TwinKillsawProfile, see game/weapons.py), Power klaw (x3) reuses the
    # existing PowerKlawProfile (identical A3 WS4+ S9 AP-2 D2 stat line to
    # Boyz/Stormboyz/Warbikers' shared Boss Nob upgrade). No wargear-swap
    # rule text given for any of these, so no wargear_options yet - same
    # documented gap as every other datasheet's own Unselected Profiles.
    # Official list: 2/3/5/6-model sizes (60/90/150/180 pts for your
    # 1st-2nd unit, 80/110/170/200 from the 3rd on) - only 2 and 6 are
    # modeled above (the two sizes an actual list has needed so far), 3/5
    # remain priced but unreachable, same "some sizes modeled, the rest
    # priced but unbuilt" pattern as Boyz'/Kroot Carnivores' own larger
    # composition.
    points=ORKS_POINTS["Meganobz"],
    abilities_text=[
        "Krumpin' Time: While the Waaagh! is active for your army, models in this unit have the "
        'Feel No Pain 5+ ability.',
    ],
))
# Krumpin' Time IS engine-wired - see this module's own docstring
# (MeganobzProfile's own `krumpin_time` flag in game/units.py and
# game/waaagh.py's effective_feel_no_pain()).

_WARBOSS_MEGA_ARMOUR_LOADOUT = [BigShootaProfile, UgeChoppaProfile]

WARBOSS_MEGA_ARMOUR = ORKS.add_datasheet(Datasheet(
    "Warboss in Mega Armour",
    keywords=("CHARACTER", "INFANTRY", "WARBOSS IN MEGA ARMOUR", "MEGA ARMOUR", "WARBOSS"),
    model_lines=[
        ModelLine(WarbossMegaArmourProfile, 1, _WARBOSS_MEGA_ARMOUR_LOADOUT, name="Warboss in Mega Armour"),
    ],
    # No Unselected Profiles block was given for this datasheet.
    # Official list: 1 model 80 pts, leads Meganobz (see
    # game/factions/orks_points.py's own entry).
    points=ORKS_POINTS["Warboss in Mega Armour"],
    abilities_text=[
        'Might is Right: While this model is leading a unit, each time a model in that unit makes '
        'a melee attack, add 1 to the Hit roll.',
        "Dead Brutal: While the Waaagh! is active for your army, this model's 'uge Choppa has a "
        'Damage characteristic of 3.',
        'Invulnerable Save (5+): This model has a 5+ invulnerable save.',
        'Leader: This model can be attached to the following unit: Meganobz.',
    ],
))
# Might is Right and Leader are NOT engine-wired - see this module's own
# docstring (same Attached-Unit-flow gap as every other Leader/Bodyguard
# text here). Dead Brutal IS engine-wired (see WarbossMegaArmourProfile's
# own `waaagh_dead_brutal_damage` flag in game/units.py and
# game/waaagh.py's waaagh_melee_adjusted_weapon()). Invulnerable Save (5+)
# is just WarbossMegaArmourProfile.invulnerable_save, no new code needed.

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
# BeastSnaggaChoppaProfile, NOT Boyz' own ChoppaProfile - this datasheet's
# printed Choppa is S5 where Boyz' is S4 (see game/weapons.py's own note).
_BEAST_SNAGGA_BOY_LOADOUT = [BeastSnaggaChoppaProfile, SluggaProfile]

BEAST_SNAGGA_BOYZ_THUMP_GUN = "Slugga + Choppa -> Thump Gun"
FLASH_GITZ_AMMO_RUNT = "Ammo Runt"


def _apply_ammo_runt(token):
    """Flags the bearer as carrying an Ammo Runt. Unlike a drone's effect
    this changes no characteristic at all - the ability it grants is
    resolved at shooting time, see game/ammo_runt.py."""
    token.ammo_runt = True

BEAST_SNAGGA_BOYZ = ORKS.add_datasheet(Datasheet(
    "Beast Snagga Boyz",
    keywords=("BATTLELINE", "INFANTRY", "MOB", "BEAST SNAGGA", "BEAST SNAGGA BOYZ"),
    model_lines=[
        ModelLine(BeastSnaggaNobProfile, 1, _BEAST_SNAGGA_NOB_LOADOUT, name="Beast Snagga Nob"),
        ModelLine(BeastSnaggaBoyProfile, 9, _BEAST_SNAGGA_BOY_LOADOUT, name="Beast Snagga Boy"),
    ],
    # The second user-supplied stat block (a lone "Beast Snagga Boy" with
    # Thump gun + Close combat weapon instead of Slugga + Choppa) is modeled
    # as a real wargear option rather than a second composition: it shares
    # this datasheet's exact stat line and only its weapons differ, which is
    # what a WargearOption is. The alternate block prints NEITHER a Slugga
    # nor a Choppa, so both are given up at once - hence the two-weapon
    # `replaces` (see WargearOption's own note on why that form exists, and
    # how it differs from Tankbustas' "replace-then-re-add" shape).
    #
    # ASSUMPTION, flagged: no "Wargear Options" rule text was supplied for
    # this datasheet, so the cap is inferred rather than quoted.
    # per_models=10 encodes the conventional wording for exactly this kind
    # of upgrade ("for every 10 models in this unit, 1 model can be equipped
    # with..."), which is also what the published points list points to - it
    # carries no per-thump-gun cost, i.e. a fixed allowance rather than a
    # paid per-model upgrade. For the 10-model composition modeled here it
    # resolves to 1 either way; per_models is preferred over a flat
    # max_models=1 only because it stays right if the 20-model build is ever
    # modeled.
    wargear_options=[
        WargearOption(
            "Beast Snagga Boy", replaces=(SluggaProfile, BeastSnaggaChoppaProfile),
            with_weapons=[ThumpGunProfile, BeastSnaggaCloseCombatWeaponProfile],
            per_models=10, name=BEAST_SNAGGA_BOYZ_THUMP_GUN,
        ),
    ],
    # Official list: 10 models 90 pts / 20 models 170 pts, no per-copy
    # tiering. Only the 10-model build is modeled here (model_lines, not
    # composition_options), so the 20-model price is carried but not yet
    # reachable - same "one size modeled, the rest priced but unbuilt"
    # pattern as Boyz'/Deffkoptas' own larger composition. The thump gun
    # swap is free on the list.
    points=ORKS_POINTS["Beast Snagga Boyz"],
    abilities_text=[
        'Monster Hunters: Each time a model in this unit makes an attack that targets a MONSTER or '
        'VEHICLE unit, you can re-roll the Hit roll.',
        'Feel No Pain 6+: Each time an attack is allocated to this model, roll one D6: on a 6, that '
        'attack is ignored.',
    ],
))
# Monster Hunters IS engine-wired - see game/monster_hunters.py, hooked into
# BOTH game/shooting.py's and game/fight.py's own hit-roll step (its text
# says "makes an attack", not "makes a ranged attack" - the same both-phases
# reasoning as Tankbustas' own Tank Hunters). Note it re-rolls the WHOLE Hit
# roll rather than just the misses, on the same literal reading of "you can
# re-roll the Hit roll" that decided Breach and Clear/Sunforge - see that
# module's docstring. Feel No Pain 6+ needs no new code at all -
# `feel_no_pain` is an existing generic UnitProfile field (rule 24.12),
# already read wherever damage is allocated. This datasheet's `waaagh` flag
# is set on both its profiles like every other Ork unit here.
#
# NOTE: this datasheet is NOT in any demo army yet (main.py) - same status as
# the T'au Riptide/Pathfinder Team when each was first added. It also has no
# sprite in Sprites/, so it renders as a plain token (missing art is fine by
# this project's convention, see game/sprites.py).

_BEASTBOSS_LOADOUT = [BeastSnaggaKlawProfile, BeastchoppaProfile, ShootaProfile]

BEASTBOSS = ORKS.add_datasheet(Datasheet(
    "Beastboss",
    keywords=("CHARACTER", "INFANTRY", "BEAST SNAGGA", "BEASTBOSS", "WARBOSS"),
    model_lines=[
        ModelLine(BeastbossProfile, 1, _BEASTBOSS_LOADOUT, name="Beastboss"),
    ],
    # No Unselected Profiles block was given for this datasheet, and no
    # Wargear Options text either - so no wargear_options, same documented
    # gap as Warboss in Mega Armour's own entry.
    #
    # Both melee weapons are carried at once, and that is the point rather
    # than an oversight: rule 04.01 lets a model swing only ONE melee weapon
    # per fight activation, so the two profiles are a real per-activation
    # choice (klaw = S10/AP-2 at WS3+, choppa = 6 attacks at WS2+). Same
    # shape as Commander Farsight's two Dawn Blade modes.
    #
    # Official list: 1 model 80 pts, leads Beast Snagga Boyz - that pairing
    # already sits in game/factions/orks_points.py's own entry, which is
    # what game/attached_units.py's can_attach() reads, so the Leader
    # ability needs no separate wiring here.
    points=ORKS_POINTS["Beastboss"],
    abilities_text=[
        'Beastboss: While this model is leading a unit, each time a model in that unit makes a '
        'melee attack, add 1 to the Hit roll.',
        'Ferocious Rage: Each time this model makes a Charge move, until the end of the turn, melee '
        'weapons it is equipped with have the [DEVASTATING WOUNDS] ability.',
        'Invulnerable Save (5+): This model has a 5+ invulnerable save.',
        'Feel No Pain 6+: Each time an attack is allocated to this model, roll one D6: on a 6, that '
        'attack is ignored.',
        'Leader: This model can be attached to the following unit: Beast Snagga Boyz.',
    ],
))
# Every one of these is engine-wired, which makes this the first Ork Leader
# datasheet with no deferred ability at all:
#   * "Beastboss" is word-for-word the Warbosses' own Might is Right, so it
#     reuses that exact flag and game/squad.py's squad_has_might_is_right()
#     - no new code. (Both Warboss datasheets' own copies were left
#     unwired back when there was no Attached-Unit flow; there is one now.)
#   * Ferocious Rage is new - see game/ferocious_rage.py, chained into
#     game/fight.py next to War Horde's Get Stuck In.
#   * Invulnerable Save (5+) and Feel No Pain 6+ are existing generic
#     UnitProfile fields (`invulnerable_save`, `feel_no_pain`).
#   * Leader is real: the legal pairing lives in the points list, which
#     game/attached_units.py's can_attach() already reads.
#
# NOTE: like Beast Snagga Boyz, this datasheet is NOT in any demo army yet
# (main.py) and has no sprite in Sprites/ - it renders as a plain token,
# which is fine by this project's convention (see game/sprites.py).

_PAINBOY_LOADOUT = [UrtySyringeProfile, PowerKlawProfile]

PAINBOY_GROT_ORDERLY = "Grot Orderly"


def _apply_grot_orderly(token):
    """Flags the bearer as carrying a Grot Orderly. Like the Ammo Runt this
    changes no characteristic - the ability is resolved in the Command phase,
    see game/grot_orderly.py."""
    token.grot_orderly = True


PAINBOY = ORKS.add_datasheet(Datasheet(
    "Painboy",
    keywords=("CHARACTER", "INFANTRY", "PAINBOY"),
    model_lines=[
        ModelLine(PainboyProfile, 1, _PAINBOY_LOADOUT, name="Painboy"),
    ],
    # Both melee weapons are carried at once, and unlike the Beastboss's pair
    # that is NOT a per-activation choice: the 'Urty syringe has [EXTRA
    # ATTACKS] (24.11), so rule 04.01's one-melee-weapon limit does not apply
    # to it and both swing every activation - the same shape as the Warboss's
    # Attack Squig. That is what makes the syringe's [ANTI-INFANTRY 4+] worth
    # having on an S2 weapon: it is not there to wound, it is there to score
    # critical wounds for Hold Still and Say 'Aargh!'.
    #
    # No Unselected Profiles block and no weapon-swap text were supplied, so
    # no wargear_options - the same documented gap every other Ork Character
    # datasheet here carries. The Grot Orderly IS supplied, and is a Gear item
    # rather than a WargearOption for the same reason as Flash Gitz' Ammo Runt:
    # it swaps no weapons, it grants an ability. Free - the published points
    # list carries no wargear entry for this datasheet.
    gear_options=[
        Gear("Painboy", PAINBOY_GROT_ORDERLY, _apply_grot_orderly),
    ],
    gear_slots={"Painboy": 1},
    # Official list: 1 model 90 pts. The pairing table it also carries is what
    # game/attached_units.py's can_attach() reads - see PainboyProfile's own
    # docstring on the leader-vs-support discrepancy between that entry and
    # this datasheet's printed "Abilities (Leader)" heading.
    points=ORKS_POINTS["Painboy"],
    abilities_text=[
        "Dok's Toolz: While this model is leading a unit, models in that unit have the "
        'Feel No Pain 5+ ability.',
        "Hold Still and Say 'Aargh!': Each time an attack made by this model with its "
        "'Urty syringe scores a Critical Wound against a unit (excluding VEHICLE units), "
        'that unit suffers D6 mortal wounds.',
        'Grot Orderly: Once per battle, in your Command phase, if the bearer is leading a unit '
        'that is below its Starting Strength, you can return up to D3 destroyed Bodyguard models '
        'to that unit.',
        'Leader: This model can be attached to the following units: Boyz, Nobz, Lootas, '
        'Burna Boyz, Tankbustas.',
    ],
))
# All four are engine-wired:
#   * Dok's Toolz - game/doks_toolz.py, folded into game/feel_no_pain.py's
#     current_feel_no_pain(), so it reaches every damage source uniformly.
#   * Hold Still and Say 'Aargh!' - game/hold_still.py, chained into
#     game/fight.py's wound-resolution tail (melee-only by construction).
#   * Grot Orderly - game/grot_orderly.py, a Command-phase controller; the
#     first ability in this engine that puts models BACK into a unit.
#   * Leader - the legal pairings live in the points list, which
#     game/attached_units.py's can_attach() already reads.
#
# NOTE: like the Beastboss, this datasheet is NOT in any demo army yet
# (main.py) and has no sprite in Sprites/ - it renders as a plain token,
# which is fine by this project's convention (see game/sprites.py).

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
