"""Lhykhis: datasheet data, Empyric Ambush, Whispering Web - and the crit
threshold leaving the Fight phase.

Two things get depth. Empyric Ambush is the only ability here that CANCELS
another one, so what is tested is that it cancels exactly that one: a
Lhykhis-led unit that Flickerjumped may charge, and the same unit may not if
something else locked it (the flag is shared with 18.04/18.05, The Shortened
Blade and The Torchstar Gambit).

Whispering Web is the first source of a lowered crit threshold that is not
melee-only, which is what turned game/melee_crit.py into game/crit_hit.py and
gave game/shooting.py's hit step a crit threshold at all. So it is read back
through the real hit resolution in BOTH phases, on identical scripted dice -
and the two melee-worded sources are checked to have stayed melee-only.
"""

import copy

import testkit as tk
from testkit import Checks, script

from game import crit_hit
from game import empyric_ambush as ea
from game import status_effects
from game import whispering_web as ww
from game.attached_units import attach, can_attach
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Lhykhis")


def lhykhis(owner="Player 1", name="1 Lhykhis 1"):
    return tk.build(ae.LHYKHIS, owner, name=name)


def spiders(owner="Player 1", name="1 Warp Spiders 1"):
    return tk.build(ae.WARP_SPIDERS, owner, name=name)


# --- 1. statline, keywords, points, weapons --------------------------------
print("--- 1. statline, keywords, points, weapons ---")

sq = lhykhis()
p = sq.models[0].profile
checks.eq("one model", len(sq.models), 1)
checks.eq("135 points", sq.points, 135)
checks.eq("M12\" - the fastest profile here", p.movement_in, 12)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv2+", p.armor_save, "2+")
checks.eq("W5", p.wounds, 5)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("4+ invulnerable", p.invulnerable_save, "4+")
checks.eq("WS2+", p.weapon_skill, "2+")
checks.eq("40 mm base", round(p.base_radius_in, 3), round(40 / 2 / 25.4, 3))
# The other two Phoenix Lords, so a copy-paste from either would show up.
for other in ("Asurmen", "Jain Zar"):
    sheet = getattr(ae, other.upper().replace(" ", "_"))
    op = tk.build(sheet, "Player 1", name=f"1 {other} 1").models[0].profile
    checks.true(f"faster than {other}", p.movement_in > op.movement_in)
checks.true("JUMP PACK", p.jump_pack)
checks.true("FLY", p.fly)
checks.true("Deep Strike (her CORE line)", p.deep_strike)
checks.true("Battle Focus", p.battle_focus)
checks.true("Empyric Ambush", p.empyric_ambush)
checks.true("Whispering Web", p.whispering_web)
for kw in ("INFANTRY", "CHARACTER", "EPIC HERO", "JUMP PACK", "FLY", "ASPECT WARRIOR", "PHOENIX LORD"):
    checks.true(f"keyword {kw}", kw in ae.LHYKHIS.keywords)
# ASPECT WARRIOR but no token: her wargear line has no entry for one.
from game import aspect_shrine  # noqa: E402

checks.eq("no Aspect Shrine token, unlike the four ASPECT WARRIORS squads",
          aspect_shrine.tokens_for(lhykhis()), 0)
checks.true("...while a Warp Spiders squad does have one",
            aspect_shrine.tokens_for(spiders()) > 0)

checks.eq("loadout", sorted(w.name for w in sq.models[0].weapons),
          ["Brood Twain", "Spider's Fangs", "Weaverender"])
gun = next(w for w in sq.models[0].weapons if w.weapon_type == RANGED)
checks.eq("Brood Twain 12\"/S6/AP-2/D1", (gun.range_in, gun.strength, gun.ap, gun.damage), (12, 6, -2, 1))
checks.eq("...D6+3 attacks, rolled",
          (gun.attacks_notation.sides, gun.attacks_notation.bonus), (6, 3))
