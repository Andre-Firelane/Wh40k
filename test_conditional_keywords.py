"""Rule 24.01's conditional weapon abilities and the keyword conditions behind them.

"If a weapon ability is followed by one or more keywords, when making attacks
with that weapon, that ability only applies if the target unit has one or more
of those keywords." The core-rules FAQ adds the negated form: ANTI-NON-(keyword)
triggers on a unit WITHOUT the keyword - which is how the 2026-09 Ork codex's
"[LETHAL HITS: non-MONSTER/VEHICLE]" reads.

Four things, each with its own section:

  1. KeywordCondition - parsing, spelling, immutability, and matches() against
     real squads ("one or more of those keywords", and "non-" as the complement
     of that whole any()).
  2. conditional_keywords.adjusted_weapon() - the grant, including the two
     guards that make it a GRANT rather than a SET (never a downgrade, a dice
     value left alone) and the identity contract ("same object" = unchanged).
  3. The grant reaches BOTH controllers' adjuster chains - a helper that is
     correct and never called is this repo's most expensive failure shape.
  4. The Leystalker's long rifle, the first carrier, resolves exactly as it did
     under its retired single-purpose module, and nothing imports that module.
"""
import ast
import os

import testkit as tk
from game import conditional_keywords
from game import weapons as wp
from game.factions import orks, tau_empire as tau
from game.keyword_condition import (
    MONSTER_OR_VEHICLE_TARGETS, NON_MONSTER_VEHICLE_TARGETS, KeywordCondition,
)
from game.unit_keywords import unit_has_keyword
from game.weapons import MELEE, RANGED, printed_keywords

c = tk.Checks("conditional keywords (rule 24.01)")
HERE = os.path.dirname(os.path.abspath(__file__))


def section(title):
    print(f"--- {title} ---")


boyz = tk.build(orks.BOYZ, "Player 1", name="1 Boyz 1")
devilfish = tk.build(tau.DEVILFISH, "Player 1", name="1 Devilfish 1")


# ------------------------------------------------------ 1. KeywordCondition

section("1. KeywordCondition")

parsed = KeywordCondition.parse("non-MONSTER/VEHICLE")
c.eq("parse reads the keywords", parsed.keywords, ("MONSTER", "VEHICLE"))
c.eq("...and the non- prefix", parsed.negated, True)
c.eq("parse is case-insensitive about the prefix and upper-cases keywords",
     KeywordCondition.parse("Non-vehicle"), KeywordCondition(("VEHICLE",), negated=True))
c.eq("it spells itself the printed way", parsed.spelled, "non-MONSTER/VEHICLE")
c.eq("the positive form spells without a prefix", MONSTER_OR_VEHICLE_TARGETS.spelled, "MONSTER/VEHICLE")
c.eq("the shipped negated constant is what parse() builds", parsed, NON_MONSTER_VEHICLE_TARGETS)
c.eq("equal conditions hash equal (a weapon class can hold one in a set)",
     len({parsed, NON_MONSTER_VEHICLE_TARGETS}), 1)
try:
    parsed.negated = False
    c.true("a condition is immutable (assignment raised)", False)
except AttributeError:
    c.true("a condition is immutable (assignment raised)", True)

c.true("scene: the Boyz are INFANTRY", unit_has_keyword(boyz, "INFANTRY"))
c.true("scene: the Devilfish is a VEHICLE", unit_has_keyword(devilfish, "VEHICLE"))
c.true("scene: the Devilfish is not a MONSTER - so MONSTER/VEHICLE is really an any()",
       not unit_has_keyword(devilfish, "MONSTER"))

c.eq("no target never matches (the positive form)", MONSTER_OR_VEHICLE_TARGETS.matches(None), False)
c.eq("no target never matches (the NEGATED form either)", NON_MONSTER_VEHICLE_TARGETS.matches(None), False)
c.eq("MONSTER/VEHICLE: a vehicle has ONE of them, which is enough",
     MONSTER_OR_VEHICLE_TARGETS.matches(devilfish), True)
