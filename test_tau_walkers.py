"""The two remaining T'au Walker datasheets (Etappe 3).

  Broadside Battlesuits · Crisis Fireknife Battlesuits

Real objects throughout: the real datasheets, the real ShootingController,
the real Feel No Pain fold, the real attach(). A/B probes accompany every
ability claim.

  1. Stat lines, bases, keywords, points, compositions, wargear
  2. Advanced Armour           (Broadside) - the first CONDITIONAL Feel No Pain
  3. Fireknife                 (Crisis Fireknife) - a ones-or-whole source
  4. Weapon Support System, printed twice in two different roles
  5. The dangling LEADER reference this batch closes
  6. The missile-pod bug this batch found, and source guards
"""

import testkit as tk
from game import advanced_armour, fireknife, reroll_scope
from game.attached_units import attach, can_attach
from game.factions.tau_empire import (
    BROADSIDE_BATTLESUITS, BROADSIDE_RAIL_TO_MISSILE_PODS, COMMANDER_FARSIGHT,
    COMMANDER_IN_COLDSTAR_BATTLESUIT, COMMANDER_IN_ENFORCER_BATTLESUIT, CRISIS_FIREKNIFE,
    CRISIS_STARSCYTHE, ENFORCER_BURST_TO_MISSILE_POD, FIREKNIFE_MISSILE_POD_TO_PLASMA,
    FIREKNIFE_PLASMA_TO_MISSILE_POD, KROOT_CARNIVORES, RIPTIDE_BATTLESUIT, STRIKE_TEAM,
)
from game.factions import build_squad
from game.damage_resolution import MortalWoundAllocationSession
from game.feel_no_pain import FeelNoPainRoll, current_feel_no_pain
from game.weapons import (
    BroadsideTwinSmartMissileSystemProfile, DroneMissilePodProfile, MissilePodProfile,
    TwinSmartMissileSystemProfile,
)

ck = tk.Checks("T'au Walkers")
MM = 25.4


def unit(sheet, owner="Player 1", ci=0, choices=None, gear=None):
    return tk.build(sheet, owner, name=f"1 {sheet.name} 1", composition_index=ci,
                    choices=choices, gear=gear)


# --- 1. Stat lines, bases, keywords, points, compositions -----------------
print("\n1. Stat lines, bases, keywords, points, compositions")


def stats(sheet, ci=0):
    p = unit(sheet, ci=ci).models[0].profile
    return (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc)


ck.eq("Broadside stat line", stats(BROADSIDE_BATTLESUITS), (5, 6, "2+", 8, "7+", 2))
ck.eq("Crisis Fireknife stat line", stats(CRISIS_FIREKNIFE), (10, 5, "3+", 4, "7+", 2))
# The Fireknife shares the Crisis chassis exactly - it is the third variant.
ck.eq("...which is the Starscythe's chassis, model for model",
      stats(CRISIS_FIREKNIFE), stats(CRISIS_STARSCYTHE))

_bs = unit(BROADSIDE_BATTLESUITS).models[0].profile
_fk = unit(CRISIS_FIREKNIFE).models[0].profile
ck.true("both are VEHICLE + WALKER + BATTLESUIT",
        _bs.vehicle and _bs.walker and _bs.battlesuit
        and _fk.vehicle and _fk.walker and _fk.battlesuit)
# The one keyword that separates them, and it is printed rather than assumed.
ck.true("the Broadside is the only Battlesuit here WITHOUT Fly",
        not _bs.fly and _fk.fly)
ck.true("...and the only one without Deep Strike either",
        not _bs.deep_strike and _fk.deep_strike)
ck.true("both are For The Greater Good",
        _bs.for_the_greater_good and _fk.for_the_greater_good)

ck.true("Broadside: 60mm base", abs(_bs.base_radius_in - 60 / 2 / MM) < 0.002)
ck.true("Fireknife: 50mm base", abs(_fk.base_radius_in - 50 / 2 / MM) < 0.002)

ck.eq("Broadside 1 / 2 / 3 models",
      [(len(unit(BROADSIDE_BATTLESUITS, ci=i).models),
        unit(BROADSIDE_BATTLESUITS, ci=i).points) for i in (0, 1, 2)],
      [(1, 75), (2, 150), (3, 255)])
# 115, not 100: "per Missile pod 5" is charged PER WEAPON IN THE UNIT, and the
# printed default carries three of them. The 100 on the page is the unit
# WITHOUT them - see game/factions/points.py for the user-supplied list that
# settles that reading, and note that this datasheet is one of only two here
# where the two readings differ at all.
ck.eq("Crisis Fireknife is always 3 models; its default carries three missile "
      "pods, so 100 + 3x5",
      (len(unit(CRISIS_FIREKNIFE).models), unit(CRISIS_FIREKNIFE).points), (3, 115))
