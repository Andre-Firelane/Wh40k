"""Windriders - statline, weapons, wargear, and Swift Demise, which is the
only real work here.

SWIFT DEMISE IS AN EITHER/OR, and that word is what the suite is built around:

    "Each time a model in this unit makes a ranged attack, re-roll a Hit roll
     of 1. If the target of that attack is the closest eligible target, you can
     re-roll the Hit roll instead."

  * against any target: the 1s are re-rolled, automatically ("re-roll", not
    "you can").
  * against the CLOSEST eligible target: the whole roll may be re-rolled
    INSTEAD - so the automatic throw is held back and the player picks one of
    the two. Never both.

Every check below goes through the real ShootingController, because the
difference between "both" and "one or the other" is invisible from the flag.
"""

import testkit as tk
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game import swift_demise
from game.units import WindriderProfile

checks = tk.Checks("Windriders")

LINE = "Windrider"


def riders(choices=None, composition_index=0):
    return tk.build(ae.WINDRIDERS, "Player 1", name="1 Windriders 1",
                    choices=choices, composition_index=composition_index)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

three = riders()
six = riders(composition_index=1)
checks.eq("3 models", len(three.models), 3)
checks.eq("6 models", len(six.models), 6)
checks.eq("...cost 80", three.points, 80)
checks.eq("...and 170", six.points, 170)

p = WindriderProfile()
checks.eq("M14\"", p.movement_in, 14)
checks.eq("T4", p.toughness, 4)
checks.eq("Sv4+", p.armor_save, "4+")
checks.eq("W2", p.wounds, 2)
checks.eq("Ld7+", p.leadership, "7+")
checks.eq("OC2", p.oc, 2)
checks.eq("BS3+ / WS3+", (p.ballistic_skill, p.weapon_skill), ("3+", "3+"))
# The first reading of the statline produced a spurious 6+ invulnerable; a
# second targeted lookup confirmed there is none. Pinned because it is a value
# that would otherwise land as dice results.
checks.eq("NO invulnerable save at all", p.invulnerable_save, "-")
checks.eq("32 mm flying base -> 0.630\"", p.base_radius_in, round(32 / 2 / 25.4, 3))
checks.true("MOUNTED on the keyword line", "MOUNTED" in ae.WINDRIDERS.keywords)
checks.true("FLY too", "FLY" in ae.WINDRIDERS.keywords)
checks.eq("NOT infantry", p.infantry, False)
checks.true("...so the FLY flag is set (21.03)", p.fly)
checks.true("Battle Focus", p.battle_focus)
checks.eq("no LEADER ability", getattr(p, "leader", False), False)
checks.eq("no Aspect Shrine (it is not an ASPECT WARRIORS datasheet)",
          getattr(p, "aspect_shrine", False), False)


# --- 2. weapons and wargear -------------------------------------------------
print("--- 2. weapons and wargear ---")


def loadout(squad, model_index=0):
    return sorted(w.name for w in squad.models[model_index].weapons)


checks.eq("default: twin shuriken catapult + close combat weapon",
          loadout(three), ["Close Combat Weapon", "Twin Shuriken Catapult"])
ccw = next(w for w in three.models[0].weapons if w.weapon_type == "melee")
checks.eq("the close combat weapon is A3/S3/AP0/D1",
          (ccw.attacks, ccw.strength, ccw.ap, ccw.damage), (3, 3, 0, 1))
# A FOURTH Aeldari "Close combat weapon" row - the three already here are
# A1/S3, A2/S3 and A3/S5, so this one needed its own class.
checks.eq("...its own class, not one of the three existing Aeldari rows",
          type(ccw).__name__, "AeldariCloseCombatWeaponA3Profile")

catapult = next(w for w in three.models[0].weapons if w.name == "Twin Shuriken Catapult")
checks.eq("the twin shuriken catapult is the shared profile",
          type(catapult).__name__, "TwinShurikenCatapultProfile")

# "Any number of models can each have their twin shuriken catapult replaced
# with ONE of the following" - both alternatives give up the SAME weapon, so
# they share a cursor and land on different models rather than stacking.
mixed = riders(composition_index=1, choices={LINE: {ae.WINDRIDER_TO_SCATTER_LASER: 2,
                                                    ae.WINDRIDER_TO_SHURIKEN_CANNON: 2}})
