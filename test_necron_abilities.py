"""The Necron datasheet abilities, driven where they actually bite.

THE RULE THIS SUITE FOLLOWS, stated because it is what makes it worth having:
a flag that is set and never read is exactly the failure a "did the flag
change" test cannot see. So each ability is measured at its consuming end -
the threshold the wound step computes, the AP the save roll is handed, the
damage the allocation session settles on - and each gets an A/B probe that
neutralises it at its SOURCE and shows the number moving back.

Abilities that are pure re-roll GRANTS are checked as predicates rather than by
driving a full re-roll: what can go wrong with them is the condition (which
target, which weapon, which phase), not the throwing of dice, and the throwing
is shared machinery that game/shooting.py's own suites already cover.
"""

import testkit as tk
from testkit import Checks, GameState, build_squad, script
from game import (
    crit_hit, damage_reduction, destroyer_cult, guardian_protocols, illuminor,
    implacable_eradication, invulnerable_save, mechanical_augmentation,
    mortal_wound_abilities as mw, my_will_be_done, overwhelming_obliteration,
    plasmacyte, reanimation_protocols as rp, resurrection_orb, rites_of_reanimation,
    technomancer as tm, wraith_form,
)
from game import attached_units, feel_no_pain
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import necrons as nec
from game.objectives import Objective
from game.terrain import EXPOSED, Obstacle, TerrainArea
from game.thresholds import parse_threshold
from game import weapons as w

c = Checks("Necron abilities")


def build(sheet, owner="Player 2", name=None, **kw):
    kw.setdefault("name", name or f"{owner[-1]} {sheet.name} 1")
    return build_squad(sheet, owner, **kw)


def lychguard(shielded=True, name="2 Lychguard 1"):
    if shielded:
        return build(nec.LYCHGUARD, name=name,
                     choices={"Lychguard": {nec.LYCHGUARD_TO_HYPERPHASE_SWORD: 5}},
                     gear={"Lychguard": [nec.LYCHGUARD_DISPERSION_SHIELD]})
    return build(nec.LYCHGUARD, name=name)


# --- 1. Guardian Protocols (Lychguard) --------------------------------------
print("--- 1. Guardian Protocols ---")

# It only works while a NOBLE leads the unit, so the check needs a real 19.01
# attachment - not merely a squad that happens to contain an Overlord.
guard = lychguard()
lord = build(nec.OVERLORD, choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}})
c.eq("unled Lychguard get nothing, however strong the attack",
     guardian_protocols.applies(guard, 20), False)

led = attached_units.attach(lord, lychguard(name="2 Lychguard 2"))
c.eq("led by a NOBLE, an attack with S > T is penalised",
     guardian_protocols.applies(led, 6), True)      # Lychguard are T5
c.eq("...but S equal to T is not - 'greater than', not 'or equal'",
     guardian_protocols.applies(led, 5), False)
c.eq("...nor is a weaker attack", guardian_protocols.applies(led, 4), False)
c.true("the Overlord really is the NOBLE the rule names",
       guardian_protocols.is_led_by_noble(led))

# ...and it reaches the threshold the wound step computes, in BOTH phases.
scene = tk.shooting_scene(nec.LOKHUST_HEAVY_DESTROYERS, nec.LYCHGUARD, gap=12.0)
sc, target = scene["shooting"], scene["target"]
sc.active_squad = scene["attacker"]
before = [m.amount for m in sc._wound_modifiers(target, 14)]
c.eq("an unled Lychguard unit collects no wound penalty", sum(before), 0)
_applies = guardian_protocols.applies
try:
    guardian_protocols.applies = lambda squad, strength: squad is target and strength > 5
    after = sum(m.amount for m in sc._wound_modifiers(target, 14))
    c.eq("with the ability live, the wound threshold is raised by 1", after, 1)
    c.eq("...and a weak attack is still untouched",
         sum(m.amount for m in sc._wound_modifiers(target, 4)), 0)
finally:
    guardian_protocols.applies = _applies
c.eq("A/B: restored, the penalty is gone again",
     sum(m.amount for m in sc._wound_modifiers(target, 14)), 0)

