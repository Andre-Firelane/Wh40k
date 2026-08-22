"""Warlock Conclave: datasheet data, Psychic Communion, Protect - and the
payoff for Wraithguard.

Two things get the depth here. Psychic Communion is the first aura in this
codebase that is answered PER MODEL rather than per unit, so the suite shows
two Warlocks of the same unit ending up with different bonuses. And this is the
first AELDARI PSYKER datasheet, which is what Wraithguard's Psychic Guidance
was waiting for - that was written as "inert today, and it will start firing on
its own when one exists", so the claim is checked rather than assumed.
"""

import testkit as tk
from testkit import Checks, script

from game import protect
from game import psychic_communion as pc
from game import psychic_guidance as pg
from game.attached_units import attach, can_attach
from game.factions import aeldari as ae
from game.factions import orks
from game.factions import tau_empire as tau
from game.leadership import leadership_threshold
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Warlock Conclave")
LINE = "Warlock"


def conclave(composition_index=0, choices=None, owner="Player 1", name="1 Warlock Conclave 1"):
    return tk.build(ae.WARLOCK_CONCLAVE, owner, name=name,
                    composition_index=composition_index, choices=choices)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

small, big = conclave(0), conclave(1)
checks.eq("2-model unit", len(small.models), 2)
checks.eq("4-model unit", len(big.models), 4)
checks.eq("2 models cost 55", small.points, 55)
checks.eq("4 models cost 120", big.points, 120)

p = small.models[0].profile
checks.eq("M7\"", p.movement_in, 7)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv6+", p.armor_save, "6+")
checks.eq("W2", p.wounds, 2)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("4+ invulnerable", p.invulnerable_save, "4+")
checks.eq("32 mm base", round(p.base_radius_in, 3), round(32 / 2 / 25.4, 3))
checks.true("INFANTRY", p.infantry)
checks.true("PSYKER", p.psyker)
checks.true("LEADER, from its CORE line", p.leader)
checks.true("Battle Focus", p.battle_focus)
checks.true("Psychic Communion", p.psychic_communion)
checks.true("Protect", p.protect)
for kw in ("INFANTRY", "PSYKER", "WARLOCKS", "WARLOCK CONCLAVE"):
    checks.true(f"keyword {kw}", kw in ae.WARLOCK_CONCLAVE.keywords)


# --- 2. weapons and wargear ------------------------------------------------
print("--- 2. weapons and wargear ---")

checks.eq("default loadout", sorted(w.name for w in small.models[0].weapons),
          ["Destructor", "Shuriken Pistol", "Witchblade"])
dest = next(w for w in small.models[0].weapons if w.name == "Destructor")
checks.eq("Destructor 12\"/S5/AP-1/D1, D6 attacks",
          (dest.range_in, dest.strength, dest.ap, dest.damage, dest.attacks_notation.sides),
          (12, 5, -1, 1, 6))
checks.true("[PSYCHIC]", dest.psychic)
# Independent of the name column: BS prints "N/A", which only [TORRENT] does.
checks.true("[TORRENT]", dest.torrent)
checks.eq("...so no BS override", dest.ballistic_skill, None)
# A targeted follow-up claimed [ASSAULT] on this weapon; the name column, which
# has been the reliable channel across eight datasheets, does not carry it.
checks.eq("NOT [ASSAULT] - the name column does not carry it", dest.assault, False)

pistol = next(w for w in small.models[0].weapons if w.name == "Shuriken Pistol")
checks.eq("the Shuriken Pistol is the existing shared profile",
          (pistol.range_in, pistol.strength, pistol.ap, pistol.assault, pistol.pistol),
          (12, 4, -1, True, True))

blade = next(w for w in small.models[0].weapons if w.name == "Witchblade")
checks.eq("Witchblade A2/S3/AP0/D2", (blade.attacks, blade.strength, blade.ap, blade.damage), (2, 3, 0, 2))
checks.true("[PSYCHIC]", blade.psychic)
checks.eq("[ANTI-INFANTRY 2+]", blade.anti, ("INFANTRY", 2))

