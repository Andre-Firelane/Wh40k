"""The 2026-09 Ork codex's mob abilities (stage E3a, part 2b).

Run: python test_ork_mobs.py

Ammo Runts, Tide of Muscle and Never Too Busy to Fight (Boyz), Mobbed (Beast
Snagga Boyz), Rokkit Charge (Stormboyz), Krumpin' Time and Arrogant
Invulnerability (Meganobz), Downtrodden and Thievin' Scavengers (Gretchin) -
each through the real controller or seam that reads it, plus the retirements
(Monster Hunters, the old Thievin' Scavengers CP roll), the AI's Rokkit Charge
verdict, and main.py's wiring at the source.
"""

import ast
import io
import os
import types

import testkit as tk
from testkit import (Checks, GameState, RecordingDice, build, fight_scene, line_up,
                     options_of, pick_option, script, shooting_scene)

from ai.agent_driver import rokkit_charge_verdict
from game import (actions, activation_state, ap_worsening, dice as dice_mod, formations,
                  krumpin_time, maps, mobbed, never_too_busy_to_fight, ork_ammo_runts,
                  rokkit_charge, thievin_scavengers, tide_of_muscle)
from game.attached_units import attach
from game.battle_shock import BattleShockController
from game.damage_resolution import save_thresholds
from game.dice_notation import DiceNotation
from game.factions.orks import (BATTLEWAGON, BEAST_SNAGGA_BOYZ, BOYZ, GRETCHIN, MEGANOBZ,
                                STORMBOYZ, TRUKK, WARBOSS_MEGA_ARMOUR)
from game.factions.tau_empire import STRIKE_TEAM
from game.mission_context import objective_centre
from game.objectives import is_within_range_of_objective
from game.transport import TransportController, _model_capacity_cost, squad_capacity_cost
from game.units import UnitProfile
from game.weapons import MELEE, RANGED

c = Checks("Ork mob abilities (2026-09 codex)")
HERE = os.path.dirname(os.path.abspath(__file__))


def mods(modifiers, label):
    """[(amount, label)] of the modifiers carrying `label`."""
    out = []
    for m in modifiers:
        text = next((getattr(m, a) for a in ("label", "reason", "source", "name")
                     if isinstance(getattr(m, a, None), str)), None)
        if text == label:
            out.append((m.amount, text))
    return out


def weapon_named(model, name):
    return next(w for w in model.weapons if w.name == name)


# ===========================================================================
print("\n1. Ammo Runts (Boyz)")
# ===========================================================================
_boyz = build(BOYZ, name="Boyz 1")
c.true("every Boyz model carries Ammo Runts", all(m.profile.ammo_runts for m in _boyz.models))
c.true("...a unit ability", ork_ammo_runts.has_ability(_boyz))
c.true("Gretchin do not have it", not ork_ammo_runts.has_ability(build(GRETCHIN, name="G")))


def ammo_scene(auto=False):
    scene = shooting_scene(BOYZ, STRIKE_TEAM, gap=10.0)
    ctrl = ork_ammo_runts.AmmoRuntsController(
        decision_manager=scene["decision"], turn_tracker=scene["turn"], game_log=scene["log"],
        auto_players=("Player 2",) if auto else ())
    scene["shooting"].ork_ammo_runts = ctrl
    scene["ctrl"] = ctrl
    return scene


_s = ammo_scene()
_sc, _a, _t = _s["shooting"], _s["attacker"], _s["target"]
_sc.start_shooting(_a)
c.eq("selected to shoot, a human is asked", options_of(_s["decision"]),
     ["Use Ammo Runts", "Save it for later"])
_boy = _a.models[1]
_group = {"pairs": [(_boy, weapon_named(_boy, "Shoota"))], "target_squad": _t}
c.eq("before the answer there is no bonus", mods(_sc._hit_modifiers(_group), "Ammo Runts"), [])
c.true("choosing it", pick_option(_s["decision"], "Use Ammo Runts"))
c.eq("the unit's ranged attacks now have +1 to hit (-1 on the threshold), through the real "
     "_hit_modifiers()", mods(_sc._hit_modifiers(_group), "Ammo Runts"), [(-1, "Ammo Runts")])