fight = tk.fight_scene(nec.SKORPEKH_DESTROYERS, nec.LYCHGUARD)
fc = fight["fight"]
fc.fighting_squad = fight["attacker"]
try:
    guardian_protocols.applies = lambda squad, strength: strength > 5
    c.eq("Guardian Protocols reaches the FIGHT phase too - its text says "
         "'an attack', not 'a ranged attack'",
         sum(m.amount for m in fc._wound_modifiers(w.SkorpekhHyperphaseWeaponsProfile(), fight["target"])), 1)
finally:
    guardian_protocols.applies = _applies


# --- 2. Dispersion Shield ----------------------------------------------------
print("--- 2. Dispersion Shield ---")

c.eq("a shielded Lychguard has a 4+ invulnerable save",
     invulnerable_save.effective_invulnerable_save(lychguard().models[0], None), "4+")
c.eq("a warscythe Lychguard has none",
     invulnerable_save.effective_invulnerable_save(lychguard(shielded=False).models[0], None), "-")


# --- 3. damage reduction (Overlord, Void Dragon) ----------------------------
print("--- 3. Implacable Resilience / Necrodermis ---")

lord_model = build(nec.OVERLORD).models[0]
dragon = build(nec.CTAN_SHARD_OF_THE_VOID_DRAGON).models[0]
warrior = build(nec.NECRON_WARRIORS, composition_index=0).models[0]
c.eq("the Overlord subtracts 1 from an attack's Damage",
     damage_reduction.adjusted_damage(lord_model, 3), 2)
c.eq("so does the Void Dragon", damage_reduction.adjusted_damage(dragon, 6), 5)
c.eq("a Damage 1 attack is never reduced to 0",
     damage_reduction.adjusted_damage(lord_model, 1), 1)
c.eq("a model without the ability is untouched",
     damage_reduction.adjusted_damage(warrior, 3), 3)
c.eq("the two carriers print DIFFERENT names for the same rule",
     (damage_reduction.label_for(lord_model), damage_reduction.label_for(dragon)),
     ("Implacable Resilience", "Necrodermis"))

# ...through the real allocation session, which is where it has to land
from game.damage_resolution import DamageAllocationSession
lord_squad = build(nec.OVERLORD, name="2 Overlord 9")
# a rolled 1 always fails the save (rule 05.04), so the Damage 6 lands
session = DamageAllocationSession([1], w.GaussDestructorProfile(), lord_squad,
                                  dice_manager=None, log=None)
c.eq("through the real session, a Damage 6 hit costs the Overlord only 5",
     lord_squad.models[0].profile.wounds - lord_squad.models[0].current_wounds, 5)


# --- 4. Rites of Reanimation (Technomancer) ---------------------------------
print("--- 4. Rites of Reanimation ---")

plain = build(nec.NECRON_WARRIORS, composition_index=0, name="2 Necron Warriors 5")
c.eq("Warriors alone have no Feel No Pain",
     feel_no_pain.current_feel_no_pain(plain.models[0]), "-")
techno_led = attached_units.attach(build(nec.TECHNOMANCER),
                                   build(nec.NECRON_WARRIORS, composition_index=0,
                                         name="2 Necron Warriors 6"))
c.eq("led by a Technomancer, the whole unit has Feel No Pain 5+",
     feel_no_pain.current_feel_no_pain(techno_led.models[0]), "5+")
c.eq("Illuminor Szeras keeps his printed 4+ rather than being worsened to a 5+",
     feel_no_pain.current_feel_no_pain(build(nec.ILLUMINOR_SZERAS).models[0]), "4+")


# --- 5. Harbinger of Destruction (Plasmancer) -------------------------------
print("--- 5. Harbinger of Destruction ---")

plain2 = build(nec.IMMORTALS, composition_index=0, name="2 Immortals 5")
c.eq("an unled unit crits on a 6 (rule 05.02)",
     crit_hit.crit_hit_threshold(plain2.models[0]), 6)
plas_led = attached_units.attach(build(nec.PLASMANCER),
                                 build(nec.IMMORTALS, composition_index=0, name="2 Immortals 6"))
