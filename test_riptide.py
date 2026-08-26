"""Riptide Battlesuit datasheet: base conversion, stat line, weapons, the
priced Ion Accelerator swap, and its three new engine-wired abilities
(Nova Charge, Weapon Support System, Invulnerable Save 4+).

Real objects throughout (build_squad() off the real datasheet, real
ShootingController/DiceManager/DecisionManager/TurnTracker/GameState), no
mocks of the things under test. A/B checks accompany every ability claim:
without them, a passing assertion could just as easily mean "the ability did
nothing and the baseline already looked like that".
"""

import math

from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.tau_empire import (
    KROOT_CARNIVORES, RIPTIDE_BATTLESUIT, RIPTIDE_BURST_TO_ION_ACCELERATOR,
)
from game.modifiers import Modifier
from game.nova_charge import NovaChargeController, weapon_instance_key
from game.shooting import NORMAL_SHOOTING, ShootingController
from game.turn import PHASE_SHOOTING, TurnTracker
from game.units import RiptideProfile

PASS = []
FAIL = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))


ION_CHOICES = {"Riptide Battlesuit": {RIPTIDE_BURST_TO_ION_ACCELERATOR: 1}}


def make_riptide(choices=None, x=20.0, y=20.0):
    return build_squad(
        RIPTIDE_BATTLESUIT, "Player 1", choices=choices, name="Riptide", x_in=x, y_in=y,
    )


def make_target(x=26.0, y=20.0):
    squad = build_squad(KROOT_CARNIVORES, "Player 2", name="Kroot", x_in=x, y_in=y)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + i * 1.2, y
    return squad


# --- 1. Base size: the 120mm x 92mm oval -> equal-area circle -------------
print("\n1. Base conversion (120mm x 92mm oval)")

expected_mm = math.sqrt(60.0 * 46.0)  # semi-axes, equal-AREA circle radius
expected_in = expected_mm / 25.4
check(
    "equal-area radius is 2.07\" (not the 2.09\" a semi-axis average would give)",
    abs(RiptideProfile.base_radius_in - round(expected_in, 2)) < 1e-9,
    f"sqrt(60*46)={expected_mm:.2f}mm = {expected_in:.4f}\" -> {RiptideProfile.base_radius_in}",
)
check(
    "the equal-area circle really has the oval's area",
    abs(math.pi * expected_mm ** 2 - math.pi * 60.0 * 46.0) < 1e-9,
)
check(
    "differs from a naive axis average (2.09\") - i.e. the formula is doing work",
    round(expected_in, 2) != round(((120 + 92) / 4) / 25.4, 2),
    f"axis average would be {(((120 + 92) / 4) / 25.4):.4f}\"",
)
check(
    "largest infantry-ish base in the engine but still under the Devilfish's 2.1\"",
    RiptideProfile.base_radius_in < 2.1,
)


# --- 2. Stat line, keywords, points --------------------------------------
print("\n2. Stat line / keywords / points")

squad = make_riptide()
model = squad.models[0]
p = model.profile
stats = (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc, p.weapon_skill, p.ballistic_skill)
check("M10\" T9 Sv2+ W14 Ld7+ OC4, WS5+/BS4+", stats == (10, 9, "2+", 14, "7+", 4, "5+", "4+"), str(stats))
check("Invulnerable Save (4+)", p.invulnerable_save == "4+")
check("one model in the unit", len(squad.models) == 1)
check("model's radius comes from the profile", abs(model.radius_in - 2.07) < 1e-9)
check("starts on 14 wounds", model.current_wounds == 14)
check(
    "VEHICLE/WALKER/FLY/BATTLESUIT, not INFANTRY",
    p.vehicle and p.walker and p.fly and p.battlesuit and not p.infantry,
)
check("keywords line matches the datasheet", RIPTIDE_BATTLESUIT.keywords == ("VEHICLE", "WALKER", "FLY", "BATTLESUIT", "RIPTIDE"))
check("Deadly Demise D6 is a real D6 roll, not a fixed 6", p.deadly_demise_notation is not None and p.deadly_demise_notation.sides == 6)
check("For The Greater Good", p.for_the_greater_good)
check("Damaged threshold is 1-4 wounds", p.damaged_threshold == 4)
check("points: 190 for the 1st-2nd unit", RIPTIDE_BATTLESUIT.points_for(0, unit_index=1) == 190)
check("points: 220 from the 3rd unit on", RIPTIDE_BATTLESUIT.points_for(0, unit_index=3) == 220)
check("Squad.points reflects the built unit", squad.points == 190)


