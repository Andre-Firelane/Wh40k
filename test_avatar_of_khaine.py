"""Avatar of Khaine: datasheet data, Molten Form, The Bloody-Handed - and the
first weapon keyword here whose value is a DIE.

Three things are new infrastructure rather than datasheet data, so each is read
back through the code the ENGINE runs, not through its own predicate:

  * [SUSTAINED HITS D3] - one die per critical hit, as a real visible roll, in
    BOTH phases. Checked by counting the dice the next step throws.
  * Molten Form - the first halving in this engine, hooked at both places
    DamageAllocationSession settles an amount, and before Feel No Pain.
  * The Bloody-Handed - the first aura that modifies a ROLL, folded with War
    Horde's 'Ere We Go into game/roll_bonus.py. Checked through the real
    Advance and Charge roll sites, including that the two sources stack.
"""

import copy

import testkit as tk
from testkit import Checks, script

from game import bloody_handed as bh
from game import molten_form as mf
from game import roll_bonus
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Avatar of Khaine")


def avatar(owner="Player 1", name="1 Avatar of Khaine 1"):
    return tk.build(ae.AVATAR_OF_KHAINE, owner, name=name)


def guardians(owner="Player 1", name="1 Guardian Defenders 1"):
    return tk.build(ae.GUARDIAN_DEFENDERS, owner, name=name)


# --- 1. statline, keywords, points, weapons --------------------------------
print("--- 1. statline, keywords, points, weapons ---")

sq = avatar()
p = sq.models[0].profile
checks.eq("one model", len(sq.models), 1)
checks.eq("250 points", sq.points, 250)
checks.eq("M10\"", p.movement_in, 10)
checks.eq("T11", p.toughness, 11)
checks.eq("Sv2+", p.armor_save, "2+")
checks.eq("W14", p.wounds, 14)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC5", p.oc, 5)
checks.eq("4+ invulnerable", p.invulnerable_save, "4+")
checks.eq("WS/BS 2+", (p.weapon_skill, p.ballistic_skill), ("2+", "2+"))
checks.eq("80 mm base", round(p.base_radius_in, 3), round(80 / 2 / 25.4, 3))
checks.true("MONSTER", p.monster)
checks.eq("Damaged: 1-5 wounds remaining", p.damaged_threshold, 5)
checks.eq("Deadly Demise D3, rolled for real", p.deadly_demise_notation.sides, 3)
checks.true("Battle Focus", p.battle_focus)
checks.true("Molten Form", p.molten_form)
checks.true("The Bloody-Handed", p.bloody_handed)
for kw in ("MONSTER", "CHARACTER", "EPIC HERO", "DAEMON"):
    checks.true(f"keyword {kw}", kw in ae.AVATAR_OF_KHAINE.keywords)
# The largest INFANTRY-scale base here: the 80 mm base out-sizes every other
# Aeldari model except the two grav-tanks. Those are excluded because their
# radius is NOT their printed base - the Falcon's was matched to the Devilfish's
# enlarged one on user request ("genau so gross machen wie devilfish"), and the
# Wave Serpent then took the same value because it is the same hull. Both are
# named rather than filtered by keyword: the War Walker is a VEHICLE too and
# does keep its printed 60 mm, so it belongs in the comparison.
_GRAV_TANKS = (ae.FALCON, ae.WAVE_SERPENT)
biggest = max((tk.build(s, "Player 1", name=f"1 {s.name} 1").models[0].profile
               for s in ae.AELDARI.datasheets.values()
               if s is not ae.AVATAR_OF_KHAINE and s not in _GRAV_TANKS),
              key=lambda q: q.base_radius_in)
checks.true("the largest base in the faction bar the two grav-tanks",
            p.base_radius_in > biggest.base_radius_in)
# No LEADER line at all - so nothing attaches in either direction.
from game.attached_units import attachment_role, can_attach  # noqa: E402

checks.eq("he is not a leader unit", attachment_role(sq), None)
checks.true("...so he cannot be attached to anything",
            bool(can_attach(avatar(), guardians())))

checks.eq("three printed rows of ONE weapon",
          sorted(w.name for w in sq.models[0].weapons),
          ["The Wailing Doom", "The Wailing Doom - Strike", "The Wailing Doom - Sweep"])
gun = next(w for w in sq.models[0].weapons if w.weapon_type == RANGED)
strike = next(w for w in sq.models[0].weapons if w.name.endswith("Strike"))
sweep = next(w for w in sq.models[0].weapons if w.name.endswith("Sweep"))
checks.eq("ranged 12\"/A1/S16/AP-4", (gun.range_in, gun.attacks, gun.strength, gun.ap), (12, 1, 16, -4))
checks.eq("...D6+2 damage, rolled",
          (gun.damage_notation.sides, gun.damage_notation.bonus), (6, 2))