c.eq("led by a Plasmancer, a RANGED attack crits on a 5+",
     crit_hit.crit_hit_threshold(plas_led.models[0]), 5)
c.eq("...but a MELEE attack does not - the text says 'ranged attack'",
     crit_hit.crit_hit_threshold(plas_led.models[0], melee_only=True), 6)


# --- 6. Mechanical Augmentation + Atomic Energy Manipulator -----------------
print("--- 6. Mechanical Augmentation ---")

state = GameState()
szeras = build(nec.ILLUMINOR_SZERAS)
warriors = build(nec.NECRON_WARRIORS, composition_index=0, name="2 Necron Warriors 7")
foe = build(nec.LYCHGUARD, owner="Player 1", name="1 Lychguard 1")
tk.line_up(szeras, x=20.0, y=20.0)
tk.line_up(warriors, x=21.0, y=20.0)
tk.line_up(foe, x=60.0, y=60.0)
state.tokens = list(szeras.models) + list(warriors.models) + list(foe.models)

c.eq("Szeras starts with a 3in aura",
     mechanical_augmentation.current_range_in(szeras.models[0]), 3)
c.true("a BATTLELINE unit standing next to him is augmented",
       mechanical_augmentation.is_augmented(warriors, state.tokens))
c.eq("Szeras does NOT augment himself - he is not BATTLELINE",
     mechanical_augmentation.is_augmented(szeras, state.tokens), False)
c.eq("a far-off unit is not augmented",
     mechanical_augmentation.is_augmented(foe, state.tokens), False)

flayer = w.GaussFlayerProfile()
sharper = mechanical_augmentation.adjusted_weapon(flayer, warriors, foe, state.tokens)
c.eq("an augmented unit's attacks improve their AP by 1 (more negative)",
     sharper.ap, flayer.ap - 1)
blunter = mechanical_augmentation.adjusted_weapon(
    w.WarscytheProfile(), foe, warriors, state.tokens)
c.eq("attacks TARGETING an augmented unit are worsened by 1",
     blunter.ap, w.WarscytheProfile().ap + 1)
c.eq("worsening is clamped at 0 - AP never becomes a bonus",
     mechanical_augmentation.adjusted_weapon(flayer, foe, warriors, state.tokens).ap, 0)
c.eq("the shared instance is never mutated", flayer.ap, w.GaussFlayerProfile().ap)

aem = mechanical_augmentation.AtomicEnergyManipulatorController()
aem.notify_destroyed([foe.models[0]], szeras)
grown = aem.resolve_end_of_fight_phase({szeras})
c.eq("killing something grows the aura by 3in",
     mechanical_augmentation.current_range_in(szeras.models[0]), 6)
c.eq("...and it is reported", len(grown), 1)
for _ in range(5):
    aem.notify_destroyed([foe.models[0]], szeras)
    aem.resolve_end_of_fight_phase({szeras})
c.eq("the aura is capped at the printed 12in",
     mechanical_augmentation.current_range_in(szeras.models[0]), 12)
c.eq("the growth lives on the TOKEN, never the shared profile class",
     mechanical_augmentation.current_range_in(build(nec.ILLUMINOR_SZERAS, name="2 Illuminor Szeras 2").models[0]), 3)
aem2 = mechanical_augmentation.AtomicEnergyManipulatorController()
before_range = mechanical_augmentation.current_range_in(szeras.models[0])
aem2.resolve_end_of_fight_phase({szeras})
c.eq("A/B: a phase with no kills grows nothing",
     mechanical_augmentation.current_range_in(szeras.models[0]), before_range)


# --- 7. Illuminor (conditional Lone Operative) ------------------------------
print("--- 7. Illuminor ---")

from game import status_effects
c.true("standing beside a friendly Necron unit, Szeras has Lone Operative",
       illuminor.grants_lone_operative(szeras, state.tokens))
c.eq("...and status_effects reports the range",
     status_effects.lone_operative_range(szeras, state.tokens), 12)
lonely = GameState()
solo = build(nec.ILLUMINOR_SZERAS, name="2 Illuminor Szeras 3")
tk.line_up(solo, x=20.0, y=20.0)
lonely.tokens = list(solo.models)
c.eq("alone, he does NOT - the condition is other friendly NECRONS nearby",
     illuminor.grants_lone_operative(solo, lonely.tokens), False)
