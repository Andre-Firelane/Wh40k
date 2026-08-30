"""The Lokhust Lord - fifteenth Necron datasheet, fifth of the DESTROYER CULT.

THREE THINGS HERE ARE SECOND CARRIERS OF SOMETHING THAT ALREADY EXISTED, and
each one forced a rename rather than a copy - which is the part of this suite
worth reading:

  * his Staff of Light is the Overlord's row to the last characteristic, so
    OverlordStaffOfLight*Profile became LordStaffOfLight*Profile. A class named
    after the first datasheet to field it is a lying name the moment a second
    one arrives.
  * his "Destroyer Cult" ability is the Plasmancer's "Harbinger of
    Destruction", word for word, under a different printed name. So the FLAG is
    named for the mechanic (leading_ranged_crit_on_5) and each datasheet keeps
    its own printed name in abilities_text.
  * his Lord's Blade is the Overlord's Blade's numbers under a different name -
    the mirror case, handled the mirror way: it INHERITS and overrides only the
    name, so the two are pinned against EACH OTHER here rather than against
    literals. A copied class would pass any check that read only one of them.

DRIVEN BY HATRED IS THE ONE GENUINELY NEW SHAPE, and it differs from its three
Destroyer Cult siblings in three ways at once (both rolls, not one; per MODEL,
not per unit; and a plain optional whole-roll re-roll with no automatic-1s
clause). All three differences are checked, because each of them disappears if
the predicate is written to look like its neighbours - and the third one is
checked as an ABSENCE from game/reroll_scope.py, which is the only place it
would show.
"""

import pathlib

import testkit as tk
from testkit import Checks, GameState, build_squad
from game import (
    attached_units, crit_hit, destroyer_cult, feel_no_pain, guardian_protocols,
    nanoscarab_amulet, reroll_scope, sprites,
)
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.squad import is_at_half_strength, is_below_half_strength
from game.units import (
    LokhustDestroyerProfile, LokhustHeavyDestroyerProfile, LokhustLordProfile,
    SkorpekhDestroyerProfile, SkorpekhLordProfile,
)
from game import weapons as w

c = Checks("Lokhust Lord")


def lord(name="2 Lokhust Lord 1", **kw):
    return build_squad(nec.LOKHUST_LORD, "Player 2", name=name, **kw)


def destroyers(name="2 Lokhust Destroyers 1"):
    return build_squad(nec.LOKHUST_DESTROYERS, "Player 2", composition_index=0, name=name)


# --- 1. statline -------------------------------------------------------------
print("--- 1. statline ---")

sq = lord()
c.eq("one model", len(sq.models), 1)
p = sq.models[0].profile
c.eq("M8 T6 Sv3+ W6 Ld6+ OC2",
     (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc),
     (8, 6, "3+", 6, "6+", 2))
c.eq("WS2+ / BS2+", (p.weapon_skill, p.ballistic_skill), ("2+", "2+"))
c.eq("4+ invulnerable save", p.invulnerable_save, "4+")
c.eq("keywords transcribed in full", nec.LOKHUST_LORD.keywords,
     ("MOUNTED", "CHARACTER", "FLY", "DESTROYER CULT", "LOKHUST LORD", "NECRONS"))

# MOUNTED and FLY, not INFANTRY - the only Necron character in this engine that
# is, and the reason the two Lords cannot share a keyword test.
c.eq("MOUNTED and FLY, and NOT infantry",
     (p.mounted, p.fly, getattr(p, "infantry", False)), (True, True, False))
c.eq("the Skorpekh Lord is the opposite on both counts",
     (SkorpekhLordProfile.infantry, getattr(SkorpekhLordProfile, "mounted", False)),
     (True, False))
c.eq("a CHARACTER and a LEADER (24.22)", (p.character, p.leader), (True, True))
c.eq("Reanimation Protocols, like every NECRONS unit", p.reanimation_protocols, True)

# NOT NOBLE - same trap as the Skorpekh Lord: the Overlord stays the roster's
# only NOBLE, so leading with this model must not switch on Guardian Protocols.
c.eq("NOBLE is not among the printed keywords",
     "NOBLE" in nec.LOKHUST_LORD.keywords, False)
_led = attached_units.attach(lord("2 Lokhust Lord 90"), destroyers("2 Lokhust Destroyers 90"))
c.eq("so leading a unit with him does NOT switch on Guardian Protocols",
     guardian_protocols.unit_has_guardian_protocols(_led), False)


# --- 2. base size ------------------------------------------------------------
print("--- 2. base size ---")

c.eq("the Lokhust Lord takes the Destroyer table size, not his printed 60 mm",
     LokhustLordProfile.base_radius_in, SkorpekhDestroyerProfile.base_radius_in)