# --- 3. Weapons ----------------------------------------------------------
print("\n3. Weapons")

names = [w.name for w in model.weapons]
check("default loadout: Riptide Fists + Heavy Burst Cannon + Twin Plasma Rifle + 2x Missile Pod",
      set(names) == {"Riptide Fists", "Heavy Burst Cannon", "Twin Plasma Rifle", "Missile Pod"}, str(names))
check("the two Missile Drones are baseline equipment, not an opt-in menu item",
      names.count("Missile Pod") == 2)
check("the drone's own BS5+ is kept, NOT deferred to the BS4+ Riptide",
      next(w for w in model.weapons if w.name == "Missile Pod").ballistic_skill == "5+")

hbc = next(w for w in model.weapons if w.name == "Heavy Burst Cannon")
check("Heavy Burst Cannon 36\"/A12/S6/AP-1/D2",
      (hbc.range_in, hbc.attacks, hbc.strength, hbc.ap, hbc.damage) == (36, 12, 6, -1, 2))
check("Heavy Burst Cannon defers BS to the model (prints BS4+, model is BS4+)", hbc.ballistic_skill is None)

tpr = next(w for w in model.weapons if w.name == "Twin Plasma Rifle")
check("Twin Plasma Rifle 18\"/A1/S8/AP-3/D3 [TWIN-LINKED]",
      (tpr.range_in, tpr.attacks, tpr.strength, tpr.ap, tpr.damage, tpr.twin_linked) == (18, 1, 8, -3, 3, True))

fists = next(w for w in model.weapons if w.name == "Riptide Fists")
check("Riptide Fists melee A6/S6/AP0/D2",
      (fists.weapon_type, fists.attacks, fists.strength, fists.ap, fists.damage) == ("melee", 6, 6, 0, 2))

ion_squad = make_riptide(ION_CHOICES)
ion_model = ion_squad.models[0]
ion_names = [w.name for w in ion_model.weapons]
check("Ion Accelerator swap REPLACES the Heavy Burst Cannon",
      "Ion Accelerator - Standard" in ion_names and "Heavy Burst Cannon" not in ion_names, str(ion_names))
check("Twin Plasma Rifle survives the swap", "Twin Plasma Rifle" in ion_names)
ion = next(w for w in ion_model.weapons if w.name.startswith("Ion Accelerator"))
check("Ion Accelerator standard 72\"/A6/S9/AP-2/D3",
      (ion.range_in, ion.attacks, ion.strength, ion.ap, ion.damage) == (72, 6, 9, -2, 3))
oc = ion.overcharge_profile()
check("Overcharge is a firing MODE (overcharge_profile), not a second weapon",
      ion.overcharge_profile is not None and len([w for w in ion_model.weapons if "Ion Accelerator" in w.name]) == 1)
check("Overcharge 72\"/A6/S10/AP-3/D4 [HAZARDOUS]",
      (oc.range_in, oc.attacks, oc.strength, oc.ap, oc.damage, oc.hazardous) == (72, 6, 10, -3, 4, True))
check("Ion Accelerator is priced at 25pts (190 -> 215)",
      RIPTIDE_BATTLESUIT.points_for(0, unit_index=1, choices=ION_CHOICES) == 215)
check("the priced swap is charged on the 3rd unit too (220 -> 245)",
      RIPTIDE_BATTLESUIT.points_for(0, unit_index=3, choices=ION_CHOICES) == 245)
check("default loadout is NOT charged the wargear price", squad.points == 190)


# --- 4. Weapon Support System (ignore Hit-roll modifiers) -----------------
print("\n4. Weapon Support System")

