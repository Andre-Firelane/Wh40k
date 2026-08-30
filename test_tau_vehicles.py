"""The three remaining T'au vehicle datasheets (Etappe 4 - the last).

  Hammerhead Gunship · Sky Ray Gunship · Piranhas

With these, all 19 engine-native T'au datasheets are built.

Real objects throughout: the real datasheets, the real ShootingController and
DiceManager, the real BattleShockController, the real ActionPanel. A/B probes
accompany every ability claim.

  1. Stat lines, bases, keywords, points, compositions, wargear
  2. Armour Hunter          (Hammerhead) - Tank Hunters with one half missing
  3. Velocity Tracker       (Sky Ray)
  4. Targeting Array        (both gunships) - a single-die re-roll, no CP
  5. Drone Harassment Tactics (Piranhas)
  6. Source guards, sprites, and the whole T'au roster
"""

import io
import os

import testkit as tk
from game import armour_hunter, drone_harassment, reroll_scope, targeting_array, velocity_tracker
from game.battle_shock import BattleShockController
from game.decision import DecisionManager
from game.dice import HIT_ROLL, SAVE_ROLL, WOUND_ROLL
from game.drone_harassment import DroneHarassmentController
from game.factions import build_squad
from game.factions.tau_empire import (
    DEVILFISH, HAMMERHEAD_CARBINES_TO_BURST, HAMMERHEAD_GUNSHIP,
    HAMMERHEAD_RAILGUN_TO_ION_CANNON, KROOT_CARNIVORES, PIRANHAS, PIRANHA_BURST_TO_FUSION,
    SKY_RAY_CARBINES_TO_SMS, SKY_RAY_GUNSHIP, STRIKE_TEAM, TAU_EMPIRE,
)
from game.game_state import GameState
from game.targeting_array import TargetingArrayController
from game.turn import TurnTracker
from game.weapons import (
    AcceleratorBurstCannonProfile, DevilfishTwinPulseCarbineProfile,
    HammerheadTwinPulseCarbineProfile, IonCannonStandardProfile, PiranhaBurstCannonProfile,
)

ck = tk.Checks("T'au vehicles")
MM = 25.4
HERE = os.path.dirname(os.path.abspath(__file__))


def unit(sheet, owner="Player 1", ci=0, choices=None, gear=None):
    return tk.build(sheet, owner, name=f"1 {sheet.name} 1", composition_index=ci,
                    choices=choices, gear=gear)


def src(path):
    return io.open(os.path.join(HERE, path), encoding="utf-8").read()


# --- 1. Stat lines, bases, keywords, points, compositions -----------------
print("\n1. Stat lines, bases, keywords, points, compositions")


def stats(sheet, ci=0):
    p = unit(sheet, ci=ci).models[0].profile
    return (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc)


ck.eq("Hammerhead stat line", stats(HAMMERHEAD_GUNSHIP), (10, 10, "3+", 14, "7+", 3))
ck.eq("the Sky Ray shares the same hull exactly",
      stats(SKY_RAY_GUNSHIP), stats(HAMMERHEAD_GUNSHIP))
ck.eq("Piranha stat line", stats(PIRANHAS), (14, 7, "4+", 7, "7+", 2))

_hh = unit(HAMMERHEAD_GUNSHIP).models[0].profile
_sr = unit(SKY_RAY_GUNSHIP).models[0].profile
_pi = unit(PIRANHAS).models[0].profile
ck.true("all three are VEHICLE + FLY",
        all(p.vehicle and p.fly for p in (_hh, _sr, _pi)))
ck.true("only the Sky Ray has MARKERLIGHT",
        _sr.markerlight and not _hh.markerlight and not _pi.markerlight)
ck.eq("both gunships are Damaged at 1-5 wounds",
      (_hh.damaged_threshold, _sr.damaged_threshold), (5, 5))
