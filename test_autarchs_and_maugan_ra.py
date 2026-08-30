"""Autarch / Autarch Wayleaper / Maugan Ra (Etappe 4b).

THREE LEADERS, and the batch that finally forced two extractions:

  * Path of Command is the FOURTH datasheet to print "once per battle round,
    reduce the CP cost of a Stratagem used on this unit by 1" - so the three
    existing copies moved into game/cp_discount.py rather than gaining a
    fourth. This suite therefore also checks the three MIGRATED abilities still
    behave, because a shared base that quietly changes one of them is the whole
    risk of the extraction.
  * Superlative Strategist needed an Advance-roll re-roll seam that did not
    exist. Protocol of the Sudden Storm had had one built and unit-tested since
    the Necron work and NEVER CALLED from main.py - and its own docstring put it
    after acknowledge(), where reroll_die() refuses to act at all. Both are now
    offered from one place, before the acknowledgement.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * The CP discount is measured through the REAL StratagemController, on cost
    AND on the once-per-round window, because "asking the price must not spend
    the entitlement" is the half that breaks silently.
  * Harvester of Souls is measured on the SPLIT-FIRE condition first: the
    ability's whole printed cost is giving that up, and a test that only ever
    fires at one target would pass with the condition deleted.
"""
import testkit as tk
from testkit import Checks

from game import (aspect_training, attached_units, cp_discount, face_of_death,
                  harvester_of_souls, indomitable_strength_of_will,
                  path_of_command, sprites, superlative_strategist)
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.units import (
    AsurmenProfile, AutarchProfile, AutarchWayleaperProfile, MauganRaProfile,
)
from game.weapons import (
    AutarchBansheeBladeProfile, AutarchReaperLauncherStarshotProfile,
    AutarchReaperLauncherStarswarmProfile, AutarchScorpionChainswordProfile,
    BansheeBladeProfile, MaugetarMeleeProfile, MaugetarRangedProfile,
    ReaperLauncherStarswarmProfile, ScorpionChainswordProfile, StarGlaiveProfile,
)

checks = Checks("Autarchs and Maugan Ra")


def build(sheet, owner="Player 1", n=1, **kw):
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


# --- 1. statlines -----------------------------------------------------------
print("--- 1. statlines ---")

a, w, m = AutarchProfile, AutarchWayleaperProfile, MauganRaProfile
checks.eq('Autarch M7"/T3/Sv3+/W4/Ld6+/OC1',
          (a.movement_in, a.toughness, a.armor_save, a.wounds, a.leadership, a.oc),
          (7, 3, "3+", 4, "6+", 1))
checks.eq("WS2+/BS2+", (a.weapon_skill, a.ballistic_skill), ("2+", "2+"))
checks.eq("Invulnerable 4+", a.invulnerable_save, "4+")
checks.eq("32 mm base", round(a.base_radius_in, 3), round(32 / 2 / 25.4, 3))
# The Wayleaper: same chassis, one different characteristic, and NOT a subclass.
checks.eq("the Wayleaper matches the Autarch except in Movement",
          (w.toughness, w.armor_save, w.wounds, w.leadership, w.oc,
           w.invulnerable_save, w.weapon_skill, w.ballistic_skill, w.base_radius_in),
          (a.toughness, a.armor_save, a.wounds, a.leadership, a.oc,
           a.invulnerable_save, a.weapon_skill, a.ballistic_skill, a.base_radius_in))
checks.eq('...and M14" against M7"', (w.movement_in, a.movement_in), (14, 7))
checks.true("...but it is NOT a subclass - all three of their named abilities differ",
            not issubclass(w, a) and not issubclass(a, w))
checks.true("the Wayleaper has JUMP PACK, FLY and Deep Strike",
            w.jump_pack and w.fly and w.deep_strike)
checks.true("...and the Autarch has none of the three",
            not (a.jump_pack or a.fly or a.deep_strike))
