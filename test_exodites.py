"""Dragon Knights / Clanblade / Leystalker / Stonesinger (Etappe 5).

FOUR DATASHEETS ON ONE DRAKESTEED, and the batch that added the most genuinely
new mechanics of the Aeldari work:

  * the NEGATED [ANTI-X] - "ANTI-non-MONSTER/VEHICLE", which no keyword entry
    could express;
  * CONDITIONAL [DEVASTATING WOUNDS], granted against some targets and not
    others;
  * ENSNARED, the third movement status, and the first that interacts with
    another one ("cannot be pinned");
  * a hazard-roll PENALTY, which rule 06.03 had no parameter for.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * Both [ANTI-X] forms are measured through the real _wound_crit_threshold()
    against BOTH kinds of target, because the negated one is exactly the case
    where a one-sided test passes while meaning the opposite.
  * The ensnared/pinned interaction is measured on the MOVE characteristic, not
    on flags: "cannot be pinned" is only worth anything if it stops the second
    -2 from landing.
  * Cornered Prey is driven through the real FallBackController, since its
    first clause is about which MODE the controller enters at all.
"""
import testkit as tk
from testkit import Checks

from game import (agile_reach, attached_units, blade_of_the_clans,
                  conditional_devastating_wounds, cornered_prey, drakolithe,
                  drakolithe_tokens, elemental_ensnarement, monofilament_web,
                  panicked_quarry, sprites)
from game.coldstar import effective_movement_in
from game.squad import edge_distance
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.hazard import hazard_failures
from game.shooting import _wound_crit_threshold
from game.units import (
    ClanbladeProfile, DragonKnightProfile, ExoditeProfile, LeystalkerProfile,
    StonesingerProfile,
)
from game.weapons import (
    NON_MONSTER_VEHICLE, DrakesteedFangsAndTalonsProfile,
    ExoditeLaserLanceMeleeProfile, ExoditeLongRifleProfile, HuntingBladesProfile,
    LaserLanceMeleeProfile, LaserLanceRangedProfile, MoonbladesProfile,
    SolarCarbineProfile, SongOfWaningProfile, StoneStaveProfile,
    VenomcrestSpitProfile,
)

checks = Checks("Exodites")

SHEETS = [(ae.DRAGON_KNIGHTS, DragonKnightProfile), (ae.CLANBLADE, ClanbladeProfile),
          (ae.LEYSTALKER, LeystalkerProfile), (ae.STONESINGER, StonesingerProfile)]


def build(sheet, owner="Player 1", n=1, **kw):
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


# --- 1. the shared drakesteed -----------------------------------------------
print("--- 1. the shared drakesteed ---")

base = ExoditeProfile
checks.eq('M10"', base.movement_in, 10)
checks.eq("T5", base.toughness, 5)
checks.eq("Sv4+", base.armor_save, "4+")
checks.eq("W4", base.wounds, 4)
checks.eq("OC2", base.oc, 2)
checks.eq("WS3+/BS3+", (base.weapon_skill, base.ballistic_skill), ("3+", "3+"))
checks.true("MOUNTED and MOBILE", base.mounted and base.mobile)
checks.eq("75 x 42 mm oval -> equal-area circle",
          round(base.base_radius_in, 3), round((37.5 * 21) ** 0.5 / 25.4, 3))
for sheet, profile in SHEETS:
    checks.true("%s rides the shared chassis" % sheet.name,
                issubclass(profile, base))
    checks.eq("%s: statline identical bar Leadership" % sheet.name,
              (profile.movement_in, profile.toughness, profile.armor_save,
               profile.wounds, profile.oc, profile.base_radius_in),
              (base.movement_in, base.toughness, base.armor_save, base.wounds,
               base.oc, base.base_radius_in))
    checks.true("...and carries Battle Focus", profile.battle_focus)
checks.eq("only the Clanblade differs in Leadership - 6+ against 7+",
          [p.__name__ for _s, p in SHEETS if p.leadership == "6+"], ["ClanbladeProfile"])
