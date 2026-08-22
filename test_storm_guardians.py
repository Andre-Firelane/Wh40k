"""Storm Guardians (Aeldari) - the melee Guardian squad, its Serpent's Scale
Platform, and the pre-existing wargear bug this datasheet surfaced.

Statline, weapons, composition and points came from Wahapedia; the platform's
own numbers were supplied directly by the user and AGREE with it line for line,
which is why they are trusted here. Stormblades is deliberately not implemented
- see game/factions/aeldari.py - so nothing here asserts it.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from collections import Counter

from game import battle_focus, crewed_platform, invulnerable_save, sprites
from game.dice_notation import describe as describe_dice
from game.factions import build_squad
from game.factions.aeldari import (
    STORM_GUARDIAN_CCW_TO_POWER_SWORD,
    STORM_GUARDIAN_PISTOL_TO_FLAMER,
    STORM_GUARDIAN_PISTOL_TO_FUSION,
    STORM_GUARDIANS,
)
from game.factions.tau_empire import PATHFINDER_CARBINE_TO_ION_RIFLE, PATHFINDER_CARBINE_TO_RAIL_RIFLE, PATHFINDER_TEAM
from game.units import SerpentsScalePlatformProfile, StormGuardianProfile
from game.weapons import MELEE, RANGED
from testkit import Checks, GameState, Log, build

checks = Checks("Storm Guardians")

NAME = "1 Storm Guardians 1"   # sprite lookup matches the datasheet name as a substring


def storm(name=NAME, choices=None):
    return build(STORM_GUARDIANS, "Player 1", name=name, choices=choices)


def weapons_of(squad):
    return Counter(w.name for m in squad.models for w in m.weapons)


def model_named(squad, profile_name):
    return next(m for m in squad.models if m.profile.name == profile_name)


# ------------------------------------------------------- 1. the datasheet

print("--- 1. datasheet ---")

squad = storm()
checks.eq("11 models", len(squad.models), 11)
checks.eq("10 Guardians + 1 platform",
          sorted(Counter(m.profile.name for m in squad.models).items()),
          [("Serpent's Scale Platform", 1), ("Storm Guardian", 10)])
checks.eq("110 points", squad.points, 110)
for keyword in ("BATTLELINE", "INFANTRY", "GRENADES", "GUARDIANS", "STORM GUARDIANS"):
    checks.true(f"keyword {keyword}", keyword in STORM_GUARDIANS.keywords)

g, p = StormGuardianProfile, SerpentsScalePlatformProfile
checks.eq("Storm Guardian statline M/T/Sv/W/Ld/OC",
          (g.movement_in, g.toughness, g.armor_save, g.wounds, g.leadership, g.oc),
          (7, 3, "4+", 1, "7+", 2))
checks.eq("Platform statline M/T/Sv/W/Ld/OC - matches the user's own paste",
          (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc),
          (7, 3, "4+", 2, "7+", 0))
checks.eq("bases 28.5mm / 40mm",
          (g.base_radius_in, p.base_radius_in),
          (round(28.5 / 2 / 25.4, 3), round(40 / 2 / 25.4, 3)))
checks.true("both INFANTRY", g.infantry and p.infantry)
checks.true("the platform carries no gun at all",
            not [w for w in model_named(squad, "Serpent's Scale Platform").weapons
                 if w.weapon_type == RANGED])


# ---------------------------------------------------------- 2. the weapons

print("--- 2. weapons ---")

guard = model_named(squad, "Storm Guardian")
pistol = next(w for w in guard.weapons if w.name == "Shuriken Pistol")
checks.eq("Shuriken Pistol range/A/S/AP/D",
          (pistol.range_in, pistol.attacks, pistol.strength, pistol.ap, pistol.damage),
          (12, 1, 4, -1, 1))
checks.true("with [ASSAULT] and [PISTOL] - two separate keywords",
            pistol.assault and pistol.pistol)

ccw = next(w for w in guard.weapons if w.name == "Close Combat Weapon")
checks.eq("this datasheet's Close Combat Weapon is A2/S3", (ccw.attacks, ccw.strength), (2, 3))
checks.eq("it is a melee weapon", ccw.weapon_type, MELEE)
# The reason it needed its own class: Guardian Defenders print A1 for the very
# same weapon name.
from game.weapons import AeldariCloseCombatWeaponProfile
checks.eq("Guardian Defenders' same-named weapon is A1, hence a separate class",
          (AeldariCloseCombatWeaponProfile.attacks, ccw.attacks), (1, 2))

swapped = storm(name="1 Storm Guardians 9", choices={"Storm Guardian": {
    STORM_GUARDIAN_PISTOL_TO_FLAMER: 1,
    STORM_GUARDIAN_PISTOL_TO_FUSION: 1,
    STORM_GUARDIAN_CCW_TO_POWER_SWORD: 1,
}})
flamer = next(w for m in swapped.models for w in m.weapons if w.name == "Flamer")
checks.eq("Flamer range/S/AP/D", (flamer.range_in, flamer.strength, flamer.ap, flamer.damage),
          (12, 4, 0, 1))
checks.eq("its Attacks are rolled as D6", describe_dice(flamer.attacks_notation), "D6")
checks.true("with [ASSAULT], [IGNORES COVER] and [TORRENT]",
            flamer.assault and flamer.ignores_cover and flamer.torrent)

fusion = next(w for m in swapped.models for w in m.weapons if w.name == "Fusion Gun")
checks.eq("Fusion Gun range/A/S/AP", (fusion.range_in, fusion.attacks, fusion.strength, fusion.ap),
          (12, 1, 8, -4))
checks.eq("its Damage is rolled as D6", describe_dice(fusion.damage_notation), "D6")
checks.eq("with [ASSAULT] and [MELTA 2]", (fusion.assault, fusion.melta), (True, 2))

sword = next(w for m in swapped.models for w in m.weapons if w.name == "Power Sword")
checks.eq("Power Sword A/S/AP/D",
          (sword.attacks, sword.strength, sword.ap, sword.damage), (2, 4, -2, 1))


# ------------------------------ 3. wargear options, and the bug they exposed

print("--- 3. wargear options ---")

full = storm(name="1 Storm Guardians 2", choices={"Storm Guardian": {
    STORM_GUARDIAN_PISTOL_TO_FLAMER: 2,
    STORM_GUARDIAN_PISTOL_TO_FUSION: 2,
    STORM_GUARDIAN_CCW_TO_POWER_SWORD: 2,
}})
counts = weapons_of(full)
checks.eq("2 flamers", counts["Flamer"], 2)
checks.eq("2 fusion guns - an INDEPENDENT cap, not 2 special weapons in total",
          counts["Fusion Gun"], 2)
checks.eq("2 power swords", counts["Power Sword"], 2)

# The bug this datasheet surfaced: both pistol swaps used to start at model 0,
# so two models ended up carrying a flamer AND a fusion gun while only two
# pistols were given up. The arithmetic is the check - 10 pistols minus 4 swaps.
checks.eq("four pistols were actually given up", counts["Shuriken Pistol"], 6)
checks.eq("and two close combat weapons", counts["Close Combat Weapon"], 9)
carrying_both = [m for m in full.models
                 if {"Flamer", "Fusion Gun"} <= {w.name for w in m.weapons}]
checks.eq("no model carries both special weapons", carrying_both, [])

over = storm(name="1 Storm Guardians 3",
             choices={"Storm Guardian": {STORM_GUARDIAN_PISTOL_TO_FLAMER: 5}})
checks.eq("an over-eager choice is trimmed to the cap of 2",
          weapons_of(over)["Flamer"], 2)

# Same fix, on the datasheet that had the bug latent all along.
pathfinders = build(PATHFINDER_TEAM, "Player 1", name="1 Pathfinder Team 1", choices={
    "Pathfinder": {PATHFINDER_CARBINE_TO_RAIL_RIFLE: 2, PATHFINDER_CARBINE_TO_ION_RIFLE: 2},
})
pf = weapons_of(pathfinders)
checks.eq("Pathfinders: two carbine swaps also land on four different models",
          (pf["Rail Rifle"], pf["Ion Rifle - Standard"], pf["Pulse Carbine"]), (2, 2, 6))


# -------------------------------------------------------- 4. Serpent Shield

print("--- 4. Serpent Shield ---")

state = GameState()
squad4 = storm(name="1 Storm Guardians 4")
for model in squad4.models:
    state.add_token(model)
guard4 = model_named(squad4, "Storm Guardian")
platform4 = model_named(squad4, "Serpent's Scale Platform")

# "-" is this engine's sentinel for "no save", not None - parse_threshold()
# turns it into None downstream.
checks.eq("a Storm Guardian prints no invulnerable save of its own",
          guard4.profile.invulnerable_save, "-")
checks.eq("but the engine reports 5+ while the platform lives",
          invulnerable_save.effective_invulnerable_save(guard4), "5+")
checks.eq("the platform itself is covered too",
          invulnerable_save.effective_invulnerable_save(platform4), "5+")
checks.true("and the unit-wide question agrees",
            invulnerable_save.unit_has_serpent_shield(squad4))

platform4.current_wounds = 0
checks.eq("a dead bearer stops granting it, before the sweep even runs",
          invulnerable_save.effective_invulnerable_save(guard4), "-")
state.remove_dead_models()
checks.eq("and after it", invulnerable_save.effective_invulnerable_save(guard4), "-")

# "Better of the two, never worse" - a printed 4+ must survive a granted 5+.
squad4b = storm(name="1 Storm Guardians 5")
tough = model_named(squad4b, "Storm Guardian")
tough.profile = type("Tough", (type(tough.profile),), {"invulnerable_save": "4+"})()
tough.squad = squad4b
checks.eq("a printed 4+ is kept, not overwritten by the granted 5+",
          invulnerable_save.effective_invulnerable_save(tough), "4+")


# ------------------------------------------------------- 5. Crewed Platform

print("--- 5. Crewed Platform ---")

state5 = GameState()
squad5 = storm(name="1 Storm Guardians 6")
for model in squad5.models:
    state5.add_token(model)
checks.true("the flags sit on the right lines",
            crewed_platform.is_platform(model_named(squad5, "Serpent's Scale Platform"))
            and crewed_platform.is_crew(model_named(squad5, "Storm Guardian")))
for model in [m for m in squad5.models if crewed_platform.is_crew(m)]:
    model.current_wounds = 0
dead = state5.remove_dead_models()
checks.eq("the last Guardian takes the platform with it", len(squad5.models), 0)
checks.eq("in the same sweep", len(dead), 11)


# ---------------------------------------------- 6. NO Fleet of Foot here

print("--- 6. no Fleet of Foot ---")

pool = battle_focus.BattleFocusPool(players=("Player 1",), game_log=Log())
pool.sync_battle_round(1)
squad6 = storm(name="1 Storm Guardians 7")
checks.eq("this datasheet does not have the ability",
          any(m.profile.fleet_of_foot for m in squad6.models), False)
checks.eq("so Fade Back is not free for it",
          pool.is_free(battle_focus.FADE_BACK, squad6), False)
pool._spend("Player 1", battle_focus.FADE_BACK, squad6)
checks.eq("it costs a token like anyone else's", pool.tokens["Player 1"], 3)
checks.true("but it does have the army rule itself",
            battle_focus.has_battle_focus(squad6))


# ---------------------------------------------------------- 6b. Stormblades

print("--- 6b. Stormblades ---")

from game.fieldcraft import apply_fieldcraft
from game.squad import squad_has_fieldcraft
from game.terrain import LIGHT, Obstacle

checks.true("Stormblades rides the shared sticky-objective flag - the same rule "
            "Kroot Carnivores print as Fieldcraft and Boyz as Get Da Good Bitz",
            squad_has_fieldcraft(squad6))

state6 = GameState()
holder = storm(name="1 Storm Guardians 10")
area = state6.add_terrain_area([Obstacle(20.0, 20.0, 6.0, 6.0, category=LIGHT)])
objective = state6.add_objective(area, name="Test Objective")
for i, model in enumerate(holder.models):
    model.x_in, model.y_in = 21.0 + (i % 4) * 0.8, 21.0 + (i // 4) * 0.8
    state6.add_token(model)

objective.update_control(state6.tokens)
checks.eq("with the unit standing on it, they control it", objective.controlled_by, "Player 1")
checks.eq("and nothing is secured yet", objective.secured_by, None)

apply_fieldcraft(state6.objectives, state6.tokens, "Player 1")
checks.eq("the end-of-phase pass secures it for them", objective.secured_by, "Player 1")

# The sticky half: control survives the unit leaving.
for model in list(holder.models):
    state6.tokens.remove(model)
objective.update_control(state6.tokens)
checks.eq("control holds with no models in range at all", objective.controlled_by, "Player 1")

# ...until the opponent's Level of Control is actually greater.
intruder = build(STORM_GUARDIANS, "Player 2", name="2 Storm Guardians 1")
for i, model in enumerate(intruder.models):
    model.x_in, model.y_in = 21.0 + (i % 4) * 0.8, 21.0 + (i // 4) * 0.8
    state6.add_token(model)
objective.update_control(state6.tokens)
checks.eq("a greater opposing Level of Control breaks it", objective.controlled_by, "Player 2")
checks.eq("and the secured status is released", objective.secured_by, None)

# A unit without the ability never secures anything.
state6b = GameState()
plain = build(STORM_GUARDIANS, "Player 1", name="1 Storm Guardians 11")
for model in plain.models:
    model.profile = type("NoSticky", (type(model.profile),), {"fieldcraft": False})()
area_b = state6b.add_terrain_area([Obstacle(20.0, 20.0, 6.0, 6.0, category=LIGHT)])
objective_b = state6b.add_objective(area_b, name="Other Objective")
for i, model in enumerate(plain.models):
    model.x_in, model.y_in = 21.0 + (i % 4) * 0.8, 21.0 + (i // 4) * 0.8
    state6b.add_token(model)
objective_b.update_control(state6b.tokens)
apply_fieldcraft(state6b.objectives, state6b.tokens, "Player 1")
checks.eq("A/B: without the ability the objective is never secured",
          objective_b.secured_by, None)

checks.eq("Stormblades is no longer recorded as missing",
          "Stormblades: NOT IMPLEMENTED" in " ".join(STORM_GUARDIANS.abilities_text), False)


# ------------------------------------------------------------ 7. sprites

print("--- 7. sprites ---")

art = [os.path.basename(x) for x in sprites.portrait_paths(squad, 4)]
checks.eq("the user's file name differs from the datasheet name", art, ["Assault Guardian.png"])
checks.eq("the platform has no art of its own and falls through to the same image",
          os.path.basename(sprites.sprite_for(model_named(squad, "Serpent's Scale Platform"))),
          "Assault Guardian.png")


# ---------------------------------------------------------- 8. A/B probes

print("--- 8. A/B probes ---")

saved = invulnerable_save.unit_has_serpent_shield
invulnerable_save.unit_has_serpent_shield = lambda squad: False
squad8 = storm(name="1 Storm Guardians 8")
checks.eq("A/B: with Serpent Shield neutralised there is no invulnerable save",
          invulnerable_save.effective_invulnerable_save(model_named(squad8, "Storm Guardian")), "-")
invulnerable_save.unit_has_serpent_shield = saved
checks.eq("A/B: and it comes back when restored",
          invulnerable_save.effective_invulnerable_save(model_named(squad8, "Storm Guardian")), "5+")

checks.finish()
