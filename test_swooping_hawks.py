"""Swooping Hawks - statline, weapons, wargear, and Grenade Pack Flyover.

GRENADE PACK FLYOVER is mechanically Seer Council's Isha's Fury with the
numbers changed, and the three differences are all worth pinning because each
is a place the printed text says something specific:

  * "one D6 for each SWOOPING HAWKS model" counts models with the ability, not
    every model in the unit - after a 19.01 merge Baharroth is in there and he
    is a BAHARROTH;
  * the cap is on the MORTAL WOUNDS ("to a maximum of 6"), not on the dice, so
    a ten-model unit still rolls ten;
  * using it locks the unit out of the Explosives Stratagem for the turn.
"""

import testkit as tk
from game import aspect_shrine, explosives, grenade_pack_flyover as gpf
from game.factions import aeldari as ae
from game.factions import orks as ork
from game.turn import PHASE_MOVEMENT
from game.units import SwoopingHawkExarchProfile, SwoopingHawkProfile

checks = tk.Checks("Swooping Hawks")

EXARCH = "Swooping Hawk Exarch"


def hawks(choices=None, composition_index=0, name="1 Swooping Hawks 1"):
    return tk.build(ae.SWOOPING_HAWKS, "Player 1", name=name,
                    choices=choices, composition_index=composition_index)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

five = hawks()
ten = hawks(composition_index=1)
checks.eq("5 models: 1 Exarch + 4", len(five.models), 5)
checks.eq("10 models: 1 Exarch + 9", len(ten.models), 10)
checks.eq("...cost 95", five.points, 95)
checks.eq("...and 190", ten.points, 190)
# Tiered by how many copies the army fields, like Warp Spiders.
# testkit's build() has no unit_index, so the tier is read off the points
# table directly - which is what Squad.points asks anyway.
from game.factions.aeldari_points import AELDARI_POINTS  # noqa: E402

checks.eq("the 3rd copy costs more", AELDARI_POINTS["Swooping Hawks"].cost_for(5, 3), 110)
checks.eq("...at both sizes", AELDARI_POINTS["Swooping Hawks"].cost_for(10, 3), 205)

p = SwoopingHawkProfile()
exarch = SwoopingHawkExarchProfile()
checks.eq("M14\"", p.movement_in, 14)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv4+", p.armor_save, "4+")
checks.eq("W1", p.wounds, 1)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("BS3+ / WS3+", (p.ballistic_skill, p.weapon_skill), ("3+", "3+"))
checks.eq("5+ invulnerable save", p.invulnerable_save, "5+")
checks.eq("32 mm base -> 0.630\"", p.base_radius_in, round(32 / 2 / 25.4, 3))
checks.eq("the Exarch differs in Wounds alone", exarch.wounds, 2)
checks.eq("...same M", exarch.movement_in, p.movement_in)
checks.true("...and is the squad leader", exarch.squad_leader)

# INFANTRY despite 14" and FLY - which is what separates them from the Aeldari
# jetbikes, and it has real consequences.
checks.true("INFANTRY", p.infantry)
checks.true("JUMP PACK", p.jump_pack)
checks.true("FLY", p.fly)
checks.true("CORE: Deep Strike (24.09)", p.deep_strike)
checks.true("Battle Focus", p.battle_focus)
checks.true("Aspect Shrine", p.aspect_shrine)
checks.eq("no LEADER ability", getattr(p, "leader", False), False)
# ...against the jetbikes that are the same speed.
checks.eq("the Shining Spears at the same speed are NOT infantry",
          tk.build(ae.SHINING_SPEARS, "Player 1", name="1 Shining Spears 1").models[0].profile.infantry,
          False)

aspect_shrine.grant_tokens(five)
aspect_shrine.grant_tokens(ten)
checks.eq("1 Aspect Shrine token per 5 models", aspect_shrine.tokens_for(five), 1)
checks.eq("...2 at 10", aspect_shrine.tokens_for(ten), 2)


# --- 2. weapons and wargear -------------------------------------------------
print("--- 2. weapons and wargear ---")


def guns(squad, i=0):
    return sorted(w.name + ("" if w.weapon_type == "ranged" else " (M)")
                  for w in squad.models[i].weapons)


checks.eq("the rank and file carry a Lasblaster",
          guns(five, 1), ["Close Combat Weapon (M)", "Lasblaster"])
checks.eq("...and the Exarch a Hawk's Talon",
          guns(five, 0), ["Close Combat Weapon (M)", "Hawk's Talon"])

las = next(w for w in five.models[1].weapons if w.name == "Lasblaster")
checks.eq("Lasblaster: 24\"/A4/S4/AP0/D1",
          (las.range_in, las.attacks, las.strength, las.ap, las.damage), (24, 4, 4, 0, 1))
checks.true("...[ASSAULT] + [LETHAL HITS]", las.assault and las.lethal_hits)