# Maugan Ra sits on the shared Phoenix Lord chassis - pinned against a sibling.
checks.eq("Maugan Ra takes the shared Phoenix Lord chassis",
          (m.toughness, m.armor_save, m.wounds, m.leadership, m.oc,
           m.invulnerable_save, m.base_radius_in),
          (AsurmenProfile.toughness, AsurmenProfile.armor_save, AsurmenProfile.wounds,
           AsurmenProfile.leadership, AsurmenProfile.oc,
           AsurmenProfile.invulnerable_save, AsurmenProfile.base_radius_in))
checks.true("...and is an EPIC HERO", m.epic_hero)
checks.true("all three lead, and all three carry Battle Focus",
            all(p.leader and p.battle_focus for p in (a, w, m)))
checks.true("both Autarchs print Path of Command, Maugan Ra does not",
            a.path_of_command and w.path_of_command and not m.path_of_command)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

autarch, wayleaper, maugan = build(ae.AUTARCH), build(ae.AUTARCH_WAYLEAPER), build(ae.MAUGAN_RA)
for sq in (autarch, wayleaper):
    checks.eq("%s default loadout" % sq.name.split(" ", 1)[1][:-2],
              sorted(x.name for x in sq.models[0].weapons),
              ["Shuriken Pistol", "Star Glaive"])
checks.eq("Maugan Ra carries the Maugetar twice - one ranged row, one melee",
          sorted(x.name for x in maugan.models[0].weapons), ["Maugetar", "Maugetar"])
checks.eq("...and they really are the two halves",
          sorted(x.weapon_type for x in maugan.models[0].weapons),
          sorted([MaugetarRangedProfile.weapon_type, MaugetarMeleeProfile.weapon_type]))

sg = StarGlaiveProfile()
checks.eq("Star Glaive A4/S6/AP-3/D3", (sg.attacks, sg.strength, sg.ap, sg.damage), (4, 6, -3, 3))
checks.true("...and no keywords at all",
            not (sg.anti or sg.sustained_hits or sg.lethal_hits or sg.devastating_wounds))
mr, mm = MaugetarRangedProfile(), MaugetarMeleeProfile()
checks.eq('Maugetar ranged 36"/A6/S7/AP-2/D2',
          (mr.range_in, mr.attacks, mr.strength, mr.ap, mr.damage), (36, 6, 7, -2, 2))
checks.true("...[DEVASTATING WOUNDS] and [IGNORES COVER]",
            mr.devastating_wounds and mr.ignores_cover)
checks.eq("Maugetar melee A5/S6/AP-2/D2",
          (mm.attacks, mm.strength, mm.ap, mm.damage), (5, 6, -2, 2))

# The three rows that differ from the Aspect Warriors' own, each pinned against
# the shared one rather than against a literal.
checks.eq("the Autarch's Banshee Blade is A5 where the Exarch's is A2",
          (AutarchBansheeBladeProfile().attacks, BansheeBladeProfile().attacks), (5, 2))
checks.true("...and everything else is inherited",
            (AutarchBansheeBladeProfile().strength, AutarchBansheeBladeProfile().ap,
             AutarchBansheeBladeProfile().anti)
            == (BansheeBladeProfile().strength, BansheeBladeProfile().ap,
                BansheeBladeProfile().anti))
checks.eq("the Autarch's Scorpion Chainsword is A7 where the Scorpion's is A4",
          (AutarchScorpionChainswordProfile().attacks,
           ScorpionChainswordProfile().attacks), (7, 4))
checks.eq("the Autarch's reaper launcher starswarm is S4 where the Dark "
          "Reapers' is S5",
          (AutarchReaperLauncherStarswarmProfile().strength,
           ReaperLauncherStarswarmProfile().strength), (4, 5))
checks.true("...and BOTH of his modes are [HEAVY], where theirs are not",
            AutarchReaperLauncherStarshotProfile().heavy
            and AutarchReaperLauncherStarswarmProfile().heavy
            and not ReaperLauncherStarswarmProfile().heavy)