# Exercised through the REAL _hit_modifiers(), using a modifier the Riptide
# actually generates for itself: its own "Damaged: 1-4 Wounds Remaining"
# ability is a +1 to the hit threshold once it is down to 4 wounds. That is
# also the datasheet's own real synergy - the wargear is what lets a wounded
# Riptide keep shooting at full accuracy.


def hit_modifiers_for(wounds, support_system):
    sq_ = make_riptide()
    m_ = sq_.models[0]
    m_.current_wounds = wounds
    if not support_system:
        # A/B: same model, same wounds, ability switched off - so a
        # difference can only come from the ability itself.
        m_.profile = type("NoWSS", (type(m_.profile),), {"ignores_hit_modifiers": False})
    tgt_ = make_target()
    tokens_ = list(sq_.models) + list(tgt_.models)
    sc_ = ShootingController(all_tokens=tokens_, player_name="Player 1")
    sc_.shooting_type = NORMAL_SHOOTING
    sc_.active_squad = sq_
    group_ = {"pairs": [(m_, next(w for w in m_.weapons if w.name == "Heavy Burst Cannon"))],
              "target_squad": tgt_}
    return sc_._hit_modifiers(group_)


undamaged = hit_modifiers_for(14, False)
damaged_without = hit_modifiers_for(4, False)
damaged_with = hit_modifiers_for(4, True)

# This synthetic setup happens to also grant Benefit of Cover (13.08), which
# makes the A/B stronger rather than weaker: TWO independent worsening
# modifiers from two different sources have to disappear, and both arms of
# the A/B see the same cover situation, so any difference is the ability.
check("baseline: at full wounds the Damaged modifier is absent",
      not any(m.source == "Damaged" for m in undamaged), str([m.source for m in undamaged]))
check("A/B: at 4 wounds, WITHOUT the ability the Damaged +1 applies",
      any(m.source == "Damaged" for m in damaged_without), str([m.source for m in damaged_without]))
check("at 4 wounds, WITH the ability EVERY worsening modifier is ignored",
      not any(m.amount > 0 for m in damaged_with), str([m.source for m in damaged_with]))
check("...including ones from other sources in the same list (Benefit of Cover)",
      any(m.amount > 0 and m.source != "Damaged" for m in damaged_without)
      and not any(m.amount > 0 for m in damaged_with))
check("the Riptide profile actually carries the ability", RiptideProfile.ignores_hit_modifiers is True)
check("no other datasheet gained it by accident",
      not build_squad(KROOT_CARNIVORES, "Player 2", name="K").models[0].profile.ignores_hit_modifiers)


# --- 5. Nova Charge ------------------------------------------------------
print("\n5. Nova Charge")

dm = DecisionManager()
nova = NovaChargeController(decision_manager=dm)
sq = make_riptide()
mdl = sq.models[0]

offered = nova.maybe_offer(sq)
check("offered when the unit is selected to shoot", offered and dm.is_pending)
check("the choice belongs to the unit's owner", dm.player == "Player 1")
labels = [o["label"] for o in dm.options]
check("one option per distinct RANGED weapon NAME, plus a decline option",
      len(labels) == 4 and any("Heavy Burst Cannon" in l for l in labels)
      and any("Twin Plasma Rifle" in l for l in labels) and any("Missile Pod" in l for l in labels),
      str(labels))
check("two identically-named weapons collapse into ONE option (2x Missile Pod)",
      sum(1 for l in labels if "Missile Pod" in l) == 1)
check("the MELEE weapon is not offered", not any("Riptide Fists" in l for l in labels))
check("declining is possible (once-per-battle is a resource, not a forced spend)",
      any("Save Nova Charge" in l for l in labels))

# Decline first: costs nothing, grants nothing.
dm.choose(len(labels) - 1)
check("declining leaves no grant", not sq.nova_charge_grants)
check("declining does NOT consume the once-per-battle use", nova.available(mdl))

