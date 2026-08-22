"""Jain Zar: datasheet data, Whirling Death, Storm of Silence.

The two abilities are tested through the paths that would silently do nothing
if they were wired to the wrong place: Whirling Death has to make the Advance
DICE ROLL not happen (not merely substitute a value into it), and Storm of
Silence has to reach BOTH phases - the fight side had no wound-reroll lookup at
all before this datasheet, only a hard-coded [TWIN-LINKED] test, so a melee
ability bolted on beside that keyword would have been easy to get wrong.
"""

import testkit as tk
from testkit import Checks, script

from game import storm_of_silence as sos
from game import whirling_death as wd
from game.attached_units import attach, can_attach
from game.coldstar import effective_movement_in
from game.factions import aeldari as ae
from game.factions import orks
from game.factions import tau_empire as tau
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Jain Zar")


def jain_zar(owner="Player 1", name="1 Jain Zar 1"):
    return tk.build(ae.JAIN_ZAR, owner, name=name)


def banshees(owner="Player 1", name="1 Howling Banshees 1"):
    return tk.build(ae.HOWLING_BANSHEES, owner, name=name)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

sq = jain_zar()
p = sq.models[0].profile
checks.eq("one model", len(sq.models), 1)
checks.eq("105 points", sq.points, 105)
checks.eq("M8\"", p.movement_in, 8)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv2+", p.armor_save, "2+")
checks.eq("W5", p.wounds, 5)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("4+ invulnerable", p.invulnerable_save, "4+")
checks.eq("WS/BS 2+", (p.weapon_skill, p.ballistic_skill), ("2+", "2+"))
checks.eq("40 mm base", round(p.base_radius_in, 3), round(40 / 2 / 25.4, 3))
checks.true("LEADER, from her CORE line", p.leader)
checks.true("Fights First (24.13), likewise", p.fights_first)
checks.true("Battle Focus", p.battle_focus)
checks.true("Whirling Death", p.whirling_death)
checks.true("Storm of Silence", p.storm_of_silence)
for kw in ("INFANTRY", "CHARACTER", "EPIC HERO", "PHOENIX LORD", "JAIN ZAR"):
    checks.true(f"keyword {kw}", kw in ae.JAIN_ZAR.keywords)


# --- 2. weapons ------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("loadout", sorted(w.name for w in sq.models[0].weapons),
          ["Blade of Destruction", "Silent Death"])
gun = next(w for w in sq.models[0].weapons if w.weapon_type == RANGED)
checks.eq("Silent Death 12\"/A6/S6/AP-2/D1",
          (gun.range_in, gun.attacks, gun.strength, gun.ap, gun.damage), (12, 6, 6, -2, 1))
blade = next(w for w in sq.models[0].weapons if w.weapon_type == MELEE)
checks.eq("Blade of Destruction A8/S6/AP-3/D2",
          (blade.attacks, blade.strength, blade.ap, blade.damage), (8, 6, -3, 2))
# The two rows' keywords landed in BOTH columns and looked swapped, which is
# why it was queried rather than guessed: each carries its own, and only the
# gun carries two.
checks.true("Silent Death is [ASSAULT]", gun.assault)
checks.eq("...and [ANTI-INFANTRY 3+]", gun.anti, ("INFANTRY", 3))
checks.eq("the Blade is [ANTI-INFANTRY 3+] too", blade.anti, ("INFANTRY", 3))
checks.eq("...but NOT [ASSAULT] - a melee weapon could not be", blade.assault, False)


# --- 3. Leader (19.01) -----------------------------------------------------
print("--- 3. Leader ---")

checks.eq("she leads Howling Banshees", can_attach(jain_zar(), banshees()), [])
checks.true("and only them",
            bool(can_attach(jain_zar(), tk.build(ae.DIRE_AVENGERS, "Player 1", name="1 Dire Avengers 1"))))


# --- 4. Whirling Death -----------------------------------------------------
print("--- 4. Whirling Death ---")


def led_unit():
    body, lord = banshees(), jain_zar()
    tk.line_up(body, x=20.0, y=20.0)
    tk.line_up(lord, x=20.0, y=18.5)
    attach(lord, body)
    return body


led = led_unit()
checks.true("a led unit has the ability", wd.unit_has_jain_zar(led))
checks.eq("a plain Banshee squad does not", wd.unit_has_jain_zar(banshees()), False)
checks.eq("a lone Jain Zar leads nobody", wd.unit_has_jain_zar(jain_zar()), False)

