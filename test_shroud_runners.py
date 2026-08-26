"""Shroud Runners - statline, weapons, and Target Acquisition.

TARGET ACQUISITION IS THE ONE COVER-BYPASSING SOURCE IN THIS ENGINE THAT MARKS
THE TARGET rather than granting something to the shooter:

    "In your Shooting phase, after this unit has shot, select one enemy unit hit
     by one or more of those attacks made with a long rifle. Until the end of
     the phase, that enemy unit cannot have the Benefit of Cover."

So the mark holds against attacks from the WHOLE army for the rest of the
phase, not just from the Shroud Runners - and that is what the checks below
measure, through the real _cover_ignored_for_group().

The "made with a long rifle" qualifier is the part that needed new plumbing:
the on_squad_finished_shooting hook reports which UNITS were hit, not which
weapon hit them.
"""

import testkit as tk
from game import invulnerable_save as inv
from game import target_acquisition as ta
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.units import ShroudRunnerProfile

checks = tk.Checks("Shroud Runners")


def runners(composition_index=0, name="1 Shroud Runners 1"):
    return tk.build(ae.SHROUD_RUNNERS, "Player 1", name=name,
                    composition_index=composition_index)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

three = runners()
six = runners(composition_index=1)
checks.eq("3 models", len(three.models), 3)
checks.eq("6 models", len(six.models), 6)
checks.eq("...cost 90", three.points, 90)
checks.eq("...and 175", six.points, 175)

p = ShroudRunnerProfile()
checks.eq("M14\"", p.movement_in, 14)
checks.eq("T4", p.toughness, 4)
checks.eq("Sv5+", p.armor_save, "5+")
checks.eq("W3", p.wounds, 3)
checks.eq("Ld7+", p.leadership, "7+")
checks.eq("OC2", p.oc, 2)
checks.eq("BS2+ / WS3+", (p.ballistic_skill, p.weapon_skill), ("2+", "3+"))
# ON-TABLE SIZE, not the printed base - a user call, so it is pinned as one
# rather than as arithmetic off the datasheet. The three MOUNTED jetbike units
# in the roster (Shining Spears, Shroud Runners, Warlock Skyrunners) were set to
# match EACH OTHER at 45 mm: the first two came down a quarter from 60 mm, the
# Skyrunner came up from 32 mm. Checked against the other two rather than
# against a literal, so the three cannot drift apart unnoticed.
from game.units import ShiningSpearProfile, WarlockSkyrunnerProfile  # noqa: E402
checks.eq("45 mm on the table (printed base is 60 mm)",
          p.base_radius_in, round(45 / 2 / 25.4, 3))
checks.eq("...the same as the Shining Spears", p.base_radius_in, ShiningSpearProfile.base_radius_in)
checks.eq("...and the same as the Warlock Skyrunner",
          p.base_radius_in, WarlockSkyrunnerProfile.base_radius_in)
checks.true("MOUNTED on the keyword line", "MOUNTED" in ae.SHROUD_RUNNERS.keywords)
checks.true("FLY", "FLY" in ae.SHROUD_RUNNERS.keywords)
checks.eq("NOT infantry", p.infantry, False)
checks.true("...so the FLY flag is set (21.03)", p.fly)
checks.true("Battle Focus", p.battle_focus)
checks.eq("CORE: Scouts 9\"", p.scouts, 9.0)
checks.true("CORE: Stealth (24.33)", p.stealth)
checks.eq("no wargear options at all", list(ae.SHROUD_RUNNERS.wargear_options), [])
checks.eq("no LEADER ability", getattr(p, "leader", False), False)

# The longest Scout move in the engine - compared rather than asserted flat,
# so a later datasheet that beats it shows up here.
others = [tk.build(sheet, "Player 1", name="1 %s 1" % sheet.name).models[0].profile.scouts
          for sheet in (ae.STRIKING_SCORPIONS, ae.RANGERS)]
checks.true("...longer than the Striking Scorpions' 7\"",
            p.scouts > (others[0] or 0))
# ...and unlike the Rangers they come from, no Infiltrators.
checks.eq("NO Infiltrators, unlike Rangers", p.infiltrators, False)
checks.true("...while Rangers do have it",
            tk.build(ae.RANGERS, "Player 1", name="1 Rangers 1").models[0].profile.infiltrators)

# Ranged-only invulnerable save, same clause as the Rangers.
checks.eq("no plain invulnerable save", p.invulnerable_save, "-")
checks.eq("5+ against ranged", inv.effective_invulnerable_save(three.models[0], melee=False), "5+")
checks.eq("...nothing against melee", inv.effective_invulnerable_save(three.models[0], melee=True), "-")


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")


