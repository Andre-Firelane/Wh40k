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
from game import units as un
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
# User: "farseer und eldrad scheinen mir zu klein. sie sollen genau so gross
# sein, wie warlock conclaive" - so the printed 25 mm base is deliberately not
# used. Pinned against the Warlock's own profile rather than against a literal,
# so the two cannot drift apart unnoticed (same call as the Falcon/Devilfish
# pair). This is not cosmetic: base_radius_in feeds placement, the movement
# clamp, edge_distance and coherency.
checks.eq("same base as the Warlock Conclave, not his printed 25 mm",
          p.base_radius_in, un.WarlockProfile.base_radius_in)
checks.true("...which really is bigger than the printed 25 mm",
            p.base_radius_in > round(25 / 2 / 25.4, 3))
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
checks.true("a led unit may use it on a roll for one of its models",
            bf.usable(led, model))
# WHETHER a die is worth changing is game/unmodified_six.py's shared gate, the
# same one the Aspect Shrine token uses - tested there. What belongs to THIS
# ability is only the resource, so that is what is checked here.
checks.eq("a miss is what the shared gate looks for",
          unmodified_six.gain(failures=1, successes=9, crits=0, crit_matters=False), "failure")
checks.eq("an all-hits roll with no crit payoff is NOT offered",
          unmodified_six.gain(failures=0, successes=10, crits=0,
                              crit_matters=unmodified_six.crit_matters_on_hit(plain_gun)), None)
# The third roll type, which the token does not cover, and which keeps its own
# offer inside the damage session (see game/unmodified_six_controller.py's own
# note on why a Damage roll cannot go through the die-picking path).
checks.eq("a Damage roll of 2 becomes 6", bf.damage_change(led, model, 2), 6)
checks.eq("...and one that is already 6 buys nothing", bf.damage_change(led, model, 6), None)

# ONCE PER PHASE, across all three roll types - one shared resource.
bf.spend(led)
checks.eq("spent, it is no longer available", bf.available(led), False)
checks.eq("...not for a hit or wound roll", bf.usable(led, model), False)
checks.eq("...nor a Damage roll", bf.damage_change(led, model, 2), None)
bf.reset_phase([led])
checks.true("but it comes back next phase - unlike a per-battle token", bf.available(led))
checks.true("...and the button says which resource it is",
            "once per phase" in bf.button_label(led).lower())

# "Excluding SUPPORT WEAPON models" is real but currently excludes nobody.
checks.eq("no model in this engine is a SUPPORT WEAPON yet", bf._excluded(model), False)
support = copy.copy(model)
support.profile = copy.copy(model.profile)
support.profile.support_weapon = True
checks.true("...but one that was would be excluded", bf._excluded(support))

# Both unmodified-6 sources come out of one table, and neither shadows the
# other: an Aspect Warrior unit with a token still gets ITS button. The table
# moved out of game/shooting.py when the offer became a left-panel button
# instead of a prompt after every roll.
from game import aspect_shrine  # noqa: E402
from game.unmodified_six_controller import SOURCES  # noqa: E402

checks.eq("both abilities are in the table",
          sorted(m.__name__ for m in SOURCES),
          ["game.aspect_shrine", "game.branching_fates"])
checks.eq("Aspect Shrine is offered first - it is the scarcer resource",
          SOURCES[0].__name__, "game.aspect_shrine")
dragons = tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1")
checks.true("a Fire Dragon unit still uses its own token, not this",
            aspect_shrine.usable(dragons, dragons.models[1]))
checks.eq("...and Branching Fates does not apply to it",
          bf.usable(dragons, dragons.models[1]), False)
# Every source has to satisfy the same small interface, or the panel and the
# controller would need a special case per ability.
for source in SOURCES:
    for attr in ("usable", "spend", "button_label", "ACCEPT_LABEL"):
        checks.true(f"{source.__name__} provides {attr}", hasattr(source, attr))


# --- 5. Branching Fates: the Damage half end to end ------------------------
print("--- 5. the Damage half ---")

from game.factions import tau_empire as tau  # noqa: E402
from game.unmodified_six_controller import UnmodifiedSixController  # noqa: E402
from game.decision import DecisionManager  # noqa: E402

# The Damage half is a left-panel button too now, spent WHILE the Damage roll
# is still on the table. User: "branching fate für den damage roll war gerade
# noch ein overlay." It cannot go through the die-PICKING path the Hit and
# Wound rolls use, because a Damage roll is one die whose RESULT is what the
# rule talks about - and nine weapons in this repo print a bonus (D6+1, D6+2),
# so the die that produces a result of 6 is not always a 6.