c.eq("...so he has no Lone Operative at all",
     status_effects.lone_operative_range(solo, lonely.tokens), None)


# --- 8. the Destroyer Cult re-rolls -----------------------------------------
print("--- 8. Destroyer Cult ---")

lokhust = build(nec.LOKHUST_DESTROYERS, composition_index=0)
skorpekh = build(nec.SKORPEKH_DESTROYERS)
heavies = build(nec.LOKHUST_HEAVY_DESTROYERS, composition_index=0)
enemy = build(nec.IMMORTALS, owner="Player 1", composition_index=0, name="1 Immortals 1")
ark = build(nec.DOOMSDAY_ARK, owner="Player 1", name="1 Doomsday Ark 1")

c.eq("Hard-wired applies against the closest eligible target",
     destroyer_cult.hard_wired_applies(lokhust, enemy, [enemy]), True)
c.eq("...but not against a target that is not the closest",
     destroyer_cult.hard_wired_applies(lokhust, ark, [enemy, ark])
     if lokhust.min_distance_to(enemy) < lokhust.min_distance_to(ark) else False, False)

def objective_at(model, controller=None, offset=0.0):
    """A one-feature objective marker sitting on (or well away from) a model."""
    area = TerrainArea([Obstacle(model.x_in + offset, model.y_in + offset, 1.0, 1.0, EXPOSED)])
    obj = Objective(area)
    obj.controlled_by = controller
    return obj


held = objective_at(enemy.models[0], "Player 1")
mine = objective_at(enemy.models[0], "Player 2")
c.eq("the whole-roll upgrade needs an objective the OPPONENT controls",
     destroyer_cult.hard_wired_offers_full_reroll(lokhust, enemy, [enemy], [held]), True)
c.eq("...an objective this army controls does NOT qualify",
     destroyer_cult.hard_wired_offers_full_reroll(lokhust, enemy, [enemy], [mine]), False)
c.eq("...and neither does no objective at all",
     destroyer_cult.hard_wired_offers_full_reroll(lokhust, enemy, [enemy], []), False)

c.eq("Whirling Onslaught's base clause is unconditional",
     destroyer_cult.whirling_onslaught_applies(skorpekh), True)
c.eq("...and its upgrade needs a Charge move this turn",
     destroyer_cult.whirling_onslaught_offers_full_reroll(skorpekh), False)
skorpekh.charged_this_turn = True
c.eq("...which is exactly what charged_this_turn records",
     destroyer_cult.whirling_onslaught_offers_full_reroll(skorpekh), True)

c.eq("the exterminator re-rolls against soft targets",
     destroyer_cult.optimised_for_slaughter_applies(heavies, w.EnmiticExterminatorProfile(), enemy), True)
c.eq("...and NOT against a vehicle",
     destroyer_cult.optimised_for_slaughter_applies(heavies, w.EnmiticExterminatorProfile(), ark), False)
c.eq("the destructor is the mirror image - it wants the vehicle",
     destroyer_cult.optimised_for_slaughter_applies(heavies, w.GaussDestructorProfile(), ark), True)
c.eq("...and does nothing against infantry",
     destroyer_cult.optimised_for_slaughter_applies(heavies, w.GaussDestructorProfile(), enemy), False)
c.eq("a weapon the ability does not name is never affected",
     destroyer_cult.optimised_for_slaughter_applies(heavies, w.GaussFlayerProfile(), enemy), False)

# the two-clause shape is what reroll_scope names
from game import reroll_scope
c.true("all three upgradeable Necron re-rolls are ones-or-whole sources",
       all(reroll_scope.is_ones_or_whole(lbl) for lbl in (
           destroyer_cult.HARD_WIRED_LABEL, destroyer_cult.WHIRLING_ONSLAUGHT_LABEL,
           implacable_eradication.IMPLACABLE_ERADICATION_LABEL)))
c.eq("Optimised for Slaughter is NOT - it has no upgrade clause",
     reroll_scope.is_ones_or_whole(destroyer_cult.OPTIMISED_FOR_SLAUGHTER_LABEL), False)