checks.eq("...and his starshot's alternate mode is his own starswarm",
          AutarchReaperLauncherStarshotProfile.overcharge_profile,
          AutarchReaperLauncherStarswarmProfile)


# --- 3. wargear and points --------------------------------------------------
print("--- 3. wargear and points ---")

for sheet, line in ((ae.AUTARCH, "Autarch"), (ae.AUTARCH_WAYLEAPER, "Autarch Wayleaper")):
    both = build(sheet, n=2, choices={line: {ae.AUTARCH_PISTOL_TO_FUSION_GUN: 1,
                                             ae.AUTARCH_GLAIVE_TO_BANSHEE_BLADE: 1}})
    checks.eq("%s: one option from EACH sentence - they replace different weapons"
              % sheet.name,
              sorted(x.name for x in both.models[0].weapons),
              ["Banshee Blade", "Dragon Fusion Gun"])
    excl = build(sheet, n=3, choices={line: {ae.AUTARCH_PISTOL_TO_DEATH_SPINNER: 1,
                                             ae.AUTARCH_PISTOL_TO_FUSION_GUN: 1}})
    checks.eq("%s: the four pistol options are mutually exclusive" % sheet.name,
              len([x for x in excl.models[0].weapons
                   if x.name in ("Death Spinner", "Dragon Fusion Gun",
                                 "Dragon Fusion Pistol", "Reaper Launcher - Starshot")]), 1)
checks.eq("Maugan Ra has no wargear options at all", len(ae.MAUGAN_RA.wargear_options), 0)

checks.eq("Autarch 75", AELDARI_POINTS["Autarch"].cost_for(1, 1), 75)
checks.eq("Autarch Wayleaper 70", AELDARI_POINTS["Autarch Wayleaper"].cost_for(1, 1), 70)
checks.eq("Maugan Ra 100", AELDARI_POINTS["Maugan Ra"].cost_for(1, 1), 100)
checks.eq("every wargear option is free",
          build(ae.AUTARCH, n=4,
                choices={"Autarch": {ae.AUTARCH_PISTOL_TO_REAPER: 1}}).points, 75)
checks.eq("the Autarch leads seven datasheets - the widest line in the faction",
          len(AELDARI_POINTS["Autarch"].leads), 7)
checks.true('...including "Dark Reapers", the PLURAL datasheet name, where the '
            'printed LEADER line says "DARK REAPER"',
            "Dark Reapers" in AELDARI_POINTS["Autarch"].leads)
checks.eq("the Wayleaper leads the two jump-pack aspects",
          tuple(AELDARI_POINTS["Autarch Wayleaper"].leads),
          ("Swooping Hawks", "Warp Spiders"))
checks.eq("Maugan Ra leads Dark Reapers - the reverse gap that datasheet carried",
          tuple(AELDARI_POINTS["Maugan Ra"].leads), ("Dark Reapers",))

reapers = tk.build(ae.DARK_REAPERS, "Player 1", name="1 Dark Reapers 1")
checks.eq("Maugan Ra really attaches to them",
          attached_units.can_attach(build(ae.MAUGAN_RA, n=5), reapers), [])
checks.eq("...and so does the Autarch",
          attached_units.can_attach(build(ae.AUTARCH, n=5), reapers), [])
checks.true("...but the Wayleaper does not",
            bool(attached_units.can_attach(build(ae.AUTARCH_WAYLEAPER, n=5), reapers)))


# --- 4. Path of Command, and the extraction it forced -----------------------
print("--- 4. Path of Command ---")

from game.stratagems import Stratagem, StratagemController
from game.command_points import CommandPointManager


class _Turn:
    battle_round = 1


def _stratagem_scene():
    cp = CommandPointManager()
    cp.cp["Player 1"] = 10
    ctrl = StratagemController(game_log=tk.Log(), command_points=cp)
    disc = path_of_command.PathOfCommandDiscount(turn_tracker=_Turn(), game_log=tk.Log())
    ctrl.cost_discounts.append(disc)
    return ctrl, disc


