"""Dark Reapers - statline, weapons, wargear, and the two things that are
actually new here:

  * INESCAPABLE ACCURACY, which is word for word the permission the Riptide
    prints as "Weapon Support System" and rule 24.29 gives [PSYCHIC]. It gets
    their flag rather than a third implementation - so the checks below go
    through the REAL _hit_modifiers(), not the flag, because a flag nobody
    reads is exactly the failure this suite exists to catch.
  * The Tempest Launcher's printed "2D6" Attacks characteristic - the first
    multi-die characteristic in the engine, which is why game/dice_notation.py
    grew a `dice` field instead of the weapon quietly becoming D6+3.
"""

import testkit as tk
from game import aspect_shrine
from game.dice_notation import D6, describe
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.units import DarkReaperExarchProfile, DarkReaperProfile

checks = tk.Checks("Dark Reapers")

EXARCH = "Dark Reaper Exarch"


def reapers(choices=None, composition_index=0, owner="Player 1"):
    return tk.build(ae.DARK_REAPERS, owner, name="1 Dark Reapers 1",
                    choices=choices, composition_index=composition_index)


def weapon_named(squad, model_index, name):
    return next(w for w in squad.models[model_index].weapons if w.name == name)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

five = reapers()
ten = reapers(composition_index=1)
checks.eq("5-model unit: 1 Exarch + 4", len(five.models), 5)
checks.eq("10-model unit: 1 Exarch + 9", len(ten.models), 10)
checks.eq("...costs 100", five.points, 100)
checks.eq("...and 210", ten.points, 210)

trooper = DarkReaperProfile()
exarch = DarkReaperExarchProfile()
checks.eq("M6\"", trooper.movement_in, 6)
checks.eq("T3", trooper.toughness, 3)
checks.eq("Sv3+", trooper.armor_save, "3+")
checks.eq("W1", trooper.wounds, 1)
checks.eq("Ld6+", trooper.leadership, "6+")
checks.eq("OC1", trooper.oc, 1)
checks.eq("BS3+", trooper.ballistic_skill, "3+")
checks.eq("5+ invulnerable save", trooper.invulnerable_save, "5+")
# The Exarch differs in exactly two characteristics - which is why the profile
# subclasses rather than repeating the statline.
checks.eq("the Exarch has W2", exarch.wounds, 2)
checks.eq("...and BS2+", exarch.ballistic_skill, "2+")
checks.eq("...and is otherwise identical (T)", exarch.toughness, trooper.toughness)
checks.eq("...(Sv)", exarch.armor_save, trooper.armor_save)
checks.eq("...(M)", exarch.movement_in, trooper.movement_in)
checks.true("...and is highlighted as the squad leader", exarch.squad_leader)
checks.eq("28.5 mm base -> 0.561\"", trooper.base_radius_in, round(28.5 / 2 / 25.4, 3))
checks.true("INFANTRY", trooper.infantry)
checks.eq("ASPECT WARRIORS on the datasheet", "ASPECT WARRIORS" in ae.DARK_REAPERS.keywords, True)
checks.eq("DARK REAPERS too", "DARK REAPERS" in ae.DARK_REAPERS.keywords, True)
checks.true("Battle Focus (army rule)", trooper.battle_focus)
# No Fleet of Foot - asked of the profile rather than assumed from the sister
# datasheets, because copying a near-identical Aspect Warrior is exactly how a
# free ability gets handed out by accident.
checks.eq("but NOT Fleet of Foot", getattr(trooper, "fleet_of_foot", False), False)
checks.eq("no LEADER ability", getattr(trooper, "leader", False), False)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

launcher = weapon_named(five, 0, "Reaper Launcher - Starshot")
checks.eq("Reaper Launcher: 48\"", launcher.range_in, 48)
checks.eq("...A1", launcher.attacks, 1)
checks.eq("...S10", launcher.strength, 10)
checks.eq("...AP-2", launcher.ap, -2)
checks.eq("...D3", launcher.damage, 3)
checks.true("...[IGNORES COVER]", launcher.ignores_cover)
# One printed entry, two firing modes - so an overcharge_profile, not a second
# weapon (nothing would otherwise stop a model firing both).
starswarm = launcher.overcharge_profile()
checks.eq("...its second mode is Starswarm", starswarm.name, "Reaper Launcher - Starswarm")
checks.eq("...A2", starswarm.attacks, 2)
checks.eq("...S5", starswarm.strength, 5)
checks.eq("...D1", starswarm.damage, 1)
checks.true("...also [IGNORES COVER]", starswarm.ignores_cover)