talon = next(w for w in five.models[0].weapons if w.name == "Hawk's Talon")
checks.eq("Hawk's Talon: A2/S6/AP-2/D2",
          (talon.attacks, talon.strength, talon.ap, talon.damage), (2, 6, -2, 2))
checks.true("...[LETHAL HITS]", talon.lethal_hits)
# The difference the swap trades away, pinned because both rows read alike.
checks.eq("...but NOT [ASSAULT], unlike the two lasblaster rows", talon.assault, False)

# The three alternatives, each replacing the same weapon.
checks.eq("-> Exarch's Lasblaster",
          guns(hawks(choices={EXARCH: {ae.HAWK_TALON_TO_EXARCHS_LASBLASTER: 1}})),
          ["Close Combat Weapon (M)", "Exarch's Lasblaster"])
checks.eq("-> Sunpistol AND Power Sword (one row, two weapons)",
          guns(hawks(choices={EXARCH: {ae.HAWK_TALON_TO_SUNPISTOL_AND_SWORD: 1}})),
          ["Close Combat Weapon (M)", "Power Sword (M)", "Sunpistol"])
checks.eq("-> Scatter Laser",
          guns(hawks(choices={EXARCH: {ae.HAWK_TALON_TO_SCATTER_LASER: 1}})),
          ["Close Combat Weapon (M)", "Scatter Laser"])
checks.eq("two at once trims to one",
          guns(hawks(choices={EXARCH: {ae.HAWK_TALON_TO_EXARCHS_LASBLASTER: 1,
                                       ae.HAWK_TALON_TO_SCATTER_LASER: 1}})),
          ["Close Combat Weapon (M)", "Exarch's Lasblaster"])
checks.eq("the rank and file are untouched",
          guns(hawks(choices={EXARCH: {ae.HAWK_TALON_TO_SCATTER_LASER: 1}}), 1),
          ["Close Combat Weapon (M)", "Lasblaster"])

exarch_las = next(w for w in hawks(choices={EXARCH: {ae.HAWK_TALON_TO_EXARCHS_LASBLASTER: 1}}
                                   ).models[0].weapons if w.name == "Exarch's Lasblaster")
checks.eq("the Exarch's Lasblaster is S5/AP-1, not the trooper's S4/AP0",
          (exarch_las.strength, exarch_las.ap), (5, -1))
sword = next(w for w in hawks(choices={EXARCH: {ae.HAWK_TALON_TO_SUNPISTOL_AND_SWORD: 1}}
                              ).models[0].weapons if w.name == "Power Sword")
checks.eq("this Power Sword is A5, not the shared A2 one", sword.attacks, 5)
checks.true("...so it is its own class",
            type(sword).__name__ == "SwoopingHawkPowerSwordProfile")
laser = next(w for w in hawks(choices={EXARCH: {ae.HAWK_TALON_TO_SCATTER_LASER: 1}}
                              ).models[0].weapons if w.name == "Scatter Laser")
checks.eq("the Scatter Laser IS the shared profile - BS3+ is the model's own",
          type(laser).__name__, "ScatterLaserProfile")


# --- 3. Grenade Pack Flyover ------------------------------------------------
print("--- 3. Grenade Pack Flyover ---")

from game.decision import DecisionManager  # noqa: E402
from game.game_state import GameState  # noqa: E402


def flyover_scene(gap=6.0, composition_index=0):
    state = GameState()
    squad = hawks(composition_index=composition_index)
    enemy = tk.build(ork.BOYZ, "Player 2", name="2 Boyz 1")
    tk.line_up(squad, y=20.0)
    tk.line_up(enemy, y=20.0 + gap)
    for s in (squad, enemy):
        for m in s.models:
            state.add_token(m)
    tt = tk._tracker(PHASE_MOVEMENT, owner="Player 1")
    log, dice, dec = tk.Log(), tk.RecordingDice(), DecisionManager()
    ctrl = gpf.GrenadePackFlyoverController(
        game_state=state, decision_manager=dec, dice_manager=dice,
        turn_tracker=tt, game_log=log,
    )
    return dict(state=state, squad=squad, enemy=enemy, ctrl=ctrl,
                dice=dice, decision=dec, turn=tt, log=log)


checks.true("the profile carries the ability", p.grenade_pack_flyover)
checks.eq("...and nothing else does",
          gpf.applies(tk.build(ork.BOYZ, "Player 2", name="2 Boyz 9")), False)

near = flyover_scene(gap=6.0)
checks.true("usable with an enemy within 8\"", near["ctrl"].can_use(near["squad"]))
checks.eq("...and it is the target", [t.name for t in near["ctrl"].targets_for(near["squad"])],
          [near["enemy"].name])
far = flyover_scene(gap=20.0)
checks.eq("...but nothing beyond 8\" qualifies", far["ctrl"].targets_for(far["squad"]), [])
wrong_phase = flyover_scene()
wrong_phase["turn"].advance_phase()
checks.eq("not outside your Movement phase",
          wrong_phase["ctrl"].can_use(wrong_phase["squad"]), False)