c.true("the once-per-battle spend is recorded", _a.ammo_runts_used)
ork_ammo_runts.reset_phase([_a])
c.eq("the grant ends with the phase", mods(_sc._hit_modifiers(_group), "Ammo Runts"), [])
c.true("...the spend survives it", _a.ammo_runts_used)
c.eq("a later activation is not offered it again", _s["ctrl"].why_not(_a), "already used this battle")

_s = ammo_scene()
_s["shooting"].start_shooting(_s["attacker"])
pick_option(_s["decision"], "Save it for later")
c.true("declining spends nothing",
       not _s["attacker"].ammo_runts_used and not ork_ammo_runts.is_active(_s["attacker"]))

_s = ammo_scene(auto=True)
_s["shooting"].start_shooting(_s["attacker"])
c.true("the AI uses it at its first opportunity, without a prompt",
       ork_ammo_runts.is_active(_s["attacker"]) and not _s["decision"].is_pending)

_s = ammo_scene()
_s["turn"].turn_owner = "Player 1"
c.eq("not in the opponent's Shooting phase", _s["ctrl"].why_not(_s["attacker"]),
     "not your Shooting phase")


# ===========================================================================
print("\n2. Tide of Muscle (Boyz)")
# ===========================================================================
_f = fight_scene(BOYZ, STRIKE_TEAM)
_fc, _a, _t = _f["fight"], _f["attacker"], _f["target"]
_fc.fighting_squad = _a
_boy = _a.models[1]
_choppa, _shoota = weapon_named(_boy, "Choppa"), weapon_named(_boy, "Shoota")
_a.charged_this_turn = False
c.eq("no charge this turn: the Choppa has no [LETHAL HITS]",
     _fc._adjusted_weapon([(_boy, _choppa)], _t).lethal_hits, False)
_a.charged_this_turn = True
c.eq("after a charge move: [LETHAL HITS], through the real fight chain",
     _fc._adjusted_weapon([(_boy, _choppa)], _t).lethal_hits, True)
c.eq("...on a copy - the carried weapon is untouched", _choppa.lethal_hits, False)
# Asked of the module DIRECTLY as well: inside the chain an earlier link already
# hands it a copy, so a mutation there could never reach the carried weapon and
# the line above would pass either way (the A/B probe that found this).
_granted = tide_of_muscle.adjusted_weapon(_choppa, _a)
c.true("the module itself returns a new weapon and leaves the one it was given alone",
       _granted is not _choppa and _granted.lethal_hits and not _choppa.lethal_hits)
c.true("ranged weapons gain nothing", tide_of_muscle.adjusted_weapon(_shoota, _a) is _shoota)
_bsb = build(BEAST_SNAGGA_BOYZ, name="BSB")
_bsb.charged_this_turn = True
c.true("Beast Snagga Boyz do not have it", not tide_of_muscle.applies(_bsb))


# ===========================================================================
print("\n3. Never Too Busy to Fight (Boyz)")
# ===========================================================================
_busy = line_up(build(BOYZ, name="Busy Boyz"), y=20.0)
_foe = line_up(build(STRIKE_TEAM, "Player 1", name="Foe"), y=21.2)
_grots = line_up(build(GRETCHIN, name="Busy Grots"), y=20.0)
_tokens = list(_busy.models) + list(_foe.models)
c.true("the scene is engaged", actions._is_engaged(_busy, _tokens))
c.eq("an engaged Boyz unit may still start an action", actions.start_eligibility(_busy, _tokens),
     (True, None))
c.eq("an engaged Gretchin unit may not", actions.start_eligibility(_grots, list(_grots.models) + list(_foe.models)),
     (False, "engaged"))
_busy.battle_shocked = True
c.eq("...and only the engaged clause is lifted", actions.start_eligibility(_busy, _tokens),
     (False, "battle-shocked"))
_busy.battle_shocked = False