strat = Stratagem("Test Ploy", 2, lambda *a, **k: True)
ctrl, disc = _stratagem_scene()
plain = tk.build(ae.DARK_REAPERS, "Player 1", name="1 Dark Reapers 2")
led = tk.build(ae.DARK_REAPERS, "Player 1", name="1 Dark Reapers 3")
attached_units.attach(build(ae.AUTARCH, n=6), led)

checks.eq("a unit without the ability pays full price",
          ctrl._cost_for("Player 1", strat, [plain], 0), 2)
checks.eq("a unit the Autarch leads pays 1 less",
          ctrl._cost_for("Player 1", strat, [led], 0), 1)
# The half that breaks silently: asking must not spend.
checks.eq("asking twice still costs 1 - a query never burns the entitlement",
          ctrl._cost_for("Player 1", strat, [led], 0), 1)
checks.true("...and it is still available", disc.available("Player 1"))
ctrl.use("Player 1", strat, [led])
checks.true("using it spends the once-per-round entitlement",
            not disc.available("Player 1"))
checks.eq("...so the next use this round is full price",
          ctrl._cost_for("Player 1", strat, [led], 0), 2)
_Turn.battle_round = 2
checks.true("...and it comes back next battle round", disc.available("Player 1"))
checks.eq("...at the discounted price again",
          ctrl._cost_for("Player 1", strat, [led], 0), 1)

# "ONE model from your army": two bearers share ONE use.
_Turn.battle_round = 3
ctrl2, disc2 = _stratagem_scene()
led_a = tk.build(ae.DARK_REAPERS, "Player 1", name="1 Dark Reapers 4")
attached_units.attach(build(ae.AUTARCH, n=7), led_a)
led_b = tk.build(ae.SWOOPING_HAWKS, "Player 1", name="1 Swooping Hawks 1")
attached_units.attach(build(ae.AUTARCH_WAYLEAPER, n=7), led_b)
ctrl2.use("Player 1", strat, [led_a])
checks.eq("two bearers share ONE use per round - the second pays full price",
          ctrl2._cost_for("Player 1", strat, [led_b], 0), 2)

# The extraction: four abilities, one base, and the three migrated ones intact.
from game import my_will_be_done, puretide, war_leader
for cls, flag, label in ((path_of_command.PathOfCommandDiscount, "path_of_command", "Path of Command"),
                         (puretide.PuretideController, "puretide_teachings", "Puretide's Teachings"),
                         (my_will_be_done.MyWillBeDoneDiscount, "my_will_be_done", "My Will Be Done"),
                         (war_leader.WarLeaderDiscount, "war_leader", "War Leader")):
    checks.true("%s shares the extracted base" % label,
                issubclass(cls, cp_discount.OncePerRoundCpDiscount))
    checks.eq("...and names its own flag", cls.flag, flag)
    checks.eq("...and its own label", cls.label, label)
    checks.eq("...and the printed 1CP", cls.discount_cp, 1)


# --- 5. Superlative Strategist, and the seam it needed ----------------------
print("--- 5. Superlative Strategist ---")

lone = build(ae.AUTARCH, n=8)
checks.true("an Autarch standing alone grants nothing - the text says LEADING",
            not superlative_strategist.applies(lone))
guided = tk.build(ae.DIRE_AVENGERS, "Player 1", name="1 Dire Avengers 1")
attached_units.attach(build(ae.AUTARCH, n=9), guided)
checks.true("a unit he leads does", superlative_strategist.applies(guided))
checks.true("...and one he does not, does not",
            not superlative_strategist.applies(
                tk.build(ae.DIRE_AVENGERS, "Player 1", name="1 Dire Avengers 2")))

dice = tk.RecordingDice()
ss = superlative_strategist.SuperlativeStrategistController(
    dice_manager=dice, game_log=tk.Log(), auto_players=("Player 1",))