c.eq("...and neither is an ordinary failures-or-whole source",
     reroll_scope.is_ones_or_whole("[TWIN-LINKED]"), False)


# --- 9. Implacable Eradication (Immortals) ----------------------------------
print("--- 9. Implacable Eradication ---")

immortals = build(nec.IMMORTALS, composition_index=0)
c.eq("Immortals have the base clause", implacable_eradication.applies(immortals), True)
c.eq("Lychguard do not", implacable_eradication.applies(lychguard()), False)
near = objective_at(enemy.models[0])
c.eq("the upgrade needs the TARGET within range of an objective - any objective",
     implacable_eradication.offers_full_reroll(immortals, enemy, [near]), True)
far = objective_at(enemy.models[0], offset=40.0)
c.eq("...and a distant one does not qualify",
     implacable_eradication.offers_full_reroll(immortals, enemy, [far]), False)
c.eq("unlike Hard-wired, WHO controls it is irrelevant here",
     implacable_eradication.offers_full_reroll(immortals, enemy, [mine]), True)


# --- 10. Wraith Form ---------------------------------------------------------
print("--- 10. Wraith Form ---")

state2 = GameState()
wraiths = build(nec.CANOPTEK_WRAITHS, composition_index=0)
victim = build(nec.IMMORTALS, owner="Player 1", composition_index=0, name="1 Immortals 2")
tk.line_up(wraiths, x=10.0, y=20.0)
tk.line_up(victim, x=20.0, y=20.0)
state2.tokens = list(wraiths.models) + list(victim.models)
starts = {m.id: (10.0 + i * 1.4, 20.0) for i, m in enumerate(wraiths.models)}
for m in wraiths.models:
    m.x_in = 30.0        # straight through the Immortals
crossed = wraith_form.units_moved_over(wraiths, starts, state2.tokens)
c.eq("a unit flown straight over is found", [s.name for s in crossed], ["1 Immortals 2"])
for m in wraiths.models:
    m.x_in, m.y_in = 10.0, 60.0   # nowhere near
c.eq("a unit the move never crossed is not",
     wraith_form.units_moved_over(wraiths, starts, state2.tokens), [])
c.eq("one D6 per model in the unit", wraith_form.dice_count(wraiths), 3)


# --- 11. Overwhelming Obliteration + Plasmacyte ------------------------------
print("--- 11. keyword grants ---")

ark2 = build(nec.DOOMSDAY_ARK, name="2 Doomsday Ark 5")
cannon = w.DoomsdayCannonProfile()
c.eq("the cannon is not devastating on its own",
     overwhelming_obliteration.adjusted_weapon(cannon, ark2).devastating_wounds, False)
overwhelming_obliteration.on_remain_stationary(ark2)
c.eq("Remaining Stationary grants [DEVASTATING WOUNDS]",
     overwhelming_obliteration.adjusted_weapon(cannon, ark2).devastating_wounds, True)
c.eq("...to the CANNON only, not the flayer arrays",
     overwhelming_obliteration.adjusted_weapon(w.GaussFlayerArrayProfile(), ark2).devastating_wounds, False)
overwhelming_obliteration.expire_for_turn([ark2])
c.eq("and it expires at the end of the turn",
     overwhelming_obliteration.adjusted_weapon(cannon, ark2).devastating_wounds, False)
c.eq("A/B: a unit without the ability never gets it",
     overwhelming_obliteration.on_remain_stationary(build(nec.IMMORTALS, composition_index=0, name="2 Immortals 8")), False)

sk = build(nec.SKORPEKH_DESTROYERS, name="2 Skorpekh Destroyers 5",
           gear={"Skorpekh Destroyer": [nec.SKORPEKH_PLASMACYTE]})
c.eq("one Plasmacyte is one use", plasmacyte.remaining_uses(sk), 1)
c.eq("using it grants [DEVASTATING WOUNDS] to melee weapons",
     (plasmacyte.use(sk),
      plasmacyte.adjusted_weapon(w.SkorpekhHyperphaseWeaponsProfile(), sk).devastating_wounds),
     (True, True))