def damage_scene(gap=6.0, faces=(1, 6, 6, 1, 2)):
    """A led Guardian unit shooting the Farseer's own Eldritch Storm - the one
    weapon here with a rolled Damage - into a W13 Devilfish.

    Not a W1 Strike Team: excess damage does not carry over from model to
    model, so against 1-wound models a 2 and a 6 both read as "one wound lost"
    and the test would prove nothing."""
    unit = led_unit()
    target = tk.build(tau.DEVILFISH, "Player 2", name="1 Devilfish 1")
    state = tk.GameState()
    tk.line_up(unit, x=20.0, y=20.0)
    tk.line_up(target, x=20.0, y=20.0 + gap)
    for squad in (unit, target):
        for model in squad.models:
            state.add_token(model)

    from game.shooting import ShootingController  # noqa: E402
    from game.turn import PHASES, PHASE_SHOOTING, TurnTracker  # noqa: E402
    turn = TurnTracker(first_player="Player 1")
    turn.phase_index = PHASES.index(PHASE_SHOOTING)
    turn.turn_owner = "Player 1"
    turn.set_active("Player 1")
    dice, dec, log = tk.RecordingDice(), DecisionManager(), tk.Log()
    shooting = ShootingController(dice_manager=dice, turn_tracker=turn, all_tokens=state.tokens,
                                  decision_manager=dec, game_log=log, obstacles=[])
    shooting.start_shooting(unit)
    shooting.choose_target_squad(target)
    key = next(r[0] for r in shooting.weapon_eligibility() if r[1] == "Eldritch Storm")
    # The Eldritch Storm rolls its Attacks (D6) AND its Damage (D3), so the
    # sequence is: attacks, hit, wound, save, damage. One attack keeps it
    # short; the save must FAIL or no damage is ever rolled.
    script(*faces, default=2)
    shooting.choose_weapon(key)
    ctrl = UnmodifiedSixController(dice, attack_controllers=(shooting,), game_log=log)
    return dict(unit=unit, target=target, shooting=shooting, dice=dice,
                decision=dec, log=log, ctrl=ctrl)


def run_to_damage_roll(sc):
    """Acknowledge rolls until the DAMAGE roll is the one on the table."""
    from game.dice import DAMAGE_ROLL  # noqa: E402
    for _ in range(14):
        if sc["dice"].is_pending and sc["dice"].roll_kind == DAMAGE_ROLL:
            return True
        if sc["decision"].is_pending:
            tk.pick_option(sc["decision"], "Keep")
        elif sc["dice"].is_pending:
            sc["dice"].acknowledge()
            sc["shooting"].on_dice_acknowledged()
        elif sc["shooting"].pending_damage_choice is not None:
            sc["shooting"].choose_damage_model(sc["shooting"].pending_damage_choice[0])
        else:
            return False
    return False


def finish(sc):
    for _ in range(16):
        if sc["decision"].is_pending:
            tk.pick_option(sc["decision"], "Keep")
        elif sc["dice"].is_pending:
            sc["dice"].acknowledge()
            sc["shooting"].on_dice_acknowledged()
        elif sc["shooting"].pending_damage_choice is not None:
            sc["shooting"].choose_damage_model(sc["shooting"].pending_damage_choice[0])
        else:
            break
    return sc


def wounds_lost(sc):
    return sum(m.profile.wounds for m in sc["target"].models) - sum(
        m.current_wounds for m in sc["target"].models)


reached = damage_scene()
checks.true("a Damage roll really is reached", run_to_damage_roll(reached))
checks.eq("...and it rolled a 2", reached["dice"].pending_values, [2])
# THE REPORT: no overlay at this moment - a button instead.
checks.eq("no overlay is raised for it", reached["decision"].is_pending, False)
offered = [s.__name__ for s, _sq, _m in reached["ctrl"].available_sources()]
checks.eq("Branching Fates is offered as a button", offered, ["game.branching_fates"])
checks.eq("...and the Aspect Shrine token is NOT - it does not cover Damage rolls",
          "game.aspect_shrine" in offered, False)

kept = finish(damage_scene())
used = damage_scene()
run_to_damage_roll(used)
used["ctrl"].start(bf)
checks.eq("there is no die to pick - it applies at once", used["ctrl"].selecting_die, False)
finish(used)

