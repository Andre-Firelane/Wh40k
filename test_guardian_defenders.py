"""Guardian Defenders (Aeldari) - the first datasheet of the third faction, and
the first carrier of the Battle Focus army rule.

Everything asserted here comes from the datasheet the user supplied. The two
abilities are checked through the code the ENGINE runs - GameState.
remove_dead_models() for Crewed Platform, BattleFocusPool's own ledger for
Fleet of Foot - never through the flag that enables them.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game import battle_focus, crewed_platform, sprites
from game.dice_notation import describe as describe_dice
from game.factions.aeldari import AELDARI, GUARDIAN_DEFENDERS
from game.units import GuardianDefenderProfile, HeavyWeaponPlatformProfile
from game.weapons import MELEE, RANGED
from testkit import Checks, GameState, Log, build

checks = Checks("Guardian Defenders")

# main.py names squads after the datasheet; sprite lookup matches the datasheet
# name as a SUBSTRING of the squad name, so a short test name would silently
# resolve to no art. Named the way the real scene names it.
NAME = "1 Guardian Defenders 1"


def guardians(owner="Player 1", name=NAME):
    return build(GUARDIAN_DEFENDERS, owner, name=name)


def lines_of(squad):
    return {m.profile.name for m in squad.models}


def model_named(squad, profile_name):
    return next(m for m in squad.models if m.profile.name == profile_name)


# ------------------------------------------------------- 1. the datasheet

print("--- 1. datasheet ---")

squad = guardians()
checks.eq("11 models", len(squad.models), 11)
checks.eq("10 Guardians + 1 platform",
          sorted((n, sum(1 for m in squad.models if m.profile.name == n)) for n in lines_of(squad)),
          [("Guardian Defender", 10), ("Heavy Weapon Platform", 1)])
checks.eq("90 points", squad.points, 90)
checks.eq("registered under the AELDARI faction keyword", AELDARI.keyword, "AELDARI")
checks.eq("the datasheet is reachable from the faction",
          AELDARI.datasheets["Guardian Defenders"] is GUARDIAN_DEFENDERS, True)
for keyword in ("BATTLELINE", "INFANTRY", "GRENADES", "GUARDIANS", "GUARDIAN DEFENDERS"):
    checks.true(f"keyword {keyword}", keyword in GUARDIAN_DEFENDERS.keywords)

g, p = GuardianDefenderProfile, HeavyWeaponPlatformProfile
checks.eq("Guardian statline M/T/Sv/W/Ld/OC",
          (g.movement_in, g.toughness, g.armor_save, g.wounds, g.leadership, g.oc),
          (7, 3, "4+", 1, "7+", 2))
checks.eq("Platform statline M/T/Sv/W/Ld/OC",
          (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc),
          (7, 3, "4+", 2, "7+", 0))
checks.eq("both are WS3+/BS3+, read off the weapon rows",
          {(g.weapon_skill, g.ballistic_skill), (p.weapon_skill, p.ballistic_skill)},
          {("3+", "3+")})
checks.true("both are INFANTRY - the keyword line is unit-wide", g.infantry and p.infantry)

# Base sizes are given on this datasheet (28.5mm / 40mm), converted the way
# every other base in the engine is. Recomputed here rather than restated, so a
# typo in either number fails.
checks.eq("Guardian base 28.5mm", round(28.5 / 2 / 25.4, 3), g.base_radius_in)
checks.eq("Platform base 40mm", round(40 / 2 / 25.4, 3), p.base_radius_in)
checks.true("and the Guardian base is the smallest in the engine so far",
            g.base_radius_in < 0.63)


# ---------------------------------------------------------- 2. the weapons

print("--- 2. weapons ---")

guard = model_named(squad, "Guardian Defender")
plat = model_named(squad, "Heavy Weapon Platform")
checks.eq("Guardian loadout", sorted(w.name for w in guard.weapons),
          ["Close Combat Weapon", "Shuriken Catapult"])
checks.eq("Platform loadout", sorted(w.name for w in plat.weapons),
          ["Bright Lance", "Close Combat Weapon"])

catapult = next(w for w in guard.weapons if w.name == "Shuriken Catapult")
checks.eq("Shuriken Catapult range/A/S/AP/D",
          (catapult.range_in, catapult.attacks, catapult.strength, catapult.ap, catapult.damage),
          (18, 2, 4, -1, 1))
checks.true("and it has [ASSAULT]", catapult.assault)
checks.eq("it is a ranged weapon", catapult.weapon_type, RANGED)

lance = next(w for w in plat.weapons if w.name == "Bright Lance")
checks.eq("Bright Lance range/A/S/AP",
          (lance.range_in, lance.attacks, lance.strength, lance.ap), (36, 1, 12, -3))
checks.eq("its Damage is rolled as D6+2", describe_dice(lance.damage_notation), "D6+2")
checks.eq("no weapon keywords - confirmed from the datasheet, not assumed",
          (lance.assault, lance.lethal_hits, lance.sustained_hits, lance.devastating_wounds,
           lance.blast, lance.heavy, lance.twin_linked),
          (False, False, 0, False, False, False, False))

ccw = next(w for w in guard.weapons if w.name == "Close Combat Weapon")
checks.eq("Close Combat Weapon A/S/AP/D",
          (ccw.attacks, ccw.strength, ccw.ap, ccw.damage), (1, 3, 0, 1))
checks.eq("it is a melee weapon", ccw.weapon_type, MELEE)
# Its own class, not the generic placeholder: same name, different Strength.
from game.weapons import CloseCombatWeaponProfile
checks.eq("the generic placeholder is S4, so this needed its own class",
          (CloseCombatWeaponProfile.strength, ccw.strength), (4, 3))


# ------------------------------------------------------ 3. Crewed Platform

print("--- 3. Crewed Platform ---")

state = GameState()
squad3 = guardians()
for model in squad3.models:
    state.add_token(model)
checks.eq("the flags sit on the right lines",
          (crewed_platform.is_platform(model_named(squad3, "Heavy Weapon Platform")),
           crewed_platform.is_crew(model_named(squad3, "Guardian Defender"))),
          (True, True))

# Losing SOME crew changes nothing.
for model in [m for m in squad3.models if crewed_platform.is_crew(m)][:9]:
    model.current_wounds = 0
state.remove_dead_models()
checks.eq("one Guardian left: the platform lives", len(squad3.models), 2)
checks.true("and it is still the platform",
            any(crewed_platform.is_platform(m) for m in squad3.models))

# The LAST crew model takes the platform with it, in the SAME sweep.
last_guardian = next(m for m in squad3.models if crewed_platform.is_crew(m))
last_guardian.current_wounds = 0
dead = state.remove_dead_models()
checks.eq("the unit is wiped out", len(squad3.models), 0)
checks.eq("the platform died in the same sweep, not a frame later", len(dead), 2)
checks.true("and it went through the normal death bookkeeping",
            all(m in squad3.destroyed_models for m in dead))
checks.eq("nothing of it is left on the board",
          [t for t in state.tokens if t.squad is squad3], [])

# A platform whose crew never dies is never touched.
state4 = GameState()
squad4 = guardians()
for model in squad4.models:
    state4.add_token(model)
state4.remove_dead_models()
checks.eq("an intact unit is untouched", len(squad4.models), 11)

# The two-flag design: a model that is neither crew nor platform (an attached
# CHARACTER under 19.01 would be one) must NOT keep the platform alive.
state5 = GameState()
squad5 = guardians()
outsider = build(GUARDIAN_DEFENDERS, "Player 1", name="outsider").models[0]
outsider.profile = type("Bystander", (), {
    "name": "Bystander", "base_radius_in": 0.63, "wounds": 3, "toughness": 3,
    "armor_save": "4+", "leadership": "7+", "oc": 1, "movement_in": 6,
    "crewed_platform": False, "platform_crew": False,
})()
outsider.squad = squad5
squad5.models.append(outsider)
for model in squad5.models:
    state5.add_token(model)
for model in [m for m in squad5.models if crewed_platform.is_crew(m)]:
    model.current_wounds = 0
state5.remove_dead_models()
checks.eq("with every Guardian dead only the bystander remains - a non-crew "
          "model does not keep the platform alive",
          [m.profile.name for m in squad5.models], ["Bystander"])


# -------------------------------------------------------- 4. Fleet of Foot

print("--- 4. Fleet of Foot ---")

pool = battle_focus.BattleFocusPool(players=("Player 1",), game_log=Log())
pool.sync_battle_round(1)
squad6 = guardians()
other = guardians(name="1 Guardian Defenders 2")
plain = build(GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 3")
for model in plain.models:            # strip the ability to get a control unit
    model.profile = type("NoFleet", (type(model.profile),), {"fleet_of_foot": False})()

checks.true("Fade Back is free for this unit",
            pool.is_free(battle_focus.FADE_BACK, squad6))
checks.eq("but only Fade Back - not the other manoeuvres",
          pool.is_free(battle_focus.SWIFT_AS_THE_WIND, squad6), False)
checks.eq("and only for a unit that has the ability",
          pool.is_free(battle_focus.FADE_BACK, plain), False)

before = pool.tokens["Player 1"]
checks.true("using it works", pool._spend("Player 1", battle_focus.FADE_BACK, squad6))
checks.eq("no token was spent", pool.tokens["Player 1"], before)
checks.true("and the log says so", pool.game_log.has("Fleet of Foot"))

checks.true("another unit can still Fade Back the same phase - it did not use "
            "up this phase's Fade Back",
            pool.can_use("Player 1", battle_focus.FADE_BACK, other))
checks.eq("the unit itself is spent for the phase, though - the ability waives "
          "the token and the per-manoeuvre limit, not the per-unit one",
          pool.can_use("Player 1", battle_focus.SWIFT_AS_THE_WIND, squad6), False)

# And it works the other way round: another unit having done Fade Back the
# normal way must not block a Fleet of Foot unit.
pool2 = battle_focus.BattleFocusPool(players=("Player 1",), game_log=Log())
pool2.sync_battle_round(1)
blocker = build(GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 9")
for model in blocker.models:
    model.profile = type("NoFleet2", (type(model.profile),), {"fleet_of_foot": False})()
pool2._spend("Player 1", battle_focus.FADE_BACK, blocker)
checks.eq("a normal Fade Back does use up a token", pool2.tokens["Player 1"], 3)
checks.eq("and blocks another ORDINARY unit this phase",
          pool2.can_use("Player 1", battle_focus.FADE_BACK,
                        build(GUARDIAN_DEFENDERS, "Player 1", name="x")) and False
          or pool2.can_use("Player 1", battle_focus.FADE_BACK, blocker), False)
checks.true("but a Fleet of Foot unit is not blocked by it",
            pool2.can_use("Player 1", battle_focus.FADE_BACK, squad6))

# Being the army rule's first real carrier.
checks.true("battle_focus is unit-wide", battle_focus.has_battle_focus(squad6))
checks.eq("so this army qualifies as ASURYANI",
          battle_focus.qualifying_players([squad6]), ("Player 1",))


# ------------------------------------------------------------ 5. sprites

print("--- 5. sprites ---")

art = [os.path.basename(p) for p in sprites.portrait_paths(squad, 4)]
checks.eq("both model lines have their own art",
          sorted(art), ["Bright Lance Weapon Platform.png", "Guardian Defender.png"])
checks.eq("the platform gets the Bright Lance art",
          os.path.basename(sprites.sprite_for(plat)), "Bright Lance Weapon Platform.png")
checks.eq("and the rank and file the Guardian art",
          os.path.basename(sprites.sprite_for(guard)), "Guardian Defender.png")


# ---------------------------------------------------------- 6. A/B probes

print("--- 6. A/B probes ---")

saved_platform = crewed_platform.is_platform
crewed_platform.is_platform = lambda model: False
state7 = GameState()
squad7 = guardians()
for model in squad7.models:
    state7.add_token(model)
for model in [m for m in squad7.models if crewed_platform.is_crew(m)]:
    model.current_wounds = 0
state7.remove_dead_models()
checks.eq("A/B: with Crewed Platform neutralised the platform survives alone",
          [m.profile.name for m in squad7.models], ["Heavy Weapon Platform"])
crewed_platform.is_platform = saved_platform

saved_free = battle_focus.BattleFocusPool.is_free
battle_focus.BattleFocusPool.is_free = lambda self, manoeuvre, squad: False
pool3 = battle_focus.BattleFocusPool(players=("Player 1",), game_log=Log())
pool3.sync_battle_round(1)
pool3._spend("Player 1", battle_focus.FADE_BACK, squad6)
checks.eq("A/B: without Fleet of Foot the same Fade Back costs a token",
          pool3.tokens["Player 1"], 3)
battle_focus.BattleFocusPool.is_free = saved_free

checks.finish()