checks.eq("Strike A6/S16/AP-4", (strike.attacks, strike.strength, strike.ap), (6, 16, -4))
checks.eq("...also D6+2", (strike.damage_notation.sides, strike.damage_notation.bonus), (6, 2))
checks.eq("Sweep A12/S8/AP-2/D2",
          (sweep.attacks, sweep.strength, sweep.ap, sweep.damage), (12, 8, -2, 2))
checks.eq("Sweep's damage is a flat value, not a die", sweep.damage_notation, None)
# Strike-or-Sweep needs no mode machinery: 04.01 makes it a choice already.
checks.eq("neither melee row has [EXTRA ATTACKS] - so 04.01 forces a choice",
          (strike.extra_attacks, sweep.extra_attacks), (False, False))


# --- 2. [SUSTAINED HITS D3] ------------------------------------------------
print("--- 2. [SUSTAINED HITS D3] ---")

checks.eq("the value is a D3, not a number", gun.sustained_hits_notation.sides, 3)
checks.true("...and the plain field is only a placeholder", gun.sustained_hits > 0)
# The Aspect Shrine / Branching Fates gate must see that a crit is worth having.
from game import unmodified_six  # noqa: E402

checks.true("a critical hit is worth something on this weapon",
            unmodified_six.crit_matters_on_hit(gun))
bare = copy.copy(gun)
bare.sustained_hits = 0
bare.sustained_hits_notation = None
checks.eq("...and not on the same weapon stripped of both fields",
          unmodified_six.crit_matters_on_hit(bare), False)