speared = conclave(choices={LINE: {ae.WARLOCK_WITCHBLADE_TO_SPEAR: 2}})
checks.true("every model can swap to a Singing Spear",
            all(any(w.name == "Singing Spear" for w in m.weapons) for m in speared.models))
checks.true("...and none keeps a witchblade",
            not any(w.name == "Witchblade" for m in speared.models for w in m.weapons))
# One weapon, two printed rows - so the swap grants both profiles.
spear_types = sorted(w.weapon_type for w in speared.models[0].weapons if w.name == "Singing Spear")
checks.eq("the spear is granted as both a ranged and a melee profile", spear_types, [MELEE, RANGED])
spear_r = next(w for w in speared.models[0].weapons if w.name == "Singing Spear" and w.weapon_type == RANGED)
checks.eq("thrown: 12\"/S9/AP0/D3", (spear_r.range_in, spear_r.strength, spear_r.ap, spear_r.damage), (12, 9, 0, 3))
checks.true("...[ASSAULT] and [PSYCHIC]", spear_r.assault and spear_r.psychic)
spear_m = next(w for w in speared.models[0].weapons if w.name == "Singing Spear" and w.weapon_type == MELEE)
checks.eq("melee: A2/S3/AP0/D3", (spear_m.attacks, spear_m.strength, spear_m.ap, spear_m.damage), (2, 3, 0, 3))
checks.eq("...[PSYCHIC] but not [ASSAULT], which a melee weapon could not be",
          (spear_m.psychic, spear_m.assault), (True, False))


# --- 3. Leader (19.01) -----------------------------------------------------
print("--- 3. Leader ---")

for sheet in (ae.GUARDIAN_DEFENDERS, ae.STORM_GUARDIANS):
    checks.eq(f"it can lead {sheet.name}",
              can_attach(conclave(), tk.build(sheet, "Player 1", name=f"1 {sheet.name} 1")), [])