ck.true("the Piranha has no Damaged profile", _pi.damaged_threshold is None)
# The longest Scout move in the engine, and the only one on a vehicle.
ck.eq("Piranhas have Scouts 9\"", _pi.scouts, 9.0)
ck.true("...longer than every other Scouts value here",
        _pi.scouts > max(p.scouts for p in
                         (unit(KROOT_CARNIVORES).models[0].profile,)
                         if p.scouts))

# The two gunships share the established grav-tank table size, like the
# Devilfish. The PIRANHA no longer does: a user decision on 2026-08-30 ("die
# piranhas sind zu gross, die sollten in etwa nur 2/3 so gross sein wie devil
# fish") cut it to two thirds of that. All three datasheets print the SAME
# 60 mm flying base, so the split is a table size, not a transcription - see
# PiranhaProfile's own note, and test_tau_army.py, which pins the ratio.
_grav = unit(DEVILFISH).models[0].profile.base_radius_in
for name, sheet in (("Hammerhead", HAMMERHEAD_GUNSHIP), ("Sky Ray", SKY_RAY_GUNSHIP)):
    ck.eq(f"{name}: the grav-tank table base size",
          unit(sheet).models[0].profile.base_radius_in, _grav)
ck.eq("Piranha: two thirds of it, by user decision",
      round(unit(PIRANHAS).models[0].profile.base_radius_in / _grav, 3), 0.667)
ck.true("...so it is the one grav-tank here that is NOT the Devilfish's size",
        unit(PIRANHAS).models[0].profile.base_radius_in < _grav)

ck.eq("Hammerhead points, tiered by copies",
      (unit(HAMMERHEAD_GUNSHIP).points,
       build_squad(HAMMERHEAD_GUNSHIP, "Player 1", unit_index=3).points), (150, 160))
ck.eq("the Sky Ray is flat 140", unit(SKY_RAY_GUNSHIP).points, 140)
ck.eq("Piranhas 1 / 2 / 3 models",
      [(len(unit(PIRANHAS, ci=i).models), unit(PIRANHAS, ci=i).points) for i in (0, 1, 2)],
      [(1, 65), (2, 110), (3, 165)])

# THE ONE-KEYWORD DIFFERENCE. The Hammerhead's twin pulse carbine prints
# [TWIN-LINKED] alone; the Sky Ray's, the Piranha's and the Devilfish's also
# print [ASSAULT] - which is what lets a weapon fire after Advancing (24.04),
# so sharing one class would quietly let a Hammerhead Advance and shoot.
ck.eq("the Hammerhead's carbine is NOT [ASSAULT]",
      HammerheadTwinPulseCarbineProfile.assault, False)
ck.eq("the Sky Ray's (the Devilfish class) IS",
      DevilfishTwinPulseCarbineProfile.assault, True)
ck.true("...and they agree on everything else",
        (HammerheadTwinPulseCarbineProfile.range_in,
         HammerheadTwinPulseCarbineProfile.attacks,
         HammerheadTwinPulseCarbineProfile.strength,
         HammerheadTwinPulseCarbineProfile.twin_linked)
        == (DevilfishTwinPulseCarbineProfile.range_in,
            DevilfishTwinPulseCarbineProfile.attacks,
            DevilfishTwinPulseCarbineProfile.strength,
            DevilfishTwinPulseCarbineProfile.twin_linked))

# The railgun, the biggest gun in the engine.
_rail = next(w for w in unit(HAMMERHEAD_GUNSHIP).models[0].weapons if w.name == "Railgun")
ck.eq("railgun 72\" S20 AP-5, [HEAVY] [DEVASTATING WOUNDS]",
      (_rail.range_in, _rail.strength, _rail.ap, _rail.heavy, _rail.devastating_wounds),
      (72, 20, -5, True, True))
ck.true("...and its Damage is a D6+6 notation", _rail.damage_notation is not None)