from game.game_state import GameState  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.turn import PHASE_MOVEMENT  # noqa: E402


def advance_scene(unit):
    state = GameState()
    for model in unit.models:
        state.add_token(model)
    tracker = tk._tracker(PHASE_MOVEMENT, "Player 1")
    log, dice = tk.Log(), tk.RecordingDice()
    mover = MovementController(obstacles=[], game_log=log, player_name="Player 1",
                               turn_tracker=tracker, all_tokens=state.tokens, dice_manager=dice)
    mover.select(unit.models[0])
    mover.start_move()
    return dict(state=state, unit=unit, move=mover, dice=dice, log=log)


# The control first, so the difference below is attributable.
plain = banshees(name="1 Howling Banshees 2")
tk.line_up(plain, x=40.0, y=20.0)
control = advance_scene(plain)
before = control["move"].remaining_range[plain.models[0].id]
script(3)
control["move"].start_run()
checks.true("an ordinary unit ROLLS its Advance", control["dice"].is_pending)
checks.eq("...and gets what it rolled",
          control["move"].remaining_range[plain.models[0].id] - before, 3)

sc = advance_scene(led_unit())
unit = sc["unit"]
before = sc["move"].remaining_range[unit.models[0].id]
script(3)   # queued but must NOT be consumed
sc["move"].start_run()
checks.eq("with Whirling Death, NO Advance die is thrown", sc["dice"].is_pending, False)
checks.eq("...the scripted die is still unconsumed", tk.scripted(), [3])
checks.eq("and the unit gets a flat 6\"",
          sc["move"].remaining_range[unit.models[0].id] - before, wd.WHIRLING_DEATH_MOVE_BONUS_IN)
checks.true("the Advance is still recorded as used", sc["move"].run_used)
checks.eq("...and its bonus recorded for the phase",
          sc["move"].advance_bonus_by_squad[unit], wd.WHIRLING_DEATH_MOVE_BONUS_IN)
checks.true("the log says it was not rolled",
            any("Whirling Death" in line and "no roll" in line for line in sc["log"].lines))
# Rule 15.02 has nothing to correct, so the pending-advance fixup must be unset.
checks.eq("no pending Advance die to be Command Re-rolled", sc["move"]._pending_advance, None)

# The Move CHARACTERISTIC itself is what the rule raises, so the engine's own
# lookup has to see it - and only after the Advance, not merely from being led.
fresh = led_unit()
checks.eq("being led alone does not raise the Move characteristic",
          effective_movement_in(fresh.models[0]), 8)
checks.eq("...but having Advanced does",
          effective_movement_in(unit.models[0]), 8 + wd.WHIRLING_DEATH_MOVE_BONUS_IN)
wd.reset_phase([unit])
checks.eq("and it expires at end of phase", effective_movement_in(unit.models[0]), 8)


# --- 5. Storm of Silence ---------------------------------------------------
print("--- 5. Storm of Silence ---")

lord = jain_zar()
character_target = tk.build(orks.WARBOSS, "Player 2", name="2 Warboss 1")
plain_target = tk.build(orks.BOYZ, "Player 2", name="2 Boyz 1")
checks.true("the Warboss datasheet really is a CHARACTER", "CHARACTER" in orks.WARBOSS.keywords)
checks.eq("...and Boyz are not", "CHARACTER" in orks.BOYZ.keywords, False)

checks.true("her attack on a CHARACTER unit qualifies", sos.applies(lord.models[0], character_target))
checks.eq("on a non-CHARACTER unit it does not", sos.applies(lord.models[0], plain_target), False)
checks.eq("another model's attack never qualifies",
          sos.applies(banshees().models[0], character_target), False)
# 19.03: a squad with a character attached IS a CHARACTER unit.
merged = tk.build(orks.BOYZ, "Player 2", name="2 Boyz 2")
boss = tk.build(orks.WARBOSS, "Player 2", name="2 Warboss 2")
tk.line_up(merged, x=20.0, y=30.0)
tk.line_up(boss, x=20.0, y=28.5)
attach(boss, merged)
checks.true("a squad with a character attached counts (19.03)", sos.applies(lord.models[0], merged))

# The FIGHT side, which had no wound-reroll lookup at all before this.
fight = tk.fight_scene(ae.JAIN_ZAR, orks.WARBOSS, attacker_owner="Player 1")
fc = fight["fight"]
fc.select_to_fight(fight["attacker"])
if fc.state == "choosing_target":
    fc.choose_target_squad(fight["target"])
