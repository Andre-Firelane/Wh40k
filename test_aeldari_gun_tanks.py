"""Fire Prism / Night Spinner / Vypers (Etappe 3).

THREE DATASHEETS, TWO CHASSIS. The Fire Prism and Night Spinner are one hull
with two guns bolted on, so the assurance worth writing down is that they
AGREE - a per-datasheet suite could not say that. The Vypers are here because
they are the third Aeldari FLY VEHICLE of the batch and because their ability
writes into a status a T'au datasheet already owns, which is the kind of shared
state that goes wrong quietly.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * Crystal Matrix is measured as TWO uses, one per roll kind. With a shared
    ledger, spending it on a Hit roll would silently remove the Wound re-roll
    the datasheet grants - half an ability, and nothing would look wrong.
  * `pinned` is measured through effective_movement_in() and the real Charge
    roll, not off the flag: the whole point of the status is that two seams
    read it, and a flag test sees neither.
  * `suppressed` is measured for BOTH abilities out of the ONE ledger, and the
    clause that differs (does it survive its source dying?) is measured in both
    directions.
"""
import testkit as tk
from testkit import Checks

from game import activation_reroll, crystal_matrix, monofilament_web, sprites, suppression
from game.coldstar import effective_movement_in
from game.dice import HIT_ROLL, WOUND_ROLL
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.units import (
    AeldariGunTankProfile, FirePrismProfile, GhostkeelProfile,
    NightSpinnerProfile, VyperProfile,
)
from game.weapons import (
    BrightLanceProfile, DoomweaverProfile, MissileLauncherStarshotProfile,
    PrismCannonDispersedPulseProfile, PrismCannonFocusedLancesProfile,
    ScatterLaserProfile, ShurikenCannonProfile, StarcannonProfile,
    TwinShurikenCatapultProfile, VyperScatterLaserProfile,
    VyperStarcannonProfile, WraithboneHullProfile,
)

checks = Checks("Aeldari gun tanks")


def build(sheet, owner="Player 1", n=1, **kw):
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


# --- 1. the shared grav-tank hull -------------------------------------------
print("--- 1. the shared hull ---")

base = AeldariGunTankProfile
checks.eq('M14"', base.movement_in, 14)
checks.eq("T9", base.toughness, 9)
checks.eq("Sv3+", base.armor_save, "3+")
checks.eq("W12", base.wounds, 12)
checks.eq("Ld7+", base.leadership, "7+")
checks.eq("OC3", base.oc, 3)
checks.eq("BS3+", base.ballistic_skill, "3+")
checks.true("VEHICLE and FLY", base.vehicle and base.fly)
checks.eq("Deadly Demise D3", (base.deadly_demise, base.deadly_demise_notation.sides), (3, 3))
checks.eq("DAMAGED at 1-4 wounds", base.damaged_threshold, 4)
for profile in (FirePrismProfile, NightSpinnerProfile):
    checks.true("%s inherits the hull" % profile.name, issubclass(profile, base))
    checks.eq("%s: statline identical to the hull" % profile.name,
              (profile.movement_in, profile.toughness, profile.wounds, profile.oc,
               profile.armor_save, profile.damaged_threshold),
              (base.movement_in, base.toughness, base.wounds, base.oc,
               base.armor_save, base.damaged_threshold))
checks.eq("only the Fire Prism has Crystal Matrix",
          (FirePrismProfile.crystal_matrix, NightSpinnerProfile.crystal_matrix), (True, False))
checks.eq("only the Night Spinner has Monofilament Web",
          (NightSpinnerProfile.monofilament_web, FirePrismProfile.monofilament_web), (True, False))

# The grav-tank table size is a standing decision, so it is pinned against the
# tanks it was matched to rather than against the literal.
checks.eq("the hull takes the grav-tank table size, not its printed 60 mm",
          base.base_radius_in, ae.FALCON.model_lines[0].profile_cls.base_radius_in)
checks.eq("...the same one the Wave Serpent carries",
          base.base_radius_in, ae.WAVE_SERPENT.model_lines[0].profile_cls.base_radius_in)

v = VyperProfile
checks.eq('Vyper M14"/T6/Sv3+/W6/OC2',
          (v.movement_in, v.toughness, v.armor_save, v.wounds, v.oc), (14, 6, "3+", 6, 2))
checks.eq("Vyper Deadly Demise 1 (flat, so no notation)",
          (v.deadly_demise, v.deadly_demise_notation), (1, None))