checks.true("...[TORRENT] - which the printed BS of N/A corroborates", gun.torrent)
checks.eq("...so it prints no Ballistic Skill", gun.ballistic_skill, None)
checks.true("...[IGNORES COVER]", gun.ignores_cover)
checks.true("...[TWIN-LINKED]", gun.twin_linked)
fangs = next(w for w in sq.models[0].weapons if w.name == "Spider's Fangs")
weaver = next(w for w in sq.models[0].weapons if w.name == "Weaverender")
checks.eq("Spider's Fangs A5/S4/AP-2/D1",
          (fangs.attacks, fangs.strength, fangs.ap, fangs.damage), (5, 4, -2, 1))
checks.eq("Weaverender A5/S6/AP-2/D2",
          (weaver.attacks, weaver.strength, weaver.ap, weaver.damage), (5, 6, -2, 2))
checks.true("the Fangs have [EXTRA ATTACKS], so both melee rows swing (24.11)", fangs.extra_attacks)
checks.eq("...and Weaverender does not - that is the one 04.01 would pick",
          weaver.extra_attacks, False)
checks.true("both [LETHAL HITS]", fangs.lethal_hits and weaver.lethal_hits)


# --- 2. Leader (19.01) -----------------------------------------------------
print("--- 2. Leader ---")

checks.eq("she leads Warp Spiders", can_attach(lhykhis(), spiders()), [])
for sheet in (ae.GUARDIAN_DEFENDERS, ae.STRIKING_SCORPIONS, ae.DIRE_AVENGERS):
    checks.true(f"and not {sheet.name} - the narrowest leader list in the faction",
                bool(can_attach(lhykhis(), tk.build(sheet, "Player 1", name=f"1 {sheet.name} 1"))))
# JUMP PACK: a Falcon cannot carry her at all, and she costs two slots anyway.
from game.formations import _model_capacity_cost  # noqa: E402

checks.eq("JUMP PACK costs two transport slots", _model_capacity_cost(sq.models[0]), 2)


# --- 3. Empyric Ambush -----------------------------------------------------
print("--- 3. Empyric Ambush ---")

from game.charge import ChargeController  # noqa: E402
from game.flickerjump import FlickerjumpController  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.turn import PHASE_MOVEMENT  # noqa: E402


_scene_n = [0]


def flickerjump_scene(led):
    """A Warp Spiders unit that can legally use Flickerjump right now, with an
    enemy 8" away so that the charge lock is the ONLY thing that can make
    can_declare_charge() refuse it."""
    _scene_n[0] += 1
    body = spiders(name=f"1 Warp Spiders S{_scene_n[0]}")
    tk.line_up(body, x=20.0, y=20.0)
    if led:
        lord = lhykhis(name=f"1 Lhykhis S{_scene_n[0]}")
        tk.line_up(lord, x=20.0, y=18.5)
        attach(lord, body)
    foe = tk.build(tau.STRIKE_TEAM, "Player 2", name=f"1 Strike Team S{_scene_n[0]}")
    tk.line_up(foe, x=20.0, y=28.0)
    tokens = list(body.models) + list(foe.models)
    tt = tk._tracker(PHASE_MOVEMENT, owner=body.owner)
    log = tk.Log()
    move = MovementController([], log, body.owner, None, tt, tokens)
    fj = FlickerjumpController(movement_controller=move, turn_tracker=tt, game_log=log)
    return body, fj, tt, log, tokens


plain, fj, tt, log, plain_tokens = flickerjump_scene(led=False)
checks.eq("an unled Warp Spiders unit is not led by her", ea.applies(plain), False)
checks.true("it can use Flickerjump", fj.use(plain))
checks.true("...and that locks its charge", plain.charge_locked_until_end_of_turn)

led, fj2, tt2, log2, led_tokens = flickerjump_scene(led=True)
checks.true("a Lhykhis-led unit IS", ea.applies(led))
checks.true("it can use Flickerjump too", fj2.use(led))
checks.eq("...and the charge is NOT locked", led.charge_locked_until_end_of_turn, False)
checks.true("...while the 24\" Move half still applies", led.flickerjump_active)