c.eq("MONSTER/VEHICLE: infantry has neither", MONSTER_OR_VEHICLE_TARGETS.matches(boyz), False)
c.eq("non-MONSTER/VEHICLE: infantry qualifies", NON_MONSTER_VEHICLE_TARGETS.matches(boyz), True)
c.eq("non-MONSTER/VEHICLE: a vehicle does not, whatever else it is",
     NON_MONSTER_VEHICLE_TARGETS.matches(devilfish), False)
c.eq("a single-keyword condition reads that keyword",
     KeywordCondition(("INFANTRY",)).matches(boyz), True)


# ------------------------------------------------- 2. adjusted_weapon()

section("2. conditional_keywords.adjusted_weapon()")


class LethalVsInfantryGun(wp.WeaponProfile):
    name = "Test Gun"
    conditional_keywords = (("lethal_hits", True, NON_MONSTER_VEHICLE_TARGETS),)


class SustainedVsVehicleBlade(wp.WeaponProfile):
    name = "Test Blade"
    weapon_type = MELEE
    conditional_keywords = (("sustained_hits", 2, MONSTER_OR_VEHICLE_TARGETS),)


class AlreadySustainedTwo(SustainedVsVehicleBlade):
    sustained_hits = 2
    conditional_keywords = (("sustained_hits", 1, MONSTER_OR_VEHICLE_TARGETS),)


class SustainedOneUpgraded(SustainedVsVehicleBlade):
    sustained_hits = 1


class DiceSustained(SustainedVsVehicleBlade):
    sustained_hits_notation = "D3"


class TwoEntries(wp.WeaponProfile):
    name = "Two Entries"
    conditional_keywords = (
        ("lethal_hits", True, NON_MONSTER_VEHICLE_TARGETS),
        ("devastating_wounds", True, MONSTER_OR_VEHICLE_TARGETS),
    )


gun = LethalVsInfantryGun()
c.eq("no weapon passes through as None", conditional_keywords.adjusted_weapon(None, boyz), None)
c.true("no target returns the SAME object", conditional_keywords.adjusted_weapon(gun, None) is gun)
c.true("a condition the target does not meet returns the SAME object",
       conditional_keywords.adjusted_weapon(gun, devilfish) is gun)
granted = conditional_keywords.adjusted_weapon(gun, boyz)
c.true("a met condition returns a COPY", granted is not gun)
c.eq("...carrying the ability", granted.lethal_hits, True)
c.eq("...and the carried instance is untouched", gun.lethal_hits, False)
c.eq("...and so is the class", LethalVsInfantryGun.lethal_hits, False)

blade = SustainedVsVehicleBlade()
c.eq("a valued ability is granted at its printed value", conditional_keywords.adjusted_weapon(blade, devilfish).sustained_hits, 2)
two = AlreadySustainedTwo()
c.true("never a downgrade: a printed [SUSTAINED HITS 2] keeps its 2 against a grant of 1",
       conditional_keywords.adjusted_weapon(two, devilfish) is two)
one = SustainedOneUpgraded()
c.eq("a smaller printed value IS raised to the granted one",
     conditional_keywords.adjusted_weapon(one, devilfish).sustained_hits, 2)
dice = DiceSustained()
c.true("a dice-notation [SUSTAINED HITS] is left alone",
       conditional_keywords.adjusted_weapon(dice, devilfish) is dice)

both = TwoEntries()
vs_boyz = conditional_keywords.adjusted_weapon(both, boyz)
vs_fish = conditional_keywords.adjusted_weapon(both, devilfish)
c.eq("two entries: each is tested on its own (infantry gets the first only)",
     (vs_boyz.lethal_hits, vs_boyz.devastating_wounds), (True, False))
c.eq("...and a vehicle the second only", (vs_fish.lethal_hits, vs_fish.devastating_wounds), (False, True))
c.eq("entries() is a tuple, empty for a plain weapon", conditional_keywords.entries(wp.WeaponProfile()), ())