checks.true("...and it is NOT the grav-tank hull", not issubclass(v, base))
checks.eq("its 105 x 70 oval takes the same equal-area circle as the Ghostkeel's",
          v.base_radius_in, GhostkeelProfile.base_radius_in)
checks.true("...which is smaller than the grav-tank size",
            v.base_radius_in < base.base_radius_in)
checks.true("all three carry Battle Focus",
            base.battle_focus and v.battle_focus)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

fp, ns, vy = build(ae.FIRE_PRISM), build(ae.NIGHT_SPINNER), build(ae.VYPERS)
checks.eq("Fire Prism loadout", sorted(w.name for w in fp.models[0].weapons),
          ["Prism Cannon - Dispersed Pulse", "Twin Shuriken Catapult", "Wraithbone Hull"])
checks.eq("Night Spinner loadout", sorted(w.name for w in ns.models[0].weapons),
          ["Doomweaver", "Twin Shuriken Catapult", "Wraithbone Hull"])
checks.eq("Vyper loadout", sorted(w.name for w in vy.models[0].weapons),
          ["Bright Lance", "Shuriken Cannon", "Wraithbone Hull"])

pulse, lances = PrismCannonDispersedPulseProfile(), PrismCannonFocusedLancesProfile()
checks.eq('dispersed pulse 60"/S6/AP-2/D2',
          (pulse.range_in, pulse.strength, pulse.ap, pulse.damage), (60, 6, -2, 2))
checks.eq("...2D6 attacks, not D6+3 - same mean, different spread",
          (pulse.attacks_notation.sides, pulse.attacks_notation.dice,
           pulse.attacks_notation.bonus), (6, 2, 0))
checks.true("...and it is [BLAST]", pulse.blast)
checks.eq('focused lances 60"/2/S18/AP-4/D6',
          (lances.range_in, lances.attacks, lances.strength, lances.ap, lances.damage),
          (60, 2, 18, -4, 6))
checks.eq("...and lances is the alternate FIRING MODE, not a second weapon",
          pulse.overcharge_profile, PrismCannonFocusedLancesProfile)
checks.true("only the pulse is granted, or the tank would have two cannons",
            "Prism Cannon - Focused Lances" not in [w.name for w in fp.models[0].weapons])

dw = DoomweaverProfile()
checks.eq('doomweaver 48"/S7/AP-1/D2',
          (dw.range_in, dw.strength, dw.ap, dw.damage), (48, 7, -1, 2))
checks.eq("...D6+3 attacks",
          (dw.attacks_notation.sides, dw.attacks_notation.bonus, dw.attacks_notation.dice),
          (6, 3, 1))
checks.true("...[BLAST], [INDIRECT FIRE] and [TWIN-LINKED]",
            dw.blast and dw.indirect_fire and dw.twin_linked)

# The two Vyper rows that differ from every other carrier of the same name.
checks.eq("the Vypers' scatter laser is [SUSTAINED HITS 2]",
          VyperScatterLaserProfile().sustained_hits, 2)
checks.eq("...where the shared row is 1", ScatterLaserProfile().sustained_hits, 1)
checks.true("...and it INHERITS, so the shared numbers cannot drift",
            issubclass(VyperScatterLaserProfile, ScatterLaserProfile)
            and VyperScatterLaserProfile().strength == ScatterLaserProfile().strength)
checks.eq("the Vypers' starcannon prints BS2+", VyperStarcannonProfile().ballistic_skill, "2+")
checks.eq("...where the shared row pins no BS at all",
          getattr(StarcannonProfile, "ballistic_skill", None), None)
checks.true("...and it INHERITS its numbers",
            (VyperStarcannonProfile().strength, VyperStarcannonProfile().ap)
            == (StarcannonProfile().strength, StarcannonProfile().ap))


# --- 3. wargear and points --------------------------------------------------
print("--- 3. wargear and points ---")

for sheet, opt in ((ae.FIRE_PRISM, ae.FIRE_PRISM_CATAPULT_TO_CANNON),
                   (ae.NIGHT_SPINNER, ae.NIGHT_SPINNER_CATAPULT_TO_CANNON)):
    line = sheet.model_lines[0].name
    swapped = build(sheet, n=2, choices={line: {opt: 1}})
    names = [w.name for w in swapped.models[0].weapons]
    checks.true("%s: the catapult becomes a shuriken cannon" % sheet.name,
                "Shuriken Cannon" in names and "Twin Shuriken Catapult" not in names)