# Both datasheets are tiered by how many copies the army already has.
ck.eq("a 3rd Broadside unit costs more",
      build_squad(BROADSIDE_BATTLESUITS, "Player 1", composition_index=2,
                  unit_index=3).points,
      275)
ck.eq("...and a 3rd Fireknife unit too (110 + 3x5)",
      build_squad(CRISIS_FIREKNIFE, "Player 1", unit_index=3).points, 125)

ck.eq("Broadside loadout",
      sorted({w.name for m in unit(BROADSIDE_BATTLESUITS, ci=2).models for w in m.weapons}),
      ["Crushing Bulk", "Heavy Rail Rifle"])
ck.eq("Fireknife loadout",
      sorted({w.name for m in unit(CRISIS_FIREKNIFE).models for w in m.weapons}),
      ["Battlesuit Fists", "Missile Pod", "Plasma Rifle"])

# The heavy rail rifle is not a bigger Rail rifle - three printed rows called
# some flavour of "rail rifle", three classes.
_hrr = next(w for w in unit(BROADSIDE_BATTLESUITS).models[0].weapons
            if w.name == "Heavy Rail Rifle")
ck.eq("heavy rail rifle 60\" S12 AP-4, [HEAVY] [DEVASTATING WOUNDS]",
      (_hrr.range_in, _hrr.strength, _hrr.ap, _hrr.heavy, _hrr.devastating_wounds),
      (60, 12, -4, True, True))
ck.true("...and its Damage is a D6+1 notation, not a fixed number",
        _hrr.damage_notation is not None)

# Two printed rows share the name "Twin smart missile system" and differ only
# in Attacks - so two classes, pinned against each other rather than literals.
ck.eq("the Broadside's twin SMS is A4 where the Riptide's is A3",
      (BroadsideTwinSmartMissileSystemProfile.attacks,
       TwinSmartMissileSystemProfile.attacks), (4, 3))
ck.eq("...and they agree on everything else",
      (BroadsideTwinSmartMissileSystemProfile.range_in,
       BroadsideTwinSmartMissileSystemProfile.strength,
       BroadsideTwinSmartMissileSystemProfile.indirect_fire,
       BroadsideTwinSmartMissileSystemProfile.twin_linked),
      (TwinSmartMissileSystemProfile.range_in, TwinSmartMissileSystemProfile.strength,
       TwinSmartMissileSystemProfile.indirect_fire, TwinSmartMissileSystemProfile.twin_linked))

# Wargear: "any number of models", and priced.
_pods = unit(BROADSIDE_BATTLESUITS, ci=2,
             choices={"Broadside Shas'vre": {BROADSIDE_RAIL_TO_MISSILE_PODS: 1},
                      "Broadside Shas'ui": {BROADSIDE_RAIL_TO_MISSILE_PODS: 2}})
ck.eq("all three models can trade the rail rifle for missile pods",
      sum(1 for m in _pods.models for w in m.weapons
          if w.name == "High-yield Missile Pods"), 3)
ck.eq("...and the swap is priced at 5 points each", _pods.points, 255 + 15)

# The two Fireknife swaps are MIRRORS - a model ends with two of one gun.
_two_pods = unit(CRISIS_FIREKNIFE,
                 choices={"Crisis Fireknife Shas'vre": {FIREKNIFE_PLASMA_TO_MISSILE_POD: 1}})
ck.eq("trading the plasma rifle leaves two missile pods",
      [w.name for w in _two_pods.models[0].weapons].count("Missile Pod"), 2)
_two_plasma = unit(CRISIS_FIREKNIFE,
                   choices={"Crisis Fireknife Shas'vre": {FIREKNIFE_MISSILE_POD_TO_PLASMA: 1}})
ck.eq("and trading the missile pod leaves two plasma rifles",
      [w.name for w in _two_plasma.models[0].weapons].count("Plasma Rifle"), 2)
# Neither DIRECTION is priced any more - the weapon is. Two pods on one model
# is four in the unit (120), two plasma rifles is two (110).
ck.eq("the price follows the missile pods in the built unit",
      (_two_pods.points, _two_plasma.points), (120, 110))

# Broadside gear: two independent menus, and the support items reach EVERY
# model ("any number of models can each be equipped"), not just the leader.
_geared = unit(BROADSIDE_BATTLESUITS, ci=2,
               gear={"Broadside Shas'vre": ["Seeker Missile", "Twin Plasma Rifle"],
                     "Broadside Shas'ui": ["Weapon Support System", "Gun Drone", "Gun Drone"]})