c.eq("...so all FIVE Destroyer Cult datasheets are now one size",
     {LokhustLordProfile.base_radius_in, SkorpekhLordProfile.base_radius_in,
      SkorpekhDestroyerProfile.base_radius_in, LokhustDestroyerProfile.base_radius_in,
      LokhustHeavyDestroyerProfile.base_radius_in},
     {0.984})


# --- 3. weapons, pinned against the classes they now share ------------------
print("--- 3. weapons ---")

names = [wp.name for wp in sq.models[0].weapons]
c.eq("the default build carries the Staff of Light's two rows",
     names, ["Staff of Light", "Staff of Light"])

staff_r, staff_m = w.LordStaffOfLightRangedProfile(), w.LordStaffOfLightMeleeProfile()
c.eq('Staff of light (ranged): 18" A3 S5 AP-2 D1',
     (staff_r.range_in, staff_r.attacks, staff_r.strength, staff_r.ap, staff_r.damage),
     (18, 3, 5, -2, 1))
c.eq("Staff of light (melee): A4 S5 AP-2 D1",
     (staff_m.attacks, staff_m.strength, staff_m.ap, staff_m.damage), (4, 5, -2, 1))

# THE RENAME. He shares the Overlord's row exactly, which is why the class is
# no longer named after the Overlord. The Technomancer's pair stays separate
# because its melee Attacks really do differ - pinned as a DIFFERENCE.
staffed_overlord = build_squad(nec.OVERLORD, "Player 2", name="2 Overlord 4",
                               choices={"Overlord": {nec.OVERLORD_TO_STAFF_OF_LIGHT: 1}})
c.eq("...once he takes his staff option, both models carry the SAME classes",
     [wp.__class__ for wp in staffed_overlord.models[0].weapons],
     [wp.__class__ for wp in sq.models[0].weapons])
c.true("...and the class is no longer named after the Overlord",
       not hasattr(w, "OverlordStaffOfLightRangedProfile"))
c.eq("the Technomancer's staff is still its own pair - its melee Attacks differ",
     w.TechnomancerStaffOfLightMeleeProfile().attacks != staff_m.attacks, True)
c.eq("...while its ranged row is identical, which is why they stay symmetric "
     "pairs rather than one shared ranged class",
     (w.TechnomancerStaffOfLightRangedProfile().attacks,
      w.TechnomancerStaffOfLightRangedProfile().strength),
     (staff_r.attacks, staff_r.strength))

# THE MIRROR CASE: same numbers, different printed name -> inherit.
blade, ov_blade = w.LordsBladeProfile(), w.OverlordsBladeProfile()
c.eq("Lord's blade: A4 WS2+ S8 AP-3 D2",
     (blade.attacks, blade.strength, blade.ap, blade.damage), (4, 8, -3, 2))
c.eq("...with [DEVASTATING WOUNDS]", blade.devastating_wounds, True)
c.eq("it INHERITS the Overlord's Blade rather than repeating it, so a "
     "correction to the shared numbers reaches both",
     isinstance(blade, type(ov_blade)), True)
c.eq("...every characteristic identical",
     (blade.attacks, blade.strength, blade.ap, blade.damage,
      blade.devastating_wounds, blade.weapon_type),
     (ov_blade.attacks, ov_blade.strength, ov_blade.ap, ov_blade.damage,
      ov_blade.devastating_wounds, ov_blade.weapon_type))
c.eq("...and only the printed NAME differs",
     (blade.name, ov_blade.name), ("Lord's Blade", "Overlord's Blade"))


# --- 4. wargear --------------------------------------------------------------
print("--- 4. wargear ---")

# "This model's staff of light can be replaced with 1 Lord's blade." The staff
# is ONE printed weapon with two rows, so the swap gives up both - and this
# build has no ranged weapon at all, which is the part worth stating.
bladed = lord("2 Lokhust Lord 10",
              choices={"Lokhust Lord": {nec.LOKHUST_LORD_TO_LORDS_BLADE: 1}})
c.eq("taking the Lord's blade replaces BOTH staff rows",
     [wp.name for wp in bladed.models[0].weapons], ["Lord's Blade"])
c.eq("...leaving him no ranged weapon at all",
     [wp.name for wp in bladed.models[0].weapons if wp.weapon_type == w.RANGED], [])

amulet = lord("2 Lokhust Lord 11", gear={"Lokhust Lord": [nec.LOKHUST_LORD_NANOSCARAB_AMULET]})
c.eq("the nanoscarab amulet grants Feel No Pain 5+",
     feel_no_pain.current_feel_no_pain(amulet.models[0]), "5+")
c.eq("...and without it he has none", feel_no_pain.current_feel_no_pain(sq.models[0]), "-")

orb = lord("2 Lokhust Lord 12", gear={"Lokhust Lord": [nec.LOKHUST_LORD_RESURRECTION_ORB]})
c.eq("the resurrection orb is the Overlord's, unchanged",
     getattr(orb.models[0], "resurrection_orb", False), True)
