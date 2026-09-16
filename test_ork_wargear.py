"""The wargear item whose rules arrived after its datasheet: the Battlewagon's
Zzap gun (a dice-rolled Strength). The Warboss's Attack Squig and the Flash Gitz'
Ammo Runt were two more, and went with their pre-codex sheets (2026-09 Ork codex;
test_ork_characters.py and test_ork_specialists.py own the new ones).

Run: python test_ork_wargear.py

Built on testkit.py (see its docstring for the headless-harness traps).
"""

import os

from testkit import (
    Checks, build, script, shooting_scene,
)

from game.dice_notation import describe as describe_dice
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, BATTLEWAGON_ADD_ZZAP_GUN, BATTLEWAGON_ARD_CASE,
)
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM
from game.weapons import ZzapGunProfile

c = Checks("Ork wargear")

BW_CHOICES = {"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1, BATTLEWAGON_ADD_ZZAP_GUN: 1}}
BW_GEAR = {"Battlewagon": [BATTLEWAGON_ARD_CASE]}

# ---------------------------------------------------------------------------
# 1. Zzap gun: the profile
# ---------------------------------------------------------------------------

zzap = ZzapGunProfile()
c.eq("range", zzap.range_in, 36)
c.eq("attacks", zzap.attacks, 1)
c.eq("AP", zzap.ap, -3)
c.eq("damage", zzap.damage, 5)
c.eq("anti-vehicle 4+", zzap.anti, (("VEHICLE", 4),))
c.eq("needs no BS override (matches the Battlewagon's 5+)", zzap.ballistic_skill, None)
c.true("Strength is a dice notation, not a fixed number", zzap.strength_notation is not None)
c.eq("...printed as D6+6", describe_dice(zzap.strength_notation), "D6+6")
c.eq("...over sides 6", zzap.strength_notation.sides, 6)
c.eq("...plus 6", zzap.strength_notation.bonus, 6)
c.true("the fixed `strength` is only a placeholder, inside D6+6's real range",
       7 <= zzap.strength <= 12)

wagon = build(BATTLEWAGON, name="Battlewagon", gear=BW_GEAR, choices=BW_CHOICES)
c.eq("the Battlewagon carries it", sorted(w.name for w in wagon.models[0].weapons),
     ["Big Shoota"] * 4 + ["Tracks and Wheels", "Zzap Gun"])
c.eq("and it is still 160 points (both additions are free)", wagon.points, 160)


# ---------------------------------------------------------------------------
# 2. Zzap gun: the Strength is really rolled, END TO END
# ---------------------------------------------------------------------------

def fire_zzap(strength_die, hit=6, wound=4, target_sheet=DEVILFISH):
    """One Zzap gun shot through the real controller. `strength_die` is what
    the D6 comes up as, so the resolved Strength is that + 6."""
    scene = shooting_scene(BATTLEWAGON, target_sheet, gap=10.0,
                           attacker_choices=BW_CHOICES)
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    sc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in sc.weapon_eligibility() if "Zzap" in str(rest[0]))
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


scene, step = fire_zzap(strength_die=3)
c.eq("a Strength step really happens, before the wound roll", step, "strength")
c.true("...and it is a visible dice roll",
       any("strength" in label.lower() for label, _ in scene["dice"].rolled))
c.true("...logged with the resolved value", scene["log"].has("Strength 9"))

# The whole point: the rolled value, not the placeholder, decides the wound
# threshold. The Devilfish is T9, so S7 needs a 5+ and S12 a 3+ - a wound
# roll of exactly 3 separates them completely. Same hit die, same wound die;
# only the Strength differs.
#
# 3 rather than the more obvious 4: this weapon's own [ANTI-VEHICLE 4+]
# makes an unmodified 4 a CRITICAL wound against a VEHICLE regardless of
# Strength, which would mask exactly the difference under test. Checked the
# hard way - the first version of this used 4 and passed for the wrong
# reason.
def wounds_from_log(scene):
    # A regex, not a split: the controller prefixes its lines with the
    # player name ("Player 2: Zzap Gun wound roll [4]: 0 wound(s) ..."), so
    # splitting on the first ": " lands in the wrong place.
    import re
    match = re.search(r"(\d+) wound\(s\)", scene["log"].find("wound roll"))
    return int(match.group(1)) if match else None


weak, _ = fire_zzap(strength_die=1, wound=3)
strong, _ = fire_zzap(strength_die=6, wound=3)
c.true("both runs reached the wound step",
       weak["log"].has("wound roll") and strong["log"].has("wound roll"))
c.eq("S7 vs T9 (needs 5+): a wound roll of 3 fails", wounds_from_log(weak), 0)
c.eq("S12 vs T9 (needs 3+): the same 3 wounds", wounds_from_log(strong), 1)
# And the masking effect itself, since it is worth pinning down: a 4 wounds
# either way, because [ANTI-VEHICLE 4+] makes it a critical wound.
c.eq("a 4 wounds even at S7, via [ANTI-VEHICLE 4+]",
     wounds_from_log(fire_zzap(strength_die=1, wound=4)[0]), 1)
c.true("...and the two rolled different Strengths",
       weak["log"].has("Strength 7") and strong["log"].has("Strength 12"))

# A weapon WITHOUT a dice Strength must not gain a Strength step.
plain = shooting_scene(BATTLEWAGON, DEVILFISH, gap=10.0, attacker_choices=BW_CHOICES)
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
# 3. (The Warboss's Attack Squig was here; the 2026-09 codex dropped it.)
# ---------------------------------------------------------------------------

import game.weapons as _weapons
c.true("the Attack Squig profile is gone with the pre-codex Warboss",
       not hasattr(_weapons, "AttackSquigProfile"))


# ---------------------------------------------------------------------------
# 4. (The Flash Gitz' Ammo Runt was here; the 2026-09 codex dropped it.)
# ---------------------------------------------------------------------------

c.true("game/ammo_runt.py is gone with the pre-codex Flash Gitz",
       not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "game", "ammo_runt.py")))

c.finish()