# Read it back through the real gate, not just the flag. Each unit has its own
# enemy 8" away, so rule 11.02's other conditions are satisfied for both and the
# lock is the only difference.
plain_gate = ChargeController(turn_tracker=tt, all_tokens=plain_tokens, game_log=log)
led_gate = ChargeController(turn_tracker=tt2, all_tokens=led_tokens, game_log=log2)
checks.eq("can_declare_charge() refuses the plain unit after Flickerjump",
          plain_gate.can_declare_charge(plain, ignore_phase=True), False)
checks.true("...and allows the Lhykhis-led one",
            led_gate.can_declare_charge(led, ignore_phase=True))

# It cancels ONLY Flickerjump's lock. Something else locking the unit still does.
also_disembarked, fj3, _, _, _ = flickerjump_scene(led=True)
also_disembarked.charge_locked_until_end_of_turn = True   # e.g. rule 18.04/18.05
fj3.use(also_disembarked)
checks.true("a led unit that ALSO disembarked still cannot charge",
            also_disembarked.charge_locked_until_end_of_turn)

# 19.04: it ends with her.
dying, fj4, _, _, _ = flickerjump_scene(led=True)
for m in dying.models:
    if getattr(m.profile, "empyric_ambush", False):
        m.current_wounds = 0
checks.eq("with her dead the unit is no longer led by her", ea.applies(dying), False)
checks.eq("a lone Lhykhis leads nobody", ea.applies(lhykhis()), False)


# --- 4. Whispering Web -----------------------------------------------------
print("--- 4. Whispering Web ---")

web_log = tk.Log()
web = ww.WhisperingWebController(game_log=web_log)
shooter = spiders(name="1 Warp Spiders 4")
lord = lhykhis(name="1 Lhykhis 4")
tk.line_up(shooter, x=20.0, y=20.0)
tk.line_up(lord, x=20.0, y=18.5)
attach(lord, shooter)
hit = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 1")
other = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 2")

checks.eq("nothing is marked to start with", web.marked_by("Player 1"), set())
# One unit hit -> taken without asking (nothing to choose, no reason to decline).
web.offer_after_shooting(shooter, [hit])
checks.true("one unit hit is marked without a prompt", hit in web.marked_by("Player 1"))
checks.true("logged", any("Whispering Web" in line for line in web_log.lines))
checks.true("a friendly AELDARI unit attacking it is covered", web.applies(shooter, hit))
checks.eq("...but not against an unmarked unit", web.applies(shooter, other), False)
checks.eq("a non-AELDARI friendly unit gets nothing",
          web.applies(tk.build(tau.STRIKE_TEAM, "Player 1", name="1 Strike Team 3"), hit), False)
checks.eq("and the enemy's own attacks get nothing", web.applies(hit, hit), False)
checks.eq("it ends at end of turn", (web.reset_turn(), web.marked_by("Player 1"))[1], set())

# A unit without her never marks anything.
plain_shooter = spiders(name="1 Warp Spiders 5")
web.offer_after_shooting(plain_shooter, [hit])
checks.eq("a unit she does not lead marks nothing", web.marked_by("Player 1"), set())
# Nothing hit -> nothing marked, even for her.
web.offer_after_shooting(shooter, [])
checks.eq("and hitting nothing marks nothing", web.marked_by("Player 1"), set())

# Several hit -> a real choice.
from game.decision import DecisionManager  # noqa: E402

dm = DecisionManager()
web2 = ww.WhisperingWebController(decision_manager=dm, game_log=web_log)
web2.offer_after_shooting(shooter, [hit, other])
checks.true("two units hit raises a choice", dm.is_pending)
checks.eq("...owned by her controller", dm.player, "Player 1")
checks.eq("...with one option per unit hit", len(dm.options), 2)
dm.choose(1)
checks.eq("choosing marks exactly one", len(web2.marked_by("Player 1")), 1)


