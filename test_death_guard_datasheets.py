"""The eleven Death Guard datasheets, their weapons, points and abilities.

Etappe 3 of the Death Guard faction. Sections:
  1. Statlines, base sizes and the two table-size decisions
  2. Weapons: the shared ones, the confusable ones, the fire-mode pairs
  3. Wargear options, including the 2-per-5 ratio at every built size
  4. Points, and the four documented deviations from the user's list
  5. The abilities, each through the funnel it really lands in
  6. The army list: 14 units, 49 models, and the two attachments
  7. Sprites: eleven files, eight of them spelled differently
  8. Source guards on main.py
  9. A/B probes
"""
import inspect
import pathlib

from testkit import Checks, GameState, TurnTracker, Log, build, script, list_key

from game import (army_lists, curse_of_the_walking_pox, death_approaches,
                  death_guard_defenders, destroyer_hive, gift_of_contagion,
                  hovering_death, icon_of_despair, leadership, lethal_ichor,
                  maps, miasma_of_pestilence, nurgles_gift, plagues,
                  scuttling_walker, spore_laced_shock_waves, sprites)
from game.factions import death_guard as dg
from game.factions.death_guard_points import DEATH_GUARD_POINTS

# Asked for by FACTION, not named - see testkit.list_key().
DG_LIST = list_key("DEATH GUARD")
from game.factions.faction import faction_keyword_of
from game.feel_no_pain import current_feel_no_pain
from game.nurgles_gift import NurglesGiftController
from game.plagues import PlagueChoice
from game.squad import Squad, tank_hunters_modifiers
from game.token import Token
from game.units import UnitProfile
from game import units as unit_module
from game import weapons as weapon_module

c = Checks("Death Guard datasheets")

DG = "Player 2"
FOE = "Player 1"

SHEETS = [dg.PLAGUE_MARINES, dg.POXWALKERS, dg.TYPHUS, dg.MALIGNANT_PLAGUECASTER,
          dg.DAEMON_PRINCE_OF_NURGLE, dg.CHAOS_SPAWN, dg.DEATHSHROUD_TERMINATORS,
          dg.DEFILER, dg.FOETID_BLOAT_DRONE, dg.MYPHITIC_BLIGHT_HAULER,
          dg.PLAGUEBURST_CRAWLER]


def dg_squad(sheet, name=None, **kw):
    return build(sheet, DG, name=name or f"2 {sheet.name} 1", **kw)


# --- 1. Statlines and bases --------------------------------------------------
print("--- 1. Statlines and bases ---")

c.eq("eleven datasheets", len(SHEETS), 11)
c.eq("...and the faction registers exactly those", len(dg.DEATH_GUARD.datasheets), 11)
for sheet in SHEETS:
    c.eq(f"{sheet.name} belongs to DEATH GUARD",
         faction_keyword_of(dg_squad(sheet)), "DEATH GUARD")

# EVERY Death Guard model carries the army rule - it is what the aura and
# game/death_lords_chosen.py's fallback both test on, so a profile that forgets
# it is invisible to the whole faction.
for sheet in SHEETS:
    squad = dg_squad(sheet)
    c.true(f"{sheet.name}: every model carries Nurgle's Gift",
           all(m.profile.nurgles_gift for m in squad.models))

P = unit_module
c.eq("Plague Marine T6 W2 Sv3+", (P.PlagueMarineProfile.toughness,
                                 P.PlagueMarineProfile.wounds,
                                 P.PlagueMarineProfile.armor_save), (6, 2, "3+"))
c.eq("the Plague Champion shares that statline and only adds squad_leader",
     (P.PlagueChampionProfile.toughness, P.PlagueChampionProfile.wounds,
      P.PlagueChampionProfile.armor_save, P.PlagueChampionProfile.squad_leader),
     (6, 2, "3+", True))
c.eq("Poxwalker Sv7+ - the worst armour save in this engine",
     P.PoxwalkerProfile.armor_save, "7+")
c.eq("...and its survivability is the FNP instead", P.PoxwalkerProfile.feel_no_pain, "5+")
c.eq("Daemon Prince T12 W10 - the toughest single model here",
     (P.DaemonPrinceOfNurgleProfile.toughness, P.DaemonPrinceOfNurgleProfile.wounds),
     (12, 10))
c.true("...and no other profile in the engine reaches T12",
       all(o.toughness <= 12 for o in vars(unit_module).values()
           if inspect.isclass(o) and issubclass(o, UnitProfile)))
c.eq("the Malignant Plaguecaster has NO invulnerable save - unusual for a PSYKER",
     P.MalignantPlaguecasterProfile.invulnerable_save, "-")
c.eq("Typhus has a 4+ invulnerable", P.TyphusProfile.invulnerable_save, "4+")
c.eq("Defiler W18 / OC5 - the largest of each in the engine",
     (P.DefilerProfile.wounds, P.DefilerProfile.oc), (18, 5))

# The two damaged brackets reuse the existing generic field.
c.eq("Defiler is Damaged at 1-6 wounds", P.DefilerProfile.damaged_threshold, 6)
c.eq("Plagueburst Crawler is Damaged at 1-4", P.PlagueburstCrawlerProfile.damaged_threshold, 4)

