"""Flash Gitz (Orks) - datasheet and Gun-crazy Show-offs.

Run: python test_flash_gitz.py

Built on testkit.py (see its docstring for the headless-harness traps).
"""

from testkit import Checks, GameState, build, line_up, script, shooting_scene

from game import gun_crazy_showoffs as gcs
from game.factions.orks import BEAST_SNAGGA_BOYZ, BOYZ, FLASH_GITZ
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM

c = Checks("Flash Gitz")

# ---------------------------------------------------------------------------
# 1. Datasheet
# ---------------------------------------------------------------------------

squad = build(FLASH_GITZ, name="Flash Gitz 1")
c.eq("unit size", len(squad.models), 5)
c.eq("points (5 models, 1st-2nd unit)", squad.points, 75)

kaptin, git = squad.models[0], squad.models[1]
c.eq("the Kaptin is the leader model", kaptin.profile.squad_leader, True)
c.eq("a rank-and-file Git is not", getattr(git.profile, "squad_leader", False), False)
c.eq("both share the same wounds", (kaptin.profile.wounds, git.profile.wounds), (2, 2))

for label, p in (("kaptin", kaptin.profile), ("git", git.profile)):
    c.eq(f"{label} base radius (40mm)", round(p.base_radius_in, 2), 0.79)
    c.eq(f"{label} move", p.movement_in, 6)
    c.eq(f"{label} toughness", p.toughness, 5)
    c.eq(f"{label} save", p.armor_save, "4+")
    c.eq(f"{label} leadership", p.leadership, "7+")
    c.eq(f"{label} OC", p.oc, 1)
    c.eq(f"{label} WS", p.weapon_skill, "3+")
    c.eq(f"{label} BS", p.ballistic_skill, "5+")
    c.eq(f"{label} INFANTRY", p.infantry, True)
    c.eq(f"{label} GRENADES", p.grenades, True)
    c.eq(f"{label} Gun-crazy Show-offs", p.gun_crazy_showoffs, True)
    c.eq(f"{label} Waaagh!", p.waaagh, True)
    c.eq(f"{label} Orks faction flag", p.orks, True)

c.eq("datasheet keywords", set(FLASH_GITZ.keywords), {"INFANTRY", "GRENADES", "FLASH GITZ"})
c.eq("the 40mm base is bigger than the Ork 32mm one",
     round(git.profile.base_radius_in, 2) > round(build(BOYZ).models[1].profile.base_radius_in, 2), True)

snazz = next(w for w in git.weapons if w.name == "Snazzgun")
c.eq("snazzgun range", snazz.range_in, 24)
c.eq("snazzgun printed attacks", snazz.attacks, 3)
c.eq("snazzgun strength", snazz.strength, 6)
c.eq("snazzgun AP", snazz.ap, -1)
c.eq("snazzgun damage", snazz.damage, 2)
c.eq("snazzgun is [HEAVY]", snazz.heavy, True)
c.eq("snazzgun has [SUSTAINED HITS 1]", snazz.sustained_hits, 1)
c.eq("snazzgun needs no BS override (matches the model's 5+)", snazz.ballistic_skill, None)

choppa = next(w for w in git.weapons if w.name == "Choppa")
c.eq("choppa attacks", choppa.attacks, 4)
c.eq("choppa strength", choppa.strength, 5)
c.eq("choppa AP", choppa.ap, -1)
c.eq("choppa damage", choppa.damage, 1)
c.eq("choppa needs no WS override", choppa.weapon_skill, None)

# Third same-named Choppa in the file - the reuse was correctly NOT made.
boyz_choppa = next(w for w in build(BOYZ).models[1].weapons if w.name == "Choppa")
bsb_choppa = next(w for w in build(BEAST_SNAGGA_BOYZ).models[1].weapons if w.name == "Choppa")
c.eq("Boyz' Choppa is still A3/S4", (boyz_choppa.attacks, boyz_choppa.strength), (3, 4))
c.eq("Beast Snagga's Choppa is still A3/S5", (bsb_choppa.attacks, bsb_choppa.strength), (3, 5))
c.eq("Flash Gitz' Choppa is A4/S5", (choppa.attacks, choppa.strength), (4, 5))
c.true("all three are different classes",
       len({type(boyz_choppa), type(bsb_choppa), type(choppa)}) == 3)

# The Kaptin's loadout is identical to the rank and file - the datasheet
# prints no upgrade at all, which is unusual enough to pin down.
c.eq("the Kaptin carries exactly the same weapons",
     sorted(w.name for w in kaptin.weapons), sorted(w.name for w in git.weapons))