groups = fc.weapon_eligibility()
checks.true("she has a melee group", bool(groups))
# 8 attacks at WS2+: seven hits and a miss, then wound dice with failures in
# them so the offer has something to throw.
script(*([4] * 7 + [1] + [4] * 4 + [1] * 3), default=1)
fc.choose_weapon(groups[0][0])
fight["dice"].acknowledge()
fc.on_dice_acknowledged()
fight["dice"].acknowledge()
fc.on_dice_acknowledged()
checks.true("the wound re-roll is offered in the Fight phase", fight["decision"].is_pending)
prompt = fight["decision"].prompt
labels = [o["label"] for o in fight["decision"].options]
checks.true("...naming the ability", sos.STORM_OF_SILENCE_LABEL in prompt)
checks.true("...offering the whole roll", any(l.startswith("Re-roll the whole Wound roll") for l in labels))
checks.true("...and the failures-only subset of it",
            any(l.startswith("Re-roll failed wound rolls") for l in labels))
checks.true("...and a way to decline", any(l == "Keep result" for l in labels))
tk.pick_option(fight["decision"], "Keep result")

# Against a non-CHARACTER target, nothing is offered - so the result above is
# attributable to the ability and not to something else in the fight step.
plain_fight = tk.fight_scene(ae.JAIN_ZAR, orks.BOYZ, attacker_owner="Player 1")
pf = plain_fight["fight"]
pf.select_to_fight(plain_fight["attacker"])
if pf.state == "choosing_target":
    pf.choose_target_squad(plain_fight["target"])
script(*([4] * 7 + [1] + [4] * 4 + [1] * 3), default=1)
pf.choose_weapon(pf.weapon_eligibility()[0][0])
plain_fight["dice"].acknowledge()
pf.on_dice_acknowledged()
plain_fight["dice"].acknowledge()
pf.on_dice_acknowledged()
checks.eq("no offer against a non-CHARACTER unit", plain_fight["decision"].is_pending, False)

# ...and the SHOOTING side reaches the same lookup.
shoot = tk.shooting_scene(ae.JAIN_ZAR, orks.WARBOSS, attacker_owner="Player 1", gap=6.0)
shoot["shooting"].start_shooting(shoot["attacker"])
shoot["shooting"].choose_target_squad(shoot["target"])
key = next(r[0] for r in shoot["shooting"].weapon_eligibility() if r[1] == "Silent Death")
script(*([4] * 6 + [4, 4, 4, 1, 1, 1]), default=1)
shoot["shooting"].choose_weapon(key)
for _ in range(4):
    if shoot["decision"].is_pending:
        break
    if shoot["dice"].is_pending:
        shoot["dice"].acknowledge()
        shoot["shooting"].on_dice_acknowledged()
checks.true("the same offer appears in the Shooting phase", shoot["decision"].is_pending)
checks.true("...naming the ability", sos.STORM_OF_SILENCE_LABEL in shoot["decision"].prompt)


# --- 6. sprite -------------------------------------------------------------
print("--- 6. sprite ---")

checks.eq("Jain Zar art", _squad_key(sq.models[0]), "JainZar")


# --- 7. A/B probes ---------------------------------------------------------
print("--- 7. A/B probes ---")

original = wd.unit_has_jain_zar
wd.unit_has_jain_zar = lambda squad: False
probe = advance_scene(led_unit())
before = probe["move"].remaining_range[probe["unit"].models[0].id]
script(3)
probe["move"].start_run()
checks.true("A/B: without the lookup the Advance is rolled again", probe["dice"].is_pending)
checks.eq("A/B: ...and the die is consumed", tk.scripted(), [])
wd.unit_has_jain_zar = original

original_sos = sos.applies
sos.applies = lambda model, target: False
probe2 = tk.fight_scene(ae.JAIN_ZAR, orks.WARBOSS, attacker_owner="Player 1")
p2 = probe2["fight"]
p2.select_to_fight(probe2["attacker"])
if p2.state == "choosing_target":
    p2.choose_target_squad(probe2["target"])
script(*([4] * 7 + [1] + [4] * 4 + [1] * 3), default=1)
p2.choose_weapon(p2.weapon_eligibility()[0][0])
probe2["dice"].acknowledge()
p2.on_dice_acknowledged()
probe2["dice"].acknowledge()
p2.on_dice_acknowledged()
checks.eq("A/B: unwired, the melee wound re-roll is never offered",
          probe2["decision"].is_pending, False)
sos.applies = original_sos

checks.finish()
