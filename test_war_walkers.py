"""War Walkers: statline, weapons, the matched-pair wargear, Crystalline
Targeting, and the sprite.

Crystalline Targeting is the interesting half, and it is checked through the
REAL ShootingController rather than off the controller's own ledger: a mark that
is set and never read is exactly the failure a "did the flag change" test cannot
see. So the AP is measured where it actually matters - on the weapon the save
step is handed.

Its two lifetimes are the other thing worth pinning. The AP effect is "until the
end of the phase"; the "each unit can only be selected for this ability once per
turn" limit is longer-lived AND is a limit on the TARGET, not on the War
Walkers. Those are two different clocks on purpose, so each is checked on its
own.
"""

import testkit as tk
from game import crystalline_targeting, sprites
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.units import WarWalkerProfile
from game.weapons import (
    BrightLanceProfile,
    MissileLauncherStarshotProfile,
    MissileLauncherSunburstProfile,
    ScatterLaserProfile,
    ShurikenCannonProfile,
    StarcannonProfile,
    WarWalkerFeetProfile,
)

checks = tk.Checks("War Walkers")

LINE = "War Walker"


def walkers(choices=None, models=1, owner="Player 1", name=None):
    return tk.build(ae.WAR_WALKERS, owner,
                    name=name or ("1 War Walkers 1" if owner == "Player 1" else "2 War Walkers 1"),
                    composition_index=0 if models == 1 else 1,
                    choices={LINE: choices} if choices else None)


def weapon_names(squad, index=0):
    return sorted(w.name for w in squad.models[index].weapons)


# --- 1. statline ------------------------------------------------------------
print("--- 1. statline ---")

one = walkers()
p = one.models[0].profile

checks.eq("M10\"", p.movement_in, 10)
checks.eq("T7", p.toughness, 7)
checks.eq("Sv3+", p.armor_save, "3+")
checks.eq("W6", p.wounds, 6)
checks.eq("Ld7+", p.leadership, "7+")
checks.eq("OC2", p.oc, 2)
checks.eq("BS3+", p.ballistic_skill, "3+")
checks.eq("WS3+", p.weapon_skill, "3+")
checks.eq("Invulnerable Save 5+", p.invulnerable_save, "5+")
checks.eq("VEHICLE", p.vehicle, True)
# 60 mm printed, and unlike the Falcon and the Wave Serpent it KEEPS it: those
# two are grav-tanks and were matched to the Devilfish on user request, a walker
# is not one of them. Checked as arithmetic so a typo in either number shows.
checks.eq("60 mm base, converted like every other base here",
          round(p.base_radius_in, 3), round(60 / 2 / 25.4, 3))
checks.true("...and it is NOT the enlarged grav-tank radius the Falcon uses",
            p.base_radius_in < ae.FALCON.model_lines[0].profile_cls.base_radius_in)

checks.eq("Battle Focus (army rule) - this is what makes the owner ASURYANI",
          p.battle_focus, True)
checks.eq("Scouts 9\" (24.31/24.32)", p.scouts, 9.0)
checks.eq("Crystalline Targeting flag", p.crystalline_targeting, True)
checks.eq("no Deep Strike printed", getattr(p, "deep_strike", False), False)
checks.eq("no Deadly Demise printed", getattr(p, "deadly_demise_notation", None), None)

checks.eq("1-2 models: two composition options",
          len(ae.WAR_WALKERS.composition_options), 2)
checks.eq("...the first is one model", len(one.models), 1)
checks.eq("...the second is two", len(walkers(models=2).models), 2)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("default loadout is TWO shuriken cannons plus the feet",
          weapon_names(one), ["Shuriken Cannon", "Shuriken Cannon", "War Walker Feet"])

feet = WarWalkerFeetProfile()
checks.eq("War Walker Feet A3", feet.attacks, 3)
checks.eq("...WS3+", feet.weapon_skill, "3+")
checks.eq("...S5", feet.strength, 5)
checks.eq("...AP0", feet.ap, 0)
checks.eq("...D1", feet.damage, 1)
# Its own class rather than the Wraithbone Hull the other Aeldari vehicles use:
# same row shape, different numbers, which is the recipe's "new class" branch.
checks.true("...and it is NOT the Wraithbone Hull (A3/WS4+/S6)",
            (feet.weapon_skill, feet.strength) != ("4+", 6))

lance = BrightLanceProfile()
checks.eq("Bright Lance S12/AP-3", (lance.strength, lance.ap), (12, -3))
scatter = ScatterLaserProfile()
checks.eq("Scatter Laser [SUSTAINED HITS 1]", scatter.sustained_hits, 1)
cannon = ShurikenCannonProfile()
checks.eq("Shuriken Cannon [LETHAL HITS]", cannon.lethal_hits, True)
star = StarcannonProfile()
checks.eq("Starcannon S8/AP-3/D2", (star.strength, star.ap, star.damage), (8, -3, 2))