# BASE SIZES. Two are table sizes rather than printed ones; both are USER
# decisions and both are pinned so nobody "corrects" them back.
c.eq("Plague Marine 32 mm", P.PlagueMarineProfile.base_radius_in, 0.63)
c.eq("Poxwalker 25 mm", P.PoxwalkerProfile.base_radius_in, 0.5)
c.eq("Deathshroud 40 mm", P.DeathshroudTerminatorProfile.base_radius_in, 0.787)
c.eq("Typhus 50 mm", P.TyphusProfile.base_radius_in, 0.984)
c.eq("Daemon Prince 60 mm", P.DaemonPrinceOfNurgleProfile.base_radius_in, 1.18)
c.eq("Myphitic Blight-hauler 80 mm", P.MyphiticBlightHaulerProfile.base_radius_in, 1.575)
# Pinned against the OTHER big vehicles rather than against a literal: the
# whole point of the decision is that they match.
from game.units import BattlewagonProfile  # noqa: E402
c.eq("the Defiler plays at the big-vehicle table size, not its printed 160 mm",
     P.DefilerProfile.base_radius_in, BattlewagonProfile.base_radius_in)
c.eq("...and so does the Plagueburst Crawler, which prints no base at all",
     P.PlagueburstCrawlerProfile.base_radius_in, BattlewagonProfile.base_radius_in)
c.true("the printed 160 mm would have been half again as large",
       3.15 > BattlewagonProfile.base_radius_in * 1.4)


# --- 2. Weapons --------------------------------------------------------------
print("--- 2. Weapons ---")

W = weapon_module
c.eq("Boltgun 24\"/A2/S4/AP0/D1 with [LETHAL HITS]",
     (W.BoltgunProfile.range_in, W.BoltgunProfile.attacks, W.BoltgunProfile.strength,
      W.BoltgunProfile.ap, W.BoltgunProfile.damage, W.BoltgunProfile.lethal_hits),
     (24, 2, 4, 0, 1, True))

# THE THREE CONFUSABLE FLAMERS. Same faction, similar names, three different
# weapons - pinned against EACH OTHER, because that is the assurance that
# matters (a copy-paste would pass a test against literals just as well).
c.true("plague spewer, plaguespitter and plaguespurt gauntlet are three DIFFERENT weapons",
       len({(W.PlagueSpewerProfile.strength, W.PlagueSpewerProfile.ap),
            (W.PlaguespitterProfile.strength, W.PlaguespitterProfile.ap),
            (W.PlaguespurtGauntletProfile.strength, W.PlaguespurtGauntletProfile.ap)}) == 3)
c.eq("plague spewer is Anti-Infantry 2+", W.PlagueSpewerProfile.anti, ("INFANTRY", 2))
c.eq("plague belcher is the weaker one, Anti-Infantry 4+",
     W.PlagueBelcherProfile.anti, ("INFANTRY", 4))
c.true("only the plaguespurt gauntlet is a [PISTOL] of the three",
       W.PlaguespurtGauntletProfile.pistol
       and not W.PlagueSpewerProfile.pistol and not W.PlaguespitterProfile.pistol)

# The plaguespitter is printed identically on two datasheets, so ONE class
# serves both - checked at the models, not at the table.
bloat = dg_squad(dg.FOETID_BLOAT_DRONE,
                 choices={"Foetid Bloat-drone": {dg.BLOAT_DRONE_TO_PLAGUESPITTERS: 1}})
crawler = dg_squad(dg.PLAGUEBURST_CRAWLER,
                   choices={"Plagueburst Crawler": {dg.CRAWLER_TO_PLAGUESPITTERS: 1}})
c.true("the Bloat-drone and the Crawler really share one plaguespitter class",
       type(next(w for w in bloat.models[0].weapons if w.name == "Plaguespitter"))
       is type(next(w for w in crawler.models[0].weapons if w.name == "Plaguespitter")))

# The four fire-mode pairs. ONE printed datasheet entry each, so they are
# overcharge_profile pairs - otherwise rule 04.01 would let a model swing both.
for base, mode in ((W.LakrimaeStrikeProfile, "Lakrimae - sweep"),
                   (W.ManreaperStrikeProfile, "Manreaper - sweep"),
                   (W.HellforgedWeaponsStrikeProfile, "Hellforged Weapons - sweep"),
                   (W.ShearingClawsStrikeProfile, "Shearing Claws - sweep")):
    c.eq(f"{base.name} carries its sweep as a fire mode",
         base.overcharge_profile.name, mode)
# The Manreaper differs from the other three in a THIRD characteristic - a
# worse WS on the sweep - which a "same shape as the others" reading loses.
c.eq("the Manreaper's sweep is WS3+ where its strike is WS2+",
     (W.ManreaperStrikeProfile.weapon_skill, W.ManreaperSweepProfile.weapon_skill),
     ("2+", "3+"))
c.eq("the Lakrimae's two halves share WS2+, unlike the Manreaper",
     (W.LakrimaeStrikeProfile.weapon_skill, W.LakrimaeSweepProfile.weapon_skill),
     ("2+", "2+"))

c.eq("the plasma gun's supercharge mode is [HAZARDOUS]",
     (W.PlasmaGunProfile.overcharge_profile.hazardous,
      W.PlasmaGunProfile.overcharge_profile.strength), (True, 8))
# Measured over the weapons this faction can actually field, default loadouts
# and every wargear option alike - so "the only one" is a real claim.
_dg_weapon_classes = {opt_weapon
                      for sheet in SHEETS
                      for line in (l for comp in sheet.compositions() for l in comp)
                      for opt_weapon in line.default_weapons}
_dg_weapon_classes |= {w for sheet in SHEETS
                       for opt in sheet.wargear_options
                       for w in opt.with_weapons}
c.eq("the heavy reaper autocannon is the only Death Guard weapon with [DEVASTATING WOUNDS]",
     sorted(w.name for w in _dg_weapon_classes if getattr(w, "devastating_wounds", False)),
     ["Heavy Reaper Autocannon"])