# The Piranha burst cannon is a rename of the accelerator burst cannon.
ck.eq("the Piranha burst cannon inherits the accelerator's numbers",
      (PiranhaBurstCannonProfile.range_in, PiranhaBurstCannonProfile.attacks,
       PiranhaBurstCannonProfile.strength, PiranhaBurstCannonProfile.ap),
      (AcceleratorBurstCannonProfile.range_in, AcceleratorBurstCannonProfile.attacks,
       AcceleratorBurstCannonProfile.strength, AcceleratorBurstCannonProfile.ap))
ck.eq("...under its own printed name",
      PiranhaBurstCannonProfile.name, "Piranha Burst Cannon")
# The highest melta value in the engine.
_fusion = unit(PIRANHAS, choices={"Piranhas": {PIRANHA_BURST_TO_FUSION: 1}})
ck.eq("the Piranha fusion blaster is [MELTA 4]",
      next(w for w in _fusion.models[0].weapons
           if w.name == "Piranha Fusion Blaster").melta, 4)

# The ion cannon is a two-mode weapon, like every other ion weapon here.
_ion = unit(HAMMERHEAD_GUNSHIP,
            choices={"Hammerhead Gunship": {HAMMERHEAD_RAILGUN_TO_ION_CANNON: 1}})
ck.true("the railgun can be traded for an ion cannon",
        any(w.name == "Ion Cannon - Standard" for w in _ion.models[0].weapons))
ck.true("...and the railgun is gone",
        not any(w.name == "Railgun" for w in _ion.models[0].weapons))
ck.eq("the ion cannon has an overcharge mode, not a second weapon",
      IonCannonStandardProfile.overcharge_profile.name, "Ion Cannon - Overcharge")
ck.true("...whose Hazardous half is the price of it",
        IonCannonStandardProfile.overcharge_profile.hazardous
        and not IonCannonStandardProfile.hazardous)

# "One of the following" on a single-model line: the shared cursor makes the
# two carbine swaps genuinely exclusive (contrast the Farstalkers' nine-model
# line, where it only makes them non-overlapping).
_burst = unit(HAMMERHEAD_GUNSHIP,
              choices={"Hammerhead Gunship": {HAMMERHEAD_CARBINES_TO_BURST: 1}})
ck.eq("both carbines become burst cannons",
      [w.name for w in _burst.models[0].weapons].count("Accelerator Burst Cannon"), 2)
_both = unit(HAMMERHEAD_GUNSHIP,
             choices={"Hammerhead Gunship": {HAMMERHEAD_CARBINES_TO_BURST: 1,
                                             "2x Twin Pulse Carbine -> 2x Smart Missile System": 1}})
ck.eq("asking for both leaves only one - the cursor makes them exclusive",
      sum(1 for w in _both.models[0].weapons
          if w.name in ("Accelerator Burst Cannon", "Smart Missile System")), 2)

_sms = unit(SKY_RAY_GUNSHIP, choices={"Sky Ray Gunship": {SKY_RAY_CARBINES_TO_SMS: 1}})
ck.eq("the Sky Ray can trade its carbines too",
      [w.name for w in _sms.models[0].weapons].count("Smart Missile System"), 2)
ck.true("its seeker missile rack is not a wargear option - it IS the datasheet",
        any(w.name == "Seeker Missile Rack" for w in unit(SKY_RAY_GUNSHIP).models[0].weapons))

# Seeker missiles: a COUNT of a repeatable item, so Gear rather than a swap.
_seekers = unit(HAMMERHEAD_GUNSHIP,
                gear={"Hammerhead Gunship": ["Seeker Missile", "Seeker Missile"]})
ck.eq("up to 2 seeker missiles",
      [w.name for w in _seekers.models[0].weapons].count("Seeker Missile"), 2)
_three = unit(HAMMERHEAD_GUNSHIP,
              gear={"Hammerhead Gunship": ["Seeker Missile"] * 3})
ck.eq("...and no more than 2",
      [w.name for w in _three.models[0].weapons].count("Seeker Missile"), 2)