c.eq("every model has a Snazzgun",
     sum(1 for m in squad.models if any(w.name == "Snazzgun" for w in m.weapons)), 5)


# ---------------------------------------------------------------------------
# 2. Gun-crazy Show-offs: the adjuster
# ---------------------------------------------------------------------------

pairs = [(git, snazz)]

c.eq("against the closest eligible target the Snazzgun is A4",
     gcs.gun_crazy_adjusted_weapon(snazz, pairs, True).attacks, 4)
c.true("against anything else it is untouched",
       gcs.gun_crazy_adjusted_weapon(snazz, pairs, False) is snazz)
c.eq("the shared instance is never mutated", snazz.attacks, 3)

# Scoped by weapon name AND by the model's own ability - both halves needed.
c.true("the unit's Choppa gains nothing (not a Snazzgun)",
       gcs.gun_crazy_adjusted_weapon(choppa, [(git, choppa)], True) is choppa)
outsider = build(BOYZ, name="Outsiders").models[1]
c.true("a Snazzgun in someone else's hands gains nothing",
       gcs.gun_crazy_adjusted_weapon(snazz, [(outsider, snazz)], True) is snazz)

# "has an Attacks characteristic of 4" is an override, not a bonus.
import copy as _copy  # noqa: E402
already_four = _copy.copy(snazz)
already_four.attacks = 5
c.true("a weapon already at 5 attacks is left alone",
       gcs.gun_crazy_adjusted_weapon(already_four, pairs, True) is already_four)

c.eq("unit predicate", gcs.unit_has_gun_crazy_showoffs(squad), True)
c.eq("a unit without the ability", gcs.unit_has_gun_crazy_showoffs(build(BOYZ, name="B")), False)
dead = build(FLASH_GITZ, name="Dead Gitz")
for m in dead.models:
    m.current_wounds = 0
c.eq("the ability dies with the models (19.04)", gcs.unit_has_gun_crazy_showoffs(dead), False)


# ---------------------------------------------------------------------------
# 3. END TO END: the Hit roll actually gets more dice
# ---------------------------------------------------------------------------

def shoot_at(target_sheet, decoy_gap=None):
    """Five Flash Gitz shooting their Snazzguns. If `decoy_gap` is given, a
    SECOND enemy unit is placed that much closer, so the one being shot at
    is no longer the closest eligible target."""
    scene = shooting_scene(FLASH_GITZ, target_sheet, gap=10.0)
    if decoy_gap is not None:
        decoy = build(target_sheet, "Player 1", name="Decoy")
        line_up(decoy, x=20.0, y=20.0 + decoy_gap)
        for m in decoy.models:
            scene["state"].add_token(m)
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    sc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in sc.weapon_eligibility() if "Snazzgun" in str(rest[0]))
    script(*([1] * 60))  # every die a miss - only the COUNT is under test
    sc.choose_weapon(key)
    return scene


def hit_dice(scene):
    for label, values in scene["dice"].rolled:
        if "hit roll" in label.lower():
            return len(values)
    return None


closest = shoot_at(STRIKE_TEAM)
c.eq("5 Snazzguns at the closest target roll 5 x 4 = 20 hit dice", hit_dice(closest), 20)

not_closest = shoot_at(STRIKE_TEAM, decoy_gap=4.0)
c.eq("with a nearer unit on the board it is 5 x 3 = 15", hit_dice(not_closest), 15)
c.true("...and that is genuinely fewer", (hit_dice(not_closest) or 0) < (hit_dice(closest) or 0))

# A/B: the same scene with the ability neutralised must give the printed 15,
# otherwise the 20 above would not prove the ability did anything.
_saved = gcs.GUN_CRAZY_ATTACKS
import game.shooting as _shooting  # noqa: E402
_orig = _shooting.gun_crazy_adjusted_weapon
_shooting.gun_crazy_adjusted_weapon = lambda w, p, i: w
c.eq("A/B: unwired, the closest target gets only the printed 15",
     hit_dice(shoot_at(STRIKE_TEAM)), 15)
_shooting.gun_crazy_adjusted_weapon = _orig
c.eq("...and it is wired again", hit_dice(shoot_at(STRIKE_TEAM)), 20)

# The bonus is about being CLOSEST, not about what the target is.
vehicle = shoot_at(DEVILFISH)
c.eq("a VEHICLE target that is closest gets the same treatment", hit_dice(vehicle), 20)

c.finish()