# ===========================================================================
print("\n4. Mobbed (Beast Snagga Boyz)")
# ===========================================================================
def mob_scene(composition_index=0, foes=(BATTLEWAGON,), owner_of_foes="Player 1"):
    mob = line_up(build(BEAST_SNAGGA_BOYZ, name="Mob", composition_index=composition_index), x=20.0, y=20.0)
    enemies = []
    for i, sheet in enumerate(foes):
        unit = build(sheet, owner_of_foes, name="%s %d" % (sheet.name, i))
        model = unit.models[0]
        model.x_in = 20.0 + i * 8.0
        model.y_in = 20.0 + mob.models[0].profile.base_radius_in + model.profile.base_radius_in + 1.0
        enemies.append(unit)
    tokens = [m for squad in [mob] + enemies for m in squad.models]
    dice = RecordingDice()
    bsc = BattleShockController(dice_manager=dice, all_tokens=tokens, game_log=tk.Log())
    ctrl = mobbed.MobbedController(battle_shock_controller=bsc, all_tokens=tokens, game_log=tk.Log())
    return dict(mob=mob, foes=enemies, tokens=tokens, dice=dice, bsc=bsc, ctrl=ctrl)


def ack(scene):
    scene["dice"].acknowledge()
    scene["bsc"].on_dice_acknowledged()
    scene["ctrl"].on_dice_acknowledged()


_m = mob_scene()
c.true("every Beast Snagga Boyz model carries Mobbed", all(x.profile.mobbed for x in _m["mob"].models))
c.eq("10 models: -1", mobbed.penalty_for(_m["mob"]), 1)
c.eq("the engaged enemy VEHICLE is the target", [s.name for s in mobbed.targets_for(_m["mob"], _m["tokens"])],
     [_m["foes"][0].name])
script(1, 1)
c.true("ending a charge move opens the test", _m["ctrl"].on_charge_move_finished(_m["mob"]))
c.true("...on the vehicle", _m["bsc"].rolling_squad is _m["foes"][0])
_label = _m["dice"].rolled[-1][0] if _m["dice"].rolled else ""
c.true("...named Mobbed, at -1 (%s)" % _label, "Mobbed" in _label and "-1" in _label)
ack(_m)
c.true("a failed test battle-shocks it", _m["foes"][0].battle_shocked)
c.true("...and nothing is left queued", not _m["ctrl"].is_busy)

_m = mob_scene(composition_index=1)
c.eq("20 models (13+): -2 replaces -1", mobbed.penalty_for(_m["mob"]), 2)
_m["mob"].models[0].current_wounds = 0
for _x in _m["mob"].models[1:8]:
    _x.current_wounds = 0
c.eq("...counted in LIVING models (12 left): -1", mobbed.penalty_for(_m["mob"]), 1)

_m = mob_scene(foes=(BATTLEWAGON, TRUKK))
c.eq("two engaged vehicles are both targets", len(mobbed.targets_for(_m["mob"], _m["tokens"])), 2)
script(6, 6, 6, 6)
_m["ctrl"].on_charge_move_finished(_m["mob"])
_first = _m["bsc"].rolling_squad
c.true("one test at a time, the other queued", _first is not None and _m["ctrl"].is_busy)
ack(_m)
c.true("the acknowledgement releases the second",
       _m["bsc"].rolling_squad is not None and _m["bsc"].rolling_squad is not _first
       and not _m["ctrl"].is_busy)

_m = mob_scene()
_m["dice"].roll(count=1, sides=6, label="someone else's roll")
_m["ctrl"].on_charge_move_finished(_m["mob"])
c.true("a roll another rule has open is waited out, never overwritten",
       _m["bsc"].rolling_squad is None and _m["ctrl"].is_busy
       and _m["dice"].rolled[-1][0] == "someone else's roll")

_m = mob_scene(foes=(STRIKE_TEAM,))
c.eq("an engaged unit that is no MONSTER/VEHICLE takes no test",
     mobbed.targets_for(_m["mob"], _m["tokens"]), [])