# On the Piranhas the printed text is "ANY NUMBER OF MODELS can each be
# equipped", so all_models - the second datasheet to need it after the
# Broadsides.
_pi_seekers = unit(PIRANHAS, ci=2, gear={"Piranhas": ["Seeker Missile", "Seeker Missile"]})
ck.eq("every Piranha gets its own pair, not just the first",
      [w.name for m in _pi_seekers.models for w in m.weapons].count("Seeker Missile"), 6)


# --- 2. Armour Hunter -----------------------------------------------------
# A/B: the _hit_modifiers entry removed -> 2 fail; the sign flipped -> 1.
print("\n2. Armour Hunter: Tank Hunters with the wound half missing")

_hammer = unit(HAMMERHEAD_GUNSHIP)
_vehicle_target = unit(DEVILFISH, owner="Player 2")
_infantry_target = unit(STRIKE_TEAM, owner="Player 2")

ck.eq("against a VEHICLE it adds 1 to the Hit roll",
      [(m.amount, m.source) for m in
       armour_hunter.modifiers(_hammer.models[0], _vehicle_target)],
      [(-1, armour_hunter.ARMOUR_HUNTER_LABEL)])
ck.eq("against INFANTRY it does nothing",
      armour_hunter.modifiers(_hammer.models[0], _infantry_target), [])
ck.eq("a model without the ability gets nothing",
      armour_hunter.modifiers(unit(PIRANHAS).models[0], _vehicle_target), [])
# The sign is the trap: a positive modifier WORSENS a threshold here.
ck.eq("the modifier is negative (a bonus)", armour_hunter.ARMOUR_HUNTER_HIT_MODIFIER, -1)

# End to end through the real controller.
_ah_scene = tk.shooting_scene(HAMMERHEAD_GUNSHIP, DEVILFISH, attacker_owner="Player 2")
_ah_scene["shooting"].active_squad = _ah_scene["attacker"]
_group = {"pairs": [(_ah_scene["attacker"].models[0],
                     next(w for w in _ah_scene["attacker"].models[0].weapons
                          if w.name == "Railgun"))],
          "target_squad": _ah_scene["target"]}
ck.true("ShootingController._hit_modifiers() picks it up",
        any(m.source == armour_hunter.ARMOUR_HUNTER_LABEL
            for m in _ah_scene["shooting"]._hit_modifiers(_group)))

# It is the HIT half only - the Hammerhead does not print Tank Hunters' +1 to
# wound, and giving it one would be the obvious silent error.
ck.true("it grants no wound bonus",
        not any(m.source == armour_hunter.ARMOUR_HUNTER_LABEL
                for m in _ah_scene["shooting"]._wound_modifiers(_ah_scene["target"])))
ck.true("and the Hammerhead does not carry the Tank Hunters flag",
        not getattr(_hammer.models[0].profile, "tank_hunters", False))
# The Sky Ray SUBCLASSES the Hammerhead, so what it turns OFF matters as much
# as what it adds - each gunship prints one of the two re-roll abilities, not
# both, and an inherited flag left standing would give the Sky Ray a bonus its
# datasheet does not print.
ck.true("the Sky Ray does NOT inherit Armour Hunter",
        not unit(SKY_RAY_GUNSHIP).models[0].profile.armour_hunter)
ck.eq("...so it gets no hit bonus against a vehicle",
      armour_hunter.modifiers(unit(SKY_RAY_GUNSHIP).models[0], _vehicle_target), [])
ck.true("and the Hammerhead does not have Velocity Tracker",
        not _hammer.models[0].profile.velocity_tracker)


# --- 3. Velocity Tracker --------------------------------------------------
# A/B: the _hit_reroll_reason entry removed -> 2 fail.
print("\n3. Velocity Tracker: re-roll the Hit roll against anything that can FLY")

