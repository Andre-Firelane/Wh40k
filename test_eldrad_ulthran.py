"""Eldrad Ulthran: datasheet data, the LEADER clause that finally reaches
Protect, Doom, and Diviner of Futures.

The headline is section 3. Protect has been sitting inert on the Warlock
Conclave through two datasheets that were each expected to bring it to life,
and the thing that actually does is not on that ability at all - it is the
second sentence of THIS model's LEADER line. So the whole chain gets pinned
here: that the attachment is legal, that the direction of the permission
matters, that protect.applies() then fires, and that the -1 reaches the wound
roll in both phases.

Doom is Guide's twin one word apart, so what is tested is what is NOT shared:
it modifies the wound roll rather than the hit roll, and it prints no
once-per-turn cap. The mark machinery itself (duration, army-wide scope,
selection criteria) belongs to game/psychic_mark.py and is covered through
Guide in test_farseer.py; the two-marks-at-once case is checked here because
only this datasheet makes it possible.
"""

import copy

import testkit as tk
from testkit import Checks

from game import diviner_of_futures as dof
from game import doom as dm
from game import guide as gd
from game import protect
from game.attached_units import attach, can_attach
from game.command_points import BONUS_CP_PER_ROUND_CAP, CommandPointManager
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Eldrad Ulthran")
LINE = "Eldrad Ulthran"


def eldrad(owner="Player 1", name="1 Eldrad Ulthran 1"):
    return tk.build(ae.ELDRAD_ULTHRAN, owner, name=name)


def guardians(owner="Player 1", name="1 Guardian Defenders 1"):
    return tk.build(ae.GUARDIAN_DEFENDERS, owner, name=name)


def conclave(owner="Player 1", name="1 Warlock Conclave 1"):
    return tk.build(ae.WARLOCK_CONCLAVE, owner, name=name)


# --- 1. statline, keywords, points, weapons --------------------------------
print("--- 1. statline, keywords, points, weapons ---")

sq = eldrad()
p = sq.models[0].profile
checks.eq("one model", len(sq.models), 1)
checks.eq("130 points", sq.points, 130)
checks.eq("M7\"", p.movement_in, 7)
checks.eq("T4", p.toughness, 4)
checks.eq("Sv6+", p.armor_save, "6+")
checks.eq("W5", p.wounds, 5)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("4+ invulnerable", p.invulnerable_save, "4+")
checks.eq("WS/BS 2+", (p.weapon_skill, p.ballistic_skill), ("2+", "2+"))
checks.eq("32 mm base", round(p.base_radius_in, 3), round(32 / 2 / 25.4, 3))
# Tougher and more wounds than the plain Farseer, whose numbers he is otherwise
# close to - pinned so a copy-paste from that profile would fail.
fp = tk.build(ae.FARSEER, "Player 1", name="1 Farseer 1").models[0].profile
checks.true("tougher than the plain Farseer", p.toughness > fp.toughness)
checks.true("...and more wounds", p.wounds > fp.wounds)
checks.true("...on a bigger base", p.base_radius_in > fp.base_radius_in)
for kw in ("INFANTRY", "CHARACTER", "EPIC HERO", "PSYKER", "FARSEER"):
    checks.true(f"keyword {kw}", kw in ae.ELDRAD_ULTHRAN.keywords)
checks.true("FARSEER on the profile too - Protect reads this", p.farseer)
checks.true("PSYKER - so he feeds Psychic Guidance/Communion as well", p.psyker)
checks.true("Battle Focus", p.battle_focus)
checks.eq("he has Doom, not Guide", (p.doom, p.guide), (True, False))
checks.true("Diviner of Futures", p.diviner_of_futures)
checks.true("the LEADER-line clause", p.joins_warlock_led_unit)

checks.eq("loadout", sorted(w.name for w in sq.models[0].weapons),
          ["Mind War", "Shuriken Pistol", "Staff of Ulthamar and Witchblade"])
mind = next(w for w in sq.models[0].weapons if w.name == "Mind War")
checks.eq("Mind War 18\"/A1/S5/AP-2",
          (mind.range_in, mind.attacks, mind.strength, mind.ap), (18, 1, 5, -2))