ck.eq("the Shas'vre took both of its support slots",
      sum(1 for w in _geared.models[0].weapons
          if w.name in ("Seeker Missile", "Twin Plasma Rifle")), 2)
ck.true("a support item reaches every model on its line, not only the first",
        all(m.profile.ignores_hit_modifiers for m in _geared.models
            if m.profile.name == "Broadside Shas'ui"))
ck.eq("...and the drone menu is independent of it",
      sum(1 for m in _geared.models for w in m.weapons
          if w.name == "Twin Pulse Carbine"), 4)

# KNOWN LIMITATION, pinned so that fixing it is a visible change: the printed
# footnote "no model can be equipped with BOTH a twin plasma rifle and twin
# smart missile system" cannot be expressed - Gear has no mutual exclusion,
# the same gap the Farstalkers' one-of-two firearm swap runs into.
_both_twins = unit(BROADSIDE_BATTLESUITS,
                   gear={"Broadside Shas'vre": ["Twin Plasma Rifle",
                                                "Twin Smart Missile System"]})
ck.eq("KNOWN LIMITATION: the printed twin-plasma/twin-SMS exclusion is not "
      "enforced",
      sum(1 for w in _both_twins.models[0].weapons
          if w.name in ("Twin Plasma Rifle", "Twin Smart Missile System")), 2)


# --- 2. Advanced Armour ---------------------------------------------------
# A/B: the fold removed -> 2 fail; the `mortal` gate removed -> 2.
print("\n2. Advanced Armour: Feel No Pain 4+ against MORTAL WOUNDS only")

_broad = unit(BROADSIDE_BATTLESUITS, ci=2).models[0]
ck.eq("against a mortal wound, Feel No Pain 4+",
      current_feel_no_pain(_broad, mortal=True), "4+")
ck.eq("against an ordinary wound, none at all",
      current_feel_no_pain(_broad, mortal=False), "-")
ck.eq("and the default is the ordinary case",
      current_feel_no_pain(_broad), "-")
ck.eq("a unit without the ability gets nothing either way",
      (current_feel_no_pain(unit(STRIKE_TEAM).models[0], mortal=True),
       current_feel_no_pain(unit(STRIKE_TEAM).models[0])), ("-", "-"))
ck.eq("the predicate itself is the whole condition",
      (advanced_armour.advanced_armour_feel_no_pain(_broad, mortal=True),
       advanced_armour.advanced_armour_feel_no_pain(_broad, mortal=False)),
      ("4+", "-"))

# Through a REAL FeelNoPainRoll, not just the fold. An A/B probe that removed
# the `mortal` argument from FeelNoPainRoll's own call left this suite green,
# because everything above called current_feel_no_pain() directly and nothing
# exercised the plumbing between the two (CLAUDE.md's Fehlerklasse 24).
_mortal_roll = FeelNoPainRoll(_broad, 1, tk.RecordingDice(), mortal=True)
ck.true("a mortal wound really does open a Feel No Pain roll", _mortal_roll.is_pending)
_plain_roll = FeelNoPainRoll(_broad, 1, tk.RecordingDice(), mortal=False)
ck.true("an ordinary wound does not", not _plain_roll.is_pending)
# And end to end through the session that is the mortal-wound path.
_mw_state = tk.GameState()
_mw_squad = unit(BROADSIDE_BATTLESUITS, ci=2)
for _m in _mw_squad.models:
    _mw_state.add_token(_m)
tk.script(4)          # the printed threshold: a 4 saves the wound
_session = MortalWoundAllocationSession(_mw_squad, 1, dice_manager=tk.RecordingDice())
ck.true("MortalWoundAllocationSession opens one too",
        _session.pending_fnp is not None or _session.pending_choice is not None)
tk.script()

# The mortal-wound session is the one caller that sets it, which is what makes
# the condition reachable at all.
_dr = open("game/damage_resolution.py", encoding="utf-8").read()
# The CALL EXPRESSION, not the name: a comment mentioning the flag would
# otherwise count as a second caller (CLAUDE.md's Fehlerklasse 24).
ck.true("MortalWoundAllocationSession is the only caller that sets it",
        _dr.count("mortal=True)") == 1)


# --- 3. Fireknife ---------------------------------------------------------
# A/B: the automatic-1s entry removed -> 1 fails; the whole-roll entry -> 2;
# the reroll_scope registration -> 1.
print("\n3. Fireknife: a ones-or-whole source")