_skyray = unit(SKY_RAY_GUNSHIP)
_flyer = unit(DEVILFISH, owner="Player 2")
_walker = unit(KROOT_CARNIVORES, owner="Player 2")
ck.true("a target that can FLY grants it", velocity_tracker.applies(_skyray, _flyer))
ck.true("one that cannot does not", not velocity_tracker.applies(_skyray, _walker))
ck.true("a unit without the ability gets nothing",
        not velocity_tracker.applies(unit(HAMMERHEAD_GUNSHIP), _flyer))

_vt_scene = tk.shooting_scene(SKY_RAY_GUNSHIP, DEVILFISH, attacker_owner="Player 2")
_vt_scene["shooting"].active_squad = _vt_scene["attacker"]
ck.eq("ShootingController._hit_reroll_reason() names it",
      _vt_scene["shooting"]._hit_reroll_reason(_vt_scene["target"]),
      velocity_tracker.VELOCITY_TRACKER_LABEL)

# An ordinary "you can re-roll the Hit roll" - no automatic-1s clause, so
# registering it in reroll_scope would offer a ones-only re-roll it never
# grants.
ck.true("it is NOT a ones-or-whole source",
        not reroll_scope.is_ones_or_whole(velocity_tracker.VELOCITY_TRACKER_LABEL))
ck.true("it is not read in the melee step", "velocity_tracker" not in src("game/fight.py"))


# --- 4. Targeting Array ---------------------------------------------------
# A/B: the begin_activation call removed -> 2 fail; the ledger removed -> 1;
# the roll-kind filter widened -> 1.
print("\n4. Targeting Array: one die, once per shooting activation, no CP")

_ta_scene = tk.shooting_scene(HAMMERHEAD_GUNSHIP, KROOT_CARNIVORES, attacker_owner="Player 2")
_ta = TargetingArrayController(dice_manager=_ta_scene["dice"],
                               shooting_controller=_ta_scene["shooting"])
_ta_scene["shooting"].active_squad = _ta_scene["attacker"]
_ta.begin_activation(_ta_scene["attacker"])

ck.true("nothing to do with no roll on the table", not _ta.can_use())
tk.script(2, 5, 3)
_ta_scene["dice"].roll(3, 6, label="Hit", roll_kind=HIT_ROLL, success_threshold=4)
ck.true("a Hit roll can be re-rolled", _ta.can_use())
_ta.start()
ck.true("with several dice it asks which", _ta.selecting_die)
_ta.choose_die(0)
ck.true("...and the selection closes once one is picked", not _ta.selecting_die)
ck.true("once per activation: it cannot be used again", not _ta.can_use())

# A NEW activation restores it.
_ta.begin_activation(_ta_scene["attacker"])
ck.true("a new activation restores the use", _ta.can_use())
_ta.end_activation(_ta_scene["attacker"])

# "one Hit roll OR one Wound roll" - and nothing else. A Save roll is not on
# the list, unlike Command Re-roll's, which reaches eight kinds.
#
# Asked of THIS ability rather than of the module: the shared set became the
# UNION when Armoured Warhost's Soulsight arrived naming a Damage roll too, so
# a module-level check would now pass while Targeting Array quietly gained a
# kind its printed text never mentions.
from game import activation_reroll as _ar  # noqa: E402
_ta_ability = next(a for a in _ar.ABILITIES if a.flag == "targeting_array")
ck.eq("Targeting Array names only Hit and Wound", set(_ta_ability.kinds),
      {HIT_ROLL, WOUND_ROLL})
ck.true("...and the module's union is only a pre-filter",
        set(_ta_ability.kinds) <= targeting_array.REROLLABLE_KINDS)
_ta2_scene = tk.shooting_scene(HAMMERHEAD_GUNSHIP, KROOT_CARNIVORES, attacker_owner="Player 2")
_ta2 = TargetingArrayController(dice_manager=_ta2_scene["dice"],
                                shooting_controller=_ta2_scene["shooting"])
