"""Two engine mechanisms that ORK wargear introduced and no shipped datasheet
carries any more, kept honest on SYNTHETIC carriers - plus the retirement pins
for the wargear that took them away.

  1. A dice-notation STRENGTH characteristic (`WeaponProfile.strength_notation`,
     ShootingController's "strength" pending step). Built for the Battlewagon's
     Zzap Gun ("D6+6"); the 2026-09 Ork codex dropped the Zzap Gun (stage E3d),
     and no other built weapon rolls its Strength. The step is live code with no
     rostered carrier, so it is driven here on a stand-in with the Zzap Gun's
     own numbers - a mechanism shipped inert and driven by no test is broken on
     the day its next carrier arrives (the WALL_CROSSING_COST_IN precedent).
  2. A PRICED Gear item (`Gear.points`, Datasheet._gear_cost()). First used by
     the Battlewagon's 'Ard Case, also retired in E3d; every Gear item still
     built is free.

The Warboss's Attack Squig and the Flash Gitz' Ammo Runt were two more items
here and went with their pre-codex sheets (test_ork_characters.py and
test_ork_specialists.py own the new ones).

Run: python test_ork_wargear.py

Built on testkit.py (see its docstring for the headless-harness traps).
"""

import os
import re

from testkit import Checks, build, script, shooting_scene

import game.factions.orks as _orks
import game.weapons as _weapons
from game.dice_notation import D6, describe as describe_dice
from game.factions.datasheet import Datasheet, Gear, ModelLine
from game.factions.orks import BATTLEWAGON
from game.factions.points import flat_points
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM
from game.units import UnitProfile
from game.weapons import BigShootaProfile, RANGED, WeaponProfile

c = Checks("Ork wargear mechanisms")


class DiceStrengthGun(WeaponProfile):
    """The retired Zzap Gun's printed row, as a stand-in: 36" A1 S D6+6 AP-3 D5,
    [ANTI-VEHICLE 4+]."""
    name = "Dice Strength Gun"
    weapon_type = RANGED
    range_in = 36
    attacks = 1
    strength = 9          # a grouping/preview placeholder only
    strength_notation = D6(6)
    ap = -3
    damage = 5
    anti = (("VEHICLE", 4),)


# ---------------------------------------------------------------------------
# 1. a dice-notation Strength: the profile
# ---------------------------------------------------------------------------

gun = DiceStrengthGun()
c.true("Strength is a dice notation, not a fixed number", gun.strength_notation is not None)
c.eq("...printed as D6+6", describe_dice(gun.strength_notation), "D6+6")
c.true("the fixed `strength` is only a placeholder, inside D6+6's real range",
       7 <= gun.strength <= 12)


# ---------------------------------------------------------------------------
# 2. ...and the Strength is really rolled, END TO END
# ---------------------------------------------------------------------------

def armed_scene():
    """A Battlewagon (whose default loadout has no ranged weapon since E3d)
    carrying the stand-in and a plain Big Shoota, ten inches from a T9 Devilfish."""
    scene = shooting_scene(BATTLEWAGON, DEVILFISH, gap=10.0)
    scene["attacker"].models[0].weapons = [DiceStrengthGun(), BigShootaProfile()]
    return scene


def fire(strength_die, hit=6, wound=4):
    """One shot through the real controller. `strength_die` is what the D6
    comes up as, so the resolved Strength is that + 6."""
    scene = armed_scene()
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    sc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in sc.weapon_eligibility() if "Dice Strength" in str(rest[0]))
    script(hit)                       # the hit roll
    sc.choose_weapon(key)
    sc.dice_manager.acknowledge()
    script(strength_die)              # then the Strength roll
    sc.on_dice_acknowledged()
    strength_step = sc.pending_step
    sc.dice_manager.acknowledge()
    script(wound)                     # then the wound roll
    sc.on_dice_acknowledged()
    # ...and acknowledge THAT too, or the wound line is never logged.
    sc.dice_manager.acknowledge()
    sc.on_dice_acknowledged()
    return scene, strength_step


scene, step = fire(strength_die=3)
c.eq("a Strength step really happens, before the wound roll", step, "strength")
c.true("...and it is a visible dice roll",
       any("strength" in label.lower() for label, _ in scene["dice"].rolled))
c.true("...logged with the resolved value", scene["log"].has("Strength 9"))


def wounds_from_log(scene):
    match = re.search(r"(\d+) wound\(s\)", scene["log"].find("wound roll"))
    return int(match.group(1)) if match else None


# The rolled value, not the placeholder, decides the wound threshold. The
# Devilfish is T9, so S7 needs a 5+ and S12 a 3+ - a wound roll of exactly 3
# separates them. 3 rather than 4: [ANTI-VEHICLE 4+] makes an unmodified 4 a
# critical wound against a VEHICLE whatever the Strength, which would mask the
# very difference under test.
weak, _ = fire(strength_die=1, wound=3)
strong, _ = fire(strength_die=6, wound=3)
c.true("both runs reached the wound step",
       weak["log"].has("wound roll") and strong["log"].has("wound roll"))