checks.eq("...D6 damage, rolled", mind.damage_notation.sides, 6)
checks.eq("...[ANTI-CHARACTER 4+]", mind.anti, ("CHARACTER", 4))
checks.true("...[PRECISION] - the pairing is the point", mind.precision)
checks.true("...[PSYCHIC]", mind.psychic)
staff = next(w for w in sq.models[0].weapons if w.weapon_type == MELEE)
checks.eq("the staff is ONE printed row", staff.name, "Staff of Ulthamar and Witchblade")
checks.eq("...Melee/A3/S5/AP-1/D2",
          (staff.attacks, staff.strength, staff.ap, staff.damage), (3, 5, -1, 2))
checks.eq("...[ANTI-INFANTRY 2+]", staff.anti, ("INFANTRY", 2))
# Deliberately NOT the shared Witchblade, which is A2/S3/AP0.
from game.weapons import ShurikenPistolProfile, WitchbladeProfile  # noqa: E402

checks.true("the staff is not the shared Witchblade",
            (staff.attacks, staff.strength, staff.ap)
            != (WitchbladeProfile.attacks, WitchbladeProfile.strength, WitchbladeProfile.ap))
checks.true("the Shuriken Pistol IS shared, BS deferred to the model",
            any(w is ShurikenPistolProfile or isinstance(w, ShurikenPistolProfile)
                for w in sq.models[0].weapons))
checks.eq("...so it defers BS", ShurikenPistolProfile.ballistic_skill, None)


# --- 2. the LEADER line, and the direction of its permission ---------------
print("--- 2. the LEADER line ---")


def led_by_conclave(name_suffix="1"):
    """Guardians with a Warlock Conclave already attached - the state Eldrad's
    clause is about."""
    body = guardians(name=f"1 Guardian Defenders {name_suffix}")
    warlocks = conclave(name=f"1 Warlock Conclave {name_suffix}")
    tk.line_up(body, x=20.0, y=20.0)
    tk.line_up(warlocks, x=20.0, y=18.5)
    attach(warlocks, body)
    return body


checks.eq("he can lead Guardian Defenders", can_attach(eldrad(), guardians()), [])
checks.eq("...and Storm Guardians",
          can_attach(eldrad(), tk.build(ae.STORM_GUARDIANS, "Player 1", name="1 Storm Guardians 1")), [])
checks.true("but not a Warlock Conclave directly - it is itself a leader unit",
            bool(can_attach(eldrad(), conclave())))

# The new thing: second leader onto a Conclave-led unit.
body = led_by_conclave()
checks.eq("he may join a unit a WARLOCKS unit has already joined",
          can_attach(eldrad(), body), [])

# DIRECTION MATTERS. The permission is printed on him, so it must not work the
# other way round: a Conclave may not join a unit Eldrad already leads.
body2 = guardians(name="1 Guardian Defenders 2")
lord = eldrad(name="1 Eldrad Ulthran 2")
tk.line_up(body2, x=30.0, y=20.0)
tk.line_up(lord, x=30.0, y=18.5)
attach(lord, body2)
checks.true("but a Conclave may NOT join a unit Eldrad already leads",
            bool(can_attach(conclave(name="1 Warlock Conclave 9"), body2)))

# "even if ONE WARLOCKS unit" - one, and it must be WARLOCKS.
body3 = guardians(name="1 Guardian Defenders 3")
seer = tk.build(ae.FARSEER, "Player 1", name="1 Farseer 3")
tk.line_up(body3, x=40.0, y=20.0)
tk.line_up(seer, x=40.0, y=18.5)
attach(seer, body3)
checks.true("not a second leader behind a non-WARLOCKS one (a plain Farseer)",
            bool(can_attach(eldrad(name="1 Eldrad Ulthran 3"), body3)))

# And the permission is HIS, not every Farseer's.
body4 = led_by_conclave("4")
checks.true("a plain Farseer still cannot be the second leader",
            bool(can_attach(tk.build(ae.FARSEER, "Player 1", name="1 Farseer 4"), body4)))