_ta2_scene["shooting"].active_squad = _ta2_scene["attacker"]
_ta2.begin_activation(_ta2_scene["attacker"])
tk.script(1, 1)
_ta2_scene["dice"].roll(2, 6, label="Save", roll_kind=SAVE_ROLL, success_threshold=4)
ck.true("a Save roll is not eligible", not _ta2.can_use())
tk.script()

# A unit without the ability never gets the button.
_pi_scene = tk.shooting_scene(PIRANHAS, KROOT_CARNIVORES, attacker_owner="Player 2")
_pi_ta = TargetingArrayController(dice_manager=_pi_scene["dice"],
                                  shooting_controller=_pi_scene["shooting"])
_pi_scene["shooting"].active_squad = _pi_scene["attacker"]
_pi_ta.begin_activation(_pi_scene["attacker"])
tk.script(2, 2)
_pi_scene["dice"].roll(2, 6, label="Hit", roll_kind=HIT_ROLL, success_threshold=4)
ck.true("a Piranha has no Targeting Array", not _pi_ta.can_use())
tk.script()

ck.true("both gunships print it",
        targeting_array.unit_has_targeting_array(unit(HAMMERHEAD_GUNSHIP))
        and targeting_array.unit_has_targeting_array(unit(SKY_RAY_GUNSHIP)))


# --- 5. Drone Harassment Tactics ------------------------------------------
# A/B: the 12" test removed -> 1 fails; the forced-roll call removed -> 1.
print("\n5. Drone Harassment Tactics")

_dh_state = GameState()
_piranhas = unit(PIRANHAS, ci=2)
_victim = unit(KROOT_CARNIVORES, owner="Player 2")
tk.line_up(_piranhas, x=20.0, y=20.0)
tk.line_up(_victim, x=26.0, y=20.0)
for _s in (_piranhas, _victim):
    for _m in _s.models:
        _dh_state.add_token(_m)
_dh_tt = TurnTracker(first_player="Player 1")
_dh_shock = BattleShockController(turn_tracker=_dh_tt, dice_manager=tk.RecordingDice(),
                                  all_tokens=_dh_state.tokens)
_dh = DroneHarassmentController(battle_shock=_dh_shock, decision_manager=DecisionManager())

ck.eq("an enemy unit within 12\" is a target",
      [s.name for s in drone_harassment.targets_for(_piranhas, [_piranhas, _victim])],
      [_victim.name])
tk.line_up(_victim, x=60.0, y=20.0)
ck.eq("beyond 12\" there is none",
      drone_harassment.targets_for(_piranhas, [_piranhas, _victim]), [])
tk.line_up(_victim, x=26.0, y=20.0)
_friendly = unit(STRIKE_TEAM)
tk.line_up(_friendly, x=26.0, y=22.0)   # IN range, so only ownership can exclude it
ck.eq("a friendly unit in range is never a target",
      drone_harassment.targets_for(_piranhas, [_piranhas, _friendly]), [])
ck.eq("...while the enemy at the same distance is",
      [s.name for s in drone_harassment.targets_for(
          _piranhas, [_piranhas, _friendly, _victim])], [_victim.name])
ck.true("a unit without the ability has none either",
        not drone_harassment.targets_for(unit(STRIKE_TEAM), [_victim]))

tk.script(6, 6)
ck.true("it really starts a Battle-shock test", _dh.offer(_piranhas, [_piranhas, _victim]))
ck.true("...on the enemy unit", _dh_shock.rolling_squad is _victim)
tk.script()

# One candidate needs no question - the text says "select", not "you can".
ck.true("with one candidate it does not ask", not _dh.decision_manager.is_pending)


# --- 6. Source guards, sprites, and the whole roster ----------------------
print("\n6. Source guards, sprites, and the whole roster")

_main = src("main.py")
ck.true("Targeting Array is constructed in main.py",
        "targeting_array_controller = TargetingArrayController(" in _main)