checks.true("the Leystalker prints Lone Operative, Scouts 9\" and Stealth OUTRIGHT",
            LeystalkerProfile.lone_operative and LeystalkerProfile.scouts == 9.0
            and LeystalkerProfile.stealth)
checks.true("the Clanblade LEADS and the Stonesinger SUPPORTS",
            ClanbladeProfile.leader and StonesingerProfile.support
            and not ClanbladeProfile.support and not StonesingerProfile.leader)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

dk, cb, ly, ss = (build(ae.DRAGON_KNIGHTS), build(ae.CLANBLADE),
                  build(ae.LEYSTALKER), build(ae.STONESINGER))
checks.eq("Dragon Knight loadout", sorted(w.name for w in dk.models[0].weapons),
          ["Drakesteed Fangs and Talons", "Laser Lance", "Laser Lance", "Solar Carbine"])
checks.eq("Clanblade loadout", sorted(w.name for w in cb.models[0].weapons),
          ["Drakesteed Fangs and Talons", "Moonblades", "Solar Carbine"])
checks.eq("Leystalker loadout", sorted(w.name for w in ly.models[0].weapons),
          ["Drakesteed Fangs and Talons", "Hunting Blades", "Long Rifle"])
checks.eq("Stonesinger loadout", sorted(w.name for w in ss.models[0].weapons),
          ["Drakesteed Fangs and Talons", "Solar Carbine", "Song of Waning",
           "Stone Stave", "Venomcrest Spit"])

fangs = DrakesteedFangsAndTalonsProfile()
checks.eq("Fangs and Talons A3/S5/AP-1/D1",
          (fangs.attacks, fangs.strength, fangs.ap, fangs.damage), (3, 5, -1, 1))
checks.true("...and it is [EXTRA ATTACKS], so 04.01 never makes it compete",
            fangs.extra_attacks)
sc = SolarCarbineProfile()
checks.eq('Solar Carbine 18"/A2/S4/AP0/D1 with [RAPID FIRE 2]',
          (sc.range_in, sc.attacks, sc.strength, sc.ap, sc.damage, sc.rapid_fire),
          (18, 2, 4, 0, 1, 2))
# The Laser Lance: ranged row shared, melee row NOT.
checks.true("the Exodites' Laser Lance shares the Shining Spears' RANGED row",
            LaserLanceRangedProfile in [type(w) for w in dk.models[0].weapons])
ell, sll = ExoditeLaserLanceMeleeProfile(), LaserLanceMeleeProfile()
checks.eq("...but its MELEE row is S6 where theirs is S5",
          (ell.strength, sll.strength), (6, 5))
checks.true("...and prints no [ANTI-MONSTER/VEHICLE] where theirs does",
            ell.anti is None and sll.anti is not None)
checks.true("...both are [LANCE]", ell.lance and sll.lance)
mb = MoonbladesProfile()
checks.eq("Moonblades A5/WS2+/S4/AP-2/D2",
          (mb.attacks, mb.weapon_skill, mb.strength, mb.ap, mb.damage), (5, "2+", 4, -2, 2))
checks.true("...[LETHAL HITS] and [TWIN-LINKED]", mb.lethal_hits and mb.twin_linked)
hb = HuntingBladesProfile()
checks.eq("Hunting Blades A2/S3/AP-1/D1",
          (hb.attacks, hb.strength, hb.ap, hb.damage), (2, 3, -1, 1))
lr = ExoditeLongRifleProfile()
checks.eq('Long Rifle 36"/A2/BS2+/S6/AP-2/D3',
          (lr.range_in, lr.attacks, lr.ballistic_skill, lr.strength, lr.ap, lr.damage),
          (36, 2, "2+", 6, -2, 3))
checks.true("...and it is [PRECISION]", lr.precision)
vs = VenomcrestSpitProfile()
checks.true("the Venomcrest Spit is [TORRENT], which is what its printed \"-\" BS "
            "means - no override needed", vs.torrent)
checks.eq("...and [BLAST]", vs.blast, 1)


# --- 3. the two [ANTI-X] forms ----------------------------------------------
print("--- 3. the two ANTI forms ---")

