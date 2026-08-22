"""Farseer: datasheet data, Branching Fates, Guide - and Protect's status.

Three things get depth. Branching Fates shares its arithmetic with the Aspect
Shrine token, so what is tested here is what is NOT shared: a per-phase
resource, a third roll type (Damage), and the fact that both abilities now come
out of one table without either shadowing the other. Guide is the first effect
in this engine whose duration deliberately spans the opponent's turn, so its
expiry point is tested rather than its setting. And Protect's status is checked
honestly: this datasheet was supposed to make it live, and it turns out the
printed LEADER lines do not allow the attachment that would.
"""

import copy

import testkit as tk
from testkit import Checks, script

from game import branching_fates as bf
from game import guide as gd
from game import protect
from game import unmodified_six
from game.attached_units import attach, can_attach
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Farseer")
LINE = "Farseer"


def farseer(owner="Player 1", name="1 Farseer 1", choices=None):
    return tk.build(ae.FARSEER, owner, name=name, choices=choices)


def guardians(owner="Player 1", name="1 Guardian Defenders 1"):
    return tk.build(ae.GUARDIAN_DEFENDERS, owner, name=name)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

sq = farseer()
p = sq.models[0].profile
checks.eq("one model", len(sq.models), 1)
checks.eq("65 points", sq.points, 65)
checks.eq("M7\"", p.movement_in, 7)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv6+", p.armor_save, "6+")
checks.eq("W4", p.wounds, 4)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("4+ invulnerable", p.invulnerable_save, "4+")
checks.eq("WS/BS 2+", (p.weapon_skill, p.ballistic_skill), ("2+", "2+"))
checks.eq("25 mm base - the smallest here",
          round(p.base_radius_in, 3), round(25 / 2 / 25.4, 3))
checks.true("PSYKER", p.psyker)
checks.true("FARSEER", p.farseer)
checks.true("LEADER, from his CORE line", p.leader)
checks.true("Battle Focus", p.battle_focus)
checks.true("Branching Fates", p.branching_fates)
checks.true("Guide", p.guide)
for kw in ("INFANTRY", "CHARACTER", "PSYKER", "FARSEER"):
    checks.true(f"keyword {kw}", kw in ae.FARSEER.keywords)


# --- 2. weapons ------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("loadout", sorted(w.name for w in sq.models[0].weapons),
          ["Eldritch Storm", "Shuriken Pistol", "Witchblade"])
storm = next(w for w in sq.models[0].weapons if w.name == "Eldritch Storm")
checks.eq("Eldritch Storm 24\"/S6/AP-2", (storm.range_in, storm.strength, storm.ap), (24, 6, -2))
checks.eq("...D6 attacks and D3 damage, both rolled",
          (storm.attacks_notation.sides, storm.damage_notation.sides), (6, 3))
checks.true("[BLAST]", bool(storm.blast))
checks.true("[PSYCHIC]", storm.psychic)
# Four of his five rows are the Warlock Conclave's, shared rather than copied:
# the printed BS/WS differ (2+ against 3+) but those belong to the MODEL, which
# both weapons defer to.
from game.weapons import ShurikenPistolProfile, WitchbladeProfile  # noqa: E402
checks.eq("the Shuriken Pistol is the shared profile, deferring BS to the model",
          ShurikenPistolProfile.ballistic_skill, None)
checks.eq("the Witchblade likewise defers WS", WitchbladeProfile.weapon_skill, None)
speared = farseer(choices={LINE: {ae.FARSEER_WITCHBLADE_TO_SPEAR: 1}})
checks.eq("the spear swap grants both printed profiles",
          sorted(w.weapon_type for w in speared.models[0].weapons if w.name == "Singing Spear"),
          [MELEE, RANGED])


# --- 3. Leader (19.01) -----------------------------------------------------
print("--- 3. Leader ---")

for sheet in (ae.GUARDIAN_DEFENDERS, ae.STORM_GUARDIANS):
    checks.eq(f"he can lead {sheet.name}",
              can_attach(farseer(), tk.build(sheet, "Player 1", name=f"1 {sheet.name} 1")), [])