def weapon(squad, name):
    return next(w for w in squad.models[0].weapons if w.name == name)


checks.eq("four weapons, every model identically equipped",
          sorted(w.name for w in three.models[0].weapons),
          ["Close Combat Weapon", "Long Rifle", "Scatter Laser", "Shuriken Pistol"])
checks.eq("...and every model really is identical",
          len({tuple(sorted(w.name for w in m.weapons)) for m in six.models}), 1)

rifle = weapon(three, "Long Rifle")
checks.eq("Long Rifle: 36\"/A1/S4/AP-1/D2",
          (rifle.range_in, rifle.attacks, rifle.strength, rifle.ap, rifle.damage),
          (36, 1, 4, -1, 2))
checks.true("...[PRECISION]", rifle.precision)
checks.eq("...but NOT [HEAVY]", rifle.heavy, False)
checks.eq("...BS2+", rifle.ballistic_skill, "2+")

laser = weapon(three, "Scatter Laser")
checks.eq("Scatter Laser: [SUSTAINED HITS 1]", laser.sustained_hits, 1)
# The model is BS2+ and the printed row is 3+, so it cannot defer - the same
# call the Dark Reapers' Reaper Launcher needed, in the other direction.
checks.eq("...printed at BS3+, worse than the model that fires it",
          laser.ballistic_skill, "3+")
checks.true("...so it is NOT the shared Scatter Laser profile",
            type(laser).__name__ == "ShroudRunnerScatterLaserProfile")

pistol = weapon(three, "Shuriken Pistol")
checks.eq("the Shuriken Pistol IS the shared profile - BS2+ is the model's own",
          type(pistol).__name__, "ShurikenPistolProfile")
checks.eq("...so it defers", pistol.ballistic_skill, None)


# --- 3. Target Acquisition ---------------------------------------------------
print("--- 3. Target Acquisition ---")

checks.true("the profile carries the ability", p.target_acquisition)
checks.eq("...and nothing else does",
          ta.applies(tk.build(tau.KROOT_CARNIVORES, "Player 2", name="K")), False)


def scene():
    s = tk.shooting_scene(ae.SHROUD_RUNNERS, tau.KROOT_CARNIVORES, attacker_owner="Player 1")
    ctrl = ta.TargetAcquisitionController(decision_manager=s["decision"], game_log=s["log"])
    s["shooting"].target_acquisition = ctrl
    s["ta"] = ctrl
    return s


# The effect, measured through the REAL cover check - and the mark is on the
# TARGET, so a completely different shooter sees it too.
s = scene()
sc, target = s["shooting"], s["target"]
sc.active_squad = s["attacker"]
gun = weapon(s["attacker"], "Shuriken Pistol")   # no [IGNORES COVER] of its own
checks.eq("before the mark, cover applies normally",
          sc._cover_ignored_for_group(gun, target), False)
s["ta"].offer_after_shooting(s["attacker"], {target}, long_rifle_hits={target})
checks.true("the unit is marked", s["ta"].is_marked(target))
checks.true("...and now cover is bypassed", sc._cover_ignored_for_group(gun, target))

# The mark belongs to the TARGET: another unit's shooting sees it too.
other = tk.shooting_scene(tau.STRIKE_TEAM, tau.KROOT_CARNIVORES, attacker_owner="Player 2")
other["shooting"].target_acquisition = s["ta"]
other["shooting"].active_squad = other["attacker"]
other_gun = next(w for w in other["attacker"].models[0].weapons if w.name == "Pulse Rifle")
checks.eq("A DIFFERENT unit shooting a DIFFERENT target is unaffected",
          other["shooting"]._cover_ignored_for_group(other_gun, other["target"]), False)
# ...and marking that one shows the mark really is per target unit.
s["ta"].offer_after_shooting(s["attacker"], {other["target"]},
                             long_rifle_hits={other["target"]})
checks.true("...until it is marked itself",
            other["shooting"]._cover_ignored_for_group(other_gun, other["target"]))

# "until the end of the phase"
s["ta"].reset_phase()
checks.eq("the phase ends and the mark goes with it", s["ta"].is_marked(target), False)
checks.eq("...for every marked unit", s["ta"].is_marked(other["target"]), False)

