"""Pathfinder Team datasheet: stat line, weapons, the inferred grenade
launcher swap, Target Uploaded, and the three special drones (Grav-inhibitor,
Pulse Accelerator, Recon) plus the two-menu drone allowance.

Real objects throughout (build_squad() off the real datasheet, real
ShootingController/ChargeController/GreaterGoodController/DiceManager), no
mocks of the things under test. Every ability claim carries an A/B: without
one, a passing assertion could equally mean "the ability did nothing and the
baseline already looked like that".
"""

from game.charge import ChargeController, DECLARING_TARGETS
from game.decision import DecisionManager
from game.dice import DiceManager
from game.drones import DRONE_SLOTS, SPECIAL_DRONE_SLOTS
from game.factions import build_squad
from game.factions.tau_empire import (
    KROOT_CARNIVORES, PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER, PATHFINDER_CARBINE_TO_RAIL_RIFLE,
    PATHFINDER_TEAM, STRIKE_TEAM,
)
from game.grav_inhibitor_drone import charge_penalty_against, unit_has_grav_inhibitor_drone
from game.movement import MovementController
from game.pulse_accelerator import effective_range_in
from game.shooting import NORMAL_SHOOTING, ShootingController
from game.squad import squad_has_infiltrators
from game.turn import PHASE_CHARGE, PHASE_SHOOTING, TurnTracker
from game.units import PathfinderProfile, PathfinderShasUiProfile

PASS = []
FAIL = []
LEADER = "Pathfinder Shas'ui"


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))