# EVERY BS here is an explicit override, and the two printed sources disagree
# for one combination: the Exarch is BS2+ but the Reaper launcher row prints
# 3+, and he carries one by default. The printed row wins.
checks.eq("the Reaper Launcher prints its own BS3+", launcher.ballistic_skill, "3+")
checks.eq("...including on the BS2+ Exarch", weapon_named(five, 0, "Reaper Launcher - Starshot").ballistic_skill, "3+")

ccw = weapon_named(five, 0, "Close Combat Weapon")
checks.eq("close combat weapon A2/S3", (ccw.attacks, ccw.strength), (2, 3))
checks.eq("...shared with the other Aeldari A2 datasheets",
          type(ccw).__name__, "AeldariCloseCombatWeaponA2Profile")

# The Shuriken Cannon is the SAME numbers as the shared one, one keyword more.
shared = next(w for w in tk.build(ae.FALCON, "Player 1", name="1 Falcon 1",
                                  choices={"Falcon": {ae.FALCON_CATAPULT_TO_SHURIKEN_CANNON: 1}}
                                  ).models[0].weapons if w.name == "Shuriken Cannon")
dr_cannon = weapon_named(reapers(choices={EXARCH: {ae.DARK_REAPER_TO_SHURIKEN_CANNON: 1}}),
                         0, "Shuriken Cannon")
checks.eq("Dark Reapers' Shuriken Cannon has the shared numbers (S)",
          dr_cannon.strength, shared.strength)
checks.eq("...(AP/D)", (dr_cannon.ap, dr_cannon.damage), (shared.ap, shared.damage))
checks.true("...and [LETHAL HITS] like it", dr_cannon.lethal_hits)
checks.true("...but adds [IGNORES COVER], which the Falcon's row does not have",
            dr_cannon.ignores_cover and not shared.ignores_cover)


# --- 3. wargear options -----------------------------------------------------
print("--- 3. wargear options ---")


def exarch_guns(choices):
    sq = reapers(choices=choices)
    return sorted(w.name for w in sq.models[0].weapons if w.weapon_type == "ranged")


checks.eq("default: Reaper Launcher", exarch_guns(None), ["Reaper Launcher - Starshot"])
checks.eq("-> Missile Launcher", exarch_guns({EXARCH: {ae.DARK_REAPER_TO_MISSILE_LAUNCHER: 1}}),
          ["Missile Launcher - Starshot"])
checks.eq("-> Shuriken Cannon", exarch_guns({EXARCH: {ae.DARK_REAPER_TO_SHURIKEN_CANNON: 1}}),
          ["Shuriken Cannon"])
checks.eq("-> Tempest Launcher", exarch_guns({EXARCH: {ae.DARK_REAPER_TO_TEMPEST_LAUNCHER: 1}}),
          ["Tempest Launcher"])
# "1 of the following" - mutually exclusive, and it falls out of the one-model
# line rather than needing a rule of its own.
checks.eq("two at once trims to one",
          exarch_guns({EXARCH: {ae.DARK_REAPER_TO_MISSILE_LAUNCHER: 1,
                                ae.DARK_REAPER_TO_TEMPEST_LAUNCHER: 1}}),
          ["Missile Launcher - Starshot"])
# ...and only the Exarch can take any of them.
checks.eq("the rank and file keep their Reaper Launchers",
          sorted({w.name for m in reapers(choices={EXARCH: {ae.DARK_REAPER_TO_TEMPEST_LAUNCHER: 1}}).models[1:]
                  for w in m.weapons if w.weapon_type == "ranged"}),
          ["Reaper Launcher - Starshot"])

missile = weapon_named(reapers(choices={EXARCH: {ae.DARK_REAPER_TO_MISSILE_LAUNCHER: 1}}),
                       0, "Missile Launcher - Starshot")