_m = mob_scene(owner_of_foes="Player 2")
c.eq("a friendly vehicle takes no test", mobbed.targets_for(_m["mob"], _m["tokens"]), [])
_m = mob_scene()
_m["foes"][0].models[0].y_in += 10.0
c.eq("an enemy vehicle out of engagement takes no test", mobbed.targets_for(_m["mob"], _m["tokens"]), [])
c.eq("a charging unit without Mobbed does nothing",
     mobbed.MobbedController(all_tokens=[]).on_charge_move_finished(build(BOYZ, name="B")), False)


# ===========================================================================
print("\n5. Rokkit Charge (Stormboyz)")
# ===========================================================================
def rokkit_scene(auto=(), verdict=None, charged=True):
    scene = fight_scene(STORMBOYZ, STRIKE_TEAM)
    ctrl = rokkit_charge.RokkitChargeController(
        decision_manager=scene["decision"], game_log=scene["log"], auto_players=auto, verdict=verdict)
    scene["fight"].rokkit_charge = ctrl
    scene["attacker"].charged_this_turn = charged
    scene["ctrl"] = ctrl
    return scene


_r = rokkit_scene()
_fc, _a, _t = _r["fight"], _r["attacker"], _r["target"]
c.true("every Stormboyz model carries Rokkit Charge", all(x.profile.rokkit_charge for x in _a.models))
_fc._start_fighting(_a)
c.eq("selected to fight after a charge, a human is asked", options_of(_r["decision"])[:2],
     ["Use Rokkit Charge", "Decline"])
c.true("choosing it", pick_option(_r["decision"], "Use Rokkit Charge"))
_nob = _a.models[0]
_klaw = next(w for w in _nob.weapons if w.weapon_type == MELEE)
_boosted = _fc._adjusted_weapon([(_nob, _klaw)], _t)
c.eq("+1 A and +1 S, and [HAZARDOUS], through the real fight chain",
     (_boosted.attacks, _boosted.strength, _boosted.hazardous),
     (_klaw.attacks + 1, _klaw.strength + 1, True))
c.eq("...on a copy", (_klaw.attacks, _klaw.hazardous), (type(_klaw).attacks, False))
_slugga = next(w for w in _nob.weapons if w.weapon_type == RANGED)
c.true("ranged weapons are untouched", rokkit_charge.adjusted_weapon(_slugga, _a) is _slugga)
_d6 = rokkit_charge.adjusted_weapon(
    types.SimpleNamespace(weapon_type=MELEE, attacks=3, attacks_notation=DiceNotation(6, 0, 1),
                          strength=5, strength_notation=None, hazardous=False), _a)
c.eq("a dice-notation Attacks takes the +1 on its flat bonus", _d6.attacks_notation, DiceNotation(6, 1, 1))
rokkit_charge.reset_phase([_a])
c.true("the grant ends with the phase", not rokkit_charge.is_active(_a))

_r = rokkit_scene()
_r["fight"]._start_fighting(_r["attacker"])
pick_option(_r["decision"], "Decline")
c.true("declining grants nothing", not rokkit_charge.is_active(_r["attacker"]))
_r = rokkit_scene(charged=False)
_r["fight"]._start_fighting(_r["attacker"])
c.true("no charge this turn: not offered", not _r["decision"].is_pending
       and not rokkit_charge.is_active(_r["attacker"]))
_r = rokkit_scene(auto=("Player 2",), verdict=lambda squad: False)
_r["fight"]._start_fighting(_r["attacker"])
c.true("the AI follows a no from its verdict", not rokkit_charge.is_active(_r["attacker"])
       and not _r["decision"].is_pending)
_r = rokkit_scene(auto=("Player 2",), verdict=lambda squad: True)
_r["fight"]._start_fighting(_r["attacker"])
c.true("...and a yes, without a prompt", rokkit_charge.is_active(_r["attacker"])
       and not _r["decision"].is_pending)