infantry = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 1")
vehicle = tk.build(ae.FALCON, "Player 2", name="2 Falcon 1")
sow = SongOfWaningProfile()
checks.eq("Song of Waning: [ANTI-MONSTER/VEHICLE 3+] crits on 3+ against a VEHICLE",
          _wound_crit_threshold(sow, vehicle), 3)
checks.eq("...and on the ordinary 6 against INFANTRY",
          _wound_crit_threshold(sow, infantry), 6)
stave = StoneStaveProfile()
checks.eq("Stone Stave: the NEGATED form crits on 2+ against INFANTRY",
          _wound_crit_threshold(stave, infantry), 2)
checks.eq("...and on the ordinary 6 against a VEHICLE - the exact complement",
          _wound_crit_threshold(stave, vehicle), 6)
checks.eq("the Venomcrest Spit is the same form one threshold worse",
          (_wound_crit_threshold(vs, infantry), _wound_crit_threshold(vs, vehicle)), (3, 6))
checks.eq("the sentinel is a keyword like any other, so the machinery is unchanged",
          stave.anti, ((NON_MONSTER_VEHICLE, 2),))

# CONDITIONAL [DEVASTATING WOUNDS] - the half a flat flag would get backwards.
checks.true("the Long Rifle does NOT print the flat keyword",
            not lr.devastating_wounds)
checks.true("...but declares the conditional one",
            lr.devastating_wounds_vs_non_monster_vehicle)
checks.true("against INFANTRY it is granted",
            conditional_devastating_wounds.adjusted_weapon(lr, infantry).devastating_wounds)
checks.true("against a VEHICLE it is NOT - which is exactly what a flat flag "
            "would have got backwards",
            not conditional_devastating_wounds.adjusted_weapon(lr, vehicle).devastating_wounds)
checks.true("...and the untouched case returns the SAME object",
            conditional_devastating_wounds.adjusted_weapon(lr, vehicle) is lr)
checks.true("...while the granted one is a copy that never mutates the shared profile",
            conditional_devastating_wounds.adjusted_weapon(lr, infantry) is not lr
            and not ExoditeLongRifleProfile().devastating_wounds)
# ...and end to end through the real adjuster chain.
dscene = tk.shooting_scene(ae.LEYSTALKER, ae.GUARDIAN_DEFENDERS, attacker_owner="Player 2")
dsc = dscene["shooting"]
dsc.active_squad = dscene["attacker"]
adjusted = dsc._adjusted_weapon([(dscene["attacker"].models[0], ExoditeLongRifleProfile())],
                                dscene["target"])
checks.true("the real chain grants it against INFANTRY", adjusted.devastating_wounds)


# --- 4. points and pairings -------------------------------------------------
print("--- 4. points and pairings ---")

checks.eq("Dragon Knights 90 for three, 180 for six",
          (AELDARI_POINTS["Dragon Knights"].cost_for(3, 1),
           AELDARI_POINTS["Dragon Knights"].cost_for(6, 1)), (90, 180))
checks.eq("Clanblade 70", AELDARI_POINTS["Clanblade"].cost_for(1, 1), 70)
checks.eq("Leystalker 80", AELDARI_POINTS["Leystalker"].cost_for(1, 1), 80)
checks.eq("Stonesinger 60", AELDARI_POINTS["Stonesinger"].cost_for(1, 1), 60)
checks.eq("the Clanblade LEADS the Dragon Knights",
          tuple(AELDARI_POINTS["Clanblade"].leads), ("Dragon Knights",))
checks.eq("the Stonesinger SUPPORTS them - a different core ability, same unit",
          tuple(AELDARI_POINTS["Stonesinger"].supports), ("Dragon Knights",))
checks.eq("...and supports rather than leads",
          tuple(AELDARI_POINTS["Stonesinger"].leads), ())
checks.eq("the Leystalker neither leads nor supports",
          (tuple(AELDARI_POINTS["Leystalker"].leads),
           tuple(AELDARI_POINTS["Leystalker"].supports)), ((), ()))
knights = build(ae.DRAGON_KNIGHTS, n=2)
checks.eq("the Clanblade really attaches",
          attached_units.can_attach(build(ae.CLANBLADE, n=2), knights), [])