theirs = flyover_scene()
theirs["turn"].turn_owner = "Player 2"
checks.eq("not in the opponent's turn", theirs["ctrl"].can_use(theirs["squad"]), False)

# "one D6 for each SWOOPING HAWKS model"
checks.eq("5 models -> 5 dice", gpf.dice_count(five), 5)
checks.eq("10 models -> 10 dice", gpf.dice_count(ten), 10)

# The roll and the mortal wounds, end to end.
go = flyover_scene()
tk.script(4, 4, 1, 1, 6, default=1)          # 3 successes at 4+
go["ctrl"].offer_after_move(go["squad"], "normal")
checks.true("ending a move raises the choice", go["decision"].is_pending)
labels = tk.options_of(go["decision"])
checks.true("...listing the target", any(go["enemy"].name in l for l in labels))
checks.true("...and a way to decline", any("not use" in l for l in labels))
tk.pick_option(go["decision"], go["enemy"].name)
checks.eq("...5 dice are thrown", len(go["dice"].pending_values or []), 5)
go["dice"].acknowledge()
go["ctrl"].on_dice_acknowledged()
checks.eq("three 4+ -> 3 mortal wounds to allocate",
          len(go["ctrl"].pending_damage_choice or []) > 0, True)
# Rule 06.02: the DEFENDER picks the models.
checks.eq("...and the defender picks them", go["turn"].active_player, "Player 2")
# Measured in WOUNDS, not in bodies: this mob's Boss Nob has 2, so allocating
# blindly to whatever the session offers first can cost 3 wounds and only 2
# models. Wounds are what the ability inflicts.
before = sum(max(0, m.current_wounds) for m in go["enemy"].models)
for _ in range(3):
    choice = go["ctrl"].pending_damage_choice
    if not choice:
        break
    go["ctrl"].choose_damage_model(choice[0])
checks.eq("3 mortal wounds are taken off the target",
          before - sum(max(0, m.current_wounds) for m in go["enemy"].models), 3)
checks.eq("...and the turn is handed back", go["turn"].active_player, "Player 1")

# "once per TURN"
checks.eq("a second use in the same turn is refused",
          go["ctrl"].can_use(go["squad"]), False)
go["ctrl"].reset_turn()
checks.true("...and comes back next turn", go["ctrl"].can_use(go["squad"]))

# THE CAP is on the wounds, not the dice.
big = flyover_scene(composition_index=1)
tk.script(*([6] * 10), default=6)            # every one of ten dice succeeds
big["ctrl"].use(big["squad"], big["enemy"])
checks.eq("a 10-model unit rolls TEN dice", len(big["dice"].pending_values or []), 10)
big["dice"].acknowledge()
big["ctrl"].on_dice_acknowledged()
checks.true("...but inflicts at most 6 mortal wounds",
            any("6 mortal wound" in l for l in big["log"].lines))
checks.true("...and says it was capped", any("capped" in l for l in big["log"].lines))

# The Explosives lock-out.
lock = flyover_scene()
checks.eq("before use, the unit is not locked out of Explosives",
          lock["squad"].explosives_locked_until_end_of_turn, False)
lock["ctrl"].use(lock["squad"], lock["enemy"])
checks.true("using it locks the unit out of the Explosives Stratagem",
            lock["squad"].explosives_locked_until_end_of_turn)
# ...read by the real controller.
import inspect  # noqa: E402
checks.true("...and game/explosives.py reads that flag",
            "explosives_locked_until_end_of_turn" in inspect.getsource(explosives.ExplosivesController.can_use))


# --- 4. A/B probe -----------------------------------------------------------
print("--- 4. A/B probe ---")

original = gpf.applies
gpf.applies = lambda squad: False
probe = flyover_scene()
probe["ctrl"].offer_after_move(probe["squad"], "normal")
checks.eq("A/B: unwired, ending a move raises nothing", probe["decision"].is_pending, False)
gpf.applies = original
restored = flyover_scene()
restored["ctrl"].offer_after_move(restored["squad"], "normal")
checks.true("A/B: restored", restored["decision"].is_pending)


# --- 5. sprite --------------------------------------------------------------
print("--- 5. sprite ---")

from game import sprites  # noqa: E402

# Art arrived after the datasheet was built. Checked at the model, not at the
# mapping table: a key that resolves to no file on disk is exactly the failure
# this is here to catch.
checks.true("Swooping Hawks resolve a sprite", sprites.sprite_for(five.models[0]))
checks.true("...and it is the Swooping Hawks file",
            "Swooping Hawks" in (sprites.sprite_for(five.models[0]) or ""))
checks.eq("the Exarch shares the unit's art - no separate file was supplied",
          sprites.sprite_for(five.models[0]), sprites.sprite_for(five.models[-1]))


checks.finish()