both = build(ae.VYPERS, n=3, composition_index=1,
             choices={"Vyper": {ae.VYPER_LANCE_TO_STARCANNON: 2,
                                ae.VYPER_CANNON_TO_MISSILE: 2}})
checks.eq("a Vyper can take one option from EACH sentence - they replace "
          "different weapons", sorted(w.name for w in both.models[0].weapons),
          ["Missile Launcher - Starshot", "Starcannon", "Wraithbone Hull"])
checks.eq("...on both models", len(both.models), 2)
lasered = build(ae.VYPERS, n=4, choices={"Vyper": {ae.VYPER_LANCE_TO_SCATTER_LASER: 1}})
checks.true("the scatter laser option gives the VYPER row, not the shared one",
            any(isinstance(w, VyperScatterLaserProfile) for w in lasered.models[0].weapons))
exclusive = build(ae.VYPERS, n=5, choices={"Vyper": {ae.VYPER_LANCE_TO_SCATTER_LASER: 1,
                                                     ae.VYPER_LANCE_TO_STARCANNON: 1}})
checks.eq("the two bright-lance options are mutually exclusive - only one lands",
          len([w for w in exclusive.models[0].weapons
               if w.name in ("Scatter Laser", "Starcannon")]), 1)

checks.eq("Fire Prism 150, flat",
          (AELDARI_POINTS["Fire Prism"].cost_for(1, 1),
           AELDARI_POINTS["Fire Prism"].cost_for(1, 3)), (150, 150))
checks.eq("Night Spinner 170 for the 1st, 190 from the 2nd",
          (AELDARI_POINTS["Night Spinner"].cost_for(1, 1),
           AELDARI_POINTS["Night Spinner"].cost_for(1, 2)), (170, 190))
checks.eq("Vypers 75 for one, 140 for two",
          (AELDARI_POINTS["Vypers"].cost_for(1, 1),
           AELDARI_POINTS["Vypers"].cost_for(2, 1)), (75, 140))
checks.eq("every wargear option is free", both.points, 140)
checks.true("none of the three leads or supports anything",
            not any(AELDARI_POINTS[n].leads or AELDARI_POINTS[n].supports
                    for n in ("Fire Prism", "Night Spinner", "Vypers")))


# --- 4. Crystal Matrix ------------------------------------------------------
print("--- 4. Crystal Matrix ---")

# Three now, since Armoured Warhost's Soulsight joined - a Stratagem rather
# than a datasheet ability, which is why its flag sits on the Squad. Counted,
# so a fourth cannot arrive without this line moving.
checks.eq("three abilities share the machinery",
          sorted(a.flag for a in activation_reroll.ABILITIES),
          ["crystal_matrix", "soulsight_active", "targeting_array"])
checks.true("...and the two datasheet ones still read a PROFILE flag",
            not any(a.on_squad for a in activation_reroll.ABILITIES
                    if a.flag in ("crystal_matrix", "targeting_array")))
checks.true("Targeting Array is the OR one - a single shared use",
            [a for a in activation_reroll.ABILITIES if a.flag == "targeting_array"][0].shared_use)
checks.true("Crystal Matrix is the AND one - one use of EACH",
            not [a for a in activation_reroll.ABILITIES if a.flag == "crystal_matrix"][0].shared_use)

prism = build(ae.FIRE_PRISM, n=9)
checks.eq("the Fire Prism resolves to Crystal Matrix",
          activation_reroll.ability_of(prism).label, crystal_matrix.CRYSTAL_MATRIX_LABEL)
checks.eq("a Night Spinner has neither", activation_reroll.ability_of(ns), None)
checks.true("the flag predicate agrees", crystal_matrix.unit_has_crystal_matrix(prism))


class _Shoot:
    active_squad = prism


ctrl = activation_reroll.ActivationRerollController(
    dice_manager=tk.RecordingDice(), shooting_controller=_Shoot(), game_log=tk.Log())
ctrl.begin_activation(prism)
checks.eq("the button names the ability the ACTIVE unit prints",
          ctrl.panel_label(), crystal_matrix.CRYSTAL_MATRIX_LABEL)
checks.true("a Hit re-roll is available", ctrl.available(prism, HIT_ROLL))
checks.true("...and so is a Wound re-roll", ctrl.available(prism, WOUND_ROLL))
# Spend the Hit one, by hand at the ledger level - the interactive path is
# Targeting Array's and is already covered by its own suite.
ability = activation_reroll.ability_of(prism)
ctrl._used_this_activation.add(ctrl._ledger_key(prism, HIT_ROLL, ability))
checks.true("spending the HIT use does not remove the WOUND use - the whole "
            "difference from Targeting Array", ctrl.available(prism, WOUND_ROLL))