# The missile launcher is one datasheet entry with two firing profiles, so the
# sunburst is the starshot's overcharge - the shape this engine uses for every
# such pair, and the reason only ONE of them is granted by the swap.
starshot = MissileLauncherStarshotProfile()
checks.eq("Missile Launcher starshot S10/AP-2", (starshot.strength, starshot.ap), (10, -2))
checks.eq("...its sunburst is the alternate FIRING MODE, not a second weapon",
          starshot.overcharge_profile, MissileLauncherSunburstProfile)
# Pre-existing gap this datasheet made live on a third sheet: the printed name
# is "missile launcher - sunburst BLAST", and the Dark Reapers' own copy already
# set the keyword, so the two would otherwise have disagreed.
checks.eq("...and the sunburst carries [BLAST]", MissileLauncherSunburstProfile().blast, 1)


# --- 3. wargear: matched pairs ---------------------------------------------
print("--- 3. wargear ---")

# The printed text is per-CANNON, so a mixed pair is legal on paper. This
# scaffold addresses MODELS, not weapon copies, so the four swaps are written as
# matched pairs - every result below is a legal printed build; only the mixed
# pair is out of reach, which is what the datasheet comment records.
for option, expected in (
    (ae.WAR_WALKER_TO_BRIGHT_LANCE, "Bright Lance"),
    (ae.WAR_WALKER_TO_SCATTER_LASER, "Scatter Laser"),
    (ae.WAR_WALKER_TO_STARCANNON, "Starcannon"),
    (ae.WAR_WALKER_TO_MISSILE, "Missile Launcher - Starshot"),
):
    got = weapon_names(walkers({option: 1}))
    checks.eq("%s gives TWO of them" % option, got.count(expected), 2)
    checks.eq("...and gives up BOTH shuriken cannons", got.count("Shuriken Cannon"), 0)
    checks.eq("...the feet are untouched", got.count("War Walker Feet"), 1)

checks.eq("default keeps both cannons", weapon_names(one).count("Shuriken Cannon"), 2)

# Four options competing for the same weapon on ONE model: whichever lands first
# leaves the rest with nobody to claim - the same mutual exclusivity the Falcon's
# turret swaps get, and for the same structural reason.
both = weapon_names(walkers({ae.WAR_WALKER_TO_BRIGHT_LANCE: 1,
                             ae.WAR_WALKER_TO_SCATTER_LASER: 1}))
checks.eq("two turret swaps on one model: only one lands (mutually exclusive)",
          (both.count("Bright Lance"), both.count("Scatter Laser")), (2, 0))

two = walkers({ae.WAR_WALKER_TO_STARCANNON: 2}, models=2)
checks.eq("a 2-model unit can arm both walkers", weapon_names(two, 0).count("Starcannon"), 2)
checks.eq("...both of them", weapon_names(two, 1).count("Starcannon"), 2)

over = walkers({ae.WAR_WALKER_TO_BRIGHT_LANCE: 5}, models=1)
checks.eq("an over-eager choice is trimmed, not an error",
          weapon_names(over).count("Bright Lance"), 2)


# --- 4. points --------------------------------------------------------------
print("--- 4. points ---")

entry = AELDARI_POINTS["War Walkers"]
checks.eq("1 model = 85 pts", entry.cost_for(1, 1), 85)
checks.eq("2 models = 160 pts", entry.cost_for(2, 1), 160)
checks.eq("no copy tiers - the same price for the army's third unit",
          entry.cost_for(2, 3), 160)
checks.eq("built squad carries the price", walkers(models=2).points, 160)
checks.eq("...and every wargear option is free",
          walkers({ae.WAR_WALKER_TO_BRIGHT_LANCE: 1}).points, 85)


# --- 5. Crystalline Targeting ----------------------------------------------
print("--- 5. Crystalline Targeting ---")

checks.eq("applies() reads the flag off the models", crystalline_targeting.applies(one), True)
checks.eq("...and a unit without it is not a source",
          crystalline_targeting.applies(tk.build(ae.RANGERS, "Player 1", name="1 Rangers 1")), False)


def scene():
    """A War Walker unit, and two enemy units it could have hit."""
    shooter = walkers(models=2)
    a = tk.build(ae.RANGERS, "Player 2", name="2 Rangers 1")
    b = tk.build(ae.RANGERS, "Player 2", name="2 Rangers 2")
    return shooter, a, b


shooter, target_a, target_b = scene()
dm = tk.DecisionManager() if hasattr(tk, "DecisionManager") else None
log = tk.Log()
ctrl = crystalline_targeting.CrystallineTargetingController(decision_manager=None, game_log=log)