# ===========================================================================
print("\n6. Rokkit Charge: the AI's verdict")
# ===========================================================================
_r = rokkit_scene()
_a, _t = _r["attacker"], _r["target"]
_ids_before = [[id(w) for w in x.weapons] for x in _a.models]
_stub = types.SimpleNamespace(engaged_enemy_squads=lambda squad: [_t])
_verdict = rokkit_charge_verdict(_a, _stub)
c.eq("its A/B puts every weapon back", [[id(w) for w in x.weapons] for x in _a.models], _ids_before)
c.true("...and leaves the grant off", not rokkit_charge.is_active(_a))
c.eq("5 Stormboyz against a Strike Team: the extra damage (22.4 pts) outweighs the hazard losses (16.7)",
     _verdict, True)
_grots = build(GRETCHIN, "Player 1", name="Grot target")
c.eq("...against 10 Gretchin it does not (12.5 pts gained, 16.7 lost)",
     rokkit_charge_verdict(_a, types.SimpleNamespace(engaged_enemy_squads=lambda s: [_grots])), False)
c.eq("nothing engaged: no", rokkit_charge_verdict(_a, types.SimpleNamespace(engaged_enemy_squads=lambda s: [])),
     False)
c.eq("no fight controller: no", rokkit_charge_verdict(_a, None), False)


# ===========================================================================
print("\n7. Krumpin' Time (Meganobz)")
# ===========================================================================
_f = fight_scene(MEGANOBZ, STRIKE_TEAM)
_fc, _a, _t = _f["fight"], _f["attacker"], _f["target"]
_fc.fighting_squad = _a
_a.riled_up = False
c.eq("not riled up: no bonus", mods(_fc._hit_modifiers(_a.models[0], _t), "Krumpin' Time"), [])
_a.riled_up = True
c.eq("riled up in the Fight phase: +1 to hit, through the real _hit_modifiers()",
     mods(_fc._hit_modifiers(_a.models[0], _t), "Krumpin' Time"), [(-1, "Krumpin' Time")])
_s = shooting_scene(MEGANOBZ, STRIKE_TEAM, gap=10.0)
_s["attacker"].riled_up = True
_s["shooting"].start_shooting(_s["attacker"])
_meg = _s["attacker"].models[0]
_shoot_group = {"pairs": [(_meg, next(w for w in _meg.weapons if w.weapon_type == RANGED))],
                "target_squad": _s["target"]}
c.eq("...and nothing in the Shooting phase", mods(_s["shooting"]._hit_modifiers(_shoot_group), "Krumpin' Time"), [])
c.true("Boyz do not have it", not krumpin_time.applies(build(BOYZ, name="B2")))


# ===========================================================================
print("\n8. Arrogant Invulnerability (Meganobz)")
# ===========================================================================
_megs = build(MEGANOBZ, name="Megs")
_meg = _megs.models[0]
_klaw = weapon_named(_meg, "Power Klaw")
_boy = build(BOYZ, name="B3").models[1]
c.eq("the Power Klaw prints AP-2", _klaw.ap, -2)
c.eq("AP-2 against Meganobz resolves as AP-1, through save_thresholds()", save_thresholds(_meg, _klaw)[2], -1)
c.eq("AP-1 becomes AP0", save_thresholds(_meg, weapon_named(_boy, "Choppa"))[2], 0)
c.eq("AP0 stays AP0 - never a bonus to the save", save_thresholds(_meg, weapon_named(_boy, "Shoota"))[2], 0)
c.eq("a Boy takes the printed AP-2", save_thresholds(_boy, _klaw)[2], -2)
_led = attach(build(WARBOSS_MEGA_ARMOUR, name="Boss"), build(MEGANOBZ, name="Megs 2"))
_boss = next(x for x in _led.models if x.profile.character)
c.eq("a Warboss in Mega Armour leading them is covered (rule 19.04)", save_thresholds(_boss, _klaw)[2], -1)
c.eq("ap_worsening: -2 -> -1, 0 -> 0, -3 by 2 -> -1",
     (ap_worsening.worsen(-2), ap_worsening.worsen(0), ap_worsening.worsen(-3, 2)), (-1, 0, -1))