_fknife = unit(CRISIS_FIREKNIFE)
_fresh = unit(KROOT_CARNIVORES, owner="Player 2")
_hurt = unit(KROOT_CARNIVORES, owner="Player 2")
_hurt.models[0].current_wounds = 0

ck.true("the automatic half applies whenever it shoots", fireknife.applies(_fknife))
ck.true("a unit without the ability gets nothing",
        not fireknife.applies(unit(CRISIS_STARSCYTHE)))
ck.true("the whole-roll half needs a target at its Starting Strength",
        fireknife.offers_full_reroll(_fknife, _fresh))
ck.true("...and a unit that has lost a model is not",
        not fireknife.offers_full_reroll(_fknife, _hurt))

# "at its Starting Strength" counts MODELS, not wounds - the obvious wrong
# guess is "undamaged".
_bleeding = unit(KROOT_CARNIVORES, owner="Player 2")
_bleeding.models[0].current_wounds = 0.5
ck.true("a unit whose models are all alive but hurt is still at Starting Strength",
        fireknife.at_starting_strength(_bleeding))

# Its two clauses are ALTERNATIVES ("instead"), so "failures only" must not be
# on offer - which is exactly what reroll_scope decides.
ck.true("it is registered as a ones-or-whole source",
        reroll_scope.is_ones_or_whole(fireknife.FIREKNIFE_LABEL))

# End to end through the real controller.
_scene = tk.shooting_scene(CRISIS_FIREKNIFE, KROOT_CARNIVORES, attacker_owner="Player 2")
_scene["shooting"].active_squad = _scene["attacker"]
ck.eq("ShootingController._hit_reroll_reason() names it against a fresh target",
      _scene["shooting"]._hit_reroll_reason(_scene["target"]), fireknife.FIREKNIFE_LABEL)
_scene["target"].models[0].current_wounds = 0
ck.true("...and not against a target below Starting Strength",
        _scene["shooting"]._hit_reroll_reason(_scene["target"]) != fireknife.FIREKNIFE_LABEL)

# Ranged only - its text says "a ranged attack".
_fight_src = open("game/fight.py", encoding="utf-8").read()
ck.true("it is not read in the melee step", "fireknife" not in _fight_src)


# --- 4. Weapon Support System, printed twice in two roles -----------------
print("\n4. Weapon Support System: one effect, two printed roles")

# On the Fireknife it is a UNIT ability, so every model has it from the start.
ck.true("the Fireknife has it as a unit ability",
        all(m.profile.ignores_hit_modifiers for m in unit(CRISIS_FIREKNIFE).models))
# On the Broadside it is WARGEAR, so a plain unit does not.
ck.true("a plain Broadside does not",
        not any(m.profile.ignores_hit_modifiers
                for m in unit(BROADSIDE_BATTLESUITS, ci=2).models))
ck.true("...until the wargear is taken",
        unit(BROADSIDE_BATTLESUITS,
             gear={"Broadside Shas'vre": ["Weapon Support System"]}
             ).models[0].profile.ignores_hit_modifiers)
# The Riptide printed it first, under the same name; Dark Reapers print the
# same effect as "Inescapable Accuracy". Hence a field named after the EFFECT.
ck.true("the Riptide has the same field set",
        unit(RIPTIDE_BATTLESUIT).models[0].profile.ignores_hit_modifiers)


# --- 5. The dangling LEADER reference this batch closes -------------------
print("\n5. Crisis Fireknife closes a dangling LEADER reference")

# THREE points-list `leads` tables have named this datasheet since the T'au
# were built, and can_attach() reads that table - so until now all three
# pointed at nothing. (can_attach returns a list of REASONS; empty = allowed.)
for name, sheet in (("Commander Farsight", COMMANDER_FARSIGHT),
                    ("Commander in Coldstar", COMMANDER_IN_COLDSTAR_BATTLESUIT),
                    ("Commander in Enforcer", COMMANDER_IN_ENFORCER_BATTLESUIT)):
    ck.true(f"{name}'s leads table names it",
            "Crisis Fireknife Battlesuits" in sheet.points.leads)
    ck.eq(f"{name} can now actually lead it",
          can_attach(unit(sheet), unit(CRISIS_FIREKNIFE)), [])

# A real attached unit, through the real attach().
_led = unit(CRISIS_FIREKNIFE)
attach(unit(COMMANDER_FARSIGHT), _led)
ck.eq("attaching merges Farsight into the unit", len(_led.models), 4)
ck.eq("...and its Starting Strength is re-derived from the components",
      _led.starting_model_count, 4)


# --- 6. The missile-pod bug this batch found, and source guards -----------
print("\n6. The missile-pod bug, and source guards")