# --- 5. the crit threshold, read from the engine's own lookup --------------
print("--- 5. the crit threshold ---")

checks.eq("default is rule 05.02's 6", crit_hit.DEFAULT_CRIT_HIT_THRESHOLD, 6)
web3 = ww.WhisperingWebController()
web3.mark("Player 1", hit)
model = shooter.models[0]
checks.eq("unmarked: 6", crit_hit.crit_hit_threshold(model, other, web3), 6)
checks.eq("marked: 5, in the SHOOTING step (melee_only=False)",
          crit_hit.crit_hit_threshold(model, hit, web3), 5)
checks.eq("...and in the Fight step too",
          crit_hit.crit_hit_threshold(model, hit, web3, melee_only=True), 5)
# The two melee-worded sources stayed melee-only.
boyz = tk.build(__import__("game.factions.orks", fromlist=["BOYZ"]).BOYZ, "Player 2", name="2 Boyz 1")
boyz.unbridled_carnage_active = True
checks.eq("Unbridled Carnage does NOT reach a ranged attack",
          crit_hit.crit_hit_threshold(boyz.models[0]), 6)
checks.eq("...but does in the Fight phase",
          crit_hit.crit_hit_threshold(boyz.models[0], melee_only=True), 5)
checks.eq("no model degrades to the default", crit_hit.crit_hit_threshold(None), 6)


# --- 6. end to end, both phases, identical dice ---------------------------
print("--- 6. end to end ---")


def crits_from_shooting(marked):
    """One activation of an AELDARI unit, counting the critical hits the ENGINE
    scored. A 5 is an ordinary hit on a 3+ weapon and a CRITICAL only under
    Whispering Web - so the difference is entirely the ability.

    Guardian Defenders rather than the Warp Spiders she actually leads: their
    Death Spinner is [TORRENT], which makes no hit roll at all, so there would
    be nothing to measure. Her own Brood Twain has the same problem - the
    ability is army-wide, and this is what benefits from it."""
    web_ctrl = ww.WhisperingWebController()
    sc = tk.shooting_scene(ae.GUARDIAN_DEFENDERS, tau.STRIKE_TEAM, attacker_owner="Player 1",
                           gap=6.0, whispering_web=web_ctrl)
    if marked:
        web_ctrl.mark("Player 1", sc["target"])
    script(*([5] * 40), default=5)
    sc["shooting"].start_shooting(sc["attacker"])
    sc["shooting"].choose_target_squad(sc["target"])
    key = sc["shooting"].weapon_eligibility()[0][0]
    sc["shooting"].choose_weapon(key)
    sc["dice"].acknowledge()
    sc["shooting"].on_dice_acknowledged()
    return [line for line in sc["log"].lines if "hit roll" in line]


plain_lines = crits_from_shooting(False)
web_lines = crits_from_shooting(True)
checks.true("the shooting hit roll happened", bool(plain_lines) and bool(web_lines))
checks.true("unmarked: no critical hits from a roll of 5s",
            "of which 0 critical" in plain_lines[0])
checks.eq("marked: every 5 is a critical instead",
          "of which 0 critical" in web_lines[0], False)


def crits_from_fight(marked):
    web_ctrl = ww.WhisperingWebController()
    sc = tk.fight_scene(ae.GUARDIAN_DEFENDERS, tau.STRIKE_TEAM, attacker_owner="Player 1",
                        whispering_web=web_ctrl)
    if marked:
        web_ctrl.mark("Player 1", sc["target"])
    script(*([5] * 40), default=5)
    sc["fight"].select_to_fight(sc["attacker"])
    if sc["fight"].state == "choosing_target":
        sc["fight"].choose_target_squad(sc["target"])
    key = sc["fight"].weapon_eligibility()[0][0]
    sc["fight"].choose_weapon(key)
    sc["dice"].acknowledge()
    sc["fight"].on_dice_acknowledged()
    return [line for line in sc["log"].lines if "hit roll" in line]