checks.eq("...and so does the Stonesinger",
          attached_units.can_attach(build(ae.STONESINGER, n=2),
                                    build(ae.DRAGON_KNIGHTS, n=3)), [])
checks.true("...but the Leystalker does not",
            bool(attached_units.can_attach(build(ae.LEYSTALKER, n=2),
                                           build(ae.DRAGON_KNIGHTS, n=4))))


# --- 5. Drakolithe ----------------------------------------------------------
print("--- 5. Drakolithe ---")

checks.eq("3 Dragon Knights get 2 tokens", drakolithe.tokens_on(build(ae.DRAGON_KNIGHTS, n=5)), 2)
checks.eq("6 get 4 - \"2 for every 3 models\"",
          drakolithe.tokens_on(build(ae.DRAGON_KNIGHTS, n=6, composition_index=1)), 4)
checks.eq("the Leystalker prints a flat 2 on its own line",
          drakolithe.tokens_on(build(ae.LEYSTALKER, n=5)), drakolithe_tokens.LEYSTALKER_TOKENS)
checks.eq("the Clanblade has none", drakolithe.tokens_on(build(ae.CLANBLADE, n=5)), 0)

bearer = build(ae.LEYSTALKER, "Player 1", n=7)
mover = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 5")
tk.line_up(bearer, x=20.0, y=20.0)
tk.line_up(mover, x=20.0, y=24.0)
tokens = list(bearer.models) + list(mover.models)
dc = drakolithe.DrakolitheController(game_log=tk.Log(), all_tokens=tokens,
                                     auto_players=("Player 1",))
checks.eq("a unit within 8\" is reacted to", [s.name for s in dc.bearers_reacting_to(mover)],
          [bearer.name])
far_mover = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 6")
tk.line_up(far_mover, x=20.0, y=60.0)
dc_far = drakolithe.DrakolitheController(
    game_log=tk.Log(), all_tokens=list(bearer.models) + list(far_mover.models),
    auto_players=("Player 1",))
checks.eq("...and one 40\" away is not", dc_far.bearers_reacting_to(far_mover), [])
tk.script(5)
checks.eq("a 3+ inflicts a mortal wound", dc.notify_move(mover), 1)
checks.eq("...and the token is spent", drakolithe.tokens_on(bearer), 1)
tk.script(1)
checks.eq("a 1 does not", dc.notify_move(mover), 0)
checks.eq("...but the token is spent anyway - \"removing one each time this "
          "ability is USED\"", drakolithe.tokens_on(bearer), 0)
tk.script(6)
checks.eq("with no tokens left, nothing happens at all", dc.notify_move(mover), 0)
# ANY move, unlike the snare's three named kinds.
spent = build(ae.LEYSTALKER, "Player 1", n=8)
tk.line_up(spent, x=20.0, y=20.0)
dc2 = drakolithe.DrakolitheController(
    game_log=tk.Log(), all_tokens=list(spent.models) + list(mover.models),
    auto_players=("Player 1",))
tk.script(6)
checks.eq("a CHARGE counts too - the printed text names no move types",
          dc2.notify_move(mover, "charge"), 1)


# --- 6. Blade of the Clans and Agile Reach ----------------------------------
print("--- 6. Blade of the Clans and Agile Reach ---")

checks.true("the Clanblade carries Blade of the Clans", blade_of_the_clans.applies(cb))
checks.true("...and a plain Dragon Knight unit does not", not blade_of_the_clans.applies(dk))
led = build(ae.DRAGON_KNIGHTS, n=9)
attached_units.attach(build(ae.CLANBLADE, n=9), led)
checks.true("...but one it has joined does, per 19.04", blade_of_the_clans.applies(led))
plain_blade = ExoditeLaserLanceMeleeProfile()
granted = blade_of_the_clans.adjusted_weapon(plain_blade, led)
checks.eq("it grants [SUSTAINED HITS 1]", granted.sustained_hits, 1)
checks.true("...as a copy", granted is not plain_blade
            and ExoditeLaserLanceMeleeProfile().sustained_hits == 0)