c.eq("printed_keywords spells a conditional flag the way the sheet does",
     printed_keywords(LethalVsInfantryGun), ["LETHAL HITS: non-MONSTER/VEHICLE"])
c.eq("...and a valued one with its value", printed_keywords(SustainedVsVehicleBlade),
     ["SUSTAINED HITS 2: MONSTER/VEHICLE"])


# ------------------------------------------- 3. both adjuster chains read it

section("3. the grant reaches both controllers' adjuster chains")

shot = tk.shooting_scene(tau.STRIKE_TEAM, orks.BOYZ, attacker_owner="Player 1", gap=10.0)
shooter = shot["attacker"].models[0]
carried = LethalVsInfantryGun()
shooter.weapons = [carried]
chain_vs_boyz = shot["shooting"]._adjusted_weapon([(shooter, carried)], shot["target"])
c.eq("ShootingController._adjusted_weapon grants [LETHAL HITS] against infantry",
     chain_vs_boyz.lethal_hits, True)
chain_vs_fish = shot["shooting"]._adjusted_weapon([(shooter, carried)], devilfish)
c.eq("...and not against a vehicle", chain_vs_fish.lethal_hits, False)
c.eq("...and the carried instance never changes", carried.lethal_hits, False)

melee = tk.fight_scene(tau.STRIKE_TEAM, orks.BOYZ, attacker_owner="Player 1")
swinger = melee["attacker"].models[0]
carried_blade = SustainedVsVehicleBlade()
swinger.weapons = [carried_blade]
fc = melee["fight"]
c.eq("FightController._adjusted_weapon grants nothing against infantry",
     fc._adjusted_weapon([(swinger, carried_blade)], melee["target"]).sustained_hits, 0)
c.eq("...and [SUSTAINED HITS 2] against a vehicle",
     fc._adjusted_weapon([(swinger, carried_blade)], devilfish).sustained_hits, 2)


# ------------------------------------- 4. the first carrier, and the retirement

section("4. the Leystalker's long rifle and the retired module")

rifle = wp.ExoditeLongRifleProfile()
c.eq("the long rifle holds its condition as data",
     [(a, v, cond.spelled) for a, v, cond in rifle.conditional_keywords],
     [("devastating_wounds", True, "non-MONSTER/VEHICLE")])
c.eq("[DEVASTATING WOUNDS] against infantry, as before",
     conditional_keywords.adjusted_weapon(rifle, boyz).devastating_wounds, True)
c.eq("...and not against a vehicle, as before",
     conditional_keywords.adjusted_weapon(rifle, devilfish).devastating_wounds, False)
c.true("the retired module's file is gone",
       not os.path.exists(os.path.join(HERE, "game", "conditional_devastating_wounds.py")))

# Per AST, not per text: game/conditional_keywords.py names the retired module
# in its own docstring, as history, and a text search would read that as a use.
stale_imports, stale_attrs, scanned = [], [], 0
for folder in ("game", "ai", "."):
    root = os.path.join(HERE, folder)
    for name in sorted(os.listdir(root)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(root, name)
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        scanned += 1
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
                if any("conditional_devastating_wounds" in n for n in names):
                    stale_imports.append(name)
            elif isinstance(node, ast.Import):
                if any("conditional_devastating_wounds" in a.name for a in node.names):
                    stale_imports.append(name)
            elif isinstance(node, ast.Attribute) and node.attr == "devastating_wounds_vs_non_monster_vehicle":
                stale_attrs.append(name)
c.true("the sweep read a real number of modules (>300)", scanned > 300)
c.eq("nothing imports the retired module", sorted(set(stale_imports)), [])
c.eq("nothing reads the retired profile flag", sorted(set(stale_attrs)), [])
c.true("...and WeaponProfile no longer declares it",
       not hasattr(wp.WeaponProfile, "devastating_wounds_vs_non_monster_vehicle"))

c.finish()