c.eq("S7 vs T9 (needs 5+): a wound roll of 3 fails", wounds_from_log(weak), 0)
c.eq("S12 vs T9 (needs 3+): the same 3 wounds", wounds_from_log(strong), 1)
c.eq("a 4 wounds even at S7, via [ANTI-VEHICLE 4+]",
     wounds_from_log(fire(strength_die=1, wound=4)[0]), 1)
c.true("...and the two rolled different Strengths",
       weak["log"].has("Strength 7") and strong["log"].has("Strength 12"))

# A weapon WITHOUT a dice Strength must not gain a Strength step.
plain = armed_scene()
sc = plain["shooting"]
sc.start_shooting(plain["attacker"])
sc.choose_target_squad(plain["target"])
big_key = next(k for k, *rest in sc.weapon_eligibility() if "Big Shoota" in str(rest[0]))
script(*([6] * 20))
sc.choose_weapon(big_key)
sc.dice_manager.acknowledge()
sc.on_dice_acknowledged()
c.eq("a Big Shoota goes straight to the wound roll", sc.pending_step, "wound")


# ---------------------------------------------------------------------------
# 3. a PRICED Gear item
# ---------------------------------------------------------------------------

class _PlateProfile(UnitProfile):
    name = "Plated Grot"
    toughness = 3
    wounds = 1
    armor_save = "6+"


def _plate(token):
    token.profile = type(token.profile)()
    token.profile.toughness += 2


PLATED = Datasheet(
    name="Plated Grot",
    model_lines=[ModelLine(_PlateProfile, 1, [])],
    gear_options=[Gear("Plated Grot", "Test Plate", _plate, points=15)],
    gear_slots={"Plated Grot": 1},
    points=flat_points({1: 20}),
)
plain_grot = build(PLATED, name="Grot 1")
plated = build(PLATED, name="Grot 2", gear={"Plated Grot": ["Test Plate"]})
c.eq("the item's effect applies", plated.models[0].profile.toughness, 5)
c.eq("...and only on the model that took it", plain_grot.models[0].profile.toughness, 3)
c.eq("it costs its price", plated.points - plain_grot.points, 15)
greedy = build(PLATED, name="Grot 3", gear={"Plated Grot": ["Test Plate", "Test Plate"]})
c.eq("a second copy beyond max_count is trimmed, not stacked", greedy.models[0].profile.toughness, 5)
c.eq("...and not charged twice", greedy.points, plated.points)
droned = build(STRIKE_TEAM, "Player 1", name="ST 2", gear={"Fire Warrior Shas'ui": ["Shield Drone"]})
c.eq("a free gear item still costs nothing", droned.points,
     build(STRIKE_TEAM, "Player 1", name="ST 1").points)


# ---------------------------------------------------------------------------
# 4. retirements (2026-09 Ork codex)
# ---------------------------------------------------------------------------

for _name in ("AttackSquigProfile", "DeffRollaProfile",
              "KoptaRokkitsProfile", "StompyFeetProfile", "TracksAndWheelsProfile"):
    c.true("game/weapons.py no longer defines %s" % _name, not hasattr(_weapons, _name))
# The Zzap Gun and the Lobba are BACK under their old class names, as the
# Gunwagon's codex rows (Mecha Orks stage G1) - not the pre-codex Battlewagon's.
# What retired stays retired: the rolled Strength, and the Battlewagon's options.
_zzap = getattr(_weapons, "ZzapGunProfile", None)
c.eq("the Zzap Gun is the Gunwagon's flat S8 row, not the pre-codex rolled Strength",
     (getattr(_zzap, "strength", None), getattr(_zzap, "strength_notation", "missing"),
      getattr(_zzap, "damage", None)), (8, None, 4))
_lobba = getattr(_weapons, "LobbaProfile", None)
c.eq("the Lobba is the Gunwagon's 48\" A3 S5 [BLAST 3] row",
     (getattr(_lobba, "range_in", None), getattr(_lobba, "attacks", None),
      getattr(_lobba, "strength", None), getattr(_lobba, "blast", None)), (48, 3, 5, 3))
c.true("...and neither is on the Battlewagon's wargear menu",
       not any(w in (_zzap, _lobba) for option in _orks.BATTLEWAGON.wargear_options
               for w in option.with_weapons))
for _name in ("BATTLEWAGON_ADD_ZZAP_GUN", "BATTLEWAGON_ARD_CASE"):
    c.true("game/factions/orks.py no longer offers %s" % _name, not hasattr(_orks, _name))
_game = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game")
for _module in ("ammo_runt.py", "ramshackle.py", "drive_by_dakka.py", "grot_riggers.py"):
    c.true("game/%s is gone with its pre-codex datasheet" % _module,
           not os.path.exists(os.path.join(_game, _module)))

c.finish()