better = ExoditeLaserLanceMeleeProfile()
better.sustained_hits = 2
checks.eq("...and never downgrades a weapon that prints more",
          blade_of_the_clans.adjusted_weapon(better, led).sustained_hits, 2)

# Agile Reach widens 12.02 for the back rank only.
reach = build(ae.DRAGON_KNIGHTS, "Player 1", n=10)
# A SINGLE-model foe, deliberately: a full Guardian line spreads along x too and
# ends up within Engagement Range of every knight, which leaves no unengaged
# model for the ability to reach and makes the check pass vacuously.
foe = build(ae.CLANBLADE, "Player 2", n=40)
# Spacing chosen so the back model lands in the band this ability exists for -
# outside 2" Engagement Range, inside 3".
tk.line_up(reach, x=20.0, y=20.0, spacing=2.0)
tk.line_up(foe, x=20.0, y=21.5)
front, back = reach.models[0], reach.models[-1]
checks.true("the unit is engaged through its front model",
            agile_reach.unit_is_engaged_with(reach, foe))
checks.true("the front model needs no help - 12.02 already covers it",
            not agile_reach.model_can_reach(front, reach, foe))
checks.true("...and the back model, unengaged but within 3\", is reached",
            agile_reach.model_can_reach(back, reach, foe))
# It cannot bring a wholly disengaged unit into a fight - and the case has to be
# a unit whose model IS within 3" but whose UNIT is engaged with nothing.
# Parking it 20" away would fail the distance test instead and prove nothing.
away = build(ae.DRAGON_KNIGHTS, "Player 1", n=11)
lone_foe = build(ae.CLANBLADE, "Player 2", n=41)
tk.line_up(away, x=40.0, y=20.0, spacing=2.0)
tk.line_up(lone_foe, x=40.0, y=24.4)
checks.true("its front model really is within 3\" of that enemy",
            min(edge_distance(away.models[0], o) for o in lone_foe.models) <= 3.0)
checks.true("...and NOT within Engagement Range, so the unit is engaged with nothing",
            not agile_reach.unit_is_engaged_with(away, lone_foe))
checks.true("so nothing is reached - it widens a fight, it does not start one",
            not agile_reach.model_can_reach(away.models[0], away, lone_foe))


# --- 7. Cornered Prey -------------------------------------------------------
print("--- 7. Cornered Prey ---")

from game.battle_shock import BattleShockController
from game.fall_back import CHOOSING_MODE, DESPERATE_ESCAPE, ORDERED_RETREAT, FallBackController
from game.movement import MovementController