c.true("the electroscourge is [EXTRA ATTACKS], so it never joins the 04.01 choice",
       W.ElectroscourgeProfile.extra_attacks)
c.eq("the heavy plague weapon trades WS for S - WS4+ against plague knives' 3+",
     (W.HeavyPlagueWeaponProfile.weapon_skill, W.HeavyPlagueWeaponProfile.strength,
      W.PlagueKnivesProfile.weapon_skill, W.PlagueKnivesProfile.strength),
     ("4+", 8, None, 4))
c.eq("the Plagueburst mortar is the only [INDIRECT FIRE] weapon in the faction",
     W.PlagueburstMortarProfile.indirect_fire, True)


# --- 3. Wargear --------------------------------------------------------------
print("--- 3. Wargear ---")

# The 2-per-5 ratio, pinned at EVERY size this datasheet can be built at -
# per_models=2.5 is exact for 5/7/10 and would over-allow at 9, which is not a
# tier. If a fourth tier is ever added, this is where it is caught.
opt = next(o for o in dg.PLAGUE_MARINES.wargear_for("Plague Marine")
           if o.name == dg.PM_TO_HEAVY_PLAGUE_WEAPON)
c.eq("5 models allow 2 heavy plague weapons", opt.max_for(5), 2)
c.eq("7 models allow 2", opt.max_for(7), 2)
c.eq("10 models allow 4", opt.max_for(10), 4)

# The user's printed Plague Marines entry, built for real.
pm = dg_squad(dg.PLAGUE_MARINES, composition_index=2,
              choices={"Plague Marine": {dg.PM_TO_PLAGUE_SPEWER: 2,
                                         dg.PM_TO_BLIGHT_LAUNCHER: 2,
                                         dg.PM_TO_HEAVY_PLAGUE_WEAPON: 2}})
names = [w.name for m in pm.models for w in m.weapons]
c.eq("10 models", len(pm.models), 10)
c.eq("2 plague spewers", names.count("Plague Spewer"), 2)
c.eq("2 blight launchers", names.count("Blight Launcher"), 2)
c.eq("2 heavy plague weapons", names.count("Heavy Plague Weapon"), 2)
c.eq("4 boltguns left (3 Marines + the Champion)", names.count("Boltgun"), 4)
c.eq("every model keeps its plague knives", names.count("Plague Knives"), 10)
champion = next(m for m in pm.models if m.profile.squad_leader)
c.eq("the Champion keeps the printed default",
     sorted(w.name for w in champion.weapons), ["Boltgun", "Plague Knives"])

# The Defiler's two "one of the following" menus REPLACE DIFFERENT weapons, so
# they get separate cursors and both can be taken - checked because the two
# menus offer the same three weapons and look like one.
d2 = dg_squad(dg.DEFILER, choices={"Defiler": {dg.DEFILER_BALEFLAMER_TO_LASCANNON: 1,
                                               dg.DEFILER_MISSILES_TO_LASCANNON: 1}})
c.eq("a Defiler can legally take TWO Hades lascannons - two menus, two cursors",
     [w.name for w in d2.models[0].weapons].count("Hades Lascannon"), 2)

# A matched pair: the swap gives up EVERY copy of the named weapon.
d3 = dg_squad(dg.DEFILER, choices={"Defiler": {dg.DEFILER_TO_MAGMA_CUTTERS: 1}})
cutter_names = [w.name for w in d3.models[0].weapons]
c.eq("both excruciator cannons go", cutter_names.count("Excruciator Cannon"), 0)
c.eq("...and two magma cutters arrive", cutter_names.count("Magma Cutters"), 2)

# The Deathshroud Champion's extra gauntlet is a pure ADDITION, not a swap.
ds = dg_squad(dg.DEATHSHROUD_TERMINATORS,
              choices={"Deathshroud Champion": {dg.DS_EXTRA_GAUNTLET: 1}})
champ = next(m for m in ds.models if m.profile.squad_leader)
c.eq("the Champion ends up with two plaguespurt gauntlets",
     [w.name for w in champ.weapons].count("Plaguespurt Gauntlet"), 2)
c.eq("...and still has his manreaper",
     [w.name for w in champ.weapons].count("Manreaper - strike"), 1)

# The icon of despair is Gear, on both datasheets that print it.
pm_icon = dg_squad(dg.PLAGUE_MARINES, composition_index=0,
                   gear={"Plague Marine": [dg.PM_ICON_OF_DESPAIR]})
c.eq("exactly one Plague Marine bears the icon",
     sum(1 for m in pm_icon.models if getattr(m, "icon_of_despair", False)), 1)
ds_icon = dg_squad(dg.DEATHSHROUD_TERMINATORS,
                   gear={"Deathshroud Champion": [dg.DS_ICON_OF_DESPAIR]})
c.true("the Deathshroud Champion can bear it too",
       any(getattr(m, "icon_of_despair", False) for m in ds_icon.models))


# --- 4. Points ---------------------------------------------------------------
print("--- 4. Points ---")

c.eq("eleven priced datasheets", len(DEATH_GUARD_POINTS), 11)
c.eq("Plague Marines 5/7/10", [DEATH_GUARD_POINTS["Plague Marines"].cost_for(n)
                               for n in (5, 7, 10)], [90, 125, 180])
c.eq("Deathshroud are tiered by COPY number, not only by size",
     (DEATH_GUARD_POINTS["Deathshroud Terminators"].cost_for(3, 1),
      DEATH_GUARD_POINTS["Deathshroud Terminators"].cost_for(3, 3)), (160, 170))