# The QUALIFIER: only a unit hit by a LONG RIFLE attack may be picked.
q = scene()
q["ta"].offer_after_shooting(q["attacker"], {q["target"]}, long_rifle_hits=set())
checks.eq("a unit hit only by other weapons is NOT marked",
          q["ta"].is_marked(q["target"]), False)
checks.eq("...and no decision is raised for it", q["decision"].is_pending, False)

# One candidate -> taken silently; several -> the player picks.
one = scene()
one["ta"].offer_after_shooting(one["attacker"], {one["target"]}, long_rifle_hits={one["target"]})
checks.eq("one candidate is taken without interrupting", one["decision"].is_pending, False)
checks.true("...and it is marked", one["ta"].is_marked(one["target"]))

many = scene()
second = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 1")
many["ta"].offer_after_shooting(many["attacker"], {many["target"], second},
                                long_rifle_hits={many["target"], second})
checks.true("two candidates raise a decision", many["decision"].is_pending)
checks.eq("...owned by the shooting player", many["decision"].player, "Player 1")
checks.eq("...with one option each", len(tk.options_of(many["decision"])), 2)
tk.pick_option(many["decision"], second.name)
checks.true("...and the chosen one is marked", many["ta"].is_marked(second))
checks.eq("...only that one", many["ta"].is_marked(many["target"]), False)

# A unit without the ability does nothing at all.
plain = tk.shooting_scene(tau.STRIKE_TEAM, tau.KROOT_CARNIVORES, attacker_owner="Player 2")
plain_ctrl = ta.TargetAcquisitionController(decision_manager=plain["decision"])
plain_ctrl.offer_after_shooting(plain["attacker"], {plain["target"]},
                                long_rifle_hits={plain["target"]})
checks.eq("a unit without Target Acquisition marks nothing",
          plain_ctrl.is_marked(plain["target"]), False)


# --- 4. the per-weapon hit record --------------------------------------------
print("--- 4. the per-weapon hit record ---")

# The plumbing the qualifier needed: which WEAPON hit, not just which unit.
live = tk.shooting_scene(ae.SHROUD_RUNNERS, tau.KROOT_CARNIVORES, attacker_owner="Player 1")
lsc = live["shooting"]
lsc.start_shooting(live["attacker"])
lsc.choose_target_squad(live["target"])
groups = lsc.weapon_eligibility()
assert groups, "no weapon group"
label = groups[0][1]
tk.script(default=6)                      # everything hits
lsc.choose_weapon(groups[0][0])
live["dice"].acknowledge()
lsc.on_dice_acknowledged()
hit_by = lsc.squads_hit_by_weapon(label if label in ("Long Rifle",) else label)
checks.true("the controller records which weapon hit which unit",
            live["target"] in lsc._hit_target_squads_this_activation)
checks.eq("...by name", lsc.squads_hit_by_weapon("Definitely Not A Weapon"), [])
checks.true("...and the fired weapon's own name finds it",
            live["target"] in lsc.squads_hit_by_weapon(label))
checks.eq("LONG_RIFLE_NAME is what the ability looks for", ta.LONG_RIFLE_NAME, "Long Rifle")


# --- 5. A/B probe -------------------------------------------------------------
print("--- 5. A/B probe ---")

original = ta.applies
ta.applies = lambda squad: False
probe = scene()
probe["ta"].offer_after_shooting(probe["attacker"], {probe["target"]},
                                 long_rifle_hits={probe["target"]})
checks.eq("A/B: unwired, nothing is marked", probe["ta"].is_marked(probe["target"]), False)
probe_sc = probe["shooting"]
probe_sc.active_squad = probe["attacker"]
checks.eq("A/B: ...so cover still applies",
          probe_sc._cover_ignored_for_group(weapon(probe["attacker"], "Shuriken Pistol"),
                                            probe["target"]), False)
ta.applies = original
restored = scene()
restored["ta"].offer_after_shooting(restored["attacker"], {restored["target"]},
                                    long_rifle_hits={restored["target"]})
checks.true("A/B: restored", restored["ta"].is_marked(restored["target"]))


# --- 6. sprite ----------------------------------------------------------------
print("--- 6. sprite ---")

from game import sprites  # noqa: E402

# Art arrived after the datasheet was built. Checked at the model, not at the
# mapping table: a key that resolves to no file on disk is exactly the failure
# this is here to catch.
checks.true("Shroud Runners resolve a sprite", sprites.sprite_for(three.models[0]))
checks.true("...and it is the Shroud Runners file",
            "Shroud Runners" in (sprites.sprite_for(three.models[0]) or ""))


checks.finish()