f_plain = crits_from_fight(False)
f_web = crits_from_fight(True)
checks.true("the melee hit roll happened", bool(f_plain) and bool(f_web))
checks.true("unmarked in the Fight phase: no criticals",
            "of which 0 critical" in f_plain[0])
checks.eq("marked in the Fight phase: criticals",
          "of which 0 critical" in f_web[0], False)


# --- 7. the board labels ---------------------------------------------------
print("--- 7. board labels ---")

from game import doom as dm_mod  # noqa: E402
from game import guide as gd_mod  # noqa: E402
from game.renderer import STATUS_LABEL_COLORS  # noqa: E402

for key, label in ((status_effects.GUIDED, "GD"), (status_effects.DOOMED, "DM"),
                   (status_effects.WEBBED, "WW")):
    checks.eq(f"{key} shows as a two-letter label", status_effects.LABELS[key], label)
    checks.eq("...two characters exactly", len(status_effects.LABELS[key]), 2)
    checks.true("...and it has a colour", key in STATUS_LABEL_COLORS)

marks = {"guide": gd_mod.GuideController(), "doom": dm_mod.DoomController(),
         "whispering_web": ww.WhisperingWebController()}
victim = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 9")
tk.line_up(victim, x=20.0, y=40.0)
tt3 = tk._tracker(PHASE_MOVEMENT, owner="Player 1")
checks.eq("unmarked: no label",
          [e for e in status_effects.active_effects(victim.models[0], [], tt3, {}, **marks)
           if e in (status_effects.GUIDED, status_effects.DOOMED, status_effects.WEBBED)], [])
for name, key in (("guide", status_effects.GUIDED), ("doom", status_effects.DOOMED),
                  ("whispering_web", status_effects.WEBBED)):
    marks[name].mark("Player 1", victim)
    effects = status_effects.active_effects(victim.models[0], [], tt3, {}, **marks)
    checks.true(f"{name} shows up once marked", key in effects)
checks.eq("all three stack on one unit",
          len([e for e in status_effects.active_effects(victim.models[0], [], tt3, {}, **marks)
               if e in (status_effects.GUIDED, status_effects.DOOMED, status_effects.WEBBED)]), 3)


# --- 8. sprite -------------------------------------------------------------
print("--- 8. sprite ---")

checks.eq("her own art, under the folder's spelling", _squad_key(lhykhis().models[0]), "Lykhis")


# --- 9. A/B probes ---------------------------------------------------------
print("--- 9. A/B probes ---")

# Without Empyric Ambush, Flickerjump locks the charge again.
probe_body, probe_fj, _, _, _ = flickerjump_scene(led=True)
for m in probe_body.models:
    if getattr(m.profile, "empyric_ambush", False):
        m.profile = copy.copy(m.profile)
        m.profile.empyric_ambush = False
probe_fj.use(probe_body)
checks.true("A/B: without the ability the charge is locked again",
            probe_body.charge_locked_until_end_of_turn)

# Without the whispering_web flag she marks nothing.
probe_web = ww.WhisperingWebController()
probe_shooter = spiders(name="1 Warp Spiders 9")
probe_lord = lhykhis(name="1 Lhykhis 9")
tk.line_up(probe_shooter, x=30.0, y=20.0)
tk.line_up(probe_lord, x=30.0, y=18.5)
attach(probe_lord, probe_shooter)
probe_web.offer_after_shooting(probe_shooter, [hit])
checks.true("A/B: with the flag she marks", hit in probe_web.marked_by("Player 1"))
probe_web.reset_turn()
for m in probe_shooter.models:
    if getattr(m.profile, "whispering_web", False):
        m.profile = copy.copy(m.profile)
        m.profile.whispering_web = False
probe_web.offer_after_shooting(probe_shooter, [hit])
checks.eq("A/B: without it she does not", probe_web.marked_by("Player 1"), set())

checks.finish()