# A third leader is refused even for him.
body5 = led_by_conclave("5")
attach(eldrad(name="1 Eldrad Ulthran 5"), body5)
checks.true("and no THIRD leader",
            bool(can_attach(eldrad(name="1 Eldrad Ulthran 6"), body5)))


# --- 3. what this unlocks: Protect goes live -------------------------------
print("--- 3. Protect goes live ---")

checks.eq("an unled Conclave has nothing", protect.applies(conclave()), False)
checks.eq("Guardians led only by a Conclave have nothing either",
          protect.applies(led_by_conclave("7")), False)

full = led_by_conclave("8")
attach(eldrad(name="1 Eldrad Ulthran 8"), full)
checks.true("Guardians + Conclave + Eldrad: Protect applies", protect.applies(full))
checks.true("...and the merged unit really holds all three components",
            len(full.attached_components) == 3)

# Read back out of the functions the ENGINE uses, in BOTH phases - the ability
# says "each time an attack targets this unit", not "ranged attack".
shoot = tk.shooting_scene(ae.FIRE_DRAGONS, ae.GUARDIAN_DEFENDERS, attacker_owner="Player 2", gap=6.0)
shoot["shooting"].active_squad = shoot["attacker"]
checks.eq("no Protect modifier against a plain Guardian squad",
          [m for m in shoot["shooting"]._wound_modifiers(shoot["target"]) if m.source == "Protect"], [])
checks.eq("...but +1 on the wound threshold against the Eldrad-led one",
          [(m.amount, m.source) for m in shoot["shooting"]._wound_modifiers(full)
           if m.source == "Protect"], [(1, "Protect")])

fight = tk.fight_scene(ae.FIRE_DRAGONS, ae.GUARDIAN_DEFENDERS, attacker_owner="Player 2")
fight["fight"].select_to_fight(fight["attacker"])
melee = next(w for w in fight["attacker"].models[0].weapons if w.weapon_type == MELEE)
checks.eq("the same in the Fight phase",
          [(m.amount, m.source) for m in fight["fight"]._wound_modifiers(melee, full)
           if m.source == "Protect"], [(1, "Protect")])
checks.eq("...and not against a plain squad there either",
          [m for m in fight["fight"]._wound_modifiers(melee, fight["target"]) if m.source == "Protect"], [])


# --- 4. Doom ---------------------------------------------------------------
print("--- 4. Doom ---")

log = tk.Log()
seer_unit = eldrad()
tk.line_up(seer_unit, x=20.0, y=20.0)
near = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 1")
far = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 2")
tk.line_up(near, x=20.0, y=28.0)      # ~8" away
tk.line_up(far, x=20.0, y=60.0)       # far beyond 18"
tokens = list(seer_unit.models) + list(near.models) + list(far.models)
ctrl = dm.DoomController(game_log=log, all_tokens=tokens)

checks.eq("range is 18\"", dm.DOOM_RANGE_IN, 18.0)
checks.eq("the bonus is a NEGATIVE amount - it improves the roll", dm.DOOM_WOUND_BONUS, -1)
checks.true("he carries it", ctrl.squad_has_ability(seer_unit))
checks.eq("a plain Farseer does not",
          ctrl.squad_has_ability(tk.build(ae.FARSEER, "Player 1", name="1 Farseer 9")), False)
names = [s.name for s in ctrl.candidates(seer_unit)]
checks.true("the near enemy is selectable", near.name in names)
checks.eq("the far one is not", far.name in names, False)

ctrl.mark("Player 1", near)
checks.true("the mark is held per PLAYER, army-wide", near in ctrl.marked_by("Player 1"))
checks.true("logged", any("Doom" in line for line in log.lines))
checks.true("a friendly AELDARI unit attacking it gets it",
            ctrl.applies_to_squad(seer_unit, near))
checks.eq("...but not against an unmarked unit", ctrl.applies_to_squad(seer_unit, far), False)
checks.eq("a non-AELDARI friendly unit gets nothing",
          ctrl.applies_to_squad(tk.build(tau.STRIKE_TEAM, "Player 1", name="1 Strike Team 3"), near), False)