# The Battlewagon's Ramshackle but Rugged was this extraction's other Ork
# reader; the 2026-09 codex took it off the datasheet (stage E3d, Mobile
# Fortress instead), so the wagon now takes the printed AP like any model.
_wagon = build(BATTLEWAGON, name="Wagon").models[0]
c.eq("the Battlewagon no longer worsens AP (Ramshackle retired in E3d)", save_thresholds(_wagon, _klaw)[2], -2)


# ===========================================================================
print("\n9. Downtrodden (Gretchin)")
# ===========================================================================
_g10 = build(GRETCHIN, name="G10")
_g20 = build(GRETCHIN, name="G20", composition_index=1)
_g11 = build(GRETCHIN, name="G11", composition_index=1)
_g11.models = _g11.models[:11]
c.true("every Gretchin model is Downtrodden", all(x.profile.downtrodden for x in _g20.models))
c.eq("10 Gretchin take 5 slots", squad_capacity_cost(_g10), 5)
c.eq("20 take 10", squad_capacity_cost(_g20), 10)
c.eq("11 take 6 - rounding up", squad_capacity_cost(_g11), 6)
c.eq("10 Boyz still take 10", squad_capacity_cost(build(BOYZ, name="B4")), 10)
_mega2 = build(MEGANOBZ, name="M4")
c.eq("MEGA ARMOUR still takes 2 each", squad_capacity_cost(_mega2), 2 * len(_mega2.models))
_trukk = build(TRUKK, name="Trukk").models[0]
c.eq("20 Gretchin fit a 12-model Trukk (18.01 at Declare Battle Formations)",
     formations.embark_errors(_g20, _trukk), [])
c.true("...which counting per model would refuse",
       sum(_model_capacity_cost(x) for x in _g20.models) > _trukk.profile.transport_capacity)
c.true("10 Boyz + 10 Gretchin (15) do not fit",
       bool(formations.embark_errors(_g10, _trukk, already_assigned=[build(BOYZ, name="B5")])))
c.eq("an embarked Gretchin unit counts 10 against the capacity mid-battle",
     TransportController.embarked_model_count(
         types.SimpleNamespace(embarked_squads_in=lambda token: [_g20]), _trukk), 10)


# ===========================================================================
print("\n10. Thievin' Scavengers (Gretchin)")
# ===========================================================================
_map = maps.MAPS["map2"]
maps.apply_to_config(_map)
_board = GameState()
_map.build(_board)
_central = next(o for o in _board.objectives if o.name == "Central Objective")
_cx, _cy = objective_centre(_central)