checks.true("and nothing else",
            bool(can_attach(farseer(), tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1"))))


# --- 4. Branching Fates ----------------------------------------------------
print("--- 4. Branching Fates ---")


def led_unit():
    body, lord = guardians(), farseer()
    tk.line_up(body, x=20.0, y=20.0)
    tk.line_up(lord, x=20.0, y=18.5)
    attach(lord, body)
    return body


led = led_unit()
checks.true("a led unit has the ability", bf.unit_has_farseer(led))
checks.eq("a plain Guardian squad does not", bf.unit_has_farseer(guardians()), False)
checks.eq("a lone Farseer leads nobody", bf.unit_has_farseer(farseer()), False)
checks.true("and it is available to start with", bf.available(led))

model = led.models[0]
plain_gun = type("W", (), {"sustained_hits": 0, "lethal_hits": False, "devastating_wounds": False})()
checks.eq("a miss on the hit roll is worth using it on",
          bf.hit_change(led, model, plain_gun, hits=9, crits=0, misses=1)[:2], (10, 1))
checks.eq("a failed wound likewise",
          bf.wound_change(led, model, plain_gun, wounds=9, crits=0, no_effect=1)[:3], (10, 1, 0))
# The gate is unmodified_six's, shared with the Aspect Shrine token.
checks.eq("an all-hits roll with no crit payoff is NOT offered",
          bf.hit_change(led, model, plain_gun, hits=10, crits=0, misses=0), None)
# The third roll type, which the token does not cover.
checks.eq("a Damage roll of 2 becomes 6", bf.damage_change(led, model, 2), 6)
checks.eq("...and one that is already 6 buys nothing", bf.damage_change(led, model, 6), None)

# ONCE PER PHASE, across all three roll types - one shared resource.
bf.spend(led)
checks.eq("spent, it is no longer available", bf.available(led), False)
checks.eq("...not for a hit roll",
          bf.hit_change(led, model, plain_gun, hits=9, crits=0, misses=1), None)
checks.eq("...nor a wound roll",
          bf.wound_change(led, model, plain_gun, wounds=9, crits=0, no_effect=1), None)
checks.eq("...nor a Damage roll", bf.damage_change(led, model, 2), None)
bf.reset_phase([led])
checks.true("but it comes back next phase - unlike a per-battle token", bf.available(led))

# "Excluding SUPPORT WEAPON models" is real but currently excludes nobody.
checks.eq("no model in this engine is a SUPPORT WEAPON yet", bf._excluded(model), False)
support = copy.copy(model)
support.profile = copy.copy(model.profile)
support.profile.support_weapon = True
checks.true("...but one that was would be excluded", bf._excluded(support))

# Both unmodified-6 sources now come out of one table, and neither shadows the
# other: an Aspect Warrior unit with a token still gets ITS offer.
from game import aspect_shrine  # noqa: E402
from game.shooting import _UNMODIFIED_SIX_SOURCES  # noqa: E402

checks.eq("both abilities are in the table",
          sorted(m.__name__ for m in _UNMODIFIED_SIX_SOURCES),
          ["game.aspect_shrine", "game.branching_fates"])
dragons = tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1")
checks.eq("a Fire Dragon unit still uses its own token, not this",
          aspect_shrine.hit_change(dragons, dragons.models[1], plain_gun, 4, 0, 1)[:2], (5, 1))
checks.eq("...and Branching Fates does not apply to it",
          bf.hit_change(dragons, dragons.models[1], plain_gun, 4, 0, 1), None)


# --- 5. Branching Fates: the Damage half end to end ------------------------
print("--- 5. the Damage half ---")

from game.damage_resolution import DamageAllocationSession  # noqa: E402
from game.decision import DecisionManager  # noqa: E402

target = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 1")


def damage_scene(answer):
    unit = led_unit()
    dm, dice, log = DecisionManager(), tk.RecordingDice(), tk.Log()
    offer = bf.BranchingFatesDamageOffer(
        squad=unit, decision_manager=dm, game_log=log, owner="Player 1", weapon_name="Eldritch Storm",
    )
    # A W13 Devilfish, not a W1 Strike Team: excess damage does not carry over
    # from model to model, so against 1-wound models a 2 and a 6 both read as
    # "one wound lost" and the test would prove nothing.
    fresh = tk.build(tau.DEVILFISH, "Player 2", name="1 Devilfish 1")
    # The Farseer's own gun, which is the one with a rolled Damage.
    weapon = next(w for w in farseer().models[0].weapons if w.name == "Eldritch Storm")
    script(2, default=2)   # the Damage roll comes up 2
    # `log` here is a CALLABLE, not the Log object - shooting.py passes its own
    # _log method.
    session = DamageAllocationSession([1], weapon, fresh, dice_manager=dice, log=log.add,
                                      damage_override=offer)
    for _ in range(8):
        if dm.is_pending:
            tk.pick_option(dm, answer)
        elif session.pending_damage_roll is not None and dice.is_pending:
            dice.acknowledge()
            session.on_damage_roll_acknowledged()
        elif session.pending_choice:
            session.choose_model(session.pending_choice[0])
        else:
            break
    return dict(unit=unit, target=fresh, session=session, log=log, decision=dm)


kept = damage_scene("Keep the Damage roll (2)")
used = damage_scene("Branching Fates: make it 6")
checks.true("the Damage offer is raised", any("Branching Fates" in line for line in used["log"].lines))


def wounds_lost(sc):
    return sum(m.profile.wounds for m in sc["target"].models) - sum(
        m.current_wounds for m in sc["target"].models)


checks.eq("kept: the rolled 2 stands", wounds_lost(kept), 2)
checks.eq("used: it counts as an unmodified 6", wounds_lost(used), 6)
checks.eq("using it spends the once-per-phase resource", bf.available(used["unit"]), False)
checks.true("declining does not", bf.available(kept["unit"]))


# --- 6. Guide --------------------------------------------------------------
print("--- 6. Guide ---")

ctrl = gd.GuideController(game_log=tk.Log())
seer = farseer()
tk.line_up(seer, x=20.0, y=20.0)
enemy_near = tk.build(tau.STRIKE_TEAM, "Player 2", name="2 Strike Team 1")
enemy_far = tk.build(tau.STRIKE_TEAM, "Player 2", name="2 Strike Team 2")
tk.line_up(enemy_near, x=20.0, y=28.0)     # 8" - within 18"
tk.line_up(enemy_far, x=20.0, y=70.0)      # far outside
ctrl.all_tokens = list(seer.models) + list(enemy_near.models) + list(enemy_far.models)

names = [s.name for s in ctrl.candidates(seer)]
checks.true("a unit within 18\" and visible is selectable", enemy_near.name in names)
checks.eq("one beyond 18\" is not", enemy_far.name in names, False)

friendly = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 2")
checks.eq("nothing is marked to begin with",
          ctrl.applies(friendly.models[0], enemy_near), False)
ctrl.mark("Player 1", enemy_near)
checks.true("a friendly AELDARI model attacking the marked unit gets it",
            ctrl.applies(friendly.models[0], enemy_near))
checks.eq("...but not against an unmarked one",
          ctrl.applies(friendly.models[0], enemy_far), False)
# ARMY-wide, not unit-wide: any Aeldari unit the player owns benefits.
other_friendly = tk.build(ae.WRAITHGUARD, "Player 1", name="1 Wraithguard 1")
checks.true("a completely different friendly Aeldari unit benefits too",
            ctrl.applies(other_friendly.models[0], enemy_near))
# ...but only AELDARI models.
ork = tk.build(__import__("game.factions.orks", fromlist=["x"]).BOYZ, "Player 1", name="1 Boyz 1")
checks.eq("a non-AELDARI friendly model does not", ctrl.applies(ork.models[0], enemy_near), False)
enemy_side = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 1")
checks.eq("nor an enemy Aeldari model", ctrl.applies(enemy_side.models[0], enemy_near), False)

# "Each unit can only be selected for this ability once per turn."
checks.eq("an already-marked unit is not offered again",
          enemy_near.name in [s.name for s in ctrl.candidates(seer)], False)

# The duration: it survives to the opponent's turn and dies at the START of the
# owner's next Command phase - the only effect here that spans a turn boundary.
ctrl.start_of_command_phase("Player 2")
checks.true("the opponent's Command phase does NOT clear it",
            ctrl.applies(friendly.models[0], enemy_near))
ctrl.start_of_command_phase("Player 1")
checks.eq("the owner's next Command phase does", ctrl.applies(friendly.models[0], enemy_near), False)
checks.true("...and the once-per-turn cap resets with it",
            enemy_near.name in [s.name for s in ctrl.candidates(seer)])

# Read back out of the function the engine uses.
shoot = tk.shooting_scene(ae.GUARDIAN_DEFENDERS, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
live = gd.GuideController(game_log=tk.Log(), all_tokens=shoot["state"].tokens)
shoot["shooting"].guide = live
shoot["shooting"].start_shooting(shoot["attacker"])
shoot["shooting"].choose_target_squad(shoot["target"])
key = next(r[0] for r in shoot["shooting"].weapon_eligibility())
script(4, default=4)
shoot["shooting"].choose_weapon(key)
checks.eq("no Guide modifier without a mark",
          [m for m in shoot["shooting"]._hit_modifiers(shoot["shooting"].current_group)
           if m.source == "Guide"], [])
live.mark("Player 1", shoot["target"])
checks.eq("...and a -1 to the threshold (i.e. +1 to the Hit roll) with one",
          [(m.amount, m.source) for m in shoot["shooting"]._hit_modifiers(shoot["shooting"].current_group)
           if m.source == "Guide"], [(-1, "Guide")])

fight = tk.fight_scene(ae.GUARDIAN_DEFENDERS, tau.STRIKE_TEAM, attacker_owner="Player 1")
fight["fight"].guide = live
fight["fight"].select_to_fight(fight["attacker"])
checks.eq("the same in the Fight phase - the rule says 'an attack'",
          [(m.amount, m.source) for m in
           fight["fight"]._hit_modifiers(fight["attacker"].models[0], fight["target"])
           if m.source == "Guide"], [])
live.mark("Player 1", fight["target"])
checks.eq("...once that target is the marked one",
          [(m.amount, m.source) for m in
           fight["fight"]._hit_modifiers(fight["attacker"].models[0], fight["target"])
           if m.source == "Guide"], [(-1, "Guide")])


# --- 7. Protect: honestly, still not reachable -----------------------------
print("--- 7. Protect ---")

# This datasheet was expected to make Warlock Conclave's Protect live, the way
# the Conclave made Wraithguard's Psychic Guidance live. It does not, and the
# reason is in the printed LEADER lines rather than in the code: Protect needs
# a Farseer LEADING a unit that contains Warlocks, and a Warlock Conclave is
# itself a leader unit which the Farseer's own LEADER line does not name. The
# a bodyguard unit with TWO leaders attached is the only shape that satisfies
# it. Rule 19.01 allows that where the BODYGUARD datasheet says so (none here
# does) - or, as Eldrad Ulthran turned out to print, where the arriving LEADER
# says so. Eldrad is therefore the datasheet that makes Protect live; these
# checks stay about the PLAIN Farseer, which prints no such clause. See
# test_eldrad_ulthran.py for the other half.
conclave = tk.build(ae.WARLOCK_CONCLAVE, "Player 1", name="1 Warlock Conclave 1")
errors = can_attach(farseer(), conclave)
checks.true("a Farseer cannot be attached to a Warlock Conclave", bool(errors))
checks.true("...because the Conclave is itself a leader unit",
            any("leader/support unit" in e for e in errors))
body = guardians()
lord = farseer()
tk.line_up(body, x=20.0, y=20.0)
tk.line_up(lord, x=20.0, y=18.5)
attach(lord, body)
tk.line_up(conclave, x=20.0, y=17.0)
checks.true("and a second leader on the same bodyguard is refused too",
            bool(can_attach(conclave, body)))
# The predicate itself is correct for whichever merge becomes legal: given the
# components it describes, it fires.
from game.attached_units import AttachedComponent, BODYGUARD, LEADER  # noqa: E402

merged = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 3")
warlocks = tk.build(ae.WARLOCK_CONCLAVE, "Player 1", name="1 Warlock Conclave 2")
seer2 = farseer(name="1 Farseer 2")
merged.attached_components = [
    AttachedComponent(merged.name, BODYGUARD, list(merged.models), datasheet=ae.GUARDIAN_DEFENDERS),
    AttachedComponent(warlocks.name, LEADER, list(warlocks.models), datasheet=ae.WARLOCK_CONCLAVE),
    AttachedComponent(seer2.name, LEADER, list(seer2.models), datasheet=ae.FARSEER),
]
for extra in (warlocks, seer2):
    merged.models.extend(extra.models)
    for m in extra.models:
        m.squad = merged
checks.true("given that merge, Protect does apply", protect.applies(merged))


# --- 8. sprite -------------------------------------------------------------
print("--- 8. sprite ---")

checks.eq("Farseer art", _squad_key(sq.models[0]), "Farseer")


# --- 9. A/B probes ---------------------------------------------------------
print("--- 9. A/B probes ---")

original = bf.unit_has_farseer
bf.unit_has_farseer = lambda squad: False
probe = led_unit()
checks.eq("A/B: without the leader lookup nothing is offered",
          bf.hit_change(probe, probe.models[0], plain_gun, 9, 0, 1), None)
bf.unit_has_farseer = original
checks.true("A/B: restored",
            bf.hit_change(probe, probe.models[0], plain_gun, 9, 0, 1) is not None)

# Patched on the CONTROLLER, not on gd.GUIDE_RANGE_IN: since the mark machinery
# moved into game/psychic_mark.py the range is a class attribute read as
# self.range_in, so mutating the module constant afterwards neutralises nothing.
# The probe has to patch what the class actually reads or it silently stops
# being a probe - the same stale-A/B trap recorded in CLAUDE.md.
saved = ctrl.range_in
ctrl.range_in = 0.0
checks.eq("A/B: with no range, nothing is selectable", ctrl.candidates(seer), [])
ctrl.range_in = saved
checks.true("A/B: restored", bool(ctrl.candidates(seer)))
checks.eq("...and the module constant still says what the datasheet prints",
          gd.GUIDE_RANGE_IN, 18.0)

checks.finish()