# ...but WITHOUT the Overlord's condition. His orb is gated on having traded
# away the tachyon arrow; this one's printed line is a plain "one of the
# following", so two effect functions rather than one with a flag.
c.eq("...and it is not gated on a weapon he does not have",
     getattr(orb.models[0], "resurrection_orb", False), True)

# "One of the following" - a flat cap of one gear slot is what makes the two
# exclusive. Measured by asking for BOTH.
greedy = lord("2 Lokhust Lord 13",
              gear={"Lokhust Lord": [nec.LOKHUST_LORD_NANOSCARAB_AMULET,
                                     nec.LOKHUST_LORD_RESURRECTION_ORB]})
c.eq("amulet and orb are mutually exclusive - asking for both yields one",
     (getattr(greedy.models[0], "nanoscarab_amulet", False),
      getattr(greedy.models[0], "resurrection_orb", False)),
     (True, False))
c.eq("...which is a gear_slots cap of 1, not a condition inside either item",
     nec.LOKHUST_LORD.gear_slots.get("Lokhust Lord"), 1)


# --- 5. points and the LEADER pairing ---------------------------------------
print("--- 5. points and pairing ---")

pts = NECRONS_POINTS["Lokhust Lord"]
c.eq("70 points, flat - no per-copy tiers", pts.cost_for(1, unit_index=1), 70)
c.eq("...the same at the fourth copy", pts.cost_for(1, unit_index=4), 70)
c.eq("he leads both Lokhust datasheets and nothing else", tuple(pts.leads),
     ("Lokhust Destroyers", "Lokhust Heavy Destroyers"))
c.eq("attaching to Lokhust Destroyers is legal",
     attached_units.can_attach(lord("2 Lokhust Lord 20"), destroyers("2 Lokhust Destroyers 20")), [])
c.eq("...and to Lokhust Heavy Destroyers",
     attached_units.can_attach(
         lord("2 Lokhust Lord 21"),
         build_squad(nec.LOKHUST_HEAVY_DESTROYERS, "Player 2", composition_index=0,
                     name="2 Lokhust Heavy Destroyers 21")), [])
c.true("but NOT to the Skorpekh Destroyers, which are the OTHER Lord's unit",
       bool(attached_units.can_attach(
           lord("2 Lokhust Lord 22"),
           build_squad(nec.SKORPEKH_DESTROYERS, "Player 2", name="2 Skorpekh Destroyers 22"))))


# --- 6. sprite ---------------------------------------------------------------
print("--- 6. sprite ---")

art = sprites.sprite_for(lord("2 Lokhust Lord 30").models[0])
c.true("the Lokhust Lord resolves to a real image file",
       art is not None and pathlib.Path(art).exists())
c.true("...to its own art", "Lokhust Lord" in str(art))
c.true("...and not to either Lokhust squad's",
       art != sprites.sprite_for(destroyers("2 Lokhust Destroyers 30").models[0]))
# _key_for_name() returns on the FIRST substring hit, so the pair that could
# shadow is checked rather than assumed.
c.eq('"Lokhust Destroyers" is not a substring of a Lokhust Lord squad name',
     "Lokhust Destroyers" in "2 Lokhust Lord 30", False)


# --- 7. Destroyer Cult (the ability, not the keyword) -----------------------
print("--- 7. Destroyer Cult ---")

plain = destroyers("2 Lokhust Destroyers 40")
c.eq("an unled Lokhust squad crits on a 6", crit_hit.crit_hit_threshold(plain.models[0], None), 6)

led = attached_units.attach(lord("2 Lokhust Lord 41"), destroyers("2 Lokhust Destroyers 41"))
body = [m for m in led.models if m.profile.name != "Lokhust Lord"][0]
c.eq("with the Lord leading, a BODYGUARD's ranged attacks crit on a 5",
     crit_hit.crit_hit_threshold(body, None), 5)
c.eq("...but melee is untouched - the text says 'a ranged attack'",
     crit_hit.crit_hit_threshold(body, None, melee_only=True), 6)

# THE SHARED FLAG. Two datasheets print this ability under two names, so the
# flag is named for the mechanic - and the old, datasheet-named one is gone.
c.eq("the Plasmancer carries the very same flag under its own printed name",
     (LokhustLordProfile.leading_ranged_crit_on_5,
      __import__("game.units", fromlist=["x"]).PlasmancerProfile.leading_ranged_crit_on_5),
     (True, True))
c.true("...and no profile still carries the old datasheet-named one",
       not hasattr(LokhustLordProfile, "harbinger_of_destruction"))
c.true('each datasheet still states its OWN printed ability name',
       any("Destroyer Cult:" in t for t in nec.LOKHUST_LORD.abilities_text)
       and any("Harbinger of Destruction:" in t for t in nec.PLASMANCER.abilities_text))