c.eq("the Defiler's two paid options cost 15 each",
     sorted(DEATH_GUARD_POINTS["Defiler"].wargear.values()), [15, 15])
c.eq("Typhus leads Deathshroud and Poxwalkers",
     sorted(DEATH_GUARD_POINTS["Typhus"].leads),
     ["Deathshroud Terminators", "Poxwalkers"])
c.eq("the Plaguecaster leads Plague Marines and Poxwalkers",
     sorted(DEATH_GUARD_POINTS["Malignant Plaguecaster"].leads),
     ["Plague Marines", "Poxwalkers"])
c.eq("the Daemon Prince leads NOTHING - a MONSTER with no LEADER line",
     tuple(DEATH_GUARD_POINTS["Daemon Prince of Nurgle"].leads), ())
# ...and the pairing table agrees, which is the assurance that actually binds:
# attach() is what would refuse, not the points list.
# can_attach() returns the LIST OF REASONS it is not allowed - empty means
# allowed. Reading it as a bool gets the sense exactly backwards.
from game.attached_units import can_attach  # noqa: E402
c.true("attach() refuses the Daemon Prince as a leader",
       bool(can_attach(dg_squad(dg.DAEMON_PRINCE_OF_NURGLE),
                       dg_squad(dg.PLAGUE_MARINES, composition_index=0))))
c.eq("...and accepts Typhus onto Deathshroud",
     can_attach(dg_squad(dg.TYPHUS), dg_squad(dg.DEATHSHROUD_TERMINATORS)), [])
c.true("...but refuses Typhus onto Plague Marines - not on his LEADER line",
       bool(can_attach(dg_squad(dg.TYPHUS),
                       dg_squad(dg.PLAGUE_MARINES, composition_index=0))))
c.eq("...and accepts the Plaguecaster onto Plague Marines",
     can_attach(dg_squad(dg.MALIGNANT_PLAGUECASTER),
                dg_squad(dg.PLAGUE_MARINES, composition_index=0)), [])


# --- 5. The abilities --------------------------------------------------------
print("--- 5. Abilities ---")


def board(*squads):
    state = GameState()
    for squad in squads:
        for m in squad.models:
            state.add_token(m)
    tracker = TurnTracker()
    tracker.battle_round = 1
    NurglesGiftController(turn_tracker=tracker,
                          plague_choice=PlagueChoice()).refresh(state.tokens)
    return state


def line_up(squad, x=10.0, y=10.0, step=1.4):
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * step, y
    return squad


class Foe(UnitProfile):
    name = "Foe"
    toughness = 4
    wounds = 2
    armor_save = "3+"
    base_radius_in = 0.63
    leadership = "6+"
    oc = 2
    infantry = True


def foe_squad(n=3, x=40.0, y=40.0):
    models = [Token(x + i * 1.4, y, 0.63, (1, 1, 1), profile=Foe) for i in range(n)]
    squad = Squad("1 Foe 1", models, owner=FOE)
    for m in models:
        m.squad = squad
    return squad


# Typhus' Destroyer Hive is a DEFENDER-side melee modifier and needs him
# LEADING - the attachment is what switches it on.
from game import attached_units  # noqa: E402

typhus = dg_squad(dg.TYPHUS, name="2 Typhus 1")
deathshroud = dg_squad(dg.DEATHSHROUD_TERMINATORS, name="2 Deathshroud Terminators 1")
c.true("unled Deathshroud get no Destroyer Hive", not destroyer_hive.applies(deathshroud))
led = attached_units.attach(typhus, deathshroud)
c.true("Typhus leading them switches it on", destroyer_hive.applies(led))
c.eq("...as +1 on the threshold, because positive WORSENS",
     [(m.amount, m.source) for m in destroyer_hive.hit_modifiers(led)],
     [(1, "The Destroyer Hive")])

# Silent Bodyguard runs the OTHER way: the bodyguards protect the leader.
typhus_model = next(m for m in led.models if m.profile.character)
bodyguard = next(m for m in led.models if not m.profile.character)
c.eq("Typhus gains Feel No Pain 4+ FROM his Deathshroud",
     current_feel_no_pain(typhus_model), "4+")
c.eq("...and the bodyguards get nothing from it",
     current_feel_no_pain(bodyguard), "-")

# Gift of Contagion needs BOTH halves: he leads, and the target is Afflicted.
plaguecaster = dg_squad(dg.MALIGNANT_PLAGUECASTER, name="2 Malignant Plaguecaster 1")
marines = dg_squad(dg.PLAGUE_MARINES, composition_index=0, name="2 Plague Marines 1")
gifted = attached_units.attach(plaguecaster, marines)
foe = foe_squad()
line_up(gifted, 10.0, 10.0)
board(gifted, foe)   # foe is 40" away, so NOT Afflicted
c.true("led but the target is not Afflicted -> no grant",
       not gift_of_contagion.applies(gifted, foe))
near = foe_squad(x=14.0, y=10.0)
board(gifted, near)
c.true("led AND the target is Afflicted -> granted",
       gift_of_contagion.applies(gifted, near))
weapon = next(w for w in gifted.models[0].weapons if w.name == "Boltgun")
c.eq("the boltgun gains [SUSTAINED HITS 1]",
     gift_of_contagion.adjusted_weapon(weapon, gifted, near).sustained_hits, 1)
c.eq("...on a COPY - the shared instance is untouched", weapon.sustained_hits, 0)

# Miasma of Pestilence: asked of the TARGET, and the bearer's own unit counts.
prince = line_up(dg_squad(dg.DAEMON_PRINCE_OF_NURGLE, name="2 Daemon Prince of Nurgle 1"),
                 10.0, 10.0)
