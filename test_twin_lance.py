"""The Twin Lance datasheet: stat line, the dual ranged/melee weapon
profiles, and its three abilities (Exemplars of Mont'ka, Neocapacitor
Shields, Retro-thrusters) plus the unit-level Ignores Cover rule.

Real objects throughout (build_squad() off the real datasheet, real
ShootingController/ChargeController/MovementController/FightController/
BattleShockController/DecisionManager), no mocks of the things under test.
Every ability claim carries an A/B.
"""

from game.battle_shock import BattleShockController
from game.charge import ChargeController, DECLARING_TARGETS
from game.decision import DecisionManager
from game.dice import DiceManager
from game.exemplars_of_montka import closest_eligible_target, montka_adjusted_weapon
from game.factions import build_squad
from game.factions.tau_empire import (
    CRISIS_SUNFORGE, DEVILFISH, KROOT_CARNIVORES, THE_TWIN_LANCE,
)
from game.movement import RETRO_THRUSTER_MOVE_IN, MovementController
from game.neocapacitor_shields import (
    NEOCAPACITOR_RANGE_IN, NeocapacitorShieldsController, charge_penalty_for,
)
from game.retro_thrusters import RetroThrustersController
from game.shooting import NORMAL_SHOOTING, ShootingController
from game.turn import PHASE_CHARGE, PHASE_FIGHT, TurnTracker
from game.units import RiLantarProfile, RiLocaiProfile

PASS = []
FAIL = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))


def make_lance(x=20.0, y=20.0):
    squad = build_squad(THE_TWIN_LANCE, "Player 1", name="1 The Twin Lance 1", x_in=x, y_in=y)
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * 2.4, y
    return squad