tk.script(2, 5)
dice.roll(1, label="Advance", roll_kind="advance")
checks.eq("the roll is on the table", dice.pending_values, [2])
checks.true("a 2 is below the floor, so it is re-rolled",
            ss.maybe_offer_advance_reroll(guided))
checks.eq("...and the die really changed", dice.pending_values, [5])
dice2 = tk.RecordingDice()
ss2 = superlative_strategist.SuperlativeStrategistController(
    dice_manager=dice2, game_log=tk.Log(), auto_players=("Player 1",))
tk.script(5, 1)
dice2.roll(1, label="Advance", roll_kind="advance")
checks.true("a 5 is kept - re-rolling an average result wins nothing",
            not ss2.maybe_offer_advance_reroll(guided))
checks.eq("...and the die is untouched", dice2.pending_values, [5])

# The seam, and the bug it fixes.
main_src = open("main.py", encoding="utf-8").read()
checks.true("main.py offers the Advance re-roll",
            "superlative_strategist_controller.maybe_offer_advance_reroll(_adv_squad)" in main_src)
checks.true("...and Protocol of the Sudden Storm's, which had NEVER been called",
            "sudden_storm_controller.maybe_offer_advance_reroll(_adv_squad)" in main_src)


def _before(text, first, second):
    """Order guard that goes RED rather than raising when a needle is gone."""
    i, j = text.find(first), text.find(second)
    return i >= 0 and j >= 0 and i < j


checks.true("...BEFORE dice_manager.acknowledge(), which is the only instant "
            "reroll_die() can act: acknowledge() clears pending_values",
            _before(main_src, "sudden_storm_controller.maybe_offer_advance_reroll",
                    "dice_manager.acknowledge()"))
checks.true("...and only for an ADVANCE roll",
            "if dice_manager.roll_kind == ADVANCE_ROLL:" in main_src)


# --- 6. Aspect Training -----------------------------------------------------
print("--- 6. Aspect Training ---")

banshees = tk.build(ae.HOWLING_BANSHEES, "Player 1", name="1 Howling Banshees 1")
attached_units.attach(build(ae.AUTARCH, n=10), banshees)
scorpions = tk.build(ae.STRIKING_SCORPIONS, "Player 1", name="1 Striking Scorpions 1")
attached_units.attach(build(ae.AUTARCH, n=11), scorpions)
checks.true("leading Banshees is recognised", aspect_training.leads_banshees(banshees))
checks.true("...and leading Scorpions is not the same thing",
            not aspect_training.leads_scorpions(banshees))
checks.true("leading Scorpions is recognised", aspect_training.leads_scorpions(scorpions))
checks.true("Fights First is granted with the Banshees",
            aspect_training.grants_fights_first(banshees))
checks.true("...and not with the Scorpions",
            not aspect_training.grants_fights_first(scorpions))
checks.eq('Scouts 7" is granted with the Scorpions',
          aspect_training.grants_scouts_in(scorpions), aspect_training.ASPECT_TRAINING_SCOUTS_IN)
checks.eq("...and nothing with the Banshees",
          aspect_training.grants_scouts_in(banshees), None)
checks.true("a unit with no Autarch grants nothing",
            not aspect_training.leads_scorpions(
                tk.build(ae.STRIKING_SCORPIONS, "Player 1", name="1 Striking Scorpions 2")))
# The measured claim that makes three of the four no-ops.
from game.squad import squad_has_stealth
from game import scouts as scouts_module
checks.true("the Scorpions keep Stealth with the Autarch attached - 19.04 "
            "already stops a joining character stripping it, which is the "
            "breakage this ability exists to prevent",
            squad_has_stealth(scorpions))
checks.eq("...and Scouts too - the Scorpions print all three themselves, which "
          "is what makes ALL FOUR grants believed no-ops here",
          scouts_module.scout_distance(scorpions), 7.0)
plain_scorpions = tk.build(ae.STRIKING_SCORPIONS, "Player 1", name="1 Striking Scorpions 3")
checks.eq("...measured from both sides: the same three without any Autarch",
          (squad_has_stealth(plain_scorpions),
           scouts_module.scout_distance(plain_scorpions)), (True, 7.0))