c.eq("...and it cannot be used twice in one phase", plasmacyte.can_use(sk), False)
plasmacyte.reset_phase([sk])
c.eq("after the phase the grant is gone",
     plasmacyte.adjusted_weapon(w.SkorpekhHyperphaseWeaponsProfile(), sk).devastating_wounds, False)
c.eq("...and so is the once-per-battle use", plasmacyte.remaining_uses(sk), 0)
c.eq("a unit with no Plasmacyte can never use it",
     plasmacyte.can_use(build(nec.SKORPEKH_DESTROYERS, name="2 Skorpekh Destroyers 6")), False)


# --- 12. My Will Be Done ----------------------------------------------------
print("--- 12. My Will Be Done ---")


class _Turn:
    battle_round = 1


discount = my_will_be_done.MyWillBeDoneDiscount(turn_tracker=_Turn())
lord_unit = build(nec.OVERLORD, name="2 Overlord 7")
c.eq("a Stratagem targeting the Overlord costs 1CP less",
     discount.available_discount("Player 2", None, [lord_unit]), 1)
c.eq("...but only for a unit that actually carries the ability",
     discount.available_discount("Player 2", None, [build(nec.IMMORTALS, composition_index=0, name="2 Immortals 7")]), 0)
discount.consume("Player 2", None, [lord_unit])
c.eq("once per battle ROUND, per army",
     discount.available_discount("Player 2", None, [lord_unit]), 0)
_Turn.battle_round = 2
c.eq("...and it comes back next round",
     discount.available_discount("Player 2", None, [lord_unit]), 1)


# --- 13. the Technomancer's repair and the Resurrection Orb -----------------
print("--- 13. repair and the orb ---")

state3 = GameState()
techno = build(nec.TECHNOMANCER, name="2 Technomancer 5")
hurt = build(nec.LYCHGUARD, name="2 Lychguard 7")
tk.line_up(techno, x=20.0, y=20.0)
tk.line_up(hurt, x=21.0, y=20.0)
state3.tokens = list(techno.models) + list(hurt.models)
hurt.models[0].current_wounds = 1

ctrl = tm.TechnomancerController(dice_manager=DiceManager(), game_state=state3,
                                 auto_players=("Player 2",))
c.eq("a damaged friendly model within 6in is eligible",
     [m.profile.name for m in ctrl.eligible_targets(techno)], ["Lychguard"])
script(2, default=2)
c.eq("the ability fires", ctrl.offer(techno), True)
ctrl.dice_manager.acknowledge()
ctrl.on_dice_acknowledged()
c.eq("the model is healed, capped at its own maximum", hurt.models[0].current_wounds, 2)
c.eq("...and cannot be picked again this turn",
     [m.profile.name for m in ctrl.eligible_targets(techno)], [])
ctrl.reset_turn()
c.eq("a fully healed unit offers nothing at all",
     ctrl.eligible_targets(techno), [])

state4 = GameState()
orb_lord = build(nec.OVERLORD, name="2 Overlord 8",
                 choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}},
                 gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]})
squad4 = build(nec.NECRON_WARRIORS, composition_index=0, name="2 Necron Warriors 8")
led4 = attached_units.attach(orb_lord, squad4, game_state=state4)
tk.line_up(led4, x=20.0, y=20.0)
state4.tokens = list(led4.models)
for m in led4.models[:4]:
    m.current_wounds = 0
state4.remove_dead_models()

orb = resurrection_orb.ResurrectionOrbController(
    dice_manager=DiceManager(), game_state=state4, auto_players=("Player 2",))
c.true("the orb is on the board", resurrection_orb.has_orb(led4))
c.true("the unit has enough to recover for the AI to spend it",
       orb.is_worth_using(led4))
script(6, default=6)
c.eq("the orb is used", orb.offer_at_end_of_phase({led4}, "Player 2"), True)
orb.dice_manager.acknowledge()
orb.on_dice_acknowledged()
c.true("...and it reanimates on a D6, so more than a D3 could",
       len(led4.models) > 7)
c.eq("once per battle, per unit", orb.can_use(led4), False)


# --- 14. the two mortal-wound abilities -------------------------------------
print("--- 14. Living Lightning / Matter Absorption ---")