checks.true("and nothing else",
            bool(can_attach(conclave(), tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1"))))


# --- 4. Psychic Communion --------------------------------------------------
print("--- 4. Psychic Communion ---")

# Per MODEL, not per unit - so the two Warlocks of one squad are placed apart
# and only one of them has company.
unit = conclave(1)                      # 4 models
near, far = unit.models[0], unit.models[3]
near.x_in, near.y_in = 20.0, 20.0
unit.models[1].x_in, unit.models[1].y_in = 21.0, 20.0
unit.models[2].x_in, unit.models[2].y_in = 22.0, 20.0
far.x_in, far.y_in = 60.0, 60.0
tokens = list(unit.models)

checks.eq("the crowded Warlock counts 2 others within 6\" (capped)",
          pc.bonus_for(near, unit, tokens), pc.PSYCHIC_COMMUNION_MAX_BONUS)
checks.eq("the isolated one counts none", pc.bonus_for(far, unit, tokens), 0)
# "each OTHER" - a Warlock never counts itself.
solo = conclave(0)
solo.models[0].x_in, solo.models[0].y_in = 5.0, 5.0
solo.models[1].x_in, solo.models[1].y_in = 40.0, 40.0
checks.eq("a lone Warlock counts nobody, least of all itself",
          pc.bonus_for(solo.models[0], solo, list(solo.models)), 0)
# ...and the cap really is a cap.
checks.eq("three neighbours still only give +2", pc.bonus_for(near, unit, tokens), 2)

# Not just any psyker: the Ork Kill Rig is one, and it is not AELDARI.
ork = tk.build(orks.KILL_RIG, "Player 1", name="1 Kill Rig 1")
ork.models[0].x_in, ork.models[0].y_in = 60.5, 60.0
checks.true("the Kill Rig really is a PSYKER", ork.models[0].profile.psyker)
checks.eq("...but it is not AELDARI, so it grants nothing",
          pc.bonus_for(far, unit, tokens + list(ork.models)), 0)
# Nor an enemy one.
enemy = conclave(0, owner="Player 2", name="2 Warlock Conclave 1")
for m in enemy.models:
    m.x_in, m.y_in = 60.5, 60.0
checks.eq("an ENEMY Aeldari psyker does not count either",
          pc.bonus_for(far, unit, tokens + list(enemy.models)), 0)

# The snapshot, and the effect, through the real adjuster.
pc.on_selected_to_shoot(unit, tokens)
checks.eq("the bonus is stored on the model", near.psychic_communion_bonus, 2)
boosted = pc.psychic_communion_adjusted_weapon(
    next(w for w in near.weapons if w.name == "Destructor"), [(near, None)])
checks.eq("+2 Strength", boosted.strength, 5 + 2)
checks.eq("...and +2 Attacks, on the D6 notation that is actually rolled",
          (boosted.attacks_notation.sides, boosted.attacks_notation.bonus), (6, 2))
unbuffed = pc.psychic_communion_adjusted_weapon(
    next(w for w in far.weapons if w.name == "Destructor"), [(far, None)])
checks.eq("the isolated Warlock's gun is untouched", unbuffed.strength, 5)
# The shared class-level profile must never be mutated.
from game.weapons import DestructorProfile  # noqa: E402
checks.eq("the printed weapon is untouched",
          (DestructorProfile.strength, DestructorProfile.attacks_notation.bonus), (5, 0))
# Only the Destructor - the ability names it.
pistol_after = pc.psychic_communion_adjusted_weapon(
    next(w for w in near.weapons if w.name == "Shuriken Pistol"), [(near, None)])
checks.eq("the Shuriken Pistol is not affected", pistol_after.strength, 4)

pc.reset_phase([unit])
checks.eq("the bonus expires at end of phase", near.psychic_communion_bonus, 0)


# --- 5. Protect ------------------------------------------------------------
print("--- 5. Protect ---")

checks.eq("without a Farseer leading it, nothing applies", protect.applies(conclave()), False)
# No FARSEER datasheet exists yet, so one is stood up - an ordinary Warlock
# given the keyword, in its own squad, attached as a leader. Profiles are
# copied per model rather than set on the shared class.
import copy  # noqa: E402

body = conclave(name="1 Warlock Conclave 2")
seer = conclave(0, name="1 Farseer 1")
for model in seer.models:
    model.profile = copy.copy(model.profile)
    model.profile.farseer = True
tk.line_up(body, x=20.0, y=20.0)
tk.line_up(seer, x=20.0, y=18.5)
# attach() checks 19.01 legality from the points list, which has no Farseer
# entry - so the components are formed the way attach() would, directly.
from game.attached_units import AttachedComponent, LEADER, BODYGUARD  # noqa: E402

led = body
led.attached_components = [
    AttachedComponent(body.name, BODYGUARD, list(body.models), datasheet=ae.WARLOCK_CONCLAVE),
    AttachedComponent(seer.name, LEADER, list(seer.models), datasheet=ae.WARLOCK_CONCLAVE),
]
led.models.extend(seer.models)
for model in seer.models:
    model.squad = led
checks.true("with a Farseer leading it, Protect applies", protect.applies(led))

# Read back out of the function the engine uses, in BOTH phases - the ability
# says "each time an attack targets this unit", not "ranged attack".
shoot = tk.shooting_scene(ae.FIRE_DRAGONS, ae.WARLOCK_CONCLAVE, attacker_owner="Player 1", gap=6.0)
shoot["shooting"].active_squad = shoot["attacker"]
mods = shoot["shooting"]._wound_modifiers(shoot["target"])
checks.eq("no Protect modifier against an unled Conclave",
          [m for m in mods if m.source == "Protect"], [])
mods = shoot["shooting"]._wound_modifiers(led)
checks.eq("...but a +1 to the wound threshold against a led one",
          [(m.amount, m.source) for m in mods if m.source == "Protect"], [(1, "Protect")])

fight = tk.fight_scene(ae.FIRE_DRAGONS, ae.WARLOCK_CONCLAVE, attacker_owner="Player 1")
fight["fight"].select_to_fight(fight["attacker"])
weapon = next(w for w in fight["attacker"].models[0].weapons if w.weapon_type == MELEE)
checks.eq("the same in the Fight phase",
          [(m.amount, m.source) for m in fight["fight"]._wound_modifiers(weapon, led)
           if m.source == "Protect"], [(1, "Protect")])
checks.eq("...and not against an unled Conclave there either",
          [m for m in fight["fight"]._wound_modifiers(weapon, fight["target"]) if m.source == "Protect"], [])


# --- 6. this is what Wraithguard were waiting for --------------------------
print("--- 6. Psychic Guidance goes live ---")

# game/psychic_guidance.py was written as "inert today, and it will start
# firing on its own the moment an AELDARI PSYKER datasheet exists". This is
# that datasheet, so the claim gets checked rather than assumed.
guard = tk.build(ae.WRAITHGUARD, "Player 1", name="1 Wraithguard 1")
tk.line_up(guard, x=20.0, y=20.0)
warlocks = conclave(name="1 Warlock Conclave 3")
tk.line_up(warlocks, x=20.0, y=45.0)          # 25" away
board = list(guard.models) + list(warlocks.models)
checks.eq("out of range, nothing applies", pg.applies(guard, board), False)
checks.eq("...and the Wraithguard keep their printed Ld8+", leadership_threshold(guard, board), 8)

tk.line_up(warlocks, x=20.0, y=25.0)          # 5" away
checks.true("within 12\" of a real Warlock Conclave, it applies", pg.applies(guard, board))
checks.eq("...their Leadership becomes 6+", leadership_threshold(guard, board), 6)
sc = tk.shooting_scene(ae.WRAITHGUARD, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
sc["shooting"].start_shooting(sc["attacker"])
sc["shooting"].choose_target_squad(sc["target"])
key = next(r[0] for r in sc["shooting"].weapon_eligibility())
script(4, 4, 4, 4, 4, default=4)
sc["shooting"].choose_weapon(key)
checks.eq("no hit bonus with no psyker nearby",
          [m for m in sc["shooting"]._hit_modifiers(sc["shooting"].current_group)
           if m.source == "Psychic Guidance"], [])
helpers = conclave(name="1 Warlock Conclave 4")
tk.line_up(helpers, x=sc["attacker"].models[0].x_in, y=sc["attacker"].models[0].y_in + 3.0)
sc["shooting"].all_tokens = list(sc["state"].tokens) + list(helpers.models)
checks.eq("...and a -1 to the threshold (i.e. +1 to the Hit roll) with one",
          [(m.amount, m.source) for m in sc["shooting"]._hit_modifiers(sc["shooting"].current_group)
           if m.source == "Psychic Guidance"], [(-1, "Psychic Guidance")])


# --- 7. sprite -------------------------------------------------------------
print("--- 7. sprite ---")

checks.eq("Warlock Conclave art", _squad_key(small.models[0]), "Warlock Conclaive")


# --- 8. A/B probes ---------------------------------------------------------
print("--- 8. A/B probes ---")

original = pc.bonus_for
pc.bonus_for = lambda model, squad, tokens: 0
probe = conclave(1)
probe.models[0].x_in = probe.models[1].x_in = 20.0
probe.models[0].y_in = 20.0
probe.models[1].y_in = 21.0
pc.on_selected_to_shoot(probe, list(probe.models))
checks.eq("A/B: with the count neutralised the Destructor is unchanged",
          pc.psychic_communion_adjusted_weapon(
              next(w for w in probe.models[0].weapons if w.name == "Destructor"),
              [(probe.models[0], None)]).strength, 5)
pc.bonus_for = original
pc.on_selected_to_shoot(probe, list(probe.models))
checks.eq("A/B: restored",
          pc.psychic_communion_adjusted_weapon(
              next(w for w in probe.models[0].weapons if w.name == "Destructor"),
              [(probe.models[0], None)]).strength, 6)

original_protect = protect.applies
protect.applies = lambda squad: False
checks.eq("A/B: unwired, Protect grants no modifier",
          [m for m in shoot["shooting"]._wound_modifiers(led) if m.source == "Protect"], [])
protect.applies = original_protect
checks.true("A/B: restored",
            any(m.source == "Protect" for m in shoot["shooting"]._wound_modifiers(led)))

checks.finish()