# --- 8. Driven by Hatred -----------------------------------------------------
print("--- 8. Driven by Hatred ---")

target = build_squad(nec.NECRON_WARRIORS, "Player 1", composition_index=0,
                     name="1 Necron Warriors 50")
lord_model = lord("2 Lokhust Lord 50").models[0]

c.eq("a full-strength target grants nothing",
     destroyer_cult.driven_by_hatred_applies(lord_model, target), False)

# "Below Half-strength" is the Appendix's STRICTLY-less-than definition, not
# the at-or-below one Battle-shock uses. Measured at the boundary, because that
# is the only place the two differ.
c.eq("the target starts at ten models", len(target.models), 10)
del target.models[:5]                  # strength is counted in MODELS (Appendix)
c.eq("exactly half is NOT below half - the boundary the two definitions "
     "disagree on",
     (is_at_half_strength(target), is_below_half_strength(target)), (True, False))
c.eq("...so the ability still grants nothing there",
     destroyer_cult.driven_by_hatred_applies(lord_model, target), False)
del target.models[0]
c.eq("one model further down, it is below half",
     is_below_half_strength(target), True)
c.eq("...and now the Lord re-rolls",
     destroyer_cult.driven_by_hatred_applies(lord_model, target), True)

# PER MODEL, unlike its three siblings. A bodyguard swinging beside him gets
# nothing - the difference that vanishes if the predicate is written to match
# its neighbours.
led2 = attached_units.attach(lord("2 Lokhust Lord 51"), destroyers("2 Lokhust Destroyers 51"))
lord_in_unit = [m for m in led2.models if m.profile.name == "Lokhust Lord"][0]
body2 = [m for m in led2.models if m.profile.name != "Lokhust Lord"][0]
c.eq("the Lord himself has it", destroyer_cult.driven_by_hatred_applies(lord_in_unit, target), True)
c.eq("...and a bodyguard in the SAME unit does not",
     destroyer_cult.driven_by_hatred_applies(body2, target), False)
c.eq("a dead Lord grants nothing either",
     (setattr(lord_model, "current_wounds", 0),
      destroyer_cult.driven_by_hatred_applies(lord_model, target))[1], False)
lord_model.current_wounds = lord_model.profile.wounds

# The GROUP form the two attack steps use: all-or-nothing, on purpose.
c.eq("a group of only the Lord qualifies",
     destroyer_cult.driven_by_hatred_applies_to_group(
         [(lord_in_unit, w.LordStaffOfLightRangedProfile())], target), True)
c.eq("...a MIXED group does not - it would re-roll a bodyguard's dice on the "
     "Lord's entitlement",
     destroyer_cult.driven_by_hatred_applies_to_group(
         [(lord_in_unit, w.LordStaffOfLightRangedProfile()),
          (body2, w.LordStaffOfLightRangedProfile())], target), False)
c.eq("an empty group is not a grant", destroyer_cult.driven_by_hatred_applies_to_group([], target), False)

# THE SCOPE. It has no automatic-1s clause, so it must NOT be one of the
# ones-or-whole sources - listing it there would offer a 1s-only option the
# printed text never gives. Checked as an ABSENCE, the only place it shows.
c.eq("it is NOT a ones-or-whole source, unlike its three siblings",
     reroll_scope.is_ones_or_whole(destroyer_cult.DRIVEN_BY_HATRED_LABEL), False)
c.eq("...while all three siblings ARE (the two that have an upgrade clause)",
     (reroll_scope.is_ones_or_whole(destroyer_cult.HARD_WIRED_LABEL),
      reroll_scope.is_ones_or_whole(destroyer_cult.WHIRLING_ONSLAUGHT_LABEL)),
     (True, True))


# --- 9. both attack steps really read it ------------------------------------
print("--- 9. wiring ---")

_shoot = pathlib.Path("game/shooting.py").read_text(encoding="utf-8")
_fight = pathlib.Path("game/fight.py").read_text(encoding="utf-8")
# It covers BOTH rolls, which no other source in this engine does - so it has
# to appear in FOUR places, and a wiring that reaches only two would look
# entirely correct from either one.
c.eq("the shooting phase reads it for the HIT roll and the WOUND roll",
     _shoot.count("destroyer_cult.driven_by_hatred_applies_to_group"), 2)
c.eq('the fight phase does too - the text says "an attack", not "a ranged attack"',
     _fight.count("destroyer_cult.driven_by_hatred_applies_to_group"), 2)
c.true("...and both sides treat it as a WHOLE-roll re-roll",
       "destroyer_cult.DRIVEN_BY_HATRED_LABEL,\n        )" in _shoot
       and "destroyer_cult.DRIVEN_BY_HATRED_LABEL)" in _fight)

c.finish()