checks.eq("and the enemy's own attacks get nothing",
          ctrl.applies_to_squad(near, near), False)

# THE DIFFERENCE FROM GUIDE: no once-per-turn cap is printed.
checks.eq("Doom prints no once-per-turn cap", dm.DoomController.once_per_turn, False)
checks.eq("...while Guide does", gd.GuideController.once_per_turn, True)
second = dm.DoomController(all_tokens=tokens)
second.mark("Player 1", near)
second._marks.pop("Player 1")   # clear only the mark, keep the "selected this turn" record
checks.true("so an already-selected unit stays selectable for Doom",
            near in second.candidates(seer_unit))
guide_ctrl = gd.GuideController(all_tokens=tokens)
guide_ctrl.mark("Player 1", near)
guide_ctrl._marks.pop("Player 1")
checks.eq("...where for Guide it would not be",
          near in guide_ctrl.candidates(seer_unit), False)

# Duration: it survives into the opponent's turn and dies at the start of the
# OWNER's next Command phase, not at end of turn.
ctrl.start_of_command_phase("Player 2")
checks.true("the opponent's Command phase does not clear it",
            near in ctrl.marked_by("Player 1"))
ctrl.start_of_command_phase("Player 1")
checks.eq("his own does", ctrl.marked_by("Player 1"), set())

# The -1 reaches the wound roll in both phases, read from the engine's own hook.
doomed_shoot = tk.shooting_scene(ae.GUARDIAN_DEFENDERS, tau.STRIKE_TEAM,
                                attacker_owner="Player 1", gap=6.0, doom=ctrl)
doomed_shoot["shooting"].active_squad = doomed_shoot["attacker"]
checks.eq("unmarked: no Doom modifier",
          [m for m in doomed_shoot["shooting"]._wound_modifiers(doomed_shoot["target"])
           if m.source == "Doom"], [])
ctrl.mark("Player 1", doomed_shoot["target"])
checks.eq("marked: -1 on the wound threshold",
          [(m.amount, m.source) for m in doomed_shoot["shooting"]._wound_modifiers(doomed_shoot["target"])
           if m.source == "Doom"], [(-1, "Doom")])

doomed_fight = tk.fight_scene(ae.GUARDIAN_DEFENDERS, tau.STRIKE_TEAM,
                             attacker_owner="Player 1", doom=ctrl)
doomed_fight["fight"].select_to_fight(doomed_fight["attacker"])
gmelee = next(w for w in doomed_fight["attacker"].models[0].weapons if w.weapon_type == MELEE)
checks.eq("unmarked in the Fight phase: nothing",
          [m for m in doomed_fight["fight"]._wound_modifiers(gmelee, doomed_fight["target"])
           if m.source == "Doom"], [])
ctrl.mark("Player 1", doomed_fight["target"])
checks.eq("marked in the Fight phase: -1 as well",
          [(m.amount, m.source) for m in doomed_fight["fight"]._wound_modifiers(gmelee, doomed_fight["target"])
           if m.source == "Doom"], [(-1, "Doom")])

# Both marks can be live at once, on different units - that is why they are two
# controllers rather than two modes of one.
# Fresh controllers, because `ctrl` above has been expired and re-marked onto
# the scene targets by now - depending on that history would test the test.
both_doom = dm.DoomController(all_tokens=tokens)
both_guide = gd.GuideController(all_tokens=tokens)
both_doom.mark("Player 1", near)
both_guide.mark("Player 1", far)
checks.true("Guide and Doom can hold different units at once",
            near in both_doom.marked_by("Player 1") and far in both_guide.marked_by("Player 1"))
checks.eq("...and neither leaks into the other",
          (far in both_doom.marked_by("Player 1"), near in both_guide.marked_by("Player 1")),
          (False, False))


# --- 5. Diviner of Futures -------------------------------------------------
print("--- 5. Diviner of Futures ---")