def make_kroot(x=30.0, y=20.0, owner="Player 2", name="1 Kroot Carnivores 1"):
    squad = build_squad(KROOT_CARNIVORES, owner, name=name, x_in=x, y_in=y)
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + (i % 5) * 1.2, y + (i // 5) * 1.2
    return squad


def make_devilfish(x=30.0, y=20.0, owner="Player 2"):
    squad = build_squad(DEVILFISH, owner, name="1 Devilfish 1", x_in=x, y_in=y)
    squad.models[0].x_in, squad.models[0].y_in = x, y
    return squad


# --- 1. Stat line, keywords, points --------------------------------------
print("\n1. Stat line / keywords / points")

squad = make_lance()
lantar, locai = squad.models
p = lantar.profile
stats = (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc, p.ballistic_skill)
check('M10" T6 Sv2+ W8 Ld6+ OC2, BS2+', stats == (10, 6, "2+", 8, "6+", 2, "2+"), str(stats))
check("Invulnerable Save (4+)", p.invulnerable_save == "4+")
check("2 named models", len(squad.models) == 2 and lantar.profile.name == "Ri'Lantar"
      and locai.profile.name == "Ri'Locai")
check("both share one stat row", locai.profile.toughness == p.toughness and locai.profile.wounds == p.wounds)
check("CHARACTER + VEHICLE/WALKER/FLY/BATTLESUIT, not INFANTRY",
      p.character and p.vehicle and p.walker and p.fly and p.battlesuit and not p.infantry)
check("Deep Strike", p.deep_strike)
check('Scouts 8"', p.scouts == 8.0)
check("For The Greater Good", p.for_the_greater_good)
check("unit-level Ignores Cover RULE (not a weapon keyword)", p.ignores_cover)
check("keywords line matches the datasheet",
      THE_TWIN_LANCE.keywords == ("EPIC HERO", "VEHICLE", "WALKER", "FLY", "CHARACTER", "BATTLESUIT", "THE TWIN LANCE"))
check("points: flat 220 for 2 models (EPIC HERO, no per-copy tiering)",
      THE_TWIN_LANCE.points_for(0, unit_index=1) == 220 and THE_TWIN_LANCE.points_for(0, unit_index=5) == 220)
check("Squad.points reflects the built unit", squad.points == 220)


# --- 2. Weapons ----------------------------------------------------------
print("\n2. Weapons")

lantar_names = sorted({w.name for w in lantar.weapons})
locai_names = sorted({w.name for w in locai.weapons})
check("Ri'Lantar carries the Fusion eliminator, Ri'Locai the Ion scattercannon",
      "Fusion Eliminator" in lantar_names and "Fusion Eliminator" not in locai_names
      and any(n.startswith("Ion Scattercannon") for n in locai_names)
      and not any(n.startswith("Ion Scattercannon") for n in lantar_names))
check("both share Shardstorm + XV pulse pistol + the MV15 Gun Drone's Twin pulse blaster",
      all(n in lantar_names and n in locai_names
          for n in ("Shardstorm Burst System", "XV Pulse Pistol", "Twin Pulse Blaster")))

fe_r = next(w for w in lantar.weapons if w.name == "Fusion Eliminator" and w.weapon_type == "ranged")
fe_m = next(w for w in lantar.weapons if w.name == "Fusion Eliminator" and w.weapon_type == "melee")
check('Fusion eliminator (ranged) 18"/A2/S10/AP-4/D D6, [MELTA 2]',
      (fe_r.range_in, fe_r.attacks, fe_r.strength, fe_r.ap, fe_r.melta) == (18, 2, 10, -4, 2)
      and fe_r.damage_notation.sides == 6 and fe_r.damage_notation.bonus == 0)
check("Fusion eliminator (melee) A1/WS4+/S10/AP-4/D D6+2, [EXTRA ATTACKS]",
      (fe_m.attacks, fe_m.weapon_skill, fe_m.strength, fe_m.ap, fe_m.extra_attacks) == (1, "4+", 10, -4, True)
      and fe_m.damage_notation.sides == 6 and fe_m.damage_notation.bonus == 2)
check("A/B: one weapon, two profiles - the ranged half is NOT [EXTRA ATTACKS]",
      fe_r.extra_attacks is False)

sb = next(w for w in lantar.weapons if w.name == "Shardstorm Burst System")
check('Shardstorm 18"/S5/AP0/D1, [PISTOL], and Attacks is a REAL D6 roll',
      (sb.range_in, sb.strength, sb.ap, sb.damage, sb.pistol) == (18, 5, 0, 1, True)
      and sb.attacks_notation is not None and sb.attacks_notation.sides == 6)

pp_r = next(w for w in lantar.weapons if w.name == "XV Pulse Pistol" and w.weapon_type == "ranged")
pp_m = next(w for w in lantar.weapons if w.name == "XV Pulse Pistol" and w.weapon_type == "melee")
check('XV pulse pistol (ranged) 12"/A2/S6/AP-1/D2, [RAPID FIRE 2] + [PISTOL]',
      (pp_r.range_in, pp_r.attacks, pp_r.strength, pp_r.ap, pp_r.damage, pp_r.rapid_fire, pp_r.pistol)
      == (12, 2, 6, -1, 2, 2, True))
check("XV pulse pistol (melee) A4/WS3+/S6/AP-1/D2, NOT [EXTRA ATTACKS]",
      (pp_m.attacks, pp_m.weapon_skill, pp_m.strength, pp_m.ap, pp_m.damage, pp_m.extra_attacks)
      == (4, "3+", 6, -1, 2, False))

ion = next(w for w in locai.weapons if w.name == "Ion Scattercannon - Standard")
ion_oc = ion.overcharge_profile()
ion_m = next(w for w in locai.weapons if w.name == "Ion Scattercannon")
check('Ion scattercannon standard 18"/A4/S7/AP-2/D2, [RAPID FIRE 2]',
      (ion.range_in, ion.attacks, ion.strength, ion.ap, ion.damage, ion.rapid_fire) == (18, 4, 7, -2, 2, 2))
check("overcharge S8/AP-3/D3, [HAZARDOUS]",
      (ion_oc.strength, ion_oc.ap, ion_oc.damage, ion_oc.hazardous) == (8, -3, 3, True))
check("the two modes are ONE weapon, not two ranged instances",
      len([w for w in locai.weapons if w.weapon_type == "ranged" and "Ion Scattercannon" in w.name]) == 1)
check("Ion scattercannon (melee) A3/WS4+/S7/AP-2/D2, [EXTRA ATTACKS]",
      (ion_m.attacks, ion_m.weapon_skill, ion_m.strength, ion_m.ap, ion_m.extra_attacks) == (3, "4+", 7, -2, True))

check("the drone's Twin pulse blaster keeps its own BS5+, not the BS2+ wielder's",
      next(w for w in lantar.weapons if w.name == "Twin Pulse Blaster").ballistic_skill == "5+")
check("A/B: the three melee weapons genuinely disagree on WS (4+/3+/4+)",
      {fe_m.weapon_skill, pp_m.weapon_skill, ion_m.weapon_skill} == {"4+", "3+"})

from game import loadout
lines = loadout.loadout_lines(squad)
check("a dual-profile weapon reads as ONE weapon, not '2x'",
      all("2x Fusion Eliminator" not in ln and "2x XV Pulse Pistol" not in ln for ln in lines), str(lines))


# --- 3. Ignores Cover (unit rule) + Exemplars of Mont'ka -----------------
print("\n3. Ignores Cover / Exemplars of Mont'ka")


def shooting_ctx(lance, enemies):
    tokens = list(lance.models) + [m for e in enemies for m in e.models]
    sc = ShootingController(all_tokens=tokens, dice_manager=DiceManager(), player_name="Player 1")
    sc.shooting_type = NORMAL_SHOOTING
    sc.active_squad = lance
    return sc


near = make_kroot(x=28.0, y=20.0, name="1 Kroot Carnivores 1")
far = make_kroot(x=36.0, y=20.0, name="1 Kroot Carnivores 2")
lance = make_lance()
sc = shooting_ctx(lance, [near, far])
check("test geometry: the near unit is genuinely nearer AND not engaged",
      lance.min_distance_to(near) < lance.min_distance_to(far)
      and not lance.is_engaged_with(near),
      f'{lance.min_distance_to(near):.2f}" vs {lance.min_distance_to(far):.2f}"')
check("closest_eligible_target picks the nearer of two", closest_eligible_target(lance, [near, far]) is near)
check("A/B: and the farther one when the near one is gone",
      closest_eligible_target(lance, [far]) is far)

sc._snapshot_target_state(near)
sc._snapshot_target_state(far)
check("the snapshot marks the near unit as closest", sc._closest_target_snapshot.get(near) is True)
check("A/B: and the far unit as not", sc._closest_target_snapshot.get(far) is False)

# "closest ELIGIBLE target", not "closest unit": a unit inside Engagement
# Range cannot be shot at (03.04), so it is not eligible and does not count
# as the closest - the word does real work here.
touching = make_kroot(x=25.0, y=20.0, name="1 Kroot Carnivores 9")
lance_b = make_lance()
sc_b = shooting_ctx(lance_b, [touching, far])
check("test geometry: the touching unit really is engaged and really is nearer",
      lance_b.is_engaged_with(touching) and lance_b.min_distance_to(touching) < lance_b.min_distance_to(far))
sc_b._snapshot_target_state(far)
check("an ENGAGED (thus ineligible) nearer unit does not steal 'closest'",
      sc_b._closest_target_snapshot.get(far) is True)

weapon = next(w for w in lance.models[0].weapons if w.name == "Shardstorm Burst System")
boosted = montka_adjusted_weapon(weapon, [(lance.models[0], weapon)], True)
plain = montka_adjusted_weapon(weapon, [(lance.models[0], weapon)], False)
check("A/B: the closest target grants [SUSTAINED HITS 1]", boosted.sustained_hits == 1)
check("A/B: a non-closest target grants nothing", plain.sustained_hits == 0)
check("the shared weapon instance is never mutated", weapon.sustained_hits == 0)
other = build_squad(CRISIS_SUNFORGE, "Player 1", name="1 Crisis Sunforge Battlesuits 1", x_in=20, y_in=20)
ow = next(w for w in other.models[0].weapons if w.name == "Fusion Blaster")
check("A/B: a unit without the ability gets nothing even against the closest",
      montka_adjusted_weapon(ow, [(other.models[0], ow)], True).sustained_hits == 0)

check("the unit-level Ignores Cover rule bypasses cover against ANY target",
      sc._cover_ignored_for_group(weapon, far))
check("...and against the closest one too", sc._cover_ignored_for_group(weapon, near))
sc_other = shooting_ctx(other, [near])
check("A/B: a unit without that rule does not bypass cover",
      not sc_other._cover_ignored_for_group(ow, near))


# --- 4. Neocapacitor Shields ---------------------------------------------
print("\n4. Neocapacitor Shields")


def neo_ctx(lance, enemies, active_player="Player 2"):
    tokens = list(lance.models) + [m for e in enemies for m in e.models]
    dm = DiceManager()
    decisions = DecisionManager()
    tt = TurnTracker()
    while tt.phase != PHASE_CHARGE:
        tt.advance_phase()
    tt.set_active(active_player)
    bs = BattleShockController(dice_manager=dm, turn_tracker=tt)
    ctrl = NeocapacitorShieldsController(
        battle_shock=bs, decision_manager=decisions, turn_tracker=tt, all_tokens=tokens,
    )
    return ctrl, decisions, dm


lance2 = make_lance(x=20.0, y=20.0)
kroot_close = make_kroot(x=26.0, y=20.0)
ctrl, decisions, dm = neo_ctx(lance2, [kroot_close])
check("eligible target within 12\" is offered", kroot_close in ctrl.eligible_targets(lance2))
veh = make_devilfish(x=27.0, y=20.0)
ctrl2, _, _ = neo_ctx(lance2, [kroot_close, veh])
check("A/B: MONSTER/VEHICLE units are excluded", veh not in ctrl2.eligible_targets(lance2))
kroot_far = make_kroot(x=60.0, y=20.0, name="1 Kroot Carnivores 3")
ctrl3, _, _ = neo_ctx(lance2, [kroot_far])
check('A/B: a unit beyond 12" is not eligible', kroot_far not in ctrl3.eligible_targets(lance2))

opened = ctrl.offer_at_charge_phase_start("Player 2")
check("offered at the start of the OPPONENT's Charge phase", opened and decisions.is_pending)
check("the choice belongs to the ability's owner", decisions.player == "Player 1")
ctrl_own, decisions_own, _ = neo_ctx(lance2, [kroot_close], active_player="Player 1")
check("A/B: NOT offered during the owner's own Charge phase",
      not ctrl_own.offer_at_charge_phase_start("Player 1"))

check("A/B: no penalty before it is used", charge_penalty_for(kroot_close) == 0)
labels = [o["label"] for o in decisions.options]
decisions.choose(next(i for i, l in enumerate(labels) if kroot_close.name in l))
check("choosing sets the -1 Charge penalty", charge_penalty_for(kroot_close) == 1)
check("...and forces a Battle-shock test", dm.is_pending and "Battle-Shock" in (dm.label or ""))

import game.neocapacitor_shields as neo
neo.expire_for_turn([kroot_close])
check('"until the end of the turn" - the flag clears', charge_penalty_for(kroot_close) == 0)


def charge_ctx(charger, target, roll):
    tokens = list(charger.models) + list(target.models)
    tt = TurnTracker()
    while tt.phase != PHASE_CHARGE:
        tt.advance_phase()
    tt.set_active(charger.owner)
    mc = MovementController(all_tokens=tokens)
    cc = ChargeController(all_tokens=tokens, turn_tracker=tt, movement_controller=mc, dice_manager=DiceManager())
    cc.active_squad = charger
    cc.state = DECLARING_TARGETS
    cc.max_distance = None
    return cc


charger = make_kroot(x=26.0, y=20.0)
cc = charge_ctx(charger, lance2, 0)
clean, _ = cc._capped_roll(8)
charger.neocapacitor_shielded = True
shielded, note = cc._capped_roll(8)
check("A/B: the -1 lands on the CHARGING unit's roll (8 -> 7)",
      clean == 8 and shielded == 7, f"{clean} vs {shielded}")
check("the log note names the ability", "Neocapacitor Shields" in note, note)


# --- 5. Retro-thrusters --------------------------------------------------
print("\n5. Retro-thrusters")


class _FightStub:
    def __init__(self, eligible):
        self._eligible = set(eligible)

    def is_eligible_to_fight(self, squad):
        return squad in self._eligible


def retro_ctx(lance, others, eligible):
    tokens = list(lance.models) + [m for o in others for m in o.models]
    tt = TurnTracker()
    while tt.phase != PHASE_FIGHT:
        tt.advance_phase()
    tt.set_active(lance.owner)
    mc = MovementController(all_tokens=tokens, turn_tracker=tt)
    ctrl = RetroThrustersController(
        fight_controller=_FightStub(eligible), movement_controller=mc,
        turn_tracker=tt, all_tokens=tokens,
    )
    ctrl.reset_fight_phase()
    return ctrl, mc


lance3 = make_lance(x=20.0, y=20.0)
away = make_kroot(x=60.0, y=20.0)
ctrl, mc = retro_ctx(lance3, [away], eligible=[lance3])
check("A/B: before the phase is sampled, nothing is offered", not ctrl.can_use(lance3))
ctrl.note_eligibility()
check("once eligibility is latched, the move is available", ctrl.can_use(lance3))
check("an unengaged unit is offered BOTH halves",
      ctrl.available_moves(lance3) == ["normal", "fall_back"], str(ctrl.available_moves(lance3)))

ctrl_no, _ = retro_ctx(make_lance(), [away], eligible=[])
ctrl_no.note_eligibility()
check("A/B: a unit that was never eligible to fight gets nothing", not ctrl_no.can_use(make_lance()))

engaged_enemy = make_kroot(x=22.6, y=20.0)
lance4 = make_lance(x=20.0, y=20.0)
ctrl4, mc4 = retro_ctx(lance4, [engaged_enemy], eligible=[lance4])
ctrl4.note_eligibility()
check("test geometry: this Twin Lance really is engaged", lance4.is_engaged(ctrl4.all_tokens))
check("an ENGAGED unit is offered only the Fall Back half (a Normal move could never end unengaged)",
      ctrl4.available_moves(lance4) == ["fall_back"], str(ctrl4.available_moves(lance4)))

before = (lance3.models[0].x_in, lance3.models[0].y_in)
opened = ctrl.start(lance3, fall_back=False)
check("starting the Normal move opens a move", opened and mc.move_mode == "retro_thrusters")
budget = mc.remaining_range[lance3.models[0].id]
check('the distance is a flat 6", NOT the unit\'s 10" Move',
      abs(budget - RETRO_THRUSTER_MOVE_IN) < 1e-9,
      f'{budget}" vs M{lance3.models[0].profile.movement_in}"')
# Move the model the way a drag does: clamp_move() decides how far it may
# actually go, then try_commit_segment() validates where it ended up.
mover = lance3.models[0]
# Sideways, not along the line of the pair: the two models sit 2.4" apart in
# x, so moving one onto the other's space would be rejected for overlap -
# correctly, but that would test the overlap rule rather than this move.
mover.x_in, mover.y_in = mc.clamp_move(mover, before[0], before[1] + 3.0)
mc.try_commit_segment(mover)
moved = abs(mover.y_in - before[1]) > 1.0
check("the models actually move", moved)
check("it is not booked as a Movement-phase move (09.02) or an Advance",
      lance3 not in mc.moved_squad_ids and lance3 not in mc.advanced_squad_ids)
check("once used, it is not offered again this phase", not ctrl.can_use(lance3))

ctrl5, mc5 = retro_ctx(make_lance(), [away], eligible=[])
lance5 = next(t.squad for t in ctrl5.all_tokens if t.squad.owner == "Player 1")
ctrl5._eligible_this_phase.add(id(lance5))
ctrl5.decline(lance5)
check("declining also closes it for the phase", not ctrl5.can_use(lance5))
ctrl5.reset_fight_phase()
check("a new Fight phase clears both the latch and the used set",
      not ctrl5.can_use(lance5) and not ctrl5._eligible_this_phase)

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