# The printed Damage is "D6", so it must be a ROLL, not a flat number. This
# line used to assert damage == 6 - the old "store the die's max value as a
# fixed int and never roll it" convention that game/dice_notation.py exists to
# replace - which quietly gave the Exarch a guaranteed 6 where the datasheet
# gives an average of 3.5. Asserting the NOTATION is what makes that
# distinction visible at all; `damage` beside it is only the grouping
# placeholder.
checks.eq("Missile Launcher: S10/AP-2", (missile.strength, missile.ap), (10, -2))
# describe() on a None notation would raise, and a probe that CRASHES the
# suite hides which check broke (this repo's recurring lesson - the two
# str.index() guards, the padded row in test_faction_badges.py). Degrade to a
# readable value instead.
checks.eq("...and Damage is a D6 ROLL, not a flat 6",
          describe(missile.damage_notation) if missile.damage_notation else
          "flat %s" % missile.damage, "D6")
checks.eq("...BS2+, the Exarch's own", missile.ballistic_skill, "2+")
checks.eq("...its Sunburst mode is D6 attacks, [BLAST]",
          (describe(missile.overcharge_profile().attacks_notation),
           missile.overcharge_profile().blast), ("D6", 1))
# Same printed name as the Falcon's, and its own class - but what separates
# them is [IGNORES COVER], not the Damage. This line used to read "D6 vs D3"
# and passed by comparing the two placeholder ints (6 against 3); both weapons
# are printed D6, and that false difference is what kept the flat 6 above
# looking deliberate. Pinned against each other rather than against literals,
# so neither can drift alone.
falcon_missile = next(
    w for w in tk.build(ae.FALCON, "Player 1", name="1 Falcon 1",
                        choices={"Falcon": {ae.FALCON_SCATTER_TO_MISSILE: 1}}).models[0].weapons
    if w.name == "Missile Launcher - Starshot")
checks.eq("...same Damage as the Falcon's, both printed D6",
          describe(missile.damage_notation) if missile.damage_notation else
          "flat %s" % missile.damage,
          describe(falcon_missile.damage_notation))
checks.eq("...what separates them is [IGNORES COVER], not the Damage",
          (missile.ignores_cover, falcon_missile.ignores_cover), (True, False))

aspect_shrine.grant_tokens(five)
aspect_shrine.grant_tokens(ten)
checks.eq("Aspect Shrine: 1 token per 5 models", aspect_shrine.tokens_for(five), 1)
checks.eq("...2 at 10 models", aspect_shrine.tokens_for(ten), 2)


# --- 4. the Tempest Launcher's printed "2D6" Attacks ------------------------
print("--- 4. 2D6 attacks ---")

tempest = weapon_named(reapers(choices={EXARCH: {ae.DARK_REAPER_TO_TEMPEST_LAUNCHER: 1}}),
                       0, "Tempest Launcher")
checks.eq("Tempest Launcher: 36\"", tempest.range_in, 36)
checks.eq("...S4/AP-1/D1", (tempest.strength, tempest.ap, tempest.damage), (4, -1, 1))
checks.eq("...[BLAST]", tempest.blast, 1)
checks.true("...[INDIRECT FIRE] (rule 10.07)", tempest.indirect_fire)
checks.eq("...its Attacks characteristic reads 2D6", describe(tempest.attacks_notation), "2D6")
checks.eq("...as two D6", (tempest.attacks_notation.dice, tempest.attacks_notation.sides), (2, 6))
# The count is what actually gets rolled, and the multiplication lives in one
# place - so a plain D6 must be unaffected. Measured in DICE, not in the total,
# because the total is random.
from game.dice_notation import DiceNotationRoll  # noqa: E402


def dice_rolled(notation, count):
    rolled = []
    original = __import__("random").randint

    def spy(lo, hi):
        rolled.append(hi)
        return original(lo, hi)
    __import__("random").randint = spy
    try:
        DiceNotationRoll(notation, count=count, dice_manager=None, label="x")
    finally:
        __import__("random").randint = original
    return len(rolled)


checks.eq("one model firing 2D6 rolls 2 dice", dice_rolled(D6(dice=2), 1), 2)
checks.eq("three models firing 2D6 roll 6", dice_rolled(D6(dice=2), 3), 6)
checks.eq("...while a plain D6 is untouched: 3 models, 3 dice", dice_rolled(D6(), 3), 3)
checks.eq("...and a D6+2 still rolls 3", dice_rolled(D6(2), 3), 3)