# MissilePodProfile used to hard-code the DRONE's BS5+. Invisible while only
# drones carried one; wrong the moment a battlesuit did.
ck.eq("the model-carried missile pod has NO ballistic-skill override",
      MissilePodProfile.ballistic_skill, None)
ck.eq("the drone's copy keeps its printed 5+", DroneMissilePodProfile.ballistic_skill, "5+")
ck.true("...and the two share every other number",
        (MissilePodProfile.range_in, MissilePodProfile.attacks, MissilePodProfile.strength,
         MissilePodProfile.ap, MissilePodProfile.damage)
        == (DroneMissilePodProfile.range_in, DroneMissilePodProfile.attacks,
            DroneMissilePodProfile.strength, DroneMissilePodProfile.ap,
            DroneMissilePodProfile.damage))
_enf = unit(COMMANDER_IN_ENFORCER_BATTLESUIT,
            choices={"Commander in Enforcer Battlesuit": {ENFORCER_BURST_TO_MISSILE_POD: 1}})
ck.eq("so the Enforcer's missile pod fires at HIS BS3+, not a drone's 5+",
      next(w for w in _enf.models[0].weapons if w.name == "Missile Pod").ballistic_skill,
      None)
ck.eq("and the Fireknife's at its own 4+",
      next(w for w in unit(CRISIS_FIREKNIFE).models[0].weapons
           if w.name == "Missile Pod").ballistic_skill, None)
# The Riptide's drone-carried pair must still be 5+ - that is what the override
# was always for.
ck.eq("while the Riptide's drone pods keep the 5+",
      [w.ballistic_skill for w in unit(RIPTIDE_BATTLESUIT).models[0].weapons
       if w.name == "Missile Pod"], ["5+", "5+"])
_drones_src = open("game/drones.py", encoding="utf-8").read()
ck.true("the Missile Drone hands out the drone's copy",
        "DroneMissilePodProfile()" in _drones_src)

_shooting_src = open("game/shooting.py", encoding="utf-8").read()
ck.true("Fireknife's automatic 1s join the other sources",
        "or fireknife_ones" in _shooting_src)
ck.true("...its whole-roll half is a hit-reroll reason",
        "fireknife.offers_full_reroll(self.active_squad, target_squad)" in _shooting_src)
ck.true("...and it names itself when it is the reason",
        "ones_reason = fireknife.FIREKNIFE_LABEL" in _shooting_src)
_fnp_src = open("game/feel_no_pain.py", encoding="utf-8").read()
ck.true("Advanced Armour is folded into current_feel_no_pain()",
        "advanced_armour_feel_no_pain(model, mortal)" in _fnp_src)
# The PARAMETER, not the whole signature line: this pinned the exact text and
# went red when Seer Council's Runes of Warding added two more conditions
# beside it - a real change to the fold, but not to what this checks. Asked of
# the live function so the check survives the next one too.
import inspect as _inspect  # noqa: E402
from game.feel_no_pain import current_feel_no_pain as _cfnp  # noqa: E402
ck.true("...and the fold takes the mortal flag through",
        _inspect.signature(_cfnp).parameters["mortal"].default is False)

# ART ARRIVED - this block pinned the absence until it did. At the MODEL, so a
# key naming a file that is not on disk fails here rather than passing.
from game import sprites  # noqa: E402
for name, sheet in (("Broadside Battlesuits", BROADSIDE_BATTLESUITS),
                    ("Crisis Fireknife Battlesuits", CRISIS_FIREKNIFE)):
    for _m in unit(sheet, ci=len(sheet.compositions()) - 1).models:
        ck.true(f"{name}: {_m.profile.name} has art", sprites.sprite_for(_m) is not None)
# Both files are spelled differently from their datasheets and the FOLDER wins -
# including a typo kept verbatim, exactly as "Ghostkheel" and "Starsythe" are.
ck.eq("the Broadside file keeps its printed typo",
      sprites._squad_key(unit(BROADSIDE_BATTLESUITS).models[0]), "Broadside Battlesuites")
ck.eq("the Fireknife takes the folder's \"Tau \" prefix",
      sprites._squad_key(unit(CRISIS_FIREKNIFE).models[0]), "Tau Crisis Fireknife")
# ...and it is not accidentally borrowing one of the other two Crisis variants.
ck.true("the Fireknife does not borrow Starscythe or Sunforge art",
        sprites._squad_key(unit(CRISIS_FIREKNIFE).models[0])
        not in {sprites._squad_key(unit(CRISIS_STARSCYTHE).models[0])})

ck.finish()