def _fall_back_scene(with_clanblade):
    victim = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 8")
    tk.line_up(victim, x=20.0, y=20.0)
    enemy = (build(ae.CLANBLADE, "Player 2", n=20) if with_clanblade
             else tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 9"))
    tk.line_up(enemy, x=20.0, y=21.0)
    board = list(victim.models) + list(enemy.models)
    mc = MovementController()
    mc.all_tokens = board
    mc.obstacles = []
    fb = FallBackController(mc, BattleShockController(dice_manager=tk.RecordingDice(),
                                                     game_log=tk.Log()),
                            game_log=tk.Log(), dice_manager=tk.RecordingDice())
    fb.all_tokens = board
    return victim, fb


victim, fb = _fall_back_scene(with_clanblade=False)
checks.true("without a Clanblade the unit gets the mode CHOICE",
            cornered_prey.forces_desperate_escape(victim, fb.all_tokens) is False)
victim2, fb2 = _fall_back_scene(with_clanblade=True)
checks.true("a Clanblade engaged with it forces Desperate Escape",
            cornered_prey.forces_desperate_escape(victim2, fb2.all_tokens))
# Through the real controller: it is about which mode it ENTERS.
fb2.declare(victim2)
checks.eq("...so declaring a Fall Back skips the mode screen entirely",
          fb2.mode, DESPERATE_ESCAPE)
fb2.decline()
victim3, fb3 = _fall_back_scene(with_clanblade=False)
fb3.declare(victim3)
checks.eq("...where without one it stops to ask", fb3.state, CHOOSING_MODE)
# ...and Ordered Retreat is refused while it applies.
victim4, fb4 = _fall_back_scene(with_clanblade=True)
fb4.acting_squad = victim4
fb4.choose_mode(ORDERED_RETREAT)
checks.true("Ordered Retreat is refused outright", fb4.mode != ORDERED_RETREAT)

# The second clause: -1 on the hazard rolls, and ONLY when battle-shocked.
checks.eq("a unit that is not battle-shocked takes no hazard penalty",
          cornered_prey.hazard_penalty_for(victim2, fb2.all_tokens), 0)
victim2.battle_shocked = True
checks.eq("...and a battle-shocked one takes -1",
          cornered_prey.hazard_penalty_for(victim2, fb2.all_tokens),
          cornered_prey.CORNERED_PREY_HAZARD_PENALTY)
checks.eq("the penalty really changes the failure count",
          (hazard_failures([1, 2, 3, 4]), hazard_failures([1, 2, 3, 4], 1)), (2, 3))


# --- 8. Panicked Quarry and Elemental Ensnarement ---------------------------
print("--- 8. Panicked Quarry and Elemental Ensnarement ---")

from game.face_of_death import FaceOfDeathController

bs_dice = tk.RecordingDice()
bs = BattleShockController(dice_manager=bs_dice, game_log=tk.Log())
pq = panicked_quarry.PanickedQuarryController(
    battle_shock_controller=bs, game_log=tk.Log())
checks.true("the Leystalker carries Panicked Quarry",
            panicked_quarry.unit_has_panicked_quarry(ly))
checks.true("an INFANTRY unit it hit takes the test",
            pq.offer_after_shooting(build(ae.LEYSTALKER, n=12), [infantry]))
# Its OWN BattleShockController, for the same reason Face of Death needs one:
# the offer above left a roll pending on the shared one, which would refuse the
# second call whatever the exclusion said.
pq_bs = BattleShockController(dice_manager=tk.RecordingDice(), game_log=tk.Log())
pq2 = panicked_quarry.PanickedQuarryController(
    battle_shock_controller=pq_bs, game_log=tk.Log())
checks.true("...but a VEHICLE does NOT - the clause that separates it from "
            "Face of Death",
            not pq2.offer_after_shooting(build(ae.LEYSTALKER, n=13), [vehicle]))
checks.true("...and no roll was started for it either",
            not pq_bs.rolling_squad)
# Its OWN BattleShockController: the offer above left a roll pending on
# the shared one, and start_forced_roll() refuses while one is open - which
# would fail this check for a reason that has nothing to do with the rule.
fod_bs = BattleShockController(dice_manager=tk.RecordingDice(), game_log=tk.Log())
fod = FaceOfDeathController(battle_shock_controller=fod_bs, game_log=tk.Log())
checks.true("...and Face of Death, which prints no such exclusion, DOES",
            fod.offer_after_shooting(build(ae.MAUGAN_RA, "Player 1", n=13), [vehicle]))
checks.eq("both share the same printed -1",
          (panicked_quarry.PANICKED_QUARRY_PENALTY,
           __import__("game.face_of_death", fromlist=["x"]).FACE_OF_DEATH_PENALTY), (1, 1))

# Elemental Ensnarement: the two bullets are not alternatives.
singer = build(ae.STONESINGER, "Player 1", n=14)
tk.line_up(singer, x=20.0, y=20.0)
prey_vehicle = tk.build(ae.FALCON, "Player 2", name="2 Falcon 2")
tk.line_up(prey_vehicle, x=20.0, y=26.0)
prey_infantry = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 10")
tk.line_up(prey_infantry, x=20.0, y=27.0)
board = list(singer.models) + list(prey_vehicle.models) + list(prey_infantry.models)
ee = elemental_ensnarement.ElementalEnsnarementController(
    game_log=tk.Log(), all_tokens=board)
checks.eq("only MONSTER/VEHICLE units are candidates",
          [s.name for s in ee.candidates(singer)], [prey_vehicle.name])
tk.script(4)
checks.true("a 4 ensnares", ee.use(singer, prey_vehicle))
checks.true("...and does not battle-shock the Stonesinger",
            not singer.battle_shocked)
checks.true("the target is ensnared", elemental_ensnarement.is_ensnared(prey_vehicle))
base_move = effective_movement_in(prey_vehicle.models[0])
prey_vehicle.ensnared_by_player = None
checks.eq("-2 Move, measured on the characteristic",
          base_move, effective_movement_in(prey_vehicle.models[0]) - 2)
# The 1: BOTH bullets fire.
singer2 = build(ae.STONESINGER, "Player 1", n=15)
tk.line_up(singer2, x=20.0, y=20.0)
prey2 = tk.build(ae.FALCON, "Player 2", name="2 Falcon 3")
tk.line_up(prey2, x=20.0, y=26.0)
ee2 = elemental_ensnarement.ElementalEnsnarementController(
    game_log=tk.Log(), all_tokens=list(singer2.models) + list(prey2.models))
tk.script(1)
checks.true("a 1 still ensnares - the roll is the PRICE, not the gate",
            ee2.use(singer2, prey2) and elemental_ensnarement.is_ensnared(prey2))
checks.true("...and battle-shocks the Stonesinger as well", singer2.battle_shocked)
checks.true("...which then stops it being used again",
            not ee2.can_use(singer2))

# "cannot be pinned" - the interaction, measured on the Move characteristic.
web = monofilament_web.MonofilamentWebController(game_log=tk.Log())
checks.true("an unensnared unit CAN be pinned", web.pin(prey_infantry, "Player 1"))
checks.true("...and an ensnared one cannot", not web.pin(prey2, "Player 1"))
checks.eq("...so the two -2s never stack: it is 2 lower, not 4",
          effective_movement_in(prey2.models[0]),
          prey2.models[0].profile.movement_in - elemental_ensnarement.ENSNARED_MOVE_PENALTY)
# ...and a unit pinned FIRST keeps the pin.
already_pinned = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 11")
web.pin(already_pinned, "Player 1")
already_pinned.ensnared_by_player = "Player 1"
checks.true("a unit ensnared AFTER being pinned keeps the pin it had - the "
            "printed text prevents BECOMING pinned",
            monofilament_web.is_pinned(already_pinned))
checks.eq("...and then really does take both penalties",
          effective_movement_in(already_pinned.models[0]),
          already_pinned.models[0].profile.movement_in - 4)


# --- 9. wiring and sprites --------------------------------------------------
print("--- 9. wiring and sprites ---")

main_src = open("main.py", encoding="utf-8").read()
for needle, label in [
    ("panicked_quarry_controller.offer_after_shooting", "Panicked Quarry is a listener"),
    ("movement_controller.drakolithe = drakolithe_controller", "Drakolithe reads the move seam"),
    ("fall_back_controller.all_tokens = state.tokens", "Cornered Prey can see the board"),
    ("elemental_ensnarement_controller.offer_at_end_of_fight(",
     "Elemental Ensnarement fires at the end of the Fight phase"),
    ("elemental_ensnarement_controller.clear_for_turn_of(", "...and expires on the turn seam"),
]:
    checks.true("main.py: %s" % label, needle in main_src)
move_src = open("game/movement.py", encoding="utf-8").read()
checks.true("confirm_move() reports to Drakolithe",
            "self.drakolithe.notify_move(self.selected_squad, self.move_mode)" in move_src)
fight_src = open("game/fight.py", encoding="utf-8").read()
checks.true("Agile Reach widens the snapshot, not the read",
            "agile_reach.model_can_reach(" in fight_src
            and fight_src.index("_snapshot_engagement") < fight_src.index("agile_reach.model_can_reach("))

ai_src = open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path for any of the seven abilities",
            not any(n in ai_src for n in
                    ("agile_reach", "drakolithe", "blade_of_the_clans", "cornered_prey",
                     "panicked_quarry", "elemental_ensnarement", "on_the_hunt")))

for sheet, _p in SHEETS:
    sq = build(sheet, n=30)
    checks.eq("%s has no art yet - pinned so adding one is visible" % sheet.name,
              sprites.sprite_for(sq.models[0]), None)

checks.finish()