checks.true("the predicates still fire, so a future tightening of 19.04 is one "
            "wiring change rather than a re-reading",
            aspect_training.grants_infiltrators(scorpions)
            and aspect_training.grants_stealth(scorpions))


# --- 7. Maugan Ra's two abilities -------------------------------------------
print("--- 7. Maugan Ra ---")

led_reapers = tk.build(ae.DARK_REAPERS, "Player 1", name="1 Dark Reapers 9")
attached_units.attach(build(ae.MAUGAN_RA, n=12), led_reapers)
checks.true("Harvester of Souls needs him LEADING", harvester_of_souls.applies(led_reapers))
checks.true("...and a lone Maugan Ra grants nothing",
            not harvester_of_souls.applies(build(ae.MAUGAN_RA, n=13)))

foe_a = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 1")
foe_b = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 2")
far = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 3")
tk.line_up(foe_a, x=20.0, y=20.0)
tk.line_up(foe_b, x=20.0, y=21.5)
tk.line_up(far, x=20.0, y=60.0)
tokens = list(foe_a.models) + list(foe_b.models) + list(far.models)
hv = harvester_of_souls.HarvesterOfSoulsController(game_log=tk.Log(), all_tokens=tokens)
checks.eq("a unit 1.5\" away is within 3\"", [s.name for s in hv.nearby_units(foe_a)], [foe_b.name])
checks.true("...and one 40\" away is not", far not in hv.nearby_units(foe_a))
# "every other ENEMY unit" - a friendly unit standing just as close is not
# struck, and without one on the board that word is untested.
friend = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 7")
tk.line_up(friend, x=20.0, y=18.6)
tokens_with_friend = tokens + list(friend.models)
hv_mixed = harvester_of_souls.HarvesterOfSoulsController(
    game_log=tk.Log(), all_tokens=tokens_with_friend)
checks.true("a FRIENDLY unit that close is still within 3\"",
            friend in hv_mixed.nearby_units(foe_a))
checks.true("...but is excluded once the attacker's owner is known - "
            "\"every other ENEMY unit\"",
            friend not in hv_mixed.nearby_units(foe_a, exclude_owner="Player 1"))
tk.script(1, 6, 6, 2)   # target misses, both neighbours would strike on a 5+
struck_mixed = hv_mixed.after_shooting(led_reapers, [foe_a], targeted_squads=[foe_a])
checks.true("...and the debris never reaches Maugan Ra's own side",
            friend not in struck_mixed)

# THE printed cost: split fire buys nothing.
tk.script(6, 6, 6, 6)
checks.eq("splitting fire across two units yields no debris at all",
          hv.after_shooting(led_reapers, [foe_a, foe_b], targeted_squads=[foe_a, foe_b]), [])
tk.script(6, 3, 2)   # target 5+ -> struck, neighbour 3 -> not, then D3 for wounds
struck = hv.after_shooting(led_reapers, [foe_a], targeted_squads=[foe_a])
checks.eq("firing everything at ONE unit rolls for it and its neighbour",
          [s.name for s in struck], [foe_a.name])
checks.eq("...and the struck unit takes mortal wounds", len(hv.mortal_wound_sessions), 1)
tk.script(1, 1)
checks.eq("two low rolls strike nothing",
          hv.after_shooting(led_reapers, [foe_a], targeted_squads=[foe_a]), [])
checks.eq("a unit without the ability does nothing",
          hv.after_shooting(foe_a, [foe_b], targeted_squads=[foe_b]), [])

# Face of Death: a FORCED test, at -1.
from game.battle_shock import BattleShockController
bs_dice = tk.RecordingDice()
bs = BattleShockController(dice_manager=bs_dice, game_log=tk.Log())
fod = face_of_death.FaceOfDeathController(battle_shock_controller=bs, game_log=tk.Log())
checks.eq("the penalty is 1", face_of_death.FACE_OF_DEATH_PENALTY, 1)
checks.true("Maugan Ra carries it",
            face_of_death.unit_has_face_of_death(build(ae.MAUGAN_RA, n=14)))