ctrl.offer_after_shooting(shooter, [target_a])
checks.eq("one unit hit -> marked without a prompt", ctrl.is_marked(target_a), True)
checks.eq("...the other is untouched", ctrl.is_marked(target_b), False)
checks.true("...and it is logged", log.has("Crystalline Targeting"))

# "each time a FRIENDLY AELDARI unit makes an attack that targets that enemy
# unit" - so the bonus is army-wide, but only for AELDARI attackers.
checks.eq("an AELDARI attacker gets +1 AP", ctrl.ap_bonus(shooter, target_a), 1)
ork = tk.build(__import__("game.factions.orks", fromlist=["BOYZ"]).BOYZ,
               "Player 2", name="2 Boyz 1")
checks.eq("a non-AELDARI attacker gets nothing", ctrl.ap_bonus(ork, target_a), 0)
checks.eq("an unmarked target gets nothing", ctrl.ap_bonus(shooter, target_b), 0)

# The AP arithmetic: "improve by 1" means MORE negative, never mutating the
# shared profile - the convention every adjuster in the chain follows.
base = ShurikenCannonProfile()
adjusted = crystalline_targeting.adjusted_weapon(base, ctrl, shooter, target_a)
checks.eq("improve AP by 1 = one MORE negative", adjusted.ap, base.ap - 1)
checks.eq("...the shared profile is never mutated", ShurikenCannonProfile().ap, base.ap)
checks.true("...and it is a copy", adjusted is not base)
checks.eq("no bonus -> the very same weapon object back, no copy",
          crystalline_targeting.adjusted_weapon(base, ctrl, shooter, target_b) is base, True)

# Two lifetimes, deliberately different clocks.
ctrl.reset_phase()
checks.eq("the AP effect ends with the phase", ctrl.is_marked(target_a), False)
ctrl.offer_after_shooting(shooter, [target_a])
checks.eq("...but the same unit cannot be picked again this TURN",
          ctrl.is_marked(target_a), False)
ctrl.offer_after_shooting(shooter, [target_b])
checks.eq("...a DIFFERENT unit still can", ctrl.is_marked(target_b), True)
ctrl.reset_turn()
ctrl.reset_phase()
ctrl.offer_after_shooting(shooter, [target_a])
checks.eq("a new turn frees the target again", ctrl.is_marked(target_a), True)

# "each unit can only be selected ONCE PER TURN" limits the TARGET, so a SECOND
# War Walker unit may still use its own ability - just not on that unit.
ctrl2 = crystalline_targeting.CrystallineTargetingController(game_log=tk.Log())
ctrl2.offer_after_shooting(shooter, [target_a])
second = walkers(models=1, name="1 War Walkers 2")
ctrl2.offer_after_shooting(second, [target_a, target_b])
checks.eq("a second source skips the already-picked unit and takes the other",
          (ctrl2.is_marked(target_a), ctrl2.is_marked(target_b)), (True, True))

nothing = crystalline_targeting.CrystallineTargetingController(game_log=tk.Log())
nothing.offer_after_shooting(shooter, [])
checks.eq("hitting nothing marks nothing", nothing.is_marked(target_a), False)
nothing.offer_after_shooting(tk.build(ae.RANGERS, "Player 1", name="1 Rangers 9"), [target_a])
checks.eq("a unit without the ability marks nothing", nothing.is_marked(target_a), False)


# --- 6. end to end through the real ShootingController ---------------------
print("--- 6. end to end ---")

scene = tk.shooting_scene(ae.WAR_WALKERS, ae.RANGERS, gap=12.0)
sc = scene["shooting"]
sc.active_squad = scene["attacker"]
sc.crystalline_targeting = crystalline_targeting.CrystallineTargetingController(
    game_log=scene["log"])

pairs = [(scene["attacker"].models[0], ShurikenCannonProfile())]
before = sc._adjusted_weapon(pairs, scene["target"]).ap
sc.crystalline_targeting.offer_after_shooting(scene["attacker"], [scene["target"]])
after = sc._adjusted_weapon(pairs, scene["target"]).ap
checks.eq("the mark reaches the weapon the save step is handed", after, before - 1)

# A/B: with the controller unplugged the very same call must NOT change the AP,
# or the difference above would prove nothing about this ability.
sc.crystalline_targeting = None
checks.eq("A/B: unplugged, the AP is untouched",
          sc._adjusted_weapon(pairs, scene["target"]).ap, before)


# --- 7. sprite --------------------------------------------------------------
print("--- 7. sprite ---")

checks.true("War Walkers resolve a sprite", sprites.sprite_for(one.models[0]))
checks.true("...and it is the War Walker file (the datasheet is plural, the file is not)",
            "War Walker" in (sprites.sprite_for(one.models[0]) or ""))


checks.finish()