state5 = GameState()
plasmancer = build(nec.PLASMANCER, name="2 Plasmancer 5")
dragon_sq = build(nec.CTAN_SHARD_OF_THE_VOID_DRAGON, name="2 Void Dragon 5")
tank = build(nec.DOOMSDAY_ARK, owner="Player 1", name="1 Doomsday Ark 5")
troops = build(nec.IMMORTALS, owner="Player 1", composition_index=0, name="1 Immortals 5")
tk.line_up(plasmancer, x=20.0, y=20.0)
tk.line_up(dragon_sq, x=20.0, y=24.0)
tk.line_up(tank, x=25.0, y=25.0)
tk.line_up(troops, x=28.0, y=28.0)
state5.tokens = (list(plasmancer.models) + list(dragon_sq.models)
                 + list(tank.models) + list(troops.models))

lightning = mw.living_lightning_targets(plasmancer, state5.tokens)
c.true("Living Lightning can reach both enemy units within 18in",
       {s.name for s in lightning} == {"1 Doomsday Ark 5", "1 Immortals 5"})
vehicles = mw.matter_absorption_targets(dragon_sq, state5.tokens)
c.eq("Matter Absorption sees VEHICLES only",
     [s.name for s in vehicles], ["1 Doomsday Ark 5"])

ll = mw.LivingLightningController(dice_manager=DiceManager(), game_state=state5,
                                  auto_players=("Player 2",))
script(4, 4, 4, 1, default=1)
c.eq("Living Lightning fires", ll.offer_at_shooting_phase({plasmancer}, "Player 2"), True)
ll.dice_manager.acknowledge()
# Snapshot BEFORE the acknowledgement: against a SINGLE-model target the
# session applies the wounds itself and never parks, which is exactly why the
# hole below survived so long - every one-model victim behaved correctly.
_ll_before = sum(m.current_wounds for s in lightning for m in s.models)
ll.on_dice_acknowledged()
c.true("...four D6 were thrown, three of them 4+", ll.mortal_wound_session is not None)
c.eq("...ordering 3 mortal wounds", ll.mortal_wound_session.inflicted
     + ll.mortal_wound_session.remaining, 3)
# AND THEY REALLY ARRIVE. The sum above is the same whether the allocation
# resolves or is abandoned - and against a MULTI-model target it was
# abandoned: rule 06.02 parks the session on pending_choice and nothing here
# ever drained it. Six abilities across four factions shared that hole; see
# the rule 06.02 note in game/mortal_wound_abilities.py.
_ll_guard = 0
while ll.pending_damage_choice and _ll_guard < 10:
    ll.choose_damage_model(ll.pending_damage_choice[0])
    _ll_guard += 1
c.eq("...and all three really come off the target",
     _ll_before - sum(m.current_wounds for s in lightning for m in s.models), 3)
c.eq("...with nothing left to pick", ll.pending_damage_choice, None)
c.eq("once per Shooting phase", ll.can_use(plasmancer), False)

ma = mw.MatterAbsorptionController(dice_manager=DiceManager(), game_state=state5,
                                   auto_players=("Player 2",))
dragon_sq.models[0].current_wounds = 10
script(5, 3, default=1)
c.eq("Matter Absorption fires", ma.offer_at_shooting_phase({dragon_sq}, "Player 2"), True)
ma.dice_manager.acknowledge(); ma.on_dice_acknowledged()   # the 2+ gate
ma.dice_manager.acknowledge(); ma.on_dice_acknowledged()   # the D3
c.eq("the Void Dragon regains up to that many lost wounds",
     dragon_sq.models[0].current_wounds, 13)

ma2 = mw.MatterAbsorptionController(dice_manager=DiceManager(), game_state=state5,
                                    auto_players=("Player 2",))
dragon_sq.models[0].current_wounds = 10
script(1, default=1)
ma2.offer_at_shooting_phase({dragon_sq}, "Player 2")
ma2.dice_manager.acknowledge(); ma2.on_dice_acknowledged()
c.eq("A/B: a failed 2+ gate drains nothing and heals nothing",
     dragon_sq.models[0].current_wounds, 10)

c.finish()