checks.eq("kept: the rolled 2 stands", wounds_lost(kept), 2)
checks.eq("used: it counts as an unmodified 6", wounds_lost(used), 6)
checks.eq("using it spends the once-per-phase resource", bf.available(used["unit"]), False)
checks.true("declining does not", bf.available(kept["unit"]))
checks.true("and it is logged",
            any("unmodified 6" in line for line in used["log"].lines))

# Once spent, the button is gone for the rest of the phase - the resource is
# what gates it, and there is no second Damage roll to offer it on.
spent = damage_scene()
run_to_damage_roll(spent)
spent["ctrl"].start(bf)
checks.eq("spent: the button is gone", spent["ctrl"].available_sources(), [])
checks.eq("...because the resource is used", bf.available(spent["unit"]), False)

# "A Damage roll that is already 6+ buys nothing" cannot be staged with this
# weapon - the Eldritch Storm's Damage is a D3, which can never roll a 6 on
# its own (the very case game/branching_fates.py's docstring calls out). The
# gate itself is checked directly in section 4 instead, which is the honest
# place for a condition no rostered weapon can produce.

# THE BONUS CASE, which is why this cannot reuse the die-picking path: on a
# D6+2 the RESULT has to become 6, so the die has to become a 4 - setting it
# to 6 would mean 8. face_for_total() owns that, and it is checked directly
# because no rostered weapon here prints both a Damage bonus and a Farseer.
from game.dice_notation import D3, D6, DiceNotationRoll  # noqa: E402

plain = DiceNotationRoll(D6(), 1, None, "probe")
checks.eq("a plain D6 wants a 6 for a result of 6", DiceNotationRoll.face_for_total(
    type("R", (), {"count": 1, "notation": D6()})(), 6), 6)
checks.eq("a D6+2 wants a 4", DiceNotationRoll.face_for_total(
    type("R", (), {"count": 1, "notation": D6(bonus=2)})(), 6), 4)
checks.eq("a D3 wants a 6 - taken literally, see the module docstring",
          DiceNotationRoll.face_for_total(
              type("R", (), {"count": 1, "notation": D3()})(), 6), 6)
checks.eq("a MULTI-die roll is refused rather than guessed at",
          DiceNotationRoll.face_for_total(
              type("R", (), {"count": 1, "notation": D6(dice=2)})(), 6), None)


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

# Protect needs a Farseer LEADING a unit that contains Warlocks. This section
# is about which shapes of that a PLAIN Farseer can reach, and the answer has
# been revised twice as printed text arrived, so both revisions are recorded
# here rather than left as a bare set of assertions:
#
#   1. First reading: unreachable for a plain Farseer. A Warlock Conclave is
#      itself a leader unit, so the Farseer cannot attach TO it, and 19.01
#      allows a bodyguard only one leader.
#   2. Then Eldrad Ulthran's LEADER line arrived, printing the "even if one
#      WARLOCKS unit has already been attached" permission - so HE could be the
#      second unit, and a plain Farseer still could not.
#   3. Then the Conclave's OWN LEADER text arrived, and it is not an
#      attachment at all: it is a JOIN whose only printed limit is one Conclave
#      per unit. So a plain Farseer reaches Protect after all - by attaching
#      FIRST and letting the Conclave join him. Which is exactly the order
#      main.py's Guardian Defenders use.
#
# What has not changed is that the Farseer cannot attach to a Conclave, nor be
# the second unit on one. Both are checked below, and so is the order that
# works - because the difference between them IS the rule.
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
# 19.01's one-leader default is intact - checked with a second FARSEER, which
# is what it is actually about. This check used to use the Conclave and assert
# refusal; that was pinning the pre-fetch assumption that a Conclave attaches
# like any other leader, and it is corrected rather than deleted.
checks.true("a second FARSEER on the same bodyguard is refused (19.01)",
            bool(can_attach(farseer(name="1 Farseer 1b"), body)))
# The Conclave, by contrast, JOINS - its own printed limit is one Conclave per
# unit, and it says nothing about other leaders. So this is the shape that
# gives a plain Farseer his Protect.
checks.eq("...but the Conclave may still join him", can_attach(conclave, body), [])
with_protect = attach(conclave, body)
checks.true("...and Protect applies to the merged unit",
            protect.applies(with_protect))
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
          bf.usable(probe, probe.models[0]), False)
bf.unit_has_farseer = original
checks.true("A/B: restored", bf.usable(probe, probe.models[0]))

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