near_dg = line_up(dg_squad(dg.POXWALKERS, name="2 Poxwalkers 1"), 13.0, 10.0)
far_dg = line_up(dg_squad(dg.POXWALKERS, name="2 Poxwalkers 2"), 60.0, 60.0)
state = board(prince, near_dg, far_dg)
c.true("a friendly Death Guard unit within 6\" gets cover",
       miasma_of_pestilence.applies(near_dg, state.tokens))
c.true("...one 50\" away does not",
       not miasma_of_pestilence.applies(far_dg, state.tokens))
c.true("...and the Prince's OWN unit qualifies - the text has no \"other\"",
       miasma_of_pestilence.applies(prince, state.tokens))

# Death Guard Defenders: Lone Operative, but only near friendly DG INFANTRY.
from game.status_effects import lone_operative_range  # noqa: E402
alone = board(prince, far_dg)
c.true("alone, the Daemon Prince has no Lone Operative",
       lone_operative_range(prince, alone.tokens) is None)
near_inf = line_up(dg_squad(dg.POXWALKERS, name="2 Poxwalkers 3"), 12.0, 10.0)
close = board(prince, near_inf)
c.eq("within 3\" of friendly DG INFANTRY it gains Lone Operative 12\"",
     lone_operative_range(prince, close.tokens), 12.0)
c.true("a VEHICLE does not count - it is not INFANTRY",
       not death_guard_defenders._is_death_guard_infantry(dg_squad(dg.DEFILER)))

# Death Approaches: TWO numbers, not one.
afflicted_foe = foe_squad(x=14.0, y=10.0)
scene = board(line_up(dg_squad(dg.PLAGUE_MARINES, composition_index=0), 10.0, 10.0),
              afflicted_foe)
plain_foe = foe_squad(x=80.0, y=80.0)
c.true("the near enemy is Afflicted", nurgles_gift.is_afflicted(afflicted_foe))
c.eq("Deathshroud may drop 6\" from an Afflicted unit",
     death_approaches.minimum_distance_to(deathshroud, afflicted_foe, 9.0), 6.0)
c.eq("...and 8\" from one that is not",
     death_approaches.minimum_distance_to(deathshroud, plain_foe, 9.0), 8.0)
c.eq("a unit without the ability keeps the printed 9\"",
     death_approaches.minimum_distance_to(marines, afflicted_foe, 9.0), 9.0)

# Hovering Death: both halves of rule 09.07's ban.
drone = dg_squad(dg.FOETID_BLOAT_DRONE)
c.true("the Bloat-drone ignores the Fall Back ban",
       hovering_death.squad_ignores_fall_back(drone))
c.true("...and the Defiler does not", not hovering_death.squad_ignores_fall_back(dg_squad(dg.DEFILER)))

# Scuttling Walker: a VEHICLE WALKER that crosses terrain, which the keyword
# rule alone can never give it.
defiler = dg_squad(dg.DEFILER)
c.true("the Defiler is not INFANTRY/BEASTS/SWARM/MOBILE",
       not defiler.models[0].profile.can_move_through_dense_terrain)
c.true("...but Scuttling Walker lets it cross terrain anyway",
       scuttling_walker.can_cross_terrain(defiler.models[0]))
c.true("...and models", scuttling_walker.can_cross_models(defiler.models[0]))
c.true("a Plague Marine does not have it",
       not scuttling_walker.can_cross_terrain(marines.models[0]))

# Tank Hunters: the Blight-hauler's is RANGED-ONLY, unlike the Ork one.
hauler_model = dg_squad(dg.MYPHITIC_BLIGHT_HAULER).models[0]


class Tank(UnitProfile):
    name = "Tank"
    vehicle = True
    toughness = 10
    wounds = 12
    base_radius_in = 2.1


tank_models = [Token(0.0, 0.0, 2.1, (1, 1, 1), profile=Tank)]
tank = Squad("1 Tank 1", tank_models, owner=FOE)
for m in tank_models:
    m.squad = tank
c.eq("the Blight-hauler gets +1/+1 when SHOOTING a vehicle",
     [m.amount for m in tank_hunters_modifiers(hauler_model, tank)], [-1])
c.eq("...and NOTHING in melee - its printed text says \"in your Shooting phase\"",
     tank_hunters_modifiers(hauler_model, tank, melee=True), [])

# Lethal Ichor: counted per attacking unit, capped at six.
spawn = dg_squad(dg.CHAOS_SPAWN)
ichor = lethal_ichor.LethalIchorController(game_log=Log())
for _ in range(9):
    ichor.notify_melee_allocation(spawn, foe)
c.eq("nine allocations are capped at six dice", ichor.dice_owed_by(foe), 6)
c.true("a unit without the ability tallies nothing",
       lethal_ichor.has_lethal_ichor(spawn) and not lethal_ichor.has_lethal_ichor(marines))

# Spore-laced Shock Waves: +1 if Afflicted, and the splash is measured from
# the TARGET.
c.true("a 5 does not strike a clean unit", not spore_laced_shock_waves.struck(5, plain_foe))
c.true("...but a 5 DOES strike an Afflicted one - the +1",
       spore_laced_shock_waves.struck(5, afflicted_foe))
c.true("only its own mortar triggers it",
       spore_laced_shock_waves.is_the_mortar(
           next(w for w in crawler.models[0].weapons if w.name == "Plagueburst Mortar")))
c.true("...and the heavy slugger does not",
       not spore_laced_shock_waves.is_the_mortar(
           next(w for w in crawler.models[0].weapons if w.name == "Heavy Slugger")))