def make_pathfinders(gear=None, choices=None, x=20.0, y=20.0, name="1 Pathfinder Team 1"):
    squad = build_squad(
        PATHFINDER_TEAM, "Player 1", gear=gear, choices=choices, name=name, x_in=x, y_in=y,
    )
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + (i % 5) * 1.2, y + (i // 5) * 1.2
    return squad


def make_enemy(x=26.0, y=20.0, name="1 Kroot Carnivores 1", owner="Player 2"):
    squad = build_squad(KROOT_CARNIVORES, owner, name=name, x_in=x, y_in=y)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + (i % 5) * 1.2, y + (i // 5) * 1.2
    return squad


# --- 1. Stat line, keywords, points --------------------------------------
print("\n1. Stat line / keywords / points")

squad = make_pathfinders()
leader, grunt = squad.models[0], squad.models[1]
p = grunt.profile
stats = (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc, p.weapon_skill, p.ballistic_skill)
check('M7" T3 Sv4+ W1 Ld7+ OC1, WS5+/BS4+', stats == (7, 3, "4+", 1, "7+", 1, "5+", "4+"), str(stats))
check("both model lines share one stat row", leader.profile.movement_in == p.movement_in and leader.profile.toughness == p.toughness)
check("10 models: 1 Shas'ui + 9 Pathfinders", len(squad.models) == 10 and leader.profile.squad_leader and not p.squad_leader)
check("INFANTRY (so Dense terrain is free, 13.06 - unlike the Battlesuits)", p.infantry)
check("GRENADES + MARKERLIGHT", p.grenades and p.markerlight)
check("For The Greater Good", p.for_the_greater_good)
check('Scouts 7"', p.scouts == 7.0)
check("keywords line matches the datasheet",
      PATHFINDER_TEAM.keywords == ("INFANTRY", "GRENADES", "MARKERLIGHT", "PATHFINDER TEAM"))
check("points: 85 for the 1st-2nd unit", PATHFINDER_TEAM.points_for(0, unit_index=1) == 85)
check("points: 100 from the 3rd unit on", PATHFINDER_TEAM.points_for(0, unit_index=3) == 100)
check("Squad.points reflects the built unit", squad.points == 85)


# --- 2. Weapons ----------------------------------------------------------
print("\n2. Weapons")

names = sorted({w.name for w in grunt.weapons})
check("every model: Close combat weapon + Pulse carbine + Pulse pistol",
      names == ["Close Combat Weapon", "Pulse Carbine", "Pulse Pistol"], str(names))
carbine = next(w for w in grunt.weapons if w.name == "Pulse Carbine")
pistol = next(w for w in grunt.weapons if w.name == "Pulse Pistol")
ccw = next(w for w in grunt.weapons if w.name == "Close Combat Weapon")
check('Pulse carbine 20"/A2/S5/AP0/D1', (carbine.range_in, carbine.attacks, carbine.strength, carbine.ap, carbine.damage) == (20, 2, 5, 0, 1))
check('Pulse pistol 12"/A1/S5/AP0/D1 [PISTOL]', (pistol.range_in, pistol.attacks, pistol.strength, pistol.ap, pistol.damage, pistol.pistol) == (12, 1, 5, 0, 1, True))
check("Close combat weapon melee A1/S3/AP0/D1", (ccw.weapon_type, ccw.attacks, ccw.strength, ccw.ap, ccw.damage) == ("melee", 1, 3, 0, 1))
check("all three defer BS/WS to the model (printed values match it)",
      carbine.ballistic_skill is None and pistol.ballistic_skill is None and ccw.ballistic_skill is None)

# THE GRENADE LAUNCHER IS AN ADDITION, NOT A SWAP. Printed: "1 model in this
# unit equipped with a pulse carbine can be equipped with 1 semi-automatic
# grenade launcher. That model's pulse carbine cannot be replaced." It used to
# be modelled as two swap options (2 on the rank and file plus 1 on the
# Shas'ui), which cost the carrier a carbine it keeps and allowed three
# launchers where the text allows one. Found while transcribing the 2026-09-05
# army list, whose Pathfinder Team prints ten weapons across nine models.
gl_squad = make_pathfinders(choices={"Pathfinder": {PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER: 1}})
gl_models = [m for m in gl_squad.models if any("Grenade Launcher" in w.name for w in m.weapons)]
check("exactly ONE model gets a grenade launcher", len(gl_models) == 1)
check("it KEEPS its pulse carbine - the printed text requires that",
      all(any(w.name == "Pulse Carbine" for w in m.weapons) for m in gl_models)
      and all(any(w.name == "Pulse Pistol" for w in m.weapons) for m in gl_models))
check("the option never reaches the Shas'ui line",
      any(w.name == "Pulse Carbine" for w in gl_squad.models[0].weapons)
      and not any("Grenade Launcher" in w.name for w in gl_squad.models[0].weapons))
over = make_pathfinders(choices={"Pathfinder": {PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER: 9}})
check("an over-eager choice is trimmed to the printed 1",
      sum(1 for m in over.models if any("Grenade Launcher" in w.name for w in m.weapons)) == 1)

gl = next(w for w in gl_models[0].weapons if "Grenade Launcher" in w.name)
fus = gl.overcharge_profile()
check('EMP mode 18"/A1/S3/AP0/D1, [ANTI-VEHICLE 4+], [DEVASTATING WOUNDS]',
      (gl.range_in, gl.attacks, gl.strength, gl.ap, gl.damage, gl.anti, gl.devastating_wounds)
      == (18, 1, 3, 0, 1, ("VEHICLE", 4), True))
check('fusion mode 18"/A1/S6/AP-1/D3',
      (fus.range_in, fus.attacks, fus.strength, fus.ap, fus.damage) == (18, 1, 6, -1, 3))
check("the two modes are ONE weapon (a firing mode), not two instances",
      sum(1 for w in gl_models[0].weapons if "Grenade Launcher" in w.name) == 1 and gl.overcharge_profile is not None)
check("points are unchanged - nothing here is priced wargear", gl_squad.points == 85)


# --- 3. Target Uploaded --------------------------------------------------
print("\n3. Target Uploaded")


class _GreaterGoodStub:
    """Only the two things target_uploaded/shooting read: who Spotted whom,
    and whether a squad is an Observer. Using the real controller would mean
    driving a whole Markerlight action just to set one dict entry."""

    def __init__(self, spotted_by=None, observers=()):
        self.spotted_by = spotted_by or {}
        self._observers = set(observers)

    def is_spotted(self, s):
        return s in self.spotted_by

    def is_observer(self, s):
        return s in self._observers

    def marked_by_markerlight(self, s):
        return self.spotted_by.get(s) is not None

    def is_guided_attack(self, attacker, target):
        # Mirrors the real rule: an Observer is never Guided itself.
        return not self.is_observer(attacker) and self.is_spotted(target)


def hit_modifiers(pf, enemy, greater_good):
    tokens = list(pf.models) + list(enemy.models)
    sc = ShootingController(all_tokens=tokens, player_name="Player 1", greater_good=greater_good)
    sc.shooting_type = NORMAL_SHOOTING
    sc.active_squad = pf
    weapon = next(w for w in pf.models[0].weapons if w.name == "Pulse Carbine")
    return sc, {"pairs": [(pf.models[0], weapon)], "target_squad": enemy}


pf = make_pathfinders()
foe = make_enemy()
weapon = next(w for w in pf.models[0].weapons if w.name == "Pulse Carbine")

# A: nothing Spotted at all.
sc_a, grp_a = hit_modifiers(pf, foe, _GreaterGoodStub())
mods_a = sc_a._hit_modifiers(grp_a)
check("A/B baseline: nothing Spotted -> no Target Uploaded modifier",
      not any(m.source == "Target Uploaded" for m in mods_a), str([m.source for m in mods_a]))
check("...and no [IGNORES COVER] either", not sc_a._cover_ignored_for_group(weapon, foe))

# B: THIS unit Spotted the target (it is the Observer) - the case Guided
# structurally cannot cover.
gg_own = _GreaterGoodStub(spotted_by={foe: pf}, observers=[pf])
sc_b, grp_b = hit_modifiers(pf, foe, gg_own)
mods_b = sc_b._hit_modifiers(grp_b)
check("marking it themselves grants +1 BS (a -1 to the threshold)",
      any(m.source == "Target Uploaded" and m.amount == -1 for m in mods_b), str([m.source for m in mods_b]))
check("...and [IGNORES COVER]", sc_b._cover_ignored_for_group(weapon, foe))
check("Guided is genuinely False here - so this is NOT just the Guided path",
      not gg_own.is_guided_attack(pf, foe))

# C: somebody ELSE marked it - normal Guided applies, Target Uploaded does not.
other = make_pathfinders(name="1 Pathfinder Team 2")
gg_other = _GreaterGoodStub(spotted_by={foe: other}, observers=[other])
sc_c, grp_c = hit_modifiers(pf, foe, gg_other)
mods_c = sc_c._hit_modifiers(grp_c)
check("a target marked by someone else uses Guided, not Target Uploaded",
      any(m.source.startswith("For the Greater Good") for m in mods_c)
      and not any(m.source == "Target Uploaded" for m in mods_c), str([m.source for m in mods_c]))
check("the two never stack into -2",
      sum(m.amount for m in mods_c if m.amount < 0) == -1)

# D: a unit WITHOUT the ability that marked its own target gets nothing.
st = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1", x_in=20.0, y_in=20.0)
for i, m in enumerate(st.models):
    m.x_in, m.y_in = 20.0 + (i % 5) * 1.2, 20.0 + (i // 5) * 1.2
gg_st = _GreaterGoodStub(spotted_by={foe: st}, observers=[st])
sc_d = ShootingController(all_tokens=list(st.models) + list(foe.models), player_name="Player 1", greater_good=gg_st)
sc_d.shooting_type = NORMAL_SHOOTING
sc_d.active_squad = st
st_weapon = next(w for w in st.models[0].weapons if w.name == "Pulse Rifle")
mods_d = sc_d._hit_modifiers({"pairs": [(st.models[0], st_weapon)], "target_squad": foe})
check("A/B: a Strike Team marking its own target gets NO such bonus",
      not any(m.source == "Target Uploaded" for m in mods_d), str([m.source for m in mods_d]))


# --- 4. Drone menus ------------------------------------------------------
print("\n4. Drone menus (2 ordinary + 1 special)")

full = make_pathfinders(gear={LEADER: ["Gun Drone", "Missile Drone", "Recon Drone"]})
check("2 ordinary + 1 special all fit", full.models[0].gear_names == ["Gun Drone", "Missile Drone", "Recon Drone"])
check("Gun Drone brings a Twin pulse carbine", any(w.name == "Twin Pulse Carbine" for w in full.models[0].weapons))
check("Missile Drone brings a Missile pod", any(w.name == "Missile Pod" for w in full.models[0].weapons))
check("both drone weapons keep their own BS5+, NOT the BS4+ Pathfinder's",
      next(w for w in full.models[0].weapons if w.name == "Missile Pod").ballistic_skill == "5+")

trimmed = make_pathfinders(gear={LEADER: [
    "Gun Drone", "Marker Drone", "Shield Drone", "Recon Drone", "Grav-inhibitor Drone",
]})
taken = trimmed.models[0].gear_names
check("a 3rd ordinary drone is trimmed away", sum(1 for g in taken if g in
      {"Gun Drone", "Marker Drone", "Shield Drone", "Guardian Drone", "Missile Drone"}) == DRONE_SLOTS, str(taken))
check("a 2nd special drone is trimmed away", sum(1 for g in taken if g in
      {"Recon Drone", "Grav-inhibitor Drone", "Pulse Accelerator Drone"}) == SPECIAL_DRONE_SLOTS, str(taken))
check("A/B: the special slot cannot be spent on an ordinary drone (and vice versa)",
      "Recon Drone" in taken and len(taken) == DRONE_SLOTS + SPECIAL_DRONE_SLOTS)

st_two = build_squad(STRIKE_TEAM, "Player 1", name="ST", gear={
    "Fire Warrior Shas'ui": ["Gun Drone", "Gun Drone", "Marker Drone"]})
check("regression: a single-menu datasheet still caps at 2 (Strike Team)",
      len(st_two.models[0].gear_names) == 2, str(st_two.models[0].gear_names))


# --- 5. Recon Drone ------------------------------------------------------
print("\n5. Recon Drone")

recon = make_pathfinders(gear={LEADER: ["Recon Drone"]})
plain = make_pathfinders()
check("A/B: without it the unit is not Infiltrators", not squad_has_infiltrators(plain))
check("with it the whole UNIT is Infiltrators (24.20's every-model gate overridden)",
      squad_has_infiltrators(recon))
check("...and only the bearer actually carries the flag",
      recon.models[0].profile.recon_drone and not recon.models[1].profile.recon_drone)
check("bearer gains a Drone burst cannon",
      any(w.name == "Drone Burst Cannon" for w in recon.models[0].weapons))
dbc = next(w for w in recon.models[0].weapons if w.name == "Drone Burst Cannon")
check('Drone burst cannon 18"/A4/BS5+/S5/AP0/D1',
      (dbc.range_in, dbc.attacks, dbc.ballistic_skill, dbc.strength, dbc.ap, dbc.damage) == (18, 4, "5+", 5, 0, 1))
recon.models[0].current_wounds = 0
check("the grant dies with its bearer", not squad_has_infiltrators(recon))


# --- 6. Pulse Accelerator Drone ------------------------------------------
print("\n6. Pulse Accelerator Drone")

pa = make_pathfinders(gear={LEADER: ["Pulse Accelerator Drone"]})
pa_carbine = next(w for w in pa.models[3].weapons if w.name == "Pulse Carbine")
plain_carbine = next(w for w in plain.models[3].weapons if w.name == "Pulse Carbine")
check("A/B: without the drone a Pulse carbine reaches 20\"",
      effective_range_in(plain.models[3], plain_carbine) == 20)
check('with it, every model in the UNIT reaches 26" (not just the bearer)',
      effective_range_in(pa.models[3], pa_carbine) == 26)
check("the bearer itself too", effective_range_in(pa.models[0], next(
      w for w in pa.models[0].weapons if w.name == "Pulse Carbine")) == 26)
check("the printed characteristic is NOT mutated", pa_carbine.range_in == 20)
check("a Pulse pistol is unaffected", effective_range_in(pa.models[3], next(
      w for w in pa.models[3].weapons if w.name == "Pulse Pistol")) == 12)
pa.models[0].current_wounds = 0
check("the bonus dies with its bearer", effective_range_in(pa.models[3], pa_carbine) == 20)

# End-to-end through the real range gate, with the target parked in the band
# the drone opens up: further than a printed 20" carbine reaches, closer than
# the boosted 26". The rightmost Pathfinder sits at x=24.8 (5 per row, 1.2"
# apart) and both bases are 0.63" radius, so an enemy at x=48 is
# 48 - 24.8 - 1.26 = 21.94" away edge to edge.
pa2 = make_pathfinders(gear={LEADER: ["Pulse Accelerator Drone"]})
plain2 = make_pathfinders()
far2 = make_enemy(x=48.0, y=20.0)


def can_reach(pf_squad, enemy):
    tokens = list(pf_squad.models) + list(enemy.models)
    sc = ShootingController(all_tokens=tokens, player_name="Player 1")
    return sc.has_valid_target(pf_squad, NORMAL_SHOOTING, tokens)


check("test geometry sits inside the band the drone opens",
      20.0 < plain2.min_distance_to(far2) < 26.0, f'gap {plain2.min_distance_to(far2):.2f}"')
check('A/B end-to-end: a target ~22" away is out of reach without the drone',
      not can_reach(plain2, far2))
check("...and IS a valid target with it", can_reach(pa2, far2))


# --- 7. Grav-inhibitor Drone ---------------------------------------------
print("\n7. Grav-inhibitor Drone (adapted to this engine's charge order)")

gi = make_pathfinders(gear={LEADER: ["Grav-inhibitor Drone"]}, x=20.0, y=20.0)
check("A/B: a plain Pathfinder Team imposes no penalty", charge_penalty_against([plain]) == 0)
check("with the drone the penalty is 2", charge_penalty_against([gi]) == 2)
check("unit_has_grav_inhibitor_drone reads it off any live bearer", unit_has_grav_inhibitor_drone(gi))
check('"not cumulative": two drone units still only subtract 2',
      charge_penalty_against([gi, make_pathfinders(gear={LEADER: ["Grav-inhibitor Drone"]}, name="PF3")]) == 2)
check("a mixed set still subtracts 2 (the modifier hits the ROLL)",
      charge_penalty_against([gi, plain]) == 2)


def charge_setup(target_squad, roll):
    """A real ChargeController with the 2D6 already acknowledged as `roll`."""
    charger = build_squad(KROOT_CARNIVORES, "Player 2", name="Chargers", x_in=20.0, y_in=28.0)
    for i, m in enumerate(charger.models):
        m.x_in, m.y_in = 20.0 + (i % 5) * 1.2, 28.0 + (i // 5) * 1.2
    tokens = list(charger.models) + list(target_squad.models)
    tt = TurnTracker()
    while tt.phase != PHASE_CHARGE:
        tt.advance_phase()
    tt.set_active("Player 2")
    mc = MovementController(all_tokens=tokens)
    cc = ChargeController(all_tokens=tokens, turn_tracker=tt, movement_controller=mc, dice_manager=DiceManager())
    cc.active_squad = charger
    cc.state = DECLARING_TARGETS
    cc.max_distance = roll
    return cc, charger


gap = None
cc_probe, chargers = charge_setup(gi, 12)
gap = round(chargers.min_distance_to(gi), 2)
check(f"test geometry: the gap is {gap}\"", gap > 0)

# A roll that clears the gap but not gap+2 must now fail to declare.
roll_just_enough = int(gap) + 1
cc_a, _ = charge_setup(gi, roll_just_enough)
cc_b, _ = charge_setup(plain, roll_just_enough)
check(f"A/B: a {roll_just_enough}\" roll CAN declare a plain unit",
      plain in cc_b.eligible_charge_target_squads())
check(f"...but the SAME roll cannot declare the drone unit (-2)",
      gi not in cc_a.eligible_charge_target_squads())
cc_c, _ = charge_setup(gi, roll_just_enough + 2)
check("a roll 2 higher declares it again - the penalty is exactly 2",
      gi in cc_c.eligible_charge_target_squads())
check("the Command Re-roll forecast uses the same gate (15.02)",
      gi not in cc_a.targets_reachable_with(roll_just_enough)
      and gi in cc_a.targets_reachable_with(roll_just_enough + 2))

cc_d, _ = charge_setup(gi, 12)
cc_d.charge_targets = [gi]
check("the MOVE distance is reduced too, not just the declaration",
      cc_d.effective_charge_distance() == 10 and cc_d.max_distance == 12)
cc_e, _ = charge_setup(plain, 12)
cc_e.charge_targets = [plain]
check("A/B: against a plain unit the move distance is the full roll",
      cc_e.effective_charge_distance() == 12)

# --- 8. Rail rifles: the full hit threshold, and the [HEAVY] boundary ----
# From a reported game: "they hit on 4+ but should have hit on 3+ - BS5+,
# +1 [HEAVY] (moved less than 3"), +1 from their own markerlight". The two
# abilities were both fine; what decided it was rule 24.16's per-MODEL
# clause. One model of the squad had drifted 3.11" while the rest stayed
# put, and "no model in that unit moved more than 3"" is a property of the
# whole unit, so 0.11" on one model costs everybody the bonus.
#
# The log could not answer that at the time - the hit-roll line printed the
# dice and the outcome but never the threshold - so the whole case had to be
# rebuilt from the [move detail] coordinates by hand. _threshold_note()
# closes that; the last checks here pin it.
print("\n8. Rail rifle hit threshold / [HEAVY] boundary")


class _MovementStub:
    """Only what rule 24.16 reads: how far the farthest model of a unit
    moved this turn (MovementController.moved_distance_this_turn)."""

    def __init__(self, distances):
        self.moved_distance_this_turn = distances
        self.stationary_squad_ids = set()


def rail_threshold(moved_in, spotted_by_self=True):
    pf_r = make_pathfinders(choices={"Pathfinder": {PATHFINDER_CARBINE_TO_RAIL_RIFLE: 3}})
    enemy = make_enemy(x=20.0, y=32.0)
    gg = _GreaterGoodStub(spotted_by={enemy: pf_r}, observers=[pf_r]) if spotted_by_self else _GreaterGoodStub()
    sc = ShootingController(
        all_tokens=list(pf_r.models) + list(enemy.models), player_name="Player 1",
        greater_good=gg, movement_controller=_MovementStub({pf_r: moved_in}),
    )
    sc.shooting_type = NORMAL_SHOOTING
    sc.active_squad = pf_r
    shooter = next(m for m in pf_r.models if any(w.name == "Rail Rifle" for w in m.weapons))
    rifle = next(w for w in shooter.weapons if w.name == "Rail Rifle")
    group = {"pairs": [(shooter, rifle)], "target_squad": enemy}
    return sc, group, sc._hit_threshold(group), sc._hit_modifiers(group)


sc_r, grp_r, _, _ = rail_threshold(0.0)
check("the rail rifle is BS5+ before modifiers", sc_r._base_hit_threshold(grp_r) == 5)
check("it is a [HEAVY] weapon", grp_r["pairs"][0][1].heavy)

_, _, thr_still, mods_still = rail_threshold(0.0)
check("stationary + own markerlight: BS5+ -1 -1 = 3+", thr_still == 3,
      str([(m.source, m.amount) for m in mods_still]))
check("...and both modifiers are named, not one applied twice",
      {m.source for m in mods_still} == {"[HEAVY] (stationary)", "Target Uploaded"})

check("moved exactly 3.00\" still counts as 'not more than 3\"' -> 3+",
      rail_threshold(3.0)[2] == 3)
check("moved 3.11\" (the reported game) loses [HEAVY] -> 4+",
      rail_threshold(3.11)[2] == 4)
# Dropping the markerlight drops BOTH halves of Target Uploaded: the +1 BS
# AND the [IGNORES COVER], so rule 13.08's +1 comes back on top (this test
# geometry has the target in cover - section 3's baseline shows the same).
thr_unmarked, mods_unmarked = rail_threshold(0.0, spotted_by_self=False)[2:]
check("A/B: unmarked, stationary -> 5+ ([HEAVY] -1, Benefit of Cover +1)",
      thr_unmarked == 5, str([(m.source, m.amount) for m in mods_unmarked]))
check("...i.e. the [IGNORES COVER] half is doing work too, not just the +1 BS",
      any(m.source == "Benefit of Cover" for m in mods_unmarked)
      and not any(m.source == "Benefit of Cover" for m in mods_still))
check("A/B: unmarked AND moved -> 6+, both abilities gone",
      rail_threshold(3.11, spotted_by_self=False)[2] == 6)

# The reported dice, read against both thresholds: this is why the report
# was about one die. [3,1,1] is 0 hits at 4+ and 1 hit at 3+.
from game.shooting import _resolve_roll as _rr  # noqa: E402  (local to this check)
check("the reported dice [3,1,1] score 0 hits at 4+ but 1 at 3+",
      sum(1 for d in (3, 1, 1) if _rr(d, 4) != "fail") == 0
      and sum(1 for d in (3, 1, 1) if _rr(d, 3) != "fail") == 1)

# The log line must now carry the contested number.
from game.shooting import _threshold_note  # noqa: E402
_, _, thr_a, mods_a2 = rail_threshold(3.11)
note = _threshold_note(thr_a, 5, mods_a2)
check("the log line states what the roll needed and why",
      "needed 4+" in note and "base 5+" in note and "Target Uploaded" in note, note)
check("an unmodified roll still states the threshold",
      _threshold_note(4, 4, []) == " (needed 4+)")
check("an auto-hitting attack ([TORRENT], no threshold) stays silent",
      _threshold_note(None, None, []) == "")


print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