# --- 5. Inescapable Accuracy, through the real hit step ---------------------
print("--- 5. Inescapable Accuracy ---")

# Measured through the REAL ShootingController._hit_modifiers(), never off the
# flag: a flag nobody reads would pass an equality check and do nothing in play.
#
# The worsening modifier is one this datasheet generates for ITSELF - rule
# 13.08's Benefit of Cover, +1 to the hit threshold - which needs the Tempest
# Launcher, because every other gun on the sheet carries [IGNORES COVER] and so
# removes the benefit before a modifier is ever produced. That is worth pinning
# in its own right, and it is checked below.
from game.shooting import ShootingController, NORMAL_SHOOTING  # noqa: E402


def hit_modifiers(weapon_name, choices=None, ability=True):
    sq = reapers(choices=choices)
    model = sq.models[0]
    if not ability:
        # A/B: same model, same weapon, same target - ability switched off, so
        # any difference can only come from the ability itself.
        model.profile = type("NoIHM", (type(model.profile),),
                             {"ignores_hit_modifiers": False})()
    target = tk.build(tau.KROOT_CARNIVORES, "Player 2", name="1 Kroot Carnivores 1")
    tk.line_up(sq, y=20.0)
    tk.line_up(target, y=26.0)
    sc = ShootingController(all_tokens=list(sq.models) + list(target.models),
                            player_name="Player 1")
    sc.shooting_type = NORMAL_SHOOTING
    sc.active_squad = sq
    weapon = next(w for w in model.weapons if w.name == weapon_name)
    return sc._hit_modifiers({"pairs": [(model, weapon)], "target_squad": target})


TEMPEST = {EXARCH: {ae.DARK_REAPER_TO_TEMPEST_LAUNCHER: 1}}

checks.true("the Dark Reaper carries the ability",
            DarkReaperProfile.ignores_hit_modifiers)
checks.true("...and so does the Exarch", DarkReaperExarchProfile.ignores_hit_modifiers)

without = hit_modifiers("Tempest Launcher", TEMPEST, ability=False)
with_it = hit_modifiers("Tempest Launcher", TEMPEST, ability=True)
checks.true("A/B: WITHOUT the ability, Benefit of Cover puts a +1 on the roll",
            any(m.amount > 0 for m in without))
checks.eq("A/B: ...and it names the source", [m.source for m in without if m.amount > 0],
          ["Benefit of Cover"])
checks.eq("WITH the ability every worsening modifier is gone",
          [m for m in with_it if m.amount > 0], [])
checks.true("...and improving modifiers would still be kept",
            all(m.amount <= 0 for m in with_it))

# The interaction that makes the Tempest Launcher the only usable probe here:
# the Reaper Launcher's own [IGNORES COVER] means no cover modifier is ever
# produced, with or without the ability.
checks.eq("the Reaper Launcher's [IGNORES COVER] removes the benefit first",
          [m.source for m in hit_modifiers("Reaper Launcher - Starshot", ability=False)], [])

# It is the SAME flag the Riptide's "Weapon Support System" sets - shared
# rather than reimplemented, which is the point of the rename.
from game.units import RiptideProfile  # noqa: E402

checks.true("shared with the Riptide's Weapon Support System",
            RiptideProfile.ignores_hit_modifiers)
checks.eq("but not handed to anything else by accident",
          tk.build(tau.KROOT_CARNIVORES, "Player 2",
                   name="1 Kroot Carnivores 1").models[0].profile.ignores_hit_modifiers, False)


# --- 6. sprite --------------------------------------------------------------
print("--- 6. sprite ---")

from game import sprites  # noqa: E402

# Art arrived after the datasheet was built. Checked at the model, not at the
# mapping table: a key that resolves to no file on disk is exactly the failure
# this is here to catch.
checks.true("Dark Reapers resolve a sprite", sprites.sprite_for(five.models[0]))
checks.true("...and it is the Dark Reaper file",
            "Dark Reaper" in (sprites.sprite_for(five.models[0]) or ""))
checks.eq("the Exarch shares the unit's art - no separate file was supplied",
          sprites.sprite_for(five.models[0]), sprites.sprite_for(five.models[-1]))


checks.finish()