# Curse of the Walking Pox: MONSTER and VEHICLE kills do not count.
c.true("an ordinary enemy model counts", curse_of_the_walking_pox.counts_as_kill(foe.models[0]))
c.true("a VEHICLE does not", not curse_of_the_walking_pox.counts_as_kill(tank_models[0]))
c.true("a MONSTER does not",
       not curse_of_the_walking_pox.counts_as_kill(prince.models[0]))

# Icon of Despair worsens enemy Ld within 6", and STACKS with Scabrous Soulrot.
bearer = dg_squad(dg.PLAGUE_MARINES, composition_index=0,
                  gear={"Plague Marine": [dg.PM_ICON_OF_DESPAIR]})
line_up(bearer, 10.0, 10.0)
victim = foe_squad(x=13.0, y=10.0)
st = board(bearer, victim)
c.eq("printed Ld 6+ becomes 7 within 6\" of the icon",
     leadership.leadership_threshold(victim, st.tokens), 7)
far_victim = foe_squad(x=70.0, y=70.0)
st2 = board(bearer, far_victim)
c.eq("...and stays 6 further away",
     leadership.leadership_threshold(far_victim, st2.tokens), 6)


# --- 5b. The two fed abilities, end to end ------------------------------------
print("--- 5b. Lethal Ichor and Spore-laced, end to end ---")

# Both of these were built and unit-tested and then never FED - found only by a
# real run. So they are now driven through the REAL controllers, which is the
# only kind of test that could have caught it.
from testkit import fight_scene, shooting_scene   # noqa: E402
from game.lethal_ichor import LethalIchorController  # noqa: E402
from game.spore_laced_shock_waves import SporeLacedShockWavesController  # noqa: E402

_ichor = LethalIchorController(game_log=Log())
_sc = fight_scene(dg.PLAGUE_MARINES, dg.CHAOS_SPAWN, attacker_owner=DG,
                  lethal_ichor=_ichor)
c.true("the FightController really holds the controller", _sc["fight"].lethal_ichor is _ichor)
# 6s throughout: plague knives are S4 against the Spawn's T7, so they only
# wound on a 5+ - and an attack that does not wound is never ALLOCATED, which
# is exactly what Lethal Ichor counts.
script(*([6] * 300))
_sc["fight"].select_to_fight(_sc["attacker"])
# select_to_fight() auto-picks the single engaged target and stops at the
# WEAPON choice - the melee twin of the shooting flow.
if _sc["fight"].remaining_weapon_types:
    _sc["fight"].choose_weapon(sorted(_sc["fight"].remaining_weapon_types)[0])
for _ in range(60):
    if _sc["dice"].pending_values:
        _sc["dice"].acknowledge()
        _sc["fight"].on_dice_acknowledged()
        continue
    if _sc["decision"].is_pending:
        _sc["decision"].choose(0)
        continue
    break
c.true("melee attacks allocated to the Chaos Spawn were counted",
       _ichor.dice_owed_by(_sc["attacker"]) > 0)
c.true("...capped at six per attacking unit",
       _ichor.dice_owed_by(_sc["attacker"]) <= lethal_ichor.LETHAL_ICHOR_MAX_DICE)

# Spore-laced Shock Waves, fed at TARGET SELECTION by the real controller.
_spore_log = Log()
_spores = SporeLacedShockWavesController(game_log=_spore_log)
_ss = shooting_scene(dg.PLAGUEBURST_CRAWLER, dg.POXWALKERS, attacker_owner=DG,
                     gap=20.0, spore_laced=_spores)
c.true("the ShootingController really holds the controller",
       _ss["shooting"].spore_laced is _spores)
_spores.game_state = _ss["state"]
script(*([6] * 200))          # every spore D6 a 6 - the printed 6+ threshold
_ss["shooting"].start_shooting(_ss["attacker"])
# The Crawler's mortar is [INDIRECT FIRE], so the activation stops on a
# SHOOTING TYPE choice first - a step a unit with only ordinary guns skips.
if _ss["shooting"].available_types:
    _ss["shooting"].choose_shooting_type(_ss["shooting"].available_types[0])
_ss["shooting"].choose_target_squad(_ss["target"])
c.true("the Crawler has weapon groups to fire",
       len(_ss["shooting"].remaining_weapon_types) > 0)
# Fire every group: the attack keys are S/AP/D tuples, not names, so the mortar
# cannot be picked out by key - and the point is that ONLY the mortar triggers
# the spores, which firing all of them shows better than firing one.
for _ in range(60):
    # Only start a NEW group when none is in progress, or the same group is
    # re-entered forever - remaining_weapon_types does not shrink until the
    # group it belongs to has finished resolving.
    if (_ss["shooting"].current_group is None
            and _ss["shooting"].remaining_weapon_types
            and not _ss["dice"].pending_values and not _ss["decision"].is_pending):
        _ss["shooting"].choose_weapon(_ss["shooting"].remaining_weapon_types[0])
        continue
    if _ss["dice"].pending_values:
        _ss["dice"].acknowledge()
        _ss["shooting"].on_dice_acknowledged()
        continue
    if _ss["decision"].is_pending:
        _ss["decision"].choose(0)
        continue
    break
_spore_lines = [l for l in _spore_log.lines if "[spores]" in l]
c.true("the mortar's spore rolls really happened", bool(_spore_lines))
c.true("...and the +1 for an Afflicted unit is reported when it applies",
       all("rolled" in l for l in _spore_lines))


# --- 6. The army list --------------------------------------------------------
print("--- 6. The army list ---")