checks.true("...and the Hit use really is spent", not ctrl.available(prism, HIT_ROLL))
ctrl.begin_activation(prism)
checks.true("a new activation restores both",
            ctrl.available(prism, HIT_ROLL) and ctrl.available(prism, WOUND_ROLL))

# ...and the OR ability still behaves as OR through the same controller.
gunship = tk.build(__import__("game.factions.tau_empire", fromlist=["x"]).HAMMERHEAD_GUNSHIP,
                   "Player 2", name="2 Hammerhead Gunship 1")
_Shoot.active_squad = gunship
ctrl2 = activation_reroll.ActivationRerollController(
    dice_manager=tk.RecordingDice(), shooting_controller=_Shoot())
ctrl2.begin_activation(gunship)
gun_ability = activation_reroll.ability_of(gunship)
ctrl2._used_this_activation.add(ctrl2._ledger_key(gunship, HIT_ROLL, gun_ability))
checks.true("Targeting Array's single use covers BOTH kinds",
            not ctrl2.available(gunship, WOUND_ROLL))
checks.eq("...and its button still says Targeting Array", ctrl2.panel_label(),
          "Targeting Array")

panel_src = open("game/ui/action_panel.py", encoding="utf-8").read()
checks.true("the panel asks the controller for the label instead of hardcoding one",
            "targeting_array_controller.panel_label()" in panel_src)


# --- 5. Monofilament Web: the `pinned` status -------------------------------
print("--- 5. Monofilament Web ---")

web = monofilament_web.MonofilamentWebController(game_log=tk.Log())
prey = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 5")
checks.true("nothing is pinned to begin with", not monofilament_web.is_pinned(prey))
checks.eq("no penalties either",
          (monofilament_web.move_penalty_for(prey),
           monofilament_web.charge_penalty_for(prey)), (0, 0))
base_move = effective_movement_in(prey.models[0])
web.pin(prey, "Player 1")
checks.true("...and pinning works", monofilament_web.is_pinned(prey))
checks.eq("-2 Move, measured through effective_movement_in()",
          effective_movement_in(prey.models[0]), base_move - 2)
checks.eq("-2 on Charge rolls", monofilament_web.charge_penalty_for(prey), 2)
# The clause that separates pinned from shaken, measured on the ADVANCE TOTAL
# itself rather than on the shaken module's predicate: a probe that made the
# Advance seam subtract the pin left a predicate-only check fully green.
from game import montka_pulse_onslaught
from game.movement import advance_total
checks.eq("a pinned unit's Advance roll is UNCHANGED - the one clause `shaken` "
          "has and `pinned` does not", advance_total(prey, [4]), 4)
shaken_probe = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 4")
shaken_probe.shaken_until_turn = 99
checks.eq("...where a SHAKEN unit's is 2 lower, which is what makes that a "
          "real distinction and not an untested one",
          advance_total(shaken_probe, [4]), 2)
checks.eq("and the shaken module does not claim the pinned unit",
          montka_pulse_onslaught.roll_penalty_for(prey), 0)
# "until the start of YOUR next turn"
web.clear_for_turn_of("Player 2", [prey])
checks.true("the opponent's turn beginning does not clear it",
            monofilament_web.is_pinned(prey))
web.clear_for_turn_of("Player 1", [prey])
checks.true("...the pinning player's turn beginning does",
            not monofilament_web.is_pinned(prey))
checks.eq("...and the Move characteristic comes back",
          effective_movement_in(prey.models[0]), base_move)

# The per-WEAPON condition, and the absence of any choice.
web2 = monofilament_web.MonofilamentWebController(game_log=tk.Log())
a = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 6")
b = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 7")
checks.eq("a unit hit only by the twin shuriken catapult is not pinned",
          web2.after_shooting(ns, [a, b], doomweaver_hits=[]), 0)
checks.eq("EVERY unit the doomweaver hit is pinned - there is no 'select'",
          web2.after_shooting(ns, [a, b], doomweaver_hits=[a, b]), 2)
checks.true("...both of them", monofilament_web.is_pinned(a) and monofilament_web.is_pinned(b))
checks.eq("a unit without the ability pins nothing",
          web2.after_shooting(fp, [a], doomweaver_hits=[a]), 0)
checks.eq("DOOMWEAVER_NAME matches the printed weapon",
          monofilament_web.DOOMWEAVER_NAME, DoomweaverProfile.name)