cp_log = tk.Log()
# CommandPointManager takes the Log OBJECT (it calls .add itself), unlike
# DamageAllocationSession which takes the callable.
cp = CommandPointManager(game_log=cp_log)
board = eldrad()
tk.line_up(board, x=20.0, y=20.0)
diviner = dof.DivinerOfFuturesController(
    command_points=cp, all_tokens=list(board.models), game_log=cp_log,
)
checks.eq("he is on the battlefield", len(dof.bearers_on_battlefield("Player 1", list(board.models))), 1)
before = cp.cp["Player 1"]
checks.eq("+1 CP at the start of his controller's Command phase",
          diviner.start_of_command_phase("Player 1"), 1)
checks.eq("...and the ledger moved", cp.cp["Player 1"] - before, 1)
checks.eq("the opponent gains nothing from it", diviner.start_of_command_phase("Player 2"), 0)

# The user's house-rule cap is enforced centrally, so a second bonus grant the
# same round lands 0 - this ability must not route around it.
checks.eq("cap is 1 bonus CP per battle round", BONUS_CP_PER_ROUND_CAP, 1)
checks.eq("a second grant the same round yields 0",
          cp.gain_cp("Player 1", None, amount=1, reason="something else"), 0)

# Not on the battlefield -> nothing, and no CP is spent looking.
off_board = dof.DivinerOfFuturesController(command_points=cp, all_tokens=[], game_log=cp_log)
checks.eq("in Reserves or embarked, he grants nothing",
          off_board.start_of_command_phase("Player 1"), 0)
dead = eldrad(name="1 Eldrad Ulthran 7")
tk.line_up(dead, x=20.0, y=20.0)
for m in dead.models:
    m.current_wounds = 0
checks.eq("a dead bearer grants nothing",
          len(dof.bearers_on_battlefield("Player 1", list(dead.models))), 0)
# Read per MODEL, not per squad: after 19.01 the unit can be alive while he is not.
merged = led_by_conclave("6")
attach(eldrad(name="1 Eldrad Ulthran 4"), merged)
his = [m for m in merged.models if getattr(m.profile, "diviner_of_futures", False)]
checks.eq("exactly one model in the merged unit carries it", len(his), 1)
for m in his:
    m.current_wounds = 0
checks.eq("...and with him dead the living unit grants nothing",
          len(dof.bearers_on_battlefield("Player 1", list(merged.models))), 0)


# --- 6. sprite -------------------------------------------------------------
print("--- 6. sprite ---")

checks.eq("his own art, under the folder's spelling",
          _squad_key(eldrad().models[0]), "Eldrad Ultran")
checks.eq("a plain Farseer is unaffected",
          _squad_key(tk.build(ae.FARSEER, "Player 1", name="1 Farseer 8").models[0]), "Farseer")


# --- 7. A/B probes ---------------------------------------------------------
print("--- 7. A/B probes ---")

# Without the LEADER-line flag the attachment is refused again - so section 2
# and the whole of section 3 hang on that clause and not on the scene.
probe_body = led_by_conclave("A")
probe_lord = eldrad(name="1 Eldrad Ulthran A")
for m in probe_lord.models:
    m.profile = copy.copy(m.profile)
    m.profile.joins_warlock_led_unit = False
checks.true("A/B: without the clause the second leader is refused",
            bool(can_attach(probe_lord, probe_body)))
checks.eq("A/B: restored", can_attach(eldrad(name="1 Eldrad Ulthran B"), probe_body), [])

# Without the doom flag there is no bearer, so nothing is selectable.
probe_seer = eldrad(name="1 Eldrad Ulthran C")
tk.line_up(probe_seer, x=20.0, y=20.0)
probe_tokens = list(probe_seer.models) + list(near.models)
probe_ctrl = dm.DoomController(all_tokens=probe_tokens)
checks.true("A/B: with the flag, a target is selectable", bool(probe_ctrl.candidates(probe_seer)))
for m in probe_seer.models:
    m.profile = copy.copy(m.profile)
    m.profile.doom = False
checks.eq("A/B: without it, none is", probe_ctrl.candidates(probe_seer), [])

checks.finish()