guns = sorted(w.name for m in mixed.models for w in m.weapons if w.weapon_type == "ranged")
checks.eq("2 scatter lasers + 2 shuriken cannons + 2 untouched catapults",
          guns, ["Scatter Laser"] * 2 + ["Shuriken Cannon"] * 2 + ["Twin Shuriken Catapult"] * 2)
checks.eq("...and no model carries two guns",
          max(len([w for w in m.weapons if w.weapon_type == "ranged"]) for m in mixed.models), 1)
all_lasers = riders(composition_index=1, choices={LINE: {ae.WINDRIDER_TO_SCATTER_LASER: 6}})
checks.eq("\"any number\" really means all six",
          [w.name for m in all_lasers.models for w in m.weapons if w.weapon_type == "ranged"],
          ["Scatter Laser"] * 6)
laser = next(w for w in all_lasers.models[0].weapons if w.name == "Scatter Laser")
checks.eq("Scatter Laser: 36\"/A6/S5/AP0/D1",
          (laser.range_in, laser.attacks, laser.strength, laser.ap, laser.damage),
          (36, 6, 5, 0, 1))
checks.eq("...[SUSTAINED HITS 1]", laser.sustained_hits, 1)
checks.eq("...the shared profile, not a new one", type(laser).__name__, "ScatterLaserProfile")


# --- 3. Swift Demise: which half applies ------------------------------------
print("--- 3. Swift Demise: which half ---")


def scene():
    """Windriders with TWO enemy units in range - one near, one far - so
    "closest eligible target" is a real distinction rather than a formality."""
    s = tk.shooting_scene(ae.WINDRIDERS, tau.KROOT_CARNIVORES,
                          attacker_owner="Player 1", gap=8.0)
    # Far enough to be a different distance, close enough that the 18" twin
    # shuriken catapult still makes it an ELIGIBLE target - which is the whole
    # point of the comparison. (A first version put it 2" away, where rule
    # 03.04 makes it engaged and so not a target at all.)
    far = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 1")
    tk.line_up(far, y=34.0)
    for model in far.models:
        s["state"].add_token(model)
    s["shooting"].all_tokens = s["state"].tokens
    s["far"] = far
    return s


sc = scene()
sc["shooting"].active_squad = sc["attacker"]
checks.true("the unit has the ability", swift_demise.applies(sc["attacker"]))
eligible = sc["shooting"]._eligible_target_squads()
checks.eq("both enemy units are eligible targets", len(eligible), 2)
checks.true("...and they are at different distances",
            sc["attacker"].min_distance_to(sc["target"])
            != sc["attacker"].min_distance_to(sc["far"]))
checks.eq("the whole-roll half is offered against the CLOSEST target",
          sc["shooting"]._hit_reroll_reason(sc["target"]), swift_demise.SWIFT_DEMISE_LABEL)
checks.eq("...and not against the far one", sc["shooting"]._hit_reroll_reason(sc["far"]), None)
# ...but the ability itself still applies there - it is the 1s half that runs.
checks.true("the unit still has Swift Demise against the far target",
            swift_demise.applies(sc["attacker"]))
checks.eq("with only one candidate, the target shot at IS the closest",
          swift_demise.is_closest_target(sc["attacker"], sc["far"], [sc["far"]]), True)
checks.eq("ties count as closest",
          swift_demise.is_closest_target(sc["attacker"], sc["target"], [sc["target"], sc["target"]]),
          True)
# And nothing else in the game picked it up.
checks.eq("no other datasheet has it",
          swift_demise.applies(tk.build(tau.KROOT_CARNIVORES, "Player 2", name="K")), False)


# --- 4. Swift Demise end to end ---------------------------------------------
print("--- 4. Swift Demise end to end ---")