# Both seams read it, checked at the source so a removed term is visible.
checks.true("effective_movement_in() subtracts the pin",
            "monofilament_web.move_penalty_for(squad)"
            in open("game/coldstar.py", encoding="utf-8").read())
checks.true("the Charge roll subtracts it too",
            "monofilament_web.charge_penalty_for(self.active_squad)"
            in open("game/charge.py", encoding="utf-8").read())


# --- 6. Harassment Fire: the shared `suppressed` status ---------------------
print("--- 6. Harassment Fire ---")

vypers = build(ae.VYPERS, n=8)
checks.true("the Vypers carry it", suppression.unit_has_harassment_fire(vypers))
checks.true("...and the grav-tanks do not",
            not suppression.unit_has_harassment_fire(fp))


class _Tokens(list):
    pass


sup = suppression.SuppressionController(
    all_tokens=_Tokens(list(vypers.models) + list(prey.models)), turn_tracker=None)
checks.true("nothing is suppressed to begin with", not sup.is_suppressed(prey))
sup.offer_harassment_fire(vypers, [prey])
checks.true("...and one hit unit becomes suppressed with no prompt needed",
            sup.is_suppressed(prey))

# The two printed differences from Suppression Volley, both measured.
sup2 = suppression.SuppressionController(all_tokens=_Tokens([]), turn_tracker=None)
sup2.offer_harassment_fire(vypers, [prey])
checks.true("Harassment Fire survives its source leaving the battlefield - it "
            "has no 'while this unit is on the battlefield' clause",
            sup2.is_suppressed(prey))
falcon = tk.build(ae.FALCON, "Player 2", name="2 Falcon 1")
sup3 = suppression.SuppressionController(
    all_tokens=_Tokens(list(vypers.models)), turn_tracker=None)
sup3.offer_harassment_fire(vypers, [falcon])
checks.true("...and it has no INFANTRY restriction, so a VEHICLE can be suppressed",
            sup3.is_suppressed(falcon))
# Suppression Volley's own clauses are untouched.
strike = tk.build(__import__("game.factions.tau_empire", fromlist=["x"]).STRIKE_TEAM,
                  "Player 2", name="2 Strike Team 1")
sup4 = suppression.SuppressionController(all_tokens=_Tokens([]), turn_tracker=None)
sup4.offer_after_shooting(strike, [prey])
checks.true("Suppression Volley still lifts when its source is gone",
            not sup4.is_suppressed(prey))
sup5 = suppression.SuppressionController(
    all_tokens=_Tokens(list(strike.models)), turn_tracker=None)
sup5.offer_after_shooting(strike, [falcon])
checks.true("...and still refuses a non-INFANTRY target", not sup5.is_suppressed(falcon))


# --- 7. wiring and sprites --------------------------------------------------
print("--- 7. wiring and sprites ---")

main_src = open("main.py", encoding="utf-8").read()
for needle, label in [
    ("monofilament_web_controller.after_shooting(", "the web is fed after shooting"),
    ("shooting_controller.squads_hit_by_weapon(DOOMWEAVER_NAME)",
     "...with the per-WEAPON subset"),
    ("monofilament_web_controller.clear_for_turn_of(turn_tracker.turn_owner)",
     "pins expire at the start of the pinning player's turn"),
    ("suppression_controller.offer_harassment_fire", "Harassment Fire is a listener"),
]:
    checks.true("main.py: %s" % label, needle in main_src)

ai_src = open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path for any of the three",
            not any(n in ai_src for n in
                    ("crystal_matrix", "monofilament_web", "harassment_fire")))

ART = {  # datasheets whose art the user has since supplied
    'Fire Prism': 'Fire Prism.png',
    'Night Spinner': 'Night Spinner.png',
    'Vypers': 'Vyper.png',
}
for sheet in (ae.FIRE_PRISM, ae.NIGHT_SPINNER, ae.VYPERS):
    sq = build(sheet, n=30)
    _p = sprites.sprite_for(sq.models[0])
    if sheet.name in ART:
        # AT THE MODEL, so a key naming a file that is not on disk fails here
        # rather than passing on a mapping table nobody checked. Named file, so
        # a datasheet quietly borrowing a NEIGHBOUR's art by substring match
        # fails too - which is how "Autarch" would shadow "Autarch Wayleaper".
        checks.true("%s draws its own art" % sheet.name,
                    ART[sheet.name] in (_p or ""))
    else:
        checks.eq("%s has no art yet - pinned so adding one is visible" % sheet.name,
                  _p, None)

checks.finish()