ck.true("...its back-reference to the shooting controller is filled in",
        "targeting_array_controller.shooting_controller = shooting_controller" in _main)
ck.true("...it reaches the shooting controller",
        "targeting_array=targeting_array_controller," in _main)
ck.true("...its die clicks are routed",
        "targeting_array_controller.choose_die(die_index)" in _main)
ck.true("...and the panel gets it",
        "targeting_array_controller=targeting_array_controller," in _main)
ck.true("Drone Harassment fires at the end of the Movement phase",
        "drone_harassment_controller.offer_at_end_of_movement(" in _main)

_panel = src("game/ui/action_panel.py")
# The button's LABEL now comes from the controller, because the Fire Prism's
# Crystal Matrix shares this button (see game/activation_reroll.py) - so the
# guard checks that the panel ASKS, and that the fallback still names this
# ability, rather than pinning a string that two datasheets have to share.
ck.true("the panel draws the free-re-roll button",
        "targeting_array_controller.panel_label()" in _panel)
ck.true("...falling back to this ability's own name",
        '"Targeting Array",' in _panel)
ck.true("...and its own die-selection mode",
        "targeting_array_controller.selecting_die" in _panel)
ck.true("the panel parameter is keyword-appended, never positional",
        "targeting_array_controller=None," in _panel)

_shooting = src("game/shooting.py")
ck.true("the activation ledger opens at start_shooting()",
        "self.targeting_array.begin_activation(squad)" in _shooting)
ck.true("...and closes when the activation really ends",
        "self.targeting_array.end_activation(self.active_squad)" in _shooting)
ck.true("Armour Hunter sits beside Tank Hunters in the hit chain",
        "armour_hunter_module.modifiers(shooter_model, target_squad)" in _shooting)

# Sprites: the Sky Ray's art had been sitting unused in the folder since before
# this datasheet existed; the other two arrived afterwards. Asserted at the
# MODEL, never at the mapping table.
from game import sprites  # noqa: E402
for name, sheet in (("Sky Ray Gunship", SKY_RAY_GUNSHIP),
                    ("Hammerhead Gunship", HAMMERHEAD_GUNSHIP),
                    ("Piranhas", PIRANHAS)):
    for _m in unit(sheet, ci=len(sheet.compositions()) - 1).models:
        ck.true(f"{name}: {_m.profile.name} has art", sprites.sprite_for(_m) is not None)
# The Piranha file is SINGULAR where the datasheet is plural - the folder wins,
# as everywhere in that table.
ck.eq("Piranhas take the folder's singular filename",
      sprites._squad_key(unit(PIRANHAS).models[0]), "Piranha")
# The two gunships share a stat line by inheritance but NOT their art.
ck.true("the Hammerhead and the Sky Ray have different images",
        sprites._squad_key(unit(HAMMERHEAD_GUNSHIP).models[0])
        != sprites._squad_key(unit(SKY_RAY_GUNSHIP).models[0]))

# The whole point of the four Etappen: every engine-native T'au datasheet is
# built. Pinned as a NAME LIST so a future addition is a visible one-line
# change, and so that a datasheet quietly disappearing is caught too.
_built = set(TAU_EMPIRE.datasheets)
ck.eq("all 33 T'au datasheets are registered", len(_built), 33)
for _name in ("Hammerhead Gunship", "Sky Ray Gunship", "Piranhas",
              "Broadside Battlesuits", "Crisis Fireknife Battlesuits",
              "Commander Shadowsun", "Ethereal", "Kroot Farstalkers",
              "Vespid Stingwings", "Krootox Rampagers"):
    ck.true(f"{_name} is registered", _name in _built)
# The three groups deliberately left out, so that building one is a decision
# rather than an oversight.
for _name in ("Razorshark Strike Fighter", "Stormsurge", "Tidewall Gunrig"):
    ck.true(f"{_name} is deliberately NOT built (Aircraft/Titanic/Fortification)",
            _name not in _built)

ck.finish()