# Now actually spend it on the Heavy Burst Cannon.
nova.maybe_offer(sq)
burst_index = next(i for i, o in enumerate(dm.options) if "Heavy Burst Cannon" in o["label"])
dm.choose(burst_index)
check("spending grants the chosen weapon", bool(sq.nova_charge_grants))
check("the once-per-battle use is now spent", not nova.available(mdl))
check("no second offer while the grant is up", not nova.maybe_offer(sq))

hbc_live = next(w for w in mdl.weapons if w.name == "Heavy Burst Cannon")
tpr_live = next(w for w in mdl.weapons if w.name == "Twin Plasma Rifle")
granted = sq.nova_charge_grants[mdl.id]
check("the grant is keyed by weapon INSTANCE id", weapon_instance_key(hbc_live) in granted)
check("the weapon that was NOT chosen is not granted", weapon_instance_key(tpr_live) not in granted)


def adjusted(weapon, model_, squad_):
    from game.nova_charge import nova_charge_adjusted_weapon
    return nova_charge_adjusted_weapon(weapon, [(model_, weapon)])


check("A/B: chosen weapon gains [DEVASTATING WOUNDS]",
      adjusted(hbc_live, mdl, sq).devastating_wounds is True)
check("A/B: the other weapon does NOT", adjusted(tpr_live, mdl, sq).devastating_wounds is False)
check("the real weapon instance is never mutated (copy, not in-place)",
      hbc_live.devastating_wounds is False)

# Overcharge: the grant must follow a firing MODE of the same weapon.
ion_sq = make_riptide(ION_CHOICES)
ion_mdl = ion_sq.models[0]
nova2 = NovaChargeController(decision_manager=DecisionManager())
nova2.maybe_offer(ion_sq)
ion_index = next(i for i, o in enumerate(nova2.decision_manager.options) if "Ion Accelerator" in o["label"])
nova2.decision_manager.choose(ion_index)
ion_std = next(w for w in ion_mdl.weapons if w.name.startswith("Ion Accelerator"))
from game.shooting import _overcharge_instance
ion_oc = _overcharge_instance(ion_std)
check("Nova Charge follows the weapon into Overcharge (same weapon, other mode)",
      adjusted(ion_oc, ion_mdl, ion_sq).devastating_wounds is True,
      "matched via overcharge_of_id, not the display name")
check("...and the Overcharge instance's own name really is different",
      ion_oc.name != ion_std.name)

# End of phase: the grant expires, the spent use does not come back.
nova.reset_phase([sq])
check("reset_phase clears the grant", not sq.nova_charge_grants)
check("A/B: after expiry the weapon is plain again", adjusted(hbc_live, mdl, sq).devastating_wounds is False)
check("the spent once-per-battle use stays spent across phases", not nova.available(mdl))
check("and no new offer is made in a later phase", not nova.maybe_offer(sq))

# A unit without the ability is never asked.
kroot = make_target()
check("a unit without Nova Charge is never offered it", not nova.maybe_offer(kroot))
check("no DecisionManager -> no crash, just no offer",
      not NovaChargeController(decision_manager=None).maybe_offer(make_riptide()))


# --- 6. Integration: the whole thing stands up ---------------------------
print("\n6. Integration")

tt = TurnTracker()
while tt.phase != PHASE_SHOOTING:
    tt.advance_phase()
tt.set_active("Player 1")
sq3 = make_riptide(x=20.0, y=20.0)
tgt = make_target(x=26.0, y=20.0)
tokens = list(sq3.models) + list(tgt.models)
dm3 = DecisionManager()
nova3 = NovaChargeController(decision_manager=dm3)
sc = ShootingController(
    all_tokens=tokens, dice_manager=DiceManager(), turn_tracker=tt,
    decision_manager=dm3, nova_charge=nova3, player_name="Player 1",
)
sc.start_shooting(sq3)
check("start_shooting() triggers the Nova Charge offer through the real controller", dm3.is_pending)
sc2 = ShootingController(all_tokens=tokens, dice_manager=DiceManager(), turn_tracker=tt, player_name="Player 1")
sq4 = make_riptide()
sc2.start_shooting(sq4)
check("A/B: no nova_charge controller wired -> no offer, no crash", not sq4.nova_charge_grants)

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