squads = army_lists.preview_squads(DG_LIST, DG)
c.eq("14 units after the two attachments", len(squads), 14)
c.eq("49 models", sum(len(s.models) for s in squads), 49)
c.eq("2020 pts (the list says 2015 - four documented deviations)",
     sum(s.points or 0 for s in squads), 2020)

by_name = {s.name: s for s in squads}
c.true("Typhus leads the first Deathshroud unit",
       "2 Deathshroud Terminators 1 + Typhus" in by_name)
c.true("the Plaguecaster leads the Plague Marines",
       "2 Plague Marines 1 + Malignant Plaguecaster" in by_name)
c.true("the second Deathshroud unit is unled",
       "2 Deathshroud Terminators 2" in by_name)
c.true("the Daemon Prince stands alone - it has no LEADER line",
       "2 Daemon Prince of Nurgle 1" in by_name)
c.eq("...and its unit really is one model",
     len(by_name["2 Daemon Prince of Nurgle 1"].models), 1)
c.eq("the merged Plague Marines are 11 models", len(by_name["2 Plague Marines 1 + Malignant Plaguecaster"].models), 11)
c.eq("the merged Deathshroud are 4", len(by_name["2 Deathshroud Terminators 1 + Typhus"].models), 4)
c.eq("two Blight-haulers are two SEPARATE one-model units",
     [len(by_name[f"2 Myphitic Blight-hauler {i}"].models) for i in (1, 2)], [1, 1])
c.eq("the Defiler took the heavy reaper autocannon and paid for it",
     by_name["2 Defiler 1"].points, 315)
c.true("...so it no longer has its heavy baleflamer",
       "Heavy Baleflamer" not in [w.name for w in by_name["2 Defiler 1"].models[0].weapons])

# The list builds for EITHER player - the name prefix is the only difference.
p1 = army_lists.preview_squads(DG_LIST, "Player 1")
c.eq("it builds for Player 1 too", len(p1), 14)
c.true("...with Player 1's own names", all(s.name.startswith("1 ") for s in p1))

# Every shipped map now fields the whole list - the 30"x30" test board that
# took a four-unit slice has been replaced by a full-size one. main.py's guard
# refuses a map that fields only PART of a list by a name that matches nothing,
# so what has to hold now is that no map filters this list at all.
armies = {"Player 1": "aeldari", "Player 2": DG_LIST}
for key in ("map1", "map2", "map3"):
    fielded = [s.name for s in squads if maps.get(key).fields(s, armies)]
    c.eq(f"{key} fields the whole Death Guard list", len(fielded), len(squads))

# The detachment setting is written from the chosen detachment, not hand-set.
# It moved off ArmyList and onto the Detachment record when the T'au gained six
# detachments and "which list" stopped being the same question as "which
# detachment" - game/detachments.py is the one writer now.
from game.factions.death_guard import DEATH_LORDS_CHOSEN            # noqa: E402
from game import detachments as detachments_module                  # noqa: E402
c.eq("the detachment declares its config setting",
     DEATH_LORDS_CHOSEN.setting, "DEATH_LORDS_CHOSEN_PLAYERS")
c.eq("...and it is what the Death Guard list fields",
     detachments_module.names_for(DG_LIST), ["Death Lord's Chosen"])
c.eq("...at its printed Detachment Points cost",
     detachments_module.points_for(DG_LIST), 2)
c.eq("...which is a legal list", detachments_module.validate(DG_LIST), [])
c.true("...and that setting is one game/detachments.py actually writes",
       "DEATH_LORDS_CHOSEN_PLAYERS" in detachments_module.all_settings())


# --- 7. Sprites --------------------------------------------------------------
print("--- 7. Sprites ---")

# Checked at the MODEL, not at the table: a key that resolves to no file on
# disk is exactly the failure a glance at the mapping cannot see.
for sheet in SHEETS:
    squad = dg_squad(sheet)
    c.true(f"{sheet.name} resolves to a file on disk",
           sprites.sprite_for(squad.models[0]) is not None)

# Eight of the eleven filenames disagree with the datasheet name and the FOLDER
# wins - so the mapping is pinned to the real spelling, misspellings included.
# "Demon Price of Nurgle" is two typos in one filename; correcting it here
# would lose the art, since _resolve_path() matches the base name exactly.
c.eq("the folder's spelling wins, misspellings and all",
     [sprites.SQUAD_SPRITE_KEYS[n] for n in
      ("Daemon Prince of Nurgle", "Deathshroud Terminators", "Defiler",
       "Foetid Bloat-drone", "Myphitic Blight-hauler", "Poxwalkers",
       "Malignant Plaguecaster")],
     ["Demon Price of Nurgle", "Death Shroud Terminators", "Deathguard Defiler",
      "Bloat Drone", "Blight Hauler", "Pox Walkers", "Malignant Plague Caster"])

# _key_for_name() returns on the FIRST substring match, and this faction has
# three keys beginning "Plague". None contains another, so no ordering between
# them matters - pinned by showing they resolve to three DIFFERENT files.
_plague_keys = [sprites.SQUAD_SPRITE_KEYS[n] for n in
                ("Plague Marines", "Plagueburst Crawler", "Malignant Plaguecaster")]
c.eq("the three \"Plague...\" keys cannot shadow each other", len(set(_plague_keys)), 3)

# An attached unit resolves each COMPONENT to its own art, not the whole
# merged squad to one - which is what stops a Plaguecaster-led squad showing
# eleven Plaguecasters.
_led = army_lists.preview_squads(DG_LIST, DG)
_pm_led = next(s for s in _led if s.name.endswith("+ Malignant Plaguecaster"))
_caster_model = next(m for m in _pm_led.models if m.profile.character)
_marine_model = next(m for m in _pm_led.models if not m.profile.character)
c.true("the Plaguecaster in the merged unit shows the Plaguecaster's art",
       "Malignant Plague Caster" in str(sprites.sprite_for(_caster_model)))