checks.true("a unit without it does nothing",
            not fod.offer_after_shooting(foe_a, [foe_b]))
checks.true("hitting nothing does nothing",
            not fod.offer_after_shooting(build(ae.MAUGAN_RA, n=15), []))
checks.true("one hit unit takes the test with no prompt needed",
            fod.offer_after_shooting(build(ae.MAUGAN_RA, n=16), [foe_a]))
checks.true("...and it really is a roll on the table", bs_dice.rolled)


# --- 8. Indomitable Strength of Will ----------------------------------------
print("--- 8. Indomitable Strength of Will ---")

from game import battle_focus as bf
pool = bf.BattleFocusPool(game_log=tk.Log())
pool.tokens["Player 1"] = 3
led_hawks = tk.build(ae.SWOOPING_HAWKS, "Player 1", name="1 Swooping Hawks 9")
attached_units.attach(build(ae.AUTARCH_WAYLEAPER, n=20), led_hawks)
ind = indomitable_strength_of_will.IndomitableStrengthOfWillController(
    battle_focus=pool, game_log=tk.Log())
checks.true("it needs the Wayleaper LEADING",
            indomitable_strength_of_will.applies(led_hawks))
checks.true("...and a lone Wayleaper refunds nothing",
            not indomitable_strength_of_will.applies(build(ae.AUTARCH_WAYLEAPER, n=21)))
tk.script(3)
checks.true("a 3+ refunds the token", ind.on_token_spent("Player 1", led_hawks))
checks.eq("...and the pool really grew", pool.tokens["Player 1"], 4)
tk.script(2)
checks.true("a 2 does not", not ind.on_token_spent("Player 1", led_hawks))
checks.eq("...and the pool is unchanged", pool.tokens["Player 1"], 4)
tk.script(6)
checks.true("a unit without the ability refunds nothing",
            not ind.on_token_spent("Player 1",
                                   tk.build(ae.SWOOPING_HAWKS, "Player 1",
                                            name="1 Swooping Hawks 8")))
bf_src = open("game/battle_focus.py", encoding="utf-8").read()
checks.true("the refund is fed from the token SPEND",
            "self.indomitable.on_token_spent(player, squad, manoeuvre)" in bf_src)
checks.true("...on the PAID path, after the decrement - a refund on the free "
            "Fleet of Foot branch would print tokens",
            _before(bf_src, "self.tokens[player] -= 1",
                    "self.indomitable.on_token_spent"))
checks.true("main.py attaches it to the pool",
            "battle_focus_pool.indomitable = indomitable_controller" in main_src)


# --- 9. wiring and sprites --------------------------------------------------
print("--- 9. wiring and sprites ---")

for needle, label in [
    ("stratagem_controller.cost_discounts.append(path_of_command_discount)",
     "Path of Command joins the discount list"),
    ("face_of_death_controller.offer_after_shooting", "Face of Death is a listener"),
    ("harvester_of_souls_controller.after_shooting(", "Harvester of Souls is a listener"),
    ("set(shooting_controller._targeted_squads_this_activation)",
     "...fed the TARGETED set, not the hit set"),
]:
    checks.true("main.py: %s" % label, needle in main_src)

ai_src = open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path for any of the six abilities",
            not any(n in ai_src for n in
                    ("aspect_training", "superlative_strategist", "path_of_command",
                     "indomitable", "harvester_of_souls", "face_of_death")))

for sheet in (ae.AUTARCH, ae.AUTARCH_WAYLEAPER, ae.MAUGAN_RA):
    sq = build(sheet, n=30)
    checks.eq("%s has no art yet - pinned so adding one is visible" % sheet.name,
              sprites.sprite_for(sq.models[0]), None)

checks.finish()