def unit_at(sheet, x, y, name, owner="Player 2"):
    squad = build(sheet, owner, name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + (i % 5) * 1.1, y + (i // 5) * 1.1
    return squad


def settle(tokens):
    for o in _board.objectives:
        o.controlled_by = None
        o.secured_by = None
    for o in _board.objectives:
        o.update_control(tokens)


_g = unit_at(GRETCHIN, _cx - 2.2, _cy - 0.55, "Grots A")
settle(list(_g.models))
c.eq("Gretchin on the Central Objective control it", _central.controlled_by, "Player 2")
_got = thievin_scavengers.secure_at_end_of_movement(_board.objectives, list(_g.models), "Player 2",
                                                    game_log=tk.Log())
c.true("...and secure it at the end of their Movement phase",
       _central in _got and _central.secured_by == "Player 2")

_g = unit_at(GRETCHIN, _cx - 2.2, _cy - 0.55, "Grots B")
_holders = unit_at(BOYZ, _cx - 2.2, _cy - 0.55, "Boyz Holders")
_g.battle_shocked = True
_tokens = list(_g.models) + list(_holders.models)
settle(_tokens)
c.eq("(the Boyz hold it)", _central.controlled_by, "Player 2")
thievin_scavengers.secure_at_end_of_movement(_board.objectives, _tokens, "Player 2")
c.true("a battle-shocked Gretchin unit is not controlling it - nothing secured", _central.secured_by is None)

_min_x, _min_y, _max_x, _max_y = _central.terrain_area.bounding_box
_g = unit_at(GRETCHIN, _max_x + 1.0, _cy, "Grots C")
_holders = unit_at(BOYZ, _cx - 2.2, _cy - 0.55, "Boyz Holders 2")
_tokens = list(_g.models) + list(_holders.models)
settle(_tokens)
c.true("(Gretchin beside the footprint: within 3\", not on it)",
       is_within_range_of_objective(_g, [_central])
       and not any(_central.terrain_area.overlaps_model(x) for x in _g.models))
thievin_scavengers.secure_at_end_of_movement(_board.objectives, _tokens, "Player 2")
c.true("...are not controlling it, though their army holds it - nothing secured", _central.secured_by is None)

_g = unit_at(GRETCHIN, _cx - 2.2, _cy - 0.55, "Grots D")
_enemy = unit_at(BOYZ, _cx - 2.2, _cy - 0.55, "Enemy Boyz", owner="Player 1")
_tokens = list(_g.models) + list(_enemy.models)
settle(_tokens)
c.eq("(the opponent's OC 20 beats the Gretchin's 10)", _central.controlled_by, "Player 1")
thievin_scavengers.secure_at_end_of_movement(_board.objectives, _tokens, "Player 2")
c.true("an objective the opponent controls is not secured", _central.secured_by is None)


# ===========================================================================
print("\n11. retired")
# ===========================================================================
c.true("game/monster_hunters.py is gone", not os.path.exists(os.path.join(HERE, "game", "monster_hunters.py")))
c.true("UnitProfile carries no monster_hunters flag", not hasattr(UnitProfile, "monster_hunters"))
c.true("the old Thievin' Scavengers roll kind is gone", not hasattr(dice_mod, "THIEVIN_SCAVENGERS_ROLL"))
c.true("...and its CP-roll controller", not hasattr(thievin_scavengers, "ThievinScavengersController"))


# ===========================================================================
print("\n12. wiring, at the source")
# ===========================================================================
def read(rel):
    return io.open(os.path.join(HERE, rel), encoding="utf-8").read()


def function_source(rel, name, cls=None):
    src = read(rel)
    tree = ast.parse(src)
    scope = tree
    if cls is not None:
        scope = next((n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == cls), None)
        if scope is None:
            return ""
    for node in ast.walk(scope):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node) or ""
    return ""


def statement_calls(src_fragment):
    """unparse of every call that is a whole statement - a call hidden behind
    `False and ...` or an unused expression does not count."""
    out = set()
    try:
        tree = ast.parse(src_fragment.strip() if not src_fragment.startswith(" ") else
                         "if True:\n" + src_fragment)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            out.add(ast.unparse(node.value.func))
    return out


_pins = [
    ("game/shooting.py", "ShootingController", "_hit_modifiers", "ork_ammo_runts.hit_modifiers(self.active_squad)"),
    ("game/shooting.py", "ShootingController", "start_shooting", "self.ork_ammo_runts.offer(squad)"),
    ("game/fight.py", "FightController", "_adjusted_weapon", "tide_of_muscle.adjusted_weapon(weapon, self.fighting_squad)"),
    ("game/fight.py", "FightController", "_adjusted_weapon", "rokkit_charge.adjusted_weapon(weapon, self.fighting_squad)"),
    ("game/fight.py", "FightController", "_hit_modifiers", "krumpin_time.hit_modifiers(self.fighting_squad)"),
    ("game/fight.py", "FightController", "_start_fighting", "self.rokkit_charge.offer(squad)"),
    ("game/actions.py", None, "start_eligibility", "never_too_busy_to_fight.applies(squad)"),
    ("game/damage_resolution.py", None, "save_thresholds", "arrogant_invulnerability.adjusted_ap(weapon.ap, model)"),
    ("game/transport.py", "TransportController", "can_embark", "squad_capacity_cost(squad)"),
    ("game/transport.py", "TransportController", "embarked_model_count", "squad_capacity_cost(s)"),
    ("game/formations.py", None, "transport_capacity_used", "squad_capacity_cost(s)"),
    ("game/formations.py", None, "embark_errors", "squad_capacity_cost(squad)"),
]
for _rel, _cls, _fn, _needle in _pins:
    _body = function_source(_rel, _fn, _cls)
    c.true("%s %s() was found" % (_rel, _fn), bool(_body))
    c.true("...and reads %s" % _needle, _needle in _body)
c.true("the fight hazard ledger reads the ADJUSTED weapon (so Rokkit Charge's [HAZARDOUS] rolls)",
       "self._adjusted_weapon(pairs, _haz_target).hazardous" in read("game/fight.py"))

for _flag in ("ammo_runts_used", "ammo_runts_active", "rokkit_charge_active"):
    c.true("%s survives a save (activation_state.SQUAD_FLAGS)" % _flag, _flag in activation_state.SQUAD_FLAGS)

MAIN = read("main.py")
MAIN_TREE = ast.parse(MAIN)
c.true("the old ThievinScavengersController is not built", "ThievinScavengersController" not in MAIN)

_sweep = [n for n in ast.walk(MAIN_TREE) if isinstance(n, ast.If)
          and ast.unparse(n.test) == "phase_before == PHASE_MOVEMENT"]
_secures = [n for block in _sweep for n in ast.walk(ast.Module(body=block.body, type_ignores=[]))
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and ast.unparse(n.value.func) == "thievin_scavengers.secure_at_end_of_movement"]
c.eq("Thievin' Scavengers is swept once, as a statement, at the end of the Movement phase", len(_secures), 1)
c.true("...for mover_before, never the flipped turn_owner",
       bool(_secures) and ast.unparse(_secures[0].value.args[2]) == "mover_before")

_appends = [n for n in ast.walk(MAIN_TREE) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "append"
            and ast.unparse(n.func.value) == "charge_controller.on_charge_move_finished"
            and n.args and ast.unparse(n.args[0]) == "mobbed_controller.on_charge_move_finished"]
c.eq("Mobbed listens to the end of every charge move", len(_appends), 1)
_bs, _mob = MAIN.find("battle_shock_controller.on_dice_acknowledged()"), MAIN.find("mobbed_controller.on_dice_acknowledged()")
c.true("Mobbed's queue is drained on each acknowledgement, after battle_shock's", 0 <= _bs < _mob)


def keyword_of(call_name, keyword):
    for node in ast.walk(MAIN_TREE):
        if isinstance(node, ast.Call) and ast.unparse(node.func) == call_name:
            for kw in node.keywords:
                if kw.arg == keyword:
                    return kw.value
    return None


_oar = keyword_of("ShootingController", "ork_ammo_runts")
c.true("ShootingController gets the Ammo Runts controller",
       _oar is not None and ast.unparse(_oar) == "ork_ammo_runts_controller")
_rc = keyword_of("FightController", "rokkit_charge")
c.true("FightController gets a RokkitChargeController",
       isinstance(_rc, ast.Call) and ast.unparse(_rc.func) == "RokkitChargeController")
_rc_kw = {kw.arg: ast.unparse(kw.value) for kw in (_rc.keywords if isinstance(_rc, ast.Call) else [])}
c.eq("...with the AI players", _rc_kw.get("auto_players"), "ai_players")
c.true("...and the injected verdict", "rokkit_charge_verdict(" in _rc_kw.get("verdict", ""))
_oar_ctor = next((n for n in ast.walk(MAIN_TREE) if isinstance(n, ast.Call)
                  and ast.unparse(n.func) == "AmmoRuntsController"), None)
c.true("the Ammo Runts controller gets the AI players",
       _oar_ctor is not None and any(kw.arg == "auto_players" and ast.unparse(kw.value) == "ai_players"
                                     for kw in _oar_ctor.keywords))
_resets = {ast.unparse(n.value.func) for n in ast.walk(MAIN_TREE)
           if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)}
for _reset in ("ork_ammo_runts.reset_phase", "rokkit_charge.reset_phase"):
    c.true("%s() runs at every phase change" % _reset, _reset in _resets)

c.finish()