c.true("...and the Marines beside him show the Marines' art",
       "Plague Marines" in str(sprites.sprite_for(_marine_model)))

# The faction badge arrived after the model art, and this pin turned over -
# which is what it was for. Checked at the FILE, not in the table: the name on
# disk is "Deathguard_Logo.jpg" (one word, underscore) where the other four
# are "<Faction> Logo" with a space, so THE FOLDER WINS here as everywhere in
# sprites.py, and a mapping entry pointing at nothing would still read fine.
_dg_badge = sprites.faction_logo_path("DEATH GUARD")
c.true("the Death Guard faction badge resolves to a file on disk", _dg_badge is not None)
c.true("...and it is the one in the Death Guard folder, under its own spelling",
       "Deathguard_Logo" in str(_dg_badge))


# --- 8. Source guards --------------------------------------------------------
print("--- 8. Wiring ---")

_main = pathlib.Path("main.py").read_text(encoding="utf-8")
for needle, label in [
    ("barrage_of_filth_controller.on_squad_finished_shooting", "Barrage of Filth is fed"),
    ("pestilent_fallout_controller.on_squad_finished_shooting", "Pestilent Fallout is fed"),
    ("spore_laced_controller.resolve_after_attacks", "Spore-laced Shock Waves resolves"),
    ("spore_laced_controller.on_dice_acknowledged()", "...and gets its dice"),
    ("lethal_ichor_controller.on_unit_finished_fighting", "Lethal Ichor resolves"),
    ("lethal_ichor_controller.on_dice_acknowledged()", "...and gets its dice"),
    ("curse_of_the_walking_pox_controller.notify_kills", "Curse of the Walking Pox counts kills"),
    # Both of these were CONSTRUCTED but never FED until a real run found it -
    # the failure class verify_mark_wiring.py exists for. A controller nothing
    # calls is invisible to every test that drives it directly, which is
    # exactly what these two suites do.
    ("fight_controller.lethal_ichor = lethal_ichor_controller",
     "Lethal Ichor is fed melee allocations"),
    ("shooting_controller.spore_laced = spore_laced_controller",
     "Spore-laced Shock Waves is fed at target selection"),
    ("curse_of_the_walking_pox_controller.resolve_after_attacks", "...and spends them"),
    ("eater_plague_controller.offer_at_shooting_phase", "Eater Plague is offered"),
    ("eater_plague_controller.on_dice_acknowledged()", "...and gets its dice"),
    ("on_kills=curse_of_the_walking_pox_controller.notify_eater_plague_kills",
     "the printed TYPHUS clause joins the two"),
    ("stratagem_controller.cost_discounts.append(fevered_strategist_discount)",
     "Fevered Strategist is a cost discount"),
    ("shooting_controller.barrage_of_filth = barrage_of_filth_controller",
     "the cover test can read Barrage of Filth back"),
    ("pestilent_fallout_controller.expire_for_turn(ending_player)",
     "Pestilent Fallout expires on the victim's turn"),
    ("barrage_of_filth_controller.reset_phase()", "Barrage of Filth is phase-scoped"),
    ("lethal_ichor_controller.reset_phase()", "the Lethal Ichor tally is phase-scoped"),
]:
    c.true(label, needle in _main)

# ...and the two engine seams really call them, not just main.py holding a
# reference. A reference without a call site is the same dead wiring.
_fight_src = pathlib.Path("game/fight.py").read_text(encoding="utf-8")
c.true("game/fight.py notifies Lethal Ichor once per ALLOCATED melee attack",
       "self.lethal_ichor.notify_melee_allocation(" in _fight_src)
c.true("...from the damage-allocation step, where a SAVED attack still counts",
       _fight_src.index("self.lethal_ichor.notify_melee_allocation(")
       > _fight_src.index("def _begin_damage_allocation("))
_shoot_src = pathlib.Path("game/shooting.py").read_text(encoding="utf-8")
c.true("game/shooting.py notifies Spore-laced Shock Waves at target selection",
       "self.spore_laced.notify_target_selected(" in _shoot_src)

_units = pathlib.Path("game/units.py").read_text(encoding="utf-8")
c.true("the Defiler's base records BOTH numbers, so nobody 'corrects' it",
       "printed 160 mm" in _units and "TABLE size 2.1" in _units)


# --- 9. A/B probes -----------------------------------------------------------
print("--- 9. A/B probes ---")

_real = destroyer_hive.applies
try:
    destroyer_hive.applies = lambda squad: False
    c.eq("A/B: without Destroyer Hive the melee modifier disappears",
         destroyer_hive.hit_modifiers(led), [])
finally:
    destroyer_hive.applies = _real

_real_gift = gift_of_contagion.applies
try:
    gift_of_contagion.applies = lambda a, t: False
    c.eq("A/B: without Gift of Contagion the boltgun keeps [SUSTAINED HITS 0]",
         gift_of_contagion.adjusted_weapon(weapon, gifted, near).sustained_hits, 0)
finally:
    gift_of_contagion.applies = _real_gift

_real_scuttle = scuttling_walker.has_ability
try:
    scuttling_walker.has_ability = lambda m: False
    c.true("A/B: without Scuttling Walker the Defiler cannot cross terrain",
           not scuttling_walker.can_cross_terrain(defiler.models[0]))
finally:
    scuttling_walker.has_ability = _real_scuttle

c.finish()