def shoot(target_key, hit_dice):
    """Drive a real activation up to the point where the hit roll resolves."""
    s = scene()
    sc_ = s["shooting"]
    target = s[target_key]
    sc_.start_shooting(s["attacker"])
    sc_.choose_target_squad(target)
    groups = sc_.weapon_eligibility()
    assert groups, "no weapon group"
    tk.script(*hit_dice, default=6)
    sc_.choose_weapon(groups[0][0])
    s["dice"].acknowledge()
    sc_.on_dice_acknowledged()
    return s


# (a) NOT the closest target: the 1s go automatically, with no decision.
away = shoot("far", [1, 1, 6, 6, 6, 6])
checks.eq("far target: no decision is raised", away["decision"].is_pending, False)
checks.true("...the 1s were thrown automatically",
            "re-roll of 1s" in (away["dice"].label or ""))
checks.true("...and the roll is named Swift Demise, not Forward Observers",
            swift_demise.SWIFT_DEMISE_LABEL in (away["dice"].label or ""))
checks.eq("...over exactly the two 1s", len(away["dice"].pending_values or []), 2)

# (b) THE closest target: a decision, and it is the either/or.
near = shoot("target", [1, 1, 6, 6, 6, 6])
checks.true("closest target: a decision IS raised", near["decision"].is_pending)
labels = tk.options_of(near["decision"])
checks.true("...offering the whole roll", any("whole Hit roll" in l for l in labels))
checks.true("...and the 1s only", any("1s only" in l for l in labels))
# The 1s re-roll is MANDATORY, so declining altogether is not a legal answer -
# this is the one re-roll offer in the engine without a "Keep result".
checks.eq("...and NOT 'Keep result' - the 1s re-roll is not optional",
          [l for l in labels if "Keep" in l], [])
checks.eq("...exactly two options", len(labels), 2)
checks.true("...the 1s option names how many", any("(2 dice)" in l for l in labels))

# Taking the 1s option throws exactly those dice.
tk.script(6, 6, default=6)
tk.pick_option(near["decision"], "1s only")
checks.eq("choosing the 1s throws 2 dice", len(near["dice"].pending_values or []), 2)

# Taking the whole roll instead throws every still-free die.
whole = shoot("target", [1, 1, 6, 6, 6, 6])
tk.script(default=6)
tk.pick_option(whole["decision"], "whole Hit roll")
checks.eq("choosing the whole roll throws all 6", len(whole["dice"].pending_values or []), 6)

# (c) No 1s at all: nothing is mandatory, so it behaves like every other
# optional re-roll and "Keep result" comes back.
clean = shoot("target", [6, 6, 6, 6, 6, 6])
checks.true("no 1s: a decision is still raised (the whole-roll half)",
            clean["decision"].is_pending)
clean_labels = tk.options_of(clean["decision"])
checks.true("...with 'Keep result' back", any("Keep" in l for l in clean_labels))
checks.eq("...and no 1s option", [l for l in clean_labels if "1s only" in l], [])


# --- 5. A/B probe -----------------------------------------------------------
print("--- 5. A/B probe ---")

# With the ability neutralised the same activation raises nothing and throws no
# extra dice - without this the checks above would only prove that the scene
# has two enemy units in it.
original = swift_demise.applies
swift_demise.applies = lambda squad: False
probe_far = shoot("far", [1, 1, 6, 6, 6, 6])
probe_near = shoot("target", [1, 1, 6, 6, 6, 6])
checks.eq("A/B: unwired, the far shot re-rolls nothing",
          "re-roll of 1s" in (probe_far["dice"].label or ""), False)
checks.eq("A/B: ...and the closest shot raises no decision",
          probe_near["decision"].is_pending, False)
swift_demise.applies = original
restored = shoot("target", [1, 1, 6, 6, 6, 6])
checks.true("A/B: restored", restored["decision"].is_pending)


# --- 6. sprite --------------------------------------------------------------
print("--- 6. sprite ---")

from game import sprites  # noqa: E402

# Art arrived after the datasheet was built. Checked at the model, not at the
# mapping table: a key that resolves to no file on disk is exactly the failure
# this is here to catch.
checks.true("Windriders resolve a sprite", sprites.sprite_for(three.models[0]))
checks.true("...and it is the Windrider file (the datasheet is plural, the file is not)",
            "Windrider" in (sprites.sprite_for(three.models[0]) or ""))


checks.finish()