def activation(melee, crits_wanted, melee_weapon_patch=None):
    """Run one activation whose hit roll produces `crits_wanted` critical hits
    and report every roll the ENGINE threw, plus the log.

    `melee_weapon_patch` grants a field to the chosen melee weapon INSTANCE
    before the activation - build_squad() gives every model its own instances,
    so this cannot leak into another test (the shared-class trap this repo
    documents)."""
    if melee:
        sc = tk.fight_scene(ae.AVATAR_OF_KHAINE, tau.STRIKE_TEAM, attacker_owner="Player 1")
        ctrl = sc["fight"]
    else:
        sc = tk.shooting_scene(ae.AVATAR_OF_KHAINE, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
        ctrl = sc["shooting"]
    if melee_weapon_patch is not None:
        for model in sc["attacker"].models:
            for w in model.weapons:
                if w.weapon_type == MELEE and w.name.endswith("Strike"):
                    for field, value in melee_weapon_patch.items():
                        setattr(w, field, value)
    script(*([6] * crits_wanted), default=1)
    if melee:
        ctrl.select_to_fight(sc["attacker"])
        if ctrl.state == "choosing_target":
            ctrl.choose_target_squad(sc["target"])
    else:
        ctrl.start_shooting(sc["attacker"])
        ctrl.choose_target_squad(sc["target"])
    rows = ctrl.weapon_eligibility()
    ctrl.choose_weapon(rows[0][0])
    for _ in range(10):
        if not sc["dice"].is_pending:
            break
        sc["dice"].acknowledge()
        ctrl.on_dice_acknowledged()
    return sc


def sustained_rolls(sc):
    return [(label, vals) for label, vals in sc["dice"].rolled if "SUSTAINED HITS" in label]


# SHOOTING: one die per critical hit, as its own labelled, visible roll.
sc1 = activation(False, 1)
rolls = sustained_rolls(sc1)
checks.eq("shooting: exactly one [SUSTAINED HITS] roll happened", len(rolls), 1)
checks.eq("...labelled with the die, not a number", "[SUSTAINED HITS D3]" in rolls[0][0], True)
checks.eq("...one die for one critical hit", len(rolls[0][1]), 1)
checks.true("...all dice are D3 results", all(1 <= v <= 3 for v in rolls[0][1]))
# The extra hits reach the NEXT step: the wound roll throws hits + sustained.
wound = next(vals for label, vals in sc1["dice"].rolled if label.startswith("Wound Roll"))
checks.eq("the wound roll sees the real hit plus the sustained one", len(wound), 2)
checks.true("...and the log says so",
            any("[SUSTAINED HITS] adds" in line for line in sc1["log"].lines))

# THE MELEE ROWS HAVE NO [SUSTAINED HITS] AT ALL - so nothing must be rolled.
# That is the datasheet, not a gap: only the ranged row prints it.
sc2 = activation(True, 3)
checks.eq("fight: his melee rows roll nothing for it", sustained_rolls(sc2), [])

# But the FIGHT-side wiring has to work, or a future melee weapon with a dice
# value would silently take the placeholder. Granted to the weapon instance.
sc3 = activation(True, 3, melee_weapon_patch={
    "sustained_hits": 1, "sustained_hits_notation": gun.sustained_hits_notation})
rolls3 = sustained_rolls(sc3)
checks.eq("fight: with the notation granted, one roll happens", len(rolls3), 1)
checks.eq("...with one die per critical hit (3)", len(rolls3[0][1]), 3)
wound3 = next(vals for label, vals in sc3["dice"].rolled if label.startswith("Wound Roll"))
checks.eq("...and the wound roll sees 3 real hits plus the sustained total",
          len(wound3), 3 + sum(rolls3[0][1]))


# --- 3. Molten Form --------------------------------------------------------
print("--- 3. Molten Form ---")

checks.true("he halves damage", mf.halves_damage(sq.models[0]))
checks.eq("a Guardian does not", mf.halves_damage(guardians().models[0]), False)
checks.eq("no model degrades safely", mf.halves_damage(None), False)
# Rounding UP, so Damage 1 is untouched and only 2+ is actually reduced.
for amount, expected in ((0, 0), (1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (6, 3), (8, 4)):
    checks.eq(f"Damage {amount} -> {expected}", mf.adjusted_damage(sq.models[0], amount), expected)
checks.eq("a model without the ability is untouched", mf.adjusted_damage(guardians().models[0], 6), 6)

# Read back through the REAL session, on both of the two paths that settle an
# amount: a flat Damage characteristic and a rolled one.
from game.damage_resolution import DamageAllocationSession  # noqa: E402


def wounds_lost(target, amount, weapon, script_values=()):
    if script_values:
        script(*script_values, default=1)
    dice = tk.RecordingDice()
    log = tk.Log()
    session = DamageAllocationSession([1], weapon, target, dice_manager=dice, log=log.add)
    for _ in range(6):
        if session.done:
            break
        if session.pending_choice is not None:
            # Driven directly, without a controller - the same standalone-session
            # pattern test_sunforge.py uses, since what is under test is the
            # arithmetic and not the controller's completion bookkeeping.
            session.choose_model(session.pending_choice[0])
        elif dice.is_pending:
            dice.acknowledge()
            session.on_damage_roll_acknowledged()
        else:
            break
    before = sum(m.profile.wounds for m in target.models)
    return before - sum(m.current_wounds for m in target.models), log.lines


flat = copy.copy(sweep)          # a flat Damage 2 melee row
flat.damage = 4
him = avatar(name="1 Avatar of Khaine 2")
lost, lines = wounds_lost(him, 4, flat)
checks.eq("a flat Damage 4 attack costs him 2 wounds", lost, 2)
checks.true("...and says so", any("Molten Form" in line for line in lines))

# A W12 Falcon, not a W3 Wraithguard: excess damage does not carry over, so
# against a 3-wound model a Damage 4 attack also only ever costs 3 and the
# control would silently agree with the halved case for the wrong reason.
other = tk.build(ae.FALCON, "Player 1", name="1 Falcon 1")
lost_other, _ = wounds_lost(other, 4, flat)
checks.eq("the same attack costs a unit without the ability the full 4", lost_other, 4)

him2 = avatar(name="1 Avatar of Khaine 3")
rolled_lost, rolled_lines = wounds_lost(him2, None, gun, script_values=(6,))
checks.true("a ROLLED Damage characteristic is halved too - the other path",
            any("Molten Form" in line for line in rolled_lines))
checks.eq("D6+2 rolling a 6 is 8, halved to 4", rolled_lost, 4)


# --- 4. The Bloody-Handed --------------------------------------------------
print("--- 4. The Bloody-Handed ---")

checks.eq("range is 6\"", bh.BLOODY_HANDED_RANGE_IN, 6.0)
checks.eq("the bonus is +1", bh.BLOODY_HANDED_ROLL_BONUS, 1)

near = guardians(name="1 Guardian Defenders 2")
far = guardians(name="1 Guardian Defenders 3")
lord = avatar(name="1 Avatar of Khaine 4")
tk.line_up(lord, x=20.0, y=20.0)
tk.line_up(near, x=20.0, y=24.0)     # 4" away
tk.line_up(far, x=20.0, y=40.0)      # 20" away
tokens = list(lord.models) + list(near.models) + list(far.models)

checks.eq("a unit within 6\" gets +1", bh.roll_bonus(near, tokens), 1)
checks.eq("one outside gets nothing", bh.roll_bonus(far, tokens), 0)
checks.eq("his own unit gets it too - the aura prints no 'excluding this unit'",
          bh.roll_bonus(lord, tokens), 1)
enemy = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 1")
tk.line_up(enemy, x=20.0, y=23.0)
checks.eq("an enemy unit 3\" away gets nothing",
          bh.roll_bonus(enemy, tokens + list(enemy.models)), 0)
friendly_non_aeldari = tk.build(tau.STRIKE_TEAM, "Player 1", name="1 Strike Team 2")
tk.line_up(friendly_non_aeldari, x=20.0, y=23.0)
checks.eq("a friendly NON-AELDARI unit gets nothing",
          bh.roll_bonus(friendly_non_aeldari, tokens + list(friendly_non_aeldari.models)), 0)
checks.eq("with no board it degrades to 0 rather than guessing", bh.roll_bonus(near, None), 0)
for m in lord.models:
    m.current_wounds = 0
checks.eq("a dead Avatar projects nothing", bh.roll_bonus(near, tokens), 0)


# --- 5. the folded roll bonus, read at both real roll sites ----------------
print("--- 5. the folded roll bonus ---")

from game.charge import ChargeController  # noqa: E402
from game.movement import MovementController, advance_total  # noqa: E402
from game.turn import PHASE_CHARGE, PHASE_MOVEMENT  # noqa: E402

lord2 = avatar(name="1 Avatar of Khaine 5")
buffed = guardians(name="1 Guardian Defenders 4")
tk.line_up(lord2, x=20.0, y=20.0)
tk.line_up(buffed, x=20.0, y=24.0)
tokens2 = list(lord2.models) + list(buffed.models)

checks.eq("no aura in reach: the Advance roll is just the die",
          advance_total(buffed, [3], None), 3)
checks.eq("with the aura: +1", advance_total(buffed, [3], tokens2), 4)
# The two sources STACK - they are separate modifiers to the same roll.
buffed.ere_we_go_active = True
checks.eq("'Ere We Go and the aura stack", advance_total(buffed, [3], tokens2), 6)
checks.eq("...and roll_bonus names both",
          sorted(label for label, _ in roll_bonus.sources(buffed, tokens2)),
          ["'Ere We Go", "The Bloody-Handed"])
buffed.ere_we_go_active = False

# And the Charge roll, through _capped_roll - which is also where rule 15.11's
# cap sits, so the bonus has to land BEFORE it.
log = tk.Log()
tt = tk._tracker(PHASE_CHARGE, owner="Player 1")
charge = ChargeController(turn_tracker=tt, all_tokens=tokens2, game_log=log)
charge.active_squad = buffed
total, note = charge._capped_roll(7)
checks.eq("a Charge roll of 7 becomes 8", total, 8)
checks.true("...and the note says why", "Bloody-Handed" in note)
charge._mode = "into_the_fray"
capped, _ = charge._capped_roll(6)
checks.eq("the bonus lands BEFORE 15.11's cap, so 6+1 caps to 6", capped, 6)


# --- 6. sprite -------------------------------------------------------------
print("--- 6. sprite ---")

checks.eq("his own art", _squad_key(avatar().models[0]), "Avatar")


# --- 7. A/B probes ---------------------------------------------------------
print("--- 7. A/B probes ---")

probe = avatar(name="1 Avatar of Khaine 9")
for m in probe.models:
    m.profile = copy.copy(m.profile)
    m.profile.molten_form = False
lost_probe, probe_lines = wounds_lost(probe, 4, flat)
checks.eq("A/B: without Molten Form the full 4 lands", lost_probe, 4)
checks.eq("...and nothing is logged", [l for l in probe_lines if "Molten Form" in l], [])

probe2 = avatar(name="1 Avatar of Khaine 10")
buffed2 = guardians(name="1 Guardian Defenders 9")
tk.line_up(probe2, x=30.0, y=20.0)
tk.line_up(buffed2, x=30.0, y=24.0)
tokens3 = list(probe2.models) + list(buffed2.models)
checks.eq("A/B: with the aura, +1", advance_total(buffed2, [3], tokens3), 4)
for m in probe2.models:
    m.profile = copy.copy(m.profile)
    m.profile.bloody_handed = False
checks.eq("A/B: without it, just the die", advance_total(buffed2, [3], tokens3), 3)

checks.finish()
